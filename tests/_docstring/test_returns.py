from __future__ import annotations

import typing  # its generator aliases are tested next to the collections.abc ones
from textwrap import dedent
from typing import TYPE_CHECKING, Annotated, Final

from pytest import MarkDecorator, fixture, mark, param
from typing_extensions import Doc

from _docstring.conftest import INT, STR, hide_type
from sphinx_autodoc_typehints._docstring.returns import description_from_doc

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Generator, Iterable, Iterator

    from conftest import BuildText, MakeModule

    from _docstring.conftest import Process
    from sphinx_autodoc_typehints._types import Annotation, Documented

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


@mark.parametrize(
    ("annotation", "expected"),
    [
        param(Annotated[int, Doc("hello")], "hello", id="annotated-with-doc"),
        param(Annotated[int, 42], None, id="annotated-without-doc"),
        param(int, None, id="plain-type"),
        param(Annotated[int, Doc("first"), Doc("second")], "first", id="picks-first-doc"),
    ],
)
def test_description_from_doc(annotation: Annotation, expected: str | None) -> None:
    assert description_from_doc(annotation) == expected


@mark.parametrize(
    ("func_name", "expected"),
    [
        param(
            "greet",
            dedent("""\
                mod.greet(name, greeting)

                   Say hello.

                   Parameters:
                      * **name** ("str") -- The person's name

                      * **greeting** ("str") -- The greeting phrase

                   Return type:
                      "str"

                   Returns:
                      The full greeting message
            """),
            id="all-params-and-return",
            marks=mark.sphinx("text", testroot="annotated-doc"),
        ),
        param(
            "partial_doc",
            dedent("""\
                mod.partial_doc(x, y)

                   Compute sum.

                   Parameters:
                      * **x** ("int") -- The x value

                      * **y** ("int") -- The y value

                   Return type:
                      "int"
            """),
            id="partial-doc-with-docstring",
            marks=mark.sphinx("text", testroot="annotated-doc"),
        ),
        param(
            "no_doc",
            dedent("""\
                mod.no_doc(x)

                   Identity.

                   Return type:
                      "int"
            """),
            id="annotated-without-doc-metadata",
            marks=mark.sphinx("text", testroot="annotated-doc"),
        ),
        param(
            "docstring_wins",
            dedent("""\
                mod.docstring_wins(x)

                   Override.

                   Parameters:
                      **x** ("int") -- Docstring description

                   Return type:
                      "int"
            """),
            id="docstring-takes-precedence",
            marks=mark.sphinx("text", testroot="annotated-doc"),
        ),
        param(
            "transform",
            dedent("""\
                mod.transform(data)

                   Transform data.

                   Parameters:
                      **data** ("str") -- The input data

                   Return type:
                      "str"

                   Returns:
                      The transformed result
            """),
            id="doc-injected",
            marks=mark.sphinx("text", testroot="annotated-doc-numpydoc"),
        ),
        param(
            "compute",
            dedent("""\
                mod.compute(x, y)

                   Compute the sum.

                   Parameters:
                      * **x** ("int") -- Placeholder.

                      * **y** ("int") -- Placeholder.

                   Return type:
                      "int"

                   Returns:
                      The sum
            """),
            id="existing-params-preserved",
            marks=mark.sphinx("text", testroot="annotated-doc-numpydoc"),
        ),
        param(
            "count",
            dedent("""\
                mod.count()

                   Count the items.

                   Return type:
                      "int"

                   Returns:
                      Number of items.
            """),
            id="docstring-return-without-params",
            marks=mark.sphinx("text", testroot="annotated-doc-numpydoc"),
        ),
    ],
)
@mark.usefixtures("fresh_mod")
def test_doc_describes_what_the_docstring_leaves_out(build_text: BuildText, func_name: str, expected: str) -> None:
    assert build_text(f".. autofunction:: mod.{func_name}") == expected


@mark.parametrize(
    ("name", "expected"),
    [
        param(
            "strings",
            dedent("""\
                returns_generators.strings(arg1=None)

                   Summary.

                   Parameters:
                      **arg1** ("int" | "None") -- argument 1

                   Yields:
                      "tuple"["str", "..."] -- strings of things
            """),
            id="generator",
        ),
        param(
            "integers",
            dedent("""\
                returns_generators.integers()

                   Summary.

                   Yields:
                      "int" -- the integers
            """),
            id="iterator",
        ),
        param(
            "async_strings",
            dedent("""\
                async returns_generators.async_strings()

                   Summary.

                   Yields:
                      "str" -- the strings
            """),
            id="async-generator",
        ),
        param(
            "async_integers",
            dedent("""\
                async returns_generators.async_integers()

                   Summary.

                   Yields:
                      "int" -- the integers
            """),
            id="async-iterator",
        ),
        param(
            "without_yields",
            dedent("""\
                returns_generators.without_yields()

                   Summary without a Yields section.

                   Return type:
                      "Generator"["int", "None", "None"]
            """),
            id="without-yields",
        ),
        param(
            "returning",
            dedent("""\
                returns_generators.returning()

                   Summary.

                   Yields:
                      "int" -- the integers

                   Return type:
                      "bool"

                   Returns:
                      whether it finished
            """),
            id="returning",
        ),
        param(
            "returning_undescribed",
            dedent("""\
                returns_generators.returning_undescribed()

                   Summary.

                   Yields:
                      "int" -- the integers
            """),
            id="returning-undescribed",
        ),
    ],
)
def test_generator_documents_what_it_yields(build_generator: Callable[[str], str], name: str, expected: str) -> None:
    assert build_generator(name) == expected


@fixture(name="build_generator")
def build_generator_fixture(build_text: BuildText, make_module: MakeModule) -> Callable[[str], str]:
    make_module(
        "returns_generators",
        dedent("""\
            from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator


            def strings(arg1: int | None = None) -> Generator[tuple[str, ...], None, None]:
                \"""
                Summary.

                Args:
                    arg1: argument 1

                Yields:
                    strings of things
                \"""


            def integers() -> Iterator[int]:
                \"""
                Summary.

                Yields:
                    the integers
                \"""


            async def async_strings() -> AsyncGenerator[str, None]:
                \"""
                Summary.

                Yields:
                    the strings
                \"""


            async def async_integers() -> AsyncIterator[int]:
                \"""
                Summary.

                Yields:
                    the integers
                \"""


            def without_yields() -> Generator[int, None, None]:
                \"""Summary without a Yields section.\"""


            def returning() -> Generator[int, None, bool]:
                \"""
                Summary.

                Yields:
                    the integers

                Returns:
                    whether it finished
                \"""


            def returning_undescribed() -> Generator[int, None, bool]:
                \"""
                Summary.

                Yields:
                    the integers
                \"""
        """),
    )
    return lambda name: build_text(f".. autofunction:: returns_generators.{name}")


def _counts() -> Iterator[int]: ...


@mark.parametrize(
    ("lines", "expected"),
    [
        param([":yields: the numbers"], [f":yields: {INT} -- the numbers"], id="description"),
        param(
            [":yields:", "    - one", "    - two"],
            [f":yields: {INT} --", "", "    - one", "    - two"],
            id="description-on-the-next-line",
        ),
        param([":yield: the numbers"], [f":yield: {INT} -- the numbers"], id="yield"),
        param([":Yields: *int* -- the numbers"], [":Yields: *int* -- the numbers"], id="typed-by-napoleon"),
        param([":Yields: int"], [":Yields: int"], id="type-only"),
        param([":Yields: * **a** -- first"], [":Yields: * **a** -- first"], id="several-entries"),
        param(
            [":Yields:", "", "    str", "        the key", "    int", "        its count", ""],
            [":Yields:", "   * str -- the key", "   * int -- its count", ""],
            id="several-numpydoc-entries",
        ),
    ],
)
def test_yields_entry_gets_the_yielded_type(process: Process, lines: list[str], expected: list[str]) -> None:
    assert process("function", "mod.counts", _counts, lines) == expected


def _documented_counts() -> Annotated[Iterator[int], Doc("the numbers")]: ...


@mark.parametrize(
    ("lines", "expected"),
    [
        param([":Yields:"], [f":Yields: {INT} -- the numbers"], id="empty"),
        param(
            [":Yields:", ":param limit: where to stop"],
            [f":Yields: {INT} -- the numbers", ":param limit: where to stop"],
            id="empty-before-a-field",
        ),
        param([":Yields: int"], [":Yields: int -- the numbers"], id="type-only"),
        param([":Yields: *int*"], [":Yields: *int* -- the numbers"], id="type-only-by-napoleon"),
        param([":yields: the integers"], [f":yields: {INT} -- the integers"], id="own-description"),
        param([":Yields: *int* -- the integers"], [":Yields: *int* -- the integers"], id="typed-own-description"),
        param(
            [":yields:", "    - one", "    - two"],
            [f":yields: {INT} --", "", "    - one", "    - two"],
            id="own-description-on-the-next-line",
        ),
    ],
)
def test_yields_entry_takes_the_doc_description(process: Process, lines: list[str], expected: list[str]) -> None:
    assert process("function", "mod.counts", _documented_counts, lines) == expected


def test_untyped_yields_entry_takes_the_doc_description(process: Process) -> None:
    def produce() -> Annotated[Iterator, Doc("the numbers")]: ...

    assert process("function", "mod.produce", produce, [":Yields:"]) == [":Yields: the numbers"]


@mark.sphinx(confoverrides={"typehints_formatter": hide_type})
def test_yields_entry_stays_untyped_when_a_formatter_hides_the_type(process: Process) -> None:
    assert process("function", "mod.counts", _counts, [":yields: the numbers"]) == [":yields: the numbers"]


def _async_counts() -> typing.AsyncGenerator[int, None]: ...


def _bare_async() -> AsyncIterator: ...


def _names() -> list[Annotated[str, {"max_length": 10}]]: ...


def _iterable() -> Iterable[int]: ...


@mark.parametrize(
    ("func", "expected"),
    [
        param(_async_counts, [f":yields: {INT} -- the numbers"], id="async-generator"),
        param(_bare_async, [":yields: the numbers"], id="bare-async-iterator"),
        param(
            _iterable,
            [
                ":yields: the numbers",
                "",
                (
                    r":rtype: :sphinx_autodoc_typehints_type:`\:py\:class\:\`\~collections.abc.Iterable\`\\ "
                    r"\\\[\:py\:class\:\`int\`\]`"
                ),
            ],
            id="iterable",
        ),
        param(
            _names,
            [
                ":yields: the numbers",
                "",
                r":rtype: :sphinx_autodoc_typehints_type:`\:py\:class\:\`list\`\\ \\\[\:py\:class\:\`str\`\]`",
            ],
            id="no-generator",
        ),
    ],
)
def test_yields_entry_types_only_a_generator(process: Process, func: Callable[[], object], expected: list[str]) -> None:
    assert process("function", "mod.produce", func, [":yields: the numbers"]) == expected


def _annotated_counts() -> Annotated[Iterator[int], "meters"]: ...


def _annotated_returning() -> Annotated[Generator[int, None, str], "meta"]: ...


def _returning_nothing() -> Generator[int, None, None]: ...


def _bare() -> typing.Generator: ...


@mark.parametrize(
    ("func", "lines", "expected"),
    [
        param(_annotated_counts, [":yields: the numbers"], [f":yields: {INT} -- the numbers"], id="annotated"),
        param(
            _annotated_returning,
            [":yields: the numbers", ":returns: a name"],
            [f":yields: {INT} -- the numbers", "", f":rtype: {STR}", ":returns: a name"],
            id="annotated-returning",
        ),
        param(
            _returning_nothing,
            [":yields: the numbers", ":returns: nothing"],
            [f":yields: {INT} -- the numbers", ":returns: nothing"],
            id="returning-none",
        ),
        param(
            _bare,
            [":yields: the numbers", ":returns: nothing"],
            [":yields: the numbers", ":returns: nothing"],
            id="bare",
        ),
    ],
)
def test_generator_return_type(
    process: Process, func: Callable[[], object], lines: list[str], expected: list[str]
) -> None:
    assert process("function", "mod.generator", func, lines) == expected


@mark.sphinx(confoverrides={"typehints_document_rtype_none": False})
def test_described_none_return_keeps_its_description(process: Process) -> None:
    def returns_described_none() -> Annotated[None, Doc("nothing at all")]: ...

    assert process("function", "mod.returns_described_none", returns_described_none, []) == [":return: nothing at all"]


@mark.sphinx(confoverrides={"typehints_formatter": hide_type})
def test_return_type_hidden_by_formatter(process: Process) -> None:
    def double(value: int) -> int: ...

    lines = ["Summary.", "", ":returns: twice the value"]
    assert process("function", "mod.double", double, lines.copy()) == lines


class _Sized:
    def __init__(self, size: int) -> None: ...

    @property
    def size(self) -> int: ...


@mark.parametrize(
    ("what", "name", "obj"),
    [
        param("class", "mod.Sized", _Sized, id="class"),
        param("method", "mod.Sized.__init__", _Sized.__init__, id="constructor"),
        param("property", "mod.Sized.size", vars(_Sized)["size"], id="property"),
        param(
            "function",
            "mod.counts",
            _counts,
            id="disabled",
            marks=mark.sphinx(confoverrides={"typehints_document_rtype": False}),
        ),
    ],
)
def test_return_type_left_out(process: Process, what: str, name: str, obj: Documented) -> None:
    assert process(what, name, obj, ["Summary."]) == ["Summary."]


@mark.parametrize(
    ("name", "expected"),
    [
        param(
            "function_no_returns",
            dedent("""\
                dummy_module_simple_no_use_rtype.function_no_returns(x, y=1)

                   Function docstring.

                   Parameters:
                      * **x** ("bool") -- foo.

                      * **y** ("int") -- bar.

                   Return type:
                      "str"
            """),
            id="no-returns-field",
        ),
        param(
            "function_returns_with_type",
            dedent("""\
                dummy_module_simple_no_use_rtype.function_returns_with_type(x, y=1)

                   Function docstring.

                   Parameters:
                      * **x** ("bool") -- foo.

                      * **y** ("int") -- bar.

                   Returns:
                      *CustomType* -- A string
            """),
            id="returns-field-typed",
        ),
        param(
            "function_returns_with_compound_type",
            dedent("""\
                dummy_module_simple_no_use_rtype.function_returns_with_compound_type(x, y=1)

                   Function docstring.

                   Parameters:
                      * **x** ("bool") -- foo.

                      * **y** ("int") -- bar.

                   Returns:
                      Union[str, int] -- A string or int
            """),
            id="returns-field-typed-with-a-compound-type",
        ),
        param(
            "function_returns_without_type",
            dedent("""\
                dummy_module_simple_no_use_rtype.function_returns_without_type(x, y=1)

                   Function docstring.

                   Parameters:
                      * **x** ("bool") -- foo.

                      * **y** ("int") -- bar.

                   Returns:
                      "str" -- A string
            """),
            id="returns-field-untyped",
        ),
    ],
)
@mark.sphinx(confoverrides={"typehints_use_rtype": False})
def test_return_type_joins_the_returns_field_without_rtype(build_text: BuildText, name: str, expected: str) -> None:
    assert build_text(f".. autofunction:: dummy_module_simple_no_use_rtype.{name}") == expected


@mark.usefixtures("native_pkg")
@mark.sphinx("text", testroot="pyi-stubs")
def test_return_type_of_a_function_without_a_signature_comes_from_its_stub(build_text: BuildText) -> None:
    assert build_text(".. autofunction:: native_pkg.warc.raw_parse") == dedent("""\
        native_pkg.warc.raw_parse()

           Parse WARC records.

           Parameters:
              **data** -- input bytes

           Return type:
              "Iterator"["WarcRecord"]
        """)
