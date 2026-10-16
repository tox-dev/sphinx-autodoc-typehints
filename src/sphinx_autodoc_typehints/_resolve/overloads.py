"""The `typing.overload` signatures the source of a module declares, which `_patches` records during analysis."""

from __future__ import annotations

__lazy_modules__ = ["contextlib", "sphinx", "sphinx.errors", "sphinx.pycode"]

from contextlib import suppress
from typing import TYPE_CHECKING, Final

from sphinx.errors import PycodeError
from sphinx.pycode import ModuleAnalyzer

if TYPE_CHECKING:
    from collections.abc import Callable
    from inspect import Signature


OVERLOADS: Final[dict[str, dict[str, list[Signature]]]] = {}


def resolve_overloads(obj: Callable[..., object]) -> list[Signature] | None:
    """Return the overloads the source of the module of `obj` declares for it, `None` when it declares none."""
    if not (module_name := getattr(obj, "__module__", None)) or not (qualname := getattr(obj, "__qualname__", None)):
        return None
    # the analysis fills the cache, and autodoc runs it only after it emits autodoc-process-signature
    if module_name not in OVERLOADS:
        with suppress(PycodeError):
            ModuleAnalyzer.for_module(module_name).analyze()
    return OVERLOADS.get(module_name, {}).get(qualname) or None


__all__ = [
    "OVERLOADS",
    "resolve_overloads",
]
