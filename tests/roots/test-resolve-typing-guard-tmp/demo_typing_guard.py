"""Module demonstrating imports that are type guarded"""
from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import define

if TYPE_CHECKING:
    import datetime


@define()
class SomeClass:
    """This class does something."""

    dt: datetime.date
    """Date to handle"""

    @classmethod
    def from_str(cls, inp_v: str) -> SomeClass:
        """
        Initialise from string

        :param inp_v: Input
        :return: result
        """
        return cls()

    @classmethod
    def from_date(cls, inp_v: datetime.date) -> SomeClass:
        """
        Initialise from date

        :param inp_v: Input
        :return: result
        """
        return cls()

    @classmethod
    def from_time(cls, inp_v: datetime.time) -> SomeClass:
        """
        Initialise from time

        :param inp_v: Input
        :return: result
        """
        return cls()

    def calc_thing(self, num: float) -> datetime.timedelta:
        """
        Calculate a thing

        :param num: Input
        :return: result
        """
        return datetime.timedelta(num)


__all__ = ["SomeClass"]
