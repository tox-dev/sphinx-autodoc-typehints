"""
Rendering turns resolved types into reST cross-reference markup for docstring fields and signatures.

It sits beside `_resolve` and imports nothing from it; `_documented` hands in what it needs from resolution, such as
the guard binder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING  # simplint: ignore[init-module-content]  # type-only relay avoids cycles

if TYPE_CHECKING:
    from .._refs import (  # simplint: ignore[private-import-path]  # root API stays unchanged
        WrittenTypeAlias as WrittenTypeAlias,
    )
    from .._types import Annotation as Annotation  # simplint: ignore[private-import-path]  # root API stays unchanged
    from .._types import Hint as Hint  # simplint: ignore[private-import-path]  # root API stays unchanged
    from .._types import RenderNode as RenderNode  # simplint: ignore[private-import-path]  # root API stays unchanged
    from .._types import TypeParam as TypeParam  # simplint: ignore[private-import-path]  # root API stays unchanged

from .annotation import (
    as_field_type,
    as_header_type,
    as_signature_type,
    fixup_module_name,
    format_annotation,
    type_param_fields,
    unstar,
)
from .context import AnnotationKind, ScopeExtras, TypeParamScope, annotation_state, render_context
from .deferred import ALIAS_CHOICE_ROLE, AliasChoiceCollector, DeferAliasChoice, alias_choice_role, note_builder
from .enum_member import ENUM_MEMBER_ROLE, enum_member_role, link_enum_member_owner
from .intersphinx import inventory, keep_type_mapping
from .rst import unescape
from .value import CONSTANT_ROLE, VALUE_ROLE, VALUE_STYLESHEET, constant_role, value_markup, value_role

__all__ = [
    "ALIAS_CHOICE_ROLE",
    "CONSTANT_ROLE",
    "ENUM_MEMBER_ROLE",
    "VALUE_ROLE",
    "VALUE_STYLESHEET",
    "AliasChoiceCollector",
    "AnnotationKind",
    "DeferAliasChoice",
    "ScopeExtras",
    "TypeParamScope",
    "alias_choice_role",
    "annotation_state",
    "as_field_type",
    "as_header_type",
    "as_signature_type",
    "constant_role",
    "enum_member_role",
    "fixup_module_name",
    "format_annotation",
    "inventory",
    "keep_type_mapping",
    "link_enum_member_owner",
    "note_builder",
    "render_context",
    "type_param_fields",
    "unescape",
    "unstar",
    "value_markup",
    "value_role",
]
