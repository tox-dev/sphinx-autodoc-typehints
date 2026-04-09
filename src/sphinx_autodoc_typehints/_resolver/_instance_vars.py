from __future__ import annotations

import ast
import inspect
import textwrap
from typing import Any


def get_instance_var_annotations(cls: type) -> dict[str, Any]:
    """
    Extract instance variable annotations from ``__init__`` by walking its AST.

    ``self.x: T = ...`` is not stored in ``cls.__annotations__`` at runtime, so
    ``typing.get_type_hints`` cannot see it — AST inspection is the only option.
    Only top-level statements of ``__init__`` are scanned to avoid picking up
    annotations from nested functions.
    """
    init = cls.__init__
    if init is object.__init__:
        return {}
    try:
        source = textwrap.dedent(inspect.getsource(init))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError, IndentationError):
        return {}

    raw: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            self_name = node.args.args[0].arg if node.args.args else "self"
            for stmt in node.body:
                if (
                    isinstance(stmt, ast.AnnAssign)
                    and isinstance(stmt.target, ast.Attribute)
                    and isinstance(stmt.target.value, ast.Name)
                    and stmt.target.value.id == self_name
                ):
                    raw[stmt.target.attr] = ast.unparse(stmt.annotation)
            break

    if not raw:
        return {}

    module = inspect.getmodule(cls)
    globalns: dict[str, Any] = vars(module) if module is not None else {}
    resolved: dict[str, Any] = {}
    for attr_name, ann_str in raw.items():
        try:
            resolved[attr_name] = eval(ann_str, globalns)  # noqa: S307
        except Exception:  # noqa: BLE001
            resolved[attr_name] = ann_str
    return resolved


__all__ = ["get_instance_var_annotations"]
