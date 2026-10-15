from __future__ import annotations

import ast
import importlib
import inspect
import os
import shutil
import subprocess  # ruff:ignore[suspicious-subprocess-import]
import sys
import sysconfig
import textwrap
import types
from collections.abc import Sequence
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional
from unittest.mock import MagicMock, patch

import pytest
from conftest import normalize_sphinx_text
from sphinx.ext.autodoc.mock import ismockmodule

from sphinx_autodoc_typehints._resolver import get_all_type_hints
from sphinx_autodoc_typehints._resolver._stubs import (
    _STUB_AST_CACHE,
    _backfill_from_stub,
    _extract_annotations_from_stub,
    _extract_class_annotations,
    _extract_func_annotations,
    _extract_type_alias_names,
    _find_ast_node,
    _find_native_submodule_stub,
    _find_stub_for_module,
    _find_stub_owner,
    _get_module,
    _get_stub_context,
    _parse_stub_ast,
    _resolve_import_from,
    _resolve_stub_imports,
    _stub_owner_package,
    stub_path,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

STUB_ROOT = Path(__file__).parent.parent / "roots" / "test-pyi-stubs"


def _import_stub_mod() -> types.ModuleType:
    import stub_mod  # ruff:ignore[import-outside-top-level]  # ty: ignore[unresolved-import]

    return stub_mod


@pytest.fixture
def stub_mod() -> Any:
    sys.path.insert(0, str(STUB_ROOT))
    try:
        yield _import_stub_mod()
    finally:
        sys.path.pop(0)
        sys.modules.pop("stub_mod", None)


def teststub_path_locates_sibling_pyi(stub_mod: Any) -> None:
    result = stub_path(stub_mod.greet)
    assert result is not None
    assert result.suffix == ".pyi"
    assert result.stem == "stub_mod"


def teststub_path_returns_none_for_no_stub() -> None:
    assert stub_path(teststub_path_returns_none_for_no_stub) is None


def teststub_path_returns_none_for_no_module() -> None:
    obj = MagicMock(spec=[])
    obj.__module__ = None
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=None):
        assert stub_path(obj) is None


def teststub_path_returns_none_for_module_without_file() -> None:
    module = types.ModuleType("fake_mod")
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module):
        assert stub_path(lambda: None) is None


@pytest.mark.parametrize(
    "ext_filename",
    [
        pytest.param("_mod.cpython-312-x86_64-linux-gnu.so", id="cpython_linux"),
        pytest.param("_mod.cpython-313-darwin.so", id="cpython_darwin"),
        pytest.param("_mod.cpython-314t-x86_64-linux-gnu.so", id="cpython_free_threaded"),
        pytest.param("_mod.cpython-314d-x86_64-linux-gnu.so", id="cpython_debug"),
        pytest.param("_mod.cpython-314-aarch64-linux-musl.so", id="cpython_musl"),
        pytest.param("_mod.abi3.so", id="abi3_stable"),
        pytest.param("_mod.so", id="simple_so"),
        pytest.param("_mod.pyd", id="windows_pyd"),
        pytest.param("_mod.cp314-win_amd64.pyd", id="windows_tagged_pyd"),
        pytest.param("_mod.dll", id="cygwin_dll"),
        pytest.param("_mod.pypy39-pp73-x86_64-linux-gnu.so", id="pypy"),
    ],
)
def teststub_path_extension_module(tmp_path: Path, ext_filename: str) -> None:
    (tmp_path / ext_filename).write_bytes(b"")
    (tmp_path / "_mod.pyi").write_text("def f(x: int) -> None: ...\n")
    module = types.ModuleType("_mod")
    module.__file__ = str(tmp_path / ext_filename)
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module):
        result = stub_path(lambda: None)
    assert result is not None
    assert result.name == "_mod.pyi"


def teststub_path_extension_module_no_stub(tmp_path: Path) -> None:
    ext_filename = "_mod.cpython-312-x86_64-linux-gnu.so"
    (tmp_path / ext_filename).write_bytes(b"")
    module = types.ModuleType("_mod")
    module.__file__ = str(tmp_path / ext_filename)
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module):
        assert stub_path(lambda: None) is None


def teststub_path_extension_module_package_fallback(tmp_path: Path) -> None:
    ext_filename = "_mod.cpython-312-x86_64-linux-gnu.so"
    (tmp_path / ext_filename).write_bytes(b"")
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    (stub_dir / "__init__.pyi").write_text("x: int\n")
    module = types.ModuleType("_mod")
    module.__file__ = str(tmp_path / ext_filename)
    module.__path__ = [str(stub_dir)]
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module):
        result = stub_path(lambda: None)
    assert result is not None
    assert result.name == "__init__.pyi"


class _ProxyModule(types.ModuleType):
    """A module subclass reporting where it lives through properties, as module proxies do."""

    def __init__(self, name: str, file: str, path: list[str] | None) -> None:
        super().__init__(name)
        self.location = file, path

    @property
    def __file__(self) -> str:  # ruff:ignore[bad-dunder-method-name]  # the module attribute a proxy reports
        return self.location[0]

    @property
    def __path__(self) -> list[str]:  # ruff:ignore[bad-dunder-method-name]  # the module attribute a proxy reports
        # a proxy for a plain module, which is no package
        if (path := self.location[1]) is None:
            msg = "__path__"
            raise AttributeError(msg)
        return path


@pytest.mark.parametrize(
    ("stub", "package_dir"),
    [
        pytest.param("_mod.pyi", None, id="beside-file"),
        pytest.param("stubs/__init__.pyi", "stubs", id="in-package-path"),
    ],
)
def teststub_path_reads_module_properties(tmp_path: Path, stub: str, package_dir: str | None) -> None:
    (tmp_path / "stubs").mkdir()
    (tmp_path / stub).write_text("x: int\n")
    module = _ProxyModule(
        "_mod", str(tmp_path / "_mod.py"), None if package_dir is None else [str(tmp_path / package_dir)]
    )
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module):
        assert stub_path(lambda: None) == tmp_path / stub


def teststub_path_skips_package_path_property_that_raises(tmp_path: Path) -> None:
    module = _ProxyModule("_mod", str(tmp_path / "_mod.py"), None)
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module):
        assert stub_path(lambda: None) is None


def teststub_path_package_init_pyi(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    no_stub_dir = tmp_path / "no_stubs"
    no_stub_dir.mkdir()
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    (stub_dir / "__init__.pyi").write_text("x: int\n")
    module = types.ModuleType("mypkg")
    module.__path__ = [str(no_stub_dir), str(stub_dir)]
    module.__file__ = str(pkg_dir / "__init__.py")
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module):
        result = stub_path(module)
    assert result is not None
    assert result.name == "__init__.pyi"


def teststub_path_package_no_init_pyi(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    module = types.ModuleType("mypkg")
    module.__path__ = [str(pkg_dir)]
    module.__file__ = str(pkg_dir / "__init__.py")
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module):
        assert stub_path(module) is None


def test_parse_stub_ast_valid_file() -> None:
    stub_path = STUB_ROOT / "stub_mod.pyi"
    result = _parse_stub_ast(stub_path)
    assert isinstance(result, ast.Module)


def test_parse_stub_ast_caches_result() -> None:
    stub = STUB_ROOT / "stub_mod.pyi"
    assert _parse_stub_ast(stub) is _parse_stub_ast(stub)


def test_parse_stub_ast_reads_an_edited_stub_again(tmp_path: Path) -> None:
    stub = tmp_path / "edited.pyi"
    stub.write_text("def run(a: int) -> None: ...\n")
    _parse_stub_ast(stub)
    stub.write_text("def run(a: bytes) -> None: ...\n")
    modified = stub.stat().st_mtime_ns + 1_000_000
    os.utime(stub, ns=(modified, modified))
    tree = _parse_stub_ast(stub)
    assert tree is not None
    assert ast.unparse(tree) == "def run(a: bytes) -> None:\n    ..."


def test_parse_stub_ast_returns_none_for_bad_syntax(tmp_path: Path) -> None:
    bad_stub = tmp_path / "bad.pyi"
    bad_stub.write_text("def (broken syntax\n")
    assert _parse_stub_ast(bad_stub) is None


def test_parse_stub_ast_returns_none_for_missing_file() -> None:
    assert _parse_stub_ast(Path("/nonexistent/stub.pyi")) is None


@pytest.mark.parametrize(
    ("source", "parts", "expected_type", "expected_name"),
    [
        pytest.param("def foo(x: int) -> str: ...", ["foo"], ast.FunctionDef, "foo", id="top_level_function"),
        pytest.param(
            "class Outer:\n  class Inner:\n    def method(self) -> None: ...",
            ["Outer", "Inner", "method"],
            ast.FunctionDef,
            "method",
            id="nested_class_method",
        ),
        pytest.param("class Foo:\n  x: int\n", ["Foo"], ast.ClassDef, "Foo", id="class"),
        pytest.param("def foo(): ...", ["bar"], None, None, id="missing"),
    ],
)
def test_find_ast_node(
    source: str, parts: list[str], expected_type: type[ast.stmt] | None, expected_name: str | None
) -> None:
    tree = ast.parse(source)
    node = _find_ast_node(tree.body, parts)
    if expected_type is None:
        assert node is None
    else:
        assert isinstance(node, expected_type)
        assert node.name == expected_name  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            "def greet(name: str, greeting: str) -> str: ...",
            {"name": "str", "greeting": "str", "return": "str"},
            id="basic",
        ),
        pytest.param("def f(x: int): ...", {"x": "int"}, id="no_return"),
        pytest.param("async def fetch(url: str) -> str: ...", {"url": "str", "return": "str"}, id="async"),
        pytest.param("def f(self, x: int) -> None: ...", {"x": "int", "return": "None"}, id="skips_unannotated"),
    ],
)
def test_extract_func_annotations(source: str, expected: dict[str, str]) -> None:
    node = ast.parse(source).body[0]
    assert isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    assert _extract_func_annotations(node) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("class Foo:\n  x: int\n  y: str\n", {"x": "int", "y": "str"}, id="basic"),
        pytest.param("class Foo:\n  x: int\n  self.y: str\n", {"x": "int"}, id="ignores_non_name_targets"),
    ],
)
def test_extract_class_annotations(source: str, expected: dict[str, str]) -> None:
    node = ast.parse(source).body[0]
    assert isinstance(node, ast.ClassDef)
    assert _extract_class_annotations(node) == expected


@pytest.mark.parametrize(
    ("source", "qualname", "expected"),
    [
        pytest.param(
            "def greet(name: str, greeting: str) -> str: ...",
            "greet",
            {"name": "str", "greeting": "str", "return": "str"},
            id="function",
        ),
        pytest.param("class Foo:\n  x: int\n  y: str\n", "Foo", {"x": "int", "y": "str"}, id="class"),
        pytest.param(
            "class Foo:\n  def __new__(cls, x: int) -> Foo: ...\n",
            "Foo.__new__",
            {"x": "int", "return": "Foo"},
            id="class_new",
        ),
        pytest.param("def greet(name: str) -> str: ...", "nonexistent", {}, id="missing_node"),
        pytest.param("x: int = 1\n", "x", {}, id="unsupported_node_type"),
    ],
)
def test_extract_annotations_from_stub(source: str, qualname: str, expected: dict[str, str]) -> None:
    tree = ast.parse(source)
    obj = MagicMock()
    obj.__qualname__ = qualname
    assert _extract_annotations_from_stub(tree, obj) == expected


def test_extract_annotations_from_stub_no_qualname() -> None:
    tree = ast.parse("def greet(name: str) -> str: ...")
    obj = MagicMock(spec=[])
    assert _extract_annotations_from_stub(tree, obj) == {}


@pytest.mark.parametrize(
    ("attr", "expected"),
    [
        pytest.param("greet", {"name": "str", "greeting": "str", "return": "str"}, id="function"),
        pytest.param("Calculator.Inner.process", {"data": "bytes", "return": "bytes"}, id="nested_class"),
        pytest.param("Converter.__new__", {"output": "str", "return": "Converter"}, id="class_new"),
        pytest.param("fetch", {"url": "str", "return": "str"}, id="async_function"),
        pytest.param("transform", {"value": "Sequence[int]", "return": "list[str]"}, id="typing_imports"),
    ],
)
def test_backfill_from_stub(stub_mod: Any, attr: str, expected: dict[str, str]) -> None:
    obj = stub_mod
    for part in attr.split("."):
        obj = getattr(obj, part)
    assert _backfill_from_stub(obj) == expected


@pytest.mark.parametrize(
    ("attr", "expected"),
    [
        pytest.param("version_gated", {"value": int, "return": bytes}, id="version-gated"),
        pytest.param("overloaded", {"value": int | str, "return": int | str}, id="overloaded"),
        pytest.param("extras_only", {"value": float, "return": float}, id="undecidable-condition"),
        pytest.param("Box.size.fget", {"return": int}, id="property-with-setter-and-deleter"),
    ],
)
def test_get_all_type_hints_reads_stub_variants(stub_mod: Any, attr: str, expected: dict[str, type]) -> None:
    assert get_all_type_hints([], attrgetter(attr)(stub_mod), f"stub_mod.{attr}", {}) == expected


@pytest.mark.parametrize(
    ("reexported", "expected"),
    [
        pytest.param(True, {"names": Sequence[str], "count": int, "return": str}, id="reexported"),
        pytest.param(False, {}, id="only-named-alike"),
    ],
)
def test_get_all_type_hints_reads_parent_stub_only_for_reexports(
    native_package: tuple[types.ModuleType, types.ModuleType], reexported: bool, expected: dict[str, Any]
) -> None:
    def greet(names: int, count: int) -> None: ...

    greet.__annotations__.clear()  # a native function carries no annotations of its own
    parent, child = native_package
    greet.__module__, greet.__qualname__ = child.__name__, "greet"
    child.greet = greet  # type: ignore[attr-defined]
    if reexported:
        parent.greet = greet  # type: ignore[attr-defined]
    assert get_all_type_hints([], greet, "mypkg.greet", {}) == expected


@pytest.fixture
def native_package(tmp_path: Path) -> Iterator[tuple[types.ModuleType, types.ModuleType]]:
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "__init__.pyi").write_text(
        "from collections.abc import Sequence\n\ndef greet(names: Sequence[str], count: Alias) -> str: ...\n"
    )
    ext_file = pkg_dir / "_ext.cpython-314-darwin.so"
    ext_file.write_bytes(b"")
    parent = types.ModuleType("mypkg")
    parent.__file__ = str(pkg_dir / "__init__.py")
    parent.__path__ = [str(pkg_dir)]
    parent.Alias = int  # type: ignore[attr-defined]
    child = types.ModuleType("mypkg._ext")
    child.__file__ = str(ext_file)
    with patch.dict(sys.modules, {"mypkg": parent, "mypkg._ext": child}):
        yield parent, child


@pytest.mark.parametrize(
    ("stub_import", "annotation"),
    [
        pytest.param("import subpkg.extra", "subpkg.extra.Extra", id="import"),
        pytest.param("from . import extra", "extra.Extra", id="from-import"),
    ],
)
def test_get_all_type_hints_imports_stub_submodules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_import: str, annotation: str
) -> None:
    (pkg_dir := tmp_path / "subpkg").mkdir()
    (pkg_dir / "__init__.py").write_text("def load(src): ...\n")
    (pkg_dir / "__init__.pyi").write_text(f"{stub_import}\n\ndef load(src: {annotation}) -> int: ...\n")
    (pkg_dir / "extra.py").write_text("class Extra: ...\n")
    monkeypatch.syspath_prepend(tmp_path)
    with patch.dict(sys.modules):
        load = importlib.import_module("subpkg").load
        hints = get_all_type_hints([], load, "subpkg.load", {})
        assert hints == {"src": importlib.import_module("subpkg.extra").Extra, "return": int}


def test_backfill_from_stub_no_stub() -> None:
    assert _backfill_from_stub(test_backfill_from_stub_no_stub) == {}


@pytest.mark.parametrize(
    ("source", "expected", "expected_unresolved"),
    [
        pytest.param("import os\nimport sys\n", {"os": os, "sys": sys}, set(), id="basic_import"),
        pytest.param("import os as operating_system\n", {"operating_system": os}, set(), id="import_as"),
        pytest.param("import os.path\n", {"os": os}, set(), id="dotted_import"),
        pytest.param("from typing import Optional, Any\n", {"Optional": Optional, "Any": Any}, set(), id="from_import"),
        pytest.param("from typing import Optional as Opt\n", {"Opt": Optional}, set(), id="from_import_as"),
        pytest.param("from typing import *\n", {}, set(), id="star_import_skipped"),
        pytest.param("from nonexistent_abc import Foo\n", {}, {"Foo"}, id="missing_module_from_import"),
        pytest.param("from typing import NonExistentThing\n", {}, {"NonExistentThing"}, id="missing_attr"),
    ],
)
def test_resolve_stub_imports(source: str, expected: dict[str, Any], expected_unresolved: set[str]) -> None:
    ns, unresolved = _resolve_stub_imports(ast.parse(source))
    for key, val in expected.items():
        assert ns[key] is val
    if not expected:
        assert ns == {}
    assert unresolved == expected_unresolved


@pytest.mark.parametrize(
    ("source", "name"),
    [
        pytest.param("import nonexistent_xyz\n", "nonexistent_xyz", id="module"),
        pytest.param("import nonexistent_xyz.sub\n", "nonexistent_xyz", id="dotted"),
        pytest.param("import nonexistent_xyz as missing\n", "missing", id="aliased"),
    ],
)
def test_resolve_stub_imports_mocks_a_missing_module(source: str, name: str) -> None:
    ns, _ = _resolve_stub_imports(ast.parse(source))
    assert ismockmodule(ns[name])


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("import nonexistent_dependency_xyz\n", id="missing-dependency"),
        pytest.param("raise ImportError('broken')\n", id="import-error"),
    ],
)
def test_resolve_stub_imports_skips_an_installed_module_that_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str
) -> None:
    (tmp_path / "fails_to_import.py").write_text(body)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "fails_to_import", raising=False)
    assert _resolve_stub_imports(ast.parse("import fails_to_import\n")) == ({}, set())


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            "from typing import TypeAlias\nFoo: TypeAlias = int\n",
            {"Foo"},
            id="typing_TypeAlias",
        ),
        pytest.param(
            "import typing\nBar: typing.TypeAlias = str\n",
            {"Bar"},
            id="qualified_TypeAlias",
        ),
        pytest.param(
            "from typing_extensions import TypeAlias\nQux: TypeAlias = int\n",
            {"Qux"},
            id="typing_extensions_TypeAlias",
        ),
        pytest.param(
            "import typing_extensions\nQuux: typing_extensions.TypeAlias = str\n",
            {"Quux"},
            id="qualified_typing_extensions_TypeAlias",
        ),
        pytest.param(
            "type Baz = int | str\n",
            {"Baz"},
            id="type_statement",
        ),
        pytest.param(
            "x: int = 1\ndef f(): ...\n",
            set(),
            id="no_aliases",
        ),
    ],
)
def test_extract_type_alias_names(source: str, expected: set[str]) -> None:
    assert _extract_type_alias_names(ast.parse(source)) == expected


def test_get_stub_context_returns_aliases(stub_mod: Any) -> None:
    ns, names, owner = _get_stub_context(stub_mod.greet)
    assert "MyAlias" in names
    assert ns["Sequence"] is Sequence
    assert owner == "stub_mod"


def test_get_stub_context_returns_empty_for_no_stub() -> None:
    ns, names, owner = _get_stub_context(test_get_stub_context_returns_empty_for_no_stub)
    assert ns == {}
    assert names == set()
    assert not owner


def test_get_stub_context_returns_empty_for_bad_syntax(stub_mod: Any, tmp_path: Path) -> None:
    bad_stub = tmp_path / "stub_mod.pyi"
    bad_stub.write_text("def (broken syntax\n")
    with patch("sphinx_autodoc_typehints._resolver._stubs._find_stub_owner", return_value=(bad_stub, stub_mod)):
        ns, names, owner = _get_stub_context(stub_mod.greet)
    assert ns == {}
    assert names == set()
    assert not owner


@pytest.mark.sphinx("text", testroot="pyi-stubs")
def test_sphinx_build_uses_stub_types(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    template = """\
.. autofunction:: stub_mod.greet

.. autoclass:: stub_mod.Calculator
   :members:

.. autoclass:: stub_mod.Converter
   :members:

.. autofunction:: stub_mod.fetch

.. autofunction:: stub_mod.transform
"""
    (Path(app.srcdir) / "index.rst").write_text(template)
    app.build()
    assert "build succeeded" in status.getvalue()
    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert "str" in result
    assert "list" in result
    warn_text = warning.getvalue()
    assert "stub_mod" not in warn_text or "forward reference" not in warn_text
    sys.modules.pop("stub_mod", None)


@pytest.mark.sphinx("text", testroot="pyi-stubs")
def test_sphinx_build_class_new_uses_param_not_class_var(app: SphinxTestApp, status: StringIO) -> None:
    template = """\
.. autoclass:: stub_mod.Converter
   :members:
"""
    (Path(app.srcdir) / "index.rst").write_text(template)
    app.build()
    assert "build succeeded" in status.getvalue()
    result = (Path(app.srcdir) / "_build/text/index.txt").read_text()
    assert '"str"' in result
    sys.modules.pop("stub_mod", None)


@pytest.mark.sphinx("pseudoxml", testroot="pyi-stubs")
def test_sphinx_build_stub_types_produce_crossrefs(app: SphinxTestApp, status: StringIO) -> None:
    template = """\
.. autofunction:: stub_mod.transform
"""
    (Path(app.srcdir) / "index.rst").write_text(template)
    app.build()
    assert "build succeeded" in status.getvalue()
    result = (Path(app.srcdir) / "_build/pseudoxml/index.pseudoxml").read_text()
    assert 'classes="xref py py-class"' in result
    assert "docs.python.org" in result


def test_find_stub_for_module_returns_none_without_file() -> None:
    assert _find_stub_for_module(types.ModuleType("fake")) is None


def test_get_module_returns_inspected_module() -> None:
    assert _get_module(test_get_module_returns_inspected_module) is sys.modules[__name__]


def test_get_module_falls_back_to_dunder_module() -> None:
    obj = MagicMock(spec=[])
    obj.__module__ = "sys"
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=None):
        assert _get_module(obj) is sys


def test_get_module_falls_back_to_objclass() -> None:
    owner = MagicMock()
    obj = type("FakeDescriptor", (), {"__objclass__": owner, "__module__": "nonexistent_xyz"})()
    with patch(
        "sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", side_effect=[None, sys.modules[__name__]]
    ):
        assert _get_module(obj) is sys.modules[__name__]


def test_get_module_falls_back_to_self_class() -> None:
    class _FakeClass:
        pass

    obj = MagicMock(spec=[])
    obj.__module__ = None
    obj.__self__ = _FakeClass
    with patch(
        "sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", side_effect=[None, sys.modules[__name__]]
    ):
        assert _get_module(obj) is sys.modules[__name__]


def test_get_module_returns_none_when_all_fail() -> None:
    obj = type("Opaque", (), {"__module__": "nonexistent_xyz"})()
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=None):
        assert _get_module(obj) is None


@pytest.mark.parametrize(
    ("source", "owner_package", "expected"),
    [
        pytest.param("from typing import Any", "", "typing", id="absolute"),
        pytest.param("from .typing import ColorType", "matplotlib", "matplotlib.typing", id="rel_level1"),
        pytest.param("from . import utils", "matplotlib", "matplotlib", id="rel_level1_bare"),
        pytest.param("from ..typing import X", "matplotlib.figure", "matplotlib.typing", id="rel_level2"),
        pytest.param("from .sub import Y", "", "sub", id="rel_no_package"),
    ],
)
def test_resolve_import_from(source: str, owner_package: str, expected: str) -> None:
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.ImportFrom)
    assert _resolve_import_from(node, owner_package) == expected


def test_resolve_import_from_level_beyond_package() -> None:
    node = ast.parse("from ...x import Y").body[0]
    assert isinstance(node, ast.ImportFrom)
    assert _resolve_import_from(node, "a") is None


def test_resolve_stub_imports_handles_conditional_blocks() -> None:
    source = textwrap.dedent("""\
        import os
        if sys.version_info >= (3, 11):
            from typing import Self
        else:
            from typing_extensions import Self
    """)
    tree = ast.parse(source)
    ns, _ = _resolve_stub_imports(tree, "")
    assert "os" in ns
    assert "Self" in ns


def test_resolve_stub_definitions_evaluates_typevars_and_classes() -> None:
    source = textwrap.dedent("""\
        from typing import TypeVar, TypedDict
        _T = TypeVar("_T")
        class MyDict(TypedDict):
            x: int
    """)
    tree = ast.parse(source)
    ns, _ = _resolve_stub_imports(tree, "")
    assert "_T" in ns
    assert "MyDict" in ns


def test_resolve_stub_imports_relative() -> None:
    source = "from .typing import ColorType\nfrom typing import Any\n"
    tree = ast.parse(source)
    # matplotlib.typing.ColorType is a type alias, check it resolves to something
    ns, _ = _resolve_stub_imports(tree, "matplotlib")
    assert "Any" in ns
    assert ns["Any"] is Any


def test_get_stub_context_resolves_relative_imports(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "relpkg"
    pkg_dir.mkdir()
    sub_dir = pkg_dir / "sub"
    sub_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (sub_dir / "__init__.py").write_text("")
    (sub_dir / "mod.py").write_text("class Cls:\n    pass\n")
    (sub_dir / "mod.pyi").write_text("from typing import Any\nfrom ..helpers import Helper\nclass Cls:\n    x: Any\n")
    (pkg_dir / "helpers.py").write_text("class Helper:\n    pass\n")

    sys.path.insert(0, str(tmp_path))
    try:
        import relpkg.sub.mod  # ruff:ignore[import-outside-top-level]  # ty: ignore[unresolved-import]

        ns, _names, owner = _get_stub_context(relpkg.sub.mod.Cls)
        assert owner == "relpkg.sub.mod"
        assert "Helper" in ns
    finally:
        sys.path.pop(0)
        for mod_name in [k for k in sys.modules if k.startswith("relpkg")]:
            sys.modules.pop(mod_name, None)
        _STUB_AST_CACHE.clear()


@pytest.mark.parametrize(
    ("owner_name", "package_attr", "stub_name", "expected"),
    [
        pytest.param("pkg", "pkg", "__init__.pyi", "pkg", id="package_with_attr"),
        pytest.param("pkg.warc", None, "warc.pyi", "pkg", id="native_module_no_attr"),
        pytest.param("pkg.sub", None, "__init__.pyi", "pkg.sub", id="native_subpackage_no_attr"),
        pytest.param("solo", "", "solo.pyi", "", id="top_level_module"),
        pytest.param("a.b.c", None, "c.pyi", "a.b", id="deep_module"),
    ],
)
def test_stub_owner_package(owner_name: str, package_attr: str | None, stub_name: str, expected: str) -> None:
    module = types.ModuleType(owner_name)
    if package_attr is None:
        del module.__package__
    else:
        module.__package__ = package_attr
    assert _stub_owner_package(module, Path(stub_name)) == expected


@pytest.fixture(scope="module")
def native_subpkg_layout(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[Path, types.ModuleType, types.ModuleType]]:
    root = tmp_path_factory.mktemp("native_subpkg")
    pkg_dir = root / "natpkg_edge"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "warc.pyi").write_text(
        textwrap.dedent("""\
            class WarcRecord:
                record_id: str
        """)
    )
    parent = types.ModuleType("natpkg_edge")
    parent.__file__ = str(pkg_dir / "__init__.py")
    parent.__path__ = [str(pkg_dir)]
    child = types.ModuleType("natpkg_edge.warc")
    yield pkg_dir, parent, child
    _STUB_AST_CACHE.clear()


def test_find_native_submodule_stub_sibling_pyi(
    native_subpkg_layout: tuple[Path, types.ModuleType, types.ModuleType],
) -> None:
    _, parent, child = native_subpkg_layout
    with patch.dict(sys.modules, {"natpkg_edge": parent, "natpkg_edge.warc": child}):
        result = _find_native_submodule_stub(child)
    assert result is not None
    assert result.name == "warc.pyi"


def test_find_native_submodule_stub_subpackage_init_pyi(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "natpkg_sub"
    pkg_dir.mkdir()
    sub_stub_dir = pkg_dir / "sub"
    sub_stub_dir.mkdir()
    (sub_stub_dir / "__init__.pyi").write_text("x: int\n")
    parent = types.ModuleType("natpkg_sub")
    parent.__path__ = [str(pkg_dir)]
    child = types.ModuleType("natpkg_sub.sub")
    with patch.dict(sys.modules, {"natpkg_sub": parent, "natpkg_sub.sub": child}):
        result = _find_native_submodule_stub(child)
    assert result is not None
    assert result.name == "__init__.pyi"
    assert result.parent.name == "sub"


@pytest.mark.parametrize(
    "module_name",
    [
        pytest.param("top_level_native", id="no_dot_in_name"),
        pytest.param("absent.child", id="parent_missing_in_sys_modules"),
    ],
)
def test_find_native_submodule_stub_returns_none_without_parent(module_name: str) -> None:
    sys.modules.pop(module_name.partition(".")[0], None)
    assert _find_native_submodule_stub(types.ModuleType(module_name)) is None


def test_find_native_submodule_stub_parent_without_path(tmp_path: Path) -> None:
    parent = types.ModuleType("flat_native")
    parent.__file__ = str(tmp_path / "flat.py")
    child = types.ModuleType("flat_native.child")
    with patch.dict(sys.modules, {"flat_native": parent, "flat_native.child": child}):
        assert _find_native_submodule_stub(child) is None


def test_find_native_submodule_stub_no_matching_stub(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "natpkg_empty"
    pkg_dir.mkdir()
    parent = types.ModuleType("natpkg_empty")
    parent.__path__ = [str(pkg_dir)]
    child = types.ModuleType("natpkg_empty.missing")
    with patch.dict(sys.modules, {"natpkg_empty": parent, "natpkg_empty.missing": child}):
        assert _find_native_submodule_stub(child) is None


def test_find_stub_for_module_uses_native_submodule_fallback(
    native_subpkg_layout: tuple[Path, types.ModuleType, types.ModuleType],
) -> None:
    _, parent, child = native_subpkg_layout
    with patch.dict(sys.modules, {"natpkg_edge": parent, "natpkg_edge.warc": child}):
        result = _find_stub_for_module(child)
    assert result is not None
    assert result.name == "warc.pyi"


@pytest.fixture(scope="module")
def native_pkg(tmp_path_factory: pytest.TempPathFactory) -> Iterator[types.ModuleType]:
    """Compile and import the PyO3-shaped reproduction extension from discussion #698."""
    if not sysconfig.get_config_var("LDSHARED"):  # pragma: no cover
        pytest.skip("no C compiler available")
    build_dir = tmp_path_factory.mktemp("native_pkg_root")
    pkg_dir = build_dir / "native_pkg"
    pkg_dir.mkdir()
    src_pkg = STUB_ROOT / "native_pkg"
    for name in ("__init__.py", "warc.pyi"):
        shutil.copyfile(src_pkg / name, pkg_dir / name)

    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    so_file = pkg_dir / f"_native{ext_suffix}"
    include_dir = sysconfig.get_path("include")
    ldshared = sysconfig.get_config_var("LDSHARED") or f"{sysconfig.get_config_var('CC') or 'cc'} -shared"
    cflags = sysconfig.get_config_var("CFLAGS") or ""
    try:
        subprocess.check_call(
            [*ldshared.split(), f"-I{include_dir}", *cflags.split(), "-o", str(so_file), str(src_pkg / "_native.c")],
            cwd=str(pkg_dir),
        )
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover
        pytest.skip("C extension compilation failed")

    sys.path.insert(0, str(build_dir))
    try:
        mod = importlib.import_module("native_pkg")
    finally:
        sys.path.pop(0)
    yield mod
    for name in [k for k in sys.modules if k == "native_pkg" or k.startswith("native_pkg.")]:
        sys.modules.pop(name, None)
    _STUB_AST_CACHE.clear()


def test_native_submodule_has_no_file(native_pkg: types.ModuleType) -> None:
    warc = native_pkg.warc
    assert not hasattr(warc, "__file__")
    assert not hasattr(warc, "__path__")
    assert warc.__name__ == "native_pkg.warc"


def test_find_stub_owner_resolves_native_submodule_stub(native_pkg: types.ModuleType) -> None:
    info = _find_stub_owner(native_pkg.warc.WarcRecord)
    assert info is not None
    stub_path, owner = info
    assert stub_path.name == "warc.pyi"
    assert owner is native_pkg.warc


def test_backfill_from_stub_for_native_submodule(native_pkg: types.ModuleType) -> None:
    parse_annotations = _backfill_from_stub(native_pkg.warc.parse)
    assert parse_annotations == {"data": "bytes", "return": "Iterator[WarcRecord]"}


def test_get_stub_context_resolves_relative_imports_for_native_submodule(native_pkg: types.ModuleType) -> None:
    ns, _names, owner = _get_stub_context(native_pkg.warc.parse)
    assert owner == "native_pkg.warc"
    assert ns["Iterator"].__module__ == "collections.abc"


def test_native_function_signature_from_clinic_docstring(native_pkg: types.ModuleType) -> None:
    assert inspect.signature(native_pkg.warc.parse).parameters
    with pytest.raises(ValueError, match="no signature found"):
        inspect.signature(native_pkg.warc.raw_parse)


@pytest.mark.usefixtures("native_pkg")
@pytest.mark.sphinx("text", testroot="pyi-stubs")
def test_sphinx_build_resolves_param_and_return_for_native_submodule(
    app: SphinxTestApp, status: StringIO, warning: StringIO
) -> None:
    (Path(app.srcdir) / "index.rst").write_text(
        textwrap.dedent("""\
            .. autofunction:: native_pkg.warc.parse
        """)
    )
    app.build()
    assert "build succeeded" in status.getvalue()
    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert "bytes" in result
    assert "Iterator" in result
    assert "WarcRecord" in result
    warn_text = warning.getvalue()
    assert "native_pkg" not in warn_text or "forward reference" not in warn_text


@pytest.mark.usefixtures("native_pkg")
@pytest.mark.sphinx("text", testroot="pyi-stubs")
def test_sphinx_build_falls_back_to_return_only_without_signature(app: SphinxTestApp, status: StringIO) -> None:
    (Path(app.srcdir) / "index.rst").write_text(
        textwrap.dedent("""\
            .. autofunction:: native_pkg.warc.raw_parse
        """)
    )
    app.build()
    assert "build succeeded" in status.getvalue()
    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert "Iterator" in result
    assert "WarcRecord" in result


@pytest.mark.usefixtures("native_pkg")
@pytest.mark.sphinx("text", testroot="pyi-stubs")
def test_sphinx_build_documents_native_class(app: SphinxTestApp, status: StringIO) -> None:
    (Path(app.srcdir) / "index.rst").write_text(
        textwrap.dedent("""\
            .. autoclass:: native_pkg.warc.WarcRecord
        """)
    )
    app.build()
    assert "build succeeded" in status.getvalue()
    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert "WarcRecord" in result


@pytest.mark.sphinx("text", testroot="pyi-stubs")
def test_editing_a_stub_rereads_the_pages_it_types(
    app: SphinxTestApp, write_rst: Callable[[str], None], status: StringIO
) -> None:
    write_rst(".. autofunction:: stub_mod.greet")
    app.build()
    stub = Path(app.srcdir) / "stub_mod.pyi"
    stub.write_text(
        stub.read_text().replace(
            "def greet(name: str, greeting: str) -> str:", "def greet(name: str, greeting: str) -> bytes:"
        )
    )
    modified = stub.stat().st_mtime_ns + 1_000_000
    os.utime(stub, ns=(modified, modified))
    status.truncate(0)

    app.build()

    # the module this process already imported keeps the first types, so only the reread shows here
    assert "1 changed" in status.getvalue()


@pytest.fixture
def lazy_package(app: SphinxTestApp) -> Iterator[None]:
    """Write a package exposing its submodule's names through ``__getattr__``, which imports on first access."""
    package = Path(app.srcdir) / "lazy_pkg"
    package.mkdir(exist_ok=True)
    (package / "__init__.py").write_text(
        textwrap.dedent("""\
            import importlib

            _LAZY = {"Handle": "_impl"}


            def __getattr__(name):
                if name == "other":
                    raise KeyError(name)
                if name not in _LAZY:
                    raise AttributeError(name)
                value = getattr(importlib.import_module(f".{_LAZY[name]}", __name__), name)
                value.__module__ = __name__
                globals()[name] = value
                return value
        """)
    )
    (package / "_impl.py").write_text(
        textwrap.dedent('''\
            class Handle:
                """Handle."""


            def other(x: int) -> str:
                """Other."""
        ''')
    )
    yield
    for name in ("lazy_pkg", "lazy_pkg._impl"):
        sys.modules.pop(name, None)


@pytest.mark.usefixtures("lazy_package")
@pytest.mark.sphinx("text", testroot="pyi-stubs")
def test_sphinx_build_keeps_member_a_lazy_package_would_rename(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. automodule:: lazy_pkg._impl\n   :members:\n   :exclude-members: other")
    app.build()
    assert "class lazy_pkg._impl.Handle" in (Path(app.srcdir) / "_build/text/index.txt").read_text()


@pytest.mark.usefixtures("lazy_package")
@pytest.mark.sphinx("text", testroot="pyi-stubs")
def test_sphinx_build_survives_lazy_package_raising_on_lookup(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. autofunction:: lazy_pkg._impl.other")
    app.build()
    assert 'Return type:\n      "str"' in (Path(app.srcdir) / "_build/text/index.txt").read_text()
