from __future__ import annotations

from ast import literal_eval
from itertools import takewhile
from pathlib import Path
from re import DOTALL, finditer, split, sub
from sys import version_info
from textwrap import dedent
from typing import TYPE_CHECKING, Final, get_args, get_type_hints

from pytest import MonkeyPatch, fixture, mark, param

from sphinx_autodoc_typehints._render import as_signature_type
from sphinx_autodoc_typehints._types import Documented
from sphinx_autodoc_typehints._warnings import warn

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.config import Config
    from sphinx.testing.util import SphinxTestApp

_README: Final[str] = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")


def _table(heading: str) -> list[list[str]]:
    lines = _README.splitlines()
    section = takewhile(lambda entry: not entry.startswith("#"), lines[lines.index(heading) + 1 :])
    rows = [line for line in section if line.startswith("|")][2:]
    return [[cell.strip().strip("`").replace("\\|", "|") for cell in split(r"(?<!\\)\|", row)[1:-1]] for row in rows]


@mark.parametrize(
    ("conf", "source", "rendered"),
    [
        param(match["conf"], match["source"], match["rendered"], id=match["id"])
        for match in finditer(
            r"<!-- example: (?P<id>[\w-]+) -->\n\n```python\n(?P<conf>.*?)```\n\n"
            r"```python\n(?P<source>.*?)```\n\n```text\n(?P<rendered>.*?)```",
            _README,
            DOTALL,
        )
    ],
)
@mark.usefixtures("fresh_mod")
def test_readme_example_renders_as_shown(
    conf: str,
    source: str,
    rendered: str,
    project: Path,
    make_app: Callable[..., SphinxTestApp],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(project)
    (project / "conf.py").write_text(
        "\n".join(['extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]', *conf.splitlines()])
    )
    (project / "mod.py").write_text(source)
    (project / "index.rst").write_text(
        dedent("""\
            Example
            =======

            .. automodule:: mod
               :members:
        """)
    )
    app = make_app("text", srcdir=project)
    app.build()

    assert rendered in (Path(app.outdir) / "index.txt").read_text()


@fixture(name="project")
def project_fixture(tmp_path: Path) -> Path:
    # conftest removes a temporary directory holding a _build, and fails on the symlink pytest makes to the latest one
    (project := tmp_path / "project").mkdir()
    return project


def test_readme_config_table_lists_the_registered_options(
    extension_config: Config, project: Path, make_app: Callable[..., SphinxTestApp]
) -> None:
    autodoc_only = make_app("text", srcdir=project, confoverrides={"extensions": ["sphinx.ext.autodoc"]}).config

    assert {row[0] for row in _table("### Configuration options")} == set(extension_config.values) - set(
        autodoc_only.values
    )


@fixture(name="extension_config")
def extension_config_fixture(project: Path, make_app: Callable[..., SphinxTestApp]) -> Config:
    (project / "conf.py").write_text('extensions = ["sphinx_autodoc_typehints"]')
    (project / "index.rst").write_text("")
    return make_app("text", srcdir=project).config


@mark.parametrize(
    ("name", "default"),
    [param(row[0], row[2], id=row[0]) for row in _table("### Configuration options")],
)
def test_readme_config_default(name: str, default: str, extension_config: Config) -> None:
    assert literal_eval(default) == extension_config[name]


@mark.parametrize(
    ("name", "rebuild"),
    [param(row[0], row[3], id=row[0]) for row in _table("### Configuration options")],
)
def test_readme_config_rebuild(name: str, rebuild: str, extension_config: Config) -> None:
    assert rebuild == extension_config.values[name].rebuild


def test_readme_warnings_table_lists_the_categories() -> None:
    assert sorted(row[0] for row in _table("### Warnings")) == sorted([
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
        for row in _table("### Typing constructs")
    ],
)
def test_readme_typing_construct_renders_as_shown(
    annotation: str, rendered: str, readme_namespace: dict[str, object], extension_config: Config
) -> None:
    hint = eval(annotation, readme_namespace)  # ruff:ignore[suspicious-eval-usage]  # an annotation the README writes

    assert sub(r"~(?:\w+\.)+", "", as_signature_type(hint, extension_config)) == rendered


@fixture(name="readme_namespace", scope="module")
def readme_namespace_fixture() -> dict[str, object]:
    block = _README.split(
        dedent("""\
            <!-- typing-namespace -->

            ```python
        """),
        1,
    )[1].split("```", 1)[0]
    namespace: dict[str, object] = {"__name__": "readme"}
    exec(block, namespace)  # ruff:ignore[exec-builtin]  # the table names what the README's own code defines
    return namespace
