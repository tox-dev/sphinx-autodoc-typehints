"""Type hint resolution with TYPE_CHECKING guard handling."""

from __future__ import annotations

import ast
import contextlib
import importlib
import importlib.util
import inspect
import re
import sys
import types
import warnings
from collections import ChainMap
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    ForwardRef,
    NewType,
    ParamSpec,
    TypeVar,
    TypeVarTuple,
    get_origin,
)

from sphinx.ext.autodoc.mock import mock
from sphinx.util import logging

from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef, _is_type_alias

from ._stubs import _backfill_descriptor_annotation, _backfill_from_stub, _get_stub_context
from ._type_comments import backfill_type_hints
from ._util import (
    SHADOWED_BY_GUARD,
    annotation_globals,
    defining_module,
    evaluate_annotation,
    get_obj_location,
    guarded_forward_refs,
    guarded_names,
    type_hints,
)

if sys.version_info >= (3, 14):  # pragma: >=3.14 cover
    import annotationlib

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

_LOGGER = logging.getLogger(__name__)
#: Modules whose ``TYPE_CHECKING`` block is executing, innermost last.
_RUNNING_GUARDS: Final[list[str]] = []
#: Guarded imports that named a module from ``_RUNNING_GUARDS``: namespace and shadowed names of the importer, the name
#: it binds, the source module, the imported name, and whether the importer binds that name at runtime.
_IMPORTS_FROM_RUNNING_GUARDS: Final[list[tuple[dict[str, Any], dict[str, Any], str, str, str, bool]]] = []
#: A statement of the module body starting with ``if``, with its indented lines and its ``elif`` and ``else`` branches.
_TOP_LEVEL_IF: Final = re.compile(r"^if\b.*\n(?:(?:[ \t]+.*|(?:elif|else)\b.*)?\n)*", re.MULTILINE)


def get_all_type_hints(
    autodoc_mock_imports: list[str], obj: Any, name: str, localns: Mapping[str, Any]
) -> dict[str, Any]:
    result = _get_type_hint(autodoc_mock_imports, name, obj, localns)
    if not result:
        stub_obj = _stub_target(obj) if inspect.isclass(obj) else obj
        result = backfill_type_hints(stub_obj, name)
        stub_localns: dict[str, Any] = {}
        stub_crossref_names: set[str] = set()
        stub_owner_module: str = ""
        if not result:
            result = _backfill_from_stub(stub_obj)
            if result:
                stub_localns, stub_crossref_names, stub_owner_module = _get_stub_context(stub_obj)
        combined_localns = {**stub_localns, **localns}
        for crossref_name in stub_crossref_names:
            ref = MyTypeAliasForwardRef(crossref_name)
            ref.crossref = True
            combined_localns[crossref_name] = ref
        try:
            obj.__annotations__ = result
        except (AttributeError, TypeError):
            result = resolve_string_annotations(obj, result, combined_localns, stub_owner_module)
        else:
            result = _get_type_hint(autodoc_mock_imports, name, obj, combined_localns)
            with contextlib.suppress(AttributeError, TypeError):
                obj.__annotations__ = result
    return result


def _stub_target(cls: type) -> Any:
    """Return the constructor method for stub/type-comment backfill when *cls* is a class."""
    if cls.__init__ is not object.__init__:
        return cls.__init__
    if cls.__new__ is not object.__new__:
        return cls.__new__
    return cls


def get_descriptor_type_hint(obj: Any) -> Any | None:
    """
    Resolve the documented type of a C data descriptor from its stub, or ``None``.

    The signature-driven backfill never sees these objects because they are not
    callable; the annotation string from the stub is evaluated in the stub's
    namespace so aliases and forward references resolve the same way they do
    for function signatures.
    """
    if (annotation := _backfill_descriptor_annotation(obj)) is None:
        return None
    localns, crossref_names, owner_module = _get_stub_context(obj)
    for crossref_name in crossref_names:
        ref = MyTypeAliasForwardRef(crossref_name)
        ref.crossref = True
        localns[crossref_name] = ref
    return resolve_string_annotations(obj, {"return": annotation}, localns, owner_module)["return"]


def _get_type_hint(autodoc_mock_imports: list[str], name: str, obj: Any, localns: Mapping[str, Any]) -> dict[str, Any]:
    resolve_type_guarded_imports(autodoc_mock_imports, obj)
    # a class reads the guard of the module defining each of its bases in that base's globals, not in shared locals
    localns = {**({} if inspect.isclass(obj) else guarded_names(obj)), **_build_localns(obj, localns)}
    try:
        if getattr(obj, "__no_type_check__", False):
            # typing.get_type_hints() unconditionally returns {} for @typing.no_type_check
            # targets; inspect.get_annotations() has no such guard, so use it to still surface
            # annotations in the rendered docs (see issue #680).
            return inspect.get_annotations(obj, locals=localns, eval_str=True)
        globalns = annotation_globals(obj) if hasattr(obj, "__globals__") else None
        return type_hints(obj, globalns, localns)
    except RecursionError:
        return {}
    except Exception as exc:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        if isinstance(exc, (NameError, AttributeError, SyntaxError)):
            _LOGGER.warning(
                'Cannot resolve forward reference in type annotations of "%s" (module %s): %s',
                name,
                getattr(obj, "__module__", "?"),
                exc,
                type="sphinx_autodoc_typehints",
                subtype="forward_reference",
                location=get_obj_location(obj),
            )
        return resolve_string_annotations(obj, _get_unevaluated_annotations(obj), localns)


def resolve_annotations(
    autodoc_mock_imports: list[str], obj: Any, name: str, localns: Mapping[str, Any]
) -> dict[str, Any]:
    """Resolve the annotations ``obj`` itself carries, without backfilling it from a stub or type comments."""
    return _get_type_hint(autodoc_mock_imports, name, obj, localns)


def _get_unevaluated_annotations(obj: Any) -> dict[str, Any]:
    if sys.version_info < (3, 14):  # pragma: <3.14 cover
        return getattr(obj, "__annotations__", {})
    # ForwardRef proxies keep unevaluatable annotations renderable as their source text — see #712
    try:  # pragma: >=3.14 cover
        return guarded_forward_refs(obj, annotationlib.get_annotations(obj, format=annotationlib.Format.FORWARDREF))
    except Exception:  # pragma: >=3.14 cover  # ruff:ignore[blind-except]  # see _get_type_hint
        return {}


def resolve_string_annotations(
    obj: Any, annotations: dict[str, Any], localns: dict[str, Any], owner_module: str = ""
) -> dict[str, Any]:
    # Use the stub owner module's namespace when available — the obj's __module__ may point at a C extension child
    # (e.g. cbor2._cbor2) while the stub lives in the parent (cbor2/__init__.pyi). Otherwise the module defining obj,
    # which a re-export does not change, as the evaluation that failed before this one used.
    globalns = vars(sys.modules[owner_module]) if owner_module in sys.modules else annotation_globals(obj)
    resolved: dict[str, Any] = {}
    for key, value in annotations.items():
        resolved[key] = value
        # Python 3.14 hands back an annotation it could not evaluate as a ForwardRef holding its source
        source = value.__forward_arg__ if type(value) is ForwardRef else value
        # a quoted annotation evaluates to the string inside it, which takes a second pass
        for _ in range(2):
            if not isinstance(source, str):
                break
            try:
                resolved[key] = source = evaluate_annotation(source, globalns, localns)
            except Exception:  # ruff:ignore[blind-except]
                _LOGGER.debug(
                    "Failed to resolve annotation %r=%r for %s", key, source, getattr(obj, "__qualname__", "?")
                )
                break
    return resolved


def resolve_type_guarded_imports(autodoc_mock_imports: list[str], obj: Any) -> None:
    """
    Execute the ``if TYPE_CHECKING`` block of *obj*'s module, binding the names it guards.

    The module gains the names it lacks, which what reads its globals directly, such as autodoc or a ``type`` alias,
    needs too. A name it binds at runtime keeps that binding, so its own code sees what it always sees; annotations see
    the guarded binding through :func:`guarded_names`.
    """
    if inspect.isclass(obj) and (module := inspect.getmodule(obj)) is not None:
        obj = module
    if _should_skip_guarded_import_resolution(obj):
        return

    if (module := defining_module(obj)) and (module_code := _module_source(module)):
        shadowed = SHADOWED_BY_GUARD[module.__name__] = {}
        _RUNNING_GUARDS.append(module.__name__)
        try:
            _execute_guarded_code(autodoc_mock_imports, obj, module_code, shadowed)
        finally:
            _RUNNING_GUARDS.pop()
            if not _RUNNING_GUARDS:
                _bind_imports_from_running_guards()


def _module_source(module: types.ModuleType) -> str:
    try:
        return inspect.getsource(module)
    except (TypeError, OSError):
        return ""


def _should_skip_guarded_import_resolution(obj: Any) -> bool:
    if isinstance(obj, types.ModuleType):
        return obj.__name__ in SHADOWED_BY_GUARD

    if not hasattr(obj, "__globals__"):
        return True

    module_name = obj.__globals__.get("__name__", obj.__module__)
    return module_name in SHADOWED_BY_GUARD or module_name in sys.builtin_module_names


def _execute_guarded_code(
    autodoc_mock_imports: list[str], obj: Any, module_code: str, shadowed: dict[str, Any]
) -> None:
    namespace = getattr(obj, "__globals__", obj.__dict__)
    # what a type checker sees, which the functions the block defines take as their globals
    scope = dict(namespace)
    statements, errors = _guarded_statements(module_code)
    for exc in errors:
        _warn_guarded_import(obj, exc)
    deferred: list[tuple[str, str, str]] = []
    # One statement at a time, so an unimportable optional dependency cannot strand the names after it — #741
    for statement in statements:
        # a stub of a function the module defines, such as an @overload, is no type an annotation names, and its
        # decorator would register it against the function
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef) and statement.name in namespace:
            continue
        try:
            _run_guarded_import(autodoc_mock_imports, obj, statement, scope, deferred)
        except Exception as exc:  # ruff:ignore[blind-except]
            if any(isinstance(node, ast.Import | ast.ImportFrom) for node in ast.walk(statement)):
                _warn_guarded_import(obj, exc)
            else:
                _LOGGER.debug("Skipped guarded statement the interpreter rejects: %r", exc)
                _bind_unresolvable_names(scope, statement)
    _IMPORTS_FROM_RUNNING_GUARDS.extend(
        (namespace, shadowed, bound, source, name, bound in namespace) for bound, source, name in deferred
    )
    for name, value in scope.items():
        if name not in namespace:
            namespace[name] = value
        elif namespace[name] is not value:
            shadowed[name] = value


def _bind_imports_from_running_guards() -> None:
    """Bind what a guard imported from a guard that was still running, now that every guard it waited on finished."""
    while _IMPORTS_FROM_RUNNING_GUARDS:
        namespace, shadowed, bound, source, name, at_runtime = _IMPORTS_FROM_RUNNING_GUARDS.pop()
        # a guard may have taken the module out of sys.modules since, leaving only what its own guard bound
        module_globals = vars(module) if (module := sys.modules.get(source)) else {}
        if name in (names := ChainMap(SHADOWED_BY_GUARD[source], module_globals)):
            if at_runtime:
                shadowed[bound] = names[name]
            else:
                namespace[bound] = names[name]


def _guarded_statements(module_code: str) -> tuple[list[ast.stmt], list[SyntaxError]]:
    """Return the statements only a type checker runs, and why the guards that could not be read failed to parse."""
    if "TYPE_CHECKING" not in module_code:
        return [], []
    # the module compiled already, so its warnings are no news, and -W error would turn them into a SyntaxError
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        try:
            nodes, errors = ast.parse(module_code).body, []
        except SyntaxError:
            nodes, errors = _parse_guards_alone(module_code)
    return [
        statement for node in nodes if isinstance(node, ast.If) for statement in _type_checking_branch(node)
    ], errors


def _parse_guards_alone(module_code: str) -> tuple[list[ast.stmt], list[SyntaxError]]:
    """
    Parse each top-level ``if`` naming ``TYPE_CHECKING`` on its own, as 3.13.10 did.

    The source ``inspect`` reads may not parse as a whole, as a stale ``linecache`` entry or a module a custom loader
    compiles from another language does, while its guards do.
    """
    nodes: list[ast.stmt] = []
    errors: list[SyntaxError] = []
    for block in _TOP_LEVEL_IF.findall(f"{module_code}\n"):
        if "TYPE_CHECKING" in block:
            try:
                nodes.extend(ast.parse(block).body)
            except SyntaxError as exc:
                errors.append(exc)
    return nodes, errors


def _type_checking_branch(node: ast.If) -> list[ast.stmt]:
    """Pick the statements only a type checker runs: ``else`` of ``if not TYPE_CHECKING``, none for other tests."""
    if (holds := _holds_when_type_checking(node.test)) is None:
        return []
    return node.body if holds else node.orelse


def _holds_when_type_checking(test: ast.expr) -> bool | None:
    """Whether a type checker takes the test as true, or ``None`` when ``TYPE_CHECKING`` plays no part in it."""
    if _names_type_checking(test):
        return True
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return None if (operand := _holds_when_type_checking(test.operand)) is None else not operand
    # the other operands of a boolean test are runtime conditions, so they cannot decide the outcome either way
    if isinstance(test, ast.BoolOp) and (
        known := [held for value in test.values if (held := _holds_when_type_checking(value)) is not None]
    ):
        return all(known) if isinstance(test.op, ast.And) else any(known)
    return None


def _names_type_checking(test: ast.expr) -> bool:
    """Match ``t.TYPE_CHECKING`` too, whatever the module alias."""
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _warn_guarded_import(obj: Any, exc: Exception) -> None:
    _LOGGER.warning(
        "Failed guarded type import in %r: %r",
        getattr(obj, "__module__", None) or getattr(obj, "__name__", "?"),
        exc,
        type="sphinx_autodoc_typehints",
        subtype="guarded_import",
        location=get_obj_location(obj),
    )


def _bind_unresolvable_names(namespace: dict[str, Any], statement: ast.stmt) -> None:
    """
    Bind the names a guarded statement would have defined, so annotations can still use them.

    Type checkers accept constructs the interpreter rejects, e.g. ``TypeVar("T", bound="A" | B)`` (#751).
    """
    for name in _defined_names(statement):
        namespace.setdefault(name, MyTypeAliasForwardRef(name))


def _defined_names(node: ast.AST) -> Iterator[str]:
    """Names the node binds, taking only its own targets so loop and comprehension variables stay out."""
    if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
        yield node.name
    elif isinstance(node, ast.Assign):
        yield from (target.id for target in node.targets if isinstance(target, ast.Name))
    elif isinstance(node, ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            yield node.target.id
    elif isinstance(node, ast.Import | ast.ImportFrom):
        yield from (alias.asname or alias.name.partition(".")[0] for alias in node.names)
    elif isinstance(node, ast.stmt):
        for child in ast.iter_child_nodes(node):
            yield from _defined_names(child)


def _run_guarded_import(
    autodoc_mock_imports: list[str],
    obj: Any,
    statement: ast.stmt,
    ns: dict[str, Any],
    deferred: list[tuple[str, str, str]],
) -> None:
    guarded_code = ast.unparse(statement)
    mocked = list(autodoc_mock_imports)
    while True:
        try:
            with mock(mocked):
                exec(guarded_code, ns)  # ruff:ignore[exec-builtin]
        except ImportError as exc:
            if not exc.name:
                return
            if (
                isinstance(exc, ModuleNotFoundError)
                and exc.name not in mocked
                and any(_is_within(module, exc.name) for module in _imported_modules(statement, ns.get("__package__")))
            ):
                # The guard means the dependency need not be installed; mock it as autodoc_mock_imports would (#768)
                _LOGGER.debug("Mocked absent guarded dependency %r for %r", exc.name, getattr(obj, "__module__", "?"))
                mocked.append(exc.name)
                continue
            resolve_type_guarded_imports(autodoc_mock_imports, importlib.import_module(exc.name))
            with mock(mocked), contextlib.suppress(ImportError):
                exec(guarded_code, ns)  # ruff:ignore[exec-builtin]
        if isinstance(statement, ast.ImportFrom):
            _import_as_guarded(autodoc_mock_imports, statement, ns, deferred)
        return


def _import_as_guarded(
    autodoc_mock_imports: list[str],
    statement: ast.ImportFrom,
    ns: dict[str, Any],
    deferred: list[tuple[str, str, str]],
) -> None:
    """Bind what the statement imports as a type checker does, reading a name the guard of its module shadows."""
    source = importlib.util.resolve_name("." * statement.level + (statement.module or ""), ns.get("__package__"))
    if (module := sys.modules.get(source)) is None:
        return
    # modules whose guards import from each other: the one still running is half-built, so read it once it finishes
    if source in _RUNNING_GUARDS:
        deferred.extend((alias.asname or alias.name, source, alias.name) for alias in statement.names)
        return
    imported = {alias.name for alias in statement.names}
    # running the guard of every module a guard imports from would warn about what nothing here reads
    if source not in SHADOWED_BY_GUARD and _guard_binds(module, imported):
        resolve_type_guarded_imports(autodoc_mock_imports, module)
    shadowed = SHADOWED_BY_GUARD.get(source, {})
    ns.update({alias.asname or alias.name: shadowed[alias.name] for alias in statement.names if alias.name in shadowed})


def _guard_binds(module: types.ModuleType, names: set[str]) -> bool:
    statements, _ = _guarded_statements(_module_source(module))
    return any(name in names for statement in statements for name in _defined_names(statement))


def _imported_modules(statement: ast.stmt, package: str | None) -> Iterator[str]:
    for node in ast.walk(statement):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            yield importlib.util.resolve_name("." * node.level + (node.module or ""), package)


def _is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


def _build_localns(obj: Any, localns: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(localns)
    result.update({p.__name__: p for p in _type_params(obj)})
    parts = (getattr(obj, "__qualname__", "") or "").split(".")
    if len(parts) <= 1:
        return result
    if ns := (vars(module) if (module := inspect.getmodule(obj)) else getattr(obj, "__globals__", None)):
        current: Any = None
        for part in parts[:-1]:
            current = (
                (ns if current is None else vars(current)).get(part)
                if current is None or hasattr(current, "__dict__")
                else None
            )
            if current is None:
                break
            if inspect.isclass(current):
                result[part] = current
            result.update({p.__name__: p for p in _type_params(current)})
        if inspect.isroutine(obj) and inspect.isclass(current):
            # nested classes, type variables and aliases resolve as they would eagerly, but other members (a method
            # named list, a field defaulting to None) must not shadow the module globals get_type_hints resolves against
            result = {**{key: value for key, value in vars(current).items() if _is_type_like(value)}, **result}
    return result


def _is_type_like(value: Any) -> bool:
    return (
        inspect.isclass(value)
        or isinstance(value, TypeVar | ParamSpec | TypeVarTuple | NewType)
        or get_origin(value) is not None
        or _is_type_alias(value)
    )


def _type_params(obj: Any) -> tuple[TypeVar | ParamSpec | TypeVarTuple, ...]:
    # A class owning the __type_params__ slot itself (typing.TypeAliasType) hands back the descriptor, not a tuple
    params = getattr(obj, "__type_params__", ())
    return params if isinstance(params, tuple) else ()


__all__ = [
    "get_all_type_hints",
    "resolve_annotations",
    "resolve_string_annotations",
    "resolve_type_guarded_imports",
]
