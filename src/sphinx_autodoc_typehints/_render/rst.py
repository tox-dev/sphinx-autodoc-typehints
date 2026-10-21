"""Parsing a rendered type inside the document being read, and dropping the markers docutils leaves on unescaping."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from docutils.frontend import get_default_settings
from docutils.utils import new_document
from sphinx.parsers import RSTParser

if TYPE_CHECKING:
    from docutils import nodes
    from docutils.statemachine import StringList
    from sphinx.environment import BuildEnvironment


def parse(inputstr: str, env: BuildEnvironment) -> nodes.document:
    """Return the document `inputstr` parses to, for a caller inside `sphinx_domains` that reports its warnings."""
    # the document being read carries the settings of its writer, which lack the rST parser's (man has no tab_width)
    settings = get_default_settings(RSTParser)
    settings.env = env
    # the caller reports them against the spot in the document being read rather than this detached snippet
    settings.warning_stream = False
    doc = new_document("", settings=settings)
    # entering sphinx_domains again would shadow the intersphinx dispatcher layered on top of it, losing the external+
    # roles the read phase resolves (#753)
    _SnippetParser().parse(inputstr, doc)
    return doc


# the prolog and the epilog belong to a document, not to each type text parsed into it
class _SnippetParser(RSTParser):
    @override
    def decorate(self, content: StringList) -> None:
        pass


def unescape(escaped: str) -> str:
    """Return `escaped` without the null markers docutils leaves before each character it unescaped."""
    return escaped.replace("\x00", "")


__all__ = [
    "parse",
    "unescape",
]
