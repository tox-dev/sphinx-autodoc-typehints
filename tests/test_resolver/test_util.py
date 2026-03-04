from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, create_autospec, patch

from sphinx.environment import BuildEnvironment

from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef
from sphinx_autodoc_typehints._resolver._util import collect_documented_type_aliases, get_obj_location


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


def test_collect_documented_type_aliases_preserves_eager_path() -> None:
    env = _make_env_with_types(["mymod.MyAlias"])

    def func(x: int) -> str: ...

    func.__annotations__ = {"x": int}
    func.__globals__["MyAlias"] = int
    deferred, eager = collect_documented_type_aliases(func, "mymod", env)
    assert "MyAlias" in deferred
    assert id(int) in eager


def test_collect_documented_type_aliases_ignores_other_module_types() -> None:
    env = _make_env_with_types(["other.Foo"])
    obj = MagicMock(spec=[])
    deferred, eager = collect_documented_type_aliases(obj, "mymod", env)
    assert "Foo" not in deferred
    assert eager == {}


def test_collect_documented_type_aliases_ignores_unqualified_names() -> None:
    env = _make_env_with_types(["EncoderHook"])
    obj = MagicMock(spec=[])
    deferred, eager = collect_documented_type_aliases(obj, "cbor2", env)
    assert "EncoderHook" not in deferred
    assert eager == {}
