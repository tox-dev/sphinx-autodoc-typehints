"""Keep napoleon from typing attributes before the extension does."""

from __future__ import annotations

from functools import lru_cache, wraps

from sphinx.ext.napoleon.docstring import GoogleDocstring

from .autodoc import BUILDING


@lru_cache
def patch_napoleon_attr_annotations() -> None:
    """Leave the config boolean intact while preventing napoleon from adding its own attribute types."""
    original = GoogleDocstring._lookup_annotation

    @wraps(original)
    def lookup_annotation(self: GoogleDocstring, name: str) -> str:
        return "" if BUILDING else original(self, name)

    GoogleDocstring._lookup_annotation = lookup_annotation  # ty: ignore[invalid-assignment]  # Sphinx's method is patched


__all__ = [
    "patch_napoleon_attr_annotations",
]
