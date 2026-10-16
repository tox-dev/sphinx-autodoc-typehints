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
from .enum_member import ENUM_MEMBER_ROLE, enum_member_role, link_enum_member_owner
from .intersphinx import keep_type_mapping
from .rst import parse, unescape
from .value import (
    CONSTANT_ROLE,
    VALUE_ROLE,
    VALUE_STYLESHEET,
    add_value_stylesheet,
    constant_role,
    value_markup,
    value_role,
)

__all__ = [
    "ALIAS_CHOICE_ROLE",
    "CONSTANT_ROLE",
    "ENUM_MEMBER_ROLE",
    "VALUE_ROLE",
    "VALUE_STYLESHEET",
    "DeferAliasChoice",
    "ScopeExtras",
    "TypeParamScope",
    "add_type_css_class",
    "add_value_stylesheet",
    "alias_choice_role",
    "annotation_state",
    "as_field_type",
    "as_signature_type",
    "constant_role",
    "enum_member_role",
    "fixup_module_name",
    "format_annotation",
    "keep_type_mapping",
    "link_enum_member_owner",
    "merge_alias_choices",
    "parse",
    "render_context",
    "type_param_fields",
    "unescape",
    "unstar",
    "value_markup",
    "value_role",
]
