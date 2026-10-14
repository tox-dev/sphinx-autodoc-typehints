"""Reading the keys of a TypedDict the way a reader of its documentation needs them."""

from __future__ import annotations

import sys
import typing
from typing import TYPE_CHECKING, Annotated, Any, Final, Never, NotRequired, cast, get_args, get_origin, get_type_hints

from sphinx import addnodes
from sphinx.domains.python._annotations import _parse_annotation  # ruff:ignore[import-private-name]  # no public parser

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


def mark_optional_keys(app: Sphinx, domain: str, objtype: str, contentnode: addnodes.desc_content) -> None:
    """
    Show a TypedDict key that may be left out as ``NotRequired``, also where ``total=False`` alone makes it so.

    autodoc shows a key's annotation as written, which under ``total=False`` reads as if the key were required.
    """
    if domain != "py" or objtype != "attribute":
        return
    for signode in cast("addnodes.desc", contentnode.parent).children:
        if isinstance(signode, addnodes.desc_signature) and (typed := _unmarked_optional_type(signode)) is not None:
            # the children after the ": " separator are the type
            del typed[2:]
            typed.extend(_parse_annotation(f"~typing.NotRequired[{typed.rawsource}]", app.env))


def _unmarked_optional_type(signode: addnodes.desc_signature) -> addnodes.desc_annotation | None:
    """Return the type shown for a TypedDict key that may be left out, unless it says so already."""
    key = signode.get("fullname", "").rpartition(".")[2]
    if (annotation := typed_dict_keys(_owner(signode)).get(key)) is None or not _is_not_required(annotation):
        return None
    typed = next((node for node in signode if isinstance(node, addnodes.desc_annotation)), None)
    # none when autodoc_typehints = "none" hides it
    if typed is None or "NotRequired" in typed.rawsource:
        return None
    return typed


def _owner(signode: addnodes.desc_signature) -> Any:
    owner: Any = sys.modules.get(signode.get("module") or "")
    for part in signode.get("fullname", "").split(".")[:-1]:
        owner = getattr(owner, part, None)
    return owner


def _is_not_required(annotation: Any) -> bool:
    if get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    return get_origin(annotation) is NotRequired


__all__ = ["inject_extra_items", "mark_optional_keys", "typed_dict_keys"]
