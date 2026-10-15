"""Reads the annotations a stub writes for an object."""

from __future__ import annotations

from ast import AnnAssign, AsyncFunctionDef, ClassDef, FunctionDef, Name, stmt, unparse
from typing import TYPE_CHECKING

from sphinx_autodoc_typehints._resolve.source import function_annotations

from .find import live_statements, parse_stub_ast, stub_path

if TYPE_CHECKING:
    from collections.abc import Callable


def stub_annotations(obj: Callable[..., object], name: str = "") -> dict[str, str]:
    """Return the annotations the stub describing `obj`, documented as `name`, writes for it, empty without one."""
    if (
        not (path := stub_path(obj, name))
        or not (tree := parse_stub_ast(path))
        or not (qualname := getattr(obj, "__qualname__", None))
        or not (nodes := _find_ast_nodes(tree.body, qualname.split(".")))
    ):
        return {}
    if isinstance(nodes[0], ClassDef):
        return {
            child.target.id: unparse(child.annotation)
            for child in live_statements(nodes[0].body)
            if isinstance(child, AnnAssign) and isinstance(child.target, Name)
        }
    # a property's setter and deleter share its name but not its type, which the getter alone carries
    variants = [
        node
        for node in nodes
        if isinstance(node, FunctionDef | AsyncFunctionDef)
        and not any(
            unparse(decorator) in {f"{node.name}.setter", f"{node.name}.deleter"} for decorator in node.decorator_list
        )
    ]
    # overload variants describe one function together; an implementation signature, where the stub has one,
    # describes it alone
    implementations = [
        node
        for node in variants
        if not any(unparse(decorator) in {"overload", "typing.overload"} for decorator in node.decorator_list)
    ]
    variant_hints = [function_annotations(node) for node in implementations or variants]
    # the union of the types of the parameters the variants share, as the implementation accepts what any variant does
    return {
        parameter: " | ".join(dict.fromkeys(variant[parameter] for variant in variant_hints))
        for parameter in variant_hints[0]
        if all(parameter in variant for variant in variant_hints)
    }


def find_ast_node(body: list[stmt], parts: list[str]) -> stmt | None:
    """Return the first statement `parts` names in `body`, following classes inward, `None` when none does."""
    return next(iter(_find_ast_nodes(body, parts)), None)


def _find_ast_nodes(body: list[stmt], parts: list[str]) -> list[stmt]:
    target, *rest = parts
    functions: list[stmt] = []
    for node in live_statements(body):
        if isinstance(node, ClassDef) and node.name == target:
            return _find_ast_nodes(node.body, rest) if rest else [node]
        if isinstance(node, FunctionDef | AsyncFunctionDef) and node.name == target and not rest:
            functions.append(node)
    return functions


__all__ = [
    "find_ast_node",
    "stub_annotations",
]
