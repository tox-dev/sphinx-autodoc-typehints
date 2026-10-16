"""
Rendering turns resolved types into reST cross-reference markup for docstring fields and signatures.

It sits beside `_resolve` and imports nothing from it; `_documented` hands in what it needs from resolution, such as
the guard binder.
"""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._render.annotation",
    "sphinx_autodoc_typehints._render.context",
    "sphinx_autodoc_typehints._render.deferred",
    "sphinx_autodoc_typehints._render.enum_member",
    "sphinx_autodoc_typehints._render.intersphinx",
    "sphinx_autodoc_typehints._render.rst",
    "sphinx_autodoc_typehints._render.value",
]

from sphinx_autodoc_typehints._render.annotation import (
    add_type_css_class,
    as_field_type,
    as_signature_type,
    fixup_module_name,
    format_annotation,
    type_param_fields,
    unstar,
)
from sphinx_autodoc_typehints._render.context import ScopeExtras, TypeParamScope, annotation_state, render_context
from sphinx_autodoc_typehints._render.deferred import (
    ALIAS_CHOICE_ROLE,
    AliasChoiceCollector,
    DeferAliasChoice,
    alias_choice_role,
    note_builder,
)
from sphinx_autodoc_typehints._render.enum_member import ENUM_MEMBER_ROLE, enum_member_role, link_enum_member_owner
from sphinx_autodoc_typehints._render.intersphinx import keep_type_mapping
from sphinx_autodoc_typehints._render.rst import parse, unescape
from sphinx_autodoc_typehints._render.value import (
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
    "AliasChoiceCollector",
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
    "note_builder",
    "parse",
    "render_context",
    "type_param_fields",
    "unescape",
    "unstar",
    "value_markup",
    "value_role",
]
