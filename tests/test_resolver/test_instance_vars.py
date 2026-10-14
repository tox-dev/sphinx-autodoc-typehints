from __future__ import annotations

import contextlib
import importlib
import sys
from typing import TYPE_CHECKING, Annotated, ClassVar, Final, Optional

import pytest
from conftest import make_docstring_app

from sphinx_autodoc_typehints import process_docstring
from sphinx_autodoc_typehints._resolver import resolve_type_guarded_imports
from sphinx_autodoc_typehints._resolver._instance_vars import get_class_body_annotations, get_instance_var_annotations

if TYPE_CHECKING:
    from pathlib import Path


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
            fake_self_attr: str = ""
            self.leaked: str = fake_self_attr

        inner()


class _ComplexTypes:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.mapping: dict[str, int] = {}
        self.maybe: Optional[int] = None


class _NoInit:
    pass


class _InBlocks:
    def __init__(self) -> None:
        with contextlib.nullcontext():
            self.label: str = ""
        try:
            self.port: int = 0
        finally:
            self.ready: bool = True
        if not self.port:
            self.flag: bool = True


class _PositionalOnlySelf:
    def __init__(self, /, size: int = 0) -> None:
        self.size: int = size


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
        pytest.param(
            type("Child", (_ComplexTypes,), {"__module__": "elsewhere"}),
            "maybe",
            Optional[int],
            id="inherited-from-another-module",
        ),
    ],
)
def test_complex_types(cls: type, attr: str, expected: object) -> None:
    cls()  # cover __init__
    result = get_instance_var_annotations(cls)
    assert result[attr] == expected


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        pytest.param(_InBlocks, {"label": str, "port": int, "ready": bool, "flag": bool}, id="inside-blocks"),
        pytest.param(_PositionalOnlySelf, {"size": int}, id="positional-only-self"),
    ],
)
def test_instance_vars_beyond_top_level_statements(cls: type, expected: dict[str, type]) -> None:
    cls()  # cover __init__
    assert get_instance_var_annotations(cls) == expected


@pytest.mark.parametrize(
    "cls",
    [
        pytest.param(_NoInit, id="no_init"),
        pytest.param(object, id="object_itself"),
    ],
)
def test_no_instance_vars(cls: type) -> None:
    assert get_instance_var_annotations(cls) == {}


class _Declared:
    plain: int
    shared: ClassVar[str] = ""
    fixed: Final[float] = 1.0
    bare: Final = 2


class _DeclaredChild(_Declared):
    extra: bytes


class _DeclaredBadly:
    broken: Undefined  # ruff:ignore[undefined-name]  # ty: ignore[unresolved-reference]  # the case under test


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        pytest.param(_Declared, {"plain": int, "shared": str, "fixed": float}, id="qualifiers-unwrapped"),
        pytest.param(
            _DeclaredChild, {"plain": int, "shared": str, "fixed": float, "extra": bytes}, id="through-the-bases"
        ),
        pytest.param(_DeclaredBadly, {}, id="unresolvable"),
        pytest.param(_NoAnnotations, {}, id="none"),
    ],
)
def test_class_body_annotations(cls: type, expected: dict[str, type]) -> None:
    assert get_class_body_annotations(cls) == expected


class _Model:
    name: Annotated[str, {"max_length": 10}] = ""


def test_class_body_annotation_with_unhashable_metadata() -> None:
    lines = [":ivar name: the name"]
    process_docstring(make_docstring_app(), "class", "mod._Model", _Model, None, lines)
    assert lines == [r":vartype name: :sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``", ":ivar name: the name"]


def test_class_body_annotation_documents_the_guarded_type_over_its_runtime_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "guarded_fallback_body.py").write_text(
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from decimal import Decimal\n"
        "else:\n"
        "    Decimal = float\n"
        "\n"
        "class Holder:\n"
        "    Unit = int\n"
        "    amount: Decimal\n"
        "    unit: Unit\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    holder = importlib.import_module("guarded_fallback_body").Holder
    lines = [":ivar amount: the amount", ":ivar unit: the unit"]
    process_docstring(make_docstring_app(), "class", "guarded_fallback_body.Holder", holder, None, lines)
    assert lines == [
        r":vartype amount: :sphinx_autodoc_typehints_type:`\:py\:class\:\`\~decimal.Decimal\``",
        ":ivar amount: the amount",
        r":vartype unit: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        ":ivar unit: the unit",
    ]


@pytest.mark.skipif(sys.version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_lazy_class_body_annotation_documents_the_guarded_type(  # pragma: >=3.14 cover
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "lazy_guarded_body.py").write_text(
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from decimal import Decimal\n"
        "else:\n"
        "    Decimal = float\n"
        "\n"
        "class Holder:\n"
        "    amount: Decimal\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    holder = importlib.import_module("lazy_guarded_body").Holder
    lines = [":ivar amount: the amount"]
    process_docstring(make_docstring_app(), "class", "lazy_guarded_body.Holder", holder, None, lines)
    assert lines == [
        r":vartype amount: :sphinx_autodoc_typehints_type:`\:py\:class\:\`\~decimal.Decimal\``",
        ":ivar amount: the amount",
    ]


@pytest.mark.skipif(sys.version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_lazy_class_body_annotation_of_a_base_reads_the_guard_of_its_module(  # pragma: >=3.14 cover
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "lazy_guarded_parent.py").write_text(
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from decimal import Decimal\n"
        "else:\n"
        "    Decimal = float\n"
        "\n"
        "class Base:\n"
        "    amount: Decimal\n"
    )
    (tmp_path / "lazy_plain_child.py").write_text("from lazy_guarded_parent import Base\n\nclass Child(Base): ...\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    resolve_type_guarded_imports([], importlib.import_module("lazy_guarded_parent"))
    child = importlib.import_module("lazy_plain_child").Child
    lines = [":ivar amount: the amount"]
    process_docstring(make_docstring_app(), "class", "lazy_plain_child.Child", child, None, lines)
    assert lines == [
        r":vartype amount: :sphinx_autodoc_typehints_type:`\:py\:class\:\`\~decimal.Decimal\``",
        ":ivar amount: the amount",
    ]
