from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Final, Protocol

from pytest import MonkeyPatch, fixture, mark, param

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.testing.util import SphinxTestApp

_EXTENSION_DIR: Final[Path] = Path(__file__).parents[1] / "docs" / "_ext"


class Render(Protocol):
    def __call__(self, index: str, builder: str = "text") -> str: ...


@fixture(name="render")
def render_fixture(tmp_path: Path, monkeypatch: MonkeyPatch, make_app: Callable[..., SphinxTestApp]) -> Render:
    monkeypatch.syspath_prepend(_EXTENSION_DIR)
    # conftest removes a temporary directory holding a _build, and fails on the symlink pytest makes to the latest one
    (project := tmp_path / "project").mkdir()
    (project / "conf.py").write_text('extensions = ["option_reference", "sphinx_autodoc_typehints"]\n')

    def render(index: str, builder: str = "text") -> str:
        (project / "index.rst").write_text(index)
        app = make_app(builder, srcdir=project)
        app.build()
        return (Path(app.outdir) / f"index.{'txt' if builder == 'text' else builder}").read_text()

    return render


@mark.parametrize(
    ("name", "rendered"),
    [
        param(
            "typehints_formatter",
            '"Callable"[[annotation, "Config"], "str" | "None"]',
            id="callable with its signature",
        ),
        param("typehints_use_rtype", '"bool"', id="bool"),
    ],
)
def test_option_reference_renders_the_type(name: str, rendered: str, render: Render) -> None:
    assert f"Type:\n      {rendered}" in render(f".. confval:: {name}\n")


def test_option_reference_adds_the_rebuild_field(render: Render) -> None:
    text = render(
        dedent("""\
            .. confval:: typehints_use_rtype
                :default: ``True``
                :rebuild: ``env``
        """)
    )

    assert 'Default:\n      "True"\n\n   Rebuild:\n      "env"\n' in text
