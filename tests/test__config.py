from __future__ import annotations

from functools import partial
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark, param, raises
from sphinx.errors import ConfigError

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp


@mark.sphinx("text", testroot="public-api")
def test_setup_registers_the_documented_options(app: SphinxTestApp) -> None:
    app.build()
    expected = {
        "always_document_param_types": (False, "env", frozenset()),
        "always_use_bars_union": (False, "env", frozenset()),
        "simplify_optional_unions": (True, "env", frozenset()),
        "typehints_defaults": (None, "env", frozenset()),
        "typehints_document_overloads": (True, "env", frozenset()),
        "typehints_document_rtype": (True, "env", frozenset()),
        "typehints_document_rtype_none": (True, "env", frozenset()),
        "typehints_fixup_module_name": (None, "env", frozenset()),
        "typehints_formatter": (None, "", frozenset()),
        "typehints_fully_qualified": (False, "env", frozenset({bool})),
        "typehints_use_rtype": (True, "env", frozenset()),
        "typehints_use_signature": (False, "env", frozenset()),
        "typehints_use_signature_return": (False, "env", frozenset()),
    }
    assert {
        name: (getattr(app.config, name), (option := app.config.values[name]).rebuild, option.valid_types)
        for name in expected
    } == expected


@mark.parametrize(
    "pattern",
    [
        param(
            # the message lists the valid values as a set, in no fixed order
            r"^typehints_defaults needs to be one of \{.*\}, not 'comma-after'$",
            marks=mark.sphinx("text", testroot="dummy", confoverrides={"typehints_defaults": "comma-after"}),
            id="defaults",
        ),
        param(
            r"^typehints_formatter needs to be callable or `None`, not some string$",
            marks=mark.sphinx("text", testroot="dummy", confoverrides={"typehints_formatter": "some string"}),
            id="formatter",
        ),
    ],
)
def test_unusable_option_fails_the_build(app: SphinxTestApp, pattern: str) -> None:
    with raises(ConfigError, match=pattern):
        app.build()


def _fixup_to_first(module: str) -> str:
    return module.replace("wrong_module_path", "first")


def _fixup_to_second(module: str) -> str:
    return module.replace("wrong_module_path", "second")


@mark.parametrize(
    ("first", "second"),
    [
        param(_fixup_to_first, _fixup_to_second, id="function"),
        param(partial(_fixup_to_first), partial(_fixup_to_second), id="no-source"),
    ],
)
@mark.sphinx("text", testroot="dummy", confoverrides={"typehints_fully_qualified": True})
def test_fixup_module_name_change_rereads_documents(
    build_text: BuildText,
    app: SphinxTestApp,
    make_app: Callable[..., SphinxTestApp],
    first: Callable[[str], str],
    second: Callable[[str], str],
) -> None:
    build_text(".. autofunction:: wrong_module_path.f")
    for fixup in (first, second):
        make_app(
            "text",
            srcdir=app.srcdir,
            confoverrides={"typehints_fixup_module_name": fixup, "typehints_fully_qualified": True},
        ).build()

    assert (Path(app.outdir) / "index.txt").read_text() == dedent("""\
        wrong_module_path.f()

           Return type:
              "second.A"
        """)


@mark.sphinx("text", testroot="dummy", confoverrides={"typehints_fixup_module_name": _fixup_to_first})
def test_fixup_module_name_unchanged_keeps_environment(
    build_text: BuildText, app: SphinxTestApp, make_app: Callable[..., SphinxTestApp]
) -> None:
    build_text(".. autofunction:: wrong_module_path.f")
    rebuilt = make_app("text", srcdir=app.srcdir, confoverrides={"typehints_fixup_module_name": _fixup_to_first})
    rebuilt.build()

    assert "typehints_fixup_module_name" not in rebuilt.status.getvalue()


@mark.parametrize(
    "expected",
    [
        param(
            '"dummy_module.Bounded"',
            marks=mark.sphinx("text", testroot="dummy", confoverrides={"autodoc_typehints_format": "fully-qualified"}),
            id="follows-autodoc",
        ),
        param(
            '"Bounded"',
            marks=mark.sphinx(
                "text",
                testroot="dummy",
                confoverrides={"autodoc_typehints_format": "fully-qualified", "typehints_fully_qualified": False},
            ),
            id="set-explicitly",
        ),
    ],
)
@mark.usefixtures("wide_text_output")
def test_fully_qualified_defaults_to_autodoc_typehints_format(build_text: BuildText, expected: str) -> None:
    assert build_text(".. py:data:: dummy_module.Bounded\n\n.. autofunction:: dummy_module.bounded") == dedent(f"""\
        dummy_module.Bounded

        dummy_module.bounded(value)

           Take a bounded type parameter.

           Parameters:
              **value** ({expected}) -- the value

           Return type:
              {expected}
        """)


@mark.sphinx("text", testroot="dummy")
def test_always_document_param_types_change_rereads_sources(
    build_text: BuildText, app: SphinxTestApp, make_app: Callable[..., SphinxTestApp]
) -> None:
    build_text(".. autofunction:: dummy_module.undocumented_function")
    make_app("text", srcdir=app.srcdir, confoverrides={"always_document_param_types": True}).build()

    assert (Path(app.outdir) / "index.txt").read_text() == dedent("""\
        dummy_module.undocumented_function(x)

           Hi

           Parameters:
              **x** ("int")

           Return type:
              "str"
        """)


@mark.sphinx(
    "text",
    testroot="dummy",
    confoverrides={"typehints_formatter": lambda _annotation, _config: "Formatted"},
    exception_on_warning=True,
)
def test_formatter_keeps_the_config_cacheable(build_text: BuildText) -> None:
    build_text(".. autofunction:: dummy_module.undocumented_function")
