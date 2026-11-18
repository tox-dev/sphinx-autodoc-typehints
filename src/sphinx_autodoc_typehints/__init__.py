"""
Sphinx extension that writes the type hints of the code autodoc documents into its signatures and docstrings.

The package root exports `setup`, which `_extension` defines, and the installed `__version__`.
"""

from __future__ import annotations

__lazy_modules__ = [
    f"{__spec__.parent}._config",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
    f"{__spec__.parent}._extension",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
    f"{__spec__.parent}.version",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
]

# a cached environment from an earlier release pickled the fixup function wrapper under the package root
from ._config import (
    _FixupModuleName as _FixupModuleName,  # simplint: ignore[private-import-path]  # cached environments reference it
)
from ._extension import setup
from .version import __version__

__all__ = [
    "__version__",
    "setup",
]
