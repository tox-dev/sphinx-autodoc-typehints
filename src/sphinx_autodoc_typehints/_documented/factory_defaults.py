"""Shows the factory call, such as `list()`, as the default of a dataclass or attrs field."""

from __future__ import annotations

__lazy_modules__ = ["dataclasses", "sphinx_autodoc_typehints._objects", "sphinx_autodoc_typehints._private_imports"]

from dataclasses import MISSING, fields, is_dataclass
from typing import TYPE_CHECKING

from sphinx_autodoc_typehints._objects import is_attrs_class
from sphinx_autodoc_typehints._private_imports import HAS_DEFAULT_FACTORY

if TYPE_CHECKING:
    from collections.abc import Callable
    from inspect import Signature


def show_factory_defaults(cls: type, signature: Signature) -> Signature:
    """Replace the placeholder default of each dataclass or attrs field built by a factory with the factory's call."""
    calls: dict[str, tuple[object, str]] = {}
    if is_dataclass(cls):
        for field in fields(cls):
            if field.default_factory is not MISSING:
                calls[field.name] = HAS_DEFAULT_FACTORY, _call_text(field.default_factory, takes_self=False)
    if is_attrs_class(cls):
        from attrs import (  # ruff:ignore[import-outside-top-level]  # optional, and installed for any class it made
            NOTHING,
            Factory,
        )
        from attrs import fields as attrs_fields  # ruff:ignore[import-outside-top-level]  # optional, as above

        for attribute in attrs_fields(cls):
            factory = attribute.default
            if isinstance(factory, Factory):  # ty: ignore[invalid-argument-type]  # attrs types it as a function
                calls[attribute.alias] = NOTHING, _call_text(factory.factory, takes_self=factory.takes_self)
    return signature.replace(
        parameters=[
            param.replace(default=_FactoryCall(found[1]))
            if (found := calls.get(param.name)) and param.default is found[0]
            else param
            for param in signature.parameters.values()
        ]
    )


def _call_text(factory: Callable[..., object], *, takes_self: bool) -> str:
    # a lambda or a function local to another has no name the reader could look up, and its source may not be
    # recoverable, so it keeps the placeholder autodoc shows for a dataclass field
    if "<" in (name := getattr(factory, "__qualname__", "<")):
        return "<factory>"
    return f"{name}(self)" if takes_self else f"{name}()"


# Sphinx describes a default by its repr, in the signature and the parameter fields alike
class _FactoryCall:
    def __init__(self, text: str) -> None:
        self._text = text

    def __repr__(self) -> str:
        return self._text


__all__ = [
    "show_factory_defaults",
]
