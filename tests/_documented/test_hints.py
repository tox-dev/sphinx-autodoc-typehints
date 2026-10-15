from __future__ import annotations

from inspect import Parameter, Signature
from sys import version_info
from textwrap import dedent
from typing import TYPE_CHECKING, Final, NamedTuple

from pytest import MarkDecorator, mark, param
from sphinx.util.console import strip_colors

from sphinx_autodoc_typehints._documented import ResolvedHints, as_written, documenting_class, resolved_type_hints
from sphinx_autodoc_typehints._refs import WrittenTypeAlias

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp

    from sphinx_autodoc_typehints._objects import QualifiedCallable
    from sphinx_autodoc_typehints._types import Annotation, Documented

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


def _convert(value: int) -> str: ...


class _Box[Item]:
    def get(self) -> Item: ...


class _IntBox(_Box[int]): ...


class _Pair(NamedTuple):
    left: int
    right: _Pair | None


class _StatesSignature:
    __signature__ = Signature([Parameter("value", Parameter.KEYWORD_ONLY, annotation=float)], return_annotation=str)

    def __init__(self, **data: float) -> None: ...


@mark.parametrize(
    ("name", "original", "obj", "expected"),
    [
        param(
            "mod._convert",
            _convert,
            _convert,
            ResolvedHints(
                types={"value": int, "return": str}, written_as={}, scope={"declared_type_params": frozenset()}
            ),
            id="function",
        ),
        param(
            f"{__name__}._IntBox.get",
            _Box.get,
            _Box.get,
            ResolvedHints(
                types={"return": int}, written_as={}, scope={"declared_type_params": frozenset(_Box.__type_params__)}
            ),
            id="bound-by-the-documenting-subclass",
        ),
        param(
            "mod._Pair",
            _Pair,
            _Pair.__new__,
            ResolvedHints(
                types={"left": int, "right": _Pair | None}, written_as={}, scope={"declared_type_params": frozenset()}
            ),
            id="namedtuple-constructor",
        ),
        param(
            "mod._StatesSignature",
            _StatesSignature,
            _StatesSignature.__init__,
            ResolvedHints(
                types={"data": float, "return": str, "value": float},
                written_as={},
                scope={"declared_type_params": frozenset()},
            ),
            id="stated-signature",
        ),
    ],
)
def test_resolved_type_hints(
    app: SphinxTestApp, name: str, original: Callable[..., object], obj: QualifiedCallable, expected: ResolvedHints
) -> None:
    assert resolved_type_hints(app, name, original, obj, obj) == expected


@mark.parametrize(
    ("name", "documented", "expected"),
    [
        param("mod._Box", _Box, (_Box, "__init__"), id="class-by-its-constructor"),
        param(f"{__name__}._IntBox.get", _Box.get, (_IntBox, "get"), id="member-by-the-listing-class"),
        param("not_imported._Box.get", _Box.get, (None, "get"), id="owner-missing"),
    ],
)
def test_documenting_class(name: str, documented: Documented, expected: tuple[Documented, str]) -> None:
    assert documenting_class(name, documented) == expected


_WRITTEN: Final[WrittenTypeAlias] = WrittenTypeAlias("Count", int)


@mark.parametrize(
    ("hint", "written", "expected"),
    [
        param(int, _WRITTEN, _WRITTEN, id="alias-holds-the-hint"),
        param(str, _WRITTEN, str, id="alias-holds-another"),
        param(int, None, int, id="no-alias"),
    ],
)
def test_as_written(
    hint: Annotation, written: WrittenTypeAlias | None, expected: Annotation | WrittenTypeAlias
) -> None:
    assert as_written(hint, written) is expected


@mark.parametrize(
    ("rst", "expected", "warnings"),
    [
        param(
            dedent("""\
                .. autoclass:: dummy_module.MyNamedTuple
                   :special-members: __new__
            """),
            dedent("""\
                class dummy_module.MyNamedTuple(x, y='hello')

                   A named tuple.

                   static __new__(_cls, x, y='hello')

                      Create new instance of MyNamedTuple(x, y)
            """),
            # namedtuple defines the __new__ it generates in globals without builtins, where before Python 3.14 the
            # string annotation naming int fails to evaluate
            []
            if version_info >= (3, 14)
            else [
                (
                    "WARNING: Cannot resolve forward reference in type annotations of "
                    "\"dummy_module.MyNamedTuple.__new__\" (module namedtuple_MyNamedTuple): name 'int' is not defined "
                    "[sphinx_autodoc_typehints.forward_reference]"
                )
            ],
            id="constructor",
        ),
        param(
            dedent("""\
                .. autoclass:: dummy_module.MyNamedTupleWithPath
                   :undoc-members:
            """),
            dedent("""\
                class dummy_module.MyNamedTupleWithPath(path, version)

                   A named tuple with non-builtin types.
            """),
            [],
            id="field-naming-a-type-of-another-module",
        ),
    ],
)
def test_resolved_type_hints_of_a_namedtuple(
    build_text: BuildText, warning: StringIO, rst: str, expected: str, warnings: list[str]
) -> None:
    assert (build_text(rst), strip_colors(warning.getvalue()).splitlines()) == (expected, warnings)
