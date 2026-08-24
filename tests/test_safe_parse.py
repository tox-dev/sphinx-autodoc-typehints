"""Tests that the throwaway snippet parse leaves the real build untouched."""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, ClassVar

import pytest
from docutils.parsers.rst import Directive, directives

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp


@pytest.mark.sphinx("text", testroot="integration")
def test_extension_directive_not_executed_during_snippet_parse(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,  # ruff:ignore[unused-function-argument]
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-builtin directive in a docstring should only execute once (during the real build)."""
    directives.register_directive("tracking-directive", _TrackingDirective)
    _TrackingDirective.executions.clear()

    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        Test
        ====

        .. autofunction:: mod.func_with_tracking_directive
    """)
    )

    src = dedent("""\
    def func_with_tracking_directive(x: int) -> int:
        \"\"\"Do something.

        :param x: A number.

        .. tracking-directive::

            unique-id-123

        \"\"\"
        return x
    """)
    exec(compile(src, "<test>", "exec"), (mod := {}))  # ruff:ignore[exec-builtin]
    fake_module = type(sys)("mod")
    fake_module.__dict__.update(mod)
    monkeypatch.setitem(sys.modules, "mod", fake_module)

    app.build()
    assert "build succeeded" in status.getvalue()
    assert _TrackingDirective.executions.count("unique-id-123") == 1


class _TrackingDirective(Directive):
    """Directive that records each execution to detect double-processing."""

    has_content = True
    executions: ClassVar[list[str]] = []

    def run(self) -> list:
        _TrackingDirective.executions.append(self.content[0] if self.content else "")
        return []


@pytest.mark.sphinx("text", testroot="intersphinx-external-role")
def test_intersphinx_role_resolves_during_snippet_parse(
    app: SphinxTestApp, status: StringIO, warning: StringIO
) -> None:
    """Neither the snippet parse nor the type role may shadow the intersphinx dispatcher (#753)."""
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue()


@pytest.mark.sphinx("text", testroot="intersphinx-missing-inventory")
def test_snippet_parse_stays_quiet(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    """A reference the role cannot resolve is reported by the real parse alone (#753)."""
    app.build()
    assert "build succeeded" in status.getvalue()
    assert warning.getvalue().count("inventory for external cross-reference not found") == 1
