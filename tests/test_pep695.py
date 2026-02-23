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

_mod_pep695 = types.ModuleType("_mod_pep695")
_mod_pep695.__file__ = __file__
exec(  # noqa: S102
    dedent("""\
    from __future__ import annotations

    class Foo[T]:
        \"\"\"A generic class.\"\"\"

        def __init__(self, thing: T) -> None:
            \"\"\"Init.

            :param thing: the thing
            \"\"\"

        def get(self) -> T:
            \"\"\"Get the thing.

            :return: the thing
            \"\"\"
            ...

    class Multi[K, V]:
        \"\"\"A class with multiple type params.\"\"\"

        def lookup(self, key: K) -> V:
            \"\"\"Look up.

            :param key: the key
            \"\"\"
            ...

    def identity[U](x: U) -> U:
        \"\"\"Identity function.

        :param x: input
        \"\"\"
        return x
    """),
    _mod_pep695.__dict__,
)


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_class_type_params(
    app: SphinxTestApp, status: StringIO, warning: StringIO, monkeypatch: pytest.MonkeyPatch
) -> None:
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        Test
        ====

        .. autoclass:: mod.Foo
           :members:
    """)
    )
    monkeypatch.setitem(sys.modules, "mod", _mod_pep695)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert "Cannot resolve forward reference" not in warning.getvalue()


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_class_multiple_type_params(
    app: SphinxTestApp, status: StringIO, warning: StringIO, monkeypatch: pytest.MonkeyPatch
) -> None:
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        Test
        ====

        .. autoclass:: mod.Multi
           :members:
    """)
    )
    monkeypatch.setitem(sys.modules, "mod", _mod_pep695)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert "Cannot resolve forward reference" not in warning.getvalue()


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_function_type_params(
    app: SphinxTestApp, status: StringIO, warning: StringIO, monkeypatch: pytest.MonkeyPatch
) -> None:
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        Test
        ====

        .. autofunction:: mod.identity
    """)
    )
    monkeypatch.setitem(sys.modules, "mod", _mod_pep695)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert "Cannot resolve forward reference" not in warning.getvalue()
