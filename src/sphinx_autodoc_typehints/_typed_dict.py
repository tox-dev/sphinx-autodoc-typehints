"""Reading the keys of a TypedDict the way a reader of its documentation needs them."""

from __future__ import annotations

import sys
import types
import typing
from typing import TYPE_CHECKING, Annotated, Any, Final, Never, NotRequired, get_args, get_origin

from ._annotations import add_type_css_class, format_annotation
from ._resolver import guarded_names, type_hints
from ._type_params import specialize, type_arguments

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx.application import Sphinx

_OPEN: Final = object()


def typed_dict_keys(typed_dict: Any, localns: Mapping[str, Any]) -> dict[str, Any]:
    """
    Return the keys of a TypedDict with their types, a key that may be left out as ``NotRequired``.

    Empty for anything else, and for a TypedDict whose annotations do not resolve.
    """
    if not hasattr(origin := get_origin(typed_dict) or typed_dict, "__optional_keys__"):
        return {}
    try:
        hints = _Hierarchy(localns).bound_hints(typed_dict)
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return {}
    return {
        key: _key_annotation(annotation, optional=key in origin.__optional_keys__) for key, annotation in hints.items()
    }


class _Hierarchy:
    """
    Read the keys of the TypedDicts in a hierarchy, each class and each base a class statement names only once.

    A diamond reaches a base along several paths, and walking every path is exponential in the depth of the hierarchy.
    """

    def __init__(self, localns: Mapping[str, Any]) -> None:
        self._localns = localns
        # keyed by identity, as a subscripted base hashes its arguments, which Annotated metadata may not support
        self._bound: dict[int, dict[str, Any]] = {}
        self._keys: dict[type, tuple[dict[str, Any], dict[str, Any]]] = {}
        self._scopes: dict[type, dict[str, Any]] = {}

    def bound_hints(self, typed_dict: Any) -> dict[str, Any]:
        """
        Return the annotations of a TypedDict, or of one it subscripts, with the type arguments bound.

        A TypedDict lists the keys of its bases as its own, with their type parameters unbound, and keeps no base in
        its MRO, so each base the class statement names supplies its keys bound by the arguments it is given there.
        """
        if (found := self._bound.get(id(typed_dict))) is not None:
            return found
        origin = get_origin(typed_dict) or typed_dict
        hints: dict[str, Any] = {}
        # the first base in the MRO decides a key two bases declare, so later bases merge in first
        for base in reversed(_typed_dict_bases(origin)):
            hints |= self.bound_hints(base)
        # a key the class redeclares, as a ReadOnly key narrows its type (PEP 705), reads as the class declares it
        hints |= self._split(origin)[1]
        arguments = type_arguments(origin, typed_dict)
        found = self._bound[id(typed_dict)] = {key: specialize(hint, arguments) for key, hint in hints.items()}
        return found

    def _split(self, typed_dict: type) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Return every key of a TypedDict and the keys it declares itself, all unbound.

        Its annotations hold each key of its bases as the last base declaring it does. The keys of a base come from that
        base's own declarations, as autodoc reassigning a base's annotations on Python 3.14 leaves a subclass reading
        none from it.
        """
        if (found := self._keys.get(typed_dict)) is not None:
            return found
        inherited: dict[str, Any] = {}
        for base in _typed_dict_bases(typed_dict):
            inherited |= self._split(get_origin(base) or base)[0]
        # a key written as a string names the type parameters of the class declaring it, which may be a base
        localns = {**guarded_names(typed_dict), **self._localns, **self._scope(typed_dict)}
        hints = type_hints(typed_dict, None, localns)
        own = {key: hint for key, hint in hints.items() if key not in inherited or not _same(inherited[key], hint)}
        found = self._keys[typed_dict] = inherited | own, own
        return found

    def _scope(self, typed_dict: type) -> dict[str, Any]:
        if (found := self._scopes.get(typed_dict)) is not None:
            return found
        scope: dict[str, Any] = {}
        for base in _typed_dict_bases(typed_dict):
            scope |= self._scope(get_origin(base) or base)
        params = {param.__name__: param for param in getattr(typed_dict, "__parameters__", ())}
        found = self._scopes[typed_dict] = scope | params
        return found


def _same(left: Any, right: Any) -> bool:
    """
    Tell whether two annotations are the same, comparing them part by part.

    A string annotation evaluates anew for each class holding it, so the parts may be equal objects rather than one,
    and comparing a whole ``Annotated`` asks its metadata, such as an array, for a truth value it may not have.
    """
    if left is right:
        return True
    if (origin := get_origin(left)) is not None:
        args, other = get_args(left), get_args(right)
        return origin is get_origin(right) and len(args) == len(other) and all(map(_same, args, other))
    try:
        return type(left) is type(right) and (left == right) is True
    except Exception:  # ruff:ignore[blind-except]  # metadata compares through user code, which may raise anything
        return False


def _typed_dict_bases(typed_dict: type) -> list[Any]:
    return [
        base for base in types.get_original_bases(typed_dict) if hasattr(get_origin(base) or base, "__optional_keys__")
    ]


def _key_annotation(annotation: Any, *, optional: bool) -> Any:
    """
    Nest the key qualifiers of a TypedDict annotation as ``NotRequired[ReadOnly[...]]``, the order the typing spec uses.

    A key that may be left out shows as ``NotRequired``, one a caller must pass without a marker. A written ``Required``
    or ``NotRequired`` decides over the class's ``__optional_keys__``, which misses both when the annotations are
    strings. ``ReadOnly`` stays, as it tells the reader the key cannot be assigned (PEP 705).
    """
    metadata: list[Any] = []
    read_only = None
    while True:
        origin = get_origin(annotation)
        qualifier = getattr(origin, "_name", None)
        if origin is not Annotated and qualifier not in {"Required", "NotRequired", "ReadOnly"}:
            break
        if qualifier in {"Required", "NotRequired"}:
            optional = qualifier == "NotRequired"
        elif qualifier == "ReadOnly":
            # the one written, as typing has none before Python 3.13
            read_only = origin
        annotation, *more = get_args(annotation)
        metadata.extend(more)
    if read_only is not None:
        annotation = read_only[annotation]
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
