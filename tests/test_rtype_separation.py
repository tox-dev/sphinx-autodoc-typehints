from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp


def func_with_note(x: int) -> str:
    """Do something.

    .. note::

        This is a note about the function.
    """
    return str(x)


@pytest.mark.sphinx("text", testroot="integration")
def test_rtype_separated_from_preceding_paragraph(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        Test
        ====

        .. autofunction:: mod.func_with_note
    """)
    )
    monkeypatch.setitem(sys.modules, "mod", sys.modules[__name__])
    app.build()
    assert "build succeeded" in status.getvalue()
    text = (Path(app.srcdir) / "_build/text/index.txt").read_text()
    assert "Return type" in text
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "Return type" in line:
            assert i > 0, "Return type should not be the first line"
            assert not lines[i - 1].strip() or lines[i - 1].lstrip().startswith("Return type"), (
                f"Return type should be preceded by a blank line, got: {lines[i - 1]!r}"
            )
