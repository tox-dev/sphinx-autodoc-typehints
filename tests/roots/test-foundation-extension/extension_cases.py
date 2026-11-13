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


Word = NewType("Word", str)


def get_local_function():  # ruff:ignore[missing-return-type-undocumented-public-function]  # the local function it returns is the case
    def wrapper(self) -> str:  # ruff:ignore[missing-type-function-argument]  # the local function is the case, as written
        """
        Wrapper
        """

    return wrapper


class Class:
    """
    Initializer docstring.

    :param flag: initializer flag
    :param count: bar
    :param label: baz
    """

    class InnerClass:
        """
        Inner class.
        """

        def inner_method(self, flag: bool) -> str:
            """
            Inner method.

            :param flag: foo
            """

        def __dunder_inner_method(self, flag: bool) -> str:
            """
            Dunder inner method.

            :param flag: foo
            """

    def __init__(self, flag: bool, count: int, label: Optional[str] = None) -> None: ...

    def __magic_custom_method__(self, flag: str) -> str:  # ruff:ignore[bad-dunder-method-name]  # a custom dunder name is the case
        """
        Magic dunder method docstring.

        :param flag: foo
        """

    @property
    def a_property(self) -> str:
        """
        Property docstring
        """

    def a_method(self, flag: bool, count: int, label: Optional[str] = None) -> str:
        """
        Method docstring.

        :param flag: method flag
        :param count: bar
        :param label: baz
        """

    def _private_method(self, flag: str) -> str:  # simplint: ignore[unused-definition]  # documented private member
        """
        Private method docstring.

        :param flag: foo
        """

    def __dunder_method(self, flag: str) -> str:  # simplint: ignore[unused-definition]  # documented dunder member
        """
        Dunder method docstring.

        :param flag: foo
        """

    @classmethod
    def a_classmethod(cls, flag: bool, count: int, label: Optional[str] = None) -> str:
        """
        Classmethod docstring.

        :param flag: classmethod flag
        :param count: bar
        :param label: baz
        """

    @staticmethod
    def a_staticmethod(flag: bool, count: int, label: Optional[str] = None) -> str:
        """
        Staticmethod docstring.

        :param flag: staticmethod flag
        :param count: bar
        :param label: baz
        """

    locally_defined_callable_field = get_local_function()


class DummyException(Exception):  # ruff:ignore[error-suffix-on-exception-name]  # the expected output names the class
    """
    Exception docstring

    :param message: blah
    """

    def __init__(self, message: str) -> None: ...


def function(flag: bool, count: int, z_: Optional[str] = None) -> str:
    """
    Function docstring.

    :param flag: foo
    :param count: bar
    :param z\\_: baz
    :return: something
    :rtype: bytes
    """


def function_with_trailing_underscore_numpy(value: int, lambda_: float | None = None) -> None:
    """Do nothing.

    Parameters
    ----------
    value
        Description for a.
    lambda_
        Description for lambda.
    """


def function_with_trailing_underscore_google(value: int, lambda_: float | None = None) -> None:
    """Do nothing.

    Args:
        value: Description for a.
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


def function_with_escaped_default(flag: str = "\b"):  # ruff:ignore[missing-return-type-undocumented-public-function]  # the case documents no return type
    """
    Function docstring.

    :param flag: foo
    """


def function_with_multiline_param_defaults(flag: int = 5, count: int = 10, label: int = 15) -> str:
    """
    Function docstring.

    :param flag: optional specifier
              line 2
    :param count: another optional
              line 4

              second paragraph for y

    :param label: yet another optional s
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


def function_with_eq_metaclass(text: Schema) -> Schema:
    """
    Do something.

    Args:
        text: Some schema.
    """


def function_with_aliased_class(text: AliasedClass) -> AliasedClass:
    """
    Do something.

    Args:
        text: Some schema.
    """


def function_with_type_aliases(flag: ArrayLike | None, count: Schema) -> str:
    """
    Function docstring.

    :param flag: foo
    :param count: boo
    :return: something
    :rtype: bytes
    """


def function_with_unresolvable_annotation(flag: a.b.c):  # ruff:ignore[missing-return-type-undocumented-public-function, undefined-name]  # the unresolvable annotation is the case
    """
    Function docstring.

    :arg flag: foo
    """


def function_with_typehint_comment(  # ruff:ignore[missing-return-type-undocumented-public-function]  # the type comment gives the return type
    flag,  # type: int  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
    count,  # type: str  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
):
    # type: (...) -> None
    """
    Function docstring.

    :parameter flag: foo
    :parameter count: bar
    """


class ClassWithTypehints:
    """
    Class docstring.

    :param flag: foo
    """

    def __init__(
        self,
        flag,  # type: int  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
    ) -> None:
        # type: (...) -> None
        ...

    def foo(  # ruff:ignore[missing-return-type-undocumented-public-function]  # the type comment gives the return type
        self,
        flag,  # type: str  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
    ):
        # type: (...) -> int
        """
        Method docstring.

        :arg flag: foo
        """

    def method_without_typehint(self, flag):  # ruff:ignore[missing-type-function-argument, missing-return-type-undocumented-public-function]  # the method without hints is the case
        """
        Method docstring.
        """


def function_with_typehint_comment_not_inline(flag=None, *count, label, **kwargs):  # ruff:ignore[missing-type-function-argument, missing-type-args, missing-type-kwargs, missing-return-type-undocumented-public-function]  # the type comment gives the types
    # type: (Union[str, bytes, None], *str, bytes, **int) -> None
    """
    Function docstring.

    :arg flag: foo
    :argument count: bar
    :parameter label: baz
    :parameter kwargs: some kwargs
    """


class ClassWithTypehintsNotInline:
    """
    Class docstring.

    :param flag: foo
    """

    def __init__(self, flag=None) -> None:  # type: (Optional[Callable[[int, bytes], int]]) -> None  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
        ...

    def foo(self, flag=1):  # type: (Callable[[int, bytes], int]) -> int  # ruff:ignore[missing-type-function-argument, missing-return-type-undocumented-public-function]  # the type comment gives the types
        """
        Method docstring.

        :param flag: callback
        """

    @classmethod
    def mk(  # ruff:ignore[missing-return-type-class-method]  # the type comment gives the return type
        cls,
        flag=None,  # ruff:ignore[missing-type-function-argument]  # the type comment gives the type
    ):  # type: (Optional[Callable[[int, bytes], int]]) -> ClassWithTypehintsNotInline
        """
        Method docstring.

        :param flag: foo
        """


def undocumented_function(flag: int) -> str:
    """Hi"""


# the docs assert the positional constructor signature
@dataclass(frozen=True, slots=True)  # simplint: ignore[dataclass-kw-only]
class DataClass:
    """Class docstring."""

    flag: int


class Decorator:
    """
    Initializer docstring.

    :param func: function
    """

    def __init__(self, func: Callable[[int, str], str]) -> None: ...


def mocked_import(flag: Mailbox):  # ruff:ignore[missing-return-type-undocumented-public-function]  # the case documents no return type
    """
    A docstring.

    :param flag: function
    """


def func_with_examples() -> int:
    """
    A docstring.

    .. rubric:: Examples

    Here are a couple of examples of how to use this function.
    """


@overload
def func_with_overload(value: int, other: int) -> None: ...


@overload
def func_with_overload(value: str, other: str) -> None: ...


def func_with_overload(value: Union[int, str], other: Union[int, str]) -> None:
    """
    f does the thing. The arguments can either be ints or strings but they must
    both have the same type.

    Parameters
    ----------
    value:
        The first thing
    other:
        The second thing
    """


@overload
def overload_with_complex_types(flag: list[int]) -> dict[str, int]: ...


@overload
def overload_with_complex_types(flag: dict[str, int]) -> list[int]: ...


def overload_with_complex_types(flag: list[int] | dict[str, int]) -> dict[str, int] | list[int]:
    """Function with overloaded complex types.

    Parameters:
        flag: Input value
    """


@overload
def func_with_overload_no_overloads(value: int, other: int) -> None: ...


@overload
def func_with_overload_no_overloads(value: str, other: str) -> None: ...


def func_with_overload_no_overloads(value: Union[int, str], other: Union[int, str]) -> None:
    """:no-overloads:

    Accepts int or str pairs, see docs for details.

    Parameters
    ----------
    value:
        The first thing
    other:
        The second thing
    """


def func_literals_long_format(value: Literal["arg1", "arg2"], other: Literal["arg1", "arg2"]) -> None:
    """
    A docstring.

    :param value: Argument that can take either of two literal values.
    :param other: Argument that can take either of two literal values.
    """


def func_literals_short_format(value: Literal["arg1", "arg2"], other: Literal["arg1", "arg2"]) -> None:
    """
    A docstring.

    :param value: Argument that can take either of two literal values.
    :param other: Argument that can take either of two literal values.
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


def func_with_parameters_and_stuff_after(value: int, other: int) -> int:
    """A func

    :param value: a tells us something
    :param other: b tells us something

    More info about the function here.
    """


def func_with_rtype_in_weird_spot(value: int, other: int) -> int:
    """A func

    :param value: a tells us something
    :param other: b tells us something

    Examples
    --------

    Here is an example

    :returns: The index of the widget

    More info about the function here.

    :rtype: int
    """


def empty_line_between_parameters(value: int, other: int) -> int:
    """A func

    :param value: One of the following possibilities:

             - a

             - b

             - c

    :param other: Whatever else we have to say.

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


def decorator_2(func: Any) -> Any:
    """Run the decorated function with `asyncio.run`.

    Parameters
    ----------
    func
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


def has_typevar[ItemT](param: ItemT) -> ItemT:
    """Do something.

    Args:
        param: Value of the type parameter.
    """


def has_newtype(param: Word) -> Word:
    """Do something.

    Args:
        param: A string of the new type.
    """


def typehints_use_signature(value: AsyncGenerator) -> AsyncGenerator:
    """Do something.

    Args:
        value: blah
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
    r"""Test that the return type follows a doctest in the function.

    >>> this is a fake doctest
    value
    >>> more doctest
    other
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
