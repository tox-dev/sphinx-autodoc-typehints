from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, TypeAliasType

from pytest import fixture, mark, param

from sphinx_autodoc_typehints._resolve import (
    bound_type_args,
    declared_type_params,
    specialize,
    type_params_of,
)
from sphinx_autodoc_typehints._resolve.generics import type_arguments

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from conftest import BuildText

    from sphinx_autodoc_typehints._types import Annotation


@mark.parametrize(
    ("rst", "return_type"),
    [
        param(".. automethod:: type_params_module.IntBox.get", '"int"', id="legacy"),
        param(".. automethod:: type_params_module.IntStack.peek", '"int"', id="pep695"),
        param(".. automethod:: type_params_module.IntListing.get", '"list"["int"]', id="through-two-bases"),
        param(".. automethod:: type_params_module.Listing.get", '"list"["U"]', id="to-own-param"),
        param(".. automethod:: type_params_module.Restack.peek", '"V"', id="to-own-param-of-the-name"),
        param(".. automethod:: type_params_module.IntFeed.pull", '"int"', id="protocol-not-runtime-checkable"),
        param(".. automethod:: type_params_module.IntSink.put", '"int"', id="past-a-registered-base"),
    ],
)
@mark.sphinx("text", testroot="type-params")
def test_type_params_bound_by_the_documenting_subclass_return(
    build_text: BuildText, rst: str, return_type: str
) -> None:
    lines = build_text(rst).splitlines()
    assert lines[lines.index("   Return type:") + 1].strip() == return_type


@mark.sphinx("text", testroot="type-params")
def test_generic_subclass_inherited_special_members_build(
    build_text: BuildText, make_module: Callable[[str], ModuleType]
) -> None:
    module = make_module(
        dedent('''\
            from typing import Generic, TypeVar

            T = TypeVar("T")

            class Base(Generic[T]):
                """A generic base class."""

                def get(self) -> T:
                    """Return a value."""

            class Derived(Base[T]):
                """A subclass passing the type variable on."""
            '''),
    )
    output = build_text(
        dedent(f"""\
            .. autoclass:: {module.__name__}.Derived
               :members:
               :inherited-members:
               :special-members:
            """)
    )
    assert "Derived" in output
    assert "__class_getitem__" in output


@mark.parametrize(
    ("rst", "expected"),
    [
        param(
            ".. automethod:: type_params_module.IntBox.get",
            '**default** ("int") -- returned when empty',
            marks=mark.sphinx(confoverrides={"always_document_param_types": True}),
            id="method-parameter",
        ),
        param(
            ".. autoclass:: type_params_module.IntStack",
            '**item** ("int")',
            marks=mark.sphinx(confoverrides={"always_document_param_types": True}),
            id="constructor-parameter",
        ),
        param(
            ".. autoclass:: type_params_module.IntPool", '**size** ("int") -- how many it holds', id="pep695-vartype"
        ),
        param(
            ".. autoclass:: type_params_module.IntCrate", '**size** ("int") -- how many it holds', id="legacy-vartype"
        ),
    ],
)
@mark.sphinx("text", testroot="type-params")
def test_type_params_bound_by_the_documenting_subclass_field(build_text: BuildText, rst: str, expected: str) -> None:
    assert expected in [line.strip() for line in build_text(rst).splitlines()]


@mark.parametrize(
    ("rst", "expected"),
    [
        param(".. automethod:: type_params_module.IntBox.get", "IntBox.get(default: int) -> int", id="method"),
        param(".. automethod:: type_params_module.IntPool.take", "IntPool.take(key: int) -> int", id="pep695-overload"),
        param(
            ".. automethod:: type_params_module.IntCrate.take", "IntCrate.take(key: int) -> int", id="legacy-overload"
        ),
    ],
)
@mark.sphinx(
    "text",
    testroot="type-params",
    confoverrides={"typehints_use_signature": True, "typehints_use_signature_return": True},
)
def test_type_params_bound_by_the_documenting_subclass_signature(
    build_text: BuildText, rst: str, expected: str
) -> None:
    assert build_text(rst).splitlines()[0] == expected


@mark.parametrize(
    ("rst", "expected"),
    [
        param(".. automethod:: type_params_module.IntPool.take", '* **key** ("int") \u2192 "int"', id="bound-pep695"),
        param(".. automethod:: type_params_module.IntCrate.take", '* **key** ("int") \u2192 "int"', id="bound-legacy"),
        param(
            ".. automethod:: type_params_module.Shelf.take",
            '* **key** ("S") → "list"["S"]',
            id="own-type-parameter",
        ),
        param(".. autofunction:: type_params_module.pick", "* **key** (K) → list[K]", id="unregistered-overloads"),
    ],
)
@mark.sphinx("text", testroot="type-params")
def test_type_params_of_an_overload(build_text: BuildText, rst: str, expected: str) -> None:
    lines = build_text(rst).splitlines()
    assert lines[lines.index("   Overloads:") + 1].strip() == expected


@mark.parametrize(
    ("owner", "legacy", "expected"),
    [
        param("Box", False, ["U"], id="pep695"),
        param("Legacy", False, [], id="legacy-left-out"),
        param("Legacy", True, ["T"], id="legacy"),
        param("pick", True, ["K"], id="function"),
        param("IntBox", True, [], id="bound"),
    ],
)
def test_type_params_of(generic_module: ModuleType, owner: str, legacy: bool, expected: list[str]) -> None:
    assert [
        type_param.__name__ for type_param in type_params_of(getattr(generic_module, owner), legacy=legacy)
    ] == expected


@fixture(name="generic_module")
def generic_module_fixture(make_module: Callable[[str], ModuleType]) -> ModuleType:
    return make_module(
        dedent("""\
            from typing import Generic, TypeVar, TypeVarTuple

            T = TypeVar("T")
            Ts = TypeVarTuple("Ts")

            class Box[U]:
                value: U

                def get(self) -> U: ...

            class Legacy(Generic[T]):
                def get(self) -> T: ...

            class IntBox(Box[int]): ...

            class Overriding(Box[int]):
                def get(self) -> int: ...

            class Relay[V](Box[V]): ...

            class StrRelay(Relay[str]): ...

            class Derived(Legacy[T]): ...

            class Variadic(Generic[*Ts]): ...

            def pick[K](key: K) -> K: ...
        """)
    )


@mark.parametrize("legacy", [param(True, id="legacy"), param(False, id="pep695")])
def test_type_params_of_a_class_owning_the_slot(legacy: bool) -> None:
    # typing.TypeAliasType hands back the __type_params__ descriptor rather than a tuple (#740)
    assert type_params_of(TypeAliasType, legacy=legacy) == ()


def test_declared_type_params_of_a_method_documented_under_a_subclass(generic_module: ModuleType) -> None:
    declared = declared_type_params(generic_module.Relay.get, generic_module.Box.get, generic_module.Relay)
    assert declared == frozenset((*generic_module.Box.__type_params__, *generic_module.Relay.__type_params__))


@mark.parametrize(
    ("documenting", "attribute", "expected"),
    [
        param("IntBox", "get", {"U": int}, id="method"),
        param("IntBox", "value", {"U": int}, id="annotated-only"),
        param("StrRelay", "get", {"U": str}, id="through-two-bases"),
        param("Overriding", "get", {}, id="defined-by-the-class"),
        param("Derived", "__class_getitem__", {}, id="inherited-generic-class-getitem"),
        param("Derived", "__init_subclass__", {}, id="inherited-generic-init-subclass"),
        param("pick", "get", {}, id="no-class"),
    ],
)
def test_bound_type_args(
    generic_module: ModuleType, documenting: str, attribute: str, expected: dict[str, type]
) -> None:
    bound = bound_type_args(getattr(generic_module, documenting), attribute)
    assert {type_param.__name__: argument for type_param, argument in bound.items()} == expected


def test_bound_type_args_past_a_class_whose_annotations_are_no_dict(
    make_module: Callable[[str], ModuleType],
) -> None:
    module = make_module(
        dedent("""\
            class Box[T]:
                def get(self) -> T: ...

            class Proxy(Box[int]):
                __annotations__ = property(lambda self: {})
        """)
    )
    assert bound_type_args(module.Proxy, "get") == {module.Box.__type_params__[0]: int}


@mark.parametrize(
    ("alias", "expected"),
    [
        param(lambda module: (module.Box, module.Box[int]), {"U": int}, id="subscribed"),
        param(lambda module: (module.Box, module.Box), {}, id="bare"),
        param(lambda module: (module.Variadic, module.Variadic[int, str]), {}, id="variadic"),
    ],
)
def test_type_arguments(
    generic_module: ModuleType,
    alias: Callable[[ModuleType], tuple[type, Annotation]],
    expected: dict[str, type],
) -> None:
    assert {
        type_param.__name__: argument for type_param, argument in type_arguments(*alias(generic_module)).items()
    } == expected


@mark.parametrize(
    ("annotation", "expected"),
    [
        param(lambda module: module.T, int, id="bound-parameter"),
        param(lambda module: module.Ts, None, id="unbound-parameter"),
        param(lambda module: list[module.T], list[int], id="generic-alias"),
        param(lambda module: module.Legacy, None, id="bare-generic-class"),
        param(lambda _: list[str], list[str], id="no-parameter"),
    ],
)
def test_specialize(
    generic_module: ModuleType, annotation: Callable[[ModuleType], Annotation], expected: Annotation | None
) -> None:
    unspecialized = annotation(generic_module)
    assert specialize(unspecialized, {generic_module.T: int}) == (unspecialized if expected is None else expected)


@mark.parametrize(
    ("rst", "expected"),
    [
        param(
            ".. autofunction:: type_params_module.bounded",
            dedent("""\
                type_params_module.bounded[T: Path](value)

                   Take a bounded type parameter.

                   Return type:
                      "T"
            """),
            id="function",
        ),
        param(
            ".. automethod:: type_params_module.Stack.peek",
            dedent("""\
                Stack.peek()

                   Look at the top.

                   Return type:
                      "T"
            """),
            id="class",
        ),
        param(
            ".. automethod:: type_params_module.Legacy.first",
            dedent("""\
                Legacy.first()

                   Return the first.

                   Return type:
                      "D"
            """),
            id="generic-subclass",
        ),
        param(
            ".. autofunction:: type_params_module.loose",
            dedent("""\
                type_params_module.loose(value)

                   Use a type variable no signature declares.

                   Return type:
                      "L"
            """),
            id="undeclared",
        ),
        param(
            ".. autofunction:: type_params_module.forward",
            dedent("""\
                type_params_module.forward[**P](call, *args, **kwargs)

                   Call with the arguments it takes.

                   Parameters:
                      * **args** ("P.args") -- positional

                      * **kwargs** ("P.kwargs") -- by keyword

                   Return type:
                      "None"
            """),
            id="param-spec-components",
        ),
        param(
            dedent("""\
                .. autoclass:: type_params_module.Forwarding
                   :members: unwrap
            """),
            dedent("""\
                class type_params_module.Forwarding

                   Forwards its annotations to the object it wraps.

                   unwrap()

                      Return the wrapped object.

                      Return type:
                         "int"
            """),
            id="class-whose-annotations-are-a-property",
        ),
    ],
)
@mark.sphinx("text", testroot="type-params")
def test_declared_type_params_show_by_name(build_text: BuildText, rst: str, expected: str) -> None:
    assert build_text(rst) == expected
