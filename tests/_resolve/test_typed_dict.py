from __future__ import annotations

from operator import attrgetter
from sys import modules
from textwrap import dedent
from typing import TYPE_CHECKING, Never, NotRequired, Protocol

from pytest import MonkeyPatch, fixture, mark, param

from sphinx_autodoc_typehints._resolve import OPEN, extra_items_type, typed_dict_keys

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import GenericAlias, ModuleType

    from conftest import BuildText

    from sphinx_autodoc_typehints._types import Annotation


@mark.parametrize(
    ("rst", "expected"),
    [
        param(".. autoattribute:: typed_dict_module.Movie.year", "NotRequired[int]", id="total-false"),
        param(".. autoattribute:: typed_dict_module.Movie.title", "str", id="required"),
        param(".. autoattribute:: typed_dict_module.Movie.rating", "NotRequired[float]", id="not-required"),
        param(".. autoattribute:: typed_dict_module.Movie.note", "NotRequired[str]", id="annotated"),
        param(".. autoattribute:: typed_dict_module.Plain.year", "int", id="not-a-typed-dict"),
        param(".. autoattribute:: typed_dict_module.Shape.size", "ReadOnly[int | str]", id="read-only"),
        param(
            ".. autoattribute:: typed_dict_module.Shape.label",
            "NotRequired[ReadOnly[str]]",
            id="read-only-not-required",
        ),
    ],
)
@mark.sphinx("text", testroot="typed-dict")
def test_typed_dict_key_shows_whether_it_may_be_left_out(build_text: BuildText, rst: str, expected: str) -> None:
    assert build_text(rst).splitlines()[0].partition(": ")[2] == expected


@mark.sphinx("text", testroot="typed-dict", confoverrides={"autodoc_typehints": "none"})
def test_typed_dict_key_without_a_shown_type(build_text: BuildText) -> None:
    assert build_text(".. autoattribute:: typed_dict_module.Movie.year").splitlines()[0] == "Movie.year"


@mark.parametrize(
    ("module", "cls", "expected"),
    [
        param(
            "typed_dict_module",
            "IntOptions",
            ["   extra: NotRequired[list[int]]", "   limit: int"],
            id="generic-base",
        ),
        param("typed_dict_module", "Square", ["   label: ReadOnly[str]", "   size: ReadOnly[int]"], id="redeclared"),
        param("typed_dict_module", "Tile", ["   label: ReadOnly[str]", "   size: ReadOnly[int]"], id="first-base"),
        param(
            "typed_dict_guarded_child",
            "Child",
            ["   inherited: int", "   own: Decimal"],
            id="base-from-another-module-ignoring-the-guard-of-the-subclass",
        ),
    ],
)
@mark.sphinx("text", testroot="typed-dict")
def test_typed_dict_key_inherited_from_a_base(
    build_text: BuildText, monkeypatch: MonkeyPatch, module: str, cls: str, expected: list[str]
) -> None:
    # autodoc lists the keys a TypedDict inherits only on the build importing its module
    monkeypatch.delitem(modules, module, raising=False)
    lines = build_text(
        dedent(f"""\
            .. autoclass:: {module}.{cls}
               :members:
               :undoc-members:
        """)
    ).splitlines()
    assert [line for line in lines if line.startswith("   ") and ": " in line] == expected


@mark.parametrize(
    ("function", "expected"),
    [
        param("configure", '**limit** ("int") -- the limit', id="pep695-generic"),
        param("configure_legacy", '**limit** ("str") -- the limit', id="legacy-generic"),
        param("draw", '**size** ("ReadOnly"["int"]) -- the size', id="key-redeclared-over-its-base"),
    ],
)
@mark.sphinx("text", testroot="typed-dict")
def test_typed_dict_unpacked_key(build_text: BuildText, function: str, expected: str) -> None:
    lines = [line.strip() for line in build_text(f".. autofunction:: typed_dict_module.{function}").splitlines()]
    assert expected in lines


@mark.sphinx("text", testroot="typed-dict")
def test_typed_dict_unpacked_key_with_metadata_that_cannot_be_compared(
    build_text: BuildText, monkeypatch: MonkeyPatch
) -> None:
    # a fresh import evaluates the metadata anew for each class holding it
    monkeypatch.delitem(modules, "typed_dict_module", raising=False)
    lines = [line.strip() for line in build_text(".. autofunction:: typed_dict_module.pack").splitlines()]
    assert [line for line in lines if line.startswith("* **")] == [
        '* **width** ("int") -- the width',
        '* **height** ("int") -- the height',
    ]


@mark.parametrize(
    ("owner", "expected"),
    [
        param(attrgetter("Movie"), {"title": str, "year": NotRequired[int]}, id="typed-dict"),
        param(attrgetter("Broken"), {}, id="annotation-that-fails"),
        param(attrgetter("Open"), {}, id="no-items"),
        param(lambda _: dict[str, int], {}, id="no-typed-dict"),
    ],
)
def test_typed_dict_keys(
    typed_dicts: ModuleType,
    owner: Callable[[ModuleType], type | GenericAlias],
    expected: dict[str, Annotation],
) -> None:
    assert typed_dict_keys(owner(typed_dicts), {}) == expected


@fixture(name="typed_dicts")
def typed_dicts_fixture(make_module: Callable[[str], ModuleType]) -> ModuleType:
    return make_module(
        dedent("""\
            from __future__ import annotations
            from typing import NotRequired, TypedDict

            from typing_extensions import TypedDict as ExtensionsTypedDict

            class Movie(TypedDict):
                title: str
                year: NotRequired[int]

            class Broken(TypedDict):
                missing: Undefined

            class Closed(ExtensionsTypedDict, closed=True):
                name: str

            class ClosedChild(Closed): ...

            class Reopened(Closed, closed=False): ...

            class Extra(ExtensionsTypedDict, extra_items=int): ...

            class ExtraChild(Extra): ...

            class Open(ExtensionsTypedDict): ...
        """)
    )


# below Python 3.14 a runtime-checkable Protocol check gave typing's metaclasses an `__annotations__`, after which a
# Protocol subclass declaring none read its base's as its own, so autodoc listed them as the subclass's members
def test_typed_dict_keys_leaves_a_protocol_subclass_without_annotations() -> None:
    class Tracer(Protocol):
        data: dict[str, int]

    class PyTracer(Tracer): ...

    assert (typed_dict_keys(PyTracer, {}), PyTracer.__annotations__) == ({}, {})


@mark.parametrize(
    ("owner", "expected"),
    [
        param("Closed", Never, id="closed"),
        param("ClosedChild", Never, id="closed-base"),
        param("Extra", int, id="extra-items"),
        param("ExtraChild", int, id="extra-items-of-a-base"),
    ],
)
def test_extra_items_type(typed_dicts: ModuleType, owner: str, expected: Annotation) -> None:
    assert extra_items_type(getattr(typed_dicts, owner), set()) is expected


@mark.parametrize(
    "owner",
    [
        param(attrgetter("Reopened"), id="reopened"),
        param(attrgetter("Open"), id="open"),
        param(attrgetter("Movie"), id="typing-typed-dict"),
        param(lambda _: dict, id="no-typed-dict"),
    ],
)
def test_extra_items_type_of_an_open_typed_dict(typed_dicts: ModuleType, owner: Callable[[ModuleType], type]) -> None:
    assert extra_items_type(owner(typed_dicts), set()) is OPEN


@mark.parametrize(
    ("rst", "counter", "expected"),
    [
        # Root and the diamonds over it, each with its left and right
        param(".. autofunction:: typed_dict_module.nest", "Counted.created", 1 + 3 * 10, id="unpacked-from-diamonds"),
        # the diamonds and their left and right, and autodoc once reading the members of the one documented
        param(".. autoclass:: typed_dict_module.Spread", "Unstated.asked", 3 * 10 + 1, id="extra-items-type"),
    ],
)
@mark.sphinx("text", testroot="typed-dict")
def test_typed_dict_reads_each_base_once(
    build_text: BuildText, monkeypatch: MonkeyPatch, rst: str, counter: str, expected: int
) -> None:
    # importing runs no annotation, so a fresh import starts the count at what the build reads
    monkeypatch.delitem(modules, "typed_dict_module", raising=False)
    build_text(rst)
    assert attrgetter(counter)(modules["typed_dict_module"]) == expected
