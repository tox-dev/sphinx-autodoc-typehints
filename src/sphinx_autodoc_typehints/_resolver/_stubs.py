"""Stub file (.pyi) annotation backfill."""

from __future__ import annotations

import ast
import contextlib
import importlib
import inspect
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._type_comments import _load_args

if TYPE_CHECKING:
    import types

_STUB_AST_CACHE: dict[Path, ast.Module | None] = {}


def _backfill_from_stub(obj: Any) -> dict[str, str]:
    if (stub_path := _find_stub_path(obj)) and (tree := _parse_stub_ast(stub_path)):
        return _extract_annotations_from_stub(tree, obj)
    return {}


def _get_stub_context(obj: Any) -> tuple[dict[str, Any], set[str], str]:
    """
    Return (localns, alias_names, owner_module_name) from the stub owning *obj*.

    Single lookup avoids duplicate ``_find_stub_owner`` / ``_parse_stub_ast`` calls. The owner module name lets callers
    use ``vars(sys.modules[name])`` as the correct globalns — important when a C extension function lives in a child
    module but its stub belongs to a parent package (e.g. ``cbor2._cbor2.dumps`` → ``cbor2/__init__.pyi``).
    """
    if (info := _find_stub_owner(obj)) is None:
        return {}, set(), ""
    stub_path, owner_module = info
    if (tree := _parse_stub_ast(stub_path)) is None:
        return {}, set(), ""
    ns: dict[str, Any] = dict(vars(owner_module))
    ns.update(_resolve_stub_imports(tree))
    return ns, _extract_type_alias_names(tree), owner_module.__name__


def _resolve_stub_imports(tree: ast.Module) -> dict[str, Any]:
    ns: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                with contextlib.suppress(ImportError):
                    if alias.asname:
                        ns[alias.asname] = importlib.import_module(alias.name)
                    else:
                        top = alias.name.split(".")[0]
                        ns[top] = importlib.import_module(top)
        elif isinstance(node, ast.ImportFrom) and node.module:
            try:
                mod = importlib.import_module(node.module)
            except ImportError:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                if (val := getattr(mod, alias.name, None)) is not None:
                    ns[name] = val
    return ns


def _get_module(obj: Any) -> types.ModuleType | None:
    if module := inspect.getmodule(obj):
        return module
    # inspect.getmodule returns None for some C/Rust extension descriptors even when __module__ is valid.
    if (mod_name := getattr(obj, "__module__", None)) and (module := sys.modules.get(mod_name)):
        return module
    # Method descriptors on C extension types expose the owning class via __objclass__.
    if (owner_cls := getattr(obj, "__objclass__", None)) and (module := inspect.getmodule(owner_cls)):
        return module
    # Bound methods like __new__ on C extension classes have __self__ pointing to the class.
    if (owner_cls := getattr(obj, "__self__", None)) and inspect.isclass(owner_cls):
        return inspect.getmodule(owner_cls)
    return None


def _find_stub_path(obj: Any) -> Path | None:
    if info := _find_stub_owner(obj):
        return info[0]
    return None


def _find_stub_owner(obj: Any) -> tuple[Path, types.ModuleType] | None:
    if (module := _get_module(obj)) is None:
        return None
    if result := _find_stub_for_module(module):
        return result, module
    # PEP 561 re-export pattern: cbor2.__init__.pyi documents functions living in cbor2._cbor2 (C/Rust). Walk up to
    # find the parent package whose stub describes the re-exported public API.
    module_name = module.__name__
    while "." in module_name:
        module_name = module_name.rsplit(".", 1)[0]
        if (parent := sys.modules.get(module_name)) and (result := _find_stub_for_module(parent)):
            return result, parent
    return None


def _find_stub_for_module(module: types.ModuleType) -> Path | None:
    try:
        source_file = inspect.getfile(module)
    except TypeError:
        return None
    source = Path(source_file)
    if (stub := source.with_name(f"{source.name.split('.')[0]}.pyi")).is_file():
        return stub
    if hasattr(module, "__path__"):
        for pkg_dir in module.__path__:
            if (init_stub := Path(pkg_dir) / "__init__.pyi").is_file():
                return init_stub
    return None


def _parse_stub_ast(stub_path: Path) -> ast.Module | None:
    if stub_path not in _STUB_AST_CACHE:
        try:
            _STUB_AST_CACHE[stub_path] = ast.parse(stub_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            _STUB_AST_CACHE[stub_path] = None
    return _STUB_AST_CACHE[stub_path]


_TYPE_ALIAS_ANNOTATIONS = {"TypeAlias", "typing.TypeAlias", "typing_extensions.TypeAlias"}


def _extract_type_alias_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.annotation, ast.Name | ast.Attribute)
            and ast.unparse(node.annotation) in _TYPE_ALIAS_ANNOTATIONS
        ):
            names.add(node.target.id)
        elif isinstance(node, ast.TypeAlias) and isinstance(node.name, ast.Name):
            names.add(node.name.id)
    return names


def _extract_annotations_from_stub(tree: ast.Module, obj: Any) -> dict[str, str]:
    qualname = getattr(obj, "__qualname__", None)
    if not qualname:
        return {}
    parts = qualname.split(".")
    if (node := _find_ast_node(tree.body, parts)) is None:
        return {}
    if isinstance(node, ast.ClassDef):
        return _extract_class_annotations(node)
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return _extract_func_annotations(node)
    return {}  # pragma: no cover


def _find_ast_node(body: list[ast.stmt], parts: list[str]) -> ast.stmt | None:
    target, *rest = parts
    for node in body:
        if isinstance(node, ast.ClassDef) and node.name == target:
            return _find_ast_node(node.body, rest) if rest else node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target and not rest:
            return node
    return None


def _extract_func_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str]:
    result: dict[str, str] = {}
    for arg in _load_args(node):
        if arg.annotation is not None:
            result[arg.arg] = ast.unparse(arg.annotation)
    if node.returns is not None:
        result["return"] = ast.unparse(node.returns)
    return result


def _extract_class_annotations(node: ast.ClassDef) -> dict[str, str]:
    result: dict[str, str] = {}
    for child in node.body:
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            result[child.target.id] = ast.unparse(child.annotation)
    return result


__all__: list[str] = []
