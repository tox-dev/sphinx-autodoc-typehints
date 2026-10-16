from __future__ import annotations

from array import array
from importlib import import_module
from pathlib import Path
from sys import modules, version_info
from textwrap import dedent
from typing import TYPE_CHECKING, ClassVar, Final

import attr  # attr.s and attr.ib are the classic spelling under test
from attrs import define
from pytest import MarkDecorator, MonkeyPatch, fixture, mark, param

from _docstring.conftest import INT, STR

if TYPE_CHECKING:
    from io import StringIO
    from types import ModuleType

    from conftest import BuildText, MakeModule

    from _docstring.conftest import Process

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


@mark.parametrize(
    "lines",
    [
        param(["the typecode character used to create the array"], id="without-stub"),
        param([":type: str"], id="typed-in-the-docstring"),
    ],
)
def test_descriptor_type_stays_as_written(process: Process, lines: list[str]) -> None:
    assert process("attribute", "array.array.typecode", array.typecode, lines.copy()) == lines


@mark.sphinx("text", testroot="docstring-inventory")
def test_descriptor_type_takes_the_role_the_inventory_uses(process: Process) -> None:
    holder = import_module("slotted_module").Holder
    assert process("attribute", "slotted_module.Holder.kind", holder.kind, []) == [
        "",
        r":type: :sphinx_autodoc_typehints_type:`\:py\:data\:\`\~types.ModuleType\``",
    ]


def test_napoleon_attribute_takes_its_type_from_init(process: Process, make_module: MakeModule) -> None:
    ledger = make_module(
        "attributes_ledger",
        dedent("""\
            class Ledger:
                def __init__(self) -> None:
                    self.amount: int = 0
                    self.owner: str = ""
        """),
    ).Ledger
    lines = [
        ".. attribute:: amount",
        "",
        "   how much",
        "",
        ".. attribute:: owner",
        "",
        "   who",
        "",
        "   :type: str",
        "",
    ]
    assert process("class", "attributes_ledger.Ledger", ledger, lines) == [
        ".. attribute:: amount",
        "",
        "   how much",
        "",
        f"   :type: {INT}",
        "",
        ".. attribute:: owner",
        "",
        "   who",
        "",
        "   :type: str",
        "",
    ]


@mark.parametrize("field", [param("ivar", id="ivar"), param("cvar", id="cvar"), param("var", id="var")])
def test_variable_takes_its_type_from_the_class_body(process: Process, field: str) -> None:
    class Job:
        retries: int
        total: ClassVar[int] = 0

    assert process("class", "mod.Job", Job, [f":{field} retries: how often"]) == [
        f":vartype retries: {INT}",
        f":{field} retries: how often",
    ]


_GUARDED_ACCOUNT: Final[str] = dedent("""\
    from __future__ import annotations

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from decimal import Decimal


    class Account:
        def __init__(self) -> None:
            self.balance: Decimal = Decimal()
""")


@mark.parametrize(
    "sources",
    [
        param({"attributes_guarded": _GUARDED_ACCOUNT}, id="defined"),
        param(
            {
                "attributes_guarded_impl": _GUARDED_ACCOUNT,
                "attributes_guarded_facade": (
                    dedent("""\
                        from attributes_guarded_impl import Account

                        Account.__module__ = __name__
                    """)
                ),
            },
            id="reexported",
        ),
    ],
)
def test_instance_variable_takes_its_type_from_a_guarded_import(
    process: Process, make_module: MakeModule, sources: dict[str, str]
) -> None:
    for name, source in sources.items():
        make_module(name, source)
    documented = next(reversed(sources))
    account = modules[documented].Account
    assert process("class", f"{documented}.Account", account, [":ivar balance: the balance"]) == [
        r":vartype balance: :sphinx_autodoc_typehints_type:`\:py\:class\:\`\~decimal.Decimal\``",
        ":ivar balance: the balance",
    ]


@mark.parametrize(
    ("lines", "expected"),
    [
        param(
            [":ivar bar: the bar value", ":ivar count: the count"],
            [f":vartype bar: {STR}", ":ivar bar: the bar value", f":vartype count: {INT}", ":ivar count: the count"],
            id="each-variable",
        ),
        param(
            [":ivar :", ":ivar bar: the bar value", ":ivar  :", ":ivar count: the count"],
            [
                ":ivar :",
                f":vartype bar: {STR}",
                ":ivar bar: the bar value",
                ":ivar  :",
                f":vartype count: {INT}",
                ":ivar count: the count",
            ],
            id="beside-malformed-fields",
        ),
        param([":ivar\tbar: the bar value"], [f":vartype bar: {STR}", ":ivar\tbar: the bar value"], id="tab"),
        param([":ivar   bar: the bar value"], [f":vartype bar: {STR}", ":ivar   bar: the bar value"], id="spaces"),
        param([":ivar  bar:  the bar value"], [f":vartype bar: {STR}", ":ivar  bar:  the bar value"], id="spaced-body"),
    ],
)
def test_instance_variable_takes_its_type_from_init(
    process: Process, ivars: type, lines: list[str], expected: list[str]
) -> None:
    assert process("class", "attributes_ivars.Ivars", ivars, lines) == expected


@fixture(name="ivars")
def ivars_fixture(make_module: MakeModule) -> type:
    return make_module(
        "attributes_ivars",
        dedent("""\
            class Ivars:
                def __init__(self, bar: str = "baz", count: int = 0) -> None:
                    self.bar: str = bar
                    self.count: int = count
        """),
    ).Ivars


@mark.parametrize(
    "lines",
    [
        param([":ivar bar: the bar value", ":vartype bar: str"], id="typed-by-a-field"),
        param([":ivar str bar: the bar value"], id="typed-inline"),
        param([":ivar Dict[str, int] bar: the bar value"], id="typed-inline-with-spaces"),
        param([":ivar Callable[[int], str] bar: the bar value"], id="typed-inline-callable"),
        param([":ivar tuple[int, ...] bar: the bar value"], id="typed-inline-tuple"),
        param([":ivar other: not annotated"], id="unannotated"),
        param([":ivar :"], id="no-name"),
        param([":ivar  :"], id="no-name-two-spaces"),
        param([":ivar   :"], id="no-name-three-spaces"),
        param([":ivar "], id="no-colon"),
        param([":ivar bar"], id="unclosed"),
        param([":ivar bar body"], id="unclosed-with-body"),
        param([":ivarname: not a real field"], id="longer-keyword"),
        param([":ivars bar: pluralised keyword"], id="plural-keyword"),
    ],
)
def test_instance_variable_stays_as_written(process: Process, ivars: type, lines: list[str]) -> None:
    assert process("class", "attributes_ivars.Ivars", ivars, lines.copy()) == lines


@mark.sphinx(confoverrides={"typehints_document_rtype": False})
def test_instance_variable_of_a_function_stays_untyped(process: Process) -> None:
    def func(value: str) -> str: ...

    assert process("function", "mod.func", func, [":ivar bar: not a class"]) == [":ivar bar: not a class"]


@mark.parametrize(
    "expected",
    [
        param(
            dedent("""\
                GoogleAttributes.count: int

                class dummy_module.{cls}

                   Class docstring.

                   location

                      the location

                      Type:
                         "list"["Path"]
            """),
            id="attribute",
        ),
        param(
            dedent("""\
                GoogleAttributes.count: int

                class dummy_module.{cls}

                   Class docstring.

                   Variables:
                      **location** ("list"["Path"]) -- the location
            """),
            id="ivar",
            marks=mark.sphinx(confoverrides={"napoleon_use_ivar": True}),
        ),
    ],
)
@mark.parametrize(
    "cls",
    [param("GoogleInitAttributes", id="google"), param("NumpyInitAttributes", id="numpy")],
)
def test_napoleon_attribute_from_init_rendered_as_field(build_text: BuildText, cls: str, expected: str) -> None:
    # documenting an attribute has autodoc add the __init__ annotations of the module's classes to theirs, where
    # napoleon reads them
    assert build_text(
        dedent(f"""\
            .. autoattribute:: dummy_module.GoogleAttributes.count

            .. autoclass:: dummy_module.{cls}""")
    ) == expected.format(cls=cls)


@mark.parametrize(
    "expected",
    [
        param(
            dedent("""\
                Module docstring.

                attributes_module.location

                   the location

                   Type:
                      "list"["Path"]

                attributes_module.level

                   the level

                   Type:
                      "int"

                attributes_module.written

                   written by hand

                   Type:
                      str
            """),
            id="attribute",
        ),
        param(
            dedent("""\
                Module docstring.

                vartype location:
                   "list"["Path"]

                ivar location:
                   the location

                vartype level:
                   "int"

                ivar level:
                   the level

                ivar written:
                   written by hand

                vartype written:
                   str
            """),
            id="ivar",
            marks=mark.sphinx(confoverrides={"napoleon_use_ivar": True}),
        ),
    ],
)
def test_napoleon_module_attributes_rendered_as_fields(build_text: BuildText, expected: str) -> None:
    assert build_text(".. automodule:: attributes_module") == expected


def test_descriptor_of_a_c_extension_takes_its_type_from_the_stub(process: Process, c_ext_mod: ModuleType) -> None:
    assert process("attribute", "c_ext_mod.Encoder.depth", c_ext_mod.Encoder.depth, ["current nesting depth"]) == [
        "current nesting depth",
        "",
        f":type: {INT}",
    ]


@attr.s
class _Classic:
    name = attr.ib(type=str)
    untyped = attr.ib()


@define
class _Defined:
    name: str


@attr.s
class _Bare:
    size = attr.ib(type=int)


_Bare.__annotations__ = None  # ty: ignore[invalid-assignment]  # typeshed says dict, a class may hold None


@mark.parametrize(
    ("cls", "lines", "expected"),
    [
        param(_Classic, [":ivar name: the name"], [f":vartype name: {STR}", ":ivar name: the name"], id="classic"),
        param(_Classic, [":ivar untyped: no type"], [":ivar untyped: no type"], id="classic-untyped"),
        param(_Defined, [":ivar name: the name"], [f":vartype name: {STR}", ":ivar name: the name"], id="define"),
        param(
            _Bare, [":ivar size: how big"], [f":vartype size: {INT}", ":ivar size: how big"], id="without-annotations"
        ),
    ],
)
def test_attrs_field_takes_its_type(process: Process, cls: type, lines: list[str], expected: list[str]) -> None:
    assert process("class", f"{__name__}.{cls.__qualname__}", cls, lines) == expected


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_attrs_class_whose_annotations_fail_documents_its_fields_untyped(  # pragma: >=3.14 cover
    process: Process, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(Path(__file__).parents[1] / "roots" / "test-attrs")
    mixed = import_module("attrs_lazy_mod").Mixed
    assert process("class", "attrs_lazy_mod.Mixed", mixed, [":ivar b: the amount"]) == [":ivar b: the amount"]


@mark.parametrize(
    ("rst", "expected"),
    [
        param(
            dedent("""\
                .. autoclass:: attrs_mod.Outer.Bar
                   :members:
                   :undoc-members:
            """),
            dedent("""\
                class attrs_mod.Outer.Bar(foo)

                   An attrs class referencing a sibling nested class.

                   foo: Foo
            """),
            id="nested-forward-reference",
        ),
        param(
            dedent("""\
                .. autoclass:: attrs_mod.ClassicAttrs
                   :members:
                   :undoc-members:

                .. autoclass:: attrs_mod.AutoAttribs
                   :members:
                   :undoc-members:

                .. autoclass:: attrs_mod.ModernAttrs
                   :members:
                   :undoc-members:
            """),
            dedent("""\
                class attrs_mod.ClassicAttrs(name, age, untyped)

                   A class using classic attr.s style.

                   age: int

                   name: str

                class attrs_mod.AutoAttribs(name, age)

                   A class using auto_attribs=True.

                   age: int

                   name: str

                class attrs_mod.ModernAttrs(name, age)

                   A class using modern attrs.define.

                   age: int

                   name: str
            """),
            id="field-styles",
        ),
    ],
)
@mark.sphinx("text", testroot="attrs")
def test_build_documents_the_fields_of_an_attrs_class(
    build_text: BuildText, warning: StringIO, rst: str, expected: str
) -> None:
    assert (build_text(rst), warning.getvalue()) == (expected, "")
