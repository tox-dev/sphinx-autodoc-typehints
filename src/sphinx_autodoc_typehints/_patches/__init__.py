"""The monkeypatches `setup` installs on Sphinx, its autodoc extension, and docutils."""

from __future__ import annotations

__lazy_modules__ = ["sphinx_autodoc_typehints._patches.autodoc", "sphinx_autodoc_typehints._patches.docutils_lines"]

from sphinx_autodoc_typehints._patches.autodoc import (
    BUILDING,
    patch_autodoc_type_hints,
    patch_overload_capture,
    patch_signature_lines,
)
from sphinx_autodoc_typehints._patches.docutils_lines import patch_doctest_line_number

__all__ = [
    "BUILDING",
    "patch_autodoc_type_hints",
    "patch_doctest_line_number",
    "patch_overload_capture",
    "patch_signature_lines",
]
