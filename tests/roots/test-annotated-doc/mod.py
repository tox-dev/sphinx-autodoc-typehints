from __future__ import annotations

from typing import Annotated

from typing_extensions import Doc


def greet(
    name: Annotated[str, Doc("The person's name")], greeting: Annotated[str, Doc("The greeting phrase")]
) -> Annotated[str, Doc("The full greeting message")]:
    """Say hello."""
    return f"{greeting}, {name}!"


def partial_doc(x: Annotated[int, Doc("The x value")], y: int) -> int:
    """Compute sum.

    :param y: The y value
    """
    return x + y


def no_doc(x: Annotated[int, 42]) -> int:
    """Identity."""
    return x


def docstring_wins(x: Annotated[int, Doc("Doc description")]) -> int:
    """Override.

    :param x: Docstring description
    """
    return x
