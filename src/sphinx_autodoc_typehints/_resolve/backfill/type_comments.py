"""Reads PEP 484 `# type: (...) -> ...` comments from the source of a function."""

from __future__ import annotations

from ast import AsyncFunctionDef, FunctionDef, parse
from inspect import getsourcelines
from textwrap import dedent
from types import ModuleType
from typing import TYPE_CHECKING

from sphinx_autodoc_typehints._refs import split_arguments
from sphinx_autodoc_typehints._warnings import warn

from ..source import parameters

if TYPE_CHECKING:
    from sphinx_autodoc_typehints._types import Documented


def backfill_type_hints(obj: Documented, name: str) -> dict[str, str]:
    """
    Return the annotations the type comment of the function `obj`, documented as `name`, gives it.

    The result is empty when the source is missing, holds no function with a type comment, or the comment does not
    parse, and holds only the return type when the comment types fewer parameters than the function takes.
    """
    if (node := _function_node(obj, name)) is None or not (type_comment := node.type_comment):
        return {}
    try:
        comment_args, comment_returns = type_comment.split(" -> ")
    except ValueError:
        warn(
            "comment",
            'Unparseable type hint comment for "%s": Expected to contain ` -> `',
            name,
            at=obj,
        )
        return {}
    hints: dict[str, str] = {"return": comment_returns} if comment_returns else {}
    params = parameters(node)
    comment_types: list[str | None] = (
        [part.strip().lstrip("*") for part in split_arguments(stripped)]
        if (stripped := comment_args.strip().lstrip("(").rstrip(")"))
        else []
    )
    if comment_types == ["..."]:
        hints.update({param.arg: param.type_comment for param in params if param.type_comment is not None})
        return hints
    if params and params[0].arg in {"self", "cls"} and len(comment_types) != len(params):
        comment_types.insert(0, None)
    if len(params) != len(comment_types):
        warn(
            "comment",
            'Not enough type comments found on "%s"',
            name,
            at=obj,
        )
        return hints
    hints.update({param.arg: value for param, value in zip(params, comment_types, strict=True) if value is not None})
    return hints


def _function_node(obj: Documented, name: str) -> FunctionDef | AsyncFunctionDef | None:
    if not (callable(obj) or isinstance(obj, ModuleType)):
        return None
    try:
        lines, _ = getsourcelines(obj)
    except (OSError, TypeError):
        return None
    # a line indented less than the `def`, as one in a multi-line string may be, keeps dedent from unindenting it
    for at, line in enumerate(lines):
        if (stripped := line.lstrip()).startswith(("def ", "async def")):
            whitespace = line[: len(line) - len(stripped)]
            lines = [
                text if index == at else whitespace + text.removeprefix(whitespace) for index, text in enumerate(lines)
            ]
            break
    try:
        tree = parse(dedent("".join(lines)), type_comments=True)
    except SyntaxError:
        return None
    if len(tree.body) != 1:
        warn(
            "multiple_ast_nodes",
            'Did not get exactly one node from AST for "%s", got %s',
            name,
            len(tree.body),
            at=obj,
        )
        return None
    # a lambda's source is the assignment holding it, whose type comment types the variable rather than the call
    return node if isinstance(node := tree.body[0], FunctionDef | AsyncFunctionDef) else None


__all__ = [
    "backfill_type_hints",
]
