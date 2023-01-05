from __future__ import annotations

import collections.abc
import pathlib
import re
import sys
import typing
from functools import cmp_to_key
from io import StringIO
from textwrap import dedent, indent
from types import FunctionType, ModuleType
from typing import (
    IO,
    Any,
    AnyStr,
    Callable,
    Dict,
    Generic,
    List,
    Mapping,
    Match,
    NewType,
    Optional,
    Pattern,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from unittest.mock import create_autospec, patch

import nptyping
import pytest
import typing_extensions
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.testing.util import SphinxTestApp
from sphobjinv import Inventory

from sphinx_autodoc_typehints import (
    _resolve_type_guarded_imports,
    backfill_type_hints,
    format_annotation,
    get_annotation_args,
    get_annotation_class_name,
    get_annotation_module,
    normalize_source_lines,
    process_docstring,
)

T = TypeVar("T")
U = TypeVar("U", covariant=True)
V = TypeVar("V", contravariant=True)
X = TypeVar("X", str, int)
Y = TypeVar("Y", bound=str)
Z = TypeVar("Z", bound="A")
S = TypeVar("S", bound="miss")  # type: ignore # miss not defined on purpose # noqa: F821
W = NewType("W", str)
P = typing_extensions.ParamSpec("P")
P_co = typing_extensions.ParamSpec("P_co", covariant=True)  # type: ignore
P_contra = typing_extensions.ParamSpec("P_contra", contravariant=True)  # type: ignore
P_bound = typing_extensions.ParamSpec("P_bound", bound=str)  # type: ignore

# Mypy does not support recursive type aliases, but
# other type checkers do.
RecList = Union[int, List["RecList"]]  # type: ignore
MutualRecA = Union[bool, List["MutualRecB"]]  # type: ignore
MutualRecB = Union[str, List["MutualRecA"]]  # type: ignore


class A:
    def get_type(self) -> type:
        return type(self)

    class Inner:
        ...


class B(Generic[T]):
    name = "Foo"  # This is set to make sure the correct class name ("B") is picked up


class C(B[str]):
    ...


class D(typing_extensions.Protocol):
    ...


class E(typing_extensions.Protocol[T]):  # type: ignore #  Invariant type variable "T" used in protocol where covariant
    ...


class Slotted:
    __slots__ = ()


class Metaclass(type):
    ...


class HintedMethods:
    @classmethod
    def from_magic(cls: type[T]) -> T:
        ...

    def method(self: T) -> T:
        ...


PY310_PLUS = sys.version_info >= (3, 10)


@pytest.mark.parametrize(
    ("annotation", "module", "class_name", "args"),
    [
        pytest.param(str, "builtins", "str", (), id="str"),
        pytest.param(None, "builtins", "None", (), id="None"),
        pytest.param(Any, "typing", "Any", (), id="Any"),
        pytest.param(AnyStr, "typing", "AnyStr", (), id="AnyStr"),
        pytest.param(Dict, "typing", "Dict", (), id="Dict"),
        pytest.param(Dict[str, int], "typing", "Dict", (str, int), id="Dict_parametrized"),
        pytest.param(Dict[T, int], "typing", "Dict", (T, int), id="Dict_typevar"),
        pytest.param(Tuple, "typing", "Tuple", (), id="Tuple"),
        pytest.param(Tuple[str, int], "typing", "Tuple", (str, int), id="Tuple_parametrized"),
        pytest.param(Union[str, int], "typing", "Union", (str, int), id="Union"),
        pytest.param(Callable, "typing", "Callable", (), id="Callable"),
        pytest.param(Callable[..., str], "typing", "Callable", (..., str), id="Callable_returntype"),
        pytest.param(Callable[[int, str], str], "typing", "Callable", (int, str, str), id="Callable_all_types"),
        pytest.param(Pattern, "typing", "Pattern", (), id="Pattern"),
        pytest.param(Pattern[str], "typing", "Pattern", (str,), id="Pattern_parametrized"),
        pytest.param(Match, "typing", "Match", (), id="Match"),
        pytest.param(Match[str], "typing", "Match", (str,), id="Match_parametrized"),
        pytest.param(IO, "typing", "IO", (), id="IO"),
        pytest.param(W, "typing", "NewType", (str,), id="W"),
        pytest.param(Metaclass, __name__, "Metaclass", (), id="Metaclass"),
        pytest.param(Slotted, __name__, "Slotted", (), id="Slotted"),
        pytest.param(A, __name__, "A", (), id="A"),
        pytest.param(B, __name__, "B", (), id="B"),
        pytest.param(C, __name__, "C", (), id="C"),
        pytest.param(D, __name__, "D", (), id="D"),
        pytest.param(E, __name__, "E", (), id="E"),
        pytest.param(E[int], __name__, "E", (int,), id="E_parametrized"),
        pytest.param(A.Inner, __name__, "A.Inner", (), id="Inner"),
    ],
)
def test_parse_annotation(annotation: Any, module: str, class_name: str, args: tuple[Any, ...]) -> None:
    assert get_annotation_module(annotation) == module
    assert get_annotation_class_name(annotation, module) == class_name
    assert get_annotation_args(annotation, module, class_name) == args


@pytest.mark.parametrize(
    ("annotation", "expected_result"),
    [
        (str, ":py:class:`str`"),
        (int, ":py:class:`int`"),
        (type(None), ":py:obj:`None`"),
        (type, ":py:class:`type`"),
        (collections.abc.Callable, ":py:class:`~collections.abc.Callable`"),
        (Type, ":py:class:`~typing.Type`"),
        (Type[A], ":py:class:`~typing.Type`\\[:py:class:`~%s.A`]" % __name__),
        (Any, ":py:data:`~typing.Any`"),
        (AnyStr, ":py:data:`~typing.AnyStr`"),
        (Generic[T], ":py:class:`~typing.Generic`\\[:py:class:`~typing.TypeVar`\\(``T``)]"),
        (Mapping, ":py:class:`~typing.Mapping`"),
        (Mapping[T, int], ":py:class:`~typing.Mapping`\\[:py:class:`~typing.TypeVar`\\(``T``), :py:class:`int`]"),
        (
            Mapping[str, V],
            ":py:class:`~typing.Mapping`\\[:py:class:`str`, :py:class:`~typing.TypeVar`\\(``V``, contravariant=True)]",
        ),
        (
            Mapping[T, U],
            ":py:class:`~typing.Mapping`\\[:py:class:`~typing.TypeVar`\\(``T``), "
            ":py:class:`~typing.TypeVar`\\(``U``, covariant=True)]",
        ),
        (Mapping[str, bool], ":py:class:`~typing.Mapping`\\[:py:class:`str`, " ":py:class:`bool`]"),
        (Dict, ":py:class:`~typing.Dict`"),
        (Dict[T, int], ":py:class:`~typing.Dict`\\[:py:class:`~typing.TypeVar`\\(``T``), :py:class:`int`]"),
        (
            Dict[str, V],
            ":py:class:`~typing.Dict`\\[:py:class:`str`, :py:class:`~typing.TypeVar`\\(``V``, contravariant=True)]",
        ),
        (
            Dict[T, U],
            ":py:class:`~typing.Dict`\\[:py:class:`~typing.TypeVar`\\(``T``),"
            " :py:class:`~typing.TypeVar`\\(``U``, covariant=True)]",
        ),
        (Dict[str, bool], ":py:class:`~typing.Dict`\\[:py:class:`str`, " ":py:class:`bool`]"),
        (Tuple, ":py:data:`~typing.Tuple`"),
        (Tuple[str, bool], ":py:data:`~typing.Tuple`\\[:py:class:`str`, " ":py:class:`bool`]"),
        (Tuple[int, int, int], ":py:data:`~typing.Tuple`\\[:py:class:`int`, " ":py:class:`int`, :py:class:`int`]"),
        (Tuple[str, ...], ":py:data:`~typing.Tuple`\\[:py:class:`str`, :py:data:`...<Ellipsis>`]"),
        (Union, ":py:data:`~typing.Union`"),
        (Union[str, bool], ":py:data:`~typing.Union`\\[:py:class:`str`, " ":py:class:`bool`]"),
        (Union[str, bool, None], ":py:data:`~typing.Union`\\[:py:class:`str`, " ":py:class:`bool`, :py:obj:`None`]"),
        pytest.param(
            Union[str, Any],
            ":py:data:`~typing.Union`\\[:py:class:`str`, " ":py:data:`~typing.Any`]",
            marks=pytest.mark.skipif(
                (3, 5, 0) <= sys.version_info[:3] <= (3, 5, 2), reason="Union erases the str on 3.5.0 -> 3.5.2"
            ),
        ),
        (Optional[str], ":py:data:`~typing.Optional`\\[:py:class:`str`]"),
        (
            Optional[Union[str, bool]],
            ":py:data:`~typing.Union`\\[:py:class:`str`, " ":py:class:`bool`, :py:obj:`None`]",
        ),
        (Callable, ":py:data:`~typing.Callable`"),
        (Callable[..., int], ":py:data:`~typing.Callable`\\[:py:data:`...<Ellipsis>`, :py:class:`int`]"),
        (Callable[[int], int], ":py:data:`~typing.Callable`\\[\\[:py:class:`int`], " ":py:class:`int`]"),
        (
            Callable[[int, str], bool],
            ":py:data:`~typing.Callable`\\[\\[:py:class:`int`, " ":py:class:`str`], :py:class:`bool`]",
        ),
        (
            Callable[[int, str], None],
            ":py:data:`~typing.Callable`\\[\\[:py:class:`int`, " ":py:class:`str`], :py:obj:`None`]",
        ),
        (
            Callable[[T], T],
            ":py:data:`~typing.Callable`\\[\\[:py:class:`~typing.TypeVar`\\(``T``)],"
            " :py:class:`~typing.TypeVar`\\(``T``)]",
        ),
        (Pattern, ":py:class:`~typing.Pattern`"),
        (Pattern[str], ":py:class:`~typing.Pattern`\\[:py:class:`str`]"),
        (IO, ":py:class:`~typing.IO`"),
        (IO[str], ":py:class:`~typing.IO`\\[:py:class:`str`]"),
        (Metaclass, ":py:class:`~%s.Metaclass`" % __name__),
        (A, ":py:class:`~%s.A`" % __name__),
        (B, ":py:class:`~%s.B`" % __name__),
        (B[int], ":py:class:`~%s.B`\\[:py:class:`int`]" % __name__),
        (C, ":py:class:`~%s.C`" % __name__),
        (D, ":py:class:`~%s.D`" % __name__),
        (E, ":py:class:`~%s.E`" % __name__),
        (E[int], ":py:class:`~%s.E`\\[:py:class:`int`]" % __name__),
        (W, f':py:{"class" if PY310_PLUS else "func"}:' f"`~typing.NewType`\\(``W``, :py:class:`str`)"),
        (T, ":py:class:`~typing.TypeVar`\\(``T``)"),
        (U, ":py:class:`~typing.TypeVar`\\(``U``, covariant=True)"),
        (V, ":py:class:`~typing.TypeVar`\\(``V``, contravariant=True)"),
        (X, ":py:class:`~typing.TypeVar`\\(``X``, :py:class:`str`, :py:class:`int`)"),
        (Y, ":py:class:`~typing.TypeVar`\\(``Y``, bound= :py:class:`str`)"),
        (Z, ":py:class:`~typing.TypeVar`\\(``Z``, bound= A)"),
        (S, ":py:class:`~typing.TypeVar`\\(``S``, bound= miss)"),
        # ParamSpec should behave like TypeVar, except for missing constraints
        (P, ":py:class:`~typing.ParamSpec`\\(``P``)"),
        (P_co, ":py:class:`~typing.ParamSpec`\\(``P_co``, covariant=True)"),
        (P_contra, ":py:class:`~typing.ParamSpec`\\(``P_contra``, contravariant=True)"),
        (P_bound, ":py:class:`~typing.ParamSpec`\\(``P_bound``, bound= :py:class:`str`)"),
        # ## These test for correct internal tuple rendering, even if not all are valid Tuple types
        # Zero-length tuple remains
        (Tuple[()], ":py:data:`~typing.Tuple`"),
        # Internal single tuple with simple types is flattened in the output
        (Tuple[(int,)], ":py:data:`~typing.Tuple`\\[:py:class:`int`]"),
        (Tuple[(int, int)], ":py:data:`~typing.Tuple`\\[:py:class:`int`, :py:class:`int`]"),
        # Ellipsis in single tuple also gets flattened
        (Tuple[(int, ...)], ":py:data:`~typing.Tuple`\\[:py:class:`int`, :py:data:`...<Ellipsis>`]"),
        # Internal tuple with following additional type cannot be flattened (specific to nptyping?)
        # These cases will fail if nptyping restructures its internal module hierarchy
        (
            nptyping.NDArray[nptyping.Shape["*"], nptyping.Float],
            (
                ":py:class:`~nptyping.base_meta_classes.NDArray`\\[:py:class:`~nptyping.base_meta_classes.Shape`\\[*], "
                ":py:class:`~numpy.float64`]"
            ),
        ),
        (
            nptyping.NDArray[nptyping.Shape["64"], nptyping.Float],
            (
                ":py:class:`~nptyping.base_meta_classes.NDArray`\\[:py:class:`~nptyping.base_meta_classes.Shape`\\[64],"
                " :py:class:`~numpy.float64`]"
            ),
        ),
        (
            nptyping.NDArray[nptyping.Shape["*, *"], nptyping.Float],
            (
                ":py:class:`~nptyping.base_meta_classes.NDArray`\\[:py:class:`~nptyping.base_meta_classes.Shape`\\[*, "
                "*], :py:class:`~numpy.float64`]"
            ),
        ),
        (
            nptyping.NDArray[nptyping.Shape["*, ..."], nptyping.Float],
            (":py:class:`~nptyping.base_meta_classes.NDArray`\\[:py:data:`~typing.Any`, :py:class:`~numpy.float64`]"),
        ),
        (
            nptyping.NDArray[nptyping.Shape["*, 3"], nptyping.Float],
            (
                ":py:class:`~nptyping.base_meta_classes.NDArray`\\[:py:class:`~nptyping.base_meta_classes.Shape`\\[*, 3"
                "], :py:class:`~numpy.float64`]"
            ),
        ),
        (
            nptyping.NDArray[nptyping.Shape["3, ..."], nptyping.Float],
            (
                ":py:class:`~nptyping.base_meta_classes.NDArray`\\[:py:class:`~nptyping.base_meta_classes.Shape`\\[3, "
                "...], :py:class:`~numpy.float64`]"
            ),
        ),
        (
            RecList,
            (":py:data:`~typing.Union`\\[:py:class:`int`, :py:class:`~typing.List`\\[RecList]]"),
        ),
        (
            MutualRecA,
            (":py:data:`~typing.Union`\\[:py:class:`bool`, :py:class:`~typing.List`\\[MutualRecB]]"),
        ),
    ],
)
def test_format_annotation(inv: Inventory, annotation: Any, expected_result: str) -> None:
    conf = create_autospec(Config, _annotation_globals=globals())
    result = format_annotation(annotation, conf)
    assert result == expected_result

    # Test with the "simplify_optional_unions" flag turned off:
    if re.match(r"^:py:data:`~typing\.Union`\\\[.*``None``.*]", expected_result):
        # strip None - argument and copy string to avoid conflicts with
        # subsequent tests
        expected_result_not_simplified = expected_result.replace(", ``None``", "")
        # encapsulate Union in typing.Optional
        expected_result_not_simplified = ":py:data:`~typing.Optional`\\[" + expected_result_not_simplified
        expected_result_not_simplified += "]"
        conf = create_autospec(Config, simplify_optional_unions=False, _annotation_globals=globals())
        assert format_annotation(annotation, conf) == expected_result_not_simplified

        # Test with the "fully_qualified" flag turned on
        if "typing" in expected_result_not_simplified:
            expected_result_not_simplified = expected_result_not_simplified.replace("~typing", "typing")
            conf = create_autospec(
                Config, typehints_fully_qualified=True, simplify_optional_unions=False, _annotation_globals=globals()
            )
            assert format_annotation(annotation, conf) == expected_result_not_simplified

    # Test with the "fully_qualified" flag turned on
    if "typing" in expected_result or "nptyping" in expected_result or __name__ in expected_result:
        expected_result = expected_result.replace("~typing", "typing")
        expected_result = expected_result.replace("~nptyping", "nptyping")
        expected_result = expected_result.replace("~numpy", "numpy")
        expected_result = expected_result.replace("~" + __name__, __name__)
        conf = create_autospec(Config, typehints_fully_qualified=True, _annotation_globals=globals())
        assert format_annotation(annotation, conf) == expected_result

    # Test for the correct role (class vs data) using the official Sphinx inventory
    if "typing" in expected_result:
        m = re.match("^:py:(?P<role>class|data|func):`~(?P<name>[^`]+)`", result)
        assert m, "No match"
        name = m.group("name")
        expected_role = next((o.role for o in inv.objects if o.name == name), None)
        if expected_role:
            if expected_role == "function":
                expected_role = "func"

            assert m.group("role") == expected_role


@pytest.mark.parametrize("library", [typing, typing_extensions], ids=["typing", "typing_extensions"])
@pytest.mark.parametrize(
    ("annotation", "params", "expected_result"),
    [
        ("ClassVar", int, ":py:data:`~typing.ClassVar`\\[:py:class:`int`]"),
        ("NoReturn", None, ":py:data:`~typing.NoReturn`"),
        ("Literal", ("a", 1), ":py:data:`~typing.Literal`\\['a', 1]"),
        ("Type", None, ":py:class:`~typing.Type`"),
        ("Type", (A,), f":py:class:`~typing.Type`\\[:py:class:`~{__name__}.A`]"),
    ],
)
def test_format_annotation_both_libs(library: ModuleType, annotation: str, params: Any, expected_result: str) -> None:
    try:
        annotation_cls = getattr(library, annotation)
    except AttributeError:
        pytest.skip(f"{annotation} not available in the {library.__name__} module")
        return  # pragma: no cover

    ann = annotation_cls if params is None else annotation_cls[params]
    result = format_annotation(ann, create_autospec(Config))
    assert result == expected_result


def test_process_docstring_slot_wrapper() -> None:
    lines: list[str] = []
    config = create_autospec(
        Config,
        typehints_fully_qualified=False,
        simplify_optional_unions=False,
        typehints_formatter=None,
        autodoc_mock_imports=[],
    )
    app: Sphinx = create_autospec(Sphinx, config=config)
    process_docstring(app, "class", "SlotWrapper", Slotted, None, lines)
    assert not lines


def set_python_path() -> None:
    test_path = pathlib.Path(__file__).parent
    # Add test directory to sys.path to allow imports of dummy module.
    if str(test_path) not in sys.path:
        sys.path.insert(0, str(test_path))


def maybe_fix_py310(expected_contents: str) -> str:
    if PY310_PLUS:
        for old, new in [
            ("*bool** | **None*", '"Optional"["bool"]'),
            ("*int** | **str** | **float*", '"int" | "str" | "float"'),
            ("*str** | **None*", '"Optional"["str"]'),
            ("(*bool*)", '("bool")'),
            ("(*int*", '("int"'),
            ("   str", '   "str"'),
            ('"Optional"["str"]', '"Optional"["str"]'),
            ('"Optional"["Callable"[["int", "bytes"], "int"]]', '"Optional"["Callable"[["int", "bytes"], "int"]]'),
        ]:
            expected_contents = expected_contents.replace(old, new)
    return expected_contents


@pytest.mark.parametrize("always_document_param_types", [True, False], ids=["doc_param_type", "no_doc_param_type"])
@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output(
    app: SphinxTestApp, status: StringIO, warning: StringIO, always_document_param_types: bool
) -> None:
    set_python_path()

    app.config.always_document_param_types = always_document_param_types  # type: ignore # create flag
    app.config.autodoc_mock_imports = ["mailbox"]  # type: ignore # create flag
    if sys.version_info < (3, 7):
        app.config.autodoc_mock_imports.append("dummy_module_future_annotations")
    app.build()

    assert "build succeeded" in status.getvalue()  # Build succeeded

    # There should be a warning about an unresolved forward reference
    warnings = warning.getvalue().strip()
    assert "Cannot resolve forward reference in type annotations of " in warnings, warnings

    format_args = {}
    for indentation_level in range(2):
        key = f"undoc_params_{indentation_level}"
        if always_document_param_types:
            format_args[key] = indent('\n\n   Parameters:\n      **x** ("int") --', "   " * indentation_level)
        else:
            format_args[key] = ""

    text_path = pathlib.Path(app.srcdir) / "_build" / "text" / "index.txt"
    with text_path.open("r") as f:
        text_contents = f.read().replace("–", "--")
        expected_contents = """\
        Dummy Module
        ************

        class dummy_module.Class(x, y, z=None)

           Initializer docstring.

           Parameters:
              * **x** ("bool") – foo

              * **y** ("int") – bar

              * **z** ("Optional"["str"]) – baz

           class InnerClass

              Inner class.

              __dunder_inner_method(x)

                 Dunder inner method.

                 Parameters:
                    **x** ("bool") -- foo

                 Return type:
                    "str"

              inner_method(x)

                 Inner method.

                 Parameters:
                    **x** ("bool") -- foo

                 Return type:
                    "str"

           __dunder_method(x)

              Dunder method docstring.

              Parameters:
                 **x** ("str") -- foo

              Return type:
                 "str"

           __magic_custom_method__(x)

              Magic dunder method docstring.

              Parameters:
                 **x** ("str") -- foo

              Return type:
                 "str"

           _private_method(x)

              Private method docstring.

              Parameters:
                 **x** ("str") -- foo

              Return type:
                 "str"

           classmethod a_classmethod(x, y, z=None)

              Classmethod docstring.

              Parameters:
                 * **x** ("bool") – foo

                 * **y** ("int") – bar

                 * **z** ("Optional"["str"]) – baz

              Return type:
                 "str"

           a_method(x, y, z=None)

              Method docstring.

              Parameters:
                 * **x** ("bool") – foo

                 * **y** ("int") – bar

                 * **z** ("Optional"["str"]) – baz

              Return type:
                 "str"

           property a_property: str

              Property docstring

              Return type:
                 "str"

           static a_staticmethod(x, y, z=None)

              Staticmethod docstring.

              Parameters:
                 * **x** ("bool") – foo

                 * **y** ("int") – bar

                 * **z** ("Optional"["str"]) – baz

              Return type:
                 "str"

           locally_defined_callable_field() -> str

              Wrapper

              Return type:
                 "str"

        exception dummy_module.DummyException(message)

           Exception docstring

           Parameters:
              **message** ("str") – blah

        dummy_module.function(x, y, z_=None)

           Function docstring.

           Parameters:
              * **x** ("bool") – foo

              * **y** ("int") – bar

              * **z_** ("Optional"["str"]) – baz

           Returns:
              something

           Return type:
              bytes

        dummy_module.function_with_escaped_default(x='\\\\x08')

           Function docstring.

           Parameters:
              **x** ("str") – foo

        dummy_module.function_with_unresolvable_annotation(x)

           Function docstring.

           Parameters:
              **x** (*a.b.c*) – foo

        dummy_module.function_with_typehint_comment(x, y)

           Function docstring.

           Parameters:
              * **x** ("int") – foo

              * **y** ("str") – bar

           Return type:
              "None"

        dummy_module.function_with_starred_documentation_param_names(*args, **kwargs)

           Function docstring.

           Usage:

              print(1)

           Parameters:
              * ***args** ("int") -- foo

              * ****kwargs** ("str") -- bar

        class dummy_module.ClassWithTypehints(x)

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

        dummy_module.function_with_typehint_comment_not_inline(x=None, *y, z, **kwargs)

           Function docstring.

           Parameters:
              * **x** ("Union"["str", "bytes", "None"]) -- foo

              * **y** ("str") -- bar

              * **z** ("bytes") -- baz

              * **kwargs** ("int") -- some kwargs

           Return type:
              "None"

        class dummy_module.ClassWithTypehintsNotInline(x=None)

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
                 **x** ("Optional"["Callable"[["int", "bytes"], "int"]]) -- foo

              Return type:
                 "ClassWithTypehintsNotInline"

        dummy_module.undocumented_function(x)

           Hi{undoc_params_0}

           Return type:
              "str"

        class dummy_module.DataClass(x)

           Class docstring.{undoc_params_0}

           __init__(x){undoc_params_1}

        @dummy_module.Decorator(func)

           Initializer docstring.

           Parameters:
              **func** ("Callable"[["int", "str"], "str"]) -- function

        dummy_module.mocked_import(x)

           A docstring.

           Parameters:
              **x** ("Mailbox") -- function
        """
        expected_contents = dedent(expected_contents).format(**format_args).replace("–", "--")
        assert text_contents == maybe_fix_py310(expected_contents)


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_future_annotations(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()

    app.config.master_doc = "future_annotations"  # type: ignore # create flag
    app.build()

    assert "build succeeded" in status.getvalue()  # Build succeeded

    text_path = pathlib.Path(app.srcdir) / "_build" / "text" / "future_annotations.txt"
    with text_path.open("r") as f:
        text_contents = f.read().replace("–", "--")
        expected_contents = """\
        Dummy Module
        ************

        dummy_module_future_annotations.function_with_py310_annotations(self, x, y, z=None)

           Method docstring.

           Parameters:
              * **x** (*bool** | **None*) -- foo

              * **y** (*int** | **str** | **float*) -- bar

              * **z** (*str** | **None*) -- baz

           Return type:
              str
        """
        expected_contents = maybe_fix_py310(dedent(expected_contents))
        assert text_contents == expected_contents


@pytest.mark.parametrize(
    ("defaults_config_val", "expected"),
    [
        (None, '("int") -- bar'),
        ("comma", '("int", default: "1") -- bar'),
        ("braces", '("int" (default: "1")) -- bar'),
        ("braces-after", '("int") -- bar (default: "1")'),
        ("comma-after", Exception("needs to be one of")),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_defaults(
    app: SphinxTestApp, status: StringIO, defaults_config_val: str, expected: str | Exception
) -> None:
    set_python_path()

    app.config.master_doc = "simple"  # type: ignore # create flag
    app.config.typehints_defaults = defaults_config_val  # type: ignore # create flag
    try:
        app.build()
    except Exception as e:
        if not isinstance(expected, Exception):
            raise
        assert str(expected) in str(e)
        return
    assert "build succeeded" in status.getvalue()

    text_path = pathlib.Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = text_path.read_text().replace("–", "--")
    expected_contents = f"""\
    Simple Module
    *************

    dummy_module_simple.function(x, y=1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** {expected}

       Return type:
          "str"
    """
    assert text_contents == dedent(expected_contents)


@pytest.mark.parametrize(
    ("formatter_config_val", "expected"),
    [
        (None, ['("bool") -- foo', '("int") -- bar', '"str"']),
        (lambda ann, conf: "Test", ["(*Test*) -- foo", "(*Test*) -- bar", "Test"]),
        ("some string", Exception("needs to be callable or `None`")),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_formatter(
    app: SphinxTestApp, status: StringIO, formatter_config_val: str, expected: tuple[str, ...] | Exception
) -> None:
    set_python_path()

    app.config.master_doc = "simple"  # type: ignore # create flag
    app.config.typehints_formatter = formatter_config_val  # type: ignore # create flag
    try:
        app.build()
    except Exception as e:
        if not isinstance(expected, Exception):
            raise
        assert str(expected) in str(e)
        return
    assert not isinstance(expected, Exception), "Expected app.build() to raise exception, but it didn’t"
    assert "build succeeded" in status.getvalue()

    text_path = pathlib.Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = text_path.read_text().replace("–", "--")
    expected_contents = f"""\
    Simple Module
    *************

    dummy_module_simple.function(x, y=1)

       Function docstring.

       Parameters:
          * **x** {expected[0]}

          * **y** {expected[1]}

       Return type:
          {expected[2]}
    """
    assert text_contents == dedent(expected_contents)


def test_normalize_source_lines_async_def() -> None:
    source = """
    async def async_function():
        class InnerClass:
            def __init__(self): ...
    """

    expected = """
    async def async_function():
        class InnerClass:
            def __init__(self): ...
    """

    assert normalize_source_lines(dedent(source)) == dedent(expected)


def test_normalize_source_lines_def_starting_decorator_parameter() -> None:
    source = """
    @_with_parameters(
        _Parameter("self", _Parameter.POSITIONAL_OR_KEYWORD),
        *_proxy_instantiation_parameters,
        _project_id,
        _Parameter(
            "node_numbers",
            _Parameter.POSITIONAL_OR_KEYWORD,
            default=None,
            annotation=Optional[Iterable[int]],
        ),
    )
    def __init__(bound_args):  # noqa: N805
        ...
    """

    expected = """
    @_with_parameters(
        _Parameter("self", _Parameter.POSITIONAL_OR_KEYWORD),
        *_proxy_instantiation_parameters,
        _project_id,
        _Parameter(
            "node_numbers",
            _Parameter.POSITIONAL_OR_KEYWORD,
            default=None,
            annotation=Optional[Iterable[int]],
        ),
    )
    def __init__(bound_args):  # noqa: N805
        ...
    """

    assert normalize_source_lines(dedent(source)) == dedent(expected)


@pytest.mark.parametrize("obj", [cmp_to_key, 1])
def test_default_no_signature(obj: Any) -> None:
    config = create_autospec(
        Config,
        typehints_fully_qualified=False,
        simplify_optional_unions=False,
        typehints_formatter=None,
        autodoc_mock_imports=[],
    )
    app: Sphinx = create_autospec(Sphinx, config=config)
    lines: list[str] = []
    process_docstring(app, "what", "name", obj, None, lines)
    assert lines == []


@pytest.mark.parametrize("method", [HintedMethods.from_magic, HintedMethods().method])
def test_bound_class_method(method: FunctionType) -> None:
    config = create_autospec(
        Config,
        typehints_fully_qualified=False,
        simplify_optional_unions=False,
        typehints_document_rtype=False,
        always_document_param_types=True,
        typehints_defaults=True,
        typehints_formatter=None,
        autodoc_mock_imports=[],
    )
    app: Sphinx = create_autospec(Sphinx, config=config)
    process_docstring(app, "class", method.__qualname__, method, None, [])


def test_syntax_error_backfill() -> None:
    # Regression test for #188
    # fmt: off
    func = (  # Note: line break here is what previously led to SyntaxError in process_docstring
        lambda x: x)
    # fmt: on
    backfill_type_hints(func, "func")


@pytest.mark.sphinx("text", testroot="resolve-typing-guard")
def test_resolve_typing_guard_imports(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    set_python_path()
    app.config.autodoc_mock_imports = ["viktor"]  # type: ignore # create flag
    app.build()
    assert "build succeeded" in status.getvalue()
    err = warning.getvalue()
    r = re.compile("WARNING: Failed guarded type import")
    assert len(r.findall(err)) == 1
    pat = r'WARNING: Failed guarded type import with ImportError\("cannot import name \'missing\' from \'functools\''
    assert re.search(pat, err)


def test_no_source_code_type_guard() -> None:
    from csv import Error

    _resolve_type_guarded_imports([], Error)


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_formatter_no_use_rtype(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "simple_no_use_rtype"  # type: ignore # create flag
    app.config.typehints_use_rtype = False  # type: ignore
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = pathlib.Path(app.srcdir) / "_build" / "text" / "simple_no_use_rtype.txt"
    text_contents = text_path.read_text().replace("–", "--")
    expected_contents = """\
    Simple Module
    *************

    dummy_module_simple_no_use_rtype.function_no_returns(x, y=1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Return type:
          "str"

    dummy_module_simple_no_use_rtype.function_returns_with_type(x, y=1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Returns:
          *CustomType* -- A string

    dummy_module_simple_no_use_rtype.function_returns_with_compound_type(x, y=1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Returns:
          Union[str, int] -- A string or int

    dummy_module_simple_no_use_rtype.function_returns_without_type(x, y=1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Returns:
          "str" -- A string
    """
    assert text_contents == dedent(expected_contents)


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_with_use_signature(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "simple"  # type: ignore # create flag
    app.config.typehints_use_signature = True  # type: ignore
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = pathlib.Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = text_path.read_text().replace("–", "--")
    expected_contents = """\
    Simple Module
    *************

    dummy_module_simple.function(x: bool, y: int = 1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Return type:
          "str"
    """
    assert text_contents == dedent(expected_contents)


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_with_use_signature_return(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "simple"  # type: ignore # create flag
    app.config.typehints_use_signature_return = True  # type: ignore
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = pathlib.Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = text_path.read_text().replace("–", "--")
    expected_contents = """\
    Simple Module
    *************

    dummy_module_simple.function(x, y=1) -> str

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Return type:
          "str"
    """
    assert text_contents == dedent(expected_contents)


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_with_use_signature_and_return(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "simple"  # type: ignore # create flag
    app.config.typehints_use_signature = True  # type: ignore
    app.config.typehints_use_signature_return = True  # type: ignore
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = pathlib.Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = text_path.read_text().replace("–", "--")
    expected_contents = """\
    Simple Module
    *************

    dummy_module_simple.function(x: bool, y: int = 1) -> str

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Return type:
          "str"
    """
    assert text_contents == dedent(expected_contents)
