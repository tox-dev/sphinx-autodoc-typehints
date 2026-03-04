from __future__ import annotations

import csv
import importlib
import subprocess  # noqa: S404
import sys
import sysconfig
import types
from collections.abc import Sequence
from csv import Error
from pathlib import Path
from typing import Any, get_args, get_origin
from unittest.mock import MagicMock, patch

import pytest

from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef
from sphinx_autodoc_typehints._resolver._type_hints import (
    _build_localns,
    _execute_guarded_code,
    _future_annotations_imported,
    _get_type_hint,
    _resolve_string_annotations,
    _resolve_type_guarded_imports,
    _run_guarded_import,
    _should_skip_guarded_import_resolution,
    get_all_type_hints,
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


def test_build_localns_adds_ancestor_classes() -> None:
    import tests.roots.test_nested_attrs_localns as mod  # noqa: PLC0415

    assert _build_localns(mod.Outer.Inner.__init__, {})["Outer"] is mod.Outer


def test_build_localns_no_qualname() -> None:
    def func() -> None: ...

    func.__qualname__ = "func"
    localns: dict[Any, Any] = {"existing": 1}
    assert _build_localns(func, localns) == {"existing": 1}


def test_build_localns_preserves_existing_localns() -> None:
    import tests.roots.test_nested_attrs_localns as mod  # noqa: PLC0415

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


def test_get_all_type_hints_resolves_c_extension_class_new(c_ext_mod: Any) -> None:
    result = get_all_type_hints([], c_ext_mod.Encoder.__new__, "c_ext_mod.Encoder.__new__", {})
    default_type = result["default"]
    assert get_origin(default_type) is types.UnionType
    args = get_args(default_type)
    assert len(args) == 2
    encoder_hook = args[0] if isinstance(args[0], MyTypeAliasForwardRef) else args[1]
    assert isinstance(encoder_hook, MyTypeAliasForwardRef)
    assert encoder_hook.name == "EncoderHook"
