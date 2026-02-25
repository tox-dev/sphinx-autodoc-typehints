"""Backfill annotations from attrs field metadata."""

from __future__ import annotations

from typing import Any


def backfill_attrs_annotations(obj: Any) -> None:
    try:
        from attrs import fields, has  # noqa: PLC0415
    except ImportError:
        return
    if not has(obj):
        return
    if (annotations := getattr(obj, "__annotations__", None)) is None:
        annotations = {}
        obj.__annotations__ = annotations
    for field in fields(obj):
        if field.name not in annotations and field.type is not None:
            annotations[field.name] = field.type


__all__ = ["backfill_attrs_annotations"]
