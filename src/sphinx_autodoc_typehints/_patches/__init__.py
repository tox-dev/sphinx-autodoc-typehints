"""The monkeypatches `setup` installs on Sphinx and its autodoc extension."""

from __future__ import annotations

from .autodoc import BUILDING, patch_autodoc_type_hints, patch_overload_capture, patch_signature_lines
from .napoleon import patch_napoleon_attr_annotations

__all__ = [
    "BUILDING",
    "patch_autodoc_type_hints",
    "patch_napoleon_attr_annotations",
    "patch_overload_capture",
    "patch_signature_lines",
]
