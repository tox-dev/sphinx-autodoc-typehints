"""Opens the render scope of one documented object, with its module, its aliases and how a guard runs."""

from __future__ import annotations

__lazy_modules__ = ["functools", "sphinx_autodoc_typehints._resolve"]

from functools import partial
from typing import TYPE_CHECKING, Unpack

from sphinx_autodoc_typehints._render import annotation_state
from sphinx_autodoc_typehints._resolve import guard_bound

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from sphinx.application import Sphinx

    from sphinx_autodoc_typehints._render import ScopeExtras


def render_scope(app: Sphinx, module_prefix: str, **extra: Unpack[ScopeExtras]) -> AbstractContextManager[None]:
    """Publish where the types render, what aliases they may link and how a guard runs, for the block's duration."""
    return annotation_state(
        app.config,
        env=app.env,
        module_prefix=module_prefix,
        guard_bound=partial(guard_bound, app.config.autodoc_mock_imports),
        **extra,
    )


__all__ = [
    "render_scope",
]
