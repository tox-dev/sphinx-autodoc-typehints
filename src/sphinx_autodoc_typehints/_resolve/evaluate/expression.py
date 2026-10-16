"""
Evaluates an annotation written as source, keeping the arguments a class drops on subscription.

It reads `X | Y` as a union when the operands are mocks that do not support `|`.
"""

from __future__ import annotations

__lazy_modules__ = [
    "annotationlib",
    "sphinx",
    "sphinx.util",
    "sphinx_autodoc_typehints._resolve.guards",
    "sphinx_autodoc_typehints._resolve.source",
    "types",
]

from ast import (
    BinOp,
    BitOr,
    Call,
    Load,
    Name,
    NodeTransformer,
    Slice,
    Subscript,
    Tuple,
    expr,
    fix_missing_locations,
    parse,
)
from sys import modules, version_info
from types import GenericAlias
from typing import TYPE_CHECKING, Final, ForwardRef, Union

from sphinx.util import logging

from sphinx_autodoc_typehints._resolve.guards import annotation_globals, guarded_names
from sphinx_autodoc_typehints._resolve.source import names_read

if version_info >= (3, 14):  # pragma: >=3.14 cover
    from annotationlib import Format, ForwardRef, get_annotations

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx_autodoc_typehints._resolve.generics import Subscriptable
    from sphinx_autodoc_typehints._types import Annotation, Documented, Hint


_UNION: Final[str] = "__sphinx_autodoc_typehints_union__"
_SUBSCRIPT: Final[str] = "__sphinx_autodoc_typehints_subscript__"


def resolve_string_annotations(
    obj: Documented,
    hints: Mapping[str, Hint],
    localns: Mapping[str, Documented],
    owner_module: str = "",
) -> dict[str, Hint]:
    """
    Return `hints` with each string or `ForwardRef` among them evaluated, left as it is where that fails.

    The globals are those of `owner_module` when it names an imported module, else those of the module defining
    `obj`, which a re-export does not change.
    """
    # the __module__ of a C extension function may name a child (cbor2._cbor2) of the package its stub describes
    # (cbor2/__init__.pyi); the module defining obj is the one the evaluation that failed before this one used
    globalns = vars(modules[owner_module]) if owner_module in modules else annotation_globals(obj)
    resolved: dict[str, Hint] = {}
    for name, value in hints.items():
        resolved[name] = value
        # Python 3.14 hands back an annotation it could not evaluate as a ForwardRef holding its source
        source = value.__forward_arg__ if type(value) is ForwardRef else value
        # a quoted annotation evaluates to the string inside it, which takes a second pass
        for _ in range(2):
            if not isinstance(source, str):
                break
            try:
                resolved[name] = source = evaluate_annotation(source, globalns, localns)
            except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
                logging.getLogger(__name__).debug(
                    "Failed to resolve annotation %r=%r for %s", name, source, getattr(obj, "__qualname__", "?")
                )
                break
    return resolved


def evaluate_annotation(
    source: str, globalns: Mapping[str, Documented], localns: Mapping[str, Documented]
) -> Annotation:
    """Evaluate an annotation written as `source`, keeping the arguments a class subscripted in it drops."""
    tree = _KeepArguments().visit(parse(source, mode="eval"))
    # a nested scope, such as a generator expression or a lambda, reads the globals but not the locals, so the helpers
    # go in a copy of the globals, which leaves those of the module untouched
    namespace = {**globalns, _SUBSCRIPT: _subscript}
    try:
        code = compile(fix_missing_locations(tree), "<annotation>", "eval")
        return eval(code, namespace, localns)  # ruff:ignore[suspicious-eval-usage]  # the annotation is code to run
    except TypeError:
        # X | Y means Union[X, Y], which also accepts operands that don't support |, such as the objects
        # autodoc_mock_imports puts in place of a missing module's
        code = compile(fix_missing_locations(_PipeAsUnion().visit(tree)), "<annotation>", "eval")
        namespace[_UNION] = Union
        return eval(code, namespace, localns)  # ruff:ignore[suspicious-eval-usage]  # the annotation is code to run


class _KeepArguments(NodeTransformer):
    def visit_Subscript(self, node: Subscript) -> expr:
        self.generic_visit(node)
        # a call takes no slice as an argument
        if any(isinstance(item, Slice) for item in (node.slice, *getattr(node.slice, "elts", ()))):
            return node
        return Call(func=Name(id=_SUBSCRIPT, ctx=Load()), args=[node.value, node.slice], keywords=[])


def _subscript(value: Subscriptable, item: object) -> Annotation | GenericAlias:
    # a generic alias renders as the subscription written, and links the class
    return (
        GenericAlias(value, item) if (subscripted := value[item]) is value and isinstance(value, type) else subscripted
    )


class _PipeAsUnion(NodeTransformer):
    def visit_BinOp(self, node: BinOp) -> expr:
        self.generic_visit(node)
        if not isinstance(node.op, BitOr):
            return node
        members = Tuple(elts=[node.left, node.right], ctx=Load())
        return Subscript(value=Name(id=_UNION, ctx=Load()), slice=members, ctx=Load())


def unevaluated_annotations(obj: Documented) -> dict[str, Hint]:
    """Return the annotations of `obj` without evaluating them, empty when reading them fails."""
    if version_info < (3, 14):  # pragma: <3.14 cover
        return getattr(obj, "__annotations__", {})
    # ForwardRef proxies keep unevaluatable annotations renderable as their source text (#712)
    try:  # pragma: >=3.14 cover
        unevaluated = get_annotations(obj, format=Format.FORWARDREF)
        if getattr(obj, "__annotate__", None) is None or not (shadowed := guarded_names(obj)):
            return unevaluated
        # FORWARDREF evaluates in the globals of the code defining the annotation, which hold the runtime binding of a
        # name the guard shadows, so such an annotation stays its source, for a later pass to read the guarded names
        return unevaluated | {
            name: ForwardRef(source)
            for name, source in get_annotations(obj, format=Format.STRING).items()
            if not shadowed.keys().isdisjoint(names_read(source))
        }
    except Exception:  # pragma: >=3.14 cover  # ruff:ignore[blind-except]  # an annotation runs user code
        return {}


__all__ = [
    "evaluate_annotation",
    "resolve_string_annotations",
    "unevaluated_annotations",
]
