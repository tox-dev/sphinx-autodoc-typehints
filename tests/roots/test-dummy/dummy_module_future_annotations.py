from __future__ import annotations


def function_with_py310_annotations(
    self, x: bool | None, y: int | str | float, z: str | None = None  # noqa: U100
) -> str:
    """
    Method docstring.

    :param x: foo
    :param y: bar
    :param z: baz
    """
