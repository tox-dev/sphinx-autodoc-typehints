from __future__ import annotations

import enum
import functools
import importlib
import inspect
import sys
import types
from pathlib import Path
from textwrap import dedent
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Final,
    Literal,
    NamedTuple,
    NewType,
    NotRequired,
    Required,
    TypedDict,
    TypeVar,
    Unpack,
    override,
)
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from conftest import make_docstring_app, make_sig_app
from docutils.frontend import get_default_settings
from docutils.parsers.rst import Parser
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.ext.autodoc import Options
from sphinx.ext.autosummary import extract_summary
from typing_extensions import Doc, deprecated

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
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp


class _ClassWithPrivate:
    def __secret(self, x: int) -> str: ...

    @staticmethod
    def __static_secret(value: int) -> str: ...


def _helper(value: int) -> str: ...


def _joined(count: int, sep: str, *, end: str = "") -> str: ...


class _Joiner:
    def __call__(self, sep: str, *, end: str = "") -> str: ...


class _BindsHelper:
    as_static = staticmethod(_helper)
    as_method = _helper

    @classmethod
    def plain_class(cls, value: int) -> str: ...

    @classmethod
    @functools.cache
    def cached_class(cls, value: int) -> str: ...

    def join(self, count: int, sep: str, *, end: str = "") -> str: ...

    as_partial = functools.partialmethod(join, 1)


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
        pytest.param("_BindsHelper.plain_class", _BindsHelper.plain_class, "(value)", id="classmethod"),
        pytest.param("_BindsHelper.cached_class", _BindsHelper.cached_class, "(value)", id="classmethod-of-wrapper"),
    ],
)
def test_process_signature_first_parameter_by_member_kind(name: str, method: Callable[..., str], expected: str) -> None:
    result = process_signature(make_sig_app(), "method", f"{__name__}.{name}", method, Options(), "", "")
    assert result == (expected, None)


def test_process_signature_leaves_data_holding_a_callable_alone() -> None:
    # Sphinx shows no signature for data, and passes none to replace
    assert process_signature(make_sig_app(), "data", f"{__name__}.alias", _helper, Options(), None, "") is None


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


@pytest.mark.parametrize(
    "decorator",
    [pytest.param(functools.cache, id="cache"), pytest.param(functools.lru_cache, id="lru_cache")],
)
def test_process_signature_strips_types_from_a_cached_function(decorator: Callable[..., Any]) -> None:
    def compute(value: int) -> str: ...

    result = process_signature(make_sig_app(), "function", "mod.compute", decorator(compute), Options(), "", "")
    assert result == ("(value)", None)


@pytest.mark.parametrize(
    ("what", "name", "obj"),
    [
        pytest.param("function", "mod.joined", functools.partial(_joined, 1), id="partial"),
        pytest.param("method", f"{__name__}._BindsHelper.as_partial", _BindsHelper.as_partial, id="partialmethod"),
        pytest.param("function", "mod.joiner", _Joiner(), id="callable-instance"),
    ],
)
def test_process_signature_strips_types_from_a_callable_without_annotations(
    what: str, name: str, obj: Callable[..., str]
) -> None:
    assert process_signature(make_sig_app(), what, name, obj, Options(), "", "") == ("(sep, *, end='')", None)


@pytest.mark.parametrize(
    "obj",
    [pytest.param(functools.partial(_joined, 1), id="partial"), pytest.param(_Joiner(), id="callable-instance")],
)
def test_process_docstring_types_a_callable_without_annotations(obj: Callable[..., str]) -> None:
    lines = [":param sep: the separator"]
    process_docstring(make_docstring_app(), "function", "mod.joined", obj, None, lines)
    assert lines == [
        r":type sep: :sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``",
        ":param sep: the separator",
        "",
        r":rtype: :sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``",
    ]


_SENTINEL: Final = object()


def _explicitly_signed(a: int, b: object = _SENTINEL) -> None: ...


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        pytest.param("(x, y=3)", None, id="written-with-other-names"),
        pytest.param("(a, *, b)", None, id="written-with-other-kinds"),
        pytest.param("(a: int, b: object = _SENTINEL)", ("(a, b=<object object>)", None), id="introspected"),
        pytest.param("(a: int, b: object = <object object>)", ("(a, b=<object object>)", None), id="unreadable"),
        pytest.param("(**kwargs)", ("(a, b=<object object>)", None), id="catch-all-keywords"),
        pytest.param("(*args: Any, **kwargs: Any)", ("(a, b=<object object>)", None), id="catch-all"),
    ],
)
def test_process_signature_keeps_a_written_signature(given: str, expected: tuple[str, None] | None) -> None:
    app = make_sig_app()
    assert process_signature(app, "function", "mod.signed", _explicitly_signed, Options(), given, "") == expected


def test_process_signature_class_omits_constructor_return() -> None:
    class ConstructedFromInit:
        def __init__(self, count: int) -> None: ...

    app = make_sig_app(typehints_use_signature=True, typehints_use_signature_return=True)
    result = process_signature(app, "class", "mod.ConstructedFromInit", ConstructedFromInit, Options(), "", "")
    assert result == ("(count: int)", None)


_UserId = NewType("_UserId", int)
_Bounded = TypeVar("_Bounded", bound=int)


def _kept_path(value: Path) -> Path: ...
def _kept_flag(value: bool) -> None: ...  # the case under test
def _kept_new_type(value: _UserId) -> None: ...
def _kept_type_var(value: _Bounded) -> None: ...  # ruff:ignore[non-pep695-generic-function]  # no signature declares it
def _kept_declared[T: int](value: T) -> None: ...
def _kept_param_spec[**P](*args: P.args, **kwargs: P.kwargs) -> None: ...
def _kept_literal(value: Literal["a", 1]) -> None: ...
def _kept_callable(value: Callable[..., int]) -> None: ...


type _Pair = tuple[int, int]


def _kept_alias(value: _Pair) -> None: ...


def _bool_as_rst(annotation: object, _config: object) -> str | None:
    return ":class:`bool`" if annotation is bool else None


@pytest.mark.parametrize(
    ("func", "overrides", "expected"),
    [
        pytest.param(_kept_path, {}, "(value: ~pathlib.Path) -> ~pathlib.Path", id="class"),
        pytest.param(
            _kept_path, {"typehints_fully_qualified": True}, "(value: pathlib.Path) -> pathlib.Path", id="qualified"
        ),
        pytest.param(
            _kept_path,
            {"typehints_fixup_module_name": lambda module: "pl" if module == "pathlib" else module},
            "(value: ~pl.Path) -> ~pl.Path",
            id="fixed-up-module",
        ),
        pytest.param(_kept_flag, {"typehints_formatter": _bool_as_rst}, "(value: bool) -> None", id="formatter-markup"),
        pytest.param(_kept_new_type, {}, "(value: ~test_init._UserId) -> None", id="new-type"),
        pytest.param(_kept_type_var, {}, "(value: ~test_init._Bounded) -> None", id="type-var"),
        pytest.param(_kept_declared, {}, "(value: T) -> None", id="declared-type-param"),
        pytest.param(_kept_param_spec, {}, "(*args: P.args, **kwargs: P.kwargs) -> None", id="param-spec-components"),
        pytest.param(_kept_literal, {}, "(value: ~typing.Literal['a', 1]) -> None", id="literal"),
        pytest.param(_kept_callable, {}, "(value: ~collections.abc.Callable[..., int]) -> None", id="callable"),
        pytest.param(_kept_alias, {}, "(value: ~test_init._Pair) -> None", id="type-alias"),
    ],
)
def test_process_signature_keeps_types_as_the_fields_render_them(
    func: types.FunctionType, overrides: dict[str, object], expected: str
) -> None:
    app = make_sig_app(typehints_use_signature=True, typehints_use_signature_return=True, **overrides)
    assert process_signature(app, "function", f"mod.{func.__name__}", func, Options(), "", "") == (expected, None)


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


def test_process_docstring_types_a_descriptor_with_the_role_the_inventory_uses() -> None:
    import array  # ruff:ignore[import-outside-top-level]

    app = make_docstring_app()
    app.env = MagicMock(intersphinx_inventory={"py:data": {"types.ModuleType": ()}})
    lines: list[str] = []
    # the stub lookup reads files, so stand in for what a stub would say
    with patch("sphinx_autodoc_typehints.get_descriptor_type_hint", return_value=types.ModuleType):
        process_docstring(app, "attribute", "array.array.typecode", array.array.typecode, None, lines)
    assert lines == ["", r":type: :sphinx_autodoc_typehints_type:`\:py\:data\:\`\~types.ModuleType\``"]


def test_process_docstring_types_a_napoleon_attribute_from_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "ledger_mod.py").write_text(
        "class Ledger:\n    def __init__(self) -> None:\n        self.amount: int = 0\n        self.owner: str = ''\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    ledger = importlib.import_module("ledger_mod").Ledger
    lines = [
        ".. attribute:: amount",
        "",
        "   how much",
        "",
        ".. attribute:: owner",
        "",
        "   who",
        "",
        "   :type: str",
        "",
    ]
    process_docstring(make_docstring_app(), "class", "ledger_mod.Ledger", ledger, None, lines)
    assert lines == [
        ".. attribute:: amount",
        "",
        "   how much",
        "",
        r"   :type: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        "",
        ".. attribute:: owner",
        "",
        "   who",
        "",
        "   :type: str",
        "",
    ]


class _Job:
    retries: int
    total: ClassVar[int] = 0


@pytest.mark.parametrize("field", ["ivar", "cvar", "var"])
def test_process_docstring_types_a_variable_from_the_class_body(field: str) -> None:
    lines = [f":{field} retries: how often"]
    process_docstring(make_docstring_app(), "class", "mod._Job", _Job, None, lines)
    assert lines == [
        r":vartype retries: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``",
        f":{field} retries: how often",
    ]


_GUARDED_ACCOUNT: Final = (
    "from __future__ import annotations\n\n"
    "from typing import TYPE_CHECKING\n\n"
    "if TYPE_CHECKING:\n    from decimal import Decimal\n\n\n"
    "class Account:\n    def __init__(self) -> None:\n        self.balance: Decimal = Decimal()\n"
)


@pytest.mark.parametrize(
    ("modules", "documented"),
    [
        pytest.param({"guarded_ivar": _GUARDED_ACCOUNT}, "guarded_ivar", id="defined"),
        pytest.param(
            {
                "guarded_ivar_impl": _GUARDED_ACCOUNT,
                "guarded_ivar_facade": "from guarded_ivar_impl import Account\n\nAccount.__module__ = __name__\n",
            },
            "guarded_ivar_facade",
            id="reexported",
        ),
    ],
)
def test_process_docstring_types_instance_var_from_guarded_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, modules: dict[str, str], documented: str
) -> None:
    for module_name, source in modules.items():
        (tmp_path / f"{module_name}.py").write_text(source)
    monkeypatch.syspath_prepend(tmp_path)
    account = importlib.import_module(documented).Account
    lines = [":ivar balance: the balance"]
    process_docstring(make_docstring_app(), "class", f"{documented}.Account", account, None, lines)
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
        assert _inject_overload_signatures(app, "function", "name", obj, obj, []) is False
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
        result = _inject_overload_signatures(app, "function", "name", obj, obj, lines)
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
        assert _inject_overload_signatures(app, "function", "name", obj, obj, []) is False
    finally:
        _OVERLOADS_CACHE.pop("test_mod2", None)


_P = inspect.Parameter
_OVERLOAD_INT: Final = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``"
_OVERLOAD_STR: Final = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``"


def _overloaded() -> None: ...


@pytest.mark.parametrize(
    ("parameters", "entry"),
    [
        pytest.param(
            [
                _P("a", _P.POSITIONAL_ONLY, annotation=int),
                _P("args", _P.VAR_POSITIONAL, annotation=int),
                _P("key", _P.KEYWORD_ONLY, annotation=str, default="k"),
                _P("kw", _P.VAR_KEYWORD, annotation=int),
            ],
            rf"**a** ({_OVERLOAD_INT}), /, **\*args** ({_OVERLOAD_INT}), **key** ({_OVERLOAD_STR}) = ``'k'``, "
            rf"**\*\*kw** ({_OVERLOAD_INT})",
            id="every-kind",
        ),
        pytest.param(
            [_P("a", _P.POSITIONAL_ONLY, annotation=int), _P("key", _P.KEYWORD_ONLY, annotation=str)],
            rf"**a** ({_OVERLOAD_INT}), /, \*, **key** ({_OVERLOAD_STR})",
            id="keyword-only-after-positional-only",
        ),
        pytest.param([], "()", id="no-parameters"),
    ],
)
def test_process_docstring_writes_an_overload_like_its_signature(
    monkeypatch: pytest.MonkeyPatch, parameters: list[inspect.Parameter], entry: str
) -> None:
    signature = inspect.Signature(parameters, return_annotation=int)
    monkeypatch.setitem(_OVERLOADS_CACHE, __name__, {_overloaded.__qualname__: [signature]})
    lines = ["Summary."]
    process_docstring(make_docstring_app(), "function", f"{__name__}._overloaded", _overloaded, None, lines)
    assert lines[:4] == ["Summary.", "", ":Overloads:", f"   * {entry} \u2192 {_OVERLOAD_INT}"]


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
        assert _inject_overload_signatures(app, "function", "name", obj, obj, lines) is True
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


@pytest.mark.parametrize(
    ("directive", "expected"),
    [
        pytest.param(
            "autofunction:: dummy_module.overloaded",
            """\
dummy_module.overloaded(value: int) -> DataClass
dummy_module.overloaded(value: str, *, strict=False) -> MyNamedTuple

   Overloaded function.
""",
            id="function",
        ),
        pytest.param(
            "automethod:: dummy_module.ClassWithOverloadedMethods.build",
            """\
classmethod ClassWithOverloadedMethods.build(value: int) -> ClassWithOverloadedMethods
classmethod ClassWithOverloadedMethods.build(value: str) -> ClassWithOverloadedMethods

   Build one.
""",
            id="classmethod",
        ),
        pytest.param(
            "automethod:: dummy_module.ClassWithOverloadedMethods.convert",
            """\
ClassWithOverloadedMethods.convert(value: int) -> int
ClassWithOverloadedMethods.convert(value: str) -> str

   Convert value.
""",
            id="method",
        ),
        pytest.param(
            "automethod:: dummy_module.ClassWithOverloadedMethods.parse",
            """\
static ClassWithOverloadedMethods.parse(value: int) -> int
static ClassWithOverloadedMethods.parse(value: str) -> str

   Parse value.
""",
            id="staticmethod",
        ),
        pytest.param(
            "autoclass:: dummy_module.ClassWithOverloadedInit",
            """\
class dummy_module.ClassWithOverloadedInit(value: int)
class dummy_module.ClassWithOverloadedInit(value: str)

   Class docstring.
""",
            id="constructor",
        ),
        pytest.param(
            "autofunction:: dummy_module.overloaded_generic",
            """\
dummy_module.overloaded_generic[T: int](value: T) -> T
dummy_module.overloaded_generic[T: int](value: list[T]) -> T

   Generic function.
""",
            id="type-params",
        ),
        pytest.param(
            "autofunction:: dummy_module.overloaded_opt_out",
            """\
dummy_module.overloaded_opt_out(value: int | str)

   Opted out.

   Return type:
      "int" | "str"
""",
            id="no-overloads",
        ),
        pytest.param(
            "autofunction:: dummy_module.overloaded_options",
            """\
dummy_module.overloaded_options(value: int) -> int
dummy_module.overloaded_options(value: str, *, flag: bool = ...) -> str

   Overloaded function taking options.
""",
            id="default-the-implementation-lacks",
        ),
        pytest.param(
            "autofunction:: dummy_module.overloaded(value)",
            """\
dummy_module.overloaded(value)

   Overloaded function.

   Overloads:
      * **value** ("int") → "DataClass"

      * **value** ("str"), *, **strict** = "False" → "MyNamedTuple"
""",
            id="written-signature",
        ),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy", confoverrides={"typehints_use_signature": True})
def test_overloads_rendered_in_signature(
    app: SphinxTestApp, write_rst: Callable[[str], None], directive: str, expected: str
) -> None:
    write_rst(f".. {directive}")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == expected


@pytest.mark.sphinx("text", testroot="dummy", confoverrides={"typehints_use_signature": True})
def test_overloads_written_signature_keeps_to_its_own_entry(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(
        ".. autofunction:: dummy_module.overloaded(value)\n\n.. autofunction:: dummy_module.overloaded\n   :no-index:\n"
    )
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == dedent("""\
        dummy_module.overloaded(value)

           Overloaded function.

           Overloads:
              * **value** ("int") → "DataClass"

              * **value** ("str"), *, **strict** = "False" → "MyNamedTuple"

        dummy_module.overloaded(value: int) -> DataClass
        dummy_module.overloaded(value: str, *, strict=False) -> MyNamedTuple

           Overloaded function.
        """)


@pytest.mark.sphinx(
    "text", testroot="dummy", confoverrides={"typehints_use_signature": True, "autoclass_content": "both"}
)
def test_overloads_in_signature_opted_out_by_constructor_docstring(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. autoclass:: dummy_module.ClassWithOverloadedInitOptingOut")
    app.build()

    assert (
        (Path(app.srcdir) / "_build/text/index.txt").read_text()
        == """\
class dummy_module.ClassWithOverloadedInitOptingOut(value: int | str)

   Class docstring.

   Constructor docstring.
"""
    )


@pytest.mark.sphinx("text", testroot="dummy", confoverrides={"typehints_use_signature": True})
def test_overload_signature_cross_references_types(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autofunction:: dummy_module.overloaded")
    app.build()

    second = list(app.env.get_doctree("index").findall(addnodes.desc_signature))[1]
    assert [xref["reftarget"] for xref in second.findall(addnodes.pending_xref)] == ["str", "dummy_module.MyNamedTuple"]


@pytest.mark.sphinx("text", testroot="dummy", confoverrides={"typehints_use_signature": True})
def test_overload_signature_targets_only_the_first_line(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autofunction:: dummy_module.overloaded")
    app.build()

    signatures = app.env.get_doctree("index").findall(addnodes.desc_signature)
    assert [signature["ids"] for signature in signatures] == [["dummy_module.overloaded"], []]


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
        assert _inject_overload_signatures(app, "function", "name", obj, obj, lines) is False
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
        assert _inject_overload_signatures(app, "function", "name", obj, obj, lines) is False
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
        assert _inject_overload_signatures(app, "function", "name", obj, obj, lines) is False
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


@deprecated("use something else")
class _Deprecated:
    def __init__(self, value: float) -> None: ...


_STATED: Final = inspect.Signature([inspect.Parameter("value", inspect.Parameter.KEYWORD_ONLY, annotation=float)])


class _StatesSignature:
    __signature__ = _STATED

    def __init__(self, **data: object) -> None: ...


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        pytest.param(_BothClass, "(value: float)", id="new-beside-init"),
        pytest.param(_InitOverridesNew, "(count: int)", id="init-overrides-inherited-new"),
        pytest.param(_Deprecated, "(value: float)", id="new-wrapping-object-new"),  # ty: ignore[deprecated]  # the case under test
        pytest.param(_StatesSignature, "(*, value: float)", id="stated-signature"),
    ],
)
def test_process_signature_picks_constructor_like_inspect(cls: type, expected: str) -> None:
    app = make_sig_app(typehints_use_signature=True)
    assert process_signature(app, "class", f"test.{cls.__name__}", cls, Options(), "", "") == (expected, None)


class _Shadowed:
    value: int

    def __new__(cls, value: float) -> _Shadowed: ...  # ruff:ignore[non-self-return-type]


_FLOAT_VALUE: Final = [r":type value: :sphinx_autodoc_typehints_type:`\:py\:class\:\`float\``", ":param value: doc"]


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        pytest.param(_BothClass, _FLOAT_VALUE, id="new-beside-init"),
        pytest.param(_Shadowed, _FLOAT_VALUE, id="new-over-shadowing-class-attribute"),
        pytest.param(
            _Deprecated,  # ty: ignore[deprecated]  # the case under test
            ["", ".. sphinx_autodoc_typehints_deprecated::", "", "   use something else", "", *_FLOAT_VALUE],
            id="init-beside-new-wrapping-object-new",
        ),
        pytest.param(_StatesSignature, _FLOAT_VALUE, id="stated-signature"),
    ],
)
def test_process_docstring_types_params_from_the_constructor(cls: type, expected: list[str]) -> None:
    lines = [":param value: doc"]
    process_docstring(make_docstring_app(typehints_document_rtype=False), "class", "test.cls", cls, None, lines)
    assert lines == expected


def _stated(*args, **kwargs): ...  # ruff:ignore[missing-type-args, missing-type-kwargs, missing-return-type-private-function]  # stated below


_stated.__signature__ = _STATED.replace(return_annotation=str)  # ty: ignore[unresolved-attribute]  # the case under test


def test_process_signature_strips_a_stated_signature() -> None:
    assert process_signature(make_sig_app(), "function", "mod.stated", _stated, Options(), "", "") == (
        "(*, value)",
        None,
    )


def _handle(ctx: object, name: str, count: int = 1) -> bool: ...


@functools.wraps(_handle)
def _injected(*args: object, **kwargs: object) -> bool: ...


# a dependency-injecting decorator hides the parameter it supplies
_injected.__signature__ = inspect.Signature(list(inspect.signature(_handle).parameters.values())[1:])  # ty: ignore[unresolved-attribute]  # the case under test


def test_process_signature_strips_a_wrapper_stated_signature() -> None:
    given = "(name: str, count: int = 1)"
    assert process_signature(make_sig_app(), "function", "mod.injected", _injected, Options(), given, "") == (
        "(name, count=1)",
        None,
    )


def test_process_docstring_types_a_stated_signature() -> None:
    lines = [":param value: doc"]
    process_docstring(make_docstring_app(), "function", "mod.stated", _stated, None, lines)
    assert lines == [
        r":type value: :sphinx_autodoc_typehints_type:`\:py\:class\:\`float\``",
        ":param value: doc",
        "",
        r":rtype: :sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``",
    ]


def test_inject_types_no_signature() -> None:
    """A missing signature leaves the parameters alone."""

    def sample() -> str: ...

    app = make_docstring_app(typehints_document_rtype=False)

    lines: list[str] = []
    sat._inject_types_to_docstring({"return": str}, None, sample, app, "function", "sample", lines, written_as={})  # ruff:ignore[private-member-access]
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


@pytest.mark.parametrize(
    ("lines", "defaults", "expected"),
    [
        pytest.param(
            [":param y: the y", ":type y: int"],
            "comma",
            [":param y: the y", ":type y: int, default: ``1``"],
            id="comma",
        ),
        pytest.param(
            [":param y: the y", ":type y: int"],
            "braces",
            [":param y: the y", ":type y: int (default: ``1``)"],
            id="braces",
        ),
        pytest.param(
            [":param y: the y", ":type y: int"],
            "braces-after",
            [":param y: the y (default: ``1``)", ":type y: int"],
            id="braces-after",
        ),
        pytest.param(
            [":param y: the y", ":type y: dict[str,", "    int]"],
            "comma",
            [":param y: the y", ":type y: dict[str,", "    int], default: ``1``"],
            id="multi-line-type",
        ),
        pytest.param(
            [":param int y: the y"], "comma", [":type y: int, default: ``1``", ":param y: the y"], id="inline-comma"
        ),
        pytest.param(
            [":param int y: the y"], "braces", [":type y: int (default: ``1``)", ":param y: the y"], id="inline-braces"
        ),
        pytest.param(
            [":param int y: the y"],
            "braces-after",
            [":type y: int", ":param y: the y (default: ``1``)"],
            id="inline-braces-after",
        ),
    ],
)
def test_process_docstring_keeps_the_default_of_a_docstring_typed_param(
    lines: list[str], defaults: str, expected: list[str]
) -> None:
    def func(y=1) -> None: ...  # ruff:ignore[missing-type-function-argument]  # the docstring types it

    app = make_docstring_app(typehints_document_rtype=False, typehints_defaults=defaults)
    process_docstring(app, "function", "test.func", func, None, lines)
    assert lines == expected


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


_INT_TYPE: Final = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``"


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        pytest.param(
            [":param a: the a, for example::", "", "    a = 5"],
            [":param a: the a, for example (default: ``1``)::", "", "    a = 5"],
            id="literal-block",
        ),
        pytest.param(
            [":param a: one of:", "", "    - x", "    - y"],
            [":param a: one of: (default: ``1``)", "", "    - x", "    - y"],
            id="bullet-list",
        ),
        pytest.param(
            [":param a: one of:", "", "    1. x", "    2. y"],
            [":param a: one of: (default: ``1``)", "", "    1. x", "    2. y"],
            id="enumerated-list",
        ),
        pytest.param(
            [":param a: the a", "", "    .. note:: careful"],
            [":param a: the a (default: ``1``)", "", "    .. note:: careful"],
            id="directive",
        ),
        pytest.param(
            [":param a: the a", "    more", "", "        quoted"],
            [":param a: the a", "    more (default: ``1``)", "", "        quoted"],
            id="deeper-indented-block",
        ),
        pytest.param(
            [":param a: the a", "", "    second paragraph"],
            [":param a: the a", "", "    second paragraph (default: ``1``)"],
            id="last-plain-paragraph",
        ),
    ],
)
def test_process_docstring_braces_after_default_ends_the_last_paragraph(lines: list[str], expected: list[str]) -> None:
    def func(a: int = 1) -> None: ...

    app = make_docstring_app(typehints_defaults="braces-after", typehints_document_rtype=False)
    process_docstring(app, "function", "mod.func", func, None, lines)
    assert lines == [f":type a: {_INT_TYPE}", *expected]


_STR_TYPE: Final = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``"
_FLOAT_TYPE: Final = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`float\``"


@pytest.mark.parametrize(
    ("lines", "overrides", "expected"),
    [
        pytest.param(
            [":Parameters: * **a** -- the a", "             * **b** -- the b"],
            {},
            [f":Parameters: * **a** ({_INT_TYPE}) -- the a", f"             * **b** ({_STR_TYPE}) -- the b"],
            id="bulleted",
        ),
        pytest.param(
            [":Parameters: * **a** -- the a", "             * **b** -- the b"],
            {"always_document_param_types": True},
            [
                f":Parameters: * **a** ({_INT_TYPE}) -- the a",
                f"             * **b** ({_STR_TYPE}) -- the b",
                rf"             * **\*args** ({_FLOAT_TYPE})",
            ],
            id="always-documented",
        ),
        pytest.param(
            [":Parameters: **b** -- the b"],
            {"always_document_param_types": True},
            [
                f":Parameters: * **a** ({_INT_TYPE})",
                f"             * **b** ({_STR_TYPE}) -- the b",
                rf"             * **\*args** ({_FLOAT_TYPE})",
            ],
            id="always-documented-around-a-single-entry",
        ),
        pytest.param(
            [":Parameters: **a** -- the a", "             more of a", "", "             still a", "", "After."],
            {"always_document_param_types": True},
            [
                f":Parameters: * **a** ({_INT_TYPE}) -- the a",
                "               more of a",
                "",
                "               still a",
                f"             * **b** ({_STR_TYPE})",
                rf"             * **\*args** ({_FLOAT_TYPE})",
                "",
                "After.",
            ],
            id="always-documented-after-a-multi-paragraph-entry",
        ),
        pytest.param(
            [":Keyword Arguments: **b** -- the b"],
            {},
            [f":Keyword Arguments: **b** ({_STR_TYPE}) -- the b"],
            id="keyword",
        ),
        pytest.param(
            [r":Parameters: **\*args** -- extra"],
            {},
            [rf":Parameters: **\*args** ({_FLOAT_TYPE}) -- extra"],
            id="star-args",
        ),
        pytest.param(
            [":Parameters: **a** (*int*) -- the a"],
            {},
            [":Parameters: **a** (*int*) -- the a"],
            id="typed-in-the-docstring",
        ),
        pytest.param(
            [":Parameters: **b** -- the b"],
            {"typehints_defaults": "comma"},
            [f":Parameters: **b** ({_STR_TYPE}, default: ``'x'``) -- the b"],
            id="comma-default",
        ),
        pytest.param(
            [":Parameters: **b** -- the b"],
            {"typehints_defaults": "braces"},
            [f":Parameters: **b** ({_STR_TYPE}) (default: ``'x'``) -- the b"],
            id="braces-default",
        ),
        pytest.param(
            [":Parameters: * **b** -- the b", "               continued", "             * **a** -- the a"],
            {"typehints_defaults": "braces-after"},
            [
                f":Parameters: * **b** ({_STR_TYPE}) -- the b",
                "               continued (default: ``'x'``)",
                f"             * **a** ({_INT_TYPE}) -- the a",
            ],
            id="braces-after-default",
        ),
        pytest.param(
            [":Parameters: * **b** -- the b", "", "               more about b", "             * **a** -- the a"],
            {"typehints_defaults": "braces-after"},
            [
                f":Parameters: * **b** ({_STR_TYPE}) -- the b",
                "",
                "               more about b (default: ``'x'``)",
                f"             * **a** ({_INT_TYPE}) -- the a",
            ],
            id="braces-after-default-past-a-paragraph",
        ),
        pytest.param(
            [":Parameters: **b** (*str*) -- the b"],
            {"typehints_defaults": "comma"},
            [":Parameters: **b** (*str*, default: ``'x'``) -- the b"],
            id="typed-in-the-docstring-comma-default",
        ),
        pytest.param(
            [":Parameters: **b** (*str*) -- the b"],
            {"typehints_defaults": "braces"},
            [":Parameters: **b** (*str*) (default: ``'x'``) -- the b"],
            id="typed-in-the-docstring-braces-default",
        ),
        pytest.param(
            [":Parameters: **b** (*str*) -- the b"],
            {"typehints_defaults": "braces-after"},
            [":Parameters: **b** (*str*) -- the b (default: ``'x'``)"],
            id="typed-in-the-docstring-braces-after-default",
        ),
        pytest.param(
            [":Parameters: **b** (*str* -- the b"],
            {"typehints_defaults": "comma"},
            [":Parameters: **b** (*str* -- the b"],
            id="typed-in-the-docstring-unclosed",
        ),
    ],
)
def test_process_docstring_types_a_combined_parameter_field(
    lines: list[str], overrides: dict[str, object], expected: list[str]
) -> None:
    def documented(a: int, b: str = "x", *args: float) -> None: ...

    app = make_docstring_app(typehints_document_rtype=False, **overrides)
    process_docstring(app, "function", "mod.documented", documented, None, lines)
    assert lines == expected


def test_process_docstring_leaves_an_unannotated_combined_entry_alone() -> None:
    def documented(a="x") -> None: ...  # ruff:ignore[missing-type-function-argument]  # the case under test

    lines = [":Parameters: **a** -- the a"]
    app = make_docstring_app(typehints_document_rtype=False, typehints_defaults="comma")
    process_docstring(app, "function", "mod.documented", documented, None, lines)
    assert lines == [":Parameters: **a** -- the a"]


@pytest.mark.parametrize(
    "outside",
    [
        pytest.param([":Overloads:", "   * **a** (int) → int", ""], id="overload"),
        pytest.param(["Example::", "", "    **a** is bold here", ""], id="code-example"),
        pytest.param([":returns:", "   * **a** (int)", ""], id="named-return"),
    ],
)
def test_process_docstring_types_only_entries_of_a_combined_field(outside: list[str]) -> None:
    def documented(a: int = 1, b: str = "x") -> None: ...

    lines = [*outside, ":Parameters: **b** -- the b"]
    app = make_docstring_app(typehints_document_rtype=False, typehints_defaults="comma")
    process_docstring(app, "function", "mod.documented", documented, None, lines)
    assert lines == [*outside, f":Parameters: **b** ({_STR_TYPE}, default: ``'x'``) -- the b"]


class _Mode(enum.Enum):
    FAST = 1


class _MultiLineRepr:
    def __repr__(self) -> str:
        return "MultiLine(\n  a=1,\n)"


@pytest.mark.parametrize(
    ("default", "expected"),
    [
        pytest.param(object(), "<object object>", id="sentinel"),
        pytest.param(_Mode.FAST, "_Mode.FAST", id="enum-member"),
        pytest.param(frozenset({"gamma", "alpha", "beta"}), "frozenset({'alpha', 'beta', 'gamma'})", id="frozenset"),
        pytest.param(_MultiLineRepr(), "MultiLine(   a=1, )", id="multi-line-repr"),
        pytest.param("x\\y", r"'x\\y'", id="backslash"),
    ],
)
def test_process_docstring_describes_a_default_like_the_signature(default: object, expected: str) -> None:
    def func(value: object = default) -> None: ...

    lines = [":param value: the value"]
    app = make_docstring_app(typehints_document_rtype=False, typehints_defaults="comma")
    process_docstring(app, "function", "mod.func", func, None, lines)
    assert lines == [
        rf":type value: :sphinx_autodoc_typehints_type:`\:py\:class\:\`object\``, default: ``{expected}``",
        ":param value: the value",
    ]


_A_TYPE: Final = r":type a: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``"
_B_TYPE: Final = r":type b: :sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``"


def _returns_described_none() -> Annotated[None, Doc("nothing at all")]: ...


def test_process_docstring_leaves_off_an_annotated_none_return_type() -> None:
    lines: list[str] = []
    process_docstring(
        make_docstring_app(typehints_document_rtype_none=False),
        "function",
        "mod._returns_described_none",
        _returns_described_none,
        None,
        lines,
    )
    assert lines == [":return: nothing at all"]


def _pair(a: int, b: str) -> None: ...


def _described(a: Annotated[int, Doc("the a")], b: str) -> None: ...


@pytest.mark.parametrize(
    ("func", "lines", "expected"),
    [
        pytest.param(
            _pair,
            [":param b: the b", "", "Closing."],
            [_A_TYPE, ":param a:", _B_TYPE, ":param b: the b", "", "Closing."],
            id="before-a-later-param",
        ),
        pytest.param(
            _pair,
            [":param a: the a", "    more", "", "Closing."],
            [_A_TYPE, ":param a: the a", "    more", _B_TYPE, ":param b:", "", "Closing."],
            id="after-the-last-param",
        ),
        pytest.param(
            _pair,
            ["Closing."],
            ["Closing.", "", _A_TYPE, ":param a:", _B_TYPE, ":param b:"],
            id="none-documented",
        ),
        pytest.param(
            _described,
            [":param b: the b", "", "Closing."],
            [_A_TYPE, ":param a: the a", _B_TYPE, ":param b: the b", "", "Closing."],
            id="doc-description",
        ),
    ],
)
def test_process_docstring_adds_params_in_signature_order(
    func: Callable[..., None], lines: list[str], expected: list[str]
) -> None:
    app = make_docstring_app(always_document_param_types=True, typehints_document_rtype=False)
    process_docstring(app, "function", "mod.func", func, None, lines)
    assert lines == expected


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


@pytest.mark.parametrize(
    ("strip_signature_backslash", "expected"),
    [
        pytest.param(False, r"(sep='\n')", id="kept-as-is"),
        pytest.param(True, r"(sep='\\n')", id="escaped-for-stripping"),
    ],
)
def test_process_signature_escapes_backslashes_only_for_stripping(
    strip_signature_backslash: bool, expected: str
) -> None:
    def join(sep: str = "\n") -> str: ...

    app = make_sig_app(strip_signature_backslash=strip_signature_backslash)
    assert process_signature(app, "function", "mod.join", join, Options(), "", "") == (expected, None)


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


class _Rejecting:
    def __class_getitem__(cls, item: type) -> type[_Rejecting]:  # pragma: >=3.14 cover
        msg = f"cannot take {item}"
        raise ValueError(msg)


@pytest.mark.skipif(sys.version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param("Undefined", id="name-error"),
        pytest.param("int[str]", id="type-error"),
        pytest.param("_Rejecting[int]", id="value-error"),
    ],
)
def test_process_signature_strips_annotations_that_fail_to_evaluate(annotation: str) -> None:  # pragma: >=3.14 cover
    namespace: dict[str, Any] = {"_Rejecting": _Rejecting}
    # dont_inherit keeps this file's `from __future__ import annotations` out, so the annotation stays lazy
    source = f"def func(value: {annotation}) -> None: ..."
    exec(compile(source, "<func>", "exec", dont_inherit=True), namespace)  # ruff:ignore[exec-builtin]
    result = process_signature(make_sig_app(), "function", "mod.func", namespace["func"], Options(), "", "")
    assert result == ("(value)", None)


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


@pytest.mark.parametrize(
    "type_text",
    [
        pytest.param("- item", id="bullet"),
        pytest.param("#. item", id="enumerated"),
        pytest.param("* item", id="asterisk-bullet"),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy")
def test_type_role_renders_list_like_text_inline(
    app: SphinxTestApp, write_rst: Callable[[str], None], type_text: str
) -> None:
    write_rst(f"A :sphinx_autodoc_typehints_type:`{type_text}` b.")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == f"A {type_text} b.\n"


@pytest.mark.sphinx("text", testroot="dummy")
def test_singledispatch_implementation_keeps_its_types(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autofunction:: dummy_module.dispatch")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == dedent("""\
        dummy_module.dispatch(arg, flag=False)
        dummy_module.dispatch(arg: int, flag: bool = False) -> str

           Dispatch on the argument type.

           Parameters:
              **arg** ("object") -- the argument

           Return type:
              "str"
        """)


@pytest.mark.parametrize("cls", ["DocumentedTwice", "DocumentedTwiceThroughNew"])
@pytest.mark.sphinx(
    "text",
    testroot="dummy",
    confoverrides={"autoclass_content": "both", "always_document_param_types": True},
)
def test_class_and_constructor_docstrings_list_each_param_once(
    app: SphinxTestApp, write_rst: Callable[[str], None], cls: str
) -> None:
    write_rst(f".. autoclass:: dummy_module.{cls}")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == dedent(f"""\
        class dummy_module.{cls}(first, second, third)

           Class docstring.

           Parameters:
              **first** ("int") -- the first

           Constructor docstring.

           Parameters:
              * **second** ("str") -- the second

              * **third** ("bool")
        """)


@pytest.mark.sphinx("text", testroot="dummy", confoverrides={"typehints_use_signature": True})
def test_kept_signature_warns_about_an_unresolvable_annotation_once(
    app: SphinxTestApp, write_rst: Callable[[str], None], warning: StringIO
) -> None:
    write_rst(".. autofunction:: dummy_module.unresolvable")
    app.build()

    assert warning.getvalue().count("Cannot resolve forward reference") == 1


@pytest.mark.sphinx(
    "text",
    testroot="dummy",
    confoverrides={"autoclass_content": "both", "always_document_param_types": True},
)
def test_class_and_constructor_docstrings_list_an_escaped_param_once(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. autoclass:: dummy_module.DocumentedTwiceWithUnderscore")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == dedent("""\
        class dummy_module.DocumentedTwiceWithUnderscore(type_, count)

           Class docstring.

           Parameters:
              **type_** ("str") -- the type

           Constructor docstring.

           Parameters:
              **count** ("int") -- the count
        """)


@pytest.mark.parametrize(
    ("cls", "body"),
    [
        pytest.param(
            "KeysTwice",
            '   Parameters:\n      **kwargs** ("Unpack"["_TwiceOptions"])\n\n'
            '   Keyword Arguments:\n      **verbose** ("bool")\n',
            id="unpacked-keys",
        ),
        pytest.param(
            "OverloadedTwice",
            '   Overloads:\n      * **a** ("int")\n\n      * **a** ("str")\n\n'
            '   Parameters:\n      **a** ("int" | "str")\n',
            id="overloads",
        ),
        pytest.param("DescribedTwice", '   Parameters:\n      **a** ("int") -- the a\n', id="doc-described"),
    ],
)
@pytest.mark.sphinx(
    "text",
    testroot="dummy",
    confoverrides={"autoclass_content": "both", "always_document_param_types": True},
)
def test_class_and_constructor_docstrings_add_to_the_constructor_once(
    app: SphinxTestApp, write_rst: Callable[[str], None], cls: str, body: str
) -> None:
    write_rst(f".. autoclass:: dummy_module.{cls}")
    app.build()

    text = (Path(app.srcdir) / "_build/text/index.txt").read_text()
    assert text.partition("\n\n")[2] == f"   Class docstring.\n\n   Constructor docstring.\n\n{body}"


@pytest.mark.sphinx("text", testroot="dummy", confoverrides={"autoclass_content": "both"})
def test_class_and_constructor_docstrings_head_the_class_with_its_deprecation(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. autoclass:: dummy_module.DeprecatedTwice")
    app.build()

    text = (Path(app.srcdir) / "_build/text/index.txt").read_text()
    assert text.partition("\n\n")[2] == (
        "   Class docstring.\n\n   Deprecated: use something else\n\n   Constructor docstring.\n\n"
        '   Parameters:\n      **a** ("int") -- the a\n'
    )


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


class _Options(TypedDict, total=False):
    verbose: Required[bool]
    level: int
    name: Annotated[NotRequired[str], Doc("the name")]
    alias: NotRequired[Annotated[str, Doc("the alias")]]


class _Unresolvable(TypedDict):
    callback: Undefined  # ruff:ignore[undefined-name]  # ty: ignore[unresolved-reference]  # the case under test


_Odd = TypedDict("_Odd", {"odd-key": int, "class": int, "count": int})


def _configure(**kwargs: Unpack[_Options]) -> None: ...


def _unresolvable(**kwargs: Unpack[_Unresolvable]) -> None: ...


def _odd(count: int, **kwargs: Unpack[_Odd]) -> None: ...


def _plain(**kwargs: int) -> None: ...


_BOOL: Final = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`bool\``"
_INT: Final = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``"
_UNPACKED: Final = (
    r":sphinx_autodoc_typehints_type:`\:py\:data\:\`\~typing.Unpack\`\\ \\\[\:py\:class\:\`\~test\_init.\{}\`\]`"
)
_NOT_REQUIRED: Final = (
    r":sphinx_autodoc_typehints_type:`\:py\:data\:\`\~typing.NotRequired\`\\ \\\[\:py\:class\:\`{}\`\]`"
)


@pytest.mark.parametrize(
    ("func", "always", "lines", "expected"),
    [
        pytest.param(
            _configure,
            False,
            [":param kwargs: the options", ":keyword verbose: be loud", ":keyword level: how loud"],
            [
                f":type kwargs: {_UNPACKED.format('_Options')}",
                ":param kwargs: the options",
                f":paramtype verbose: {_BOOL}",
                ":keyword verbose: be loud",
                f":paramtype level: {_NOT_REQUIRED.format('int')}",
                ":keyword level: how loud",
                f":paramtype name: {_NOT_REQUIRED.format('str')}",
                ":keyword name: the name",
                f":paramtype alias: {_NOT_REQUIRED.format('str')}",
                ":keyword alias: the alias",
            ],
            id="documented-keys",
        ),
        pytest.param(
            _configure,
            True,
            [":param kwargs: the options"],
            [
                f":type kwargs: {_UNPACKED.format('_Options')}",
                ":param kwargs: the options",
                f":paramtype verbose: {_BOOL}",
                ":keyword verbose:",
                f":paramtype level: {_NOT_REQUIRED.format('int')}",
                ":keyword level:",
                f":paramtype name: {_NOT_REQUIRED.format('str')}",
                ":keyword name: the name",
                f":paramtype alias: {_NOT_REQUIRED.format('str')}",
                ":keyword alias: the alias",
            ],
            id="undocumented-keys",
        ),
        pytest.param(
            _configure,
            True,
            [":param kwargs: the options", ":Keyword Arguments: **verbose** -- be loud"],
            [
                f":type kwargs: {_UNPACKED.format('_Options')}",
                ":param kwargs: the options",
                f":Keyword Arguments: * **verbose** ({_BOOL}) -- be loud",
                f"                    * **level** ({_NOT_REQUIRED.format('int')})",
                f"                    * **name** ({_NOT_REQUIRED.format('str')}) -- the name",
                f"                    * **alias** ({_NOT_REQUIRED.format('str')}) -- the alias",
            ],
            id="combined-keyword-field",
        ),
        pytest.param(
            _odd,
            False,
            [":param count: the count", ":param kwargs: the rest"],
            [
                f":type count: {_INT}",
                ":param count: the count",
                f":type kwargs: {_UNPACKED.format('_Odd')}",
                ":param kwargs: the rest",
            ],
            id="keys-that-cannot-be-parameters",
        ),
        pytest.param(
            _unresolvable,
            True,
            [":param kwargs: the options"],
            [f":type kwargs: {_UNPACKED.format('_Unresolvable')}", ":param kwargs: the options"],
            id="unresolvable-key-types",
        ),
        pytest.param(
            _plain,
            True,
            [":param kwargs: the options"],
            [f":type kwargs: {_INT}", ":param kwargs: the options"],
            id="not-unpacked",
        ),
    ],
)
def test_process_docstring_types_the_keys_of_unpacked_kwargs(
    func: types.FunctionType, always: bool, lines: list[str], expected: list[str]
) -> None:
    app = make_docstring_app(typehints_document_rtype=False, always_document_param_types=always)
    process_docstring(app, "function", f"mod.{func.__name__}", func, None, lines)
    assert lines == expected


class _OverrideBase:
    def run(self) -> str: ...

    @property
    def size(self) -> int: ...


class _OverrideChild(_OverrideBase):
    @override
    def run(self) -> str: ...

    @property
    @override
    def size(self) -> int: ...

    @override
    def extra(self) -> str: ...  # ty: ignore[invalid-explicit-override]  # the case under test

    def plain(self) -> str: ...


class _OverrideGrandchild(_OverrideChild):
    @override
    @functools.cache  # ruff:ignore[cached-instance-method]  # any decorator that wraps
    def run(self) -> str: ...


class _OverrideInheritor(_OverrideChild):
    """Inherits the override of _OverrideChild."""


@pytest.mark.parametrize(
    ("what", "member", "overrides", "expected"),
    [
        pytest.param(
            "method",
            "_OverrideChild.run",
            {},
            [":Overrides: :py:meth:`_OverrideBase.run <test_init._OverrideBase.run>`"],
            id="method",
        ),
        pytest.param(
            "property",
            "_OverrideChild.size",
            {},
            [":Overrides: :py:attr:`_OverrideBase.size <test_init._OverrideBase.size>`"],
            id="property",
        ),
        pytest.param(
            "method",
            "_OverrideGrandchild.run",
            {},
            [":Overrides: :py:meth:`_OverrideChild.run <test_init._OverrideChild.run>`"],
            id="wrapped-method-nearest-base",
        ),
        pytest.param(
            "method",
            "_OverrideInheritor.run",
            {},
            [":Overrides: :py:meth:`_OverrideBase.run <test_init._OverrideBase.run>`"],
            id="inherited-member",
        ),
        pytest.param(
            "method",
            "_OverrideChild.run",
            {"typehints_fully_qualified": True},
            [":Overrides: :py:meth:`test_init._OverrideBase.run <test_init._OverrideBase.run>`"],
            id="fully-qualified",
        ),
        pytest.param(
            "method",
            "_OverrideChild.run",
            {"typehints_fixup_module_name": lambda module: "renamed" if module == "test_init" else module},
            [":Overrides: :py:meth:`_OverrideBase.run <renamed._OverrideBase.run>`"],
            id="fixed-up-module",
        ),
        pytest.param("method", "_OverrideChild.extra", {}, [], id="nothing-to-override"),
        pytest.param("method", "_OverrideChild.plain", {}, [], id="not-marked"),
    ],
)
def test_process_docstring_links_what_an_override_overrides(
    what: str, member: str, overrides: dict[str, object], expected: list[str]
) -> None:
    owner, attribute = member.split(".")
    obj = inspect.getattr_static(globals()[owner], attribute)
    lines = ["Summary."]
    app = make_docstring_app(typehints_document_rtype=False, **overrides)
    process_docstring(app, what, f"test_init.{member}", obj, None, lines)
    assert lines == ["Summary.", *([""] if expected else []), *expected]


def test_process_docstring_override_outside_an_importable_class() -> None:
    lines = ["Summary."]
    process_docstring(make_docstring_app(), "method", "missing_module.Child.run", _OverrideChild.run, None, lines)
    assert lines == ["Summary.", "", r":rtype: :sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``"]


class _Setters:
    @property
    def wider(self) -> int: ...

    @wider.setter
    def wider(self, new: int | str) -> None: ...

    @property
    def untyped_getter(self): ...  # ruff:ignore[missing-return-type-private-function]  # the case under test

    @untyped_getter.setter
    def untyped_getter(self, new: int) -> None: ...

    @property
    def same(self) -> int: ...

    @same.setter
    def same(self, new: int) -> None: ...

    @property
    def untyped_setter(self) -> int: ...

    @untyped_setter.setter
    def untyped_setter(self, new) -> None: ...  # ruff:ignore[missing-type-function-argument]  # the case under test

    @property
    def read_only(self) -> int: ...

    @functools.cached_property
    def cached(self) -> int: ...


@pytest.mark.parametrize(
    ("member", "lines", "expected"),
    [
        pytest.param(
            "wider",
            ["Summary."],
            [
                "Summary.",
                "",
                r":Setter accepts: :sphinx_autodoc_typehints_type:`\:py\:class\:\`int\` \| \:py\:class\:\`str\``",
            ],
            id="setter-wider-than-getter",
        ),
        pytest.param("untyped_getter", ["Summary."], ["Summary.", "", f":Setter accepts: {_INT}"], id="untyped-getter"),
        pytest.param("same", ["Summary."], ["Summary."], id="same-type"),
        pytest.param("untyped_setter", ["Summary."], ["Summary."], id="untyped-setter"),
        pytest.param("read_only", ["Summary."], ["Summary."], id="no-setter"),
        pytest.param("cached", ["Summary."], ["Summary."], id="cached-property"),
        pytest.param(
            "wider",
            ["Summary.", "", ":Setter accepts: a number"],
            ["Summary.", "", ":Setter accepts: a number"],
            id="docstring-states-it",
        ),
    ],
)
def test_process_docstring_shows_the_type_a_property_setter_accepts(
    member: str, lines: list[str], expected: list[str]
) -> None:
    process_docstring(
        make_docstring_app(), "property", f"test_init._Setters.{member}", vars(_Setters)[member], None, lines
    )
    assert lines == expected
