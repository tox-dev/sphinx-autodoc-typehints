"""
Alias names for annotations.

They come from `autodoc_type_aliases`, the documented `py:type` entries, and module-level aliases such as
`Count = int` that the source writes an annotation as.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._objects import alias_lookup_names, enclosing_scopes
from .._refs import MyTypeAliasForwardRef, WrittenTypeAlias
from .guards import annotation_globals
from .source import written_annotations

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx.environment import BuildEnvironment

    from .._types import Documented, Hint


def type_alias_namespace(
    type_aliases: Mapping[str, str], obj: Documented, module_prefix: str, env: BuildEnvironment | None
) -> tuple[dict[str, MyTypeAliasForwardRef], dict[str, WrittenTypeAlias]]:
    """
    Return the names the annotations of `obj` resolve to an alias, and the annotations written as an alias.

    The annotations of `obj` add nothing to either when reading them fails.
    """
    localns = {name: MyTypeAliasForwardRef(value, configured=True) for name, value in type_aliases.items()}
    if env is None:
        return localns, {}
    py_objects = env.domains.python_domain.objects
    scopes = set(enclosing_scopes(module_prefix))
    for qualified_name, entry in py_objects.items():
        scope, _, short_name = qualified_name.rpartition(".")
        if entry.objtype == "type" and scope in scopes:
            localns[short_name] = MyTypeAliasForwardRef(short_name, crossref=True)
    # under PEP 649 the annotations run on first access and may fail, naming what only a TYPE_CHECKING block binds or
    # subscripting a class that is not generic
    try:
        raw_annotations = getattr(obj, "__annotations__", {})
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return localns, {}
    if not raw_annotations:
        return localns, {}
    obj_globals = annotation_globals(obj) if hasattr(obj, "__globals__") else {}
    # an alias evaluates to the object it names (`Count = int`), so only the annotation as written tells them apart;
    # a module or class holds no globals to find the alias in, so its source is not worth parsing
    written = written_annotations(obj) if obj_globals else {}
    written_as: dict[str, WrittenTypeAlias] = {}
    for name, annotation in raw_annotations.items():
        if isinstance(annotation, str):
            if any(
                candidate in py_objects and py_objects[candidate].objtype == "type"
                for candidate in alias_lookup_names(module_prefix, annotation)
            ):
                localns[annotation] = MyTypeAliasForwardRef(annotation, crossref=True)
        elif (source := written.get(name)) and (alias := written_type_alias(source, annotation, obj_globals)):
            written_as[name] = alias
    return localns, written_as


def written_type_alias(written: str, value: Hint, namespace: Mapping[str, Documented]) -> WrittenTypeAlias | None:
    """Return the module-level alias an annotation `written` as its bare name names, if it evaluated to `value`."""
    if written.startswith("_") or written not in namespace or namespace[written] is not value:
        return None
    # Sphinx knows which aliases the project documents only after reading every document, so rendering decides
    return WrittenTypeAlias(written, value)


__all__ = [
    "type_alias_namespace",
    "written_type_alias",
]
