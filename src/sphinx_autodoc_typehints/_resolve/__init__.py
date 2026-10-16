"""
Turns the annotations of a documented object into types, falling back to its stub or its type comments.

It sits beside `_render`, neither imports the other, and both import only the foundation modules.
"""

from __future__ import annotations

from .aliases import type_alias_namespace, written_type_alias
from .attributes import get_body_annotations, get_instance_var_annotations
from .backfill import stub_path
from .evaluate import resolve_string_annotations
from .generics import (
    TYPE_PARAM_KINDS,
    bound_type_args,
    declared_type_params,
    specialize,
    type_params_of,
)
from .guards import (
    SHADOWED_BY_GUARD,
    annotation_globals,
    guard_bound,
    guarded_names_bound,
    resolve_type_guarded_imports,
)
from .hints import get_all_type_hints, get_descriptor_type_hint, resolve_annotations
from .overloads import OVERLOADS, resolve_overloads
from .typed_dict import OPEN, extra_items_type, typed_dict_keys

__all__ = [
    "OPEN",
    "OVERLOADS",
    "SHADOWED_BY_GUARD",
    "TYPE_PARAM_KINDS",
    "annotation_globals",
    "bound_type_args",
    "declared_type_params",
    "extra_items_type",
    "get_all_type_hints",
    "get_body_annotations",
    "get_descriptor_type_hint",
    "get_instance_var_annotations",
    "guard_bound",
    "guarded_names_bound",
    "resolve_annotations",
    "resolve_overloads",
    "resolve_string_annotations",
    "resolve_type_guarded_imports",
    "specialize",
    "stub_path",
    "type_alias_namespace",
    "type_params_of",
    "typed_dict_keys",
    "written_type_alias",
]
