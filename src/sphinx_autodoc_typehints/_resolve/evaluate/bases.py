"""Evaluates the annotations of each base of a class in the globals of its own module, as `get_type_hints` does."""

from __future__ import annotations

from inspect import get_annotations
from typing import TYPE_CHECKING, get_type_hints

from ..guards import annotation_globals

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from sphinx_autodoc_typehints._types import Annotation, Documented


def hints_of_bases(
    cls: type,
    globalns: dict[str, Documented] | None,
    localns: Mapping[str, Documented] | None,
    evaluate: Callable[[type, dict[str, Documented], Mapping[str, Documented]], dict[str, Annotation]],
) -> dict[str, Annotation]:
    """Evaluate the annotations of each base as `typing.get_type_hints` would, in the globals of its module."""
    hints: dict[str, Annotation] = {}
    for base, base_globals, base_locals in base_scopes(cls, globalns, localns):
        hints |= evaluate(base, base_globals, base_locals)
    return hints


def base_scopes(
    cls: type, globalns: dict[str, Documented] | None, localns: Mapping[str, Documented] | None
) -> Iterator[tuple[type, dict[str, Documented], Mapping[str, Documented]]]:
    """Yield each base of `cls`, `object` first, with the namespaces get_type_hints evaluates it in."""
    for base in reversed(cls.__mro__):
        base_globals = annotation_globals(base) if globalns is None else globalns
        base_locals = dict(vars(base)) if localns is None else localns
        if localns is None and globalns is None:
            # as get_type_hints does, so the names of the module come before those of the class body
            base_globals, base_locals = base_locals, base_globals
        yield base, dict(base_globals), base_locals


def declared_hints(
    base: type, globalns: dict[str, Documented], localns: Mapping[str, Documented]
) -> dict[str, Annotation]:
    """Return the type hints of the annotations `base` declares itself, leaving out those of its own bases."""
    # a class holding only what the base declares, as get_type_hints evaluates the annotations of every base it holds
    declared = type(
        base.__name__,
        (),
        {"__annotations__": get_annotations(base), "__type_params__": getattr(base, "__type_params__", ())},
    )
    return get_type_hints(declared, globalns, localns, include_extras=True)


__all__ = [
    "base_scopes",
    "declared_hints",
    "hints_of_bases",
]
