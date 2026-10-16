from __future__ import annotations

from importlib.metadata import version
from json import loads as json_loads
from pickle import loads  # ruff:ignore[suspicious-pickle-import]  # loads only a literal payload
from subprocess import check_output  # ruff:ignore[suspicious-subprocess-import]  # modules load per process
from sys import executable, version_info
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark, param

import sphinx_autodoc_typehints  # a from-import of __all__ would become this module's own

if TYPE_CHECKING:
    from sphinx.testing.util import SphinxTestApp


def test_package_exports_setup_and_version() -> None:
    assert sphinx_autodoc_typehints.__all__ == ["__version__", "setup"]


def test_package_version_matches_the_installed_distribution() -> None:
    assert sphinx_autodoc_typehints.__version__ == version("sphinx-autodoc-typehints")


def fixup(module: str) -> str:
    return module


@mark.sphinx("text", testroot="public-api", confoverrides={"typehints_fixup_module_name": fixup})
def test_fixup_module_name_from_an_older_environment_compares_by_source(app: SphinxTestApp) -> None:
    app.build()
    # the value a cached environment holds, written by a release that defined the class at the package root
    cached = loads(  # ruff:ignore[suspicious-pickle-usage]  # the payload is a literal written here
        b"\x80\x04\x95v\x00\x00\x00\x00\x00\x00\x00\x8c\x18sphinx_autodoc_typehints\x94\x8c\x10_FixupModuleName"
        b"\x94\x93\x94)\x81\x94}\x94\x8c\x07_source\x94\x8c1def fixup(module: str) -> str:\n    return module\n"
        b"\x94sb."
    )
    assert app.config.typehints_fixup_module_name == cached


def modules_loaded_by_setup() -> list[str]:
    code = dedent("""\
        import json, sys
        from unittest.mock import MagicMock
        import sphinx_autodoc_typehints

        sphinx_autodoc_typehints.setup(MagicMock())
        print(json.dumps(sorted(sys.modules)))
    """)
    return json_loads(check_output([executable, "-c", code], text=True))


def test_setup_loads_the_modules_it_registers() -> None:
    assert "sphinx_autodoc_typehints._extension" in modules_loaded_by_setup()


@mark.skipif(version_info < (3, 15), reason="__lazy_modules__ (PEP 810) is honored from Python 3.15")
@mark.parametrize(
    "module",
    [
        param("sphinx_autodoc_typehints._resolve.backfill.stubs.find", id="stub-lookup"),
        param("sphinx_autodoc_typehints._resolve.guards.run", id="guard-evaluation"),
        param("sphinx_autodoc_typehints._docstring.formats.numpydoc.convert", id="numpydoc-conversion"),
        param("sphinx_autodoc_typehints._docstring.formats.napoleon.combined", id="napoleon-conversion"),
        param("sphinx_autodoc_typehints._render.annotation.walker", id="annotation-walker"),
        param("sphinx.ext.napoleon", id="sphinx-napoleon"),
        param("numpydoc", id="numpydoc"),
    ],
)
def test_setup_defers_modules_until_first_use(module: str) -> None:  # pragma: >=3.15 cover
    assert module not in modules_loaded_by_setup()
