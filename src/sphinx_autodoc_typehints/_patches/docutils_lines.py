"""
Patches that put line numbers on the nodes the docutils parser leaves without.

Placing the `:rtype:` field reads those line numbers.
"""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Final

from docutils import nodes
from docutils.parsers.rst.directives.admonitions import BaseAdmonition
from docutils.parsers.rst.states import Body, Text

if TYPE_CHECKING:
    from collections.abc import Callable
    from re import Match

_ORIGINAL_ADMONITION_RUN: Final[Callable[[BaseAdmonition], list[nodes.Node]]] = BaseAdmonition.run
_ORIGINAL_TEXT_INDENT: Final[Callable[[Text, Match[str], list[str], str], tuple[list[str], str, list[nodes.Node]]]] = (
    Text.indent
)


def patch_line_numbers() -> None:
    """Put line numbers on the nodes the rst parser leaves without, which placing the `:rtype:` field reads."""
    Text.indent = _patched_text_indent  # ty: ignore[invalid-assignment]  # wraps returns a _Wrapped
    BaseAdmonition.run = _patched_base_admonition_run  # ty: ignore[invalid-assignment]  # wraps returns a _Wrapped
    Body.doctest = _patched_body_doctest  # ty: ignore[invalid-assignment]  # wraps returns a _Wrapped


@wraps(_ORIGINAL_ADMONITION_RUN)
def _patched_base_admonition_run(self: BaseAdmonition) -> list[nodes.Node]:
    result = _ORIGINAL_ADMONITION_RUN(self)
    # the directive counts lines across included files, the node names its place within its own source file
    result[0].source, result[0].line = self.state_machine.get_source_and_line(self.lineno)
    return result


@wraps(_ORIGINAL_TEXT_INDENT)
def _patched_text_indent(
    self: Text, match: Match[str], context: list[str], next_state: str
) -> tuple[list[str], str, list[nodes.Node]]:
    _, line = self.state_machine.get_source_and_line()  # ty: ignore[unresolved-attribute]  # None only after unlink()
    result = _ORIGINAL_TEXT_INDENT(self, match, context, next_state)
    node = self.parent[-1]  # ty: ignore[not-subscriptable]  # docutils types it optional, a parsing state has one
    if node.tagname == "system_message":
        node = self.parent[-2]  # ty: ignore[not-subscriptable]  # docutils types it optional, a parsing state has one
    node.line = line
    return result


@wraps(Body.doctest)
def _patched_body_doctest(
    self: Body, _match: Match[str], _context: list[str], next_state: str
) -> tuple[list[str], str, list[nodes.Node]]:
    # read before get_text_block moves past the block
    line = self.document.current_line
    lines = self.state_machine.get_text_block()  # ty: ignore[unresolved-attribute]  # None only after unlink()
    data = "\n".join(lines)
    block = nodes.doctest_block(data, data)
    block.line = line
    self.parent += block  # ty: ignore[unsupported-operator]  # docutils types it optional, a parsing state has one
    return [], next_state, []


__all__ = [
    "patch_line_numbers",
]
