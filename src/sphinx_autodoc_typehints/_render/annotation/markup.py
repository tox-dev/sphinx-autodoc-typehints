"""The role giving a field type the extension's CSS class."""

from __future__ import annotations

__lazy_modules__ = ["sphinx", "sphinx.util"]

from sphinx.util import rst


def add_type_css_class(type_rst: str) -> str:
    """
    Wrap `type_rst` in the role giving a field type the extension's CSS class.

    An empty `type_rst`, a type a `typehints_formatter` hides, stays empty, as a role around nothing is not markup.
    """
    return f":sphinx_autodoc_typehints_type:`{rst.escape(type_rst)}`" if type_rst else ""


__all__ = [
    "add_type_css_class",
]
