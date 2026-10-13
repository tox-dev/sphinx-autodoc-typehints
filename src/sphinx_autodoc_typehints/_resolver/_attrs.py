"""Backfill annotations from attrs field metadata."""

from __future__ import annotations

from typing import Any


def backfill_attrs_annotations(obj: Any) -> None:
    try:
        from attrs import fields, has  # ruff:ignore[import-outside-top-level]
    except ImportError:
        return
    if not has(obj):
        return
    try:
        annotations = getattr(obj, "__annotations__", None)
    except (NameError, AttributeError, TypeError):  # pragma: >=3.14 cover
        # PEP 649 evaluates annotations on first read, so one naming something undefined fails here; such a class
        # keeps its annotations as written rather than failing the build
        return
    if annotations is None:
        annotations = {}
        obj.__annotations__ = annotations
    for field in fields(obj):
        if field.name not in annotations and field.type is not None:
            annotations[field.name] = field.type


__all__ = ["backfill_attrs_annotations"]
