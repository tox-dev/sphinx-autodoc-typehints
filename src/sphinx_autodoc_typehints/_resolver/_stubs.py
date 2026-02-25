"""Stub file (.pyi) annotation backfill."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

from ._type_comments import _load_args

_STUB_AST_CACHE: dict[Path, ast.Module | None] = {}


def _backfill_from_stub(obj: Any) -> dict[str, str]:
    if (stub_path := _find_stub_path(obj)) and (tree := _parse_stub_ast(stub_path)):
        return _extract_annotations_from_stub(tree, obj)
    return {}


def _find_stub_path(obj: Any) -> Path | None:
    module = inspect.getmodule(obj)
    if module is None:
        return None
    try:
        source_file = inspect.getfile(module)
    except TypeError:
        return None
    stub = Path(source_file).with_suffix(".pyi")
    if stub.is_file():
        return stub
    if hasattr(module, "__path__"):
        for pkg_dir in module.__path__:
            init_stub = Path(pkg_dir) / "__init__.pyi"
            if init_stub.is_file():
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
