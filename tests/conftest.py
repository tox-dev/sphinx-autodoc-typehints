from __future__ import annotations

from contextlib import suppress
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from os import sep
from pathlib import Path
from shutil import copyfile, copytree, ignore_patterns, rmtree
from subprocess import CalledProcessError, check_call  # ruff:ignore[suspicious-subprocess-import]  # the C extensions under test need a compiler
from sys import modules, path, version_info
from sysconfig import get_config_var, get_path
from typing import TYPE_CHECKING, Final, Protocol
from urllib.request import urlopen

from pytest import Config, FixtureRequest, MonkeyPatch, TempPathFactory, fixture, skip
from sphinx.ext.autodoc.mock import mock
from sphinx.pycode import ModuleAnalyzer
from sphobjinv import Inventory

from sphinx_autodoc_typehints._resolve.guards.overlay import SHADOWED_BY_GUARD
from sphinx_autodoc_typehints._resolve.overloads import OVERLOADS

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from types import ModuleType

    from sphinx.testing.util import SphinxTestApp


pytest_plugins: Final[str] = "sphinx.testing.fixtures"
collect_ignore: Final[list[str]] = ["roots"]

type MakeModule = Callable[[str, str], ModuleType]


class BuildText(Protocol):
    def __call__(self, index: str, output: str = "", **documents: str) -> str: ...


@fixture(name="make_app")
def make_app_fixture(make_app: Callable[..., SphinxTestApp]) -> Iterator[Callable[..., SphinxTestApp]]:
    confdirs: set[str] = set()

    def make(*args: object, **kwargs: object) -> SphinxTestApp:
        app = make_app(*args, **kwargs)
        confdirs.add(f"{app.confdir}{sep}")
        return app

    yield make
    # a project's conf.py puts its directory on sys.path and autodoc imports from there, so a later test importing the
    # same module name would get this copy, which the next build of that project deletes
    for name in [
        name
        for name, module in modules.items()
        if isinstance(file := getattr(module, "__file__", None), str) and file.startswith(tuple(confdirs))
    ]:
        del modules[name]


@fixture(autouse=True)
def _forget_test_imports() -> Iterator[None]:
    saved_path = path.copy()
    yield
    # an app restores on cleanup the sys.path it started with, which runs after the monkeypatch of a test creating the
    # app undid its own entries, and so puts them back
    path[:] = saved_path
    # what the process keeps per module name outlives a module a test unloaded, and holds objects of it that a later
    # test loading another module under the name would read
    tracked = {*SHADOWED_BY_GUARD, *OVERLOADS, *(name for kind, name in ModuleAnalyzer.cache if kind == "module")}
    for name in tracked - modules.keys():
        SHADOWED_BY_GUARD.pop(name, None)
        OVERLOADS.pop(name, None)
        ModuleAnalyzer.cache.pop(("module", name), None)


@fixture(autouse=True, scope="session")
def _test_python_path() -> Iterator[None]:
    test_path = str(Path(__file__).parent)
    path.insert(0, test_path)
    yield
    path.remove(test_path)


@fixture
def wide_text_output(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("sphinx.writers.text.MAXWIDTH", 2000)


@fixture(scope="session")
def inv(pytestconfig: Config) -> Inventory:
    cache_path = f"python{version_info.major}.{version_info.minor}/objects.inv"
    # the cache provider is absent under -p no:cacheprovider
    if (cache := getattr(pytestconfig, "cache", None)) is None or (
        inv_dict := cache.get(cache_path, None)
    ) is None:  # pragma: no cover -- network fetch, CI has cache
        url = f"https://docs.python.org/{version_info.major}.{version_info.minor}/objects.inv"
        try:
            # sphobjinv downloads without a timeout, so a stalled connection would hang the whole run
            with urlopen(url, timeout=30) as response:
                inv_dict = Inventory(
                    zlib=response.read()  # ty: ignore[unknown-argument]  # https://github.com/astral-sh/ty/issues/2404
                ).json_dict()
        except OSError as exc:
            skip(f"the Python inventory is neither cached nor downloadable from {url}: {exc}")
        if cache is not None:
            cache.set(cache_path, inv_dict)
    return Inventory(
        inv_dict  # ty: ignore[too-many-positional-arguments]  # https://github.com/astral-sh/ty/issues/2404
    )


@fixture(autouse=True)
def _remove_sphinx_projects(request: FixtureRequest, sphinx_test_tempdir: Path) -> None:
    if not request.node.get_closest_marker("sphinx"):
        return
    for entry in sphinx_test_tempdir.iterdir():
        with suppress(PermissionError):
            if entry.is_dir() and Path(entry, "_build").exists():
                rmtree(str(entry))


@fixture
def mocked_object() -> Callable[..., object]:
    with mock(["mocked_dependency"]):
        return import_module("mocked_dependency").Thing


@fixture
def make_module(tmp_path: Path, monkeypatch: MonkeyPatch) -> MakeModule:
    monkeypatch.syspath_prepend(tmp_path)

    def make(name: str, source: str) -> ModuleType:
        (module_path := tmp_path / f"{name}.py").write_text(source)
        spec = spec_from_file_location(name, module_path)
        assert spec is not None
        assert spec.loader is not None
        module = module_from_spec(spec)
        # registered before it runs, as a module importing itself or a dataclass in it looks itself up there
        monkeypatch.setitem(modules, name, module)
        spec.loader.exec_module(module)
        return module

    return make


@fixture
def fresh_mod(monkeypatch: MonkeyPatch) -> None:
    # several testroots name their module mod, so forget what the process keeps about the mod an earlier test imported
    monkeypatch.delitem(modules, "mod", raising=False)
    monkeypatch.delitem(ModuleAnalyzer.cache, ("module", "mod"), raising=False)
    monkeypatch.delitem(SHADOWED_BY_GUARD, "mod", raising=False)
    monkeypatch.delitem(OVERLOADS, "mod", raising=False)


@fixture
def rootdir() -> Path:
    return Path(__file__).parent / "roots"


@fixture
def build_text(app: SphinxTestApp, write_rst: Callable[[str], None]) -> BuildText:
    def build(index: str, output: str = "", **documents: str) -> str:
        write_rst(index)
        for name, text in documents.items():
            (Path(app.srcdir) / f"{name}.rst").write_text(text)
        app.build()
        return (Path(app.outdir) / output if output else next(Path(app.outdir).glob("index.*"))).read_text()

    return build


@fixture(name="write_rst")
def write_rst_fixture(app: SphinxTestApp) -> Callable[[str], None]:
    def _write(content: str) -> None:
        for rst_file in Path(app.srcdir).glob("*.rst"):
            rst_file.unlink()
        (Path(app.srcdir) / "index.rst").write_text(content)

    return _write


_STUB_ROOT: Final[Path] = Path(__file__).parent / "roots" / "test-pyi-stubs"


@fixture(scope="session")
def c_ext_mod(tmp_path_factory: TempPathFactory) -> Iterator[ModuleType]:
    build_dir = tmp_path_factory.mktemp("c_ext")
    _compile(_STUB_ROOT / "c_ext_mod.c", build_dir / "c_ext_mod")
    copyfile(_STUB_ROOT / "c_ext_mod.pyi", build_dir / "c_ext_mod.pyi")
    yield _import_from(build_dir, "c_ext_mod")
    del modules["c_ext_mod"]


# a PyO3 extension registers a submodule with no file of its own, whose stub sits in the package (discussion #698)
@fixture(scope="session")
def native_pkg(tmp_path_factory: TempPathFactory) -> Iterator[ModuleType]:
    build_dir = tmp_path_factory.mktemp("native_pkg_root")
    copytree(_STUB_ROOT / "native_pkg", build_dir / "native_pkg", ignore=ignore_patterns("*.c"))
    _compile(_STUB_ROOT / "native_pkg" / "_native.c", build_dir / "native_pkg" / "_native")
    yield _import_from(build_dir, "native_pkg")
    for name in [name for name in modules if name.partition(".")[0] == "native_pkg"]:
        del modules[name]


def _compile(source: Path, target: Path) -> None:
    if not (linker := get_config_var("LDSHARED")):  # pragma: no cover  # reached only without a C toolchain
        skip("no C compiler available")
    command = [
        *linker.split(),
        f"-I{get_path('include')}",
        *(get_config_var("CFLAGS") or "").split(),
        "-o",
        f"{target}{get_config_var('EXT_SUFFIX')}",
        str(source),
    ]
    try:
        check_call(command)
    except (CalledProcessError, FileNotFoundError):  # pragma: no cover  # reached only without a C toolchain
        skip("C extension compilation failed")


def _import_from(directory: Path, name: str) -> ModuleType:
    path.insert(0, str(directory))
    try:
        return import_module(name)
    finally:
        path.remove(str(directory))


__all__ = [
    "BuildText",
    "MakeModule",
]
