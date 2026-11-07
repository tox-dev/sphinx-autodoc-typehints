"""Module demonstrating type guarded code that the interpreter cannot run."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from demo_unexecutable_guard_dummy import Dataset

    T_Other = TypeVar("T_Other", bound="DataArray" | Dataset)

    class Wrapper(Dataset[int]):
        """A wrapped dataset."""


class DataArray:
    """An array."""


def combine(array: DataArray, other: T_Other) -> T_Other:
    """
    Combine two arrays.

    :param array: the first array
    :param other: the second array
    :return: the combination
    """
    raise NotImplementedError


def wrap(array: DataArray) -> Wrapper:
    """
    Wrap an array.

    :param array: the array to wrap
    :return: the wrapper
    """
    raise NotImplementedError


__all__ = ["DataArray", "combine", "wrap"]
