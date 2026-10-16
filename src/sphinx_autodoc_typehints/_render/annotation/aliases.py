"""PEP 695 aliases in rendered types, whether one recurses or evaluates, and how a reference names it."""

from __future__ import annotations

from inspect import getmodule
from sys import modules
from types import ModuleType
from typing import TYPE_CHECKING, TypeAliasType, get_args, get_origin

from sphinx_autodoc_typehints._objects import enclosing_scopes

from ..context import render_context
from .names import fixup_module_name, name_prefix

if TYPE_CHECKING:
    from sphinx.config import Config

    from sphinx_autodoc_typehints._types import RenderNode, TypeParam


def reaches_itself(alias: TypeAliasType) -> bool:
    """
    Return whether the value of `alias`, or of an alias it names on the way, leads back to `alias`.

    Only such an alias can recurse; one that nests in its own arguments, as `Pair[Pair[int]]`, expands fully. An alias
    whose value does not evaluate yet counts as recursive, so the walk does not expand its value.
    """
    seen: set[int] = set()
    pending: list[RenderNode] = [alias]
    while pending:
        if (inner := underlying_type_alias(node := pending.pop())) is not None:
            if (inner is alias and seen) or not _alias_value_evaluates(inner):
                return True
            if id(inner) not in seen:
                seen.add(id(inner))
                pending.append(inner.__value__)
        pending.extend(get_args(node))
    return False


def underlying_type_alias(annotation: RenderNode) -> TypeAliasType | None:
    """Return the PEP 695 alias an annotation is, or the one a subscripted alias parametrizes."""
    if isinstance(annotation, TypeAliasType):
        return annotation
    if isinstance(origin := get_origin(annotation), TypeAliasType):
        return origin
    return None


def _alias_value_evaluates(alias: TypeAliasType) -> bool:
    try:
        _ = alias.__value__
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return False
    return True


def alias_crossref(annotation: TypeAliasType, config: Config) -> str | None:
    """
    Render a PEP 695 type alias as a cross-reference, or `None` when it is not a known target yet.

    A `T` documented where the module Sphinx builds re-exports it wins over a same-named alias that module does not
    bind. An alias imported from elsewhere resolves through its canonical module, and one owned by a different
    top-level package falls back to an intersphinx-style reference. Only a document already read can answer, so the
    caller defers the choice to the resolve phase on `None`.
    """
    context = render_context(config)
    if (env := context.env) is None:
        return None
    canonical = _get_canonical_type_alias_name(annotation)
    candidates = [
        *(
            f"{module}.{annotation.__name__}"
            for module in enclosing_scopes(context.module_prefix)
            if getattr(modules.get(module), annotation.__name__, None) is annotation
        ),
        *([canonical] if canonical else []),
        annotation.__name__,
    ]
    prefix = name_prefix(config)
    for candidate in candidates:
        if (obj := env.domains.python_domain.objects.get(candidate)) is not None and obj.objtype == "type":
            return f":py:type:`{prefix}{candidate}`"
    if canonical and canonical.split(".")[0] != context.module_prefix.split(".")[0]:
        return f":py:obj:`{prefix}{fixup_module_name(config, canonical.rpartition('.')[0])}.{annotation.__name__}`"
    return None


# an alias a private module defines, such as numpy._typing.ArrayLike, takes the name of a public module re-exporting
# it, such as numpy.typing.ArrayLike
def _get_canonical_type_alias_name(annotation: TypeAliasType) -> str:
    if not (module := annotation.__module__):
        return ""
    name = annotation.__name__
    if not any(part.startswith("_") for part in module.split(".")):
        return f"{module}.{name}"
    top_pkg = module.split(".")[0]
    return next(
        (
            f"{mod_name}.{name}"
            for mod_name in sorted(modules)
            if mod_name.startswith(top_pkg)
            and isinstance(mod := modules[mod_name], ModuleType)
            and not any(part.startswith("_") for part in mod_name.split("."))
            and getattr(mod, name, None) is annotation
        ),
        f"{module}.{name}",
    )


def alias_name_reference(alias: TypeAliasType, config: Config) -> str:
    """
    Render an alias as a cross-reference to its own name, without expanding its value.

    A cross-module alias may live in a module Sphinx has not read yet, leaving it out of the py domain. Its canonical
    qualified name resolves in the later xref phase and renders the same short form when nothing documents the alias.
    """
    return f":py:type:`{name_prefix(config)}{_get_canonical_type_alias_name(alias) or alias.__name__}`"


def can_expand_alias(alias: TypeAliasType, config: Config) -> bool:
    """
    Return whether the value of `alias`, which Python evaluates on first access, evaluates now.

    A module reached only through an annotation has not had its `if TYPE_CHECKING` block executed, so the names the
    value uses can still be missing; run that block before giving up, so what we render does not depend on the order
    Sphinx reads modules in (#764).
    """
    if _alias_evaluates(alias):
        return True
    if (guard_bound := render_context(config).guard_bound) is None:
        return False
    # they evaluate in the globals of the module, which hold what the block binds only while they evaluate
    with guard_bound(getmodule(alias)):
        return _alias_evaluates(alias)


def _alias_evaluates(alias: TypeAliasType) -> bool:
    return _alias_value_evaluates(alias) and all(map(_type_param_evaluates, alias.__type_params__))


def _type_param_evaluates(param: TypeParam) -> bool:
    try:
        _ = [getattr(param, f"__{kind}__", None) for kind in ("bound", "constraints", "default")]
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return False
    return True


__all__ = [
    "alias_crossref",
    "alias_name_reference",
    "can_expand_alias",
    "reaches_itself",
    "underlying_type_alias",
]
