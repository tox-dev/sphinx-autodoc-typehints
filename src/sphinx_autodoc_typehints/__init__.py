"""Sphinx autodoc type hints."""

from __future__ import annotations

import inspect
import types
from typing import TYPE_CHECKING, Any, TypeVar

from docutils import nodes
from sphinx.util import logging
from sphinx.util.inspect import signature as sphinx_signature
from sphinx.util.inspect import stringify_signature

# re-exports for backward compatibility
from ._annotations import (
    MyTypeAliasForwardRef,
    add_type_css_class,
    format_annotation,
    get_annotation_args,
    get_annotation_class_name,
    get_annotation_module,
    unescape,
)
from ._formats import detect_format
from ._formats._numpydoc import _convert_numpydoc_to_sphinx_fields  # noqa: F401
from ._formats._sphinx import _has_yields_section, _is_generator_type
from ._parser import parse
from ._resolver import (
    _collect_documented_type_aliases,
    backfill_type_hints,
    get_all_type_hints,
    normalize_source_lines,
)
from .patches import _OVERLOADS_CACHE, install_patches
from .version import __version__

if TYPE_CHECKING:
    from collections.abc import Callable

    from docutils.nodes import Node
    from docutils.parsers.rst import states
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.ext.autodoc import Options

_LOGGER = logging.getLogger(__name__)


def process_signature(  # noqa: C901, PLR0911, PLR0912, PLR0913, PLR0917
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    options: Options,  # noqa: ARG001
    signature: str,  # noqa: ARG001
    return_annotation: str,  # noqa: ARG001
) -> tuple[str, None] | None:
    """Process the signature."""
    if not callable(obj):
        return None

    original_obj = obj
    obj = getattr(obj, "__init__", getattr(obj, "__new__", None)) if inspect.isclass(obj) else obj
    if not getattr(obj, "__annotations__", None):
        return None

    try:
        obj = inspect.unwrap(obj)  # ty: ignore[invalid-argument-type]
    except ValueError:
        return None
    sph_signature = sphinx_signature(obj, type_aliases=app.config["autodoc_type_aliases"])
    typehints_formatter: Callable[..., str | None] | None = getattr(app.config, "typehints_formatter", None)

    def _get_formatted_annotation(annotation: TypeVar) -> TypeVar:
        if typehints_formatter is None:
            return annotation
        formatted_name = typehints_formatter(annotation)
        return annotation if not isinstance(formatted_name, str) else TypeVar(formatted_name)  # ty: ignore[invalid-legacy-type-variable]

    if app.config.typehints_use_signature_return:
        sph_signature = sph_signature.replace(
            return_annotation=_get_formatted_annotation(sph_signature.return_annotation)
        )

    if app.config.typehints_use_signature:
        parameters = [
            param.replace(annotation=_get_formatted_annotation(param.annotation))
            for param in sph_signature.parameters.values()
        ]
    else:
        parameters = [param.replace(annotation=inspect.Parameter.empty) for param in sph_signature.parameters.values()]

    start = 0
    if parameters:
        if inspect.isclass(original_obj) or (what == "method" and name.endswith(".__init__")):
            start = 1
        elif what == "method":
            if "<locals>" in obj.__qualname__ and not _is_dataclass(name, what, obj.__qualname__):
                _LOGGER.warning(
                    'Cannot handle as a local function: "%s" (use @functools.wraps)',
                    name,
                    type="sphinx_autodoc_typehints",
                    subtype="local_function",
                )
                return None
            outer = inspect.getmodule(obj)
            if outer is None:
                return None
            for class_name in obj.__qualname__.split(".")[:-1]:
                if (outer := getattr(outer, class_name, None)) is None:
                    return None
            method_name = obj.__name__
            if method_name.startswith("__") and not method_name.endswith("__"):
                method_name = f"_{obj.__qualname__.split('.')[-2]}{method_name}"
            method_object = outer.__dict__.get(method_name, obj) if outer else obj
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
    return (what == "method" and name.endswith(".__init__")) or (what == "class" and qualname.endswith(".__init__"))


def process_docstring(  # noqa: PLR0913, PLR0917
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    options: Options | None,  # noqa: ARG001
    lines: list[str],
) -> None:
    """Process the docstring for an entry."""
    original_obj = obj
    obj = obj.fget if isinstance(obj, property) else obj
    if not callable(obj):
        return
    obj = obj.__init__ if inspect.isclass(obj) else obj
    try:
        obj = inspect.unwrap(obj)
    except ValueError:
        return

    try:
        signature = sphinx_signature(obj, type_aliases=app.config["autodoc_type_aliases"])
    except (ValueError, TypeError):
        signature = None

    localns = {key: MyTypeAliasForwardRef(value) for key, value in app.config["autodoc_type_aliases"].items()}
    module_prefix = name.rsplit(".", maxsplit=1)[0] if "." in name else ""
    eager_aliases: dict[int, MyTypeAliasForwardRef] = {}
    if (env := getattr(app, "env", None)) is not None:
        deferred, eager_aliases = _collect_documented_type_aliases(obj, module_prefix, env)
        localns.update(deferred)
    type_hints = get_all_type_hints(app.config.autodoc_mock_imports, obj, name, localns)
    for param, hint in type_hints.items():
        if id(hint) in eager_aliases:
            type_hints[param] = eager_aliases[id(hint)]
    app.config._annotation_globals = getattr(obj, "__globals__", {})  # noqa: SLF001
    app.config._typehints_env = env  # noqa: SLF001
    app.config._typehints_module_prefix = module_prefix  # noqa: SLF001
    try:
        has_overloads = _inject_overload_signatures(app, what, name, obj, lines)
        _inject_types_to_docstring(type_hints, signature, original_obj, app, what, name, lines, has_overloads)
    finally:
        delattr(app.config, "_annotation_globals")
        delattr(app.config, "_typehints_env")
        delattr(app.config, "_typehints_module_prefix")


def _inject_overload_signatures(
    app: Sphinx,
    what: str,
    name: str,  # noqa: ARG001
    obj: Any,
    lines: list[str],
) -> bool:
    if what not in {"function", "method"}:
        return False

    module_name = getattr(obj, "__module__", None)
    if not module_name or module_name not in _OVERLOADS_CACHE:
        return False

    qualname = getattr(obj, "__qualname__", None)
    if not qualname:
        return False

    overloads = _OVERLOADS_CACHE[module_name].get(qualname)
    if not overloads:
        return False

    short_literals = app.config.python_display_short_literal_types
    overload_lines = [":Overloads:"]
    for overload_sig in overloads:
        params = []
        for param_name, param in overload_sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                formatted_type = format_annotation(param.annotation, app.config, short_literals=short_literals)
                formatted_type = add_type_css_class(formatted_type)
                params.append(f"**{param_name}** ({formatted_type})")
            else:
                params.append(f"**{param_name}**")

        return_annotation = ""
        if overload_sig.return_annotation != inspect.Signature.empty:
            formatted_return = format_annotation(
                overload_sig.return_annotation, app.config, short_literals=short_literals
            )
            formatted_return = add_type_css_class(formatted_return)
            return_annotation = f" \u2192 {formatted_return}"

        sig_line = f"   * {', '.join(params)}{return_annotation}"
        overload_lines.append(sig_line)

    overload_lines.append("")
    for line in reversed(overload_lines):
        lines.insert(0, line)
    return True


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


def _inject_types_to_docstring(  # noqa: PLR0913, PLR0917
    type_hints: dict[str, Any],
    signature: inspect.Signature | None,
    original_obj: Any,
    app: Sphinx,
    what: str,
    name: str,
    lines: list[str],
    has_overloads: bool = False,  # noqa: FBT001, FBT002
) -> None:
    fmt = detect_format(lines)
    if signature is not None:
        _inject_signature(type_hints, signature, app, lines, fmt)
    if "return" in type_hints and not has_overloads:
        _inject_rtype(type_hints, original_obj, app, what, name, lines, fmt)


def _inject_signature(
    type_hints: dict[str, Any],
    signature: inspect.Signature,
    app: Sphinx,
    lines: list[str],
    fmt: Any,
) -> None:
    for arg_name in signature.parameters:
        _inject_arg_signature(type_hints, signature, app, lines, arg_name, fmt)


def _inject_arg_signature(  # noqa: PLR0913, PLR0917
    type_hints: dict[str, Any],
    signature: inspect.Signature,
    app: Sphinx,
    lines: list[str],
    arg_name: str,
    fmt: Any,
) -> None:
    annotation = type_hints.get(arg_name)
    default = signature.parameters[arg_name].default

    if arg_name.endswith("_"):
        arg_name = f"{arg_name[:-1]}\\_"

    insert_index = fmt.find_param(lines, arg_name)

    if insert_index is not None and hasattr(fmt, "get_arg_name_from_line"):
        arg_name = fmt.get_arg_name_from_line(lines[insert_index]) or arg_name

    if annotation is not None and insert_index is None and app.config.always_document_param_types:
        insert_index = fmt.add_undocumented_param(lines, arg_name)

    if insert_index is not None:
        has_preexisting_annotation = False

        if annotation is None:
            type_annotation, has_preexisting_annotation = fmt.find_preexisting_type(lines, arg_name)
        else:
            short_literals = app.config.python_display_short_literal_types
            formatted_annotation = add_type_css_class(
                format_annotation(annotation, app.config, short_literals=short_literals)
            )
            type_annotation = f":type {arg_name}: {formatted_annotation}"

        if app.config.typehints_defaults:
            formatted_default = format_default(app, default, annotation is not None or has_preexisting_annotation)
            if formatted_default:
                after = app.config.typehints_defaults.endswith("after")
                type_annotation = fmt.append_default(
                    lines, insert_index, type_annotation, formatted_default, after=after
                )

        lines.insert(insert_index, type_annotation)


def _inject_rtype(  # noqa: PLR0913, PLR0917
    type_hints: dict[str, Any],
    original_obj: Any,
    app: Sphinx,
    what: str,
    name: str,
    lines: list[str],
    fmt: Any,
) -> None:
    if inspect.isclass(original_obj) or inspect.isdatadescriptor(original_obj):
        return
    if what == "method" and name.endswith(".__init__"):
        return
    if not app.config.typehints_document_rtype:
        return
    if not app.config.typehints_document_rtype_none and type_hints["return"] is types.NoneType:
        return
    if _has_yields_section(lines) and _is_generator_type(type_hints["return"]):
        return

    r = fmt.get_rtype_insert_info(app, lines)
    if r is None:
        return

    short_literals = app.config.python_display_short_literal_types
    formatted_annotation = add_type_css_class(
        format_annotation(type_hints["return"], app.config, short_literals=short_literals)
    )

    fmt.inject_rtype(lines, formatted_annotation, r, use_rtype=app.config.typehints_use_rtype)


def validate_config(app: Sphinx, env: BuildEnvironment, docnames: list[str]) -> None:  # noqa: ARG001
    valid = {None, "comma", "braces", "braces-after"}
    if app.config.typehints_defaults not in valid | {False}:
        msg = f"typehints_defaults needs to be one of {valid!r}, not {app.config.typehints_defaults!r}"
        raise ValueError(msg)

    formatter = app.config.typehints_formatter
    if formatter is not None and not callable(formatter):
        msg = f"typehints_formatter needs to be callable or `None`, not {formatter}"
        raise ValueError(msg)


def sphinx_autodoc_typehints_type_role(
    _role: str,
    _rawtext: str,
    text: str,
    _lineno: int,
    inliner: states.Inliner,
    _options: dict[str, Any] | None = None,
    _content: list[str] | None = None,
) -> tuple[list[Node], list[Node]]:
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
    app.add_config_value("typehints_document_rtype_none", True, "env")  # noqa: FBT003
    app.add_config_value("typehints_use_rtype", True, "env")  # noqa: FBT003
    app.add_config_value("typehints_defaults", None, "env")
    app.add_config_value("simplify_optional_unions", True, "env")  # noqa: FBT003
    app.add_config_value("always_use_bars_union", False, "env")  # noqa: FBT003
    app.add_config_value("typehints_formatter", None, "env")
    app.add_config_value("typehints_use_signature", False, "env")  # noqa: FBT003
    app.add_config_value("typehints_use_signature_return", False, "env")  # noqa: FBT003
    app.add_config_value("typehints_fixup_module_name", None, "env")
    app.add_role("sphinx_autodoc_typehints_type", sphinx_autodoc_typehints_type_role)
    app.connect("env-before-read-docs", validate_config)
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
