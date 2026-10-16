"""
Locates the stub describing an object and parses it once per modification time.

The stub sits beside the module, in its package, or in a parent package that re-exports the object.
"""

from __future__ import annotations

__lazy_modules__ = ["ast", "importlib", "inspect", "pathlib", "sphinx_autodoc_typehints._objects"]

import sys  # the stub guard is evaluated with the module in scope
from ast import AsyncFunctionDef, ClassDef, Expression, FunctionDef, If, ImportFrom, Module, parse, stmt
from collections.abc import Iterable
from importlib import import_module
from inspect import getattr_static, getmodule, isclass, isdatadescriptor
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Final

from sphinx_autodoc_typehints._objects import imported_prefix

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType

    from sphinx_autodoc_typehints._types import Documented


_STUB_AST_CACHE: Final[dict[tuple[Path, int], Module | None]] = {}


def stub_path(obj: Documented, name: str = "") -> Path | None:
    """Return the stub file describing `obj` documented as `name`, whose edits change what that shows."""
    return info[0] if (info := find_stub_owner(obj, name)) else None


def find_stub_owner(obj: Documented, name: str = "") -> tuple[Path, ModuleType] | None:
    """Return the stub describing `obj`, documented as `name`, and the module it belongs to, if any."""
    module = getmodule(obj)
    # a method descriptor of a C extension type reaches its class through __objclass__
    if module is None and (owner_cls := getattr(obj, "__objclass__", None)):
        module = getmodule(owner_cls)
    # a bound method, such as the __new__ of a C extension class, reaches its class through __self__
    if module is None and isclass(owner_cls := getattr(obj, "__self__", None)):
        module = getmodule(owner_cls)
    if module is None:
        return None
    if result := _find_stub_for_module(module):
        return result, module
    # the PEP 561 stub of a parent package describes what it re-exports, as cbor2/__init__.pyi does for the functions
    # of the native cbor2._cbor2, and only those, so the same name there must be this very object; getattr_static reads
    # the names, as the lazy `__getattr__` of a package imports on access and may raise, or rewrite `__module__` so
    # autodoc skips the class as imported
    top_name = str(getattr(obj, "__qualname__", "")).partition(".")[0]
    if (defined := getattr_static(module, top_name, None)) is None:
        return None
    module_name = module.__name__
    while "." in module_name:
        module_name = module_name.rsplit(".", 1)[0]
        if (
            (parent := sys.modules.get(module_name))
            and (result := _find_stub_for_module(parent))
            and getattr_static(parent, top_name, None) is defined
        ):
            return result, parent
    # the module autodoc documents `name` under types the names it exports, also by importing them from another stub,
    # as `attrs/__init__.pyi` does with `from attr import asdict as asdict` although `attrs.asdict` is a
    # different function at runtime
    if (found := imported_prefix(name.split(".")[:-1])) is None or getattr_static(
        documenting := sys.modules[found[0]], top_name, None
    ) is not defined:
        return None
    return _find_stub_naming(documenting, top_name, set())


def _find_stub_for_module(module: ModuleType) -> Path | None:
    # a module lacking an attribute hands the lookup to its `__getattr__`
    if not (source_file := _module_attribute(module, "__file__")) or not isinstance(source_file, str | PathLike):
        # a PyO3-style submodule `PyModule_AddObject` registers has its `.pyi` in the parent package
        parent_name, _, child = module.__name__.rpartition(".")
        parent = sys.modules.get(parent_name) if parent_name else None
        return next(
            (
                stub
                for package_dir in getattr(parent, "__path__", []) or []
                for stub in (Path(package_dir) / f"{child}.pyi", Path(package_dir) / child / "__init__.pyi")
                if stub.is_file()
            ),
            None,
        )
    source = Path(source_file)
    if (stub := source.with_name(f"{source.name.split('.')[0]}.pyi")).is_file():
        return stub
    if isinstance(package_dirs := _module_attribute(module, "__path__"), Iterable):
        for package_dir in package_dirs:
            if (init_stub := Path(package_dir) / "__init__.pyi").is_file():
                return init_stub
    return None


# without the `__getattr__` of the module, through the property a module subclass may define
def _module_attribute(module: ModuleType, name: str) -> Documented:
    if not isdatadescriptor(value := getattr_static(module, name, None)):
        return value
    # calling the getter skips the fallback to __getattr__ that getattr takes when the getter raises AttributeError
    try:
        return value.__get__(module, type(module))
    except AttributeError:
        return None


def _find_stub_naming(module: ModuleType, top_name: str, seen: set[str]) -> tuple[Path, ModuleType] | None:
    seen.add(module.__name__)
    if (path := _find_stub_for_module(module)) is None or (tree := parse_stub_ast(path)) is None:
        return None
    for node in live_statements(tree.body):
        if isinstance(node, ClassDef | FunctionDef | AsyncFunctionDef) and node.name == top_name:
            return path, module
        if (
            isinstance(node, ImportFrom)
            and any(alias.name == top_name and alias.asname in {None, top_name} for alias in node.names)
            and (source_name := resolve_import_from(node, stub_owner_package(module, path)))
            and source_name not in seen
            and (source := import_module_or_none(source_name)) is not None
        ):
            return _find_stub_naming(source, top_name, seen)
    return None


def parse_stub_ast(path: Path) -> Module | None:
    """Return the parsed stub at `path`, `None` when it cannot be read or does not parse."""
    # keyed on the modification time too, so a stub edited while the process runs is read again
    try:
        key = (path, path.stat().st_mtime_ns)
    except OSError:
        return None
    if key not in _STUB_AST_CACHE:
        try:
            _STUB_AST_CACHE[key] = parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            _STUB_AST_CACHE[key] = None
    return _STUB_AST_CACHE[key]


def live_statements(body: list[stmt]) -> Iterator[stmt]:
    """Yield the statements of `body`, taking the `if` branch this interpreter takes, or both if it can't tell."""
    # stubs gate definitions on the Python version or platform
    for node in body:
        if not isinstance(node, If):
            yield node
            continue
        try:
            live = eval(  # ruff:ignore[suspicious-eval-usage]  # nothing but sys is in scope
                compile(Expression(node.test), "<stub>", "eval"), {"__builtins__": {}, "sys": sys}
            )
        except Exception:  # ruff:ignore[blind-except]  # a condition on something else keeps both branches
            yield from live_statements([*node.body, *node.orelse])
        else:
            yield from live_statements(node.body if live else node.orelse)


def stub_owner_package(owner_module: ModuleType, path: Path) -> str:
    # a native submodule holds `__package__ = None`, so its package derives from the name of the stub
    if owner_package := getattr(owner_module, "__package__", None):
        return owner_package
    owner_name = owner_module.__name__
    return owner_name if path.name == "__init__.pyi" else owner_name.rpartition(".")[0]


def resolve_import_from(node: ImportFrom, owner_package: str) -> str | None:
    """Return the module a `from` import in a stub of `owner_package` names, `None` past the top package."""
    if not node.level or not owner_package:
        return node.module or None
    if len(parts := owner_package.rsplit(".", node.level - 1)) < node.level:
        return None
    return f"{parts[0]}.{node.module}" if node.module else parts[0]


def import_module_or_none(module_name: str) -> ModuleType | None:
    try:
        return import_module(module_name)
    except ImportError:
        return None


__all__ = [
    "find_stub_owner",
    "import_module_or_none",
    "live_statements",
    "parse_stub_ast",
    "resolve_import_from",
    "stub_owner_package",
    "stub_path",
]
