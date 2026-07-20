from __future__ import annotations


def function_with_py310_annotations(
    self,  # ruff:ignore[missing-type-function-argument]
    x: bool | None,
    y: int | str | float,  # ruff:ignore[redundant-numeric-union]
    z: str | None = None,
) -> str:
    """
    Method docstring.

    :param x: foo
    :param y: bar
    :param z: baz
    """
