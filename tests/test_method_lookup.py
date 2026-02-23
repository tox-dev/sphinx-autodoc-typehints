from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp


class MyClass:
    """A class with a property."""

    @property
    def n_unique_nonzero(self) -> int:
        """Number of unique nonzero elements."""
        return 0

    def regular_method(self, x: int) -> int:  # noqa: PLR6301
        """Do something.

        Args:
            x: a number
        """
        return x


@pytest.mark.sphinx("text", testroot="integration")
def test_method_lookup_does_not_crash(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        Test
        ====

        .. autoclass:: mod.MyClass
           :members:
    """)
    )
    monkeypatch.setitem(sys.modules, "mod", sys.modules[__name__])
    app.build()
    assert "build succeeded" in status.getvalue()
