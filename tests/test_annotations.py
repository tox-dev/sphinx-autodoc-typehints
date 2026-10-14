from __future__ import annotations

import dataclasses
import enum
import importlib
import pydoc
import re
import sys
import types
import typing
import warnings
from collections.abc import Callable, Mapping
from io import StringIO
from pathlib import Path
from textwrap import dedent
from types import EllipsisType, FrameType, FunctionType, ModuleType, NotImplementedType, TracebackType
from typing import (  # ruff:ignore[deprecated-import]
    IO,
    TYPE_CHECKING,
    Annotated,
    Any,
    AnyStr,
    Dict,
    Final,
    ForwardRef,
    Generic,
    List,
    Literal,
    NewType,
    NotRequired,
    Optional,
    Required,
    Tuple,
    Type,
    TypeAliasType,
    TypeVar,
    Union,
)
from unittest.mock import MagicMock, create_autospec

import pytest
import typing_extensions
from sphinx.config import Config
from sphinx.ext.autodoc.mock import mock
from sphinx.util.inspect import TypeAliasForwardRef

from sphinx_autodoc_typehints import (
    format_annotation,
    get_annotation_args,
    get_annotation_class_name,
    get_annotation_module,
)
from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef, _get_canonical_type_alias_name

if TYPE_CHECKING:
    from sphinx.testing.util import SphinxTestApp
    from sphobjinv import Inventory

T = TypeVar("T")
U_co = TypeVar("U_co", covariant=True)
V_contra = TypeVar("V_contra", contravariant=True)
X = TypeVar("X", str, int)
Y = TypeVar("Y", bound=str)
Z = TypeVar("Z", bound="A")
S = TypeVar("S", bound="miss")  # type: ignore[name-defined] # miss not defined on purpose # ruff:ignore[undefined-name]
W = NewType("W", str)


class SomeEnum(enum.Enum):
    VALUE = "val"


P = typing_extensions.ParamSpec("P")
P_args = P.args
P_kwargs = P.kwargs
P_co = typing_extensions.ParamSpec("P_co", covariant=True)  # ty: ignore[invalid-paramspec]
P_contra = typing_extensions.ParamSpec("P_contra", contravariant=True)  # ty: ignore[invalid-paramspec]
P_bound = typing_extensions.ParamSpec("P_bound", bound=str)  # ty: ignore[invalid-paramspec]
P_default = typing_extensions.ParamSpec("P_default", default=[int, str])
T_default = typing_extensions.TypeVar("T_default", bound=int, default=bool)
Ts = typing_extensions.TypeVarTuple("Ts")
Ts_stdlib = typing.TypeVarTuple("Ts_stdlib")
RecList = Union[int, List["RecList"]]
MutualRecA = Union[bool, List["MutualRecB"]]
MutualRecB = Union[str, List["MutualRecA"]]


class A:
    def get_type(self) -> type:
        """Get the type."""

    class Inner: ...


class B[T]:
    name = "Foo"


class C(B[str]): ...


class WithParams[**Q]: ...


class D(typing_extensions.Protocol): ...


class E(typing_extensions.Protocol[T]): ...


class Slotted:
    __slots__ = ()


class Metaclass(type): ...


# The interpreter reports NoneType instead of None for an unset ParamSpec bound before CPython gh-151955 (fixed at
# patch level, e.g. present in 3.13.15 but not 3.14.7), so probe the runtime instead of the version.
_NONE_BOUND = r", bound=\ :py:obj:`None`" if P.__bound__ is not None else ""
_PARAMSPEC_COMPONENT_ROLE: Final[str] = "data" if sys.version_info < (3, 13) else "class"


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
        pytest.param(Callable, "collections.abc", "Callable", (), id="Callable"),
        pytest.param(Callable[..., str], "collections.abc", "Callable", (..., str), id="Callable_returntype"),
        pytest.param(
            Callable[[int, str], str], "collections.abc", "Callable", (int, str, str), id="Callable_all_types"
        ),
        pytest.param(
            Callable[[int, str], str],
            "collections.abc",
            "Callable",
            (int, str, str),
            id="collections.abc.Callable_all_types",
        ),
        pytest.param(re.Pattern, "re", "Pattern", (), id="Pattern"),
        pytest.param(re.Pattern[str], "re", "Pattern", (str,), id="Pattern_parametrized"),
        pytest.param(re.Match, "re", "Match", (), id="Match"),
        pytest.param(re.Match[str], "re", "Match", (str,), id="Match_parametrized"),
        pytest.param(IO, "typing", "IO", (), id="IO"),
        pytest.param(W, "typing", "NewType", (str,), id="W"),
        pytest.param(dataclasses.InitVar[str], "dataclasses", "InitVar", (str,), id="InitVar"),
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
    pytest.param(
        EllipsisType,
        f":py:{'class' if sys.version_info >= (3, 13) else 'data'}:`~types.EllipsisType`",
        id="EllipsisType",
    ),
    pytest.param(
        FunctionType,
        f":py:{'class' if sys.version_info >= (3, 13) else 'data'}:`~types.FunctionType`",
        id="FunctionType",
    ),
    pytest.param(
        FrameType,
        f":py:{'class' if sys.version_info >= (3, 13) else 'data'}:`~types.FrameType`",
        id="FrameType",
    ),
    pytest.param(ModuleType, ":py:class:`~types.ModuleType`", id="ModuleType"),
    pytest.param(
        NotImplementedType,
        f":py:{'class' if sys.version_info >= (3, 13) else 'data'}:`~types.NotImplementedType`",
        id="NotImplementedType",
    ),
    pytest.param(TracebackType, ":py:class:`~types.TracebackType`", id="TracebackType"),
    pytest.param(type(None), ":py:obj:`None`", id="type None"),
    pytest.param(type, ":py:class:`type`", id="type"),
    pytest.param(Callable, ":py:class:`~collections.abc.Callable`", id="abc-Callable"),
    pytest.param(Type, ":py:class:`~typing.Type`", id="typing-Type"),
    pytest.param(Type[A], rf":py:class:`~typing.Type`\ \[:py:class:`~{__name__}.A`]", id="typing-A"),
    pytest.param(Any, ":py:data:`~typing.Any`", id="Any"),
    pytest.param(AnyStr, ":py:data:`~typing.AnyStr`", id="AnyStr"),
    pytest.param(Generic[T], r":py:class:`~typing.Generic`\ \[:py:class:`~typing.TypeVar`\ \(``T``)]", id="Generic"),
    pytest.param(Mapping, ":py:class:`~collections.abc.Mapping`", id="Mapping"),
    pytest.param(
        Mapping[T, int],
        r":py:class:`~collections.abc.Mapping`\ \[:py:class:`~typing.TypeVar`\ \(``T``), :py:class:`int`]",
        id="Mapping-T-int",
    ),
    pytest.param(
        Mapping[str, V_contra],
        r":py:class:`~collections.abc.Mapping`\ \[:py:class:`str`, :py:class:`~typing.TypeVar`\ \("
        r"``V_contra``, contravariant=\ True)]",
        id="Mapping-T-int-contra",
    ),
    pytest.param(
        Mapping[T, U_co],
        r":py:class:`~collections.abc.Mapping`\ \[:py:class:`~typing.TypeVar`\ \(``T``), "
        r":py:class:`~typing.TypeVar`\ \(``U_co``, covariant=\ True)]",
        id="Mapping-T-int-co",
    ),
    pytest.param(
        Mapping[str, bool],
        r":py:class:`~collections.abc.Mapping`\ \[:py:class:`str`, :py:class:`bool`]",
        id="Mapping-str-bool",
    ),
    pytest.param(Dict, ":py:class:`~typing.Dict`", id="Dict"),
    pytest.param(
        Dict[T, int],
        r":py:class:`~typing.Dict`\ \[:py:class:`~typing.TypeVar`\ \(``T``), :py:class:`int`]",
        id="Dict-T-int",
    ),
    pytest.param(
        Dict[str, V_contra],
        r":py:class:`~typing.Dict`\ \[:py:class:`str`, :py:class:`~typing.TypeVar`\ \(``V_contra``, "
        r"contravariant=\ True)]",
        id="Dict-T-int-contra",
    ),
    pytest.param(
        Dict[T, U_co],
        r":py:class:`~typing.Dict`\ \[:py:class:`~typing.TypeVar`\ \(``T``),"
        r" :py:class:`~typing.TypeVar`\ \(``U_co``, covariant=\ True)]",
        id="Dict-T-int-co",
    ),
    pytest.param(
        Dict[str, bool],
        r":py:class:`~typing.Dict`\ \[:py:class:`str`, :py:class:`bool`]",
        id="Dict-str-bool",
    ),
    pytest.param(Tuple, ":py:data:`~typing.Tuple`", id="Tuple"),
    pytest.param(
        Tuple[str, bool],
        r":py:data:`~typing.Tuple`\ \[:py:class:`str`, :py:class:`bool`]",
        id="Tuple-str-bool",
    ),
    pytest.param(
        Tuple[int, int, int],
        r":py:data:`~typing.Tuple`\ \[:py:class:`int`, :py:class:`int`, :py:class:`int`]",
        id="Tuple-int-int-int",
    ),
    pytest.param(
        Tuple[str, ...],
        r":py:data:`~typing.Tuple`\ \[:py:class:`str`, :py:data:`...<Ellipsis>`]",
        id="Tuple-str-Ellipsis",
    ),
    pytest.param(Union, f":py:{'class' if sys.version_info >= (3, 14) else 'data'}:`~typing.Union`", id="Union"),
    pytest.param(
        types.UnionType, f":py:{'class' if sys.version_info >= (3, 14) else 'data'}:`~typing.Union`", id="UnionType"
    ),
    pytest.param(
        Union[str, bool],
        ":py:class:`str` | :py:class:`bool`"
        if sys.version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:class:`bool`]",
        id="Union-str-bool",
    ),
    pytest.param(
        Union[str, bool, None],
        ":py:class:`str` | :py:class:`bool` | :py:obj:`None`"
        if sys.version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:class:`bool`, :py:obj:`None`]",
        id="Union-str-bool-None",
    ),
    pytest.param(
        Union[str, Any],
        ":py:class:`str` | :py:data:`~typing.Any`"
        if sys.version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:data:`~typing.Any`]",
        id="Union-str-Any",
    ),
    pytest.param(
        Optional[str],
        ":py:class:`str` | :py:obj:`None`"
        if sys.version_info >= (3, 14)
        else r":py:data:`~typing.Optional`\ \[:py:class:`str`]",
        id="Optional-str",
    ),
    pytest.param(
        Union[str, None],
        ":py:class:`str` | :py:obj:`None`"
        if sys.version_info >= (3, 14)
        else r":py:data:`~typing.Optional`\ \[:py:class:`str`]",
        id="Optional-str-None",
    ),
    pytest.param(
        type[T] | types.UnionType,
        ":py:class:`type`\\ \\[:py:class:`~typing.TypeVar`\\ \\(``T``)] | "
        f":py:{'class' if sys.version_info >= (3, 14) else 'data'}:`~typing.Union`",
        id="typevar union bar uniontype",
    ),
    pytest.param(
        Optional[str | bool],
        ":py:class:`str` | :py:class:`bool` | :py:obj:`None`"
        if sys.version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:class:`bool`, :py:obj:`None`]",
        id="Optional-Union-str-bool",
    ),
    pytest.param(
        RecList,
        ":py:class:`int` | :py:class:`~typing.List`\\ \\[RecList]"
        if sys.version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`int`, :py:class:`~typing.List`\ \[RecList]]",
        id="RecList",
    ),
    pytest.param(
        MutualRecA,
        ":py:class:`bool` | :py:class:`~typing.List`\\ \\[MutualRecB]"
        if sys.version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`bool`, :py:class:`~typing.List`\ \[MutualRecB]]",
        id="MutualRecA",
    ),
    pytest.param(Callable, ":py:class:`~collections.abc.Callable`", id="Callable"),
    pytest.param(
        Callable[..., int],
        r":py:class:`~collections.abc.Callable`\ \[:py:data:`...<Ellipsis>`, :py:class:`int`]",
        id="Callable-Ellipsis-int",
    ),
    pytest.param(
        Callable[[int], int],
        r":py:class:`~collections.abc.Callable`\ \[\[:py:class:`int`], :py:class:`int`]",
        id="Callable-int-int",
    ),
    pytest.param(
        Callable[[int, str], bool],
        r":py:class:`~collections.abc.Callable`\ \[\[:py:class:`int`, :py:class:`str`], :py:class:`bool`]",
        id="Callable-int-str-bool",
    ),
    pytest.param(
        Callable[[int, str], None],
        r":py:class:`~collections.abc.Callable`\ \[\[:py:class:`int`, :py:class:`str`], :py:obj:`None`]",
        id="Callable-int-str",
    ),
    pytest.param(
        Callable[[T], T],
        r":py:class:`~collections.abc.Callable`\ \[\[:py:class:`~typing.TypeVar`\ \(``T``)],"
        r" :py:class:`~typing.TypeVar`\ \(``T``)]",
        id="Callable-T-T",
    ),
    pytest.param(
        Callable[[int, str], bool],
        r":py:class:`~collections.abc.Callable`\ \[\[:py:class:`int`, :py:class:`str`], :py:class:`bool`]",
        id="Callable-int-str-bool",
    ),
    pytest.param(
        Callable[P, int],
        rf":py:class:`~collections.abc.Callable`\ \[:py:class:`~typing.ParamSpec`\ \(``P``{_NONE_BOUND}),"
        r" :py:class:`int`]",
        id="Callable-ParamSpec-int",
    ),
    pytest.param(
        Callable[typing_extensions.Concatenate[str, P], int],
        r":py:class:`~collections.abc.Callable`\ \[:py:data:`~typing.Concatenate`\ \[:py:class:`str`, "
        rf":py:class:`~typing.ParamSpec`\ \(``P``{_NONE_BOUND})], :py:class:`int`]",
        id="Callable-Concatenate-int",
    ),
    pytest.param(
        WithParams[[int, str]],
        rf":py:class:`~{__name__}.WithParams`\ \[\[:py:class:`int`, :py:class:`str`]]",
        id="ParamSpec-generic-list",
    ),
    pytest.param(re.Pattern, ":py:class:`~re.Pattern`", id="Pattern"),
    pytest.param(re.Pattern[str], r":py:class:`~re.Pattern`\ \[:py:class:`str`]", id="Pattern-str"),
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
    pytest.param(W, f":py:class:`~{__name__}.W` (:py:class:`str`)", id="W"),
    pytest.param(
        dataclasses.InitVar[list[int]],
        r":py:class:`~dataclasses.InitVar`\ \[:py:class:`list`\ \[:py:class:`int`]]",
        id="InitVar",
    ),
    pytest.param(T, r":py:class:`~typing.TypeVar`\ \(``T``)", id="T"),
    pytest.param(TypeVar, ":py:class:`~typing.TypeVar`", id="TypeVar-class"),
    pytest.param(typing.ParamSpec, ":py:class:`~typing.ParamSpec`", id="ParamSpec-class"),
    pytest.param(
        typing.ParamSpecArgs, f":py:{_PARAMSPEC_COMPONENT_ROLE}:`~typing.ParamSpecArgs`", id="ParamSpecArgs-class"
    ),
    pytest.param(
        typing.ParamSpecKwargs, f":py:{_PARAMSPEC_COMPONENT_ROLE}:`~typing.ParamSpecKwargs`", id="ParamSpecKwargs-class"
    ),
    pytest.param(U_co, r":py:class:`~typing.TypeVar`\ \(``U_co``, covariant=\ True)", id="U-co"),
    pytest.param(V_contra, r":py:class:`~typing.TypeVar`\ \(``V_contra``, contravariant=\ True)", id="V-contra"),
    pytest.param(X, r":py:class:`~typing.TypeVar`\ \(``X``, :py:class:`str`, :py:class:`int`)", id="X"),
    pytest.param(Y, r":py:class:`~typing.TypeVar`\ \(``Y``, bound=\ :py:class:`str`)", id="Y"),
    pytest.param(Z, r":py:class:`~typing.TypeVar`\ \(``Z``, bound=\ A)", id="Z"),
    pytest.param(S, r":py:class:`~typing.TypeVar`\ \(``S``, bound=\ miss)", id="S"),
    pytest.param(P, rf":py:class:`~typing.ParamSpec`\ \(``P``{_NONE_BOUND})", id="P"),
    pytest.param(P_args, rf":py:{_PARAMSPEC_COMPONENT_ROLE}:`~typing.ParamSpecArgs`\ \(``P``)", id="P-args"),
    pytest.param(P_kwargs, rf":py:{_PARAMSPEC_COMPONENT_ROLE}:`~typing.ParamSpecKwargs`\ \(``P``)", id="P-kwargs"),
    pytest.param(
        P_co,
        rf":py:class:`~typing.ParamSpec`\ \(``P_co``{_NONE_BOUND}, covariant=\ True)",
        id="P_co",
    ),
    pytest.param(
        P_contra,
        rf":py:class:`~typing.ParamSpec`\ \(``P_contra``{_NONE_BOUND}"
        r", contravariant=\ True)",
        id="P-contra",
    ),
    pytest.param(P_bound, r":py:class:`~typing.ParamSpec`\ \(``P_bound``, bound=\ :py:class:`str`)", id="P-bound"),
    pytest.param(
        P_default,
        rf":py:class:`~typing.ParamSpec`\ \(``P_default``{_NONE_BOUND}, default=\ \[:py:class:`int`, :py:class:`str`])",
        id="P-default",
    ),
    pytest.param(
        T_default,
        r":py:class:`~typing.TypeVar`\ \(``T_default``, bound=\ :py:class:`int`, default=\ :py:class:`bool`)",
        id="T-default",
    ),
    pytest.param(Ts, r":py:class:`~typing.TypeVarTuple`\ \(``Ts``)", id="Ts"),
    pytest.param(Ts_stdlib, r":py:class:`~typing.TypeVarTuple`\ \(``Ts_stdlib``)", id="Ts-stdlib"),
    pytest.param(Tuple[()], r":py:data:`~typing.Tuple`\ \[()]", id="Tuple-p"),
    pytest.param(tuple[()], r":py:class:`tuple`\ \[()]", id="tuple-p"),
    pytest.param(Tuple[int,], r":py:data:`~typing.Tuple`\ \[:py:class:`int`]", id="Tuple-p-int"),
    pytest.param(
        Tuple[int, int],
        r":py:data:`~typing.Tuple`\ \[:py:class:`int`, :py:class:`int`]",
        id="Tuple-p-int-int",
    ),
    pytest.param(
        Tuple[int, ...],
        r":py:data:`~typing.Tuple`\ \[:py:class:`int`, :py:data:`...<Ellipsis>`]",
        id="Tuple-p-Ellipsis",
    ),
    pytest.param(
        tuple[int, *tuple[str, ...]],
        r":py:class:`tuple`\ \[:py:class:`int`, :py:data:`~typing.Unpack`\ \[:py:class:`tuple`\ \[:py:class:`str`,"
        r" :py:data:`...<Ellipsis>`]]]",
        id="tuple-unpacked-tuple",
    ),
    pytest.param(Annotated[int, "metadata"], r":py:class:`int`", id="Annotated-metadata"),
    pytest.param(Required[int], r":py:data:`~typing.Required`\ \[:py:class:`int`]", id="Required"),
    pytest.param(NotRequired[int], r":py:data:`~typing.NotRequired`\ \[:py:class:`int`]", id="NotRequired"),
]


@pytest.mark.parametrize(("annotation", "expected_result"), _CASES)
def test_format_annotation(inv: Inventory, annotation: Any, expected_result: str) -> None:
    conf = create_autospec(Config, _annotation_globals=globals(), always_use_bars_union=False)
    result = format_annotation(annotation, conf)
    assert result == expected_result

    if "typing" in expected_result or __name__ in expected_result:
        expected_result = expected_result.replace("~typing", "typing")
        expected_result = expected_result.replace("~collections.abc", "collections.abc")
        expected_result = expected_result.replace("~numpy", "numpy")
        expected_result = expected_result.replace("~" + __name__, __name__)
        conf = create_autospec(
            Config,
            typehints_fully_qualified=True,
            _annotation_globals=globals(),
            always_use_bars_union=False,
        )
        assert format_annotation(annotation, conf) == expected_result

    if (
        result.count(":py:") == 1
        and ("typing" in result or "types" in result)
        and (match := re.match(r"^:py:(?P<role>class|data|func):`~(?P<name>[^`]+)`", result))
    ):
        name = match.group("name")
        expected_role = next((o.role for o in inv.objects if o.name == name), None)
        if expected_role == "function":  # pragma: no cover -- Python docs inventory always uses "func"
            expected_role = "func"
        assert match.group("role") == expected_role


@pytest.mark.skipif(sys.version_info >= (3, 14), reason="Union renders with bars from Python 3.14")
@pytest.mark.parametrize(
    ("fully_qualified", "prefix"), [pytest.param(False, "~", id="short"), pytest.param(True, "", id="qualified")]
)
def test_format_annotation_unsimplified_optional_union(
    fully_qualified: bool, prefix: str
) -> None:  # pragma: <3.14 cover
    conf = create_autospec(
        Config, simplify_optional_unions=False, typehints_fully_qualified=fully_qualified, always_use_bars_union=False
    )
    assert format_annotation(Union[int, str, None], conf) == (
        rf":py:data:`{prefix}typing.Optional`\ \[:py:data:`{prefix}typing.Union`\ \[:py:class:`int`, :py:class:`str`]]"
    )


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
def test_always_use_bars_union(annotation: str, expected_result: str) -> None:
    conf = create_autospec(Config, always_use_bars_union=True)
    result = format_annotation(eval(annotation), conf)  # ruff:ignore[suspicious-eval-usage]
    assert result == expected_result


@pytest.mark.parametrize("library", [typing, typing_extensions], ids=["typing", "typing_extensions"])
@pytest.mark.parametrize(
    ("annotation", "params", "expected_result"),
    [
        pytest.param("ClassVar", int, ":py:data:`~typing.ClassVar`\\ \\[:py:class:`int`]", id="ClassVar"),
        pytest.param("NoReturn", None, ":py:data:`~typing.NoReturn`", id="NoReturn"),
        pytest.param("Literal", None, ":py:data:`~typing.Literal`", id="Literal-bare"),
        pytest.param("Literal", ("a", 1), ":py:data:`~typing.Literal`\\ \\[``'a'``, ``1``]", id="Literal"),
        pytest.param(
            "Literal",
            (SomeEnum.VALUE,),
            rf":py:data:`~typing.Literal`\ \[:py:attr:`SomeEnum.VALUE <{__name__}.SomeEnum.VALUE>`]",
            id="Literal-enum",
        ),
        pytest.param("Self", None, ":py:data:`~typing.Self`", id="Self"),
        pytest.param("Never", None, ":py:data:`~typing.Never`", id="Never"),
        pytest.param("LiteralString", None, ":py:data:`~typing.LiteralString`", id="LiteralString"),
        pytest.param("TypeAlias", None, ":py:data:`~typing.TypeAlias`", id="TypeAlias"),
        pytest.param("Final", int, ":py:data:`~typing.Final`\\ \\[:py:class:`int`]", id="Final"),
        pytest.param("ReadOnly", int, ":py:data:`~typing.ReadOnly`\\ \\[:py:class:`int`]", id="ReadOnly"),
        pytest.param("TypeGuard", int, ":py:data:`~typing.TypeGuard`\\ \\[:py:class:`int`]", id="TypeGuard"),
        pytest.param("TypeIs", int, ":py:data:`~typing.TypeIs`\\ \\[:py:class:`int`]", id="TypeIs"),
        pytest.param("TypeForm", int, ":py:data:`~typing.TypeForm`\\ \\[:py:class:`int`]", id="TypeForm"),
        pytest.param("Doc", None, ":py:class:`~typing.Doc`", id="Doc"),
        pytest.param("TypedDict", None, ":py:class:`~typing.TypedDict`", id="TypedDict"),
        pytest.param(
            "Unpack",
            tuple[int],
            ":py:data:`~typing.Unpack`\\ \\[:py:class:`tuple`\\ \\[:py:class:`int`]]",
            id="Unpack",
        ),
        pytest.param(
            "Concatenate",
            (int, ...),
            ":py:data:`~typing.Concatenate`\\ \\[:py:class:`int`, :py:data:`...<Ellipsis>`]",
            id="Concatenate",
        ),
        pytest.param("Type", None, ":py:class:`~typing.Type`", id="Type-none"),
        pytest.param("Type", (A,), rf":py:class:`~typing.Type`\ \[:py:class:`~{__name__}.A`]", id="Type-A"),
    ],
)
def test_format_annotation_both_libs(library: ModuleType, annotation: str, params: Any, expected_result: str) -> None:
    try:
        annotation_cls = getattr(library, annotation)
    except AttributeError:  # pragma: no cover -- typing gained some of these after 3.12
        pytest.skip(f"{annotation} not available in the {library.__name__} module")

    ann = annotation_cls if params is None else annotation_cls[params]
    if library is typing_extensions and not hasattr(typing, annotation):
        # a name only typing_extensions has on this Python is documented there
        expected_result = expected_result.replace("~typing.", "~typing_extensions.")
    assert format_annotation(ann, create_autospec(Config)) == expected_result


def test_format_annotation_role_matches_python_inventory(inv: Inventory) -> None:
    # CPython moving a typing/types object between py:class and py:data would leave our reference unresolved.
    not_rendered_as_itself = {
        *("types.BuiltinFunctionType", "types.LambdaType", "typing.Text"),  # aliases render as their target
        *("types.NoneType", "types.UnionType", "typing.ForwardRef"),  # rendered as None, Union, annotationlib
        *("typing.Annotated", "typing.NewType"),  # only meaningful subscripted or called
        *("typing.NoDefault", "typing.NoExtraItems", "typing.TYPE_CHECKING"),  # values, not annotations
    }
    conf = create_autospec(Config, always_use_bars_union=False)
    with warnings.catch_warnings(action="ignore", category=DeprecationWarning):  # typing.ByteString on 3.15+
        mismatches = {
            entry.name: rendered
            for entry in inv.objects
            if entry.domain == "py"
            and entry.role in {"class", "data"}
            and entry.name.rpartition(".")[0] in {"typing", "types"}
            and entry.name not in not_rendered_as_itself
            and not (rendered := format_annotation(pydoc.locate(entry.name), conf)).startswith(
                f":py:{entry.role}:`~{entry.name}`"
            )
        }
    assert mismatches == {}


def test_format_annotation_tuple() -> None:
    conf = create_autospec(Config)
    assert format_annotation((int, str), conf) == "(:py:class:`int`, :py:class:`str`)"


def test_format_annotation_empty_tuple() -> None:
    conf = create_autospec(Config)
    assert format_annotation((), conf) == "()"


def test_format_annotation_single_element_tuple() -> None:
    conf = create_autospec(Config)
    assert format_annotation((int,), conf) == "(:py:class:`int`, )"


def test_format_annotation_none() -> None:
    conf = create_autospec(Config)
    assert format_annotation(None, conf) == ":py:obj:`None`"


def test_format_annotation_ellipsis() -> None:
    conf = create_autospec(Config)
    assert format_annotation(Ellipsis, conf) == ":py:data:`...<Ellipsis>`"


def test_format_annotation_forward_ref() -> None:
    conf = create_autospec(Config)
    assert format_annotation(ForwardRef("SomeClass"), conf) == "SomeClass"


def test_format_annotation_typing_extensions_module_fixup() -> None:
    conf = create_autospec(Config)
    result = format_annotation(typing_extensions.ClassVar[int], conf)
    assert "typing.ClassVar" in result


def test_format_annotation_io_module_fixup() -> None:
    conf = create_autospec(Config)
    result = format_annotation(StringIO, conf)
    assert "io.StringIO" in result


def test_format_annotation_with_formatter_returning_value() -> None:
    conf = create_autospec(Config, typehints_formatter=lambda ann, _cfg: f"Custom({ann})")
    result = format_annotation(int, conf)
    assert result == "Custom(<class 'int'>)"


def test_format_annotation_with_formatter_returning_none() -> None:
    conf = create_autospec(Config, typehints_formatter=lambda _ann, _cfg: None, always_use_bars_union=False)
    result = format_annotation(int, conf)
    assert result == ":py:class:`int`"


@pytest.mark.parametrize(
    ("annotation", "expected_result"),
    [
        pytest.param(Literal["a", "b"], "``'a'`` | ``'b'``", id="values"),
        pytest.param(Literal, ":py:data:`~typing.Literal`", id="bare"),
    ],
)
def test_format_annotation_short_literals(annotation: Any, expected_result: str) -> None:
    assert format_annotation(annotation, create_autospec(Config), short_literals=True) == expected_result


class _OtherEnum(enum.Enum):
    VALUE = 1


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        pytest.param(
            {},
            rf":py:data:`~typing.Literal`\ \[:py:attr:`SomeEnum.VALUE <{__name__}.SomeEnum.VALUE>`, "
            rf":py:attr:`_OtherEnum.VALUE <{__name__}._OtherEnum.VALUE>`]",
            id="short",
        ),
        pytest.param(
            {"typehints_fully_qualified": True},
            rf":py:data:`typing.Literal`\ \[:py:attr:`{__name__}.SomeEnum.VALUE`, "
            rf":py:attr:`{__name__}._OtherEnum.VALUE`]",
            id="fully-qualified",
        ),
        pytest.param(
            {"typehints_fixup_module_name": lambda module: "" if module == __name__ else module},
            r":py:data:`~typing.Literal`\ \[:py:attr:`SomeEnum.VALUE`, :py:attr:`_OtherEnum.VALUE`]",
            id="without-module",
        ),
    ],
)
def test_format_annotation_literal_enum_members_keep_their_class(overrides: dict[str, Any], expected: str) -> None:
    config = create_autospec(Config, **overrides)
    assert format_annotation(Literal[SomeEnum.VALUE, _OtherEnum.VALUE], config) == expected


@pytest.mark.parametrize(
    ("build", "expected"),
    [
        pytest.param(lambda ref: ref | None, "Json | :py:obj:`None`", id="alias-or-none"),
        pytest.param(lambda ref: None | ref, ":py:obj:`None` | Json", id="none-or-alias"),
        pytest.param(lambda ref: int | ref, ":py:class:`int` | Json", id="type-or-alias"),
        pytest.param(lambda ref: ref | ref, "Json", id="same-alias-twice"),
    ],
)
def test_format_annotation_alias_union_keeps_its_bars(build: Callable[[Any], Any], expected: str) -> None:
    config = create_autospec(Config, always_use_bars_union=False)
    assert format_annotation(build(MyTypeAliasForwardRef("Json")), config) == expected


def test_format_annotation_alias_union_leaves_optional_alone() -> None:
    alias = MyTypeAliasForwardRef("Json")
    config = create_autospec(Config, always_use_bars_union=False)
    optional = "Json | :py:obj:`None`" if sys.version_info >= (3, 14) else r":py:data:`~typing.Optional`\ \[Json]"
    # the | form renders first, and the Union typing caches for both must not keep its mark
    bars = format_annotation(alias | None, config)
    optional_alias = Optional[alias]  # ty: ignore[invalid-type-form]  # the cached runtime Optional is under test
    assert (bars, format_annotation(optional_alias, config)) == ("Json | :py:obj:`None`", optional)


@pytest.mark.parametrize(
    ("subscript", "expected"),
    [
        pytest.param(lambda sub: sub.Thing[int], r"\[:py:class:`int`]", id="builtin"),
        pytest.param(lambda sub: sub.Thing[sub.Other], r"\[:py:class:`~mockedpkg.sub.Other`]", id="mocked"),
        pytest.param(lambda sub: sub.Thing[int, str], r"\[:py:class:`int`, :py:class:`str`]", id="several"),
        pytest.param(lambda sub: sub.Thing[Literal["a"]], r"\[``typing.Literal['a']``]", id="not-a-name"),
    ],
)
def test_format_annotation_subscripted_mock(subscript: Callable[[Any], Any], expected: str) -> None:
    with mock(["mockedpkg"]):
        sub = importlib.import_module("mockedpkg.sub")
        annotation = subscript(sub)
    assert format_annotation(annotation, create_autospec(Config)) == rf":py:class:`~mockedpkg.sub.Thing`\ {expected}"


def test_get_annotation_module_raises_on_unknown() -> None:
    with pytest.raises(ValueError, match="Cannot determine the module"):
        get_annotation_module(42)


def test_get_annotation_class_name_name_attr() -> None:
    result = get_annotation_class_name(IO, "typing")
    assert result == "IO"


def test_get_annotation_args_classvar() -> None:
    result = get_annotation_args(typing.ClassVar[int], "typing", "ClassVar")
    assert result == (int,)


def test_get_annotation_args_literal_values() -> None:
    result = get_annotation_args(typing.Literal["a", 1], "typing", "Literal")
    assert result == ("a", 1)


def test_get_annotation_args_generic() -> None:
    result = get_annotation_args(Generic[T], "typing", "Generic")
    assert result == (T,)


def test_get_canonical_type_alias_name_public_module(monkeypatch: pytest.MonkeyPatch) -> None:
    pub = types.ModuleType("mypkg")
    exec("type MyAlias = str | int", pub.__dict__)  # ruff:ignore[exec-builtin]
    alias: TypeAliasType = pub.__dict__["MyAlias"]
    monkeypatch.setitem(sys.modules, "mypkg", pub)
    assert _get_canonical_type_alias_name(alias) == "mypkg.MyAlias"


def test_get_canonical_type_alias_name_private_to_public(monkeypatch: pytest.MonkeyPatch) -> None:
    priv = types.ModuleType("extpkg._priv")
    exec("type ExtAlias = str | int", priv.__dict__)  # ruff:ignore[exec-builtin]
    alias: TypeAliasType = priv.__dict__["ExtAlias"]
    pub = types.ModuleType("extpkg")
    pub.ExtAlias = alias  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "extpkg._priv", priv)
    monkeypatch.setitem(sys.modules, "extpkg", pub)
    assert _get_canonical_type_alias_name(alias) == "extpkg.ExtAlias"


def test_get_canonical_type_alias_name_no_public_reexport(monkeypatch: pytest.MonkeyPatch) -> None:
    priv = types.ModuleType("extpkg2._priv")
    exec("type ExtAlias2 = str | int", priv.__dict__)  # ruff:ignore[exec-builtin]
    alias: TypeAliasType = priv.__dict__["ExtAlias2"]
    monkeypatch.setitem(sys.modules, "extpkg2._priv", priv)
    assert _get_canonical_type_alias_name(alias) == "extpkg2._priv.ExtAlias2"


def _config_without_env(*, fully_qualified: bool = False) -> MagicMock:
    config = MagicMock()
    config.typehints_formatter = None
    config.typehints_fully_qualified = fully_qualified
    del config._typehints_env  # ruff:ignore[private-member-access]
    return config


class _Rejecting:
    def __class_getitem__(cls, item: object) -> type[_Rejecting]:
        msg = f"cannot take {item}"
        raise ValueError(msg)


type _RejectedAlias = _Rejecting[int]


def test_format_annotation_type_alias_whose_value_raises() -> None:
    assert format_annotation(_RejectedAlias, _config_without_env()) == f":py:type:`~{__name__}._RejectedAlias`"


def test_format_annotation_type_alias_without_env() -> None:
    """TypeAliasForwardRef falls back to plain name when no env is available."""
    assert format_annotation(TypeAliasForwardRef("SomeAlias"), _config_without_env()) == "SomeAlias"


@pytest.mark.parametrize(
    ("crossref", "fully_qualified", "expected_result"),
    [
        pytest.param(True, False, ":py:type:`~EncoderHook`", id="crossref"),
        pytest.param(True, True, ":py:type:`EncoderHook`", id="crossref-fully-qualified"),
        pytest.param(False, False, "EncoderHook", id="plain-name"),
    ],
)
def test_format_annotation_crossref_alias(crossref: bool, fully_qualified: bool, expected_result: str) -> None:
    annotation = MyTypeAliasForwardRef("EncoderHook")
    annotation.crossref = crossref
    assert format_annotation(annotation, _config_without_env(fully_qualified=fully_qualified)) == expected_result


@pytest.mark.parametrize(
    ("documents", "href"),
    [
        pytest.param(
            {
                "index": ".. autodata:: dummy_module.ConfiguredAlias\n\n"
                ".. autofunction:: dummy_module.takes_configured_alias\n"
            },
            "#dummy_module.ConfiguredAlias",
            id="same-document",
        ),
        pytest.param(
            {
                "index": ".. toctree::\n\n   later\n\n.. autofunction:: dummy_module.takes_configured_alias\n",
                "later": ".. autodata:: dummy_module.ConfiguredAlias\n",
            },
            "later.html#dummy_module.ConfiguredAlias",
            id="later-document",
        ),
    ],
)
@pytest.mark.sphinx(
    "html",
    testroot="dummy",
    confoverrides={"autodoc_type_aliases": {"ConfiguredAlias": "dummy_module.ConfiguredAlias"}},
)
def test_configured_alias_links_its_data_entry(app: SphinxTestApp, documents: dict[str, str], href: str) -> None:
    for name, content in documents.items():
        (Path(app.srcdir) / f"{name}.rst").write_text(content)
    app.build()

    html = (Path(app.outdir) / "index.html").read_text()
    assert set(re.findall(r'class="reference internal" href="([^"]*ConfiguredAlias)"', html)) == {href}


@pytest.mark.parametrize(
    ("rst", "href"),
    [
        pytest.param(
            ".. autoclass:: local_widget.Widget\n\n.. autofunction:: local_widget.use\n",
            "#local_widget.Widget",
            id="documented-locally",
        ),
        pytest.param(
            ".. autofunction:: local_widget.use\n", "https://example.org/remote/api.html#remote.Widget", id="remote"
        ),
    ],
)
@pytest.mark.sphinx("html", testroot="intersphinx-local-target")
def test_intersphinx_mapped_type_prefers_the_local_target(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, href: str
) -> None:
    write_rst(rst)
    app.build()

    html = (Path(app.outdir) / "index.html").read_text()
    assert set(re.findall(r'href="([^"]*Widget)"', html)) == {href}


@pytest.mark.parametrize(
    "role",
    [
        pytest.param(
            role,
            id=role,
            marks=pytest.mark.sphinx(
                "html",
                testroot="intersphinx-role",
                confoverrides={"intersphinx_mapping": {"py": (f"https://example.org/{role}/", f"{role}.inv")}},
            ),
        )
        for role in ("class", "data")
    ],
)
def test_inventory_decides_the_role_of_a_type(app: SphinxTestApp, role: str) -> None:
    app.build()

    html = (Path(app.outdir) / "index.html").read_text()
    assert set(re.findall(r'href="([^"]*FunctionType)"', html)) == {
        f"https://example.org/{role}/library/types.html#types.FunctionType"
    }


def test_format_annotation_type_alias_found_in_py_domain() -> None:
    config = MagicMock()
    config.typehints_formatter = None
    config.typehints_fully_qualified = False
    config._typehints_module_prefix = "mymod"  # ruff:ignore[private-member-access]
    py_domain = MagicMock()
    py_domain.objects = {"mymod.SomeAlias": MagicMock(objtype="type")}
    env = MagicMock()
    env.get_domain.return_value = py_domain
    config._typehints_env = env  # ruff:ignore[private-member-access]
    annotation = TypeAliasForwardRef("SomeAlias")
    assert format_annotation(annotation, config) == ":py:type:`~mymod.SomeAlias`"


@pytest.mark.parametrize(
    ("documented", "expected"),
    [
        pytest.param("Config", "other.Config", id="same-name-in-the-parent-package"),
        pytest.param("sub.Config", "sub.Config", id="reexported-where-documented"),
    ],
)
def test_format_annotation_type_alias_links_the_alias_it_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest, documented: str, expected: str
) -> None:
    package = re.sub(r"\W", "_", request.node.name)
    (tmp_path / package).mkdir()
    (tmp_path / package / "__init__.py").write_text("type Config = int\n")
    (tmp_path / package / "other.py").write_text("type Config = dict[str, str]\n")
    (tmp_path / package / "sub.py").write_text(f"from {package}.other import Config\n")
    monkeypatch.syspath_prepend(tmp_path)
    py_objects = dict.fromkeys([f"{package}.{documented}", f"{package}.other.Config"], MagicMock(objtype="type"))
    env = MagicMock(get_domain=MagicMock(return_value=MagicMock(objects=py_objects)))
    config = create_autospec(
        Config,
        typehints_formatter=None,
        typehints_fully_qualified=False,
        _typehints_module_prefix=f"{package}.sub",
        _typehints_env=env,
    )
    alias = importlib.import_module(f"{package}.sub").Config
    assert format_annotation(alias, config) == f":py:type:`~{package}.{expected}`"


_TE_INT_LIST = typing_extensions.TypeAliasType(  # ruff:ignore[non-pep695-type-alias]  # the backport is under test
    "_TE_INT_LIST", list[int]
)
_TE_PAIR = typing_extensions.TypeAliasType(  # ruff:ignore[non-pep695-type-alias]  # the backport is under test
    "_TE_PAIR", tuple[T, T], type_params=(T,)
)


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(_TE_INT_LIST, r":py:class:`list`\ \[:py:class:`int`]", id="plain"),
        pytest.param(_TE_PAIR[int], r":py:class:`tuple`\ \[:py:class:`int`, :py:class:`int`]", id="subscripted"),
    ],
)
def test_format_annotation_typing_extensions_type_alias(
    annotation: typing_extensions.TypeAliasType | types.GenericAlias, expected: str
) -> None:
    assert format_annotation(annotation, create_autospec(Config)) == expected


def test_format_annotation_recursive_type_alias() -> None:
    """A self-referential PEP 695 alias renders as a cross-reference to itself, not forever (#720)."""
    namespace: dict[str, Any] = {}
    exec("type RecType = int | list[RecType]", namespace)  # ruff:ignore[exec-builtin]
    result = format_annotation(namespace["RecType"], create_autospec(Config))
    assert result == ":py:class:`int` | :py:class:`list`\\ \\[:py:type:`~RecType`]"


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        pytest.param(
            "Pair",
            r":py:class:`tuple`\ \[:py:class:`tuple`\ \[:py:class:`int`, :py:class:`int`], "
            r":py:class:`tuple`\ \[:py:class:`int`, :py:class:`int`]]",
            id="expands-when-it-cannot-recurse",
        ),
        pytest.param(
            "Outer",
            r":py:class:`list`\ \[:py:class:`tuple`\ \[:py:type:`~Outer`, :py:type:`~Inner`]]",
            id="guarded-when-its-value-does-not-evaluate",
        ),
    ],
)
def test_format_annotation_generic_alias_nested_in_itself(alias: str, expected: str) -> None:
    namespace: dict[str, Any] = {}
    exec(  # ruff:ignore[exec-builtin]
        "type Pair[T] = tuple[T, T]\ntype Outer[T] = list[tuple[T, Inner]]\ntype Inner = Missing", namespace
    )
    generic = namespace[alias]
    assert format_annotation(generic[generic[int]], create_autospec(Config)) == expected


def test_format_annotation_mutually_recursive_type_alias() -> None:
    """An indirect cycle between PEP 695 aliases resolves to a self cross-reference too (#720)."""
    namespace: dict[str, Any] = {}
    exec("type A = int | list[B]\ntype B = str | list[A]", namespace)  # ruff:ignore[exec-builtin]
    result = format_annotation(namespace["A"], create_autospec(Config))
    assert result == ":py:class:`int` | :py:class:`list`\\ \\[:py:class:`str` | :py:class:`list`\\ \\[:py:type:`~A`]]"


@pytest.mark.sphinx("text", testroot="dummy")
def test_type_variable_parameter_follows_its_equals_sign(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autofunction:: dummy_module.bounded")
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text() == dedent("""\
        dummy_module.bounded(value)

           Take a bounded type parameter.

           Parameters:
              **value** ("TypeVar"("Bounded", bound="int")) -- the value

           Return type:
              "TypeVar"("Bounded", bound="int")
        """)
