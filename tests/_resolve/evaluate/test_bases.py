from __future__ import annotations

from decimal import Decimal
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import fixture

from sphinx_autodoc_typehints._resolve.evaluate.bases import base_scopes, declared_hints, hints_of_bases

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType


def test_base_scopes_yields_the_bases_object_first(bases_module: ModuleType) -> None:
    assert [base for base, _, _ in base_scopes(bases_module.Child, None, None)] == [
        object,
        bases_module.Base,
        bases_module.Child,
    ]


@fixture(name="bases_module")
def bases_module_fixture(make_module: Callable[[str], ModuleType]) -> ModuleType:
    return make_module(
        dedent("""\
            from __future__ import annotations
            from decimal import Decimal

            class Base:
                inherited: int

            class Child(Base):
                Local = bytes
                own: Decimal
                local: Local
        """)
    )


def test_base_scopes_reads_the_module_before_the_class_body(bases_module: ModuleType) -> None:
    # as get_type_hints does, the names of the class body evaluate as the globals
    *_, (_, scope_globals, scope_locals) = base_scopes(bases_module.Child, None, None)
    assert (scope_globals["Local"], scope_locals) == (bytes, vars(bases_module))


def test_base_scopes_hands_out_the_namespaces_it_is_given(bases_module: ModuleType) -> None:
    scopes = [
        (scope_globals, scope_locals)
        for _, scope_globals, scope_locals in base_scopes(bases_module.Child, {"a": 1}, {"b": 2})
    ]
    assert scopes == [({"a": 1}, {"b": 2})] * 3


def test_declared_hints_leaves_out_the_annotations_of_the_bases(bases_module: ModuleType) -> None:
    child = bases_module.Child
    assert declared_hints(child, dict(vars(child)), vars(bases_module)) == {"own": Decimal, "local": bytes}


def test_hints_of_bases_merges_the_bases_in_order(bases_module: ModuleType) -> None:
    hints = hints_of_bases(bases_module.Child, None, None, declared_hints)
    assert list(hints.items()) == [("inherited", int), ("own", Decimal), ("local", bytes)]
