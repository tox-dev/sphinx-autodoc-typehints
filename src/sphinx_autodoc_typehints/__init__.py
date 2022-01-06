from __future__ import annotations

import inspect
import sys
import textwrap
import typing
from ast import FunctionDef, Module, stmt
from typing import Any, AnyStr, NewType, TypeVar, get_type_hints

from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from sphinx.ext.autodoc import Options
from sphinx.util import logging
from sphinx.util.inspect import signature as sphinx_signature
from sphinx.util.inspect import stringify_signature

from .version import version as __version__

logger = logging.getLogger(__name__)
pydata_annotations = {"Any", "AnyStr", "Callable", "ClassVar", "Literal", "NoReturn", "Optional", "Tuple", "Union"}

__all__ = [
    "__version__",
]


def get_annotation_module(annotation: Any) -> str:
    # Special cases
    if annotation is None:
        return "builtins"

    if sys.version_info >= (3, 10) and isinstance(annotation, NewType):  # type: ignore # isinstance NewType is Callable
        return "typing"

    if hasattr(annotation, "__module__"):
        return annotation.__module__  # type: ignore # deduced Any

    if hasattr(annotation, "__origin__"):
        return annotation.__origin__.__module__  # type: ignore # deduced Any

    raise ValueError(f"Cannot determine the module of {annotation}")


def get_annotation_class_name(annotation: Any, module: str) -> str:
    # Special cases
    if annotation is None:
        return "None"
    elif annotation is Any:
        return "Any"
    elif annotation is AnyStr:
        return "AnyStr"
    elif (sys.version_info < (3, 10) and inspect.isfunction(annotation) and hasattr(annotation, "__supertype__")) or (
        sys.version_info >= (3, 10) and isinstance(annotation, NewType)  # type: ignore # isinstance NewType is Callable
    ):
        return "NewType"

    if getattr(annotation, "__qualname__", None):
        return annotation.__qualname__  # type: ignore # deduced Any
    elif getattr(annotation, "_name", None):  # Required for generic aliases on Python 3.7+
        return annotation._name  # type: ignore # deduced Any
    elif module in ("typing", "typing_extensions") and isinstance(getattr(annotation, "name", None), str):
        # Required for at least Pattern and Match
        return annotation.name  # type: ignore # deduced Any

    origin = getattr(annotation, "__origin__", None)
    if origin:
        if getattr(origin, "__qualname__", None):  # Required for Protocol subclasses
            return origin.__qualname__  # type: ignore # deduced Any
        elif getattr(origin, "_name", None):  # Required for Union on Python 3.7+
            return origin._name  # type: ignore # deduced Any

    annotation_cls = annotation if inspect.isclass(annotation) else annotation.__class__
    return annotation_cls.__qualname__.lstrip("_")  # type: ignore # deduced Any


def get_annotation_args(annotation: Any, module: str, class_name: str) -> tuple[Any, ...]:
    try:
        original = getattr(sys.modules[module], class_name)
    except (KeyError, AttributeError):
        pass
    else:
        if annotation is original:
            return ()  # This is the original, not parametrized type

    # Special cases
    if class_name in ("Pattern", "Match") and hasattr(annotation, "type_var"):  # Python < 3.7
        return (annotation.type_var,)
    elif class_name == "ClassVar" and hasattr(annotation, "__type__"):  # ClassVar on Python < 3.7
        return (annotation.__type__,)
    elif class_name == "NewType" and hasattr(annotation, "__supertype__"):
        return (annotation.__supertype__,)
    elif class_name == "Literal" and hasattr(annotation, "__values__"):
        return annotation.__values__  # type: ignore # deduced Any
    elif class_name == "Generic":
        return annotation.__parameters__  # type: ignore # deduced Any

    return getattr(annotation, "__args__", ())


def format_annotation(annotation: Any, fully_qualified: bool = False, simplify_optional_unions: bool = True) -> str:
    # Special cases
    if annotation is None or annotation is type(None):  # noqa: E721
        return ":py:obj:`None`"
    elif annotation is Ellipsis:
        return "..."

    # Type variables are also handled specially
    try:
        if isinstance(annotation, TypeVar) and annotation is not AnyStr:
            return "\\" + repr(annotation)
    except TypeError:
        pass

    try:
        module = get_annotation_module(annotation)
        class_name = get_annotation_class_name(annotation, module)
        args = get_annotation_args(annotation, module, class_name)
    except ValueError:
        return str(annotation).strip("'")

    # Redirect all typing_extensions types to the stdlib typing module
    if module == "typing_extensions":
        module = "typing"

    full_name = f"{module}.{class_name}" if module != "builtins" else class_name
    prefix = "" if fully_qualified or full_name == class_name else "~"
    role = "data" if class_name in pydata_annotations else "class"
    args_format = "\\[{}]"
    formatted_args = ""

    # Some types require special handling
    if full_name == "typing.NewType":
        args_format = f"\\(``{annotation.__name__}``, {{}})"
        role = "class" if sys.version_info >= (3, 10) else "func"
    elif full_name == "typing.Optional":
        args = tuple(x for x in args if x is not type(None))  # noqa: E721
    elif full_name == "typing.Union" and type(None) in args:
        if len(args) == 2:
            full_name = "typing.Optional"
            args = tuple(x for x in args if x is not type(None))  # noqa: E721
        elif not simplify_optional_unions:
            full_name = "typing.Optional"
            args_format = f"\\[:py:data:`{prefix}typing.Union`\\[{{}}]]"
            args = tuple(x for x in args if x is not type(None))  # noqa: E721
    elif full_name == "typing.Callable" and args and args[0] is not ...:
        fmt = ", ".join(format_annotation(arg, simplify_optional_unions=simplify_optional_unions) for arg in args[:-1])
        formatted_args = f"\\[\\[{fmt}]"
        formatted_args += f", {format_annotation(args[-1], simplify_optional_unions=simplify_optional_unions)}]"
    elif full_name == "typing.Literal":
        formatted_args = f"\\[{', '.join(repr(arg) for arg in args)}]"

    if args and not formatted_args:
        fmt = ", ".join(format_annotation(arg, fully_qualified, simplify_optional_unions) for arg in args)
        formatted_args = args_format.format(fmt)

    return f":py:{role}:`{prefix}{full_name}`{formatted_args}"


# reference: https://github.com/pytorch/pytorch/pull/46548/files
def normalize_source_lines(source_lines: str) -> str:
    """
    This helper function accepts a list of source lines. It finds the
    indentation level of the function definition (`def`), then it indents
    all lines in the function body to a point at or greater than that
    level. This allows for comments and continued string literals that
    are at a lower indentation than the rest of the code.
    Arguments:
        source_lines: source code
    Returns:
        source lines that have been correctly aligned
    """
    lines = source_lines.split("\n")

    def remove_prefix(text: str, prefix: str) -> str:
        return text[text.startswith(prefix) and len(prefix) :]

    # Find the line and line number containing the function definition
    for i, l in enumerate(lines):
        if l.lstrip().startswith("def "):
            idx = i
            whitespace_separator = "def"
            break
        elif l.lstrip().startswith("async def"):
            idx = i
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


def process_signature(
    app: Sphinx, what: str, name: str, obj: Any, options: Options, signature: str, return_annotation: str  # noqa: U100
) -> tuple[str, None] | None:
    if not callable(obj):
        return None

    original_obj = obj
    if inspect.isclass(obj):
        obj = getattr(obj, "__init__", getattr(obj, "__new__", None))

    if not getattr(obj, "__annotations__", None):
        return None

    obj = inspect.unwrap(obj)
    sph_signature = sphinx_signature(obj)
    parameters = [param.replace(annotation=inspect.Parameter.empty) for param in sph_signature.parameters.values()]

    # The generated dataclass __init__() and class are weird and need extra checks
    # This helper function operates on the generated class and methods
    # of a dataclass, not an instantiated dataclass object. As such,
    # it cannot be replaced by a call to `dataclasses.is_dataclass()`.
    def _is_dataclass(name: str, what: str, qualname: str) -> bool:
        if what == "method" and name.endswith(".__init__"):
            # generated __init__()
            return True
        if what == "class" and qualname.endswith(".__init__"):
            # generated class
            return True
        return False

    if "<locals>" in obj.__qualname__ and not _is_dataclass(name, what, obj.__qualname__):
        logger.warning('Cannot treat a function defined as a local function: "%s"  (use @functools.wraps)', name)
        return None

    if parameters:
        if inspect.isclass(original_obj) or (what == "method" and name.endswith(".__init__")):
            del parameters[0]
        elif what == "method":
            outer = inspect.getmodule(obj)
            for class_name in obj.__qualname__.split(".")[:-1]:
                outer = getattr(outer, class_name)

            method_name = obj.__name__
            if method_name.startswith("__") and not method_name.endswith("__"):
                # If the method starts with double underscore (dunder)
                # Python applies mangling so we need to prepend the class name.
                # This doesn't happen if it always ends with double underscore.
                class_name = obj.__qualname__.split(".")[-2]
                method_name = f"_{class_name}{method_name}"

            method_object = outer.__dict__[method_name] if outer else obj
            if not isinstance(method_object, (classmethod, staticmethod)):
                del parameters[0]

    sph_signature = sph_signature.replace(parameters=parameters, return_annotation=inspect.Signature.empty)

    return stringify_signature(sph_signature).replace("\\", "\\\\"), None


def _future_annotations_imported(obj: Any) -> bool:
    _annotations = getattr(inspect.getmodule(obj), "annotations", None)
    if _annotations is None:
        return False

    # Make sure that annotations is imported from __future__ - defined in cpython/Lib/__future__.py
    # annotations become strings at runtime
    future_annotations = 0x100000 if sys.version_info[0:2] == (3, 7) else 0x1000000
    return bool(_annotations.compiler_flag == future_annotations)


def get_all_type_hints(obj: Any, name: str) -> dict[str, Any]:
    rv = {}

    try:
        rv = get_type_hints(obj)
    except (AttributeError, TypeError, RecursionError) as exc:
        # Introspecting a slot wrapper will raise TypeError, and and some recursive type
        # definitions will cause a RecursionError (https://github.com/python/typing/issues/574).

        # If one is using PEP563 annotations, Python will raise a (e.g.,)
        # TypeError("TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'")
        # on 'str | None', therefore we accept TypeErrors with that error message
        # if 'annotations' is imported from '__future__'.
        if isinstance(exc, TypeError) and _future_annotations_imported(obj) and "unsupported operand type" in str(exc):
            rv = obj.__annotations__
    except NameError as exc:
        logger.warning('Cannot resolve forward reference in type annotations of "%s": %s', name, exc)
        rv = obj.__annotations__

    if rv:
        return rv

    rv = backfill_type_hints(obj, name)

    try:
        obj.__annotations__ = rv
    except (AttributeError, TypeError):
        return rv

    try:
        rv = get_type_hints(obj)
    except (AttributeError, TypeError):
        pass
    except NameError as exc:
        logger.warning('Cannot resolve forward reference in type annotations of "%s": %s', name, exc)
        rv = obj.__annotations__

    return rv


def backfill_type_hints(obj: Any, name: str) -> dict[str, Any]:
    parse_kwargs = {}
    if sys.version_info < (3, 8):
        try:
            import typed_ast.ast3 as ast
        except ImportError:
            return {}
    else:
        import ast

        parse_kwargs = {"type_comments": True}

    def _one_child(module: Module) -> stmt | None:
        children = module.body  # use the body to ignore type comments

        if len(children) != 1:
            logger.warning('Did not get exactly one node from AST for "%s", got %s', name, len(children))
            return None

        return children[0]

    try:
        code = textwrap.dedent(normalize_source_lines(inspect.getsource(obj)))
        obj_ast = ast.parse(code, **parse_kwargs)  # type: ignore # dynamic kwargs
    except (OSError, TypeError):
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
        logger.warning('Unparseable type hint comment for "%s": Expected to contain ` -> `', name)
        return {}

    rv = {}
    if comment_returns:
        rv["return"] = comment_returns

    args = load_args(obj_ast)
    comment_args = split_type_comment_args(comment_args_str)
    is_inline = len(comment_args) == 1 and comment_args[0] == "..."
    if not is_inline:
        if args and args[0].arg in ("self", "cls") and len(comment_args) != len(args):
            comment_args.insert(0, None)  # self/cls may be omitted in type comments, insert blank

        if len(args) != len(comment_args):
            logger.warning('Not enough type comments found on "%s"', name)
            return rv

    for at, arg in enumerate(args):
        arg_key = getattr(arg, "arg", None)
        if arg_key is None:
            continue

        if is_inline:  # the type information now is tied to the argument
            value = getattr(arg, "type_comment", None)
        else:  # type data from comment
            value = comment_args[at]

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
        if char in ("[", "("):
            brackets += 1
        elif char in ("]", ")"):
            brackets -= 1
        elif char == "," and brackets == 0:
            add(comment[start_arg_at:at])
            start_arg_at = at + 1

    add(comment[start_arg_at : at + 1])
    return result


def format_default(app: Sphinx, default: Any) -> str | None:
    if default is inspect.Parameter.empty:
        return None
    formatted = repr(default).replace("\\", "\\\\")
    if app.config.typehints_defaults.startswith("braces"):
        return f" (default: ``{formatted}``)"
    else:
        return f", default: ``{formatted}``"


def process_docstring(
    app: Sphinx, what: str, name: str, obj: Any, options: Options | None, lines: list[str]  # noqa: U100
) -> None:
    original_obj = obj
    if isinstance(obj, property):
        obj = obj.fget

    if callable(obj):
        if inspect.isclass(obj):
            obj = obj.__init__

        obj = inspect.unwrap(obj)
        signature = sphinx_signature(obj)
        type_hints = get_all_type_hints(obj, name)

        for arg_name, annotation in type_hints.items():
            if arg_name == "return":
                continue  # this is handled separately later
            default = signature.parameters[arg_name].default
            if arg_name.endswith("_"):
                arg_name = f"{arg_name[:-1]}\\_"

            formatted_annotation = format_annotation(
                annotation,
                fully_qualified=app.config.typehints_fully_qualified,
                simplify_optional_unions=app.config.simplify_optional_unions,
            )

            search_for = [f":{field} {arg_name}:" for field in ("param", "parameter", "arg", "argument")]
            insert_index = None

            for i, line in enumerate(lines):
                if any(line.startswith(search_string) for search_string in search_for):
                    insert_index = i
                    break

            if insert_index is None and app.config.always_document_param_types:
                lines.append(f":param {arg_name}:")
                insert_index = len(lines)

            if insert_index is not None:
                type_annotation = f":type {arg_name}: {formatted_annotation}"
                if app.config.typehints_defaults:
                    formatted_default = format_default(app, default)
                    if formatted_default:
                        if app.config.typehints_defaults.endswith("after"):
                            lines[insert_index] += formatted_default
                        else:  # add to last param doc line
                            type_annotation += formatted_default
                lines.insert(insert_index, type_annotation)

        if "return" in type_hints and not inspect.isclass(original_obj):
            # This avoids adding a return type for data class __init__ methods
            if what == "method" and name.endswith(".__init__"):
                return

            formatted_annotation = format_annotation(
                type_hints["return"],
                fully_qualified=app.config.typehints_fully_qualified,
                simplify_optional_unions=app.config.simplify_optional_unions,
            )

            insert_index = len(lines)
            for i, line in enumerate(lines):
                if line.startswith(":rtype:"):
                    insert_index = None
                    break
                elif line.startswith(":return:") or line.startswith(":returns:"):
                    insert_index = i

            if insert_index is not None and app.config.typehints_document_rtype:
                if insert_index == len(lines):
                    # Ensure that :rtype: doesn't get joined with a paragraph of text, which
                    # prevents it being interpreted.
                    lines.append("")
                    insert_index += 1

                lines.insert(insert_index, f":rtype: {formatted_annotation}")


def builder_ready(app: Sphinx) -> None:
    if app.config.set_type_checking_flag:
        typing.TYPE_CHECKING = True


def validate_config(app: Sphinx, env: BuildEnvironment, docnames: list[str]) -> None:  # noqa: U100
    valid = {None, "comma", "braces", "braces-after"}
    if app.config.typehints_defaults not in valid | {False}:
        raise ValueError(f"typehints_defaults needs to be one of {valid!r}, not {app.config.typehints_defaults!r}")


def setup(app: Sphinx) -> dict[str, bool]:
    app.add_config_value("set_type_checking_flag", False, "html")
    app.add_config_value("always_document_param_types", False, "html")
    app.add_config_value("typehints_fully_qualified", False, "env")
    app.add_config_value("typehints_document_rtype", True, "env")
    app.add_config_value("typehints_defaults", None, "env")
    app.add_config_value("simplify_optional_unions", True, "env")
    app.connect("builder-inited", builder_ready)
    app.connect("env-before-read-docs", validate_config)  # config may be changed after “config-inited” event
    app.connect("autodoc-process-signature", process_signature)
    app.connect("autodoc-process-docstring", process_docstring)
    return {"parallel_read_safe": True}
