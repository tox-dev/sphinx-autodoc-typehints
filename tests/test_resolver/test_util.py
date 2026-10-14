from __future__ import annotations

import dataclasses
import importlib
import re
from operator import attrgetter
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from sphinx.environment import BuildEnvironment

from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef
from sphinx_autodoc_typehints._resolver._util import collect_documented_type_aliases, get_obj_location

if TYPE_CHECKING:
    from pathlib import Path


def _typed_func(x: int, y: str) -> bool: ...


class _BackfillClass:
    def method(self, x: int) -> str: ...


def test_get_obj_location_with_function() -> None:
    location = get_obj_location(_typed_func)
    assert location is not None
    assert location.endswith(".py:" + str(_typed_func.__code__.co_firstlineno))
    assert "test_util.py" in location


def test_get_obj_location_with_class() -> None:
    location = get_obj_location(_BackfillClass)
    assert location is not None
    assert "test_util.py" in location


def test_get_obj_location_non_inspectable() -> None:
    assert get_obj_location(42) is None


def test_get_obj_location_of_generated_code() -> None:
    @dataclasses.dataclass
    class Generated:
        value: int

    assert get_obj_location(Generated.__init__) is None


def test_get_obj_location_no_source_lines() -> None:
    with patch("sphinx_autodoc_typehints._resolver._util.inspect.getsourcelines", side_effect=OSError):
        location = get_obj_location(_typed_func)
    assert location is not None
    assert location.endswith(".py")
    assert ":" not in location.rsplit("/", 1)[-1]


def _make_env_with_types(type_names: list[str]) -> Any:
    obj_info = MagicMock()
    obj_info.objtype = "type"
    py_objects = dict.fromkeys(type_names, obj_info)
    domain = MagicMock()
    domain.objects = py_objects
    env = create_autospec(BuildEnvironment, instance=True)
    env.get_domain.return_value = domain
    return env


def test_collect_documented_type_aliases_no_annotations() -> None:
    env = _make_env_with_types(["mymod.EncoderHook", "mymod.TagHook"])
    obj = MagicMock(spec=[])
    deferred, eager = collect_documented_type_aliases(obj, "mymod", env)
    assert "EncoderHook" in deferred
    assert "TagHook" in deferred
    assert isinstance(deferred["EncoderHook"], MyTypeAliasForwardRef)
    assert eager == {}


@pytest.mark.parametrize(
    "attr",
    [
        pytest.param("func", id="written-as-the-type"),
        pytest.param("lam", id="lambda"),
        pytest.param("Point.__init__", id="generated-without-source"),
    ],
)
def test_collect_documented_type_aliases_ignores_annotations_not_written_as_the_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest, attr: str
) -> None:
    name = re.sub(r"\W", "_", request.node.name)
    (tmp_path / f"{name}.py").write_text(
        "from dataclasses import dataclass\n\n"
        "MyAlias = int\n\n\n"
        "def func(x: int) -> None: ...\n\n\n"
        "lam = lambda x: None\n"
        "lam.__annotations__ = {'x': int}\n\n\n"
        "@dataclass\n"
        "class Point:\n"
        "    x: int\n"
    )
    monkeypatch.syspath_prepend(tmp_path)
    obj = attrgetter(attr)(importlib.import_module(name))
    _, eager = collect_documented_type_aliases(obj, name, _make_env_with_types([f"{name}.MyAlias"]))
    assert eager == {}


@pytest.mark.parametrize(
    "documented",
    [pytest.param("other.Foo", id="other-module"), pytest.param("mymod.sub.Foo", id="submodule")],
)
def test_collect_documented_type_aliases_ignores_other_module_types(documented: str) -> None:
    env = _make_env_with_types([documented])
    obj = MagicMock(spec=[])
    deferred, eager = collect_documented_type_aliases(obj, "mymod", env)
    assert "Foo" not in deferred
    assert eager == {}


@pytest.mark.parametrize(
    "documented",
    [pytest.param("am.Vector", id="module"), pytest.param("am.Ops.Vector", id="class-body")],
)
def test_collect_documented_type_aliases_sees_the_scopes_around_a_method(documented: str) -> None:
    deferred, _ = collect_documented_type_aliases(MagicMock(spec=[]), "am.Ops", _make_env_with_types([documented]))
    assert list(deferred) == ["Vector"]


def test_collect_documented_type_aliases_ignores_unqualified_names() -> None:
    env = _make_env_with_types(["EncoderHook"])
    obj = MagicMock(spec=[])
    deferred, eager = collect_documented_type_aliases(obj, "cbor2", env)
    assert "EncoderHook" not in deferred
    assert eager == {}


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(NameError("Callable"), id="name-error"),
        pytest.param(TypeError("type 'DiGraph' is not subscriptable"), id="type-error"),
    ],
)
def test_collect_documented_type_aliases_annotations_error(error: Exception) -> None:
    """PEP 649 lazy annotation evaluation raising (NameError for TYPE_CHECKING-only names, TypeError
    for subscripting a non-generic class) must not propagate (issue #712)."""

    class _AnnotationsRaiser:
        @property
        def __annotations__(self) -> dict[str, object]:  # ruff:ignore[bad-dunder-method-name]
            raise error

    env = _make_env_with_types(["mymod.MyType"])
    deferred, eager = collect_documented_type_aliases(_AnnotationsRaiser(), "mymod", env)
    assert "MyType" in deferred
    assert eager == {}
