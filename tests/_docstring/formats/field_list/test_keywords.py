from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Final

from pytest import MarkDecorator, mark, param
from typing_extensions import Doc

from _docstring.conftest import INT, NONE, STR
from sphinx_autodoc_typehints._docstring.formats.field_list.keywords import field_keyword_and_argument

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import FunctionType

    from _docstring.conftest import Process

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


@mark.parametrize(
    ("line", "expected"),
    [
        param(":param int x: the x", ("param", "int x"), id="with-argument"),
        param(":returns: the value", ("returns", None), id="without-argument"),
        param(":: a literal", None, id="no-keyword"),
        param(":param x", None, id="unclosed"),
        param("   :param x: the x", None, id="indented"),
    ],
)
def test_field_keyword_and_argument(line: str, expected: tuple[str, str | None] | None) -> None:
    assert field_keyword_and_argument(line) == expected


def _nested_param(value: int) -> None: ...


def _nested_yields() -> Iterator[int]: ...


def _nested_returns() -> Annotated[int, Doc("the count")]: ...


@mark.parametrize(
    ("func", "lines", "expected"),
    [
        param(
            _nested_param,
            ["Example::", "", "    :param value: in a literal block", "", ":param value: the value"],
            [
                "Example::",
                "",
                "    :param value: in a literal block",
                "",
                f":type value: {INT}",
                ":param value: the value",
                "",
                f":sphinx_autodoc_typehints_rtype: {NONE}",
            ],
            id="param",
        ),
        param(
            _nested_yields,
            ["Example::", "", "    :yields: in a literal block"],
            [
                "Example::",
                "",
                "    :yields: in a literal block",
                "",
                (
                    r":sphinx_autodoc_typehints_rtype: "
                    r":sphinx_autodoc_typehints_type:`\:py\:class\:\`\~collections.abc.Iterator\`\\ "
                    r"\\\[\:py\:class\:\`int\`\]`"
                ),
            ],
            id="yields",
        ),
        param(
            _nested_returns,
            ["Example::", "", "    :returns: in a literal block"],
            ["Example::", "", "    :returns: in a literal block", "", f":rtype: {INT}", ":return: the count"],
            id="returns",
        ),
    ],
)
def test_field_nested_in_a_block_documents_nothing(
    process: Process, func: FunctionType, lines: list[str], expected: list[str]
) -> None:
    assert process("function", f"mod.{func.__name__}", func, lines) == expected


def _typed(value: int) -> None: ...


def _starred(*values: int, **options: str) -> None: ...


@mark.parametrize(
    ("func", "lines", "expected"),
    [
        param(
            _typed,
            [":param str value: the value"],
            [f":type value: {INT}", ":param value: the value"],
            id="annotated",
        ),
        param(
            _typed,
            [":param ~typing.IO[bytes] value: the value"],
            [f":type value: {INT}", ":param value: the value"],
            id="annotated-complex",
        ),
        param(
            _typed,
            [":param value: the value"],
            [f":type value: {INT}", ":param value: the value"],
            id="no-inline-type",
        ),
        param(
            _starred,
            [r":param int \*values: the values"],
            [rf":type \*values: {INT}", r":param \*values: the values"],
            id="starred",
        ),
        param(
            _starred,
            [r":param \*\*options: the options"],
            [rf":type \*\*options: {STR}", r":param \*\*options: the options"],
            id="double-starred",
        ),
        param(
            lambda value: value,
            [":param str value: the value"],
            [":type value: str", ":param value: the value"],
            id="unannotated",
        ),
    ],
)
@mark.sphinx(confoverrides={"typehints_document_rtype": False})
def test_inline_param_type_gives_way_to_the_annotation(
    process: Process, func: FunctionType, lines: list[str], expected: list[str]
) -> None:
    assert process("function", f"mod.{func.__name__}", func, lines) == expected
