"""Builds an entry's header: the overloads its signature lists, its type parameters, and the type of data."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import Documented as Documented
    from .. import Hint as Hint
    from .. import QualifiedCallable as QualifiedCallable
    from .. import TypeParam as TypeParam

from .data_types import render_header_types
from .type_params import add_type_params

__all__ = [
    "add_type_params",
    "render_header_types",
]
