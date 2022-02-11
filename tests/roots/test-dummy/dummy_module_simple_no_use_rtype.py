def function_no_returns(x: bool, y: int = 1) -> str:  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    """


def function_returns_with_type(x: bool, y: int = 1) -> str:  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    :returns: *CustomType* -- A string
    """


def function_returns_with_compound_type(x: bool, y: int = 1) -> str:  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    :returns: Union[str, int] -- A string or int
    """


def function_returns_without_type(x: bool, y: int = 1) -> str:  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    :returns: A string
    """
