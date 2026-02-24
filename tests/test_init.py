from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import MagicMock, create_autospec, patch

from sphinx.application import Sphinx
from sphinx.config import Config

import sphinx_autodoc_typehints as sat
from sphinx_autodoc_typehints import _inject_overload_signatures, process_docstring, process_signature
from sphinx_autodoc_typehints.patches import _OVERLOADS_CACHE


class _ClassWithPrivate:
    def __secret(self, x: int) -> str: ...


def _make_sig_app(**overrides: Any) -> Sphinx:
    defaults = {
        "typehints_fully_qualified": False,
        "simplify_optional_unions": False,
        "typehints_formatter": None,
        "typehints_use_signature": False,
        "typehints_use_signature_return": False,
        "autodoc_type_aliases": {},
    }
    defaults.update(overrides)
    config = create_autospec(Config, **defaults)  # ty: ignore[invalid-argument-type]
    return create_autospec(Sphinx, config=config)


def _make_docstring_app(**overrides: Any) -> Sphinx:
    config = MagicMock()
    config.__getitem__ = getattr
    config.autodoc_type_aliases = {}
    config.autodoc_mock_imports = []
    config.typehints_fully_qualified = False
    config.simplify_optional_unions = False
    config.typehints_formatter = None
    config.typehints_document_rtype = True
    config.typehints_document_rtype_none = True
    config.typehints_use_rtype = True
    config.typehints_defaults = None
    config.always_document_param_types = False
    config.python_display_short_literal_types = False
    for key, value in overrides.items():
        setattr(config, key, value)
    app = MagicMock(spec=Sphinx)
    app.config = config
    app.env = None
    return app


def test_process_signature_class_attr_lookup_fails() -> None:
    """Line 111: class name not found on module returns None."""

    def fake_method(self: Any, x: int) -> str: ...

    fake_method.__annotations__ = {"x": int, "return": str}
    fake_method.__qualname__ = "NonExistentClass.method"
    fake_method.__module__ = __name__

    app = _make_sig_app()
    result = process_signature(app, "method", "test.NonExistentClass.method", fake_method, MagicMock(), "", "")
    assert result is None


def test_process_signature_private_name_mangling() -> None:
    """Line 114: dunder-prefixed method names get mangled."""
    method = _ClassWithPrivate.__dict__["_ClassWithPrivate__secret"]

    app = _make_sig_app()
    result = process_signature(app, "method", "test_init._ClassWithPrivate.__secret", method, MagicMock(), "", "")
    assert result is not None
    sig_str, _ = result
    assert "self" not in sig_str


def test_process_docstring_sphinx_signature_raises_value_error() -> None:
    """Lines 157-158: sphinx_signature raising ValueError sets signature to None."""

    def func(x: int) -> str: ...

    app = _make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param x: the x"]
    with patch("sphinx_autodoc_typehints.sphinx_signature", side_effect=ValueError("bad")):
        process_docstring(app, "function", "func", func, None, lines)
    assert ":param x: the x" in lines


def test_process_docstring_sphinx_signature_raises_type_error() -> None:
    """Lines 157-158: sphinx_signature raising TypeError sets signature to None."""

    def func(x: int) -> str: ...

    app = _make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param x: the x"]
    with patch("sphinx_autodoc_typehints.sphinx_signature", side_effect=TypeError("bad")):
        process_docstring(app, "function", "func", func, None, lines)
    assert ":param x: the x" in lines


def test_inject_overload_no_qualname() -> None:
    """Line 198: obj without __qualname__ returns False."""
    obj = MagicMock(spec=[])
    obj.__module__ = "some_module"
    obj.__qualname__ = ""
    _OVERLOADS_CACHE["some_module"] = {}
    try:
        app = _make_docstring_app()
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
    try:
        app = _make_docstring_app()
        lines: list[str] = []
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
        app = _make_docstring_app()
        assert _inject_overload_signatures(app, "function", "name", obj, []) is False
    finally:
        _OVERLOADS_CACHE.pop("test_mod2", None)


def test_inject_types_no_signature() -> None:
    """Branch 261->263: signature is None skips _inject_signature."""

    def sample() -> str: ...

    app = _make_docstring_app(typehints_document_rtype=False)

    lines: list[str] = []
    sat._inject_types_to_docstring({"return": str}, None, sample, app, "function", "sample", lines)  # noqa: SLF001
    assert not any(line.startswith(":type") for line in lines)
