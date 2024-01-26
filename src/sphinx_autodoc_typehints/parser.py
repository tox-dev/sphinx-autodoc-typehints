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


def parse(inputstr: str, settings: Values | optparse.Values) -> nodes.document:
    """Parse inputstr and return a docutils document."""
    doc = new_document("", settings=settings)
    with sphinx_domains(settings.env):
        parser = RSTParser()
        parser.set_application(settings.env.app)
        parser.parse(inputstr, doc)
    return doc
