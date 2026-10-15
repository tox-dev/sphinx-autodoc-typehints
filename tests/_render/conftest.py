from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Protocol

from pytest import fixture
from sphinx.config import Config
from sphinx.ext.autodoc.mock import mock

from sphinx_autodoc_typehints._config import OPTIONS

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from sphinx_autodoc_typehints._render.context import TypehintsFormatter


class MakeConfig(Protocol):
    def __call__(self, **overrides: bool | TypehintsFormatter | Callable[[str], str]) -> Config: ...


@fixture
def config(make_config: MakeConfig) -> Config:
    return make_config()


@fixture(name="make_config")
def make_config_fixture() -> MakeConfig:
    def make(**overrides: bool | TypehintsFormatter | Callable[[str], str]) -> Config:
        made = Config(overrides)
        for option in OPTIONS:
            made.add(option.name, option.default, option.rebuild, option.types)
        # autodoc and the Python domain register these in a build, and the extension reads them
        made.add("autodoc_typehints_format", "short", "env", ())
        made.add("python_display_short_literal_types", False, "env", ())
        made.init_values()
        return made

    return make


@fixture
def mocked_module() -> ModuleType:
    with mock(["mockedpkg"]):
        return import_module("mockedpkg.sub")


__all__ = [
    "MakeConfig",
]
