from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, NamedTuple
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from conftest import make_docstring_app, make_sig_app
from docutils.frontend import get_default_settings
from docutils.parsers.rst import Parser
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.ext.autodoc import Options
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

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.testing.util import SphinxTestApp


class _ClassWithPrivate:
    def __secret(self, x: int) -> str: ...

    @staticmethod
    def __static_secret(value: int) -> str: ...


def _helper(value: int) -> str: ...


class _BindsHelper:
    as_static = staticmethod(_helper)
    as_method = _helper


@pytest.mark.parametrize(
    ("name", "method", "expected"),
    [
        pytest.param(
            "_ClassWithPrivate._ClassWithPrivate__static_secret",
            vars(_ClassWithPrivate)["_ClassWithPrivate__static_secret"].__func__,
            "(value)",
            id="private-staticmethod-of-private-class",
        ),
        pytest.param(
            "_BindsHelper.as_static", _BindsHelper.as_static, "(value)", id="staticmethod-of-outside-function"
        ),
        pytest.param("_BindsHelper.as_method", _BindsHelper.as_method, "()", id="method-of-outside-function"),
    ],
)
def test_process_signature_first_parameter_by_member_kind(name: str, method: Callable[..., str], expected: str) -> None:
    result = process_signature(make_sig_app(), "method", f"{__name__}.{name}", method, Options(), "", "")
    assert result == (expected, None)


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(f"{__name__}.NonExistentClass.method", id="class-missing"),
        pytest.param("not_imported.NonExistentClass.method", id="module-missing"),
    ],
)
def test_process_signature_class_attr_lookup_fails(name: str) -> None:
    def fake_method(self: object, x: int) -> str: ...

    fake_method.__qualname__ = "NonExistentClass.method"
    assert process_signature(make_sig_app(), "method", name, fake_method, Options(), "", "") is None


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


def test_process_signature_class_omits_constructor_return() -> None:
    class ConstructedFromInit:
        def __init__(self, count: int) -> None: ...

    app = make_sig_app(typehints_use_signature=True, typehints_use_signature_return=True)
    result = process_signature(app, "class", "mod.ConstructedFromInit", ConstructedFromInit, Options(), "", "")
    assert result == ("(count: int)", None)


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
    import array  # ruff:ignore[import-outside-top-level]

    app = make_docstring_app()
    lines = ["the typecode character used to create the array"]
    process_docstring(app, "attribute", "array.array.typecode", array.array.typecode, None, lines)
    assert lines == ["the typecode character used to create the array"]


def test_process_docstring_descriptor_with_existing_type_field() -> None:
    """An explicit :type: field wins over the stub annotation."""
    import array  # ruff:ignore[import-outside-top-level]

    app = make_docstring_app()
    lines = [":type: str"]
    process_docstring(app, "attribute", "array.array.typecode", array.array.typecode, None, lines)
    assert lines == [":type: str"]


def test_process_docstring_types_instance_var_from_guarded_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "guarded_ivar.py").write_text(
        "from __future__ import annotations\n\n"
        "from typing import TYPE_CHECKING\n\n"
        "if TYPE_CHECKING:\n    from decimal import Decimal\n\n\n"
        "class Account:\n    def __init__(self) -> None:\n        self.balance: Decimal = Decimal()\n"
    )
    monkeypatch.syspath_prepend(tmp_path)
    account = importlib.import_module("guarded_ivar").Account
    lines = [":ivar balance: the balance"]
    process_docstring(make_docstring_app(), "class", "guarded_ivar.Account", account, None, lines)
    assert lines == [
        r":vartype balance: :sphinx_autodoc_typehints_type:`\:py\:class\:\`\~decimal.Decimal\``",
        ":ivar balance: the balance",
    ]


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


@pytest.mark.parametrize(
    ("directive", "expected"),
    [
        pytest.param(
            "automethod:: dummy_module.ClassWithOverloadedMethods.build",
            """\
classmethod ClassWithOverloadedMethods.build(value)

   Build one.

   Overloads:
      * **value** ("int") → "ClassWithOverloadedMethods"

      * **value** ("str") → "ClassWithOverloadedMethods"
""",
            id="classmethod",
        ),
        pytest.param(
            "automethod:: dummy_module.ClassWithOverloadedMethods.convert",
            """\
ClassWithOverloadedMethods.convert(value)

   Convert value.

   Overloads:
      * **value** ("int") → "int"

      * **value** ("str") → "str"
""",
            id="method",
        ),
        pytest.param(
            "automethod:: dummy_module.ClassWithOverloadedMethods.parse",
            """\
static ClassWithOverloadedMethods.parse(value)

   Parse value.

   Overloads:
      * **value** ("int") → "int"

      * **value** ("str") → "str"
""",
            id="staticmethod",
        ),
        pytest.param(
            "autoclass:: dummy_module.ClassWithOverloadedInit",
            """\
class dummy_module.ClassWithOverloadedInit(value)

   Class docstring.

   Overloads:
      * **value** ("int")

      * **value** ("str")
""",
            id="constructor",
        ),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy")
def test_overloads_rendered_in_docstring(
    app: SphinxTestApp, write_rst: Callable[[str], None], directive: str, expected: str
) -> None:
    write_rst(f".. {directive}")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == expected


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


def test_process_docstring_strips_no_overloads_while_overloads_are_disabled() -> None:
    def takes_count(count: int) -> None: ...

    lines = [":no-overloads:", "", "Accepts an int.", "", ":param count: The count"]
    app = make_docstring_app(typehints_document_overloads=False, typehints_document_rtype=False)
    process_docstring(app, "function", "mod.takes_count", takes_count, None, lines)
    assert lines == [
        "",
        "Accepts an int.",
        "",
        r":type count: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        ":param count: The count",
    ]


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
        def __new__(cls, x: int, y: str) -> _NewOnlyClass:  # ruff:ignore[unused-static-method-argument, non-self-return-type]
            return super().__new__(cls)

    app = make_docstring_app(typehints_document_rtype=False)
    lines: list[str] = [":param x: the x", ":param y: the y"]
    process_docstring(app, "class", "test._NewOnlyClass", _NewOnlyClass, None, lines)
    joined = "\n".join(lines)
    assert ":type x:" in joined
    assert ":type y:" in joined


def test_process_signature_strips_types_from_namedtuple() -> None:
    class _Point(NamedTuple):
        x: int
        y: str

    result = process_signature(make_sig_app(), "class", "test._Point", _Point, MagicMock(), "", "")
    assert result == ("(x, y)", None)


def test_process_signature_uses_new_when_init_inherited() -> None:
    class _NewOnlyClass:
        def __new__(cls, x: int, y: str) -> _NewOnlyClass: ...  # ruff:ignore[non-self-return-type]

    app = make_sig_app(typehints_use_signature=True)
    result = process_signature(app, "class", "test._NewOnlyClass", _NewOnlyClass, MagicMock(), "", "")
    assert result == ("(x: int, y: str)", None)


class _BothClass:
    def __new__(cls, value: float) -> _BothClass: ...  # ruff:ignore[non-self-return-type]

    def __init__(self, *args: float) -> None: ...


class _InitOverridesNew(_BothClass):
    def __init__(self, count: int) -> None: ...


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        pytest.param(_BothClass, "(value: float)", id="new-beside-init"),
        pytest.param(_InitOverridesNew, "(count: int)", id="init-overrides-inherited-new"),
    ],
)
def test_process_signature_picks_constructor_like_inspect(cls: type, expected: str) -> None:
    app = make_sig_app(typehints_use_signature=True)
    assert process_signature(app, "class", f"test.{cls.__name__}", cls, Options(), "", "") == (expected, None)


class _Shadowed:
    value: int

    def __new__(cls, value: float) -> _Shadowed: ...  # ruff:ignore[non-self-return-type]


@pytest.mark.parametrize(
    "cls",
    [
        pytest.param(_BothClass, id="new-beside-init"),
        pytest.param(_Shadowed, id="new-over-shadowing-class-attribute"),
    ],
)
def test_process_docstring_types_params_from_new(cls: type) -> None:
    lines = [":param value: doc"]
    process_docstring(make_docstring_app(typehints_document_rtype=False), "class", "test.cls", cls, None, lines)
    assert lines == [r":type value: :sphinx_autodoc_typehints_type:`\:py\:class\:\`float\``", ":param value: doc"]


def test_inject_types_no_signature() -> None:
    """Branch 261->263: signature is None skips _inject_signature."""

    def sample() -> str: ...

    app = make_docstring_app(typehints_document_rtype=False)

    lines: list[str] = []
    sat._inject_types_to_docstring({"return": str}, None, sample, app, "function", "sample", lines)  # ruff:ignore[private-member-access]
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


def test_process_docstring_braces_after_default_stays_on_its_param() -> None:
    def typed_defaults(width: int = 5, height: int = 10) -> None: ...

    lines = [":param width: the width", ":type width: int", ":param height: the height", ":type height: int"]
    app = make_docstring_app(typehints_defaults="braces-after", typehints_document_rtype=False)
    process_docstring(app, "function", "mod.typed_defaults", typed_defaults, None, lines)
    assert lines == [
        ":param width: the width (default: ``5``)",
        r":type width: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        ":param height: the height (default: ``10``)",
        r":type height: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
    ]


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
        def __annotations__(self) -> dict[str, object]:  # ruff:ignore[bad-dunder-method-name]
            raise error

        def __call__(self) -> None: ...

    app = make_sig_app()
    result = process_signature(app, "function", "test.func", _Func(), MagicMock(), "", "")
    assert result is None


@pytest.mark.sphinx(
    "text", testroot="dummy", confoverrides={"extensions": ["sphinx_autodoc_typehints", "sphinx.ext.autodoc"]}
)
def test_setup_loads_autodoc_listed_after_it(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autofunction:: dummy_module.undocumented_function")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == dedent("""\
        dummy_module.undocumented_function(x)

           Hi

           Return type:
              "str"
        """)


def test_setup_returns_version() -> None:
    """setup() returns metadata dict with version from __version__."""
    app = create_autospec(Sphinx)
    app.config = create_autospec(Config)
    result = setup(app)
    assert result["version"] == __version__
    assert result["parallel_read_safe"] is True
    assert result["parallel_write_safe"] is True


@pytest.mark.sphinx("text", testroot="dummy")
def test_always_document_param_types_change_rereads_sources(
    app: SphinxTestApp, make_app: Callable[..., SphinxTestApp], write_rst: Callable[[str], None]
) -> None:
    write_rst(".. autofunction:: dummy_module.undocumented_function")
    app.build()

    make_app("text", srcdir=app.srcdir, confoverrides={"always_document_param_types": True}).build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == dedent("""\
        dummy_module.undocumented_function(x)

           Hi

           Parameters:
              **x** ("int")

           Return type:
              "str"
        """)


def test_process_docstring_reentrant_call_keeps_outer_state() -> None:
    """A nested call must hand the outer one its own state back (#750)."""

    def inner(flag: str) -> str: ...

    def outer(flag: bool) -> bool: ...

    app = make_docstring_app()
    prefix_after_nesting = []

    def formatter(annotation: Any, config: Config) -> None:
        if annotation is bool:
            process_docstring(app, "function", "inner_mod.inner", inner, None, ["Inner.", "", ":return: it"])
            prefix_after_nesting.append(config._typehints_module_prefix)  # ruff:ignore[private-member-access]

    app.config.typehints_formatter = formatter
    lines = ["Outer.", "", ":param flag: the flag", ":return: it"]
    process_docstring(app, "function", "outer_mod.outer", outer, None, lines)
    bool_type = ":sphinx_autodoc_typehints_type:`\\:py\\:class\\:\\`bool\\``"
    assert lines == [
        "Outer.",
        "",
        f":type flag: {bool_type}",
        ":param flag: the flag",
        "",
        f":rtype: {bool_type}",
        ":return: it",
    ]
    assert prefix_after_nesting == ["outer_mod", "outer_mod"]
