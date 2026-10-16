"""Annotations for code that has none at runtime."""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._resolve.backfill.stubs",
    "sphinx_autodoc_typehints._resolve.backfill.type_comments",
]

from sphinx_autodoc_typehints._resolve.backfill.stubs import (
    find_ast_node,
    parse_stub_ast,
    stub_annotations,
    stub_context,
    stub_path,
)
from sphinx_autodoc_typehints._resolve.backfill.type_comments import backfill_type_hints

__all__ = [
    "backfill_type_hints",
    "find_ast_node",
    "parse_stub_ast",
    "stub_annotations",
    "stub_context",
    "stub_path",
]
