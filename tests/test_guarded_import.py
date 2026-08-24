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
    exec(compile(source, "/fake/user_mod.py", "exec"), user_mod.__dict__)  # ruff:ignore[exec-builtin]

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


@pytest.mark.sphinx("text", testroot="unexecutable-guard")
def test_guarded_code_the_interpreter_rejects(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    """Names from type-checker-only code render without warnings (#751)."""
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue()
    text = (Path(app.srcdir) / "_build" / "text" / "index.txt").read_text()
    assert text == dedent("""\
        Module demonstrating type guarded code that the interpreter cannot
        run.

        class demo_unexecutable_guard.DataArray

           An array.

        demo_unexecutable_guard.combine(array, other)

           Combine two arrays.

           Parameters:
              * **array** ("DataArray") -- the first array

              * **other** (T_Other) -- the second array

           Return type:
              T_Other

           Returns:
              the combination

        demo_unexecutable_guard.wrap(array)

           Wrap an array.

           Parameters:
              **array** ("DataArray") -- the array to wrap

           Return type:
              Wrapper

           Returns:
              the wrapper
        """)
