from __future__ import annotations

import sys
import types
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest
from conftest import normalize_sphinx_text

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

_mod_pep695 = types.ModuleType("mod")
_mod_pep695.__file__ = __file__
exec(  # noqa: S102
    dedent("""\
    from __future__ import annotations

    type IntList = list[int]
    type StringOrInt = str | int

    def type_alias_func(x: IntList) -> StringOrInt:
        \"\"\"Function using PEP 695 type aliases.

        :param x: List of integers
        :return: String or integer
        \"\"\"
        ...

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

    class FooStringOrInt(Foo[StringOrInt]):
        \"\"\"A subclass of Foo with StringOrInt type param.\"\"\"

        def set(self, thing: StringOrInt) -> StringOrInt:
            \"\"\"Set the thing.

            :param thing: the thing
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


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_type_alias_in_function_undocumented(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that PEP 695 type aliases in function signatures
    are rendered as their literal types when the type aliases are
    not documented."""
    (Path(app.srcdir) / "index.rst").write_text(".. autofunction:: mod.type_alias_func")
    monkeypatch.setitem(sys.modules, "mod", _mod_pep695)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue().strip()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    expected = dedent("""\
        mod.type_alias_func(x)

           Function using PEP 695 type aliases.

           Parameters:
              **x** ("list"["int"]) -- List of integers

           Return type:
              "str" | "int"

           Returns:
              String or integer
        """).strip()
    assert result.strip() == normalize_sphinx_text(expected)


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_type_alias_in_function_documented(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that PEP 695 type aliases in function signatures
    are rendered as their documented type names when the type aliases
    are documented."""
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        .. py:type:: mod.IntList

           List of integers

        .. py:type:: mod.StringOrInt

           String or integer

        .. autofunction:: mod.type_alias_func
        """)
    )
    monkeypatch.setitem(sys.modules, "mod", _mod_pep695)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue().strip()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    expected = dedent("""\
        type mod.IntList

           List of integers

        type mod.StringOrInt

           String or integer

        mod.type_alias_func(x)

           Function using PEP 695 type aliases.

           Parameters:
              **x** ("IntList") -- List of integers

           Return type:
              "StringOrInt"

           Returns:
              String or integer
        """).strip()
    assert result.strip() == normalize_sphinx_text(expected)


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_type_alias_in_method_undocumented(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that PEP 695 type aliases in method signatures are
    rendered as their literal types when the type aliases are not
    documented."""
    (Path(app.srcdir) / "index.rst").write_text(".. autoclass:: mod.FooStringOrInt\n   :members:")
    monkeypatch.setitem(sys.modules, "mod", _mod_pep695)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue().strip()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    expected = dedent("""\
        class mod.FooStringOrInt(thing)

           A subclass of Foo with StringOrInt type param.

           set(thing)

              Set the thing.

              Parameters:
                 **thing** ("str" | "int") -- the thing

              Return type:
                 "str" | "int"

              Returns:
                 the thing
        """).strip()
    assert result.strip() == normalize_sphinx_text(expected)


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_type_alias_in_method_documented(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that PEP 695 type aliases in method signatures are
    rendered as their documented type names when the type aliases
    are documented."""
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        .. py:type:: mod.StringOrInt

           String or integer

        .. autoclass:: mod.FooStringOrInt
           :members:
        """)
    )
    monkeypatch.setitem(sys.modules, "mod", _mod_pep695)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue().strip()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    expected = dedent("""\
        type mod.StringOrInt

           String or integer

        class mod.FooStringOrInt(thing)

           A subclass of Foo with StringOrInt type param.

           set(thing)

              Set the thing.

              Parameters:
                 **thing** ("StringOrInt") -- the thing

              Return type:
                 "StringOrInt"

              Returns:
                 the thing
        """).strip()
    assert result.strip() == normalize_sphinx_text(expected)


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_external_type_alias(
    app: SphinxTestApp,
    status: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that external TypeAliasType renders as the alias name, not the expanded value."""
    # Define an external type alias in a private module
    ext_priv_mod = types.ModuleType("extpkg._priv")
    exec("type ExtAlias = str | int", ext_priv_mod.__dict__)  # noqa: S102
    ext_alias = ext_priv_mod.__dict__["ExtAlias"]
    # Reexport the type alias in a public module
    ext_pub_mod = types.ModuleType("extpkg")
    ext_pub_mod.ExtAlias = ext_alias  # type: ignore[attr-defined]
    # Import and use the external type alias in user module
    user_mod = types.ModuleType("user_mod")
    user_mod.__dict__["ExtAlias"] = ext_alias
    exec(  # noqa: S102
        dedent("""\
        from __future__ import annotations

        def ext_alias_func(x: ExtAlias) -> ExtAlias:
            \"\"\"Function using external type alias.

            :param x: the value
            :return: the value
            \"\"\"
            ...
        """),
        user_mod.__dict__,
    )

    (Path(app.srcdir) / "index.rst").write_text(".. autofunction:: user_mod.ext_alias_func")
    monkeypatch.setitem(sys.modules, "user_mod", user_mod)
    app.build()
    assert "build succeeded" in status.getvalue()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert '"ExtAlias"' in result
    assert '"str" | "int"' not in result
