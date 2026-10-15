from __future__ import annotations

from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, mark, param

from _docstring.conftest import FLOAT, INT, STR, without_rtype

if TYPE_CHECKING:
    from _docstring.conftest import Process


pytestmark: Final[list[MarkDecorator]] = [mark.sphinx("text", testroot="dummy"), without_rtype()]


@mark.parametrize(
    ("lines", "expected"),
    [
        param(
            [":Parameters: * **first** -- the first", "             * **second** -- the second"],
            [f":Parameters: * **first** ({INT}) -- the first", f"             * **second** ({STR}) -- the second"],
            id="bulleted",
        ),
        param(
            [":Parameters: * **first** -- the first", "             * **second** -- the second"],
            [
                f":Parameters: * **first** ({INT}) -- the first",
                f"             * **second** ({STR}) -- the second",
                rf"             * **\*args** ({FLOAT})",
            ],
            id="always-documented",
            marks=without_rtype(always_document_param_types=True),
        ),
        param(
            [":Parameters: **second** -- the second"],
            [
                f":Parameters: * **first** ({INT})",
                f"             * **second** ({STR}) -- the second",
                rf"             * **\*args** ({FLOAT})",
            ],
            id="always-documented-around-a-single-entry",
            marks=without_rtype(always_document_param_types=True),
        ),
        param(
            [
                ":Parameters: **first** -- the first",
                "             more of first",
                "",
                "             still first",
                "",
                "After.",
            ],
            [
                f":Parameters: * **first** ({INT}) -- the first",
                "               more of first",
                "",
                "               still first",
                f"             * **second** ({STR})",
                rf"             * **\*args** ({FLOAT})",
                "",
                "After.",
            ],
            id="always-documented-after-a-multi-paragraph-entry",
            marks=without_rtype(always_document_param_types=True),
        ),
        param(
            [":Keyword Arguments: **second** -- the second"],
            [f":Keyword Arguments: **second** ({STR}) -- the second"],
            id="keyword",
        ),
        param([r":Parameters: **\*args** -- extra"], [rf":Parameters: **\*args** ({FLOAT}) -- extra"], id="star-args"),
        param(
            [":Parameters: **first** (*int*) -- the first"],
            [":Parameters: **first** (*int*) -- the first"],
            id="typed-in-the-docstring",
        ),
        param(
            [":Parameters: **second** -- the second"],
            [f":Parameters: **second** ({STR}, default: ``'x'``) -- the second"],
            id="comma-default",
            marks=without_rtype(typehints_defaults="comma"),
        ),
        param(
            [":Parameters: **second** -- the second"],
            [f":Parameters: **second** ({STR}) (default: ``'x'``) -- the second"],
            id="braces-default",
            marks=without_rtype(typehints_defaults="braces"),
        ),
        param(
            [
                ":Parameters: * **second** -- the second",
                "               continued",
                "             * **first** -- the first",
            ],
            [
                f":Parameters: * **second** ({STR}) -- the second",
                "               continued (default: ``'x'``)",
                f"             * **first** ({INT}) -- the first",
            ],
            id="braces-after-default",
            marks=without_rtype(typehints_defaults="braces-after"),
        ),
        param(
            [
                ":Parameters: * **second** -- the second",
                "",
                "               more about second",
                "             * **first** -- the first",
            ],
            [
                f":Parameters: * **second** ({STR}) -- the second",
                "",
                "               more about second (default: ``'x'``)",
                f"             * **first** ({INT}) -- the first",
            ],
            id="braces-after-default-past-a-paragraph",
            marks=without_rtype(typehints_defaults="braces-after"),
        ),
        param(
            [":Parameters: **second** (*str*) -- the second"],
            [":Parameters: **second** (*str*, default: ``'x'``) -- the second"],
            id="typed-in-the-docstring-comma-default",
            marks=without_rtype(typehints_defaults="comma"),
        ),
        param(
            [":Parameters: **second** (*str*) -- the second"],
            [":Parameters: **second** (*str*) (default: ``'x'``) -- the second"],
            id="typed-in-the-docstring-braces-default",
            marks=without_rtype(typehints_defaults="braces"),
        ),
        param(
            [":Parameters: **second** (*str*) -- the second"],
            [":Parameters: **second** (*str*) -- the second (default: ``'x'``)"],
            id="typed-in-the-docstring-braces-after-default",
            marks=without_rtype(typehints_defaults="braces-after"),
        ),
        param(
            [":Parameters: **second** (*str* -- the second"],
            [":Parameters: **second** (*str* -- the second"],
            id="typed-in-the-docstring-unclosed",
            marks=without_rtype(typehints_defaults="comma"),
        ),
    ],
)
def test_combined_field_entry_gets_its_type(process: Process, lines: list[str], expected: list[str]) -> None:
    def documented(first: int, second: str = "x", *args: float) -> None: ...

    assert process("function", "mod.documented", documented, lines) == expected


@without_rtype(typehints_defaults="comma")
def test_combined_field_entry_of_an_unannotated_parameter_stays_untyped(process: Process) -> None:
    assert process("function", "mod.unannotated", lambda first="x": first, [":Parameters: **first** -- the first"]) == [
        ":Parameters: **first** -- the first"
    ]


@mark.parametrize(
    "outside",
    [
        param([":Overloads:", "   * **first** (int) → int", ""], id="overload"),
        param(["Example::", "", "    **first** is bold here", ""], id="code-example"),
        param([":returns:", "   * **first** (int)", ""], id="named-return"),
    ],
)
@without_rtype(typehints_defaults="comma")
def test_combined_field_entry_outside_a_parameter_field_stays_untyped(process: Process, outside: list[str]) -> None:
    def two(first: int = 1, second: str = "x") -> None: ...

    assert process("function", "mod.two", two, [*outside, ":Parameters: **second** -- the second"]) == [
        *outside,
        f":Parameters: **second** ({STR}, default: ``'x'``) -- the second",
    ]
