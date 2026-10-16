"""The monkeypatches `setup` installs on Sphinx, its autodoc and napoleon extensions, and docutils."""

from __future__ import annotations

from .autodoc import BUILDING, patch_autodoc_type_hints, patch_overload_capture, patch_signature_lines
from .docutils_lines import patch_line_numbers
from .napoleon import patch_lookup_annotation

__all__ = [
    "BUILDING",
    "patch_autodoc_type_hints",
    "patch_line_numbers",
    "patch_lookup_annotation",
    "patch_overload_capture",
    "patch_signature_lines",
]
