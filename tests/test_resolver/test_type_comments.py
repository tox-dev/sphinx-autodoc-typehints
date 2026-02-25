from __future__ import annotations

from textwrap import dedent
from unittest.mock import MagicMock, patch

from sphinx_autodoc_typehints._resolver._type_comments import (
    _normalize_source_lines,
    _split_type_comment_args,
    backfill_type_hints,
)


def test__normalize_source_lines_async_def() -> None:
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

    assert _normalize_source_lines(dedent(source)) == dedent(expected)


def test__normalize_source_lines_def_starting_decorator_parameter() -> None:
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

    assert _normalize_source_lines(dedent(source)) == dedent(expected)


def test_syntax_error_backfill() -> None:
    def func(x):  # noqa: ANN202
        ...

    backfill_type_hints(func, "func")


def test__normalize_source_lines_no_def() -> None:
    source = "x = 1\ny = 2\n"
    assert _normalize_source_lines(source) == source


def test__split_type_comment_args_empty() -> None:
    assert _split_type_comment_args("") == []


def test__split_type_comment_args_single() -> None:
    assert _split_type_comment_args("int") == ["int"]


def test__split_type_comment_args_multiple() -> None:
    assert _split_type_comment_args("int, str, bool") == ["int", "str", "bool"]


def test__split_type_comment_args_nested_brackets() -> None:
    assert _split_type_comment_args("List[int], Dict[str, int]") == ["List[int]", "Dict[str, int]"]


def test__split_type_comment_args_strips_stars() -> None:
    assert _split_type_comment_args("*args, **kwargs") == ["args", "kwargs"]


def test_backfill_type_hints_no_type_comment_attr() -> None:
    with patch("sphinx_autodoc_typehints._resolver._type_comments.inspect.getsource", return_value="import os\n"):
        assert backfill_type_hints(lambda: None, "test") == {}


def test_backfill_type_hints_multi_child_ast() -> None:
    with patch(
        "sphinx_autodoc_typehints._resolver._type_comments.inspect.getsource",
        return_value="x = 1\ndef foo(): pass\n",
    ):
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
        "sphinx_autodoc_typehints._resolver._type_comments.inspect.getsource",
        return_value="def f(x):\n    # type: (int) -> \n    pass\n",
    ):

        def f(x): ...  # noqa: ANN202

        result = backfill_type_hints(f, "f")
    assert result == {"x": "int"}


def test_backfill_type_hints_unparseable_type_comment() -> None:
    with patch(
        "sphinx_autodoc_typehints._resolver._type_comments.inspect.getsource",
        return_value="def f(x):\n    # type: bad_comment\n    pass\n",
    ):

        def f(x): ...  # noqa: ANN202

        result = backfill_type_hints(f, "f")
    assert result == {}


def test_backfill_type_hints_inline_type_comments() -> None:
    result = backfill_type_hints(_inline_typed_func, "_inline_typed_func")
    assert result == {"x": "int", "y": "str", "return": "bool"}


def test_multi_child_ast_warning_includes_location() -> None:
    mock_logger = MagicMock()
    with (
        patch(
            "sphinx_autodoc_typehints._resolver._type_comments.inspect.getsource",
            return_value="x = 1\ndef foo(): pass\n",
        ),
        patch("sphinx_autodoc_typehints._resolver._type_comments._LOGGER", mock_logger),
    ):
        backfill_type_hints(lambda: None, "test")
    mock_logger.warning.assert_called_once()
    kwargs = mock_logger.warning.call_args.kwargs
    assert "location" in kwargs


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
