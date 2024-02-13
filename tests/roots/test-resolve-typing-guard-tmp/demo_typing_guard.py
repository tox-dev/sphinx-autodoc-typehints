"""Module demonstrating imports that are type guarded"""

from __future__ import annotations

import datetime

from attrs import define


@define()
class SomeClass:
    """This class does something."""

    date: datetime.date
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
    def from_date(cls, input_value: datetime.date) -> SomeClass:
        """
        Initialize from date

        :param input_value: Input
        :return: result
        """
        return cls(input_value)

    @classmethod
    def from_time(cls, input_value: datetime.time) -> SomeClass:
        """
        Initialize from time

        :param input_value: Input
        :return: result
        """
        return cls(input_value)

    def calculate_thing(self, number: float) -> datetime.timedelta:  # noqa: PLR6301
        """
        Calculate a thing

        :param number: Input
        :return: result
        """
        return datetime.timedelta(number)


__all__ = ["SomeClass"]
