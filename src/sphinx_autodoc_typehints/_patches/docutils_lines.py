"""
Patch that puts the line number on a doctest block, which docutils 0.21 leaves one line past the block's first.

Placing the `:rtype:` field reads that line number.
"""

from __future__ import annotations

__lazy_modules__ = ["docutils"]

from functools import wraps
from typing import TYPE_CHECKING

from docutils import __version_info__, nodes
from docutils.parsers.rst.states import Body

if TYPE_CHECKING:
    from re import Match


def patch_doctest_line_number() -> None:
    """Put a doctest block on its first line, as docutils 0.22 does, for the `:rtype:` placement to read."""
    # Sphinx 9.1 still allows docutils 0.21; drop the patch once it requires 0.22
    if __version_info__ < (0, 22):  # pragma: no cover  # tests run against the newest docutils
        Body.doctest = _patched_body_doctest  # ty: ignore[invalid-assignment]  # wraps returns a _Wrapped


@wraps(Body.doctest)
def _patched_body_doctest(  # pragma: no cover  # installed only on docutils 0.21
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
    "patch_doctest_line_number",
]
