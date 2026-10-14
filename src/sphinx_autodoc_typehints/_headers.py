"""Rendering the type in the header of data, an attribute or a property the way the extension renders types."""

from __future__ import annotations

import inspect
import sys
from functools import cached_property, partial
from typing import TYPE_CHECKING, Any, Final, cast

from sphinx import addnodes
from sphinx.domains.python._annotations import _parse_annotation  # ruff:ignore[import-private-name]  # no public parser
from sphinx.util import logging

from ._annotations import annotation_state, format_annotation, signature_text
from ._resolver import documented_type_names, resolve_annotations, resolve_type_guarded_imports, type_alias_namespace
from ._type_params import bound_type_args, specialize
from ._typed_dict import typed_dict_keys

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment

_DOCUMENTED: Final = "sphinx_autodoc_typehints_documented"
_MISSING: Final = object()
#: The hints resolved per owner while one document is read, keyed by that document; resolving an owner evaluates every
#: annotation it holds, which a module of many documented globals would otherwise repeat for each of their headers.
_RESOLVED: Final[dict[object, dict[tuple[str, frozenset[str]], dict[str, Any]]]] = {}


def note_documented(env: BuildEnvironment, name: str) -> None:
    """Remember that autodoc documents ``name`` on the page being read, so its header is the extension's to render."""
    cast("set[str]", env.temp_data.setdefault(_DOCUMENTED, set())).add(name)


def render_header_types(app: Sphinx, domain: str, objtype: str, contentnode: addnodes.desc_content) -> None:
    """
    Render the type after the name of data, an attribute or a property as the extension renders any type.

    autodoc evaluates that annotation itself, before any event lets the extension bind the names a module imports only
    for type checking, so they resolved only when documenting something else had bound them first. A header written
    by hand, rather than by autodoc, keeps its type.
    """
    if domain != "py" or objtype not in {"data", "attribute", "property"}:
        return
    documented = app.env.temp_data.get(_DOCUMENTED) or frozenset()
    for signode in cast("addnodes.desc", contentnode.parent).children:
        if (
            isinstance(signode, addnodes.desc_signature)
            and (typed := _type_annotation(signode)) is not None
            and (name := f"{signode.get('module')}.{signode.get('fullname')}") in documented
            and (hint := _hint(app, signode, objtype, name)) is not _MISSING
        ):
            with annotation_state(
                app.config,
                _typehints_env=app.env,
                _typehints_module_prefix=name.rpartition(".")[0],
                _typehints_resolve_guarded_imports=partial(
                    resolve_type_guarded_imports, app.config.autodoc_mock_imports
                ),
                _typehints_signature=True,
            ):
                short_literals = app.config.python_display_short_literal_types
                text = signature_text(format_annotation(hint, app.config, short_literals=short_literals))
            # the children after the ": " separator are the type
            del typed[2:]
            typed.extend(_parse_annotation(text, app.env))


def _type_annotation(signode: addnodes.desc_signature) -> addnodes.desc_annotation | None:
    """Return the node holding ``: type``, absent when ``autodoc_typehints = "none"`` hides it."""
    return next(
        (
            node
            for node in signode
            if isinstance(node, addnodes.desc_annotation) and node.children and node[0].astext() == ":"
        ),
        None,
    )


def _hint(app: Sphinx, signode: addnodes.desc_signature, objtype: str, name: str) -> Any:
    owner: Any = sys.modules.get(signode.get("module") or "")
    *path, attribute = signode.get("fullname", "").split(".")
    for part in path:
        owner = getattr(owner, part, None)
    # the header's own resolution reports nothing, the docstring of the same object warns about what fails there
    with logging.suppress_logging():
        hint = _declared_hint(app, owner, attribute, objtype, name)
    # a member inherited from a generic base reads the arguments the documenting class gives its type parameters
    return specialize(hint, arguments) if (arguments := bound_type_args(owner, attribute)) else hint


def _declared_hint(app: Sphinx, owner: Any, attribute: str, objtype: str, name: str) -> Any:
    if objtype == "property":
        # a class property is a classmethod wrapping the property
        member = getattr(member := inspect.getattr_static(owner, attribute), "__func__", member)
        getter = member.func if isinstance(member, cached_property) else member.fget
        return _resolved_hints(app, getter, name).get("return", _MISSING)
    return _owner_hints(app, owner, name).get(attribute, _MISSING)


def _owner_hints(app: Sphinx, owner: Any, name: str) -> dict[str, Any]:
    # the document being read is a new object each time, so neither an earlier document nor an earlier build matches
    if (resolved := _RESOLVED.get(document := app.env.current_document)) is None:
        _RESOLVED.clear()
        resolved = _RESOLVED[document] = {}
    # an alias documented further down the page changes what the owner's annotations resolve to
    key = name.rpartition(".")[0], documented_type_names(app.env)
    if (hints := resolved.get(key)) is None:
        hints = resolved[key] = _resolved_hints(app, owner, name)
    return hints


def _resolved_hints(app: Sphinx, annotated: Any, name: str) -> dict[str, Any]:
    """Resolve the annotations of ``annotated`` as the fields and signature of the same build do, aliases included."""
    localns, written_aliases = type_alias_namespace(
        app.config.autodoc_type_aliases, annotated, name.rpartition(".")[0], app.env
    )
    # a TypedDict key also shows whether a caller may leave it out
    if keys := typed_dict_keys(annotated, localns):
        return keys
    return resolve_annotations(app.config.autodoc_mock_imports, annotated, name, localns) | written_aliases


__all__ = ["note_documented", "render_header_types"]
