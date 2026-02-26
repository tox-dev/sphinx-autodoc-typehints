from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from conftest import normalize_sphinx_text

numpydoc = pytest.importorskip("numpydoc")

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp


def simple_func(x: int, y: str) -> str:
    """
    Do something simple.

    Parameters
    ----------
    x : int
        The x value.
    y : str
        The y value.

    Returns
    -------
    result : str
        The combined result.
    """


def raises_func(x: int) -> None:
    """
    Raise on bad input.

    Parameters
    ----------
    x : int
        The input value.

    Raises
    ------
    ValueError
        If x is negative.
    TypeError
        If x is not an integer.
    """


def multi_return(x: int) -> tuple[str, int]:
    """
    Return multiple values.

    Parameters
    ----------
    x : int
        The input.

    Returns
    -------
    name : str
        The name.
    value : int
        The value.
    """


def no_params() -> str:
    """
    Function with no parameters.

    Returns
    -------
    str
        A greeting.
    """


def _build_and_get_output(
    app: SphinxTestApp,
    status: StringIO,
    monkeypatch: pytest.MonkeyPatch,
    func_name: str,
) -> str:
    template = f"""\
.. autofunction:: mod_numpy.{func_name}
"""
    (Path(app.srcdir) / "index.rst").write_text(template)
    monkeypatch.setitem(sys.modules, "mod_numpy", sys.modules[__name__])
    app.build()
    assert "build succeeded" in status.getvalue()
    return normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())


@pytest.mark.sphinx("text", testroot="issue_347")
def test_simple_params_and_return(
    app: SphinxTestApp,
    status: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _build_and_get_output(app, status, monkeypatch, "simple_func")
    assert "Parameters:" in result
    assert "**x** (" in result
    assert "**y** (" in result
    assert "Return type:" in result


@pytest.mark.sphinx("text", testroot="issue_347")
def test_raises_section(
    app: SphinxTestApp,
    status: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _build_and_get_output(app, status, monkeypatch, "raises_func")
    assert "Parameters:" in result
    assert "Raises:" in result
    assert "ValueError" in result
    assert "TypeError" in result


@pytest.mark.sphinx("text", testroot="issue_347")
def test_multi_return(
    app: SphinxTestApp,
    status: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _build_and_get_output(app, status, monkeypatch, "multi_return")
    assert "Return type:" in result


@pytest.mark.sphinx("text", testroot="issue_347")
def test_no_params(
    app: SphinxTestApp,
    status: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _build_and_get_output(app, status, monkeypatch, "no_params")
    assert "Return type:" in result
