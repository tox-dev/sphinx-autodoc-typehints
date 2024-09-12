from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from inspect import isclass
from pathlib import Path
from textwrap import dedent, indent
from typing import (  # no type comments
    TYPE_CHECKING,
    Any,
    NewType,
    Optional,
    TypeVar,
    Union,
    overload,
)

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable
    from io import StringIO
    from mailbox import Mailbox
    from types import CodeType, ModuleType

    from sphinx.testing.util import SphinxTestApp

T = TypeVar("T")
W = NewType("W", str)


def expected(expected: str, **options: dict[str, Any]) -> Callable[[T], T]:
    def dec(val: T) -> T:
        val.EXPECTED = expected
        val.OPTIONS = options
        return val

    return dec


def warns(pattern: str) -> Callable[[T], T]:
    def dec(val: T) -> T:
        val.WARNING = pattern
        return val

    return dec


@expected("mod.get_local_function()")
def get_local_function():  # noqa: ANN201
    def wrapper(self) -> str:  # noqa: ANN001
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
    """,
)
class Class:
    """
    Initializer docstring.

    :param x: foo
    :param y: bar
    :param z: baz
    """

    def __init__(self, x: bool, y: int, z: Optional[str] = None) -> None:  # noqa: UP007
        pass

    def a_method(self, x: bool, y: int, z: Optional[str] = None) -> str:  # noqa: UP007
        """
        Method docstring.

        :param x: foo
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

    def __magic_custom_method__(self, x: str) -> str:  # noqa: PLW3201
        """
        Magic dunder method docstring.

        :param x: foo
        """

    @classmethod
    def a_classmethod(cls, x: bool, y: int, z: Optional[str] = None) -> str:  # noqa: UP007
        """
        Classmethod docstring.

        :param x: foo
        :param y: bar
        :param z: baz
        """

    @staticmethod
    def a_staticmethod(x: bool, y: int, z: Optional[str] = None) -> str:  # noqa: UP007
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


@expected(
    """\
exception mod.DummyException(message)

   Exception docstring

   Parameters:
      **message** ("str") -- blah
""",
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
""",
)
def function(x: bool, y: int, z_: Optional[str] = None) -> str:  # noqa: UP007
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
""",
)
def function_with_starred_documentation_param_names(*args: int, **kwargs: str):  # noqa: ANN201
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
""",
)
def function_with_escaped_default(x: str = "\b"):  # noqa: ANN201
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
      **x** (a.b.c) -- foo
""",
)
def function_with_unresolvable_annotation(x: a.b.c):  # noqa: ANN201, F821
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
""",
)
def function_with_typehint_comment(  # noqa: ANN201
    x,  # type: int  # noqa: ANN001
    y,  # type: str  # noqa: ANN001
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
""",
)
class ClassWithTypehints:
    """
    Class docstring.

    :param x: foo
    """

    def __init__(
        self,
        x,  # type: int  # noqa: ANN001
    ) -> None:
        # type: (...) -> None
        pass

    def foo(  # noqa: ANN201, PLR6301
        self,
        x,  # type: str  # noqa: ANN001, ARG002
    ):
        # type: (...) -> int
        """
        Method docstring.

        :arg x: foo
        """
        return 42

    def method_without_typehint(self, x):  # noqa: ANN001, ANN201, ARG002, PLR6301
        """
        Method docstring.
        """
        # test that multiline str can be correctly indented
        multiline_str = """
test
"""
        return multiline_str  # noqa: RET504


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
""",
)
def function_with_typehint_comment_not_inline(x=None, *y, z, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN201
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
""",
)
class ClassWithTypehintsNotInline:
    """
    Class docstring.

    :param x: foo
    """

    def __init__(self, x=None) -> None:  # type: (Optional[Callable[[int, bytes], int]]) -> None  # noqa: ANN001
        pass

    def foo(self, x=1):  # type: (Callable[[int, bytes], int]) -> int  # noqa: ANN001, ANN201, PLR6301
        """
        Method docstring.

        :param x: foo
        """
        return x(1, b"")

    @classmethod
    def mk(  # noqa: ANN206
        cls,
        x=None,  # noqa: ANN001
    ):  # type: (Optional[Callable[[int, bytes], int]]) -> ClassWithTypehintsNotInline
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
""",
)
def undocumented_function(x: int) -> str:
    """Hi"""

    return str(x)


@expected(
    """\
class mod.DataClass(x)

   Class docstring.
""",
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
""",
)
class Decorator:
    """
    Initializer docstring.

    :param func: function
    """

    def __init__(self, func: Callable[[int, str], str]) -> None:
        pass


@expected(
    """\
mod.mocked_import(x)

   A docstring.

   Parameters:
      **x** ("Mailbox") -- function
""",
)
def mocked_import(x: Mailbox):  # noqa: ANN201
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
""",
)
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
""",
)
def func_with_overload(a: Union[int, str], b: Union[int, str]) -> None:  # noqa: UP007
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
""",
)
class TestClassAttributeDocs:
    """A class"""

    code: Optional[CodeType]  # noqa: UP007
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
""",
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
""",
)
def func_with_parameters_and_stuff_after(a: int, b: int) -> int:
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
""",
)
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
""",
)
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
""",
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
    """,
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
""",
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
    assert f is not None


@expected(
    """
    class mod.ParamAndAttributeHaveSameName(blah)

       A Class

       Parameters:
          **blah** ("CodeType") -- Description of parameter blah

       blah: "ModuleType"

          Description of attribute blah

    """,
)
class ParamAndAttributeHaveSameName:
    """
    A Class

    Parameters
    ----------
    blah:
        Description of parameter blah
    """

    def __init__(self, blah: CodeType) -> None:
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
    """,
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

    """,
)
def google_docstrings(arg1: CodeType, arg2: ModuleType) -> CodeType:
    """Summary line.

    Extended description of function.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value
    """


@expected(
    """
    mod.docstring_with_multiline_note_after_params(param)

       Do something.

       Parameters:
          **param** ("int") -- A parameter.

       Return type:
          "None"

       Note:

         Some notes. More notes

    """,
)
def docstring_with_multiline_note_after_params(param: int) -> None:
    """Do something.

    Args:
        param: A parameter.

    Note:

        Some notes.
        More notes
    """


@expected(
    """
    mod.docstring_with_bullet_list_after_params(param)

       Do something.

       Parameters:
          **param** ("int") -- A parameter.

       Return type:
          "None"

       * A: B

       * C: D

    """,
)
def docstring_with_bullet_list_after_params(param: int) -> None:
    """Do something.

    Args:
        param: A parameter.

    * A: B
    * C: D
    """


@expected(
    """
    mod.docstring_with_definition_list_after_params(param)

       Do something.

       Parameters:
          **param** ("int") -- A parameter.

       Return type:
          "None"

       Term
          A description

          maybe multiple lines

       Next Term
          Something about it

    """,
)
def docstring_with_definition_list_after_params(param: int) -> None:
    """Do something.

    Args:
        param: A parameter.

    Term
        A description

        maybe multiple lines

    Next Term
        Something about it
    """


@expected(
    """
    mod.docstring_with_enum_list_after_params(param)

       Do something.

       Parameters:
          **param** ("int") -- A parameter.

       Return type:
          "None"

       1. A: B

       2. C: D

    """,
)
def docstring_with_enum_list_after_params(param: int) -> None:
    """Do something.

    Args:
        param: A parameter.

    1. A: B
    2. C: D
    """


@warns("Definition list ends without a blank line")
@expected(
    """
    mod.docstring_with_definition_list_after_params_no_blank_line(param)

       Do something.

       Parameters:
          **param** ("int") -- A parameter.

       Return type:
          "None"

       Term
          A description

          maybe multiple lines

       Next Term
          Something about it

       -[ Example ]-
    """,
)
def docstring_with_definition_list_after_params_no_blank_line(param: int) -> None:
    """Do something.

    Args:
        param: A parameter.

    Term
        A description

        maybe multiple lines

    Next Term
        Something about it
    .. rubric:: Example
    """


@expected(
    """
    mod.has_typevar(param)

       Do something.

       Parameters:
          **param** ("TypeVar"("T")) -- A parameter.

       Return type:
          "TypeVar"("T")

    """,
)
def has_typevar(param: T) -> T:
    """Do something.

    Args:
        param: A parameter.
    """
    return param


@expected(
    """
    mod.has_newtype(param)

       Do something.

       Parameters:
          **param** ("NewType"("W", "str")) -- A parameter.

       Return type:
          "NewType"("W", "str")

    """,
)
def has_newtype(param: W) -> W:
    """Do something.

    Args:
        param: A parameter.
    """
    return param


AUTO_FUNCTION = ".. autofunction:: mod.{}"
AUTO_CLASS = """\
.. autoclass:: mod.{}
    :members:
"""
AUTO_EXCEPTION = """\
.. autoexception:: mod.{}
   :members:
"""

LT_PY310 = sys.version_info < (3, 10)


@expected(
    """
    mod.typehints_use_signature(a: AsyncGenerator) -> AsyncGenerator

       Do something.

       Parameters:
          **a** ("AsyncGenerator") -- blah

       Return type:
          "AsyncGenerator"

    """,
    typehints_use_signature=True,
    typehints_use_signature_return=True,
)
def typehints_use_signature(a: AsyncGenerator) -> AsyncGenerator:
    """Do something.

    Args:
        a: blah
    """
    return a


prolog = """
.. |test_node_start| replace:: {test_node_start}
""".format(test_node_start="test_start")


@expected(
    """
    mod.docstring_with_multiline_note_after_params_prolog_replace(param)

       Do something.

       Parameters:
          **param** ("int") -- A parameter.

       Return type:
          "None"

       Note:

         Some notes. test_start More notes

    """,
    rst_prolog=prolog,
)
def docstring_with_multiline_note_after_params_prolog_replace(param: int) -> None:
    """Do something.

    Args:
        param: A parameter.

    Note:

        Some notes. |test_node_start|
        More notes
    """


epilog = """
.. |test_node_end| replace:: {test_node_end}
""".format(test_node_end="test_end")


@expected(
    """
    mod.docstring_with_multiline_note_after_params_epilog_replace(param)

       Do something.

       Parameters:
          **param** ("int") -- A parameter.

       Return type:
          "None"

       Note:

         Some notes. test_end More notes

    """,
    rst_epilog=epilog,
)
def docstring_with_multiline_note_after_params_epilog_replace(param: int) -> None:
    """Do something.

    Args:
        param: A parameter.

    Note:

        Some notes. |test_node_end|
        More notes
    """


@expected(
    """
    mod.docstring_with_see_also()

       Return type:
          "str"

       See also: more info at <https://example.com>`_.

    """
)
def docstring_with_see_also() -> str:
    """
    .. seealso:: more info at <https://example.com>`_.
    """
    return ""


@expected(
    """
    mod.has_doctest1()

       Test that we place the return type correctly when the function has
       a doctest.

       Return type:
          "None"

       >>> this is a fake doctest
       a
       >>> more doctest
       b
    """
)
def has_doctest1() -> None:
    r"""Test that we place the return type correctly when the function has a doctest.

    >>> this is a fake doctest
    a
    >>> more doctest
    b
    """


# Config settings for each test run.
# Config Name: Sphinx Options as Dict.
configs = {
    "default_conf": {},
    "prolog_conf": {"rst_prolog": prolog},
    "epilog_conf": {
        "rst_epilog": epilog,
    },
    "bothlog_conf": {
        "rst_prolog": prolog,
        "rst_epilog": epilog,
    },
}


@pytest.mark.parametrize("val", [x for x in globals().values() if hasattr(x, "EXPECTED")])
@pytest.mark.parametrize("conf_run", ["default_conf", "prolog_conf", "epilog_conf", "bothlog_conf"])
@pytest.mark.sphinx("text", testroot="integration")
def test_integration(
    app: SphinxTestApp, status: StringIO, warning: StringIO, monkeypatch: pytest.MonkeyPatch, val: Any, conf_run: str
) -> None:
    if isclass(val) and issubclass(val, BaseException):
        template = AUTO_EXCEPTION
    elif isclass(val):
        template = AUTO_CLASS
    else:
        template = AUTO_FUNCTION

    (Path(app.srcdir) / "index.rst").write_text(template.format(val.__name__))
    app.config.__dict__.update(configs[conf_run])
    app.config.__dict__.update(val.OPTIONS)
    monkeypatch.setitem(sys.modules, "mod", sys.modules[__name__])
    app.build()
    assert "build succeeded" in status.getvalue()  # Build succeeded

    regexp = getattr(val, "WARNING", None)
    value = warning.getvalue().strip()
    if regexp:
        msg = f"Regex pattern did not match.\n Regex: {regexp!r}\n Input: {value!r}"
        assert re.search(regexp, value), msg
    else:
        assert not value

    result = (Path(app.srcdir) / "_build/text/index.txt").read_text()

    expected = val.EXPECTED
    if LT_PY310:
        expected = expected.replace("NewType", "NewType()")
    try:
        assert result.strip() == dedent(expected).strip()
    except Exception:
        indented = indent(f'"""\n{result}\n"""', " " * 4)
        print(f"@expected(\n{indented}\n)\n")  # noqa: T201
        raise
