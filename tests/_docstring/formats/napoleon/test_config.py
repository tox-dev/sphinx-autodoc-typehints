from __future__ import annotations

from typing import TYPE_CHECKING

from pytest import mark

if TYPE_CHECKING:
    from sphinx.testing.util import SphinxTestApp


@mark.sphinx("text", testroot="dummy", confoverrides={"napoleon_attr_annotations": True})
def test_napoleon_attr_annotations_keeps_configured_boolean(app: SphinxTestApp) -> None:
    assert app.config.napoleon_attr_annotations is True
