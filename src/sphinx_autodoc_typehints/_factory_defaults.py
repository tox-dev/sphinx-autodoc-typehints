"""Show a default that a factory builds on each call as that call, rather than the placeholder standing in for it."""

from __future__ import annotations

import dataclasses

# the default a generated __init__ gives a field with a default_factory, which typeshed leaves out
from dataclasses import _HAS_DEFAULT_FACTORY  # ruff:ignore[import-private-name]  # ty: ignore[unresolved-import]
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import inspect
    from collections.abc import Callable, Iterator


def show_factory_defaults(cls: type, signature: inspect.Signature) -> inspect.Signature:
    """Replace the placeholder default of each dataclass or attrs field built by a factory with the factory's call."""
    calls = {name: (placeholder, call) for name, placeholder, call in _factory_calls(cls)}
    return signature.replace(
        parameters=[
            param.replace(default=_FactoryCall(found[1]))
            if (found := calls.get(param.name)) and param.default is found[0]
            else param
            for param in signature.parameters.values()
        ]
    )


def _factory_calls(cls: type) -> Iterator[tuple[str, object, str]]:
    if dataclasses.is_dataclass(cls):
        for field in dataclasses.fields(cls):
            if field.default_factory is not dataclasses.MISSING:
                yield field.name, _HAS_DEFAULT_FACTORY, _call_text(field.default_factory, takes_self=False)
    if not hasattr(cls, "__attrs_attrs__"):
        return
    import attrs  # ruff:ignore[import-outside-top-level]  # optional, and installed for any class it made

    for attribute in attrs.fields(cls):
        # attrs types Factory as a function, though it is the class its instances are made from
        if isinstance(factory := attribute.default, attrs.Factory):  # ty: ignore[invalid-argument-type]
            yield attribute.alias, attrs.NOTHING, _call_text(factory.factory, takes_self=factory.takes_self)


def _call_text(factory: Callable[..., Any], *, takes_self: bool) -> str:
    # a lambda or a function local to another has no name the reader could look up, and its source is not reliably
    # recoverable, so it keeps the placeholder autodoc shows for a dataclass field
    if "<" in (name := getattr(factory, "__qualname__", "<")):
        return "<factory>"
    return f"{name}(self)" if takes_self else f"{name}()"


class _FactoryCall:
    """A default Sphinx describes by its repr, as both the signature and the parameter fields do."""

    def __init__(self, text: str) -> None:
        self._text = text

    def __repr__(self) -> str:
        return self._text


__all__ = ["show_factory_defaults"]
