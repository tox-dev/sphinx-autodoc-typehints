"""Stub file (.pyi) annotation backfill."""

from __future__ import annotations

import ast
import contextlib
import importlib
import inspect
import sys
from copy import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, ParamSpec, TypeVar, TypeVarTuple, cast

from sphinx.ext.autodoc.mock import mock

from ._type_comments import _load_args

if TYPE_CHECKING:
    import types
    from collections.abc import Callable, Iterator

_STUB_AST_CACHE: dict[tuple[Path, int], ast.Module | None] = {}


def _backfill_from_stub(obj: Any) -> dict[str, str]:
    if (path := stub_path(obj)) and (tree := _parse_stub_ast(path)):
        return _extract_annotations_from_stub(tree, obj)
    return {}


def _get_stub_context(obj: Any) -> tuple[dict[str, Any], set[str], str]:
    """
    Return (localns, crossref_names, owner_module_name) from the stub owning *obj*.

    Single lookup avoids duplicate ``_find_stub_owner`` / ``_parse_stub_ast`` calls. The owner module name lets callers
    use ``vars(sys.modules[name])`` as the correct globalns — important when a C extension function lives in a child
    module but its stub belongs to a parent package (e.g. ``cbor2._cbor2.dumps`` → ``cbor2/__init__.pyi``).

    Crossref names are the stub's type aliases plus every name it imports that has no runtime counterpart, such as
    numpy's ``_SeriesLikeCoef_co`` living in the stub-only ``numpy/polynomial/_polytypes.pyi``. Both render as a plain
    cross-reference instead of failing to evaluate.
    """
    if (info := _find_stub_owner(obj)) is None:
        return {}, set(), ""
    path, owner_module = info
    if (tree := _parse_stub_ast(path)) is None:
        return {}, set(), ""
    ns: dict[str, Any] = dict(vars(owner_module))
    resolved, unresolved = _resolve_stub_imports(tree, _stub_owner_package(owner_module, path))
    ns.update(resolved)
    ns.update(_stub_type_params(tree, obj))
    return ns, _extract_type_alias_names(tree) | (unresolved - ns.keys()), owner_module.__name__


_TYPE_PARAM_FACTORIES: Final[dict[type[ast.type_param], Callable[[str], TypeVar | ParamSpec | TypeVarTuple]]] = {
    ast.TypeVar: TypeVar,
    ast.ParamSpec: ParamSpec,
    ast.TypeVarTuple: TypeVarTuple,
}


def _stub_type_params(tree: ast.Module, obj: Any) -> dict[str, TypeVar | ParamSpec | TypeVarTuple]:
    result: dict[str, TypeVar | ParamSpec | TypeVarTuple] = {}
    parts = str(getattr(obj, "__qualname__", "")).split(".")
    for depth in range(1, len(parts) + 1):
        if isinstance(
            node := _find_ast_node(tree.body, parts[:depth]), ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            for param in cast("list[ast.TypeVar | ast.ParamSpec | ast.TypeVarTuple]", node.type_params):
                result[param.name] = _TYPE_PARAM_FACTORIES[type(param)](param.name)
    return result


def _stub_owner_package(owner_module: types.ModuleType, path: Path) -> str:
    # Native submodules expose ``__package__ = None``; derive the package from the stub's name
    # so relative imports inside ``<child>.pyi`` resolve relative to its parent package.
    if owner_package := getattr(owner_module, "__package__", None):
        return owner_package
    owner_name = owner_module.__name__
    if path.name == "__init__.pyi":
        return owner_name
    return owner_name.rpartition(".")[0]


def _resolve_stub_imports(tree: ast.Module, owner_package: str = "") -> tuple[dict[str, Any], set[str]]:
    ns: dict[str, Any] = {}
    unresolved: set[str] = set()
    _resolve_stub_imports_from_body(tree.body, owner_package, ns, unresolved)
    _resolve_stub_definitions(tree.body, ns)
    return ns, unresolved - ns.keys()


def _resolve_stub_imports_from_body(
    body: list[ast.stmt], owner_package: str, ns: dict[str, Any], unresolved: set[str]
) -> None:
    for node in body:
        if isinstance(node, ast.Import):
            _resolve_import_node(node, ns)
        elif isinstance(node, ast.ImportFrom):
            _resolve_import_from_node(node, owner_package, ns, unresolved)
        elif isinstance(node, ast.If):
            _resolve_stub_imports_from_body(node.body, owner_package, ns, unresolved)
            _resolve_stub_imports_from_body(node.orelse, owner_package, ns, unresolved)


_STUB_DEFINITION_TYPES = (ast.Assign, ast.AnnAssign, ast.ClassDef, ast.TypeAlias)


def _resolve_stub_definitions(body: list[ast.stmt], ns: dict[str, Any]) -> None:
    for node in body:
        if isinstance(node, _STUB_DEFINITION_TYPES):
            exec_node = _strip_class_decorators(node) if isinstance(node, ast.ClassDef) else node
            with contextlib.suppress(Exception):
                exec(compile(ast.Module(body=[exec_node], type_ignores=[]), "<stub>", "exec"), ns)  # ruff:ignore[exec-builtin]
        elif isinstance(node, ast.If):
            _resolve_stub_definitions(node.body, ns)
            _resolve_stub_definitions(node.orelse, ns)


def _strip_class_decorators(node: ast.ClassDef) -> ast.ClassDef:
    if not node.decorator_list:
        return node
    stripped = copy(node)
    stripped.decorator_list = []
    return stripped


def _resolve_import_node(node: ast.Import, ns: dict[str, Any]) -> None:
    for alias in node.names:
        if (module := _import_for_stub(alias.name, top=not alias.asname)) is not None:
            ns[alias.asname or alias.name.partition(".")[0]] = module


def _import_for_stub(name: str, *, top: bool) -> types.ModuleType | None:
    """
    Import a module a stub imports, returning it or, with ``top``, its top-level package, as ``import a.b`` binds.

    A stub may import a module only type checkers need, so a missing one is mocked as ``autodoc_mock_imports`` would,
    while a module that exists but fails to import binds nothing.
    """
    mocked: list[str] = []
    try:
        importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name is None or (name != exc.name and not name.startswith(f"{exc.name}.")):
            return None
        mocked.append(exc.name)
    except ImportError:
        return None
    with mock(mocked):
        module = importlib.import_module(name)
        return sys.modules[name.partition(".")[0]] if top else module


def _resolve_import_from_node(
    node: ast.ImportFrom, owner_package: str, ns: dict[str, Any], unresolved: set[str]
) -> None:
    module_name = _resolve_import_from(node, owner_package)
    mod = _import_module_or_none(module_name) if module_name else None
    for alias in node.names:
        if alias.name == "*":
            continue
        name = alias.asname or alias.name
        if mod is not None and (
            (val := getattr(mod, alias.name, None)) is not None
            or (val := _import_module_or_none(f"{module_name}.{alias.name}")) is not None
        ):
            ns[name] = val
        else:
            unresolved.add(name)


def _import_module_or_none(module_name: str) -> types.ModuleType | None:
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def _resolve_import_from(node: ast.ImportFrom, owner_package: str) -> str | None:
    if not node.level:
        return node.module or None
    if not owner_package:
        return node.module or None
    parts = owner_package.rsplit(".", node.level - 1)
    if len(parts) < node.level:
        return None
    base = parts[0]
    return f"{base}.{node.module}" if node.module else base


def _get_module(obj: Any) -> types.ModuleType | None:
    if module := inspect.getmodule(obj):
        return module
    # inspect.getmodule returns None for some C/Rust extension descriptors even when __module__ is valid.
    if (mod_name := getattr(obj, "__module__", None)) and (module := sys.modules.get(mod_name)):
        return module
    # Method descriptors on C extension types expose the owning class via __objclass__.
    if (owner_cls := getattr(obj, "__objclass__", None)) and (module := inspect.getmodule(owner_cls)):
        return module
    # Bound methods like __new__ on C extension classes have __self__ pointing to the class.
    if (owner_cls := getattr(obj, "__self__", None)) and inspect.isclass(owner_cls):
        return inspect.getmodule(owner_cls)
    return None


def stub_path(obj: Any) -> Path | None:
    """Return the stub file describing ``obj``, whose edits change what its documentation shows."""
    return info[0] if (info := _find_stub_owner(obj)) else None


def _find_stub_owner(obj: Any) -> tuple[Path, types.ModuleType] | None:
    if (module := _get_module(obj)) is None:
        return None
    if result := _find_stub_for_module(module):
        return result, module
    # PEP 561 re-export pattern: cbor2.__init__.pyi documents functions living in cbor2._cbor2 (C/Rust). Walk up to
    # find the parent package whose stub describes the re-exported public API; a parent only describes the objects it
    # re-exports, so the same name there must be this very object. Names are read statically: a package's lazy
    # ``__getattr__`` imports on access and may raise, or rewrite ``__module__`` so autodoc skips the class as imported.
    top_name = str(getattr(obj, "__qualname__", "")).partition(".")[0]
    if (defined := inspect.getattr_static(module, top_name, None)) is None:
        return None
    module_name = module.__name__
    while "." in module_name:
        module_name = module_name.rsplit(".", 1)[0]
        if (
            (parent := sys.modules.get(module_name))
            and (result := _find_stub_for_module(parent))
            and inspect.getattr_static(parent, top_name, None) is defined
        ):
            return result, parent
    return None


def _find_stub_for_module(module: types.ModuleType) -> Path | None:
    # a module lacking an attribute hands the lookup to its ``__getattr__``
    if not (source_file := _module_attribute(module, "__file__")):
        return _find_native_submodule_stub(module)
    source = Path(source_file)
    if (stub := source.with_name(f"{source.name.split('.')[0]}.pyi")).is_file():
        return stub
    for pkg_dir in _module_attribute(module, "__path__") or ():
        if (init_stub := Path(pkg_dir) / "__init__.pyi").is_file():
            return init_stub
    return None


def _module_attribute(module: types.ModuleType, name: str) -> Any:
    """Read a module attribute without its ``__getattr__``, through the property a module subclass may define."""
    if not inspect.isdatadescriptor(value := inspect.getattr_static(module, name, None)):
        return value
    # calling the getter directly skips the fallback to __getattr__ that getattr takes when it raises AttributeError
    try:
        return value.__get__(module, type(module))
    except AttributeError:
        return None


def _find_native_submodule_stub(module: types.ModuleType) -> Path | None:
    """Locate the sibling ``.pyi`` for a PyO3-style submodule registered via ``PyModule_AddObject``."""
    name = getattr(module, "__name__", "")
    parent_name, _, child = name.rpartition(".")
    if not parent_name or (parent := sys.modules.get(parent_name)) is None:
        return None
    for pkg_dir in getattr(parent, "__path__", []) or []:
        pkg_path = Path(pkg_dir)
        if (stub := pkg_path / f"{child}.pyi").is_file():
            return stub
        if (init_stub := pkg_path / child / "__init__.pyi").is_file():
            return init_stub
    return None


def _parse_stub_ast(path: Path) -> ast.Module | None:
    # keyed on the modification time too, so a stub edited while the process runs is read again
    try:
        key = (path, path.stat().st_mtime_ns)
    except OSError:
        return None
    if key not in _STUB_AST_CACHE:
        try:
            _STUB_AST_CACHE[key] = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            _STUB_AST_CACHE[key] = None
    return _STUB_AST_CACHE[key]


_TYPE_ALIAS_ANNOTATIONS = {"TypeAlias", "typing.TypeAlias", "typing_extensions.TypeAlias"}


def _extract_type_alias_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.annotation, ast.Name | ast.Attribute)
            and ast.unparse(node.annotation) in _TYPE_ALIAS_ANNOTATIONS
        ):
            names.add(node.target.id)
        elif isinstance(node, ast.TypeAlias) and isinstance(node.name, ast.Name):
            names.add(node.name.id)
    return names


def _extract_annotations_from_stub(tree: ast.Module, obj: Any) -> dict[str, str]:
    qualname = getattr(obj, "__qualname__", None)
    if not qualname:
        return {}
    if not (nodes := _find_ast_nodes(tree.body, qualname.split("."))):
        return {}
    if isinstance(nodes[0], ast.ClassDef):
        return _extract_class_annotations(nodes[0])
    # a property's setter and deleter share its name but not its type, which the getter alone carries
    variants = [
        node
        for node in nodes
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not any(
            ast.unparse(decorator) in {f"{node.name}.setter", f"{node.name}.deleter"}
            for decorator in node.decorator_list
        )
    ]
    # overload variants describe one function together; an implementation signature, when given, says it directly
    implementations = [node for node in variants if not _is_overload(node)]
    return _merge_annotations([_extract_func_annotations(node) for node in implementations or variants])


def _find_ast_node(body: list[ast.stmt], parts: list[str]) -> ast.stmt | None:
    return next(iter(_find_ast_nodes(body, parts)), None)


def _find_ast_nodes(body: list[ast.stmt], parts: list[str]) -> list[ast.stmt]:
    target, *rest = parts
    functions: list[ast.stmt] = []
    for node in _live_statements(body):
        if isinstance(node, ast.ClassDef) and node.name == target:
            return _find_ast_nodes(node.body, rest) if rest else [node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target and not rest:
            functions.append(node)
    return functions


def _live_statements(body: list[ast.stmt]) -> Iterator[ast.stmt]:
    """Stubs gate definitions on the Python version or platform, so follow the branch this interpreter takes."""
    for node in body:
        if not isinstance(node, ast.If):
            yield node
            continue
        try:
            live = eval(  # ruff:ignore[suspicious-eval-usage]  # nothing but sys is in scope
                compile(ast.Expression(node.test), "<stub>", "eval"), {"__builtins__": {}, "sys": sys}
            )
        except Exception:  # ruff:ignore[blind-except]  # a condition on something else keeps both branches
            yield from _live_statements([*node.body, *node.orelse])
        else:
            yield from _live_statements(node.body if live else node.orelse)


def _is_overload(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(ast.unparse(decorator) in {"overload", "typing.overload"} for decorator in node.decorator_list)


def _merge_annotations(variants: list[dict[str, str]]) -> dict[str, str]:
    """Union the shared parameters' types, since the implementation accepts whatever any variant does."""
    return {
        name: " | ".join(dict.fromkeys(variant[name] for variant in variants))
        for name in variants[0]
        if all(name in variant for variant in variants)
    }


def _extract_func_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str]:
    result: dict[str, str] = {}
    for arg in _load_args(node):
        if arg.annotation is not None:
            result[arg.arg] = ast.unparse(arg.annotation)
    if node.returns is not None:
        result["return"] = ast.unparse(node.returns)
    return result


def _backfill_descriptor_annotation(obj: Any) -> str | None:
    """
    Return the stub annotation string for a C data descriptor, or ``None``.

    getset and member descriptors carry no runtime annotations, so their type
    can only come from the owning class's stub: either a ``@property`` return
    annotation or a class-level annotated assignment with the same name.
    """
    objclass = getattr(obj, "__objclass__", None)
    name = getattr(obj, "__name__", None)
    if objclass is None or not name:
        return None
    if (path := stub_path(obj)) is None or (tree := _parse_stub_ast(path)) is None:
        return None
    node = _find_ast_node(tree.body, objclass.__qualname__.split("."))
    if not isinstance(node, ast.ClassDef):
        return None
    members: list[ast.stmt] = list(node.body)
    while members:
        member = members.pop()
        if isinstance(member, ast.If):
            # stubs guard members behind `if sys.version_info >= ...` blocks (numpy's ndarray does)
            members.extend(member.body)
            members.extend(member.orelse)
            continue
        if isinstance(member, ast.AnnAssign) and isinstance(member.target, ast.Name) and member.target.id == name:
            return ast.unparse(member.annotation)
        if not isinstance(member, ast.FunctionDef) or member.name != name or member.returns is None:
            continue
        if any(isinstance(decorator, ast.Name) and decorator.id == "property" for decorator in member.decorator_list):
            return ast.unparse(member.returns)
    return None


def _extract_class_annotations(node: ast.ClassDef) -> dict[str, str]:
    result: dict[str, str] = {}
    for child in _live_statements(node.body):
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            result[child.target.id] = ast.unparse(child.annotation)
    return result


__all__ = ["stub_path"]
