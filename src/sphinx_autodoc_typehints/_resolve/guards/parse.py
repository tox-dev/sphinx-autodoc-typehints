"""Reads the statements of the `TYPE_CHECKING` guard of a module and the names they define, without running them."""

from __future__ import annotations

import sys
from ast import (
    AST,
    And,
    AnnAssign,
    Assign,
    AsyncFunctionDef,
    Attribute,
    BoolOp,
    ClassDef,
    Compare,
    Constant,
    Eq,
    FunctionDef,
    If,
    Import,
    ImportFrom,
    Name,
    Not,
    NotEq,
    UnaryOp,
    expr,
    iter_child_nodes,
    parse,
    stmt,
    walk,
)
from functools import cache
from inspect import getsource
from re import MULTILINE, findall
from typing import TYPE_CHECKING
from warnings import catch_warnings, simplefilter

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType


def guard_binds(module: ModuleType, names: set[str]) -> bool:
    statements, _ = guarded_statements(module_source(module))
    return any(name in names for statement in statements for name in defined_names(statement))


def module_source(module: ModuleType) -> str:
    try:
        return getsource(module)
    except (TypeError, OSError):
        return ""


# every importer of a module asks again while its guard binds none of the names imported, and parsing typing takes
# milliseconds; keyed on the source, so reloading an edited module parses it again
@cache
def guarded_statements(module_code: str) -> tuple[tuple[stmt, ...], tuple[SyntaxError, ...]]:
    """Return the statements only a type checker runs, and why the guards that could not be read failed to parse."""
    if "TYPE_CHECKING" not in module_code:
        return (), ()
    # the module compiled already, so its warnings are no news, and -W error would turn them into a SyntaxError
    with catch_warnings():
        simplefilter("ignore", SyntaxWarning)
        try:
            nodes, errors = parse(module_code).body, []
        except SyntaxError:
            # parse each top-level `if` naming `TYPE_CHECKING` on its own, as 3.13.10 did: the source `inspect`
            # reads may not parse as a whole, as a stale `linecache` entry or a module a custom loader compiles from
            # another language does, while its guards do
            nodes, errors = [], []
            # a statement of the module body starting with `if`, with its indented lines and its `elif` and
            # `else` branches
            for block in findall(
                r"^if\b.*(?:\n|\Z)(?:(?:[ \t]+.*|(?:elif|else)\b.*)?(?:\n|\Z))*", module_code, MULTILINE
            ):
                if "TYPE_CHECKING" in block:
                    try:
                        nodes.extend(parse(block).body)
                    except SyntaxError as exc:
                        errors.append(exc)
    # the `else` of `if not TYPE_CHECKING` is what only a type checker runs
    return tuple(
        statement
        for node in nodes
        if isinstance(node, If)
        and any(
            (isinstance(part, Name) and part.id == "TYPE_CHECKING")
            or (isinstance(part, Attribute) and part.attr == "TYPE_CHECKING")
            for part in walk(node.test)
        )
        and (holds := _holds_when_type_checking(node.test)) is not None
        for statement in (node.body if holds else node.orelse)
    ), tuple(errors)


# `None` when `TYPE_CHECKING` plays no part in the test
def _holds_when_type_checking(test: expr) -> bool | None:
    if isinstance(test, Constant):
        return bool(test.value)
    # a bare name or from any alias the module gives typing
    if (isinstance(test, Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, Attribute) and test.attr == "TYPE_CHECKING"
    ):
        return True
    if isinstance(test, UnaryOp) and isinstance(test.op, Not):
        return None if (operand := _holds_when_type_checking(test.operand)) is None else not operand
    if isinstance(test, Compare):
        return _platform_comparison(test)
    if isinstance(test, BoolOp):
        values = [_holds_when_type_checking(value) for value in test.values]
        if isinstance(test.op, And):
            holds = False if False in values else True if all(value is True for value in values) else None
        else:
            holds = True if True in values else False if all(value is False for value in values) else None
        return holds
    return None


def _platform_comparison(test: Compare) -> bool | None:
    if len(test.ops) != 1 or len(test.comparators) != 1:
        return None
    if not isinstance(test.left, Attribute) or not isinstance(test.left.value, Name):
        return None
    if test.left.value.id != "sys" or test.left.attr != "platform":
        return None
    if not isinstance(test.comparators[0], Constant) or not isinstance(test.comparators[0].value, str):
        return None
    if isinstance(test.ops[0], Eq):
        return sys.platform == test.comparators[0].value
    return sys.platform != test.comparators[0].value if isinstance(test.ops[0], NotEq) else None


def defined_names(node: AST) -> Iterator[str]:
    """Yield the names the node binds, taking only its own targets so loop and comprehension variables stay out."""
    if isinstance(node, ClassDef | FunctionDef | AsyncFunctionDef):
        yield node.name
    elif isinstance(node, Assign):
        yield from (target.id for target in node.targets if isinstance(target, Name))
    elif isinstance(node, AnnAssign):
        if isinstance(node.target, Name):
            yield node.target.id
    elif isinstance(node, Import | ImportFrom):
        yield from (alias.asname or alias.name.partition(".")[0] for alias in node.names)
    elif isinstance(node, stmt):
        for child in iter_child_nodes(node):
            yield from defined_names(child)


__all__ = [
    "defined_names",
    "guard_binds",
    "guarded_statements",
    "module_source",
]
