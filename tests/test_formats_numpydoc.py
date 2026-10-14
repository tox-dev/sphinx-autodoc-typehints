from __future__ import annotations

import sys
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from conftest import make_docstring_app, normalize_sphinx_text
from sphinx.application import Sphinx

from sphinx_autodoc_typehints import process_docstring
from sphinx_autodoc_typehints._formats import detect_format
from sphinx_autodoc_typehints._formats._base import InsertIndexInfo
from sphinx_autodoc_typehints._formats._numpydoc import NumpydocFormat, _convert_numpydoc_to_sphinx_fields
from sphinx_autodoc_typehints._formats._sphinx import SphinxFieldListFormat

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
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
    assert lines == [":returns: **result** (str) -- The combined result.", ""]


def test_convert_returns_no_name() -> None:
    lines = [
        ":Returns:",
        "",
        "    str",
        "        A greeting.",
        "",
    ]
    _convert_numpydoc_to_sphinx_fields(lines)
    assert lines == [":rtype: str", ":returns: A greeting.", ""]


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
    assert lines == [":Other Parameters: **flag** (bool) -- A flag.", ""]


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
    assert lines == [":returns: **result** (str)", ""]


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
    assert ":returns: **result** (str) -- The result." in lines
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
    assert lines == [":Yields: **result** (int)", "", ":param x: The x.", ":type x: int", ""]


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


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param(["The first,", "wrapped."], [":param first: The first,", "   wrapped."], id="wrapped"),
        pytest.param(
            ["The first.", "", "More about it."],
            [":param first: The first.", "", "   More about it."],
            id="paragraphs",
        ),
        pytest.param(
            ["The first, one of:", "", "- a", "- b"],
            [":param first: The first, one of:", "", "   - a", "   - b"],
            id="list",
        ),
    ],
)
def test_process_docstring_numpydoc_description_keeps_its_blocks(body: list[str], expected: list[str]) -> None:
    def two_params(first: int, second: str) -> None: ...

    # numpydoc indents the blank line separating the blocks
    lines = [
        ":Parameters:",
        "",
        "    **first** : int",
        *(f"        {line}" for line in body),
        "",
        "    **second** : str",
        "        The second.",
        "",
    ]
    app = make_docstring_app(typehints_document_rtype=False)
    process_docstring(app, "function", "mod.two_params", two_params, None, lines)
    assert lines == [
        *expected,
        r":type first: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        ":param second: The second.",
        r":type second: :sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``",
        "",
    ]


def test_process_docstring_numpydoc_params_sharing_a_type_line() -> None:
    def coordinates(lat: int, lon: int) -> None: ...

    lines = [":Parameters:", "", "    **lat, lon** : int", "        The coordinates.", ""]
    app = make_docstring_app(typehints_document_rtype=False)
    process_docstring(app, "function", "mod.coordinates", coordinates, None, lines)
    assert lines == [
        ":param lat: The coordinates.",
        r":type lat: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        ":param lon: The coordinates.",
        r":type lon: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        "",
    ]


@pytest.mark.parametrize(
    ("entry", "description", "expected"),
    [
        pytest.param("    int", "        A number.", ":Yields: int -- A number.", id="unnamed"),
        pytest.param("    **item** : int", "        A number.", ":Yields: **item** (int) -- A number.", id="named"),
        pytest.param("    **item**", "        A number.", ":Yields: **item** -- A number.", id="named-untyped"),
        pytest.param("    int", "        ..", ":Yields: int", id="placeholder-description"),
    ],
)
def test_process_docstring_numpydoc_single_yield_keeps_its_type(entry: str, description: str, expected: str) -> None:
    def counter(bound: int) -> Iterator[int]: ...

    lines = [
        ":Parameters:",
        "",
        "    **bound** : int",
        "        The bound.",
        "",
        ":Yields:",
        "",
        entry,
        description,
        "",
    ]
    process_docstring(make_docstring_app(), "function", "mod.counter", counter, None, lines)
    assert lines == [
        ":param bound: The bound.",
        r":type bound: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        "",
        expected,
        "",
    ]


def test_process_docstring_numpydoc_returns_without_descriptions() -> None:
    def pair(bound: int) -> tuple[int, str]: ...

    lines = [":Returns:", "", "    **x** : int", "        ..", "    **y** : str", "        ..", ""]
    process_docstring(make_docstring_app(), "function", "mod.pair", pair, None, lines)
    assert lines[-4:] == [":returns:", "   * **x** (int)", "   * **y** (str)", ""]


def _annotated_ratio(a: int) -> float: ...


# only the docstring types it
def _unannotated_ratio(a):  # ruff:ignore[missing-type-function-argument, missing-return-type-private-function]
    ...


@pytest.mark.parametrize(
    ("func", "rtype"),
    [
        pytest.param(_annotated_ratio, r":sphinx_autodoc_typehints_type:`\:py\:class\:\`float\``", id="annotated"),
        pytest.param(_unannotated_ratio, "float", id="unannotated"),
    ],
)
def test_process_docstring_numpydoc_unnamed_return_keeps_its_type(func: Callable[..., Any], rtype: str) -> None:
    lines = [":Returns:", "", "    float", "        The ratio.", ""]
    process_docstring(make_docstring_app(), "function", "mod.ratio", func, None, lines)
    assert lines == [f":rtype: {rtype}", ":returns: The ratio.", ""]


def test_process_docstring_numpydoc_other_parameters_keep_their_section() -> None:
    def tune(a: int, *, flag: bool = False, x: int = 0, y: int = 0) -> None: ...

    lines = [":Parameters:", "", "    **a**", "        The a.", "", ":Other Parameters:", "", "    **flag**"]
    lines += ["        A flag.", "    **x, y** : int", "        Shared.", ""]
    process_docstring(make_docstring_app(typehints_document_rtype=False), "function", "mod.tune", tune, None, lines)
    assert lines == [
        r":type a: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        ":param a: The a.",
        "",
        ":Other Parameters:",
        r"   * **flag** (:sphinx_autodoc_typehints_type:`\:py\:class\:\`bool\``) -- A flag.",
        "   * **x** (int) -- Shared.",
        "   * **y** (int) -- Shared.",
        "",
    ]
