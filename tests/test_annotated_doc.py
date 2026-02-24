from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import pytest
from typing_extensions import Doc

from sphinx_autodoc_typehints import _extract_doc_description

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

numpydoc = pytest.importorskip("numpydoc")


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(Annotated[int, Doc("hello")], "hello", id="annotated-with-doc"),
        pytest.param(Annotated[int, 42], None, id="annotated-without-doc"),
        pytest.param(int, None, id="plain-type"),
        pytest.param(Annotated[int, Doc("first"), Doc("second")], "first", id="picks-first-doc"),
    ],
)
def test_extract_doc_description(annotation: type, expected: str | None) -> None:
    assert _extract_doc_description(annotation) == expected


def _load_and_build(
    app: SphinxTestApp,
    status: StringIO,
    monkeypatch: pytest.MonkeyPatch,
    testroot: str,
    func_name: str,
) -> str:
    mod_name = "mod"
    mod_path = Path(__file__).parent / "roots" / f"test-{testroot}" / f"{mod_name}.py"
    spec = importlib.util.spec_from_file_location(mod_name, mod_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    (Path(app.srcdir) / "index.rst").write_text(f".. autofunction:: {mod_name}.{func_name}\n")
    monkeypatch.setitem(sys.modules, mod_name, module)
    app.build()
    assert "build succeeded" in status.getvalue()
    return (Path(app.srcdir) / "_build/text/index.txt").read_text()


@pytest.mark.parametrize(
    ("func_name", "expected", "not_expected"),
    [
        pytest.param(
            "greet",
            ["The person's name", "The greeting phrase", "The full greeting message"],
            [],
            id="all-params-and-return",
        ),
        pytest.param("partial_doc", ["The x value", "The y value"], [], id="partial-doc-with-docstring"),
        pytest.param("no_doc", ["Identity"], [], id="annotated-without-doc-metadata"),
        pytest.param("docstring_wins", ["Docstring description"], ["Doc description"], id="docstring-takes-precedence"),
    ],
)
@pytest.mark.sphinx("text", testroot="annotated-doc")
def test_sphinx_field_list(
    app: SphinxTestApp,
    status: StringIO,
    monkeypatch: pytest.MonkeyPatch,
    func_name: str,
    expected: list[str],
    not_expected: list[str],
) -> None:
    result = _load_and_build(app, status, monkeypatch, "annotated-doc", func_name)
    for text in expected:
        assert text in result
    for text in not_expected:
        assert text not in result


@pytest.mark.parametrize(
    ("func_name", "expected"),
    [
        pytest.param("transform", ["The input data", "The transformed result"], id="doc-injected"),
        pytest.param("compute", ["Placeholder", "The sum"], id="existing-params-preserved"),
    ],
)
@pytest.mark.sphinx("text", testroot="annotated-doc-numpydoc")
def test_numpydoc(
    app: SphinxTestApp,
    status: StringIO,
    monkeypatch: pytest.MonkeyPatch,
    func_name: str,
    expected: list[str],
) -> None:
    result = _load_and_build(app, status, monkeypatch, "annotated-doc-numpydoc", func_name)
    for text in expected:
        assert text in result
