from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from conftest import normalize_sphinx_text

from sphinx_autodoc_typehints._resolver import _get_type_hint

if sys.version_info >= (3, 14):
    import annotationlib

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

SKIP_REASON = "annotationlib requires Python 3.14+"
needs_314 = pytest.mark.skipif(sys.version_info < (3, 14), reason=SKIP_REASON)


@needs_314
@pytest.mark.sphinx("text", testroot="issue_572")
def test_forward_ref_builds_without_errors(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,  # noqa: ARG001
) -> None:
    """Forward-referencing module builds cleanly on 3.14+ using annotationlib."""
    template = """\
.. autoclass:: mod_forward_ref.Tree
   :members:
"""
    (Path(app.srcdir) / "index.rst").write_text(template)
    app.build()
    assert "build succeeded" in status.getvalue()
    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert "Tree" in result


@needs_314
def test_get_type_hint_uses_annotationlib_on_name_error() -> None:
    """_get_type_hint falls back to annotationlib.get_annotations on 3.14+ NameError."""
    sentinel = {"x": int}

    def dummy() -> None: ...

    with (
        patch("sphinx_autodoc_typehints._resolver.get_type_hints", side_effect=NameError("name 'Foo' is not defined")),
        patch.object(annotationlib, "get_annotations", return_value=sentinel) as mock_get_ann,
    ):
        result = _get_type_hint([], "dummy", dummy, {})

    mock_get_ann.assert_called_once_with(dummy, format=annotationlib.Format.FORWARDREF)
    assert result is sentinel


@pytest.mark.skipif(sys.version_info >= (3, 14), reason="Tests pre-3.14 fallback path")
def test_get_type_hint_falls_back_to_dunder_annotations_before_314() -> None:  # pragma: <3.14 cover
    """_get_type_hint falls back to __annotations__ on pre-3.14 NameError."""

    def dummy(x: int) -> str: ...

    with patch("sphinx_autodoc_typehints._resolver.get_type_hints", side_effect=NameError("name 'Foo' is not defined")):
        result = _get_type_hint([], "dummy", dummy, {})

    assert result == dummy.__annotations__
