"""Reading the keys of a TypedDict the way a reader of its documentation needs them."""

from __future__ import annotations

from typing import Annotated, Any, NotRequired, get_args, get_origin, get_type_hints


def typed_dict_keys(typed_dict: Any) -> dict[str, Any]:
    """
    Return the keys of a TypedDict with their types, a key that may be left out as ``NotRequired``.

    Empty for anything else, and for a TypedDict whose annotations do not resolve.
    """
    if not hasattr(typed_dict, "__optional_keys__"):
        return {}
    try:
        hints = get_type_hints(typed_dict, include_extras=True)
    except (NameError, TypeError):
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


__all__ = ["typed_dict_keys"]
