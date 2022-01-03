import typing
from dataclasses import dataclass
from mailbox import Mailbox
from typing import Callable, Union


def get_local_function():
    def wrapper(self) -> str:
        """
        Wrapper
        """

    return wrapper


class Class:
    """
    Initializer docstring.

    :param x: foo
    :param y: bar
    :param z: baz
    """

    def __init__(self, x: bool, y: int, z: typing.Optional[str] = None) -> None:  # noqa: U100
        pass

    def a_method(self, x: bool, y: int, z: typing.Optional[str] = None) -> str:  # noqa: U100
        """
        Method docstring.

        :param x: foo
        :param y: bar
        :param z: baz
        """

    def _private_method(self, x: str) -> str:  # noqa: U100
        """
        Private method docstring.

        :param x: foo
        """

    def __dunder_method(self, x: str) -> str:  # noqa: U100
        """
        Dunder method docstring.

        :param x: foo
        """

    def __magic_custom_method__(self, x: str) -> str:  # noqa: U100
        """
        Magic dunder method docstring.

        :param x: foo
        """

    @classmethod
    def a_classmethod(cls, x: bool, y: int, z: typing.Optional[str] = None) -> str:  # noqa: U100
        """
        Classmethod docstring.

        :param x: foo
        :param y: bar
        :param z: baz
        """

    @staticmethod
    def a_staticmethod(x: bool, y: int, z: typing.Optional[str] = None) -> str:  # noqa: U100
        """
        Staticmethod docstring.

        :param x: foo
        :param y: bar
        :param z: baz
        """

    @property
    def a_property(self) -> str:
        """
        Property docstring
        """

    class InnerClass:
        """
        Inner class.
        """

        def inner_method(self, x: bool) -> str:  # noqa: U100
            """
            Inner method.

            :param x: foo
            """

        def __dunder_inner_method(self, x: bool) -> str:  # noqa: U100
            """
            Dunder inner method.

            :param x: foo
            """

    locally_defined_callable_field = get_local_function()


class DummyException(Exception):  # noqa: N818
    """
    Exception docstring

    :param message: blah
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


def function(x: bool, y: int, z_: typing.Optional[str] = None) -> str:  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    :param z\\_: baz
    :return: something
    :rtype: bytes
    """


def function_with_escaped_default(x: str = "\b"):  # noqa: U100
    """
    Function docstring.

    :param x: foo
    """


def function_with_unresolvable_annotation(x: "a.b.c"):  # noqa: U100,F821
    """
    Function docstring.

    :arg x: foo
    """


def function_with_typehint_comment(
    x,  # type: int  # noqa: U100
    y,  # type: str  # noqa: U100
):
    # type: (...) -> None
    """
    Function docstring.

    :parameter x: foo
    :param y: bar
    """


class ClassWithTypehints:
    """
    Class docstring.

    :param x: foo
    """

    def __init__(
        self, x  # type: int  # noqa: U100
    ):
        # type: (...) -> None
        pass

    def foo(
        self, x  # type: str  # noqa: U100
    ):
        # type: (...) -> int
        """
        Method docstring.

        :arg x: foo
        """
        return 42

    def method_without_typehint(self, x):  # noqa: U100
        """
        Method docstring.
        """
        # test that multiline str can be correctly indented
        multiline_str = """
test
"""
        return multiline_str


def function_with_typehint_comment_not_inline(x=None, *y, z, **kwargs):  # noqa: U100
    # type: (Union[str, bytes], *str, bytes, **int) -> None
    """
    Function docstring.

    :arg x: foo
    :argument y: bar
    :parameter z: baz
    :parameter kwargs: some kwargs
    """


class ClassWithTypehintsNotInline:
    """
    Class docstring.

    :param x: foo
    """

    def __init__(self, x=None):  # noqa: U100
        # type: (Callable[[int, bytes], int]) -> None
        pass

    def foo(self, x=1):
        # type: (Callable[[int, bytes], int]) -> int
        """
        Method docstring.

        :param x: foo
        """
        return x(1, b"")

    @classmethod
    def mk(cls, x=None):
        # type: (Callable[[int, bytes], int]) -> ClassWithTypehintsNotInline
        """
        Method docstring.

        :param x: foo
        """
        return cls(x)


def undocumented_function(x: int) -> str:
    """Hi"""

    return str(x)


@dataclass
class DataClass:
    """Class docstring."""

    x: int


class Decorator:
    """
    Initializer docstring.

    :param func: function
    """

    def __init__(self, func: Callable[[int, str], str]):  # noqa: U100
        pass


def mocked_import(x: Mailbox):  # noqa: U100
    """
    A docstring.

    :param x: function
    """
