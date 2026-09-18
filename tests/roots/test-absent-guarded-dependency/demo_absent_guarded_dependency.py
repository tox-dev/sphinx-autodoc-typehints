"""Module whose type checking guard names a dependency the docs environment lacks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

    import no_such_array.core
    from no_such_cube.cube import Cube


def load(cube: Cube, array: no_such_array.core.Array, precision: Decimal) -> list[Cube]:
    """
    Load a cube.

    :param cube: the cube
    :param array: the backing array
    :param precision: the precision
    :return: the cubes
    """
    raise NotImplementedError


__all__ = ["load"]
