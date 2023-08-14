from __future__ import annotations


def function_with_py310_annotations(
    self,  # noqa: ANN001, ARG001
    x: bool | None,  # noqa: ARG001
    y: int | str | float,  # noqa: ARG001,PYI041
    z: str | None = None,  # noqa: ARG001
) -> str:
    """
    Method docstring.

    :param x: foo
    :param y: bar
    :param z: baz
    """
