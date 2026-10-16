from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import fixture, mark, param

from sphinx_autodoc_typehints._objects import callable_target, constructor_name, get_obj_location

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from types import ModuleType

    from conftest import MakeModule

    from sphinx_autodoc_typehints._types import Documented


@mark.parametrize(
    ("name", "line"),
    [
        param("func", 1, id="function"),
        param("Klass", 4, id="class"),
    ],
)
def test_get_obj_location_points_at_the_definition(located: ModuleType, tmp_path: Path, name: str, line: int) -> None:
    assert get_obj_location(getattr(located, name)) == f"{tmp_path / 'located.py'}:{line}"


@fixture(name="located")
def located_fixture(make_module: MakeModule) -> ModuleType:
    return make_module(
        "located",
        dedent("""\
            def func() -> None: ...


            class Klass: ...
        """),
    )


def test_get_obj_location_without_the_source_is_the_file(located: ModuleType, tmp_path: Path) -> None:
    (source := tmp_path / "located.py").unlink()
    assert get_obj_location(located.func) == str(source)


@mark.parametrize(
    "obj",
    [
        param(42, id="value"),
        param(int, id="built-in-class"),
    ],
)
def test_get_obj_location_without_a_source_file_is_none(obj: Documented) -> None:
    assert get_obj_location(obj) is None


def test_get_obj_location_of_generated_code_is_none() -> None:
    @dataclass
    class Generated:
        value: int

    assert get_obj_location(Generated.__init__) is None


# a mock answers every __wrapped__ with another mock, which unwrapping past it follows to the recursion limit
def test_callable_target_of_a_mock_is_none(mocked_object: Callable[..., object]) -> None:
    assert callable_target(mocked_object) is None


def test_constructor_name_of_a_new_a_mock_decorates_is_new(mocked_object: Callable[..., object]) -> None:
    assert constructor_name(type("Made", (), {"__new__": mocked_object})) == "__new__"
