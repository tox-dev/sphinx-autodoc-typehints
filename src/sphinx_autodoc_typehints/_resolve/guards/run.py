"""
Runs the `TYPE_CHECKING` guard of a module one statement at a time into a scratch namespace.

It mocks a dependency the docs environment lacks and records the names the guard shadows.
"""

from __future__ import annotations

from ast import AsyncFunctionDef, FunctionDef, Import, ImportFrom, stmt, unparse, walk
from collections import ChainMap
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from importlib import import_module
from importlib.util import resolve_name
from inspect import getmodule, isclass
from sys import builtin_module_names, modules
from types import ModuleType
from typing import TYPE_CHECKING, Final

from sphinx.ext.autodoc.mock import mock
from sphinx.util import logging

from sphinx_autodoc_typehints._objects import defining_module
from sphinx_autodoc_typehints._refs import MyTypeAliasForwardRef
from sphinx_autodoc_typehints._warnings import warn

from .overlay import SHADOWED_BY_GUARD, guarded_names_bound
from .parse import defined_names, guard_binds, guarded_statements, module_source

if TYPE_CHECKING:
    from collections.abc import Generator

    from sphinx_autodoc_typehints._types import Documented


_LOGGER: Final[logging.SphinxLoggerAdapter] = logging.getLogger(__name__)

_RUNNING_GUARDS: Final[list[str]] = []

_IMPORTS_FROM_RUNNING_GUARDS: Final[list[_PendingImport]] = []


@contextmanager
def guard_bound(autodoc_mock_imports: list[str], obj: Documented) -> Generator[None]:
    """Run the `if TYPE_CHECKING` block of the module of `obj`, binding the names it adds while the block runs."""
    resolve_type_guarded_imports(autodoc_mock_imports, obj)
    with guarded_names_bound(obj):
        yield


def resolve_type_guarded_imports(autodoc_mock_imports: list[str], obj: Documented) -> None:
    """
    Execute the `if TYPE_CHECKING` block of the module of `obj`, recording the names it binds for `guarded_names`.

    The module itself stays unchanged, since autodoc would list a name it gained as a member, and its own code would
    read the guarded binding in place of the runtime one.
    """
    if isclass(obj) and (module := getmodule(obj)) is not None:
        obj = module
    if isinstance(obj, ModuleType):
        if obj.__name__ in SHADOWED_BY_GUARD:
            return
    elif (obj_globals := getattr(obj, "__globals__", None)) is None or (
        (module_name := obj_globals.get("__name__", obj.__module__)) in SHADOWED_BY_GUARD
        or module_name in builtin_module_names
    ):
        return
    if (module := defining_module(obj)) and (module_code := module_source(module)):
        shadowed = SHADOWED_BY_GUARD[module.__name__] = {}
        _RUNNING_GUARDS.append(module.__name__)
        try:
            _execute_guarded_code(autodoc_mock_imports, obj, module_code, shadowed)
        finally:
            _RUNNING_GUARDS.pop()
            # what a guard imported from a guard still running binds once every guard it waited on finished
            if not _RUNNING_GUARDS:
                while _IMPORTS_FROM_RUNNING_GUARDS:
                    pending = _IMPORTS_FROM_RUNNING_GUARDS.pop()
                    # a guard may have taken the module out of sys.modules since, leaving only what its own guard bound
                    module_globals = vars(source_module) if (source_module := modules.get(pending.source)) else {}
                    if pending.name in (names := ChainMap(SHADOWED_BY_GUARD[pending.source], module_globals)):
                        pending.importer[pending.bound] = names[pending.name]


def _execute_guarded_code(
    autodoc_mock_imports: list[str], obj: Documented, module_code: str, shadowed: dict[str, Documented]
) -> None:
    namespace = getattr(obj, "__globals__", obj.__dict__)
    # what a type checker sees, which the functions the block defines take as their globals
    scope = dict(namespace)
    statements, errors = guarded_statements(module_code)
    for exc in errors:
        _warn_guarded_import(obj, exc)
    deferred: list[tuple[str, str, str]] = []
    # one statement at a time, so an unimportable optional dependency cannot strand the names after it (#741)
    for statement in statements:
        # a stub of a function the module defines, such as an @overload, is no type an annotation names, and its
        # decorator would register it against the function
        if isinstance(statement, FunctionDef | AsyncFunctionDef) and statement.name in namespace:
            continue
        try:
            _run_guarded_import(autodoc_mock_imports, obj, statement, scope, deferred)
        except Exception as exc:  # ruff:ignore[blind-except]  # a guarded statement may raise anything
            if any(isinstance(node, Import | ImportFrom) for node in walk(statement)):
                _warn_guarded_import(obj, exc)
            else:
                _LOGGER.debug("Skipped guarded statement the interpreter rejects: %r", exc)
                # type checkers accept constructs the interpreter rejects, such as `TypeVar("T", bound="A" | B)`
                # (#751), so the names the statement would have defined stay usable in annotations
                for name in defined_names(statement):
                    scope.setdefault(name, MyTypeAliasForwardRef(name))
    _IMPORTS_FROM_RUNNING_GUARDS.extend(
        _PendingImport(importer=shadowed, bound=bound, source=source, name=name) for bound, source, name in deferred
    )
    shadowed.update({
        name: value for name, value in scope.items() if name not in namespace or namespace[name] is not value
    })


@dataclass(frozen=True, slots=True, kw_only=True)
class _PendingImport:
    importer: dict[str, Documented]
    bound: str
    source: str
    name: str


def _warn_guarded_import(obj: Documented, exc: Exception) -> None:
    warn(
        "guarded_import",
        "Failed guarded type import in %r: %r",
        getattr(obj, "__module__", None) or getattr(obj, "__name__", "?"),
        exc,
        at=obj,
    )


def _run_guarded_import(
    autodoc_mock_imports: list[str],
    obj: Documented,
    statement: stmt,
    namespace: dict[str, Documented],
    deferred: list[tuple[str, str, str]],
) -> None:
    guarded_code = unparse(statement)
    mocked = list(autodoc_mock_imports)
    while True:
        try:
            with mock(mocked):
                exec(guarded_code, namespace)  # ruff:ignore[exec-builtin]  # runs the guard's statement
        except ImportError as exc:
            if not exc.name:
                return
            if (
                isinstance(exc, ModuleNotFoundError)
                and exc.name not in mocked
                and any(
                    module == exc.name or module.startswith(f"{exc.name}.")
                    for node in walk(statement)
                    for module in (
                        [alias.name for alias in node.names]
                        if isinstance(node, Import)
                        else [_source_module(node, namespace)]
                        if isinstance(node, ImportFrom)
                        else []
                    )
                )
            ):
                # the guard lets the code run without the dependency, so mock it as autodoc_mock_imports would (#768)
                _LOGGER.debug("Mocked absent guarded dependency %r for %r", exc.name, getattr(obj, "__module__", "?"))
                mocked.append(exc.name)
                continue
            resolve_type_guarded_imports(autodoc_mock_imports, import_module(exc.name))
            with mock(mocked), suppress(ImportError):
                exec(guarded_code, namespace)  # ruff:ignore[exec-builtin]  # runs the guard's statement
        if (
            not isinstance(statement, ImportFrom)
            or (module := modules.get(source := _source_module(statement, namespace))) is None
        ):
            return
        # when the guards of two modules import from each other, the one still running is half-built, so read it once it
        # finishes
        if source in _RUNNING_GUARDS:
            deferred.extend((alias.asname or alias.name, source, alias.name) for alias in statement.names)
            return
        # running the guard of every module a guard imports from would warn about what nothing here reads
        if source not in SHADOWED_BY_GUARD and guard_binds(module, {alias.name for alias in statement.names}):
            resolve_type_guarded_imports(autodoc_mock_imports, module)
        shadowed = SHADOWED_BY_GUARD.get(source, {})
        namespace.update({
            alias.asname or alias.name: shadowed[alias.name] for alias in statement.names if alias.name in shadowed
        })
        return


def _source_module(statement: ImportFrom, namespace: dict[str, Documented]) -> str:
    return resolve_name(
        "." * statement.level + (statement.module or ""),
        package if isinstance(package := namespace.get("__package__"), str) else None,
    )


__all__ = [
    "guard_bound",
    "resolve_type_guarded_imports",
]
