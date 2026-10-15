"""
The type hints of a documented object, backfilled from a type comment or a stub when it carries none.

It also types a C data descriptor from the stub of its class.
"""

from __future__ import annotations

from ast import AnnAssign, ClassDef, FunctionDef, If, Name, stmt, unparse
from contextlib import suppress
from inspect import get_annotations, getmodule, isclass, isroutine
from types import GetSetDescriptorType, MemberDescriptorType, ModuleType
from typing import TYPE_CHECKING, NewType, ParamSpec, TypeVar, TypeVarTuple, get_origin

from .._refs import is_type_alias
from .._warnings import warn
from .backfill import backfill_type_hints, find_ast_node, parse_stub_ast, stub_annotations, stub_context, stub_path
from .evaluate import resolve_string_annotations, type_hints, unevaluated_annotations
from .generics import type_params_of
from .guards import (
    SHADOWED_BY_GUARD,
    annotation_globals,
    guard_binds,
    guard_bound,
    guarded_names,
    resolve_type_guarded_imports,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from .._types import Documented, Hint


def get_all_type_hints(
    autodoc_mock_imports: list[str], obj: Callable[..., object], name: str, localns: Mapping[str, Documented]
) -> dict[str, Hint]:
    """
    Return the type hints of `obj`, documented as `name`, backfilled from type comments or a stub when it has none.

    The backfilled annotations replace those of `obj` where it accepts the assignment.
    """
    if result := resolve_annotations(autodoc_mock_imports, obj, name, localns):
        return result
    stub_obj = obj
    if isclass(obj):
        if obj.__init__ is not object.__init__:
            stub_obj = obj.__init__
        elif obj.__new__ is not object.__new__:
            stub_obj = obj.__new__
    stub_localns, crossrefs, owner_module = (
        stub_context(stub_obj, name)
        if not (result := backfill_type_hints(stub_obj, name)) and (result := stub_annotations(stub_obj, name))
        else ({}, {}, "")
    )
    combined_localns = {**stub_localns, **localns, **crossrefs}
    try:
        obj.__annotations__ = result
    except (AttributeError, TypeError):
        return resolve_string_annotations(obj, result, combined_localns, owner_module)
    result = resolve_annotations(autodoc_mock_imports, obj, name, combined_localns)
    with suppress(AttributeError, TypeError):
        obj.__annotations__ = result
    return result


def resolve_annotations(
    autodoc_mock_imports: list[str], obj: Documented, name: str, localns: Mapping[str, Documented]
) -> dict[str, Hint]:
    """Resolve the annotations `obj` itself carries, without backfilling it from a stub or type comments."""
    resolve_type_guarded_imports(autodoc_mock_imports, obj)
    # a class reads the guard of the module defining each of its bases in that base's globals, not in shared locals
    scope = {**({} if isclass(obj) else guarded_names(obj)), **_build_localns(obj, localns)}
    try:
        if getattr(obj, "__no_type_check__", False):
            # typing.get_type_hints returns {} for a @typing.no_type_check target, while inspect.get_annotations still
            # reads its annotations for the rendered docs (#680)
            return get_annotations(obj, locals=scope, eval_str=True)
        # copied into a dict that also takes what the fallback leaves unevaluated, as a dict is invariant in its values
        return dict(type_hints(obj, annotation_globals(obj) if hasattr(obj, "__globals__") else None, scope))
    except RecursionError:
        return {}
    except Exception as exc:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        # `_t.Alias` where `_t` is a module whose own guard binds `Alias`, as `from . import _types as _t`
        if (
            isinstance(exc, AttributeError)
            and isinstance(module := exc.obj, ModuleType)
            and exc.name
            and guard_binds(module, {exc.name})
        ):
            if module.__name__ not in SHADOWED_BY_GUARD:
                with guard_bound(autodoc_mock_imports, module):
                    return resolve_annotations(autodoc_mock_imports, obj, name, localns)
        elif isinstance(exc, NameError | AttributeError | SyntaxError):
            warn(
                "forward_reference",
                'Cannot resolve forward reference in type annotations of "%s" (module %s): %s',
                name,
                getattr(obj, "__module__", "?"),
                exc,
                at=obj,
            )
        return resolve_string_annotations(obj, unevaluated_annotations(obj), scope)


def _build_localns(obj: Documented, localns: Mapping[str, Documented]) -> dict[str, Documented]:
    result = dict(localns)
    result.update({param.__name__: param for param in type_params_of(obj, legacy=False)})
    parts = (getattr(obj, "__qualname__", "") or "").split(".")
    if len(parts) <= 1:
        return result
    if namespace := (vars(module) if (module := getmodule(obj)) else getattr(obj, "__globals__", None)):
        current: Documented = None
        for part in parts[:-1]:
            current = (
                (namespace if current is None else vars(current)).get(part)
                if current is None or hasattr(current, "__dict__")
                else None
            )
            if current is None:
                break
            if isclass(current):
                result[part] = current
            result.update({param.__name__: param for param in type_params_of(current, legacy=False)})
        if isroutine(obj) and isclass(current):
            # nested classes, type variables and aliases resolve as they do when annotations evaluate at definition,
            # but other members (a method named list, a field defaulting to None) must not shadow the module globals
            # get_type_hints resolves against
            result = {
                **{
                    key: value
                    for key, value in vars(current).items()
                    if isclass(value)
                    or isinstance(value, TypeVar | ParamSpec | TypeVarTuple | NewType)
                    or get_origin(value) is not None
                    or is_type_alias(value)
                },
                **result,
            }
    return result


def get_descriptor_type_hint(obj: GetSetDescriptorType | MemberDescriptorType) -> Hint | None:
    """
    Return the type the stub of its class gives a C data descriptor, `None` when it gives none.

    Getset and member descriptors carry no annotations at runtime, so only the stub of the owning class types them, by
    the return annotation of a `@property` or by an annotated assignment of the same name in the class body. The
    backfill working from signatures skips these objects, as they are not callable. Evaluating the annotation in the
    namespace of the stub resolves aliases and forward references the way it does for a function signature.
    """
    if (path := stub_path(obj)) is None or (tree := parse_stub_ast(path)) is None:
        return None
    if not isinstance(node := find_ast_node(tree.body, obj.__objclass__.__qualname__.split(".")), ClassDef):
        return None
    members: list[stmt] = list(node.body)
    while members:
        member = members.pop()
        if isinstance(member, If):
            # stubs guard members behind `if sys.version_info >= ...` blocks (numpy's ndarray does)
            members.extend(member.body)
            members.extend(member.orelse)
            continue
        if isinstance(member, AnnAssign) and isinstance(member.target, Name) and member.target.id == obj.__name__:
            annotation = unparse(member.annotation)
            break
        if not isinstance(member, FunctionDef) or member.name != obj.__name__ or member.returns is None:
            continue
        if any(isinstance(decorator, Name) and decorator.id == "property" for decorator in member.decorator_list):
            annotation = unparse(member.returns)
            break
    else:
        return None
    localns, crossrefs, owner_module = stub_context(obj)
    return resolve_string_annotations(obj, {"return": annotation}, localns | crossrefs, owner_module)["return"]


__all__ = [
    "get_all_type_hints",
    "get_descriptor_type_hint",
    "resolve_annotations",
]
