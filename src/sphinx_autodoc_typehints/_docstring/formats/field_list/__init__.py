"""Editing of the reST field list in a docstring, the form numpydoc's sections convert to."""

from __future__ import annotations

from .edit import FieldListFormat, write_rtype
from .keywords import STAR_PREFIXES, field_keyword_and_argument

__all__ = [
    "STAR_PREFIXES",
    "FieldListFormat",
    "field_keyword_and_argument",
    "write_rtype",
]
