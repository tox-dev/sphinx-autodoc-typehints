from __future__ import annotations

import typing  # passed as a library and probed at runtime
from collections.abc import Callable, Mapping
from dataclasses import InitVar
from enum import Enum
from io import StringIO
from pydoc import locate
from re import Pattern, findall
from sys import version_info
from textwrap import dedent
from threading import local
from types import EllipsisType, FrameType, FunctionType, ModuleType, NotImplementedType, TracebackType, UnionType
from typing import IO, TYPE_CHECKING, Annotated, AnyStr, Final, ForwardRef, Literal, NewType, TypeVar
from warnings import catch_warnings

import typing_extensions  # passed as a library and compared by identity
from pytest import mark, param, skip
from sphinx.util.inspect import TypeAliasForwardRef

from sphinx_autodoc_typehints._refs import MyTypeAliasForwardRef, WrittenTypeAlias
from sphinx_autodoc_typehints._render import ENUM_MEMBER_ROLE, annotation_state, format_annotation

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from conftest import BuildText
    from sphinx.config import Config
    from sphinx.testing.util import SphinxTestApp
    from sphobjinv import Inventory

    from _render.conftest import MakeConfig
    from sphinx_autodoc_typehints._render.context import TypehintsFormatter
    from sphinx_autodoc_typehints._types import Annotation

Item = TypeVar("Item")
Out_co = TypeVar("Out_co", covariant=True)
In_contra = TypeVar("In_contra", contravariant=True)
Constrained = TypeVar("Constrained", str, int)
Bounded = TypeVar("Bounded", bound=str)
ForwardBounded = TypeVar("ForwardBounded", bound="Plain")
UserName = NewType("UserName", str)
_MISSING: Final[typing_extensions.Sentinel] = typing_extensions.Sentinel("_MISSING")
Params = typing_extensions.ParamSpec("Params")
# typing_extensions takes a variance and a bound for a ParamSpec, which the typing spec leaves out
Params_co = typing_extensions.ParamSpec("Params_co", covariant=True)
Params_contra = typing_extensions.ParamSpec("Params_contra", contravariant=True)
BoundParams = typing_extensions.ParamSpec("BoundParams", bound=str)  # ty: ignore[invalid-paramspec]  # under test
DefaultParams = typing_extensions.ParamSpec("DefaultParams", default=[int, str])
DefaultItem = typing_extensions.TypeVar("DefaultItem", bound=int, default=bool)
Items = typing_extensions.TypeVarTuple("Items")
StdItems = typing.TypeVarTuple("StdItems")
RecList = typing.Union[int, typing.List["RecList"]]
MutualRecA = typing.Union[bool, typing.List["MutualRecB"]]
MutualRecB = typing.Union[str, typing.List["MutualRecA"]]


class SomeEnum(Enum):
    VALUE = "val"


class OtherEnum(Enum):
    VALUE = 1


class Plain: ...


class Box[Content]: ...


class StrBox(Box[str]): ...


class WithParams[**Arguments]: ...


class Proto(typing_extensions.Protocol): ...


class GenericProto[Element](typing_extensions.Protocol): ...


class Metaclass(type): ...


_CLASS_SINCE_313_ROLE: Final[str] = "class" if version_info >= (3, 13) else "data"
_UNION_ROLE: Final[str] = "class" if version_info >= (3, 14) else "data"
_CASES: Final[list[ParameterSet]] = [
    param(str, ":py:class:`str`", id="str"),
    param(int, ":py:class:`int`", id="int"),
    param(StringIO, ":py:class:`~io.StringIO`", id="StringIO"),
    param(local, ":py:class:`~_thread._local`", id="defined-in-a-private-module"),
    param(EllipsisType, f":py:{_CLASS_SINCE_313_ROLE}:`~types.EllipsisType`", id="EllipsisType"),
    param(FunctionType, f":py:{_CLASS_SINCE_313_ROLE}:`~types.FunctionType`", id="FunctionType"),
    param(FrameType, f":py:{_CLASS_SINCE_313_ROLE}:`~types.FrameType`", id="FrameType"),
    param(ModuleType, ":py:class:`~types.ModuleType`", id="ModuleType"),
    param(NotImplementedType, f":py:{_CLASS_SINCE_313_ROLE}:`~types.NotImplementedType`", id="NotImplementedType"),
    param(TracebackType, ":py:class:`~types.TracebackType`", id="TracebackType"),
    param(None, ":py:obj:`None`", id="None"),
    param(type(None), ":py:obj:`None`", id="NoneType"),
    param(Ellipsis, ":py:data:`...<Ellipsis>`", id="Ellipsis"),
    param(ForwardRef("SomeClass"), "SomeClass", id="ForwardRef"),
    param((), "()", id="empty-tuple"),
    param((int,), "(:py:class:`int`, )", id="one-tuple"),
    param((int, str), "(:py:class:`int`, :py:class:`str`)", id="tuple"),
    param(type, ":py:class:`type`", id="type"),
    param(Callable, ":py:class:`~collections.abc.Callable`", id="abc-Callable"),
    param(typing.Type, ":py:class:`~typing.Type`", id="typing-Type"),
    param(typing.Type[Plain], rf":py:class:`~typing.Type`\ \[:py:class:`~{__name__}.Plain`]", id="typing-Plain"),
    param(typing.Any, ":py:data:`~typing.Any`", id="Any"),
    param(AnyStr, ":py:data:`~typing.AnyStr`", id="AnyStr"),
    param(
        typing.Generic[Item], r":py:class:`~typing.Generic`\ \[:py:class:`~typing.TypeVar`\ \(``Item``)]", id="Generic"
    ),
    param(Mapping, ":py:class:`~collections.abc.Mapping`", id="Mapping"),
    param(
        Mapping[Item, int],
        r":py:class:`~collections.abc.Mapping`\ \[:py:class:`~typing.TypeVar`\ \(``Item``), :py:class:`int`]",
        id="Mapping-Item-int",
    ),
    param(
        Mapping[str, In_contra],
        r":py:class:`~collections.abc.Mapping`\ \[:py:class:`str`, :py:class:`~typing.TypeVar`\ \("
        r"``In_contra``, contravariant=\ True)]",
        id="Mapping-str-contravariant",
    ),
    param(
        Mapping[Item, Out_co],
        r":py:class:`~collections.abc.Mapping`\ \[:py:class:`~typing.TypeVar`\ \(``Item``), "
        r":py:class:`~typing.TypeVar`\ \(``Out_co``, covariant=\ True)]",
        id="Mapping-Item-covariant",
    ),
    param(
        Mapping[str, bool],
        r":py:class:`~collections.abc.Mapping`\ \[:py:class:`str`, :py:class:`bool`]",
        id="Mapping-str-bool",
    ),
    param(typing.Dict, ":py:class:`~typing.Dict`", id="Dict"),
    param(
        typing.Dict[Item, int],
        r":py:class:`~typing.Dict`\ \[:py:class:`~typing.TypeVar`\ \(``Item``), :py:class:`int`]",
        id="Dict-Item-int",
    ),
    param(
        typing.Dict[str, bool], r":py:class:`~typing.Dict`\ \[:py:class:`str`, :py:class:`bool`]", id="Dict-str-bool"
    ),
    param(typing.Tuple, ":py:data:`~typing.Tuple`", id="Tuple"),
    param(
        typing.Tuple[str, bool], r":py:data:`~typing.Tuple`\ \[:py:class:`str`, :py:class:`bool`]", id="Tuple-str-bool"
    ),
    param(
        typing.Tuple[int, int, int],
        r":py:data:`~typing.Tuple`\ \[:py:class:`int`, :py:class:`int`, :py:class:`int`]",
        id="Tuple-int-int-int",
    ),
    param(
        typing.Tuple[str, ...],
        r":py:data:`~typing.Tuple`\ \[:py:class:`str`, :py:data:`...<Ellipsis>`]",
        id="Tuple-str-Ellipsis",
    ),
    param(typing.Tuple[()], r":py:data:`~typing.Tuple`\ \[()]", id="Tuple-empty"),
    param(tuple[()], r":py:class:`tuple`\ \[()]", id="tuple-empty"),
    param(typing.Tuple[int,], r":py:data:`~typing.Tuple`\ \[:py:class:`int`]", id="Tuple-int"),
    param(
        tuple[int, *tuple[str, ...]],
        r":py:class:`tuple`\ \[:py:class:`int`, :py:data:`~typing.Unpack`\ \[:py:class:`tuple`\ \[:py:class:`str`,"
        r" :py:data:`...<Ellipsis>`]]]",
        id="tuple-unpacked-tuple",
    ),
    param(typing.Union, f":py:{_UNION_ROLE}:`~typing.Union`", id="Union"),
    param(UnionType, f":py:{_UNION_ROLE}:`~typing.Union`", id="UnionType"),
    param(
        typing.Union[str, bool],
        ":py:class:`str` | :py:class:`bool`"
        if version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:class:`bool`]",
        id="Union-str-bool",
    ),
    param(
        typing.Union[str, bool, None],
        ":py:class:`str` | :py:class:`bool` | :py:obj:`None`"
        if version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:class:`bool`, :py:obj:`None`]",
        id="Union-str-bool-None",
    ),
    param(
        typing.Union[str, typing.Any],
        ":py:class:`str` | :py:data:`~typing.Any`"
        if version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:data:`~typing.Any`]",
        id="Union-str-Any",
    ),
    param(
        typing.Optional[str],
        ":py:class:`str` | :py:obj:`None`"
        if version_info >= (3, 14)
        else r":py:data:`~typing.Optional`\ \[:py:class:`str`]",
        id="Optional-str",
    ),
    param(
        typing.Optional[str | bool],
        ":py:class:`str` | :py:class:`bool` | :py:obj:`None`"
        if version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`str`, :py:class:`bool`, :py:obj:`None`]",
        id="Optional-str-or-bool",
    ),
    param(
        type[Item] | UnionType,
        rf":py:class:`type`\ \[:py:class:`~typing.TypeVar`\ \(``Item``)] | :py:{_UNION_ROLE}:`~typing.Union`",
        id="type-or-UnionType",
    ),
    param(
        RecList,
        r":py:class:`int` | :py:class:`~typing.List`\ \[RecList]"
        if version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`int`, :py:class:`~typing.List`\ \[RecList]]",
        id="RecList",
    ),
    param(
        MutualRecA,
        r":py:class:`bool` | :py:class:`~typing.List`\ \[MutualRecB]"
        if version_info >= (3, 14)
        else r":py:data:`~typing.Union`\ \[:py:class:`bool`, :py:class:`~typing.List`\ \[MutualRecB]]",
        id="MutualRecA",
    ),
    param(
        Callable[..., int],
        r":py:class:`~collections.abc.Callable`\ \[:py:data:`...<Ellipsis>`, :py:class:`int`]",
        id="Callable-Ellipsis-int",
    ),
    param(
        Callable[[int], int],
        r":py:class:`~collections.abc.Callable`\ \[\[:py:class:`int`], :py:class:`int`]",
        id="Callable-int-int",
    ),
    param(
        Callable[[int, str], bool],
        r":py:class:`~collections.abc.Callable`\ \[\[:py:class:`int`, :py:class:`str`], :py:class:`bool`]",
        id="Callable-int-str-bool",
    ),
    param(
        Callable[[int, str], None],
        r":py:class:`~collections.abc.Callable`\ \[\[:py:class:`int`, :py:class:`str`], :py:obj:`None`]",
        id="Callable-int-str-None",
    ),
    param(
        Callable[[Item], Item],
        r":py:class:`~collections.abc.Callable`\ \[\[:py:class:`~typing.TypeVar`\ \(``Item``)],"
        r" :py:class:`~typing.TypeVar`\ \(``Item``)]",
        id="Callable-Item-Item",
    ),
    param(
        Callable[Params, int],
        r":py:class:`~collections.abc.Callable`\ \[:py:class:`~typing.ParamSpec`\ \(``Params``), :py:class:`int`]",
        id="Callable-ParamSpec-int",
    ),
    param(
        Callable[typing_extensions.Concatenate[str, Params], int],
        r":py:class:`~collections.abc.Callable`\ \[:py:data:`~typing.Concatenate`\ \[:py:class:`str`, "
        r":py:class:`~typing.ParamSpec`\ \(``Params``)], :py:class:`int`]",
        id="Callable-Concatenate-int",
    ),
    param(
        WithParams[[int, str]],
        rf":py:class:`~{__name__}.WithParams`\ \[\[:py:class:`int`, :py:class:`str`]]",
        id="ParamSpec-generic-list",
    ),
    param(Pattern, ":py:class:`~re.Pattern`", id="Pattern"),
    param(Pattern[str], r":py:class:`~re.Pattern`\ \[:py:class:`str`]", id="Pattern-str"),
    param(IO, ":py:class:`~typing.IO`", id="IO"),
    param(IO[str], r":py:class:`~typing.IO`\ \[:py:class:`str`]", id="IO-str"),
    param(Metaclass, f":py:class:`~{__name__}.Metaclass`", id="Metaclass"),
    param(Plain, f":py:class:`~{__name__}.Plain`", id="Plain"),
    param(Box, f":py:class:`~{__name__}.Box`", id="Box"),
    param(Box[int], rf":py:class:`~{__name__}.Box`\ \[:py:class:`int`]", id="Box-int"),
    param(StrBox, f":py:class:`~{__name__}.StrBox`", id="StrBox"),
    param(Proto, f":py:class:`~{__name__}.Proto`", id="Proto"),
    param(GenericProto, f":py:class:`~{__name__}.GenericProto`", id="GenericProto"),
    param(GenericProto[int], rf":py:class:`~{__name__}.GenericProto`\ \[:py:class:`int`]", id="GenericProto-int"),
    param(UserName, f":py:class:`~{__name__}.UserName` (:py:class:`str`)", id="NewType"),
    param(_MISSING, f":py:data:`~{__name__}._MISSING`", id="sentinel"),
    param(
        InitVar[list[int]],
        r":py:class:`~dataclasses.InitVar`\ \[:py:class:`list`\ \[:py:class:`int`]]",
        id="InitVar",
    ),
    param(Item, r":py:class:`~typing.TypeVar`\ \(``Item``)", id="TypeVar"),
    param(TypeVar, ":py:class:`~typing.TypeVar`", id="TypeVar-class"),
    param(typing.ParamSpec, ":py:class:`~typing.ParamSpec`", id="ParamSpec-class"),
    param(typing.ParamSpecArgs, f":py:{_CLASS_SINCE_313_ROLE}:`~typing.ParamSpecArgs`", id="ParamSpecArgs-class"),
    param(typing.ParamSpecKwargs, f":py:{_CLASS_SINCE_313_ROLE}:`~typing.ParamSpecKwargs`", id="ParamSpecKwargs-class"),
    param(Out_co, r":py:class:`~typing.TypeVar`\ \(``Out_co``, covariant=\ True)", id="TypeVar-covariant"),
    param(
        In_contra, r":py:class:`~typing.TypeVar`\ \(``In_contra``, contravariant=\ True)", id="TypeVar-contravariant"
    ),
    param(
        Constrained,
        r":py:class:`~typing.TypeVar`\ \(``Constrained``, :py:class:`str`, :py:class:`int`)",
        id="TypeVar-constrained",
    ),
    param(Bounded, r":py:class:`~typing.TypeVar`\ \(``Bounded``, bound=\ :py:class:`str`)", id="TypeVar-bound"),
    param(
        ForwardBounded,
        r":py:class:`~typing.TypeVar`\ \(``ForwardBounded``, bound=\ Plain)",
        id="TypeVar-forward-bound",
    ),
    param(Params, r":py:class:`~typing.ParamSpec`\ \(``Params``)", id="ParamSpec"),
    param(Params.args, rf":py:{_CLASS_SINCE_313_ROLE}:`~typing.ParamSpecArgs`\ \(``Params``)", id="ParamSpec-args"),
    param(
        Params.kwargs,
        rf":py:{_CLASS_SINCE_313_ROLE}:`~typing.ParamSpecKwargs`\ \(``Params``)",
        id="ParamSpec-kwargs",
    ),
    param(Params_co, r":py:class:`~typing.ParamSpec`\ \(``Params_co``, covariant=\ True)", id="ParamSpec-covariant"),
    param(
        Params_contra,
        r":py:class:`~typing.ParamSpec`\ \(``Params_contra``, contravariant=\ True)",
        id="ParamSpec-contravariant",
    ),
    param(
        BoundParams,
        r":py:class:`~typing.ParamSpec`\ \(``BoundParams``, bound=\ :py:class:`str`)",
        id="ParamSpec-bound",
    ),
    param(
        DefaultParams,
        r":py:class:`~typing.ParamSpec`\ \(``DefaultParams``, default=\ \[:py:class:`int`, :py:class:`str`])",
        id="ParamSpec-default",
    ),
    param(
        DefaultItem,
        r":py:class:`~typing.TypeVar`\ \(``DefaultItem``, bound=\ :py:class:`int`, default=\ :py:class:`bool`)",
        id="TypeVar-default",
    ),
    param(Items, r":py:class:`~typing.TypeVarTuple`\ \(``Items``)", id="TypeVarTuple"),
    param(StdItems, r":py:class:`~typing.TypeVarTuple`\ \(``StdItems``)", id="TypeVarTuple-stdlib"),
    param(Annotated[int, "metadata"], r":py:class:`int`", id="Annotated"),
    param(typing.Required[int], r":py:data:`~typing.Required`\ \[:py:class:`int`]", id="Required"),
    param(typing.NotRequired[int], r":py:data:`~typing.NotRequired`\ \[:py:class:`int`]", id="NotRequired"),
]


@mark.parametrize(("annotation", "expected"), _CASES)
def test_format_annotation(config: Config, annotation: Annotation, expected: str) -> None:
    assert format_annotation(annotation, config) == expected


@mark.parametrize(("annotation", "expected"), _CASES)
def test_format_annotation_fully_qualified(make_config: MakeConfig, annotation: Annotation, expected: str) -> None:
    assert format_annotation(annotation, make_config(typehints_fully_qualified=True)) == expected.replace("~", "")


@mark.skipif(version_info >= (3, 14), reason="Union renders with bars from Python 3.14")
@mark.parametrize(("fully_qualified", "prefix"), [param(False, "~", id="short"), param(True, "", id="qualified")])
def test_format_annotation_unsimplified_optional_union(
    make_config: MakeConfig, fully_qualified: bool, prefix: str
) -> None:  # pragma: <3.14 cover
    config = make_config(simplify_optional_unions=False, typehints_fully_qualified=fully_qualified)
    assert format_annotation(typing.Union[int, str, None], config) == (
        rf":py:data:`{prefix}typing.Optional`\ \[:py:data:`{prefix}typing.Union`\ \[:py:class:`int`, :py:class:`str`]]"
    )


@mark.parametrize(
    ("annotation", "expected"),
    [
        param(int | float, ":py:class:`int` | :py:class:`float`", id="bars"),
        param(int | float | None, ":py:class:`int` | :py:class:`float` | :py:obj:`None`", id="bars-None"),
        param(typing.Union[int, float], ":py:class:`int` | :py:class:`float`", id="Union"),
        param(typing.Union[int, float, None], ":py:class:`int` | :py:class:`float` | :py:obj:`None`", id="Union-None"),
        param(typing.Optional[int | float], ":py:class:`int` | :py:class:`float` | :py:obj:`None`", id="Optional-bars"),
        param(
            typing.Optional[typing.Union[int, float]],
            ":py:class:`int` | :py:class:`float` | :py:obj:`None`",
            id="Optional-Union",
        ),
        param(
            typing.Union[int | float, str], ":py:class:`int` | :py:class:`float` | :py:class:`str`", id="Union-of-bars"
        ),
        param(
            typing.Union[int, float] | str, ":py:class:`int` | :py:class:`float` | :py:class:`str`", id="bars-of-Union"
        ),
    ],
)
def test_format_annotation_always_use_bars_union(
    make_config: MakeConfig, annotation: Annotation, expected: str
) -> None:
    assert format_annotation(annotation, make_config(always_use_bars_union=True)) == expected


@mark.parametrize("library", [param(typing, id="typing"), param(typing_extensions, id="typing_extensions")])
@mark.parametrize(
    ("name", "params", "expected"),
    [
        param("ClassVar", int, r":py:data:`~typing.ClassVar`\ \[:py:class:`int`]", id="ClassVar"),
        param("NoReturn", None, ":py:data:`~typing.NoReturn`", id="NoReturn"),
        param("Literal", None, ":py:data:`~typing.Literal`", id="Literal-bare"),
        param("Literal", ("a", 1), r":py:data:`~typing.Literal`\ \[``'a'``, ``1``]", id="Literal"),
        param(
            "Literal",
            (SomeEnum.VALUE,),
            rf":py:data:`~typing.Literal`\ \[:{ENUM_MEMBER_ROLE}:`SomeEnum.VALUE <{__name__}.SomeEnum.VALUE>`]",
            id="Literal-enum",
        ),
        param(
            "Literal",
            (None, True, False, b"raw"),
            r":py:data:`~typing.Literal`\ \[:py:obj:`None`, :py:data:`True`, :py:data:`False`, ``b'raw'``]",
            id="Literal-constants",
        ),
        param("Self", None, ":py:data:`~typing.Self`", id="Self"),
        param("Never", None, ":py:data:`~typing.Never`", id="Never"),
        param("LiteralString", None, ":py:data:`~typing.LiteralString`", id="LiteralString"),
        param("TypeAlias", None, ":py:data:`~typing.TypeAlias`", id="TypeAlias"),
        param("Final", int, r":py:data:`~typing.Final`\ \[:py:class:`int`]", id="Final"),
        param("ReadOnly", int, r":py:data:`~typing.ReadOnly`\ \[:py:class:`int`]", id="ReadOnly"),
        param("TypeGuard", int, r":py:data:`~typing.TypeGuard`\ \[:py:class:`int`]", id="TypeGuard"),
        param("TypeIs", int, r":py:data:`~typing.TypeIs`\ \[:py:class:`int`]", id="TypeIs"),
        param("TypeForm", int, r":py:data:`~typing.TypeForm`\ \[:py:class:`int`]", id="TypeForm"),
        param("Doc", None, ":py:class:`~typing.Doc`", id="Doc"),
        param("TypedDict", None, ":py:class:`~typing.TypedDict`", id="TypedDict"),
        param(
            "Unpack", tuple[int], r":py:data:`~typing.Unpack`\ \[:py:class:`tuple`\ \[:py:class:`int`]]", id="Unpack"
        ),
        param(
            "Concatenate",
            (int, ...),
            r":py:data:`~typing.Concatenate`\ \[:py:class:`int`, :py:data:`...<Ellipsis>`]",
            id="Concatenate",
        ),
        param("Type", None, ":py:class:`~typing.Type`", id="Type"),
        param("Type", (Plain,), rf":py:class:`~typing.Type`\ \[:py:class:`~{__name__}.Plain`]", id="Type-Plain"),
    ],
)
def test_format_annotation_both_libs(
    config: Config, library: ModuleType, name: str, params: Annotation, expected: str
) -> None:
    if (form := getattr(library, name, None)) is None:  # pragma: no cover -- typing gained some of these after 3.12
        skip(f"{name} not available in the {library.__name__} module")
    if library is typing_extensions and not hasattr(typing, name):
        # the docs list a name under typing_extensions while typing on this Python lacks it
        expected = expected.replace("~typing.", "~typing_extensions.")
    assert format_annotation(form if params is None else form[params], config) == expected


@mark.parametrize(
    ("form", "expected"),
    [
        param(typing.NewType, ":py:class:`~typing.NewType`", id="NewType"),
        param(typing.Annotated, ":py:data:`~typing.Annotated`", id="Annotated"),
    ],
)
@mark.parametrize("signature", [param(False, id="field"), param(True, id="signature")])
def test_format_annotation_of_a_bare_form_names_it(
    config: Config, form: Annotation, expected: str, *, signature: bool
) -> None:
    with annotation_state(config, signature=signature):
        assert format_annotation(form, config) == expected


def test_format_annotation_role_matches_python_inventory(config: Config, inv: Inventory) -> None:
    # CPython moving a typing/types object between py:class and py:data would leave our reference unresolved
    not_rendered_as_itself = {
        *("types.BuiltinFunctionType", "types.LambdaType", "typing.Text"),  # aliases render as their target
        *("types.NoneType", "types.UnionType", "typing.ForwardRef"),  # rendered as None, Union, annotationlib
        *("typing.NoDefault", "typing.NoExtraItems", "typing.TYPE_CHECKING"),  # values, not annotations
    }
    with catch_warnings(action="ignore", category=DeprecationWarning):  # typing.ByteString on 3.15+
        assert {
            entry.name: rendered
            for entry in inv.objects
            if entry.domain == "py"
            and entry.role in {"class", "data"}
            and entry.name.rpartition(".")[0] in {"typing", "types"}
            and entry.name not in not_rendered_as_itself
            and not (
                rendered := format_annotation(
                    locate(entry.name),  # ty: ignore[invalid-argument-type]  # locate returns object
                    config,
                )
            ).startswith(f":py:{entry.role}:`~{entry.name}`")
        } == {}


@mark.parametrize(
    ("subscript", "expected"),
    [
        param(lambda sub: sub.Thing[int], r"\[:py:class:`int`]", id="builtin"),
        param(lambda sub: sub.Thing[sub.Other], r"\[:py:class:`~mockedpkg.sub.Other`]", id="mocked"),
        param(lambda sub: sub.Thing[int, str], r"\[:py:class:`int`, :py:class:`str`]", id="several"),
        param(lambda sub: sub.Thing[typing.Literal["a"]], r"\[:py:class:`~typing.Literal`\ \[``'a'``]]", id="literal"),
        param(
            lambda sub: sub.Thing[str, dict[str, typing.Any]],
            r"\[:py:class:`str`, :py:class:`dict`\ \[:py:class:`str`, :py:class:`~typing.Any`]]",
            id="nested",
        ),
        param(
            lambda sub: sub.Thing[typing.Callable[[int], str]],
            r"\[:py:class:`~typing.Callable`\ \[\[:py:class:`int`], :py:class:`str`]]",
            id="nested-list",
        ),
        param(lambda sub: sub.Thing["x y"], r"\[``x y``]", id="not-a-name"),
    ],
)
def test_format_annotation_mocked_subscript(
    config: Config, mocked_module: ModuleType, subscript: Callable[[ModuleType], Annotation], expected: str
) -> None:
    assert format_annotation(subscript(mocked_module), config) == rf":py:class:`~mockedpkg.sub.Thing`\ {expected}"


@mark.parametrize(
    ("annotation", "formatter", "expected"),
    [
        param(int, lambda hint, _config: f"Custom({hint.__name__})", "Custom(int)", id="formats"),
        param(int, lambda _annotation, _config: None, ":py:class:`int`", id="defers"),
        param(
            WrittenTypeAlias("Count", int),
            lambda hint, _config: f"Custom({hint.__name__})",
            "Custom(int)",
            id="sees-the-value-of-a-written-alias",
        ),
    ],
)
def test_format_annotation_formatter(
    make_config: MakeConfig,
    annotation: Annotation | WrittenTypeAlias,
    formatter: TypehintsFormatter,
    expected: str,
) -> None:
    assert format_annotation(annotation, make_config(typehints_formatter=formatter)) == expected


@mark.parametrize(
    ("annotation", "overrides", "expected"),
    [
        param(Literal["a", "b"], {}, "``'a'`` | ``'b'``", id="values"),
        param(Literal, {}, ":py:data:`~typing.Literal`", id="bare"),
        param(Literal["`"], {}, r":literal:`\'\`\'`", id="backtick"),
        param(Literal[True], {}, ":py:data:`True`", id="constant"),
        param(
            Literal[OtherEnum.VALUE],
            {"typehints_fully_qualified": True},
            f":{ENUM_MEMBER_ROLE}:`{__name__}.OtherEnum.VALUE`",
            id="enum-member-fully-qualified",
        ),
        param(
            Literal[SomeEnum.VALUE],
            {"typehints_fixup_module_name": lambda module: "" if module == __name__ else module},
            f":{ENUM_MEMBER_ROLE}:`SomeEnum.VALUE`",
            id="enum-member-without-module",
        ),
    ],
)
def test_format_annotation_short_literals(
    make_config: MakeConfig,
    annotation: Annotation,
    overrides: dict[str, bool | Callable[[str], str]],
    expected: str,
) -> None:
    assert format_annotation(annotation, make_config(**overrides), short_literals=True) == expected


@mark.parametrize(
    ("make_union", "expected"),
    [
        param(lambda alias: alias | None, "Json | :py:obj:`None`", id="alias-or-None"),
        param(lambda alias: None | alias, ":py:obj:`None` | Json", id="None-or-alias"),
        param(lambda alias: int | alias, ":py:class:`int` | Json", id="type-or-alias"),
        param(lambda alias: alias | alias, "Json", id="same-alias-twice"),
    ],
)
def test_format_annotation_alias_union_keeps_its_bars(
    config: Config, make_union: Callable[[MyTypeAliasForwardRef], Annotation], expected: str
) -> None:
    assert format_annotation(make_union(MyTypeAliasForwardRef("Json")), config) == expected


def test_format_annotation_alias_union_leaves_optional_alone(config: Config) -> None:
    alias = MyTypeAliasForwardRef("Json")
    # the | form renders first, and the Union typing caches for both must not keep its mark
    format_annotation(alias | None, config)
    optional_alias = typing.Optional[alias]  # ty: ignore[invalid-type-form]  # the cached Optional is under test
    assert format_annotation(optional_alias, config) == (
        "Json | :py:obj:`None`" if version_info >= (3, 14) else r":py:data:`~typing.Optional`\ \[Json]"
    )


@mark.parametrize(
    ("annotation", "overrides", "expected"),
    [
        param(TypeAliasForwardRef("SomeAlias"), {}, "SomeAlias", id="name"),
        param(MyTypeAliasForwardRef("EncoderHook"), {}, "EncoderHook", id="plain-name"),
        param(MyTypeAliasForwardRef("Json", configured=True), {}, "Json", id="configured-without-env"),
        param(MyTypeAliasForwardRef("EncoderHook", crossref=True), {}, ":py:type:`~EncoderHook`", id="crossref"),
        param(
            MyTypeAliasForwardRef("EncoderHook", crossref=True),
            {"typehints_fully_qualified": True},
            ":py:type:`EncoderHook`",
            id="crossref-fully-qualified",
        ),
    ],
)
def test_format_annotation_forward_alias(
    make_config: MakeConfig, annotation: TypeAliasForwardRef, overrides: dict[str, bool], expected: str
) -> None:
    assert format_annotation(annotation, make_config(**overrides)) == expected


@mark.sphinx("text", testroot="render-types")
def test_format_annotation_forward_alias_documented_so_far(app: SphinxTestApp, build_text: BuildText) -> None:
    build_text(".. py:type:: mymod.SomeAlias")
    with annotation_state(app.config, env=app.env, module_prefix="mymod"):
        assert format_annotation(TypeAliasForwardRef("SomeAlias"), app.config) == ":py:type:`~mymod.SomeAlias`"


@mark.sphinx("text", testroot="dummy")
def test_format_annotation_type_variable_parameter_follows_its_equals_sign(build_text: BuildText) -> None:
    assert build_text(".. autofunction:: dummy_module.bounded") == (
        dedent("""\
            dummy_module.bounded(value)

               Take a bounded type parameter.

               Parameters:
                  **value** ("TypeVar"("Bounded", bound="int")) -- the value

               Return type:
                  "TypeVar"("Bounded", bound="int")
        """)
    )


@mark.parametrize(
    ("rst", "header"),
    [
        param(
            dedent("""\
                .. autofunction:: mod_eager.count_eager

                .. py:type:: mod_eager.Count
            """),
            "mod_eager.count_eager(amount: int, limit: int)",
            id="documented-after-its-use-shows-its-value",
        ),
        param(
            dedent("""\
                .. py:type:: mod_eager.UserId

                .. py:type:: mod_eager.Count

                .. automethod:: mod_eager.Users.get
            """),
            "Users.get(user_id: UserId)",
            id="method-signature",
        ),
        param(
            dedent("""\
                .. py:type:: mod_eager.UserId

                .. py:type:: mod_eager.Count

                .. autoproperty:: mod_eager.Users.size
            """),
            "property Users.size: Count",
            id="property-header",
        ),
    ],
)
@mark.sphinx("text", testroot="integration", confoverrides={"typehints_use_signature": True})
def test_format_annotation_module_alias_in_a_signature(build_text: BuildText, rst: str, header: str) -> None:
    assert header in build_text(rst).splitlines()


@mark.parametrize(
    ("rst", "href"),
    [
        param(
            dedent("""\
                .. autoclass:: local_widget.Widget

                .. autofunction:: local_widget.use
            """),
            "#local_widget.Widget",
            id="documented-locally",
        ),
        param(".. autofunction:: local_widget.use", "https://example.org/remote/api.html#remote.Widget", id="remote"),
    ],
)
@mark.sphinx("html", testroot="intersphinx-local-target")
def test_format_annotation_mapped_type_prefers_the_local_target(build_text: BuildText, rst: str, href: str) -> None:
    assert set(findall(r'href="([^"]*Widget)"', build_text(rst))) == {href}


def _int_as_count(annotation: Annotation, _config: Config) -> str | None:
    return ":class:`Count`" if annotation is int else None


def _everything_as_test(_annotation: Annotation, _config: Config) -> str:
    return "Test"


@mark.parametrize(
    ("value", "label"),
    [
        param(
            '"Count"',
            '"str"',
            marks=mark.sphinx(confoverrides={"typehints_formatter": _int_as_count}),
            id="formats-some",
        ),
        param(
            "Test",
            "Test",
            marks=mark.sphinx(confoverrides={"typehints_formatter": _everything_as_test}),
            id="formats-every-type",
        ),
    ],
)
@mark.sphinx("text", testroot="public-api")
def test_format_annotation_formatter_replaces_the_types_it_formats_in_a_build(
    build_text: BuildText, value: str, label: str
) -> None:
    assert build_text(".. autofunction:: public_module.count") == dedent(f"""\
        public_module.count(value, label)

           Count.

           Parameters:
              * **value** ({value}) -- the value

              * **label** ({label}) -- the label

           Return type:
              {value}
        """)
