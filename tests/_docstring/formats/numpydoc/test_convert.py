from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, fixture, mark, param

from _docstring.conftest import BOOL, FLOAT, INT, STR
from sphinx_autodoc_typehints._docstring.formats.numpydoc.convert import convert_to_field_list, is_numpydoc_section

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from conftest import BuildText, MakeModule

    from _docstring.conftest import Process

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


@mark.parametrize(
    ("lines", "expected"),
    [
        param(
            [
                "",
                "Summary.",
                "",
                ":Parameters:",
                "",
                "    **x** : int",
                "        The x value.",
                "",
                "    **y** : str",
                "        The y value.",
                "",
            ],
            [
                "",
                "Summary.",
                "",
                ":param x: The x value.",
                ":type x: int",
                ":param y: The y value.",
                ":type y: str",
                "",
            ],
            id="parameters",
        ),
        param(
            [":Parameters:", "    **x** : int", "        The x value.", ""],
            [":param x: The x value.", ":type x: int", ""],
            id="parameters-without-a-blank-line",
        ),
        param(
            [":Parameters:", "", "    **x**", "        The x value.", ""],
            [":param x: The x value.", ""],
            id="parameter-without-type",
        ),
        param(
            [":Parameters:", "", "    **x** : int", ""],
            [":param x:", ":type x: int", ""],
            id="parameter-without-description",
        ),
        param(
            [":Parameters:", "", "    **x** : int", "        The x value.", "not an entry"],
            [":param x: The x value.", ":type x: int", "not an entry"],
            id="parameters-ended-by-text",
        ),
        param(
            [":Returns:", "", "    **result** : str", "        The combined result.", ""],
            [":returns: **result** (str) -- The combined result.", ""],
            id="named-return",
        ),
        param(
            [":Returns:", "", "    **result** : str", ""],
            [":returns: **result** (str)", ""],
            id="named-return-undescribed",
        ),
        param(
            [":Returns:", "", "    str", "        A greeting.", ""],
            [":rtype: str", ":returns: A greeting.", ""],
            id="unnamed-return",
        ),
        param(
            [":Returns:", "", "    str or bytes", "        The payload.", ""],
            [":rtype: str or bytes", ":returns: The payload.", ""],
            id="multiword-return",
        ),
        param([":Returns:", "", "    str", "        ..", ""], [":rtype: str", ""], id="unnamed-return-undescribed"),
        param(
            [
                ":Returns:",
                "",
                "    **name** : str",
                "        The name.",
                "",
                "    **value** : int",
                "        The value.",
                "",
            ],
            [":returns:", "   * **name** (str) -- The name.", "   * **value** (int) -- The value.", ""],
            id="returns",
        ),
        param(
            [
                ":Raises:",
                "",
                "    ValueError",
                "        If x is negative.",
                "",
                "    TypeError",
                "        If x is not an integer.",
                "",
            ],
            [":raises ValueError: If x is negative.", ":raises TypeError: If x is not an integer.", ""],
            id="raises",
        ),
        param(
            [":Raises:", "", "    **err** : ValueError", "        If something is wrong.", ""],
            [":raises err: If something is wrong.", ""],
            id="named-raise",
        ),
        param(
            [
                ":Yields:",
                "",
                "    **name** : str",
                "        The name.",
                "",
                "    **value** : int",
                "        The value.",
                "",
            ],
            [":Yields:", "   * **name** (str) -- The name.", "   * **value** (int) -- The value.", ""],
            id="yields",
        ),
        param(
            [":Yields:", "", "    **result** : int", "", ":Parameters:", "", "    **x** : int", "        The x.", ""],
            [":Yields: **result** (int)", "", ":param x: The x.", ":type x: int", ""],
            id="undescribed-yield-before-parameters",
        ),
        param(
            [":Other Parameters:", "", "    **flag** : bool", "        A flag.", ""],
            [":Other Parameters: **flag** (bool) -- A flag.", ""],
            id="other-parameters",
        ),
        param(
            [":Other Parameters:", "", "    **x, y** : int", "        Shared.", ""],
            [":Other Parameters:", "   * **x** (int) -- Shared.", "   * **y** (int) -- Shared.", ""],
            id="other-parameters-sharing-a-line",
        ),
        param(
            [
                "Summary.",
                "",
                ":Parameters:",
                "",
                "    **x** : int",
                "        The x value.",
                "",
                ":Returns:",
                "",
                "    **result** : str",
                "        The result.",
                "",
                ":Raises:",
                "",
                "    ValueError",
                "        If bad.",
                "",
            ],
            [
                "Summary.",
                "",
                ":param x: The x value.",
                ":type x: int",
                "",
                ":returns: **result** (str) -- The result.",
                "",
                ":raises ValueError: If bad.",
                "",
            ],
            id="several-sections",
        ),
        param(
            ["", "A normal docstring.", "", ":param x: The x value.", ":type x: int"],
            ["", "A normal docstring.", "", ":param x: The x value.", ":type x: int"],
            id="field-list",
        ),
        param([":Returns:", "    The result."], [":Returns:", "    The result."], id="manual-returns-field"),
        param([":Returns:", "    Result"], [":Returns:", "    Result"], id="manual-returns-single-word"),
    ],
)
def test_convert_to_field_list(lines: list[str], expected: list[str]) -> None:
    convert_to_field_list(lines)
    assert lines == expected


@mark.parametrize(
    ("lines", "expected"),
    [
        param([":Parameters:", "", "    **x** : int"], True, id="bold-parameter"),
        param([":Returns:", "    int", "        .."], True, id="plain-return"),
        param([":Returns:", "    str or bytes", "        The result."], True, id="multiword-return"),
        param([":Returns:", "    Result"], False, id="manual-single-word-description"),
        param([":Returns:", "    The result."], False, id="manual-return-description"),
        param([":Parameters:", "    x : int"], False, id="plain-parameter"),
        param([":Notes:", "    **x** : int"], False, id="other-field"),
        param([":Returns:"], False, id="empty"),
    ],
)
def test_is_numpydoc_section(lines: list[str], expected: bool) -> None:
    assert is_numpydoc_section(lines, 0) is expected


@mark.parametrize(
    ("name", "expected"),
    [
        param(
            "simple_func",
            dedent("""\
                convert_numpydoc.simple_func(x, y)

                   Do something simple.

                   Parameters:
                      * **x** ("int") -- The x value.

                      * **y** ("str") -- The y value.

                   Return type:
                      "str"

                   Returns:
                      **result** (str) -- The combined result.
            """),
            id="params-and-return",
        ),
        param(
            "raises_func",
            dedent("""\
                convert_numpydoc.raises_func(x)

                   Raise on bad input.

                   Parameters:
                      **x** ("int") -- The input value.

                   Raises:
                      * **ValueError** -- If x is negative.

                      * **TypeError** -- If x is not an integer.

                   Return type:
                      "None"
            """),
            id="raises",
        ),
        param(
            "multi_return",
            dedent("""\
                convert_numpydoc.multi_return(x)

                   Return two values.

                   Parameters:
                      **x** ("int") -- The input.

                   Return type:
                      "tuple"["str", "int"]

                   Returns:
                      * **name** (str) -- The name.

                      * **value** (int) -- The value.
            """),
            id="returns",
        ),
        param(
            "no_params",
            dedent("""\
                convert_numpydoc.no_params()

                   Greet.

                   Return type:
                      "str"

                   Returns:
                      A greeting.
            """),
            id="unnamed-return",
        ),
    ],
)
@mark.sphinx("text", testroot="numpydoc")
def test_numpydoc_docstring_keeps_its_types(build_numpydoc: Callable[[str], str], name: str, expected: str) -> None:
    assert build_numpydoc(name) == expected


@mark.sphinx("text", testroot="numpydoc")
def test_manual_returns_field_keeps_its_description(build_text: BuildText, make_module: MakeModule) -> None:
    make_module(
        "manual_return",
        dedent('''\
            def answer() -> int:
                """Return a value.

                :Returns:
                    The result.
                """
                return 1
        '''),
    )
    output = build_text(".. autofunction:: manual_return.answer")
    assert "The result." in output


@mark.sphinx("text", testroot="numpydoc")
def test_numpydoc_multiword_return_type_keeps_the_description(build_text: BuildText, make_module: MakeModule) -> None:
    make_module(
        "multiword_return",
        dedent('''\
            def answer() -> str | bytes:
                """Return a value.

                Returns
                -------
                str or bytes
                    The payload.
                """
                return "value"
        '''),
    )
    output = build_text(".. autofunction:: multiword_return.answer")
    assert "The payload." in output
    assert "str or bytes" not in output


@fixture(name="build_numpydoc")
def build_numpydoc_fixture(build_text: BuildText, make_module: MakeModule) -> Callable[[str], str]:
    make_module(
        "convert_numpydoc",
        dedent("""\
            def simple_func(x: int, y: str) -> str:
                \"""
                Do something simple.

                Parameters
                ----------
                x : int
                    The x value.
                y : str
                    The y value.

                Returns
                -------
                result : str
                    The combined result.
                \"""


            def raises_func(x: int) -> None:
                \"""
                Raise on bad input.

                Parameters
                ----------
                x : int
                    The input value.

                Raises
                ------
                ValueError
                    If x is negative.
                TypeError
                    If x is not an integer.
                \"""


            def multi_return(x: int) -> tuple[str, int]:
                \"""
                Return two values.

                Parameters
                ----------
                x : int
                    The input.

                Returns
                -------
                name : str
                    The name.
                value : int
                    The value.
                \"""


            def no_params() -> str:
                \"""
                Greet.

                Returns
                -------
                str
                    A greeting.
                \"""
        """),
    )
    return lambda name: build_text(f".. autofunction:: convert_numpydoc.{name}")


@mark.parametrize(
    ("body", "expected"),
    [
        param(["The first,", "wrapped."], [":param first: The first,", "   wrapped."], id="wrapped"),
        param(
            ["The first.", "", "More about it."],
            [":param first: The first.", "", "   More about it."],
            id="paragraphs",
        ),
        param(
            ["The first, one of:", "", "- a", "- b"],
            [":param first: The first, one of:", "", "   - a", "   - b"],
            id="list",
        ),
    ],
)
@mark.sphinx(confoverrides={"typehints_document_rtype": False})
def test_numpydoc_description_keeps_its_blocks(process: Process, body: list[str], expected: list[str]) -> None:
    def two_params(first: int, second: str) -> None: ...

    # numpydoc indents the blank line separating the blocks
    lines = [
        ":Parameters:",
        "",
        "    **first** : int",
        *(f"        {line}" for line in body),
        "",
        "    **second** : str",
        "        The second.",
        "",
    ]
    assert process("function", "mod.two_params", two_params, lines) == [
        *expected,
        f":type first: {INT}",
        ":param second: The second.",
        f":type second: {STR}",
        "",
    ]


@mark.sphinx(confoverrides={"typehints_document_rtype": False})
def test_numpydoc_params_sharing_a_type_line(process: Process) -> None:
    def coordinates(lat: int, lon: int) -> None: ...

    lines = [":Parameters:", "", "    **lat, lon** : int", "        The coordinates.", ""]
    assert process("function", "mod.coordinates", coordinates, lines) == [
        ":param lat: The coordinates.",
        f":type lat: {INT}",
        ":param lon: The coordinates.",
        f":type lon: {INT}",
        "",
    ]


@mark.parametrize(
    ("entry", "description", "expected"),
    [
        param("    int", "        A number.", ":Yields: int -- A number.", id="unnamed"),
        param("    **item** : int", "        A number.", ":Yields: **item** (int) -- A number.", id="named"),
        param("    **item**", "        A number.", ":Yields: **item** -- A number.", id="named-untyped"),
        param("    int", "        ..", ":Yields: int", id="placeholder-description"),
    ],
)
def test_numpydoc_single_yield_keeps_its_type(process: Process, entry: str, description: str, expected: str) -> None:
    def counter(bound: int) -> Iterator[int]: ...

    lines = [
        ":Parameters:",
        "",
        "    **bound** : int",
        "        The bound.",
        "",
        ":Yields:",
        "",
        entry,
        description,
        "",
    ]
    assert process("function", "mod.counter", counter, lines) == [
        ":param bound: The bound.",
        f":type bound: {INT}",
        "",
        expected,
        "",
    ]


def test_numpydoc_returns_without_descriptions(process: Process) -> None:
    def pair(bound: int) -> tuple[int, str]: ...

    lines = [":Returns:", "", "    **x** : int", "        ..", "    **y** : str", "        ..", ""]
    assert process("function", "mod.pair", pair, lines) == [
        (
            r":rtype: :sphinx_autodoc_typehints_type:`\:py\:class\:\`tuple\`\\ \\\[\:py\:class\:\`int\`\, "
            r"\:py\:class\:\`str\`\]`"
        ),
        ":returns:",
        "   * **x** (int)",
        "   * **y** (str)",
        "",
    ]


def _annotated_ratio(value: int) -> float: ...


@mark.parametrize(
    ("func", "rtype"),
    [
        param(_annotated_ratio, FLOAT, id="annotated"),
        param(lambda value: value, "float", id="unannotated"),
    ],
)
def test_numpydoc_unnamed_return_keeps_its_type(process: Process, func: Callable[..., object], rtype: str) -> None:
    lines = [":Returns:", "", "    float", "        The ratio.", ""]
    assert process("function", "mod.ratio", func, lines) == [f":rtype: {rtype}", ":returns: The ratio.", ""]


@mark.sphinx(confoverrides={"typehints_document_rtype": False})
def test_numpydoc_other_parameters_keep_their_section(process: Process) -> None:
    def tune(size: int, *, flag: bool = False, width: int = 0, height: int = 0) -> None: ...

    lines = [
        ":Parameters:",
        "",
        "    **size**",
        "        The size.",
        "",
        ":Other Parameters:",
        "",
        "    **flag**",
        "        A flag.",
        "    **width, height** : int",
        "        Shared.",
        "",
    ]
    assert process("function", "mod.tune", tune, lines) == [
        f":type size: {INT}",
        ":param size: The size.",
        "",
        ":Other Parameters:",
        f"   * **flag** ({BOOL}) -- A flag.",
        "   * **width** (int) -- Shared.",
        "   * **height** (int) -- Shared.",
        "",
    ]


@mark.parametrize(
    "body",
    [
        param(
            [
                "    `name` : str",
                "        The name,",
                "        on two lines.",
                "    `count` : int",
                "        How many.",
            ],
            id="definition-list",
        ),
        param(
            ["    - `name` -- the name, which goes on", "      for two lines.", "    - `count` -- how many."],
            id="bullets",
        ),
    ],
)
@mark.sphinx(confoverrides={"typehints_document_rtype": False})
def test_docutils_parameters_field_stays_as_written(process: Process, body: list[str]) -> None:
    def scale(name: str, count: int) -> None: ...

    lines = ["Summary.", "", ":Parameters:", *body, ""]
    assert process("function", "mod.scale", scale, lines) == ["Summary.", "", ":Parameters:", *body, ""]
