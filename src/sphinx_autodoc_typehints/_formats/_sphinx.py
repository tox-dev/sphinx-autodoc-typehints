"""
Sphinx field list format handler for standard ``:param:``/``:type:``/``:rtype:`` docstrings.

Implements `DocstringFormat` for docstrings that use Sphinx-native field list syntax, which is
also the output format produced by Napoleon when processing Google or NumPy-style docstrings.
This is the default fallback format when no other format is detected.
"""

from __future__ import annotations

import collections.abc
import re
from itertools import pairwise
from typing import TYPE_CHECKING, Any, Literal

from docutils import nodes
from docutils.frontend import get_default_settings
from docutils.parsers.rst import Directive, directives
from docutils.utils import new_document
from sphinx.parsers import RSTParser
from sphinx.util import logging

from sphinx_autodoc_typehints._parser import _RstSnippetParser

from ._base import DocstringFormat, InsertIndexInfo

if TYPE_CHECKING:
    import optparse

    from docutils.frontend import Values
    from docutils.nodes import Node
    from sphinx.application import Sphinx

_BUILTIN_DIRECTIVES = frozenset(directives._directive_registry)  # ruff:ignore[private-member-access]

PARAM_SYNONYMS = ("param ", "parameter ", "arg ", "argument ", "keyword ", "kwarg ", "kwparam ")

_GENERATOR_TYPES = frozenset({
    collections.abc.Generator,
    collections.abc.Iterator,
    collections.abc.AsyncGenerator,
    collections.abc.AsyncIterator,
})


def _get_sphinx_line_keyword_and_argument(line: str) -> tuple[str, str | None] | None:
    # an indented field belongs to the block around it, such as a literal block or a note, not to the object
    if not line.startswith(":"):
        return None
    param_line_without_description = line.split(":", maxsplit=2)
    if len(param_line_without_description) != 3:  # ruff:ignore[magic-value-comparison]
        return None

    split_directive_and_name = param_line_without_description[1].split(maxsplit=1)
    if len(split_directive_and_name) != 2:  # ruff:ignore[magic-value-comparison]
        if not len(split_directive_and_name):
            return None
        return split_directive_and_name[0], None

    return tuple(split_directive_and_name)  # type: ignore[return-value]


def _line_is_param_line_for_arg(line: str, arg_name: str) -> bool:
    keyword_and_name = _get_sphinx_line_keyword_and_argument(line)
    if keyword_and_name is None:
        return False

    keyword, doc_name = keyword_and_name
    if doc_name is None:
        return False

    if f"{keyword} " not in PARAM_SYNONYMS:
        return False

    if any(doc_name == prefix + arg_name for prefix in ("", "\\*", "\\**", "\\*\\*")):
        return True
    # Match `:param type name:` format where inline type precedes the argument name.
    return any(doc_name.endswith(f" {prefix}{arg_name}") for prefix in ("", "\\*", "\\**", "\\*\\*"))


def _strip_inline_param_type(line: str, arg_name: str) -> tuple[str, str] | None:
    """Split the type written in a ``:param type name:`` field off, returning the field without it and that type."""
    parts = line.split(":", maxsplit=2)
    if len(parts) != 3:  # ruff:ignore[magic-value-comparison]
        return None
    directive_and_name = parts[1]
    for prefix in ("", "\\*", "\\**", "\\*\\*"):
        suffix = f" {prefix}{arg_name}"
        if directive_and_name.endswith(suffix):
            keyword, _, inline_type = directive_and_name.removesuffix(suffix).partition(" ")
            return f":{keyword} {prefix}{arg_name}:{parts[2]}", inline_type.strip()
    return None


def _is_generator_type(annotation: Any) -> bool:
    origin = getattr(annotation, "__origin__", None)
    return origin in _GENERATOR_TYPES or annotation in _GENERATOR_TYPES


def _has_yields_section(lines: list[str]) -> bool:
    return any(line.startswith((":Yields:", ":yields:", ":yield:")) for line in lines)


def _safe_parse(inputstr: str, settings: Values | optparse.Values) -> nodes.document:
    original_lookup = directives.directive

    def _safe_directive_lookup(
        directive_name: str,
        language_module: Any,
        document: Any,
    ) -> tuple[type[Directive] | None, list[Any]]:
        cls, messages = original_lookup(directive_name, language_module, document)
        if cls is not None and directive_name not in _BUILTIN_DIRECTIVES:
            return _NoOpDirective, messages
        return cls, messages

    # Whatever this parse has to say about the docstring, the real parse says again with the right line number,
    # so its warnings are only duplicates; docutils writes them to its own stream, Sphinx logs the rest. The
    # docstring may not even be rendered: autodoc processes members it then leaves out, imported ones among them
    settings.warning_stream = False
    doc = new_document("", settings=settings)  # ty: ignore[invalid-argument-type]
    # The read phase already runs inside sphinx_domains; entering it again shadows the intersphinx
    # dispatcher layered on top of it, losing the external+ roles (#753)
    directives.directive = _safe_directive_lookup  # type: ignore[assignment]
    try:
        with logging.suppress_logging():
            _RstSnippetParser().parse(inputstr, doc)
    finally:
        directives.directive = original_lookup
    return doc


class _NoOpDirective(Directive):
    has_content = True
    optional_arguments = 99
    final_argument_whitespace = True

    def run(self) -> list[nodes.Node]:
        # a node keeps the directive's place, so the return type lands before it as before a docutils directive
        placeholder = _SphinxDirectivePlaceholder()
        placeholder.line = self.lineno
        return [placeholder]


class _SphinxDirectivePlaceholder(nodes.Element):
    """Stand in for a directive only Sphinx knows, during the parse that finds where the return type goes."""


def _node_line_no(node: Node) -> int | None:
    if node is None:
        return None
    while node.line is None and node.children:
        node = node.children[0]
    return node.line


def _tag_name(node: Node) -> str:
    return node.tagname


class SphinxFieldListFormat(DocstringFormat):
    @staticmethod
    def detect(lines: list[str]) -> bool:  # ruff:ignore[unused-static-method-argument]
        return True

    def find_param(self, lines: list[str], arg_name: str) -> int | None:  # ruff:ignore[no-self-use]
        for at, line in enumerate(lines):
            if _line_is_param_line_for_arg(line, arg_name):
                return at
        return None

    def inject_param_type(self, lines: list[str], arg_name: str, formatted_type: str, at: int) -> None:  # ruff:ignore[no-self-use]
        lines.insert(at, f":type {arg_name}: {formatted_type}")

    def add_undocumented_param(  # ruff:ignore[no-self-use]
        self,
        lines: list[str],
        arg_name: str,
        description: str = "",
        *,
        before: int | None = None,
        field: Literal["param", "keyword"] = "param",
    ) -> int:
        # beside the documented parameters, not after whatever the docstring ends with, such as its examples
        if before is not None:
            at = before
        elif (at := _after_last_param_field(lines)) is None:
            # the first field after text, which a blank line has to separate a field list from
            if lines and lines[-1].strip():
                lines.append("")
            at = len(lines)
        lines.insert(at, f":{field} {arg_name}: {description}".rstrip())
        return at

    def find_preexisting_type(self, lines: list[str], arg_name: str) -> tuple[str, bool]:  # ruff:ignore[no-self-use]
        # napoleon types a keyword argument with kwtype, and paramtype works for both parameter kinds
        fields = tuple(f":{field} {arg_name}: " for field in ("type", "paramtype", "kwtype"))
        return next(((line, True) for line in lines if line.startswith(fields)), (fields[0], False))

    def has_return_description(self, lines: list[str]) -> bool:  # ruff:ignore[no-self-use]
        return any(line.startswith((":return:", ":returns:")) for line in lines)

    def get_rtype_insert_info(self, app: Sphinx, lines: list[str]) -> InsertIndexInfo | None:  # ruff:ignore[no-self-use]
        rtype_at = _remove_rtype(lines)
        return_at = next((i for i, line in enumerate(lines) if line.startswith((":return:", ":returns:"))), None)
        # inline mode merges the type into the :return: entry, so it replaces a preexisting :rtype: only without one
        if rtype_at is not None and (app.config.typehints_use_rtype or return_at is None):
            return InsertIndexInfo(insert_index=rtype_at)
        if return_at is not None:
            return InsertIndexInfo(insert_index=return_at, found_return=True, found_rtype=rtype_at is not None)

        settings = get_default_settings(RSTParser)  # type: ignore[arg-type]
        settings.env = app.env
        doc = _safe_parse("\n".join(lines), settings)

        for child in doc.children:
            if _tag_name(child) != "field_list":
                continue

            if not any(c.children[0].astext().startswith(PARAM_SYNONYMS) for c in child.children):
                continue

            next_sibling = child.next_node(descend=False, siblings=True)
            line_no = _node_line_no(next_sibling) if next_sibling else None
            at = max(line_no - 2, 0) if line_no else len(lines)
            return InsertIndexInfo(insert_index=at, found_param=True)

        for child in doc.children:
            if (tag := _tag_name(child)) in {
                "literal_block",
                "paragraph",
                "field_list",
                _SphinxDirectivePlaceholder.__name__,
            }:
                continue
            line_no = _node_line_no(child)
            # placement before a doctest block was tuned while it reported the line after its first one
            at = max(line_no - (1 if tag == "doctest_block" else 2), 0) if line_no else len(lines)
            if lines[at - 1]:
                break
            return InsertIndexInfo(insert_index=at, found_directive=True)

        return InsertIndexInfo(insert_index=len(lines))

    def inject_rtype(  # ruff:ignore[no-self-use]
        self,
        lines: list[str],
        formatted_annotation: str,
        info: InsertIndexInfo,
        *,
        use_rtype: bool,
    ) -> None:
        insert_index = info.insert_index

        # beside an :rtype: field, the :returns: text describes the value rather than stating its type
        if not use_rtype and info.found_return and not info.found_rtype and _gives_its_type(lines[insert_index]):
            return

        if info.found_param and insert_index < len(lines) and lines[insert_index].strip():
            insert_index -= 1

        if insert_index > 0 and insert_index <= len(lines) and lines[insert_index - 1].strip():
            lines.insert(insert_index, "")
            insert_index += 1

        if use_rtype or not info.found_return:
            lines.insert(insert_index, f":rtype: {formatted_annotation}")
            if info.found_directive:
                lines.insert(insert_index + 1, "")
        elif description := lines[insert_index].split(":", 2)[2].strip():
            lines[insert_index] = f":return: {formatted_annotation} -- {description}"
        else:
            # the description starts on the next line, and a block such as a list cannot follow inline text
            lines[insert_index : insert_index + 1] = [f":return: {formatted_annotation} --", ""]

    def append_default(  # ruff:ignore[no-self-use]
        self,
        lines: list[str],
        insert_index: int,
        type_annotation: str,
        formatted_default: str,
        *,
        after: bool,
    ) -> str:
        if after:
            end = _last_paragraph_end(lines, insert_index)
            # a paragraph introducing a literal block keeps its :: last
            if (line := lines[end]).endswith("::"):
                lines[end] = f"{line[:-2].rstrip()}{formatted_default}::"
            else:
                lines[end] += formatted_default
        else:
            type_annotation += formatted_default
        return type_annotation

    @staticmethod
    def get_arg_name_from_line(line: str) -> str | None:
        result = _get_sphinx_line_keyword_and_argument(line)
        if result is None:
            return None
        _, arg_name = result
        return arg_name


def _last_paragraph_end(lines: list[str], at: int) -> int:
    """
    Find the line ending the last plain paragraph of the description the field at ``at`` starts.

    A list, a directive such as a note, a literal block, or deeper indented text after it is not a place for the
    default, which would render inside that block.
    """
    blocks: list[list[int]] = [[at]]
    index = at + 1
    while index < len(lines) and (not lines[index].strip() or lines[index][0].isspace()):
        if not lines[index].strip():
            blocks.append([])
        else:
            blocks[-1].append(index)
        index += 1
    blocks = [block for block in blocks if block]
    indent = min((_indent(lines[line_at]) for block in blocks for line_at in block if line_at != at), default=0)
    end = blocks[0][-1]
    for previous, block in pairwise(blocks):
        first = lines[block[0]]
        if not (
            lines[previous[-1]].endswith("::")
            or _indent(first) > indent
            or re.match(r"\s*(?:[-*+]|\d+[.)]|#\.|\.\.)\s", first)
        ):
            end = block[-1]
    return end


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _after_last_param_field(lines: list[str]) -> int | None:
    """Return the index past the last parameter field and its continuation lines, if the docstring has one."""
    fields = ("type", *(synonym.strip() for synonym in PARAM_SYNONYMS))
    found = (
        at
        for at, line in enumerate(lines)
        if (field := _get_sphinx_line_keyword_and_argument(line)) and field[0] in fields
    )
    return None if (last := max(found, default=None)) is None else _field_end(lines, last)


def _remove_rtype(lines: list[str]) -> int | None:
    """Remove the docstring's :rtype: field, which the annotation replaces, and return where it was."""
    if (rtype_at := next((i for i, line in enumerate(lines) if line.startswith(":rtype:")), None)) is None:
        return None
    del lines[rtype_at : _field_end(lines, rtype_at)]
    return rtype_at


def _field_end(lines: list[str], at: int) -> int:
    """Return the index past the field at ``at`` and its indented continuation lines."""
    end = at + 1
    while end < len(lines) and lines[end][:1].isspace() and lines[end].strip():
        end += 1
    return end


def _gives_its_type(return_line: str) -> bool:
    """
    Whether a ``:returns: X -- text`` field states its type as ``X``, as napoleon writes it without an rtype field.

    Only text that reads as a type counts: napoleon's emphasized ``*int*``, a role or literal, or a single token once
    its brackets are dropped, so a description that itself contains `` -- `` keeps getting the type.
    """
    if " -- " not in (description := return_line.split(":", 2)[2].strip()):
        return False
    stated = description.split(" -- ", 1)[0]
    if stated.startswith(("*", ":", "`")):
        return True
    while (unbracketed := re.sub(r"\[[^\[\]]*\]", "", stated)) != stated:
        stated = unbracketed
    return " " not in stated
