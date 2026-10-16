"""The annotations of attributes, as a class or module body declares them or `__init__` writes them on `self`."""

from __future__ import annotations

from ast import (
    AST,
    AnnAssign,
    AsyncFunctionDef,
    Attribute,
    ClassDef,
    FunctionDef,
    Name,
    iter_child_nodes,
    unparse,
    walk,
)
from inspect import unwrap
from typing import TYPE_CHECKING, ClassVar, Final, get_args, get_origin

from .evaluate import evaluate_annotation, type_hints
from .guards import annotation_globals, guarded_names
from .source import parsed_source

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType

    from .._types import Annotation


def get_instance_var_annotations(cls: type) -> dict[str, Annotation | str]:
    """
    Return the annotations `__init__` gives the attributes of `self`, the source text of one that fails to evaluate.

    The runtime stores no `self.x: T = ...` annotation, so `typing.get_type_hints` cannot see it and only the
    source has it. Statements inside `if`, `try` and `with` blocks count; those of nested functions and classes
    do not, as they belong to a scope that may not run.
    """
    if (init := cls.__init__) is object.__init__ or (tree := parsed_source(init)) is None:
        return {}
    raw: dict[str, str] = {}
    for node in walk(tree):
        if isinstance(node, FunctionDef) and node.name == "__init__":
            params = [*node.args.posonlyargs, *node.args.args]
            self_name = params[0].arg if params else "self"
            for statement in _own_nodes(node):
                if (
                    isinstance(statement, AnnAssign)
                    and isinstance(statement.target, Attribute)
                    and isinstance(statement.target.value, Name)
                    and statement.target.value.id == self_name
                ):
                    raw[statement.target.attr] = unparse(statement.annotation)
            break
    if not raw:
        return {}
    # an inherited or re-exported `__init__` sees the names of the module defining it, not those of the class's
    globalns = annotation_globals(unwrap(init))
    resolved: dict[str, Annotation | str] = {}
    for attribute, source in raw.items():
        try:
            resolved[attribute] = evaluate_annotation(source, globalns, {})
        except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
            resolved[attribute] = source
    return resolved


def _own_nodes(node: AST) -> Iterator[AST]:
    for child in iter_child_nodes(node):
        yield child
        if not isinstance(child, FunctionDef | AsyncFunctionDef | ClassDef):
            yield from _own_nodes(child)


def get_body_annotations(owner: type | ModuleType) -> dict[str, Annotation]:
    """
    Return the attributes the body of a module, or of a class and its bases, annotates, the PEP 526 way to declare one.

    A `ClassVar` or `Final` qualifier says how the attribute behaves, not what it holds, so the result drops it.
    The result is empty when an annotation fails to evaluate.
    """
    try:
        # a class reads the guard of the module defining each base itself
        hints = type_hints(owner, None, None if isinstance(owner, type) else guarded_names(owner))
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return {}
    held = {name: get_args(hint)[0] if _is_qualifier(get_origin(hint)) else hint for name, hint in hints.items()}
    # a bare ClassVar or Final names no type
    return {name: hint for name, hint in held.items() if not _is_qualifier(hint)}


def _is_qualifier(hint: object) -> bool:
    # matched by identity, as a set lookup would hash the annotation, which Annotated with dict metadata cannot do
    return hint is ClassVar or hint is Final


__all__ = [
    "get_body_annotations",
    "get_instance_var_annotations",
]
