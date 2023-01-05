def function_with_some_defaults_and_without_typehints(x, y=None):
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_some_defaults_and_some_typehints(x: int, y=None):
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_some_defaults_and_more_typehints(x: int, y=None) -> str:
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_with_defaults_and_some_typehints(x: int = 0, y=None) -> str:
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """
