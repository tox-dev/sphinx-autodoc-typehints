"""
Keeps or strips the types in the signatures autodoc writes, and adds types to the headers the Python domain builds.

In the import layering the package sits beside `_docstring` and above the `_documented`, `_render` and
`_resolve` layers it calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._objects import (  # simplint: ignore[private-import-path]  # root API stays unchanged
        QualifiedCallable as QualifiedCallable,
    )
    from .._refs import (  # simplint: ignore[private-import-path]  # root API stays unchanged
        WrittenTypeAlias as WrittenTypeAlias,
    )
    from .._types import Documented as Documented  # simplint: ignore[private-import-path]  # root API stays unchanged
    from .._types import Hint as Hint  # simplint: ignore[private-import-path]  # root API stays unchanged
    from .._types import TypeParam as TypeParam  # simplint: ignore[private-import-path]  # root API stays unchanged

from .bases import process_bases
from .handler import process_signature
from .header import add_type_params, render_header_types

__all__ = [
    "add_type_params",
    "process_bases",
    "process_signature",
    "render_header_types",
]
