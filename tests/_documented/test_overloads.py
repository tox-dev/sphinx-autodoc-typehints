from __future__ import annotations

from textwrap import dedent
from types import FunctionType
from typing import TYPE_CHECKING, Final, get_overloads, overload

from pytest import MarkDecorator, mark, param

from sphinx_autodoc_typehints._documented import typed_overloads
from sphinx_autodoc_typehints._render import render_context
from sphinx_autodoc_typehints._resolve import resolve_overloads

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp

    from sphinx_autodoc_typehints._types import Annotation, TypeParam

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


@overload
def _pick(value: int) -> int: ...


@overload
def _pick(value: str) -> str: ...


def _pick(value: int | str) -> int | str: ...


class _Box[Item]:
    @overload
    def get(self, key: int) -> Item: ...

    @overload
    def get(self, key: str) -> list[Item]: ...

    def get(self, key: int | str) -> Item | list[Item]: ...


@overload
def _wrap[Item](value: Item) -> list[Item]: ...


@overload
def _wrap(value: None) -> None: ...


def _wrap[Item](value: Item | None) -> list[Item] | None: ...


if TYPE_CHECKING:

    @overload
    def _guarded[Item](value: Item) -> list[Item]: ...

    @overload
    def _guarded(value: None) -> None: ...


def _guarded[Item](value: Item | None) -> list[Item] | None: ...


@mark.parametrize(
    ("name", "target", "skip", "arguments", "expected"),
    [
        param(
            "_pick",
            _pick,
            0,
            {},
            [(["value"], {"value": int, "return": int}), (["value"], {"value": str, "return": str})],
            id="function",
        ),
        param(
            "_Box.get",
            _Box.get,
            1,
            dict.fromkeys(_Box.__type_params__, int),
            [(["key"], {"key": int, "return": int}), (["key"], {"key": str, "return": list[int]})],
            id="method-past-self-with-bound-arguments",
        ),
    ],
)
def test_typed_overloads_types_each_overload(
    app: SphinxTestApp,
    name: str,
    target: Callable[..., object],
    skip: int,
    arguments: dict[TypeParam, Annotation],
    expected: list[tuple[list[str], dict[str, Annotation]]],
) -> None:
    overloads = resolve_overloads(target)
    assert overloads is not None
    typed = typed_overloads(app, f"{__name__}.{name}", target, overloads, skip, arguments)
    assert [([parameter.name for parameter in params], hints) for params, hints in typed] == expected


@mark.parametrize(
    ("name", "target", "expected"),
    [
        param(
            "_wrap",
            _wrap,
            [
                frozenset(
                    next(func.__type_params__ for func in get_overloads(_wrap) if isinstance(func, FunctionType))
                ),
                frozenset(),
            ],
            id="registered",
        ),
        # typing registers no overload a TYPE_CHECKING block keeps from running
        param("_guarded", _guarded, [frozenset(), frozenset()], id="unregistered"),
    ],
)
def test_typed_overloads_declares_the_type_params_of_each_overload(
    app: SphinxTestApp, name: str, target: Callable[..., object], expected: list[frozenset[TypeParam]]
) -> None:
    overloads = resolve_overloads(target)
    assert overloads is not None
    typed = typed_overloads(app, f"{__name__}.{name}", target, overloads, 0, {})
    assert [render_context(app.config).declared_type_params for _ in typed] == expected


@mark.sphinx(
    "text",
    testroot="integration",
    confoverrides={"typehints_use_signature": True, "typehints_use_signature_return": True},
)
def test_typed_overloads_name_an_alias_in_the_signature(build_text: BuildText) -> None:
    assert build_text(
        dedent("""\
            .. py:type:: mod_eager.Count

            .. autofunction:: mod_eager.scale
        """)
    ) == dedent("""\
        type mod_eager.Count

        mod_eager.scale(amount: Count) -> Count
        mod_eager.scale(amount: str) -> str

           Scale an amount.

           Parameters:
              **amount** ("int" | "str") -- The amount
        """)
