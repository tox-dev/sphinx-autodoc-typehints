from __future__ import annotations

import pathlib
import sys
from typing import TYPE_CHECKING, Any

from sphinx_autodoc_typehints import process_docstring

sys.path.insert(0, str(pathlib.Path(__file__).parent))

master_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
]

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config


def setup(app: Sphinx) -> None:
    """Install a formatter that documents a second object, re-entering the docstring handler."""

    def inner(flag: str) -> str: ...

    def formatter(annotation: Any, config: Config) -> None:  # ruff:ignore[unused-function-argument]
        if annotation is bool:
            process_docstring(app, "function", "inner_mod.inner", inner, None, ["Inner.", "", ":return: it"])

    app.config.typehints_formatter = formatter
