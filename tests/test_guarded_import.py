from __future__ import annotations

import sys
import types
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp


@pytest.mark.sphinx("text", testroot="integration")
def test_guarded_import_missing_name_no_warning(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_mod = types.ModuleType("target_mod")
    target_mod.__file__ = "/fake/target_mod.py"
    target_mod.existing_name = "value"

    source = dedent("""\
    from __future__ import annotations
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from target_mod import nonexistent_name

    def func(x: int) -> int:
        '''Do something.

        Args:
            x: a number
        '''
        return x
    """)
    user_mod = types.ModuleType("user_mod")
    user_mod.__file__ = "/fake/user_mod.py"
    exec(compile(source, "/fake/user_mod.py", "exec"), user_mod.__dict__)  # noqa: S102

    monkeypatch.setitem(sys.modules, "target_mod", target_mod)
    monkeypatch.setitem(sys.modules, "user_mod", user_mod)

    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        Test
        ====

        .. autofunction:: user_mod.func
    """)
    )
    app.build()
    assert "build succeeded" in status.getvalue()
    assert "Failed guarded type import" not in warning.getvalue()
