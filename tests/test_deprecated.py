from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.testing.util import SphinxTestApp


@pytest.mark.parametrize(
    ("rst", "expected"),
    [
        pytest.param(
            ".. autofunction:: deprecated_module.stale",
            """\
            deprecated_module.stale(value)

               Do the stale thing.

               Deprecated: Use fresh() instead, *really*.

               More words.

               Return type:
                  "int"
            """,
            id="function",
        ),
        pytest.param(
            ".. autoclass:: deprecated_module.Stale",
            """\
            class deprecated_module.Stale(**kwargs)

               A stale class.

               Deprecated: Use Fresh. It is faster.
            """,
            id="class",
        ),
        pytest.param(
            ".. autoclass:: deprecated_module.Child",
            """\
            class deprecated_module.Child(**kwargs)

               Not deprecated itself.
            """,
            id="subclass",
        ),
        pytest.param(
            ".. autofunction:: deprecated_module.noted",
            """\
            deprecated_module.noted(value)

               Do the noted thing.

               Deprecated since version 2.0: Use fresh().

               Return type:
                  "int"
            """,
            id="documented-deprecation",
        ),
    ],
)
@pytest.mark.sphinx("text", testroot="deprecated")
def test_deprecated_message_follows_the_summary(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, expected: str
) -> None:
    write_rst(rst)
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text() == dedent(expected)


@pytest.mark.sphinx("html", testroot="deprecated")
def test_deprecated_message_renders_as_a_version_change(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autofunction:: deprecated_module.stale")
    app.build()

    assert (
        '<div class="deprecated">\n<p><span class="versionmodified deprecated">Deprecated: </span>'
        "Use fresh() instead, *really*.</p>\n</div>"
    ) in (Path(app.outdir) / "index.html").read_text()
