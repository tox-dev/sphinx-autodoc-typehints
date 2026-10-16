from __future__ import annotations

from csv import Error
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from sys import modules, version_info
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Final, Protocol, get_overloads

from pytest import MonkeyPatch, fixture, mark, param, raises

from sphinx_autodoc_typehints._refs import MyTypeAliasForwardRef
from sphinx_autodoc_typehints._resolve import get_all_type_hints
from sphinx_autodoc_typehints._resolve.guards import SHADOWED_BY_GUARD, guarded_names, resolve_type_guarded_imports

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO
    from types import ModuleType

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp

    from sphinx_autodoc_typehints._types import Documented

_GUARD: Final[str] = dedent("""\
    from __future__ import annotations
    import sys
    from typing import TYPE_CHECKING, TypeAlias

    if TYPE_CHECKING:""")
_FUNC: Final[str] = "def func(): ..."


def test_resolve_type_guarded_imports_records_nothing_for_a_module_without_source(
    make_module: Callable[[str], ModuleType],
) -> None:
    module = make_module(_FUNC)
    resolve_type_guarded_imports([], Error)
    resolve_type_guarded_imports([], module.func)
    assert (Error.__module__ in SHADOWED_BY_GUARD, module.__name__ in SHADOWED_BY_GUARD) == (False, True)


@mark.parametrize(
    "target",
    [
        param(lambda loaded: loaded, id="module"),
        param(lambda loaded: loaded.func, id="function"),
        param(lambda loaded: loaded.Holder, id="class"),
    ],
)
def test_resolve_type_guarded_imports_records_the_guard_of_the_module(
    make_module: Callable[[str], ModuleType],
    guarded: Callable[[str, str], str],
    target: Callable[[ModuleType], ModuleType | Callable[..., object]],
) -> None:
    module = make_module(
        guarded(
            "from decimal import Decimal",
            dedent("""\
                def func(): ...

                class Holder: ...
            """),
        )
    )
    resolve_type_guarded_imports([], target(module))
    assert guarded_names(module) == {"Decimal": Decimal}


def test_resolve_type_guarded_imports_skips_a_false_compound_guard(make_module: Callable[[str], ModuleType]) -> None:
    module = make_module(
        dedent("""\
            from __future__ import annotations
            from typing import TYPE_CHECKING

            if TYPE_CHECKING and False:
                from decimal import Decimal as Ghost

            def consume(value: Ghost) -> None: ...
        """)
    )
    resolve_type_guarded_imports([], module.consume)
    assert "Ghost" not in guarded_names(module.consume)


def test_resolve_type_guarded_imports_skips_an_instance_but_not_its_class(
    make_module: Callable[[str], ModuleType], guarded: Callable[[str, str], str]
) -> None:
    module = make_module(guarded("from decimal import Decimal", "class Holder: ..."))
    resolve_type_guarded_imports([], module.Holder())
    skipped = module.__name__ not in SHADOWED_BY_GUARD
    resolve_type_guarded_imports([], module.Holder)
    assert (skipped, guarded_names(module)) == (True, {"Decimal": Decimal})


def test_resolve_type_guarded_imports_records_the_guard_of_the_module_defining_a_reexported_function(
    module_dir: Path, make_module: Callable[[str], ModuleType], guarded: Callable[[str, str], str]
) -> None:
    (module_dir / "reexported_impl.py").write_text(guarded("from decimal import Decimal", "def convert(): ..."))
    module = make_module(
        dedent("""\
            from reexported_impl import convert

            convert.__module__ = __name__
        """)
    )
    resolve_type_guarded_imports([], module.convert)
    assert guarded_names(module.convert) == {"Decimal": Decimal}


def test_resolve_type_guarded_imports_binds_the_names_below_an_absent_dependency(
    make_module: Callable[[str], ModuleType], guarded: Callable[[str, str], str]
) -> None:
    # the absent dependency must not strand the imports under it (#741)
    module = make_module(
        guarded(
            dedent("""\
                from no_such_dependency import Absent
                from decimal import Decimal
            """),
            _FUNC,
        )
    )
    resolve_type_guarded_imports([], module.func)
    assert {name: getattr(value, "__display_name__", value) for name, value in guarded_names(module.func).items()} == {
        "Absent": "no_such_dependency.Absent",
        "Decimal": Decimal,
    }


@mark.parametrize(
    ("guard", "annotation", "display_name"),
    [
        param("from no_such_dependency import Absent", "Absent", "no_such_dependency.Absent", id="from"),
        param(
            "import no_such_dependency.sub",
            "no_such_dependency.sub.Absent",
            "no_such_dependency.sub.Absent",
            id="dotted",
        ),
        param(
            dedent("""\
                try:
                    from no_such_dependency import Absent
                except ImportError:
                    from no_such_fallback import Absent
            """),
            "Absent",
            "no_such_fallback.Absent",
            id="try-except",
        ),
    ],
)
def test_resolve_type_guarded_imports_mocks_an_absent_dependency(
    make_module: Callable[[str], ModuleType],
    guarded: Callable[[str, str], str],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    guard: str,
    annotation: str,
    display_name: str,
) -> None:
    # a guarded dependency the docs environment lacks reads as autodoc_mock_imports would mock it (#768)
    module = make_module(guarded(guard, f"def func(value: {annotation}) -> None: ..."))
    assert (repr(get_all_type_hints([], module.func, "mod.func", {})["value"]), logged_warnings()) == (display_name, [])


def test_resolve_type_guarded_imports_mocks_an_absent_sibling_imported_relatively(
    module_dir: Path, guarded: Callable[[str, str], str]
) -> None:
    # the absent module matches by its absolute name (#768)
    (package := module_dir / "relative_absent").mkdir()
    (package / "__init__.py").write_text(guarded("from .absent import Thing", "def func(value: Thing) -> None: ..."))
    func = import_module("relative_absent").func
    assert repr(get_all_type_hints([], func, "mod.func", {})["value"]) == "relative_absent.absent.Thing"


@mark.parametrize(
    ("guard", "dependency", "error"),
    [
        param(
            "from broken_dependency import Broken",
            "import no_such_inner",
            "No module named 'no_such_inner'",
            id="installed-but-broken",
        ),
        param(
            "import broken_dependency.sub",
            "",
            "No module named 'broken_dependency.sub'; 'broken_dependency' is not a package",
            id="module-imported-as-a-package",
        ),
        param(
            "import broken_dependency",
            'raise RuntimeError("boom")',
            "boom",
            id="raising-on-import",
        ),
    ],
)
def test_resolve_type_guarded_imports_warns_about_a_dependency_that_fails(
    module_dir: Path,
    make_module: Callable[[str], ModuleType],
    guarded: Callable[[str, str], str],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    guard: str,
    dependency: str,
    error: str,
) -> None:
    # mocking cannot stand in for an installed module, nor give a plain module a submodule (#768)
    (module_dir / "broken_dependency.py").write_text(dependency)
    module = make_module(guarded(guard, _FUNC))
    resolve_type_guarded_imports([], module.func)
    assert logged_warnings() == [
        ("guarded_import", f"{module.__file__}:{module.func.__code__.co_firstlineno}", module.__name__, error)
    ]


@mark.parametrize(
    ("dependency", "content", "guard", "expected"),
    [
        param(
            "needs_extra",
            'raise ImportError("install the extra")',
            dedent("""\
                import needs_extra
                from decimal import Decimal
            """),
            {"Decimal": Decimal},
            id="dependency-failing-without-a-name",
        ),
        param("target_mod", "", "from target_mod import nonexistent_name", {}, id="name-missing-from-its-module"),
    ],
)
def test_resolve_type_guarded_imports_skips_what_fails_silently(
    module_dir: Path,
    make_module: Callable[[str], ModuleType],
    guarded: Callable[[str, str], str],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    dependency: str,
    content: str,
    guard: str,
    expected: dict[str, Documented],
) -> None:
    (module_dir / f"{dependency}.py").write_text(content)
    module = make_module(guarded(guard, _FUNC))
    resolve_type_guarded_imports([], module.func)
    assert (guarded_names(module.func), logged_warnings()) == (expected, [])


def test_resolve_type_guarded_imports_warns_about_a_guard_that_does_not_parse(
    module_dir: Path,
    make_module: Callable[[str], ModuleType],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
) -> None:
    source = dedent("""\
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            import decimal

        def func(): ...
    """)
    module = make_module(source)
    (module_dir / f"{module.__name__}.py").write_text(
        source
        + dedent("""\

            if TYPE_CHECKING:
                this is not python (
        """)
    )
    resolve_type_guarded_imports([], module.func)
    assert logged_warnings() == [
        ("guarded_import", f"{module.__file__}:6", module.__name__, "'(' was never closed (<unknown>, line 2)")
    ]


def test_resolve_type_guarded_imports_reads_a_guard_of_a_module_whose_source_does_not_parse(
    module_dir: Path, make_module: Callable[[str], ModuleType], guarded: Callable[[str, str], str]
) -> None:
    source = dedent("""\
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            Thing = int
        else:
            Thing = str
    """)
    (module_dir / "unparsed_source.py").write_text(source)
    import_module("unparsed_source")
    # what a stale linecache entry or a transpiling loader hands inspect.getsource
    (module_dir / "unparsed_source.py").write_text(f"{source}this is not python (")
    module = make_module(guarded("from unparsed_source import Thing", _FUNC))
    resolve_type_guarded_imports([], module.func)
    assert guarded_names(module.func) == {"Thing": int}


@mark.parametrize(
    ("guard", "expected"),
    [
        param(
            dedent("""\
                from decimal import Decimal
                REGISTRY = {type: Decimal[type] for type in (int, str)}
            """),
            {"Decimal": Decimal, "REGISTRY": MyTypeAliasForwardRef("REGISTRY")},
            id="comprehension-leaving-the-builtin-alone",
        ),
        param(
            dedent("""\
                from decimal import Decimal
                if sys.version_info >= (3, 12):
                    Coords: TypeAlias = Decimal[int]
                else:
                    Coords: TypeAlias = Decimal
            """),
            {"Decimal": Decimal, "Coords": MyTypeAliasForwardRef("Coords")},
            id="version-gated-alias",
        ),
    ],
)
def test_resolve_type_guarded_imports_binds_a_name_the_interpreter_rejects(
    make_module: Callable[[str], ModuleType],
    guarded: Callable[[str, str], str],
    guard: str,
    expected: dict[str, Documented],
) -> None:
    # a type checker accepts what the interpreter cannot run, so the names stand in for themselves (#751)
    module = make_module(guarded(guard, _FUNC))
    resolve_type_guarded_imports([], module.func)
    # Python 3.14 records the annotations an if statement may set in __conditional_annotations__
    names = {name: value for name, value in guarded_names(module.func).items() if not name.startswith("__")}
    assert {name: (type(value), value) for name, value in names.items()} == {
        name: (type(value), value) for name, value in expected.items()
    }


_OVERLOADED_PICK: Final[str] = dedent("""\
    from __future__ import annotations
    from typing import TYPE_CHECKING, overload

    if TYPE_CHECKING:
        from decimal import Decimal

        @overload
        def pick(value: int) -> int: ...
        @overload
        def pick(value: str) -> str: ...

    def pick(value):
        return value
""")


@mark.parametrize(
    "source",
    [
        param(_OVERLOADED_PICK, id="overload-stubs"),
        param(
            dedent("""\
                from __future__ import annotations
                from typing import TYPE_CHECKING

                if TYPE_CHECKING:
                    from decimal import Decimal

                    class Store: ...

                class Store: ...
            """),
            id="class",
        ),
        param(
            dedent("""\
                from __future__ import annotations
                from typing import TYPE_CHECKING

                if TYPE_CHECKING:
                    from decimal import Context, Decimal

                Decimal = float
            """),
            id="import",
        ),
        param(
            dedent("""\
                from __future__ import annotations
                from typing import TYPE_CHECKING

                if TYPE_CHECKING:
                    from decimal import Decimal
                else:
                    Decimal = float
            """),
            id="else-branch",
        ),
        param(
            dedent("""\
                from __future__ import annotations
                from typing import TYPE_CHECKING

                if not TYPE_CHECKING:
                    Decimal = float
                else:
                    from decimal import Decimal
            """),
            id="negated-else-branch",
        ),
    ],
)
def test_resolve_type_guarded_imports_leaves_the_module_as_it_runs(
    make_module: Callable[[str], ModuleType], source: str
) -> None:
    module = make_module(f"{source}def func(value: Decimal) -> None: ...")
    runtime = dict(vars(module))
    resolve_type_guarded_imports([], module.func)
    assert (vars(module), guarded_names(module.func)["Decimal"]) == (runtime, Decimal)


def test_resolve_type_guarded_imports_registers_no_overload_for_a_runtime_function(
    make_module: Callable[[str], ModuleType],
) -> None:
    module = make_module(f"{_OVERLOADED_PICK}{_FUNC}")
    resolve_type_guarded_imports([], module.func)
    assert (get_overloads(module.pick), guarded_names(module.func)["Decimal"]) == ([], Decimal)


@mark.parametrize(
    "imported",
    [
        param("Fn", id="runtime-name"),
        param("Fn, Other", id="beside-a-guard-only-name"),
    ],
)
def test_resolve_type_guarded_imports_reads_a_name_as_the_guard_of_its_module_binds_it(
    module_dir: Path, make_module: Callable[[str], ModuleType], guarded: Callable[[str, str], str], imported: str
) -> None:
    (module_dir / "guarded_source.py").write_text(
        dedent("""\
            from collections.abc import Callable
            from typing import TYPE_CHECKING, Protocol

            if TYPE_CHECKING:
                class Fn(Protocol): ...

                Other = int
            else:
                Fn = Callable[[int], str]
        """)
    )
    module = make_module(guarded(f"from guarded_source import {imported}", _FUNC))
    resolve_type_guarded_imports([], module.func)
    assert isinstance(fn := guarded_names(module.func)["Fn"], type)
    assert fn.__bases__ == (Protocol,)


@mark.parametrize(
    ("order", "imported", "runtime"),
    [
        param(("amod_mutual", "bmod_mutual"), "AAlias", "", id="first-imported-first"),
        param(("bmod_mutual", "amod_mutual"), "AAlias", "", id="last-imported-first"),
        param(("amod_mutual", "bmod_mutual"), "AAlias", "AAlias = complex", id="importer-rebinds-it"),
        param(("amod_mutual", "bmod_mutual"), "AAlias, Missing", "", id="beside-a-name-never-bound"),
    ],
)
def test_resolve_type_guarded_imports_of_guards_importing_each_other(
    write_mutual_guards: _WriteMutualGuards, order: tuple[str, str], imported: str, runtime: str
) -> None:
    write_mutual_guards("amod_mutual", "bmod_mutual", imported=imported, runtime=runtime)
    hints = {name: get_all_type_hints([], import_module(name).func, f"{name}.func", {})["value"] for name in order}
    assert hints == {"amod_mutual": bytes, "bmod_mutual": int}


def test_resolve_type_guarded_imports_binds_what_a_guard_waited_on_after_another_raised(
    module_dir: Path, guarded: Callable[[str, str], str], write_mutual_guards: _WriteMutualGuards
) -> None:
    write_mutual_guards("amod_raised", "bmod_raised")
    (module_dir / "exiting_guard.py").write_text(guarded("import exiting_dependency", ""))
    (module_dir / "exiting_dependency.py").write_text("raise SystemExit(1)")
    with raises(SystemExit):
        resolve_type_guarded_imports([], import_module("exiting_guard"))
    get_all_type_hints([], import_module("amod_raised").func, "amod_raised.func", {})
    assert get_all_type_hints([], import_module("bmod_raised").func, "bmod_raised.func", {})["value"] is int


def test_resolve_type_guarded_imports_reads_what_a_guard_bound_for_a_module_it_removed(
    write_mutual_guards: _WriteMutualGuards,
) -> None:
    write_mutual_guards(
        "amod_removed",
        "bmod_removed",
        extra=dedent("""\
            import sys
            del sys.modules["amod_removed"]
        """),
    )
    get_all_type_hints([], import_module("amod_removed").func, "amod_removed.func", {})
    assert get_all_type_hints([], import_module("bmod_removed").func, "bmod_removed.func", {})["value"] is int


@mark.parametrize(
    ("package", "aliases", "kind"),
    [
        param("guard_leak_class", "Kind = int", '"int"', id="guard-only-class"),
        param("guard_leak_alias", 'type Kind = "Left" | "Right"', '"Kind"', id="alias-whose-value-fails"),
    ],
)
@mark.sphinx("text", testroot="integration")
def test_build_lists_no_member_the_guard_of_an_imported_member_adds(
    app: SphinxTestApp,
    build_text: BuildText,
    monkeypatch: MonkeyPatch,
    package: str,
    aliases: str,
    kind: str,
) -> None:
    (directory := Path(app.srcdir) / package).mkdir()
    (directory / "__init__.py").touch()
    (directory / "aliases.py").write_text(aliases)
    (directory / "impl.py").write_text(
        dedent("""\
            from __future__ import annotations

            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from typing import Protocol

                from .aliases import Kind

                class Reader(Protocol):
                    def read(self) -> bytes: ...


            class Parser:
                '''Parse.'''

                def parse(self, reader: Reader, kind: Kind) -> int:
                    '''Parse it.

                    :param reader: the source
                    :param kind: the kind
                    '''
                    return 1
        """)
    )
    (directory / "api.py").write_text(f"from {package}.impl import Parser")
    monkeypatch.syspath_prepend(app.srcdir)
    assert build_text(
        dedent(f"""\
            .. automodule:: {package}.api
               :members:

            .. automodule:: {package}.impl
               :members:
               :undoc-members:
        """)
    ) == dedent(f"""\
        class {package}.impl.Parser

           Parse.

           parse(reader, kind)

              Parse it.

              Parameters:
                 * **reader** ("Reader") -- the source

                 * **kind** ({kind}) -- the kind

              Return type:
                 "int"
    """)


@mark.parametrize(
    ("module", "expected"),
    [
        # names from code only a type checker runs render without warnings (#751)
        param(
            "demo_unexecutable_guard",
            dedent("""\
                Module demonstrating type guarded code that the interpreter cannot run.

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
            """),
            marks=mark.sphinx("text", testroot="unexecutable-guard"),
            id="guard-the-interpreter-rejects",
        ),
        # mocking a dependency the docs environment lacks keeps its types as cross-references (#768)
        param(
            "demo_absent_guarded_dependency",
            dedent("""\
                Module whose type checking guard names a dependency the docs environment lacks.

                demo_absent_guarded_dependency.load(cube, array, precision)

                   Load a cube.

                   Parameters:
                      * **cube** ("Cube") -- the cube

                      * **array** ("Array") -- the backing array

                      * **precision** ("Decimal") -- the precision

                   Return type:
                      "list"["Cube"]

                   Returns:
                      the cubes
            """),
            marks=mark.sphinx("text", testroot="absent-guarded-dependency"),
            id="absent-guarded-dependency",
        ),
        param(
            "demo_typing_guard",
            dedent(f"""\
                Module demonstrating imports that are type guarded

                class demo_typing_guard.AnotherClass

                   Another class is here

                class demo_typing_guard.SomeClass

                   This class do something.

                   create(item)

                      Create something.

                      Parameters:
                         **item** ("Decimal") -- the item in question

                      Return type:
                         "None"

                exception demo_typing_guard.ValueError

                   Inappropriate argument value (of correct type).

                demo_typing_guard.a[AnyStr: (bytes, str)](f, s)

                   Do.

                   Parameters:
                      * **f** ("Decimal") -- first

                      * **s** ("AnyStr") -- second

                   Return type:
                      "Sequence"[{
                # Python 3.14 writes a Union with bars
                '"AnyStr" | "Decimal"' if version_info >= (3, 14) else '"Union"["AnyStr", "Decimal"]'
            }]

                   Returns:
                      result

                demo_typing_guard.cmp_to_key(mycmp)

                   Convert a cmp= function into a key= function.

                   mycmp
                      Function that compares two objects.
            """),
            marks=mark.sphinx(
                "text", testroot="resolve-typing-guard", confoverrides={"autodoc_mock_imports": ["viktor"]}
            ),
            id="guarded-imports",
        ),
        param(
            "demo_typing_guard",
            dedent("""\
                Module demonstrating imports that are type guarded

                class demo_typing_guard.SomeClass(date)

                   This class does something.

                   calculate_thing(number)

                      Calculate a thing

                      Parameters:
                         **number** ("float") -- Input

                      Return type:
                         "timedelta"

                      Returns:
                         result

                   date: date

                      Date to handle

                   classmethod from_date(input_value)

                      Initialize from date

                      Parameters:
                         **input_value** ("date") -- Input

                      Return type:
                         "SomeClass"

                      Returns:
                         result

                   classmethod from_str(input_value)

                      Initialize from string

                      Parameters:
                         **input_value** ("str") -- Input

                      Return type:
                         "SomeClass"

                      Returns:
                         result

                   classmethod from_time(input_value)

                      Initialize from time

                      Parameters:
                         **input_value** ("time") -- Input

                      Return type:
                         "SomeClass"

                      Returns:
                         result
            """),
            marks=mark.sphinx("text", testroot="resolve-typing-guard-tmp"),
            id="attrs-class",
        ),
    ],
)
@mark.usefixtures("wide_text_output")
def test_build_documents_the_names_of_a_guard(
    build_text: BuildText, warning: StringIO, monkeypatch: MonkeyPatch, module: str, expected: str
) -> None:
    # roots may name their module alike
    monkeypatch.delitem(modules, module, raising=False)
    assert (
        build_text(
            dedent(f"""\
                .. automodule:: {module}
                   :members:
            """)
        ),
        warning.getvalue(),
    ) == (expected, "")


class _WriteMutualGuards(Protocol):
    def __call__(
        self, first: str, second: str, *, imported: str = ..., runtime: str = ..., extra: str = ...
    ) -> None: ...


@fixture(name="guarded")
def guarded_fixture() -> Callable[[str, str], str]:
    def source(guard: str, body: str) -> str:
        return "\n".join((_GUARD, indent(guard, "    "), body))

    return source


@fixture(name="write_mutual_guards")
def write_mutual_guards_fixture(module_dir: Path) -> _WriteMutualGuards:
    def write(first: str, second: str, *, imported: str = "AAlias", runtime: str = "", extra: str = "") -> None:
        (module_dir / f"{first}.py").write_text(
            "\n".join((
                _GUARD,
                f"    from {second} import BAlias",
                "    AAlias = int",
                "else:",
                "    AAlias = str",
                "def func(value: BAlias) -> None: ...",
            ))
        )
        (module_dir / f"{second}.py").write_text(
            "\n".join((
                _GUARD,
                f"    from {first} import {imported}",
                indent(extra, "    "),
                "    BAlias = bytes",
                "else:",
                "    BAlias = float",
                indent(runtime, "    "),
                "def func(value: AAlias) -> None: ...",
            ))
        )

    return write
