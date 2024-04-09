"""Utilities for side-effect-free rST parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils.utils import new_document
from sphinx.parsers import RSTParser
from sphinx.util.docutils import sphinx_domains

if TYPE_CHECKING:
    import optparse

    from docutils import nodes
    from docutils.frontend import Values
    from docutils.statemachine import StringList


class _RstSnippetParser(RSTParser):
    @staticmethod
    def decorate(_content: StringList) -> None:
        """Override to skip processing rst_epilog/rst_prolog for typing."""


def parse(inputstr: str, settings: Values | optparse.Values) -> nodes.document:
    """Parse inputstr and return a docutils document."""
    doc = new_document("", settings=settings)
    with sphinx_domains(settings.env):
        parser = _RstSnippetParser()
        parser.set_application(settings.env.app)
        parser.parse(inputstr, doc)
    return doc
