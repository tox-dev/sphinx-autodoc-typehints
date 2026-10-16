"""
Annotations as the source writes them.

It reads a `def`, a module or class body, and the names an annotation refers to.
"""

from __future__ import annotations

from ast import AST, AnnAssign, AsyncFunctionDef, ClassDef, FunctionDef, Module, Name, arg, parse, unparse, walk
from collections import defaultdict
from functools import cache
from inspect import getsource
from sys import version_info
from textwrap import dedent
from types import ModuleType
from typing import TYPE_CHECKING
from warnings import catch_warnings, simplefilter

from sphinx.errors import PycodeError
from sphinx.pycode import ModuleAnalyzer

from .._private_imports import VariableCommentPicker
from .._types import frozendict

if version_info >= (3, 14):  # pragma: >=3.14 cover
    from annotationlib import Format, get_annotations

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from .._types import Annotation, Documented


def written_annotations(obj: Documented) -> dict[str, str]:
    """Read the annotations the `def` of `obj` writes from its source, empty when that is no function definition."""
    if (tree := parsed_source(obj)) is None or not isinstance(node := tree.body[0], FunctionDef | AsyncFunctionDef):
        return {}
    return function_annotations(node)


def parsed_source(obj: Documented) -> Module | None:
    """Parse the source of `obj`, `None` when it has none or the source does not parse on its own."""
    if not (callable(obj) or isinstance(obj, ModuleType)):
        return None
    try:
        return parse(dedent(getsource(obj)))
    except (OSError, TypeError, SyntaxError):
        return None


def function_annotations(node: FunctionDef | AsyncFunctionDef) -> dict[str, str]:
    """Return the annotations a `def` writes, keyed by parameter name and `return`."""
    written = {param.arg: unparse(param.annotation) for param in parameters(node) if param.annotation}
    return written | ({"return": unparse(node.returns)} if node.returns else {})


def parameters(node: FunctionDef | AsyncFunctionDef) -> list[arg]:
    """List the parameters of a `def` in the order a call binds them."""
    arguments = node.args
    return [
        *arguments.posonlyargs,
        *arguments.args,
        *([arguments.vararg] if arguments.vararg else []),
        *arguments.kwonlyargs,
        *([arguments.kwarg] if arguments.kwarg else []),
    ]


def source_annotations(module: str, qualname: str) -> dict[str, str]:
    """
    Return the annotations the body of `qualname` writes, the module's own for an empty name.

    autodoc replaces the annotations a module and its classes hold with what it evaluated, so only the source has them.
    The result is empty when Sphinx cannot analyze the module.
    """
    try:
        analyzer = ModuleAnalyzer.for_module(module)
        analyzer.analyze()
    except PycodeError:
        return {}
    return {attribute: source for (scope, attribute), source in _unambiguous(analyzer).items() if scope == qualname}


# Sphinx keeps the last annotation written for a name, which under `if`/`else` may be the branch that did not run
@cache
def _unambiguous(analyzer: ModuleAnalyzer) -> Mapping[tuple[str, str], str]:
    picker = _AnnotationsPicker(analyzer.code.splitlines(keepends=True), "utf-8")
    # the analyzer may have parsed the code with warnings silenced, while -W error turns them into a SyntaxError
    with catch_warnings():
        simplefilter("ignore", SyntaxWarning)
        picker.visit(parse(analyzer.code, type_comments=True))
    return frozendict({key: written.pop() for key, written in picker.written.items() if len(written) == 1})


class _AnnotationsPicker(VariableCommentPicker):
    def __init__(self, buffers: list[str], encoding: str) -> None:
        super().__init__(buffers, encoding)
        self.written: defaultdict[tuple[str, str], set[str]] = defaultdict(set)

    def add_variable_annotation(self, name: str, annotation: AST) -> None:
        super().add_variable_annotation(name, annotation)
        if qualname := self.get_qualname_for(name):
            key = ".".join(qualname[:-1]), name
            self.written[key].add(self.annotations[key])


def names_read(source: str) -> Iterator[str]:  # pragma: >=3.14 cover
    """Yield the names the annotation `source` reads, none when it does not parse."""
    yield from _names_in(source)


@cache
def _names_in(source: str) -> tuple[str, ...]:  # pragma: >=3.14 cover
    try:
        # as annotationlib compiles `*Ts`, the starred annotation of `*args`
        tree = parse(f"({source},)[0]" if source.lstrip().startswith("*") else source, mode="eval")
    except SyntaxError:
        # the source prints a value it holds no code for, such as a lambda in `Annotated` metadata, by its repr
        return ()
    return tuple(node.id for node in walk(tree) if isinstance(node, Name))


def annotations_as_written(owner: Documented) -> dict[str, Annotation | str]:  # pragma: >=3.14 cover
    """
    Return the source of each annotation of `owner`, or its value where the source is gone.

    The values include what code added to the annotations after evaluating them, as attrs does for its fields.
    """
    try:
        stored = dict(getattr(owner, "__annotations__", None) or {})
    except NameError:
        # the values evaluate in the module globals, which lack a name only the `TYPE_CHECKING` block binds; that
        # leaves nothing cached for code to have added to
        stored = {}
    if getattr(owner, "__annotate__", None) is not None:
        return stored | get_annotations(owner, format=Format.STRING)
    if not holds_values(owner) or (tree := parsed_source(owner)) is None:
        return stored
    # inspect.getsource of a class starts at its class statement
    body = node.body if isinstance(owner, type) and isinstance(node := tree.body[0], ClassDef) else tree.body
    return stored | {
        statement.target.id: unparse(statement.annotation)
        for statement in body
        if isinstance(statement, AnnAssign) and isinstance(statement.target, Name)
    }


def holds_values(owner: Documented) -> bool:  # pragma: >=3.14 cover
    """
    Return whether autodoc replaced the lazy annotations of a module or class with their values.

    It does so to add the types its comments give, which drops the code that would evaluate them again.
    """
    return isinstance(owner, type | ModuleType) and any(
        not isinstance(value, str) for value in (getattr(owner, "__annotations__", None) or {}).values()
    )


__all__ = [
    "annotations_as_written",
    "function_annotations",
    "holds_values",
    "names_read",
    "parameters",
    "parsed_source",
    "source_annotations",
    "written_annotations",
]
