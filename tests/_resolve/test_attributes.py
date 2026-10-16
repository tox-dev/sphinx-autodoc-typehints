from __future__ import annotations

from decimal import Decimal
from operator import attrgetter
from textwrap import dedent
from typing import TYPE_CHECKING, Annotated, Optional

from pytest import fixture, mark, param

from sphinx_autodoc_typehints._resolve import (
    get_body_annotations,
    get_instance_var_annotations,
    resolve_type_guarded_imports,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from _resolve.conftest import MakeSubclassOfAGuardedBase
    from sphinx_autodoc_typehints._types import Annotation


@mark.parametrize(
    ("owner", "expected"),
    [
        param(attrgetter("Simple"), {"bar": str}, id="one"),
        param(attrgetter("Multi"), {"x": int, "y": str, "z": float}, id="several"),
        param(attrgetter("NoAnnotations"), {}, id="unannotated"),
        param(attrgetter("NestedFunction"), {"outer": int}, id="nested-scopes-left-out"),
        param(
            attrgetter("ComplexTypes"),
            {"items": list[str], "mapping": dict[str, int], "maybe": Optional[int]},
            id="generics",
        ),
        param(
            attrgetter("Inherited"),
            {"items": list[str], "mapping": dict[str, int], "maybe": Optional[int]},
            id="inherited-from-another-module",
        ),
        param(attrgetter("InBlocks"), {"label": str, "port": int, "ready": bool, "flag": bool}, id="inside-blocks"),
        param(attrgetter("PositionalOnlySelf"), {"size": int}, id="positional-only-self"),
        param(attrgetter("NoSelf"), {}, id="no-self-parameter"),
        param(attrgetter("Unresolvable"), {"broken": "Undefined"}, id="unresolvable-kept-as-written"),
        param(attrgetter("NoInit"), {}, id="no-init"),
        param(attrgetter("Generated"), {}, id="init-without-a-def"),
        param(lambda _: object, {}, id="object"),
    ],
)
def test_get_instance_var_annotations(
    instance_module: ModuleType, owner: Callable[[ModuleType], type], expected: dict[str, Annotation | str]
) -> None:
    assert get_instance_var_annotations(owner(instance_module)) == expected


@fixture(name="instance_module")
def instance_module_fixture(make_module: Callable[[str], ModuleType]) -> ModuleType:
    return make_module(
        dedent("""\
            import contextlib
            from typing import Optional

            class Simple:
                def __init__(self, bar: str = "baz") -> None:
                    self.bar: str = bar

            class Multi:
                def __init__(self) -> None:
                    self.x: int = 0
                    self.y: str = ""
                    self.z: float = 0.0

            class NoAnnotations:
                def __init__(self) -> None:
                    self.x = 0

            class NestedFunction:
                def __init__(self) -> None:
                    self.outer: int = 0

                    def inner() -> None:
                        fake_self_attr: str = ""
                        self.leaked: str = fake_self_attr

                    class Inner:
                        def __init__(inner_self) -> None:
                            inner_self.hidden: str = ""

            class ComplexTypes:
                def __init__(self) -> None:
                    self.items: list[str] = []
                    self.mapping: dict[str, int] = {}
                    self.maybe: Optional[int] = None

            Inherited = type("Inherited", (ComplexTypes,), {"__module__": "elsewhere"})

            class InBlocks:
                def __init__(self) -> None:
                    with contextlib.nullcontext():
                        self.label: str = ""
                    try:
                        self.port: int = 0
                    finally:
                        self.ready: bool = True
                    if not self.port:
                        self.flag: bool = True

            class PositionalOnlySelf:
                def __init__(self, /, size: int = 0) -> None:
                    self.size: int = size

            class NoSelf:
                def __init__(*args) -> None:
                    other.size: int = 0

            class Unresolvable:
                def __init__(self) -> None:
                    self.broken: Undefined = None

            class NoInit: ...

            Generated = type("Generated", (), {"__init__": lambda self: None})

            class Box[T]:
                def __init__(self, item: T) -> None:
                    self.item: T = item

            class IntBox(Box[int]): ...
        """)
    )


@mark.parametrize("owner", [param("Box", id="defining"), param("IntBox", id="inheriting")])
def test_get_instance_var_annotations_resolves_a_type_parameter_of_the_class_defining_init(
    instance_module: ModuleType, owner: str
) -> None:
    assert get_instance_var_annotations(getattr(instance_module, owner)) == {
        "item": instance_module.Box.__type_params__[0]
    }


@mark.parametrize(
    ("owner", "expected"),
    [
        param(attrgetter("Declared"), {"plain": int, "shared": str, "fixed": float}, id="qualifiers-unwrapped"),
        param(
            attrgetter("DeclaredChild"),
            {"plain": int, "shared": str, "fixed": float, "extra": bytes},
            id="through-the-bases",
        ),
        param(attrgetter("DeclaredBadly"), {}, id="unresolvable"),
        param(attrgetter("Model"), {"name": Annotated[str, {"max_length": 10}]}, id="unhashable-metadata"),
        param(attrgetter("Plain"), {}, id="none"),
        param(lambda module: module, {"count": int}, id="module"),
    ],
)
def test_get_body_annotations(
    body_module: ModuleType,
    owner: Callable[[ModuleType], type | ModuleType],
    expected: dict[str, Annotation],
) -> None:
    assert get_body_annotations(owner(body_module)) == expected


@fixture(name="body_module")
def body_module_fixture(make_module: Callable[[str], ModuleType]) -> ModuleType:
    return make_module(
        dedent("""\
            from __future__ import annotations
            from typing import Annotated, ClassVar, Final

            class Declared:
                plain: int
                shared: ClassVar[str] = ""
                fixed: Final[float] = 1.0
                bare: Final = 2

            class DeclaredChild(Declared):
                extra: bytes

            class DeclaredBadly:
                broken: Undefined

            class Model:
                name: Annotated[str, {"max_length": 10}] = ""

            class Plain: ...

            count: int
        """)
    )


def test_get_body_annotations_reads_the_guarded_type_over_its_runtime_fallback(
    make_module: Callable[[str], ModuleType], annotations_header: str, decimal_fallback: str
) -> None:
    module = make_module(
        annotations_header
        + decimal_fallback
        + dedent("""\
            class Holder:
                Unit = int
                amount: Decimal
                unit: Unit
        """)
    )
    resolve_type_guarded_imports([], module.Holder)
    assert get_body_annotations(module.Holder) == {"amount": Decimal, "unit": int}


def test_get_body_annotations_of_a_base_reads_the_guard_of_its_module(
    make_subclass_of_a_guarded_base: MakeSubclassOfAGuardedBase, annotations_header: str
) -> None:
    child = make_subclass_of_a_guarded_base(
        annotations_header,
        dedent("""\
            from guarded_base import Base

            class Child(Base): ...
        """),
    )
    assert get_body_annotations(child) == {"amount": Decimal}


def test_get_body_annotations_of_a_base_ignores_the_guard_of_the_module_of_a_subclass(guarded_subclass: type) -> None:
    assert get_body_annotations(guarded_subclass) == {"inherited": int, "own": Decimal}
