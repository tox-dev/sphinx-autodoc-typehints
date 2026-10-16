from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, mark, param

from _docstring.conftest import INT, STR
from sphinx_autodoc_typehints._docstring.formats.base import InsertIndexInfo
from sphinx_autodoc_typehints._docstring.formats.field_list import (
    FieldListFormat,
    write_rtype,
)
from sphinx_autodoc_typehints._docstring.formats.field_list.rtype import RTYPE_MARKER

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp

    from _docstring.conftest import Process

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


@mark.parametrize(
    ("lines", "expected"),
    [
        param(["Summary.", "", ":param x: the x"], 2, id="param"),
        param([":keyword x: the x"], 0, id="keyword"),
        param([r":param \*x: the x"], 0, id="starred"),
        param([":param int x: the x"], 0, id="typed"),
        param([":parameter x: the x"], 0, id="parameter"),
        param([":arg x: the x"], 0, id="arg"),
        param([":argument x: the x"], 0, id="argument"),
        param([":kwarg x: the x"], 0, id="kwarg"),
        param([":kwparam x: the x"], 0, id="kwparam"),
        param([r":param \*\*x: the x"], 0, id="double-starred"),
        param([":param xy: the xy", ":type x: int"], None, id="other-name"),
        param([":param: the x"], None, id="no-name"),
        param(["    :param x: in a block"], None, id="indented"),
    ],
)
def test_find_param(lines: list[str], expected: int | None) -> None:
    assert FieldListFormat().find_param(lines, "x") == expected


@mark.parametrize(
    ("lines", "before", "expected"),
    [
        param([":param y: the y"], 0, [":param x: the x", ":param y: the y"], id="before-a-later-param"),
        param(
            [":param w: the w", "   more", ":type w: int", "", "Example."],
            None,
            [":param w: the w", "   more", ":type w: int", ":param x: the x", "", "Example."],
            id="after-the-last-param",
        ),
        param(
            [":kwarg w: the w", "", "Example."],
            None,
            [":kwarg w: the w", ":param x: the x", "", "Example."],
            id="after-the-last-keyword",
        ),
        param(["Summary."], None, ["Summary.", "", ":param x: the x"], id="after-text"),
        param(["Summary.", ""], None, ["Summary.", "", ":param x: the x"], id="after-a-blank-line"),
        param([], None, [":param x: the x"], id="empty"),
    ],
)
def test_add_undocumented_param(lines: list[str], before: int | None, expected: list[str]) -> None:
    at = FieldListFormat().add_undocumented_param(lines, "x", "the x", before=before)
    assert (lines, lines[at]) == (expected, ":param x: the x")


def test_add_undocumented_param_as_a_keyword_without_description() -> None:
    lines: list[str] = []
    FieldListFormat().add_undocumented_param(lines, "x", field="keyword")
    assert lines == [":keyword x:"]


@mark.parametrize(
    ("lines", "expected"),
    [
        param([":return: it"], True, id="return"),
        param([":returns: it"], True, id="returns"),
        param([":rtype: int", ":param x: the x"], False, id="none"),
    ],
)
def test_has_return_description(lines: list[str], expected: bool) -> None:
    assert FieldListFormat().has_return_description(lines) is expected


@mark.parametrize(
    ("lines", "use_rtype", "expected_info", "expected_lines"),
    [
        param(
            [":returns: it", ":rtype: str", "   on two lines", "Closing."],
            True,
            InsertIndexInfo(insert_index=1),
            [":returns: it", "Closing."],
            id="rtype-replaced",
        ),
        param(
            [":param x: the x", ":rtype: str"],
            False,
            InsertIndexInfo(insert_index=1),
            [":param x: the x"],
            id="rtype-replaced-without-return",
        ),
        param(
            [":returns: it", ":rtype: str"],
            False,
            InsertIndexInfo(insert_index=0, found_return=True, found_rtype=True),
            [":returns: it"],
            id="return-beside-rtype-inline",
        ),
        param(
            ["Summary.", "", ":returns: it"],
            True,
            InsertIndexInfo(insert_index=2, found_return=True),
            ["Summary.", "", ":returns: it"],
            id="return",
        ),
        param(
            ["Summary.", "", ":param x: the x", "", "Closing."],
            True,
            InsertIndexInfo(insert_index=5, deferred=True),
            ["Summary.", "", ":param x: the x", "", "Closing."],
            id="param-field-list",
        ),
        param(
            [":var x: some variable"],
            True,
            InsertIndexInfo(insert_index=1, deferred=True),
            [":var x: some variable"],
            id="field-list-without-params",
        ),
        param(
            ["Summary.", "", "More."],
            True,
            InsertIndexInfo(insert_index=3, deferred=True),
            ["Summary.", "", "More."],
            id="text",
        ),
    ],
)
def test_get_rtype_insert_info(
    app: SphinxTestApp,
    lines: list[str],
    use_rtype: bool,
    expected_info: InsertIndexInfo,
    expected_lines: list[str],
) -> None:
    app.config.typehints_use_rtype = use_rtype
    assert (FieldListFormat().get_rtype_insert_info(app, lines), lines) == (expected_info, expected_lines)


@mark.parametrize(
    ("lines", "info", "use_rtype", "expected"),
    [
        param(
            ["A paragraph."],
            InsertIndexInfo(insert_index=1, deferred=True),
            True,
            ["A paragraph.", "", f":{RTYPE_MARKER}: str"],
            id="marked-after-text",
        ),
        param(
            ["A paragraph.", ""],
            InsertIndexInfo(insert_index=2, deferred=True),
            False,
            ["A paragraph.", "", f":{RTYPE_MARKER}: str"],
            id="marked-after-a-blank-line",
        ),
        param([], InsertIndexInfo(insert_index=0, deferred=True), True, [f":{RTYPE_MARKER}: str"], id="marked-alone"),
        param(["", ""], InsertIndexInfo(insert_index=1), True, ["", ":rtype: str", ""], id="after-a-blank-line"),
        param(
            [":returns: it"],
            InsertIndexInfo(insert_index=0, found_return=True),
            True,
            [":rtype: str", ":returns: it"],
            id="above-the-return",
        ),
        param(
            [":returns: it"],
            InsertIndexInfo(insert_index=0, found_return=True),
            False,
            [":return: str -- it"],
            id="inline",
        ),
        param(
            [":returns: int -- it"],
            InsertIndexInfo(insert_index=0, found_return=True),
            False,
            [":returns: int -- it"],
            id="inline-where-the-return-states-a-type",
        ),
        param(
            [":returns: *int* -- the value"],
            InsertIndexInfo(insert_index=0, found_return=True),
            False,
            [":returns: *int* -- the value"],
            id="inline-where-the-return-states-a-napoleon-type",
        ),
        param(
            [":returns: ``int`` -- the value"],
            InsertIndexInfo(insert_index=0, found_return=True),
            False,
            [":returns: ``int`` -- the value"],
            id="inline-where-the-return-states-a-literal-type",
        ),
        param(
            [":returns: dict[str, int] -- the value"],
            InsertIndexInfo(insert_index=0, found_return=True),
            False,
            [":returns: dict[str, int] -- the value"],
            id="inline-where-the-return-states-a-bracketed-type",
        ),
        param(
            [":returns: the value -- or None when missing"],
            InsertIndexInfo(insert_index=0, found_return=True),
            False,
            [":return: str -- the value -- or None when missing"],
            id="inline-where-the-description-has-dashes",
        ),
        param(
            [":returns: int"],
            InsertIndexInfo(insert_index=0, found_return=True),
            False,
            [":return: str -- int"],
            id="inline-where-the-return-has-no-description",
        ),
        param(
            [":returns: int -- it"],
            InsertIndexInfo(insert_index=0, found_return=True, found_rtype=True),
            False,
            [":return: str -- int -- it"],
            id="inline-where-an-rtype-stated-the-type",
        ),
        param(
            [":returns:", "   * a string"],
            InsertIndexInfo(insert_index=0, found_return=True),
            False,
            [":return: str --", "", "   * a string"],
            id="inline-before-a-block",
        ),
    ],
)
def test_write_rtype(lines: list[str], info: InsertIndexInfo, use_rtype: bool, expected: list[str]) -> None:
    write_rtype(lines, "str", info, use_rtype=use_rtype)
    assert lines == expected


@mark.parametrize(
    ("lines", "expected"),
    [
        param([":returns: A string", ":rtype: bytes"], [f":return: {STR} -- A string"], id="replaces-rtype"),
        param(
            [":returns: value -- or None when missing", ":rtype: bytes"],
            [f":return: {STR} -- value -- or None when missing"],
            id="replaces-rtype-beside-text-reading-as-a-type",
        ),
        param(
            [":returns:", "   * a string", "   * or another"],
            [f":return: {STR} --", "", "   * a string", "   * or another"],
            id="description-on-next-line",
        ),
        param([":returns: *str* -- the value"], [":returns: *str* -- the value"], id="typed-by-napoleon"),
    ],
)
@mark.sphinx(confoverrides={"typehints_use_rtype": False})
def test_return_type_inline(process: Process, lines: list[str], expected: list[str]) -> None:
    def returns_str() -> str: ...

    assert process("function", "mod.returns_str", returns_str, lines) == expected


_DICT_STR_INT: Final[str] = (
    r":sphinx_autodoc_typehints_type:`\:py\:class\:\`dict\`\\ \\\[\:py\:class\:\`str\`\, \:py\:class\:\`int\`\]`"
)


@mark.parametrize(
    ("use_rtype", "expected"),
    [
        param(
            True,
            [
                ":returns: the mapping",
                "",
                f":rtype: {_DICT_STR_INT}",
            ],
            id="rtype",
        ),
        param(
            False,
            [f":return: {_DICT_STR_INT} -- the mapping"],
            id="inline",
        ),
    ],
)
def test_return_type_replaces_a_multi_line_rtype(
    app: SphinxTestApp, process: Process, use_rtype: bool, expected: list[str]
) -> None:
    def mapping() -> dict[str, int]: ...

    app.config.typehints_use_rtype = use_rtype
    lines = [":returns: the mapping", ":rtype: dict of str to int, keyed", "    by name"]
    assert process("function", "mod.mapping", mapping, lines) == expected


@mark.sphinx(confoverrides={"typehints_document_rtype": False, "always_document_param_types": True})
def test_added_param_starts_a_field_list_after_a_comment(process: Process) -> None:
    def ratio(value: int) -> None: ...

    assert process("function", "mod.ratio", ratio, ["Summary.", "", "..", "    !! processed by numpydoc !!"]) == [
        "Summary.",
        "",
        "..",
        "    !! processed by numpydoc !!",
        "",
        f":type value: {INT}",
        ":param value:",
    ]


def test_return_type_stays_with_params_before_a_sphinx_directive(build_text: BuildText) -> None:
    assert build_text(".. autofunction:: dummy_module.versioned") == dedent("""\
        dummy_module.versioned(a)

           Do it.

           Parameters:
              **a** ("int") -- the a

           Return type:
              "int"

           Added in version 1.0.
        """)


_PARAMETERS: Final[tuple[str, ...]] = (":Parameters:", "", "    **x** : int", "        The x value.", "")


_CONVERTED: Final[list[str]] = [":param x: The x value.", ":type x: int", ""]


@mark.parametrize(
    ("read", "lines", "expected"),
    [
        param(
            lambda fmt, field_lines, _app: fmt.find_param(field_lines, "x"),
            list(_PARAMETERS),
            (0, _CONVERTED),
            id="find-param",
        ),
        param(
            lambda fmt, field_lines, _app: fmt.add_undocumented_param(field_lines, "y"),
            list(_PARAMETERS),
            (2, [":param x: The x value.", ":type x: int", ":param y:", ""]),
            id="add-undocumented-param",
        ),
        param(
            lambda fmt, field_lines, _app: fmt.has_return_description(field_lines),
            [":Returns:", "", "    str", "        A greeting.", ""],
            (True, [":rtype: str", ":returns: A greeting.", ""]),
            id="has-return-description",
        ),
        param(
            lambda fmt, field_lines, sphinx_app: fmt.get_rtype_insert_info(sphinx_app, field_lines),
            list(_PARAMETERS),
            (InsertIndexInfo(insert_index=3, deferred=True), _CONVERTED),
            id="get-rtype-insert-info",
        ),
    ],
)
def test_numpydoc_sections_convert_before_the_first_read(
    app: SphinxTestApp,
    read: Callable[[FieldListFormat, list[str], SphinxTestApp], int | bool | InsertIndexInfo | None],
    lines: list[str],
    expected: tuple[int | bool | InsertIndexInfo, list[str]],
) -> None:
    assert (read(FieldListFormat(numpydoc_pending=True), lines, app), lines) == expected
