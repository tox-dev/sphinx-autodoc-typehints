from __future__ import annotations

from operator import attrgetter
from textwrap import dedent
from typing import TYPE_CHECKING, Final, Protocol

from pytest import MarkDecorator, fixture, mark, param

from sphinx_autodoc_typehints._refs import WrittenTypeAlias
from sphinx_autodoc_typehints._resolve.aliases import (
    type_alias_namespace,
    written_type_alias,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO
    from types import ModuleType

    from conftest import BuildText
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment
    from sphinx.testing.util import SphinxTestApp

    from sphinx_autodoc_typehints._types import Annotation

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="resolve-stubs")


class _DocumentTypes(Protocol):
    def __call__(self, *names: str) -> BuildEnvironment: ...


_CONFIGURED: Final[dict[str, str | bool]] = {"name": "pkg.Configured", "configured": True, "crossref": False}


def _crossref(name: str) -> dict[str, str | bool]:
    return {"name": name, "configured": False, "crossref": True}


@mark.parametrize(
    ("aliases", "owner", "module", "documented", "expected"),
    [
        param({}, lambda _: len, "mymod", ("other.Foo",), {}, id="other-module"),
        param({}, lambda _: len, "mymod", ("mymod.sub.Foo",), {}, id="submodule"),
        param({}, lambda _: len, "mymod", ("Foo",), {}, id="unqualified"),
        param(
            {}, lambda _: len, "am.Ops", ("am.Vector",), {"Vector": _crossref("Vector")}, id="module-around-a-method"
        ),
        param(
            {},
            lambda _: len,
            "am.Ops",
            ("am.Ops.Vector",),
            {"Vector": _crossref("Vector")},
            id="class-body-around-a-method",
        ),
        param(
            {},
            attrgetter("quoted"),
            "elsewhere",
            ("elsewhere.MyType",),
            {"MyType": _crossref("MyType")},
            id="string-naming-a-type",
        ),
        param(
            {"Configured": "pkg.Configured"},
            lambda _: len,
            "mymod",
            None,
            {"Configured": _CONFIGURED},
            id="configured-without-an-environment",
        ),
        param(
            {"Configured": "pkg.Configured"},
            lambda _: len,
            "mymod",
            ("mymod.Hook", "mymod.Tag"),
            {"Configured": _CONFIGURED, "Hook": _crossref("Hook"), "Tag": _crossref("Tag")},
            id="configured-with-an-environment",
        ),
    ],
)
def test_type_alias_namespace(
    aliased_module: ModuleType,
    documented_types: _DocumentTypes,
    aliases: dict[str, str],
    owner: Callable[[ModuleType], Callable[..., object]],
    module: str,
    documented: tuple[str, ...] | None,
    expected: dict[str, dict[str, str | bool]],
) -> None:
    env = None if documented is None else documented_types(*documented)
    deferred, written = type_alias_namespace(aliases, owner(aliased_module), module, env)
    assert ({name: vars(ref) for name, ref in deferred.items()}, written) == (expected, {})


@fixture(name="documented_types")
def documented_types_fixture(app: SphinxTestApp) -> _DocumentTypes:
    def document(*names: str) -> BuildEnvironment:
        for name in names:
            app.env.domains.python_domain.note_object(name, "type", name)
        return app.env

    return document


@mark.parametrize(
    ("attr", "expected"),
    [
        param("aliased", {"x": (WrittenTypeAlias, "MyAlias", int)}, id="written-as-the-alias"),
        param("plain", {}, id="written-as-the-type"),
        param("lam", {}, id="lambda"),
        param("Point.__init__", {}, id="generated-without-source"),
    ],
)
def test_type_alias_namespace_of_an_annotation_written_as_an_alias(
    aliased_module: ModuleType,
    documented_types: _DocumentTypes,
    attr: str,
    expected: dict[str, tuple[type, str, type]],
) -> None:
    env = documented_types(f"{aliased_module.__name__}.MyAlias")
    _, written = type_alias_namespace({}, attrgetter(attr)(aliased_module), aliased_module.__name__, env)
    assert {name: (type(alias), alias.name, alias.value) for name, alias in written.items()} == expected


@fixture(name="aliased_module")
def aliased_module_fixture(make_module: Callable[[str], ModuleType]) -> ModuleType:
    return make_module(
        dedent("""\
            from dataclasses import dataclass

            MyAlias = int

            def aliased(x: MyAlias) -> None: ...

            def plain(x: int) -> None: ...

            def quoted(x: "MyType") -> None: ...

            lam = lambda x: None
            lam.__annotations__ = {"x": int}

            @dataclass
            class Point:
                x: int
        """)
    )


@mark.parametrize(
    "error",
    [
        param(NameError("Callable"), id="name-error"),
        param(TypeError("type 'DiGraph' is not subscriptable"), id="type-error"),
        param(ValueError("a shape takes an int"), id="value-error"),
    ],
)
def test_type_alias_namespace_of_annotations_that_raise(documented_types: _DocumentTypes, error: Exception) -> None:
    # PEP 649 evaluates annotations on first read, naming what only a TYPE_CHECKING block binds (#712)
    class AnnotationsRaiser:
        @property
        def __annotations__(self) -> dict[str, type]:  # ruff:ignore[bad-dunder-method-name]  # the case under test
            raise error

    deferred, written = type_alias_namespace({}, AnnotationsRaiser(), "mymod", documented_types("mymod.MyType"))
    assert ({name: vars(ref) for name, ref in deferred.items()}, written) == (
        {"MyType": {"name": "MyType", "configured": False, "crossref": True}},
        {},
    )


@mark.parametrize(
    ("written", "namespace", "expected"),
    [
        param("Count", {"Count": int}, ("Count", int), id="alias"),
        param("_Count", {"_Count": int}, None, id="private"),
        param("Count", {}, None, id="not-in-the-namespace"),
        param("Count", {"Count": str}, None, id="other-value"),
    ],
)
def test_written_type_alias(written: str, namespace: dict[str, type], expected: tuple[str, type] | None) -> None:
    alias = written_type_alias(written, int, namespace)
    assert (None if alias is None else (alias.name, alias.value)) == expected


def _special_formatter(annotation: Annotation, _config: Config) -> str | None:
    return "**SPECIAL**" if getattr(annotation, "__name__", None) == "Special" else None


@mark.parametrize(
    ("index", "expected"),
    [
        param(
            ".. autofunction:: mod_eager.describe",
            dedent("""\
                mod_eager.describe(value)

                   Describe a value.

                   Parameters:
                      **value** ("int") -- an int value

                   Return type:
                      "None"
            """),
            id="doc-description",
        ),
        param(
            dedent("""\
                .. autoclass:: mod_eager.Special

                .. autofunction:: mod_eager.take_special
            """),
            dedent("""\
                class mod_eager.Special

                   A class a formatter renders.

                mod_eager.take_special(value)

                   Take a special value.

                   Parameters:
                      **value** (**SPECIAL**) -- The value

                   Return type:
                      "None"
            """),
            id="formatter",
        ),
        param(
            dedent("""\
                .. autoclass:: mod_eager.Sub
                   :members:
                   :inherited-members:
            """),
            dedent("""\
                class mod_eager.Sub

                   A subclass binding the type parameter.

                   echo(value)

                      Echo a value.

                      Parameters:
                         **value** ("int") -- The value

                      Return type:
                         "int"
            """),
            id="bound-type-parameter",
        ),
        param(
            ".. autofunction:: mod_eager.count_up",
            dedent("""\
                mod_eager.count_up()

                   Count up.

                   Yields:
                      numbers

                   Return type:
                      "str"

                   Returns:
                      a name
            """),
            id="generator-return",
        ),
        param(
            dedent("""\
                .. py:data:: mod_eager.Ticket

                .. autofunction:: mod_eager.take_ticket
            """),
            dedent("""\
                mod_eager.Ticket

                mod_eager.take_ticket(number)

                   Take a ticket.

                   Parameters:
                      **number** ("Ticket" ("int")) -- The number

                   Return type:
                      "None"
            """),
            id="documented-newtype",
        ),
        param(
            dedent("""\
                .. py:type:: mod_deferred.UserId

                   A user identifier that can be either an integer or a string.

                .. autofunction:: mod_deferred.get_user
            """),
            dedent("""\
                type mod_deferred.UserId

                   A user identifier that can be either an integer or a string.

                mod_deferred.get_user(user_id)

                   Get a user by ID.

                   Parameters:
                      **user_id** ("UserId") -- The user identifier

                   Return type:
                      "str"
            """),
            id="deferred-union",
        ),
        param(
            dedent("""\
                .. py:type:: mod_deferred.RequestData

                   Request data dictionary.

                .. autofunction:: mod_deferred.process_request
            """),
            dedent("""\
                type mod_deferred.RequestData

                   Request data dictionary.

                mod_deferred.process_request(data)

                   Process a request.

                   Parameters:
                      **data** ("RequestData") -- The request data

                   Return type:
                      "bool"
            """),
            id="deferred-generic",
        ),
        param(
            dedent("""\
                .. py:type:: mod_eager.UserId

                   A user identifier.

                .. autofunction:: mod_eager.get_user_eager
            """),
            dedent("""\
                type mod_eager.UserId

                   A user identifier.

                mod_eager.get_user_eager(user_id)

                   Get a user by ID.

                   Parameters:
                      **user_id** ("UserId") -- The user identifier

                   Return type:
                      "str"
            """),
            id="eager-union",
        ),
        param(
            dedent("""\
                .. py:type:: mod_eager.Count

                .. autofunction:: mod_eager.count_eager
            """),
            dedent("""\
                type mod_eager.Count

                mod_eager.count_eager(amount, limit)

                   Count up to a limit.

                   Parameters:
                      * **amount** ("Count") -- The amount

                      * **limit** ("int") -- The limit

                   Return type:
                      "None"
            """),
            id="eager-only-where-written",
        ),
        param(
            dedent("""\
                .. py:type:: mod_eager.UserId

                .. automethod:: mod_eager.Users.get
            """),
            dedent("""\
                type mod_eager.UserId

                Users.get(user_id)

                   Get a user by ID.

                   Parameters:
                      **user_id** ("UserId") -- The user identifier

                   Return type:
                      "str"
            """),
            id="eager-in-a-method",
        ),
    ],
)
@mark.sphinx("text", testroot="integration", confoverrides={"typehints_formatter": _special_formatter})
def test_build_renders_an_alias_as_written(build_text: BuildText, warning: StringIO, index: str, expected: str) -> None:
    assert (build_text(index), warning.getvalue()) == (expected, "")
