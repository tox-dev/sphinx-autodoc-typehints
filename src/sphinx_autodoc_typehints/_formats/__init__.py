"""
Docstring format detection and dispatch to format-specific handlers.

Provides the `detect_format` entry point that inspects docstring lines and returns the appropriate
`DocstringFormat` handler. Numpydoc-style sections (`:Parameters:`, `:Returns:`) get a `NumpydocFormat`
handler; everything else (including Napoleon-processed output) gets `SphinxFieldListFormat`.
"""

from __future__ import annotations

from ._base import DocstringFormat, InsertIndexInfo
from ._numpydoc import NumpydocFormat
from ._sphinx import SphinxFieldListFormat

__all__ = ["DocstringFormat", "InsertIndexInfo", "NumpydocFormat", "SphinxFieldListFormat", "detect_format"]


def detect_format(lines: list[str]) -> DocstringFormat:
    """Detect and return the appropriate docstring format handler for the given lines."""
    if NumpydocFormat.detect(lines):
        return NumpydocFormat()
    return SphinxFieldListFormat()
