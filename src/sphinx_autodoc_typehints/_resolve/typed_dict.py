"""The items of a TypedDict with their qualifiers, bound through generic bases, and the type of its extra items."""

from __future__ import annotations

__lazy_modules__ = [
    "annotationlib",
    "sphinx_autodoc_typehints._resolve.evaluate",
    "sphinx_autodoc_typehints._resolve.generics",
    "sphinx_autodoc_typehints._resolve.guards",
    "types",
]

import typing  # NoExtraItems exists only on newer Pythons, so it is looked up at runtime
from sys import modules, version_info
from types import get_original_bases
from typing import (
    TYPE_CHECKING,
    Annotated,
    Never,
    NotRequired,
    get_args,
    get_origin,
)

from sphinx_autodoc_typehints._resolve.evaluate import type_hints
from sphinx_autodoc_typehints._resolve.generics import specialize, type_arguments
from sphinx_autodoc_typehints._resolve.guards import guarded_names
from sphinx_autodoc_typehints._types import sentinel

if version_info >= (3, 14):  # pragma: >=3.14 cover
    from annotationlib import Format, get_annotations

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import ForwardRef

    from sphinx_autodoc_typehints._types import Annotation, Documented, TypeParam


# no `Final`: ty stops reading an annotated sentinel as a type https://github.com/astral-sh/ty/issues/4737
OPEN = sentinel("OPEN")


def typed_dict_keys(typed_dict: Documented, localns: Mapping[str, Documented]) -> dict[str, Annotation]:
    """
    Return the items of a TypedDict with their types, marking one a caller may omit as `NotRequired`.

    The result is empty for anything else, and for a TypedDict whose annotations do not resolve. The qualifiers of an
    item nest as `NotRequired[ReadOnly[...]]`, the order the typing spec uses. A written `Required` or
    `NotRequired` decides over the class's `__optional_keys__`, which misses both when the annotations are strings.
    `ReadOnly` stays, as it tells the reader that code cannot assign the item (PEP 705).
    """
    # an attribute read, not a runtime-checkable Protocol: below Python 3.14 the protocol check reads the class's
    # `__annotations__`, which creates an empty dict on a class without one and changes the members autodoc lists
    if not isinstance(origin := get_origin(typed_dict) or typed_dict, type) or not isinstance(
        optional_keys := getattr(origin, "__optional_keys__", None), frozenset
    ):
        return {}
    try:
        hints = _Hierarchy(localns).bound_hints(typed_dict, origin)
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return {}
    items: dict[str, Annotation] = {}
    for name, hint in hints.items():
        optional = name in optional_keys
        annotation = hint
        metadata: list[object] = []
        read_only = None
        while True:
            item_origin = get_origin(annotation)
            qualifier = getattr(item_origin, "_name", None)
            if item_origin is not Annotated and qualifier not in {"Required", "NotRequired", "ReadOnly"}:
                break
            if qualifier in {"Required", "NotRequired"}:
                optional = qualifier == "NotRequired"
            elif qualifier == "ReadOnly":
                # the one written, as typing has none before Python 3.13
                read_only = item_origin
            annotation, *more = get_args(annotation)
            metadata.extend(more)
        if read_only is not None:
            annotation = read_only[annotation]
        if optional:
            annotation = NotRequired[annotation]
        # an Annotated outermost keeps its Doc() a description
        items[name] = (
            Annotated[
                annotation,  # ty: ignore[invalid-type-form]  # https://github.com/astral-sh/ty/issues/727
                *metadata,
            ]
            if metadata
            else annotation
        )
    return items


# visiting each class, and each base a class statement names, once, as a diamond reaches a base along several paths, and
# walking every path is exponential in the depth of the hierarchy
class _Hierarchy:
    def __init__(self, localns: Mapping[str, Documented]) -> None:
        self._localns = localns
        # by identity, as a subscripted base hashes its arguments, which Annotated metadata may not support
        self._bound: dict[int, dict[str, Annotation]] = {}
        self._items: dict[type, tuple[dict[str, Annotation], dict[str, Annotation]]] = {}
        self._scopes: dict[type, dict[str, TypeParam]] = {}

    # a TypedDict lists the items of its bases as its own, with their type parameters unbound, and keeps no base in its
    # MRO, so each base the class statement names supplies its items, bound by the arguments the statement gives it
    def bound_hints(self, typed_dict: Documented, origin: type) -> dict[str, Annotation]:
        if (found := self._bound.get(id(typed_dict))) is not None:
            return found
        hints: dict[str, Annotation] = {}
        # the first base in the MRO decides an item two bases declare, so later bases merge in first
        for base, base_origin in reversed(_typed_dict_bases(origin)):
            hints |= self.bound_hints(base, base_origin)
        # an item the class redeclares, as one narrowing the type of a `ReadOnly` item does (PEP 705), reads as the
        # class declares it
        hints |= self._split(origin)[1]
        arguments = type_arguments(origin, typed_dict)
        found = self._bound[id(typed_dict)] = {name: specialize(hint, arguments) for name, hint in hints.items()}
        return found

    # all items and those the class declares itself, unbound; the items of a base come from that base's own
    # declarations, as autodoc reassigning a base's annotations on Python 3.14 leaves a subclass reading none from it
    def _split(self, typed_dict: type) -> tuple[dict[str, Annotation], dict[str, Annotation]]:
        if (found := self._items.get(typed_dict)) is not None:
            return found
        inherited: dict[str, Annotation] = {}
        bases = [origin for _, origin in _typed_dict_bases(typed_dict)]
        for base in bases:
            inherited |= self._split(base)[0]
        # an item written as a string names the type parameters of the class declaring it, which may be a base
        localns = {**guarded_names(typed_dict), **self._localns, **self._scope(typed_dict)}
        hints = type_hints(typed_dict, None, localns)
        # an item holding what a base holds belongs to that base, read in the module and guard of the base, not of
        # this class
        written = _written(typed_dict)
        declared_by_base = [_written(base) for base in bases]
        own = {
            name: hint
            for name, hint in hints.items()
            if name not in inherited
            or not (
                _same(inherited[name], hint)
                or any(
                    name in base_written and _same(base_written[name], written[name])
                    for base_written in declared_by_base
                )
            )
        }
        found = self._items[typed_dict] = inherited | own, own
        return found

    def _scope(self, typed_dict: type) -> dict[str, TypeParam]:
        if (found := self._scopes.get(typed_dict)) is not None:
            return found
        scope: dict[str, TypeParam] = {}
        for _, origin in _typed_dict_bases(typed_dict):
            scope |= self._scope(origin)
        params = {param.__name__: param for param in getattr(typed_dict, "__parameters__", ())}
        found = self._scopes[typed_dict] = scope | params
        return found


def _typed_dict_bases(typed_dict: type) -> list[tuple[Annotation, type]]:
    return [
        (base, origin)
        for base in get_original_bases(typed_dict)
        if isinstance(origin := get_origin(base) or base, type) and hasattr(origin, "__optional_keys__")
    ]


# without reading a guard, so an inherited item holds what its base holds
def _written(typed_dict: type) -> dict[str, Annotation | ForwardRef]:
    if version_info >= (3, 14):  # pragma: >=3.14 cover
        return get_annotations(typed_dict, format=Format.FORWARDREF)
    return dict(typed_dict.__annotations__)  # pragma: <3.14 cover


# part by part, as a string annotation evaluates anew for each class holding it, so the parts may be equal objects
# rather than one, and comparing a whole `Annotated` asks its metadata, such as an array, for a truth value it may not
# have
def _same(left: object, right: object) -> bool:
    if left is right:
        return True
    if (origin := get_origin(left)) is not None:
        args, other = get_args(left), get_args(right)
        return origin is get_origin(right) and len(args) == len(other) and all(map(_same, args, other))
    try:
        return type(left) is type(right) and (left == right) is True
    except Exception:  # ruff:ignore[blind-except]  # metadata compares through user code, which may raise anything
        return False


def extra_items_type(typed_dict: Documented, seen: set[int]) -> Annotation | OPEN:
    """
    Return the type of the extra items a TypedDict accepts beyond those it declares, which a subclass inherits.

    The result is `Never` for a closed TypedDict, and `OPEN` when neither it nor a base states one. A diamond
    reaches a base along several paths, and a base already read stated nothing, so this skips it.
    """
    if id(typed_dict) in seen or not hasattr(typed_dict, "__optional_keys__"):
        return OPEN
    seen.add(id(typed_dict))
    if closed := getattr(typed_dict, "__closed__", None):
        return Never
    # the sentinel a TypedDict without extra_items holds, typing's from 3.15 or the backport's
    unset = (
        getattr(typing, "NoExtraItems", OPEN),
        getattr(modules.get("typing_extensions"), "NoExtraItems", OPEN),
    )
    extra = getattr(typed_dict, "__extra_items__", OPEN)
    if all(extra is not marker for marker in (OPEN, *unset)):
        return extra
    if closed is False:
        return OPEN
    for base in getattr(typed_dict, "__orig_bases__", ()):
        if (found := extra_items_type(base, seen)) is not OPEN:
            return found
    return OPEN


__all__ = [
    "OPEN",
    "extra_items_type",
    "typed_dict_keys",
]
