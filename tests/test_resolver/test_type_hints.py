from __future__ import annotations

import ast
import csv
import importlib
import logging
import re
import subprocess  # ruff:ignore[suspicious-subprocess-import]
import sys
import sysconfig
import types
from collections.abc import Iterator, Mapping, Sequence
from csv import Error
from decimal import Decimal
from pathlib import Path
from typing import (
    Any,
    Final,
    ParamSpec,
    Protocol,
    TypeAliasType,
    TypeVar,
    TypeVarTuple,
    Union,
    get_args,
    get_origin,
)
from unittest.mock import MagicMock, patch

import pytest
from conftest import make_docstring_app
from sphinx.ext.autodoc.mock import mock

from sphinx_autodoc_typehints import process_docstring
from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef
from sphinx_autodoc_typehints._resolver._type_hints import (
    _TYPE_GUARD_IMPORTS_RESOLVED,
    _build_localns,
    _execute_guarded_code,
    _get_type_hint,
    _run_guarded_import,
    _should_skip_guarded_import_resolution,
    get_all_type_hints,
    get_descriptor_type_hint,
    resolve_string_annotations,
    resolve_type_guarded_imports,
)

STUB_ROOT = Path(__file__).parent.parent / "roots" / "test-pyi-stubs"


def test_no_source_code_type_guard() -> None:
    resolve_type_guarded_imports([], Error)


@pytest.mark.parametrize(
    "annotation",
    [pytest.param("a positive float", id="prose"), pytest.param("csv.NoSuchName", id="missing-attribute")],
)
def test_process_docstring_keeps_an_unresolvable_annotation_as_written(
    unresolvable: types.FunctionType, annotation: str
) -> None:
    lines = [":param count: the count", ":param value: the value"]
    app = make_docstring_app(typehints_document_rtype=False)
    process_docstring(app, "function", "mod.unresolvable", unresolvable, None, lines)
    assert lines == [
        r":type count: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        ":param count: the count",
        f":type value: :sphinx_autodoc_typehints_type:`{annotation}`",
        ":param value: the value",
    ]


@pytest.mark.parametrize(
    ("annotation", "message"),
    [
        pytest.param(
            "a positive float", "Forward reference must be an expression -- got 'a positive float'", id="prose"
        ),
        pytest.param("csv.NoSuchName", "module 'csv' has no attribute 'NoSuchName'", id="missing-attribute"),
    ],
)
def test_process_docstring_warns_on_an_unresolvable_annotation(
    unresolvable: types.FunctionType, message: str, caplog: pytest.LogCaptureFixture
) -> None:
    app = make_docstring_app(typehints_document_rtype=False)
    process_docstring(app, "function", "mod.unresolvable", unresolvable, None, [])
    # sphinx rewrites the message once a build has set up its logging, so compare the record's fields
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert [(vars(record)["subtype"], str(vars(record)["args"][-1])) for record in warnings] == [
        ("forward_reference", message)
    ]


with mock(["_sat_mocked"]):
    # a module autodoc_mock_imports stands in for
    Gen = importlib.import_module("_sat_mocked").Gen


def _mocked_union(value: Gen[int] | None) -> None: ...


def _mocked_union_with_arithmetic(value: Gen[3 * 3] | None) -> None: ...


_MOCKED_LINK: Final = r"\:py\:class\:\`\~\_sat\_mocked.Gen\`"


@pytest.mark.parametrize(
    "func",
    [pytest.param(_mocked_union, id="plain"), pytest.param(_mocked_union_with_arithmetic, id="beside-arithmetic")],
)
def test_process_docstring_links_a_mocked_type_in_a_pipe_union(func: types.FunctionType) -> None:
    lines = [":param value: the value"]
    app = make_docstring_app(typehints_document_rtype=False)
    process_docstring(app, "function", "mod.mocked", func, None, lines)
    assert _MOCKED_LINK in lines[0]


@pytest.mark.skipif(sys.version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_process_docstring_links_a_lazy_mocked_type_in_a_pipe_union() -> None:  # pragma: >=3.14 cover
    namespace: dict[str, Any] = {"__name__": __name__, "Gen": Gen}
    # dont_inherit keeps this file's `from __future__ import annotations` out, so the annotation stays lazy
    source = "def mocked(value: Gen[int] | None) -> None: ..."
    exec(compile(source, "<mocked>", "exec", dont_inherit=True), namespace)  # ruff:ignore[exec-builtin]
    lines = [":param value: the value"]
    app = make_docstring_app(typehints_document_rtype=False)
    process_docstring(app, "function", "mod.mocked", namespace["mocked"], None, lines)
    assert _MOCKED_LINK in lines[0]


def test_process_docstring_resolves_a_reexported_function_in_its_defining_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "reexporting"
    package.mkdir()
    (package / "_impl.py").write_text(
        "from __future__ import annotations\nimport decimal\n\n"
        "def f(a: decimal.Decimal, b: NotDefinedAnywhere) -> None: ...\n"
    )
    (package / "__init__.py").write_text("from reexporting._impl import f\nf.__module__ = 'reexporting'\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    func = importlib.import_module("reexporting").f
    lines = [":param a: the a"]
    process_docstring(
        make_docstring_app(typehints_document_rtype=False), "function", "reexporting.f", func, None, lines
    )
    assert lines == [r":type a: :sphinx_autodoc_typehints_type:`\:py\:class\:\`\~decimal.Decimal\``", ":param a: the a"]


class _Shape:
    def __class_getitem__(cls, item: type) -> type[_Shape]:
        msg = f"a shape cannot take {item}"
        raise ValueError(msg)


def _rejected(value: _Shape[int]) -> None: ...


def test_process_docstring_shows_an_annotation_that_raises_as_written(caplog: pytest.LogCaptureFixture) -> None:
    lines = [":param value: the value"]
    process_docstring(
        make_docstring_app(typehints_document_rtype=False), "function", "mod.rejected", _rejected, None, lines
    )
    expected = [
        r":type value: :sphinx_autodoc_typehints_type:`\_Shape\[int\]`",
        ":param value: the value",
    ]
    assert (lines, [record for record in caplog.records if record.levelno >= logging.WARNING]) == (expected, [])


@pytest.fixture
def unresolvable(annotation: str) -> types.FunctionType:
    def annotated(count: int, value: str) -> None: ...

    # the type checkers reject these when written as an annotation
    annotated.__annotations__["value"] = annotation
    return annotated


def test_should_skip_module_type() -> None:
    assert not _should_skip_guarded_import_resolution(csv)


def test_should_skip_no_globals() -> None:
    assert _should_skip_guarded_import_resolution(42)


def test_should_skip_builtin_module() -> None:
    fn: Any = type("FakeFunc", (), {"__globals__": {}, "__module__": "builtins"})()
    assert _should_skip_guarded_import_resolution(fn)


def test_get_type_hint_recursion_error() -> None:
    def func(x: int) -> str: ...

    with patch("sphinx_autodoc_typehints._resolver._type_hints.get_type_hints", side_effect=RecursionError):
        assert _get_type_hint([], "test", func, {}) == {}


@pytest.fixture
def non_subscriptable_generic_func() -> Any:  # pragma: >=3.14 cover
    # dont_inherit keeps this file's `from __future__ import annotations` (PEP 563) out of the
    # compiled module so its annotations stay lazily evaluated (PEP 649)
    source = "class NotGeneric: ...\n\n\ndef func(g: NotGeneric[int]) -> None: ...\n"
    ns: dict[str, Any] = {}
    exec(compile(source, "<mod_712>", "exec", dont_inherit=True), ns)  # ruff:ignore[exec-builtin]
    return ns["func"]


@pytest.mark.skipif(sys.version_info < (3, 14), reason="PEP 649 lazy annotation evaluation is Python 3.14+")
def test_get_type_hint_unevaluatable_annotation_falls_back_to_forward_ref(
    non_subscriptable_generic_func: Any,
) -> None:  # pragma: >=3.14 cover
    """Annotations whose evaluation raises TypeError degrade to ForwardRef proxies (issue #712)."""
    result = _get_type_hint([], "test.func", non_subscriptable_generic_func, {})
    assert result["g"].__forward_arg__ == "NotGeneric[int]"


@pytest.mark.skipif(sys.version_info < (3, 14), reason="PEP 649 lazy annotation evaluation is Python 3.14+")
def test_get_type_hint_forward_ref_fallback_failure_returns_empty(
    non_subscriptable_generic_func: Any,
) -> None:  # pragma: >=3.14 cover
    """When even the FORWARDREF format cannot evaluate the annotations, fall back to no hints."""
    with patch("sphinx_autodoc_typehints._resolver._type_hints.annotationlib.get_annotations", side_effect=TypeError):
        assert _get_type_hint([], "test.func", non_subscriptable_generic_func, {}) == {}


def test_execute_guarded_code_catches_exception() -> None:
    module = type("FakeModule", (), {"__globals__": {}, "__dict__": {}})()
    with patch("sphinx_autodoc_typehints._resolver._type_hints._run_guarded_import", side_effect=RuntimeError("boom")):
        _execute_guarded_code([], module, "\nif TYPE_CHECKING:\n    import os\nx = 1\n")


def test_run_guarded_import_no_exc_name() -> None:
    ns: dict[str, Any] = {}
    obj: Any = type("FakeObj", (), {"__globals__": ns})()
    _run_guarded_import([], obj, ast.parse("raise ImportError()").body[0])


def test_forward_ref_warning_includes_module() -> None:
    def func(x: int) -> str: ...

    func.__module__ = "some_module"
    func.__annotations__ = {"x": "NonExistent"}
    mock_logger = MagicMock()
    with (
        patch("sphinx_autodoc_typehints._resolver._type_hints.get_type_hints", side_effect=NameError("NonExistent")),
        patch("sphinx_autodoc_typehints._resolver._type_hints._LOGGER", mock_logger),
    ):
        _get_type_hint([], "func", func, {})
    mock_logger.warning.assert_called_once()
    args = mock_logger.warning.call_args
    assert "some_module" in str(args)
    assert "location" in args.kwargs


def test_guarded_import_warning_includes_module() -> None:
    module = type("FakeModule", (), {"__globals__": {}, "__dict__": {}, "__module__": "fake_mod"})()
    mock_logger = MagicMock()
    with (
        patch("sphinx_autodoc_typehints._resolver._type_hints._run_guarded_import", side_effect=RuntimeError("boom")),
        patch("sphinx_autodoc_typehints._resolver._type_hints._LOGGER", mock_logger),
    ):
        _execute_guarded_code([], module, "\nif TYPE_CHECKING:\n    import os\nx = 1\n")
    mock_logger.warning.assert_called_once()
    args = mock_logger.warning.call_args
    assert "fake_mod" in str(args)


def test_get_all_type_hints_for_class_owning_the_type_params_slot() -> None:
    """typing.TypeAliasType hands back the __type_params__ descriptor rather than a tuple (issue #740)."""
    assert get_all_type_hints([], TypeAliasType, "mod.TypeAliasType", {}) == {}


class _GuardedModuleBuilder(Protocol):
    def __call__(
        self, source: str, *, package: bool = False, files: Mapping[str, str] | None = None
    ) -> types.ModuleType: ...


@pytest.fixture
def guarded_module(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[_GuardedModuleBuilder]:
    name = re.sub(r"\W", "_", request.node.name)
    sys.path.insert(0, str(tmp_path))

    def build(source: str, *, package: bool = False, files: Mapping[str, str] | None = None) -> types.ModuleType:
        for path, content in {f"{name}/__init__.py" if package else f"{name}.py": source, **(files or {})}.items():
            (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / path).write_text(content)
        return importlib.import_module(name)

    yield build
    sys.path.remove(str(tmp_path))
    for loaded, module in list(sys.modules.items()):
        if str(getattr(module, "__file__", None) or "").startswith(str(tmp_path)):
            del sys.modules[loaded]


def test_guarded_import_binds_names_below_an_unimportable_one(
    guarded_module: _GuardedModuleBuilder,
) -> None:
    """An absent optional dependency must not strand the imports under it (issue #741)."""
    module = guarded_module(
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from no_such_dependency import Absent\n"
        "    from decimal import Decimal\n"
        "\n"
        "def func(value: Decimal) -> None: ...\n"
    )
    assert get_all_type_hints([], module.func, f"{module.__name__}.func", {})["value"] is Decimal


def test_guarded_import_resolves_for_a_reexported_function(guarded_module: _GuardedModuleBuilder) -> None:
    module = guarded_module(
        "from reexported_impl import convert\n\nconvert.__module__ = __name__\n",
        files={
            "reexported_impl.py": "from __future__ import annotations\n"
            "from typing import TYPE_CHECKING\n"
            "\n"
            "if TYPE_CHECKING:\n"
            "    from decimal import Decimal\n"
            "\n"
            "def convert(value: Decimal) -> None: ...\n"
        },
    )
    assert get_all_type_hints([], module.convert, f"{module.__name__}.convert", {})["value"] is Decimal


@pytest.mark.parametrize(
    ("declaration", "annotation", "kind"),
    [
        pytest.param("T: int", "T", TypeVar, id="type-var"),
        pytest.param("**P", "P", ParamSpec, id="param-spec"),
        pytest.param("*Ts", "Ts", TypeVarTuple, id="type-var-tuple"),
    ],
)
def test_stub_generic_parameters_resolve_on_repeated_calls(
    guarded_module: _GuardedModuleBuilder,
    declaration: str,
    annotation: str,
    kind: type[TypeVar | ParamSpec | TypeVarTuple],
) -> None:
    module = guarded_module("def func(value): return value\n")
    Path(str(module.__file__)).with_suffix(".pyi").write_text(
        f"from collections.abc import Callable\ndef func[{declaration}](value: {annotation}) -> {annotation}: ...\n"
    )
    for _ in range(2):
        assert {
            key: (type(value), value.__name__) for key, value in get_all_type_hints([], module.func, "func", {}).items()
        } == {
            "value": (kind, annotation),
            "return": (kind, annotation),
        }


def test_stub_method_resolves_class_and_function_parameters(guarded_module: _GuardedModuleBuilder) -> None:
    module = guarded_module("class Owner:\n    async def func(self, value): return value\n")
    Path(str(module.__file__)).with_suffix(".pyi").write_text(
        "from collections.abc import Callable\n"
        "class Owner[T]:\n"
        "    async def func[**P](self, value: Callable[P, T]) -> T: ...\n"
    )
    assert {key: str(value) for key, value in get_all_type_hints([], module.Owner.func, "Owner.func", {}).items()} == {
        "value": "collections.abc.Callable[~P, ~T]",
        "return": "~T",
    }


def test_guarded_import_resolves_namedtuple_field_without_prior_function(
    guarded_module: _GuardedModuleBuilder,
) -> None:
    module = guarded_module(
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING, NamedTuple\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from pathlib import Path\n"
        "\n"
        "class P(NamedTuple):\n"
        "    path: Path\n"
    )
    assert get_all_type_hints([], module.P, f"{module.__name__}.P", {}) == {"path": Path}


_GUARDED_FUNC: Final = "def func(value: Decimal) -> None: ...\n"


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            f"import typing as t\n\nif t.TYPE_CHECKING:\n    from decimal import Decimal\n\n{_GUARDED_FUNC}",
            id="module-alias",
        ),
        pytest.param(
            f"from typing import TYPE_CHECKING\n\n{_GUARDED_FUNC}\n"
            "if TYPE_CHECKING:\n    from decimal import Decimal\n",
            id="end-of-file",
        ),
        pytest.param(
            "from typing import TYPE_CHECKING\n\n"
            "if TYPE_CHECKING:\n    import os\n# a note\n    from decimal import Decimal\n\n"
            f"{_GUARDED_FUNC}",
            id="column-zero-comment",
        ),
        pytest.param(
            f"from typing import TYPE_CHECKING\n\nif TYPE_CHECKING: from decimal import Decimal\n\n{_GUARDED_FUNC}",
            id="one-line",
        ),
        pytest.param(
            "from typing import TYPE_CHECKING\n\n"
            'if TYPE_CHECKING:\n    DOC = """\ntext\n"""\n    from decimal import Decimal\n\n'
            f"{_GUARDED_FUNC}",
            id="multi-line-string",
        ),
        pytest.param(
            "from typing import TYPE_CHECKING\n\n"
            "if not TYPE_CHECKING:\n    pass\nelse:\n    from decimal import Decimal\n\n"
            f"{_GUARDED_FUNC}",
            id="negated-else",
        ),
        pytest.param(
            "import typing\nfrom typing import TYPE_CHECKING\n\n"
            "if TYPE_CHECKING and typing.TYPE_CHECKING:\n    from decimal import Decimal\n\n"
            f"{_GUARDED_FUNC}",
            id="compound-and",
        ),
        pytest.param(
            "import sys\nfrom typing import TYPE_CHECKING\n\n"
            "if TYPE_CHECKING or sys.version_info < (3, 0):\n    from decimal import Decimal\n\n"
            f"{_GUARDED_FUNC}",
            id="compound-or",
        ),
        pytest.param(
            "import sys\nfrom typing import TYPE_CHECKING\n\n"
            "if TYPE_CHECKING:\n    from decimal import Decimal\n"
            "if not sys.argv:\n    Decimal = int\n"
            "if sys.argv and sys.path:\n    Decimal = int\n\n"
            f"{_GUARDED_FUNC}",
            id="unrelated-tests-left-alone",
        ),
    ],
)
def test_guarded_import_binds_names_from_any_guard_form(source: str, guarded_module: _GuardedModuleBuilder) -> None:
    module = guarded_module(f"from __future__ import annotations\n\n{source}")
    hints = get_all_type_hints([], module.func, f"{module.__name__}.func", {})
    assert hints == {"value": Decimal, "return": type(None)}


@pytest.mark.parametrize(
    ("guard", "annotation", "display_name"),
    [
        pytest.param("from no_such_dependency import Absent", "Absent", "no_such_dependency.Absent", id="from"),
        pytest.param(
            "import no_such_dependency.sub",
            "no_such_dependency.sub.Absent",
            "no_such_dependency.sub.Absent",
            id="dotted",
        ),
        pytest.param(
            "try:\n"
            "        from no_such_dependency import Absent\n"
            "    except ImportError:\n"
            "        from no_such_fallback import Absent",
            "Absent",
            "no_such_fallback.Absent",
            id="try-except",
        ),
    ],
)
def test_guarded_import_mocks_an_absent_dependency(
    guarded_module: _GuardedModuleBuilder, guard: str, annotation: str, display_name: str
) -> None:
    """The resolver mocks a guarded dependency the docs environment lacks, as autodoc_mock_imports would (#768)."""
    module = guarded_module(
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        f"    {guard}\n"
        "\n"
        f"def func(value: {annotation}) -> None: ...\n"
    )
    mock_logger = MagicMock()
    with patch("sphinx_autodoc_typehints._resolver._type_hints._LOGGER", mock_logger):
        hints = get_all_type_hints([], module.func, f"{module.__name__}.func", {})
    mock_logger.warning.assert_not_called()
    assert hints["value"].__display_name__ == display_name


def test_guarded_relative_import_of_an_absent_sibling_is_mocked(guarded_module: _GuardedModuleBuilder) -> None:
    """The resolver matches the absent module by absolute name, so a relative guarded import gets mocked too (#768)."""
    module = guarded_module(
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from .absent import Thing\n"
        "\n"
        "def func(value: Thing) -> None: ...\n",
        package=True,
    )
    hint = get_all_type_hints([], module.func, f"{module.__name__}.func", {})["value"]
    assert hint.__display_name__ == f"{module.__name__}.absent.Thing"


def test_guarded_import_warns_when_the_dependency_is_installed_but_broken(
    guarded_module: _GuardedModuleBuilder,
) -> None:
    """A dependency that is installed yet fails to import is an environment fault and still warns (#768)."""
    module = guarded_module(
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from broken_dependency import Broken\n"
        "\n"
        "def func(value: Broken) -> None: ...\n",
        files={"broken_dependency.py": "import no_such_inner\n"},
    )
    mock_logger = MagicMock()
    with patch("sphinx_autodoc_typehints._resolver._type_hints._LOGGER", mock_logger):
        get_all_type_hints([], module.func, f"{module.__name__}.func", {})
    assert "No module named 'no_such_inner'" in str(mock_logger.warning.call_args_list)


def test_guarded_import_warns_when_a_module_is_imported_as_a_package(guarded_module: _GuardedModuleBuilder) -> None:
    """Mocking cannot give a plain module a submodule, so the failure warns once instead of looping (#768)."""
    module = guarded_module(
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    import plain_module.sub\n"
        "\n"
        "def func(value: plain_module.sub.Thing) -> None: ...\n",
        files={"plain_module.py": ""},
    )
    mock_logger = MagicMock()
    with patch("sphinx_autodoc_typehints._resolver._type_hints._LOGGER", mock_logger):
        get_all_type_hints([], module.func, f"{module.__name__}.func", {})
    assert "'plain_module' is not a package" in str(mock_logger.warning.call_args_list)


def test_guarded_comprehension_target_leaves_the_builtin_alone(
    guarded_module: _GuardedModuleBuilder,
) -> None:
    """Only the statement's own targets are stood in, so a comprehension variable cannot shadow a builtin (#751)."""
    module = guarded_module(
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from decimal import Decimal\n"
        "    REGISTRY = {type: Decimal[type] for type in (int, str)}\n"
        "\n"
        "def func(value: type, registry: REGISTRY) -> None: ...\n"
    )
    hints = get_all_type_hints([], module.func, f"{module.__name__}.func", {})
    assert hints["value"] is type
    assert hints["registry"].name == "REGISTRY"


def test_guarded_version_gated_alias_binds_its_name(
    guarded_module: _GuardedModuleBuilder,
) -> None:
    """A failing annotated assignment nested in a version check still leaves its name usable (#751)."""
    module = guarded_module(
        "from __future__ import annotations\n"
        "import sys\n"
        "from typing import TYPE_CHECKING, TypeAlias\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from decimal import Decimal\n"
        "    if sys.version_info >= (3, 12):\n"
        "        Coords: TypeAlias = Decimal[int]\n"
        "    else:\n"
        "        Coords: TypeAlias = Decimal\n"
        "\n"
        "def func(value: Coords) -> None: ...\n"
    )
    assert get_all_type_hints([], module.func, f"{module.__name__}.func", {})["value"].name == "Coords"


def test_get_all_type_hints_resolves_a_class_nested_beside_the_method() -> None:
    hints = get_all_type_hints([], Outer.make, f"{__name__}.Outer.make", {})
    assert hints == {"value": Outer.Inner, "return": Outer.Inner}


class Outer:
    class Inner: ...

    def make(self, value: Inner) -> Inner: ...


def test_build_localns_adds_ancestor_classes() -> None:
    import tests.roots.test_nested_attrs_localns as mod  # ruff:ignore[import-outside-top-level]

    assert _build_localns(mod.Outer.Inner.__init__, {})["Outer"] is mod.Outer


def test_build_localns_no_qualname() -> None:
    def func() -> None: ...

    func.__qualname__ = "func"
    localns: dict[Any, Any] = {"existing": 1}
    assert _build_localns(func, localns) == {"existing": 1}


def test_build_localns_preserves_existing_localns() -> None:
    import tests.roots.test_nested_attrs_localns as mod  # ruff:ignore[import-outside-top-level]

    localns: dict[Any, Any] = {"key": "value"}
    assert (result := _build_localns(mod.Outer.Inner.__init__, localns))["key"] == "value"
    assert result["Outer"] is mod.Outer


def test_resolve_string_annotations_keeps_unresolvable_strings() -> None:
    obj = MagicMock()
    obj.__module__ = "builtins"
    result = resolve_string_annotations(obj, {"x": "NoSuchType", "y": "int"}, {})
    assert result["x"] == "NoSuchType"
    assert result["y"] is int


def test_resolve_string_annotations_passes_non_strings() -> None:
    obj = MagicMock()
    obj.__module__ = "builtins"
    result = resolve_string_annotations(obj, {"x": int, "return": str}, {})
    assert result["x"] is int
    assert result["return"] is str


@pytest.fixture(scope="session")
def c_ext_mod(tmp_path_factory: pytest.TempPathFactory) -> Any:
    if not sysconfig.get_config_var("LDSHARED"):
        pytest.skip("no C compiler available")
    build_dir = tmp_path_factory.mktemp("c_ext")
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    so_file = build_dir / f"c_ext_mod{ext_suffix}"
    include_dir = sysconfig.get_path("include")
    cc = sysconfig.get_config_var("CC") or "cc"
    ldshared = sysconfig.get_config_var("LDSHARED") or f"{cc} -shared"
    cflags = sysconfig.get_config_var("CFLAGS") or ""
    c_src = str(STUB_ROOT / "c_ext_mod.c")
    try:
        subprocess.check_call(
            [*ldshared.split(), f"-I{include_dir}", *cflags.split(), "-o", str(so_file), c_src],
            cwd=str(STUB_ROOT),
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("C extension compilation failed")
    for stub in STUB_ROOT.glob("c_ext_mod.pyi"):
        (build_dir / stub.name).write_text(stub.read_text())
    sys.path.insert(0, str(build_dir))
    try:
        mod = importlib.import_module("c_ext_mod")
    finally:
        sys.path.pop(0)
    return mod


def test_get_all_type_hints_resolves_stub_annotations_for_c_extension(c_ext_mod: Any) -> None:
    result = get_all_type_hints([], c_ext_mod.greet, "c_ext_mod.greet", {})
    assert result["name"] is str
    assert result["greeting"] == Sequence[str]
    assert result["return"] is str


def test_get_all_type_hints_preserves_stub_type_aliases(c_ext_mod: Any) -> None:
    result = get_all_type_hints([], c_ext_mod.with_hook, "c_ext_mod.with_hook", {})
    assert isinstance(result["callback"], MyTypeAliasForwardRef)
    assert result["callback"].name == "GreetHook"


def test_descriptor_type_hint_resolves_from_stub(c_ext_mod: Any) -> None:
    assert get_descriptor_type_hint(c_ext_mod.Encoder.depth) is int


def test_descriptor_type_hint_preserves_stub_type_aliases(c_ext_mod: Any) -> None:
    hint = get_descriptor_type_hint(c_ext_mod.Encoder.hook)
    args = get_args(hint)
    assert len(args) == 2
    encoder_hook = args[0] if isinstance(args[0], MyTypeAliasForwardRef) else args[1]
    assert encoder_hook.name == "EncoderHook"


def test_descriptor_type_hint_resolves_class_annotation(c_ext_mod: Any) -> None:
    assert get_descriptor_type_hint(c_ext_mod.Encoder.flags) is int


def test_descriptor_type_hint_inside_version_guard(c_ext_mod: Any) -> None:
    assert get_descriptor_type_hint(c_ext_mod.Encoder.guarded) is bool


def test_descriptor_type_hint_for_non_class_stub_node(c_ext_mod: Any) -> None:
    fake_class = type("greet", (), {"__module__": c_ext_mod.__name__, "__qualname__": "greet"})
    descriptor = types.SimpleNamespace(__objclass__=fake_class, __name__="depth")
    assert get_descriptor_type_hint(descriptor) is None


def test_descriptor_type_hint_for_name_missing_from_stub(c_ext_mod: Any) -> None:
    descriptor = types.SimpleNamespace(__objclass__=c_ext_mod.Encoder, __name__="missing")
    assert get_descriptor_type_hint(descriptor) is None


def test_process_docstring_injects_descriptor_type(c_ext_mod: Any) -> None:
    app = make_docstring_app()
    lines = ["current nesting depth"]
    process_docstring(app, "attribute", "c_ext_mod.Encoder.depth", c_ext_mod.Encoder.depth, None, lines)
    assert lines[0] == "current nesting depth"
    assert lines[-1].startswith(":type: ")
    assert "int" in lines[-1]


def test_descriptor_type_hint_without_stub_is_none() -> None:
    import array  # ruff:ignore[import-outside-top-level]

    assert get_descriptor_type_hint(array.array.typecode) is None


def test_descriptor_type_hint_ignores_non_descriptors() -> None:
    assert get_descriptor_type_hint(object()) is None


def test_get_all_type_hints_resolves_c_extension_class_new(c_ext_mod: Any) -> None:
    result = get_all_type_hints([], c_ext_mod.Encoder.__new__, "c_ext_mod.Encoder.__new__", {})
    default_type = result["default"]
    # Python 3.14+ produces types.UnionType for `X | None`, earlier versions produce typing.Union/Optional.
    assert get_origin(default_type) in {types.UnionType, Union}
    args = get_args(default_type)
    assert len(args) == 2
    encoder_hook = args[0] if isinstance(args[0], MyTypeAliasForwardRef) else args[1]
    assert isinstance(encoder_hook, MyTypeAliasForwardRef)
    assert encoder_hook.name == "EncoderHook"


def test_stub_annotations_not_polluted_on_repeated_calls(tmp_path: Path) -> None:
    pkg = tmp_path / "stubpkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "_types.py").write_text("class MyType: ...\n")
    (pkg / "mod.py").write_text("class Klass:\n    def method(self, x): ...\n")
    (pkg / "mod.pyi").write_text(
        "from stubpkg._types import MyType\nclass Klass:\n    def method(self, x: MyType) -> None: ...\n"
    )
    sys.path.insert(0, str(tmp_path))
    mod = importlib.import_module("stubpkg.mod")
    _TYPE_GUARD_IMPORTS_RESOLVED.discard("stubpkg.mod")
    my_type = importlib.import_module("stubpkg._types").MyType
    try:
        result1 = get_all_type_hints([], mod.Klass.method, "stubpkg.mod.Klass.method", {})
        assert result1["x"] is my_type
        _TYPE_GUARD_IMPORTS_RESOLVED.discard("stubpkg.mod")
        result2 = _get_type_hint([], "another.Klass.method", mod.Klass.method, {})
        assert result2.get("x") is my_type
    finally:
        sys.path.pop(0)
        for name in [n for n in sys.modules if n.startswith("stubpkg")]:
            del sys.modules[name]
        _TYPE_GUARD_IMPORTS_RESOLVED.discard("stubpkg.mod")


def test_get_all_type_hints_crossrefs_names_from_stub_only_modules(tmp_path: Path) -> None:
    """numpy's _polybase.pyi imports from _polytypes.pyi, which ships no runtime module (issue #741)."""
    pkg = tmp_path / "stubonlypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "_types.pyi").write_text("from typing import Any\n_SeriesLike = Any\n")
    (pkg / "poly.py").write_text("class Poly:\n    def __init__(self, coef): ...\n")
    (pkg / "poly.pyi").write_text(
        "from ._types import _SeriesLike\nclass Poly:\n    def __init__(self, coef: _SeriesLike) -> None: ...\n"
    )
    sys.path.insert(0, str(tmp_path))
    try:
        mod = importlib.import_module("stubonlypkg.poly")
        hint = get_all_type_hints([], mod.Poly, "stubonlypkg.poly.Poly", {})["coef"]
    finally:
        sys.path.remove(str(tmp_path))
        for name in [n for n in sys.modules if n.startswith("stubonlypkg")]:
            del sys.modules[name]
    assert isinstance(hint, MyTypeAliasForwardRef)
    assert hint.name == "_SeriesLike"


def _one_unsubscriptable(first: NotGenericAtRuntime[int], second: int) -> str: ...


def _one_unresolvable(
    first: Missing,  # ruff:ignore[undefined-name]  # ty: ignore[unresolved-reference]  # the case under test
    second: int,
) -> str: ...


@pytest.mark.parametrize(
    ("func", "unresolved"),
    [
        pytest.param(_one_unsubscriptable, r"NotGenericAtRuntime\[int\]", id="type-error"),
        pytest.param(_one_unresolvable, "Missing", id="name-error"),
    ],
)
def test_process_docstring_keeps_other_hints_when_one_fails(func: types.FunctionType, unresolved: str) -> None:
    lines = [":param first: the first", ":param second: the second"]
    process_docstring(make_docstring_app(), "function", f"{__name__}.{func.__name__}", func, None, lines)
    assert lines == [
        f":type first: :sphinx_autodoc_typehints_type:`{unresolved}`",
        ":param first: the first",
        r":type second: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        ":param second: the second",
        "",
        r":rtype: :sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``",
    ]


class NotGenericAtRuntime: ...


def test_resolve_string_annotations_evaluates_quoted_annotation() -> None:
    def func() -> None: ...

    assert resolve_string_annotations(func, {"x": "'Path'"}, {}) == {"x": Path}


@pytest.mark.skipif(sys.version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_process_docstring_links_an_attrs_field_beside_one_that_fails(  # pragma: >=3.14 cover
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent / "roots" / "test-attrs"))
    mixed = importlib.import_module("attrs_lazy_mod").Mixed
    lines = [":param b: the b"]
    process_docstring(make_docstring_app(typehints_document_rtype=False), "class", "mod.Mixed", mixed, None, lines)
    assert lines == [r":type b: :sphinx_autodoc_typehints_type:`\:py\:class\:\`\~decimal.Decimal\``", ":param b: the b"]
