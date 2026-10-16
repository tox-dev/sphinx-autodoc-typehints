from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache, lru_cache, partial, partialmethod, update_wrapper, wraps
from inspect import Parameter, Signature, signature
from sys import version_info
from textwrap import dedent
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, NewType, Self, TypeVar

from pytest import LogCaptureFixture, MarkDecorator, fixture, mark, param
from sphinx.util.console import strip_colors
from typing_extensions import deprecated

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO
    from types import FunctionType

    from conftest import BuildText, MakeModule
    from sphinx.config import Config

    from _signature.conftest import SignatureOf
    from sphinx_autodoc_typehints._types import Annotation

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


class _ClassWithPrivate:
    def __secret(self, count: int) -> str: ...

    @staticmethod
    def __static_secret(value: int) -> str: ...


def _helper(value: int) -> str: ...


def _joined(count: int, sep: str, *, end: str = "") -> str: ...


class _BindsHelper:
    as_static = staticmethod(_helper)
    as_method = _helper

    @classmethod
    def plain_class(cls, value: int) -> str: ...

    @classmethod
    @cache
    def cached_class(cls, value: int) -> str: ...

    def join(self, count: int, sep: str, *, end: str = "") -> str: ...

    as_partial = partialmethod(join, 1)


def _nothing() -> None: ...


@mark.parametrize(
    ("name", "method", "expected"),
    [
        param(
            f"{__name__}._ClassWithPrivate._ClassWithPrivate__static_secret",
            vars(_ClassWithPrivate)["_ClassWithPrivate__static_secret"].__func__,
            "(value)",
            id="private-staticmethod-of-private-class",
        ),
        param(
            f"{__name__}._ClassWithPrivate.__secret",
            vars(_ClassWithPrivate)["_ClassWithPrivate__secret"],
            "(count)",
            id="mangled",
        ),
        param(
            f"{__name__}._ClassWithPrivate.__secret",
            vars(_ClassWithPrivate)["_ClassWithPrivate__secret"].__get__(_ClassWithPrivate()),
            "(count)",
            id="bound-to-an-instance",
        ),
        param(
            f"{__name__}._BindsHelper.as_static",
            _BindsHelper.as_static,
            "(value)",
            id="staticmethod-of-outside-function",
        ),
        param(f"{__name__}._BindsHelper.as_method", _BindsHelper.as_method, "()", id="method-of-outside-function"),
        param(f"{__name__}._BindsHelper.plain_class", _BindsHelper.plain_class, "(value)", id="classmethod"),
        param(
            f"{__name__}._BindsHelper.cached_class", _BindsHelper.cached_class, "(value)", id="classmethod-of-wrapper"
        ),
        param("not_imported.Missing.nothing", _nothing, "()", id="no-parameters-whatever-the-class"),
    ],
)
def test_process_signature_first_parameter_by_member_kind(
    signature_of: SignatureOf, name: str, method: Callable[..., object], expected: str
) -> None:
    assert signature_of("method", name, method) == (expected, None)


def _unowned(self: _Lock, count: int) -> str: ...


def _looping(value: int) -> str: ...


# a wrapper loop, which inspect.unwrap cannot follow (#405)
update_wrapper(_looping, _looping)


@mark.parametrize(
    ("what", "name", "obj", "given"),
    [
        param("data", f"{__name__}.alias", _helper, None, id="data-holding-a-callable"),
        param("function", "mod.joined", _joined, "(x, y=3)", id="written-with-other-parameters"),
        param("method", f"{__name__}.NonExistentClass.method", _unowned, "", id="class-missing"),
        param("method", "not_imported.NonExistentClass.method", _unowned, "", id="module-missing"),
        param("function", "mod.looping", _looping, "", id="wrapper-loop"),
    ],
)
def test_process_signature_leaves_the_signature(
    signature_of: SignatureOf, what: str, name: str, obj: Callable[..., object], given: str | None
) -> None:
    assert signature_of(what, name, obj, given) is None


def _compute(value: int) -> str: ...


class _Joiner:
    def __call__(self, sep: str, *, end: str = "") -> str: ...


class _Point(NamedTuple):
    left: int
    right: str


@dataclass
class _Made:
    value: list[int] = field(default_factory=list)


class _Lock:
    def __init__(self, path: str, timeout: float = -1) -> None: ...


class _ExtendingMeta(type):
    def __call__(cls, path: str, timeout: float = -1, **kwargs: float) -> _Lock: ...


class _PassingMeta(type):
    def __call__(cls, *args: str, **kwargs: str) -> _Lock: ...


class _LoopingMeta(type):
    def __call__(cls, path: str) -> _Lock: ...


# a wrapper loop, which hides the signature
update_wrapper(_LoopingMeta.__call__, _LoopingMeta.__call__)


class _ExtendedLock(_Lock, metaclass=_ExtendingMeta): ...


class _PassedLock(_Lock, metaclass=_PassingMeta): ...


class _LoopedLock(_Lock, metaclass=_LoopingMeta): ...


_STATED: Final[Signature] = Signature([Parameter("value", Parameter.KEYWORD_ONLY, annotation=float)])


def _stated(*args: float, **kwargs: float) -> None: ...


_stated.__dict__["__signature__"] = _STATED.replace(return_annotation=str)


def _handle(ctx: _Lock, name: str, count: int = 1) -> bool: ...


@wraps(_handle)
def _injected(*args: str, **kwargs: int) -> bool: ...


# a dependency-injecting decorator hides the parameter it supplies
_injected.__dict__["__signature__"] = Signature(list(signature(_handle, eval_str=True).parameters.values())[1:])


@mark.parametrize(
    ("what", "name", "obj", "given", "expected"),
    [
        param("function", "mod.compute", cache(_compute), "", "(value)", id="cache"),
        param("function", "mod.compute", lru_cache(_compute), "", "(value)", id="lru_cache"),
        param("function", "mod.joined", partial(_joined, 1), "", "(sep, *, end='')", id="partial"),
        param(
            "method",
            f"{__name__}._BindsHelper.as_partial",
            _BindsHelper.as_partial,
            "",
            "(sep, *, end='')",
            id="partialmethod",
        ),
        param("function", "mod.joiner", _Joiner(), "", "(sep, *, end='')", id="callable-instance"),
        param("class", "mod._Point", _Point, "", "(left, right)", id="namedtuple"),
        param("class", "mod._Made", _Made, "", "(value=list())", id="dataclass-factory-default"),
        param(
            "class",
            "mod.documented",
            _ExtendedLock,
            "(path: str, timeout: float = -1, **kwargs: Any)",
            "(path, timeout=-1, **kwargs)",
            id="metaclass-call",
        ),
        param(
            "class",
            "mod.documented",
            _PassedLock,
            "(*args: Any, **kwargs: Any)",
            "(path, timeout=-1)",
            id="pass-through-metaclass-call",
        ),
        param(
            "class",
            "mod.documented",
            _LoopedLock,
            "(path: str, timeout: float = -1)",
            "(path, timeout=-1)",
            id="unreadable-metaclass-call",
        ),
        param("function", "mod.documented", _stated, "", "(*, value)", id="stated-signature"),
        param(
            "function",
            "mod.documented",
            _injected,
            "(name: str, count: int = 1)",
            "(name, count=1)",
            id="wrapper-stated",
        ),
    ],
)
def test_process_signature_strips_the_types(
    signature_of: SignatureOf, what: str, name: str, obj: Callable[..., object], given: str, expected: str
) -> None:
    assert signature_of(what, name, obj, given) == (expected, None)


_KEPT: Final[dict[str, bool]] = {"typehints_use_signature": True, "typehints_use_signature_return": True}


class _ConstructedFromInit:
    def __init__(self, count: int) -> None: ...


def _counted(count: int) -> str: ...


# a class signature is the call building the instance, so its constructor's -> None does not show, whichever directive
# documents a class without overloads
@mark.parametrize(
    ("what", "obj", "expected"),
    [
        param("class", _ConstructedFromInit, "(count: int)", id="class"),
        param("function", _ConstructedFromInit, "(count: int)", id="class-as-a-function"),
        param("class", _counted, "(count: int) -> str", id="function-as-a-class"),
    ],
)
@mark.sphinx(confoverrides=_KEPT)
def test_process_signature_omits_only_a_constructor_return(
    signature_of: SignatureOf, what: str, obj: Callable[..., object], expected: str
) -> None:
    assert signature_of(what, "mod.documented", obj) == (expected, None)


_UserId = NewType("_UserId", int)


_Bounded = TypeVar("_Bounded", bound=int)


def _kept_class(value: Signature) -> Signature: ...


def _kept_flag(value: bool) -> None: ...


def _kept_new_type(value: _UserId) -> None: ...


def _kept_type_var(value: _Bounded) -> None: ...  # ruff:ignore[non-pep695-generic-function]  # no signature declares it


def _kept_declared[Number: int](value: Number) -> None: ...


def _kept_param_spec[**Params](*args: Params.args, **kwargs: Params.kwargs) -> None: ...


def _kept_literal(value: Literal["a", 1]) -> None: ...


def _kept_callable(value: Callable[..., int]) -> None: ...


type _Pair = tuple[int, int]


def _kept_alias(value: _Pair) -> None: ...


def _bool_as_rst(annotation: Annotation, _config: Config) -> str | None:
    return ":class:`bool`" if annotation is bool else None


@mark.parametrize(
    ("func", "expected"),
    [
        param(
            _kept_class,
            "(value: ~inspect.Signature) -> ~inspect.Signature",
            marks=mark.sphinx(confoverrides=_KEPT),
            id="class",
        ),
        param(
            _kept_class,
            "(value: inspect.Signature) -> inspect.Signature",
            marks=mark.sphinx(confoverrides=_KEPT | {"typehints_fully_qualified": True}),
            id="qualified",
        ),
        param(
            _kept_class,
            "(value: ~insp.Signature) -> ~insp.Signature",
            marks=mark.sphinx(
                confoverrides=_KEPT | {"typehints_fixup_module_name": lambda module: module.replace("inspect", "insp")}
            ),
            id="fixed-up-module",
        ),
        param(
            _kept_flag,
            "(value: bool) -> None",
            marks=mark.sphinx(confoverrides=_KEPT | {"typehints_formatter": _bool_as_rst}),
            id="formatter-markup",
        ),
        param(
            _kept_new_type,
            f"(value: ~{__name__}._UserId) -> None",
            marks=mark.sphinx(confoverrides=_KEPT),
            id="new-type",
        ),
        param(
            _kept_type_var,
            f"(value: ~{__name__}._Bounded) -> None",
            marks=mark.sphinx(confoverrides=_KEPT),
            id="type-var",
        ),
        param(
            _kept_declared,
            "(value: Number) -> None",
            marks=mark.sphinx(confoverrides=_KEPT),
            id="declared-type-param",
        ),
        param(
            _kept_param_spec,
            "(*args: Params.args, **kwargs: Params.kwargs) -> None",
            marks=mark.sphinx(confoverrides=_KEPT),
            id="param-spec-components",
        ),
        param(
            _kept_literal,
            "(value: ~typing.Literal['a', 1]) -> None",
            marks=mark.sphinx(confoverrides=_KEPT),
            id="literal",
        ),
        param(
            _kept_callable,
            "(value: ~collections.abc.Callable[..., int]) -> None",
            marks=mark.sphinx(confoverrides=_KEPT),
            id="callable",
        ),
        param(
            _kept_alias,
            f"(value: ~{__name__}._Pair) -> None",
            marks=mark.sphinx(confoverrides=_KEPT),
            id="type-alias",
        ),
    ],
)
def test_process_signature_keeps_types_as_the_fields_render_them(
    signature_of: SignatureOf, func: FunctionType, expected: str
) -> None:
    assert signature_of("function", f"mod.{func.__name__}", func) == (expected, None)


def test_process_signature_warns_about_a_local_method(signature_of: SignatureOf, caplog: LogCaptureFixture) -> None:
    def inner(self: _Lock, count: int) -> str: ...

    signature_of("method", "mod.outer.<locals>.inner", inner)

    assert caplog.messages == [
        (
            f"{__file__}:{inner.__code__.co_firstlineno}: WARNING: Cannot handle as a local function:"
            ' "mod.outer.<locals>.inner" (use @functools.wraps) [sphinx_autodoc_typehints.local_function]'
        )
    ]


class _NewOnlyClass:
    def __new__(cls, count: int, label: str) -> Self: ...


class _BothClass:
    def __new__(cls, value: float) -> Self: ...

    def __init__(self, *args: float) -> None: ...


class _InitOverridesNew(_BothClass):
    def __init__(self, count: int) -> None: ...


class _Plain:
    def __init__(self, value: float) -> None: ...


# the call form keeps type checkers from flagging each use of the class under test
_Deprecated = deprecated("use something else")(_Plain)


class _StatesSignature:
    __signature__ = _STATED

    def __init__(self, **data: float) -> None: ...


def _unready_signature(cls: type) -> Signature:
    raise ValueError(cls)


class _UnreadyMeta(type):
    __signature__ = property(_unready_signature)


class _Unready(metaclass=_UnreadyMeta):
    def __init__(self, value: float) -> None: ...


@mark.parametrize(
    ("cls", "expected"),
    [
        param(_NewOnlyClass, "(count: int, label: str)", id="new-when-init-inherited"),
        param(_BothClass, "(value: float)", id="new-beside-init"),
        param(_InitOverridesNew, "(count: int)", id="init-overrides-inherited-new"),
        param(_Deprecated, "(value: float)", id="new-wrapping-object-new"),
        param(_StatesSignature, "(*, value: float)", id="stated-signature"),
        param(_Unready, "(value: float)", id="signature-raises"),
    ],
)
@mark.sphinx(confoverrides={"typehints_use_signature": True})
def test_process_signature_picks_constructor_like_inspect(signature_of: SignatureOf, cls: type, expected: str) -> None:
    assert signature_of("class", f"mod.{cls.__name__}", cls) == (expected, None)


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
@mark.parametrize(
    "func",
    [
        param("name_error", id="name-error"),
        param("type_error", id="type-error"),
        param("value_error", id="value-error"),
    ],
)
def test_process_signature_strips_annotations_that_fail_to_evaluate(  # pragma: >=3.14 cover
    signature_of: SignatureOf, lazy_module: dict[str, FunctionType], func: str
) -> None:
    assert signature_of("function", "mod.func", lazy_module[func]) == ("(value)", None)


@fixture(name="lazy_module")
def lazy_module_fixture(make_module: MakeModule) -> dict[str, FunctionType]:  # pragma: >=3.14 cover
    # no `from __future__ import annotations`, so the annotations stay lazy instead of turning into strings
    return vars(
        make_module(
            "lazy_module",
            dedent("""\
            class Rejecting:
                def __class_getitem__(cls, item):
                    raise ValueError(item)

            def name_error(value: Undefined) -> None: ...

            def type_error(value: int[str]) -> None: ...

            def value_error(value: Rejecting[int]) -> None: ...
        """),
        )
    )


def test_singledispatch_implementation_keeps_its_types(build_text: BuildText) -> None:
    assert build_text(".. autofunction:: dummy_module.dispatch") == dedent("""\
        dummy_module.dispatch(arg, flag=False)
        dummy_module.dispatch(arg: int, flag: bool = False) -> str

           Dispatch on the argument type.

           Parameters:
              **arg** ("object") -- the argument

           Return type:
              "str"
    """)


@mark.sphinx(confoverrides={"typehints_use_signature": True})
def test_kept_signature_warns_about_an_unresolvable_annotation_once(build_text: BuildText, warning: StringIO) -> None:
    build_text(".. autofunction:: dummy_module.unresolvable")

    assert warning.getvalue().count("Cannot resolve forward reference") == 1


@mark.parametrize(
    "header",
    [
        param(
            "dummy_module_simple.function(x: bool, y: int = 1)",
            marks=mark.sphinx(confoverrides={"typehints_use_signature": True}),
            id="parameters",
        ),
        param(
            "dummy_module_simple.function(x, y=1) -> str",
            marks=mark.sphinx(confoverrides={"typehints_use_signature_return": True}),
            id="return",
        ),
        param(
            "dummy_module_simple.function(x: bool, y: int = 1) -> str",
            marks=mark.sphinx(confoverrides=_KEPT),
            id="both",
        ),
    ],
)
def test_process_signature_keeps_the_configured_types_in_a_build(build_text: BuildText, header: str) -> None:
    assert build_text(".. autofunction:: dummy_module_simple.function") == dedent(f"""\
        {header}

           Function docstring.

           Parameters:
              * **x** ("bool") -- foo

              * **y** ("int") -- bar

           Return type:
              "str"
    """)


# napoleon looks up a property and a method by name, which raised a KeyError (#620)
@mark.sphinx("text", testroot="integration")
def test_process_signature_of_the_members_napoleon_looks_up(
    build_text: BuildText, warning: StringIO, make_module: MakeModule
) -> None:
    make_module(
        "napoleon_lookup",
        dedent("""\
            class Counted:
                '''Count the elements.'''

                @property
                def n_unique_nonzero(self) -> int:
                    '''Number of unique nonzero elements.'''

                def regular_method(self, x: int) -> int:
                    '''
                    Do something.

                    Args:
                        x: a number
                    '''
        """),
    )
    assert (
        build_text(
            dedent("""\
                .. autoclass:: napoleon_lookup.Counted
                   :members:
            """)
        ),
        warning.getvalue(),
    ) == (
        dedent("""\
            class napoleon_lookup.Counted

               Count the elements.

               property n_unique_nonzero: int

                  Number of unique nonzero elements.

               regular_method(x)

                  Do something.

                  Parameters:
                     **x** ("int") -- a number

                  Return type:
                     "int"
        """),
        "",
    )


@mark.skipif(version_info < (3, 14), reason="eager annotations fail at import instead")
@mark.sphinx("text", testroot="integration")
def test_process_signature_of_a_generic_function_annotated_with_guarded_names(  # pragma: >=3.14 cover
    build_text: BuildText, warning: StringIO, make_module: MakeModule
) -> None:
    make_module(
        "guarded_generic",
        dedent("""\
            import functools
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from collections.abc import Callable

            def decorate[**P, R]() -> Callable[[Callable[P, R]], Callable[P, R]]:
                '''Return a decorator that wraps functions.'''
                def decorator[**P, R](func: Callable[P, R]) -> Callable[P, R]:
                    @functools.wraps(func)
                    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                        return func(*args, **kwargs)
                    return wrapper
                return decorator
        """),
    )
    assert (
        build_text(".. autofunction:: guarded_generic.decorate"),
        strip_colors(warning.getvalue()).splitlines(),
    ) == (
        dedent("""\
            guarded_generic.decorate[**P, R]()

               Return a decorator that wraps functions.

               Return type:
                  "Callable"[["Callable"["P", "R"]], "Callable"["P", "R"]]
        """),
        [],
    )
