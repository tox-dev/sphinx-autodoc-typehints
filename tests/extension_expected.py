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
        class mod.Class(flag, count, label=None)

           Initializer docstring.

           Parameters:
              * **flag** ("bool") -- initializer flag

              * **count** ("int") -- bar

              * **label** ("str" | "None") -- baz

           class InnerClass

              Inner class.

              inner_method(flag)

                 Inner method.

                 Parameters:
                    **flag** ("bool") -- foo

                 Return type:
                    "str"

           classmethod a_classmethod(flag, count, label=None)

              Classmethod docstring.

              Parameters:
                 * **flag** ("bool") -- classmethod flag

                 * **count** ("int") -- bar

                 * **label** ("str" | "None") -- baz

              Return type:
                 "str"

           a_method(flag, count, label=None)

              Method docstring.

              Parameters:
                 * **flag** ("bool") -- method flag

                 * **count** ("int") -- bar

                 * **label** ("str" | "None") -- baz

              Return type:
                 "str"

           property a_property: str

              Property docstring

           static a_staticmethod(flag, count, label=None)

              Staticmethod docstring.

              Parameters:
                 * **flag** ("bool") -- staticmethod flag

                 * **count** ("int") -- bar

                 * **label** ("str" | "None") -- baz

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
        mod.function(flag, count, z_=None)

           Function docstring.

           Parameters:
              * **flag** ("bool") -- foo

              * **count** ("int") -- bar

              * **z_** ("str" | "None") -- baz

           Returns:
              something

           Return type:
              "str"
    """),
    "function_with_trailing_underscore_numpy": dedent("""\
        mod.function_with_trailing_underscore_numpy(value, lambda_=None)

           Do nothing.

           Parameters:
              * **value** ("int") -- Description for a.

              * **lambda_** ("float" | "None", default: "None") -- Description
                for lambda.

           Return type:
              "None"
    """),
    "function_with_trailing_underscore_google": dedent("""\
        mod.function_with_trailing_underscore_google(value, lambda_=None)

           Do nothing.

           Parameters:
              * **value** ("int") -- Description for a.

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
        mod.function_with_escaped_default(flag='\\x08')

           Function docstring.

           Parameters:
              **flag** ("str") -- foo
    """),
    "function_with_multiline_param_defaults": dedent("""\
        mod.function_with_multiline_param_defaults(flag=5, count=10, label=15)

           Function docstring.

           Parameters:
              * **flag** ("int") -- optional specifier line 2 (default: "5")

              * **count** ("int") --

                another optional line 4

                second paragraph for y (default: "10")

              * **label** ("int") -- yet another optional s line 6 (default:
                "15")

           Returns:
              something

           Return type:
              "str"
    """),
    "function_with_eq_metaclass": dedent("""\
        mod.function_with_eq_metaclass(text)

           Do something.

           Parameters:
              **text** ("Schema") -- Some schema.

           Return type:
              "Schema"
    """),
    "function_with_aliased_class": dedent("""\
        mod.function_with_aliased_class(text)

           Do something.

           Parameters:
              **text** ("Class Alias") -- Some schema.

           Return type:
              "Class Alias"
    """),
    "function_with_type_aliases": dedent("""\
        mod.function_with_type_aliases(flag, count)

           Function docstring.

           Parameters:
              * **flag** (Array | "None") -- foo

              * **count** ("Schema") -- boo

           Returns:
              something

           Return type:
              "str"

    """),
    "function_with_unresolvable_annotation": dedent("""\
        mod.function_with_unresolvable_annotation(flag)

           Function docstring.

           Parameters:
              **flag** (a.b.c) -- foo
    """),
    "function_with_typehint_comment": dedent("""\
        mod.function_with_typehint_comment(flag, count)

           Function docstring.

           Parameters:
              * **flag** ("int") -- foo

              * **count** ("str") -- bar

           Return type:
              "None"
    """),
    "ClassWithTypehints": dedent("""\
        class mod.ClassWithTypehints(flag)

           Class docstring.

           Parameters:
              **flag** ("int") -- foo

           foo(flag)

              Method docstring.

              Parameters:
                 **flag** ("str") -- foo

              Return type:
                 "int"

           method_without_typehint(flag)

              Method docstring.
    """),
    "function_with_typehint_comment_not_inline": dedent("""\
        mod.function_with_typehint_comment_not_inline(flag=None, *count, label, **kwargs)

           Function docstring.

           Parameters:
              * **flag** ("str" | "bytes" | "None") -- foo

              * **count** ("str") -- bar

              * **label** ("bytes") -- baz

              * **kwargs** ("int") -- some kwargs

           Return type:
              "None"
    """),
    "ClassWithTypehintsNotInline": dedent("""\
        class mod.ClassWithTypehintsNotInline(flag=None)

           Class docstring.

           Parameters:
              **flag** ("Callable"[["int", "bytes"], "int"] | "None") -- foo

           foo(flag=1)

              Method docstring.

              Parameters:
                 **flag** ("Callable"[["int", "bytes"], "int"]) -- callback

              Return type:
                 "int"

           classmethod mk(flag=None)

              Method docstring.

              Parameters:
                 **flag** ("Callable"[["int", "bytes"], "int"] | "None") --
                 foo

              Return type:
                 "ClassWithTypehintsNotInline"
    """),
    "undocumented_function": dedent("""\
        mod.undocumented_function(flag)

           Hi

           Return type:
              "str"
    """),
    "DataClass": dedent("""\
        class mod.DataClass(flag)

           Class docstring.
    """),
    "Decorator": dedent("""\
        class mod.Decorator(func)

           Initializer docstring.

           Parameters:
              **func** ("Callable"[["int", "str"], "str"]) -- function
    """),
    "mocked_import": dedent("""\
        mod.mocked_import(flag)

           A docstring.

           Parameters:
              **flag** ("Mailbox") -- function
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
        mod.func_with_overload(value, other)

           f does the thing. The arguments can either be ints or strings but
           they must both have the same type.

           Overloads:
              * **value** ("int"), **other** ("int") \N{RIGHTWARDS ARROW} "None"

              * **value** ("str"), **other** ("str") \N{RIGHTWARDS ARROW} "None"

           Parameters:
              * **value** ("int" | "str") -- The first thing

              * **other** ("int" | "str") -- The second thing
    """),
    "overload_with_complex_types": dedent("""\
        mod.overload_with_complex_types(flag)

           Function with overloaded complex types.

           Overloads:
              * **flag** ("list"["int"]) \N{RIGHTWARDS ARROW} "dict"["str", "int"]

              * **flag** ("dict"["str", "int"]) \N{RIGHTWARDS ARROW} "list"["int"]

           Parameters:
              **flag** ("list"["int"] | "dict"["str", "int"]) -- Input value
    """),
    "func_with_overload_no_overloads": dedent("""\
        mod.func_with_overload_no_overloads(value, other)

           Accepts int or str pairs, see docs for details.

           Parameters:
              * **value** ("int" | "str") -- The first thing

              * **other** ("int" | "str") -- The second thing

           Return type:
              "None"
    """),
    "func_literals_long_format": dedent("""\
        mod.func_literals_long_format(value, other)

           A docstring.

           Parameters:
              * **value** ("Literal"["'arg1'", "'arg2'"]) -- Argument that can
                take either of two literal values.

              * **other** ("Literal"["'arg1'", "'arg2'"]) -- Argument that can
                take either of two literal values.

           Return type:
              "None"
    """),
    "func_literals_short_format": dedent("""\
        mod.func_literals_short_format(value, other)

           A docstring.

           Parameters:
              * **value** ("'arg1'" | "'arg2'") -- Argument that can take
                either of two literal values.

              * **other** ("'arg1'" | "'arg2'") -- Argument that can take
                either of two literal values.

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
        mod.func_with_parameters_and_stuff_after(value, other)

           A func

           Parameters:
              * **value** ("int") -- a tells us something

              * **other** ("int") -- b tells us something

           Return type:
              "int"

           More info about the function here.
    """),
    "func_with_rtype_in_weird_spot": dedent("""\
        mod.func_with_rtype_in_weird_spot(value, other)

           A func

           Parameters:
              * **value** ("int") -- a tells us something

              * **other** ("int") -- b tells us something

           -[ Examples ]-

           Here is an example

           Returns:
              The index of the widget

           More info about the function here.

           Return type:
              "int"
    """),
    "empty_line_between_parameters": dedent("""\
        mod.empty_line_between_parameters(value, other)

           A func

           Parameters:
              * **value** ("int") --

                One of the following possibilities:

                * a

                * b

                * c

              * **other** ("int") --

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
        mod.decorator_2(func)

           Run the decorated function with *asyncio.run*.

           Parameters:
              **func** ("Any") -- The function to wrap.

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
        mod.has_typevar[ItemT](param)

           Do something.

           Parameters:
              **param** ("ItemT") -- Value of the type parameter.

           Return type:
              "ItemT"

    """),
    "has_newtype": dedent("""\
        mod.has_newtype(param)

           Do something.

           Parameters:
              **param** ("Word" ("str")) -- A string of the new type.

           Return type:
              "Word" ("str")

    """),
    "typehints_use_signature": dedent("""\
        mod.typehints_use_signature(value: AsyncGenerator) -> AsyncGenerator

           Do something.

           Parameters:
              **value** ("AsyncGenerator") -- blah

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
           value
           >>> more doctest
           other

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
