from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Final
from unittest.mock import MagicMock, create_autospec

import pytest
from conftest import make_docstring_app
from docutils import nodes
from sphinx.application import Sphinx
from sphinx.config import Config

import sphinx_autodoc_typehints as sat
from sphinx_autodoc_typehints._formats import InsertIndexInfo
from sphinx_autodoc_typehints._formats._sphinx import SphinxFieldListFormat, _node_line_no

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.testing.util import SphinxTestApp


def test_inject_rtype_inserts_blank_line_before_rtype(monkeypatch: pytest.MonkeyPatch) -> None:
    def sample() -> str: ...

    config = create_autospec(
        Config,
        typehints_document_rtype=True,
        typehints_document_rtype_none=True,
        typehints_use_rtype=True,
        python_display_short_literal_types=False,
    )
    app: Sphinx = create_autospec(Sphinx, config=config)

    fmt = SphinxFieldListFormat()
    monkeypatch.setattr(
        fmt, "get_rtype_insert_info", lambda _app, _lines: InsertIndexInfo(insert_index=1, found_directive=True)
    )
    monkeypatch.setattr(sat, "format_annotation", lambda *_args, **_kwargs: "str")
    monkeypatch.setattr(sat, "add_type_css_class", lambda value: value)

    lines = ["A paragraph.", ".. note:: hi"]
    sat._inject_rtype({"return": str}, sample, app, "function", "sample", lines, fmt)  # ruff:ignore[private-member-access]

    assert lines == ["A paragraph.", "", ":rtype: str", "", ".. note:: hi"]


def test_inject_rtype_does_not_add_extra_blank_line(monkeypatch: pytest.MonkeyPatch) -> None:
    def sample() -> str: ...

    config = create_autospec(
        Config,
        typehints_document_rtype=True,
        typehints_document_rtype_none=True,
        typehints_use_rtype=True,
        python_display_short_literal_types=False,
    )
    app: Sphinx = create_autospec(Sphinx, config=config)

    fmt = SphinxFieldListFormat()
    monkeypatch.setattr(fmt, "get_rtype_insert_info", lambda _app, _lines: InsertIndexInfo(insert_index=1))
    monkeypatch.setattr(sat, "format_annotation", lambda *_args, **_kwargs: "str")
    monkeypatch.setattr(sat, "add_type_css_class", lambda value: value)

    lines = ["", ""]
    sat._inject_rtype({"return": str}, sample, app, "function", "sample", lines, fmt)  # ruff:ignore[private-member-access]

    assert lines == ["", ":rtype: str", ""]


def test_node_line_no_none_input() -> None:
    assert _node_line_no(None) is None  # type: ignore[arg-type]


def test_node_line_no_descends_to_find_line() -> None:
    child = MagicMock(spec=nodes.Node)
    child.line = 5
    child.children = []

    parent = MagicMock(spec=nodes.Node)
    parent.line = None
    parent.children = [child]

    assert _node_line_no(parent) == 5


def test_sphinx_format_detect_always_true() -> None:
    assert SphinxFieldListFormat.detect([]) is True
    assert SphinxFieldListFormat.detect([":param x: foo"]) is True


def test_get_rtype_insert_info_field_list_without_param_synonyms() -> None:
    """Line 169: field list exists but has no param-like fields, so it's skipped."""
    config = create_autospec(Config)
    app: Sphinx = create_autospec(Sphinx, config=config)
    app.env = MagicMock()

    fmt = SphinxFieldListFormat()
    lines = [":var x: some variable"]
    result = fmt.get_rtype_insert_info(app, lines)
    assert result is not None
    assert result.insert_index == len(lines)


_FLAG_TYPE: Final = r":paramtype flag: :sphinx_autodoc_typehints_type:`\:py\:class\:\`bool\``"


@pytest.mark.parametrize(
    ("lines", "always_document_param_types", "expected"),
    [
        pytest.param([":keyword flag: on"], False, [_FLAG_TYPE, ":keyword flag: on"], id="keyword"),
        pytest.param([":keyword flag: on"], True, [_FLAG_TYPE, ":keyword flag: on"], id="keyword-not-duplicated"),
        pytest.param([":kwarg flag: on"], False, [_FLAG_TYPE, ":kwarg flag: on"], id="kwarg"),
        pytest.param(
            [":keyword flag: on", ":kwtype flag: int"], False, [":keyword flag: on", _FLAG_TYPE], id="replaces-kwtype"
        ),
    ],
)
def test_process_docstring_types_keyword_arguments(
    lines: list[str], always_document_param_types: bool, expected: list[str]
) -> None:
    def takes_flag(*, flag: bool) -> None: ...

    app = make_docstring_app(always_document_param_types=always_document_param_types, typehints_document_rtype=False)
    sat.process_docstring(app, "function", "mod.takes_flag", takes_flag, None, lines)
    assert lines == expected


def test_get_rtype_insert_info_directive_with_nonempty_preceding_line() -> None:
    """Line 182: directive found but preceding line is non-empty triggers break."""
    config = create_autospec(Config)
    app: Sphinx = create_autospec(Sphinx, config=config)
    app.env = MagicMock()

    fmt = SphinxFieldListFormat()
    lines = ["Some text.", "", ".. note::", "", "   Important note"]
    result = fmt.get_rtype_insert_info(app, lines)
    assert result is not None
    assert result.insert_index == len(lines)


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        pytest.param(
            [":returns: A string", ":rtype: bytes"],
            [r":return: :sphinx_autodoc_typehints_type:`\:py\:class\:\`str\`` -- A string"],
            id="replaces-rtype",
        ),
        pytest.param(
            [":returns:", "   * a string", "   * or another"],
            [
                r":return: :sphinx_autodoc_typehints_type:`\:py\:class\:\`str\`` --",
                "",
                "   * a string",
                "   * or another",
            ],
            id="description-on-next-line",
        ),
    ],
)
def test_process_docstring_inline_return_type(lines: list[str], expected: list[str]) -> None:
    def returns_str() -> str: ...

    sat.process_docstring(
        make_docstring_app(typehints_use_rtype=False), "function", "mod.returns_str", returns_str, None, lines
    )
    assert lines == expected


@pytest.mark.sphinx("text", testroot="dummy")
def test_rtype_stays_with_params_before_a_sphinx_directive(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. autofunction:: dummy_module.versioned")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == dedent("""\
        dummy_module.versioned(a)

           Do it.

           Parameters:
              **a** ("int") -- the a

           Return type:
              "int"

           Added in version 1.0.
        """)


def test_process_docstring_keeps_the_placement_parse_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    def broken() -> int: ...

    lines = ["Behaves like this:", "- a list item", "    an unexpected indent"]
    sat.process_docstring(make_docstring_app(), "function", "mod.broken", broken, None, lines)
    rtype = r":rtype: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``"
    expected = ["Behaves like this:", "- a list item", "    an unexpected indent", "", rtype]
    assert (lines, capsys.readouterr().err) == (expected, "")
