"""Types the overloads of a documented callable, each in the scope of its own type parameters."""

from __future__ import annotations

from inspect import Parameter, Signature, signature
from typing import TYPE_CHECKING, Final, get_overloads

from .._objects import alias_lookup_names, declared_signature, prefix_of, unwrapped
from .._render import annotation_state, render_context
from .._resolve import (
    annotation_globals,
    declared_type_params,
    guarded_names,
    resolve_string_annotations,
    specialize,
    type_alias_namespace,
    written_type_alias,
)
from .hints import as_written

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from sphinx.application import Sphinx

    from .._refs import WrittenTypeAlias
    from .._types import Annotation, Hint, TypeParam


OVERLOADED_KINDS: Final[frozenset[str]] = frozenset({"function", "method", "class", "exception"})


def typed_overloads(
    app: Sphinx,
    name: str,
    obj: Callable[..., object],
    overloads: list[Signature],
    skip: int,
    arguments: dict[TypeParam, Annotation],
) -> Iterator[tuple[list[Parameter], dict[str, Hint | WrittenTypeAlias]]]:
    """
    Yield the parameters of each overload past `skip` and their types, rendered as its type parameters declare.

    Parsed from the source, the annotations are strings until evaluated in the function's module, where the aliases the
    parameters resolve to and the PEP 695 type parameters of the overload, the function and its class are no globals.
    """
    # typing holds the functions defining the overloads only while its registry does, which clear_overloads empties,
    # and misses those a TYPE_CHECKING block keeps from running, so a count differing from the source gives None each
    if len(functions := get_overloads(obj)) != len(overloads):
        defining: list[Callable[..., object] | None] = [None] * len(overloads)
    else:
        # a staticmethod or classmethod overload registers the descriptor
        defining = [unwrapped(function) for function in functions]
    aliases = type_alias_namespace(app.config["autodoc_type_aliases"], obj, prefix_of(name), app.env)[0]
    guarded = guarded_names(obj)
    scope = aliases | {param.__name__: param for param in declared_type_params(None, obj, None)}
    namespace = annotation_globals(obj)
    declared = render_context(app.config).declared_type_params
    # a decorator stating `__signature__` may hide parameters it supplies, which the overloads parsed from the source
    # of the function it wraps still list
    hidden = (
        frozenset(signature(wrapped).parameters) - frozenset(stated.parameters)
        if (stated := declared_signature(obj)) is not None and (wrapped := unwrapped(obj)) is not None
        else frozenset()
    )
    for overload, function in zip(overloads, defining, strict=True):
        own = declared_type_params(function, None, None)
        parameters = [param for param in list(overload.parameters.values())[skip:] if param.name not in hidden]
        written = {param.name: param.annotation for param in parameters} | {"return": overload.return_annotation}
        hints = resolve_string_annotations(obj, written, scope | {param.__name__: param for param in own})
        written_aliases = {
            key: written_type_alias(source, hints[key], namespace)
            for key, source in written.items()
            if isinstance(source, str)
            and (source not in guarded or alias_lookup_names(prefix_of(name), source, guarded=guarded))
        }
        with annotation_state(app.config, declared_type_params=declared | own):
            yield (
                parameters,
                {key: as_written(specialize(hint, arguments), written_aliases.get(key)) for key, hint in hints.items()},
            )


__all__ = [
    "OVERLOADED_KINDS",
    "typed_overloads",
]
