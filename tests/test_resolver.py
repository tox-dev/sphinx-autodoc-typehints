from __future__ import annotations

import csv
from csv import Error
from textwrap import dedent
from typing import Any
from unittest.mock import patch

from sphinx_autodoc_typehints import backfill_type_hints, normalize_source_lines
from sphinx_autodoc_typehints._resolver import (
    _execute_guarded_code,
    _future_annotations_imported,
    _get_type_hint,
    _resolve_type_guarded_imports,
    _run_guarded_import,
    _should_skip_guarded_import_resolution,
    split_type_comment_args,
)


def test_normalize_source_lines_async_def() -> None:
    source = """
    async def async_function():
        class InnerClass:
            def __init__(self): ...
    """

    expected = """
    async def async_function():
        class InnerClass:
            def __init__(self): ...
    """

    assert normalize_source_lines(dedent(source)) == dedent(expected)


def test_normalize_source_lines_def_starting_decorator_parameter() -> None:
    source = """
    @_with_parameters(
        _Parameter("self", _Parameter.POSITIONAL_OR_KEYWORD),
        *_proxy_instantiation_parameters,
        _project_id,
        _Parameter(
            "node_numbers",
            _Parameter.POSITIONAL_OR_KEYWORD,
            default=None,
            annotation=Optional[Iterable[int]],
        ),
    )
    def __init__(bound_args):  # noqa: N805
        ...
    """

    expected = """
    @_with_parameters(
        _Parameter("self", _Parameter.POSITIONAL_OR_KEYWORD),
        *_proxy_instantiation_parameters,
        _project_id,
        _Parameter(
            "node_numbers",
            _Parameter.POSITIONAL_OR_KEYWORD,
            default=None,
            annotation=Optional[Iterable[int]],
        ),
    )
    def __init__(bound_args):  # noqa: N805
        ...
    """

    assert normalize_source_lines(dedent(source)) == dedent(expected)


def test_syntax_error_backfill() -> None:
    def func(x):  # noqa: ANN202
        ...

    backfill_type_hints(func, "func")


def test_no_source_code_type_guard() -> None:
    _resolve_type_guarded_imports([], Error)


def test_normalize_source_lines_no_def() -> None:
    source = "x = 1\ny = 2\n"
    assert normalize_source_lines(source) == source


def test_split_type_comment_args_empty() -> None:
    assert split_type_comment_args("") == []


def test_split_type_comment_args_single() -> None:
    assert split_type_comment_args("int") == ["int"]


def test_split_type_comment_args_multiple() -> None:
    assert split_type_comment_args("int, str, bool") == ["int", "str", "bool"]


def test_split_type_comment_args_nested_brackets() -> None:
    assert split_type_comment_args("List[int], Dict[str, int]") == ["List[int]", "Dict[str, int]"]


def test_split_type_comment_args_strips_stars() -> None:
    assert split_type_comment_args("*args, **kwargs") == ["args", "kwargs"]


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

    with patch("sphinx_autodoc_typehints._resolver.get_type_hints", side_effect=RecursionError):
        assert _get_type_hint([], "test", func, {}) == {}


def test_execute_guarded_code_catches_exception() -> None:
    module = type("FakeModule", (), {"__globals__": {}, "__dict__": {}})()
    with patch("sphinx_autodoc_typehints._resolver._run_guarded_import", side_effect=RuntimeError("boom")):
        _execute_guarded_code([], module, "\nif TYPE_CHECKING:\n    import os\nx = 1\n")


def test_run_guarded_import_no_exc_name() -> None:
    ns: dict[str, Any] = {}
    obj: Any = type("FakeObj", (), {"__globals__": ns})()
    _run_guarded_import([], obj, "raise ImportError()")


def test_backfill_type_hints_no_type_comment_attr() -> None:
    with patch("sphinx_autodoc_typehints._resolver.inspect.getsource", return_value="import os\n"):
        assert backfill_type_hints(lambda: None, "test") == {}


def test_backfill_type_hints_multi_child_ast() -> None:
    with patch("sphinx_autodoc_typehints._resolver.inspect.getsource", return_value="x = 1\ndef foo(): pass\n"):
        assert backfill_type_hints(lambda: None, "test") == {}


def test_backfill_type_hints_with_type_comment() -> None:
    result = backfill_type_hints(_typed_func, "_typed_func")
    assert result == {"x": "int", "y": "str", "return": "bool"}


def test_backfill_type_hints_type_comment_self_insertion() -> None:
    result = backfill_type_hints(_BackfillClass.method, "_BackfillClass.method")
    assert result == {"x": "int", "return": "str"}


def test_backfill_type_hints_type_comment_mismatch() -> None:
    result = backfill_type_hints(_mismatched_type_comment, "_mismatched_type_comment")
    assert result == {"return": "bool"}


def test_backfill_type_hints_posonly_args() -> None:
    result = backfill_type_hints(_posonly_typed_func, "_posonly_typed_func")
    assert result == {"x": "int", "y": "str", "return": "bool"}


def test_backfill_type_hints_empty_return() -> None:
    with patch(
        "sphinx_autodoc_typehints._resolver.inspect.getsource",
        return_value="def f(x):\n    # type: (int) -> \n    pass\n",
    ):

        def f(x): ...  # noqa: ANN202

        result = backfill_type_hints(f, "f")
    assert result == {"x": "int"}


def test_backfill_type_hints_unparseable_type_comment() -> None:
    with patch(
        "sphinx_autodoc_typehints._resolver.inspect.getsource",
        return_value="def f(x):\n    # type: bad_comment\n    pass\n",
    ):

        def f(x): ...  # noqa: ANN202

        result = backfill_type_hints(f, "f")
    assert result == {}


def test_backfill_type_hints_inline_type_comments() -> None:
    result = backfill_type_hints(_inline_typed_func, "_inline_typed_func")
    assert result == {"x": "int", "y": "str", "return": "bool"}


# --- module-level fixtures for inspect.getsource ---


class _BackfillClass:
    def method(self, x):  # noqa: ANN202
        # type: (int) -> str
        ...


def _typed_func(x, y):  # noqa: ANN202
    # type: (int, str) -> bool
    ...


def _posonly_typed_func(x, y, /):  # noqa: ANN202
    # type: (int, str) -> bool
    ...


def _inline_typed_func(  # noqa: ANN202
    x,  # type: int
    y,  # type: str
):
    # type: (...) -> bool
    ...


def _mismatched_type_comment(x, y, z):  # noqa: ANN202
    # type: (int) -> bool
    ...
