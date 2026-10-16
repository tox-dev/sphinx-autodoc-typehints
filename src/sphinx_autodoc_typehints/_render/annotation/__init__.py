"""One annotation as reST markup, in a field and in a signature."""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._render.annotation.markup",
    "sphinx_autodoc_typehints._render.annotation.names",
    "sphinx_autodoc_typehints._render.annotation.rendered",
    "sphinx_autodoc_typehints._render.annotation.walker",
]

from sphinx_autodoc_typehints._render.annotation.markup import add_type_css_class
from sphinx_autodoc_typehints._render.annotation.names import fixup_module_name
from sphinx_autodoc_typehints._render.annotation.rendered import as_field_type, as_signature_type
from sphinx_autodoc_typehints._render.annotation.walker import format_annotation, type_param_fields, unstar

__all__ = [
    "add_type_css_class",
    "as_field_type",
    "as_signature_type",
    "fixup_module_name",
    "format_annotation",
    "type_param_fields",
    "unstar",
]
