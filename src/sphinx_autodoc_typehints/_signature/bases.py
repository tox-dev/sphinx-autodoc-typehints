"""Listens to `autodoc-process-bases` to render the "Bases:" line of a class as the extension renders any type."""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx",
    "sphinx.ext",
    "sphinx.ext.autodoc.mock",
    "sphinx_autodoc_typehints._documented",
    "sphinx_autodoc_typehints._objects",
    "sphinx_autodoc_typehints._render",
]

from typing import TYPE_CHECKING

from sphinx.ext.autodoc.mock import ismock

from sphinx_autodoc_typehints._documented import render_scope
from sphinx_autodoc_typehints._objects import prefix_of
from sphinx_autodoc_typehints._render import format_annotation

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc import Options

    from sphinx_autodoc_typehints._types import Hint


def process_bases(app: Sphinx, name: str, _obj: type, _options: Options, bases: list[Hint | str]) -> None:
    """
    Replace each base autodoc lists with the reST the extension renders, so `Mapping[str, int]` reads as in a field.

    Sphinx keeps a string as it is. A mock stays for Sphinx to render, as the extension has no type to read off it.
    """
    with render_scope(app, prefix_of(name)):
        bases[:] = [
            base if isinstance(base, str) or ismock(base) else format_annotation(base, app.config) for base in bases
        ]


__all__ = [
    "process_bases",
]
