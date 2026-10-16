from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from sphinx_autodoc_typehints._render.context import TypehintsFormatter

PROLOG: Final[str] = dedent("""\
    .. |test_node_start| replace:: test_start
""")
EPILOG: Final[str] = dedent("""\
    .. |test_node_end| replace:: test_end
""")

EXPECTED: Final[dict[str, str]] = {
    "get_local_function": "mod.get_local_function()",
    "Class": dedent("""\
        class mod.Class(x, y, z=None)

           Initializer docstring.

           Parameters:
              * **x** ("bool") -- initializer flag

              * **y** ("int") -- bar

              * **z** ("str" | "None") -- baz

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
                 * **x** ("bool") -- classmethod flag

                 * **y** ("int") -- bar

                 * **z** ("str" | "None") -- baz

              Return type:
                 "str"

           a_method(x, y, z=None)

              Method docstring.

              Parameters:
                 * **x** ("bool") -- method flag

                 * **y** ("int") -- bar

                 * **z** ("str" | "None") -- baz

              Return type:
                 "str"

           property a_property: str

              Property docstring

           static a_staticmethod(x, y, z=None)

              Staticmethod docstring.

              Parameters:
                 * **x** ("bool") -- staticmethod flag

                 * **y** ("int") -- bar

                 * **z** ("str" | "None") -- baz

              Return type:
                 "str"

           locally_defined_callable_field()

              Wrapper

              Return type:
                 "str"
    """),
    "DummyException": dedent("""\
        exception mod.DummyException(message)

           Exception docstring

           Parameters:
              **message** ("str") -- blah
    """),
    "function": dedent("""\
        mod.function(x, y, z_=None)

           Function docstring.

           Parameters:
              * **x** ("bool") -- foo

              * **y** ("int") -- bar

              * **z_** ("str" | "None") -- baz

           Returns:
              something

           Return type:
              "str"
    """),
    "function_with_trailing_underscore_numpy": dedent("""\
        mod.function_with_trailing_underscore_numpy(a, lambda_=None)

           Do nothing.

           Parameters:
              * **a** ("int") -- Description for a.

              * **lambda_** ("float" | "None", default: "None") -- Description
                for lambda.

           Return type:
              "None"
    """),
    "function_with_trailing_underscore_google": dedent("""\
        mod.function_with_trailing_underscore_google(a, lambda_=None)

           Do nothing.

           Parameters:
              * **a** ("int") -- Description for a.

              * **lambda_** ("float" | "None", default: "None") -- Description
                for lambda.

           Return type:
              "None"
    """),
    "function_with_starred_documentation_param_names": dedent("""\
        mod.function_with_starred_documentation_param_names(*args, **kwargs)

           Function docstring.

           Usage:

              print(1)

           Parameters:
              * ***args** ("int") -- foo

              * ****kwargs** ("str") -- bar
    """),
    "function_with_escaped_default": dedent("""\
        mod.function_with_escaped_default(x='\\x08')

           Function docstring.

           Parameters:
              **x** ("str") -- foo
    """),
    "function_with_multiline_param_defaults": dedent("""\
        mod.function_with_multiline_param_defaults(x=5, y=10, z=15)

           Function docstring.

           Parameters:
              * **x** ("int") -- optional specifier line 2 (default: "5")

              * **y** ("int") --

                another optional line 4

                second paragraph for y (default: "10")

              * **z** ("int") -- yet another optional s line 6 (default: "15")

           Returns:
              something

           Return type:
              "str"

    """),
    "function_with_eq_metaclass": dedent("""\
        mod.function_with_eq_metaclass(s)

           Do something.

           Parameters:
              **s** ("Schema") -- Some schema.

           Return type:
              "Schema"
    """),
    "function_with_aliased_class": dedent("""\
        mod.function_with_aliased_class(s)

           Do something.

           Parameters:
              **s** ("Class Alias") -- Some schema.

           Return type:
              "Class Alias"
    """),
    "function_with_type_aliases": dedent("""\
        mod.function_with_type_aliases(x, y)

           Function docstring.

           Parameters:
              * **x** (Array | "None") -- foo

              * **y** ("Schema") -- boo

           Returns:
              something

           Return type:
              "str"

    """),
    "function_with_unresolvable_annotation": dedent("""\
        mod.function_with_unresolvable_annotation(x)

           Function docstring.

           Parameters:
              **x** (a.b.c) -- foo
    """),
    "function_with_typehint_comment": dedent("""\
        mod.function_with_typehint_comment(x, y)

           Function docstring.

           Parameters:
              * **x** ("int") -- foo

              * **y** ("str") -- bar

           Return type:
              "None"
    """),
    "ClassWithTypehints": dedent("""\
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
    """),
    "function_with_typehint_comment_not_inline": dedent("""\
        mod.function_with_typehint_comment_not_inline(x=None, *y, z, **kwargs)

           Function docstring.

           Parameters:
              * **x** ("str" | "bytes" | "None") -- foo

              * **y** ("str") -- bar

              * **z** ("bytes") -- baz

              * **kwargs** ("int") -- some kwargs

           Return type:
              "None"
    """),
    "ClassWithTypehintsNotInline": dedent("""\
        class mod.ClassWithTypehintsNotInline(x=None)

           Class docstring.

           Parameters:
              **x** ("Callable"[["int", "bytes"], "int"] | "None") -- foo

           foo(x=1)

              Method docstring.

              Parameters:
                 **x** ("Callable"[["int", "bytes"], "int"]) -- callback

              Return type:
                 "int"

           classmethod mk(x=None)

              Method docstring.

              Parameters:
                 **x** ("Callable"[["int", "bytes"], "int"] | "None") -- foo

              Return type:
                 "ClassWithTypehintsNotInline"
    """),
    "undocumented_function": dedent("""\
        mod.undocumented_function(x)

           Hi

           Return type:
              "str"
    """),
    "DataClass": dedent("""\
        class mod.DataClass(x)

           Class docstring.
    """),
    "Decorator": dedent("""\
        class mod.Decorator(func)

           Initializer docstring.

           Parameters:
              **func** ("Callable"[["int", "str"], "str"]) -- function
    """),
    "mocked_import": dedent("""\
        mod.mocked_import(x)

           A docstring.

           Parameters:
              **x** ("Mailbox") -- function
    """),
    "func_with_examples": dedent("""\
        mod.func_with_examples()

           A docstring.

           -[ Examples ]-

           Here are a couple of examples of how to use this function.

           Return type:
              "int"
    """),
    "func_with_overload": dedent("""\
        mod.func_with_overload(a, b)

           f does the thing. The arguments can either be ints or strings but
           they must both have the same type.

           Overloads:
              * **a** ("int"), **b** ("int") \N{RIGHTWARDS ARROW} "None"

              * **a** ("str"), **b** ("str") \N{RIGHTWARDS ARROW} "None"

           Parameters:
              * **a** ("int" | "str") -- The first thing

              * **b** ("int" | "str") -- The second thing
    """),
    "overload_with_complex_types": dedent("""\
        mod.overload_with_complex_types(x)

           Function with overloaded complex types.

           Overloads:
              * **x** ("list"["int"]) \N{RIGHTWARDS ARROW} "dict"["str", "int"]

              * **x** ("dict"["str", "int"]) \N{RIGHTWARDS ARROW} "list"["int"]

           Parameters:
              **x** ("list"["int"] | "dict"["str", "int"]) -- Input value
    """),
    "func_with_overload_no_overloads": dedent("""\
        mod.func_with_overload_no_overloads(a, b)

           Accepts int or str pairs, see docs for details.

           Parameters:
              * **a** ("int" | "str") -- The first thing

              * **b** ("int" | "str") -- The second thing

           Return type:
              "None"
    """),
    "func_literals_long_format": dedent("""\
        mod.func_literals_long_format(a, b)

           A docstring.

           Parameters:
              * **a** ("Literal"["'arg1'", "'arg2'"]) -- Argument that can
                take either of two literal values.

              * **b** ("Literal"["'arg1'", "'arg2'"]) -- Argument that can
                take either of two literal values.

           Return type:
              "None"
    """),
    "func_literals_short_format": dedent("""\
        mod.func_literals_short_format(a, b)

           A docstring.

           Parameters:
              * **a** ("'arg1'" | "'arg2'") -- Argument that can take either
                of two literal values.

              * **b** ("'arg1'" | "'arg2'") -- Argument that can take either
                of two literal values.

           Return type:
              "None"
    """),
    "func_literal_backslashes": dedent("""\
        mod.func_literal_backslashes(sep)

           A docstring.

           Parameters:
              **sep** ("Literal"["'\\n'", "'\\\\'"]) -- The separator.

           Return type:
              "None"
    """),
    "func_literal_backticks": dedent("""\
        mod.func_literal_backticks(fence)

           A docstring.

           Parameters:
              **fence** ("Literal"["'``'", "'```'"]) -- The fence.

           Return type:
              "None"
    """),
    "TestClassAttributeDocs": dedent("""\
        class mod.TestClassAttributeDocs

           A class

           code: CodeType | None

              An attribute
    """),
    "func_with_examples_and_returns_after": dedent("""\
        mod.func_with_examples_and_returns_after()

           f does the thing.

           -[ Examples ]-

           Here is an example

           Return type:
              "int"

           Returns:
              The index of the widget
    """),
    "func_with_parameters_and_stuff_after": dedent("""\
        mod.func_with_parameters_and_stuff_after(a, b)

           A func

           Parameters:
              * **a** ("int") -- a tells us something

              * **b** ("int") -- b tells us something

           Return type:
              "int"

           More info about the function here.
    """),
    "func_with_rtype_in_weird_spot": dedent("""\
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
              "int"
    """),
    "empty_line_between_parameters": dedent("""\
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
    """),
    "func_with_code_block": dedent("""\
        mod.func_with_code_block()

           A docstring.

           You would say:

              print("some python code here")

           -[ Examples ]-

           Here are a couple of examples of how to use this function.

           Return type:
              "int"
    """),
    "func_with_definition_list": dedent("""\
        mod.func_with_definition_list()

           Some text and then a definition list.

           abc
              x

           xyz
              something

           Return type:
              "int"
    """),
    "decorator_2": dedent("""\
        mod.decorator_2(f)

           Run the decorated function with *asyncio.run*.

           Parameters:
              **f** ("Any") -- The function to wrap.

           Return type:
              "Any"

           -[ Examples ]-

              A
    """),
    "ParamAndAttributeHaveSameName": dedent("""\
        class mod.ParamAndAttributeHaveSameName(blah)

           A Class

           Parameters:
              **blah** ("CodeType") -- Description of parameter blah

           blah: ModuleType

              Description of attribute blah

    """),
    "napoleon_returns": dedent("""\
        mod.napoleon_returns()

           A function.

           Return type:
              "CodeType"

           Returns:
              The info about the whatever.
    """),
    "napoleon_returns_unindented_sentence": dedent("""\
        mod.napoleon_returns_unindented_sentence()

           A function.

           Return type:
              "CodeType"

           Returns:
              The info about the whatever.
    """),
    "napoleon_returns_type_then_description": dedent("""\
        mod.napoleon_returns_type_then_description()

           A function.

           Returns:
              The info about the whatever.

           Return type:
              "CodeType"
    """),
    "napoleon_returns_type_only": dedent("""\
        mod.napoleon_returns_type_only()

           A function.

           Return type:
              "CodeType"
    """),
    "google_docstrings": dedent("""\
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

    """),
    "docstring_with_multiline_note_after_params": dedent("""\
        mod.docstring_with_multiline_note_after_params(param)

           Do something.

           Parameters:
              **param** ("int") -- A parameter.

           Return type:
              "None"

           Note:

             Some notes. More notes

    """),
    "docstring_with_bullet_list_after_params": dedent("""\
        mod.docstring_with_bullet_list_after_params(param)

           Do something.

           Parameters:
              **param** ("int") -- The count.

           Return type:
              "None"

           * A: B

           * C: D

    """),
    "docstring_with_definition_list_after_params": dedent("""\
        mod.docstring_with_definition_list_after_params(param)

           Do something.

           Parameters:
              **param** ("int") -- Any integer.

           Return type:
              "None"

           Term
              A description

              maybe multiple lines

           Next Term
              Something about it

    """),
    "docstring_with_enum_list_after_params": dedent("""\
        mod.docstring_with_enum_list_after_params(param)

           Do something.

           Parameters:
              **param** ("int") -- An index.

           Return type:
              "None"

           1. A: B

           2. C: D

    """),
    "docstring_with_definition_list_after_params_no_blank_line": dedent("""\
        mod.docstring_with_definition_list_after_params_no_blank_line(param)

           Do something.

           Parameters:
              **param** ("int") -- The number.

           Return type:
              "None"

           Term
              A description

              maybe multiple lines

           Next Term
              Something about it

           -[ Example ]-
    """),
    "has_typevar": dedent("""\
        mod.has_typevar[T](param)

           Do something.

           Parameters:
              **param** ("T") -- Value of the type parameter.

           Return type:
              "T"

    """),
    "has_newtype": dedent("""\
        mod.has_newtype(param)

           Do something.

           Parameters:
              **param** ("W" ("str")) -- A string of the new type.

           Return type:
              "W" ("str")

    """),
    "typehints_use_signature": dedent("""\
        mod.typehints_use_signature(a: AsyncGenerator) -> AsyncGenerator

           Do something.

           Parameters:
              **a** ("AsyncGenerator") -- blah

           Return type:
              "AsyncGenerator"

    """),
    "typehints_no_rtype_none": dedent("""\
        mod.typehints_no_rtype_none()

           Do something.

    """),
    "docstring_with_multiline_note_after_params_prolog_replace": dedent("""\
        mod.docstring_with_multiline_note_after_params_prolog_replace(param)

           Do something.

           Parameters:
              **param** ("int") -- A parameter.

           Return type:
              "None"

           Note:

             Some notes. test_start More notes

    """),
    "docstring_with_multiline_note_after_params_epilog_replace": dedent("""\
        mod.docstring_with_multiline_note_after_params_epilog_replace(param)

           Do something.

           Parameters:
              **param** ("int") -- An integer.

           Return type:
              "None"

           Note:

             Some notes. test_end More notes

    """),
    "docstring_with_see_also": dedent("""\
        mod.docstring_with_see_also()

           Test

           See also: more info at <https://example.com>`_.

           Return type:
              "str"

    """),
    "has_doctest1": dedent("""\
        mod.has_doctest1()

           Test that the return type follows a doctest in the function.

           >>> this is a fake doctest
           a
           >>> more doctest
           b

           Return type:
              "None"
    """),
    "typehints_formatter_applied_to_signature": dedent("""\
        mod.typehints_formatter_applied_to_signature[Unformatted](param: Formatted) -> Formatted

           Do nothing

           Parameters:
              **param** (Formatted) -- A parameter

           Return type:
              Formatted

           Returns:
              The return value
    """),
}

OPTIONS: Final[dict[str, dict[str, str | bool | dict[str, str] | TypehintsFormatter]]] = {
    "function_with_trailing_underscore_numpy": {"typehints_defaults": "comma"},
    "function_with_trailing_underscore_google": {"typehints_defaults": "comma"},
    "function_with_multiline_param_defaults": {"typehints_defaults": "braces-after"},
    **{
        name: {"autodoc_type_aliases": {"ArrayLike": "Array", "AliasedClass": '"Class Alias"'}}
        for name in ("function_with_eq_metaclass", "function_with_aliased_class", "function_with_type_aliases")
    },
    "func_literals_short_format": {"python_display_short_literal_types": True},
    "typehints_use_signature": {"typehints_use_signature": True, "typehints_use_signature_return": True},
    "typehints_no_rtype_none": {"typehints_document_rtype_none": False},
    "docstring_with_multiline_note_after_params_prolog_replace": {"rst_prolog": PROLOG},
    "docstring_with_multiline_note_after_params_epilog_replace": {"rst_epilog": EPILOG},
    "typehints_formatter_applied_to_signature": {
        "typehints_use_signature": True,
        "typehints_use_signature_return": True,
        "typehints_formatter": lambda _annotation, _config: "Formatted",
    },
}

WARNINGS: Final[dict[str, list[str]]] = {
    "function_with_unresolvable_annotation": [
        (
            'Cannot resolve forward reference in type annotations of "mod.function_with_unresolvable_annotation"'
            " (module extension_cases): name 'a' is not defined [sphinx_autodoc_typehints.forward_reference]"
        )
    ],
    "docstring_with_definition_list_after_params_no_blank_line": [
        "Definition list ends without a blank line; unexpected unindent. [docutils]"
    ],
}

__all__ = [
    "EPILOG",
    "EXPECTED",
    "OPTIONS",
    "PROLOG",
    "WARNINGS",
]
