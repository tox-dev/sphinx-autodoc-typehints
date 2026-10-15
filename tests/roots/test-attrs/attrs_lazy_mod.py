from typing import TYPE_CHECKING

from attrs import define

if TYPE_CHECKING:
    from decimal import Decimal


@define
class Mixed:
    """Annotations evaluate on access, and attrs gives every field a ForwardRef once one of them fails."""

    a: Undefined  # ruff:ignore[undefined-name]  # ty: ignore[unresolved-reference]  # the case under test
    b: Decimal
