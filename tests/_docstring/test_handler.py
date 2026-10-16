from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property, cmp_to_key, partial, update_wrapper, wraps
from inspect import Parameter, Signature, signature
from os import utime
from pathlib import Path
from re import findall
from typing import TYPE_CHECKING, Final, Self

import typing_extensions  # its Self is tested next to typing.Self
from pytest import MarkDecorator, mark, param
from typing_extensions import deprecated

from _docstring.conftest import BOOL, FLOAT, INT, NONE, STR

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO
    from types import MethodType

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp

    from _docstring.conftest import Process
    from sphinx_autodoc_typehints._types import Documented

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")

_FLOAT_VALUE: Final[list[str]] = [f":type value: {FLOAT}", ":param value: doc"]


def _joined(count: int, sep: str, *, end: str = "") -> str: ...


class _Joiner:
    def __call__(self, sep: str, *, end: str = "") -> str: ...


@mark.parametrize(
    "obj",
    [param(partial(_joined, 1), id="partial"), param(_Joiner(), id="callable-instance")],
)
def test_callable_takes_the_types_of_what_it_calls(process: Process, obj: Callable[..., str]) -> None:
    assert process("function", "mod.joined", obj, [":param sep: the separator"]) == [
        f":type sep: {STR}",
        ":param sep: the separator",
        "",
        f":rtype: {STR}",
    ]


@mark.parametrize(
    ("what", "obj"),
    [
        param("data", _Joiner(), id="data-callable-instance"),
        param("data", _joined, id="data-function"),
        param("attribute", _Joiner(), id="attribute-callable-instance"),
        param("data", 1, id="data"),
    ],
)
def test_value_holding_a_callable_stays_untyped(process: Process, what: str, obj: Documented) -> None:
    assert process(what, "mod.held", obj, ["The converter."]) == ["The converter."]


class _Slotted:
    __slots__ = ()


def _looping(value: int) -> str: ...


vars(_looping)["__wrapped__"] = _looping


@mark.parametrize(
    ("what", "obj"),
    [
        param("class", _Slotted, id="slot-wrapper-constructor"),
        param("function", _looping, id="wrapper-loop"),
        param("function", cmp_to_key, id="builtin"),
        param("function", next, id="builtin-without-signature"),
    ],
)
def test_callable_it_cannot_inspect_stays_untyped(process: Process, what: str, obj: Documented) -> None:
    assert process(what, "mod.obj", obj, [":param value: the value"]) == [":param value: the value"]


def test_callable_with_an_unreadable_signature_types_only_its_return(process: Process) -> None:
    class UnreadableSignature:
        __signature__ = "unreadable"

        def __call__(self, value: int) -> str: ...

    assert process("function", "mod.unreadable", UnreadableSignature(), [":param value: the value"]) == [
        ":param value: the value",
        "",
        f":rtype: {STR}",
    ]


class _NewOnly:
    def __new__(cls, value: float) -> Self: ...


class _BothClass:
    def __new__(cls, value: float) -> Self: ...

    def __init__(self, *args: float) -> None: ...


@deprecated("use something else")
class _Deprecated:
    def __init__(self, value: float) -> None: ...


class _StatesSignature:
    __signature__ = Signature([Parameter("value", Parameter.KEYWORD_ONLY, annotation=float)])

    def __init__(self, **data: object) -> None: ...


class _UnreadyMeta(type):
    @property
    def __signature__(cls) -> Signature:  # ruff:ignore[bad-dunder-method-name]  # inspect reads it
        raise ValueError


class _Unready(metaclass=_UnreadyMeta):
    def __init__(self, value: float) -> None: ...


class _Shadowed:
    value: int

    def __new__(cls, value: float) -> Self: ...


@mark.parametrize(
    ("cls", "expected"),
    [
        param(_NewOnly, _FLOAT_VALUE, id="new-beside-inherited-init"),
        param(_BothClass, _FLOAT_VALUE, id="new-beside-init"),
        param(_Shadowed, _FLOAT_VALUE, id="new-over-shadowing-class-attribute"),
        param(
            _Deprecated,  # ty: ignore[deprecated]  # the case under test
            ["", ".. sphinx_autodoc_typehints_deprecated::", "", "   use something else", "", *_FLOAT_VALUE],
            id="init-beside-new-wrapping-object-new",
        ),
        param(_StatesSignature, _FLOAT_VALUE, id="stated-signature"),
        param(_Unready, _FLOAT_VALUE, id="signature-raises"),
    ],
)
def test_class_takes_the_params_of_its_constructor(process: Process, cls: type, expected: list[str]) -> None:
    assert process("class", "mod.cls", cls, [":param value: doc"]) == expected


def _wrapped(value: float) -> None: ...


class _UnreadyWrapper:
    @property
    def __signature__(self) -> Signature:  # ruff:ignore[bad-dunder-method-name]  # inspect reads it
        raise RuntimeError

    def __call__(self, value: float) -> None: ...


def _stated(*args: object, **kwargs: object) -> None: ...


vars(_stated)["__signature__"] = Signature(
    [Parameter("value", Parameter.KEYWORD_ONLY, annotation=float)], return_annotation=str
)


@mark.parametrize(
    ("func", "expected"),
    [
        param(
            update_wrapper(_UnreadyWrapper(), _wrapped),
            [*_FLOAT_VALUE, "", f":rtype: {NONE}"],
            id="wrapper-whose-signature-raises",
        ),
        param(_stated, [*_FLOAT_VALUE, "", f":rtype: {STR}"], id="stated-signature"),
    ],
)
def test_function_takes_the_params_of_what_it_calls(process: Process, func: Documented, expected: list[str]) -> None:
    assert process("function", "mod.func", func, [":param value: doc"]) == expected


@mark.sphinx(confoverrides={"always_document_param_types": True, "typehints_defaults": "comma"})
def test_wrapper_lists_the_parameters_it_states(process: Process) -> None:
    def handle(ctx: object, name: str, count: int = 1) -> bool: ...

    @wraps(handle)
    def injected(*args: object, **kwargs: object) -> bool: ...

    # a dependency-injecting decorator hides the parameter it supplies
    vars(injected)["__signature__"] = Signature(list(signature(handle, eval_str=True).parameters.values())[1:])
    assert process("function", "mod.injected", injected, [":param name: the name"]) == [
        f":type name: {STR}",
        ":param name: the name",
        f":type count: {INT}, default: ``1``",
        ":param count:",
        "",
        f":rtype: {BOOL}",
    ]


class _DeprecatedGetters:
    @property
    @deprecated("use size_v2")
    def plain(self) -> int: ...

    @cached_property
    @deprecated("use size_v2")
    def cached(self) -> int: ...


@mark.parametrize("member", [param("plain", id="property"), param("cached", id="cached-property")])
def test_process_docstring_marks_a_deprecated_property_getter(process: Process, member: str) -> None:
    prop = vars(_DeprecatedGetters)[member]
    assert process("property", f"mod._DeprecatedGetters.{member}", prop, ["Size."]) == [
        "Size.",
        "",
        ".. sphinx_autodoc_typehints_deprecated::",
        "",
        "   use size_v2",
        "",
    ]


class _ReturnsSelf:
    @classmethod
    def from_magic(cls) -> typing_extensions.Self: ...

    def method(self) -> typing_extensions.Self: ...


@mark.parametrize(
    "method",
    [param(_ReturnsSelf.from_magic, id="classmethod"), param(_ReturnsSelf().method, id="method")],
)
@mark.sphinx(confoverrides={"always_document_param_types": True, "typehints_defaults": "comma"})
def test_process_docstring_of_a_bound_method_types_its_return(process: Process, method: MethodType) -> None:
    assert process("method", f"mod.{method.__qualname__}", method, ["Summary."]) == [
        "Summary.",
        "",
        r":rtype: :sphinx_autodoc_typehints_type:`\:py\:data\:\`\~typing.Self\``",
    ]


@mark.sphinx(confoverrides={"typehints_defaults": "comma"})
def test_process_docstring_shows_a_dataclass_factory_as_its_call(process: Process) -> None:
    @dataclass
    class Made:
        value: list[int] = field(default_factory=list)

    assert process("class", "mod.Made", Made, [":param value: the value"]) == [
        (
            r":type value: :sphinx_autodoc_typehints_type:`\:py\:class\:\`list\`\\ \\\[\:py\:class\:\`int\`\]`, "
            "default: ``list()``"
        ),
        ":param value: the value",
    ]


@mark.sphinx("text", testroot="pyi-stubs")
def test_process_docstring_rereads_the_pages_a_stub_types_once_it_changes(
    build_text: BuildText, app: SphinxTestApp, status: StringIO
) -> None:
    build_text(".. autofunction:: stub_mod.greet")
    stub = Path(app.srcdir) / "stub_mod.pyi"
    stub.write_text(stub.read_text().replace("greeting: str) -> str:", "greeting: str) -> bytes:"))
    # a rewrite within the same clock tick would keep the time Sphinx compares
    utime(stub, ns=(modified := stub.stat().st_mtime_ns + 1_000_000, modified))

    app.build()

    # the module this process already imported keeps the first types, so only the reread shows
    assert findall(r"(\d+) added, (\d+) changed, (\d+) removed", status.getvalue()) == [
        ("1", "0", "0"),
        ("0", "1", "0"),
    ]
