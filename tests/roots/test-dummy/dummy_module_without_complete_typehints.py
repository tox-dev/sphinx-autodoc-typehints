from __future__ import annotations


def function_with_some_defaults_and_without_typehints(x, y=None):  # noqa: ANN001, ANN201
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_some_defaults_and_some_typehints(x: int, y=None):  # noqa: ANN001, ANN201
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_some_defaults_and_more_typehints(x: int, y=None) -> str:  # noqa: ANN001
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_defaults_and_some_typehints(x: int = 0, y=None) -> str:  # noqa: ANN001
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """
