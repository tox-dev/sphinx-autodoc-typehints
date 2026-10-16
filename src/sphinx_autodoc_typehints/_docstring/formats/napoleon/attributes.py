"""
Notes the attributes a docstring documented before napoleon rewrote its `Attributes` section.

With `napoleon_attr_annotations` off, napoleon's own entries then stay untyped while fields written by hand still get
their type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from sphinx_autodoc_typehints._docstring.attributes import documented_attributes

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc import Options

    from sphinx_autodoc_typehints._types import Documented


#: the attributes each docstring documented before napoleon rewrote it, by the id of its line list
WRITTEN_BEFORE_NAPOLEON: Final[dict[int, frozenset[str]]] = {}


def note_attributes_before_napoleon(
    app: Sphinx,
    _what: str,
    _name: str,
    _obj: Documented,
    _options: Options | None,
    lines: list[str],
) -> None:
    """
    Note the attributes a docstring documents before napoleon writes its `Attributes` section as the same reST.

    `napoleon_attr_annotations = False` asks for napoleon's entries to stay untyped, while reST written by hand still
    takes its types from the annotations.
    """
    if not getattr(app.config, "napoleon_attr_annotations", True):
        WRITTEN_BEFORE_NAPOLEON[id(lines)] = frozenset(documented_attributes(lines))


__all__ = [
    "WRITTEN_BEFORE_NAPOLEON",
    "note_attributes_before_napoleon",
]
