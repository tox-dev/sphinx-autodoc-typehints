"""Evaluates annotations where a type checker would."""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._resolve.evaluate.expression",
    "sphinx_autodoc_typehints._resolve.evaluate.type_hints",
]

from sphinx_autodoc_typehints._resolve.evaluate.expression import (
    evaluate_annotation,
    resolve_string_annotations,
    unevaluated_annotations,
)
from sphinx_autodoc_typehints._resolve.evaluate.type_hints import type_hints

__all__ = [
    "evaluate_annotation",
    "resolve_string_annotations",
    "type_hints",
    "unevaluated_annotations",
]
