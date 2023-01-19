from dataclasses import dataclass
from mailbox import Mailbox
from types import CodeType
from typing import Callable, Optional, Union, overload


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

    def __init__(self, x: bool, y: int, z: Optional[str] = None) -> None:  # noqa: U100
        pass

    def a_method(self, x: bool, y: int, z: Optional[str] = None) -> str:  # noqa: U100
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
    def a_classmethod(cls, x: bool, y: int, z: Optional[str] = None) -> str:  # noqa: U100
        """
        Classmethod docstring.

        :param x: foo
        :param y: bar
        :param z: baz
        """

    @staticmethod
    def a_staticmethod(x: bool, y: int, z: Optional[str] = None) -> str:  # noqa: U100
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


def function(x: bool, y: int, z_: Optional[str] = None) -> str:  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    :param z\\_: baz
    :return: something
    :rtype: bytes
    """


def function_with_starred_documentation_param_names(*args: int, **kwargs: str):  # noqa: U100
    r"""
    Function docstring.

    Usage::

        print(1)

    :param \*args: foo
    :param \**kwargs: bar
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
    :parameter y: bar
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
    # type: (Union[str, bytes, None], *str, bytes, **int) -> None
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
        # type: (Optional[Callable[[int, bytes], int]]) -> None
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
        # type: (Optional[Callable[[int, bytes], int]]) -> ClassWithTypehintsNotInline
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


def func_with_examples() -> int:
    """
    A docstring.

    .. rubric:: Examples

    Here are a couple of examples of how to use this function.
    """


@overload
def func_with_overload(a: int, b: int) -> None:  # noqa: U100
    ...


@overload
def func_with_overload(a: str, b: str) -> None:  # noqa: U100
    ...


def func_with_overload(a: Union[int, str], b: Union[int, str]) -> None:  # noqa: U100
    """
    f does the thing. The arguments can either be ints or strings but they must
    both have the same type.

    Parameters
    ----------
    a:
        The first thing
    b:
        The second thing
    """


class TestClassAttributeDocs:
    """A class"""

    code: Union[CodeType, None]
    """An attribute"""


def func_with_examples_and_returns_after() -> int:
    """
    f does the thing.

    Examples
    --------

    Here is an example

    :returns: The index of the widget
    """


def func_with_parameters_and_stuff_after(a: int, b: int) -> int:  # noqa: U100
    """A func

    :param a: a tells us something
    :param b: b tells us something

    More info about the function here.
    """


def func_with_rtype_in_weird_spot(a: int, b: int) -> int:  # noqa: U100
    """A func

    :param a: a tells us something
    :param b: b tells us something

    Examples
    --------

    Here is an example

    :returns: The index of the widget

    More info about the function here.

    :rtype: int
    """


def empty_line_between_parameters(a: int, b: int) -> int:  # noqa: U100
    """A func

    :param a: One of the following possibilities:

             - a

             - b

             - c

    :param b: Whatever else we have to say.

              There is more of it And here too

    More stuff here.
    """


def func_with_code_block() -> int:
    """
    A docstring.

    You would say:

    .. code-block::

        print("some python code here")


    .. rubric:: Examples

    Here are a couple of examples of how to use this function.
    """


def func_with_definition_list() -> int:
    """Some text and then a definition list.

    abc
        x

    xyz
        something
    """
    # See https://github.com/tox-dev/sphinx-autodoc-typehints/issues/302
