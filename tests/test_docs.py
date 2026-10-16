from __future__ import annotations

import typing
from ast import literal_eval
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from re import MULTILINE, escape, findall, finditer, search, split, sub
from sys import version_info
from textwrap import dedent
from types import ModuleType, UnionType
from typing import TYPE_CHECKING, Final, Literal, Union, get_args, get_origin, get_type_hints

from pytest import MonkeyPatch, fixture, mark, param, raises
from sphinx.errors import ConfigError

from sphinx_autodoc_typehints._config import OPTIONS
from sphinx_autodoc_typehints._render import as_signature_type
from sphinx_autodoc_typehints._types import Documented
from sphinx_autodoc_typehints._warnings import warn

if TYPE_CHECKING:
    from sphinx.config import Config
    from sphinx.testing.util import SphinxTestApp

_REFERENCE: Final[str] = (Path(__file__).parents[1] / "docs" / "reference.rst").read_text(encoding="utf-8")
_GALLERY: Final[str] = (Path(__file__).parents[1] / "docs" / "typing.rst").read_text(encoding="utf-8")
_OPTIONS: Final[dict[str, dict[str, str]]] = {
    match["name"]: {key: value.strip("`") for key, value in findall(r":(\w+): (.*)", match["options"])}
    for match in finditer(r"^\.\. confval:: (?P<name>\w+)\n(?P<options>(?: +:\w+: .*\n)+)", _REFERENCE, MULTILINE)
}


def _section(title: str) -> str:
    start = search(rf"^ {escape(title)}\n\*+\n", _REFERENCE, MULTILINE)
    assert start is not None
    return _REFERENCE[start.end() :].split("\n***", 1)[0]


def _list_table(title: str) -> list[list[str]]:
    rows = split(r"^ *\* ", _section(title), flags=MULTILINE)[2:]
    return [[cell.strip().strip("`") for cell in split(r"^ *-(?: |$)", row, flags=MULTILINE)[1:]] for row in rows]


@fixture(name="project")
def project_fixture(tmp_path: Path) -> Path:
    # conftest removes a temporary directory holding a _build, and fails on the symlink pytest makes to the latest one
    (project := tmp_path / "project").mkdir()
    return project


@fixture(name="extension_config")
def extension_config_fixture(project: Path, make_app: Callable[..., SphinxTestApp]) -> Config:
    (project / "conf.py").write_text('extensions = ["sphinx_autodoc_typehints"]')
    (project / "index.rst").write_text("")
    return make_app("text", srcdir=project).config


def test_docs_reference_lists_the_registered_options(
    extension_config: Config, project: Path, make_app: Callable[..., SphinxTestApp]
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


def _admits(annotation: object, value: object) -> bool:
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


@mark.usefixtures("extension_config")
def test_docs_option_type_lists_the_defaults_styles_the_extension_accepts(
    option_reference: ModuleType, project: Path, make_app: Callable[..., SphinxTestApp]
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


@mark.parametrize(
    ("annotation", "rendered"),
    [
        param(
            row[1],
            row[2],
            id=" ".join(filter(None, (row[1], row[3]))),
            marks=[
                mark.skipif(
                    (version_info >= (int(found[2]), int(found[3]))) == bool(found[1]), reason=f"holds on {row[3]}"
                )
                for found in finditer(r"^(<)?(\d+)\.(\d+)\+?$", row[3])
            ],
        )
        for row in _list_table("Typing constructs")
    ],
)
def test_docs_typing_construct_renders_as_shown(
    annotation: str, rendered: str, docs_namespace: dict[str, object], extension_config: Config
) -> None:
    hint = eval(annotation, docs_namespace)  # ruff:ignore[suspicious-eval-usage]  # an annotation the reference writes

    assert sub(r"~(?:\w+\.)+", "", as_signature_type(hint, extension_config)) == rendered


@fixture(name="docs_namespace", scope="module")
def docs_namespace_fixture() -> dict[str, object]:
    block = _section("Typing constructs").split(".. code-block:: python\n", 1)[1].split("\n.. ", 1)[0]
    namespace: dict[str, object] = {"__name__": "reference"}
    exec(dedent(block), namespace)  # ruff:ignore[exec-builtin]  # the table names what the reference's own code defines
    return namespace


def test_docs_typing_gallery_names_every_public_typing_name() -> None:
    referenced = findall(r":(?:class|data|func|obj):`[^`]*?\btyping\.(\w+)>?`", _GALLERY)
    literal = findall(r"``(?:typing\.)?(\w+)``", _GALLERY)

    assert set(typing.__all__) - {*referenced, *literal} == set()


def test_docs_typing_gallery_describes_every_picked_option(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(Path(__file__).parents[1] / "docs" / "_ext")
    content = _GALLERY.split(".. live-example-picker::\n", 1)[1].split("\n\n", 2)[1]
    options = import_module("live_example_variants").parse_options(dedent(content).splitlines())

    described = import_module("live_example_selector").describe(_REFERENCE)

    assert [option.name for option in options if not described.get(option.name)] == []
