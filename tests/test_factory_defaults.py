from __future__ import annotations

import dataclasses
import functools
from typing import TYPE_CHECKING, Any

import attrs
import pytest
from conftest import make_docstring_app, make_sig_app
from sphinx.ext.autodoc import Options

from sphinx_autodoc_typehints import process_docstring, process_signature

if TYPE_CHECKING:
    from collections.abc import Callable


class _Thing: ...


def _make() -> list[int]: ...
def _from_self(instance: object) -> list[object]: ...


def _with_factory(factory: Callable[[], Any]) -> type:
    return dataclasses.make_dataclass("Made", [("value", list[int], dataclasses.field(default_factory=factory))])


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        pytest.param(list, "(value=list())", id="builtin"),
        pytest.param(_Thing, "(value=_Thing())", id="class"),
        pytest.param(_make, "(value=_make())", id="function"),
    ],
)
def test_process_signature_shows_a_dataclass_factory_as_its_call(factory: Callable[[], Any], expected: str) -> None:
    result = process_signature(make_sig_app(), "class", "mod.Made", _with_factory(factory), Options(), "", "")
    assert result == (expected, None)


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(lambda: [1, 2], id="lambda"),
        pytest.param(functools.partial(list, (1,)), id="partial"),
    ],
)
def test_process_signature_keeps_the_placeholder_of_a_nameless_dataclass_factory(factory: Callable[[], Any]) -> None:
    made = dataclasses.make_dataclass(
        "Made",
        [
            ("named", list[int], dataclasses.field(default_factory=list)),
            ("nameless", list[int], dataclasses.field(default_factory=factory)),
        ],
    )
    result = process_signature(make_sig_app(), "class", "mod.Made", made, Options(), "", "")
    assert result == ("(named=list(), nameless=<factory>)", None)


def test_process_docstring_shows_a_dataclass_factory_as_its_call() -> None:
    lines = [":param value: the value"]
    app = make_docstring_app(typehints_defaults="comma")
    process_docstring(app, "class", "mod.Made", _with_factory(list), None, lines)
    assert lines == [
        (
            r":type value: :sphinx_autodoc_typehints_type:`\:py\:class\:\`list\`\\ \\\[\:py\:class\:\`int\`\]`, "
            "default: ``list()``"
        ),
        ":param value: the value",
    ]


@pytest.mark.parametrize(
    ("name", "factory", "takes_self", "expected"),
    [
        pytest.param("value", list, False, "(value=list())", id="factory"),
        pytest.param("value", _from_self, True, "(value=_from_self(self))", id="takes-self"),
        pytest.param("value", lambda: [1], False, "(value=<factory>)", id="lambda"),
        pytest.param("_value", list, False, "(value=list())", id="private-name"),
    ],
)
def test_process_signature_shows_an_attrs_factory_as_its_call(
    name: str, factory: Callable[..., list[object]], takes_self: bool, expected: str
) -> None:
    default = attrs.Factory(factory, takes_self=takes_self)
    made = attrs.make_class("Made", {name: attrs.field(default=default, type=list[int])})
    assert process_signature(make_sig_app(), "class", "mod.Made", made, Options(), "", "") == (expected, None)
