from __future__ import annotations

import re
import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp


class GenClass:
    """A class with generators."""

    def gen_method(  # noqa: PLR6301
        self,
        arg1: int | None = None,  # noqa: ARG002
    ) -> Generator[tuple[str, ...], None, None]:
        """Summary.

        Args:
            arg1: argument 1

        Yields:
            strings of things
        """
        yield ("test",)

    def iter_method(self) -> Iterator[int]:  # noqa: PLR6301
        """Summary.

        Yields:
            integers
        """
        yield 1

    async def async_gen_method(self) -> AsyncGenerator[str, None]:  # noqa: PLR6301
        """Summary.

        Yields:
            strings
        """
        yield "test"

    async def async_iter_method(self) -> AsyncIterator[int]:  # noqa: PLR6301
        """Summary.

        Yields:
            integers
        """
        yield 1

    def no_yields_method(self) -> Generator[int, None, None]:  # noqa: PLR6301
        """Summary without yields section."""
        yield 1


def _extract_section(text: str, method_name: str) -> str:
    pattern = rf"({method_name}\(\).*?)(?=(?:async\s+)?\w+\(\)|$)"
    if match := re.search(pattern, text, re.DOTALL):
        return match.group(1)
    msg = f"Method {method_name} not found in output"
    raise ValueError(msg)


def _build_genclass(app: SphinxTestApp, monkeypatch: pytest.MonkeyPatch) -> str:
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        Test
        ====

        .. autoclass:: mod.GenClass
           :members:
    """)
    )
    monkeypatch.setitem(sys.modules, "mod", sys.modules[__name__])
    app.build()
    return (Path(app.srcdir) / "_build/text/index.txt").read_text()


@pytest.mark.sphinx("text", testroot="integration")
def test_generator_no_duplicate_return_type(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _build_genclass(app, monkeypatch)
    assert "build succeeded" in status.getvalue()

    for method in ("gen_method", "iter_method", "async_gen_method", "async_iter_method"):
        section = _extract_section(text, method)
        assert "Yields" in section, f"{method} missing Yields"
        assert "Return type" not in section, f"{method} has unexpected Return type"


@pytest.mark.sphinx("text", testroot="integration")
def test_generator_without_yields_keeps_rtype(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _build_genclass(app, monkeypatch)
    assert "build succeeded" in status.getvalue()

    section = _extract_section(text, "no_yields_method")
    assert "Return type" in section
