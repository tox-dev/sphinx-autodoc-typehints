from __future__ import annotations

from dataclasses import field as dataclass_field
from dataclasses import make_dataclass
from functools import partial
from inspect import signature

from attrs import Factory, field, make_class
from pytest import mark, param

from sphinx_autodoc_typehints._documented import show_factory_defaults


class _Thing: ...


def _make() -> list[int]: ...


def _from_self(instance: _Thing) -> list[int]: ...


@mark.parametrize(
    ("declared", "expected"),
    [
        param(dataclass_field(default_factory=list), "(value: list[int] = list()) -> None", id="builtin"),
        param(dataclass_field(default_factory=_Thing), "(value: list[int] = _Thing()) -> None", id="class"),
        param(dataclass_field(default_factory=_make), "(value: list[int] = _make()) -> None", id="function"),
        param(dataclass_field(default_factory=lambda: [1, 2]), "(value: list[int] = <factory>) -> None", id="lambda"),
        param(
            dataclass_field(default_factory=partial(list, (1,))),
            "(value: list[int] = <factory>) -> None",
            id="partial",
        ),
        param(dataclass_field(default=None), "(value: list[int] = None) -> None", id="plain-default"),
    ],
)
def test_show_factory_defaults_of_a_dataclass(declared: list[int] | _Thing | None, expected: str) -> None:
    made = make_dataclass("Made", [("value", list[int], declared)])
    assert str(show_factory_defaults(made, signature(made))) == expected


@mark.parametrize(
    ("name", "default", "expected"),
    [
        param("value", Factory(list), "(value: list[int] = list()) -> None", id="factory"),
        param(
            "value",
            Factory(_from_self, takes_self=True),
            "(value: list[int] = _from_self(self)) -> None",
            id="takes-self",
        ),
        param("value", Factory(lambda: [1]), "(value: list[int] = <factory>) -> None", id="lambda"),
        param("_value", Factory(list), "(value: list[int] = list()) -> None", id="private-name"),
        param("value", [], "(value: list[int] = []) -> None", id="plain-default"),
    ],
)
def test_show_factory_defaults_of_an_attrs_class(name: str, default: list[int], expected: str) -> None:
    made = make_class("Made", {name: field(default=default, type=list[int])})
    assert str(show_factory_defaults(made, signature(made))) == expected
