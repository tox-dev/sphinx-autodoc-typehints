from __future__ import annotations

import os  # the module objects are the expected namespace
import sys  # the module objects are the expected namespace
from collections.abc import Callable, Sequence
from importlib import import_module
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Never, Optional, ParamSpec, TypeVar, TypeVarTuple

from pytest import fixture, mark, param
from sphinx.ext.autodoc.mock import ismockmodule

from sphinx_autodoc_typehints._resolve.backfill.stubs.context import stub_context

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    from _resolve.conftest import MakeStubbedModule
    from sphinx_autodoc_typehints._types import Documented

type StubNamespace = tuple[dict[str, Documented], set[str]]


@mark.parametrize(
    ("stub", "expected"),
    [
        param(
            dedent("""\
                import os
                import sys
            """),
            ({"os": os, "sys": sys}, set()),
            id="import",
        ),
        param("import os as operating_system", ({"operating_system": os}, set()), id="import-as"),
        param("import os.path", ({"os": os}, set()), id="dotted-import"),
        param("from typing import Optional, Any", ({"Optional": Optional, "Any": Any}, set()), id="import-from"),
        param("from typing import Optional as Opt", ({"Opt": Optional}, set()), id="import-from-as"),
        param("from typing import *", ({}, set()), id="star-import"),
        param("from nonexistent_abc import Foo", ({}, {"Foo"}), id="missing-module"),
        param("from typing import NonExistentThing", ({}, {"NonExistentThing"}), id="missing-name"),
        param(
            dedent("""\
                if sys.version_info >= (3, 11):
                    from typing import Self
                else:
                    from typing import Never as Self
            """),
            ({"Self": Never}, set()),
            id="both-branches-of-a-condition",
        ),
    ],
)
def test_stub_context_resolves_the_imports_of_a_stub(
    stub_namespace: Callable[[str], StubNamespace], stub: str, expected: StubNamespace
) -> None:
    assert stub_namespace(stub) == expected


@fixture(name="stub_namespace")
def stub_namespace_fixture(make_stubbed_module: MakeStubbedModule) -> Callable[[str], StubNamespace]:
    def read(stub: str) -> StubNamespace:
        module = make_stubbed_module("def func(): ...", stub)
        namespace, crossrefs, _ = stub_context(module.func)
        return {name: value for name, value in namespace.items() if name not in vars(module)}, set(crossrefs)

    return read


@mark.parametrize(
    ("stub", "name"),
    [
        param("import nonexistent_xyz", "nonexistent_xyz", id="module"),
        param("import nonexistent_xyz.sub", "nonexistent_xyz", id="dotted"),
        param("import nonexistent_xyz as missing", "missing", id="aliased"),
    ],
)
def test_stub_context_mocks_a_missing_module(
    stub_namespace: Callable[[str], StubNamespace], stub: str, name: str
) -> None:
    assert [(added, ismockmodule(value)) for added, value in stub_namespace(stub)[0].items()] == [(name, True)]


@mark.parametrize(
    "body",
    [
        param("import nonexistent_dependency_xyz", id="missing-dependency"),
        param("raise ImportError('broken')", id="import-error"),
    ],
)
def test_stub_context_skips_an_installed_module_that_fails(
    module_dir: Path, stub_namespace: Callable[[str], StubNamespace], body: str
) -> None:
    (module_dir / "fails_to_import.py").write_text(body)
    assert stub_namespace("import fails_to_import") == ({}, set())


@mark.parametrize(
    "decorator",
    [param("", id="plain"), param("@undefined_decorator", id="decorated")],
)
def test_stub_context_defines_what_the_stub_defines(
    stub_namespace: Callable[[str], StubNamespace], decorator: str
) -> None:
    namespace, _ = stub_namespace(
        "\n".join((
            dedent("""\
                from typing import TypeVar, TypedDict
                _T = TypeVar("_T")
            """),
            decorator,
            dedent("""\
                class MyDict(TypedDict):
                    x: int
            """),
        ))
    )
    assert {name: (type(value).__name__, getattr(value, "__name__", None)) for name, value in namespace.items()} == {
        "TypeVar": ("type", "TypeVar"),
        "TypedDict": ("function", "TypedDict"),
        "_T": ("TypeVar", "_T"),
        "MyDict": ("_TypedDictMeta", "MyDict"),
    }


def test_stub_context_places_a_stub_class_in_the_module_of_the_stub(make_stubbed_module: MakeStubbedModule) -> None:
    module = make_stubbed_module("def load(path): ...", "class Config: ...")
    assert stub_context(module.load)[0]["Config"].__module__ == module.__name__


@mark.parametrize(
    ("stub", "expected"),
    [
        param(
            dedent("""\
                from typing import TypeAlias
                Foo: TypeAlias = int
            """),
            {"Foo"},
            id="typing_TypeAlias",
        ),
        param(
            dedent("""\
                import typing
                Bar: typing.TypeAlias = str
            """),
            {"Bar"},
            id="qualified_TypeAlias",
        ),
        param(
            dedent("""\
                from typing_extensions import TypeAlias
                Qux: TypeAlias = int
            """),
            {"Qux"},
            id="typing_extensions_TypeAlias",
        ),
        param(
            dedent("""\
                import typing_extensions
                Quux: typing_extensions.TypeAlias = str
            """),
            {"Quux"},
            id="qualified_typing_extensions_TypeAlias",
        ),
        param("type Baz = int | str", {"Baz"}, id="type_statement"),
        param(
            dedent("""\
                x: int = 1
                limit: list[int]
            """),
            set(),
            id="no_aliases",
        ),
    ],
)
def test_stub_context_cross_references_the_aliases_of_a_stub(
    stub_namespace: Callable[[str], StubNamespace], stub: str, expected: set[str]
) -> None:
    assert stub_namespace(stub)[1] == expected


def test_stub_context_of_a_function(stub_mod: ModuleType) -> None:
    namespace, crossrefs, owner = stub_context(stub_mod.greet)
    assert (namespace["Sequence"], {name: vars(ref) for name, ref in crossrefs.items()}, owner) == (
        Sequence,
        {"MyAlias": {"name": "MyAlias", "configured": False, "crossref": True}},
        "stub_mod",
    )


@mark.parametrize("stub", [param(None, id="no-stub"), param("def (broken", id="bad-syntax")])
def test_stub_context_without_a_stub(
    make_module: Callable[[str], ModuleType], make_stubbed_module: MakeStubbedModule, stub: str | None
) -> None:
    module = make_module("def func(): ...") if stub is None else make_stubbed_module("def func(): ...", stub)
    assert stub_context(module.func) == ({}, {}, "")


@mark.parametrize(
    ("declaration", "kind"),
    [
        param("T: int", TypeVar, id="type-var"),
        param("**T", ParamSpec, id="param-spec"),
        param("*T", TypeVarTuple, id="type-var-tuple"),
    ],
)
def test_stub_context_binds_the_type_parameters_of_a_function(
    make_stubbed_module: MakeStubbedModule, declaration: str, kind: type
) -> None:
    module = make_stubbed_module("def func(value): return value", f"def func[{declaration}](value: T) -> T: ...")
    namespace, _, _ = stub_context(module.func)
    assert (type(namespace["T"]), getattr(namespace["T"], "__name__", None)) == (kind, "T")


def test_stub_context_binds_the_type_parameters_of_a_method_and_its_class(
    make_stubbed_module: MakeStubbedModule,
) -> None:
    module = make_stubbed_module(
        dedent("""\
            class Owner:
                async def func(self, value): return value
        """),
        dedent("""\
            from collections.abc import Callable
            class Owner[T]:
                async def func[**P](self, value: Callable[P, T]) -> T: ...
        """),
    )
    namespace, _, _ = stub_context(module.Owner.func)
    assert [(type(namespace[name]), getattr(namespace[name], "__name__", None)) for name in ("T", "P")] == [
        (TypeVar, "T"),
        (ParamSpec, "P"),
    ]


@mark.parametrize(
    ("stub_import", "bound", "module_name"),
    [
        param("import subpkg.extra", "subpkg", "subpkg", id="import"),
        param("from . import extra", "extra", "subpkg.extra", id="from-import"),
    ],
)
def test_stub_context_imports_a_submodule_of_the_stub(
    module_dir: Path, stub_import: str, bound: str, module_name: str
) -> None:
    (package := module_dir / "subpkg").mkdir()
    (package / "__init__.py").write_text("def load(src): ...")
    (package / "__init__.pyi").write_text(
        dedent(f"""\
            {stub_import}

            def load(src: extra.Extra) -> int: ...
        """)
    )
    (package / "extra.py").write_text("class Extra: ...")
    assert stub_context(import_module("subpkg").load)[0][bound] is import_module(module_name)


def test_stub_context_resolves_the_relative_imports_of_a_package_stub(module_dir: Path) -> None:
    (package := module_dir / "relpkg").mkdir()
    (sub := package / "sub").mkdir()
    (package / "__init__.py").write_text("")
    (sub / "__init__.py").write_text("")
    (sub / "mod.py").write_text("class Cls: ...")
    (sub / "mod.pyi").write_text(
        dedent("""\
            from ..helpers import Helper
            class Cls:
                x: Helper
        """)
    )
    (package / "helpers.py").write_text("class Helper: ...")
    namespace, _, owner = stub_context(import_module("relpkg.sub.mod").Cls)
    assert (namespace["Helper"], owner) == (import_module("relpkg.helpers").Helper, "relpkg.sub.mod")


def test_stub_context_cross_references_a_name_only_a_stub_defines(stub_only_module: ModuleType) -> None:
    assert set(stub_context(stub_only_module.make)[1]) == {"_SeriesLike"}


def test_stub_context_of_a_native_submodule(native_pkg: ModuleType) -> None:
    namespace, _, owner = stub_context(native_pkg.warc.parse)
    assert (namespace["Iterator"].__module__, owner) == ("collections.abc", "native_pkg.warc")
