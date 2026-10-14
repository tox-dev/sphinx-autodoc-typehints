"""Reading the keys of a TypedDict the way a reader of its documentation needs them."""

from __future__ import annotations

import sys
import typing
from typing import TYPE_CHECKING, Annotated, Any, Final, Never, NotRequired, get_args, get_origin, get_type_hints

from ._annotations import add_type_css_class, format_annotation

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_OPEN: Final = object()


def typed_dict_keys(typed_dict: Any) -> dict[str, Any]:
    """
    Return the keys of a TypedDict with their types, a key that may be left out as ``NotRequired``.

    Empty for anything else, and for a TypedDict whose annotations do not resolve.
    """
    if not hasattr(typed_dict, "__optional_keys__"):
        return {}
    try:
        hints = get_type_hints(typed_dict, include_extras=True)
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return {}
    return {
        key: _key_annotation(annotation, optional=key in typed_dict.__optional_keys__)
        for key, annotation in hints.items()
    }


def _key_annotation(annotation: Any, *, optional: bool) -> Any:
    """
    Drop the key qualifiers of a TypedDict annotation, marking a key that may be left out as ``NotRequired``.

    A written ``Required`` or ``NotRequired`` decides over the class's ``__optional_keys__``, which misses both when
    the annotations are strings.
    """
    metadata: list[Any] = []
    while True:
        origin = get_origin(annotation)
        qualifier = getattr(origin, "_name", None)
        if origin is not Annotated and qualifier not in {"Required", "NotRequired", "ReadOnly"}:
            break
        if qualifier in {"Required", "NotRequired"}:
            optional = qualifier == "NotRequired"
        annotation, *more = get_args(annotation)
        metadata.extend(more)
    if optional:
        annotation = NotRequired[annotation]
    # an Annotated outermost keeps its Doc() a description
    return Annotated[annotation, *metadata] if metadata else annotation


def inject_extra_items(app: Sphinx, cls: Any, lines: list[str]) -> None:
    """
    Add what a TypedDict accepts beyond its keys, as its class options state it rather than its annotations.

    ``closed=True`` means the same as ``extra_items=Never`` (PEP 728), so both show as an ``Extra items`` type.
    """
    if (extra := _extra_items(cls)) is _OPEN or any(line.startswith(":Extra items:") for line in lines):
        return
    formatted = add_type_css_class(format_annotation(extra, app.config))
    lines.extend(["", f":Extra items: {formatted}"])


def _extra_items(typed_dict: Any) -> Any:
    """Return the type of the items a TypedDict accepts beyond its keys, which a subclass inherits, or ``_OPEN``."""
    if not hasattr(typed_dict, "__optional_keys__"):
        return _OPEN
    if (closed := getattr(typed_dict, "__closed__", None)) is True:
        return Never
    # the sentinel a TypedDict without extra_items holds, typing's from 3.15 or the backport's
    unset = (
        getattr(typing, "NoExtraItems", _OPEN),
        getattr(sys.modules.get("typing_extensions"), "NoExtraItems", _OPEN),
    )
    extra = getattr(typed_dict, "__extra_items__", _OPEN)
    if all(extra is not sentinel for sentinel in (_OPEN, *unset)):
        return extra
    if closed is False:
        return _OPEN
    return next(
        (found for base in getattr(typed_dict, "__orig_bases__", ()) if (found := _extra_items(base)) is not _OPEN),
        _OPEN,
    )


__all__ = ["inject_extra_items", "typed_dict_keys"]
