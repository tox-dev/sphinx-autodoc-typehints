"""Resolves the parameter and return types of a documented callable, with the aliases that name them."""

from __future__ import annotations

from dataclasses import dataclass
from inspect import isclass, isfunction
from typing import TYPE_CHECKING

from .._objects import constructor_name, declared_signature, documented_owner, prefix_of
from .._resolve import (
    bound_type_args,
    declared_type_params,
    get_all_type_hints,
    resolve_string_annotations,
    specialize,
    type_alias_namespace,
)
from .._types import frozendict

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx.application import Sphinx

    from .._objects import QualifiedCallable
    from .._refs import WrittenTypeAlias
    from .._render import TypeParamScope
    from .._types import Documented, Hint


def resolved_type_hints(
    app: Sphinx, name: str, original_obj: Documented, obj: QualifiedCallable, annotated: QualifiedCallable
) -> ResolvedHints:
    """
    Return the types of the parameters and return of `obj`, the aliases naming them, and what renders them.

    The types stay what the annotations evaluate to, as what reads them (the `Doc` of an `Annotated`, a generator's
    return, a type parameter a subclass binds) looks through an alias; only rendering names the alias.
    """
    localns, written_as = type_alias_namespace(app.config["autodoc_type_aliases"], annotated, prefix_of(name), app.env)
    documenting, attribute = documenting_class(name, original_obj)
    # namedtuple builds __new__ without builtins, so forward references resolve only via the class (#657), which a
    # `__new__` documented on its own reaches through its name (#992)
    namedtuple_new = isclass(documenting) and isfunction(obj) and obj.__module__.startswith("namedtuple_")
    owner = documenting if namedtuple_new else annotated
    type_hints = get_all_type_hints(
        app.config.autodoc_mock_imports, owner, name, localns, use_type_comments=app.config.autodoc_use_type_comments
    )
    if (stated_signature := declared_signature(original_obj)) is not None:
        # the parameters it lists, such as a pydantic model's fields, may be ones no annotation of the constructor names
        stated = {key: param.annotation for key, param in stated_signature.parameters.items()}
        # a decorator building it with `inspect.signature` under `from __future__ import annotations` copies strings
        type_hints |= {
            key: annotation
            for key, annotation in resolve_string_annotations(
                annotated, stated | {"return": stated_signature.return_annotation}, localns
            ).items()
            if annotation is not stated_signature.empty
        }
    if arguments := bound_type_args(documenting, attribute):
        type_hints = {key: specialize(hint, arguments) for key, hint in type_hints.items()}
    return ResolvedHints(
        types=frozendict(type_hints),
        written_as=frozendict(written_as),
        scope={"declared_type_params": declared_type_params(original_obj, obj, documenting)},
    )


def documenting_class(name: str, documented: Documented) -> tuple[Documented, str]:
    """
    Return the class documenting an object and the attribute naming the object in it.

    A class documents its constructor, and the class listing a member documents it, which may be a subclass binding
    the type parameters of the base it inherits the member from.
    """
    if isclass(documented):
        return documented, constructor_name(documented)
    return documented_owner(name)


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedHints:
    types: Mapping[str, Hint]
    written_as: Mapping[str, WrittenTypeAlias]
    scope: TypeParamScope


def as_written[Hinted](hint: Hinted, written: WrittenTypeAlias | None) -> Hinted | WrittenTypeAlias:
    """Return the alias `written` in place of `hint` while it holds `hint`, which a subclass binding changes."""
    return written if written is not None and written.value is hint else hint


__all__ = [
    "ResolvedHints",
    "as_written",
    "documenting_class",
    "resolved_type_hints",
]
