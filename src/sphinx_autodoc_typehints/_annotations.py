"""
Annotation inspection and RST formatting.

Converts Python type annotations into reStructuredText cross-reference markup for Sphinx output.
Handles standard library types, typing constructs (Union, Optional, Literal, NewType, etc.),
forward references, type aliases, and pydata-sphinx-theme compatibility annotations.

This is a leaf module with no internal package imports to keep the dependency graph acyclic.
"""

from __future__ import annotations

import enum
import inspect
import re
import sys
import types
from typing import TYPE_CHECKING, Any, AnyStr, ForwardRef, NewType, TypeVar, Union

from sphinx.util import rst
from sphinx.util.inspect import TypeAliasForwardRef

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from sphinx.config import Config

from typing import TypeAliasType

_PYDATA_ANNOTS_TYPING = {
    "Any",
    "AnyStr",
    "Callable",
    "ClassVar",
    "Literal",
    "NoReturn",
    "Optional",
    "Tuple",
    *({"Union"} if sys.version_info < (3, 14) else set()),
}
_PYDATA_ANNOTS_TYPES = {
    *("AsyncGeneratorType", "BuiltinFunctionType", "BuiltinMethodType"),
    *("CellType", "ClassMethodDescriptorType", "CoroutineType"),
    *("FrameType", "FunctionType"),
    *("GeneratorType", "GetSetDescriptorType"),
    "LambdaType",
    *("MemberDescriptorType", "MethodDescriptorType", "MethodType", "MethodWrapperType"),
    "NoneType",
    "WrapperDescriptorType",
    # documented as ``py:class`` since the Python 3.13 docs
    *({"EllipsisType", "NotImplementedType"} if sys.version_info < (3, 13) else set()),
}
_PYDATA_ANNOTATIONS = {
    *(("typing", n) for n in _PYDATA_ANNOTS_TYPING),
    *(("types", n) for n in _PYDATA_ANNOTS_TYPES),
}

_TYPES_DICT = {getattr(types, name): name for name in types.__all__}
_TYPES_DICT[types.FunctionType] = "FunctionType"

_UNESCAPE_RE = re.compile(
    r"""
    \\          # literal backslash
    ([^ ])      # followed by any non-space character (captured)
    """,
    re.VERBOSE,
)


class MyTypeAliasForwardRef(TypeAliasForwardRef):
    crossref: bool = False

    def __or__(self, value: Any) -> Any:  # ty: ignore[invalid-method-override]
        return Union[self, value]  # noqa: UP007


def format_annotation(annotation: Any, config: Config, *, short_literals: bool = False) -> str:
    """
    Format the annotation into reStructuredText cross-reference markup.

    The annotation is a tree (``dict[str, list[int]]`` nests three levels), so formatting it is a
    post-order walk. The walk is driven iteratively with an explicit stack rather than by recursion:
    a PEP 695 type alias may reference itself (``type T = int | list[T]``), which is a fully
    supported recursive type but would expand forever and exhaust the interpreter recursion limit if
    walked naively. Each frame on the stack is one suspended ``_format_node`` generator; the generator
    yields the child annotations it needs formatted and is resumed with their rendered strings.
    ``active`` holds the aliases currently being expanded along the path from the root, so when an
    alias references itself it is rendered as a cross-reference to its own name -- the natural
    representation of a recursive type -- instead of being expanded again.
    """
    fully_qualified: bool = getattr(config, "typehints_fully_qualified", False)
    cycle_prefix = "" if fully_qualified else "~"

    stack = [(_format_node(annotation, config, short_literals=short_literals), annotation)]
    active = {id(annotation)} if isinstance(annotation, TypeAliasType) else set()
    rendered: str | None = None
    while True:
        gen, node = stack[-1]
        try:
            child = next(gen) if rendered is None else gen.send(rendered)
        except StopIteration as done:
            stack.pop()
            if isinstance(node, TypeAliasType):
                active.discard(id(node))
            rendered = done.value
            if not stack:
                return rendered
            continue
        if isinstance(child, TypeAliasType) and id(child) in active:
            rendered = f":py:type:`{cycle_prefix}{child.__name__}`"
            continue
        stack.append((_format_node(child, config, short_literals=short_literals), child))
        if isinstance(child, TypeAliasType):
            active.add(id(child))
        rendered = None


def _format_node(  # noqa: C901, PLR0911, PLR0912, PLR0915, PLR0914
    annotation: Any,
    config: Config,
    *,
    short_literals: bool,
) -> Generator[Any, str, str]:
    """
    Format a single annotation node, delegating nested annotations to :func:`format_annotation`.

    Every nested annotation is ``yield``-ed and the driver sends back its formatted string, so the
    recursion lives in the driver's explicit stack rather than on the Python call stack.
    """
    typehints_formatter: Callable[..., str] | None = getattr(config, "typehints_formatter", None)
    if typehints_formatter is not None:
        formatted = typehints_formatter(annotation, config)
        if formatted is not None:
            return formatted

    if isinstance(annotation, ForwardRef):
        return annotation.__forward_arg__
    if annotation is None or annotation is type(None):
        return ":py:obj:`None`"
    if annotation is Ellipsis:
        return ":py:data:`...<Ellipsis>`"

    if isinstance(annotation, tuple):
        parts = []
        for item in annotation:
            parts.append((yield item))  # noqa: PERF401  # yield is illegal inside a comprehension
        if not parts:
            return "()"
        if len(parts) == 1:
            return f"({parts[0]}, )"
        return f"({', '.join(parts)})"

    if isinstance(annotation, TypeAliasForwardRef):
        fully_qualified: bool = getattr(config, "typehints_fully_qualified", False)
        prefix = "" if fully_qualified else "~"
        if (env := getattr(config, "_typehints_env", None)) is not None:
            py_domain = env.get_domain("py")
            module_prefix = getattr(config, "_typehints_module_prefix", "")
            for candidate in (f"{module_prefix}.{annotation.name}", annotation.name):
                if candidate in py_domain.objects and py_domain.objects[candidate].objtype == "type":
                    return f":py:type:`{prefix}{candidate}`"
        if isinstance(annotation, MyTypeAliasForwardRef) and annotation.crossref:
            return f":py:type:`{prefix}{annotation.name}`"
        return annotation.name

    if isinstance(annotation, TypeAliasType):
        fully_qualified = getattr(config, "typehints_fully_qualified", False)
        prefix = "" if fully_qualified else "~"
        if (env := getattr(config, "_typehints_env", None)) is not None:
            py_domain = env.get_domain("py")
            module_prefix = getattr(config, "_typehints_module_prefix", "")
            prefix_parts = module_prefix.split(".") if module_prefix else []
            # Walk up the module prefix to find a matching type in the py domain
            candidates = [
                f"{'.'.join(prefix_parts[:n])}.{annotation.__name__}" for n in range(len(prefix_parts), 0, -1)
            ]
            candidates.append(annotation.__name__)
            for candidate in candidates:
                if candidate in py_domain.objects and py_domain.objects[candidate].objtype == "type":
                    return f":py:type:`{prefix}{candidate}`"
            # Handle external type aliases
            canonical = _get_canonical_type_alias_name(annotation)
            current_top = module_prefix.split(".")[0] if module_prefix else ""
            if canonical and canonical.split(".")[0] != current_top:
                full_name = _fixup_module_name(config, canonical.rpartition(".")[0]) + "." + annotation.__name__
                return f":py:obj:`{prefix}{full_name}`"
        return (yield annotation.__value__)

    try:
        module = get_annotation_module(annotation)
        class_name = get_annotation_class_name(annotation, module)
        args = get_annotation_args(annotation, module, class_name)
    except ValueError:
        return str(annotation).strip("'")

    module = _fixup_module_name(config, module)
    internal_path = f"{module}.{class_name}"
    if (mapping := getattr(config, "_intersphinx_type_mapping", None)) and (mapped := mapping.get(internal_path)):
        module, _, class_name = mapped.rpartition(".")
    full_name = f"{module}.{class_name}" if module != "builtins" else class_name
    fully_qualified = getattr(config, "typehints_fully_qualified", False)
    prefix = "" if fully_qualified or full_name == class_name else "~"
    role = "data" if (module, class_name) in _PYDATA_ANNOTATIONS else "class"
    args_format = "\\[{}]"
    formatted_args: str | None = ""

    always_use_bars_union: bool = getattr(config, "always_use_bars_union", True)
    is_bars_union = (
        (sys.version_info >= (3, 14) and full_name == "typing.Union")
        or full_name == "types.UnionType"
        or (always_use_bars_union and type(annotation).__qualname__ == "_UnionGenericAlias")
    )
    if is_bars_union:
        full_name = ""

    if full_name == "typing.NewType":
        newtype_module = _fixup_module_name(config, getattr(annotation, "__module__", ""))
        newtype_name = annotation.__name__
        newtype_qualified = f"{newtype_module}.{newtype_name}" if newtype_module else newtype_name
        newtype_prefix = "" if fully_qualified or not newtype_module else "~"
        supertype = yield annotation.__supertype__
        return f":py:class:`{newtype_prefix}{newtype_qualified}` ({supertype})"
    if full_name == "typing.Annotated":
        return (yield annotation.__origin__)
    if full_name in {"typing.TypeVar", "typing.ParamSpec"}:
        params = {k: getattr(annotation, f"__{k}__") for k in ("bound", "covariant", "contravariant")}
        params = {k: v for k, v in params.items() if v}
        if "bound" in params:
            bound = yield params["bound"]
            params["bound"] = f" {bound}"
        args_format = f"\\(``{annotation.__name__}``{', {}' if args else ''}"
        if params:
            args_format += "".join(f", {k}={v}" for k, v in params.items())
        args_format += ")"
        formatted_args = None if args else args_format
    elif full_name == "typing.Optional":  # pragma: <3.14 cover
        args = tuple(x for x in args if x is not type(None))
    elif full_name in {"typing.Union", "types.UnionType"} and type(None) in args:  # pragma: <3.14 cover
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
        fmt = []
        for arg in args:
            fmt.append((yield arg))  # noqa: PERF401  # yield is illegal inside a comprehension
        formatted_args = f"\\[\\[{', '.join(fmt[:-1])}], {fmt[-1]}]"
    elif full_name == "typing.Literal":
        literal_parts = [_format_literal_arg(arg, config) for arg in args]
        if short_literals:
            return f"\\{' | '.join(literal_parts)}"
        formatted_args = f"\\[{', '.join(literal_parts)}]"
    elif is_bars_union:
        if not args:
            return f":py:{'class' if sys.version_info >= (3, 14) else 'data'}:`{prefix}typing.Union`"
        union_parts = []
        for arg in args:
            union_parts.append((yield arg))  # noqa: PERF401  # yield is illegal inside a comprehension
        return " | ".join(union_parts)

    if args and not formatted_args:
        fmt = []
        for arg in args:
            fmt.append((yield arg))
        formatted_args = args_format.format(", ".join(fmt))

    escape = "\\ " if formatted_args else ""
    # B901: returning a value from a generator is intentional here — the driver reads it via StopIteration
    return f":py:{role}:`{prefix}{full_name}`{escape}{formatted_args}"  # noqa: B901


def get_annotation_module(annotation: Any) -> str:
    if annotation is None:
        return "builtins"
    if _get_types_type(annotation) is not None:
        return "types"
    is_new_type = isinstance(annotation, NewType)
    if (
        is_new_type
        or isinstance(annotation, TypeVar)
        or type(annotation).__name__ in {"ParamSpec", "ParamSpecArgs", "ParamSpecKwargs"}
    ):
        return "typing"
    if hasattr(annotation, "__module__"):
        return annotation.__module__
    msg = f"Cannot determine the module of {annotation}"
    raise ValueError(msg)


def get_annotation_class_name(annotation: Any, module: str) -> str:  # noqa: C901, PLR0911
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
        return annotation.__qualname__
    if getattr(annotation, "_name", None):  # pragma: <3.14 cover
        return annotation._name  # noqa: SLF001
    if module in {"typing", "typing_extensions"} and isinstance(
        getattr(annotation, "name", None), str
    ):  # pragma: <3.14 cover
        return annotation.name

    origin = getattr(annotation, "__origin__", None)
    if origin:
        if getattr(origin, "__qualname__", None):  # pragma: <3.14 cover
            return origin.__qualname__
        if getattr(origin, "_name", None):  # pragma: <3.14 cover
            return origin._name  # noqa: SLF001

    annotation_cls = annotation if inspect.isclass(annotation) else type(annotation)
    return annotation_cls.__qualname__.lstrip("_")


def get_annotation_args(annotation: Any, module: str, class_name: str) -> tuple[Any, ...]:
    try:
        original = getattr(sys.modules[module], class_name)
    except (KeyError, AttributeError):
        pass
    else:
        if annotation is original:
            return ()

    if class_name == "TypeVar" and hasattr(annotation, "__constraints__"):
        return annotation.__constraints__
    if class_name == "NewType" and hasattr(annotation, "__supertype__"):
        return (annotation.__supertype__,)
    if class_name == "Generic":
        return annotation.__parameters__
    result = getattr(annotation, "__args__", ())
    return () if len(result) == 1 and result[0] == () else result  # type: ignore[misc]


def _fixup_module_name(config: Config, module: str) -> str:
    if getattr(config, "typehints_fixup_module_name", None):
        module = config.typehints_fixup_module_name(module)
    if module == "typing_extensions":  # pragma: <3.14 cover
        module = "typing"
    if module == "_io":
        module = "io"
    return module


def _format_literal_arg(arg: Any, config: Config) -> str:
    if isinstance(arg, enum.Enum):
        enum_cls = type(arg)
        module = _fixup_module_name(config, enum_cls.__module__)
        fully_qualified = getattr(config, "typehints_fully_qualified", False)
        qualified = f"{module}.{enum_cls.__qualname__}.{arg.name}" if module else f"{enum_cls.__qualname__}.{arg.name}"
        prefix = "" if fully_qualified or not module else "~"
        return f":py:attr:`{prefix}{qualified}`"
    return f"``{arg!r}``"


def _get_types_type(obj: Any) -> str | None:
    try:
        return _TYPES_DICT.get(obj)
    except Exception:  # noqa: BLE001
        return None


def _is_newtype(annotation: Any) -> bool:
    return isinstance(annotation, NewType)


def _get_canonical_type_alias_name(annotation: TypeAliasType) -> str:
    """
    Get canonical public qualified name for a TypeAliasType.

    For types defined in private modules (e.g. ``numpy._typing.ArrayLike``),
    search ``sys.modules`` for a public re-export
    (e.g. ``numpy.typing.ArrayLike``).
    """
    module = getattr(annotation, "__module__", "") or ""
    name = getattr(annotation, "__name__", "") or ""
    if not module or not name:
        return ""
    if not any(part.startswith("_") for part in module.split(".")):
        return f"{module}.{name}"
    top_pkg = module.split(".")[0]
    for mod_name in sorted(sys.modules):
        if not mod_name.startswith(top_pkg):
            continue
        mod = sys.modules[mod_name]
        if not isinstance(mod, types.ModuleType):
            continue
        if any(part.startswith("_") for part in mod_name.split(".")):
            continue
        if getattr(mod, name, None) is annotation:
            return f"{mod_name}.{name}"
    return f"{module}.{name}"


def unescape(escaped: str) -> str:
    escaped = escaped.replace("\x00", "")
    return _UNESCAPE_RE.sub(r"\1", escaped)


def add_type_css_class(type_rst: str) -> str:
    return f":sphinx_autodoc_typehints_type:`{rst.escape(type_rst)}`"
