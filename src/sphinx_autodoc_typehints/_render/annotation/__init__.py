"""One annotation as reST markup, in a field and in a signature."""

from __future__ import annotations

__lazy_modules__ = [
    f"{__spec__.parent}.names",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
    f"{__spec__.parent}.rendered",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
    f"{__spec__.parent}.walker",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import Annotation as Annotation
    from .. import Hint as Hint
    from .. import RenderNode as RenderNode
    from .. import TypeParam as TypeParam
    from .. import WrittenTypeAlias as WrittenTypeAlias

from .names import fixup_module_name
from .rendered import as_field_type, as_header_type, as_signature_type
from .walker import format_annotation, type_param_fields, unstar

__all__ = [
    "as_field_type",
    "as_header_type",
    "as_signature_type",
    "fixup_module_name",
    "format_annotation",
    "type_param_fields",
    "unstar",
]
