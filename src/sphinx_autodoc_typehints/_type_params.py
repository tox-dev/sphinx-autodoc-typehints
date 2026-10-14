"""Showing the type parameters of generic classes, functions and type aliases in their signatures."""

from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING, Any, Final, Literal, cast, get_args, get_origin

from sphinx import addnodes
from sphinx.domains.python._annotations import _parse_type_list  # ruff:ignore[import-private-name]  # no public parser
from sphinx.util.typing import stringify_annotation

if sys.version_info >= (3, 14):  # pragma: >=3.14 cover
    from annotationlib import Format, call_evaluate_function

if TYPE_CHECKING:
    from sphinx.application import Sphinx

type _Mode = Literal["fully-qualified-except-typing", "smart"]

_KINDS: Final = {"TypeVar": "", "TypeVarTuple": "*", "ParamSpec": "**"}
_UNKNOWN: Final = object()


def add_type_params(app: Sphinx, domain: str, _objtype: str, contentnode: addnodes.desc_content) -> None:
    """
    Show the type parameters of a generic object after its name, as in ``class Stack[T: int]``.

    autodoc writes no type parameters into the directive it generates, and it leaves no hook to add them for a type
    alias, so they go into the signature the Python domain built from that directive.
    """
    if domain != "py":
        return
    mode: _Mode = "fully-qualified-except-typing" if app.config.typehints_fully_qualified else "smart"
    # the signatures are the siblings of the content, which may nest the signatures of members
    for signode in cast("addnodes.desc", contentnode.parent).children:
        if (
            isinstance(signode, addnodes.desc_signature)
            and not any(isinstance(node, addnodes.desc_type_parameter_list) for node in signode)
            and (name := next((node for node in signode if isinstance(node, addnodes.desc_name)), None)) is not None
            and (params := _type_params(_documented_object(signode)))
        ):
            text = ", ".join(_type_param(param, mode) for param in params)
            signode.insert(signode.index(name) + 1, _parse_type_list(text, app.env))


def declared_type_params(documented: Any, function: Any, documenting: Any) -> frozenset[Any]:
    """
    Return the type parameters the signatures of ``documented`` declare.

    That is its own, those of ``function`` documenting it, those of the class defining ``function``, which a method
    uses from the header of its class, and those of the class ``documenting`` it, whose own replace inherited ones.
    """
    owner: Any = sys.modules.get(getattr(function, "__module__", None) or "")
    for part in getattr(function, "__qualname__", "").split(".")[:-1]:
        owner = getattr(owner, part, None)
    return frozenset((
        *_type_params(documented),
        *_type_params(function),
        *_type_params(owner),
        *_type_params(documenting),
    ))


def bound_type_args(documenting: Any, attribute: str) -> dict[Any, Any]:
    """
    Map the type parameters of the class defining ``attribute`` to the arguments ``documenting`` gives them.

    A member inherited from ``class Base[T]`` and documented under ``class Child(Base[int])`` then reads ``int`` for
    ``T``.
    """
    if (
        not isinstance(documenting, type)
        or (definer := next((klass for klass in documenting.__mro__ if attribute in vars(klass)), documenting))
        is documenting
    ):
        return {}
    return _arguments(definer, _parametrized(documenting, definer))


def specialize(annotation: Any, arguments: dict[Any, Any]) -> Any:
    """Replace the type parameters in ``annotation`` that ``arguments`` binds."""
    if type(annotation).__name__ in _KINDS:
        return arguments.get(annotation, annotation)
    # a bare generic class lists its parameters too, yet names the class, not an alias to fill in
    if (
        isinstance(annotation, type)
        or not isinstance(params := getattr(annotation, "__parameters__", None), tuple)
        or not any(param in arguments for param in params)
    ):
        return annotation
    return annotation[tuple(arguments.get(param, param) for param in params)]


def _parametrized(cls: type, target: type) -> Any:
    """Return ``target`` subscripted as ``cls`` subclasses it, through the bases in between."""
    # a base the class statement names may stand in for the class it adds, as TypedDict does for dict, binding nothing
    base = next((base for base in types.get_original_bases(cls) if _derives(base, target)), target)
    if (origin := get_origin(base) or base) is target:
        return base
    return specialize(_parametrized(origin, target), _arguments(origin, base))


def _derives(base: Any, target: type) -> bool:
    return isinstance(origin := get_origin(base) or base, type) and issubclass(origin, target)


def _arguments(cls: type, alias: Any) -> dict[Any, Any]:
    params = getattr(cls, "__parameters__", ())
    # a TypeVarTuple takes any number of arguments, leaving no one-to-one match, and a bare base binds none
    return dict(zip(params, args, strict=True)) if len(params) == len(args := get_args(alias)) else {}


def _documented_object(signode: addnodes.desc_signature) -> Any:
    obj = sys.modules.get(signode.get("module") or "")
    for part in (signode.get("fullname") or "").split("."):
        obj = getattr(obj, part, None)
    return obj


def _type_params(obj: Any) -> tuple[Any, ...]:
    params = getattr(obj, "__type_params__", None)
    if not params and isinstance(obj, type):
        # a class made generic the pre-PEP 695 way, by subclassing Generic[T]
        params = getattr(obj, "__parameters__", None)
    if not isinstance(params, tuple):
        return ()
    return tuple(param for param in params if type(param).__name__ in _KINDS)


def _type_param(param: Any, mode: _Mode) -> str:
    text = f"{_KINDS[type(param).__name__]}{param.__name__}"
    if (constraints := _lazy(param, "constraints")) and constraints is not _UNKNOWN:
        text += f": ({', '.join(_stringify(constraint, mode) for constraint in constraints)})"
    # an unbound ParamSpec reports NoneType as its bound before CPython gh-151955
    elif (bound := _lazy(param, "bound")) is not None and bound is not type(None) and bound is not _UNKNOWN:
        text += f": {_stringify(bound, mode)}"
    # PEP 696 defaults exist on typing from 3.13 and on typing_extensions before that
    if (
        (has_default := getattr(param, "has_default", None))
        and has_default()
        and (default := _lazy(param, "default")) is not _UNKNOWN
    ):
        text += f" = {_stringify(default, mode)}"
    return text


def _lazy(param: Any, kind: str) -> Any:
    """Read a bound, constraints or default, which PEP 695 evaluates only on access, so it may fail."""
    try:
        return getattr(param, f"__{kind}__", None)
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        if sys.version_info >= (3, 14):  # pragma: >=3.14 cover
            return call_evaluate_function(getattr(param, f"evaluate_{kind}"), Format.FORWARDREF)
        return _UNKNOWN  # pragma: <3.14 cover


def _stringify(value: Any, mode: _Mode) -> str:
    if isinstance(value, list):  # the parameter list of a ParamSpec
        return f"[{', '.join(_stringify(item, mode) for item in value)}]"
    if isinstance(value, types.GenericAlias) and value.__unpacked__:
        value = types.GenericAlias(value.__origin__, value.__args__)
        return f"*{stringify_annotation(value, mode)}"
    return stringify_annotation(value, mode)


__all__ = ["add_type_params", "bound_type_args", "declared_type_params", "specialize"]
