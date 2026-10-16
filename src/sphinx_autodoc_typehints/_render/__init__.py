"""
Rendering turns resolved types into reST cross-reference markup for docstring fields and signatures.

It sits beside `_resolve` and imports nothing from it; `_documented` hands in what it needs from resolution, such as
the guard binder.
"""

from __future__ import annotations

from .annotation import (
    add_type_css_class,
    as_field_type,
    as_signature_type,
    fixup_module_name,
    format_annotation,
    type_param_fields,
    unstar,
)
from .context import ScopeExtras, TypeParamScope, annotation_state, render_context
from .deferred import ALIAS_CHOICE_ROLE, DeferAliasChoice, alias_choice_role, merge_alias_choices
from .intersphinx import keep_type_mapping
from .rst import parse, unescape

__all__ = [
    "ALIAS_CHOICE_ROLE",
    "DeferAliasChoice",
    "ScopeExtras",
    "TypeParamScope",
    "add_type_css_class",
    "alias_choice_role",
    "annotation_state",
    "as_field_type",
    "as_signature_type",
    "fixup_module_name",
    "format_annotation",
    "keep_type_mapping",
    "merge_alias_choices",
    "parse",
    "render_context",
    "type_param_fields",
    "unescape",
    "unstar",
]
