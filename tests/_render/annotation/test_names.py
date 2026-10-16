from __future__ import annotations

from collections.abc import Callable
from dataclasses import InitVar
from importlib.machinery import ModuleSpec
from re import Match, Pattern, findall
from textwrap import dedent
from types import CodeType, CoroutineType, FunctionType, ModuleType
from typing import (  # ruff:ignore[deprecated-import]  # the legacy aliases are under test
    IO,
    TYPE_CHECKING,
    Any,
    AnyStr,
    ClassVar,
    Dict,
    Final,
    Generic,
    Literal,
    NewType,
    Protocol,
    Tuple,
    TypeVar,
    Union,
)

from pytest import mark, param, raises
from typing_extensions import ParamSpec

from sphinx_autodoc_typehints._render import fixup_module_name
from sphinx_autodoc_typehints._render.annotation.names import (
    get_annotation_args,
    get_annotation_class_name,
    get_annotation_module,
)

if TYPE_CHECKING:
    from io import StringIO

    from conftest import BuildText

    from _render.conftest import MakeConfig
    from sphinx_autodoc_typehints._types import Hint, RenderNode


Item = TypeVar("Item")
UserName = NewType("UserName", str)
Params = ParamSpec("Params")


class Plain:
    class Inner: ...


class Box[Content]: ...


class StrBox(Box[str]): ...


class Proto(Protocol): ...


class GenericProto[Element](Protocol): ...


class Slotted:
    __slots__ = ()


class Metaclass(type): ...


# an instance has no __qualname__ of its own, so only the _name a third-party alias keeps names it
class Aliased:
    _name = "Alias"


# no typing object of a supported Python declares its name on its origin alone, a third-party alias may
class PlainOrigin:
    __origin__ = Plain


class AliasedOrigin:
    __origin__ = Aliased()


_NAMES: Final[list[tuple[str, object, str, str, tuple[object, ...]]]] = [
    ("str", str, "builtins", "str", ()),
    ("None", None, "builtins", "None", ()),
    ("ModuleType", ModuleType, "types", "ModuleType", ()),
    ("FunctionType", FunctionType, "types", "FunctionType", ()),
    ("CodeType", CodeType, "types", "CodeType", ()),
    ("CoroutineType", CoroutineType, "types", "CoroutineType", ()),
    ("Any", Any, "typing", "Any", ()),
    ("AnyStr", AnyStr, "typing", "AnyStr", ()),
    ("Dict", Dict, "typing", "Dict", ()),
    ("Dict-str-int", Dict[str, int], "typing", "Dict", (str, int)),
    ("Dict-TypeVar-int", Dict[Item, int], "typing", "Dict", (Item, int)),
    ("Tuple", Tuple, "typing", "Tuple", ()),
    ("Tuple-str-int", Tuple[str, int], "typing", "Tuple", (str, int)),
    ("Union", Union[str, int], "typing", "Union", (str, int)),
    ("ClassVar", ClassVar[int], "typing", "ClassVar", (int,)),
    ("Literal", Literal["a", 1], "typing", "Literal", ("a", 1)),
    ("Generic", Generic[Item], "typing", "Generic", (Item,)),
    ("Callable", Callable, "collections.abc", "Callable", ()),
    ("Callable-Ellipsis", Callable[..., str], "collections.abc", "Callable", (..., str)),
    ("Callable-int-str", Callable[[int, str], str], "collections.abc", "Callable", (int, str, str)),
    ("Pattern", Pattern, "re", "Pattern", ()),
    ("Pattern-str", Pattern[str], "re", "Pattern", (str,)),
    ("Match", Match, "re", "Match", ()),
    ("Match-str", Match[str], "re", "Match", (str,)),
    ("IO", IO, "typing", "IO", ()),
    ("NewType", UserName, "typing", "NewType", (str,)),
    ("InitVar", InitVar[str], "dataclasses", "InitVar", (str,)),
    ("ParamSpec", Params, "typing", "ParamSpec", ()),
    ("ParamSpec-args", Params.args, "typing", "ParamSpecArgs", ()),
    ("ParamSpec-kwargs", Params.kwargs, "typing", "ParamSpecKwargs", ()),
    ("Metaclass", Metaclass, __name__, "Metaclass", ()),
    ("Slotted", Slotted, __name__, "Slotted", ()),
    ("Plain", Plain, __name__, "Plain", ()),
    ("Box", Box, __name__, "Box", ()),
    ("StrBox", StrBox, __name__, "StrBox", ()),
    ("Proto", Proto, __name__, "Proto", ()),
    ("GenericProto", GenericProto, __name__, "GenericProto", ()),
    ("GenericProto-int", GenericProto[int], __name__, "GenericProto", (int,)),
    ("Inner", Plain.Inner, __name__, "Plain.Inner", ()),
]


@mark.parametrize(
    ("annotation", "module"), [param(annotation, module, id=name) for name, annotation, module, _, _ in _NAMES]
)
def test_get_annotation_module(annotation: Hint | NewType | None, module: str) -> None:
    assert get_annotation_module(annotation) == module


@mark.parametrize(
    ("annotation", "module", "class_name"),
    [
        *(param(annotation, module, class_name, id=name) for name, annotation, module, class_name, _ in _NAMES),
        param(Aliased(), "mod", "Alias", id="own-alias-name"),
        param(ModuleSpec("Alias", None), "typing", "Alias", id="typing-name"),
        param(ModuleSpec("Alias", None), "mod", "ModuleSpec", id="name-outside-typing"),
        param(PlainOrigin(), "mod", "Plain", id="origin-qualname"),
        param(AliasedOrigin(), "mod", "Alias", id="origin-alias-name"),
        param(Plain(), "mod", "Plain", id="undeclared"),
    ],
)
def test_get_annotation_class_name(annotation: Hint | NewType | None, module: str, class_name: str) -> None:
    assert get_annotation_class_name(annotation, module) == class_name


@mark.parametrize(
    ("annotation", "module", "class_name", "args"),
    [param(*arguments, id=name) for name, *arguments in _NAMES],
)
def test_get_annotation_args(
    annotation: Hint | NewType | None, module: str, class_name: str, args: tuple[RenderNode, ...]
) -> None:
    assert get_annotation_args(annotation, module, class_name) == args


def test_get_annotation_module_raises_on_unknown() -> None:
    with raises(ValueError, match="Cannot determine the module of Undefined"):
        get_annotation_module("Undefined")


@mark.parametrize(
    ("overrides", "module", "expected"),
    [
        param({}, "pathlib", "pathlib", id="kept"),
        param({}, "_io", "io", id="io"),
        param(
            {"typehints_fixup_module_name": lambda module_name: f"docs.{module_name}"}, "pkg", "docs.pkg", id="fixup"
        ),
        param({"typehints_fixup_module_name": lambda module_name: f"_{module_name}"}, "io", "io", id="fixup-to-io"),
    ],
)
def test_fixup_module_name(
    make_config: MakeConfig, overrides: dict[str, Callable[[str], str]], module: str, expected: str
) -> None:
    assert fixup_module_name(make_config(**overrides), module) == expected


@mark.parametrize(
    "role",
    [
        param(
            role,
            id=role,
            marks=mark.sphinx(
                "html",
                testroot="intersphinx-role",
                confoverrides={"intersphinx_mapping": {"py": (f"https://example.org/{role}/", f"{role}.inv")}},
            ),
        )
        for role in ("class", "data")
    ],
)
def test_inventory_role_follows_the_inventory(build_text: BuildText, role: str) -> None:
    assert set(findall(r'href="([^"]*FunctionType)"', build_text(".. autofunction:: role_module.call"))) == {
        f"https://example.org/{role}/library/types.html#types.FunctionType"
    }


def _fixup_wrong_module_path(module: str) -> str:
    return module.replace("wrong_module_path", "export_module")


@mark.sphinx(
    "text",
    testroot="dummy",
    confoverrides={"typehints_fixup_module_name": _fixup_wrong_module_path, "nitpicky": True},
)
def test_fixup_module_name_links_the_path_the_docs_document(build_text: BuildText, warning: StringIO) -> None:
    assert (
        build_text(
            dedent("""\
                .. class:: export_module.A

                .. autofunction:: export_module.f
            """)
        ),
        warning.getvalue(),
    ) == (
        dedent("""\
            class export_module.A

            export_module.f()

               Return type:
                  "A"
        """),
        "",
    )
