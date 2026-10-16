from __future__ import annotations

from importlib.metadata import version
from pickle import loads  # ruff:ignore[suspicious-pickle-import]  # loads only a literal payload
from typing import TYPE_CHECKING

from pytest import mark

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
