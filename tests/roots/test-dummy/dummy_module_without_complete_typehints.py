def function_with_some_defaults_and_without_typehints(x, y=None):  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_some_defaults_and_some_typehints(x: int, y=None):  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_some_defaults_and_more_typehints(x: int, y=None) -> str:  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_defaults_and_some_typehints(x: int = 0, y=None) -> str:  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """
