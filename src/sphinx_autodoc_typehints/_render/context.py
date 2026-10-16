"""
The render context a documented object keeps on the config while its types render.

The protocols that plug into rendering live here too.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final, Protocol, TypedDict, Unpack

if TYPE_CHECKING:
    from collections.abc import Generator
    from contextlib import AbstractContextManager
    from types import ModuleType

    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment

    from sphinx_autodoc_typehints._types import RenderNode, TypeParam


_ATTRIBUTE: Final[str] = "_typehints_render_context"


@contextmanager
def annotation_state(config: Config, **changes: Unpack[RenderChanges]) -> Generator[None, None, None]:
    """
    Publish the state format_annotation reads off the config, restoring what was there.

    Documenting an object can re-enter this handler for another one, and deleting the attributes on the way out of the
    inner call then broke the outer call's teardown (#750).
    """
    had = hasattr(config, _ATTRIBUTE)
    previous = getattr(config, _ATTRIBUTE, None)
    setattr(config, _ATTRIBUTE, replace(render_context(config), **changes))
    try:
        yield
    finally:
        if had:
            setattr(config, _ATTRIBUTE, previous)
        else:
            delattr(config, _ATTRIBUTE)


def render_context(config: Config) -> RenderContext:
    """Outside any documented object, return the defaults."""
    return getattr(config, _ATTRIBUTE, None) or RenderContext()


@dataclass(frozen=True, slots=True)
class RenderContext:
    """Kept on the config, as a `typehints_formatter` may format a nested type with it, which must render the same."""

    env: BuildEnvironment | None = None
    #: the dotted path of the documented object, the scopes its aliases resolve in
    module_prefix: str = ""
    #: whether the text goes into a signature, which the Python domain parses and links itself
    signature: bool = False
    #: the type parameters the signature lists, with their bounds, constraints and defaults
    declared_type_params: frozenset[TypeParam] = frozenset()
    #: how to bind the guarded names of a module, which resolution owns and rendering cannot import
    guard_bound: GuardBinder | None = None


class TypeParamScope(TypedDict, total=False):
    declared_type_params: frozenset[TypeParam]


class ScopeExtras(TypeParamScope, total=False):
    signature: bool


class RenderChanges(ScopeExtras, total=False):
    env: BuildEnvironment | None
    module_prefix: str
    guard_bound: GuardBinder | None


class GuardBinder(Protocol):
    def __call__(self, module: ModuleType | None, /) -> AbstractContextManager[None]: ...


class FixupModuleName(Protocol):
    """The `typehints_fixup_module_name` option, which returns the module name the docs use for `module`."""

    def __call__(self, module: str, /) -> str: ...


class TypehintsFormatter(Protocol):
    """
    The `typehints_formatter` option, which renders `annotation` as reST or returns `None` for the default.

    It may call the extension's formatting again with `config`, which then renders in the same context.
    """

    def __call__(self, annotation: RenderNode, config: Config, /) -> str | None: ...


__all__ = [
    "FixupModuleName",
    "RenderContext",
    "ScopeExtras",
    "TypeParamScope",
    "TypehintsFormatter",
    "annotation_state",
    "render_context",
]
