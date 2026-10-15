from __future__ import annotations

from functools import partial
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, fixture, mark, param

from sphinx_autodoc_typehints._resolve import resolve_overloads

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType


# the extension records the overloads the source declares while Sphinx analyzes it, once an application installed it
pytestmark: Final[list[MarkDecorator]] = [
    mark.sphinx("text", testroot="resolve-stubs"),
    mark.usefixtures("app"),
]


def test_resolve_overloads(overloaded: ModuleType) -> None:
    assert (signatures := resolve_overloads(overloaded.pick)) is not None
    assert [str(signature) for signature in signatures] == ["(value: 'int') -> 'int'", "(value: 'str') -> 'str'"]


@fixture(name="overloaded")
def overloaded_fixture(make_module: Callable[[str], ModuleType]) -> ModuleType:
    return make_module(
        dedent("""\
            from typing import overload

            @overload
            def pick(value: int) -> int: ...
            @overload
            def pick(value: str) -> str: ...
            def pick(value):
                return value

            def plain(value: int) -> int: ...
        """)
    )


@mark.parametrize(
    "owner",
    [
        param(lambda module: module.plain, id="no-overloads"),
        param(lambda _: partial(len), id="no-qualname"),
        param(lambda _: len, id="module-without-source"),
    ],
)
def test_resolve_overloads_without_overloads(
    overloaded: ModuleType, owner: Callable[[ModuleType], Callable[..., object]]
) -> None:
    assert resolve_overloads(owner(overloaded)) is None
