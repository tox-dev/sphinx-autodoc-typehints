from __future__ import annotations

from importlib import import_module
from logging import WARNING
from pathlib import Path
from re import sub
from sys import modules, version_info
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import FixtureRequest, LogCaptureFixture, MonkeyPatch, fixture, mark, param

from sphinx_autodoc_typehints._resolve.guards import SHADOWED_BY_GUARD, resolve_type_guarded_imports

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping
    from types import ModuleType

    from sphinx_autodoc_typehints._types import Hint

type MakeModule = Callable[[str], ModuleType]
type MakeStubbedModule = Callable[[str, str], ModuleType]
type MakeSubclassOfAGuardedBase = Callable[[str, str], type]
type AsWritten = Callable[[Mapping[str, Hint]], dict[str, Hint]]


@fixture
def make_stubbed_module(module_dir: Path, make_module: MakeModule) -> MakeStubbedModule:
    def make(runtime: str, stub: str) -> ModuleType:
        module = make_module(runtime)
        (module_dir / f"{module.__name__}.pyi").write_text(stub)
        return module

    return make


@fixture
def guarded_subclass(module_dir: Path, make_module: MakeModule, annotations_header: str) -> type:
    # the guard of the subclass's module rebinds a name the base annotates with, which must not reach the base
    (module_dir / "unguarded_base.py").write_text(
        annotations_header
        + dedent("""\
            Item = int

            class Base:
                inherited: Item
        """)
    )
    child = make_module(
        annotations_header
        + dedent("""\
            from typing import TYPE_CHECKING
            from unguarded_base import Base

            if TYPE_CHECKING:
                from decimal import Decimal as Item
            else:
                Item = str

            class Child(Base):
                own: Item
        """)
    ).Child
    resolve_type_guarded_imports([], child)
    return child


@fixture
def make_subclass_of_a_guarded_base(
    module_dir: Path, make_module: MakeModule, decimal_fallback: str
) -> MakeSubclassOfAGuardedBase:
    # the base module's guard binds what the base annotates with, and runs before the subclass reads it
    def make(header: str, child: str) -> type:
        (module_dir / "guarded_base.py").write_text(
            header
            + decimal_fallback
            + dedent("""\
                class Base:
                    amount: Decimal
            """)
        )
        child_cls = make_module(child).Child
        resolve_type_guarded_imports([], import_module("guarded_base"))
        return child_cls

    return make


@fixture
def stub_only_module(module_dir: Path) -> ModuleType:
    # numpy's _polybase.pyi imports from _polytypes.pyi, which ships no runtime module (#741)
    (package := module_dir / "stubonlypkg").mkdir()
    (package / "__init__.py").write_text("")
    (package / "_types.pyi").write_text(
        dedent("""\
            from typing import Any
            _SeriesLike = Any
        """)
    )
    (package / "poly.py").write_text(
        dedent("""\
            class Poly:
                def __init__(self, coef): ...

            def make(coef): ...
        """)
    )
    (package / "poly.pyi").write_text(
        dedent("""\
            from ._types import _SeriesLike
            class Poly:
                def __init__(self, coef: _SeriesLike) -> None: ...

            def make(coef: _SeriesLike) -> None: ...
        """)
    )
    return import_module("stubonlypkg.poly")


@fixture(name="make_module")
def make_module_fixture(module_dir: Path, request: FixtureRequest) -> MakeModule:
    # named after the test, as Sphinx caches the analysis of a module by its name
    name = sub(r"\W", "_", request.node.name)

    def make(source: str) -> ModuleType:
        (module_dir / f"{name}.py").write_text(source)
        return import_module(name)

    return make


@fixture(name="module_dir")
def module_dir_fixture(tmp_path: Path, monkeypatch: MonkeyPatch) -> Iterator[Path]:
    monkeypatch.syspath_prepend(tmp_path)
    yield tmp_path
    for name, module in list(modules.items()):
        if str(getattr(module, "__file__", None) or "").startswith(str(tmp_path)):
            del modules[name]
            SHADOWED_BY_GUARD.pop(name, None)


@fixture
def as_written() -> AsWritten:
    # Python 3.14 reads an annotation it cannot evaluate as a ForwardRef, which compares by more than its source
    def unwrap(hints: Mapping[str, Hint]) -> dict[str, Hint]:
        return {name: getattr(hint, "__forward_arg__", hint) for name, hint in hints.items()}

    return unwrap


@fixture
def logged_warnings(caplog: LogCaptureFixture) -> Callable[[], list[tuple[str, ...]]]:
    # once an application set up Sphinx logging, the debug records reach caplog and the messages carry the location
    def read() -> list[tuple[str, ...]]:
        return [
            (vars(record)["subtype"], str(vars(record)["location"]), *map(str, vars(record)["args"] or ()))
            for record in caplog.records
            if record.levelno >= WARNING
        ]

    return read


@fixture
def stub_mod(monkeypatch: MonkeyPatch) -> Iterator[ModuleType]:
    monkeypatch.syspath_prepend(Path(__file__).parents[1] / "roots" / "test-pyi-stubs")
    yield import_module("stub_mod")
    modules.pop("stub_mod", None)


@fixture(
    name="annotations_header",
    params=[
        param(
            dedent("""\
                from __future__ import annotations
            """),
            id="stringified",
        ),
        param(
            "",
            id="lazy",
            marks=mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14"),
        ),
    ],
)
def annotations_header_fixture(request: FixtureRequest) -> str:
    return request.param


@fixture(name="decimal_fallback")
def decimal_fallback_fixture() -> str:
    return dedent("""\
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from decimal import Decimal
        else:
            Decimal = float

    """)


__all__ = [
    "AsWritten",
    "MakeModule",
    "MakeStubbedModule",
    "MakeSubclassOfAGuardedBase",
]
