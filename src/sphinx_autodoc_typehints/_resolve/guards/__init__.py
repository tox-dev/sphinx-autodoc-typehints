"""
Support for names only a `TYPE_CHECKING` block binds.

It parses the block, runs it, and lets annotations read what it binds.
"""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._resolve.guards.overlay",
    "sphinx_autodoc_typehints._resolve.guards.parse",
    "sphinx_autodoc_typehints._resolve.guards.run",
]

from sphinx_autodoc_typehints._resolve.guards.overlay import (
    SHADOWED_BY_GUARD,
    annotation_globals,
    guarded_names,
    guarded_names_bound,
)
from sphinx_autodoc_typehints._resolve.guards.parse import guard_binds
from sphinx_autodoc_typehints._resolve.guards.run import guard_bound, resolve_type_guarded_imports

__all__ = [
    "SHADOWED_BY_GUARD",
    "annotation_globals",
    "guard_binds",
    "guard_bound",
    "guarded_names",
    "guarded_names_bound",
    "resolve_type_guarded_imports",
]
