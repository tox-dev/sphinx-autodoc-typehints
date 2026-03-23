"""Type hint resolution with TYPE_CHECKING guard handling."""

from __future__ import annotations

import importlib
import inspect
import re
import sys
import textwrap
import types
from typing import Any, get_type_hints

from sphinx.ext.autodoc.mock import mock
from sphinx.util import logging

from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef

from ._stubs import _backfill_from_stub, _get_stub_context
from ._type_comments import backfill_type_hints
from ._util import get_obj_location

if sys.version_info >= (3, 14):  # pragma: >=3.14 cover
    import annotationlib

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
    autodoc_mock_imports: list[str], obj: Any, name: str, localns: dict[Any, MyTypeAliasForwardRef]
) -> dict[str, Any]:
    result = _get_type_hint(autodoc_mock_imports, name, obj, localns)
    if not result:
        stub_obj = _stub_target(obj) if inspect.isclass(obj) else obj
        result = backfill_type_hints(stub_obj, name)
        stub_localns: dict[str, Any] = {}
        stub_alias_names: set[str] = set()
        stub_owner_module: str = ""
        if not result:
            result = _backfill_from_stub(stub_obj)
            if result:
                stub_localns, stub_alias_names, stub_owner_module = _get_stub_context(stub_obj)
        combined_localns = {**stub_localns, **localns}
        for alias_name in stub_alias_names:
            ref = MyTypeAliasForwardRef(alias_name)
            ref.crossref = True
            combined_localns[alias_name] = ref
        try:
            obj.__annotations__ = result
        except (AttributeError, TypeError):
            result = _resolve_string_annotations(obj, result, combined_localns, stub_owner_module)
        else:
            result = _get_type_hint(autodoc_mock_imports, name, obj, combined_localns)
    return result


def _stub_target(cls: type) -> Any:
    """Return the constructor method for stub/type-comment backfill when *cls* is a class."""
    if cls.__init__ is not object.__init__:
        return cls.__init__
    if cls.__new__ is not object.__new__:
        return cls.__new__
    return cls


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
                resolved[key] = eval(value, globalns, localns)  # noqa: S307
            except Exception:  # noqa: BLE001
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


def _get_type_hint(
    autodoc_mock_imports: list[str], name: str, obj: Any, localns: dict[Any, MyTypeAliasForwardRef]
) -> dict[str, Any]:
    _resolve_type_guarded_imports(autodoc_mock_imports, obj)
    localns = _build_localns(obj, localns)
    try:
        result = get_type_hints(obj, None, localns, include_extras=True)
    except (AttributeError, TypeError, RecursionError) as exc:
        if (
            isinstance(exc, TypeError) and _future_annotations_imported(obj) and "unsupported operand type" in str(exc)
        ):  # pragma: <3.14 cover
            result = obj.__annotations__
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
        guarded_code = textwrap.dedent(part)
        try:
            _run_guarded_import(autodoc_mock_imports, obj, guarded_code)
        except Exception as exc:  # noqa: BLE001
            module_name = getattr(obj, "__module__", None) or getattr(obj, "__name__", "?")
            _LOGGER.warning(
                "Failed guarded type import in %r: %r",
                module_name,
                exc,
                type="sphinx_autodoc_typehints",
                subtype="guarded_import",
                location=get_obj_location(obj),
            )


def _run_guarded_import(autodoc_mock_imports: list[str], obj: Any, guarded_code: str) -> None:
    ns = getattr(obj, "__globals__", obj.__dict__)
    try:
        with mock(autodoc_mock_imports):
            exec(guarded_code, ns)  # noqa: S102
    except ImportError as exc:
        if not exc.name:
            return
        _resolve_type_guarded_imports(autodoc_mock_imports, importlib.import_module(exc.name))
        try:
            with mock(autodoc_mock_imports):
                exec(guarded_code, ns)  # noqa: S102
        except ImportError:
            pass


def _build_localns(obj: Any, localns: dict[Any, MyTypeAliasForwardRef]) -> dict[Any, MyTypeAliasForwardRef]:
    if type_params := getattr(obj, "__type_params__", None):
        localns = {**localns, **{p.__name__: p for p in type_params}}
    parts = (getattr(obj, "__qualname__", "") or "").split(".")
    if len(parts) <= 1:
        return localns
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
                localns = {**localns, part: current}
            if ancestor_params := getattr(current, "__type_params__", None):
                localns = {**localns, **{p.__name__: p for p in ancestor_params}}
    return localns


def _future_annotations_imported(obj: Any) -> bool:
    annotations_ = getattr(inspect.getmodule(obj), "annotations", None)
    if annotations_ is None:
        return False
    return bool(annotations_.compiler_flag == 0x1000000)  # noqa: PLR2004


__all__ = ["get_all_type_hints"]
