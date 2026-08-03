from __future__ import annotations

import sys
import types
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Union
from unittest.mock import create_autospec

import pytest
from conftest import normalize_sphinx_text
from sphinx.config import Config

from sphinx_autodoc_typehints import format_annotation

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

_mod_pep695 = types.ModuleType("mod")
_mod_pep695.__file__ = __file__
exec(  # ruff:ignore[exec-builtin]
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
    exec("type ExtAlias = str | int", ext_priv_mod.__dict__)  # ruff:ignore[exec-builtin]
    ext_alias = ext_priv_mod.__dict__["ExtAlias"]
    # Reexport the type alias in a public module
    ext_pub_mod = types.ModuleType("extpkg")
    ext_pub_mod.ExtAlias = ext_alias  # type: ignore[attr-defined]
    # Import and use the external type alias in user module
    user_mod = types.ModuleType("user_mod")
    user_mod.__dict__["ExtAlias"] = ext_alias
    exec(  # ruff:ignore[exec-builtin]
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


@pytest.mark.skipif(sys.version_info < (3, 14), reason="PEP 649 lazy annotation evaluation is Python 3.14+")
@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_type_checking_only_annotation(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression test for #703: PEP 695 generic functions with TYPE_CHECKING-only annotations
    must not raise NameError during Sphinx processing."""
    mod = types.ModuleType("mod_703")
    mod.__file__ = __file__
    exec(  # ruff:ignore[exec-builtin]
        dedent("""\
        import functools
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from collections.abc import Callable

        def my_customizable_decorator[**P, R]() -> Callable[[Callable[P, R]], Callable[P, R]]:
            \"\"\"Return a decorator that wraps functions.\"\"\"
            def decorator[**P, R](func: Callable[P, R]) -> Callable[P, R]:
                @functools.wraps(func)
                def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                    return func(*args, **kwargs)
                return wrapper
            return decorator
        """),
        mod.__dict__,
    )
    (Path(app.srcdir) / "index.rst").write_text(".. autofunction:: mod_703.my_customizable_decorator")
    monkeypatch.setitem(sys.modules, "mod_703", mod)
    app.build()
    assert "build succeeded" in status.getvalue()
    # The fix prevents process_signature from throwing — a forward_reference warning
    # for unresolvable TYPE_CHECKING imports in exec'd modules is acceptable.
    assert "threw an exception" not in warning.getvalue()


UserId = Union[int, str]
RequestData = dict[str, Any]

_TYPE_ALIAS_PREAMBLE = """\
.. py:type:: mod.UserId

   A user identifier that can be either an integer or a string.

.. py:type:: mod.RequestData

   Request data dictionary.

.. autofunction:: mod.{}
"""

_TYPE_ALIAS_EXPECTED = """\
type mod.UserId

   A user identifier that can be either an integer or a string.

type mod.RequestData

   Request data dictionary.

{}
"""


def get_user(user_id: UserId) -> str:
    """
    Get a user by ID.

    Args:
        user_id: The user identifier
    """


def process_request(data: RequestData) -> bool:
    """
    Process a request.

    Args:
        data: The request data
    """


@pytest.mark.parametrize(
    ("documented", "expected_body"),
    [
        pytest.param(
            get_user,
            """\
mod.get_user(user_id)

   Get a user by ID.

   Parameters:
      **user_id** ("UserId") -- The user identifier

   Return type:
      "str"
""",
            id="get-user",
        ),
        pytest.param(
            process_request,
            """\
mod.process_request(data)

   Process a request.

   Parameters:
      **data** ("RequestData") -- The request data

   Return type:
      "bool"
""",
            id="process-request",
        ),
    ],
)
@pytest.mark.sphinx("text", testroot="integration")
def test_documented_type_alias_crossref(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
    documented: Any,
    expected_body: str,
) -> None:
    (Path(app.srcdir) / "index.rst").write_text(_TYPE_ALIAS_PREAMBLE.format(documented.__name__))
    monkeypatch.setitem(sys.modules, "mod", sys.modules[__name__])
    app.build()
    assert "build succeeded" in status.getvalue()

    value = warning.getvalue().strip()
    assert not value or "Inline strong start-string without end-string" in value

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    expected = dedent(normalize_sphinx_text(_TYPE_ALIAS_EXPECTED.format(expected_body))).strip()
    assert result.strip() == expected


@pytest.mark.sphinx("text", testroot="integration")
def test_recursive_type_alias_does_not_recurse_forever(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A self-referential PEP 695 alias builds cleanly and renders as a self cross-reference (#720)."""
    mod = types.ModuleType("mod_720")
    mod.__file__ = __file__
    exec(  # ruff:ignore[exec-builtin]
        dedent("""\
        from __future__ import annotations

        type RecType = int | list[RecType]
        \"\"\"A recursive type alias.\"\"\"

        def some_func(some_param: RecType) -> None:
            \"\"\"Describe.

            :param some_param: some description
            \"\"\"
            ...
        """),
        mod.__dict__,
    )
    (Path(app.srcdir) / "index.rst").write_text(".. autofunction:: mod_720.some_func")
    monkeypatch.setitem(sys.modules, "mod_720", mod)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue().strip()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert '"RecType"' in result


@pytest.mark.sphinx("text", testroot="integration")
def test_recursive_type_alias_from_other_module(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recursive alias imported from another module resolves to that module's target (#723)."""
    pkg = Path(app.srcdir) / "pkg_723"
    pkg.mkdir()
    (pkg / "other.py").write_text('type RecType = int | list[RecType]\n"""A recursive type alias."""\n')
    (pkg / "__init__.py").write_text(
        dedent("""\
        from pkg_723.other import RecType


        def some_func(some_param: RecType) -> None:
            \"\"\"Describe.

            :param some_param: some description
            \"\"\"
            ...
        """)
    )
    (Path(app.srcdir) / "index.rst").write_text(
        ".. automodule:: pkg_723\n   :members:\n\n.. automodule:: pkg_723.other\n   :members:\n"
    )
    monkeypatch.syspath_prepend(str(app.srcdir))
    app.config.nitpicky = True
    app.build()
    assert "build succeeded" in status.getvalue()
    assert "reference target not found" not in warning.getvalue()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert '"int" | "list"["RecType"]' in result


@pytest.mark.sphinx("text", testroot="integration")
def test_eager_annotations(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
) -> None:
    """Non-deferred annotations (no ``from __future__ import annotations``) also resolve."""
    template = """\
.. py:type:: mod_eager.UserId

   A user identifier.

.. autofunction:: mod_eager.get_user_eager
"""
    (Path(app.srcdir) / "index.rst").write_text(template)
    app.build()
    assert "build succeeded" in status.getvalue()

    value = warning.getvalue().strip()
    assert not value or "Inline strong start-string without end-string" in value

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert '"UserId"' in result


@pytest.mark.skipif(sys.version_info < (3, 14), reason="annotationlib requires Python 3.14+")
@pytest.mark.sphinx("text", testroot="integration")
def test_forward_ref_builds_without_errors(  # pragma: >=3.14 cover
    app: SphinxTestApp,
    status: StringIO,
) -> None:
    """Forward-referencing module builds cleanly on 3.14+ using annotationlib."""
    (Path(app.srcdir) / "index.rst").write_text(".. autoclass:: mod_forward_ref.Tree\n   :members:\n")
    app.build()
    assert "build succeeded" in status.getvalue()
    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert "Tree" in result


@pytest.mark.skipif(sys.version_info < (3, 14), reason="PEP 649 lazy annotation evaluation is Python 3.14+")
@pytest.mark.sphinx("text", testroot="integration")
def test_non_subscriptable_generic_annotation(  # pragma: >=3.14 cover
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression test for #712: annotations whose lazy evaluation raises (here TypeError from
    subscripting a non-generic class) must not crash the build; the hint degrades to its source text."""
    mod = types.ModuleType("mod_712")
    mod.__file__ = __file__
    source = dedent("""\
    class DiGraph:
        pass


    def add_node_between_nodes(g: DiGraph[int]) -> None:
        \"\"\"Stub.\"\"\"
    """)
    # dont_inherit keeps this file's `from __future__ import annotations` (PEP 563) out of the
    # compiled module so its annotations stay lazily evaluated (PEP 649)
    exec(compile(source, "<mod_712>", "exec", dont_inherit=True), mod.__dict__)  # ruff:ignore[exec-builtin]
    (Path(app.srcdir) / "index.rst").write_text(".. autofunction:: mod_712.add_node_between_nodes")
    monkeypatch.setitem(sys.modules, "mod_712", mod)
    app.config.__dict__["always_document_param_types"] = True
    app.build()
    assert "build succeeded" in status.getvalue()
    assert "threw an exception" not in warning.getvalue()
    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert "DiGraph[int]" in result


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_generic_type_alias_undocumented(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A subscripted generic alias expands to its value with the type params substituted."""
    mod = types.ModuleType("mod_generic_alias")
    mod.__file__ = __file__
    exec(  # ruff:ignore[exec-builtin]
        dedent("""\
        from __future__ import annotations

        type Pair[T] = tuple[T, T]

        def pair_func(x: Pair[int]) -> None:
            \"\"\"Describe.

            :param x: a pair
            \"\"\"
            ...
        """),
        mod.__dict__,
    )
    (Path(app.srcdir) / "index.rst").write_text(".. autofunction:: mod_generic_alias.pair_func")
    monkeypatch.setitem(sys.modules, "mod_generic_alias", mod)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue().strip()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert '"tuple"["int", "int"]' in result


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_generic_type_alias_documented(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A subscripted generic alias cross-references the alias and keeps its args."""
    mod = types.ModuleType("mod_generic_alias_doc")
    mod.__file__ = __file__
    exec(  # ruff:ignore[exec-builtin]
        dedent("""\
        from __future__ import annotations

        type Pair[T] = tuple[T, T]
        \"\"\"A pair of things.\"\"\"

        def pair_func(x: Pair[int]) -> None:
            \"\"\"Describe.

            :param x: a pair
            \"\"\"
            ...
        """),
        mod.__dict__,
    )
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
        .. py:type:: mod_generic_alias_doc.Pair

           A pair of things

        .. autofunction:: mod_generic_alias_doc.pair_func
        """)
    )
    monkeypatch.setitem(sys.modules, "mod_generic_alias_doc", mod)
    app.config.nitpicky = True
    app.build()
    assert "build succeeded" in status.getvalue()
    assert "reference target not found" not in warning.getvalue()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert '"Pair"["int"]' in result


@pytest.mark.sphinx("text", testroot="integration")
def test_pep695_external_generic_type_alias(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A subscripted generic alias from another package resolves to its canonical public name.

    This is ``numpy.typing.NDArray[np.void]``: an alias defined in a private module, re-exported from a
    public one, used subscripted. Without unwrapping the subscription it renders as ``GenericAlias``.
    """
    ext_priv_mod = types.ModuleType("extpkg2._priv")
    exec("type ExtPair[T] = tuple[T, T]", ext_priv_mod.__dict__)  # ruff:ignore[exec-builtin]
    ext_alias = ext_priv_mod.__dict__["ExtPair"]
    ext_pub_mod = types.ModuleType("extpkg2")
    ext_pub_mod.ExtPair = ext_alias  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "extpkg2._priv", ext_priv_mod)
    monkeypatch.setitem(sys.modules, "extpkg2", ext_pub_mod)

    user_mod = types.ModuleType("user_mod_generic")
    user_mod.__dict__["ExtPair"] = ext_alias
    exec(  # ruff:ignore[exec-builtin]
        dedent("""\
        from __future__ import annotations

        def ext_pair_func(x: ExtPair[int]) -> None:
            \"\"\"Describe.

            :param x: a pair
            \"\"\"
            ...
        """),
        user_mod.__dict__,
    )
    (Path(app.srcdir) / "index.rst").write_text(".. autofunction:: user_mod_generic.ext_pair_func")
    monkeypatch.setitem(sys.modules, "user_mod_generic", user_mod)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert "GenericAlias" not in warning.getvalue()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert '"ExtPair"["int"]' in result
    assert "GenericAlias" not in result


@pytest.mark.sphinx("text", testroot="integration")
def test_recursive_generic_type_alias_does_not_recurse_forever(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A generic alias that references itself through its subscripted form builds cleanly."""
    mod = types.ModuleType("mod_rec_generic")
    mod.__file__ = __file__
    exec(  # ruff:ignore[exec-builtin]
        dedent("""\
        from __future__ import annotations

        type RecPair[T] = T | list[RecPair[T]]
        \"\"\"A recursive generic type alias.\"\"\"

        def some_func(some_param: RecPair[int]) -> None:
            \"\"\"Describe.

            :param some_param: some description
            \"\"\"
            ...
        """),
        mod.__dict__,
    )
    (Path(app.srcdir) / "index.rst").write_text(".. autofunction:: mod_rec_generic.some_func")
    monkeypatch.setitem(sys.modules, "mod_rec_generic", mod)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue().strip()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert '"RecPair"' in result


_mod_generic_edge = types.ModuleType("mod_generic_edge")
_mod_generic_edge.__file__ = __file__
exec(  # ruff:ignore[exec-builtin]
    dedent("""\
    type Ident[X] = X
    type Count[X] = int
    type Nested[X] = list[Ident[X]]
    type Pair[A, B] = tuple[A, B]
    type Star[*Ts] = tuple[*Ts]
    """),
    _mod_generic_edge.__dict__,
)
_ALIAS_XREF = r":py:type:`~mod_generic_edge.Pair`"


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(_mod_generic_edge.Ident[int], r":py:class:`int`", id="value_is_a_bare_type_param"),
        pytest.param(_mod_generic_edge.Count[int], r":py:class:`int`", id="value_ignores_its_type_param"),
        pytest.param(
            _mod_generic_edge.Nested[int],
            r":py:class:`list`\ \[:py:class:`int`]",
            id="value_wraps_another_alias",
        ),
        pytest.param(
            _mod_generic_edge.Star[int, str],
            r":py:class:`tuple`\ \[:py:class:`int`, :py:class:`str`]",
            id="variadic_type_param",
        ),
        pytest.param(
            _mod_generic_edge.Pair[int],
            _ALIAS_XREF + r"\ \[:py:class:`int`]",
            id="too_few_args",
        ),
        pytest.param(
            _mod_generic_edge.Pair[int, str, bool],
            _ALIAS_XREF + r"\ \[:py:class:`int`, :py:class:`str`, :py:class:`bool`]",
            id="too_many_args",
        ),
    ],
)
def test_undocumented_generic_alias_substitution(annotation: Any, expected: str) -> None:
    """An undocumented generic alias expands its value, unless the subscript arity rules that out."""
    assert format_annotation(annotation, create_autospec(Config)) == expected
