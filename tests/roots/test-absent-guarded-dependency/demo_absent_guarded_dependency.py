from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

    import no_such_array.core  # a guarded import of a missing submodule is the case under test
    from no_such_cube.cube import Cube


def load(cube: Cube, array: no_such_array.core.Array, precision: Decimal) -> list[Cube]:
    """
    Load a cube.

    :param cube: the cube
    :param array: the backing array
    :param precision: the precision
    :returns: the cubes
    """
    raise NotImplementedError


__all__ = [
    "load",
]
