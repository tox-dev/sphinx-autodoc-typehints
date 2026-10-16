"""Finds the `.pyi` stub of an object, reads its annotations, and builds the namespace they evaluate in."""

from __future__ import annotations

from .context import stub_context
from .extract import find_ast_node, stub_annotations
from .find import parse_stub_ast, stub_path

__all__ = [
    "find_ast_node",
    "parse_stub_ast",
    "stub_annotations",
    "stub_context",
    "stub_path",
]
