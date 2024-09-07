"""Sphinx autodoc type hints."""

from __future__ import annotations

import ast
import importlib
import inspect
import re
import sys
import textwrap
import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AnyStr, ForwardRef, NewType, TypeVar, get_type_hints

from docutils import nodes
from docutils.frontend import OptionParser
from sphinx.ext.autodoc.mock import mock
from sphinx.parsers import RSTParser
from sphinx.util import logging, rst
from sphinx.util.inspect import TypeAliasForwardRef, TypeAliasNamespace, stringify_signature
from sphinx.util.inspect import signature as sphinx_signature

from ._parser import parse
from .patches import install_patches
from .version import __version__

if TYPE_CHECKING:
    from ast import FunctionDef, Module, stmt
    from collections.abc import Callable

    from docutils.nodes import Node
    from docutils.parsers.rst import states
    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment
    from sphinx.ext.autodoc import Options

_LOGGER = logging.getLogger(__name__)
_PYDATA_ANNOTATIONS = {"Any", "AnyStr", "Callable", "ClassVar", "Literal", "NoReturn", "Optional", "Tuple", "Union"}

# types has a bunch of things like ModuleType where ModuleType.__module__ is
# "builtins" and ModuleType.__name__ is "module", so we have to check for this.
_TYPES_DICT = {getattr(types, name): name for name in types.__all__}
# Prefer FunctionType to LambdaType (they are synonymous)
_TYPES_DICT[types.FunctionType] = "FunctionType"


def _get_types_type(obj: Any) -> str | None:
    try:
        return _TYPES_DICT.get(obj)
    except Exception:  # noqa: BLE001
        # e.g. exception: unhashable type
        return None


def get_annotation_module(annotation: Any) -> str:
    """
    Get module for an annotation.

    :param annotation:
    :return:
    """
    if annotation is None:
        return "builtins"
    if _get_types_type(annotation) is not None:
        return "types"
    is_new_type = sys.version_info >= (3, 10) and isinstance(annotation, NewType)
    if (
        is_new_type
        or isinstance(annotation, TypeVar)
        or type(annotation).__name__ in {"ParamSpec", "ParamSpecArgs", "ParamSpecKwargs"}
    ):
        return "typing"
    if hasattr(annotation, "__module__"):
        return annotation.__module__  # type: ignore[no-any-return]
    if hasattr(annotation, "__origin__"):
        return annotation.__origin__.__module__  # type: ignore[no-any-return]
    msg = f"Cannot determine the module of {annotation}"
    raise ValueError(msg)


def _is_newtype(annotation: Any) -> bool:
    return isinstance(annotation, NewType)


def get_annotation_class_name(annotation: Any, module: str) -> str:  # noqa: C901, PLR0911
    """
    Get class name for annotation.

    :param annotation:
    :param module:
    :return:
    """
    # Special cases
    if annotation is None:
        return "None"
    if annotation is AnyStr:
        return "AnyStr"
    val = _get_types_type(annotation)
    if val is not None:
        return val
    if _is_newtype(annotation):
        return "NewType"

    if getattr(annotation, "__qualname__", None):
        return annotation.__qualname__  # type: ignore[no-any-return]
    if getattr(annotation, "_name", None):  # Required for generic aliases on Python 3.7+
        return annotation._name  # type: ignore[no-any-return]  # noqa: SLF001
    if module in {"typing", "typing_extensions"} and isinstance(getattr(annotation, "name", None), str):
        # Required for at least Pattern and Match
        return annotation.name  # type: ignore[no-any-return]

    origin = getattr(annotation, "__origin__", None)
    if origin:
        if getattr(origin, "__qualname__", None):  # Required for Protocol subclasses
            return origin.__qualname__  # type: ignore[no-any-return]
        if getattr(origin, "_name", None):  # Required for Union on Python 3.7+
            return origin._name  # type: ignore[no-any-return]  # noqa: SLF001

    annotation_cls = annotation if inspect.isclass(annotation) else type(annotation)
    return annotation_cls.__qualname__.lstrip("_")


def get_annotation_args(annotation: Any, module: str, class_name: str) -> tuple[Any, ...]:  # noqa: PLR0911
    """
    Get annotation arguments.

    :param annotation:
    :param module:
    :param class_name:
    :return:
    """
    try:
        original = getattr(sys.modules[module], class_name)
    except (KeyError, AttributeError):
        pass
    else:
        if annotation is original:
            return ()  # This is the original, not parametrized type

    # Special cases
    if class_name in {"Pattern", "Match"} and hasattr(annotation, "type_var"):  # Python < 3.7
        return (annotation.type_var,)
    if class_name == "ClassVar" and hasattr(annotation, "__type__"):  # ClassVar on Python < 3.7
        return (annotation.__type__,)
    if class_name == "TypeVar" and hasattr(annotation, "__constraints__"):
        return annotation.__constraints__  # type: ignore[no-any-return]
    if class_name == "NewType" and hasattr(annotation, "__supertype__"):
        return (annotation.__supertype__,)
    if class_name == "Literal" and hasattr(annotation, "__values__"):
        return annotation.__values__  # type: ignore[no-any-return]
    if class_name == "Generic":
        return annotation.__parameters__  # type: ignore[no-any-return]
    result = getattr(annotation, "__args__", ())
    # 3.10 and earlier Tuple[()] returns ((), ) instead of () the tuple does
    return () if len(result) == 1 and result[0] == () else result  # type: ignore[misc]


def format_internal_tuple(t: tuple[Any, ...], config: Config) -> str:
    # An annotation can be a tuple, e.g., for nptyping:
    # In this case, format_annotation receives:
    # This solution should hopefully be general for *any* type that allows tuples in annotations
    fmt = [format_annotation(a, config) for a in t]
    if len(fmt) == 0:
        return "()"
    if len(fmt) == 1:
        return f"({fmt[0]}, )"
    return f"({', '.join(fmt)})"


def fixup_module_name(config: Config, module: str) -> str:
    if getattr(config, "typehints_fixup_module_name", None):
        module = config.typehints_fixup_module_name(module)

    if module == "typing_extensions":
        module = "typing"

    if module == "_io":
        module = "io"
    return module


def format_annotation(annotation: Any, config: Config) -> str:  # noqa: C901, PLR0911, PLR0912, PLR0915, PLR0914
    """
    Format the annotation.

    :param annotation:
    :param config:
    :return:
    """
    typehints_formatter: Callable[..., str] | None = getattr(config, "typehints_formatter", None)
    if typehints_formatter is not None:
        formatted = typehints_formatter(annotation, config)
        if formatted is not None:
            return formatted

    # Special cases
    if isinstance(annotation, ForwardRef):
        return annotation.__forward_arg__
    if annotation is None or annotation is type(None):
        return ":py:obj:`None`"
    if annotation is Ellipsis:
        return ":py:data:`...<Ellipsis>`"

    if isinstance(annotation, tuple):
        return format_internal_tuple(annotation, config)

    if isinstance(annotation, TypeAliasForwardRef):
        return str(annotation)

    try:
        module = get_annotation_module(annotation)
        class_name = get_annotation_class_name(annotation, module)
        args = get_annotation_args(annotation, module, class_name)
    except ValueError:
        return str(annotation).strip("'")

    module = fixup_module_name(config, module)
    full_name = f"{module}.{class_name}" if module != "builtins" else class_name
    fully_qualified: bool = getattr(config, "typehints_fully_qualified", False)
    prefix = "" if fully_qualified or full_name == class_name else "~"
    role = "data" if module == "typing" and class_name in _PYDATA_ANNOTATIONS else "class"
    args_format = "\\[{}]"
    formatted_args: str | None = ""

    always_use_bars_union: bool = getattr(config, "always_use_bars_union", True)
    is_bars_union = full_name == "types.UnionType" or (
        always_use_bars_union and type(annotation).__qualname__ == "_UnionGenericAlias"
    )
    if is_bars_union:
        full_name = ""

    # Some types require special handling
    if full_name == "typing.NewType":
        args_format = f"\\(``{annotation.__name__}``, {{}})"
        role = "class" if sys.version_info >= (3, 10) else "func"
    elif full_name in {"typing.TypeVar", "typing.ParamSpec"}:
        params = {k: getattr(annotation, f"__{k}__") for k in ("bound", "covariant", "contravariant")}
        params = {k: v for k, v in params.items() if v}
        if "bound" in params:
            params["bound"] = f" {format_annotation(params['bound'], config)}"
        args_format = f"\\(``{annotation.__name__}``{', {}' if args else ''}"
        if params:
            args_format += "".join(f", {k}={v}" for k, v in params.items())
        args_format += ")"
        formatted_args = None if args else args_format
    elif full_name == "typing.Optional":
        args = tuple(x for x in args if x is not type(None))
    elif full_name in {"typing.Union", "types.UnionType"} and type(None) in args:
        if len(args) == 2:  # noqa: PLR2004
            full_name = "typing.Optional"
            role = "data"
            args = tuple(x for x in args if x is not type(None))
        else:
            simplify_optional_unions: bool = getattr(config, "simplify_optional_unions", True)
            if not simplify_optional_unions:
                full_name = "typing.Optional"
                role = "data"
                args_format = f"\\[:py:data:`{prefix}typing.Union`\\[{{}}]]"
                args = tuple(x for x in args if x is not type(None))
    elif full_name in {"typing.Callable", "collections.abc.Callable"} and args and args[0] is not ...:
        fmt = [format_annotation(arg, config) for arg in args]
        formatted_args = f"\\[\\[{', '.join(fmt[:-1])}], {fmt[-1]}]"
    elif full_name == "typing.Literal":
        formatted_args = f"\\[{', '.join(f'``{arg!r}``' for arg in args)}]"
    elif is_bars_union:
        return " | ".join([format_annotation(arg, config) for arg in args])

    if args and not formatted_args:
        try:
            iter(args)
        except TypeError:
            fmt = [format_annotation(args, config)]
        else:
            fmt = [format_annotation(arg, config) for arg in args]
        formatted_args = args_format.format(", ".join(fmt))

    escape = "\\ " if formatted_args else ""
    return f":py:{role}:`{prefix}{full_name}`{escape}{formatted_args}"


# reference: https://github.com/pytorch/pytorch/pull/46548/files
def normalize_source_lines(source_lines: str) -> str:
    """
    Normalize the source lines.

    It finds the indentation level of the function definition (`def`), then it indents all lines in the function body to
    a point at or greater than that level. This allows for comments and continued string literals that are at a lower
    indentation than the rest of the code.

    :param source_lines: source code
    :return: source lines that have been correctly aligned
    """
    lines = source_lines.split("\n")

    def remove_prefix(text: str, prefix: str) -> str:
        return text[text.startswith(prefix) and len(prefix) :]

    # Find the line and line number containing the function definition
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

    # Get a string representing the amount of leading whitespace
    whitespace = fn_def.split(whitespace_separator)[0]

    # Add this leading whitespace to all lines before and after the `def`
    aligned_prefix = [whitespace + remove_prefix(s, whitespace) for s in lines[:idx]]
    aligned_suffix = [whitespace + remove_prefix(s, whitespace) for s in lines[idx + 1 :]]

    # Put it together again
    aligned_prefix.append(fn_def)
    return "\n".join(aligned_prefix + aligned_suffix)


def process_signature(  # noqa: C901, PLR0913, PLR0917
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    options: Options,  # noqa: ARG001
    signature: str,  # noqa: ARG001
    return_annotation: str,  # noqa: ARG001
) -> tuple[str, None] | None:
    """
    Process the signature.

    :param app:
    :param what:
    :param name:
    :param obj:
    :param options:
    :param signature:
    :param return_annotation:
    :return:
    """
    if not callable(obj):
        return None

    original_obj = obj
    obj = getattr(obj, "__init__", getattr(obj, "__new__", None)) if inspect.isclass(obj) else obj
    if not getattr(obj, "__annotations__", None):  # when has no annotation we cannot autodoc typehints so bail
        return None

    obj = inspect.unwrap(obj)
    sph_signature = sphinx_signature(obj, type_aliases=app.config["autodoc_type_aliases"])

    if app.config.typehints_use_signature:
        parameters = list(sph_signature.parameters.values())
    else:
        parameters = [param.replace(annotation=inspect.Parameter.empty) for param in sph_signature.parameters.values()]

    # if we have parameters we may need to delete first argument that's not documented, e.g. self
    start = 0
    if parameters:
        if inspect.isclass(original_obj) or (what == "method" and name.endswith(".__init__")):
            start = 1
        elif what == "method":
            # bail if it is a local method as we cannot determine if first argument needs to be deleted or not
            if "<locals>" in obj.__qualname__ and not _is_dataclass(name, what, obj.__qualname__):
                _LOGGER.warning('Cannot handle as a local function: "%s" (use @functools.wraps)', name)
                return None
            outer = inspect.getmodule(obj)
            for class_name in obj.__qualname__.split(".")[:-1]:
                outer = getattr(outer, class_name)
            method_name = obj.__name__
            if method_name.startswith("__") and not method_name.endswith("__"):
                # when method starts with double underscore Python applies mangling -> prepend the class name
                method_name = f"_{obj.__qualname__.split('.')[-2]}{method_name}"
            method_object = outer.__dict__[method_name] if outer else obj
            if not isinstance(method_object, classmethod | staticmethod):
                start = 1

    sph_signature = sph_signature.replace(parameters=parameters[start:])
    show_return_annotation = app.config.typehints_use_signature_return
    unqualified_typehints = not getattr(app.config, "typehints_fully_qualified", False)
    return (
        stringify_signature(
            sph_signature,
            show_return_annotation=show_return_annotation,
            unqualified_typehints=unqualified_typehints,
        ).replace("\\", "\\\\"),
        None,
    )


def _is_dataclass(name: str, what: str, qualname: str) -> bool:
    # generated dataclass __init__() and class need extra checks, as the function operates on the generated class
    # and methods (not an instantiated dataclass object) it cannot be replaced by a call to
    # `dataclasses.is_dataclass()` => check manually for either generated __init__ or generated class
    return (what == "method" and name.endswith(".__init__")) or (what == "class" and qualname.endswith(".__init__"))


def _future_annotations_imported(obj: Any) -> bool:
    _annotations = getattr(inspect.getmodule(obj), "annotations", None)
    if _annotations is None:
        return False

    # Make sure that annotations is imported from __future__ - defined in cpython/Lib/__future__.py
    # annotations become strings at runtime
    future_annotations = 0x100000 if sys.version_info[0:2] == (3, 7) else 0x1000000
    return bool(_annotations.compiler_flag == future_annotations)


def get_all_type_hints(
    autodoc_mock_imports: list[str], obj: Any, name: str, localns: TypeAliasNamespace
) -> dict[str, Any]:
    result = _get_type_hint(autodoc_mock_imports, name, obj, localns)
    if not result:
        result = backfill_type_hints(obj, name)
        try:
            obj.__annotations__ = result
        except (AttributeError, TypeError):
            pass
        else:
            result = _get_type_hint(autodoc_mock_imports, name, obj, localns)
    return result


_TYPE_GUARD_IMPORT_RE = re.compile(r"\nif (typing.)?TYPE_CHECKING:[^\n]*([\s\S]*?)(?=\n\S)")
_TYPE_GUARD_IMPORTS_RESOLVED = set()
_TYPE_GUARD_IMPORTS_RESOLVED_GLOBALS_ID = set()


def _should_skip_guarded_import_resolution(obj: Any) -> bool:
    if isinstance(obj, types.ModuleType):
        return False  # Don't skip modules

    if not hasattr(obj, "__globals__"):
        return True  # Skip objects without __globals__

    if hasattr(obj, "__module__"):
        return obj.__module__ in _TYPE_GUARD_IMPORTS_RESOLVED or obj.__module__ in sys.builtin_module_names

    return id(obj.__globals__) in _TYPE_GUARD_IMPORTS_RESOLVED_GLOBALS_ID


def _execute_guarded_code(autodoc_mock_imports: list[str], obj: Any, module_code: str) -> None:
    for _, part in _TYPE_GUARD_IMPORT_RE.findall(module_code):
        guarded_code = textwrap.dedent(part)
        try:
            try:
                with mock(autodoc_mock_imports):
                    exec(guarded_code, getattr(obj, "__globals__", obj.__dict__))  # noqa: S102
            except ImportError as exc:
                # ImportError might have occurred because the module has guarded code as well,
                # so we recurse on the module.
                if exc.name:
                    _resolve_type_guarded_imports(autodoc_mock_imports, importlib.import_module(exc.name))

                    # Retry the guarded code and see if it works now after resolving all nested type guards.
                    with mock(autodoc_mock_imports):
                        exec(guarded_code, getattr(obj, "__globals__", obj.__dict__))  # noqa: S102
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Failed guarded type import with %r", exc)


def _resolve_type_guarded_imports(autodoc_mock_imports: list[str], obj: Any) -> None:
    if _should_skip_guarded_import_resolution(obj):
        return

    if hasattr(obj, "__globals__"):
        _TYPE_GUARD_IMPORTS_RESOLVED_GLOBALS_ID.add(id(obj.__globals__))

    module = inspect.getmodule(obj)

    if module:
        try:
            module_code = inspect.getsource(module)
        except (TypeError, OSError):
            ...  # no source code => no type guards
        else:
            _TYPE_GUARD_IMPORTS_RESOLVED.add(module.__name__)
            _execute_guarded_code(autodoc_mock_imports, obj, module_code)


def _get_type_hint(autodoc_mock_imports: list[str], name: str, obj: Any, localns: TypeAliasNamespace) -> dict[str, Any]:
    _resolve_type_guarded_imports(autodoc_mock_imports, obj)
    try:
        result = get_type_hints(obj, None, localns)
    except (AttributeError, TypeError, RecursionError) as exc:
        # TypeError - slot wrapper, PEP-563 when part of new syntax not supported
        # RecursionError - some recursive type definitions https://github.com/python/typing/issues/574
        if isinstance(exc, TypeError) and _future_annotations_imported(obj) and "unsupported operand type" in str(exc):
            result = obj.__annotations__
        else:
            result = {}
    except NameError as exc:
        _LOGGER.warning('Cannot resolve forward reference in type annotations of "%s": %s', name, exc)
        result = obj.__annotations__
    return result


def backfill_type_hints(obj: Any, name: str) -> dict[str, Any]:  # noqa: C901, PLR0911
    """
    Backfill type hints.

    :param obj: the object
    :param name: the name
    :return: backfilled value
    """
    parse_kwargs = {"type_comments": True}

    def _one_child(module: Module) -> stmt | None:
        children = module.body  # use the body to ignore type comments
        if len(children) != 1:
            _LOGGER.warning('Did not get exactly one node from AST for "%s", got %s', name, len(children))
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
        type_comment = obj_ast.type_comment
    except AttributeError:
        return {}

    if not type_comment:
        return {}

    try:
        comment_args_str, comment_returns = type_comment.split(" -> ")
    except ValueError:
        _LOGGER.warning('Unparseable type hint comment for "%s": Expected to contain ` -> `', name)
        return {}

    rv = {}
    if comment_returns:
        rv["return"] = comment_returns

    args = load_args(obj_ast)
    comment_args = split_type_comment_args(comment_args_str)
    is_inline = len(comment_args) == 1 and comment_args[0] == "..."
    if not is_inline:
        if args and args[0].arg in {"self", "cls"} and len(comment_args) != len(args):
            comment_args.insert(0, None)  # self/cls may be omitted in type comments, insert blank

        if len(args) != len(comment_args):
            _LOGGER.warning('Not enough type comments found on "%s"', name)
            return rv

    for at, arg in enumerate(args):
        arg_key = getattr(arg, "arg", None)
        if arg_key is None:
            continue

        value = getattr(arg, "type_comment", None) if is_inline else comment_args[at]

        if value is not None:
            rv[arg_key] = value

    return rv


def load_args(obj_ast: FunctionDef) -> list[Any]:
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
        result.append(val.strip().lstrip("*"))  # remove spaces, and var/kw arg marker

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


def format_default(app: Sphinx, default: Any, is_annotated: bool) -> str | None:  # noqa: FBT001
    if default is inspect.Parameter.empty:
        return None
    formatted = repr(default).replace("\\", "\\\\")

    if is_annotated:
        if app.config.typehints_defaults.startswith("braces"):
            return f" (default: ``{formatted}``)"
        return f", default: ``{formatted}``"
    if app.config.typehints_defaults == "braces-after":
        return f" (default: ``{formatted}``)"
    return f"default: ``{formatted}``"


def process_docstring(  # noqa: PLR0913, PLR0917
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    options: Options | None,  # noqa: ARG001
    lines: list[str],
) -> None:
    """
    Process the docstring for an entry.

    :param app: the Sphinx app
    :param what: the target
    :param name: the name
    :param obj: the object
    :param options: the options
    :param lines: the lines
    :return:
    """
    original_obj = obj
    obj = obj.fget if isinstance(obj, property) else obj
    if not callable(obj):
        return
    obj = obj.__init__ if inspect.isclass(obj) else obj
    obj = inspect.unwrap(obj)

    try:
        signature = sphinx_signature(obj, type_aliases=app.config["autodoc_type_aliases"])
    except (ValueError, TypeError):
        signature = None

    localns = TypeAliasNamespace(app.config["autodoc_type_aliases"])
    type_hints = get_all_type_hints(app.config.autodoc_mock_imports, obj, name, localns)
    app.config._annotation_globals = getattr(obj, "__globals__", {})  # noqa: SLF001
    try:
        _inject_types_to_docstring(type_hints, signature, original_obj, app, what, name, lines)
    finally:
        delattr(app.config, "_annotation_globals")


def _get_sphinx_line_keyword_and_argument(line: str) -> tuple[str, str | None] | None:
    """
    Extract a keyword, and its optional argument out of a sphinx field option line.

    For example
    >>> _get_sphinx_line_keyword_and_argument(":param parameter:")
    ("param", "parameter")
    >>> _get_sphinx_line_keyword_and_argument(":return:")
    ("return", None)
    >>> _get_sphinx_line_keyword_and_argument("some invalid line")
    None
    """
    param_line_without_description = line.split(":", maxsplit=2)
    if len(param_line_without_description) != 3:  # noqa: PLR2004
        return None

    split_directive_and_name = param_line_without_description[1].split(maxsplit=1)
    if len(split_directive_and_name) != 2:  # noqa: PLR2004
        if not len(split_directive_and_name):
            return None
        return split_directive_and_name[0], None

    return tuple(split_directive_and_name)  # type: ignore[return-value]


def _line_is_param_line_for_arg(line: str, arg_name: str) -> bool:
    """Return True if `line` is a valid parameter line for `arg_name`, false otherwise."""
    keyword_and_name = _get_sphinx_line_keyword_and_argument(line)
    if keyword_and_name is None:
        return False

    keyword, doc_name = keyword_and_name
    if doc_name is None:
        return False

    if keyword not in {"param", "parameter", "arg", "argument"}:
        return False

    return any(doc_name == prefix + arg_name for prefix in ("", "\\*", "\\**", "\\*\\*"))


def _inject_types_to_docstring(  # noqa: PLR0913, PLR0917
    type_hints: dict[str, Any],
    signature: inspect.Signature | None,
    original_obj: Any,
    app: Sphinx,
    what: str,
    name: str,
    lines: list[str],
) -> None:
    if signature is not None:
        _inject_signature(type_hints, signature, app, lines)
    if "return" in type_hints:
        _inject_rtype(type_hints, original_obj, app, what, name, lines)


def _inject_signature(
    type_hints: dict[str, Any],
    signature: inspect.Signature,
    app: Sphinx,
    lines: list[str],
) -> None:
    for arg_name in signature.parameters:
        annotation = type_hints.get(arg_name)

        default = signature.parameters[arg_name].default

        if arg_name.endswith("_"):
            arg_name = f"{arg_name[:-1]}\\_"  # noqa: PLW2901

        insert_index = None
        for at, line in enumerate(lines):
            if _line_is_param_line_for_arg(line, arg_name):
                # Get the arg_name from the doc to match up for type in case it has a star prefix.
                # Line is in the correct format so this is guaranteed to return tuple[str, str].
                func = _get_sphinx_line_keyword_and_argument
                _, arg_name = func(line)  # type: ignore[assignment, misc] # noqa: PLW2901
                insert_index = at
                break

        if annotation is not None and insert_index is None and app.config.always_document_param_types:
            lines.append(f":param {arg_name}:")
            insert_index = len(lines)

        if insert_index is not None:
            if annotation is None:
                type_annotation = f":type {arg_name}: "
            else:
                formatted_annotation = add_type_css_class(format_annotation(annotation, app.config))
                type_annotation = f":type {arg_name}: {formatted_annotation}"

            if app.config.typehints_defaults:
                formatted_default = format_default(app, default, annotation is not None)
                if formatted_default:
                    type_annotation = _append_default(app, lines, insert_index, type_annotation, formatted_default)

            lines.insert(insert_index, type_annotation)


def _append_default(
    app: Sphinx, lines: list[str], insert_index: int, type_annotation: str, formatted_default: str
) -> str:
    if app.config.typehints_defaults.endswith("after"):
        # advance the index to the end of the :param: paragraphs
        # (terminated by a line with no indentation)
        # append default to the last nonempty line
        nlines = len(lines)
        next_index = insert_index + 1
        append_index = insert_index  # last nonempty line
        while next_index < nlines and (not lines[next_index] or lines[next_index].startswith(" ")):
            if lines[next_index]:
                append_index = next_index
            next_index += 1
        lines[append_index] += formatted_default

    else:  # add to last param doc line
        type_annotation += formatted_default

    return type_annotation


@dataclass
class InsertIndexInfo:
    insert_index: int
    found_param: bool = False
    found_return: bool = False
    found_directive: bool = False


# Sphinx allows so many synonyms...
# See sphinx.domains.python.PyObject
PARAM_SYNONYMS = ("param ", "parameter ", "arg ", "argument ", "keyword ", "kwarg ", "kwparam ")


def node_line_no(node: Node) -> int | None:
    """
    Get the 1-indexed line on which the node starts if possible. If not, return None.

    Descend through the first children until we locate one with a line number or return None if None of them have one.

    I'm not aware of any rst on which this returns None, to find out would require a more detailed analysis of the
    docutils rst parser source code. An example where the node doesn't have a line number but the first child does is
    all `definition_list` nodes. It seems like bullet_list and option_list get line numbers, but enum_list also doesn't.
    """
    if node is None:
        return None

    while node.line is None and node.children:
        node = node.children[0]
    return node.line


def tag_name(node: Node) -> str:
    return node.tagname  # type:ignore[attr-defined,no-any-return]


def get_insert_index(app: Sphinx, lines: list[str]) -> InsertIndexInfo | None:
    # 1. If there is an existing :rtype: anywhere, don't insert anything.
    if any(line.startswith(":rtype:") for line in lines):
        return None

    # 2. If there is a :returns: anywhere, either modify that line or insert
    #    just before it.
    for at, line in enumerate(lines):
        if line.startswith((":return:", ":returns:")):
            return InsertIndexInfo(insert_index=at, found_return=True)

    # 3. Insert after the parameters.
    # To find the parameters, parse as a docutils tree.
    settings = OptionParser(components=(RSTParser,)).get_default_values()
    settings.env = app.env
    doc = parse("\n".join(lines), settings)

    # Find a top level child which is a field_list that contains a field whose
    # name starts with one of the PARAM_SYNONYMS. This is the parameter list. We
    # hope there is at most of these.
    for child in doc.children:
        if tag_name(child) != "field_list":
            continue

        if not any(c.children[0].astext().startswith(PARAM_SYNONYMS) for c in child.children):
            continue

        # Found it! Try to insert before the next sibling. If there is no next
        # sibling, insert at end.
        # If there is a next sibling but we can't locate a line number, insert
        # at end. (I don't know of any input where this happens.)
        next_sibling = child.next_node(descend=False, siblings=True)
        line_no = node_line_no(next_sibling) if next_sibling else None
        at = max(line_no - 2, 0) if line_no else len(lines)
        return InsertIndexInfo(insert_index=at, found_param=True)

    # 4. Insert before examples
    for child in doc.children:
        if tag_name(child) in {"literal_block", "paragraph", "field_list"}:
            continue
        line_no = node_line_no(child)
        at = max(line_no - 2, 0) if line_no else len(lines)
        return InsertIndexInfo(insert_index=at, found_directive=True)

    # 5. Otherwise, insert at end
    return InsertIndexInfo(insert_index=len(lines))


def _inject_rtype(  # noqa: PLR0913, PLR0917
    type_hints: dict[str, Any],
    original_obj: Any,
    app: Sphinx,
    what: str,
    name: str,
    lines: list[str],
) -> None:
    if inspect.isclass(original_obj) or inspect.isdatadescriptor(original_obj):
        return
    if what == "method" and name.endswith(".__init__"):  # avoid adding a return type for data class __init__
        return
    if not app.config.typehints_document_rtype:
        return

    r = get_insert_index(app, lines)
    if r is None:
        return

    insert_index = r.insert_index

    if not app.config.typehints_use_rtype and r.found_return and " -- " in lines[insert_index]:
        return

    formatted_annotation = add_type_css_class(format_annotation(type_hints["return"], app.config))

    if r.found_param and insert_index < len(lines) and lines[insert_index].strip():
        insert_index -= 1

    if insert_index == len(lines) and not r.found_param:
        # ensure that :rtype: doesn't get joined with a paragraph of text
        lines.append("")
        insert_index += 1
    if app.config.typehints_use_rtype or not r.found_return:
        line = f":rtype: {formatted_annotation}"
        lines.insert(insert_index, line)
        if r.found_directive:
            lines.insert(insert_index + 1, "")
    else:
        line = lines[insert_index]
        lines[insert_index] = f":return: {formatted_annotation} --{line[line.find(' ') :]}"


def validate_config(app: Sphinx, env: BuildEnvironment, docnames: list[str]) -> None:  # noqa: ARG001
    valid = {None, "comma", "braces", "braces-after"}
    if app.config.typehints_defaults not in valid | {False}:
        msg = f"typehints_defaults needs to be one of {valid!r}, not {app.config.typehints_defaults!r}"
        raise ValueError(msg)

    formatter = app.config.typehints_formatter
    if formatter is not None and not callable(formatter):
        msg = f"typehints_formatter needs to be callable or `None`, not {formatter}"
        raise ValueError(msg)


def unescape(escaped: str) -> str:
    # For some reason the string we get has a bunch of null bytes in it??
    # Remove them...
    escaped = escaped.replace("\x00", "")
    # For some reason the extra slash before spaces gets lost between the .rst
    # source and when this directive is called. So don't replace "\<space>" =>
    # "<space>"
    return re.sub(r"\\([^ ])", r"\1", escaped)


def add_type_css_class(type_rst: str) -> str:
    return f":sphinx_autodoc_typehints_type:`{rst.escape(type_rst)}`"


def sphinx_autodoc_typehints_type_role(
    _role: str,
    _rawtext: str,
    text: str,
    _lineno: int,
    inliner: states.Inliner,
    _options: dict[str, Any] | None = None,
    _content: list[str] | None = None,
) -> tuple[list[Node], list[Node]]:
    """
    Add css tag around rendered type.

    The body should be escaped rst. This renders its body as rst and wraps the
    result in <span class="sphinx_autodoc_typehints-type"> </span>
    """
    unescaped = unescape(text)
    doc = parse(unescaped, inliner.document.settings)
    n = nodes.inline(text)
    n["classes"].append("sphinx_autodoc_typehints-type")
    n += doc.children[0].children
    return [n], []


def setup(app: Sphinx) -> dict[str, bool]:
    app.add_config_value("always_document_param_types", False, "html")  # noqa: FBT003
    app.add_config_value("typehints_fully_qualified", False, "env")  # noqa: FBT003
    app.add_config_value("typehints_document_rtype", True, "env")  # noqa: FBT003
    app.add_config_value("typehints_use_rtype", True, "env")  # noqa: FBT003
    app.add_config_value("typehints_defaults", None, "env")
    app.add_config_value("simplify_optional_unions", True, "env")  # noqa: FBT003
    app.add_config_value("always_use_bars_union", False, "env")  # noqa: FBT003
    app.add_config_value("typehints_formatter", None, "env")
    app.add_config_value("typehints_use_signature", False, "env")  # noqa: FBT003
    app.add_config_value("typehints_use_signature_return", False, "env")  # noqa: FBT003
    app.add_config_value("typehints_fixup_module_name", None, "env")
    app.add_role("sphinx_autodoc_typehints_type", sphinx_autodoc_typehints_type_role)
    app.connect("env-before-read-docs", validate_config)  # config may be changed after “config-inited” event
    app.connect("autodoc-process-signature", process_signature)
    app.connect("autodoc-process-docstring", process_docstring)
    install_patches(app)
    return {"parallel_read_safe": True, "parallel_write_safe": True}


__all__ = [
    "__version__",
    "backfill_type_hints",
    "format_annotation",
    "get_annotation_args",
    "get_annotation_class_name",
    "get_annotation_module",
    "normalize_source_lines",
    "process_docstring",
    "process_signature",
]
