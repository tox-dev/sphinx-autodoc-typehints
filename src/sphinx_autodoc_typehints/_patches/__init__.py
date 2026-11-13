"""The monkeypatches `setup` installs on Sphinx and its autodoc extension."""

from __future__ import annotations

from typing import TYPE_CHECKING  # simplint: ignore[init-module-content]  # type-only relay avoids cycles

if TYPE_CHECKING:
    from .._types import Annotation as Annotation  # simplint: ignore[private-import-path]  # root API stays unchanged
    from .._types import Documented as Documented  # simplint: ignore[private-import-path]  # root API stays unchanged

from .autodoc import BUILDING, patch_autodoc_type_hints, patch_overload_capture, patch_signature_lines
from .napoleon import patch_napoleon_attr_annotations

__all__ = [
    "BUILDING",
    "patch_autodoc_type_hints",
    "patch_napoleon_attr_annotations",
    "patch_overload_capture",
    "patch_signature_lines",
]
