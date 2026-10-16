from __future__ import annotations

from operator import attrgetter
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark, param

from sphinx_autodoc_typehints._resolve.backfill import backfill_type_hints

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType


@mark.parametrize(
    ("source", "owner", "expected", "warning"),
    [
        param(
            dedent("""\
                def func(x, y):
                    # type: (int, str) -> bool
                    ...
            """),
            "func",
            {"x": "int", "y": "str", "return": "bool"},
            None,
            id="function",
        ),
        param(
            dedent("""\
                class Holder:
                    def method(self, x):
                        # type: (int) -> str
                        ...
            """),
            "Holder.method",
            {"x": "int", "return": "str"},
            None,
            id="method-leaving-out-self",
        ),
        param(
            dedent("""\
                def func(x, y, /):
                    # type: (int, str) -> bool
                    ...
            """),
            "func",
            {"x": "int", "y": "str", "return": "bool"},
            None,
            id="positional-only",
        ),
        param(
            dedent("""\
                def func(
                    x,  # type: int
                    y,  # type: str
                ):
                    # type: (...) -> bool
                    ...
            """),
            "func",
            {"x": "int", "y": "str", "return": "bool"},
            None,
            id="per-parameter",
        ),
        param(
            # the escape keeps the space the comment ends with, which an editor would strip
            dedent("""\
                def func(x):
                    # type: (int) ->\x20
                    ...
            """),
            "func",
            {"x": "int"},
            None,
            id="empty-return",
        ),
        param(
            dedent("""\
                def func():
                    # type: () -> int
                    ...
            """),
            "func",
            {"return": "int"},
            None,
            id="no-parameters",
        ),
        param(
            dedent("""\
                def func(x, y):
                    # type: (List[int], Dict[str, int]) -> None
                    ...
            """),
            "func",
            {"x": "List[int]", "y": "Dict[str, int]", "return": "None"},
            None,
            id="nested-brackets",
        ),
        param(
            dedent("""\
                def func(*args, **kwargs):
                    # type: (*int, **str) -> None
                    ...
            """),
            "func",
            {"args": "int", "kwargs": "str", "return": "None"},
            None,
            id="variadic",
        ),
        param(
            dedent("""\
                async def func(x):
                    # type: (int) -> None
                    class Inner:
                        def __init__(self): ...
            """),
            "func",
            {"x": "int", "return": "None"},
            None,
            id="async",
        ),
        param(
            dedent("""\
                def decorate(*args, **kwargs):
                    return lambda func: func

                class Holder:
                    @decorate(
                        "self",
                        default=None,
                    )
                    def method(self, x):
                        # type: (int) -> str
                        ...
            """),
            "Holder.method",
            {"x": "int", "return": "str"},
            None,
            id="decorator-over-several-lines",
        ),
        param(
            dedent("""\
                class Holder:
                    def method(self, x):
                        # type: (int) -> str
                        text = '''
                at the first column
                '''
            """),
            "Holder.method",
            {"x": "int", "return": "str"},
            None,
            id="line-left-of-the-def",
        ),
        param(
            dedent("""\
                def func(x):
                    ...
            """),
            "func",
            {},
            None,
            id="no-type-comment",
        ),
        param(
            dedent("""\
                square = lambda x: x * x  # type: Callable[[int], int]
            """),
            "square",
            {},
            None,
            id="lambda-typed-as-a-variable",
        ),
        param(
            dedent("""\
                square = (0,
                    lambda x: x * x)[1]
            """),
            "square",
            {},
            None,
            id="source-that-does-not-parse-alone",
        ),
        param(
            dedent("""\
                def func(x, y, z):
                    # type: (int) -> bool
                    ...
            """),
            "func",
            {"return": "bool"},
            ("comment", "mod.func"),
            id="fewer-types-than-parameters",
        ),
        param(
            dedent("""\
                def func(x):
                    # type: bad_comment
                    ...
            """),
            "func",
            {},
            ("comment", "mod.func"),
            id="no-arrow",
        ),
        param(
            dedent("""\
                first = 1; square = lambda x: x * x
            """),
            "square",
            {},
            ("multiple_ast_nodes", "mod.func", "2"),
            id="source-of-two-statements",
        ),
    ],
)
def test_backfill_type_hints(
    make_module: Callable[[str], ModuleType],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    source: str,
    owner: str,
    expected: dict[str, str],
    warning: tuple[str, ...] | None,
) -> None:
    module = make_module(source)
    assert (backfill_type_hints(attrgetter(owner)(module), "mod.func"), logged_warnings()) == (
        expected,
        [] if warning is None else [(warning[0], f"{module.__file__}:1", *warning[1:])],
    )


@mark.parametrize("obj", [param(len, id="builtin"), param(property(), id="not-callable")])
def test_backfill_type_hints_of_an_object_without_source(obj: Callable[..., object] | property) -> None:
    assert backfill_type_hints(obj, "mod.obj") == {}
