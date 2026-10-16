from __future__ import annotations

from collections import Counter
from pathlib import Path
from re import findall
from textwrap import dedent
from typing import TYPE_CHECKING, Final
from zlib import compress

from pytest import MonkeyPatch, fixture, mark, param

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.testing.util import SphinxTestApp

_EXTENSION_DIR: Final[Path] = Path(__file__).parents[1] / "docs" / "_ext"
_EXAMPLE: Final[str] = dedent('''\
    .. live-example::

        # show the default next to the type
        typehints_defaults = "comma"
        ---
        def scale(value: float, factor: int = 2) -> float:
            """
            Scale a value.

            :param value: the value
            :param factor: the factor
            """
            return value * factor
''')
# Sphinx alone can't resolve a name imported under TYPE_CHECKING, so nitpicky mode fails its build
_GUARDED: Final[str] = dedent('''\
    .. live-example::

        nitpicky = True
        ---
        from __future__ import annotations

        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from decimal import Decimal


        def total(price: Decimal) -> None:
            """
            Add the price.

            :param price: the price
            """
''')
_INVENTORY: Final[bytes] = (
    b"# Sphinx inventory version 2\n# Project: Python\n# Version: 3\n"
    b"# The remainder of this file is compressed using zlib.\n"
    + compress(b"decimal.Decimal py:class 1 library/decimal.html#$ -\nNone py:data 1 library/constants.html#$ -\n")
)

type Build = Callable[[str], SphinxTestApp]


@fixture(name="project")
def project_fixture(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    monkeypatch.syspath_prepend(_EXTENSION_DIR)
    # conftest removes a temporary directory holding a _build, and fails on the symlink pytest makes to the latest one
    (project := tmp_path / "project").mkdir()
    (project / "conf.py").write_text('extensions = ["live_example"]\n')
    return project


@fixture(name="build")
def build_fixture(project: Path, make_app: Callable[..., SphinxTestApp]) -> Build:
    def build(index: str) -> SphinxTestApp:
        (project / "index.rst").write_text(f"Example\n=======\n\n{index}")
        app = make_app("html", srcdir=project, freshenv=True)
        app.build()
        return app

    return build


@fixture(name="build_linked")
def build_linked_fixture(project: Path, build: Build) -> Build:
    (project / "python.inv").write_bytes(_INVENTORY)
    (project / "conf.py").write_text(
        dedent("""\
            extensions = ["live_example", "sphinx.ext.intersphinx"]
            intersphinx_mapping = {"python": ("https://docs.python.org/3", "python.inv")}
        """)
    )
    return build


def _tab(app: SphinxTestApp, label: str) -> str:
    page = (Path(app.outdir) / "index.html").read_text()
    return page.split(f"\n{label}</label>", 1)[1].split("</label>", 1)[0]


@mark.parametrize(
    "fragment",
    [
        param('typehints_defaults</span> <span class="o">=</span>', id="conf"),
        param('<span class="k">def</span><span class="w"> </span><span class="nf">scale</span>', id="source"),
        param('</span>, default: <span class="highlight sphinx_autodoc_typehints-value"><code', id="rendered default"),
        param('<span class="sphinx_autodoc_typehints-type">', id="rendered type"),
    ],
)
def test_live_example_shows(fragment: str, build: Build) -> None:
    app = build(_EXAMPLE)

    assert fragment in (Path(app.outdir) / "index.html").read_text()


def test_live_example_tab_order(build: Build) -> None:
    app = build(_EXAMPLE)

    labels = findall(
        r'<label class="sd-tab-label"[^>]*>\s*([^<]+?)\s*</label>', (Path(app.outdir) / "index.html").read_text()
    )

    assert labels == ["conf.py", "mod.py", "sphinx-autodoc-typehints", "Sphinx built-in"]


def test_live_example_builtin_tab_renders_without_the_extension(build: Build) -> None:
    app = build(_EXAMPLE)

    builtin = _tab(app, "Sphinx built-in")

    assert "scale" in builtin
    assert "sphinx_autodoc_typehints-type" not in builtin


def test_live_example_links_through_the_parent_inventory(build_linked: Build) -> None:
    app = build_linked(_GUARDED)

    assert 'href="https://docs.python.org/3/library/decimal.html#decimal.Decimal"' in _tab(
        app, "sphinx-autodoc-typehints"
    )


def test_live_example_shows_why_the_builtin_build_fails(build_linked: Build) -> None:
    app = build_linked(_GUARDED)

    assert "py:class reference target not found: Decimal" in _tab(app, "Sphinx built-in")
    assert "ERROR" not in app.warning.getvalue()


def test_live_example_keeps_anchors_unique(build: Build) -> None:
    app = build(f"{_EXAMPLE}\n{_EXAMPLE.replace('comma', 'braces')}")

    ids = Counter(findall(r'\bid="([^"]+)"', (Path(app.outdir) / "index.html").read_text()))

    assert [anchor for anchor, count in ids.items() if count > 1] == []


def test_live_example_reuses_the_cached_render(build: Build, monkeypatch: MonkeyPatch) -> None:
    build(_EXAMPLE)
    # an interpreter that cannot start fails any nested build, so only the cache can render the second one
    monkeypatch.setenv("PYTHONHOME", "/nonexistent")

    app = build(_EXAMPLE)

    assert "ERROR" not in app.warning.getvalue()


def test_live_example_reports_a_failing_build(build: Build) -> None:
    app = build(_EXAMPLE.replace("    def scale", "    raise RuntimeError('broken module')\n    def scale"))

    assert "the example fails to build:" in app.warning.getvalue()


def test_live_example_requires_the_separator(build: Build) -> None:
    app = build(_EXAMPLE.replace("    ---\n", ""))

    assert "separate the conf.py lines from the module source with a '---' line" in app.warning.getvalue()
