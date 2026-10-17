"""Helpers every docstring style shares, for placing the return type and the default of a parameter."""

from __future__ import annotations

from dataclasses import dataclass
from inspect import Parameter
from itertools import pairwise
from re import match
from typing import TYPE_CHECKING

from sphinx.util.inspect import object_description

from sphinx_autodoc_typehints._render import value_markup

if TYPE_CHECKING:
    from sphinx.application import Sphinx


@dataclass(frozen=True, slots=True)
class InsertIndexInfo:
    """Where the return type goes, and which field or block of the docstring sits there."""

    insert_index: int
    found_return: bool = False
    found_rtype: bool = False
    deferred: bool = False


def format_default(app: Sphinx, default: object, *, annotated: bool) -> str | None:
    """Describe a default the way `typehints_defaults` asks, after a type when `annotated` or on its own."""
    if default is Parameter.empty:
        return None
    style = app.config.typehints_defaults
    if style == "optional":
        return ", optional" if annotated else " (optional)"
    formatted = value_markup(object_description(default))
    if style.startswith("braces") if annotated else style == "braces-after":
        return f" (default: {formatted})"
    return f"{', ' if annotated else ''}default: {formatted}"


def last_paragraph_end(lines: list[str], at: int) -> int:
    """
    Return the index of the line ending the last plain paragraph of the description the field at `at` starts.

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
    indent = min((line_indent(lines[line_at]) for block in blocks for line_at in block if line_at != at), default=0)
    end = blocks[0][-1]
    for previous, block in pairwise(blocks):
        first = lines[block[0]]
        if not (
            lines[previous[-1]].endswith("::")
            or line_indent(first) > indent
            or match(r"\s*(?:[-*+]|\d+[.)]|#\.|\.\.)\s", first)
        ):
            end = block[-1]
    return end


def line_indent(line: str) -> int:
    return len(line) - len(line.lstrip())


__all__ = [
    "InsertIndexInfo",
    "format_default",
    "last_paragraph_end",
    "line_indent",
]
