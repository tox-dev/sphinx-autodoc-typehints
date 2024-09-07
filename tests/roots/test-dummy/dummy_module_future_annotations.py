from __future__ import annotations


def function_with_py310_annotations(
    self,  # noqa: ANN001
    x: bool | None,
    y: int | str | float,  # noqa: PYI041
    z: str | None = None,
) -> str:
    """
    Method docstring.

    :param x: foo
    :param y: bar
    :param z: baz
    """
