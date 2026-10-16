from __future__ import annotations

from importlib import import_module
from inspect import isclass
from pathlib import Path
from shutil import copytree
from sys import modules
from textwrap import dedent
from typing import TYPE_CHECKING

from extension_expected import EPILOG, EXPECTED, OPTIONS, PROLOG, WARNINGS
from pytest import MonkeyPatch, fixture, mark, param
from sphinx.util.console import strip_colors

from sphinx_autodoc_typehints.version import __version__

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp


@mark.sphinx("text", testroot="dummy", confoverrides={"extensions": ["sphinx_autodoc_typehints", "sphinx.ext.autodoc"]})
def test_setup_loads_autodoc_listed_after_it(build_text: BuildText) -> None:
    assert build_text(".. autofunction:: dummy_module.undocumented_function") == dedent("""\
        dummy_module.undocumented_function(x)

           Hi

           Return type:
              "str"
        """)


@mark.parametrize(
    "type_text",
    [
        param("- item", id="bullet"),
        param("#. item", id="enumerated"),
        param("* item", id="asterisk-bullet"),
    ],
)
@mark.sphinx("text", testroot="dummy")
def test_type_role_renders_list_like_text_inline(build_text: BuildText, type_text: str) -> None:
    assert build_text(f"A :sphinx_autodoc_typehints_type:`{type_text}` b.").splitlines() == [f"A {type_text} b."]


@mark.sphinx("text", testroot="public-api")
def test_setup_declares_parallel_safety(app: SphinxTestApp) -> None:
    app.build()
    extension = app.extensions["sphinx_autodoc_typehints"]
    assert (extension.parallel_read_safe, extension.parallel_write_safe) == (True, True)


@mark.sphinx("text", testroot="public-api")
def test_setup_reports_the_package_version(app: SphinxTestApp) -> None:
    app.build()
    assert app.extensions["sphinx_autodoc_typehints"].version == __version__


@mark.parametrize(
    "log_conf",
    [
        param({}, id="no-prolog"),
        param({"rst_prolog": PROLOG}, id="prolog"),
        param({"rst_epilog": EPILOG}, id="epilog"),
        param({"rst_prolog": PROLOG, "rst_epilog": EPILOG}, id="prolog-and-epilog"),
    ],
)
@mark.parametrize("name", [param(name, id=name) for name in EXPECTED])
def test_integration(
    make_app: Callable[..., SphinxTestApp],
    rootdir: Path,
    tmp_path: Path,
    cases_module: ModuleType,
    name: str,
    log_conf: dict[str, str],
) -> None:
    srcdir = copytree(rootdir / "test-foundation-extension", tmp_path / "src")
    if isclass(documented := getattr(cases_module, name)):
        rst = dedent(f"""\
            .. {"autoexception" if issubclass(documented, BaseException) else "autoclass"}:: mod.{name}
               :members:
        """)
    else:
        rst = f".. autofunction:: mod.{name}"
    (srcdir / "index.rst").write_text(rst)
    app = make_app(
        "text", srcdir=srcdir, confoverrides={**log_conf, **OPTIONS.get(name, {}), "always_use_bars_union": True}
    )
    app.build()

    output = (Path(app.outdir) / "index.txt").read_text().strip()
    warnings = [line.partition(" WARNING: ")[2] for line in strip_colors(app.warning.getvalue()).splitlines()]
    assert (output, warnings) == (EXPECTED[name].strip(), WARNINGS.get(name, []))


@fixture(name="cases_module")
def cases_module_fixture(rootdir: Path, monkeypatch: MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(rootdir / "test-foundation-extension")
    # the expected output names the module mod, while a module file of that name would share the import and the source
    # analysis the process keeps per module name with the mod of another testroot
    monkeypatch.setitem(modules, "mod", module := import_module("extension_cases"))
    return module


@mark.sphinx("text", testroot="dummy", confoverrides={"default_role": "literal"})
def test_type_role_keeps_the_default_role_of_the_document(build_text: BuildText) -> None:
    assert build_text(".. autofunction:: dummy_module_simple_default_role.function") == dedent("""\
        dummy_module_simple_default_role.function(x, y)

           Function docstring.

           Parameters:
              * **x** ("bool") -- "foo"

              * **y** ("int") -- "bar"

           Return type:
              "str"
        """)


def test_build_reads_the_guard_of_a_module_edited_since_the_last_build(
    make_app: Callable[..., SphinxTestApp], tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    (project := tmp_path / "project").mkdir()
    (project / "conf.py").write_text('extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]')
    (project / "index.rst").write_text(".. autofunction:: guard_edited.convert")
    monkeypatch.syspath_prepend(project)
    for imported in ("from pathlib import Path", "from decimal import Decimal as Path"):
        (project / "guard_edited.py").write_text(
            dedent(f"""\
                from typing import TYPE_CHECKING

                if TYPE_CHECKING:
                    {imported}


                def convert(value: "Path") -> None:
                    '''Convert.

                    :param value: the input
                    '''
            """)
        )
        monkeypatch.delitem(modules, "guard_edited", raising=False)
        (app := make_app("text", srcdir=project, freshenv=True)).build()
    assert (Path(app.outdir) / "index.txt").read_text() == dedent("""\
        guard_edited.convert(value)

           Convert.

           Parameters:
              **value** ("Decimal") -- the input

           Return type:
              "None"
        """)
