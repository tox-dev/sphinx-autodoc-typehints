from __future__ import annotations

import ast
import os
import sys
import types
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional
from unittest.mock import MagicMock, patch

import pytest
from conftest import normalize_sphinx_text

from sphinx_autodoc_typehints._resolver._stubs import (
    _STUB_AST_CACHE,
    _backfill_from_stub,
    _extract_annotations_from_stub,
    _extract_class_annotations,
    _extract_func_annotations,
    _extract_type_alias_names,
    _find_ast_node,
    _find_stub_for_module,
    _find_stub_owner,
    _find_stub_path,
    _get_module,
    _get_stub_context,
    _parse_stub_ast,
    _resolve_import_from,
    _resolve_stub_imports,
)

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

STUB_ROOT = Path(__file__).parent.parent / "roots" / "test-pyi-stubs"


def _import_stub_mod() -> types.ModuleType:
    import stub_mod  # noqa: PLC0415  # ty: ignore[unresolved-import]

    return stub_mod


@pytest.fixture
def stub_mod() -> Any:
    sys.path.insert(0, str(STUB_ROOT))
    try:
        yield _import_stub_mod()
    finally:
        sys.path.pop(0)
        sys.modules.pop("stub_mod", None)


def test_find_stub_path_locates_sibling_pyi(stub_mod: Any) -> None:
    result = _find_stub_path(stub_mod.greet)
    assert result is not None
    assert result.suffix == ".pyi"
    assert result.stem == "stub_mod"


def test_find_stub_path_returns_none_for_no_stub() -> None:
    assert _find_stub_path(test_find_stub_path_returns_none_for_no_stub) is None


def test_find_stub_path_returns_none_for_no_module() -> None:
    obj = MagicMock(spec=[])
    obj.__module__ = None
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=None):
        assert _find_stub_path(obj) is None


def test_find_stub_path_returns_none_when_getfile_fails() -> None:
    module = types.ModuleType("fake_mod")
    with (
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module),
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getfile", side_effect=TypeError),
    ):
        assert _find_stub_path(lambda: None) is None


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
def test_find_stub_path_extension_module(tmp_path: Path, ext_filename: str) -> None:
    (tmp_path / ext_filename).write_bytes(b"")
    (tmp_path / "_mod.pyi").write_text("def f(x: int) -> None: ...\n")
    module = types.ModuleType("_mod")
    module.__file__ = str(tmp_path / ext_filename)
    with (
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module),
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getfile", return_value=module.__file__),
    ):
        result = _find_stub_path(lambda: None)
    assert result is not None
    assert result.name == "_mod.pyi"


def test_find_stub_path_extension_module_no_stub(tmp_path: Path) -> None:
    ext_filename = "_mod.cpython-312-x86_64-linux-gnu.so"
    (tmp_path / ext_filename).write_bytes(b"")
    module = types.ModuleType("_mod")
    module.__file__ = str(tmp_path / ext_filename)
    with (
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module),
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getfile", return_value=module.__file__),
    ):
        assert _find_stub_path(lambda: None) is None


def test_find_stub_path_extension_module_package_fallback(tmp_path: Path) -> None:
    ext_filename = "_mod.cpython-312-x86_64-linux-gnu.so"
    (tmp_path / ext_filename).write_bytes(b"")
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    (stub_dir / "__init__.pyi").write_text("x: int\n")
    module = types.ModuleType("_mod")
    module.__file__ = str(tmp_path / ext_filename)
    module.__path__ = [str(stub_dir)]
    with (
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module),
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getfile", return_value=module.__file__),
    ):
        result = _find_stub_path(lambda: None)
    assert result is not None
    assert result.name == "__init__.pyi"


def test_find_stub_path_package_init_pyi(tmp_path: Path) -> None:
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
        result = _find_stub_path(module)
    assert result is not None
    assert result.name == "__init__.pyi"


def test_find_stub_path_package_no_init_pyi(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    module = types.ModuleType("mypkg")
    module.__path__ = [str(pkg_dir)]
    module.__file__ = str(pkg_dir / "__init__.py")
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=module):
        assert _find_stub_path(module) is None


def test_parse_stub_ast_valid_file() -> None:
    stub_path = STUB_ROOT / "stub_mod.pyi"
    result = _parse_stub_ast(stub_path)
    assert isinstance(result, ast.Module)


def test_parse_stub_ast_caches_result() -> None:
    stub_path = STUB_ROOT / "stub_mod.pyi"
    _STUB_AST_CACHE.pop(stub_path, None)
    first = _parse_stub_ast(stub_path)
    second = _parse_stub_ast(stub_path)
    assert first is second
    _STUB_AST_CACHE.pop(stub_path, None)


def test_parse_stub_ast_caches_none_for_bad_syntax(tmp_path: Path) -> None:
    bad_stub = tmp_path / "bad.pyi"
    bad_stub.write_text("def (broken syntax\n")
    result = _parse_stub_ast(bad_stub)
    assert result is None
    assert bad_stub in _STUB_AST_CACHE
    assert _STUB_AST_CACHE[bad_stub] is None
    _STUB_AST_CACHE.pop(bad_stub, None)


def test_parse_stub_ast_returns_none_for_missing_file() -> None:
    missing = Path("/nonexistent/stub.pyi")
    _STUB_AST_CACHE.pop(missing, None)
    assert _parse_stub_ast(missing) is None
    _STUB_AST_CACHE.pop(missing, None)


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


def test_backfill_from_stub_no_stub() -> None:
    assert _backfill_from_stub(test_backfill_from_stub_no_stub) == {}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("import os\nimport sys\n", {"os": os, "sys": sys}, id="basic_import"),
        pytest.param("import os as operating_system\n", {"operating_system": os}, id="import_as"),
        pytest.param("import os.path\n", {"os": os}, id="dotted_import"),
        pytest.param("from typing import Optional, Any\n", {"Optional": Optional, "Any": Any}, id="from_import"),
        pytest.param("from typing import Optional as Opt\n", {"Opt": Optional}, id="from_import_as"),
        pytest.param("from typing import *\n", {}, id="star_import_skipped"),
        pytest.param("import nonexistent_xyz\nfrom nonexistent_abc import Foo\n", {}, id="missing_module_skipped"),
        pytest.param("from typing import NonExistentThing\n", {}, id="missing_attr_skipped"),
    ],
)
def test_resolve_stub_imports(source: str, expected: dict[str, Any]) -> None:
    ns = _resolve_stub_imports(ast.parse(source))
    for key, val in expected.items():
        assert ns[key] is val
    if not expected:
        assert ns == {}


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
    _STUB_AST_CACHE.pop(bad_stub, None)


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


def test_find_stub_path_falls_back_to_parent_package(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "__init__.pyi").write_text("def greet(name: str) -> str: ...\n")
    ext_file = pkg_dir / "_ext.cpython-314-darwin.so"
    ext_file.write_bytes(b"")

    parent_module = types.ModuleType("mypkg")
    parent_module.__file__ = str(pkg_dir / "__init__.py")
    parent_module.__path__ = [str(pkg_dir)]

    child_module = types.ModuleType("mypkg._ext")
    child_module.__file__ = str(ext_file)

    with (
        patch.dict(sys.modules, {"mypkg": parent_module, "mypkg._ext": child_module}),
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=child_module),
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getfile", side_effect=lambda m: m.__file__),
    ):
        result = _find_stub_path(lambda: None)
    assert result is not None
    assert result.name == "__init__.pyi"
    assert result.parent == pkg_dir


def test_find_stub_owner_returns_parent_module(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "__init__.pyi").write_text("def greet(name: str) -> str: ...\n")
    ext_file = pkg_dir / "_ext.cpython-314-darwin.so"
    ext_file.write_bytes(b"")

    parent_module = types.ModuleType("mypkg")
    parent_module.__file__ = str(pkg_dir / "__init__.py")
    parent_module.__path__ = [str(pkg_dir)]

    child_module = types.ModuleType("mypkg._ext")
    child_module.__file__ = str(ext_file)

    with (
        patch.dict(sys.modules, {"mypkg": parent_module, "mypkg._ext": child_module}),
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=child_module),
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getfile", side_effect=lambda m: m.__file__),
    ):
        info = _find_stub_owner(lambda: None)
    assert info is not None
    stub_path, owner = info
    assert stub_path.name == "__init__.pyi"
    assert owner is parent_module


def test_find_stub_for_module_returns_none_when_getfile_raises() -> None:
    module = types.ModuleType("fake")
    with patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getfile", side_effect=TypeError):
        assert _find_stub_for_module(module) is None


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


def test_get_stub_context_includes_owner_module_vars(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "__init__.pyi").write_text("from collections.abc import Sequence\ndef greet(name: str) -> str: ...\n")
    ext_file = pkg_dir / "_ext.cpython-314-darwin.so"
    ext_file.write_bytes(b"")

    parent_module = types.ModuleType("mypkg")
    parent_module.__file__ = str(pkg_dir / "__init__.py")
    parent_module.__path__ = [str(pkg_dir)]
    parent_module.MyAlias = int  # type: ignore[attr-defined]

    child_module = types.ModuleType("mypkg._ext")
    child_module.__file__ = str(ext_file)

    with (
        patch.dict(sys.modules, {"mypkg": parent_module, "mypkg._ext": child_module}),
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getmodule", return_value=child_module),
        patch("sphinx_autodoc_typehints._resolver._stubs.inspect.getfile", side_effect=lambda m: m.__file__),
    ):
        ns, _names, owner = _get_stub_context(lambda: None)
    assert ns["Sequence"] is Sequence
    assert ns["MyAlias"] is int
    assert owner == "mypkg"


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


def test_resolve_stub_imports_relative() -> None:
    source = "from .typing import ColorType\nfrom typing import Any\n"
    tree = ast.parse(source)
    # matplotlib.typing.ColorType is a type alias, check it resolves to something
    ns = _resolve_stub_imports(tree, "matplotlib")
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
        import relpkg.sub.mod  # noqa: PLC0415  # ty: ignore[unresolved-import]

        ns, _names, owner = _get_stub_context(relpkg.sub.mod.Cls)
        assert owner == "relpkg.sub.mod"
        assert "Helper" in ns
    finally:
        sys.path.pop(0)
        for mod_name in [k for k in sys.modules if k.startswith("relpkg")]:
            sys.modules.pop(mod_name, None)
        _STUB_AST_CACHE.clear()
