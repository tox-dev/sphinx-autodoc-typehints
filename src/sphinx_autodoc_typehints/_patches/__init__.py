"""The monkeypatches `setup` installs on Sphinx and its autodoc extension."""

from __future__ import annotations

from .autodoc import BUILDING, patch_autodoc_type_hints, patch_overload_capture, patch_signature_lines

__all__ = [
    "BUILDING",
    "patch_autodoc_type_hints",
    "patch_overload_capture",
    "patch_signature_lines",
]
