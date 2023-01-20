import re
import sys
from dataclasses import dataclass
from inspect import isclass
from io import StringIO
from mailbox import Mailbox
from pathlib import Path
from textwrap import dedent, indent
from types import CodeType, ModuleType
from typing import Any, Callable, Optional, TypeVar, Union, overload

import pytest
from sphinx.testing.util import SphinxTestApp

T = TypeVar("T")


def expected(expected: str) -> Callable[[T], T]:
    def dec(val: T) -> T:
        val.EXPECTED = expected
        return val

    return dec


def warns(pattern: str) -> Callable[[T], T]:
    def dec(val: T) -> T:
        val.WARNING = pattern
        return val

    return dec


@expected("mod.get_local_function()")
def get_local_function():
    def wrapper(self) -> str:
        """
        Wrapper
        """

    return wrapper


@warns("Cannot handle as a local function")
@expected(
    """\
class mod.Class(x, y, z=None)

   Initializer docstring.

   Parameters:
      * **x** ("bool") -- foo

      * **y** ("int") -- bar

      * **z** ("Optional"["str"]) -- baz

   class InnerClass

      Inner class.

      inner_method(x)

         Inner method.

         Parameters:
            **x** ("bool") -- foo

         Return type:
            "str"

   classmethod a_classmethod(x, y, z=None)

      Classmethod docstring.

      Parameters:
         * **x** ("bool") -- foo

         * **y** ("int") -- bar

         * **z** ("Optional"["str"]) -- baz

      Return type:
         "str"

   a_method(x, y, z=None)

      Method docstring.

      Parameters:
         * **x** ("bool") -- foo

         * **y** ("int") -- bar

         * **z** ("Optional"["str"]) -- baz

      Return type:
         "str"

   property a_property: str

      Property docstring

   static a_staticmethod(x, y, z=None)

      Staticmethod docstring.

      Parameters:
         * **x** ("bool") -- foo

         * **y** ("int") -- bar

         * **z** ("Optional"["str"]) -- baz

      Return type:
         "str"

   locally_defined_callable_field() -> str

      Wrapper

      Return type:
         "str"
    """
)
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


@expected(
    """\
exception mod.DummyException(message)

   Exception docstring

   Parameters:
      **message** ("str") -- blah
"""
)
class DummyException(Exception):  # noqa: N818
    """
    Exception docstring

    :param message: blah
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


@expected(
    """\
mod.function(x, y, z_=None)

   Function docstring.

   Parameters:
      * **x** ("bool") -- foo

      * **y** ("int") -- bar

      * **z_** ("Optional"["str"]) -- baz

   Returns:
      something

   Return type:
      bytes
"""
)
def function(x: bool, y: int, z_: Optional[str] = None) -> str:  # noqa: U100
    """
    Function docstring.

    :param x: foo
    :param y: bar
    :param z\\_: baz
    :return: something
    :rtype: bytes
    """


@expected(
    """\
mod.function_with_starred_documentation_param_names(*args, **kwargs)

   Function docstring.

   Usage:

      print(1)

   Parameters:
      * ***args** ("int") -- foo

      * ****kwargs** ("str") -- bar
"""
)
def function_with_starred_documentation_param_names(*args: int, **kwargs: str):  # noqa: U100
    r"""
    Function docstring.

    Usage::

        print(1)

    :param \*args: foo
    :param \**kwargs: bar
    """


@expected(
    """\
mod.function_with_escaped_default(x='\\\\x08')

   Function docstring.

   Parameters:
      **x** ("str") -- foo
"""
)
def function_with_escaped_default(x: str = "\b"):  # noqa: U100
    """
    Function docstring.

    :param x: foo
    """


@warns("Cannot resolve forward reference in type annotations")
@expected(
    """\
mod.function_with_unresolvable_annotation(x)

   Function docstring.

   Parameters:
      **x** (*a.b.c*) -- foo
"""
)
def function_with_unresolvable_annotation(x: "a.b.c"):  # noqa: U100,F821
    """
    Function docstring.

    :arg x: foo
    """


@expected(
    """\
mod.function_with_typehint_comment(x, y)

   Function docstring.

   Parameters:
      * **x** ("int") -- foo

      * **y** ("str") -- bar

   Return type:
      "None"
"""
)
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


@expected(
    """\
class mod.ClassWithTypehints(x)

   Class docstring.

   Parameters:
      **x** ("int") -- foo

   foo(x)

      Method docstring.

      Parameters:
         **x** ("str") -- foo

      Return type:
         "int"

   method_without_typehint(x)

      Method docstring.
"""
)
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


@expected(
    """\
mod.function_with_typehint_comment_not_inline(x=None, *y, z, **kwargs)

   Function docstring.

   Parameters:
      * **x** ("Union"["str", "bytes", "None"]) -- foo

      * **y** ("str") -- bar

      * **z** ("bytes") -- baz

      * **kwargs** ("int") -- some kwargs

   Return type:
      "None"
"""
)
def function_with_typehint_comment_not_inline(x=None, *y, z, **kwargs):  # noqa: U100
    # type: (Union[str, bytes, None], *str, bytes, **int) -> None
    """
    Function docstring.

    :arg x: foo
    :argument y: bar
    :parameter z: baz
    :parameter kwargs: some kwargs
    """


@expected(
    """\
class mod.ClassWithTypehintsNotInline(x=None)

   Class docstring.

   Parameters:
      **x** ("Optional"["Callable"[["int", "bytes"], "int"]]) -- foo

   foo(x=1)

      Method docstring.

      Parameters:
         **x** ("Callable"[["int", "bytes"], "int"]) -- foo

      Return type:
         "int"

   classmethod mk(x=None)

      Method docstring.

      Parameters:
         **x** ("Optional"["Callable"[["int", "bytes"], "int"]]) --
         foo

      Return type:
         "ClassWithTypehintsNotInline"
"""
)
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


@expected(
    """\
mod.undocumented_function(x)

   Hi

   Return type:
      "str"
"""
)
def undocumented_function(x: int) -> str:
    """Hi"""

    return str(x)


@expected(
    """\
class mod.DataClass(x)

   Class docstring.
"""
)
@dataclass
class DataClass:
    """Class docstring."""

    x: int


@expected(
    """\
class mod.Decorator(func)

   Initializer docstring.

   Parameters:
      **func** ("Callable"[["int", "str"], "str"]) -- function
"""
)
class Decorator:
    """
    Initializer docstring.

    :param func: function
    """

    def __init__(self, func: Callable[[int, str], str]):  # noqa: U100
        pass


@expected(
    """\
mod.mocked_import(x)

   A docstring.

   Parameters:
      **x** ("Mailbox") -- function
"""
)
def mocked_import(x: Mailbox):  # noqa: U100
    """
    A docstring.

    :param x: function
    """


@expected(
    """\
mod.func_with_examples()

   A docstring.

   Return type:
      "int"

   -[ Examples ]-

   Here are a couple of examples of how to use this function.
"""
)
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


@expected(
    """\
mod.func_with_overload(a, b)

   f does the thing. The arguments can either be ints or strings but
   they must both have the same type.

   Parameters:
      * **a** ("Union"["int", "str"]) -- The first thing

      * **b** ("Union"["int", "str"]) -- The second thing

   Return type:
      "None"
"""
)
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


@expected(
    """\
class mod.TestClassAttributeDocs

   A class

   code: "Optional"["CodeType"]

      An attribute
"""
)
class TestClassAttributeDocs:
    """A class"""

    code: Union[CodeType, None]
    """An attribute"""


@expected(
    """\
mod.func_with_examples_and_returns_after()

   f does the thing.

   -[ Examples ]-

   Here is an example

   Return type:
      "int"

   Returns:
      The index of the widget
"""
)
def func_with_examples_and_returns_after() -> int:
    """
    f does the thing.

    Examples
    --------

    Here is an example

    :returns: The index of the widget
    """


@expected(
    """\
mod.func_with_parameters_and_stuff_after(a, b)

   A func

   Parameters:
      * **a** ("int") -- a tells us something

      * **b** ("int") -- b tells us something

   Return type:
      "int"

   More info about the function here.
"""
)
def func_with_parameters_and_stuff_after(a: int, b: int) -> int:  # noqa: U100
    """A func

    :param a: a tells us something
    :param b: b tells us something

    More info about the function here.
    """


@expected(
    """\
mod.func_with_rtype_in_weird_spot(a, b)

   A func

   Parameters:
      * **a** ("int") -- a tells us something

      * **b** ("int") -- b tells us something

   -[ Examples ]-

   Here is an example

   Returns:
      The index of the widget

   More info about the function here.

   Return type:
      int
"""
)
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


@expected(
    """\
mod.empty_line_between_parameters(a, b)

   A func

   Parameters:
      * **a** ("int") --

        One of the following possibilities:

        * a

        * b

        * c

      * **b** ("int") --

        Whatever else we have to say.

        There is more of it And here too

   Return type:
      "int"

   More stuff here.
"""
)
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


@expected(
    """\
mod.func_with_code_block()

   A docstring.

   You would say:

      print("some python code here")

   Return type:
      "int"

   -[ Examples ]-

   Here are a couple of examples of how to use this function.
"""
)
def func_with_code_block() -> int:
    """
    A docstring.

    You would say:

    .. code-block::

        print("some python code here")


    .. rubric:: Examples

    Here are a couple of examples of how to use this function.
    """


@expected(
    """
    mod.func_with_definition_list()

       Some text and then a definition list.

       Return type:
          "int"

       abc
          x

       xyz
          something
    """
)
def func_with_definition_list() -> int:
    """Some text and then a definition list.

    abc
        x

    xyz
        something
    """
    # See https://github.com/tox-dev/sphinx-autodoc-typehints/issues/302


@expected(
    """\
mod.decorator_2(f)

   Run the decorated function with *asyncio.run*.

   Parameters:
      **f** ("Any") -- The function to wrap.

   Return type:
      "Any"

   -[ Examples ]-

      A
"""
)
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
    f


@expected(
    """
    class mod.ParamAndAttributeHaveSameName(blah)

       A Class

       Parameters:
          **blah** ("CodeType") -- Description of parameter blah

       blah: "ModuleType"

          Description of attribute blah

    """
)
class ParamAndAttributeHaveSameName:
    """
    A Class

    Parameters
    ----------
    blah:
        Description of parameter blah
    """

    def __init__(self, blah: CodeType):  # noqa: U100
        pass

    blah: ModuleType
    """Description of attribute blah"""


@expected(
    """
    mod.napoleon_returns()

       A function.

       Return type:
          "CodeType"

       Returns:
          The info about the whatever.
    """
)
def napoleon_returns() -> CodeType:
    """
    A function.

    Returns
    -------
        The info about the whatever.
    """


@expected(
    """
    mod.google_docstrings(arg1, arg2)

       Summary line.

       Extended description of function.

       Parameters:
          * **arg1** ("CodeType") -- Description of arg1

          * **arg2** ("ModuleType") -- Description of arg2

       Return type:
          "CodeType"

       Returns:
          Description of return value

    """
)
def google_docstrings(arg1: CodeType, arg2: ModuleType) -> CodeType:  # noqa: U100
    """Summary line.

    Extended description of function.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value
    """


AUTO_FUNCTION = ".. autofunction:: mod.{}"
AUTO_CLASS = """\
.. autoclass:: mod.{}
    :members:
"""
AUTO_EXCEPTION = """\
.. autoexception:: mod.{}
   :members:
"""


@pytest.mark.parametrize("object", [x for x in globals().values() if hasattr(x, "EXPECTED")])
@pytest.mark.sphinx("text", testroot="integration")
def test_integration(app: SphinxTestApp, status: StringIO, warning: StringIO, monkeypatch, object: Any) -> None:
    if isclass(object) and issubclass(object, BaseException):
        template = AUTO_EXCEPTION
    elif isclass(object):
        template = AUTO_CLASS
    else:
        template = AUTO_FUNCTION

    (Path(app.srcdir) / "index.rst").write_text(template.format(object.__name__))
    monkeypatch.setitem(sys.modules, "mod", sys.modules[__name__])
    app.build()
    assert "build succeeded" in status.getvalue()  # Build succeeded

    regexp = getattr(object, "WARNING", None)
    value = warning.getvalue().strip()
    if regexp:
        msg = f"Regex pattern did not match.\n Regex: {regexp!r}\n Input: {value!r}"
        assert re.search(regexp, value), msg
    else:
        assert not value

    result = (Path(app.srcdir) / "_build/text/index.txt").read_text()

    expected = object.EXPECTED
    try:
        assert result.strip() == dedent(expected).strip()
    except Exception:
        indented = indent(f'"""\n{result}\n"""', " " * 4)
        print(f"@expected(\n{indented}\n)\n")
        raise
