"""
Keeps napoleon from typing attributes, and notes those a docstring documented before napoleon rewrote it.

With `napoleon_attr_annotations` off, napoleon's own entries then stay untyped while fields written by hand still get
their type.
"""

from __future__ import annotations

__lazy_modules__ = ["sphinx_autodoc_typehints._docstring.attributes"]

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from sphinx_autodoc_typehints._docstring.attributes import documented_attributes

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.ext.autodoc import Options

    from sphinx_autodoc_typehints._types import Documented


# napoleon types an attribute from its annotation while the option is truthy, and the extension types attributes itself;
# napoleon sees this falsy, the extension reads the user's setting from it, and the cached environment compares two of
# them by that setting, so changing it still re-reads every document
@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _NapoleonAttrAnnotations:
    requested: bool

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return repr(self.requested)


_REQUESTED_WITHOUT_NAPOLEON: Final[_NapoleonAttrAnnotations] = _NapoleonAttrAnnotations(requested=True)


def take_over_napoleon_attr_annotations(_app: Sphinx, config: Config) -> None:
    """Turn napoleon's `napoleon_attr_annotations` off for napoleon, keeping what the user set for the extension."""
    if "napoleon_attr_annotations" in config:
        config.napoleon_attr_annotations = _NapoleonAttrAnnotations(requested=config.napoleon_attr_annotations)


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
    # an entry outlives its docstring when a handler between this one and `process_docstring` raises, and a later line
    # list allocated at the same address would then read it as its own
    WRITTEN_BEFORE_NAPOLEON.clear()
    if not getattr(app.config, "napoleon_attr_annotations", _REQUESTED_WITHOUT_NAPOLEON).requested:
        WRITTEN_BEFORE_NAPOLEON[id(lines)] = frozenset(documented_attributes(lines))


__all__ = [
    "WRITTEN_BEFORE_NAPOLEON",
    "note_attributes_before_napoleon",
    "take_over_napoleon_attr_annotations",
]
