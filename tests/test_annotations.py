from __future__ import annotations

import enum
import re
import sys
import types
import typing
from collections.abc import Callable, Mapping
from io import StringIO
from types import EllipsisType, FrameType, FunctionType, ModuleType, NotImplementedType, TracebackType
from typing import (  # noqa: UP035
    IO,
    TYPE_CHECKING,
    Annotated,
    Any,
    AnyStr,
    Dict,
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
    TypeVar,
    Union,
)
from unittest.mock import create_autospec

import pytest
import typing_extensions
from sphinx.config import Config

from sphinx_autodoc_typehints import (
    format_annotation,
    get_annotation_args,
    get_annotation_class_name,
    get_annotation_module,
)

if TYPE_CHECKING:
    from sphobjinv import Inventory

T = TypeVar("T")
U_co = TypeVar("U_co", covariant=True)
V_contra = TypeVar("V_contra", contravariant=True)
X = TypeVar("X", str, int)
Y = TypeVar("Y", bound=str)
Z = TypeVar("Z", bound="A")
S = TypeVar("S", bound="miss")  # type: ignore[name-defined] # miss not defined on purpose # noqa: F821
W = NewType("W", str)


class SomeEnum(enum.Enum):
    VALUE = "val"


P = typing_extensions.ParamSpec("P")
P_args = P.args
P_kwargs = P.kwargs
P_co = typing_extensions.ParamSpec("P_co", covariant=True)  # ty: ignore[invalid-paramspec]
P_contra = typing_extensions.ParamSpec("P_contra", contravariant=True)  # ty: ignore[invalid-paramspec]
P_bound = typing_extensions.ParamSpec("P_bound", bound=str)  # ty: ignore[invalid-paramspec]
RecList = Union[int, List["RecList"]]
MutualRecA = Union[bool, List["MutualRecB"]]
MutualRecB = Union[str, List["MutualRecA"]]


class A:
    def get_type(self) -> type:
        return type(self)  # pragma: no cover

    class Inner: ...


class B[T]:
    name = "Foo"


class C(B[str]): ...


class D(typing_extensions.Protocol): ...


class E(typing_extensions.Protocol[T]): ...


class Slotted:
    __slots__ = ()


class Metaclass(type): ...


PY312_PLUS = sys.version_info >= (3, 12)


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
    pytest.param(EllipsisType, ":py:data:`~types.EllipsisType`", id="EllipsisType"),
    pytest.param(FunctionType, ":py:data:`~types.FunctionType`", id="FunctionType"),
    pytest.param(FrameType, ":py:data:`~types.FrameType`", id="FrameType"),
    pytest.param(ModuleType, ":py:class:`~types.ModuleType`", id="ModuleType"),
    pytest.param(NotImplementedType, ":py:data:`~types.NotImplementedType`", id="NotImplementedType"),
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
        "``V_contra``, contravariant=True)]",
        id="Mapping-T-int-contra",
    ),
    pytest.param(
        Mapping[T, U_co],
        r":py:class:`~collections.abc.Mapping`\ \[:py:class:`~typing.TypeVar`\ \(``T``), "
        r":py:class:`~typing.TypeVar`\ \(``U_co``, covariant=True)]",
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
        r"contravariant=True)]",
        id="Dict-T-int-contra",
    ),
    pytest.param(
        Dict[T, U_co],
        r":py:class:`~typing.Dict`\ \[:py:class:`~typing.TypeVar`\ \(``T``),"
        r" :py:class:`~typing.TypeVar`\ \(``U_co``, covariant=True)]",
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
    pytest.param(T, r":py:class:`~typing.TypeVar`\ \(``T``)", id="T"),
    pytest.param(U_co, r":py:class:`~typing.TypeVar`\ \(``U_co``, covariant=True)", id="U-co"),
    pytest.param(V_contra, r":py:class:`~typing.TypeVar`\ \(``V_contra``, contravariant=True)", id="V-contra"),
    pytest.param(X, r":py:class:`~typing.TypeVar`\ \(``X``, :py:class:`str`, :py:class:`int`)", id="X"),
    pytest.param(Y, r":py:class:`~typing.TypeVar`\ \(``Y``, bound= :py:class:`str`)", id="Y"),
    pytest.param(Z, r":py:class:`~typing.TypeVar`\ \(``Z``, bound= A)", id="Z"),
    pytest.param(S, r":py:class:`~typing.TypeVar`\ \(``S``, bound= miss)", id="S"),
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
    pytest.param(Tuple[()], ":py:data:`~typing.Tuple`", id="Tuple-p"),
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
    pytest.param(Annotated[int, "metadata"], r":py:class:`int`", id="Annotated-metadata"),
    pytest.param(Required[int], r":py:class:`~typing.Required`\ \[:py:class:`int`]", id="Required"),
    pytest.param(NotRequired[int], r":py:class:`~typing.NotRequired`\ \[:py:class:`int`]", id="NotRequired"),
]


@pytest.mark.parametrize(("annotation", "expected_result"), _CASES)
def test_format_annotation(inv: Inventory, annotation: Any, expected_result: str) -> None:
    conf = create_autospec(Config, _annotation_globals=globals(), always_use_bars_union=False)
    result = format_annotation(annotation, conf)
    assert result == expected_result

    if re.match(r"^:py:data:`~typing\.Union`\\\[.*``None``.*]", expected_result):  # pragma: <3.14 cover
        expected_result_not_simplified = expected_result.replace(", ``None``", "")
        expected_result_not_simplified += ":py:data:`~typing.Optional`\\ \\["
        expected_result_not_simplified += "]"
        conf = create_autospec(
            Config,
            simplify_optional_unions=False,
            _annotation_globals=globals(),
            always_use_bars_union=False,
        )
        assert format_annotation(annotation, conf) == expected_result_not_simplified

        if "typing" in expected_result_not_simplified:
            expected_result_not_simplified = expected_result_not_simplified.replace("~typing", "typing")
            conf = create_autospec(
                Config,
                typehints_fully_qualified=True,
                simplify_optional_unions=False,
                _annotation_globals=globals(),
            )
            assert format_annotation(annotation, conf) == expected_result_not_simplified

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
        if expected_role and expected_role == "function":  # pragma: no cover
            expected_role = "func"
        assert match.group("role") == expected_role


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
    result = format_annotation(eval(annotation), conf)  # noqa: S307
    assert result == expected_result


@pytest.mark.parametrize("library", [typing, typing_extensions], ids=["typing", "typing_extensions"])
@pytest.mark.parametrize(
    ("annotation", "params", "expected_result"),
    [
        pytest.param("ClassVar", int, ":py:data:`~typing.ClassVar`\\ \\[:py:class:`int`]", id="ClassVar"),
        pytest.param("NoReturn", None, ":py:data:`~typing.NoReturn`", id="NoReturn"),
        pytest.param("Literal", ("a", 1), ":py:data:`~typing.Literal`\\ \\[``'a'``, ``1``]", id="Literal"),
        pytest.param(
            "Literal",
            (SomeEnum.VALUE,),
            rf":py:data:`~typing.Literal`\ \[:py:attr:`~{__name__}.SomeEnum.VALUE`]",
            id="Literal-enum",
        ),
        pytest.param("Type", None, ":py:class:`~typing.Type`", id="Type-none"),
        pytest.param("Type", (A,), rf":py:class:`~typing.Type`\ \[:py:class:`~{__name__}.A`]", id="Type-A"),
    ],
)
def test_format_annotation_both_libs(library: ModuleType, annotation: str, params: Any, expected_result: str) -> None:
    try:
        annotation_cls = getattr(library, annotation)
    except AttributeError:  # pragma: no cover
        pytest.skip(f"{annotation} not available in the {library.__name__} module")

    ann = annotation_cls if params is None else annotation_cls[params]
    result = format_annotation(ann, create_autospec(Config))
    assert result == expected_result


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


def test_format_annotation_short_literals() -> None:
    conf = create_autospec(Config)
    result = format_annotation(Literal["a", "b"], conf, short_literals=True)
    assert result == "\\``'a'`` | ``'b'``"


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
