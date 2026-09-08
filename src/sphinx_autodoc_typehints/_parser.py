"""Utilities for side-effect-free rST parsing."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from docutils.utils import new_document
from sphinx.parsers import RSTParser

if TYPE_CHECKING:
    import optparse

    from docutils import nodes
    from docutils.frontend import Values
    from docutils.statemachine import StringList

_UNESCAPE_RE: Final = re.compile(
    r"""
    \\          # literal backslash
    ([^ ])      # followed by any non-space character (captured)
    """,
    re.VERBOSE,
)


class _RstSnippetParser(RSTParser):
    @staticmethod
    def decorate(_content: StringList) -> None:  # ty: ignore[invalid-method-override]
        """Override to skip processing rst_epilog/rst_prolog for typing."""


def parse(inputstr: str, settings: Values | optparse.Values) -> nodes.document:
    """Parse inputstr and return a docutils document. Callers must already be inside ``sphinx_domains``."""
    doc = new_document("", settings=settings)  # ty: ignore[invalid-argument-type]
    # Entering sphinx_domains again shadows the intersphinx dispatcher layered on top of it,
    # losing the external+ roles the read phase resolves (#753)
    _RstSnippetParser().parse(inputstr, doc)
    return doc


def unescape(escaped: str) -> str:
    escaped = escaped.replace("\x00", "")
    return _UNESCAPE_RE.sub(r"\1", escaped)


__all__ = ["parse", "unescape"]
