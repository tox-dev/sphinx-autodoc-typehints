"""Utilities for side-effect-free rST parsing."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import patch

from docutils.parsers.rst import Directive, directives
from docutils.utils import new_document
from sphinx.parsers import RSTParser
from sphinx.util.docutils import sphinx_domains

if TYPE_CHECKING:
    import optparse
    from collections.abc import Iterator

    from docutils import nodes
    from docutils.frontend import Values
    from docutils.statemachine import StringList


class _RstSnippetParser(RSTParser):
    @staticmethod
    def decorate(_content: StringList) -> None:  # ty: ignore[invalid-method-override]
        """Override to skip processing rst_epilog/rst_prolog for typing."""


class _NoOpDirective(Directive):
    has_content = True
    optional_arguments = 99
    final_argument_whitespace = True

    def run(self) -> list[nodes.Node]:  # noqa: PLR6301
        return []


_BUILTIN_DIRECTIVES = frozenset(directives._directive_registry)  # noqa: SLF001


@contextmanager
def _safe_directives() -> Iterator[None]:
    original = directives.directive

    def _safe_lookup(
        directive_name: str,
        language_module: object,
        document: object,
    ) -> tuple[type[Directive] | None, list[str]]:
        cls, messages = original(directive_name, language_module, document)
        if cls is not None and directive_name not in _BUILTIN_DIRECTIVES:
            return _NoOpDirective, messages
        return cls, messages

    with patch.object(directives, "directive", _safe_lookup):
        yield


def parse(inputstr: str, settings: Values | optparse.Values) -> nodes.document:
    """Parse inputstr and return a docutils document."""
    doc = new_document("", settings=settings)  # ty: ignore[invalid-argument-type]
    with sphinx_domains(settings.env), _safe_directives():
        parser = _RstSnippetParser()
        parser.parse(inputstr, doc)
    return doc
