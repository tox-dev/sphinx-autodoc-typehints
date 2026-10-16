"""Renders the type in the header of data, an attribute or a property."""

from __future__ import annotations

from inspect import getattr_static
from typing import TYPE_CHECKING, Final

from sphinx import addnodes
from sphinx.util.inspect import safe_getattr

from sphinx_autodoc_typehints._documented import render_scope
from sphinx_autodoc_typehints._objects import object_at, prefix_of, property_getter
from sphinx_autodoc_typehints._private_imports import parse_annotation, suppress_logging
from sphinx_autodoc_typehints._refs import WrittenTypeAlias
from sphinx_autodoc_typehints._render import as_signature_type
from sphinx_autodoc_typehints._resolve import (
    bound_type_args,
    resolve_annotations,
    specialize,
    type_alias_namespace,
    typed_dict_keys,
)
from sphinx_autodoc_typehints._state import note_type_documented, types_documented
from sphinx_autodoc_typehints._types import sentinel

from .lookup import documented_signatures

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx.application import Sphinx
    from sphinx.environment import _CurrentDocument

    from sphinx_autodoc_typehints._types import Documented, Hint


# The hints resolved per owner while one document is read, keyed by that document; resolving an owner evaluates every
# annotation it holds, which a module of many documented globals would otherwise repeat for each of their headers.
_RESOLVED: Final[dict[_CurrentDocument, dict[tuple[str, int], Mapping[str, Hint | WrittenTypeAlias]]]] = {}


def render_header_types(app: Sphinx, domain: str, objtype: str, contentnode: addnodes.desc_content) -> None:
    """
    Render the type after the name of data, an attribute or a property as the extension renders any type.

    autodoc evaluates that annotation itself, before any event lets the extension bind the names a module imports only
    for type checking, so they resolved only when documenting something else had bound them first. A header written
    by hand, rather than by autodoc, keeps its type.
    """
    if domain != "py":
        return
    if objtype == "type":
        # an alias documented further down the page changes what the annotations of the headers after it resolve to
        note_type_documented(app.env)
        return
    if objtype not in {"data", "attribute", "property"}:
        return
    for signode, module, fullname in documented_signatures(app.env, contentnode):
        if (
            # autodoc_typehints = "none" writes no node holding the type
            (
                typed := next(
                    (
                        node
                        for node in signode
                        if isinstance(node, addnodes.desc_annotation) and node.children and node[0].astext() == ":"
                    ),
                    None,
                )
            )
            is not None
            and (hint := _hint(app, module, fullname, objtype)) is not _MISSING
        ):
            with render_scope(app, prefix_of(f"{module}.{fullname}"), signature=True):
                text = as_signature_type(hint, app.config, kind="attribute")
            # a type a formatter hides takes its ": " separator along, leaving `attr = 1`
            if not text:
                signode.remove(typed)
                continue
            # the children after the ": " separator are the type
            del typed[2:]
            typed.extend(parse_annotation(text, app.env))
            # Sphinx marks each parsed name `refspecific`, which also matches any documented name ending in it, so
            # `type` linked to an attribute `Event.type`; the fields of the same entry look their names up exactly
            for xref in typed.findall(addnodes.pending_xref):
                del xref["refspecific"]


def _hint(app: Sphinx, module: str, fullname: str, objtype: str) -> Hint | WrittenTypeAlias | _MISSING:
    *path, attribute = fullname.split(".")
    owner = object_at(module, path)
    name = f"{module}.{fullname}"
    # the header's own resolution reports nothing, the docstring of the same object warns about what fails there
    with suppress_logging():
        if objtype == "property":
            # a class property is a classmethod wrapping the property, which Python before 3.13 runs on class access
            if isinstance(static := getattr_static(owner, attribute, None), classmethod):
                member = static.__func__
            else:
                # a descriptor may hand out the property only on class access
                member = safe_getattr(owner, attribute, None)
            hint = (
                _MISSING
                if (getter := property_getter(member)) is None
                else _resolved_hints(app, getter, name).get("return", _MISSING)
            )
        else:
            # the document being read is a new object each time, so neither an earlier document nor build matches
            if (resolved := _RESOLVED.get(document := app.env.current_document)) is None:
                _RESOLVED.clear()
                resolved = _RESOLVED[document] = {}
            # the aliases documented on other pages stay fixed while this one is read, so counting this page's will do
            key = prefix_of(name), types_documented(app.env)
            if (hints := resolved.get(key)) is None:
                hints = resolved[key] = _resolved_hints(app, owner, name)
            hint = hints.get(attribute, _MISSING)
    # a member inherited from a generic base reads the arguments the documenting class gives its type parameters
    if not (arguments := bound_type_args(owner, attribute)) or hint is _MISSING or isinstance(hint, WrittenTypeAlias):
        return hint
    return specialize(hint, arguments)


# no `Final`: ty stops reading an annotated sentinel as a type https://github.com/astral-sh/ty/issues/4737
_MISSING = sentinel("_MISSING")


def _resolved_hints(app: Sphinx, annotated: Documented, name: str) -> Mapping[str, Hint | WrittenTypeAlias]:
    localns, written_aliases = type_alias_namespace(
        app.config.autodoc_type_aliases, annotated, prefix_of(name), app.env
    )
    # a TypedDict field also shows whether a caller may leave it out
    if keys := typed_dict_keys(annotated, localns):
        return keys
    return resolve_annotations(app.config.autodoc_mock_imports, annotated, name, localns) | written_aliases


__all__ = [
    "render_header_types",
]
