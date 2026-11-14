"""
Support for names only a `TYPE_CHECKING` block binds.

It parses the block, runs it, and lets annotations read what it binds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import Documented as Documented

from .overlay import annotation_globals, guarded_names, guarded_names_bound
from .run import guard_bound, resolve_type_guarded_imports

__all__ = [
    "annotation_globals",
    "guard_bound",
    "guarded_names",
    "guarded_names_bound",
    "resolve_type_guarded_imports",
]
