"""
Foundation helpers that inspect the objects autodoc documents.

They unwrap callables, pick the constructor a signature comes from, and find what defines or owns an object.
"""

from __future__ import annotations

from functools import cached_property, partial, partialmethod
from inspect import Signature, getfile, getmodule, getsourcefile, getsourcelines, isclass, isroutine, unwrap
from sys import modules
from types import CodeType, FrameType, FunctionType, MethodType, ModuleType, TracebackType
from typing import TYPE_CHECKING, Literal, Protocol

from sphinx.ext.autodoc.mock import ismock
from sphinx.util.inspect import safe_getattr

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import TypeIs

    from attrs import AttrsInstance

    from ._types import Documented


class QualifiedCallable(Protocol):
    __qualname__: str
    __module__: str
    __annotations__: dict[str, object]

    def __call__(self, *args: object, **kwargs: object) -> object: ...


def callable_target(obj: Callable[..., object]) -> tuple[QualifiedCallable, QualifiedCallable] | None:
    """
    Return the function callers call through `obj` and the function holding its annotations.

    Unwrapping stops at a wrapper stating `__signature__`, as autodoc does. `None` means `obj` unwraps to a mock,
    which holds no types.
    """
    if (callee := unwrapped(obj, stop=lambda func: declared_signature(func) is not None)) is None:
        return None
    annotated: Callable[..., object] = callee
    # a partial or a partialmethod holds its annotations on the function it calls, and the method a partialmethod
    # builds keeps it under a private name before Python 3.13
    while True:
        if isinstance(annotated, partial):
            annotated = annotated.func
        elif isinstance(
            method := getattr(annotated, "__partialmethod__", getattr(annotated, "_partialmethod", None)),
            partialmethod,
        ):
            annotated = method.func
        else:
            break
    # a callable instance holds them on its __call__, and a wrapper may carry none of its own, like the 3.14 lru_cache
    # one that only copies __annotate__
    found = unwrapped(annotated if isroutine(annotated) or isclass(annotated) else type(annotated).__call__)
    return None if found is None else (callee, found)


def unwrapped(
    obj: Callable[..., object], stop: Callable[[Callable[..., object]], bool] = lambda _: False
) -> QualifiedCallable | None:
    """Return the callable `obj` wraps, `None` when that is a mock or the `__wrapped__` chain loops."""
    # a mock answers __wrapped__ with a new mock, so inspect.unwrap would build mocks up to the recursion limit
    try:
        inner = unwrap(obj, stop=lambda func: ismock(func) or stop(func))
    except ValueError:
        return None
    return None if ismock(inner) else inner


def declared_signature(obj: Documented) -> Signature | None:
    """Return the signature an object states in `__signature__`, as a pydantic model does, which callers go by."""
    # a property computing it may raise anything, as a metaclass's does for a class it cannot describe yet
    return signature if isinstance(signature := safe_getattr(obj, "__signature__", None), Signature) else None


def property_getter(member: Documented) -> Callable[..., object] | None:
    """Return the getter of a `property` or a `functools.cached_property`, `None` for any other member."""
    if isinstance(member, cached_property):
        return member.func
    return member.fget if isinstance(member, property) else None


def constructor_name(cls: type) -> Literal["__new__", "__init__"]:
    """Choose the constructor as `inspect.signature` does: the one defined lowest in the MRO, `__new__` on a tie."""
    depth = {
        name: next(at for at, klass in enumerate(cls.__mro__) if name in vars(klass))
        for name in ("__new__", "__init__")
    }
    # a __new__ that only wraps object's, as @warnings.deprecated adds, is no constructor of its own to inspect
    own_new = unwrapped(cls.__new__) is not object.__new__
    return "__new__" if own_new and depth["__new__"] <= depth["__init__"] else "__init__"


def is_attrs_class(obj: Documented) -> TypeIs[type[AttrsInstance]]:
    """Return whether attrs made `obj`, without importing attrs, an optional dependency."""
    return hasattr(obj, "__attrs_attrs__")


def stored_name(owner: Documented, attribute: str) -> str:
    """Return the name the body of `owner` stores `attribute` under, mangled for a private name."""
    if (
        attribute.startswith("__")
        and not attribute.endswith("__")
        and isinstance(owner_name := getattr(owner, "__name__", None), str)
    ):
        return f"_{owner_name.lstrip('_')}{attribute}"
    return attribute


def documented_owner(name: str) -> tuple[Documented, str]:
    """Return the object holding the documented member `name`, found through its imported module, and the member."""
    *path, attribute = name.split(".")
    return (None if (found := imported_prefix(path)) is None else object_at(*found)), attribute


def imported_prefix(path: list[str]) -> tuple[str, list[str]] | None:
    """Return the longest imported module `path` starts with, and the parts of `path` naming an object in it."""
    return next(
        ((module, path[depth:]) for depth in range(len(path), 0, -1) if modules.get(module := ".".join(path[:depth]))),
        None,
    )


def object_at(module: str | None, path: Iterable[str]) -> Documented:
    """Return the object `path` names in the imported `module`, `None` where a part of it is missing."""
    found: Documented = modules.get(module or "")
    for part in path:
        if found is None:
            return None
        found = getattr(found, part, None)
    return found


def prefix_of(name: str) -> str:
    return name.rpartition(".")[0]


def alias_lookup_names(module_prefix: str, name: str) -> list[str]:
    """Return the names a `py:type` documenting an alias used under `module_prefix` may have, innermost first."""
    scopes = enclosing_scopes(module_prefix)
    missing = object()

    def binding(scope: str) -> object:
        if (prefix := imported_prefix(scope.split("."))) is None:
            return missing
        owner = object_at(*prefix)
        return vars(owner).get(name, missing) if hasattr(owner, "__dict__") else missing

    visible = next((value for scope in scopes if (value := binding(scope)) is not missing), missing)
    return [*(f"{scope}.{name}" for scope in scopes if visible is missing or binding(scope) is visible), name]


def enclosing_scopes(module_prefix: str) -> list[str]:
    """Annotations see the names of the module and the class bodies around them, not those of other modules."""
    parts = module_prefix.split(".")
    return [".".join(parts[:end]) for end in range(len(parts), 0, -1)]


def get_obj_location(obj: Documented) -> str | None:
    """Return where the source of `obj` sits, as `path:line` or the path alone, for a warning to point at."""
    if not isinstance(
        obj,
        ModuleType | type | MethodType | FunctionType | TracebackType | FrameType | CodeType,
    ):
        return None
    try:
        filepath = getsourcefile(obj) or getfile(obj)
    except TypeError:
        return None
    # code compiled from no file, such as the __init__ a dataclass generates, has a name like <string>
    if filepath.startswith("<"):
        return None
    try:
        lineno = getsourcelines(obj)[1]
    except (OSError, TypeError):
        return filepath
    return f"{filepath}:{lineno}"


def defining_module(obj: Documented) -> ModuleType | None:
    # re-exporting reassigns `__module__`, while the globals stay those of the module defining the object
    return modules.get(getattr(obj, "__globals__", {}).get("__name__", "")) or getmodule(obj)


__all__ = [
    "QualifiedCallable",
    "alias_lookup_names",
    "callable_target",
    "constructor_name",
    "declared_signature",
    "defining_module",
    "documented_owner",
    "enclosing_scopes",
    "get_obj_location",
    "imported_prefix",
    "is_attrs_class",
    "object_at",
    "prefix_of",
    "property_getter",
    "stored_name",
    "unwrapped",
]
