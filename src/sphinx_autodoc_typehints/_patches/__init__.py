"""The monkeypatches `setup` installs on Sphinx, its autodoc extension, and docutils."""

from __future__ import annotations

from .autodoc import BUILDING, patch_autodoc_type_hints, patch_overload_capture, patch_signature_lines
from .docutils_lines import patch_doctest_line_number

__all__ = [
    "BUILDING",
    "patch_autodoc_type_hints",
    "patch_doctest_line_number",
    "patch_overload_capture",
    "patch_signature_lines",
]
