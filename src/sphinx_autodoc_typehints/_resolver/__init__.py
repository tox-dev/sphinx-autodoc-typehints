"""Type hint resolution and backfilling from source annotations."""

from __future__ import annotations

from ._attrs import backfill_attrs_annotations
from ._type_comments import backfill_type_hints
from ._type_hints import get_all_type_hints
from ._util import collect_documented_type_aliases, get_obj_location

__all__ = [
    "backfill_attrs_annotations",
    "backfill_type_hints",
    "collect_documented_type_aliases",
    "get_all_type_hints",
    "get_obj_location",
]
