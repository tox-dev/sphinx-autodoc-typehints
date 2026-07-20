from __future__ import annotations

import sys
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from conftest import normalize_sphinx_text
from sphinx.application import Sphinx

from sphinx_autodoc_typehints._formats import detect_format
from sphinx_autodoc_typehints._formats._base import InsertIndexInfo
from sphinx_autodoc_typehints._formats._numpydoc import NumpydocFormat, _convert_numpydoc_to_sphinx_fields
from sphinx_autodoc_typehints._formats._sphinx import SphinxFieldListFormat

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp


def test_convert_parameters_section() -> None:
    lines = [
        "",
        "Summary.",
        "",
        ":Parameters:",
        "",
        "    **x** : int",
        "        The x value.",
        "",
        "    **y** : str",
        "        The y value.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":param x: The x value." in lines
    assert ":type x: int" in lines
    assert ":param y: The y value." in lines
    assert ":type y: str" in lines
    assert ":Parameters:" not in lines


def test_convert_returns_single() -> None:
    lines = [
        ":Returns:",
        "",
        "    **result** : str",
        "        The combined result.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":returns: The combined result." in lines
    assert ":Returns:" not in lines


def test_convert_returns_no_name() -> None:
    lines = [
        ":Returns:",
        "",
        "    str",
        "        A greeting.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":returns: A greeting." in lines


def test_convert_returns_multiple() -> None:
    lines = [
        ":Returns:",
        "",
        "    **name** : str",
        "        The name.",
        "",
        "    **value** : int",
        "        The value.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":returns:" in lines
    assert any("**name**" in line and "str" in line for line in lines)
    assert any("**value**" in line and "int" in line for line in lines)


def test_convert_raises() -> None:
    lines = [
        ":Raises:",
        "",
        "    ValueError",
        "        If x is negative.",
        "",
        "    TypeError",
        "        If x is not an integer.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":raises ValueError: If x is negative." in lines
    assert ":raises TypeError: If x is not an integer." in lines


def test_convert_yields_single() -> None:
    lines = [
        ":Yields:",
        "",
        "    int",
        "        A number.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":Yields: A number." in lines


def test_convert_yields_multiple() -> None:
    lines = [
        ":Yields:",
        "",
        "    **name** : str",
        "        The name.",
        "",
        "    **value** : int",
        "        The value.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":Yields:" in lines
    assert any("**name**" in line and "str" in line for line in lines)
    assert any("**value**" in line and "int" in line for line in lines)


def test_convert_other_parameters() -> None:
    lines = [
        ":Other Parameters:",
        "",
        "    **flag** : bool",
        "        A flag.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":param flag: A flag." in lines
    assert ":type flag: bool" in lines


def test_no_numpydoc_content_is_noop() -> None:
    original = [
        "",
        "A normal docstring.",
        "",
        ":param x: The x value.",
        ":type x: int",
    ]
    lines = list(original)
    _convert_numpydoc_to_sphinx_fields(lines)
    assert lines == original


def test_multiline_description() -> None:
    lines = [
        ":Parameters:",
        "",
        "    **data** : dict",
        "        The data dictionary.",
        "        It can span multiple lines.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":param data: The data dictionary. It can span multiple lines." in lines
    assert ":type data: dict" in lines


def test_param_without_type() -> None:
    lines = [
        ":Parameters:",
        "",
        "    **x**",
        "        The x value.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":param x: The x value." in lines
    assert not any(line.startswith(":type x:") for line in lines)


def test_param_without_description() -> None:
    lines = [
        ":Parameters:",
        "",
        "    **x** : int",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":param x:" in lines
    assert ":type x: int" in lines


def test_raises_with_named_exception() -> None:
    lines = [
        ":Raises:",
        "",
        "    **err** : ValueError",
        "        If something is wrong.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":raises err: If something is wrong." in lines


def test_returns_single_no_description() -> None:
    lines = [
        ":Returns:",
        "",
        "    **result** : str",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert not any(line.startswith(":returns:") for line in lines)


def test_multiple_sections() -> None:
    lines = [
        "Summary.",
        "",
        ":Parameters:",
        "",
        "    **x** : int",
        "        The x value.",
        "",
        ":Returns:",
        "",
        "    **result** : str",
        "        The result.",
        "",
        ":Raises:",
        "",
        "    ValueError",
        "        If bad.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":param x: The x value." in lines
    assert ":type x: int" in lines
    assert ":returns: The result." in lines
    assert ":raises ValueError: If bad." in lines


def test_numpydoc_format_detect() -> None:
    assert NumpydocFormat.detect([":Parameters:", "    **x** : int", "        desc"])
    assert NumpydocFormat.detect([":Returns:", "    str", "        result"])
    assert not NumpydocFormat.detect([":param x: foo", ":type x: int"])


def test_numpydoc_format_find_param() -> None:
    fmt = NumpydocFormat()
    lines = [
        ":Parameters:",
        "",
        "    **x** : int",
        "        The x value.",
        "",
    ]
    idx = fmt.find_param(lines, "x")
    assert idx is not None
    assert lines[idx].startswith(":param x:")


def test_numpydoc_format_find_preexisting_type() -> None:
    fmt = NumpydocFormat()
    lines = [
        ":Parameters:",
        "",
        "    **x** : int",
        "        The x value.",
        "",
    ]
    fmt._ensure_converted(lines)  # ruff:ignore[private-member-access]
    annotation, found = fmt.find_preexisting_type(lines, "x")
    assert found
    assert "int" in annotation


def test_numpydoc_format_add_undocumented_param() -> None:
    fmt = NumpydocFormat()
    lines = [
        ":Parameters:",
        "",
        "    **x** : int",
        "        The x value.",
        "",
    ]
    idx = fmt.add_undocumented_param(lines, "y")
    assert idx is not None
    assert ":param y:" in lines[idx]


def test_numpydoc_format_inject_param_type() -> None:
    fmt = NumpydocFormat()
    lines = [
        ":Parameters:",
        "",
        "    **x** : int",
        "        The x value.",
        "",
    ]
    fmt._ensure_converted(lines)  # ruff:ignore[private-member-access]
    idx = fmt.find_param(lines, "x")
    assert idx is not None
    fmt.inject_param_type(lines, "x", "int", idx + 1)
    assert ":type x: int" in lines


def test_numpydoc_format_get_arg_name_from_line() -> None:
    fmt = NumpydocFormat()
    assert fmt.get_arg_name_from_line(":param x: foo") == "x"
    assert fmt.get_arg_name_from_line("not a param line") is None


def test_numpydoc_format_append_default() -> None:
    """Line 199: append_default delegates to SphinxFieldListFormat."""
    fmt = NumpydocFormat()
    lines = [":param x: the x"]
    result = fmt.append_default(lines, 0, ":type x: int", " (default: ``0``)", after=False)
    assert result == ":type x: int (default: ``0``)"


def test_convert_section_without_blank_line_after_header() -> None:
    """Branch 99->102: no empty line between section header and first entry."""
    lines = [
        ":Parameters:",
        "    **x** : int",
        "        The x value.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":param x: The x value." in lines
    assert ":type x: int" in lines


def test_convert_yields_single_no_description_then_params() -> None:
    """Branch 133->90: single Yields entry without description followed by another section."""
    lines = [
        ":Yields:",
        "",
        "    **result** : int",
        "",
        ":Parameters:",
        "",
        "    **x** : int",
        "        The x.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert not any(line.startswith(":Yields:") for line in lines)
    assert ":param x: The x." in lines
    assert ":type x: int" in lines


def test_detect_format_returns_numpydoc_for_numpydoc_lines() -> None:
    lines = [":Parameters:", "", "    **x** : int", "        desc"]
    fmt = detect_format(lines)
    assert isinstance(fmt, NumpydocFormat)


def test_detect_format_returns_sphinx_for_plain_lines() -> None:
    lines = [":param x: The x value."]
    fmt = detect_format(lines)
    assert isinstance(fmt, SphinxFieldListFormat)


def test_parse_numpydoc_entries_breaks_on_unrecognized_format() -> None:
    lines = [
        ":Parameters:",
        "",
        "    **x** : int",
        "        The x value.",
        "not an entry",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert ":param x: The x value." in lines


def test_numpydoc_format_get_rtype_insert_info() -> None:
    fmt = NumpydocFormat()
    lines = [
        ":Parameters:",
        "",
        "    **x** : int",
        "        The x value.",
        "",
    ]
    app: Sphinx = MagicMock(spec=Sphinx)
    app.env = MagicMock()
    result = fmt.get_rtype_insert_info(app, lines)
    assert result is not None


def test_numpydoc_format_inject_rtype() -> None:
    fmt = NumpydocFormat()
    lines = [":param x: value"]
    info = InsertIndexInfo(insert_index=len(lines))
    fmt.inject_rtype(lines, ":py:class:`str`", info, use_rtype=True)
    assert any("rtype" in line for line in lines)


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


@pytest.mark.skipif(find_spec("numpydoc") is None, reason="requires the numpydoc extension")
@pytest.mark.parametrize(
    ("func", "expected_fragments"),
    [
        pytest.param(simple_func, ["Parameters:", "**x** (", "**y** (", "Return type:"], id="params-and-return"),
        pytest.param(raises_func, ["Parameters:", "Raises:", "ValueError", "TypeError"], id="raises-section"),
        pytest.param(multi_return, ["Return type:"], id="multi-return"),
        pytest.param(no_params, ["Return type:"], id="no-params"),
    ],
)
@pytest.mark.sphinx("text", testroot="numpydoc")
def test_numpydoc_extension_build(
    app: SphinxTestApp,
    status: StringIO,
    monkeypatch: pytest.MonkeyPatch,
    func: Any,
    expected_fragments: list[str],
) -> None:
    """Regression test for #347: docstrings preprocessed by the numpydoc extension keep their types."""
    (Path(app.srcdir) / "index.rst").write_text(f".. autofunction:: mod_numpy.{func.__name__}")
    monkeypatch.setitem(sys.modules, "mod_numpy", sys.modules[__name__])
    app.build()
    assert "build succeeded" in status.getvalue()
    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    for fragment in expected_fragments:
        assert fragment in result
