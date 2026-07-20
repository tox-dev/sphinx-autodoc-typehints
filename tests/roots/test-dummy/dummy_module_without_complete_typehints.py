from __future__ import annotations


def function_with_some_defaults_and_without_typehints(x, y=None):  # ruff:ignore[missing-type-function-argument, missing-return-type-undocumented-public-function]
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_some_defaults_and_some_typehints(x: int, y=None):  # ruff:ignore[missing-type-function-argument, missing-return-type-undocumented-public-function]
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_some_defaults_and_more_typehints(x: int, y=None) -> str:  # ruff:ignore[missing-type-function-argument]
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_defaults_and_some_typehints(x: int = 0, y=None) -> str:  # ruff:ignore[missing-type-function-argument]
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_defaults_and_type_information_in_docstring(x, y=0) -> str:  # ruff:ignore[missing-type-function-argument]
    """
    Function docstring.

    :type x: int
    :type y: int
    :param x: foo
    :param y: bar
    """
