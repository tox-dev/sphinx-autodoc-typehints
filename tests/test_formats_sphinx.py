from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, create_autospec

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.config import Config

import sphinx_autodoc_typehints as sat
from sphinx_autodoc_typehints._formats import InsertIndexInfo
from sphinx_autodoc_typehints._formats._sphinx import SphinxFieldListFormat, _node_line_no

if TYPE_CHECKING:
    import pytest


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
    sat._inject_rtype({"return": str}, sample, app, "function", "sample", lines, fmt)  # noqa: SLF001

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
    sat._inject_rtype({"return": str}, sample, app, "function", "sample", lines, fmt)  # noqa: SLF001

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
