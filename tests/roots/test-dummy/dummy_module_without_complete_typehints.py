from __future__ import annotations


def function_with_some_defaults_and_without_typehints(num, opt=None):  # ruff:ignore[missing-type-function-argument, missing-return-type-undocumented-public-function]  # the fixture omits its types
    """
    Function docstring.

    :param num: untyped without a default
    :param opt: untyped with a default
    """


def function_with_some_defaults_and_some_typehints(num: int, opt=None):  # ruff:ignore[missing-type-function-argument, missing-return-type-undocumented-public-function]  # the fixture omits one type
    """
    Function docstring.

    :param num: typed without a default
    :param opt: untyped with a default
    """


def function_with_some_defaults_and_more_typehints(num: int, opt=None) -> str:  # ruff:ignore[missing-type-function-argument]  # the fixture omits one type
    """
    Function docstring.

    :param num: typed without a default
    :param opt: untyped with a default
    """


def function_with_defaults_and_some_typehints(num: int = 0, opt=None) -> str:  # ruff:ignore[missing-type-function-argument]  # the fixture omits one type
    """
    Function docstring.

    :param num: typed with a default
    :param opt: untyped with a default
    """


def function_with_defaults_and_type_information_in_docstring(num, opt=0) -> str:  # ruff:ignore[missing-type-function-argument]  # the types live in the docstring
    """
    Function docstring.

    :type num: int
    :type opt: int
    :param num: typed in the docstring
    :param opt: typed in the docstring with a default
    """
