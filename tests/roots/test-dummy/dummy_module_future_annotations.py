from __future__ import annotations


def function_with_py310_annotations(
    self,  # ruff:ignore[missing-type-function-argument]  # the fixture leaves `self` untyped, as a method does
    value: bool | None,
    other: int | str | float,  # ruff:ignore[redundant-numeric-union]  # the fixture renders the union as written
    extra: str | None = None,
) -> str:
    """
    Method docstring.

    :param value: foo
    :param other: bar
    :param extra: baz
    """
