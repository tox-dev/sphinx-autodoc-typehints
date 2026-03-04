"""Shared utilities for type hint resolution."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef

if TYPE_CHECKING:
    from sphinx.environment import BuildEnvironment


def get_obj_location(obj: Any) -> str | None:
    try:
        filepath = inspect.getsourcefile(obj) or inspect.getfile(obj)
    except TypeError:
        return None
    try:
        lineno = inspect.getsourcelines(obj)[1]
    except (OSError, TypeError):
        return filepath
    else:
        return f"{filepath}:{lineno}"


def collect_documented_type_aliases(
    obj: Any, module_prefix: str, env: BuildEnvironment
) -> tuple[dict[str, MyTypeAliasForwardRef], dict[int, MyTypeAliasForwardRef]]:
    py_objects = env.get_domain("py").objects  # ty: ignore[unresolved-attribute]
    deferred: dict[str, MyTypeAliasForwardRef] = {}
    eager: dict[int, MyTypeAliasForwardRef] = {}

    prefix_dot = f"{module_prefix}."
    for fqn, obj_info in py_objects.items():
        if obj_info.objtype != "type":
            continue
        if fqn.startswith(prefix_dot) or fqn == module_prefix:
            short_name = fqn.rsplit(".", 1)[-1]
            ref = MyTypeAliasForwardRef(short_name)
            ref.crossref = True
            deferred[short_name] = ref

    raw_annotations = getattr(obj, "__annotations__", {})
    if not raw_annotations:
        return deferred, eager

    obj_globals = getattr(obj, "__globals__", {})
    for annotation in raw_annotations.values():
        if isinstance(annotation, str):
            if _is_documented_type(annotation, module_prefix, py_objects):
                ref = MyTypeAliasForwardRef(annotation)
                ref.crossref = True
                deferred[annotation] = ref
        else:
            for var_name, var_value in obj_globals.items():
                if (
                    var_value is annotation
                    and not var_name.startswith("_")
                    and _is_documented_type(var_name, module_prefix, py_objects)
                ):
                    ref = MyTypeAliasForwardRef(var_name)
                    ref.crossref = True
                    eager[id(annotation)] = ref

    return deferred, eager


def _is_documented_type(name: str, module_prefix: str, py_objects: dict[str, Any]) -> bool:
    return any(
        candidate in py_objects and py_objects[candidate].objtype == "type"
        for candidate in (f"{module_prefix}.{name}", name)
    )


__all__ = [
    "collect_documented_type_aliases",
    "get_obj_location",
]
