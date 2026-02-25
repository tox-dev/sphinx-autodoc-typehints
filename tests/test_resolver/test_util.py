from __future__ import annotations

from unittest.mock import patch

from sphinx_autodoc_typehints._resolver._util import get_obj_location


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
