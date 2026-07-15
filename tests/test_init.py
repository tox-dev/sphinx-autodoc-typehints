from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from conftest import make_docstring_app, make_sig_app
from docutils.frontend import get_default_settings
from docutils.parsers.rst import Parser
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.ext.autosummary import extract_summary

import sphinx_autodoc_typehints as sat
from sphinx_autodoc_typehints import (
    __version__,
    _inject_overload_signatures,
    process_docstring,
    process_signature,
    setup,
)
from sphinx_autodoc_typehints._resolver._util import get_obj_location
from sphinx_autodoc_typehints.patches import _OVERLOADS_CACHE


class _ClassWithPrivate:
    def __secret(self, x: int) -> str: ...


def test_process_signature_class_attr_lookup_fails() -> None:
    """Line 111: class name not found on module returns None."""

    def fake_method(self: object, x: int) -> str: ...

    fake_method.__annotations__ = {"x": int, "return": str}
    fake_method.__qualname__ = "NonExistentClass.method"
    fake_method.__module__ = __name__

    app = make_sig_app()
    result = process_signature(app, "method", "test.NonExistentClass.method", fake_method, MagicMock(), "", "")
    assert result is None


def test_process_signature_private_name_mangling() -> None:
    """Line 114: dunder-prefixed method names get mangled."""
    method = _ClassWithPrivate.__dict__["_ClassWithPrivate__secret"]

    app = make_sig_app()
    result = process_signature(app, "method", "test_init._ClassWithPrivate.__secret", method, MagicMock(), "", "")
    assert result is not None
    sig_str, _ = result
    assert "self" not in sig_str


def test_process_signature_class_instance() -> None:
    """Line 121: bound instance methods should not have their first argument removed."""
    instance = _ClassWithPrivate()
    method = _ClassWithPrivate.__dict__["_ClassWithPrivate__secret"].__get__(instance)
    app = make_sig_app()
    result = process_signature(app, "method", "test_init._ClassWithPrivate.__secret", method, MagicMock(), "", "")
    assert result is not None
    sig_str, _ = result
    assert sig_str == "(x)"


def test_process_docstring_sphinx_signature_raises_value_error() -> None:
    """Lines 157-158: sphinx_signature raising ValueError sets signature to None."""

    def func(x: int) -> str: ...

    app = make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param x: the x"]
    with patch("sphinx_autodoc_typehints.sphinx_signature", side_effect=ValueError("bad")):
        process_docstring(app, "function", "func", func, None, lines)
    assert ":param x: the x" in lines


def test_process_docstring_sphinx_signature_raises_type_error() -> None:
    """Lines 157-158: sphinx_signature raising TypeError sets signature to None."""

    def func(x: int) -> str: ...

    app = make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param x: the x"]
    with patch("sphinx_autodoc_typehints.sphinx_signature", side_effect=TypeError("bad")):
        process_docstring(app, "function", "func", func, None, lines)
    assert ":param x: the x" in lines


def test_process_docstring_descriptor_without_stub_is_untouched() -> None:
    """A C data descriptor with no stub keeps its docstring as-is."""
    import array  # noqa: PLC0415

    app = make_docstring_app()
    lines = ["the typecode character used to create the array"]
    process_docstring(app, "attribute", "array.array.typecode", array.array.typecode, None, lines)
    assert lines == ["the typecode character used to create the array"]


def test_process_docstring_descriptor_with_existing_type_field() -> None:
    """An explicit :type: field wins over the stub annotation."""
    import array  # noqa: PLC0415

    app = make_docstring_app()
    lines = [":type: str"]
    process_docstring(app, "attribute", "array.array.typecode", array.array.typecode, None, lines)
    assert lines == [":type: str"]


def test_inject_overload_no_qualname() -> None:
    """Line 198: obj without __qualname__ returns False."""
    obj = MagicMock(spec=[])
    obj.__module__ = "some_module"
    obj.__qualname__ = ""
    _OVERLOADS_CACHE["some_module"] = {}
    try:
        app = make_docstring_app()
        assert _inject_overload_signatures(app, "function", "name", obj, []) is False
    finally:
        _OVERLOADS_CACHE.pop("some_module", None)


def test_inject_overload_unannotated_param_and_no_return() -> None:
    """Lines 214, 217->224: overload with unannotated param and no return annotation."""
    obj = MagicMock()
    obj.__module__ = "test_mod"
    obj.__qualname__ = "func"

    sig = inspect.Signature(
        parameters=[inspect.Parameter("x", inspect.Parameter.POSITIONAL_OR_KEYWORD)],
    )
    _OVERLOADS_CACHE["test_mod"] = {"func": [sig]}
    app = make_docstring_app()
    lines: list[str] = []
    try:
        result = _inject_overload_signatures(app, "function", "name", obj, lines)
        assert result is True
        joined = "\n".join(lines)
        assert "**x**" in joined
        assert "\u2192" not in joined
    finally:
        _OVERLOADS_CACHE.pop("test_mod", None)


def test_inject_overload_empty_overloads_returns_false() -> None:
    """Line 233: no matching overloads returns False."""
    obj = MagicMock()
    obj.__module__ = "test_mod2"
    obj.__qualname__ = "func"

    _OVERLOADS_CACHE["test_mod2"] = {"other_func": []}
    try:
        app = make_docstring_app()
        assert _inject_overload_signatures(app, "function", "name", obj, []) is False
    finally:
        _OVERLOADS_CACHE.pop("test_mod2", None)


def test_inject_overload_keeps_summary_first() -> None:
    """Overloads must follow the summary so autosummary can still extract it (#730)."""
    obj = MagicMock()
    obj.__module__ = "test_mod"
    obj.__qualname__ = "func"
    sig = inspect.Signature(
        parameters=[inspect.Parameter("x", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int)],
        return_annotation=str,
    )
    _OVERLOADS_CACHE["test_mod"] = {"func": [sig]}
    try:
        app = make_docstring_app()
        lines = ["Run the thing.", "", ":param x: the x"]
        assert _inject_overload_signatures(app, "function", "name", obj, lines) is True
        assert extract_summary(lines, get_default_settings(Parser())) == "Run the thing."
    finally:
        _OVERLOADS_CACHE.pop("test_mod", None)


def test_local_function_warning_includes_location() -> None:
    def fake_method(self: object, x: int) -> str: ...

    fake_method.__annotations__ = {"x": int, "return": str}
    fake_method.__qualname__ = "outer.<locals>.inner"
    fake_method.__module__ = __name__

    app = make_sig_app()
    mock_logger = MagicMock()
    with patch("sphinx_autodoc_typehints._LOGGER", mock_logger):
        process_signature(app, "method", "test.outer.<locals>.inner", fake_method, MagicMock(), "", "")
    mock_logger.warning.assert_called_once()
    kwargs = mock_logger.warning.call_args.kwargs
    assert "location" in kwargs
    assert kwargs["location"] == get_obj_location(fake_method)


def test_inject_overload_global_disable() -> None:
    obj = MagicMock()
    obj.__module__ = "test_mod"
    obj.__qualname__ = "func"

    sig = inspect.Signature(
        parameters=[inspect.Parameter("x", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int)],
        return_annotation=str,
    )
    _OVERLOADS_CACHE["test_mod"] = {"func": [sig]}
    try:
        app = make_docstring_app(typehints_document_overloads=False)
        lines: list[str] = []
        assert _inject_overload_signatures(app, "function", "name", obj, lines) is False
        assert lines == []
    finally:
        _OVERLOADS_CACHE.pop("test_mod", None)


def test_inject_overload_local_no_overloads_directive() -> None:
    obj = MagicMock()
    obj.__module__ = "test_mod"
    obj.__qualname__ = "func"

    sig = inspect.Signature(
        parameters=[inspect.Parameter("x", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int)],
        return_annotation=str,
    )
    _OVERLOADS_CACHE["test_mod"] = {"func": [sig]}
    try:
        app = make_docstring_app()
        lines = [":no-overloads:", "", "Some docstring."]
        assert _inject_overload_signatures(app, "function", "name", obj, lines) is False
        assert ":no-overloads:" not in lines
        assert lines == ["", "Some docstring."]
    finally:
        _OVERLOADS_CACHE.pop("test_mod", None)


def test_inject_overload_local_directive_with_global_enabled() -> None:
    obj = MagicMock()
    obj.__module__ = "test_mod"
    obj.__qualname__ = "func"

    sig = inspect.Signature(
        parameters=[inspect.Parameter("x", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int)],
        return_annotation=str,
    )
    _OVERLOADS_CACHE["test_mod"] = {"func": [sig]}
    try:
        app = make_docstring_app(typehints_document_overloads=True)
        lines = [":no-overloads:", "", "Docs here."]
        assert _inject_overload_signatures(app, "function", "name", obj, lines) is False
        assert ":no-overloads:" not in lines
    finally:
        _OVERLOADS_CACHE.pop("test_mod", None)


def test_process_docstring_uses_new_when_init_inherited() -> None:
    class _NewOnlyClass:
        def __new__(cls, x: int, y: str) -> _NewOnlyClass:  # noqa: ARG004, PYI034
            return super().__new__(cls)

    app = make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param x: the x", ":param y: the y"]
    process_docstring(app, "class", "test._NewOnlyClass", _NewOnlyClass, None, lines)
    joined = "\n".join(lines)
    assert ":type x:" in joined
    assert ":type y:" in joined


def test_process_docstring_prefers_init_over_new() -> None:
    class _BothClass:
        def __new__(cls, a: float) -> _BothClass:  # noqa: ARG004, PYI034
            return super().__new__(cls)

        def __init__(self, x: int) -> None:
            self.x = x

    app = make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param x: the x"]
    process_docstring(app, "class", "test._BothClass", _BothClass, None, lines)
    joined = "\n".join(lines)
    assert ":type x:" in joined


def test_inject_types_no_signature() -> None:
    """Branch 261->263: signature is None skips _inject_signature."""

    def sample() -> str: ...

    app = make_docstring_app(typehints_document_rtype=False)

    lines: list[str] = []
    sat._inject_types_to_docstring({"return": str}, None, sample, app, "function", "sample", lines)  # noqa: SLF001
    assert not any(s.startswith(":type") for s in lines)


def test_process_docstring_replaces_preexisting_single_line_type() -> None:
    def func(x: int) -> None: ...

    app = make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param x: the x parameter", ":type x: str"]
    process_docstring(app, "function", "test.func", func, None, lines)
    type_lines = [line for line in lines if line.startswith(":type x:")]
    assert len(type_lines) == 1
    assert "int" in type_lines[0]
    assert "str" not in "\n".join(lines)


def test_process_docstring_replaces_preexisting_multiline_type() -> None:
    def func(callback: int) -> None: ...

    app = make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [
        ":param callback: the callback parameter",
        ":type callback: ~collections.abc.Callable[[int,",
        "    str], bool]",
    ]
    process_docstring(app, "function", "test.func", func, None, lines)
    type_lines = [line for line in lines if line.startswith(":type callback:")]
    assert len(type_lines) == 1
    assert "int" in type_lines[0]
    assert "Callable" not in "\n".join(lines)


def test_process_docstring_preserves_blank_line_after_preexisting_type() -> None:
    def func(x: int) -> None: ...

    app = make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param x: the x parameter", ":type x: str", "", ".. rubric:: Notes"]
    process_docstring(app, "function", "test.func", func, None, lines)
    blank_idx = next(i for i, line in enumerate(lines) if not line)
    assert lines[blank_idx + 1] == ".. rubric:: Notes"


def test_process_docstring_strips_inline_param_type() -> None:
    def func(x: int) -> None: ...

    app = make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param str x: the x parameter"]
    process_docstring(app, "function", "test.func", func, None, lines)
    assert ":param x: the x parameter" in lines
    type_lines = [line for line in lines if line.startswith(":type x:")]
    assert len(type_lines) == 1
    assert "int" in type_lines[0]


def test_process_docstring_strips_complex_inline_param_type() -> None:
    def func(fp: int) -> None: ...

    app = make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param ~typing.IO[bytes] fp: the file"]
    process_docstring(app, "function", "test.func", func, None, lines)
    assert ":param fp: the file" in lines
    type_lines = [line for line in lines if line.startswith(":type fp:")]
    assert len(type_lines) == 1
    assert "int" in type_lines[0]


def _trailing_underscore_func(lambda_: float) -> None: ...


def _trailing_underscore_starred_func(*args_: float) -> None: ...


def _trailing_underscore_undocumented_func(x_: float) -> None: ...


@pytest.mark.parametrize(
    ("func", "lines", "expected_param_line", "expected_type_name"),
    [
        pytest.param(
            _trailing_underscore_func,
            [":param lambda_: description"],
            ":param lambda\\_: description",
            "lambda\\_",
            id="unescaped-line-rewritten",
        ),
        pytest.param(
            _trailing_underscore_starred_func,
            [":param \\*args_: description"],
            ":param \\*args_: description",
            "args_",
            id="starred-line-kept",
        ),
        pytest.param(
            _trailing_underscore_undocumented_func,
            [],
            ":param x\\_:",
            "x\\_",
            id="undocumented-escaped",
        ),
    ],
)
def test_process_docstring_trailing_underscore_param(
    func: Any, lines: list[str], expected_param_line: str, expected_type_name: str
) -> None:
    """napoleon emits ``:param lambda_:`` unescaped by default; the param line must be rewritten to
    the escaped form and the type attached, except for forms that cannot be rewritten (issue #708)."""
    app = make_docstring_app(typehints_document_rtype=False, always_document_param_types=True)
    process_docstring(app, "function", "test.func", func, None, lines)
    assert expected_param_line in lines
    assert any(line.startswith(":type ") and expected_type_name in line and "float" in line for line in lines)


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(NameError("Callable"), id="name-error"),
        pytest.param(TypeError("type 'DiGraph' is not subscriptable"), id="type-error"),
    ],
)
def test_process_signature_annotations_error(error: Exception) -> None:
    """PEP 649 lazy annotation evaluation raising (NameError for TYPE_CHECKING-only names, TypeError
    for subscripting a non-generic class) must not propagate from process_signature (issue #712)."""

    class _Func:
        @property
        def __annotations__(self) -> dict[str, object]:  # noqa: PLW3201
            raise error

        def __call__(self) -> None: ...

    app = make_sig_app()
    result = process_signature(app, "function", "test.func", _Func(), MagicMock(), "", "")
    assert result is None


def test_setup_returns_version() -> None:
    """setup() returns metadata dict with version from __version__."""
    app = create_autospec(Sphinx)
    app.config = create_autospec(Config)
    result = setup(app)
    assert result["version"] == __version__
    assert result["parallel_read_safe"] is True
    assert result["parallel_write_safe"] is True
