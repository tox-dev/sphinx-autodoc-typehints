from __future__ import annotations

from array import array
from collections.abc import Callable, Sequence
from decimal import Decimal
from operator import attrgetter
from sys import version_info
from textwrap import dedent
from typing import TYPE_CHECKING, Final, TypeAliasType, TypeVar, Union, get_args, get_origin, no_type_check

from pytest import FixtureRequest, fixture, mark, param

from sphinx_autodoc_typehints._refs import MyTypeAliasForwardRef
from sphinx_autodoc_typehints._resolve import get_all_type_hints, get_descriptor_type_hint, resolve_annotations

if TYPE_CHECKING:
    from pathlib import Path
    from types import FunctionType, GetSetDescriptorType, MemberDescriptorType, ModuleType

    from _pytest.mark import ParameterSet
    from conftest import BuildText

    from _resolve.conftest import AsWritten, MakeStubbedModule
    from sphinx_autodoc_typehints._types import Annotation, Hint

    type Descriptor = GetSetDescriptorType | MemberDescriptorType


@no_type_check
def _unchecked(count: int, label: str) -> bool: ...


@no_type_check
class _Unchecked:
    def method(self, value: int) -> str: ...


class _Target: ...


@no_type_check
def _unchecked_forward_reference(obj: _Target) -> _Target: ...


@mark.parametrize(
    ("obj", "expected"),
    [
        param(_unchecked, {"count": int, "label": str, "return": bool}, id="function"),
        param(_Unchecked.method, {"value": int, "return": str}, id="method-of-a-class"),
        param(_unchecked_forward_reference, {"obj": _Target, "return": _Target}, id="forward-reference"),
    ],
)
def test_get_all_type_hints_reads_a_no_type_check_target(obj: FunctionType, expected: dict[str, type]) -> None:
    assert get_all_type_hints([], obj, obj.__qualname__, {}) == expected


@mark.parametrize(
    "annotation",
    [
        param("a positive float", id="prose"),
        param("csv.NoSuchName", id="missing-attribute"),
        param("Undefined", id="undefined-name"),
    ],
)
def test_get_all_type_hints_keeps_an_unresolvable_annotation_as_written(
    annotated_module: Callable[[str], ModuleType], annotation: str
) -> None:
    assert get_all_type_hints([], annotated_module(annotation).annotated, "mod.annotated", {}) == {
        "count": int,
        "value": annotation,
        "return": None,
    }


@fixture(name="annotated_module")
def annotated_module_fixture(make_module: Callable[[str], ModuleType]) -> Callable[[str], ModuleType]:
    def make(annotation: str) -> ModuleType:
        return make_module(
            dedent(f"""\
                import csv

                def annotated(count: int, value: {annotation!r}) -> None: ...
            """)
        )

    return make


@mark.parametrize(
    ("annotation", "message"),
    [
        param("a positive float", "Forward reference must be an expression -- got 'a positive float'", id="prose"),
        param("csv.NoSuchName", "module 'csv' has no attribute 'NoSuchName'", id="missing-attribute"),
        param("int.nope", "type object 'int' has no attribute 'nope'", id="missing-attribute-of-a-class"),
        param("Undefined", "name 'Undefined' is not defined", id="undefined-name"),
    ],
)
def test_get_all_type_hints_warns_on_an_unresolvable_annotation(
    annotated_module: Callable[[str], ModuleType],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    annotation: str,
    message: str,
) -> None:
    module = annotated_module(annotation)
    get_all_type_hints([], module.annotated, "mod.annotated", {})
    assert logged_warnings() == [
        ("forward_reference", f"{module.__file__}:3", "mod.annotated", module.__name__, message)
    ]


def test_get_all_type_hints_reads_a_pipe_union_of_a_mocked_type(
    make_module: Callable[[str], ModuleType], annotations_header: str
) -> None:
    module = make_module(
        annotations_header
        + dedent("""\
            from sphinx.ext.autodoc.mock import mock

            with mock(["absent_generics"]):
                from absent_generics import Gen

            def mocked(value: Gen[int] | None) -> None: ...
        """)
    )
    hint = get_all_type_hints([], module.mocked, "mod.mocked", {})["value"]
    assert (get_origin(hint), [getattr(arg, "__display_name__", arg) for arg in get_args(hint)]) == (
        Union,
        ["absent_generics.Gen.<class 'int'>", type(None)],
    )


def test_get_all_type_hints_keeps_an_annotation_whose_class_raises_on_subscription(
    make_module: Callable[[str], ModuleType], logged_warnings: Callable[[], list[tuple[str, ...]]]
) -> None:
    module = make_module(
        dedent("""\
            from __future__ import annotations

            class Shape:
                def __class_getitem__(cls, item):
                    raise ValueError(f"a shape cannot take {item}")

            def rejected(value: Shape[int]) -> None: ...
        """)
    )
    hints = get_all_type_hints([], module.rejected, "mod.rejected", {})
    assert (hints, logged_warnings()) == ({"value": "Shape[int]", "return": None}, [])


def test_resolve_annotations_gives_up_on_an_annotation_that_recurses_without_end(
    make_module: Callable[[str], ModuleType],
) -> None:
    module = make_module(
        dedent("""\
            from __future__ import annotations

            class Recursive:
                def __class_getitem__(cls, item):
                    raise RecursionError("maximum recursion depth exceeded")

            def func(value: Recursive[int]) -> None: ...
        """)
    )
    assert resolve_annotations([], module.func, "mod.func", {}) == {}


@mark.parametrize(
    "source",
    [
        param(
            dedent("""\
                from __future__ import annotations

                class NotGeneric: ...

                def func(first: NotGeneric[int], second: int) -> str: ...
            """),
            id="type-error",
        ),
        param(
            dedent("""\
                from __future__ import annotations

                def func(first: NotGeneric[int], second: int) -> str: ...
            """),
            id="name-error",
        ),
    ],
)
def test_get_all_type_hints_keeps_the_hints_beside_one_that_fails(
    make_module: Callable[[str], ModuleType], source: str
) -> None:
    assert get_all_type_hints([], make_module(source).func, "mod.func", {}) == {
        "first": "NotGeneric[int]",
        "second": int,
        "return": str,
    }


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_resolve_annotations_keeps_a_lazy_annotation_that_fails_as_a_forward_reference(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType], as_written: AsWritten
) -> None:
    module = make_module(
        dedent("""\
            class NotGeneric: ...

            def func(value: NotGeneric[int]) -> None: ...
        """)
    )
    hints = resolve_annotations([], module.func, "mod.func", {})
    assert (type(hints["value"]).__name__, as_written(hints)) == (
        "ForwardRef",
        {"value": "NotGeneric[int]", "return": None},
    )


def test_get_all_type_hints_of_a_class_owning_the_type_params_slot() -> None:
    # typing.TypeAliasType hands back the __type_params__ descriptor rather than a tuple (#740)
    assert get_all_type_hints([], TypeAliasType, "mod.TypeAliasType", {}) == {}


@mark.parametrize(
    ("imported", "expected"),
    [
        param("Decimal", {"value": Decimal, "return": type(None)}, id="bound"),
        param("NoSuchName", {"value": "_t.Number", "return": None}, id="kept-as-written"),
    ],
)
def test_get_all_type_hints_runs_the_guard_of_a_module_an_alias_names(
    module_dir: Path,
    make_module: Callable[[str], ModuleType],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    as_written: AsWritten,
    imported: str,
    expected: dict[str, Hint],
) -> None:
    (module_dir / "guard_alias_types.py").write_text(
        dedent(f"""\
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from decimal import {imported} as Number
        """)
    )
    module = make_module(
        dedent("""\
            from __future__ import annotations
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                import guard_alias_types as _t

            def func(value: _t.Number) -> None: ...
        """)
    )
    assert (as_written(get_all_type_hints([], module.func, "mod.func", {})), logged_warnings()) == (expected, [])


@mark.parametrize(
    ("method", "expected"),
    [
        param("Outer.make", {"value": "Outer.Inner", "return": "Outer.Inner"}, id="beside-the-method"),
        param("Outer.Inner.clone", {"return": "Outer.Inner"}, id="the-class-of-the-method"),
    ],
)
def test_get_all_type_hints_resolves_a_nested_class(
    make_module: Callable[[str], ModuleType], method: str, expected: dict[str, str]
) -> None:
    module = make_module(
        dedent("""\
            from __future__ import annotations

            class Outer:
                class Inner:
                    def clone(self) -> Inner: ...

                def make(self, value: Inner) -> Inner: ...
        """)
    )
    hints = get_all_type_hints([], attrgetter(method)(module), f"mod.{method}", {})
    assert hints == {name: attrgetter(path)(module) for name, path in expected.items()}


def test_get_all_type_hints_of_a_function_local_to_another(make_module: Callable[[str], ModuleType]) -> None:
    module = make_module(
        dedent("""\
            from __future__ import annotations

            def make():
                def func(value: int) -> None: ...
                return func
        """)
    )
    assert get_all_type_hints([], module.make(), "mod.func", {}) == {"value": int, "return": type(None)}


@mark.parametrize(
    ("method", "expected"),
    [
        param("list", {"return": list[str]}, id="method-named-like-a-builtin"),
        param("move", {"to": Decimal, "return": type(None)}, id="field-default-named-like-a-global"),
    ],
)
def test_get_all_type_hints_reads_a_global_a_class_member_names_alike(
    make_module: Callable[[str], ModuleType], method: str, expected: dict[str, type]
) -> None:
    module = make_module(
        dedent("""\
            from __future__ import annotations
            from decimal import Decimal

            class Shadowing:
                Decimal = None

                def list(self) -> list[str]: ...

                def move(self, to: Decimal) -> None: ...
        """)
    )
    assert get_all_type_hints([], getattr(module.Shadowing, method), f"mod.Shadowing.{method}", {}) == expected


@mark.parametrize(
    "definition",
    [
        param('Kind = typing.TypeVar("Kind")', id="type-var"),
        param('Kind = typing.ParamSpec("Kind")', id="param-spec"),
        param('Kind = typing.TypeVarTuple("Kind")', id="type-var-tuple"),
        param("Kind = tuple[int, int]", id="generic-alias"),
        param("Kind = typing.Optional[int]", id="typing-alias"),
        param("Kind = int | str", id="union"),
        param("type Kind = int", id="type-statement"),
        param('Kind = typing_extensions.TypeAliasType("Kind", int)', id="typing-extensions-alias"),
        param('Kind = typing.NewType("Kind", int)', id="new-type"),
    ],
)
def test_get_all_type_hints_resolves_a_type_from_the_class_body(
    make_module: Callable[[str], ModuleType], definition: str
) -> None:
    module = make_module(
        dedent(f"""\
            from __future__ import annotations
            import typing
            import typing_extensions

            class Holder:
                {definition}

                def take(self, value: Kind) -> None: ...
        """)
    )
    assert get_all_type_hints([], module.Holder.take, "mod.Holder.take", {}) == {
        "value": module.Holder.Kind,
        "return": type(None),
    }


@mark.parametrize("owner", [param("func", id="function"), param("Holder.method", id="method")])
def test_get_all_type_hints_reads_the_names_it_is_given(make_module: Callable[[str], ModuleType], owner: str) -> None:
    module = make_module(
        dedent("""\
            from __future__ import annotations

            def func(value: Given) -> None: ...

            class Holder:
                def method(self, value: Given) -> None: ...
        """)
    )
    hints = get_all_type_hints([], attrgetter(owner)(module), f"mod.{owner}", {"Given": Decimal})
    assert hints == {"value": Decimal, "return": type(None)}


@mark.parametrize(
    ("owner", "expected"),
    [
        param(
            "Box.__init__", lambda loaded: {"thing": loaded.Box.__type_params__[0], "return": type(None)}, id="class"
        ),
        param(
            "Pair.lookup",
            lambda loaded: dict(zip(("key", "return"), loaded.Pair.__type_params__, strict=True)),
            id="class-of-two",
        ),
        param(
            "identity",
            lambda loaded: dict.fromkeys(("value", "return"), loaded.identity.__type_params__[0]),
            id="function",
        ),
    ],
)
def test_get_all_type_hints_resolves_a_type_parameter(
    make_module: Callable[[str], ModuleType],
    owner: str,
    expected: Callable[[ModuleType], dict[str, TypeVar | type[None]]],
) -> None:
    module = make_module(
        dedent("""\
            from __future__ import annotations

            class Box[T]:
                def __init__(self, thing: T) -> None: ...

            class Pair[K, V]:
                def lookup(self, key: K) -> V: ...

            def identity[U](value: U) -> U: ...
        """)
    )
    assert get_all_type_hints([], attrgetter(owner)(module), f"mod.{owner}", {}) == expected(module)


@mark.parametrize(
    ("fixture_name", "owner", "expected"),
    [
        param("stub_mod", lambda module: module.greet, {"name": str, "greeting": str, "return": str}, id="function"),
        param(
            "stub_mod",
            lambda module: module.Calculator.Inner().process,
            {"data": bytes, "return": bytes},
            id="bound-method-refusing-annotations",
        ),
        param(
            "c_ext_mod",
            lambda module: module.greet,
            {"name": str, "greeting": Sequence[str], "return": str},
            id="c-extension",
        ),
    ],
)
def test_get_all_type_hints_reads_a_stub(
    request: FixtureRequest,
    fixture_name: str,
    owner: Callable[[ModuleType], Callable[..., object]],
    expected: dict[str, Annotation],
) -> None:
    assert get_all_type_hints([], owner(request.getfixturevalue(fixture_name)), "mod.documented", {}) == expected


@mark.parametrize(
    ("runtime", "stub", "expected"),
    [
        param(
            dedent("""\
                class Typed:
                    def __init__(self, size): ...
            """),
            dedent("""\
                class Typed:
                    def __init__(self, size: int) -> None: ...
            """),
            {"size": int, "return": type(None)},
            id="constructor",
        ),
        param(
            dedent("""\
                class Typed:
                    def __new__(cls, size): ...
            """),
            dedent("""\
                class Typed:
                    def __new__(cls, size: int) -> int: ...
            """),
            {"size": int, "return": int},
            id="allocator",
        ),
        param(
            "class Typed: ...",
            dedent("""\
                class Typed:
                    size: int
            """),
            {"size": int},
            id="class-body",
        ),
    ],
)
def test_get_all_type_hints_types_a_class_by_its_stub(
    make_stubbed_module: MakeStubbedModule, runtime: str, stub: str, expected: dict[str, type]
) -> None:
    assert get_all_type_hints([], make_stubbed_module(runtime, stub).Typed, "mod.Typed", {}) == expected


def test_get_all_type_hints_reads_a_stub_type_parameter_again(make_stubbed_module: MakeStubbedModule) -> None:
    module = make_stubbed_module("def func(value): return value", "def func[T](value: T) -> T: ...")
    calls = [get_all_type_hints([], module.func, "mod.func", {}) for _ in range(2)]
    assert [{name: (type(hint), str(hint)) for name, hint in hints.items()} for hints in calls] == [
        {"value": (TypeVar, "~T"), "return": (TypeVar, "~T")}
    ] * 2


# the stub imports `Decimal` where the runtime module does not, so only its namespace resolves the name
_BACKFILLED: Final[list[ParameterSet]] = [
    param("def load(path): ...", "from decimal import Decimal\ndef load(path: Decimal) -> None: ...", id="stub"),
    param(
        dedent("""\
            from decimal import Decimal
            def load(path):
                # type: (Decimal) -> None
                ...
        """),
        "",
        id="type-comment",
    ),
]


@mark.parametrize(("runtime", "stub"), _BACKFILLED)
def test_get_all_type_hints_leaves_the_runtime_annotations_of_a_backfilled_object(
    make_stubbed_module: MakeStubbedModule, runtime: str, stub: str
) -> None:
    load = make_stubbed_module(runtime, stub).load
    hints = get_all_type_hints([], load, "mod.load", {})
    assert (hints, load.__annotations__) == ({"path": Decimal, "return": type(None)}, {})


@mark.parametrize(("runtime", "stub"), _BACKFILLED)
def test_get_all_type_hints_resolves_a_backfilled_object_again_without_warning(
    make_stubbed_module: MakeStubbedModule,
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    runtime: str,
    stub: str,
) -> None:
    load = make_stubbed_module(runtime, stub).load
    calls = [get_all_type_hints([], load, "mod.load", {}) for _ in range(2)]
    assert (calls, logged_warnings()) == ([{"path": Decimal, "return": type(None)}] * 2, [])


@mark.parametrize(
    ("fixture_name", "owner", "key", "alias"),
    [
        param("stub_only_module", lambda module: module.Poly, "coef", "_SeriesLike", id="name-only-a-stub-defines"),
        param("c_ext_mod", lambda module: module.with_hook, "callback", "GreetHook", id="stub-alias"),
    ],
)
def test_get_all_type_hints_cross_references_a_name_of_the_stub(
    request: FixtureRequest,
    fixture_name: str,
    owner: Callable[[ModuleType], Callable[..., object]],
    key: str,
    alias: str,
) -> None:
    hint = get_all_type_hints([], owner(request.getfixturevalue(fixture_name)), "mod.documented", {})[key]
    assert (type(hint), vars(hint)) == (MyTypeAliasForwardRef, {"name": alias, "configured": False, "crossref": True})


def test_get_all_type_hints_reads_the_stub_of_a_c_extension_allocator(c_ext_mod: ModuleType) -> None:
    hint = get_all_type_hints([], c_ext_mod.Encoder.__new__, "c_ext_mod.Encoder.__new__", {})["default"]
    assert [(type(arg), str(arg)) for arg in get_args(hint)] == [
        (MyTypeAliasForwardRef, "MyTypeAliasForwardRef('EncoderHook')"),
        (type, "<class 'NoneType'>"),
    ]


def test_get_descriptor_type_hint_cross_references_a_stub_alias(c_ext_mod: ModuleType) -> None:
    hint = get_descriptor_type_hint(c_ext_mod.Encoder.hook)
    assert [(type(arg), getattr(arg, "crossref", None)) for arg in get_args(hint)] == [
        (MyTypeAliasForwardRef, True),
        (type, None),
    ]


@mark.parametrize(
    ("fixture_name", "descriptor", "expected"),
    [
        param("c_ext_mod", attrgetter("Encoder.depth"), int, id="c-extension-property"),
        param("c_ext_mod", attrgetter("Encoder.flags"), int, id="c-extension-class-body"),
        param("c_ext_mod", attrgetter("Encoder.guarded"), bool, id="c-extension-version-gated"),
        param("slotted", lambda _: array.typecode, None, id="no-stub"),
        param("slotted", attrgetter("Slotted.size"), int, id="class-body"),
        param("slotted", attrgetter("Slotted.sized"), Sequence[int], id="evaluated-in-the-stub"),
        param("slotted", attrgetter("Slotted.depth"), bytes, id="property"),
        param("slotted", attrgetter("Slotted.guarded"), bool, id="property-of-a-version"),
        param("slotted", attrgetter("Slotted.plain"), None, id="method"),
        param("slotted", attrgetter("Slotted.untyped"), None, id="property-without-return"),
        param("slotted", attrgetter("Slotted.missing"), None, id="missing-from-the-stub"),
        param("slotted", attrgetter("Function.size"), None, id="class-the-stub-defines-as-a-function"),
    ],
)
def test_get_descriptor_type_hint(
    request: FixtureRequest,
    fixture_name: str,
    descriptor: Callable[[ModuleType], Descriptor],
    expected: Annotation | None,
) -> None:
    assert get_descriptor_type_hint(descriptor(request.getfixturevalue(fixture_name))) == expected


@fixture
def slotted(make_stubbed_module: MakeStubbedModule) -> ModuleType:
    return make_stubbed_module(
        dedent("""\
            class Slotted:
                __slots__ = ("size", "sized", "depth", "guarded", "missing", "plain", "untyped")

            class Function:
                __slots__ = ("size",)
        """),
        dedent("""\
            import sys
            from collections.abc import Sequence

            class Slotted:
                size: int
                sized: Sequence[int]
                @property
                def depth(self) -> bytes: ...
                if sys.version_info >= (3, 99):
                    guarded: str
                else:
                    @property
                    def guarded(self) -> bool: ...
                def plain(self) -> float: ...
                @property
                def untyped(self): ...

            def Function() -> None: ...
        """),
    )


@mark.parametrize(
    ("fixture_name", "rst", "expected"),
    [
        param(
            "stub_mod",
            ".. autofunction:: stub_mod.greet",
            dedent("""\
                stub_mod.greet(name, greeting)

                   Return type:
                      "str"
            """),
            marks=mark.sphinx("text", testroot="resolve-stubs"),
            id="function",
        ),
        param(
            "stub_mod",
            ".. autoclass:: stub_mod.Converter",
            dedent("""\
                class stub_mod.Converter(output)

                   Convert output.

                   Parameters:
                      **output** ("str") -- the output format
            """),
            marks=mark.sphinx("text", testroot="resolve-stubs"),
            id="allocator",
        ),
        param(
            "native_pkg",
            ".. autofunction:: native_pkg.warc.parse",
            dedent("""\
                native_pkg.warc.parse(data)

                   Parse WARC records.

                   Parameters:
                      **data** ("bytes") -- input bytes

                   Return type:
                      "Iterator"["WarcRecord"]
            """),
            marks=mark.sphinx("text", testroot="resolve-stubs"),
            id="native-submodule-function",
        ),
        param(
            "native_pkg",
            ".. autoclass:: native_pkg.warc.WarcRecord",
            dedent("""\
                class native_pkg.warc.WarcRecord

                   A WARC record (native).
            """),
            marks=mark.sphinx("text", testroot="resolve-stubs"),
            id="native-submodule-class",
        ),
        param(
            None,
            ".. autofunction:: dummy_module_future_annotations.function_with_py310_annotations",
            dedent("""\
                dummy_module_future_annotations.function_with_py310_annotations(self, x, y, z=None)

                   Method docstring.

                   Parameters:
                      * **x** ("bool" | "None") -- foo

                      * **y** ("int" | "str" | "float") -- bar

                      * **z** ("str" | "None") -- baz

                   Return type:
                      "str"
            """),
            marks=mark.sphinx("text", testroot="dummy"),
            id="union-syntax-as-strings",
        ),
        param(
            None,
            dedent("""\
                .. autoclass:: mod_forward_ref.Tree
                   :members:
            """),
            dedent("""\
                class mod_forward_ref.Tree

                   children()

                      Get child nodes.

                      Return type:
                         "list"["Tree"]

                      Returns:
                         The children of this node.
            """),
            marks=mark.sphinx("text", testroot="integration"),
            id="forward-reference-in-an-eager-module",
        ),
    ],
)
@mark.sphinx(exception_on_warning=True)
def test_build_documents_the_types_of_a_stub_or_a_string(
    request: FixtureRequest,
    build_text: BuildText,
    fixture_name: str | None,
    rst: str,
    expected: str,
) -> None:
    # pytest.param cannot carry usefixtures, so each case names the fixture importing its module
    if fixture_name is not None:
        request.getfixturevalue(fixture_name)
    assert build_text(rst) == expected


@mark.skipif(version_info < (3, 14), reason="eager annotations fail at import instead")
def test_get_all_type_hints_keeps_an_attrs_field_naming_nothing(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType], as_written: AsWritten
) -> None:
    module = make_module(
        dedent("""\
            import attrs

            @attrs.define
            class Price:
                amount: Decimal
        """)
    )
    assert as_written(get_all_type_hints([], module.Price.__init__, "mod.Price", {}))["amount"] == "Decimal"


# subscripting a class that is no generic raises on evaluation (#712)
@mark.skipif(version_info < (3, 14), reason="eager annotations fail at import instead")
@mark.sphinx(
    "text", testroot="integration", confoverrides={"always_document_param_types": True}, exception_on_warning=True
)
def test_build_shows_the_source_of_an_annotation_whose_evaluation_raises(  # pragma: >=3.14 cover
    build_text: BuildText, make_module: Callable[[str], ModuleType]
) -> None:
    module = make_module(
        dedent("""\
            class DiGraph:
                pass


            def add_node_between_nodes(g: DiGraph[int]) -> None:
                \"\"\"Stub.\"\"\"
        """)
    )
    assert (build_text(f".. autofunction:: {module.__name__}.add_node_between_nodes")) == (
        dedent(f"""\
            {module.__name__}.add_node_between_nodes(g)

               Stub.

               Parameters:
                  **g** (DiGraph[int])

               Return type:
                  "None"
        """)
    )
