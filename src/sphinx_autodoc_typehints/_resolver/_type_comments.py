"""Type comment backfill for functions lacking runtime annotations."""

from __future__ import annotations

import ast
import inspect
import textwrap
from typing import TYPE_CHECKING, Any

from sphinx.util import logging

from ._util import get_obj_location

if TYPE_CHECKING:
    from ast import AsyncFunctionDef, FunctionDef, Module, stmt

_LOGGER = logging.getLogger(__name__)


def backfill_type_hints(obj: Any, name: str) -> dict[str, Any]:  # noqa: C901, PLR0911
    parse_kwargs = {"type_comments": True}

    def _one_child(module: Module) -> stmt | None:
        children = module.body
        if len(children) != 1:
            _LOGGER.warning(
                'Did not get exactly one node from AST for "%s", got %s',
                name,
                len(children),
                type="sphinx_autodoc_typehints",
                subtype="multiple_ast_nodes",
                location=get_obj_location(obj),
            )
            return None
        return children[0]

    try:
        code = textwrap.dedent(_normalize_source_lines(inspect.getsource(obj)))
        obj_ast = ast.parse(code, **parse_kwargs)  # type: ignore[call-overload]  # dynamic kwargs
    except (OSError, TypeError, SyntaxError):
        return {}

    obj_ast = _one_child(obj_ast)
    if obj_ast is None:
        return {}

    try:
        type_comment = obj_ast.type_comment  # type: ignore[attr-defined]
    except AttributeError:
        return {}

    if not type_comment:
        return {}

    try:
        comment_args_str, comment_returns = type_comment.split(" -> ")
    except ValueError:
        _LOGGER.warning(
            'Unparseable type hint comment for "%s": Expected to contain ` -> `',
            name,
            type="sphinx_autodoc_typehints",
            subtype="comment",
            location=get_obj_location(obj),
        )
        return {}

    rv = {}
    if comment_returns:
        rv["return"] = comment_returns

    args = _load_args(obj_ast)  # type: ignore[arg-type]
    comment_args = _split_type_comment_args(comment_args_str)
    is_inline = len(comment_args) == 1 and comment_args[0] == "..."
    if not is_inline:
        if args and args[0].arg in {"self", "cls"} and len(comment_args) != len(args):
            comment_args.insert(0, None)

        if len(args) != len(comment_args):
            _LOGGER.warning(
                'Not enough type comments found on "%s"',
                name,
                type="sphinx_autodoc_typehints",
                subtype="comment",
                location=get_obj_location(obj),
            )
            return rv

    for at, arg in enumerate(args):
        value = getattr(arg, "type_comment", None) if is_inline else comment_args[at]
        if value is not None:
            rv[arg.arg] = value

    return rv


def _normalize_source_lines(source_lines: str) -> str:
    lines = source_lines.split("\n")

    def remove_prefix(text: str, prefix: str) -> str:
        return text[text.startswith(prefix) and len(prefix) :]

    for pos, line in enumerate(lines):
        if line.lstrip().startswith("def "):
            idx = pos
            whitespace_separator = "def"
            break
        if line.lstrip().startswith("async def"):
            idx = pos
            whitespace_separator = "async def"
            break

    else:
        return "\n".join(lines)
    fn_def = lines[idx]

    whitespace = fn_def.split(whitespace_separator)[0]

    aligned_prefix = [whitespace + remove_prefix(s, whitespace) for s in lines[:idx]]
    aligned_suffix = [whitespace + remove_prefix(s, whitespace) for s in lines[idx + 1 :]]

    aligned_prefix.append(fn_def)
    return "\n".join(aligned_prefix + aligned_suffix)


def _load_args(obj_ast: FunctionDef | AsyncFunctionDef) -> list[Any]:
    func_args = obj_ast.args
    args = []
    pos_only = getattr(func_args, "posonlyargs", None)
    if pos_only:
        args.extend(pos_only)

    args.extend(func_args.args)
    if func_args.vararg:
        args.append(func_args.vararg)

    args.extend(func_args.kwonlyargs)
    if func_args.kwarg:
        args.append(func_args.kwarg)

    return args


def _split_type_comment_args(comment: str) -> list[str | None]:
    def add(val: str) -> None:
        result.append(val.strip().lstrip("*"))

    comment = comment.strip().lstrip("(").rstrip(")")
    result: list[str | None] = []
    if not comment:
        return result

    brackets, start_arg_at, at = 0, 0, 0
    for at, char in enumerate(comment):
        if char in {"[", "("}:
            brackets += 1
        elif char in {"]", ")"}:
            brackets -= 1
        elif char == "," and brackets == 0:
            add(comment[start_arg_at:at])
            start_arg_at = at + 1

    add(comment[start_arg_at : at + 1])
    return result


__all__ = ["backfill_type_hints"]
