from __future__ import annotations

from unittest.mock import MagicMock, patch

from sphinx_autodoc_typehints.attributes_patch import (
    OKAY_TO_PATCH,
    TYPE_IS_RST_LABEL,
    patch_attribute_handling,
    patched_parse_annotation,
)


def test_okay_to_patch_is_true() -> None:
    assert OKAY_TO_PATCH


def test_patched_parse_annotation_without_label() -> None:
    settings = MagicMock()
    env = MagicMock()
    with patch("sphinx_autodoc_typehints.attributes_patch._parse_annotation") as mock_parse:
        mock_parse.return_value = "parsed"
        result = patched_parse_annotation(settings, "int", env)
    assert result == "parsed"
    mock_parse.assert_called_once_with("int", env)


def test_patched_parse_annotation_dispatches_on_label() -> None:
    settings = MagicMock()
    env = MagicMock()
    with patch("sphinx_autodoc_typehints.attributes_patch.rst_to_docutils", return_value=["nodes"]) as mock_rst:
        result = patched_parse_annotation(settings, f"{TYPE_IS_RST_LABEL}**bold**", env)
    mock_rst.assert_called_once_with(settings, "**bold**")
    assert result == ["nodes"]


def test_patch_attribute_handling_when_not_okay() -> None:
    app = MagicMock()
    with patch("sphinx_autodoc_typehints.attributes_patch.OKAY_TO_PATCH", False):
        patch_attribute_handling(app)


def test_rst_to_docutils_returns_parsed_nodes() -> None:
    """Lines 34-36: rst_to_docutils parses RST and returns inner nodes."""
    from docutils.frontend import get_default_settings  # noqa: PLC0415
    from sphinx.parsers import RSTParser  # noqa: PLC0415

    from sphinx_autodoc_typehints.attributes_patch import rst_to_docutils  # noqa: PLC0415

    settings = get_default_settings(RSTParser)  # type: ignore[arg-type]
    settings.env = MagicMock()
    result = rst_to_docutils(settings, "**bold text**")
    assert len(result) > 0
    assert any("bold text" in node.astext() for node in result)
