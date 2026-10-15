from __future__ import annotations

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NewType,
    Optional,
    TypeVar,
    Union,
    overload,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable
    from mailbox import Mailbox
    from types import CodeType, ModuleType


W = NewType("W", str)


def get_local_function():  # ruff:ignore[missing-return-type-undocumented-public-function]  # the local function it returns is the case
    def wrapper(self) -> str:  # ruff:ignore[missing-type-function-argument]  # the local function is the case, as written
        """
        Wrapper
        """

    return wrapper


class Class:
    """
    Initializer docstring.

    :param x: initializer flag
    :param y: bar
    :param z: baz
    """

    def __init__(self, x: bool, y: int, z: Optional[str] = None) -> None: ...

    def a_method(self, x: bool, y: int, z: Optional[str] = None) -> str:
        """
        Method docstring.

        :param x: method flag
        :param y: bar
        :param z: baz
        """

    def _private_method(self, x: str) -> str:
        """
        Private method docstring.

        :param x: foo
        """

    def __dunder_method(self, x: str) -> str:
        """
        Dunder method docstring.

        :param x: foo
        """

    def __magic_custom_method__(self, x: str) -> str:  # ruff:ignore[bad-dunder-method-name]  # a custom dunder name is the case
        """
        Magic dunder method docstring.

        :param x: foo
        """

    @classmethod
    def a_classmethod(cls, x: bool, y: int, z: Optional[str] = None) -> str:
        """
        Classmethod docstring.

        :param x: classmethod flag
        :param y: bar
        :param z: baz
        """

    @staticmethod
    def a_staticmethod(x: bool, y: int, z: Optional[str] = None) -> str:
        """
        Staticmethod docstring.

        :param x: staticmethod flag
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

        def inner_method(self, x: bool) -> str:
            """
            Inner method.

            :param x: foo
            """

        def __dunder_inner_method(self, x: bool) -> str:
            """
            Dunder inner method.

            :param x: foo
            """

    locally_defined_callable_field = get_local_function()


class DummyException(Exception):  # ruff:ignore[error-suffix-on-exception-name]  # the expected output names the class
    """
    Exception docstring

    :param message: blah
    """

    def __init__(self, message: str) -> None: ...


def function(x: bool, y: int, z_: Optional[str] = None) -> str:
    """
    Function docstring.

    :param x: foo
    :param y: bar
    :param z\\_: baz
    :return: something
    :rtype: bytes
    """


def function_with_trailing_underscore_numpy(a: int, lambda_: float | None = None) -> None:
    """Do nothing.

    Parameters
    ----------
    a
        Description for a.
    lambda_
        Description for lambda.
    """


def function_with_trailing_underscore_google(a: int, lambda_: float | None = None) -> None:
    """Do nothing.

    Args:
        a: Description for a.
        lambda_: Description for lambda.
    """


def function_with_starred_documentation_param_names(*args: int, **kwargs: str):  # ruff:ignore[missing-return-type-undocumented-public-function]  # the case documents no return type
    r"""
    Function docstring.

    Usage::

        print(1)

    :param \*args: foo
    :param \**kwargs: bar
    """


def function_with_escaped_default(x: str = "\b"):  # ruff:ignore[missing-return-type-undocumented-public-function]  # the case documents no return type
    """
    Function docstring.

    :param x: foo
    """


def function_with_multiline_param_defaults(x: int = 5, y: int = 10, z: int = 15) -> str:
    """
    Function docstring.

    :param x: optional specifier
              line 2
    :param y: another optional
              line 4

              second paragraph for y

    :param z: yet another optional s
              line 6

    :return: something
    :rtype: bytes
    """


ArrayLike = Literal["test"]


class _SchemaMeta(type):  # ruff:ignore[eq-without-hash]  # the metaclass compares every class equal, and hashing stays the default
    def __eq__(cls, other: object) -> bool:
        return True


class Schema(metaclass=_SchemaMeta):
    pass


class AliasedClass: ...


def function_with_eq_metaclass(s: Schema) -> Schema:
    """
    Do something.

    Args:
        s: Some schema.
    """


def function_with_aliased_class(s: AliasedClass) -> AliasedClass:
    """
    Do something.

    Args:
        s: Some schema.
    """


def function_with_type_aliases(x: ArrayLike | None, y: Schema) -> str:
    """
    Function docstring.

    :param x: foo
    :param y: boo
    :return: something
    :rtype: bytes
    """


def function_with_unresolvable_annotation(x: a.b.c):  # ruff:ignore[missing-return-type-undocumented-public-function, undefined-name]  # the unresolvable annotation is the case
    """
    Function docstring.

    :arg x: foo
    """


def function_with_typehint_comment(  # ruff:ignore[missing-return-type-undocumented-public-function]  # the type comment gives the return type
    x,  # type: int  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
    y,  # type: str  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
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
        self,
        x,  # type: int  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
    ) -> None:
        # type: (...) -> None
        ...

    def foo(  # ruff:ignore[missing-return-type-undocumented-public-function]  # the type comment gives the return type
        self,
        x,  # type: str  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
    ):
        # type: (...) -> int
        """
        Method docstring.

        :arg x: foo
        """

    def method_without_typehint(self, x):  # ruff:ignore[missing-type-function-argument, missing-return-type-undocumented-public-function]  # the method without hints is the case
        """
        Method docstring.
        """


def function_with_typehint_comment_not_inline(x=None, *y, z, **kwargs):  # ruff:ignore[missing-type-function-argument, missing-type-args, missing-type-kwargs, missing-return-type-undocumented-public-function]  # the type comment gives the types
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

    def __init__(self, x=None) -> None:  # type: (Optional[Callable[[int, bytes], int]]) -> None  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
        ...

    def foo(self, x=1):  # type: (Callable[[int, bytes], int]) -> int  # ruff:ignore[missing-type-function-argument, missing-return-type-undocumented-public-function]  # the type comment gives the types
        """
        Method docstring.

        :param x: callback
        """

    @classmethod
    def mk(  # ruff:ignore[missing-return-type-class-method]  # the type comment gives the return type
        cls,
        x=None,  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
    ):  # type: (Optional[Callable[[int, bytes], int]]) -> ClassWithTypehintsNotInline
        """
        Method docstring.

        :param x: foo
        """


def undocumented_function(x: int) -> str:
    """Hi"""


@dataclass
class DataClass:
    """Class docstring."""

    x: int


class Decorator:
    """
    Initializer docstring.

    :param func: function
    """

    def __init__(self, func: Callable[[int, str], str]) -> None: ...


def mocked_import(x: Mailbox):  # ruff:ignore[missing-return-type-undocumented-public-function]  # the case documents no return type
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
def func_with_overload(a: int, b: int) -> None: ...


@overload
def func_with_overload(a: str, b: str) -> None: ...


def func_with_overload(a: Union[int, str], b: Union[int, str]) -> None:
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


@overload
def overload_with_complex_types(x: list[int]) -> dict[str, int]: ...


@overload
def overload_with_complex_types(x: dict[str, int]) -> list[int]: ...


def overload_with_complex_types(x: list[int] | dict[str, int]) -> dict[str, int] | list[int]:
    """Function with overloaded complex types.

    Parameters:
        x: Input value
    """


@overload
def func_with_overload_no_overloads(a: int, b: int) -> None: ...


@overload
def func_with_overload_no_overloads(a: str, b: str) -> None: ...


def func_with_overload_no_overloads(a: Union[int, str], b: Union[int, str]) -> None:
    """:no-overloads:

    Accepts int or str pairs, see docs for details.

    Parameters
    ----------
    a:
        The first thing
    b:
        The second thing
    """


def func_literals_long_format(a: Literal["arg1", "arg2"], b: Literal["arg1", "arg2"]) -> None:
    """
    A docstring.

    :param a: Argument that can take either of two literal values.
    :param b: Argument that can take either of two literal values.
    """


def func_literals_short_format(a: Literal["arg1", "arg2"], b: Literal["arg1", "arg2"]) -> None:
    """
    A docstring.

    :param a: Argument that can take either of two literal values.
    :param b: Argument that can take either of two literal values.
    """


def func_literal_backslashes(sep: Literal["\n", "\\"]) -> None:
    """
    A docstring.

    :param sep: The separator.
    """


def func_literal_backticks(fence: Literal["``", "```"]) -> None:
    """
    A docstring.

    :param fence: The fence.
    """


class TestClassAttributeDocs:
    """A class"""

    code: Optional[CodeType]
    """An attribute"""


def func_with_examples_and_returns_after() -> int:
    """
    f does the thing.

    Examples
    --------

    Here is an example

    :returns: The index of the widget
    """


def func_with_parameters_and_stuff_after(a: int, b: int) -> int:
    """A func

    :param a: a tells us something
    :param b: b tells us something

    More info about the function here.
    """


def func_with_rtype_in_weird_spot(a: int, b: int) -> int:
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


def empty_line_between_parameters(a: int, b: int) -> int:
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


def decorator_2(f: Any) -> Any:
    """Run the decorated function with `asyncio.run`.

    Parameters
    ----------
    f
        The function to wrap.

    Examples
    --------

    .. code-block:: python

        A
    """


class ParamAndAttributeHaveSameName:
    """
    A Class

    Parameters
    ----------
    blah:
        Description of parameter blah
    """

    def __init__(self, blah: CodeType) -> None: ...

    blah: ModuleType
    """Description of attribute blah"""


def napoleon_returns() -> CodeType:
    """
    A function.

    Returns
    -------
        The info about the whatever.
    """


def napoleon_returns_unindented_sentence() -> CodeType:
    """
    A function.

    Returns
    -------
    The info about the whatever.
    """


def napoleon_returns_type_then_description() -> CodeType:
    """
    A function.

    Returns
    -------
    CodeType
        The info about the whatever.
    """


def napoleon_returns_type_only() -> CodeType:
    """
    A function.

    Returns
    -------
    CodeType
    """


def google_docstrings(arg1: CodeType, arg2: ModuleType) -> CodeType:
    """Summary line.

    Extended description of function.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value
    """


def docstring_with_multiline_note_after_params(param: int) -> None:
    """Do something.

    Args:
        param: A parameter.

    Note:

        Some notes.
        More notes
    """


def docstring_with_bullet_list_after_params(param: int) -> None:
    """Do something.

    Args:
        param: The count.

    * A: B
    * C: D
    """


def docstring_with_definition_list_after_params(param: int) -> None:
    """Do something.

    Args:
        param: Any integer.

    Term
        A description

        maybe multiple lines

    Next Term
        Something about it
    """


def docstring_with_enum_list_after_params(param: int) -> None:
    """Do something.

    Args:
        param: An index.

    1. A: B
    2. C: D
    """


def docstring_with_definition_list_after_params_no_blank_line(param: int) -> None:
    """Do something.

    Args:
        param: The number.

    Term
        A description

        maybe multiple lines

    Next Term
        Something about it
    .. rubric:: Example
    """


def has_typevar[T](param: T) -> T:
    """Do something.

    Args:
        param: Value of the type parameter.
    """


def has_newtype(param: W) -> W:
    """Do something.

    Args:
        param: A string of the new type.
    """


def typehints_use_signature(a: AsyncGenerator) -> AsyncGenerator:
    """Do something.

    Args:
        a: blah
    """


def typehints_no_rtype_none() -> None:
    """Do something."""


def docstring_with_multiline_note_after_params_prolog_replace(param: int) -> None:
    """Do something.

    Args:
        param: A parameter.

    Note:

        Some notes. |test_node_start|
        More notes
    """


def docstring_with_multiline_note_after_params_epilog_replace(param: int) -> None:
    """Do something.

    Args:
        param: An integer.

    Note:

        Some notes. |test_node_end|
        More notes
    """


def docstring_with_see_also() -> str:
    """
    Test

    .. seealso:: more info at <https://example.com>`_.
    """


def has_doctest1() -> None:
    r"""Test that the return type goes ahead of a doctest in the function.

    >>> this is a fake doctest
    a
    >>> more doctest
    b
    """


Unformatted = TypeVar("Unformatted")


def typehints_formatter_applied_to_signature[Unformatted](param: Unformatted) -> Unformatted:
    """
    Do nothing

    Args:
        param: A parameter

    Returns:
        The return value
    """


# Config settings for each test run.
# Config Name: Sphinx Options as Dict.
