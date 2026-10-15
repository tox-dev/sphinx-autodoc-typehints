from __future__ import annotations

from ast import ImportFrom, Module, parse, unparse
from importlib import import_module
from os import utime
from pathlib import Path
from sys import modules
from textwrap import dedent
from types import ModuleType
from typing import TYPE_CHECKING

from pytest import MonkeyPatch, fixture, mark, param

from sphinx_autodoc_typehints._resolve.backfill.stubs.find import (
    find_stub_owner,
    live_statements,
    parse_stub_ast,
    resolve_import_from,
    stub_owner_package,
    stub_path,
)

if TYPE_CHECKING:
    from sphinx_autodoc_typehints._types import Documented


def test_stub_path_of_a_module_with_a_stub_beside_it(stub_mod: ModuleType) -> None:
    assert stub_path(stub_mod.greet) == Path(str(stub_mod.__file__)).with_suffix(".pyi")


@mark.parametrize(
    "obj",
    [
        param(test_stub_path_of_a_module_with_a_stub_beside_it, id="no-stub"),
        param(42, id="no-module"),
        param(ModuleType("fileless"), id="module-without-file"),
    ],
)
def test_stub_path_without_a_stub(obj: Documented) -> None:
    assert stub_path(obj) is None


@mark.parametrize(
    "ext_filename",
    [
        param("_mod.cpython-312-x86_64-linux-gnu.so", id="cpython_linux"),
        param("_mod.cpython-313-darwin.so", id="cpython_darwin"),
        param("_mod.cpython-314t-x86_64-linux-gnu.so", id="cpython_free_threaded"),
        param("_mod.cpython-314d-x86_64-linux-gnu.so", id="cpython_debug"),
        param("_mod.cpython-314-aarch64-linux-musl.so", id="cpython_musl"),
        param("_mod.abi3.so", id="abi3_stable"),
        param("_mod.so", id="simple_so"),
        param("_mod.pyd", id="windows_pyd"),
        param("_mod.cp314-win_amd64.pyd", id="windows_tagged_pyd"),
        param("_mod.dll", id="cygwin_dll"),
        param("_mod.pypy39-pp73-x86_64-linux-gnu.so", id="pypy"),
    ],
)
def test_stub_path_of_an_extension_module(tmp_path: Path, ext_filename: str) -> None:
    (tmp_path / "_mod.pyi").write_text("def f(x: int) -> None: ...")
    module = ModuleType("_mod")
    module.__file__ = str(tmp_path / ext_filename)
    assert stub_path(module) == tmp_path / "_mod.pyi"


@mark.parametrize(
    ("stubs", "expected"),
    [
        param(["second/__init__.pyi"], "second/__init__.pyi", id="init-stub-in-a-later-path"),
        param([], None, id="no-stub"),
    ],
)
def test_stub_path_of_a_package(tmp_path: Path, stubs: list[str], expected: str | None) -> None:
    for directory in ("first", "second"):
        (tmp_path / directory).mkdir()
    for stub in stubs:
        (tmp_path / stub).write_text("x: int")
    module = ModuleType("_pkg")
    module.__file__ = str(tmp_path / "_pkg.cpython-312-x86_64-linux-gnu.so")
    module.__path__ = [str(tmp_path / "first"), str(tmp_path / "second")]
    assert stub_path(module) == (None if expected is None else tmp_path / expected)


@mark.parametrize(
    ("stub", "package_dir", "expected"),
    [
        param("_mod.pyi", None, "_mod.pyi", id="beside-file"),
        param("stubs/__init__.pyi", "stubs", "stubs/__init__.pyi", id="in-package-path"),
        param("elsewhere.pyi", None, None, id="package-path-raising"),
    ],
)
def test_stub_path_reads_the_properties_of_a_module_proxy(
    tmp_path: Path, stub: str, package_dir: str | None, expected: str | None
) -> None:
    (tmp_path / "stubs").mkdir()
    (tmp_path / stub).write_text("x: int")

    def package_path(_: ModuleType) -> list[str]:
        if package_dir is None:
            msg = "__path__"
            raise AttributeError(msg)
        return [str(tmp_path / package_dir)]

    # module proxies report where they live through properties
    proxy = type(
        "_ProxyModule",
        (ModuleType,),
        {"__file__": property(lambda _: str(tmp_path / "_mod.py")), "__path__": property(package_path)},
    )
    assert stub_path(proxy("_mod")) == (None if expected is None else tmp_path / expected)


@mark.parametrize(
    ("stub", "child", "expected"),
    [
        param("warc.pyi", "warc", "warc.pyi", id="sibling-stub"),
        param("sub/__init__.pyi", "sub", "sub/__init__.pyi", id="subpackage-stub"),
        param("warc.pyi", "missing", None, id="no-matching-stub"),
    ],
)
def test_stub_path_of_a_native_submodule(
    tmp_path: Path, monkeypatch: MonkeyPatch, stub: str, child: str, expected: str | None
) -> None:
    # PyO3 registers a submodule through PyModule_AddObject, which leaves it no file of its own
    (tmp_path / "sub").mkdir()
    (tmp_path / stub).write_text(
        dedent("""\
            class WarcRecord:
                record_id: str
        """)
    )
    parent = ModuleType("natpkg")
    parent.__path__ = [str(tmp_path)]
    monkeypatch.setitem(modules, "natpkg", parent)
    assert stub_path(ModuleType(f"natpkg.{child}")) == (None if expected is None else tmp_path / expected)


@mark.parametrize(
    ("parent", "child"),
    [
        param(None, "top_level_native", id="no-parent"),
        param(None, "absent_parent.child", id="parent-not-imported"),
        param(ModuleType("flat_native"), "flat_native.child", id="parent-without-path"),
    ],
)
def test_stub_path_of_a_native_submodule_without_a_package(
    monkeypatch: MonkeyPatch, parent: ModuleType | None, child: str
) -> None:
    if parent is not None:
        monkeypatch.setitem(modules, parent.__name__, parent)
    assert stub_path(ModuleType(child)) is None


def test_find_stub_owner_of_a_native_submodule(native_pkg: ModuleType) -> None:
    warc = native_pkg.warc
    assert find_stub_owner(warc.WarcRecord) == (Path(str(native_pkg.__file__)).with_name("warc.pyi"), warc)


@mark.parametrize(
    ("reexported", "expected"),
    [param(True, "parent", id="reexported"), param(False, None, id="only-named-alike")],
)
def test_find_stub_owner_reads_a_parent_stub_only_for_what_it_reexports(
    tmp_path: Path, monkeypatch: MonkeyPatch, reexported: bool, expected: str | None
) -> None:
    # cbor2/__init__.pyi types the functions of the native cbor2._cbor2 it re-exports
    (tmp_path / "__init__.pyi").write_text("def greet(names: list[str]) -> str: ...")
    parent = ModuleType("mypkg")
    parent.__file__ = str(tmp_path / "__init__.py")
    child = ModuleType("mypkg._ext")
    child.__file__ = str(tmp_path / "_ext.cpython-314-darwin.so")
    namespace: dict[str, Documented] = {"__name__": child.__name__}
    exec("def greet(names, count): ...", namespace)  # ruff:ignore[exec-builtin]  # a function of the native module
    monkeypatch.setattr(child, "greet", greet := namespace["greet"], raising=False)
    if reexported:
        monkeypatch.setattr(parent, "greet", greet, raising=False)
    monkeypatch.setitem(modules, "mypkg", parent)
    monkeypatch.setitem(modules, "mypkg._ext", child)
    assert find_stub_owner(greet) == (None if expected is None else (tmp_path / "__init__.pyi", parent))


@mark.parametrize(
    ("documenting_stub", "name", "expected"),
    [
        param("from reexp_src import conv as conv", "reexp_doc.conv", "reexp_src", id="reexported-stub"),
        param("def conv(x: bytes) -> bytes: ...", "reexp_doc.conv", "reexp_doc", id="own-stub"),
        param("from reexp_doc import conv as conv", "reexp_doc.conv", None, id="reexported-from-itself"),
        param("from reexp_src import conv as conv", "reexp_src._next.conv", None, id="defining-module"),
        param("from reexp_src import conv as conv", "reexp_src.conv", None, id="other-object-named-alike"),
    ],
)
def test_stub_path_of_the_module_documenting_a_function(
    reexport_packages: Path, documenting_stub: str, name: str, expected: str | None
) -> None:
    (reexport_packages / "reexp_doc" / "__init__.pyi").write_text(documenting_stub)
    import_module("reexp_doc")
    found = stub_path(import_module("reexp_src._next").conv, name)
    assert found == (None if expected is None else reexport_packages / expected / "__init__.pyi")


# the layout behind `attrs.asdict`, which its stub types as the function of another package
@fixture(name="reexport_packages")
def reexport_packages_fixture(module_dir: Path) -> Path:
    (source := module_dir / "reexp_src").mkdir()
    (source / "__init__.py").write_text("from reexp_src._funcs import conv")
    (source / "__init__.pyi").write_text("def conv(x: int) -> str: ...")
    (source / "_funcs.py").write_text(
        dedent("""\
            def conv(x, legacy=True):
                return str(x)
        """)
    )
    (source / "_next.py").write_text(
        dedent("""\
            def conv(x):
                return str(x)
        """)
    )
    (documenting := module_dir / "reexp_doc").mkdir()
    (documenting / "__init__.py").write_text("from reexp_src._next import conv")
    return module_dir


def test_stub_path_reads_no_name_through_the_lazy_getattr_of_a_package(module_dir: Path) -> None:
    (package := module_dir / "lazy_pkg").mkdir()
    (package / "__init__.py").write_text(
        dedent("""\
            import importlib

            def __getattr__(name):
                if name == "other":
                    raise KeyError(name)
                value = getattr(importlib.import_module("._impl", __name__), name)
                value.__module__ = __name__
                return value
        """)
    )
    (package / "_impl.py").write_text(
        dedent("""\
            class Handle: ...

            def other(x: int) -> str: ...
        """)
    )
    impl = import_module("lazy_pkg._impl")
    assert ((stub_path(impl.Handle), stub_path(impl.other)), impl.Handle.__module__) == ((None, None), "lazy_pkg._impl")


def test_parse_stub_ast(tmp_path: Path) -> None:
    (stub := tmp_path / "typed.pyi").write_text("def run(a: int) -> None: ...")
    assert isinstance(tree := parse_stub_ast(stub), Module)
    assert unparse(tree) == dedent("""\
        def run(a: int) -> None:
            ...""")


def test_parse_stub_ast_parses_a_stub_once(tmp_path: Path) -> None:
    (stub := tmp_path / "typed.pyi").write_text("def run(a: int) -> None: ...")
    assert isinstance(tree := parse_stub_ast(stub), Module)
    assert parse_stub_ast(stub) is tree


def test_parse_stub_ast_reads_an_edited_stub_again(tmp_path: Path) -> None:
    (stub := tmp_path / "edited.pyi").write_text("def run(a: int) -> None: ...")
    parse_stub_ast(stub)
    stub.write_text("def run(a: bytes) -> None: ...")
    utime(stub, ns=(modified := stub.stat().st_mtime_ns + 1_000_000, modified))
    assert isinstance(tree := parse_stub_ast(stub), Module)
    assert unparse(tree) == dedent("""\
        def run(a: bytes) -> None:
            ...""")


@mark.parametrize(
    "content",
    [param("def (broken syntax", id="bad-syntax"), param(None, id="missing-file")],
)
def test_parse_stub_ast_of_an_unreadable_stub(tmp_path: Path, content: str | None) -> None:
    stub = tmp_path / "unreadable.pyi"
    if content is not None:
        stub.write_text(content)
    assert parse_stub_ast(stub) is None


@mark.parametrize(
    ("source", "expected"),
    [
        param(
            dedent("""\
                if sys.version_info >= (3, 99):
                    future = 1
                else:
                    present = 1
            """),
            ["present = 1"],
            id="version-gate",
        ),
        param(
            dedent("""\
                if sys.version_info >= (3,):
                    if sys.platform == "nowhere":
                        elsewhere = 1
                    current = 1
            """),
            ["current = 1"],
            id="nested-gates",
        ),
        param(
            dedent("""\
                if WITH_EXTRAS:
                    extra = 1
                else:
                    plain = 1
            """),
            ["extra = 1", "plain = 1"],
            id="undecidable",
        ),
    ],
)
def test_live_statements(source: str, expected: list[str]) -> None:
    assert [unparse(node) for node in live_statements(parse(source).body)] == expected


@mark.parametrize(
    ("source", "owner_package", "expected"),
    [
        param("from typing import Any", "", "typing", id="absolute"),
        param("from .typing import ColorType", "matplotlib", "matplotlib.typing", id="rel_level1"),
        param("from . import utils", "matplotlib", "matplotlib", id="rel_level1_bare"),
        param("from ..typing import X", "matplotlib.figure", "matplotlib.typing", id="rel_level2"),
        param("from .sub import Y", "", "sub", id="rel_no_package"),
        param("from ...x import Y", "a", None, id="beyond-the-top-package"),
    ],
)
def test_resolve_import_from(source: str, owner_package: str, expected: str | None) -> None:
    assert isinstance(node := parse(source).body[0], ImportFrom)
    assert resolve_import_from(node, owner_package) == expected


@mark.parametrize(
    ("owner_name", "package_attr", "stub_name", "expected"),
    [
        param("pkg", "pkg", "__init__.pyi", "pkg", id="package_with_attr"),
        param("pkg.warc", None, "warc.pyi", "pkg", id="native_module_no_attr"),
        param("pkg.sub", None, "__init__.pyi", "pkg.sub", id="native_subpackage_no_attr"),
        param("solo", "", "solo.pyi", "", id="top_level_module"),
        param("a.b.c", None, "c.pyi", "a.b", id="deep_module"),
    ],
)
def test_stub_owner_package(owner_name: str, package_attr: str | None, stub_name: str, expected: str) -> None:
    module = ModuleType(owner_name)
    module.__package__ = package_attr
    assert stub_owner_package(module, Path(stub_name)) == expected
