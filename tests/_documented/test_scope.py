from __future__ import annotations

from dataclasses import replace
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from _docstring.conftest import BOOL
from pytest import MarkDecorator, fixture, mark

from sphinx_autodoc_typehints._docstring import process_docstring
from sphinx_autodoc_typehints._documented import render_scope
from sphinx_autodoc_typehints._render import render_context
from sphinx_autodoc_typehints._render.context import RenderContext

if TYPE_CHECKING:
    from types import ModuleType

    from conftest import MakeModule
    from sphinx.config import Config
    from sphinx.testing.util import SphinxTestApp

    from sphinx_autodoc_typehints._types import Annotation

pytestmark: Final[MarkDecorator] = mark.sphinx(
    "text", testroot="dummy", confoverrides={"autodoc_mock_imports": ["mocked"]}
)


def test_render_scope_publishes_where_the_types_render(app: SphinxTestApp) -> None:
    declared = frozenset(_generic.__type_params__)
    with render_scope(app, "mod", signature=True, declared_type_params=declared):
        context = render_context(app.config)

    expected = RenderContext(env=app.env, module_prefix="mod", signature=True, declared_type_params=declared)
    assert replace(context, guard_bound=None) == expected


def _generic[Item]() -> None: ...


def test_render_scope_guards_with_the_mocked_imports(app: SphinxTestApp, guarded_module: ModuleType) -> None:
    with render_scope(app, "scope_guarded_module"):
        binder = render_context(app.config).guard_bound
    assert binder is not None
    before = set(vars(guarded_module))

    with binder(guarded_module.func):
        bound = {name: repr(value) for name, value in vars(guarded_module).items() if name not in before}

    assert bound == {"Thing": "mocked.Thing"}


@fixture(name="guarded_module")
def guarded_module_fixture(make_module: MakeModule) -> ModuleType:
    return make_module(
        "scope_guarded_module",
        dedent("""\
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from mocked import Thing

            def func() -> None: ...
        """),
    )


def test_render_scope_hands_a_nested_docstring_the_outer_scope_back(app: SphinxTestApp) -> None:
    def inner(flag: str) -> str: ...

    def outer(flag: bool) -> bool: ...

    prefixes: list[str] = []

    def formatter(annotation: Annotation, config: Config) -> None:
        if annotation is bool:
            process_docstring(app, "function", "inner_mod.inner", inner, None, ["Inner.", "", ":return: it"])
            prefixes.append(render_context(config).module_prefix)

    app.config.typehints_formatter = formatter
    lines = ["Outer.", "", ":param flag: the flag", ":return: it"]
    process_docstring(app, "function", "outer_mod.outer", outer, None, lines)

    expected = [
        "Outer.",
        "",
        f":type flag: {BOOL}",
        ":param flag: the flag",
        "",
        f":rtype: {BOOL}",
        ":return: it",
    ]
    assert (lines, prefixes) == (expected, ["outer_mod", "outer_mod"])
