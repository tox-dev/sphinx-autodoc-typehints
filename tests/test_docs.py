from __future__ import annotations

import re
import typing
from ast import literal_eval
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from re import MULTILINE, VERBOSE, escape, findall, finditer, search
from sys import version_info
from textwrap import dedent
from types import MappingProxyType, ModuleType, UnionType
from typing import TYPE_CHECKING, Final, Literal, Union, get_args, get_origin, get_type_hints

from pytest import MonkeyPatch, fixture, mark, param, raises
from sphinx.errors import ConfigError

from sphinx_autodoc_typehints._config import OPTIONS
from sphinx_autodoc_typehints._render.annotation.rendered import as_signature_type
from sphinx_autodoc_typehints._render.annotation.walker import format_annotation
from sphinx_autodoc_typehints._types import Documented
from sphinx_autodoc_typehints._warnings import warn

if TYPE_CHECKING:
    from conftest import MakeApp
    from pytest import MarkDecorator
    from sphinx.config import Config
    from sphobjinv import Inventory

_REFERENCE: Final[str] = (Path(__file__).parents[1] / "docs" / "reference.rst").read_text(encoding="utf-8")
_GALLERY: Final[str] = (Path(__file__).parents[1] / "docs" / "typing.rst").read_text(encoding="utf-8")
_OPTIONS: Final[MappingProxyType[str, dict[str, str]]] = MappingProxyType({
    match["name"]: {key: value.strip("`") for key, value in findall(r":(?P<key>\w+): (?P<value>.*)", match["options"])}
    for match in finditer(
        r"""
        ^\.\.\ confval::\ (?P<name>\w+)\n  # the directive and the option it names
        (?P<options>(?:\ +:\w+:\ .*\n)+)   # the field list of the option
        """,
        _REFERENCE,
        MULTILINE | VERBOSE,
    )
})


def _section(title: str) -> str:
    start = search(rf"^ {escape(title)}\n\*+\n", _REFERENCE, MULTILINE)
    assert start is not None
    return _REFERENCE[start.end() :].split("\n***", 1)[0]


_LIST_TABLE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^ *\* ", flags=MULTILINE)

_LIST_TABLE_PATTERN_2: Final[re.Pattern[str]] = re.compile(r"^ *-(?: |$)", flags=MULTILINE)


def _list_table(title: str) -> list[list[str]]:
    rows = _LIST_TABLE_PATTERN.split(_section(title))[2:]
    return [[cell.strip().strip("`") for cell in _LIST_TABLE_PATTERN_2.split(row)[1:]] for row in rows]


@fixture(name="project")
def project_fixture(tmp_path: Path) -> Path:
    # conftest removes a temporary directory holding a _build, and fails on the symlink pytest makes to the latest one
    (project := tmp_path / "project").mkdir()
    return project


@fixture(name="extension_config")
def extension_config_fixture(project: Path, make_app: MakeApp) -> Config:
    (project / "conf.py").write_text('extensions = ["sphinx_autodoc_typehints"]')
    (project / "index.rst").write_text("")
    return make_app("text", srcdir=project).config


def test_docs_reference_lists_the_registered_options(
    extension_config: Config, project: Path, make_app: MakeApp
) -> None:
    autodoc_only = make_app("text", srcdir=project, confoverrides={"extensions": ["sphinx.ext.autodoc"]}).config

    assert set(_OPTIONS) == set(extension_config.values) - set(autodoc_only.values)


@mark.parametrize(("name", "default"), [param(name, options["default"], id=name) for name, options in _OPTIONS.items()])
def test_docs_option_default(name: str, default: str, extension_config: Config) -> None:
    assert literal_eval(default) == extension_config[name]


@mark.parametrize(
    ("name", "rebuild"), [param(name, options.get("rebuild", ""), id=name) for name, options in _OPTIONS.items()]
)
def test_docs_option_rebuild(name: str, rebuild: str, extension_config: Config) -> None:
    assert rebuild == extension_config.values[name].rebuild


@fixture(name="option_reference")
def option_reference_fixture(monkeypatch: MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(Path(__file__).parents[1] / "docs" / "_ext")
    return import_module("option_reference")


def _admits(
    annotation: object,  # simplint: ignore[imprecise-annotation]  # reference values vary
    value: object,  # simplint: ignore[imprecise-annotation]  # reference values vary
) -> bool:
    if (origin := get_origin(annotation)) in {Union, UnionType}:
        return any(_admits(member, value) for member in get_args(annotation))
    if origin is Literal:
        return value in get_args(annotation)
    if origin is Callable:
        return callable(value)
    if origin is tuple:
        return isinstance(value, tuple) and all(_admits(get_args(annotation)[0], item) for item in value)
    return isinstance(value, annotation)  # ty: ignore[invalid-argument-type]  # what remains is a class


def test_docs_option_types_cover_the_documented_options(option_reference: ModuleType) -> None:
    assert set(option_reference.OPTION_TYPES) == set(_OPTIONS)


@mark.parametrize("name", [param(name, id=name) for name in _OPTIONS])
def test_docs_option_type_admits_the_default(name: str, option_reference: ModuleType, extension_config: Config) -> None:
    assert _admits(option_reference.documented_type(name), extension_config[name])


@mark.parametrize("name", [param(name, id=name) for name in _OPTIONS])
def test_docs_option_type_admits_the_registered_types(name: str, option_reference: ModuleType) -> None:
    registered = next(option.types for option in OPTIONS if option.name == name)

    assert all(_admits(option_reference.documented_type(name), kind()) for kind in registered)


_TEST_DOCS_OPTION_TYPE_REFERENCES_USE_PUBLIC_PYTHON_NAMES_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
            :py:(?P<role>class|data|func|obj|type):  # the role of a Python cross reference
            `(?P<target>[^`]+)`                      # its target
            """,
    flags=VERBOSE,
)


def test_docs_option_type_references_use_public_python_names(
    option_reference: ModuleType, extension_config: Config, inv: Inventory
) -> None:
    known = {(entry.role, entry.name) for entry in inv.objects if entry.domain == "py"}
    generated = {
        (role, target.rsplit("<", 1)[-1].rstrip(">").lstrip("~"))
        for name in _OPTIONS
        for role, target in _TEST_DOCS_OPTION_TYPE_REFERENCES_USE_PUBLIC_PYTHON_NAMES_PATTERN.findall(
            format_annotation(option_reference.documented_type(name), extension_config)
        )
    }

    assert generated
    assert generated - known == {("class", "sphinx.config.Config")}


@mark.usefixtures("extension_config")
def test_docs_option_type_lists_the_defaults_styles_the_extension_accepts(
    option_reference: ModuleType, project: Path, make_app: MakeApp
) -> None:
    app = make_app("text", srcdir=project, confoverrides={"typehints_defaults": "inline"})
    with raises(ConfigError) as error:
        app.build()
    accepted = literal_eval(str(error.value).split(" one of ", 1)[1].split(", not ", 1)[0])
    styles = get_args(get_args(option_reference.documented_type("typehints_defaults"))[0])

    assert {*accepted, False} == {*styles, None}


def test_docs_warnings_table_lists_the_categories() -> None:
    assert sorted(row[0] for row in _list_table("Warnings")) == sorted([
        "sphinx_autodoc_typehints",
        *(
            f"sphinx_autodoc_typehints.{subtype}"
            for subtype in get_args(get_type_hints(warn, localns={"Documented": Documented})["subtype"].__value__)
        ),
    ])


_TEST_DOCS_TYPING_CONSTRUCT_RENDERS_AS_SHOWN_PATTERN: Final[re.Pattern[str]] = re.compile(r"~(?:\w+\.)+")


_VERSION_MARKS_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
    ^(?P<less><)?                # a bound that the version has to exceed
    (?P<major>\d+)\.(?P<minor>\d+)\+?$  # the version, with an optional `+` for later releases
    """,
    VERBOSE,
)


# a version cell, as `3.13+` or `<3.14`, skips the row on the versions it does not hold on
def _version_marks(versions: str) -> list[MarkDecorator]:
    return [
        mark.skipif((version_info >= (int(found[2]), int(found[3]))) == bool(found[1]), reason=f"holds on {versions}")
        for found in _VERSION_MARKS_PATTERN.finditer(versions)
    ]


@mark.parametrize(
    ("annotation", "rendered"),
    [
        param(
            row[1],
            row[2],
            id=" ".join(filter(None, (row[1], row[3]))),
            marks=_version_marks(row[3]),
        )
        for row in _list_table("Typing constructs")
    ],
)
def test_docs_typing_construct_renders_as_shown(
    annotation: str,
    rendered: str,
    docs_namespace: dict[str, object],  # simplint: ignore[imprecise-annotation]  # the reference defines any values
    extension_config: Config,
) -> None:
    hint = eval(annotation, docs_namespace)  # ruff:ignore[suspicious-eval-usage]  # an annotation the reference writes

    assert (
        _TEST_DOCS_TYPING_CONSTRUCT_RENDERS_AS_SHOWN_PATTERN.sub("", as_signature_type(hint, extension_config))
        == rendered
    )


@fixture(name="docs_namespace", scope="module")
def docs_namespace_fixture() -> dict[
    str, object  # simplint: ignore[imprecise-annotation]  # the reference defines any values
]:
    block = _section("Typing constructs").split(".. code-block:: python\n", 1)[1].split("\n.. ", 1)[0]
    namespace: dict[str, object] = {"__name__": "reference"}  # simplint: ignore[imprecise-annotation]  # any values
    exec(dedent(block), namespace)  # ruff:ignore[exec-builtin]  # the table names what the reference's own code defines
    return namespace


_REFERENCED_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
        :(?:class|data|func|obj):`  # a cross reference to a typing name
        [^`]*?\btyping\.(\w+)>?`
        """,
    VERBOSE,
)

_LITERAL_PATTERN: Final[re.Pattern[str]] = re.compile(r"``(?:typing\.)?(\w+)``")


def test_docs_typing_gallery_names_every_public_typing_name() -> None:
    referenced = _REFERENCED_PATTERN.findall(_GALLERY)
    literal = _LITERAL_PATTERN.findall(_GALLERY)

    assert set(typing.__all__) - {*referenced, *literal} == set()


def test_docs_typing_gallery_describes_every_picked_option(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(Path(__file__).parents[1] / "docs" / "_ext")
    content = _GALLERY.split(".. live-example-picker::\n", 1)[1].split("\n\n", 2)[1]
    options = import_module("live_example_variants").parse_options(dedent(content).splitlines())

    described = import_module("live_example_selector").describe(_REFERENCE)

    assert [option.name for option in options if not described.get(option.name)] == []
