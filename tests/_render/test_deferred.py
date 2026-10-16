from __future__ import annotations

from pathlib import Path
from re import findall
from sys import version_info
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import mark, param
from sphinx.errors import NoUri

from sphinx_autodoc_typehints._render import ALIAS_CHOICE_ROLE, annotation_state
from sphinx_autodoc_typehints._render.deferred import defer_alias_choice
from sphinx_autodoc_typehints._state import alias_choices, document_alias_choices

if TYPE_CHECKING:
    from io import StringIO

    from conftest import BuildText
    from docutils import nodes
    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment
    from sphinx.testing.util import SphinxTestApp

    from sphinx_autodoc_typehints._types import Annotation


def test_defer_alias_choice_in_a_signature_links(config: Config) -> None:
    with annotation_state(config, signature=True):
        assert defer_alias_choice(config, ":py:type:`~mod.Alias`", ":py:class:`int`") == ":py:type:`~mod.Alias`"


def test_defer_alias_choice_without_an_environment(config: Config) -> None:
    assert defer_alias_choice(config, ":py:type:`~mod.Alias`", ":py:class:`int`") is None


@mark.sphinx("text", testroot="render-types")
def test_defer_alias_choice_between_equal_renderings(app: SphinxTestApp) -> None:
    with annotation_state(app.config, env=app.env):
        assert defer_alias_choice(app.config, ":py:class:`int`", ":py:class:`int`") is None


@mark.parametrize(
    ("objtype", "expected"),
    [
        param(None, (":py:type:`~mod.Alias`", ":py:class:`int`"), id="any-object"),
        param("type", (":py:type:`~mod.Alias`", ":py:class:`int`", "type"), id="one-kind-of-object"),
    ],
)
@mark.sphinx("text", testroot="render-types")
def test_defer_alias_choice_records_the_choice_its_marker_names(
    app: SphinxTestApp, objtype: str | None, expected: tuple[str, ...]
) -> None:
    with annotation_state(app.config, env=app.env):
        marker = defer_alias_choice(app.config, ":py:type:`~mod.Alias`", ":py:class:`int`", objtype=objtype)
    choices = alias_choices(app.env)
    assert (marker, list(choices.values())) == (f":{ALIAS_CHOICE_ROLE}:`{next(iter(choices))}`", [expected])


@mark.parametrize(
    ("documents", "href"),
    [
        param(
            {
                "index": dedent("""\
                    .. autodata:: dummy_module.ConfiguredAlias

                    .. autofunction:: dummy_module.takes_configured_alias
                    """)
            },
            "#dummy_module.ConfiguredAlias",
            id="same-document",
        ),
        param(
            {
                "index": dedent("""\
                    .. toctree::

                       later

                    .. autofunction:: dummy_module.takes_configured_alias
                """),
                "later": ".. autodata:: dummy_module.ConfiguredAlias",
            },
            "later.html#dummy_module.ConfiguredAlias",
            id="later-document",
        ),
    ],
)
@mark.sphinx(
    "html",
    testroot="dummy",
    confoverrides={"autodoc_type_aliases": {"ConfiguredAlias": "dummy_module.ConfiguredAlias"}},
)
def test_deferred_configured_alias_links_its_data_entry(
    build_text: BuildText, documents: dict[str, str], href: str
) -> None:
    assert set(findall(r'class="reference internal" href="([^"]*ConfiguredAlias)"', build_text(**documents))) == {href}


def _int_as_bool_class(annotation: Annotation, _config: Config) -> str | None:
    return ":class:`bool`" if annotation is int else None


def _int_as_unknown_role(annotation: Annotation, _config: Config) -> str | None:
    return ":unknown:`bool`" if annotation is int else None


@mark.sphinx("text", testroot="integration", confoverrides={"typehints_formatter": _int_as_bool_class})
def test_deferred_alias_value_keeps_the_roles_a_formatter_writes(build_text: BuildText) -> None:
    lines = build_text(".. autofunction:: mod_eager.get_user_eager").splitlines()
    rendered = '"bool" | "str"' if version_info >= (3, 14) else '"Union"["bool", "str"]'
    assert lines[lines.index("   Parameters:") + 1] == f"      **user_id** ({rendered}) -- The user identifier"


def _int_as_bare_bool(annotation: Annotation, _config: Config) -> str | None:
    return "`bool`" if annotation is int else None


@mark.parametrize(
    "index",
    [
        param(
            ".. autofunction:: mod_eager.get_user_eager",
            id="configured",
            marks=mark.sphinx(
                "text",
                testroot="integration",
                confoverrides={"typehints_formatter": _int_as_bare_bool, "default_role": "py:class"},
            ),
        ),
        param(
            ".. default-role:: py:class\n\n.. autofunction:: mod_eager.get_user_eager",
            id="document",
            marks=mark.sphinx(
                "text",
                testroot="integration",
                confoverrides={"typehints_formatter": _int_as_bare_bool, "default_role": "emphasis"},
            ),
        ),
    ],
)
def test_deferred_alias_value_keeps_the_default_role(build_text: BuildText, index: str) -> None:
    lines = build_text(index).splitlines()
    rendered = '"bool" | "str"' if version_info >= (3, 14) else '"Union"["bool", "str"]'
    assert lines[lines.index("   Parameters:") + 1] == f"      **user_id** ({rendered}) -- The user identifier"


@mark.sphinx("text", testroot="integration", confoverrides={"typehints_formatter": _int_as_unknown_role})
def test_deferred_alias_value_reports_its_markup_errors_at_the_docstring(
    build_text: BuildText, warning: StringIO
) -> None:
    build_text(".. autofunction:: mod_eager.get_user_eager")
    expected = 'docstring of mod_eager.get_user_eager:3: ERROR: Unknown interpreted text role "unknown"'
    assert expected in warning.getvalue()


_TYPE_ALIAS_FUNC_EXPANDED: Final[str] = dedent("""\
    render_pep695.type_alias_func(value)

       Take and return aliases.

       Parameters:
          **value** ("list"["int"]) -- List of integers

       Return type:
          "str" | "int"
    """)


@mark.parametrize(
    ("index", "documents", "output", "expected"),
    [
        param(
            dedent("""\
                .. autofunction:: mod_eager.count_eager

                .. py:type:: mod_eager.Count
            """),
            {},
            "index.txt",
            dedent("""\
                mod_eager.count_eager(amount, limit)

                   Count up to a limit.

                   Parameters:
                      * **amount** ("Count") -- The amount

                      * **limit** ("int") -- The limit

                   Return type:
                      "None"

                type mod_eager.Count
            """),
            id="later-on-the-page",
            marks=mark.sphinx("text", testroot="integration", parallel=2),
        ),
        param(
            dedent("""\
                .. autofunction:: mod_eager.count_eager

                .. toctree::

                   zz
            """),
            {"zz": ".. py:type:: mod_eager.Count"},
            "index.txt",
            dedent("""\
                mod_eager.count_eager(amount, limit)

                   Count up to a limit.

                   Parameters:
                      * **amount** ("Count") -- The amount

                      * **limit** ("int") -- The limit

                   Return type:
                      "None"

                * "mod_eager.Count"
            """),
            id="later-document",
            marks=mark.sphinx("text", testroot="integration", parallel=2),
        ),
        param(
            dedent("""\
                .. toctree::

                   doc0
                   doc1
                   doc2
                   doc3
                   doc4
                   doc5
            """),
            {
                **{
                    f"doc{number}": dedent(f"""\
                        Doc {number}
                        =====
                    """)
                    for number in range(1, 5)
                },
                "doc0": ".. autofunction:: mod_eager.count_eager",
                "doc5": ".. py:type:: mod_eager.Count",
            },
            "doc0.txt",
            dedent("""\
                mod_eager.count_eager(amount, limit)

                   Count up to a limit.

                   Parameters:
                      * **amount** ("Count") -- The amount

                      * **limit** ("int") -- The limit

                   Return type:
                      "None"
            """),
            id="parallel-read",
            marks=mark.sphinx("text", testroot="integration", parallel=2),
        ),
        param(
            dedent("""\
                .. autofunction:: render_pep695.type_alias_func

                .. toctree::

                   zz_aliases
            """),
            {
                "zz_aliases": dedent("""\
                    .. py:type:: render_pep695.IntList

                       List of integers.
                """)
            },
            "",
            dedent("""\
                render_pep695.type_alias_func(value)

                   Take and return aliases.

                   Parameters:
                      **value** ("IntList") -- List of integers

                   Return type:
                      "str" | "int"

                * "render_pep695.IntList"
            """),
            id="documented-in-a-later-document",
            marks=mark.sphinx("text", testroot="render-types"),
        ),
        param(
            dedent("""\
                .. autofunction:: render_generic.take_pair

                .. py:type:: render_generic.Pair
            """),
            {},
            "",
            dedent("""\
                render_generic.take_pair(value)

                   Take a pair of an undocumented class.

                   Parameters:
                      **value** ("Pair"["Undocumented"]) -- the pair

                   Return type:
                      "None"

                type render_generic.Pair
                """),
            id="undocumented-argument",
            marks=mark.sphinx("text", testroot="render-types"),
        ),
        param(
            dedent("""\
                .. autofunction:: render_generic.take_nested_pair

                .. py:type:: render_generic.Pair
            """),
            {},
            "",
            dedent("""\
                render_generic.take_nested_pair(value)

                   Take a pair of pairs.

                   Parameters:
                      **value** ("Pair"["Pair"["int"]]) -- the pairs

                   Return type:
                      "None"

                type render_generic.Pair
                """),
            id="alias-argument-of-itself",
            marks=mark.sphinx("text", testroot="render-types"),
        ),
        param(
            dedent("""\
                .. automodule:: render_generic
                   :members: pair_func

                .. py:type:: render_generic.Pair
            """),
            {},
            "",
            dedent("""\
                Generic and recursive PEP 695 aliases.

                render_generic.pair_func(value)

                   Take a pair.

                   Parameters:
                      **value** ("Pair"["int"]) -- a pair

                   Return type:
                      "None"

                type render_generic.Pair
                """),
            id="automodule-member-later-on-the-page",
            marks=mark.sphinx("text", testroot="render-types"),
        ),
        param(
            dedent("""\
                .. automodule:: mod_eager
                   :members: count_eager

                .. py:type:: mod_eager.Count
            """),
            {},
            "index.txt",
            dedent("""\
                Module without deferred annotations to test the globals-scanning path.

                mod_eager.count_eager(amount, limit)

                   Count up to a limit.

                   Parameters:
                      * **amount** ("Count") -- The amount

                      * **limit** ("int") -- The limit

                   Return type:
                      "None"

                type mod_eager.Count
            """),
            id="automodule-member-written-alias-later-on-the-page",
            marks=mark.sphinx("text", testroot="integration"),
        ),
        param(
            dedent("""\
                .. autofunction:: render_nested.nested_func

                .. toctree::

                   zz_aliases
            """),
            {
                "zz_aliases": dedent("""\
                    .. py:type:: render_nested.Documented

                       A documented alias.
                """)
            },
            "",
            dedent("""\
                render_nested.nested_func(value)

                   Take and return aliases naming aliases.

                   Parameters:
                      **value** ("Documented" | "int" | "str") -- the value

                   Return type:
                      "int" | "str" | "bytes"

                * "render_nested.Documented"
                """),
            id="expansion-resolves-the-aliases-it-names",
            marks=mark.sphinx("text", testroot="render-types"),
        ),
    ],
)
def test_deferred_alias_links(
    build_text: BuildText, warning: StringIO, index: str, documents: dict[str, str], output: str, expected: str
) -> None:
    assert (build_text(index, output=output, **documents), warning.getvalue()) == (expected, "")


@mark.sphinx("text", testroot="render-types", confoverrides={"primary_domain": None})
def test_deferred_alias_without_a_default_domain_expands(build_text: BuildText, warning: StringIO) -> None:
    text = build_text(".. autofunction:: render_pep695.type_alias_func")
    assert (text, warning.getvalue()) == (_TYPE_ALIAS_FUNC_EXPANDED, "")


@mark.sphinx("text", testroot="render-types")
def test_deferred_alias_a_handler_leaves_without_a_target_expands(
    app: SphinxTestApp, build_text: BuildText, warning: StringIO
) -> None:
    def no_uri(_app: Sphinx, _env: BuildEnvironment, node: nodes.Element, _contnode: nodes.TextElement) -> None:
        if node["reftarget"] == "render_pep695.IntList":
            raise NoUri

    app.connect("missing-reference", no_uri)
    text = build_text(".. autofunction:: render_pep695.type_alias_func")
    assert (text, warning.getvalue()) == (_TYPE_ALIAS_FUNC_EXPANDED, "")


@mark.sphinx("man", testroot="render-types")
def test_deferred_alias_expands_in_a_man_page(build_text: BuildText) -> None:
    page = build_text(".. autofunction:: render_pep695.type_alias_func", output="projectnamenotset.1")
    assert r"\fBvalue\fP (\fBlist\fP[\fBint\fP]) \-\- List of integers" in page.splitlines()


@mark.sphinx("text", testroot="render-types")
def test_deferred_alias_marker_without_a_recorded_choice_is_dropped(build_text: BuildText) -> None:
    assert build_text(f"Text :{ALIAS_CHOICE_ROLE}:`0123456789abcdef` end.") == dedent("""\
        Text  end.
    """)


_ALIAS_DOCUMENT: Final[str] = ".. autofunction:: render_pep695.type_alias_func\n"


@mark.sphinx("text", testroot="render-types")
def test_alias_choice_collector_files_choices_under_their_document(build_text: BuildText, app: SphinxTestApp) -> None:
    build_text(_ALIAS_DOCUMENT)
    assert set(document_alias_choices(app.env)) == {"index"}


@mark.sphinx("text", testroot="render-types")
def test_alias_choice_collector_drops_choices_of_a_removed_document(build_text: BuildText, app: SphinxTestApp) -> None:
    build_text(_ALIAS_DOCUMENT)
    app.env.events.emit("env-purge-doc", app.env, "index")
    assert document_alias_choices(app.env) == {}


@mark.sphinx("text", testroot="render-types")
def test_alias_choice_collector_drops_choices_a_reread_document_no_longer_has(
    build_text: BuildText, app: SphinxTestApp
) -> None:
    build_text(_ALIAS_DOCUMENT)
    (Path(app.srcdir) / "index.rst").write_text("Nothing to resolve.\n")
    app.build()
    assert document_alias_choices(app.env) == {}


@mark.sphinx("text", testroot="render-types", parallel=2)
def test_alias_choice_collector_merges_documents_read_in_workers(build_text: BuildText, app: SphinxTestApp) -> None:
    names = [f"doc{number}" for number in range(8)]
    build_text(_ALIAS_DOCUMENT, **dict.fromkeys(names, _ALIAS_DOCUMENT))
    assert set(document_alias_choices(app.env)) == {"index", *names}
