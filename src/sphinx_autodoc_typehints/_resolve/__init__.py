"""
Turns the annotations of a documented object into types, falling back to its stub or its type comments.

It sits beside `_render`, neither imports the other, and both import only the foundation modules.
"""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._resolve.aliases",
    "sphinx_autodoc_typehints._resolve.attributes",
    "sphinx_autodoc_typehints._resolve.backfill",
    "sphinx_autodoc_typehints._resolve.evaluate",
    "sphinx_autodoc_typehints._resolve.generics",
    "sphinx_autodoc_typehints._resolve.guards",
    "sphinx_autodoc_typehints._resolve.hints",
    "sphinx_autodoc_typehints._resolve.overloads",
    "sphinx_autodoc_typehints._resolve.typed_dict",
]

from sphinx_autodoc_typehints._resolve.aliases import type_alias_namespace, written_type_alias
from sphinx_autodoc_typehints._resolve.attributes import get_body_annotations, get_instance_var_annotations
from sphinx_autodoc_typehints._resolve.backfill import stub_path
from sphinx_autodoc_typehints._resolve.evaluate import resolve_string_annotations
from sphinx_autodoc_typehints._resolve.generics import (
    TYPE_PARAM_KINDS,
    bound_type_args,
    declared_type_params,
    specialize,
    type_params_of,
)
from sphinx_autodoc_typehints._resolve.guards import (
    SHADOWED_BY_GUARD,
    annotation_globals,
    guard_bound,
    guarded_names_bound,
    resolve_type_guarded_imports,
)
from sphinx_autodoc_typehints._resolve.hints import get_all_type_hints, get_descriptor_type_hint, resolve_annotations
from sphinx_autodoc_typehints._resolve.overloads import OVERLOADS, resolve_overloads
from sphinx_autodoc_typehints._resolve.typed_dict import OPEN, extra_items_type, typed_dict_keys

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
