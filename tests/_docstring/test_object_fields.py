from __future__ import annotations

from functools import cache, cached_property, partial
from inspect import getattr_static
from textwrap import dedent
from typing import TYPE_CHECKING, Final, overload, override

from pytest import MarkDecorator, mark, param

from _docstring.conftest import BOOL, INT, NONE, STR
from sphinx_autodoc_typehints._docstring.object_fields import inject_overloads, summary_end
from sphinx_autodoc_typehints._documented import Entry

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FunctionType

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp

    from _docstring.conftest import Process

pytestmark: Final[MarkDecorator] = mark.sphinx(
    "text", testroot="dummy", confoverrides={"typehints_document_rtype": False}
)


@overload
def _pick(value: int) -> int: ...


@overload
def _pick(value: str) -> str: ...


def _pick(value: int | str) -> int | str: ...


@overload
def _shaped(first: int, /, second: str = "x", *, third: bool) -> None: ...


@overload
def _shaped(first: str, /, *args: int, third: bool = True, **kwargs: str) -> None: ...


def _shaped(first: int | str, /, *args: object, **kwargs: object) -> None: ...


@overload
def _unbounded(*, flag: bool) -> None: ...


@overload
def _unbounded(first: int, /) -> None: ...


def _unbounded(*args: object, **kwargs: object) -> None: ...


@overload
def _bare() -> int: ...


@overload
def _bare(value: int) -> int: ...


def _bare(value: int = 0) -> int: ...


@overload
# ruff:ignore[missing-type-function-argument, missing-return-type-private-function]  # the case under test
def _untyped(first): ...


@overload
# ruff:ignore[missing-type-function-argument, missing-return-type-private-function]  # the case under test
def _untyped(first, second): ...


def _untyped(first, second=None): ...


_PICK: Final[list[str]] = [
    ":Overloads:",
    f"   * **value** ({INT}) → {INT}",
    f"   * **value** ({STR}) → {STR}",
    "",
]


@mark.parametrize(
    ("func", "lines", "expected"),
    [
        param(_pick, [], ["", *_PICK], id="empty"),
        param(
            _pick,
            ["Run the thing.", "more of it.", "", ":param value: the value"],
            ["Run the thing.", "more of it.", "", *_PICK, "", ":param value: the value"],
            id="below-the-summary",
        ),
        param(
            _shaped,
            [],
            [
                "",
                ":Overloads:",
                rf"   * **first** ({INT}), /, **second** ({STR}) = ``'x'``, \*, **third** ({BOOL}) → {NONE}",
                (
                    rf"   * **first** ({STR}), /, **\*args** ({INT}), **third** ({BOOL}) = ``True``, "
                    rf"**\*\*kwargs** ({STR}) → {NONE}"
                ),
                "",
            ],
            id="parameter-kinds",
        ),
        param(
            _unbounded,
            [],
            [
                "",
                ":Overloads:",
                rf"   * \*, **flag** ({BOOL}) → {NONE}",
                rf"   * **first** ({INT}), / → {NONE}",
                "",
            ],
            id="keyword-only-first-and-positional-only-last",
        ),
        param(
            _bare,
            [],
            ["", ":Overloads:", f"   * () → {INT}", f"   * **value** ({INT}) → {INT}", ""],
            id="no-parameters",
        ),
        param(_untyped, [], ["", ":Overloads:", "   * **first**", "   * **first**, **second**", ""], id="unannotated"),
    ],
)
def test_inject_overloads_lists_them(
    app: SphinxTestApp, func: FunctionType, lines: list[str], expected: list[str]
) -> None:
    has_overloads = inject_overloads(Entry(app, "function", f"{__name__}.{func.__name__}", func), func, lines)
    assert (has_overloads, lines) == (True, expected)


@mark.parametrize(
    ("what", "func", "lines", "expected"),
    [
        param("function", _pick, [":no-overloads:", "", "Docs."], ["", "Docs."], id="opted-out"),
        param("function", partial(_pick, 1), ["Docs."], ["Docs."], id="no-qualname"),
        param("function", inject_overloads, ["Docs."], ["Docs."], id="none-declared"),
        param("property", _pick, ["Docs."], ["Docs."], id="not-overloadable"),
        param(
            "function",
            _pick,
            [":no-overloads:", "Docs."],
            ["Docs."],
            id="opted-out-while-disabled",
            marks=mark.sphinx(confoverrides={"typehints_document_overloads": False}),
        ),
        param(
            "function",
            _pick,
            ["Docs."],
            ["Docs."],
            id="disabled",
            marks=mark.sphinx(confoverrides={"typehints_document_overloads": False}),
        ),
    ],
)
def test_inject_overloads_lists_none(
    app: SphinxTestApp, what: str, func: Callable[..., object], lines: list[str], expected: list[str]
) -> None:
    assert (inject_overloads(Entry(app, what, f"{__name__}._pick", func), func, lines), lines) == (False, expected)


@mark.sphinx(confoverrides={"typehints_use_signature": True})
def test_inject_overloads_leaves_them_to_the_signature(app: SphinxTestApp) -> None:
    lines = ["Docs."]
    assert (inject_overloads(Entry(app, "function", f"{__name__}._pick", _pick), _pick, lines), lines) == (
        True,
        ["Docs."],
    )


@mark.sphinx(confoverrides={"typehints_document_overloads": False, "typehints_document_rtype": False})
def test_no_overloads_directive_stripped_while_overloads_are_disabled(process: Process) -> None:
    def takes_count(count: int) -> None: ...

    lines = [":no-overloads:", "", "Accepts an int.", "", ":param count: The count"]
    assert process("function", "mod.takes_count", takes_count, lines) == [
        "",
        "Accepts an int.",
        "",
        f":type count: {INT}",
        ":param count: The count",
    ]


@mark.parametrize(
    ("lines", "expected"),
    [
        param([], 0, id="empty"),
        param(["", ""], 2, id="blank"),
        param(["", "Summary.", "more.", "", "Body."], 3, id="paragraph"),
        param(["Summary."], 1, id="summary-only"),
        param(["Example::", "", "    code", "", "After."], 4, id="introducing-a-literal-block"),
        param(["Example::", "", "    code"], 3, id="introducing-a-closing-literal-block"),
    ],
)
def test_summary_end(lines: list[str], expected: int) -> None:
    assert summary_end(lines) == expected


@mark.parametrize(
    ("directive", "expected"),
    [
        param(
            "automethod:: dummy_module.ClassWithOverloadedMethods.build",
            dedent("""\
                classmethod ClassWithOverloadedMethods.build(value)

                   Build one.

                   Overloads:
                      * **value** ("int") \N{RIGHTWARDS ARROW} "ClassWithOverloadedMethods"

                      * **value** ("str") \N{RIGHTWARDS ARROW} "ClassWithOverloadedMethods"
            """),
            id="classmethod",
        ),
        param(
            "automethod:: dummy_module.ClassWithOverloadedMethods.convert",
            dedent("""\
                ClassWithOverloadedMethods.convert(value)

                   Convert value.

                   Overloads:
                      * **value** ("int") \N{RIGHTWARDS ARROW} "int"

                      * **value** ("str") \N{RIGHTWARDS ARROW} "str"
            """),
            id="method",
        ),
        param(
            "automethod:: dummy_module.ClassWithOverloadedMethods.parse",
            dedent("""\
                static ClassWithOverloadedMethods.parse(value)

                   Parse value.

                   Overloads:
                      * **value** ("int") \N{RIGHTWARDS ARROW} "int"

                      * **value** ("str") \N{RIGHTWARDS ARROW} "str"
            """),
            id="staticmethod",
        ),
        param(
            "autoclass:: dummy_module.ClassWithOverloadedInit",
            dedent("""\
                class dummy_module.ClassWithOverloadedInit(value)

                   Class docstring.

                   Overloads:
                      * **value** ("int")

                      * **value** ("str")
            """),
            id="constructor",
        ),
    ],
)
def test_overloads_rendered_in_docstring(build_text: BuildText, directive: str, expected: str) -> None:
    assert build_text(f".. {directive}") == expected


@mark.sphinx(confoverrides={"typehints_use_signature": True, "autoclass_content": "both"})
def test_class_doc_from_class_ignores_the_constructor_opting_out_of_overloads(build_text: BuildText) -> None:
    assert build_text(
        dedent("""\
            .. autoclass:: dummy_module.ClassWithOverloadedInitOptingOut
               :class-doc-from: class
        """)
    ) == dedent("""\
        class dummy_module.ClassWithOverloadedInitOptingOut(value: int)
        class dummy_module.ClassWithOverloadedInitOptingOut(value: str)

           Class docstring.
        """)


class _OverrideBase:
    def run(self) -> str: ...

    def __hook(self) -> None: ...

    @property
    def size(self) -> int: ...


class _OverrideChild(_OverrideBase):
    @override
    def run(self) -> str: ...

    @property
    @override
    def size(self) -> int: ...

    @override
    def extra(self) -> str: ...  # ty: ignore[invalid-explicit-override]  # the case under test

    def plain(self) -> str: ...

    @override
    def __hook(self) -> None: ...  # ty: ignore[invalid-explicit-override]  # the case under test


class _OverrideGrandchild(_OverrideChild):
    @override
    @cache  # ruff:ignore[cached-instance-method]  # any decorator that wraps
    def run(self) -> str: ...


class _OverrideInheritor(_OverrideChild): ...


@mark.parametrize(
    ("what", "member", "expected"),
    [
        param(
            "method",
            "_OverrideChild.run",
            [
                "Summary.",
                "",
                ":Overrides: :py:meth:`_OverrideBase.run <_docstring.test_object_fields._OverrideBase.run>`",
            ],
            id="method",
        ),
        param(
            "property",
            "_OverrideChild.size",
            [
                "Summary.",
                "",
                ":Overrides: :py:attr:`_OverrideBase.size <_docstring.test_object_fields._OverrideBase.size>`",
            ],
            id="property",
        ),
        param(
            "method",
            "_OverrideGrandchild.run",
            [
                "Summary.",
                "",
                ":Overrides: :py:meth:`_OverrideChild.run <_docstring.test_object_fields._OverrideChild.run>`",
            ],
            id="wrapped-method-nearest-base",
        ),
        param(
            "method",
            "_OverrideInheritor.run",
            [
                "Summary.",
                "",
                ":Overrides: :py:meth:`_OverrideBase.run <_docstring.test_object_fields._OverrideBase.run>`",
            ],
            id="inherited-member",
        ),
        param(
            "method",
            "_OverrideChild.run",
            [
                "Summary.",
                "",
                (
                    ":Overrides: :py:meth:`_docstring.test_object_fields._OverrideBase.run "
                    "<_docstring.test_object_fields._OverrideBase.run>`"
                ),
            ],
            id="fully-qualified",
            marks=mark.sphinx(confoverrides={"typehints_document_rtype": False, "typehints_fully_qualified": True}),
        ),
        param(
            "method",
            "_OverrideChild.run",
            ["Summary.", "", ":Overrides: :py:meth:`_OverrideBase.run <renamed._OverrideBase.run>`"],
            id="fixed-up-module",
            marks=mark.sphinx(
                confoverrides={
                    "typehints_document_rtype": False,
                    "typehints_fixup_module_name": lambda module: (
                        "renamed" if module == "_docstring.test_object_fields" else module
                    ),
                }
            ),
        ),
        param("method", "_OverrideChild.extra", ["Summary."], id="nothing-to-override"),
        param("method", "_OverrideChild.plain", ["Summary."], id="not-marked"),
    ],
)
def test_override_links_what_it_overrides(process: Process, what: str, member: str, expected: list[str]) -> None:
    owner, attribute = member.split(".")
    obj = getattr_static(globals()[owner], attribute)
    assert process(what, f"{__name__}.{member}", obj, ["Summary."]) == expected


@mark.parametrize("owner", [param("_OverrideChild", id="own"), param("_OverrideInheritor", id="inherited")])
def test_override_of_a_private_member_links_nothing(process: Process, owner: str) -> None:
    obj = getattr_static(_OverrideChild, "_OverrideChild__hook")
    assert process("method", f"{__name__}.{owner}.__hook", obj, ["Summary."]) == ["Summary."]


@mark.sphinx(confoverrides={"typehints_document_rtype": True})
def test_override_outside_an_importable_class_links_nothing(process: Process) -> None:
    assert process("method", "missing_module.Child.run", _OverrideChild.run, ["Summary."]) == [
        "Summary.",
        "",
        f":rtype: {STR}",
    ]


def _get_int(self: object) -> int: ...


def _set_int(self: object, new: int) -> None: ...


def _set_int_or_str(self: object, new: int | str) -> None: ...


class _Unreadable:
    __signature__ = "unreadable"

    def __call__(self, owner: object, new: int) -> None: ...


@mark.parametrize(
    ("prop", "lines", "expected"),
    [
        param(
            property(_get_int, _set_int_or_str),
            ["Summary."],
            [
                "Summary.",
                "",
                r":Setter accepts: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\` \| \:py\:class\:\`str\``",
            ],
            id="setter-wider-than-getter",
        ),
        param(
            property(lambda self: self, _set_int),
            ["Summary."],
            ["Summary.", "", f":Setter accepts: {INT}"],
            id="untyped-getter",
        ),
        param(
            property(_get_int, _set_int_or_str),
            ["Summary.", "", ":Setter accepts: a number"],
            ["Summary.", "", ":Setter accepts: a number"],
            id="docstring-states-it",
        ),
        param(property(_get_int, _set_int), ["Summary."], ["Summary."], id="same-type"),
        param(property(_get_int, lambda _holder, _new_value: None), ["Summary."], ["Summary."], id="untyped-setter"),
        param(property(_get_int), ["Summary."], ["Summary."], id="no-setter"),
        param(
            property(_get_int, "Set the value."),  # ty: ignore[invalid-argument-type]  # pygments passes a docstring
            ["Summary."],
            ["Summary."],
            id="docstring-as-setter",
        ),
        param(
            property(
                _get_int,
                partial(_set_int, None, 1),  # ty: ignore[invalid-argument-type]  # takes no value
            ),
            ["Summary."],
            ["Summary."],
            id="setter-without-parameters",
        ),
        param(property(_get_int, _Unreadable()), ["Summary."], ["Summary."], id="unreadable-setter"),
        param(cached_property(_get_int), ["Summary."], ["Summary."], id="cached-property"),
    ],
)
def test_property_shows_the_type_its_setter_accepts(
    process: Process, prop: property, lines: list[str], expected: list[str]
) -> None:
    assert process("property", f"{__name__}.Holder.value", prop, lines) == expected


@mark.parametrize(
    ("cls", "expected"),
    [
        param(
            "Closed",
            dedent("""\
                class typed_dict_module.Closed

                   Closed.

                   Extra items:
                      "Never"
            """),
            id="closed",
        ),
        param(
            "ClosedChild",
            dedent("""\
                class typed_dict_module.ClosedChild

                   Inherits closed=True from its base.

                   Extra items:
                      "Never"
            """),
            id="inherited",
        ),
        param(
            "ExtraUnstated",
            dedent("""\
                class typed_dict_module.ExtraUnstated

                   Typed extra items.

                   Extra items:
                      "int"
            """),
            id="extra-items",
        ),
        param(
            "Extra",
            dedent("""\
                class typed_dict_module.Extra

                   Typed extra items.

                   Extra items:
                      integer counts documented by hand
            """),
            id="documented",
        ),
        param(
            "Reopened",
            dedent("""\
                class typed_dict_module.Reopened

                   Says it is open.
            """),
            id="open",
        ),
        param(
            "Movie",
            dedent("""\
                class typed_dict_module.Movie

                   A movie.
            """),
            id="unstated",
        ),
    ],
)
@mark.sphinx("text", testroot="typed-dict")
def test_typed_dict_extra_items(build_text: BuildText, cls: str, expected: str) -> None:
    assert build_text(f".. autoclass:: typed_dict_module.{cls}") == expected


@mark.parametrize(
    ("index", "expected"),
    [
        param(
            dedent("""\
                .. py:type:: mod_eager.Count

                .. autofunction:: mod_eager.scale
            """),
            dedent("""\
                type mod_eager.Count

                mod_eager.scale(amount)

                   Scale an amount.

                   Overloads:
                      * **amount** ("Count") → "Count"

                      * **amount** ("str") → "str"

                   Parameters:
                      **amount** ("int" | "str") -- The amount
            """),
            id="documented-before",
        ),
        param(
            dedent("""\
                .. autofunction:: mod_eager.scale

                .. py:type:: mod_eager.Count
            """),
            dedent("""\
                mod_eager.scale(amount)

                   Scale an amount.

                   Overloads:
                      * **amount** ("Count") → "Count"

                      * **amount** ("str") → "str"

                   Parameters:
                      **amount** ("int" | "str") -- The amount

                type mod_eager.Count
            """),
            id="documented-after",
        ),
        param(
            ".. autofunction:: mod_eager.scale",
            dedent("""\
                mod_eager.scale(amount)

                   Scale an amount.

                   Overloads:
                      * **amount** (mod_eager.Count) → mod_eager.Count

                      * **amount** ("str") → "str"

                   Parameters:
                      **amount** ("int" | "str") -- The amount
            """),
            marks=mark.sphinx(confoverrides={"autodoc_type_aliases": {"Count": "mod_eager.Count"}}),
            id="configured",
        ),
    ],
)
@mark.sphinx("text", testroot="integration")
def test_overloads_name_an_alias_as_written(build_text: BuildText, index: str, expected: str) -> None:
    assert build_text(index) == expected
