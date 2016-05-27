#!/usr/bin/env python

"""Small module to provide sourcecode for testing if everything works as needed

"""

from typing import Union, Optional, Iterable


def format_unit(self, value: Union[float, int], unit: str, test: Optional[Union[Iterable, str]]) -> str:
    """
    Formats the given value as a human readable string using the given units.

    :param value: a numeric value
    :param unit: the unit for the value (kg, m, etc.)
    :param test: bla bla blathe unit for the value (kg, m, etc.)
    """
    return '{} {}'.format(value, unit)


def format_unit_google(self, value: Union[float, int], unit: str, test: Optional[Union[Iterable, str]]) -> str:
    """
    Formats the given value as a human readable string using the given units.

    Args:
        value: a numeric value
        unit: the unit for the value (kg, m, etc.)
        test: bla bla blathe unit for the value (kg, m, etc.)

    Returns:
       This function returns something of
       value: and does not overwrite this part.
    """
    return '{} {}'.format(value, unit)


def format_unit_numpy(self, value: Union[float, int], unit: str, test: Optional[Union[Iterable, str]]) -> str:
    """
    Formats the given value as a human readable string using the given units.

    Parameters
    ----------
    value: a numeric value
    unit: the unit for the value (kg, m, etc.)
    test: bla bla blathe unit for the value (kg, m, etc.)

    Returns
    -------
    This function returns something of
    value: and does not overwrite this part.
    """
    return '{} {}'.format(value, unit)
