"""
The `autodoc-process-docstring` side of the extension, which writes types into docstring fields.

In the layering it sits beside `_signature`, above `_documented`, and above the `_render` and `_resolve`
packages those two build on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._refs import (  # simplint: ignore[private-import-path]  # root API stays unchanged
        WrittenTypeAlias as WrittenTypeAlias,
    )
    from .._types import (  # simplint: ignore[private-import-path]  # root API stays unchanged
        Annotation as Annotation,
    )
    from .._types import (  # simplint: ignore[private-import-path]  # root API stays unchanged
        Documented as Documented,
    )
    from .._types import (  # simplint: ignore[private-import-path]  # root API stays unchanged
        Hint as Hint,
    )

from .deprecation import DEPRECATED_DIRECTIVE, DeprecatedDirective
from .formats import mark_numpy_returns, note_attributes_before_napoleon, place_rtype
from .handler import process_docstring

__all__ = [
    "DEPRECATED_DIRECTIVE",
    "DeprecatedDirective",
    "mark_numpy_returns",
    "note_attributes_before_napoleon",
    "place_rtype",
    "process_docstring",
]
