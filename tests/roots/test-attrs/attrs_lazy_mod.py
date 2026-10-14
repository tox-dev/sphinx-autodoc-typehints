from typing import TYPE_CHECKING

import attrs

if TYPE_CHECKING:
    from decimal import Decimal


@attrs.define
class Mixed:
    """Evaluated lazily: attrs gives every field a ForwardRef once one of them fails."""

    a: Undefined  # ruff:ignore[undefined-name]  # ty: ignore[unresolved-reference]  # the case under test
    b: Decimal
