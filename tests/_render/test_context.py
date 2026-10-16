from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark, raises

from sphinx_autodoc_typehints._render import annotation_state, render_context
from sphinx_autodoc_typehints._render.context import RenderContext

if TYPE_CHECKING:
    from conftest import BuildText
    from sphinx.config import Config


def test_render_context_outside_a_block(config: Config) -> None:
    assert render_context(config) == RenderContext()


def test_annotation_state_publishes_its_changes(config: Config) -> None:
    with annotation_state(config, module_prefix="pkg.mod", signature=True):
        assert render_context(config) == RenderContext(module_prefix="pkg.mod", signature=True)


def test_annotation_state_nested_keeps_the_outer_changes(config: Config) -> None:
    with annotation_state(config, module_prefix="pkg.mod"), annotation_state(config, signature=True):
        assert render_context(config) == RenderContext(module_prefix="pkg.mod", signature=True)


def test_annotation_state_nested_restores_the_outer_context(config: Config) -> None:
    with annotation_state(config, module_prefix="pkg.mod"):
        with annotation_state(config, module_prefix="pkg.other", signature=True):
            pass
        assert render_context(config) == RenderContext(module_prefix="pkg.mod")


def test_annotation_state_restores_the_default_on_exit(config: Config) -> None:
    with annotation_state(config, module_prefix="pkg.mod"):
        pass
    assert render_context(config) == RenderContext()


def test_annotation_state_restores_the_default_on_error(config: Config) -> None:
    with raises(LookupError), annotation_state(config, module_prefix="pkg.mod"):
        raise LookupError
    assert render_context(config) == RenderContext()


# regression test for #750
@mark.sphinx("text", testroot="reentrant-formatter", exception_on_warning=True)
def test_render_context_survives_a_formatter_documenting_another_object(build_text: BuildText) -> None:
    assert (build_text(".. autofunction:: demo_reentrant.outer")) == (
        dedent("""\
            demo_reentrant.outer(flag)

               Outer.

               Parameters:
                  **flag** ("bool") -- the flag

               Return type:
                  "bool"

               Returns:
                  it
        """)
    )
