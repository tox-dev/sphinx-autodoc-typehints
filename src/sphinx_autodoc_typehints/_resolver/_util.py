"""Shared utilities for type hint resolution."""

from __future__ import annotations

import ast
import inspect
import textwrap
from typing import TYPE_CHECKING, Any

from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef

if TYPE_CHECKING:
    from sphinx.environment import BuildEnvironment


def get_obj_location(obj: Any) -> str | None:
    try:
        filepath = inspect.getsourcefile(obj) or inspect.getfile(obj)
    except TypeError:
        return None
    # code without a file, such as the __init__ a dataclass generates, is named like <string>
    if filepath.startswith("<"):
        return None
    try:
        lineno = inspect.getsourcelines(obj)[1]
    except (OSError, TypeError):
        return filepath
    else:
        return f"{filepath}:{lineno}"


def collect_documented_type_aliases(
    obj: Any, module_prefix: str, env: BuildEnvironment
) -> tuple[dict[str, MyTypeAliasForwardRef], dict[str, MyTypeAliasForwardRef]]:
    py_objects = env.get_domain("py").objects  # ty: ignore[unresolved-attribute]
    deferred = _collect_module_type_aliases(module_prefix, py_objects)
    eager: dict[str, MyTypeAliasForwardRef] = {}

    # PEP 649 (Python 3.14+): annotation expressions only run on access and may fail at runtime
    # (TYPE_CHECKING-only names, subscripting a non-generic class)
    try:
        raw_annotations = getattr(obj, "__annotations__", {})
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return deferred, eager
    if not raw_annotations:
        return deferred, eager

    obj_globals = getattr(obj, "__globals__", {})
    # an alias evaluates to the object it names (``Count = int``), so only the annotation as written tells them apart
    written = _written_annotations(obj)
    for key, annotation in raw_annotations.items():
        if isinstance(annotation, str):
            if _is_documented_type(annotation, module_prefix, py_objects):
                ref = MyTypeAliasForwardRef(annotation)
                ref.crossref = True
                deferred[annotation] = ref
        elif (
            (name := written.get(key))
            and not name.startswith("_")
            and obj_globals.get(name) is annotation
            and _is_documented_type(name, module_prefix, py_objects)
        ):
            ref = MyTypeAliasForwardRef(name)
            ref.crossref = True
            eager[key] = ref

    return deferred, eager


def _collect_module_type_aliases(module_prefix: str, py_objects: dict[str, Any]) -> dict[str, MyTypeAliasForwardRef]:
    scopes = _enclosing_scopes(module_prefix)
    result: dict[str, MyTypeAliasForwardRef] = {}
    for fqn, obj_info in py_objects.items():
        if obj_info.objtype == "type" and fqn.rpartition(".")[0] in scopes:
            short_name = fqn.rsplit(".", 1)[-1]
            ref = MyTypeAliasForwardRef(short_name)
            ref.crossref = True
            result[short_name] = ref
    return result


def _enclosing_scopes(module_prefix: str) -> set[str]:
    """Annotations see the names of the module and the class bodies around them, not those of other modules."""
    parts = module_prefix.split(".")
    return {".".join(parts[:end]) for end in range(1, len(parts) + 1)}


def _written_annotations(obj: Any) -> dict[str, str]:
    try:
        node = ast.parse(textwrap.dedent(inspect.getsource(obj))).body[0]
    except (OSError, TypeError, SyntaxError):
        return {}
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return {}
    arguments = node.args
    params = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, arguments.vararg, arguments.kwarg]
    written = {param.arg: ast.unparse(param.annotation) for param in params if param and param.annotation}
    return written | ({"return": ast.unparse(node.returns)} if node.returns else {})


def _is_documented_type(name: str, module_prefix: str, py_objects: dict[str, Any]) -> bool:
    return any(
        candidate in py_objects and py_objects[candidate].objtype == "type"
        for candidate in (*(f"{scope}.{name}" for scope in _enclosing_scopes(module_prefix)), name)
    )


__all__ = [
    "collect_documented_type_aliases",
    "get_obj_location",
]
