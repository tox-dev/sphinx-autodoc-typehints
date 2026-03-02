"""Stub file (.pyi) annotation backfill."""

from __future__ import annotations

import ast
import contextlib
import importlib
import inspect
from pathlib import Path
from typing import Any

from ._type_comments import _load_args

_STUB_AST_CACHE: dict[Path, ast.Module | None] = {}


def _backfill_from_stub(obj: Any) -> dict[str, str]:
    if (stub_path := _find_stub_path(obj)) and (tree := _parse_stub_ast(stub_path)):
        return _extract_annotations_from_stub(tree, obj)
    return {}


def _get_stub_localns(obj: Any) -> dict[str, Any]:
    if (stub_path := _find_stub_path(obj)) and (tree := _parse_stub_ast(stub_path)):
        return _resolve_stub_imports(tree)
    return {}


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


def _find_stub_path(obj: Any) -> Path | None:
    if (module := inspect.getmodule(obj)) is None:
        return None
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
