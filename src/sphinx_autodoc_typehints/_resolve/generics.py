"""
Type parameters and the arguments that bind them.

It finds those an object declares, those a subclass binds, and substitutes the arguments into a hint.
"""

from __future__ import annotations

from sys import version_info
from types import get_original_bases
from typing import TYPE_CHECKING, Final, Protocol, TypeGuard, get_args, get_origin

from .._objects import object_at
from .._types import frozendict

if version_info >= (3, 14):  # pragma: >=3.14 cover
    from annotationlib import Format, get_annotations

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import TypeIs

    from .._types import Annotation, Documented, TypeParam


TYPE_PARAM_KINDS: Final[Mapping[str, str]] = frozendict({"TypeVar": "", "TypeVarTuple": "*", "ParamSpec": "**"})


class Subscriptable(Protocol):
    def __getitem__(self, item: object, /) -> Annotation: ...


def declared_type_params(
    documented: Documented, function: Callable[..., object] | None, documenting: Documented
) -> frozenset[TypeParam]:
    """
    Return the type parameters the signatures of `documented` declare.

    That is its own, those of `function` documenting it, those of the class defining `function`, which a method
    uses from the header of its class, and those of the class `documenting` it, whose own replace inherited ones.
    """
    owner = object_at(getattr(function, "__module__", None), getattr(function, "__qualname__", "").split(".")[:-1])
    return frozenset((
        *type_params_of(documented, legacy=True),
        *type_params_of(function, legacy=True),
        *type_params_of(owner, legacy=True),
        *type_params_of(documenting, legacy=True),
    ))


def type_params_of(obj: Documented, *, legacy: bool) -> tuple[TypeParam, ...]:
    """
    Return the PEP 695 type parameters of `obj`, with `legacy` those a class takes from `Generic[T]` too.

    A class owning the `__type_params__` slot itself, as `typing.TypeAliasType` does, hands back the descriptor.
    """
    params = getattr(obj, "__type_params__", None)
    if not legacy:
        return params if isinstance(params, tuple) else ()
    if not params and isinstance(obj, type):
        # a class made generic the pre-PEP 695 way, by subclassing Generic[T]
        params = getattr(obj, "__parameters__", None)
    if not isinstance(params, tuple):
        return ()
    return tuple(param for param in params if _is_type_param(param))


def _is_type_param(value: object) -> TypeIs[TypeParam]:
    return type(value).__name__ in TYPE_PARAM_KINDS


def bound_type_args(documenting: Documented, attribute: str) -> dict[TypeParam, Annotation]:
    """
    Map the type parameters of the class defining `attribute` to the arguments `documenting` gives them.

    A member inherited from `class Base[T]` and documented under `class Child(Base[int])` then reads `int` for
    `T`. The map is empty when `documenting` is no class or defines `attribute` itself.
    """
    if not isinstance(documenting, type):
        return {}
    for definer in documenting.__mro__:
        if attribute in vars(definer):
            break
        # an attribute only annotated in the class body, as `value: T` is, counts too; the annotation may name what
        # only a type checker imports, so read it without evaluating, and a class may define __annotations__ as
        # anything, such as a property forwarding those of the object it wraps
        if version_info >= (3, 14):  # pragma: >=3.14 cover
            try:
                declared = get_annotations(definer, format=Format.FORWARDREF)
            except ValueError:
                declared = {}
        else:  # pragma: <3.14 cover
            declared = vars(definer).get("__annotations__")
        if isinstance(declared, dict) and attribute in declared:
            break
    else:
        return {}
    if definer is documenting or not getattr(definer, "__parameters__", ()):
        return {}
    return type_arguments(definer, _parametrized(documenting, definer))


def _parametrized(cls: type, target: type) -> Annotation:
    # a base the class statement names may stand in for the class it adds, as TypedDict does for dict, binding nothing;
    # issubclass would raise for a Protocol that is not runtime checkable and count a class registered with an ABC
    base = next(
        (
            base
            for base in get_original_bases(cls)
            if isinstance(origin := get_origin(base) or base, type) and target in origin.__mro__
        ),
        target,
    )
    if (origin := get_origin(base) or base) is target:
        return base
    return specialize(_parametrized(origin, target), type_arguments(origin, base))


def type_arguments(cls: type, alias: Documented) -> dict[TypeParam, Annotation]:
    """Map the type parameters of `cls` to the arguments `alias` subscripting it gives them, none for `cls`."""
    params = getattr(cls, "__parameters__", ())
    # a TypeVarTuple takes any number of arguments, leaving no one-to-one match, and a bare base binds none
    return dict(zip(params, args, strict=True)) if len(params) == len(args := get_args(alias)) else {}


def specialize[Value](annotation: Value, arguments: Mapping[TypeParam, Annotation]) -> Value | Annotation:
    if _is_type_param(annotation):
        return arguments.get(annotation, annotation)
    # a bare generic class lists its parameters too, yet names the class, not an alias to fill in
    if (
        isinstance(annotation, type)
        or not isinstance(params := getattr(annotation, "__parameters__", None), tuple)
        or not any(param in arguments for param in params)
        or not _subscriptable(annotation)
    ):
        return annotation
    return annotation[tuple(arguments.get(param, param) for param in params)]


# reads the class as the subscript operator does; a runtime-checkable Protocol check would, below Python 3.14, read the
# __annotations__ of every class in the checked type's MRO and so create one on each that has none
def _subscriptable(value: object) -> TypeGuard[Subscriptable]:
    return callable(getattr(type(value), "__getitem__", None))


__all__ = [
    "TYPE_PARAM_KINDS",
    "Subscriptable",
    "bound_type_args",
    "declared_type_params",
    "specialize",
    "type_arguments",
    "type_params_of",
]
