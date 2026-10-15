"""
Patches to autodoc and the Python domain.

They capture overloads, write multi-line signatures, and evaluate annotations with what `TYPE_CHECKING` blocks bind.
"""

from __future__ import annotations

from functools import lru_cache, wraps
from typing import TYPE_CHECKING, Final

from sphinx.directives import ObjectDescription
from sphinx.ext.autodoc._dynamic import (  # ruff:ignore[import-private-name]  # where autodoc evaluates annotations
    _importer,
    _loader,
)
from sphinx.pycode import ModuleAnalyzer
from sphinx.util.typing import get_type_hints

from .._resolve import OVERLOADS, guarded_names_bound
from .._state import signature_lines

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .._types import Annotation, Documented


BUILDING: Final[set[int]] = set()


@lru_cache
def patch_overload_capture() -> None:
    """
    Keep the overloads the analyzer of a module finds, and hide them from autodoc.

    autodoc would show each as a signature of its own. Their types cannot link there, so the extension shows them in the
    docstring, or as the lines of one signature, instead.
    """
    original_analyze = ModuleAnalyzer.analyze

    @wraps(original_analyze)
    def patched_analyze(self: ModuleAnalyzer) -> None:
        original_analyze(self)
        if self.overloads:
            OVERLOADS[self.modname] = dict(self.overloads)
        # every app in the process shares the analyzer, so hide the overloads only while an app using us builds
        self.overloads = {} if BUILDING else dict(OVERLOADS.get(self.modname, {}))

    ModuleAnalyzer.analyze = patched_analyze  # ty: ignore[invalid-assignment]  # wraps returns a _Wrapped


@lru_cache
def patch_signature_lines() -> None:
    """
    Add the signature lines autodoc-process-signature cannot return to the directive autodoc writes.

    The event replaces only the first line, and a line break in it breaks the directive, while the Python domain
    parses each line of the directive into a signature of its own, linking only the first as the target.
    """
    # patched on the class defining it, so the Python domain's directives gain no member of their own
    original_get_signatures = ObjectDescription.get_signatures

    @wraps(original_get_signatures)
    def get_signatures(self: ObjectDescription[object]) -> list[str]:
        line = self.arguments[0]
        if signatures := signature_lines(self.env).pop(f"{self.options.get('module')}.{line}", None):
            name = line.removesuffix(signatures[0])
            self.arguments[0] = "\n".join(f"{name}{signature}" for signature in signatures)
        return original_get_signatures(self)

    ObjectDescription.get_signatures = get_signatures  # ty: ignore[invalid-assignment]  # wraps returns a _Wrapped


@lru_cache
def patch_autodoc_type_hints() -> None:
    """
    Have autodoc evaluate annotations with the names the `TYPE_CHECKING` blocks run so far bind.

    autodoc evaluates in the globals of the module, which hold those names only while it does, so it does not list them
    as members. Without them it misses an attribute only a base class annotates, and the type an attribute shows.
    """
    _importer.get_type_hints = _guarded_type_hints  # ty: ignore[invalid-assignment]  # wraps returns a _Wrapped
    _loader.get_type_hints = _guarded_type_hints  # ty: ignore[invalid-assignment]  # wraps returns a _Wrapped


@wraps(get_type_hints)
def _guarded_type_hints(
    obj: Documented,
    globalns: dict[str, object] | None = None,
    localns: Mapping[str, object] | None = None,
    # ruff:ignore[boolean-type-hint-positional-argument, boolean-default-value-positional-argument]  # as it replaces
    include_extras: bool = False,
) -> dict[str, Annotation]:
    with guarded_names_bound(obj):
        return get_type_hints(obj, globalns, localns, include_extras=include_extras)


__all__ = [
    "BUILDING",
    "patch_autodoc_type_hints",
    "patch_overload_capture",
    "patch_signature_lines",
]
