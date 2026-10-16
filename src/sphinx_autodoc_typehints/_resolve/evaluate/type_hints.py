"""
`typing.get_type_hints` that reads a guarded name as the guard binds it.

It evaluates the source again where a `__class_getitem__` dropped the arguments an annotation gives.
"""

from __future__ import annotations

__lazy_modules__ = [
    "annotationlib",
    "dataclasses",
    "functools",
    "inspect",
    "sphinx_autodoc_typehints._objects",
    "sphinx_autodoc_typehints._resolve.evaluate.bases",
    "sphinx_autodoc_typehints._resolve.evaluate.expression",
    "sphinx_autodoc_typehints._resolve.guards",
    "sphinx_autodoc_typehints._resolve.source",
    "types",
]

from dataclasses import is_dataclass
from functools import partial
from inspect import getattr_static, isfunction, isroutine
from sys import version_info
from types import GenericAlias, ModuleType
from typing import TYPE_CHECKING, get_args, get_origin, get_type_hints

from sphinx_autodoc_typehints._objects import defining_module, is_attrs_class, object_at
from sphinx_autodoc_typehints._resolve.evaluate.bases import base_scopes, declared_hints, hints_of_bases
from sphinx_autodoc_typehints._resolve.evaluate.expression import evaluate_annotation
from sphinx_autodoc_typehints._resolve.guards import annotation_globals, guarded_names
from sphinx_autodoc_typehints._resolve.source import (
    annotations_as_written,
    holds_values,
    names_read,
    source_annotations,
    written_annotations,
)

if version_info >= (3, 14):  # pragma: >=3.14 cover
    from typing import evaluate_forward_ref

    from annotationlib import ForwardRef

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from typing import TypeAliasType

    from sphinx_autodoc_typehints._types import Annotation, Documented


def type_hints(
    obj: Documented, globalns: dict[str, Documented] | None, localns: Mapping[str, Documented] | None
) -> dict[str, Annotation]:
    """
    Return `typing.get_type_hints` with the extras, reading a name a guard shadows as the guard binds it.

    A class whose `__class_getitem__` hands back the class itself, as SQLAlchemy's `TypeEngine` does, evaluates
    `TypeEngine[Any]` to a bare `TypeEngine`, so this evaluates the source of an annotation left holding one again.
    """
    # PEP 649 evaluates an annotation in the globals of the code defining it, which hold the runtime binding of a name
    # the TYPE_CHECKING block of its module shadows, so such an annotation evaluates from its source in the guarded
    # globals, as get_type_hints would
    if version_info >= (3, 14) and any(  # pragma: >=3.14 cover
        (getattr(owner, "__annotate__", None) is not None or holds_values(owner))
        and (shadowed := guarded_names(owner))
        and any(
            name in shadowed
            for source in annotations_as_written(owner).values()
            if isinstance(source, str)
            for name in names_read(source)
        )
        for owner in (obj.__mro__ if isinstance(obj, type) else (obj,))
    ):
        if isinstance(obj, type):
            hints = hints_of_bases(obj, globalns, localns, partial(_evaluate_written, is_argument=False))
        else:
            hints = _evaluate_written(obj, *_scope(obj, globalns, localns), is_argument=not isinstance(obj, ModuleType))
    elif isinstance(obj, type) and any(guarded_names(base) for base in obj.__mro__):
        hints = hints_of_bases(obj, globalns, localns, declared_hints)
    else:
        hints = get_type_hints(obj, globalns, localns, include_extras=True)
    if not (
        dropped := {
            name
            for name, hint in hints.items()
            if any(
                isinstance(part, type) and get_origin(part) is None and _drops_arguments(part) for part in _parts(hint)
            )
        }
    ):
        return hints
    again: dict[str, Annotation] = {}
    for name, source, scope_globals, scope_locals in _written_sources(obj, dropped, globalns, localns):
        try:
            # a quoted annotation evaluates to the string inside it
            if isinstance(value := evaluate_annotation(source, scope_globals, scope_locals), str):
                value = evaluate_annotation(value, scope_globals, scope_locals)
        except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
            value = hints[name]
        # an alias named in the source holds the forward references get_type_hints resolved, so it only wins when it
        # kept the arguments the source gives it; such a class subscripts to itself, so only evaluate_annotation builds
        # a generic alias of it
        again[name] = (
            value
            if any(isinstance(part, GenericAlias) and _drops_arguments(part.__origin__) for part in _parts(value))
            else hints[name]
        )
    return hints | again


def _evaluate_written(  # pragma: >=3.14 cover
    owner: Documented, globalns: dict[str, Documented], localns: Mapping[str, Documented], *, is_argument: bool
) -> dict[str, Annotation]:
    params = getattr(owner, "__type_params__", ())
    hints: dict[str, Annotation] = {}
    for name, source in annotations_as_written(owner).items():
        if isinstance(source, str):
            try:
                value = evaluate_forward_ref(
                    ForwardRef(source, is_argument=is_argument, is_class=isinstance(owner, type)),
                    owner=owner,
                    globals=globalns,
                    locals=localns,
                    type_params=params,  # ty: ignore[invalid-argument-type]  # typeshed declares a fixed 3-tuple
                )
            except Exception:
                # a value printed by its repr, as a lambda is, may not evaluate, so it reads as the runtime evaluated it
                if name not in (runtime := getattr(owner, "__annotations__", None) or {}):
                    raise
                # under `from __future__ import annotations` the runtime value is the source again, which reads
                # `X | Y` of mocked operands as a Union
                if isinstance(value := runtime[name], str):
                    value = evaluate_annotation(value, globalns, localns)
        else:
            value = source
        hints[name] = type(None) if value is None else value
    return hints


def _parts(hint: Annotation) -> Iterator[Annotation]:
    yield hint
    # the parameters of a Callable come as a list
    for argument in hint if isinstance(hint, list) else get_args(hint):
        yield from _parts(argument)


def _drops_arguments(cls: type | TypeAliasType) -> bool:
    # the standard library subscripts its classes in C, only a __class_getitem__ written in Python can drop arguments
    method = getattr_static(cls, "__class_getitem__", None)
    return isfunction(getattr(method, "__func__", method))


# a class yields its bases first, so the class that declares an attribute last comes last, as get_type_hints orders them
def _written_sources(
    obj: Documented, names: set[str], globalns: dict[str, Documented] | None, localns: Mapping[str, Documented] | None
) -> Iterator[tuple[str, str, dict[str, Documented], Mapping[str, Documented]]]:
    if isroutine(obj) or isinstance(obj, ModuleType):
        written = written_annotations(obj) if isroutine(obj) else source_annotations(obj.__name__, "")
        scope_globals, scope_locals = _scope(obj, globalns, localns)
        yield from ((name, written[name], scope_globals, scope_locals) for name in names & written.keys())
        # the __init__ a dataclass or attrs generates, code compiled from no file, takes its annotations from the
        # fields the class body writes
        if (
            (unwritten := names - written.keys())
            and getattr(getattr(obj, "__code__", None), "co_filename", "").startswith("<")
            and getattr(obj, "__name__", None) == "__init__"
            and (
                is_dataclass(
                    owner := object_at(
                        getattr(defining_module(obj), "__name__", None), obj.__qualname__.split(".")[:-1]
                    )
                )
                or is_attrs_class(owner)
            )
        ):
            yield from _written_sources(owner, unwritten, None, localns)
        return
    # an instance takes the annotations of its attributes from its class
    for base, base_globals, base_locals in base_scopes(obj if isinstance(obj, type) else type(obj), globalns, localns):
        # a generic class binds its type parameters in a scope of their own, neither the module nor the class body
        params = {param.__name__: param for param in getattr(base, "__type_params__", ())}
        scope_locals = {**base_locals, **params} if params else base_locals
        written = source_annotations(base.__module__, base.__qualname__)
        yield from ((name, written[name], base_globals, scope_locals) for name in names & written.keys())


# an annotation evaluates in the globals of the code defining it, and in those again unless the caller passes locals
def _scope(
    obj: Documented, globalns: dict[str, Documented] | None, localns: Mapping[str, Documented] | None
) -> tuple[dict[str, Documented], Mapping[str, Documented]]:
    scope_globals = annotation_globals(obj) if globalns is None else globalns
    return scope_globals, scope_globals if localns is None else localns


__all__ = [
    "type_hints",
]
