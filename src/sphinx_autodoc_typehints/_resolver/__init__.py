"""Type hint resolution and backfilling from source annotations."""

from __future__ import annotations

from ._attrs import backfill_attrs_annotations
from ._instance_vars import get_instance_var_annotations
from ._stubs import stub_path
from ._type_comments import backfill_type_hints
from ._type_hints import (
    get_all_type_hints,
    get_descriptor_type_hint,
    resolve_annotations,
    resolve_string_annotations,
    resolve_type_guarded_imports,
)
from ._util import collect_documented_type_aliases, get_obj_location

__all__ = [
    "backfill_attrs_annotations",
    "backfill_type_hints",
    "collect_documented_type_aliases",
    "get_all_type_hints",
    "get_descriptor_type_hint",
    "get_instance_var_annotations",
    "get_obj_location",
    "resolve_annotations",
    "resolve_string_annotations",
    "resolve_type_guarded_imports",
    "stub_path",
]
