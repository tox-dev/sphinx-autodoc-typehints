from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Annotated, Final, NotRequired, Required, TypedDict, Unpack

from annotated_doc import Doc as AnnotatedDoc
from pytest import MarkDecorator, mark, param
from typing_extensions import Doc

from _docstring.conftest import BOOL, FLOAT, INT, STR, without_rtype
from sphinx_autodoc_typehints._docstring.parameters import escape_trailing_underscore

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FunctionType

    from conftest import BuildText

    from _docstring.conftest import Process


pytestmark: Final[list[MarkDecorator]] = [mark.sphinx("text", testroot="dummy"), without_rtype()]


@mark.parametrize(
    ("lines", "expected"),
    [
        param([":keyword flag: on"], [f":paramtype flag: {BOOL}", ":keyword flag: on"], id="keyword"),
        param(
            [":keyword flag: on"],
            [f":paramtype flag: {BOOL}", ":keyword flag: on"],
            id="keyword-not-duplicated",
            marks=without_rtype(always_document_param_types=True),
        ),
        param([":kwarg flag: on"], [f":paramtype flag: {BOOL}", ":kwarg flag: on"], id="kwarg"),
        param(
            [":keyword flag: on", ":kwtype flag: int"],
            [":keyword flag: on", f":paramtype flag: {BOOL}"],
            id="replaces-kwtype",
        ),
    ],
)
def test_keyword_argument_gets_a_paramtype(process: Process, lines: list[str], expected: list[str]) -> None:
    def takes_flag(*, flag: bool) -> None: ...

    assert process("function", "mod.takes_flag", takes_flag, lines) == expected


@mark.parametrize(
    ("lines", "expected"),
    [
        param(
            [":param value: the value parameter", ":type value: str"],
            [":param value: the value parameter", f":type value: {INT}"],
            id="single-line",
        ),
        param(
            [":param value: the value parameter", ":type value: ~collections.abc.Callable[[int,", "    str], bool]"],
            [":param value: the value parameter", f":type value: {INT}"],
            id="multi-line",
        ),
        param(
            [":param value: the value parameter", ":type value: str", "", ".. rubric:: Notes"],
            [":param value: the value parameter", f":type value: {INT}", "", ".. rubric:: Notes"],
            id="before-a-blank-line",
        ),
        param(
            [":param\tvalue: the value"], [f":type value: {INT}", ":param\tvalue: the value"], id="tab-separated-field"
        ),
        param(
            [":param value: the value", ":paramtype value: str"],
            [":param value: the value", f":type value: {INT}"],
            id="paramtype",
        ),
        param(
            [":param value: the value", ":type values: str"],
            [f":type value: {INT}", ":param value: the value", ":type values: str"],
            id="type-of-another-name",
        ),
    ],
)
def test_annotation_replaces_the_docstring_type(process: Process, lines: list[str], expected: list[str]) -> None:
    def func(value: int) -> None: ...

    assert process("function", "mod.func", func, lines) == expected


def _sized(width: int = 5, height: int = 10) -> None: ...


def _defaulted(amount: int = 1) -> None: ...


@mark.parametrize(
    ("func", "lines", "expected"),
    [
        param(
            lambda count=1: count,
            [":param count: the count", ":type count: int"],
            [":param count: the count", ":type count: int, default: :sphinx_autodoc_typehints_value:`1`"],
            id="comma",
            marks=without_rtype(typehints_defaults="comma"),
        ),
        param(
            lambda count=1: count,
            [":param count: the count", ":type count: int"],
            [":param count: the count", ":type count: int (default: :sphinx_autodoc_typehints_value:`1`)"],
            id="braces",
            marks=without_rtype(typehints_defaults="braces"),
        ),
        param(
            lambda count=1: count,
            [":param count: the count", ":type count: int"],
            [":param count: the count (default: :sphinx_autodoc_typehints_value:`1`)", ":type count: int"],
            id="braces-after",
            marks=without_rtype(typehints_defaults="braces-after"),
        ),
        param(
            lambda count=1: count,
            [":param count: the count", ":type count: dict[str,", "    int]"],
            [
                ":param count: the count",
                ":type count: dict[str,",
                "    int], default: :sphinx_autodoc_typehints_value:`1`",
            ],
            id="multi-line-type",
            marks=without_rtype(typehints_defaults="comma"),
        ),
        param(
            lambda count=1: count,
            [":param int count: the count"],
            [":type count: int, default: :sphinx_autodoc_typehints_value:`1`", ":param count: the count"],
            id="inline-comma",
            marks=without_rtype(typehints_defaults="comma"),
        ),
        param(
            lambda count=1: count,
            [":param int count: the count"],
            [":type count: int (default: :sphinx_autodoc_typehints_value:`1`)", ":param count: the count"],
            id="inline-braces",
            marks=without_rtype(typehints_defaults="braces"),
        ),
        param(
            lambda count=1: count,
            [":param int count: the count"],
            [":type count: int", ":param count: the count (default: :sphinx_autodoc_typehints_value:`1`)"],
            id="inline-braces-after",
            marks=without_rtype(typehints_defaults="braces-after"),
        ),
        param(
            lambda count=1: count,
            [":param count: the count"],
            [":type count: default: :sphinx_autodoc_typehints_value:`1`", ":param count: the count"],
            id="untyped",
            marks=without_rtype(typehints_defaults="comma"),
        ),
        param(
            _sized,
            [":param width: the width", ":type width: int", ":param height: the height", ":type height: int"],
            [
                ":param width: the width (default: :sphinx_autodoc_typehints_value:`5`)",
                f":type width: {INT}",
                ":param height: the height (default: :sphinx_autodoc_typehints_value:`10`)",
                f":type height: {INT}",
            ],
            id="braces-after-each-param",
            marks=without_rtype(typehints_defaults="braces-after"),
        ),
        param(
            _defaulted,
            [":param amount: the amount, for example::", "", "    amount = 5"],
            [
                f":type amount: {INT}",
                ":param amount: the amount, for example (default: :sphinx_autodoc_typehints_value:`1`)::",
                "",
                "    amount = 5",
            ],
            id="braces-after-before-a-literal-block",
            marks=without_rtype(typehints_defaults="braces-after"),
        ),
    ],
)
def test_default_joins_the_type_or_the_description(
    process: Process, func: FunctionType, lines: list[str], expected: list[str]
) -> None:
    assert process("function", f"mod.{func.__name__}", func, lines) == expected


_FIRST_TYPE: Final[str] = f":type first: {INT}"
_SECOND_TYPE: Final[str] = f":type second: {STR}"


def _pair(first: int, second: str) -> None: ...


def _described(first: Annotated[int, Doc("the first")], second: str) -> None: ...


def _described_external(first: Annotated[int, AnnotatedDoc("the first")], second: str) -> None: ...


@mark.parametrize(
    ("func", "lines", "expected"),
    [
        param(
            _pair,
            [":param second: the second", "", "Closing."],
            [_FIRST_TYPE, ":param first:", _SECOND_TYPE, ":param second: the second", "", "Closing."],
            id="before-a-later-param",
        ),
        param(
            _pair,
            [":param first: the first", "    more", "", "Closing."],
            [_FIRST_TYPE, ":param first: the first", "    more", _SECOND_TYPE, ":param second:", "", "Closing."],
            id="after-the-last-param",
        ),
        param(
            _pair,
            ["Closing."],
            ["Closing.", "", _FIRST_TYPE, ":param first:", _SECOND_TYPE, ":param second:"],
            id="none-documented",
        ),
        param(
            _described,
            [":param second: the second", "", "Closing."],
            [_FIRST_TYPE, ":param first: the first", _SECOND_TYPE, ":param second: the second", "", "Closing."],
            id="doc-description",
        ),
        param(
            _described_external,
            [":param second: the second", "", "Closing."],
            [_FIRST_TYPE, ":param first: the first", _SECOND_TYPE, ":param second: the second", "", "Closing."],
            id="annotated-doc-description",
        ),
        param(
            _described,
            [],
            [_FIRST_TYPE, ":param first: the first", _SECOND_TYPE, ":param second:"],
            id="doc-description-alone",
        ),
    ],
)
@without_rtype(always_document_param_types=True)
def test_added_params_keep_signature_order(
    process: Process, func: Callable[..., None], lines: list[str], expected: list[str]
) -> None:
    assert process("function", "mod.func", func, lines) == expected


def test_param_without_annotation_or_description_gets_no_field(process: Process) -> None:
    assert process("function", "mod._pair", _pair, ["Summary."]) == ["Summary."]


def _trailing(lambda_: float) -> None: ...


def _starred_trailing(*args_: float) -> None: ...


@mark.parametrize(
    ("func", "lines", "expected"),
    [
        param(
            _trailing,
            [":param lambda_: description"],
            [rf":type lambda\_: {FLOAT}", r":param lambda\_: description"],
            id="unescaped-line-rewritten",
        ),
        param(
            _trailing,
            [r":param lambda\_: description"],
            [rf":type lambda\_: {FLOAT}", r":param lambda\_: description"],
            id="escaped",
        ),
        param(_trailing, [], [rf":type lambda\_: {FLOAT}", r":param lambda\_:"], id="undocumented-escaped"),
        param(
            _starred_trailing,
            [r":param \*args_: description"],
            [rf":type \*args_: {FLOAT}", r":param \*args_: description"],
            id="starred-keeps-its-field",
        ),
    ],
)
@without_rtype(always_document_param_types=True)
def test_trailing_underscore_param(process: Process, func: FunctionType, lines: list[str], expected: list[str]) -> None:
    assert process("function", f"mod.{func.__name__}", func, lines) == expected


@mark.parametrize(
    ("name", "expected"),
    [param("lambda_", r"lambda\_", id="trailing"), param("_private", "_private", id="leading")],
)
def test_escape_trailing_underscore(name: str, expected: str) -> None:
    assert escape_trailing_underscore(name) == expected


class _Options(TypedDict, total=False):
    verbose: Required[bool]
    level: int
    name: Annotated[NotRequired[str], Doc("the name")]
    alias: NotRequired[Annotated[str, Doc("the alias")]]


class _Unresolvable(TypedDict):
    callback: Undefined  # ruff:ignore[undefined-name]  # ty: ignore[unresolved-reference]  # the case under test


_Odd = TypedDict("_Odd", {"odd-key": int, "class": int, "count": int})


def _configure(**kwargs: Unpack[_Options]) -> None: ...


def _unresolvable(**kwargs: Unpack[_Unresolvable]) -> None: ...


def _odd(count: int, **kwargs: Unpack[_Odd]) -> None: ...  # ty: ignore[invalid-type-form]  # the case under test


def _plain(**kwargs: int) -> None: ...


_UNPACKED: Final[str] = (
    r":sphinx_autodoc_typehints_type:`\:py\:data\:\`\~typing.Unpack\`\\ "
    r"\\\[\:py\:class\:\`\~\_docstring.test\_parameters.\{}\`\]`"
)
_NOT_REQUIRED: Final[str] = (
    r":sphinx_autodoc_typehints_type:`\:py\:data\:\`\~typing.NotRequired\`\\ \\\[\:py\:class\:\`{}\`\]`"
)


@mark.parametrize(
    ("func", "lines", "expected"),
    [
        param(
            _configure,
            [":param kwargs: the options", ":keyword verbose: be loud", ":keyword level: how loud"],
            [
                f":type kwargs: {_UNPACKED.format('_Options')}",
                ":param kwargs: the options",
                f":paramtype verbose: {BOOL}",
                ":keyword verbose: be loud",
                f":paramtype level: {_NOT_REQUIRED.format('int')}",
                ":keyword level: how loud",
                f":paramtype name: {_NOT_REQUIRED.format('str')}",
                ":keyword name: the name",
                f":paramtype alias: {_NOT_REQUIRED.format('str')}",
                ":keyword alias: the alias",
            ],
            id="documented-keys",
        ),
        param(
            _configure,
            [":param kwargs: the options"],
            [
                f":type kwargs: {_UNPACKED.format('_Options')}",
                ":param kwargs: the options",
                f":paramtype verbose: {BOOL}",
                ":keyword verbose:",
                f":paramtype level: {_NOT_REQUIRED.format('int')}",
                ":keyword level:",
                f":paramtype name: {_NOT_REQUIRED.format('str')}",
                ":keyword name: the name",
                f":paramtype alias: {_NOT_REQUIRED.format('str')}",
                ":keyword alias: the alias",
            ],
            id="undocumented-keys",
            marks=without_rtype(always_document_param_types=True),
        ),
        param(
            _configure,
            [":param kwargs: the options", ":Keyword Arguments: **verbose** -- be loud"],
            [
                f":type kwargs: {_UNPACKED.format('_Options')}",
                ":param kwargs: the options",
                f":Keyword Arguments: * **verbose** ({BOOL}) -- be loud",
                f"                    * **level** ({_NOT_REQUIRED.format('int')})",
                f"                    * **name** ({_NOT_REQUIRED.format('str')}) -- the name",
                f"                    * **alias** ({_NOT_REQUIRED.format('str')}) -- the alias",
            ],
            id="combined-keyword-field",
            marks=without_rtype(always_document_param_types=True),
        ),
        param(
            _odd,
            [":param count: the count", ":param kwargs: the rest"],
            [
                f":type count: {INT}",
                ":param count: the count",
                f":type kwargs: {_UNPACKED.format('_Odd')}",
                ":param kwargs: the rest",
            ],
            id="keys-that-cannot-be-parameters",
        ),
        param(
            _unresolvable,
            [":param kwargs: the options"],
            [f":type kwargs: {_UNPACKED.format('_Unresolvable')}", ":param kwargs: the options"],
            id="unresolvable-key-types",
            marks=without_rtype(always_document_param_types=True),
        ),
        param(
            _plain,
            [":param kwargs: the options"],
            [f":type kwargs: {INT}", ":param kwargs: the options"],
            id="not-unpacked",
            marks=without_rtype(always_document_param_types=True),
        ),
    ],
)
def test_unpacked_kwargs_keys_get_their_types(
    process: Process, func: FunctionType, lines: list[str], expected: list[str]
) -> None:
    assert process("function", f"mod.{func.__name__}", func, lines) == expected


@mark.parametrize(
    "expected",
    [
        param(
            dedent("""\
                dummy_module.undocumented_function(x)

                   Hi

                   Return type:
                      "str"

                class dummy_module.DataClass(x)

                   Class docstring.

                   __init__(x)
            """),
            id="no_doc_param_type",
            marks=mark.sphinx(confoverrides={"typehints_document_rtype": True}),
        ),
        param(
            dedent("""\
                dummy_module.undocumented_function(x)

                   Hi

                   Parameters:
                      **x** ("int")

                   Return type:
                      "str"

                class dummy_module.DataClass(x)

                   Class docstring.

                   Parameters:
                      **x** ("int")

                   __init__(x)

                      Parameters:
                         **x** ("int")
            """),
            id="doc_param_type",
            marks=mark.sphinx(confoverrides={"always_document_param_types": True}),
        ),
    ],
)
@mark.sphinx(exception_on_warning=True)
def test_always_document_param_types(build_text: BuildText, expected: str) -> None:
    text = build_text(
        dedent("""\
            .. autofunction:: dummy_module.undocumented_function

            .. autoclass:: dummy_module.DataClass
                :undoc-members:
                :special-members: __init__
        """)
    )
    assert text == expected


@mark.sphinx(confoverrides={"always_document_param_types": True, "typehints_defaults": "braces-after"})
def test_always_document_param_types_with_braces_after_defaults(build_text: BuildText) -> None:
    assert build_text(".. autofunction:: dummy_module.undocumented_function_with_defaults") == dedent("""\
        dummy_module.undocumented_function_with_defaults(x, y='hello')

           Hi

           Parameters:
              * **x** ("int")

              * **y** ("str") -- (default: "'hello'")

           Return type:
              "str"
        """)


@mark.parametrize(
    "expected",
    [
        param('("int") -- bar', id="none", marks=mark.sphinx(confoverrides={"typehints_document_rtype": True})),
        param(
            '("int", default: "1") -- bar',
            id="comma",
            marks=mark.sphinx(confoverrides={"typehints_defaults": "comma"}),
        ),
        param(
            '("int" (default: "1")) -- bar',
            id="braces",
            marks=mark.sphinx(confoverrides={"typehints_defaults": "braces"}),
        ),
        param(
            '("int") -- bar (default: "1")',
            id="braces-after",
            marks=mark.sphinx(confoverrides={"typehints_defaults": "braces-after"}),
        ),
    ],
)
def test_default_shown_as_configured(build_text: BuildText, expected: str) -> None:
    assert build_text(".. autofunction:: dummy_module_simple.function") == dedent(f"""\
        dummy_module_simple.function(x, y=1)

           Function docstring.

           Parameters:
              * **x** ("bool") -- foo

              * **y** {expected}

           Return type:
              "str"
        """)


@mark.parametrize(
    ("name", "expected"),
    [
        param(
            "function_with_some_defaults_and_without_typehints",
            dedent("""\
                dummy_module_without_complete_typehints.function_with_some_defaults_and_without_typehints(x, y=None)

                   Function docstring.

                   Parameters:
                      * **x** -- untyped without a default

                      * **y** (default: "None") -- untyped with a default
            """),
            id="untyped",
        ),
        param(
            "function_with_some_defaults_and_some_typehints",
            dedent("""\
                dummy_module_without_complete_typehints.function_with_some_defaults_and_some_typehints(x, y=None)

                   Function docstring.

                   Parameters:
                      * **x** ("int") -- typed without a default

                      * **y** (default: "None") -- untyped with a default
            """),
            id="partly-typed",
        ),
        param(
            "function_with_some_defaults_and_more_typehints",
            dedent("""\
                dummy_module_without_complete_typehints.function_with_some_defaults_and_more_typehints(x, y=None)

                   Function docstring.

                   Parameters:
                      * **x** ("int") -- typed without a default

                      * **y** (default: "None") -- untyped with a default

                   Return type:
                      "str"
            """),
            id="partly-typed-with-return",
        ),
        param(
            "function_with_defaults_and_some_typehints",
            dedent("""\
                dummy_module_without_complete_typehints.function_with_defaults_and_some_typehints(x=0, y=None)

                   Function docstring.

                   Parameters:
                      * **x** ("int", default: "0") -- typed with a default

                      * **y** (default: "None") -- untyped with a default

                   Return type:
                      "str"
            """),
            id="typed-with-default",
        ),
        param(
            "function_with_defaults_and_type_information_in_docstring",
            dedent("""\
                dummy_module_without_complete_typehints.function_with_defaults_and_type_information_in_docstring(x, y=0)

                   Function docstring.

                   Parameters:
                      * **x** (*int*) -- typed in the docstring

                      * **y** (int, default: "0") -- typed in the docstring with a default

                   Return type:
                      "str"
            """),
            id="docstring-typed",
        ),
    ],
)
@mark.usefixtures("wide_text_output")
@mark.sphinx(confoverrides={"typehints_defaults": "comma"})
def test_default_annotation_without_typehints(build_text: BuildText, name: str, expected: str) -> None:
    assert build_text(f".. autofunction:: dummy_module_without_complete_typehints.{name}") == expected
