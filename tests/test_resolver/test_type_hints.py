from __future__ import annotations

import csv
import importlib
import re
import subprocess  # ruff:ignore[suspicious-subprocess-import]
import sys
import sysconfig
import types
from collections.abc import Callable, Iterator, Sequence
from csv import Error
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeAliasType, Union, get_args, get_origin
from unittest.mock import MagicMock, patch

if sys.version_info >= (3, 14):  # pragma: >=3.14 cover
    import annotationlib

import pytest
from conftest import make_docstring_app

from sphinx_autodoc_typehints import process_docstring
from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef
from sphinx_autodoc_typehints._resolver._type_hints import (
    _TYPE_GUARD_IMPORTS_RESOLVED,
    _build_localns,
    _execute_guarded_code,
    _future_annotations_imported,
    _get_type_hint,
    _resolve_string_annotations,
    _resolve_type_guarded_imports,
    _run_guarded_import,
    _should_skip_guarded_import_resolution,
    get_all_type_hints,
    get_descriptor_type_hint,
)

STUB_ROOT = Path(__file__).parent.parent / "roots" / "test-pyi-stubs"


def test_no_source_code_type_guard() -> None:
    _resolve_type_guarded_imports([], Error)


def test_future_annotations_not_imported() -> None:
    assert not _future_annotations_imported(csv)


def test_future_annotations_imported() -> None:
    assert _future_annotations_imported(test_future_annotations_imported)


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
    _run_guarded_import([], obj, "raise ImportError()")


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


@pytest.fixture
def guarded_module(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[Callable[[str], types.ModuleType]]:
    name = re.sub(r"\W", "_", request.node.name)
    sys.path.insert(0, str(tmp_path))

    def build(source: str) -> types.ModuleType:
        (tmp_path / f"{name}.py").write_text(source)
        return importlib.import_module(name)

    yield build
    sys.path.remove(str(tmp_path))
    sys.modules.pop(name, None)


def test_guarded_import_binds_names_below_an_unimportable_one(
    guarded_module: Callable[[str], types.ModuleType],
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


def test_guarded_import_warns_when_the_block_does_not_parse(
    guarded_module: Callable[[str], types.ModuleType],
) -> None:
    """A block truncated mid-literal by the guard regex is reported rather than raised (issue #741)."""
    module = guarded_module(
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        '    DOC = """\n'
        "text\n"
        '"""\n'
        "\n"
        "def func(value: int) -> None: ...\n"
    )
    mock_logger = MagicMock()
    with patch("sphinx_autodoc_typehints._resolver._type_hints._LOGGER", mock_logger):
        get_all_type_hints([], module.func, f"{module.__name__}.func", {})
    assert "unterminated triple-quoted string literal" in str(mock_logger.warning.call_args)


def test_guarded_import_warns_when_a_compound_statement_hides_it(
    guarded_module: Callable[[str], types.ModuleType],
) -> None:
    """A version gated or try/except import still reports the absent dependency (issue #751)."""
    module = guarded_module(
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    try:\n"
        "        from no_such_dependency import Absent\n"
        "    except ImportError:\n"
        "        from no_such_fallback import Absent\n"
        "\n"
        "def func(value: Absent) -> None: ...\n"
    )
    mock_logger = MagicMock()
    with patch("sphinx_autodoc_typehints._resolver._type_hints._LOGGER", mock_logger):
        get_all_type_hints([], module.func, f"{module.__name__}.func", {})
    assert "Failed guarded type import" in str(mock_logger.warning.call_args_list)


def test_guarded_comprehension_target_leaves_the_builtin_alone(
    guarded_module: Callable[[str], types.ModuleType],
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
    guarded_module: Callable[[str], types.ModuleType],
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
    result = _resolve_string_annotations(obj, {"x": "NoSuchType", "y": "int"}, {})
    assert result["x"] == "NoSuchType"
    assert result["y"] is int


def test_resolve_string_annotations_passes_non_strings() -> None:
    obj = MagicMock()
    obj.__module__ = "builtins"
    result = _resolve_string_annotations(obj, {"x": int, "return": str}, {})  # type: ignore[dict-item]
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


@pytest.mark.skipif(sys.version_info < (3, 14), reason="annotationlib requires Python 3.14+")
def test_get_type_hint_uses_annotationlib_on_name_error() -> None:  # pragma: >=3.14 cover
    """_get_type_hint falls back to annotationlib.get_annotations on 3.14+ NameError."""
    sentinel = {"x": int}

    def dummy() -> None: ...

    with (
        patch(
            "sphinx_autodoc_typehints._resolver._type_hints.get_type_hints",
            side_effect=NameError("name 'Foo' is not defined"),
        ),
        patch.object(annotationlib, "get_annotations", return_value=sentinel) as mock_get_ann,
    ):
        result = _get_type_hint([], "dummy", dummy, {})

    mock_get_ann.assert_called_once_with(dummy, format=annotationlib.Format.FORWARDREF)
    assert result is sentinel


@pytest.mark.skipif(sys.version_info >= (3, 14), reason="Tests pre-3.14 fallback path")
def test_get_type_hint_falls_back_to_dunder_annotations_before_314() -> None:  # pragma: <3.14 cover
    """_get_type_hint falls back to __annotations__ on pre-3.14 NameError."""

    def dummy(x: int) -> str: ...

    with patch(
        "sphinx_autodoc_typehints._resolver._type_hints.get_type_hints",
        side_effect=NameError("name 'Foo' is not defined"),
    ):
        result = _get_type_hint([], "dummy", dummy, {})

    assert result == dummy.__annotations__
