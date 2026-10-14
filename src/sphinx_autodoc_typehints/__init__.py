"""Sphinx autodoc type hints."""

from __future__ import annotations

import inspect
import re
import sys
import types
from contextlib import contextmanager
from functools import partial
from keyword import iskeyword
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypeVar,
    Unpack,
    get_args,
    get_origin,
)

from docutils import nodes
from sphinx.errors import ConfigError
from sphinx.util import logging
from sphinx.util.inspect import getdoc, object_description, stringify_signature
from sphinx.util.inspect import signature as sphinx_signature

# re-exports for backward compatibility
from ._annotations import (
    MyTypeAliasForwardRef,
    add_type_css_class,
    format_annotation,
    get_annotation_args,
    get_annotation_class_name,
    get_annotation_module,
)
from ._deferred import ALIAS_CHOICE_ROLE, DeferAliasChoice, alias_choice_role, merge_alias_choices
from ._formats import detect_format
from ._formats._numpydoc import _convert_numpydoc_to_sphinx_fields  # ruff:ignore[unused-import]
from ._formats._sphinx import _has_yields_section, _is_generator_type, _strip_inline_param_type
from ._intersphinx import build_type_mapping
from ._parser import unescape
from ._resolver import (
    backfill_attrs_annotations,
    backfill_type_hints,
    collect_documented_type_aliases,
    get_all_type_hints,
    get_descriptor_type_hint,
    get_instance_var_annotations,
    get_obj_location,
    resolve_string_annotations,
    resolve_type_guarded_imports,
)
from ._type_params import add_type_params
from ._typed_dict import typed_dict_keys
from .patches import _OVERLOADS_CACHE, install_patches
from .version import __version__

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from docutils.nodes import Node
    from docutils.parsers.rst import states
    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment
    from sphinx.ext.autodoc import Options

_LOGGER = logging.getLogger(__name__)


def process_signature(  # ruff:ignore[complex-structure, too-many-branches, too-many-arguments, too-many-positional-arguments]
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    options: Options,  # ruff:ignore[unused-function-argument]
    signature: str,  # ruff:ignore[unused-function-argument]
    return_annotation: str,  # ruff:ignore[unused-function-argument]
) -> tuple[str, None] | None:
    """Process the signature."""
    # Sphinx lists each singledispatch implementation under a nameless entry with no docstring to move types into,
    # and the dispatch type is what tells the implementations apart
    if not callable(obj) or not name.strip("."):
        return None

    original_obj = obj
    if inspect.isclass(obj):
        obj = getattr(obj, _constructor_name(obj))
    # a wrapper may carry no annotations of its own, like the 3.14 lru_cache one that only copies __annotate__
    try:
        obj = inspect.unwrap(obj)
    except ValueError:
        return None
    try:
        has_annotations = getattr(obj, "__annotations__", None)
    except (NameError, TypeError, AttributeError):
        # PEP 649 (Python 3.14+): annotation expressions only run on access and may fail at runtime
        # (TYPE_CHECKING-only names, subscripting a non-generic class). __annotate__ still signals
        # annotations exist, and sphinx_signature renders them without evaluation via FORWARDREF.
        has_annotations = getattr(obj, "__annotate__", None)
    if not has_annotations:
        return None

    sph_signature = sphinx_signature(obj, type_aliases=app.config["autodoc_type_aliases"])
    typehints_formatter: Callable[..., str | None] | None = getattr(app.config, "typehints_formatter", None)

    def _get_formatted_annotation(annotation: TypeVar) -> TypeVar:
        if typehints_formatter is None:
            return annotation
        formatted_name = typehints_formatter(annotation, app.config)
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
                    location=get_obj_location(obj),
                )
                return None
            if (member_type := _class_member_type(name)) is None:
                return None
            if not issubclass(member_type, staticmethod) and not inspect.ismethod(obj):
                start = 1

    sph_signature = sph_signature.replace(parameters=parameters[start:])
    formatted = stringify_signature(
        sph_signature,
        # a class signature describes the call building the instance, so its constructor's -> None does not belong
        show_return_annotation=app.config.typehints_use_signature_return and not inspect.isclass(original_obj),
        unqualified_typehints=not getattr(app.config, "typehints_fully_qualified", False),
    )
    # the directive strips one level of backslashes only under this option, so escaping otherwise doubles them
    return formatted.replace("\\", "\\\\") if app.config.strip_signature_backslash else formatted, None


def _is_dataclass(name: str, what: str, qualname: str) -> bool:
    return (what == "method" and name.endswith(".__init__")) or (what == "class" and qualname.endswith(".__init__"))


def process_docstring(  # ruff:ignore[too-many-arguments, too-many-positional-arguments]
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    options: Options | None,  # ruff:ignore[unused-function-argument]
    lines: list[str],
) -> None:
    """Process the docstring for an entry."""
    original_obj = obj
    obj = obj.fget if isinstance(obj, property) else obj
    if not callable(obj):
        _maybe_inject_descriptor_type(app, what, obj, lines)
        return
    if inspect.isclass(obj):
        # class and instance variable annotations evaluate in the modules defining the class and its __init__, so
        # their guarded imports must be bound first
        resolve_type_guarded_imports(app.config.autodoc_mock_imports, obj)
        resolve_type_guarded_imports(app.config.autodoc_mock_imports, inspect.unwrap(obj.__init__))
        backfill_attrs_annotations(obj)
        ivar_annotations = get_instance_var_annotations(obj)
    else:
        ivar_annotations = {}
    use_class_for_signature = False
    cls_for_hints = None
    if inspect.isclass(obj):
        obj = getattr(obj, constructor := _constructor_name(obj))
        use_class_for_signature = constructor == "__new__"
        # namedtuple builds __new__ without builtins, so forward references resolve only via the class (#657)
        cls_for_hints = original_obj if inspect.isfunction(obj) and obj.__module__.startswith("namedtuple_") else None
    try:
        obj = inspect.unwrap(obj)
    except ValueError:
        return

    try:
        signature = sphinx_signature(
            original_obj if use_class_for_signature else obj, type_aliases=app.config["autodoc_type_aliases"]
        )
    except (ValueError, TypeError):
        signature = None

    localns = {
        key: MyTypeAliasForwardRef(value, configured=True) for key, value in app.config["autodoc_type_aliases"].items()
    }
    module_prefix = name.rsplit(".", maxsplit=1)[0] if "." in name else ""
    eager_aliases: dict[str, MyTypeAliasForwardRef] = {}
    if (env := getattr(app, "env", None)) is not None:
        deferred, eager_aliases = collect_documented_type_aliases(obj, module_prefix, env)
        localns.update(deferred)
    type_hints = get_all_type_hints(app.config.autodoc_mock_imports, cls_for_hints or obj, name, localns)
    type_hints |= eager_aliases
    with _annotation_state(
        app.config,
        _annotation_globals=getattr(obj, "__globals__", {}),
        _typehints_env=env,
        _typehints_module_prefix=module_prefix,
        _typehints_resolve_guarded_imports=partial(resolve_type_guarded_imports, app.config.autodoc_mock_imports),
    ):
        has_overloads = _inject_overload_signatures(app, what, name, obj, lines)
        _inject_types_to_docstring(
            type_hints,
            signature,
            original_obj,
            app,
            what,
            name,
            lines,
            has_overloads,
            documented_elsewhere=_params_documented_elsewhere(app, name, original_obj, signature, lines),
        )
        _inject_ivar_types(ivar_annotations, app, lines)


def _constructor_name(cls: type) -> Literal["__new__", "__init__"]:
    """Choose the constructor as ``inspect.signature`` does: the one defined lowest in the MRO, ``__new__`` on a tie."""
    depth = {
        name: next(i for i, klass in enumerate(cls.__mro__) if name in vars(klass)) for name in ("__new__", "__init__")
    }
    # a __new__ that only wraps object's, as @warnings.deprecated adds, is no constructor of its own to inspect
    own_new = inspect.unwrap(cls.__new__) is not object.__new__
    return "__new__" if own_new and depth["__new__"] <= depth["__init__"] else "__init__"


@contextmanager
def _annotation_state(config: Config, **values: Any) -> Generator[None, None, None]:
    """
    Publish the state format_annotation reads off the config, restoring what was there.

    Documenting an object can re-enter this handler for another one, and deleting the attributes
    on the way out of the inner call then broke the outer call's teardown (#750).
    """
    previous = {name: getattr(config, name) for name in values if hasattr(config, name)}
    for name, value in values.items():
        setattr(config, name, value)
    try:
        yield
    finally:
        for name in values:
            if name in previous:
                setattr(config, name, previous[name])
            else:
                delattr(config, name)


def _maybe_inject_descriptor_type(app: Sphinx, what: str, obj: Any, lines: list[str]) -> None:
    """C data descriptors document as plain attributes; lift their type from the stub."""
    if what != "attribute" or not (inspect.isgetsetdescriptor(obj) or inspect.ismemberdescriptor(obj)):
        return
    if any(line.startswith(":type:") for line in lines):
        return
    if (hint := get_descriptor_type_hint(obj)) is None:
        return
    formatted = add_type_css_class(
        format_annotation(hint, app.config, short_literals=app.config.python_display_short_literal_types)
    )
    lines.extend(["", f":type: {formatted}"])


def _inject_overload_signatures(
    app: Sphinx,
    what: str,
    name: str,
    obj: Any,
    lines: list[str],
) -> bool:
    # strip the directive first, as it must not show even where overloads are not rendered
    if (
        _strip_no_overloads_directive(lines)
        or what not in {"function", "method", "class", "exception"}
        or not app.config.typehints_document_overloads
    ):
        return False
    if (overloads := _resolve_overloads(obj)) is None:
        return False
    if what in {"class", "exception"}:
        # a class documents its constructor's overloads, which return the instance like the class signature shows
        overloads = [overload.replace(return_annotation=inspect.Signature.empty) for overload in overloads]
    # overloads parsed from the source still list a method's self or cls
    skip = int(what != "function" and (what != "method" or _class_member_type(name) is not staticmethod))
    idx = _summary_end(lines)
    lines[idx:idx] = ["", *_format_overload_lines(overloads, obj, app, skip)]
    return True


def _summary_end(lines: list[str]) -> int:
    """Index past the summary paragraph so overloads land below it and autosummary still reads it (#730)."""
    if (start := next((i for i, line in enumerate(lines) if line.strip()), None)) is None:
        return len(lines)
    return next((i for i in range(start, len(lines)) if not lines[i].strip()), len(lines))


def _strip_no_overloads_directive(lines: list[str]) -> bool:
    for idx, line in enumerate(lines):
        if line.strip() == ":no-overloads:":
            del lines[idx]
            return True
    return False


def _resolve_overloads(obj: Any) -> list[inspect.Signature] | None:
    module_name = getattr(obj, "__module__", None)
    if not module_name or module_name not in _OVERLOADS_CACHE:
        return None
    qualname = getattr(obj, "__qualname__", None)
    if not qualname:
        return None
    return _OVERLOADS_CACHE[module_name].get(qualname) or None


def _class_member_type(name: str) -> type | None:
    """
    Locate the class through the documented name, not ``__qualname__``.

    A class can bind a function defined elsewhere (``add = staticmethod(helper)``).
    """
    parts = name.split(".")
    if (split := next((i for i in range(len(parts) - 1, 0, -1) if ".".join(parts[:i]) in sys.modules), None)) is None:
        return None
    owner = sys.modules[".".join(parts[:split])]
    for part in parts[split:-1]:
        if (owner := getattr(owner, part, None)) is None:
            return None
    attribute = parts[-1]
    if attribute.startswith("__") and not attribute.endswith("__"):
        attribute = f"_{owner.__name__.lstrip('_')}{attribute}"
    return None if (member := inspect.getattr_static(owner, attribute, None)) is None else type(member)


def _format_overload_lines(overloads: list[inspect.Signature], obj: Any, app: Sphinx, skip: int) -> list[str]:
    render = partial(format_annotation, config=app.config, short_literals=app.config.python_display_short_literal_types)
    result = [":Overloads:"]
    for overload_sig in overloads:
        # parsed from the source, so the annotations are strings until evaluated in the function's module
        hints = resolve_string_annotations(
            obj,
            {
                **{param_name: param.annotation for param_name, param in list(overload_sig.parameters.items())[skip:]},
                "return": overload_sig.return_annotation,
            },
            {},
        )
        return_hint = hints.pop("return")
        params = []
        for param_name, hint in hints.items():
            if hint is inspect.Parameter.empty:
                params.append(f"**{param_name}**")
            else:
                params.append(f"**{param_name}** ({add_type_css_class(render(hint))})")
        return_annotation = (
            "" if return_hint is inspect.Signature.empty else f" \u2192 {add_type_css_class(render(return_hint))}"
        )
        result.append(f"   * {', '.join(params)}{return_annotation}")
    result.append("")
    return result


def format_default(app: Sphinx, default: Any, is_annotated: bool) -> str | None:  # ruff:ignore[boolean-type-hint-positional-argument]
    if default is inspect.Parameter.empty:
        return None
    formatted = object_description(default).replace("\\", "\\\\")

    if is_annotated:
        if app.config.typehints_defaults.startswith("braces"):
            return f" (default: ``{formatted}``)"
        return f", default: ``{formatted}``"
    if app.config.typehints_defaults == "braces-after":
        return f" (default: ``{formatted}``)"
    return f"default: ``{formatted}``"


def _params_documented_elsewhere(
    app: Sphinx, name: str, obj: Any, signature: inspect.Signature | None, lines: list[str]
) -> frozenset[str]:
    """
    With ``autoclass_content = "both"`` Sphinx processes a class and its constructor docstring one after the other.

    Only the constructor's lists the parameters that neither of them documents.
    """
    if (
        not inspect.isclass(obj)
        or signature is None
        or (env := getattr(app, "env", None)) is None
        or not _has_constructor_docstring(app, obj)
    ):
        return frozenset()
    class_docstrings = env.temp_data.setdefault("sphinx_autodoc_typehints_class_docstrings", {})
    if (class_lines := class_docstrings.pop(name, None)) is None:
        class_docstrings[name] = lines
        return frozenset(signature.parameters)
    fmt = detect_format(class_lines)
    return frozenset(param for param in signature.parameters if fmt.find_param(class_lines, param) is not None)


def _has_constructor_docstring(app: Sphinx, cls: type) -> bool:
    """Mirror Sphinx's choice of docstrings for ``autoclass_content = "both"``."""
    if app.config.autoclass_content != "both" or not getdoc(cls):
        return False
    inherit = app.config.autodoc_inherit_docstrings
    init_doc = getdoc(cls.__init__, allow_inherited=inherit, cls=cls, name="__init__")
    if init_doc and init_doc != object.__init__.__doc__:
        return True
    new_doc = getdoc(cls.__new__, allow_inherited=inherit, cls=object, name="__new__")
    return bool(new_doc) and new_doc != object.__new__.__doc__


def _inject_types_to_docstring(  # ruff:ignore[too-many-arguments, too-many-positional-arguments]
    type_hints: dict[str, Any],
    signature: inspect.Signature | None,
    original_obj: Any,
    app: Sphinx,
    what: str,
    name: str,
    lines: list[str],
    has_overloads: bool = False,  # ruff:ignore[boolean-type-hint-positional-argument, boolean-default-value-positional-argument]
    *,
    documented_elsewhere: frozenset[str] = frozenset(),
) -> None:
    fmt = detect_format(lines)
    if signature is not None:
        for arg_name in signature.parameters:
            _inject_arg_signature(type_hints, signature, app, lines, arg_name, fmt, documented_elsewhere, "param")
        if keys := _unpacked_keywords(signature, type_hints):
            # after the parameters, as a docstring describes **kwargs before its keys
            keywords = inspect.Signature([inspect.Parameter(key, inspect.Parameter.KEYWORD_ONLY) for key in keys])
            for key in keys:
                _inject_arg_signature(keys, keywords, app, lines, key, fmt, documented_elsewhere, "keyword")
    if "return" in type_hints and not has_overloads:
        _inject_rtype(type_hints, original_obj, app, what, name, lines, fmt)


def _unpacked_keywords(signature: inspect.Signature, type_hints: dict[str, Any]) -> dict[str, Any]:
    """Return the keys of ``**kwargs: Unpack[TD]`` with their types, the keyword-only parameters PEP 692 makes them."""
    params = list(signature.parameters.values())
    if (
        not params
        or params[-1].kind is not inspect.Parameter.VAR_KEYWORD
        or get_origin(unpacked := type_hints.get(params[-1].name)) is not Unpack
    ):
        return {}
    return {
        key: annotation
        for key, annotation in typed_dict_keys(get_args(unpacked)[0]).items()
        if key.isidentifier() and not iskeyword(key) and key not in signature.parameters
    }


def _inject_arg_signature(  # ruff:ignore[too-many-arguments, too-many-positional-arguments]
    type_hints: dict[str, Any],
    signature: inspect.Signature,
    app: Sphinx,
    lines: list[str],
    arg_name: str,
    fmt: Any,
    documented_elsewhere: frozenset[str],
    field: Literal["param", "keyword"],
) -> None:
    annotation = type_hints.get(arg_name)
    default = signature.parameters[arg_name].default
    kind = signature.parameters[arg_name].kind
    doc_description = _extract_doc_description(annotation) if annotation is not None else None
    # taken by the signature's own name, as the docstring may spell it escaped (``x\_``)
    names = list(signature.parameters)
    later_names = names[names.index(arg_name) + 1 :]

    arg_name, insert_index = _find_param(lines, arg_name, fmt)

    # the annotation replaces a type written in the field, which otherwise becomes the type a default joins
    inline_type = ""
    if insert_index is not None and (stripped := _strip_inline_param_type(lines[insert_index], arg_name)):
        lines[insert_index], inline_type = stripped

    if insert_index is not None and hasattr(fmt, "get_arg_name_from_line"):
        arg_name = fmt.get_arg_name_from_line(lines[insert_index]) or arg_name

    if insert_index is None and _type_combined_field_entry(app, lines, arg_name, annotation, default):
        return

    if insert_index is None and (
        doc_description
        or (annotation is not None and app.config.always_document_param_types and arg_name not in documented_elsewhere)
    ):
        stars = {"VAR_POSITIONAL": "\\*", "VAR_KEYWORD": "\\*\\*"}.get(kind.name, "")
        entry = f"**{stars}{arg_name}**{f' -- {doc_description}' if doc_description else ''}"
        if _add_combined_field_entry(lines, field, entry, later_names):
            _type_combined_field_entry(app, lines, arg_name, annotation, default)
            return
        insert_index = fmt.add_undocumented_param(
            lines, arg_name, doc_description or "", before=_next_documented_param(lines, later_names, fmt), field=field
        )

    if insert_index is None:
        return

    preexisting_line, has_preexisting = fmt.find_preexisting_type(lines, arg_name)
    if annotation is None:
        type_annotation = (
            f":type {arg_name}: {inline_type}" if inline_type and not has_preexisting else preexisting_line
        )
    else:
        # napoleon gives keyword arguments a field of their own, which reads paramtype but not type
        type_field = "paramtype" if lines[insert_index].startswith((":keyword ", ":kwarg ", ":kwparam ")) else "type"
        type_annotation = ":{} {}: {}".format(
            type_field,
            arg_name,
            add_type_css_class(
                format_annotation(annotation, app.config, short_literals=app.config.python_display_short_literal_types)
            ),
        )

    # a braces-after default goes on the :param: line, so append it while insert_index still points there
    if app.config.typehints_defaults and (
        formatted_default := format_default(
            app, default, annotation is not None or has_preexisting or bool(inline_type)
        )
    ):
        type_annotation = fmt.append_default(
            lines,
            insert_index,
            type_annotation,
            formatted_default,
            after=app.config.typehints_defaults.endswith("after"),
        )

    if has_preexisting:
        _place_over_preexisting_type(lines, preexisting_line, type_annotation, keep=annotation is None)
    else:
        lines.insert(insert_index, type_annotation)


def _find_param(lines: list[str], arg_name: str, fmt: Any) -> tuple[str, int | None]:
    if not arg_name.endswith("_"):
        return arg_name, fmt.find_param(lines, arg_name)
    escaped_name = f"{arg_name[:-1]}\\_"
    if (insert_index := fmt.find_param(lines, escaped_name)) is not None:
        return escaped_name, insert_index
    if (insert_index := fmt.find_param(lines, arg_name)) is None:
        return escaped_name, None
    # napoleon only escapes the trailing underscore when strip_signature_backslash is on, and docutils
    # swallows an unescaped one as reference markup — see issue #708
    rewritten = lines[insert_index].replace(f" {arg_name}:", f" {escaped_name}:", 1)
    if rewritten == lines[insert_index]:
        return arg_name, insert_index
    lines[insert_index] = rewritten
    return escaped_name, insert_index


def _type_combined_field_entry(app: Sphinx, lines: list[str], arg_name: str, annotation: Any, default: Any) -> bool:
    """
    Type the ``**name** -- text`` entry of a combined field, where one field lists every parameter.

    Napoleon writes these with ``napoleon_use_param`` or ``napoleon_use_keyword`` off, and puts a docstring type in
    parentheses right after the name, which a type from the annotation follows too.
    """
    names = "|".join(re.escape(f"{prefix}{arg_name}") for prefix in ("", "\\*", "\\*\\*"))
    entry = re.compile(rf"^(?::[^:]+: +|\s+)(?:\* )?\*\*(?:{names})\*\*(?P<typed> \()?")
    if (found := next(((at, match) for at, line in enumerate(lines) if (match := entry.match(line))), None)) is None:
        return False
    at, match = found
    if match["typed"]:
        # the docstring's type stays, and only a default joins it
        type_end = _closing_parenthesis(lines[at], match.end())
    elif annotation is None:
        return False
    else:
        short_literals = app.config.python_display_short_literal_types
        typed = f" ({add_type_css_class(format_annotation(annotation, app.config, short_literals=short_literals))})"
        lines[at] = f"{lines[at][: match.end()]}{typed}{lines[at][match.end() :]}"
        type_end = match.end() + len(typed)
    if (
        type_end is None
        or not app.config.typehints_defaults
        or not (formatted_default := format_default(app, default, is_annotated=True))
    ):
        return True
    if app.config.typehints_defaults == "comma":
        lines[at] = f"{lines[at][: type_end - 1]}{formatted_default}{lines[at][type_end - 1 :]}"
    elif app.config.typehints_defaults == "braces":
        lines[at] = f"{lines[at][:type_end]}{formatted_default}{lines[at][type_end:]}"
    else:
        end = at
        while (
            end + 1 < len(lines)
            and lines[end + 1][:1].isspace()
            and lines[end + 1].strip()
            and not lines[end + 1].lstrip().startswith("* **")
        ):
            end += 1
        lines[end] += formatted_default
    return True


def _closing_parenthesis(line: str, start: int) -> int | None:
    """Return the index past the parenthesis closing the one opened right before ``start``, if the line closes it."""
    depth = 1
    for at, char in enumerate(line[start:], start):
        depth += {"(": 1, ")": -1}.get(char, 0)
        if not depth:
            return at + 1
    return None


def _add_combined_field_entry(
    lines: list[str], field: Literal["param", "keyword"], entry: str, later_names: list[str]
) -> bool:
    """
    Add a parameter the docstring leaves out to napoleon's combined field, when the docstring lists the others there.

    A field with one entry has no bullet, which it needs once it has two, and the entry goes before the first of the
    later parameters the field lists, keeping signature order.
    """
    heading = ":Parameters: " if field == "param" else ":Keyword Arguments: "
    if (start := next((at for at, line in enumerate(lines) if line.startswith(heading)), None)) is None:
        return False
    indent = " " * len(heading)
    end = start + 1
    while end < len(lines):
        # a blank line belongs to the field only inside an entry's description, which goes on indented after it
        if not (lines[end] or "".join(lines[end + 1 : end + 2])).startswith(indent):
            break
        end += 1
    if not lines[start].startswith(f"{heading}* "):
        lines[start] = f"{heading}* {lines[start][len(heading) :]}"
        lines[start + 1 : end] = [f"  {line}" if line else line for line in lines[start + 1 : end]]
    names = "|".join(re.escape(name) for name in later_names)
    later = re.compile(rf"(?:{re.escape(heading)}|{indent})\* \*\*(?:\\\*){{0,2}}(?:{names})\*\*")
    at = next((at for at in range(start, end) if later_names and later.match(lines[at])), end)
    if at == start:
        # the first entry shares its line with the heading, which the new entry takes over
        lines[start] = f"{indent}{lines[start][len(heading) :]}"
        lines.insert(start, f"{heading}* {entry}")
    else:
        lines.insert(at, f"{indent}* {entry}")
    return True


def _next_documented_param(lines: list[str], later_names: list[str], fmt: Any) -> int | None:
    """Return where the docstring documents the first of the later parameters, so fields keep signature order."""
    found = (fmt.find_param(lines, name) for name in later_names)
    return min((at for at in found if at is not None), default=None)


def _place_over_preexisting_type(lines: list[str], preexisting_line: str, type_annotation: str, *, keep: bool) -> None:
    """
    Put the type where the docstring typed the parameter.

    An annotated type replaces the docstring's. Without an annotation, the docstring's type stays as written,
    continuation lines and all, and only gains the default at its end.
    """
    idx = lines.index(preexisting_line)
    end = idx + 1
    while end < len(lines) and lines[end] and lines[end][0].isspace():
        end += 1
    if keep:
        lines[end - 1] += type_annotation.removeprefix(preexisting_line)
    else:
        lines[idx:end] = [type_annotation]


def _inject_rtype(  # ruff:ignore[too-many-arguments, too-many-positional-arguments]
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

    if (return_doc := _extract_doc_description(type_hints["return"])) and not fmt.has_return_description(lines):
        lines.append(f":return: {return_doc}")

    r = fmt.get_rtype_insert_info(app, lines)
    if r is None:
        return

    short_literals = app.config.python_display_short_literal_types
    formatted_annotation = add_type_css_class(
        format_annotation(type_hints["return"], app.config, short_literals=short_literals)
    )

    fmt.inject_rtype(lines, formatted_annotation, r, use_rtype=app.config.typehints_use_rtype)


# Matches a well-formed Sphinx ``:ivar ...:`` field list entry. Supports both
# ``:ivar name:`` and the inline-typed ``:ivar <type> name:`` grammar. The
# optional type is lazy so the final whitespace-delimited token before the
# closing colon is always captured as the attribute name. Anything that does
# not match (empty name, missing closing colon, bare ``:ivar :``) is skipped
# rather than crashing the parser — see issue #683.
_IVAR_FIELD_RE = re.compile(
    r"""
    ^:ivar                       # literal field marker
    (?:\s+(?P<type>\S.*?))?      # optional inline type expression
    \s+(?P<name>\w+)             # attribute name (Python identifier)
    \s*:                         # closing colon of the field name
    """,
    re.VERBOSE,
)


def _inject_ivar_types(ivar_annotations: dict[str, Any], app: Sphinx, lines: list[str]) -> None:
    line_index = 0
    while line_index < len(lines):
        match = _IVAR_FIELD_RE.match(lines[line_index])
        if match is None:
            line_index += 1
            continue
        attr_name = match["name"]
        has_inline_type = match["type"] is not None
        has_vartype = any(existing.startswith(f":vartype {attr_name}:") for existing in lines)
        if has_inline_type or has_vartype or attr_name not in ivar_annotations:
            line_index += 1
            continue
        formatted = add_type_css_class(
            format_annotation(
                ivar_annotations[attr_name],
                app.config,
                short_literals=app.config.python_display_short_literal_types,
            )
        )
        lines.insert(line_index, f":vartype {attr_name}: {formatted}")
        line_index += 2


def _extract_doc_description(annotation: Any) -> str | None:
    if not (hasattr(annotation, "__metadata__") and hasattr(annotation, "__origin__")):
        return None
    for meta in annotation.__metadata__:
        if type(meta).__qualname__ == "Doc" and type(meta).__module__ in {"typing_extensions", "typing"}:
            return meta.documentation
    return None


def validate_config(app: Sphinx, env: BuildEnvironment, docnames: list[str]) -> None:  # ruff:ignore[unused-function-argument]
    valid = {None, "comma", "braces", "braces-after"}
    if app.config.typehints_defaults not in valid | {False}:
        msg = f"typehints_defaults needs to be one of {valid!r}, not {app.config.typehints_defaults!r}"
        raise ConfigError(msg)

    formatter = app.config.typehints_formatter
    if formatter is not None and not callable(formatter):
        msg = f"typehints_formatter needs to be callable or `None`, not {formatter}"
        raise ConfigError(msg)

    app.config._intersphinx_type_mapping = build_type_mapping(env)  # ruff:ignore[private-member-access]


def sphinx_autodoc_typehints_type_role(
    _role: str,
    _rawtext: str,
    text: str,
    lineno: int,
    inliner: states.Inliner,
    _options: dict[str, Any] | None = None,
    _content: list[str] | None = None,
) -> tuple[list[Node], list[Node]]:
    # a type is inline text, a block parse would turn one such as ``- item`` into a list
    children, messages = inliner.parse(unescape(text), lineno, inliner, inliner.parent)
    return [nodes.inline(text, "", *children, classes=["sphinx_autodoc_typehints-type"])], messages


def setup(app: Sphinx) -> dict[str, bool | str]:
    app.setup_extension("sphinx.ext.autodoc")
    app.add_config_value("always_document_param_types", False, "env")  # ruff:ignore[boolean-positional-value-in-call]
    app.add_config_value("typehints_fully_qualified", False, "env")  # ruff:ignore[boolean-positional-value-in-call]
    app.add_config_value("typehints_document_rtype", True, "env")  # ruff:ignore[boolean-positional-value-in-call]
    app.add_config_value("typehints_document_rtype_none", True, "env")  # ruff:ignore[boolean-positional-value-in-call]
    app.add_config_value("typehints_use_rtype", True, "env")  # ruff:ignore[boolean-positional-value-in-call]
    app.add_config_value("typehints_defaults", None, "env")
    app.add_config_value("simplify_optional_unions", True, "env")  # ruff:ignore[boolean-positional-value-in-call]
    app.add_config_value("always_use_bars_union", False, "env")  # ruff:ignore[boolean-positional-value-in-call]
    app.add_config_value("typehints_formatter", None, "")
    app.add_config_value("typehints_document_overloads", True, "env")  # ruff:ignore[boolean-positional-value-in-call]
    app.add_config_value("typehints_use_signature", False, "env")  # ruff:ignore[boolean-positional-value-in-call]
    app.add_config_value("typehints_use_signature_return", False, "env")  # ruff:ignore[boolean-positional-value-in-call]
    app.add_config_value("typehints_fixup_module_name", None, "")
    app.add_role("sphinx_autodoc_typehints_type", sphinx_autodoc_typehints_type_role)
    app.add_role(ALIAS_CHOICE_ROLE, alias_choice_role)
    app.add_post_transform(DeferAliasChoice)
    app.connect("env-merge-info", merge_alias_choices)
    app.connect("env-before-read-docs", validate_config)
    app.connect("autodoc-process-signature", process_signature)
    app.connect("autodoc-process-docstring", process_docstring)
    app.connect("object-description-transform", add_type_params)
    install_patches(app)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


__all__ = [
    "__version__",
    "backfill_type_hints",
    "format_annotation",
    "get_annotation_args",
    "get_annotation_class_name",
    "get_annotation_module",
    "process_docstring",
    "process_signature",
]
