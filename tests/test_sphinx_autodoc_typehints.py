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
from typing import (  # noqa: UP035
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

import pytest
import typing_extensions
from sphinx.application import Sphinx
from sphinx.config import Config

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

if typing.TYPE_CHECKING:
    from sphinx.testing.util import SphinxTestApp
    from sphobjinv import Inventory

try:
    import nptyping
except ImportError:
    nptyping = None  # type: ignore[assignment]

T = TypeVar("T")
U_co = TypeVar("U_co", covariant=True)
V_contra = TypeVar("V_contra", contravariant=True)
X = TypeVar("X", str, int)
Y = TypeVar("Y", bound=str)
Z = TypeVar("Z", bound="A")
S = TypeVar("S", bound="miss")  # type: ignore[name-defined] # miss not defined on purpose # noqa: F821
W = NewType("W", str)
P = typing_extensions.ParamSpec("P")
P_args = P.args  # type:ignore[attr-defined]
P_kwargs = P.kwargs  # type:ignore[attr-defined]
P_co = typing_extensions.ParamSpec("P_co", covariant=True)  # type: ignore[misc]
P_contra = typing_extensions.ParamSpec("P_contra", contravariant=True)  # type: ignore[misc]
P_bound = typing_extensions.ParamSpec("P_bound", bound=str)  # type: ignore[misc]

# Mypy does not support recursive type aliases, but
# other type checkers do.
RecList = Union[int, List["RecList"]]  # noqa: UP006, UP007
MutualRecA = Union[bool, List["MutualRecB"]]  # noqa: UP006, UP007
MutualRecB = Union[str, List["MutualRecA"]]  # noqa: UP006, UP007


class A:
    def get_type(self) -> type:
        return type(self)

    class Inner: ...


class B(Generic[T]):
    name = "Foo"  # This is set to make sure the correct class name ("B") is picked up


class C(B[str]): ...


class D(typing_extensions.Protocol): ...


class E(typing_extensions.Protocol[T]):  # type: ignore[misc]
    ...


class Slotted:
    __slots__ = ()


class Metaclass(type): ...


class HintedMethods:
    @classmethod
    def from_magic(cls: type[T]) -> T:  # type: ignore[empty-body]
        ...

    def method(self: T) -> T:  # type: ignore[empty-body]
        ...


PY310_PLUS = sys.version_info >= (3, 10)
PY312_PLUS = sys.version_info >= (3, 12)

if sys.version_info >= (3, 9):  # noqa: UP036
    AbcCallable = collections.abc.Callable  # type: ignore[type-arg]
else:
    # We could also set AbcCallable = typing.Callable and x fail the tests that
    # use AbcCallable when in versions less than 3.9.
    class MyGenericAlias(typing._VariadicGenericAlias, _root=True):  # noqa: SLF001
        def __getitem__(self, params):  # noqa: ANN001, ANN204
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
        pytest.param(Dict, "typing", "Dict", (), id="Dict"),  # noqa: UP006
        pytest.param(Dict[str, int], "typing", "Dict", (str, int), id="Dict_parametrized"),  # noqa: UP006
        pytest.param(Dict[T, int], "typing", "Dict", (T, int), id="Dict_typevar"),  # type: ignore[valid-type]  # noqa: UP006
        pytest.param(Tuple, "typing", "Tuple", (), id="Tuple"),  # noqa: UP006
        pytest.param(Tuple[str, int], "typing", "Tuple", (str, int), id="Tuple_parametrized"),  # noqa: UP006
        pytest.param(Union[str, int], "typing", "Union", (str, int), id="Union"),  # noqa: UP007
        pytest.param(Callable, "typing", "Callable", (), id="Callable"),
        pytest.param(Callable[..., str], "typing", "Callable", (..., str), id="Callable_returntype"),
        pytest.param(Callable[[int, str], str], "typing", "Callable", (int, str, str), id="Callable_all_types"),
        pytest.param(
            AbcCallable[[int, str], str],  # type: ignore[type-arg,misc,valid-type]
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
        pytest.param(P, "typing", "ParamSpec", (), id="P"),
        pytest.param(P_args, "typing", "ParamSpecArgs", (), id="P_args"),
        pytest.param(P_kwargs, "typing", "ParamSpecKwargs", (), id="P_kwargs"),
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


_CASES = [
    pytest.param(str, ":py:class:`str`", id="str"),
    pytest.param(int, ":py:class:`int`", id="int"),
    pytest.param(StringIO, ":py:class:`~io.StringIO`", id="StringIO"),
    pytest.param(FunctionType, ":py:class:`~types.FunctionType`", id="FunctionType"),
    pytest.param(ModuleType, ":py:class:`~types.ModuleType`", id="ModuleType"),
    pytest.param(type(None), ":py:obj:`None`", id="type None"),
    pytest.param(type, ":py:class:`type`", id="type"),
    pytest.param(collections.abc.Callable, ":py:class:`~collections.abc.Callable`", id="abc-Callable"),
    pytest.param(Type, ":py:class:`~typing.Type`", id="typing-Type"),  # noqa: UP006
    pytest.param(Type[A], rf":py:class:`~typing.Type`\ \[:py:class:`~{__name__}.A`]", id="typing-A"),  # noqa: UP006
    pytest.param(Any, ":py:data:`~typing.Any`", id="Any"),
    pytest.param(AnyStr, ":py:data:`~typing.AnyStr`", id="AnyStr"),
    pytest.param(Generic[T], r":py:class:`~typing.Generic`\ \[:py:class:`~typing.TypeVar`\ \(``T``)]", id="Generic"),
    pytest.param(Mapping, ":py:class:`~typing.Mapping`", id="Mapping"),
    pytest.param(
        Mapping[T, int],  # type: ignore[valid-type]
        r":py:class:`~typing.Mapping`\ \[:py:class:`~typing.TypeVar`\ \(``T``), :py:class:`int`]",
        id="Mapping-T-int",
    ),
    pytest.param(
        Mapping[str, V_contra],  # type: ignore[valid-type]
        r":py:class:`~typing.Mapping`\ \[:py:class:`str`, :py:class:`~typing.TypeVar`\ \("
        "``V_contra``, contravariant=True)]",
        id="Mapping-T-int-contra",
    ),
    pytest.param(
        Mapping[T, U_co],  # type: ignore[valid-type]
        r":py:class:`~typing.Mapping`\ \[:py:class:`~typing.TypeVar`\ \(``T``), "
        r":py:class:`~typing.TypeVar`\ \(``U_co``, covariant=True)]",
        id="Mapping-T-int-co",
    ),
    pytest.param(
        Mapping[str, bool],
        r":py:class:`~typing.Mapping`\ \[:py:class:`str`, :py:class:`bool`]",
        id="Mapping-str-bool",
    ),
    pytest.param(Dict, ":py:class:`~typing.Dict`", id="Dict"),  # noqa: UP006
    pytest.param(
        Dict[T, int],  # type: ignore[valid-type]  # noqa: UP006
        r":py:class:`~typing.Dict`\ \[:py:class:`~typing.TypeVar`\ \(``T``), :py:class:`int`]",
        id="Dict-T-int",
    ),
    pytest.param(
        Dict[str, V_contra],  # type: ignore[valid-type]  # noqa: UP006
        r":py:class:`~typing.Dict`\ \[:py:class:`str`, :py:class:`~typing.TypeVar`\ \(``V_contra``, "
        r"contravariant=True)]",
        id="Dict-T-int-contra",
    ),
    pytest.param(
        Dict[T, U_co],  # type: ignore[valid-type]  # noqa: UP006
        r":py:class:`~typing.Dict`\ \[:py:class:`~typing.TypeVar`\ \(``T``),"
        r" :py:class:`~typing.TypeVar`\ \(``U_co``, covariant=True)]",
        id="Dict-T-int-co",
    ),
    pytest.param(
        Dict[str, bool],  # noqa: UP006
        r":py:class:`~typing.Dict`\ \[:py:class:`str`, :py:class:`bool`]",
        id="Dict-str-bool",  # noqa: RUF100, UP006
    ),
    pytest.param(Tuple, ":py:data:`~typing.Tuple`", id="Tuple"),  # noqa: UP006
    pytest.param(
        Tuple[str, bool],  # noqa: UP006
        r":py:data:`~typing.Tuple`\ \[:py:class:`str`, :py:class:`bool`]",
        id="Tuple-str-bool",  # noqa: RUF100, UP006
    ),
    pytest.param(
        Tuple[int, int, int],  # noqa: UP006
        r":py:data:`~typing.Tuple`\ \[:py:class:`int`, :py:class:`int`, :py:class:`int`]",
        id="Tuple-int-int-int",
    ),
    pytest.param(
        Tuple[str, ...],  # noqa: UP006
        r":py:data:`~typing.Tuple`\ \[:py:class:`str`, :py:data:`...<Ellipsis>`]",
        id="Tuple-str-Ellipsis",
    ),
    pytest.param(Union, ":py:data:`~typing.Union`", id="Union"),
    pytest.param(
        Union[str, bool],  # noqa: UP007
        r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:class:`bool`]",
        id="Union-str-bool",
    ),
    pytest.param(
        Union[str, bool, None],  # noqa: UP007
        r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:class:`bool`, :py:obj:`None`]",
        id="Union-str-bool-None",
    ),
    pytest.param(
        Union[str, Any],  # noqa: UP007
        r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:data:`~typing.Any`]",
        id="Union-str-Any",
    ),
    pytest.param(
        Optional[str],  # noqa: UP007
        r":py:data:`~typing.Optional`\ \[:py:class:`str`]",
        id="Optional-str",
    ),
    pytest.param(
        Union[str, None],  # noqa: UP007
        r":py:data:`~typing.Optional`\ \[:py:class:`str`]",
        id="Optional-str-None",
    ),
    pytest.param(
        Optional[str | bool],  # noqa: UP007
        r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:class:`bool`, :py:obj:`None`]",
        id="Optional-Union-str-bool",
    ),
    pytest.param(Callable, ":py:data:`~typing.Callable`", id="Callable"),
    pytest.param(
        Callable[..., int],
        r":py:data:`~typing.Callable`\ \[:py:data:`...<Ellipsis>`, :py:class:`int`]",
        id="Callable-Ellipsis-int",
    ),
    pytest.param(
        Callable[[int], int],
        r":py:data:`~typing.Callable`\ \[\[:py:class:`int`], :py:class:`int`]",
        id="Callable-int-int",
    ),
    pytest.param(
        Callable[[int, str], bool],
        r":py:data:`~typing.Callable`\ \[\[:py:class:`int`, :py:class:`str`], :py:class:`bool`]",
        id="Callable-int-str-bool",
    ),
    pytest.param(
        Callable[[int, str], None],
        r":py:data:`~typing.Callable`\ \[\[:py:class:`int`, :py:class:`str`], :py:obj:`None`]",
        id="Callable-int-str",
    ),
    pytest.param(
        Callable[[T], T],
        r":py:data:`~typing.Callable`\ \[\[:py:class:`~typing.TypeVar`\ \(``T``)],"
        r" :py:class:`~typing.TypeVar`\ \(``T``)]",
        id="Callable-T-T",
    ),
    pytest.param(
        AbcCallable[[int, str], bool],  # type: ignore[valid-type,misc,type-arg]
        r":py:class:`~collections.abc.Callable`\ \[\[:py:class:`int`, :py:class:`str`], :py:class:`bool`]",
        id="AbcCallable-int-str-bool",
    ),
    pytest.param(Pattern, ":py:class:`~typing.Pattern`", id="Pattern"),
    pytest.param(Pattern[str], r":py:class:`~typing.Pattern`\ \[:py:class:`str`]", id="Pattern-str"),
    pytest.param(IO, ":py:class:`~typing.IO`", id="IO"),
    pytest.param(IO[str], r":py:class:`~typing.IO`\ \[:py:class:`str`]", id="IO-str"),
    pytest.param(Metaclass, f":py:class:`~{__name__}.Metaclass`", id="Metaclass"),
    pytest.param(A, f":py:class:`~{__name__}.A`", id="A"),
    pytest.param(B, f":py:class:`~{__name__}.B`", id="B"),
    pytest.param(B[int], rf":py:class:`~{__name__}.B`\ \[:py:class:`int`]", id="B-int"),
    pytest.param(C, f":py:class:`~{__name__}.C`", id="C"),
    pytest.param(D, f":py:class:`~{__name__}.D`", id="D"),
    pytest.param(E, f":py:class:`~{__name__}.E`", id="E"),
    pytest.param(E[int], rf":py:class:`~{__name__}.E`\ \[:py:class:`int`]", id="E-int"),
    pytest.param(W, rf":py:{'class' if PY310_PLUS else 'func'}:`~typing.NewType`\ \(``W``, :py:class:`str`)", id="W"),
    pytest.param(T, r":py:class:`~typing.TypeVar`\ \(``T``)", id="T"),
    pytest.param(U_co, r":py:class:`~typing.TypeVar`\ \(``U_co``, covariant=True)", id="U-co"),
    pytest.param(V_contra, r":py:class:`~typing.TypeVar`\ \(``V_contra``, contravariant=True)", id="V-contra"),
    pytest.param(X, r":py:class:`~typing.TypeVar`\ \(``X``, :py:class:`str`, :py:class:`int`)", id="X"),
    pytest.param(Y, r":py:class:`~typing.TypeVar`\ \(``Y``, bound= :py:class:`str`)", id="Y"),
    pytest.param(Z, r":py:class:`~typing.TypeVar`\ \(``Z``, bound= A)", id="Z"),
    pytest.param(S, r":py:class:`~typing.TypeVar`\ \(``S``, bound= miss)", id="S"),
    # ParamSpec should behave like TypeVar, except for missing constraints
    pytest.param(
        P, rf":py:class:`~typing.ParamSpec`\ \(``P``{', bound= :py:obj:`None`' if PY312_PLUS else ''})", id="P"
    ),
    pytest.param(
        P_co,
        rf":py:class:`~typing.ParamSpec`\ \(``P_co``{', bound= :py:obj:`None`' if PY312_PLUS else ''}, covariant=True)",
        id="P_co",
    ),
    pytest.param(
        P_contra,
        rf":py:class:`~typing.ParamSpec`\ \(``P_contra``{', bound= :py:obj:`None`' if PY312_PLUS else ''}"
        ", contravariant=True)",
        id="P-contra",
    ),
    pytest.param(P_bound, r":py:class:`~typing.ParamSpec`\ \(``P_bound``, bound= :py:class:`str`)", id="P-bound"),
    # ## These test for correct internal tuple rendering, even if not all are valid Tuple types
    # Zero-length tuple remains
    pytest.param(Tuple[()], ":py:data:`~typing.Tuple`", id="Tuple-p"),  # noqa: UP006
    # Internal single tuple with simple types is flattened in the output
    pytest.param(Tuple[int,], r":py:data:`~typing.Tuple`\ \[:py:class:`int`]", id="Tuple-p-int"),  # noqa: UP006
    pytest.param(
        Tuple[int, int],  # noqa: UP006
        r":py:data:`~typing.Tuple`\ \[:py:class:`int`, :py:class:`int`]",
        id="Tuple-p-int-int",  # noqa: RUF100, UP006
    ),
    # Ellipsis in single tuple also gets flattened
    pytest.param(
        Tuple[int, ...],  # noqa: UP006
        r":py:data:`~typing.Tuple`\ \[:py:class:`int`, :py:data:`...<Ellipsis>`]",
        id="Tuple-p-Ellipsis",
    ),
    pytest.param(
        RecList, r":py:data:`~typing.Union`\ \[:py:class:`int`, :py:class:`~typing.List`\ \[RecList]]", id="RecList"
    ),
    pytest.param(
        MutualRecA,
        r":py:data:`~typing.Union`\ \[:py:class:`bool`, :py:class:`~typing.List`\ \[MutualRecB]]",
        id="MutualRecA",
    ),
]

if nptyping is not None:
    _CASES.extend(
        [  # Internal tuple with following additional type cannot be flattened (specific to nptyping?)
            # These cases will fail if nptyping restructures its internal module hierarchy
            pytest.param(
                nptyping.NDArray[nptyping.Shape["*"], nptyping.Float],
                (
                    ":py:class:`~nptyping.ndarray.NDArray`\\ \\[:py:class:`~nptyping.base_meta_classes.Shape`\\ \\[*], "
                    ":py:class:`~numpy.float64`]"
                ),
                id="NDArray-star-float",
            ),
            pytest.param(
                nptyping.NDArray[nptyping.Shape["64"], nptyping.Float],
                (
                    ":py:class:`~nptyping.ndarray.NDArray`\\ \\[:py:class:`~nptyping.base_meta_classes.Shape`\\ \\[64],"
                    " :py:class:`~numpy.float64`]"
                ),
                id="NDArray-64-float",
            ),
            pytest.param(
                nptyping.NDArray[nptyping.Shape["*, *"], nptyping.Float],
                (
                    ":py:class:`~nptyping.ndarray.NDArray`\\ \\[:py:class:`~nptyping.base_meta_classes.Shape`\\ \\[*, "
                    "*], :py:class:`~numpy.float64`]"
                ),
                id="NDArray-star-star-float",
            ),
            pytest.param(
                nptyping.NDArray[nptyping.Shape["*, ..."], nptyping.Float],
                ":py:class:`~nptyping.ndarray.NDArray`\\ \\[:py:data:`~typing.Any`, :py:class:`~numpy.float64`]",
                id="NDArray-star-Ellipsis-float",
            ),
            pytest.param(
                nptyping.NDArray[nptyping.Shape["*, 3"], nptyping.Float],
                (
                    ":py:class:`~nptyping.ndarray.NDArray`\\ \\[:py:class:`~nptyping.base_meta_classes.Shape`\\ \\[*, 3"
                    "], :py:class:`~numpy.float64`]"
                ),
                id="NDArray-star-3-float",
            ),
            pytest.param(
                nptyping.NDArray[nptyping.Shape["3, ..."], nptyping.Float],
                (
                    ":py:class:`~nptyping.ndarray.NDArray`\\ \\[:py:class:`~nptyping.base_meta_classes.Shape`\\ \\[3, "
                    "...], :py:class:`~numpy.float64`]"
                ),
                id="NDArray-3-Ellipsis-float",
            ),
        ],
    )


@pytest.mark.parametrize(("annotation", "expected_result"), _CASES)
def test_format_annotation(inv: Inventory, annotation: Any, expected_result: str) -> None:
    conf = create_autospec(Config, _annotation_globals=globals(), always_use_bars_union=False)
    result = format_annotation(annotation, conf)
    assert result == expected_result

    # Test with the "simplify_optional_unions" flag turned off:
    if re.match(r"^:py:data:`~typing\.Union`\\\[.*``None``.*]", expected_result):
        # strip None - argument and copy string to avoid conflicts with
        # subsequent tests
        expected_result_not_simplified = expected_result.replace(", ``None``", "")
        # encapsulate Union in typing.Optional
        expected_result_not_simplified += ":py:data:`~typing.Optional`\\ \\["
        expected_result_not_simplified += "]"
        conf = create_autospec(
            Config,
            simplify_optional_unions=False,
            _annotation_globals=globals(),
            always_use_bars_union=False,
        )
        assert format_annotation(annotation, conf) == expected_result_not_simplified

        # Test with the "fully_qualified" flag turned on
        if "typing" in expected_result_not_simplified:
            expected_result_not_simplified = expected_result_not_simplified.replace("~typing", "typing")
            conf = create_autospec(
                Config,
                typehints_fully_qualified=True,
                simplify_optional_unions=False,
                _annotation_globals=globals(),
            )
            assert format_annotation(annotation, conf) == expected_result_not_simplified

    # Test with the "fully_qualified" flag turned on
    if "typing" in expected_result or "nptyping" in expected_result or __name__ in expected_result:
        expected_result = expected_result.replace("~typing", "typing")
        expected_result = expected_result.replace("~nptyping", "nptyping")
        expected_result = expected_result.replace("~numpy", "numpy")
        expected_result = expected_result.replace("~" + __name__, __name__)
        conf = create_autospec(
            Config,
            typehints_fully_qualified=True,
            _annotation_globals=globals(),
            always_use_bars_union=False,
        )
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


@pytest.mark.parametrize(
    ("annotation", "expected_result"),
    [
        ("int | float", ":py:class:`int` | :py:class:`float`"),
        ("int | float | None", ":py:class:`int` | :py:class:`float` | :py:obj:`None`"),
        ("Union[int, float]", ":py:class:`int` | :py:class:`float`"),
        ("Union[int, float, None]", ":py:class:`int` | :py:class:`float` | :py:obj:`None`"),
        ("Optional[int | float]", ":py:class:`int` | :py:class:`float` | :py:obj:`None`"),
        ("Optional[Union[int, float]]", ":py:class:`int` | :py:class:`float` | :py:obj:`None`"),
        ("Union[int | float, str]", ":py:class:`int` | :py:class:`float` | :py:class:`str`"),
        ("Union[int, float] | str", ":py:class:`int` | :py:class:`float` | :py:class:`str`"),
    ],
)
@pytest.mark.skipif(not PY310_PLUS, reason="| union doesn't work before py310")
def test_always_use_bars_union(annotation: str, expected_result: str) -> None:
    conf = create_autospec(Config, always_use_bars_union=True)
    result = format_annotation(eval(annotation), conf)  # noqa: S307
    assert result == expected_result


@pytest.mark.parametrize("library", [typing, typing_extensions], ids=["typing", "typing_extensions"])
@pytest.mark.parametrize(
    ("annotation", "params", "expected_result"),
    [
        pytest.param("ClassVar", int, ":py:data:`~typing.ClassVar`\\ \\[:py:class:`int`]", id="ClassVar"),
        pytest.param("NoReturn", None, ":py:data:`~typing.NoReturn`", id="NoReturn"),
        pytest.param("Literal", ("a", 1), ":py:data:`~typing.Literal`\\ \\[``'a'``, ``1``]", id="Literal"),
        pytest.param("Type", None, ":py:class:`~typing.Type`", id="Type-none"),
        pytest.param("Type", (A,), rf":py:class:`~typing.Type`\ \[:py:class:`~{__name__}.A`]", id="Type-A"),
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
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    always_document_param_types: bool,
) -> None:
    set_python_path()

    app.config.always_document_param_types = always_document_param_types  # create flag
    app.config.autodoc_mock_imports = ["mailbox"]  # create flag

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
            """,
        ),
    )

    app.build()

    assert "build succeeded" in status.getvalue()  # Build succeeded
    assert not warning.getvalue().strip()

    format_args = {}
    for indentation_level in range(2):
        key = f"undoc_params_{indentation_level}"
        if always_document_param_types:
            format_args[key] = indent('\n\n   Parameters:\n      **x** ("int")', "   " * indentation_level)
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
    if sys.version_info >= (3, 11):
        return expected_contents
    if not PY310_PLUS:
        return expected_contents.replace('"', "")

    for old, new in [
        ('"str" | "None"', '"Optional"["str"]'),
    ]:
        expected_contents = expected_contents.replace(old, new)
    return expected_contents


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_future_annotations(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()

    app.config.master_doc = "future_annotations"  # create flag
    app.build()

    assert "build succeeded" in status.getvalue()  # Build succeeded

    contents = (Path(app.srcdir) / "_build/text/future_annotations.txt").read_text()
    expected_contents = """\
    Dummy Module
    ************

    dummy_module_future_annotations.function_with_py310_annotations(self, x, y, z=None)

       Method docstring.

       Parameters:
          * **x** ("bool" | "None") -- foo

          * **y** ("int" | "str" | "float") -- bar

          * **z** ("str" | "None") -- baz

       Return type:
          "str"
    """
    expected_contents = dedent(expected_contents)
    expected_contents = maybe_fix_py310(dedent(expected_contents))
    assert contents == expected_contents


@pytest.mark.sphinx("pseudoxml", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_default_role(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()

    app.config.master_doc = "simple_default_role"  # create flag
    app.config.default_role = "literal"
    app.build()

    assert "build succeeded" in status.getvalue()  # Build succeeded

    contents_lines = (
        (Path(app.srcdir) / "_build/pseudoxml/simple_default_role.pseudoxml").read_text(encoding="utf-8").splitlines()
    )
    list_item_idxs = [i for i, line in enumerate(contents_lines) if line.strip() == "<list_item>"]
    foo_param = dedent("\n".join(contents_lines[list_item_idxs[0] : list_item_idxs[1]]))
    expected_foo_param = """\
    <list_item>
        <paragraph>
            <literal_strong>
                x
             (
            <inline classes="sphinx_autodoc_typehints-type">
                <literal classes="xref py py-class">
                    bool
            )
             \N{EN DASH}\N{SPACE}
            <literal>
                foo
    """.rstrip()
    expected_foo_param = dedent(expected_foo_param)
    assert foo_param == expected_foo_param


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
    app: SphinxTestApp,
    status: StringIO,
    defaults_config_val: str,
    expected: str | Exception,
) -> None:
    set_python_path()

    app.config.master_doc = "simple"  # create flag
    app.config.typehints_defaults = defaults_config_val  # create flag
    if isinstance(expected, Exception):
        with pytest.raises(Exception, match=re.escape(str(expected))):
            app.build()
        return
    app.build()
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
        (lambda ann, conf: "Test", ["(Test) -- foo", "(Test) -- bar", "Test"]),  # noqa: ARG005
        ("some string", Exception("needs to be callable or `None`")),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_formatter(
    app: SphinxTestApp,
    status: StringIO,
    formatter_config_val: str,
    expected: tuple[str, ...] | Exception,
) -> None:
    set_python_path()

    app.config.master_doc = "simple"  # create flag
    app.config.typehints_formatter = formatter_config_val  # create flag
    if isinstance(expected, Exception):
        with pytest.raises(Exception, match=re.escape(str(expected))):
            app.build()
        return
    app.build()
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
    def func(x):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN202
        return x

    # fmt: on
    backfill_type_hints(func, "func")


@pytest.mark.sphinx("text", testroot="resolve-typing-guard")
def test_resolve_typing_guard_imports(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    set_python_path()
    app.config.autodoc_mock_imports = ["viktor"]  # create flag
    app.build()
    out = status.getvalue()
    assert "build succeeded" in out
    err = warning.getvalue()
    r = re.compile("WARNING: Failed guarded type import")
    assert len(r.findall(err)) == 1
    pat = r'WARNING: Failed guarded type import with ImportError\("cannot import name \'missing\' from \'functools\''
    assert re.search(pat, err)


@pytest.mark.sphinx("text", testroot="resolve-typing-guard-tmp")
def test_resolve_typing_guard_attrs_imports(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    set_python_path()
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue()


def test_no_source_code_type_guard() -> None:
    from csv import Error  # noqa: PLC0415

    _resolve_type_guarded_imports([], Error)


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_formatter_no_use_rtype(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "simple_no_use_rtype"  # create flag
    app.config.typehints_use_rtype = False
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "simple_no_use_rtype.txt"
    text_contents = text_path.read_text().replace("–", "--")  # noqa: RUF001 # keep ambiguous EN DASH
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
    app.config.master_doc = "simple"  # create flag
    app.config.typehints_use_signature = True
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = text_path.read_text().replace("–", "--")  # noqa: RUF001 # keep ambiguous EN DASH
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
    app.config.master_doc = "simple"  # create flag
    app.config.typehints_use_signature_return = True
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = text_path.read_text().replace("–", "--")  # noqa: RUF001 # keep ambiguous EN DASH
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
    app.config.master_doc = "simple"  # create flag
    app.config.typehints_use_signature = True
    app.config.typehints_use_signature_return = True
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = text_path.read_text().replace("–", "--")  # noqa: RUF001 # keep ambiguous EN DASH
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
    app.config.master_doc = "without_complete_typehints"  # create flag
    app.config.typehints_defaults = "comma"
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "without_complete_typehints.txt"
    text_contents = text_path.read_text().replace("–", "--")  # noqa: RUF001 # keep ambiguous EN DASH
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


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_wrong_module_path(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    set_python_path()

    app.config.master_doc = "wrong_module_path"  # create flag
    app.config.default_role = "literal"
    app.config.nitpicky = True
    app.config.nitpick_ignore = {("py:data", "typing.Optional")}

    def fixup_module_name(mod: str) -> str:
        if not mod.startswith("wrong_module_path"):
            return mod
        return "export_module" + mod.removeprefix("wrong_module_path")

    app.config.suppress_warnings = ["config.cache"]
    app.config.typehints_fixup_module_name = fixup_module_name
    app.build()

    assert "build succeeded" in status.getvalue()  # Build succeeded
    assert not warning.getvalue().strip()
