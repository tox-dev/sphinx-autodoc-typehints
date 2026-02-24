"""
Sphinx field list format handler for standard ``:param:``/``:type:``/``:rtype:`` docstrings.

Implements `DocstringFormat` for docstrings that use Sphinx-native field list syntax, which is
also the output format produced by Napoleon when processing Google or NumPy-style docstrings.
This is the default fallback format when no other format is detected.
"""

from __future__ import annotations

import collections.abc
from typing import TYPE_CHECKING, Any

from docutils.frontend import get_default_settings
from docutils.parsers.rst import Directive, directives
from docutils.utils import new_document
from sphinx.parsers import RSTParser
from sphinx.util.docutils import sphinx_domains

from sphinx_autodoc_typehints._parser import _RstSnippetParser

from ._base import DocstringFormat, InsertIndexInfo

if TYPE_CHECKING:
    import optparse

    from docutils import nodes
    from docutils.frontend import Values
    from docutils.nodes import Node
    from sphinx.application import Sphinx

_BUILTIN_DIRECTIVES = frozenset(directives._directive_registry)  # noqa: SLF001

PARAM_SYNONYMS = ("param ", "parameter ", "arg ", "argument ", "keyword ", "kwarg ", "kwparam ")

_GENERATOR_TYPES = frozenset({
    collections.abc.Generator,
    collections.abc.Iterator,
    collections.abc.AsyncGenerator,
    collections.abc.AsyncIterator,
})


def _get_sphinx_line_keyword_and_argument(line: str) -> tuple[str, str | None] | None:
    param_line_without_description = line.split(":", maxsplit=2)
    if len(param_line_without_description) != 3:  # noqa: PLR2004
        return None

    split_directive_and_name = param_line_without_description[1].split(maxsplit=1)
    if len(split_directive_and_name) != 2:  # noqa: PLR2004
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

    if keyword not in {"param", "parameter", "arg", "argument"}:
        return False

    return any(doc_name == prefix + arg_name for prefix in ("", "\\*", "\\**", "\\*\\*"))


def _is_generator_type(annotation: Any) -> bool:
    origin = getattr(annotation, "__origin__", None)
    return origin in _GENERATOR_TYPES or annotation in _GENERATOR_TYPES


def _has_yields_section(lines: list[str]) -> bool:
    return any(line.lstrip().startswith((":Yields:", ":yields:", ":yield:")) for line in lines)


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

    doc = new_document("", settings=settings)  # ty: ignore[invalid-argument-type]
    with sphinx_domains(settings.env):
        directives.directive = _safe_directive_lookup  # type: ignore[assignment]
        try:
            parser = _RstSnippetParser()
            parser.parse(inputstr, doc)
        finally:
            directives.directive = original_lookup
    return doc


class _NoOpDirective(Directive):
    has_content = True
    optional_arguments = 99
    final_argument_whitespace = True

    def run(self) -> list[nodes.Node]:  # noqa: PLR6301
        return []


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
    def detect(lines: list[str]) -> bool:  # noqa: ARG004
        return True

    def find_param(self, lines: list[str], arg_name: str) -> int | None:  # noqa: PLR6301
        for at, line in enumerate(lines):
            if _line_is_param_line_for_arg(line, arg_name):
                return at
        return None

    def inject_param_type(self, lines: list[str], arg_name: str, formatted_type: str, at: int) -> None:  # noqa: PLR6301
        lines.insert(at, f":type {arg_name}: {formatted_type}")

    def add_undocumented_param(self, lines: list[str], arg_name: str) -> int:  # noqa: PLR6301
        lines.append(f":param {arg_name}:")
        return len(lines) - 1

    def find_preexisting_type(self, lines: list[str], arg_name: str) -> tuple[str, bool]:  # noqa: PLR6301
        type_annotation = f":type {arg_name}: "
        for line in lines:
            if line.startswith(type_annotation):
                return line, True
        return type_annotation, False

    def get_rtype_insert_info(self, app: Sphinx, lines: list[str]) -> InsertIndexInfo | None:  # noqa: PLR6301
        if any(line.startswith(":rtype:") for line in lines):
            return None

        for at, line in enumerate(lines):
            if line.startswith((":return:", ":returns:")):
                return InsertIndexInfo(insert_index=at, found_return=True)

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
            if _tag_name(child) in {"literal_block", "paragraph", "field_list"}:
                continue
            line_no = _node_line_no(child)
            at = max(line_no - 2, 0) if line_no else len(lines)
            if lines[at - 1]:
                break
            return InsertIndexInfo(insert_index=at, found_directive=True)

        return InsertIndexInfo(insert_index=len(lines))

    def inject_rtype(  # noqa: PLR6301
        self,
        lines: list[str],
        formatted_annotation: str,
        info: InsertIndexInfo,
        *,
        use_rtype: bool,
    ) -> None:
        insert_index = info.insert_index

        if not use_rtype and info.found_return and " -- " in lines[insert_index]:
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
        else:
            line = lines[insert_index]
            lines[insert_index] = f":return: {formatted_annotation} --{line[line.find(' ') :]}"

    def append_default(  # noqa: PLR6301
        self,
        lines: list[str],
        insert_index: int,
        type_annotation: str,
        formatted_default: str,
        *,
        after: bool,
    ) -> str:
        if after:
            nlines = len(lines)
            next_index = insert_index + 1
            append_index = insert_index
            while next_index < nlines and (not lines[next_index] or lines[next_index].startswith(" ")):
                if lines[next_index]:
                    append_index = next_index
                next_index += 1
            lines[append_index] += formatted_default
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
