"""
Parses a docstring without warnings to find the line where the return type goes.

Directives only Sphinx knows parse as placeholders, which keep their place in the document.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.util import logging

from sphinx_autodoc_typehints._private_imports import BUILTIN_DIRECTIVES
from sphinx_autodoc_typehints._render import parse

if TYPE_CHECKING:
    from types import ModuleType

    from docutils.nodes import Node
    from sphinx.environment import BuildEnvironment


def safe_parse(inputstr: str, env: BuildEnvironment) -> nodes.document:
    """Parse a docstring with the directives only Sphinx knows standing in as placeholders, and no warnings."""
    original_lookup = directives.directive

    def safe_lookup(
        directive_name: str,
        language_module: ModuleType,
        document: nodes.document,
    ) -> tuple[type[Directive] | None, list[nodes.system_message]]:
        cls, messages = original_lookup(directive_name, language_module, document)
        if cls is not None and directive_name not in BUILTIN_DIRECTIVES:
            return _NoOpDirective, messages
        return cls, messages

    # the real parse repeats this parse's warnings with the right line number, and autodoc also processes members it
    # then leaves out, imported ones among them, so Sphinx's log stays quiet here as `parse` keeps docutils' stream
    directives.directive = safe_lookup  # ty: ignore[invalid-assignment]  # https://github.com/astral-sh/ty/issues/3962
    try:
        with logging.suppress_logging():
            return parse(inputstr, env)
    finally:
        directives.directive = original_lookup


class _NoOpDirective(Directive):
    has_content = True
    optional_arguments = 99
    final_argument_whitespace = True

    def run(self) -> list[nodes.Node]:
        # a node keeps the directive's place, so the return type lands before it as before a docutils directive
        placeholder = SphinxDirectivePlaceholder()
        placeholder.line = self.lineno
        return [placeholder]


class SphinxDirectivePlaceholder(nodes.Element):
    """Stand in for a directive only Sphinx knows, during the parse that finds where the return type goes."""


def node_line_no(node: Node) -> int | None:
    """Return the line of `node`, or of its first descendant with one, `None` when none has a line."""
    while node.line is None and node.children:
        node = node.children[0]
    return node.line


__all__ = [
    "SphinxDirectivePlaceholder",
    "node_line_no",
    "safe_parse",
]
