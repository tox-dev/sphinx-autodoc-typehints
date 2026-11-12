"""One annotation as reST markup, in a field and in a signature."""

from __future__ import annotations

from typing import TYPE_CHECKING  # simplint: ignore[init-module-content]  # type-only relay avoids cycles

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
