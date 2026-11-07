from __future__ import annotations

type Inner = int | str
type Outer = Inner | bytes
type Documented = float
type Mixed = Documented | Inner


def nested_func(value: Mixed) -> Outer:
    """
    Take and return aliases naming aliases.

    Parameters
    ----------
    value
        the value
    """
