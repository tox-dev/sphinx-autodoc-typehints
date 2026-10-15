from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark

from sphinx_autodoc_typehints._signature.header.lookup import documented_signatures

if TYPE_CHECKING:
    from conftest import BuildText
    from sphinx import addnodes
    from sphinx.application import Sphinx
    from sphinx.testing.util import SphinxTestApp


@mark.sphinx("text", testroot="dummy")
def test_documented_signatures_yields_only_what_autodoc_documents(app: SphinxTestApp, build_text: BuildText) -> None:
    found: list[tuple[str, str]] = []

    # autodoc records what it documents only while the page is read, so the walk runs where the extension runs it
    def collect(sphinx_app: Sphinx, _domain: str, _objtype: str, contentnode: addnodes.desc_content) -> None:
        found.extend((module, fullname) for _, module, fullname in documented_signatures(sphinx_app.env, contentnode))

    app.connect("object-description-transform", collect)
    build_text(
        dedent("""\
            .. autofunction:: dummy_module_simple.function

            .. py:function:: dummy_module_simple.handwritten(value)
        """)
    )

    assert found == [("dummy_module_simple", "function")]
