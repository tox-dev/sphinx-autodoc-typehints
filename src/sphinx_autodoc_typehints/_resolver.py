"""
Type hint resolution and backfilling from source annotations.

Resolves type hints for documented objects by executing ``TYPE_CHECKING``-guarded imports,
handling forward references via ``annotationlib`` on Python 3.14+, and falling back to
AST-based type comment parsing when runtime annotations are unavailable.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import re
import sys
import textwrap
import types
from pathlib import Path
from typing import TYPE_CHECKING, Any, get_type_hints

from sphinx.ext.autodoc.mock import mock
from sphinx.util import logging

from ._annotations import MyTypeAliasForwardRef

if sys.version_info >= (3, 14):
    import annotationlib

if TYPE_CHECKING:
    from ast import AsyncFunctionDef, FunctionDef, Module, stmt

    from sphinx.environment import BuildEnvironment

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
        result = backfill_type_hints(obj, name)
        if not result:
            result = _backfill_from_stub(obj)
        try:
            obj.__annotations__ = result
        except (AttributeError, TypeError):
            pass
        else:
            result = _get_type_hint(autodoc_mock_imports, name, obj, localns)
    return result


def _get_type_hint(
    autodoc_mock_imports: list[str], name: str, obj: Any, localns: dict[Any, MyTypeAliasForwardRef]
) -> dict[str, Any]:
    _resolve_type_guarded_imports(autodoc_mock_imports, obj)
    localns = _add_type_params_to_localns(obj, localns)
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


def _add_type_params_to_localns(
    obj: Any, localns: dict[Any, MyTypeAliasForwardRef]
) -> dict[Any, MyTypeAliasForwardRef]:
    if type_params := getattr(obj, "__type_params__", None):
        localns = {**localns, **{p.__name__: p for p in type_params}}
    qualname = getattr(obj, "__qualname__", "") or ""
    parts = qualname.rsplit(".", 1)
    if len(parts) > 1:
        parent_name = parts[0]
        ns = getattr(obj, "__globals__", None)
        if ns is None:
            module = inspect.getmodule(obj)
            ns = vars(module) if module else None
        if ns and (parent := ns.get(parent_name)) and (parent_params := getattr(parent, "__type_params__", None)):
            localns = {**localns, **{p.__name__: p for p in parent_params}}
    return localns


def _future_annotations_imported(obj: Any) -> bool:
    annotations_ = getattr(inspect.getmodule(obj), "annotations", None)
    if annotations_ is None:
        return False
    return bool(annotations_.compiler_flag == 0x1000000)  # noqa: PLR2004


def backfill_type_hints(obj: Any, name: str) -> dict[str, Any]:  # noqa: C901, PLR0911
    parse_kwargs = {"type_comments": True}

    def _one_child(module: Module) -> stmt | None:
        children = module.body
        if len(children) != 1:
            _LOGGER.warning(
                'Did not get exactly one node from AST for "%s", got %s',
                name,
                len(children),
                type="sphinx_autodoc_typehints",
                subtype="multiple_ast_nodes",
                location=get_obj_location(obj),
            )
            return None
        return children[0]

    try:
        code = textwrap.dedent(normalize_source_lines(inspect.getsource(obj)))
        obj_ast = ast.parse(code, **parse_kwargs)  # type: ignore[call-overload]  # dynamic kwargs
    except (OSError, TypeError, SyntaxError):
        return {}

    obj_ast = _one_child(obj_ast)
    if obj_ast is None:
        return {}

    try:
        type_comment = obj_ast.type_comment  # type: ignore[attr-defined]
    except AttributeError:
        return {}

    if not type_comment:
        return {}

    try:
        comment_args_str, comment_returns = type_comment.split(" -> ")
    except ValueError:
        _LOGGER.warning(
            'Unparseable type hint comment for "%s": Expected to contain ` -> `',
            name,
            type="sphinx_autodoc_typehints",
            subtype="comment",
            location=get_obj_location(obj),
        )
        return {}

    rv = {}
    if comment_returns:
        rv["return"] = comment_returns

    args = _load_args(obj_ast)  # type: ignore[arg-type]
    comment_args = split_type_comment_args(comment_args_str)
    is_inline = len(comment_args) == 1 and comment_args[0] == "..."
    if not is_inline:
        if args and args[0].arg in {"self", "cls"} and len(comment_args) != len(args):
            comment_args.insert(0, None)

        if len(args) != len(comment_args):
            _LOGGER.warning(
                'Not enough type comments found on "%s"',
                name,
                type="sphinx_autodoc_typehints",
                subtype="comment",
                location=get_obj_location(obj),
            )
            return rv

    for at, arg in enumerate(args):
        value = getattr(arg, "type_comment", None) if is_inline else comment_args[at]
        if value is not None:
            rv[arg.arg] = value

    return rv


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


def normalize_source_lines(source_lines: str) -> str:
    lines = source_lines.split("\n")

    def remove_prefix(text: str, prefix: str) -> str:
        return text[text.startswith(prefix) and len(prefix) :]

    for pos, line in enumerate(lines):
        if line.lstrip().startswith("def "):
            idx = pos
            whitespace_separator = "def"
            break
        if line.lstrip().startswith("async def"):
            idx = pos
            whitespace_separator = "async def"
            break

    else:
        return "\n".join(lines)
    fn_def = lines[idx]

    whitespace = fn_def.split(whitespace_separator)[0]

    aligned_prefix = [whitespace + remove_prefix(s, whitespace) for s in lines[:idx]]
    aligned_suffix = [whitespace + remove_prefix(s, whitespace) for s in lines[idx + 1 :]]

    aligned_prefix.append(fn_def)
    return "\n".join(aligned_prefix + aligned_suffix)


def _load_args(obj_ast: FunctionDef | AsyncFunctionDef) -> list[Any]:
    func_args = obj_ast.args
    args = []
    pos_only = getattr(func_args, "posonlyargs", None)
    if pos_only:
        args.extend(pos_only)

    args.extend(func_args.args)
    if func_args.vararg:
        args.append(func_args.vararg)

    args.extend(func_args.kwonlyargs)
    if func_args.kwarg:
        args.append(func_args.kwarg)

    return args


def split_type_comment_args(comment: str) -> list[str | None]:
    def add(val: str) -> None:
        result.append(val.strip().lstrip("*"))

    comment = comment.strip().lstrip("(").rstrip(")")
    result: list[str | None] = []
    if not comment:
        return result

    brackets, start_arg_at, at = 0, 0, 0
    for at, char in enumerate(comment):
        if char in {"[", "("}:
            brackets += 1
        elif char in {"]", ")"}:
            brackets -= 1
        elif char == "," and brackets == 0:
            add(comment[start_arg_at:at])
            start_arg_at = at + 1

    add(comment[start_arg_at : at + 1])
    return result


_STUB_AST_CACHE: dict[Path, ast.Module | None] = {}


def _backfill_from_stub(obj: Any) -> dict[str, str]:
    if (stub_path := _find_stub_path(obj)) and (tree := _parse_stub_ast(stub_path)):
        return _extract_annotations_from_stub(tree, obj)
    return {}


def _find_stub_path(obj: Any) -> Path | None:
    module = inspect.getmodule(obj)
    if module is None:
        return None
    try:
        source_file = inspect.getfile(module)
    except TypeError:
        return None
    stub = Path(source_file).with_suffix(".pyi")
    if stub.is_file():
        return stub
    if hasattr(module, "__path__"):
        for pkg_dir in module.__path__:
            init_stub = Path(pkg_dir) / "__init__.pyi"
            if init_stub.is_file():
                return init_stub
    return None


def _parse_stub_ast(stub_path: Path) -> ast.Module | None:
    if stub_path not in _STUB_AST_CACHE:
        try:
            _STUB_AST_CACHE[stub_path] = ast.parse(stub_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            _STUB_AST_CACHE[stub_path] = None
    return _STUB_AST_CACHE[stub_path]


def _extract_annotations_from_stub(tree: ast.Module, obj: Any) -> dict[str, str]:
    qualname = getattr(obj, "__qualname__", None)
    if not qualname:
        return {}
    parts = qualname.split(".")
    if (node := _find_ast_node(tree.body, parts)) is None:
        return {}
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return _extract_func_annotations(node)
    if isinstance(node, ast.ClassDef):
        return _extract_class_annotations(node)
    return {}


def _find_ast_node(body: list[ast.stmt], parts: list[str]) -> ast.stmt | None:
    target, *rest = parts
    for node in body:
        if isinstance(node, ast.ClassDef) and node.name == target:
            return _find_ast_node(node.body, rest) if rest else node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target and not rest:
            return node
    return None


def _extract_func_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str]:
    result: dict[str, str] = {}
    for arg in _load_args(node):
        if arg.annotation is not None:
            result[arg.arg] = ast.unparse(arg.annotation)
    if node.returns is not None:
        result["return"] = ast.unparse(node.returns)
    return result


def _extract_class_annotations(node: ast.ClassDef) -> dict[str, str]:
    result: dict[str, str] = {}
    for child in node.body:
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            result[child.target.id] = ast.unparse(child.annotation)
    return result


def _collect_documented_type_aliases(
    obj: Any, module_prefix: str, env: BuildEnvironment
) -> tuple[dict[str, MyTypeAliasForwardRef], dict[int, MyTypeAliasForwardRef]]:
    raw_annotations = getattr(obj, "__annotations__", {})
    if not raw_annotations:
        return {}, {}

    py_objects = env.get_domain("py").objects  # ty: ignore[unresolved-attribute]
    deferred: dict[str, MyTypeAliasForwardRef] = {}
    eager: dict[int, MyTypeAliasForwardRef] = {}
    obj_globals = getattr(obj, "__globals__", {})

    for annotation in raw_annotations.values():
        if isinstance(annotation, str):
            if _is_documented_type(annotation, module_prefix, py_objects):
                deferred[annotation] = MyTypeAliasForwardRef(annotation)
        else:
            for var_name, var_value in obj_globals.items():
                if (
                    var_value is annotation
                    and not var_name.startswith("_")
                    and _is_documented_type(var_name, module_prefix, py_objects)
                ):
                    eager[id(annotation)] = MyTypeAliasForwardRef(var_name)

    return deferred, eager


def _is_documented_type(name: str, module_prefix: str, py_objects: dict[str, Any]) -> bool:
    return any(
        candidate in py_objects and py_objects[candidate].objtype == "type"
        for candidate in (f"{module_prefix}.{name}", name)
    )
