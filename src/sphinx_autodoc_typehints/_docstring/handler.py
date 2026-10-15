"""The `autodoc-process-docstring` listener, which routes each docstring to the modules typing its fields."""

from __future__ import annotations

from inspect import isclass, isgetsetdescriptor, ismemberdescriptor, ismodule
from typing import TYPE_CHECKING

from sphinx.util.inspect import signature as sphinx_signature

from .._documented import Entry, render_scope, resolved_type_hints, show_factory_defaults
from .._objects import (
    callable_target,
    constructor_name,
    declared_signature,
    prefix_of,
)
from .._render import add_type_css_class, as_field_type, format_annotation
from .._resolve import (
    OPEN,
    extra_items_type,
    get_body_annotations,
    get_descriptor_type_hint,
    resolve_type_guarded_imports,
    stub_path,
)
from .attributes import (
    class_attribute_annotations,
    documented_attributes,
    inject_attribute_types,
    inject_ivar_types,
)
from .class_parts import docstring_part, has_constructor_docstring
from .deprecation import inject_deprecation
from .formats import WRITTEN_BEFORE_NAPOLEON, detect_format
from .object_fields import inject_overloads, inject_override, inject_setter_type, summary_end
from .parameters import inject_parameters
from .returns import inject_rtype

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.application import Sphinx
    from sphinx.ext.autodoc import Options

    from .._types import Documented


def process_docstring(
    app: Sphinx,
    what: str,
    name: str,
    obj: Documented,
    options: Options | None,
    lines: list[str],
) -> None:
    """Add the types of the object autodoc documents as `name` to its docstring `lines`."""
    written = WRITTEN_BEFORE_NAPOLEON.pop(id(lines), None)
    documented = obj.fget if isinstance(obj, property) else obj
    # a stub supplies the types of what it describes, so editing it has to reread the pages documenting them
    if (stub := stub_path(documented, name)) is not None:
        app.env.note_dependency(str(stub))
    if ismodule(documented):
        # evaluating the annotations runs the module's guard, which a docstring listing no attribute does not need
        if any(documented_attributes(lines)):
            resolve_type_guarded_imports(app.config.autodoc_mock_imports, documented)
            body_hints = {
                name: hint
                for name, hint in get_body_annotations(documented).items()
                if written is None or name in written
            }
            with render_scope(app, name):
                inject_ivar_types(body_hints, app, lines)
                inject_attribute_types(body_hints, app, lines)
    # a data or attribute entry documents the value it holds, which a call to it does not describe
    elif what in {"data", "attribute"} or not callable(documented):
        # a C data descriptor, which autodoc documents as a plain attribute, takes its type from its stub
        if (
            what == "attribute"
            and (isgetsetdescriptor(documented) or ismemberdescriptor(documented))
            and not any(line.startswith(":type:") for line in lines)
            and (hint := get_descriptor_type_hint(documented)) is not None
        ):
            # rendered with the state a parameter's type gets, so aliases and the inventory's roles apply here too
            with render_scope(app, prefix_of(name)):
                lines.extend(["", f":type: {as_field_type(hint, app.config)}"])
    else:
        _type_callable(Entry(app, what, name, obj), documented, options, lines, written)


# `declared` is the callable before unwrapping, as decorators mark that one
def _type_callable(
    entry: Entry,
    declared: Callable[..., object],
    options: Options | None,
    lines: list[str],
    written: frozenset[str] | None,
) -> None:
    app = entry.app
    if isclass(declared):
        ivar_annotations, attribute_annotations = class_attribute_annotations(app, declared, written)
        callee = getattr(declared, constructor := constructor_name(declared))
        use_class_for_signature = constructor == "__new__" or declared_signature(entry.obj) is not None
    else:
        ivar_annotations = attribute_annotations = {}
        callee, use_class_for_signature = declared, False
    if (target := callable_target(callee)) is None:
        return
    callee, annotated = target
    try:
        signature = (
            sphinx_signature(subject, type_aliases=app.config["autodoc_type_aliases"])
            if callable(subject := entry.obj if use_class_for_signature else callee)
            else None
        )
    except (ValueError, TypeError):
        signature = None
    if signature is not None and isclass(entry.obj):
        signature = show_factory_defaults(entry.obj, signature)
    hints = resolved_type_hints(app, entry.name, entry.obj, callee, annotated)
    with render_scope(app, prefix_of(entry.name), **hints.scope):
        part, documented_elsewhere = (
            docstring_part(app.env, entry.name, signature, options, lines)
            if signature is not None and has_constructor_docstring(app, entry.name, entry.obj, options)
            else ("whole", frozenset())
        )
        # the constructor's overloads describe its part, while the notice heads the entry
        has_overloads = part != "class" and inject_overloads(entry, callee, lines)
        if part != "constructor":
            inject_deprecation(declared, lines, summary_end(lines))
        fmt = detect_format(lines)
        if signature is not None:
            inject_parameters(app, lines, fmt, signature, hints, documented_elsewhere=documented_elsewhere)
        if "return" in hints.types and not has_overloads:
            inject_rtype(entry, lines, fmt, hints)
        inject_ivar_types(ivar_annotations, app, lines)
        inject_attribute_types(attribute_annotations, app, lines)
        # `closed=True` means the same as `extra_items=Never` (PEP 728), so both show as an `Extra items` type
        if (extra := extra_items_type(entry.obj, set())) is not OPEN and not any(
            line.startswith(":Extra items:") for line in lines
        ):
            lines.extend(["", f":Extra items: {add_type_css_class(format_annotation(extra, app.config))}"])
        inject_setter_type(app, entry.name, entry.obj, hints.types, lines)
        inject_override(app, entry.what, entry.name, declared, lines)


__all__ = [
    "process_docstring",
]
