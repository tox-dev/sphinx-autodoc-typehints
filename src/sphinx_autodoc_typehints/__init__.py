"""
Sphinx extension that writes the type hints of the code autodoc documents into its signatures and docstrings.

The package root exports only `setup`, which `_extension` defines.
"""

from __future__ import annotations

# a cached environment from an earlier release pickled the fixup function wrapper under the package root
from ._config import _FixupModuleName as _FixupModuleName
from ._extension import setup

__all__ = [
    "setup",
]
