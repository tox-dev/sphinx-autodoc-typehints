from __future__ import annotations

from typing import Optional

import pytest

from sphinx_autodoc_typehints._resolver._instance_vars import get_instance_var_annotations


class _Simple:
    def __init__(self, bar: str = "baz") -> None:
        self.bar: str = bar


class _Multi:
    def __init__(self) -> None:
        self.x: int = 0
        self.y: str = ""
        self.z: float = 0.0


class _NoAnnotations:
    def __init__(self) -> None:
        self.x = 0


class _NestedFunction:
    def __init__(self) -> None:
        self.outer: int = 0

        def inner() -> None:
            fake_self_attr: str = ""  # noqa: F841

        inner()


class _ComplexTypes:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.mapping: dict[str, int] = {}
        self.maybe: Optional[int] = None


class _NoInit:
    pass


def test_basic_instance_var() -> None:
    assert _Simple().bar == "baz"
    assert get_instance_var_annotations(_Simple) == {"bar": str}


def test_multiple_instance_vars() -> None:
    assert _Multi().x == 0
    assert get_instance_var_annotations(_Multi) == {"x": int, "y": str, "z": float}


def test_no_annotations_in_init() -> None:
    assert _NoAnnotations().x == 0
    assert get_instance_var_annotations(_NoAnnotations) == {}


def test_nested_function_annotations_ignored() -> None:
    assert _NestedFunction().outer == 0
    result = get_instance_var_annotations(_NestedFunction)
    assert result == {"outer": int}
    assert "fake_self_attr" not in result


@pytest.mark.parametrize(
    ("cls", "attr", "expected"),
    [
        pytest.param(_ComplexTypes, "items", list[str], id="list"),
        pytest.param(_ComplexTypes, "mapping", dict[str, int], id="dict"),
        pytest.param(_ComplexTypes, "maybe", Optional[int], id="optional"),
    ],
)
def test_complex_types(cls: type, attr: str, expected: object) -> None:
    cls()  # cover __init__
    result = get_instance_var_annotations(cls)
    assert result[attr] == expected


@pytest.mark.parametrize(
    "cls",
    [
        pytest.param(_NoInit, id="no_init"),
        pytest.param(object, id="object_itself"),
    ],
)
def test_no_instance_vars(cls: type) -> None:
    assert get_instance_var_annotations(cls) == {}
