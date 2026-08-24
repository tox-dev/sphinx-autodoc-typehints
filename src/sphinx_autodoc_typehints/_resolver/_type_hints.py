"""Type hint resolution with TYPE_CHECKING guard handling."""

from __future__ import annotations

import ast
import contextlib
import importlib
import inspect
import re
import sys
import textwrap
import types
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, TypeVarTuple, get_type_hints

from sphinx.ext.autodoc.mock import mock
from sphinx.util import logging

from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef

from ._stubs import _backfill_descriptor_annotation, _backfill_from_stub, _get_stub_context
from ._type_comments import backfill_type_hints
from ._util import get_obj_location

if sys.version_info >= (3, 14):  # pragma: >=3.14 cover
    import annotationlib

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

_LOGGER = logging.getLogger(__name__)

_TYPE_GUARD_IMPORT_RE = re.compile(
    r"""
    \n                          # leading newline before the guard
    if[ ](typing\.)?            # "if typing." or "if " prefix
    TYPE_CHECKING:              # the TYPE_CHECKING constant
    [^\n]*                      # rest of the if-line
    ([\s\S]*?)                  # guarded block body (captured, non-greedy)
    (?=\n\S)                    # lookahead: next non-indented line
    """,
    re.VERBOSE,
)
_TYPE_GUARD_IMPORTS_RESOLVED: set[str] = set()


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
            result = _resolve_string_annotations(obj, result, combined_localns, stub_owner_module)
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
    return _resolve_string_annotations(obj, {"return": annotation}, localns, owner_module)["return"]


def _resolve_string_annotations(
    obj: Any, annotations: dict[str, str], localns: dict[str, Any], owner_module: str = ""
) -> dict[str, Any]:
    # Use the stub owner module's namespace when available — the obj's __module__ may point at a C extension child
    # (e.g. cbor2._cbor2) while the stub lives in the parent (cbor2/__init__.pyi).
    module_name = owner_module or getattr(obj, "__module__", None)
    globalns = vars(sys.modules[module_name]) if module_name and module_name in sys.modules else {}
    resolved: dict[str, Any] = {}
    for key, value in annotations.items():
        if isinstance(value, str):
            try:
                resolved[key] = eval(value, globalns, localns)  # ruff:ignore[suspicious-eval-usage]
            except Exception:  # ruff:ignore[blind-except]
                _LOGGER.debug(
                    "Failed to resolve annotation %r=%r for %s",
                    key,
                    value,
                    getattr(obj, "__qualname__", "?"),
                )
                resolved[key] = value
        else:
            resolved[key] = value
    return resolved


def _get_type_hint(autodoc_mock_imports: list[str], name: str, obj: Any, localns: Mapping[str, Any]) -> dict[str, Any]:
    _resolve_type_guarded_imports(autodoc_mock_imports, obj)
    localns = _build_localns(obj, localns)
    try:
        if getattr(obj, "__no_type_check__", False):
            # typing.get_type_hints() unconditionally returns {} for @typing.no_type_check
            # targets; inspect.get_annotations() has no such guard, so use it to still surface
            # annotations in the rendered docs (see issue #680).
            result = inspect.get_annotations(obj, locals=localns, eval_str=True)
        else:
            result = get_type_hints(obj, None, localns, include_extras=True)
    except (AttributeError, TypeError, RecursionError) as exc:
        if (
            isinstance(exc, TypeError) and _future_annotations_imported(obj) and "unsupported operand type" in str(exc)
        ):  # pragma: <3.14 cover
            result = obj.__annotations__
        elif isinstance(exc, TypeError) and sys.version_info >= (3, 14):  # pragma: >=3.14 cover
            result = _get_forward_ref_annotations(obj)
        else:
            result = {}
    except NameError as exc:
        _LOGGER.warning(
            'Cannot resolve forward reference in type annotations of "%s" (module %s): %s',
            name,
            getattr(obj, "__module__", "?"),
            exc,
            type="sphinx_autodoc_typehints",
            subtype="forward_reference",
            location=get_obj_location(obj),
        )
        if sys.version_info >= (3, 14):
            result = annotationlib.get_annotations(obj, format=annotationlib.Format.FORWARDREF)
        else:
            result = obj.__annotations__  # pragma: <3.14 cover
    return result


def _get_forward_ref_annotations(obj: Any) -> dict[str, Any]:  # pragma: >=3.14 cover
    # ForwardRef proxies keep unevaluatable annotations renderable as their source text — see #712
    try:
        return annotationlib.get_annotations(obj, format=annotationlib.Format.FORWARDREF)
    except (NameError, TypeError, AttributeError, RecursionError):
        return {}


def _resolve_type_guarded_imports(autodoc_mock_imports: list[str], obj: Any) -> None:
    if _should_skip_guarded_import_resolution(obj):
        return

    module = inspect.getmodule(obj)

    if module:
        try:
            module_code = inspect.getsource(module)
        except (TypeError, OSError):
            ...
        else:
            _TYPE_GUARD_IMPORTS_RESOLVED.add(module.__name__)
            _execute_guarded_code(autodoc_mock_imports, obj, module_code)


def _should_skip_guarded_import_resolution(obj: Any) -> bool:
    if isinstance(obj, types.ModuleType):
        return False

    if not hasattr(obj, "__globals__"):
        return True

    return obj.__module__ in _TYPE_GUARD_IMPORTS_RESOLVED or obj.__module__ in sys.builtin_module_names


def _execute_guarded_code(autodoc_mock_imports: list[str], obj: Any, module_code: str) -> None:
    for _, part in _TYPE_GUARD_IMPORT_RE.findall(module_code):
        try:
            # One statement at a time, so an unimportable optional dependency cannot strand the names after it — #741
            statements = ast.parse(textwrap.dedent(part)).body
        except SyntaxError as exc:
            _warn_guarded_import(obj, exc)
            continue
        for statement in statements:
            try:
                _run_guarded_import(autodoc_mock_imports, obj, ast.unparse(statement))
            except Exception as exc:  # ruff:ignore[blind-except]
                if any(isinstance(node, ast.Import | ast.ImportFrom) for node in ast.walk(statement)):
                    _warn_guarded_import(obj, exc)
                else:
                    _LOGGER.debug("Skipped guarded statement the interpreter rejects: %r", exc)
                    _bind_unresolvable_names(obj, statement)


def _warn_guarded_import(obj: Any, exc: Exception) -> None:
    _LOGGER.warning(
        "Failed guarded type import in %r: %r",
        getattr(obj, "__module__", None) or getattr(obj, "__name__", "?"),
        exc,
        type="sphinx_autodoc_typehints",
        subtype="guarded_import",
        location=get_obj_location(obj),
    )


def _bind_unresolvable_names(obj: Any, statement: ast.stmt) -> None:
    """
    Bind the names a guarded statement would have defined, so annotations can still use them.

    Type checkers accept constructs the interpreter rejects, e.g. ``TypeVar("T", bound="A" | B)`` (#751).
    """
    namespace = getattr(obj, "__globals__", obj.__dict__)
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
    elif isinstance(node, ast.stmt):
        for child in ast.iter_child_nodes(node):
            yield from _defined_names(child)


def _run_guarded_import(autodoc_mock_imports: list[str], obj: Any, guarded_code: str) -> None:
    ns = getattr(obj, "__globals__", obj.__dict__)
    try:
        with mock(autodoc_mock_imports):
            exec(guarded_code, ns)  # ruff:ignore[exec-builtin]
    except ImportError as exc:
        if not exc.name:
            return
        _resolve_type_guarded_imports(autodoc_mock_imports, importlib.import_module(exc.name))
        try:
            with mock(autodoc_mock_imports):
                exec(guarded_code, ns)  # ruff:ignore[exec-builtin]
        except ImportError:
            pass


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
    return result


def _type_params(obj: Any) -> tuple[TypeVar | ParamSpec | TypeVarTuple, ...]:
    # A class owning the __type_params__ slot itself (typing.TypeAliasType) hands back the descriptor, not a tuple
    params = getattr(obj, "__type_params__", ())
    return params if isinstance(params, tuple) else ()


def _future_annotations_imported(obj: Any) -> bool:
    annotations_ = getattr(inspect.getmodule(obj), "annotations", None)
    if annotations_ is None:
        return False
    return bool(annotations_.compiler_flag == 0x1000000)  # ruff:ignore[magic-value-comparison]


__all__ = ["get_all_type_hints"]
