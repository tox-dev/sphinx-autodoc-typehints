from __future__ import annotations

from re import findall
from shutil import copytree
from typing import TYPE_CHECKING, Final

from pytest import mark, param

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from sphinx.testing.util import SphinxTestApp


_SUBTYPES: Final[set[str]] = {"comment", "forward_reference", "guarded_import", "local_function", "multiple_ast_nodes"}


@mark.parametrize(
    ("suppressed", "expected"),
    [
        param([], _SUBTYPES, id="none"),
        param(["sphinx_autodoc_typehints"], set(), id="all"),
        *(
            param([f"sphinx_autodoc_typehints.{subtype}"], _SUBTYPES - {subtype}, id=subtype)
            for subtype in sorted(_SUBTYPES)
        ),
    ],
)
def test_warnings_carry_suppressible_categories(
    make_app: Callable[..., SphinxTestApp], rootdir: Path, tmp_path: Path, suppressed: list[str], expected: set[str]
) -> None:
    # the guard of a module runs once per process, so each build documents a module of its own
    module = f"public_module_{tmp_path.name}"
    copytree(rootdir / "test-public-api", srcdir := tmp_path / "src")
    (srcdir / "public_module.py").rename(srcdir / f"{module}.py")
    (index := srcdir / "index.rst").write_text(index.read_text().replace("public_module.", f"{module}."))
    app = make_app("text", srcdir=srcdir, confoverrides={"suppress_warnings": suppressed})
    app.build()

    assert set(findall(r"\[sphinx_autodoc_typehints\.(\w+)\]", app.warning.getvalue())) == expected
