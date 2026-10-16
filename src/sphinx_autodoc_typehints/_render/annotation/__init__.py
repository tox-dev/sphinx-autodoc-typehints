"""One annotation as reST markup, in a field and in a signature."""

from __future__ import annotations

from .markup import add_type_css_class
from .names import fixup_module_name
from .rendered import as_field_type, as_signature_type
from .walker import format_annotation, type_param_fields, unstar

__all__ = [
    "add_type_css_class",
    "as_field_type",
    "as_signature_type",
    "fixup_module_name",
    "format_annotation",
    "type_param_fields",
    "unstar",
]
