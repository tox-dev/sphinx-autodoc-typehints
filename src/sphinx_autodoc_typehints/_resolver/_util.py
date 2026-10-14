"""Shared utilities for type hint resolution."""

from __future__ import annotations

import ast
import inspect
import sys
import textwrap
import types
from typing import TYPE_CHECKING, Any, Final, cast, get_type_hints

from sphinx_autodoc_typehints._annotations import (
    MyTypeAliasForwardRef,
    WrittenTypeAlias,
    alias_lookup_names,
    enclosing_scopes,
)

if sys.version_info >= (3, 14):  # pragma: >=3.14 cover
    from typing import evaluate_forward_ref

    from annotationlib import Format, ForwardRef, get_annotations

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from sphinx.environment import BuildEnvironment

_DOCUMENTED: Final = "sphinx_autodoc_typehints_documented"
#: Per module, what its ``TYPE_CHECKING`` block binds a name to that the module binds to something else at runtime.
SHADOWED_BY_GUARD: Final[dict[str, dict[str, Any]]] = {}


def note_documented(env: BuildEnvironment, name: str) -> None:
    """Remember that autodoc documents ``name`` on the page being read, so its header is the extension's to render."""
    cast("set[str]", env.temp_data.setdefault(_DOCUMENTED, set())).add(name)


def is_documented(env: BuildEnvironment, name: str) -> bool:
    """
    Tell whether autodoc documents ``name`` on the page being read.

    autodoc already looked such a name up, so looking it up again runs no package ``__getattr__`` autodoc did not run;
    looking up a name written by hand could import, raise, or rename what autodoc documents later.
    """
    return name in (env.temp_data.get(_DOCUMENTED) or ())


def get_obj_location(obj: Any) -> str | None:
    try:
        filepath = inspect.getsourcefile(obj) or inspect.getfile(obj)
    except TypeError:
        return None
    # code without a file, such as the __init__ a dataclass generates, is named like <string>
    if filepath.startswith("<"):
        return None
    try:
        lineno = inspect.getsourcelines(obj)[1]
    except (OSError, TypeError):
        return filepath
    else:
        return f"{filepath}:{lineno}"


def type_hints(obj: Any, globalns: dict[str, Any] | None, localns: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return :func:`typing.get_type_hints` with the extras, reading a name a guard shadows as the guard binds it."""
    if sys.version_info >= (3, 14) and _reads_shadowed_name(obj):  # pragma: >=3.14 cover
        return _hints_from_source(obj, globalns, localns)
    return get_type_hints(obj, globalns, localns, include_extras=True)


def _reads_shadowed_name(obj: Any) -> bool:  # pragma: >=3.14 cover
    """
    Whether an annotation of ``obj`` evaluated at runtime names what the ``TYPE_CHECKING`` block of its module shadows.

    PEP 649 evaluates such an annotation in the globals it was compiled in, which hold the runtime binding of the name.
    """
    return any(
        (getattr(owner, "__annotate__", None) is not None or _holds_values(owner))
        and (shadowed := guarded_names(owner))
        and any(
            isinstance(node, ast.Name) and node.id in shadowed
            for source in _written(owner).values()
            if isinstance(source, str)
            for node in ast.walk(ast.parse(source, mode="eval"))
        )
        for owner in (obj.__mro__ if isinstance(obj, type) else (obj,))
    )


def _hints_from_source(  # pragma: >=3.14 cover
    obj: Any, globalns: dict[str, Any] | None, localns: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Evaluate the source of each annotation as :func:`typing.get_type_hints` would, in the guarded globals."""
    if not isinstance(obj, type):
        globalns = annotation_globals(obj) if globalns is None else globalns
        return _evaluate_written(
            obj, globalns, globalns if localns is None else localns, is_argument=not isinstance(obj, types.ModuleType)
        )
    hints: dict[str, Any] = {}
    for base in reversed(obj.__mro__):
        base_globals = annotation_globals(base) if globalns is None else globalns
        base_locals = dict(vars(base)) if localns is None else localns
        if localns is None and globalns is None:
            # as get_type_hints does, so the names of the module come before those of the class body
            base_globals, base_locals = base_locals, base_globals
        hints |= _evaluate_written(base, dict(base_globals), base_locals, is_argument=False)
    return hints


def _evaluate_written(  # pragma: >=3.14 cover
    owner: Any, globalns: dict[str, Any], localns: Mapping[str, Any], *, is_argument: bool
) -> dict[str, Any]:
    params = getattr(owner, "__type_params__", ())
    hints: dict[str, Any] = {}
    for name, source in _written(owner).items():
        if isinstance(source, str):
            ref = ForwardRef(source, is_argument=is_argument, is_class=isinstance(owner, type))
            value = evaluate_forward_ref(
                ref,
                owner=owner,
                globals=globalns,
                locals=localns,
                # typeshed declares a 3-tuple of one TypeVar, ParamSpec and TypeVarTuple, not a tuple of any of them
                type_params=params,  # ty: ignore[invalid-argument-type]
            )
        else:
            value = source
        hints[name] = type(None) if value is None else value
    return hints


def _written(owner: Any) -> dict[str, Any]:  # pragma: >=3.14 cover
    """
    Return the source of each annotation of ``owner``, or its value where the source is gone.

    The values include what was added to the annotations after they were evaluated, as attrs fields are.
    """
    stored = dict(getattr(owner, "__annotations__", None) or {})
    if getattr(owner, "__annotate__", None) is not None:
        return stored | get_annotations(owner, format=Format.STRING)
    return stored | _annotated_assignments(owner) if _holds_values(owner) else stored


def _holds_values(owner: Any) -> bool:  # pragma: >=3.14 cover
    """
    Whether autodoc replaced the lazy annotations of a module or class with their values.

    It does so to add the types its comments give, which drops the code that would evaluate them again.
    """
    return isinstance(owner, type | types.ModuleType) and any(
        not isinstance(value, str) for value in (getattr(owner, "__annotations__", None) or {}).values()
    )


def _annotated_assignments(owner: type | types.ModuleType) -> dict[str, str]:  # pragma: >=3.14 cover
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(owner)))
    except (OSError, TypeError, SyntaxError):
        return {}
    body = cast("ast.ClassDef", tree.body[0]).body if isinstance(owner, type) else tree.body
    return {
        statement.target.id: ast.unparse(statement.annotation)
        for statement in body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }


def annotation_globals(obj: Any) -> dict[str, Any]:
    """
    Return the globals the annotations of ``obj`` evaluate in, read as a type checker reads them.

    Generated code such as an attrs ``__init__`` runs in a globals dict of its own, which misses the names the module
    binds afterwards, so the module's names fill the gaps.
    """
    if (module := defining_module(obj)) is None:
        return getattr(obj, "__globals__", {})
    own = getattr(obj, "__globals__", vars(module))
    names = own if own is vars(module) else {**vars(module), **own}
    return {**names, **shadowed} if (shadowed := guarded_names(obj)) else names


def guarded_names(obj: Any) -> dict[str, Any]:
    """Return what the ``TYPE_CHECKING`` block of the module of ``obj`` binds the names it rebinds at runtime to."""
    return SHADOWED_BY_GUARD.get(module.__name__, {}) if (module := defining_module(obj)) else {}


def defining_module(obj: Any) -> types.ModuleType | None:
    # re-exporting reassigns ``__module__``, while the globals stay those of the module defining the object
    return sys.modules.get(getattr(obj, "__globals__", {}).get("__name__", "")) or inspect.getmodule(obj)


def object_at(module: str | None, path: Iterable[str]) -> Any:
    """Return the object ``path`` names in the imported ``module``, ``None`` where a part of it is missing."""
    found: Any = sys.modules.get(module or "")
    for part in path:
        if found is None:
            return None
        found = getattr(found, part, None)
    return found


def type_alias_namespace(
    type_aliases: Mapping[str, str], obj: Any, module_prefix: str, env: BuildEnvironment | None
) -> tuple[dict[str, MyTypeAliasForwardRef], dict[str, WrittenTypeAlias]]:
    """Return the names the annotations of ``obj`` resolve to an alias, and the annotations written as an alias."""
    localns = {key: MyTypeAliasForwardRef(value, configured=True) for key, value in type_aliases.items()}
    if env is None:
        return localns, {}
    deferred, eager = collect_documented_type_aliases(obj, module_prefix, env)
    return localns | deferred, eager


def documented_type_names(env: BuildEnvironment) -> frozenset[str]:
    """Return the names the docs read so far document as a type, the ones an annotation may resolve to an alias."""
    py_objects = env.get_domain("py").objects  # ty: ignore[unresolved-attribute]
    return frozenset(name for name, entry in py_objects.items() if entry.objtype == "type")


def collect_documented_type_aliases(
    obj: Any, module_prefix: str, env: BuildEnvironment
) -> tuple[dict[str, MyTypeAliasForwardRef], dict[str, WrittenTypeAlias]]:
    py_objects = env.get_domain("py").objects  # ty: ignore[unresolved-attribute]
    deferred = _collect_module_type_aliases(module_prefix, py_objects)
    written_as: dict[str, WrittenTypeAlias] = {}

    # PEP 649 (Python 3.14+): annotation expressions only run on access and may fail at runtime
    # (TYPE_CHECKING-only names, subscripting a non-generic class)
    try:
        raw_annotations = getattr(obj, "__annotations__", {})
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return deferred, written_as
    if not raw_annotations:
        return deferred, written_as

    obj_globals = annotation_globals(obj) if hasattr(obj, "__globals__") else {}
    # an alias evaluates to the object it names (``Count = int``), so only the annotation as written tells them apart;
    # a module or class holds no globals to find the alias in, so its source is not worth parsing
    written = written_annotations(obj) if obj_globals else {}
    for key, annotation in raw_annotations.items():
        if isinstance(annotation, str):
            if _is_documented_type(annotation, module_prefix, py_objects):
                ref = MyTypeAliasForwardRef(annotation)
                ref.crossref = True
                deferred[annotation] = ref
        elif (name := written.get(key)) and (alias := written_type_alias(name, annotation, obj_globals)):
            written_as[key] = alias

    return deferred, written_as


def written_type_alias(written: str, value: Any, namespace: Mapping[str, Any]) -> WrittenTypeAlias | None:
    """Return the module-level alias an annotation ``written`` as its bare name names, if it evaluated to ``value``."""
    if written.startswith("_") or written not in namespace or namespace[written] is not value:
        return None
    # whether the alias is documented is only known once every document is read, so rendering decides
    return WrittenTypeAlias(written, value)


def _collect_module_type_aliases(module_prefix: str, py_objects: dict[str, Any]) -> dict[str, MyTypeAliasForwardRef]:
    scopes = set(enclosing_scopes(module_prefix))
    result: dict[str, MyTypeAliasForwardRef] = {}
    for fqn, obj_info in py_objects.items():
        if obj_info.objtype == "type" and fqn.rpartition(".")[0] in scopes:
            short_name = fqn.rsplit(".", 1)[-1]
            ref = MyTypeAliasForwardRef(short_name)
            ref.crossref = True
            result[short_name] = ref
    return result


def written_annotations(obj: Any) -> dict[str, str]:
    try:
        node = ast.parse(textwrap.dedent(inspect.getsource(obj))).body[0]
    except (OSError, TypeError, SyntaxError):
        return {}
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return {}
    arguments = node.args
    params = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, arguments.vararg, arguments.kwarg]
    written = {param.arg: ast.unparse(param.annotation) for param in params if param and param.annotation}
    return written | ({"return": ast.unparse(node.returns)} if node.returns else {})


def _is_documented_type(name: str, module_prefix: str, py_objects: dict[str, Any]) -> bool:
    return any(
        candidate in py_objects and py_objects[candidate].objtype == "type"
        for candidate in alias_lookup_names(module_prefix, name)
    )


__all__ = [
    "SHADOWED_BY_GUARD",
    "annotation_globals",
    "collect_documented_type_aliases",
    "defining_module",
    "documented_type_names",
    "get_obj_location",
    "guarded_names",
    "is_documented",
    "note_documented",
    "object_at",
    "type_alias_namespace",
    "type_hints",
    "written_annotations",
    "written_type_alias",
]
