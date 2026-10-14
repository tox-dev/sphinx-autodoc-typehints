from __future__ import annotations

import ast
import inspect
import textwrap
from typing import TYPE_CHECKING, Any, ClassVar, Final, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from collections.abc import Iterator


def get_instance_var_annotations(cls: type) -> dict[str, Any]:
    """
    Extract instance variable annotations from ``__init__`` by walking its AST.

    ``self.x: T = ...`` is not stored in ``cls.__annotations__`` at runtime, so
    ``typing.get_type_hints`` cannot see it — AST inspection is the only option.
    Statements inside blocks such as ``if``, ``try`` and ``with`` count, those of
    nested functions and classes do not, as they belong to a scope that may never run.
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
            params = [*node.args.posonlyargs, *node.args.args]
            self_name = params[0].arg if params else "self"
            for stmt in _own_nodes(node):
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

    # an inherited or re-exported ``__init__`` sees the names of the module defining it, not those of the class's
    globalns = inspect.unwrap(init).__globals__
    resolved: dict[str, Any] = {}
    for attr_name, ann_str in raw.items():
        try:
            resolved[attr_name] = eval(ann_str, globalns)  # ruff:ignore[suspicious-eval-usage]
        except Exception:  # ruff:ignore[blind-except]
            resolved[attr_name] = ann_str
    return resolved


def get_class_body_annotations(cls: type) -> dict[str, Any]:
    """
    Return the attributes the bodies of a class and its bases annotate, the PEP 526 way to declare one.

    A ``ClassVar`` or ``Final`` qualifier says how the attribute behaves, not what it holds, so it is left off.
    """
    try:
        hints = get_type_hints(cls, include_extras=True)
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return {}
    held = {name: get_args(hint)[0] if _is_qualifier(get_origin(hint)) else hint for name, hint in hints.items()}
    # a bare ClassVar or Final names no type
    return {name: hint for name, hint in held.items() if not _is_qualifier(hint)}


def _is_qualifier(hint: Any) -> bool:
    # matched by identity, as a set lookup would hash the annotation, which Annotated with dict metadata cannot do
    return hint is ClassVar or hint is Final


def _own_nodes(node: ast.AST) -> Iterator[ast.AST]:
    for child in ast.iter_child_nodes(node):
        yield child
        if not isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            yield from _own_nodes(child)


__all__ = ["get_class_body_annotations", "get_instance_var_annotations"]
