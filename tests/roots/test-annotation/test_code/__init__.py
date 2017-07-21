# coding=utf-8
""" Test type hints. """
from typing import Tuple, Union


def test_param_init_return_str(param: int) -> str:
    """ Test one init param and return value is str.

    :param param: parameter to increase
    :return: increase value with one
    """
    return str(param + 1)


# noinspection PyUnusedLocal
def test_param_init_return_tuple_str_int(param: Tuple[str, int], i: int) -> Tuple[str, int]:
    """ Test one init param and return value is str.

    :param param: parameter to increase
    :param i: integer
    :return: increase value with one
    """
    return param


# noinspection PyUnusedLocal
def test_param_init_return_tuple_str_ellipsis(param: Tuple[str, ...], i: int) -> Tuple[str, ...]:
    """ Test one init param and return value is str.

    :param param: parameter to increase
    :param i: integer
    :return: increase value with one
    """
    return param


# noinspection PyUnusedLocal
def test_param_init_return_union_str_int(param: Union[str, int], i: int) -> Union[str, int]:
    """ Test one init param and return value is str.

    :param param: parameter to increase
    :param i: integer
    :return: increase value with one
    """
    return param
