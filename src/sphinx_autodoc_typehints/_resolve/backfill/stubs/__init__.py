"""Finds the `.pyi` stub of an object, reads its annotations, and builds the namespace they evaluate in."""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._resolve.backfill.stubs.context",
    "sphinx_autodoc_typehints._resolve.backfill.stubs.extract",
    "sphinx_autodoc_typehints._resolve.backfill.stubs.find",
]

from sphinx_autodoc_typehints._resolve.backfill.stubs.context import stub_context
from sphinx_autodoc_typehints._resolve.backfill.stubs.extract import find_ast_node, stub_annotations
from sphinx_autodoc_typehints._resolve.backfill.stubs.find import parse_stub_ast, stub_path

__all__ = [
    "find_ast_node",
    "parse_stub_ast",
    "stub_annotations",
    "stub_context",
    "stub_path",
]
