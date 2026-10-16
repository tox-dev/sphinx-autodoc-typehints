"""Evaluates annotations where a type checker would."""

from __future__ import annotations

from .expression import evaluate_annotation, resolve_string_annotations, unevaluated_annotations
from .type_hints import type_hints

__all__ = [
    "evaluate_annotation",
    "resolve_string_annotations",
    "type_hints",
    "unevaluated_annotations",
]
