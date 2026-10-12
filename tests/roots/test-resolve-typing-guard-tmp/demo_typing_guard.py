"""Module demonstrating imports that are type guarded"""

from __future__ import annotations

import datetime as dt

from attrs import define


@define()
class SomeClass:
    """This class does something."""

    date: dt.date
    """Date to handle"""

    @classmethod
    def from_str(cls, input_value: str) -> SomeClass:
        """
        Initialize from string

        :param input_value: Input
        :return: result
        """
        return cls(input_value)

    @classmethod
    def from_date(cls, input_value: dt.date) -> SomeClass:
        """
        Initialize from date

        :param input_value: Input
        :return: result
        """
        return cls(input_value)

    @classmethod
    def from_time(cls, input_value: dt.time) -> SomeClass:
        """
        Initialize from time

        :param input_value: Input
        :return: result
        """
        return cls(input_value)

    def calculate_thing(self, number: float) -> dt.timedelta:  # ruff:ignore[no-self-use]
        """
        Calculate a thing

        :param number: Input
        :return: result
        """
        return dt.timedelta(number)


__all__ = ["SomeClass"]
