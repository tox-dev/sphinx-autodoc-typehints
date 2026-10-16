"""
The namespace the annotations of a stub evaluate in, and the names they render as plain cross-references.

It holds the stub's imports, its own definitions and the type parameters around the object.
"""

from __future__ import annotations

__lazy_modules__ = [
    "contextlib",
    "copy",
    "importlib",
    "sphinx",
    "sphinx.ext",
    "sphinx.ext.autodoc",
    "sphinx.ext.autodoc.mock",
    "sphinx_autodoc_typehints._refs",
    "sphinx_autodoc_typehints._resolve.backfill.stubs.extract",
    "sphinx_autodoc_typehints._resolve.backfill.stubs.find",
]

import ast  # its TypeVar, ParamSpec and TypeVarTuple nodes clash with the typing ones
from contextlib import suppress
from copy import copy
from importlib import import_module
from sys import modules
from typing import TYPE_CHECKING, Final, ParamSpec, TypeVar, TypeVarTuple

from sphinx.ext.autodoc.mock import mock

from sphinx_autodoc_typehints._refs import MyTypeAliasForwardRef
from sphinx_autodoc_typehints._resolve.backfill.stubs.extract import find_ast_node
from sphinx_autodoc_typehints._resolve.backfill.stubs.find import (
    find_stub_owner,
    import_module_or_none,
    parse_stub_ast,
    resolve_import_from,
    stub_owner_package,
)
from sphinx_autodoc_typehints._types import frozendict

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from types import GetSetDescriptorType, MemberDescriptorType, ModuleType

    from sphinx_autodoc_typehints._types import Documented

# built once rather than for every stub read
_FACTORIES: Final[Mapping[type[ast.type_param], Callable[[str], TypeVar | ParamSpec | TypeVarTuple]]] = frozendict({
    ast.TypeVar: TypeVar,
    ast.ParamSpec: ParamSpec,
    ast.TypeVarTuple: TypeVarTuple,
})


def stub_context(
    obj: Callable[..., object] | GetSetDescriptorType | MemberDescriptorType, name: str = ""
) -> tuple[dict[str, Documented], dict[str, MyTypeAliasForwardRef], str]:
    """
    Return the namespace the stub of `obj` evaluates in, the names to render as a plain cross-reference, its module.

    All three are empty when no stub that parses describes `obj`. Callers evaluate in the globals of the returned
    module, which differs from the one `obj.__module__` names when a C extension function lives in a child module
    and its stub belongs to the parent package, as `cbor2._cbor2.dumps` and `cbor2/__init__.pyi` do.

    The cross-reference names are the type aliases of the stub and every name it imports that has no runtime
    counterpart, such as numpy's `_SeriesLikeCoef_co`, which only the stub `numpy/polynomial/_polytypes.pyi`
    defines. They cannot evaluate, so they render as a plain cross-reference.
    """
    if (info := find_stub_owner(obj, name)) is None:
        return {}, {}, ""
    path, owner_module = info
    if (tree := parse_stub_ast(path)) is None:
        return {}, {}, ""
    namespace: dict[str, Documented] = dict(vars(owner_module))
    # a class takes its `__module__` from the `__name__` of the globals it runs in, `builtins` when they lack one
    resolved: dict[str, Documented] = {"__name__": owner_module.__name__}
    unresolved: set[str] = set()
    _resolve_stub_imports_from_body(tree.body, stub_owner_package(owner_module, path), resolved, unresolved)
    _resolve_stub_definitions(tree.body, resolved)
    namespace.update(resolved)
    parts = str(getattr(obj, "__qualname__", "")).split(".")
    for depth in range(1, len(parts) + 1):
        if isinstance(
            node := find_ast_node(tree.body, parts[:depth]), ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            # typeshed types the list by the base class, which lacks the name all three subclasses have
            namespace.update({
                param.name: _FACTORIES[type(param)](param.name)
                for param in node.type_params
                if isinstance(param, ast.TypeVar | ast.ParamSpec | ast.TypeVarTuple)
            })
    type_alias_names: set[str] = set()
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.annotation, ast.Name | ast.Attribute)
            and ast.unparse(node.annotation) in {"TypeAlias", "typing.TypeAlias", "typing_extensions.TypeAlias"}
        ):
            type_alias_names.add(node.target.id)
        elif isinstance(node, ast.TypeAlias) and isinstance(node.name, ast.Name):
            type_alias_names.add(node.name.id)
    return (
        namespace,
        {
            crossref_name: MyTypeAliasForwardRef(crossref_name, crossref=True)
            for crossref_name in type_alias_names | (unresolved - namespace.keys())
        },
        owner_module.__name__,
    )


def _resolve_stub_imports_from_body(
    body: list[ast.stmt], owner_package: str, namespace: dict[str, Documented], unresolved: set[str]
) -> None:
    for node in body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if (module := _import_for_stub(alias.name, top=not alias.asname)) is not None:
                    namespace[alias.asname or alias.name.partition(".")[0]] = module
        elif isinstance(node, ast.ImportFrom):
            module_name = resolve_import_from(node, owner_package)
            from_module = import_module_or_none(module_name) if module_name else None
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                if from_module is not None and (
                    (value := getattr(from_module, alias.name, None)) is not None
                    or (value := import_module_or_none(f"{module_name}.{alias.name}")) is not None
                ):
                    namespace[name] = value
                else:
                    unresolved.add(name)
        elif isinstance(node, ast.If):
            _resolve_stub_imports_from_body(node.body, owner_package, namespace, unresolved)
            _resolve_stub_imports_from_body(node.orelse, owner_package, namespace, unresolved)


# a stub may import a module only type checkers need, so this mocks a missing one as `autodoc_mock_imports` would,
# while a module that exists but fails to import binds nothing
def _import_for_stub(name: str, *, top: bool) -> ModuleType | None:
    mocked: list[str] = []
    try:
        import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name is None or (name != exc.name and not name.startswith(f"{exc.name}.")):
            return None
        mocked.append(exc.name)
    except ImportError:
        return None
    with mock(mocked):
        module = import_module(name)
        return modules[name.partition(".")[0]] if top else module


def _resolve_stub_definitions(body: list[ast.stmt], namespace: dict[str, Documented]) -> None:
    for node in body:
        if isinstance(node, ast.Assign | ast.AnnAssign | ast.ClassDef | ast.TypeAlias):
            definition = node
            if isinstance(node, ast.ClassDef) and node.decorator_list:
                definition = copy(node)
                definition.decorator_list = []
            # a stub names what only type checkers know and its class bodies run code, so it may raise anything
            with suppress(Exception):
                code = compile(ast.Module(body=[definition], type_ignores=[]), "<stub>", "exec")
                exec(code, namespace)  # ruff:ignore[exec-builtin]  # defines what the stub defines
        elif isinstance(node, ast.If):
            _resolve_stub_definitions(node.body, namespace)
            _resolve_stub_definitions(node.orelse, namespace)


__all__ = [
    "stub_context",
]
