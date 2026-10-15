"""Rendering the type in the header of data, an attribute or a property the way the extension renders types."""

from __future__ import annotations

import ast
import inspect
from functools import cached_property, partial
from types import ModuleType
from typing import TYPE_CHECKING, Any, Final, cast, get_args, get_origin

from sphinx import addnodes
from sphinx.domains.python._annotations import _parse_annotation  # ruff:ignore[import-private-name]  # no public parser
from sphinx.errors import PycodeError
from sphinx.pycode import ModuleAnalyzer
from sphinx.util import logging
from sphinx.util.inspect import safe_getattr

from ._annotations import annotation_state, format_annotation, signature_text
from ._resolver import (
    is_documented,
    object_at,
    resolve_annotations,
    resolve_type_guarded_imports,
    type_alias_namespace,
    written_annotations,
)
from ._type_params import bound_type_args, specialize
from ._typed_dict import typed_dict_keys

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment

_TYPES_DOCUMENTED: Final = "sphinx_autodoc_typehints_types_documented"
_MISSING: Final = object()
#: The hints resolved per owner while one document is read, keyed by that document; resolving an owner evaluates every
#: annotation it holds, which a module of many documented globals would otherwise repeat for each of their headers.
_RESOLVED: Final[dict[object, dict[tuple[str, int], dict[str, Any]]]] = {}


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
        app.env.temp_data[_TYPES_DOCUMENTED] = _types_documented(app.env) + 1
        return
    if objtype not in {"data", "attribute", "property"}:
        return
    for signode in cast("addnodes.desc", contentnode.parent).children:
        if (
            isinstance(signode, addnodes.desc_signature)
            and (typed := _type_annotation(signode)) is not None
            and is_documented(app.env, name := f"{signode.get('module')}.{signode.get('fullname')}")
            and (text := _header_text(app, signode, objtype, name)) is not None
        ):
            # the children after the ": " separator are the type
            del typed[2:]
            typed.extend(_parse_annotation(text, app.env))


def _types_documented(env: BuildEnvironment) -> int:
    return cast("int", env.temp_data.get(_TYPES_DOCUMENTED, 0))


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


def _header_text(app: Sphinx, signode: addnodes.desc_signature, objtype: str, name: str) -> str | None:
    *path, attribute = signode.get("fullname", "").split(".")
    owner = object_at(signode.get("module"), path)
    # the header's own resolution reports nothing, the docstring of the same object warns about what fails there
    with logging.suppress_logging():
        hint = _declared_hint(app, owner, attribute, objtype, name)
    if hint is _MISSING:
        return None
    if (written := _written_when_arguments_drop(owner, attribute, objtype, hint)) is not None:
        return written
    # a member inherited from a generic base reads the arguments the documenting class gives its type parameters
    if arguments := bound_type_args(owner, attribute):
        hint = specialize(hint, arguments)
    with annotation_state(
        app.config,
        _typehints_env=app.env,
        _typehints_module_prefix=name.rpartition(".")[0],
        _typehints_resolve_guarded_imports=partial(resolve_type_guarded_imports, app.config.autodoc_mock_imports),
        _typehints_signature=True,
    ):
        short_literals = app.config.python_display_short_literal_types
        return signature_text(format_annotation(hint, app.config, short_literals=short_literals))


def _declared_hint(app: Sphinx, owner: Any, attribute: str, objtype: str, name: str) -> Any:
    if objtype == "property":
        if (getter := _property_getter(owner, attribute)) is None:
            return _MISSING
        return _resolved_hints(app, getter, name).get("return", _MISSING)
    return _owner_hints(app, owner, name).get(attribute, _MISSING)


def _property_getter(owner: Any, attribute: str) -> Any:
    """Find the getter of the property autodoc documents, reading the member the way autodoc reads it."""
    # a class property is a classmethod wrapping the property, which Python before 3.13 runs on class access
    if isinstance(static := inspect.getattr_static(owner, attribute, None), classmethod):
        member = static.__func__
    else:
        # a descriptor may hand out the property only on class access
        member = safe_getattr(owner, attribute, None)
    if isinstance(member, cached_property):
        return member.func
    return member.fget if isinstance(member, property) else None


def _owner_hints(app: Sphinx, owner: Any, name: str) -> dict[str, Any]:
    # the document being read is a new object each time, so neither an earlier document nor an earlier build matches
    if (resolved := _RESOLVED.get(document := app.env.current_document)) is None:
        _RESOLVED.clear()
        resolved = _RESOLVED[document] = {}
    # the aliases documented on other pages stay the same while this one is read, so counting this page's will do
    key = name.rpartition(".")[0], _types_documented(app.env)
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


def _written_when_arguments_drop(owner: Any, attribute: str, objtype: str, hint: Any) -> str | None:
    """
    Return the annotation as written when evaluating it left bare a class it subscripts, so the header keeps them.

    A class whose ``__class_getitem__`` hands back the class itself, as SQLAlchemy's ``TypeEngine`` does, evaluates
    ``TypeEngine[_T]`` to ``TypeEngine``.
    """
    if (
        not (
            bare := {
                leaf.__name__
                for leaf in _bare_classes(hint)
                if inspect.getattr_static(leaf, "__class_getitem__", None) is not None
            }
        )
        or (written := _written_annotation(owner, attribute, objtype)) is None
    ):
        return None
    subscripted = (
        ast.unparse(node.value).rpartition(".")[2]
        for node in ast.walk(ast.parse(written, mode="eval"))
        if isinstance(node, ast.Subscript)
    )
    return None if bare.isdisjoint(subscripted) else written


def _bare_classes(hint: Any) -> Iterator[type]:
    if isinstance(hint, type) and get_origin(hint) is None:
        yield hint
    # the parameters of a Callable come as a list
    for argument in hint if isinstance(hint, list) else get_args(hint):
        yield from _bare_classes(argument)


def _written_annotation(owner: Any, attribute: str, objtype: str) -> str | None:
    if objtype == "property":
        return written_annotations(_property_getter(owner, attribute)).get("return")
    # autodoc replaces the annotations a module and its classes hold with what it evaluated, so read the source
    if isinstance(owner, ModuleType):
        return _source_annotation(owner.__name__, "", attribute)
    # the attribute of an instance is annotated in its class
    klass = owner if isinstance(owner, type) else type(owner)
    return next(
        (
            written
            for holder in klass.__mro__
            if (written := _source_annotation(holder.__module__, holder.__qualname__, attribute))
        ),
        None,
    )


def _source_annotation(module: str, qualname: str, attribute: str) -> str | None:
    try:
        analyzer = ModuleAnalyzer.for_module(module)
        analyzer.analyze()
    except PycodeError:
        return None
    return analyzer.annotations.get((qualname, attribute))


__all__ = ["render_header_types"]
