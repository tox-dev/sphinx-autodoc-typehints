"""
Sphinx extension that writes the type hints of the code autodoc documents into its signatures and docstrings.

The package root exports `setup`, which `_extension` defines, and the installed `__version__`.
"""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._config",
    "sphinx_autodoc_typehints._extension",
    "sphinx_autodoc_typehints.version",
]

# a cached environment from an earlier release pickled the fixup function wrapper under the package root
from sphinx_autodoc_typehints._config import _FixupModuleName as _FixupModuleName
from sphinx_autodoc_typehints._extension import setup
from sphinx_autodoc_typehints.version import __version__

__all__ = [
    "__version__",
    "setup",
]
