from __future__ import annotations

from typing import Annotated

from typing_extensions import Doc


def greet(
    name: Annotated[str, Doc("The person's name")], greeting: Annotated[str, Doc("The greeting phrase")]
) -> Annotated[str, Doc("The full greeting message")]:
    """Say hello."""
    return f"{greeting}, {name}!"


def partial_doc(value: Annotated[int, Doc("The x value")], other: int) -> int:
    """Compute sum.

    :param other: The y value
    """
    return value + other


def no_doc(value: Annotated[int, 42]) -> int:
    """Identity."""
    return value


def docstring_wins(value: Annotated[int, Doc("Doc description")]) -> int:
    """Override.

    :param value: Docstring description
    """
    return value
