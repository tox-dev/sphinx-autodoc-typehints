from __future__ import annotations

from typing import Annotated

from typing_extensions import Doc


def compute(
    x: Annotated[int, Doc("The x input")], y: Annotated[int, Doc("The y input")]
) -> Annotated[int, Doc("The sum")]:
    """
    Compute the sum.

    Parameters
    ----------
    x
        Placeholder.
    y
        Placeholder.
    """
    return x + y


def transform(data: Annotated[str, Doc("The input data")]) -> Annotated[str, Doc("The transformed result")]:
    """Transform data."""
    return data.upper()
