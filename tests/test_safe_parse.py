"""Tests that snippet parsing doesn't trigger extension directive side-effects."""

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
    warning: StringIO,  # noqa: ARG001
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
    exec(compile(src, "<test>", "exec"), (mod := {}))  # noqa: S102
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
