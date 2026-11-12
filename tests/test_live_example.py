from __future__ import annotations

import re
from collections import Counter
from json import loads
from pathlib import Path
from re import VERBOSE
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Final, TypedDict
from zlib import compress

from pytest import MonkeyPatch, fixture, mark, param

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import MakeApp
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
    (project / "reference.rst").write_text(_REFERENCE)
    return project


@fixture(name="build")
def build_fixture(project: Path, make_app: MakeApp) -> Build:
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


_TABS_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
            <label\b[^>]*                    # attributes can precede the class
            \bclass="sd-tab-label"[^>]*>      # tab label with any later attributes
            \s*([^<]+?)\s*</label>            # displayed tab name
            """,
    VERBOSE,
)


def _tabs(app: SphinxTestApp) -> list[tuple[str, str]]:
    page = (Path(app.outdir) / "index.html").read_text()
    labels = list(_TABS_PATTERN.finditer(page))
    return [
        (match.group(1), page[match.end() : labels[index + 1].start() if index + 1 < len(labels) else len(page)])
        for index, match in enumerate(labels)
    ]


def _tab(app: SphinxTestApp, label: str) -> str:
    return next(content for name, content in _tabs(app) if name == label)


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

    labels = [name for name, _ in _tabs(app)]

    assert labels == ["conf.py", "demo.py", "sphinx-autodoc-typehints", "Sphinx built-in"]


def test_live_example_builtin_tab_renders_without_the_extension(build: Build) -> None:

    builtin = _tab(build(_EXAMPLE), "Sphinx built-in")

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


_TEST_LIVE_EXAMPLE_KEEPS_ANCHORS_UNIQUE_PATTERN: Final[re.Pattern[str]] = re.compile(r'\bid="([^"]+)"')


def test_live_example_keeps_anchors_unique(build: Build) -> None:
    app = build(f"{_EXAMPLE}\n{_EXAMPLE.replace('comma', 'braces')}")

    ids = Counter(
        _TEST_LIVE_EXAMPLE_KEEPS_ANCHORS_UNIQUE_PATTERN.findall((Path(app.outdir) / "index.html").read_text())
    )

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


_PICKED_SOURCE: Final[str] = dedent('''\
    type Size = int
    """How many times over."""


    class Box:
        """A box."""


    def scale(box: Box, factor: Size = 2) -> Box:
        """
        Scale a box.

        :param box: the box
        :param factor: the factor
        :return: the scaled box
        """
        return box
''')
_PICKER: Final[str] = dedent("""\
    .. live-example-picker::
        :reference: reference

        Names
            Full module paths: typehints_fully_qualified = False, True
        Rendering
            Default value style: typehints_defaults = None, "comma"
            Document the return type: typehints_document_rtype = True, False
            Return type as its own field: typehints_use_rtype = True, False if typehints_document_rtype

""")
# the page whose confval entries describe the options of the picker
_REFERENCE: Final[str] = dedent("""\
    :orphan:

    .. confval:: typehints_fully_qualified
        :default: ``False``

        Show each type with its module; follows :confval:`autodoc_typehints_format` unless set.

    .. confval:: typehints_defaults

        Show defaults in the ``"comma"`` style. Leave them out otherwise.

    .. confval:: typehints_document_rtype

        Add the return type of a :func:`@overload <typing.overload>` or :class:`~typing.Union`.

    .. confval:: typehints_use_rtype

        Give the return type its own field.
""")
_SHARED_CONF: Final[str] = "# shared by every example"


def _picked(source: str = _PICKED_SOURCE, conf: str = _SHARED_CONF) -> str:
    return f".. live-example::\n\n{indent(f'{conf}\n---\n{source}', '    ')}\n"


class _Option(TypedDict):
    name: str
    values: list[str | bool]
    dependsOn: str | None
    lines: list[str]


class _About(TypedDict):
    options: list[_Option]
    conf: str
    data: str


class _Variants(TypedDict):
    bodies: list[str]
    relevant: list[list[int]]
    examples: list[dict[str, int]]


_FOUND_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'<script type="application/json" id="live-example-picker">(?P<config>.*?)</script>'
)


def _about(app: SphinxTestApp) -> _About:
    found = _FOUND_PATTERN.search((Path(app.outdir) / "index.html").read_text())
    assert found is not None
    return loads(found["config"])


def _variants(app: SphinxTestApp) -> _Variants:
    script = (Path(app.outdir) / _about(app)["data"]).read_text()
    return loads(script[script.index("(") + 1 : script.rindex(")")])


_WITHOUT_PREFIXES_PATTERN: Final[re.Pattern[str]] = re.compile(r'(id="|href="#)[0-9a-f]{12}-')


def _without_prefixes(html: str) -> str:
    return _WITHOUT_PREFIXES_PATTERN.sub(r"\1", html)


def test_live_example_picker_puts_its_controls_above_the_rendered_page(build: Build) -> None:

    conf = _tab(build(f"{_PICKER}{_picked()}"), "sphinx-autodoc-typehints")

    assert (
        'role="switch" class="lep-switch" id="lep-0-typehints_fully_qualified" name="typehints_fully_qualified">'
        in conf
    )
    assert 'id="lep-0-typehints_document_rtype" name="typehints_document_rtype" checked>' in conf
    assert '<input type="radio" name="typehints_defaults" value="1"><span>comma</span>' in conf


@mark.parametrize(
    "fragment",
    [
        param('<details class="lep-details"><summary><span class="lep-toggle">conf.py</span>', id="toggle"),
        param("<legend>Rendering</legend>", id="group"),
        param('<label class="lep-label" for="lep-0-typehints_fully_qualified">Full module paths</label>', id="label"),
        param('href="reference.html#confval-typehints_fully_qualified"', id="reference link"),
        param(">Show each type with its module.</span>", id="description up to a semicolon"),
        param(">Show defaults in the <code>&quot;comma&quot;</code> style.</span>", id="literal"),
        param(">Add the return type of a @overload or Union.</span>", id="roles"),
        param('aria-describedby="lep-0-typehints_use_rtype-tip"', id="tooltip"),
    ],
)
def test_live_example_picker_describes_each_option(fragment: str, build: Build) -> None:
    app = build(f"{_PICKER}{_picked()}")

    assert fragment in _tab(app, "sphinx-autodoc-typehints")


def test_live_example_picker_warns_of_an_option_the_reference_leaves_out(build: Build) -> None:
    picker = _PICKER.replace("typehints_use_rtype = True, False if", "always_document_param_types = False, True if")

    app = build(f"{picker}{_picked()}")

    assert "no confval entry of reference describes always_document_param_types" in app.warning.getvalue()


def test_live_example_picker_drops_the_conf_tab(build: Build) -> None:
    app = build(f"{_PICKER}{_picked()}")

    labels = [name for name, _ in _tabs(app)]

    assert labels == ["demo.py", "sphinx-autodoc-typehints", "Sphinx built-in"]


def test_live_example_picker_shows_the_defaults_in_the_page(build: Build) -> None:
    app = build(f"{_PICKER}{_picked()}")

    assert 'id="' in (rendered := _tab(app, "sphinx-autodoc-typehints"))
    assert "demo.scale" in rendered


def test_live_example_picker_publishes_the_variants(build: Build) -> None:
    app = build(f"{_PICKER}{_picked()}{_picked(_PICKED_SOURCE.replace('scale', 'grow'))}")

    assert len(_variants(app)["examples"]) == 2


def test_live_example_picker_lists_the_options_with_their_conf_lines(build: Build) -> None:

    options = _about(build(f"{_PICKER}{_picked()}"))["options"]

    assert [option["name"] for option in options] == [
        "typehints_fully_qualified",
        "typehints_defaults",
        "typehints_document_rtype",
        "typehints_use_rtype",
    ]
    assert options[3]["dependsOn"] == "typehints_document_rtype"
    assert "typehints_defaults" in options[1]["lines"][1]


@mark.parametrize(
    "picked",
    [
        param({"typehints_fully_qualified": True}, id="fully qualified"),
        param({"typehints_defaults": "comma"}, id="defaults"),
        param({"typehints_document_rtype": False}, id="no return type"),
        param({"typehints_use_rtype": False}, id="return type in the return text"),
        param(
            {"typehints_fully_qualified": True, "typehints_defaults": "comma", "typehints_use_rtype": False},
            id="three options",
        ),
    ],
)
def test_live_example_picker_variant_matches_a_build_with_that_conf(
    picked: dict[str, str | bool], build: Build
) -> None:
    about, variants = _about(app := build(f"{_PICKER}{_picked()}")), _variants(app)
    combination = [
        option["values"].index(picked.get(option["name"], option["values"][0])) for option in about["options"]
    ]
    chosen = {index: at for index, at in enumerate(combination) if index in variants["relevant"][0]}
    key = "".join(str(chosen.get(index, 0)) for index in range(len(combination)))
    variant = variants["bodies"][variants["examples"][0][key]]

    alone = build(_picked(conf="\n".join([_SHARED_CONF, *(f"{name} = {value!r}" for name, value in picked.items())])))

    assert _without_prefixes(variant) in _without_prefixes(_tab(alone, "sphinx-autodoc-typehints"))


def test_live_example_picker_skips_options_that_change_nothing(build: Build) -> None:
    app = build(f"{_PICKER}{_picked(_PICKED_SOURCE.replace('factor: Size = 2', 'factor: Size'))}")

    assert 1 not in _variants(app)["relevant"][0]


def test_live_example_picker_copies_its_variants_next_to_the_page(build: Build) -> None:
    app = build(f"{_PICKER}{_picked()}")

    assert (Path(app.outdir) / _about(app)["data"]).is_file()


def test_live_example_picker_reuses_the_cached_variants(build: Build, monkeypatch: MonkeyPatch) -> None:
    build(f"{_PICKER}{_picked()}")
    # a nested application that cannot start fails any render, so only the cache can fill the second page
    monkeypatch.setattr("live_example_variants.Sphinx", None)

    app = build(f"{_PICKER}{_picked()}")

    assert "ERROR" not in app.warning.getvalue()


def test_live_example_picker_needs_one_conf(build: Build) -> None:
    app = build(f"{_PICKER}{_picked()}{_picked(conf='# another conf.py')}")

    assert "the examples under a live-example-picker need one conf.py they all share" in app.warning.getvalue()


def test_live_example_picker_reports_a_failing_variant(build: Build) -> None:
    app = build(f"{_PICKER}{_picked(_PICKED_SOURCE.replace('    :param box: the box', '    :param box: `unclosed'))}")

    assert "the examples fail to build:" in app.warning.getvalue()


def test_live_example_picker_leaves_the_outer_build_logging(build: Build) -> None:
    app = build(f"{_PICKER}{_picked()}\n.. warning-target-that-does-not-exist::\n")

    assert 'Unknown directive type "warning-target-that-does-not-exist"' in app.warning.getvalue()
