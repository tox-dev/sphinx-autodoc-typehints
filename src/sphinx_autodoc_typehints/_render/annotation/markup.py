"""The role giving a field type the extension's CSS class."""

from __future__ import annotations

from sphinx.util import rst


def add_type_css_class(type_rst: str) -> str:
    """Wrap `type_rst` in the role giving a field type the extension's CSS class."""
    return f":sphinx_autodoc_typehints_type:`{rst.escape(type_rst)}`"


__all__ = [
    "add_type_css_class",
]
