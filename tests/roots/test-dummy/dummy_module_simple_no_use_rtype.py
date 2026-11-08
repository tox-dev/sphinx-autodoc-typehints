from __future__ import annotations


def function_no_returns(value: bool, other: int = 1) -> str:
    """
    Function docstring.

    :param value: foo.
    :param other: bar.
    """


def function_returns_with_type(value: bool, other: int = 1) -> str:
    """
    Function docstring.

    :param value: foo.
    :param other: bar.
    :returns: *CustomType* -- A string
    """


def function_returns_with_compound_type(value: bool, other: int = 1) -> str:
    """
    Function docstring.

    :param value: foo.
    :param other: bar.
    :returns: Union[str, int] -- A string or int
    """


def function_returns_without_type(value: bool, other: int = 1) -> str:
    """
    Function docstring.

    :param value: foo.
    :param other: bar.
    :returns: A string
    """
