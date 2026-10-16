from __future__ import annotations

from importlib import import_module
from sys import version_info
from textwrap import dedent
from typing import TYPE_CHECKING, TypeAliasType, TypeVar

import typing_extensions  # its TypeAliasType backport is tested next to typing's
from pytest import MonkeyPatch, fixture, mark, param

from sphinx_autodoc_typehints._render import annotation_state, format_annotation
from sphinx_autodoc_typehints._render.annotation.aliases import alias_name_reference

if TYPE_CHECKING:
    from collections.abc import Callable
    from decimal import Decimal
    from io import StringIO
    from pathlib import Path
    from types import ModuleType

    from conftest import BuildText
    from sphinx.config import Config
    from sphinx.testing.util import SphinxTestApp

    from _render.conftest import MakeConfig
    from sphinx_autodoc_typehints._types import Annotation

Item = TypeVar("Item")
BackportIntList = typing_extensions.TypeAliasType(  # ruff:ignore[non-pep695-type-alias]  # the backport is under test
    "BackportIntList", list[int]
)
BackportPair = typing_extensions.TypeAliasType(  # ruff:ignore[non-pep695-type-alias]  # the backport is under test
    "BackportPair", tuple[Item, Item], type_params=(Item,)
)


class Rejecting[Element]:
    def __class_getitem__(cls, item: type) -> type[Rejecting]:
        msg = f"cannot take {item}"
        raise ValueError(msg)


type Rejected = Rejecting[int]
# only a type checker runs the import, so evaluating the value raises NameError
type Unevaluable = Decimal
type RecType = int | list[RecType]
type MutualA = int | list[MutualB]
type MutualB = str | list[MutualA]
type Pair[Element] = tuple[Element, Element]
type Outer[Element] = list[tuple[Element, Unevaluable]]
type Leaf = int
type Twice[Element] = tuple[Leaf, Leaf, Element]
type Ident[Element] = Element
type Count[Element] = int
type Nested[Element] = list[Ident[Element]]
type Couple[First, Second] = tuple[First, Second]
type Star[*Elements] = tuple[*Elements]


@mark.parametrize(
    ("module", "name", "overrides", "expected"),
    [
        param("render_pep695", "IntList", {}, ":py:type:`~render_pep695.IntList`", id="public-module"),
        param(
            "render_pep695",
            "IntList",
            {"typehints_fully_qualified": True},
            ":py:type:`render_pep695.IntList`",
            id="fully-qualified",
        ),
        param("render_ext._priv", "ExtAlias", {}, ":py:type:`~render_ext.ExtAlias`", id="public-re-export"),
        param("render_ext._priv", "Hidden", {}, ":py:type:`~render_ext._priv.Hidden`", id="private-only"),
    ],
)
def test_alias_name_reference(
    make_config: MakeConfig,
    import_render_types: Callable[[str], ModuleType],
    module: str,
    name: str,
    overrides: dict[str, bool],
    expected: str,
) -> None:
    assert alias_name_reference(getattr(import_render_types(module), name), make_config(**overrides)) == expected


@fixture(name="import_render_types")
def import_render_types_fixture(monkeypatch: MonkeyPatch, rootdir: Path) -> Callable[[str], ModuleType]:
    monkeypatch.syspath_prepend(rootdir / "test-render-types")
    return import_module


def test_alias_name_reference_without_a_module(config: Config) -> None:
    namespace: dict[str, TypeAliasType] = {}
    exec("type Loose = int", namespace)  # ruff:ignore[exec-builtin]  # only code run outside a module lacks one
    assert alias_name_reference(namespace["Loose"], config) == ":py:type:`~Loose`"


@mark.parametrize(
    "alias",
    [param(Rejected, id="value-raises"), param(Unevaluable, id="value-names-a-guarded-import")],
)
def test_format_annotation_alias_that_cannot_expand_names_itself(config: Config, alias: TypeAliasType) -> None:
    assert format_annotation(alias, config) == f":py:type:`~{__name__}.{alias.__name__}`"


@mark.parametrize(
    ("documented", "expected"),
    [
        param("Config", "other.Config", id="same-name-in-the-parent-package"),
        param("sub.Config", "sub.Config", id="re-exported-where-documented"),
    ],
)
@mark.sphinx("text", testroot="render-types")
def test_format_annotation_alias_links_the_alias_it_names(
    app: SphinxTestApp, build_text: BuildText, documented: str, expected: str
) -> None:
    build_text(
        dedent(f"""\
            .. py:type:: render_scopes.{documented}

            .. py:type:: render_scopes.other.Config
        """)
    )
    alias = import_module("render_scopes.sub").Config
    with annotation_state(app.config, env=app.env, module_prefix="render_scopes.sub"):
        assert format_annotation(alias, app.config) == f":py:type:`~render_scopes.{expected}`"


@mark.parametrize(
    ("annotation", "expected"),
    [
        param(BackportIntList, r":py:class:`list`\ \[:py:class:`int`]", id="typing-extensions"),
        param(
            BackportPair[int],
            r":py:class:`tuple`\ \[:py:class:`int`, :py:class:`int`]",
            id="typing-extensions-subscripted",
        ),
        param(
            RecType,
            rf":py:class:`int` | :py:class:`list`\ \[:py:type:`~{__name__}.RecType`]",
            id="refers-to-itself",
        ),
        param(
            MutualA,
            rf":py:class:`int` | :py:class:`list`\ \[:py:class:`str` | :py:class:`list`\ \["
            rf":py:type:`~{__name__}.MutualA`]]",
            id="refers-to-itself-through-another",
        ),
        param(
            Pair[Pair[int]],
            r":py:class:`tuple`\ \[:py:class:`tuple`\ \[:py:class:`int`, :py:class:`int`], "
            r":py:class:`tuple`\ \[:py:class:`int`, :py:class:`int`]]",
            id="nests-in-its-arguments",
        ),
        param(
            Twice[Twice[int]],
            r":py:class:`tuple`\ \[:py:class:`int`, :py:class:`int`, :py:class:`tuple`\ \[:py:class:`int`, "
            r":py:class:`int`, :py:class:`int`]]",
            id="names-another-alias-twice",
        ),
        param(
            Outer[Outer[int]],
            rf":py:class:`list`\ \[:py:class:`tuple`\ \[:py:type:`~{__name__}.Outer`, "
            rf":py:type:`~{__name__}.Unevaluable`]]",
            id="value-does-not-evaluate",
        ),
        param(Ident[int], r":py:class:`int`", id="value-is-a-bare-type-param"),
        param(Count[int], r":py:class:`int`", id="value-ignores-its-type-param"),
        param(Nested[int], r":py:class:`list`\ \[:py:class:`int`]", id="value-wraps-another-alias"),
        param(
            Star[int, str],
            r":py:class:`tuple`\ \[:py:class:`int`, :py:class:`str`]",
            id="variadic-type-param",
        ),
        param(
            Couple[int],  # ty: ignore[invalid-type-arguments]  # the arity mismatch is under test
            rf":py:type:`~{__name__}.Couple`\ \[:py:class:`int`]",
            id="too-few-args",
        ),
        param(
            Couple[int, str, bool],  # ty: ignore[invalid-type-arguments]  # the arity mismatch is under test
            rf":py:type:`~{__name__}.Couple`\ \[:py:class:`int`, :py:class:`str`, :py:class:`bool`]",
            id="too-many-args",
        ),
    ],
)
def test_format_annotation_alias(config: Config, annotation: Annotation, expected: str) -> None:
    assert format_annotation(annotation, config) == expected


@mark.parametrize(
    ("index", "expected"),
    [
        param(
            ".. autofunction:: render_pep695.type_alias_func",
            dedent("""\
                render_pep695.type_alias_func(value)

                   Take and return aliases.

                   Parameters:
                      **value** ("list"["int"]) -- List of integers

                   Return type:
                      "str" | "int"
                """),
            id="function-undocumented",
        ),
        param(
            dedent("""\
                .. py:type:: render_pep695.IntList

                .. py:type:: render_pep695.StringOrInt

                .. autofunction:: render_pep695.type_alias_func
            """),
            dedent("""\
                type render_pep695.IntList

                type render_pep695.StringOrInt

                render_pep695.type_alias_func(value)

                   Take and return aliases.

                   Parameters:
                      **value** ("IntList") -- List of integers

                   Return type:
                      "StringOrInt"
                """),
            id="function-documented",
        ),
        param(
            dedent("""\
                .. autoclass:: render_pep695.FooStringOrInt
                   :members:
            """),
            dedent("""\
                class render_pep695.FooStringOrInt(thing)

                   A subclass binding the type parameter to an alias.

                   set(thing)

                      Set the thing.

                      Parameters:
                         **thing** ("str" | "int") -- the thing

                      Return type:
                         "str" | "int"
                """),
            id="method-undocumented",
        ),
        param(
            dedent("""\
                .. py:type:: render_pep695.StringOrInt

                .. autoclass:: render_pep695.FooStringOrInt
                   :members:
            """),
            dedent("""\
                type render_pep695.StringOrInt

                class render_pep695.FooStringOrInt(thing)

                   A subclass binding the type parameter to an alias.

                   set(thing)

                      Set the thing.

                      Parameters:
                         **thing** ("StringOrInt") -- the thing

                      Return type:
                         "StringOrInt"
                """),
            id="method-documented",
        ),
        param(
            ".. autofunction:: render_ext_user.ext_alias_func",
            dedent("""\
                render_ext_user.ext_alias_func(value)

                   Take and return an alias of another package.

                   Parameters:
                      **value** ("ExtAlias") -- the value

                   Return type:
                      "ExtAlias"
                """),
            id="another-package",
        ),
        param(
            ".. autofunction:: render_ext_user.ext_pair_func",
            dedent("""\
                render_ext_user.ext_pair_func(value)

                   Take a generic alias of another package.

                   Parameters:
                      **value** ("ExtPair"["int"]) -- a pair

                   Return type:
                      "None"
                """),
            id="another-package-generic",
        ),
        # documented further down the same document, which only the resolve phase can know
        param(
            dedent("""\
                .. automodule:: render_rec_pkg
                   :members:

                .. automodule:: render_rec_pkg.other
                   :members:
            """),
            dedent("""\
                A package using a recursive alias of its submodule.

                render_rec_pkg.some_func(some_param)

                   Take the recursive alias.

                   Parameters:
                      **some_param** ("RecType") -- some description

                   Return type:
                      "None"

                The submodule defining a recursive alias.

                type render_rec_pkg.other.RecType = int | list[RecType]

                   A recursive type alias.
                """),
            id="recursive-alias-of-another-module",
            marks=mark.sphinx(confoverrides={"nitpicky": True}),
        ),
    ],
)
@mark.sphinx("text", testroot="render-types")
def test_pep695_alias_in_a_docstring(build_text: BuildText, warning: StringIO, index: str, expected: str) -> None:
    assert (build_text(index), warning.getvalue()) == (expected, "")


@mark.parametrize(
    ("function", "description", "expected"),
    [
        param("rec_func", "a recursive alias", '("int" | "list"["RecType"]) -- some description', id="plain"),
        param(
            "rec_pair_func",
            "a recursive generic alias",
            '("int" | "list"["RecPair"]) -- some description'
            if version_info >= (3, 14)
            else dedent("""\
                ("Union"["int", "list"["RecPair"]]) -- some
                      description"""),
            id="generic",
        ),
    ],
)
@mark.sphinx("text", testroot="render-types")
def test_pep695_recursive_alias_refers_to_itself(
    build_text: BuildText, warning: StringIO, function: str, description: str, expected: str
) -> None:
    assert (build_text(f".. autofunction:: render_generic.{function}"), warning.getvalue()) == (
        dedent("""\
            render_generic.{}(some_param)

               Take {}.

               Parameters:
                  **some_param** {}

               Return type:
                  "None"
            """).format(function, description, expected),
        "",
    )


@mark.parametrize(
    ("index", "expected"),
    [
        param(".. autofunction:: render_generic.pair_func", '"tuple"["int", "int"]', id="undocumented"),
        param(
            dedent("""\
                .. py:type:: render_generic.Pair

                .. autofunction:: render_generic.pair_func
            """),
            '"Pair"["int"]',
            id="documented",
        ),
    ],
)
@mark.sphinx("text", testroot="render-types", confoverrides={"nitpicky": True})
def test_pep695_generic_alias(build_text: BuildText, warning: StringIO, index: str, expected: str) -> None:
    text = build_text(index)
    assert (text[text.index("render_generic.pair_func") :], warning.getvalue()) == (
        dedent(f"""\
            render_generic.pair_func(value)

               Take a pair.

               Parameters:
                  **value** ({expected}) -- a pair

               Return type:
                  "None"
            """),
        "",
    )


# regression test for #764
@mark.parametrize(
    ("function", "summary", "field"),
    [
        param("plain", "Accept an alias.", '("int" | "Sequence"["str"] | "None") -- an argument.', id="plain"),
        param("wrapped", "Use a generic alias.", '("Sequence"["int"]) -- a sequence of them.', id="generic"),
        param(
            "bounded",
            "Take an alias with a bounded type parameter.",
            dedent("""\
                ("list"["TypeVar"("Element",
                      bound="Sequence"["str"])]) -- a list of them."""),
            id="type-parameter-bound",
        ),
    ],
)
@mark.sphinx("text", testroot="render-types")
def test_pep695_alias_value_needs_a_guarded_import(
    build_text: BuildText, warning: StringIO, function: str, summary: str, field: str
) -> None:
    assert (build_text(f".. autofunction:: render_guard.api.{function}"), warning.getvalue()) == (
        dedent("""\
            render_guard.api.{}(value)

               {}

               Parameters:
                  **value** {}

               Return type:
                  "None"
            """).format(function, summary, field),
        "",
    )
