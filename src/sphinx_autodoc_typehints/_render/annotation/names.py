"""How a class reference names the module and class it points at, and the arguments it carries."""

from __future__ import annotations

import types  # the whole namespace is scanned for public names
from dataclasses import InitVar
from inspect import isclass
from sys import modules, version_info
from typing import (
    TYPE_CHECKING,
    AnyStr,
    Final,
    NewType,
    ParamSpec,
    ParamSpecArgs,
    ParamSpecKwargs,
    TypeVar,
    TypeVarTuple,
)

from sphinx_autodoc_typehints._types import frozendict

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx.config import Config

    from sphinx_autodoc_typehints._types import Hint, RenderNode

    from ..context import FixupModuleName


PYDATA_ANNOTATIONS: Final[set[tuple[str, str]]] = {
    *(
        ("typing", name)
        for name in (
            *("Annotated", "Any", "AnyStr", "Callable", "ClassVar", "Concatenate", "Final", "Literal"),
            *("LiteralString", "Never", "NoReturn", "NotRequired", "Optional", "ReadOnly", "Required", "Self"),
            *("Tuple", "TypeAlias", "TypeForm", "TypeGuard", "TypeIs", "Unpack"),
            *(("ParamSpecArgs", "ParamSpecKwargs") if version_info < (3, 13) else ()),
            *(("Union",) if version_info < (3, 14) else ()),
        )
    ),
    # the types module documents these as py:data through 3.12 and as py:class from 3.13 on
    *(
        (
            ("types", name)
            for name in (
                *("AsyncGeneratorType", "BuiltinFunctionType", "BuiltinMethodType"),
                *("CellType", "ClassMethodDescriptorType", "CoroutineType"),
                *("EllipsisType", "FrameType", "FunctionType"),
                *("GeneratorType", "GetSetDescriptorType"),
                "LambdaType",
                *("MemberDescriptorType", "MethodDescriptorType", "MethodType", "MethodWrapperType"),
                *("NoneType", "NotImplementedType", "WrapperDescriptorType"),
            )
        )
        if version_info < (3, 13)
        else ()
    ),
}
# built once, as every annotation rendered looks itself up in it
_TYPES_NAMES: Final[Mapping[object, str]] = frozendict(
    {getattr(types, name): name for name in types.__all__} | {types.FunctionType: "FunctionType"}
)


def get_annotation_module(annotation: Hint | NewType | None) -> str:
    """Return the module the reference to `annotation` names, raising `ValueError` when `__module__` is no string."""
    if annotation is None:
        return "builtins"
    if _get_types_type(annotation) is not None:
        return "types"
    if isinstance(annotation, NewType | TypeVar | ParamSpec | ParamSpecArgs | ParamSpecKwargs | TypeVarTuple):
        return "typing"
    # `type()` accepts any `__module__`, such as `None`, and `repr` then shows the class name alone
    if isinstance(module := getattr(annotation, "__module__", None), str):
        return module
    msg = f"Cannot determine the module of {annotation}"
    raise ValueError(msg)


def _get_types_type(obj: Hint | NewType | None) -> str | None:
    try:
        return _TYPES_NAMES.get(obj)
    except Exception:  # ruff:ignore[blind-except]  # hashing an annotation runs user code, which may raise anything
        return None


def get_annotation_class_name(annotation: Hint | NewType | None, module: str) -> str:
    """Return the name the reference to `annotation` gives inside `module`, such as `Optional` or `NewType`."""
    if annotation is None:
        return "None"
    if annotation is AnyStr:
        return "AnyStr"
    if (types_name := _get_types_type(annotation)) is not None:
        return types_name
    if isinstance(annotation, NewType):
        return "NewType"
    if (declared := _declared_name(annotation, module)) is not None:
        return declared
    return (annotation if isclass(annotation) else type(annotation)).__qualname__.lstrip("_")


def _declared_name(annotation: Hint | NewType | None, module: str) -> str | None:
    if qualname := getattr(annotation, "__qualname__", None):
        return qualname
    # typing keeps the name of an alias in _name alone
    if name := getattr(annotation, "_name", None):
        return name
    if module in {"typing", "typing_extensions"} and isinstance(name := getattr(annotation, "name", None), str):
        return name
    if (origin := getattr(annotation, "__origin__", None)) and (
        name := getattr(origin, "__qualname__", None) or getattr(origin, "_name", None)
    ):
        return name
    return None


def get_annotation_args(annotation: Hint | NewType | None, module: str, class_name: str) -> tuple[RenderNode, ...]:
    """Return the arguments the reference to `annotation` shows, none for the bare class `module` exports."""
    try:
        original = getattr(modules[module], class_name)
    except (KeyError, AttributeError):
        pass
    else:
        if annotation is original:
            return ()

    if isinstance(annotation, TypeVar):
        return annotation.__constraints__
    if isinstance(annotation, NewType):
        return (annotation.__supertype__,)
    if class_name == "Generic":
        return getattr(annotation, "__parameters__", ())
    if isinstance(annotation, InitVar):
        return (annotation.type,)
    return () if len(args := getattr(annotation, "__args__", ())) == 1 and args[0] == () else args


def fixup_module_name(config: Config, module: str) -> str:
    """Return `module` as the docs name it, after `typehints_fixup_module_name` and with `_io` as `io`."""
    fixup: FixupModuleName | None = config.typehints_fixup_module_name
    if fixup:
        module = fixup(module)
    if module == "_io":
        module = "io"
    return module


def name_prefix(config: Config) -> str:
    return "" if config.typehints_fully_qualified else "~"


__all__ = [
    "PYDATA_ANNOTATIONS",
    "fixup_module_name",
    "get_annotation_args",
    "get_annotation_class_name",
    "get_annotation_module",
    "name_prefix",
]
