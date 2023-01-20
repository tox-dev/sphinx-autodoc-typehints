from __future__ import annotations

import collections.abc
import re
import sys
import types
import typing
from functools import cmp_to_key
from io import StringIO
from pathlib import Path
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
RecList = Union[int, List["RecList"]]
MutualRecA = Union[bool, List["MutualRecB"]]
MutualRecB = Union[str, List["MutualRecA"]]


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
    def from_magic(cls: type[T]) -> T:  # type: ignore
        ...

    def method(self: T) -> T:  # type: ignore
        ...


PY310_PLUS = sys.version_info >= (3, 10)

if sys.version_info >= (3, 9):
    AbcCallable = collections.abc.Callable  # type: ignore[type-arg]
else:
    # Hacks to make it work the same in old versions.
    # We could also set AbcCallable = typing.Callable and x fail the tests that
    # use AbcCallable when in versions less than 3.9.
    class MyGenericAlias(typing._VariadicGenericAlias, _root=True):  # noqa: SC200
        def __getitem__(self, params):
            result = super().__getitem__(params)
            # Make a copy so we don't change the name of a cached annotation
            result = result.copy_with(result.__args__)
            result.__module__ = "collections.abc"
            return result

    AbcCallable = MyGenericAlias(collections.abc.Callable, (), special=True)
    AbcCallable.__module__ = "collections.abc"


@pytest.mark.parametrize(
    ("annotation", "module", "class_name", "args"),
    [
        pytest.param(str, "builtins", "str", (), id="str"),
        pytest.param(None, "builtins", "None", (), id="None"),
        pytest.param(ModuleType, "types", "ModuleType", (), id="ModuleType"),
        pytest.param(FunctionType, "types", "FunctionType", (), id="FunctionType"),
        pytest.param(types.CodeType, "types", "CodeType", (), id="CodeType"),
        pytest.param(types.CoroutineType, "types", "CoroutineType", (), id="CoroutineType"),
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
        pytest.param(
            AbcCallable[[int, str], str],  # type: ignore
            "collections.abc",
            "Callable",
            (int, str, str),
            id="collections.abc.Callable_all_types",
        ),
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
    got_mod = get_annotation_module(annotation)
    got_cls = get_annotation_class_name(annotation, module)
    got_args = get_annotation_args(annotation, module, class_name)
    assert (got_mod, got_cls, got_args) == (module, class_name, args)


@pytest.mark.parametrize(
    ("annotation", "expected_result"),
    [
        (str, ":py:class:`str`"),
        (int, ":py:class:`int`"),
        (StringIO, ":py:class:`~io.StringIO`"),
        (FunctionType, ":py:class:`~types.FunctionType`"),
        (ModuleType, ":py:class:`~types.ModuleType`"),
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
        (Union[str, None], ":py:data:`~typing.Optional`\\[:py:class:`str`]"),
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
        (
            AbcCallable[[int, str], bool],  # type: ignore
            ":py:class:`~collections.abc.Callable`\\[\\[:py:class:`int`, " ":py:class:`str`], :py:class:`bool`]",
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
        ("Literal", ("a", 1), ":py:data:`~typing.Literal`\\[``'a'``, ``1``]"),
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
    test_path = Path(__file__).parent
    # Add test directory to sys.path to allow imports of dummy module.
    if str(test_path) not in sys.path:
        sys.path.insert(0, str(test_path))


@pytest.mark.parametrize("always_document_param_types", [True, False], ids=["doc_param_type", "no_doc_param_type"])
@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_always_document_param_types(
    app: SphinxTestApp, status: StringIO, warning: StringIO, always_document_param_types: bool
) -> None:
    set_python_path()

    app.config.always_document_param_types = always_document_param_types  # type: ignore # create flag
    app.config.autodoc_mock_imports = ["mailbox"]  # type: ignore # create flag

    # Prevent "document isn't included in any toctree" warnings
    for f in Path(app.srcdir).glob("*.rst"):
        f.unlink()
    (Path(app.srcdir) / "index.rst").write_text(
        dedent(
            """
            .. autofunction:: dummy_module.undocumented_function

            .. autoclass:: dummy_module.DataClass
                :undoc-members:
                :special-members: __init__
            """
        )
    )

    app.build()

    assert "build succeeded" in status.getvalue()  # Build succeeded
    assert not warning.getvalue().strip()

    format_args = {}
    for indentation_level in range(2):
        key = f"undoc_params_{indentation_level}"
        if always_document_param_types:
            format_args[key] = indent('\n\n   Parameters:\n      **x** ("int") --', "   " * indentation_level)
        else:
            format_args[key] = ""

    contents = (Path(app.srcdir) / "_build/text/index.txt").read_text()
    expected_contents = """\
    dummy_module.undocumented_function(x)

       Hi{undoc_params_0}

       Return type:
          "str"

    class dummy_module.DataClass(x)

       Class docstring.{undoc_params_0}

       __init__(x){undoc_params_1}
    """
    expected_contents = dedent(expected_contents).format(**format_args)
    assert contents == expected_contents


def maybe_fix_py310(expected_contents: str) -> str:
    if not PY310_PLUS:
        return expected_contents
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


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_future_annotations(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()

    app.config.master_doc = "future_annotations"  # type: ignore # create flag
    app.build()

    assert "build succeeded" in status.getvalue()  # Build succeeded

    contents = (Path(app.srcdir) / "_build/text/future_annotations.txt").read_text()
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
    assert contents == expected_contents


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

    contents = (Path(app.srcdir) / "_build/text/simple.txt").read_text()
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
    assert contents == dedent(expected_contents)


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

    contents = (Path(app.srcdir) / "_build/text/simple.txt").read_text()
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
    assert contents == dedent(expected_contents)


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
    text_path = Path(app.srcdir) / "_build" / "text" / "simple_no_use_rtype.txt"
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
    text_path = Path(app.srcdir) / "_build" / "text" / "simple.txt"
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
    text_path = Path(app.srcdir) / "_build" / "text" / "simple.txt"
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
    text_path = Path(app.srcdir) / "_build" / "text" / "simple.txt"
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


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_default_annotation_without_typehints(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "without_complete_typehints"  # type: ignore # create flag
    app.config.typehints_defaults = "comma"  # type: ignore
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "without_complete_typehints.txt"
    text_contents = text_path.read_text().replace("–", "--")
    expected_contents = """\
    Simple Module
    *************

    dummy_module_without_complete_typehints.function_with_some_defaults_and_without_typehints(x, y=None)

       Function docstring.

       Parameters:
          * **x** -- foo

          * **y** (default: "None") -- bar

    dummy_module_without_complete_typehints.function_with_some_defaults_and_some_typehints(x, y=None)

       Function docstring.

       Parameters:
          * **x** ("int") -- foo

          * **y** (default: "None") -- bar

    dummy_module_without_complete_typehints.function_with_some_defaults_and_more_typehints(x, y=None)

       Function docstring.

       Parameters:
          * **x** ("int") -- foo

          * **y** (default: "None") -- bar

       Return type:
          "str"

    dummy_module_without_complete_typehints.function_with_defaults_and_some_typehints(x=0, y=None)

       Function docstring.

       Parameters:
          * **x** ("int", default: "0") -- foo

          * **y** (default: "None") -- bar

       Return type:
          "str"
    """
    assert text_contents == dedent(expected_contents)
