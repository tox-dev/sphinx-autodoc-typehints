from __future__ import annotations

import csv
from csv import Error
from typing import Any
from unittest.mock import MagicMock, patch

from sphinx_autodoc_typehints._resolver._type_hints import (
    _execute_guarded_code,
    _future_annotations_imported,
    _get_type_hint,
    _resolve_type_guarded_imports,
    _run_guarded_import,
    _should_skip_guarded_import_resolution,
)


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
