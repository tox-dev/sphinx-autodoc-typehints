"""Listens to `autodoc-process-signature` to keep or strip the types of a signature, one line per overload."""

from __future__ import annotations

from inspect import Parameter, Signature, isclass, isfunction, ismethod
from typing import TYPE_CHECKING

from sphinx.util.inspect import is_builtin_class_method, safe_getattr, stringify_signature
from sphinx.util.inspect import signature as sphinx_signature

from .._documented import (
    Entry,
    as_written,
    class_member_type,
    documenting_class,
    overload_skip,
    render_scope,
    resolved_type_hints,
    show_factory_defaults,
    typed_overloads,
)
from .._objects import (
    callable_target,
    constructor_name,
    declared_signature,
    prefix_of,
)
from .._private_imports import METACLASS_CALL_BLACKLIST, suppress_logging
from .._resolve import bound_type_args
from .._state import add_signature_lines, note_documented, written_signatures
from .._warnings import warn
from .header import signature_overloads
from .text import directive_text, names_other_parameters, signature_type

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.application import Sphinx
    from sphinx.ext.autodoc import Options

    from .._objects import QualifiedCallable
    from .._types import Documented


def process_signature(
    app: Sphinx,
    what: str,
    name: str,
    obj: Documented,
    options: Options,
    signature: str | None,
    _return_annotation: str,
) -> tuple[str, None] | None:
    """Return the signature autodoc shows for `name`, its types kept or left off as configured, or leave it."""
    # autodoc emits this for every object it documents, one it cannot import included, unlike the docstring event
    note_documented(app.env, name)
    # a page may document the object again, and only the entry this signature heads can have kept it as written
    written_signatures(app.env).discard(name)
    # Sphinx lists each singledispatch implementation under a nameless entry with no docstring to move types into,
    # and the dispatch type is what tells the implementations apart; data and attributes holding a callable show
    # no signature, so Sphinx passes none to replace
    if signature is None or not callable(obj) or not name.strip(".") or (target := _target(obj)) is None:
        return None
    callee, annotated = target
    overloads = signature_overloads(app, what, obj, callee, options)
    if not _annotates(annotated) and declared_signature(callee) is None and not overloads:
        return None
    entry = Entry(app, what, name, obj)
    full_signature = sphinx_signature(callee, type_aliases=app.config["autodoc_type_aliases"])
    if isclass(obj):
        full_signature = show_factory_defaults(obj, full_signature)
    shown, overloads = _shown_types(entry, callee, annotated, overloads)
    if app.config.typehints_use_signature_return:
        full_signature = full_signature.replace(return_annotation=shown.get("return", full_signature.return_annotation))
    keep = app.config.typehints_use_signature
    parameters = [
        param.replace(annotation=shown.get(param.name, param.annotation) if keep else Parameter.empty)
        for param in full_signature.parameters.values()
    ]
    if (start := _leading_skip(entry, callee, annotated, parameters)) is None:
        return None
    if names_other_parameters(signature, parameters[start:]):
        if overloads:
            # the header keeps the written signature, so the overloads go to the docstring field instead
            written_signatures(app.env).add(name)
        return None
    unqualified = not app.config.typehints_fully_qualified
    if overloads:
        # the return is what tells overloads apart, so each shows it
        texts = [
            directive_text(app, stringify_signature(overload, unqualified_typehints=unqualified))
            for overload in overloads
        ]
        # the directive shows the first, and each other overload on a line of its own
        add_signature_lines(app.env, name, texts)
        return texts[0], None
    formatted = stringify_signature(
        full_signature.replace(parameters=parameters[start:]),
        # a class signature describes the call building the instance, so its constructor's -> None does not belong
        show_return_annotation=app.config.typehints_use_signature_return and not isclass(obj),
        unqualified_typehints=unqualified,
    )
    return directive_text(app, formatted), None


def _target(obj: Callable[..., object]) -> tuple[QualifiedCallable, QualifiedCallable] | None:
    if isclass(obj) and declared_signature(obj) is None:
        # autodoc takes a class signature from the `__call__` of its metaclass ahead of the constructor
        call = None
        if (
            not is_builtin_class_method(metaclass := type(obj), "__call__")
            and isfunction(found := safe_getattr(metaclass, "__call__", None))
            and f"{found.__module__}.{found.__qualname__}" not in METACLASS_CALL_BLACKLIST
        ):
            try:
                parameters = sphinx_signature(found, bound_method=True).parameters.values()
            except ValueError:
                # autodoc moves on to the constructor too
                parameters = ()
            # a pass-through says nothing of the parameters, so the constructor shows them as for any catch-all (#903)
            if not all(param.kind in {param.VAR_POSITIONAL, param.VAR_KEYWORD} for param in parameters):
                call = found
        obj = call or getattr(obj, constructor_name(obj))
    return callable_target(obj)


def _annotates(annotated: QualifiedCallable) -> bool:
    try:
        return bool(annotated.__annotations__)
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        # PEP 649 runs an annotation on access, where a name a TYPE_CHECKING block binds or a subscripted non-generic
        # class fails; __annotate__ still shows annotations exist, and sphinx_signature renders them as FORWARDREF
        return getattr(annotated, "__annotate__", None) is not None


def _shown_types(
    entry: Entry, callee: QualifiedCallable, annotated: QualifiedCallable, overloads: list[Signature]
) -> tuple[dict[str, str | type[Parameter.empty]], list[Signature]]:
    app = entry.app
    if not (app.config.typehints_use_signature or app.config.typehints_use_signature_return):
        return {}, overloads
    # the docstring of the same object resolves these hints too, and warns about any that fail there
    with suppress_logging():
        hints = resolved_type_hints(app, entry.name, entry.obj, callee, annotated)
    # a kept type reads as its field does: the same resolution, aliases, fixups and formatter, written as Python
    with render_scope(app, prefix_of(entry.name), **hints.scope, signature=True):
        shown = {
            key: signature_type(app, as_written(hint, hints.written_as.get(key))) for key, hint in hints.types.items()
        }
        arguments = bound_type_args(*documenting_class(entry.name, entry.obj))
        typed = typed_overloads(app, entry.name, callee, overloads, overload_skip(entry), arguments)
        return shown, [
            overload.replace(
                parameters=[param.replace(annotation=signature_type(app, types[param.name])) for param in params],
                # the overloads of a class drop the return as its signature does
                return_annotation=Signature.empty if isclass(entry.obj) else signature_type(app, types["return"]),
            )
            for overload, (params, types) in zip(overloads, typed, strict=True)
        ]


# None leaves the entry as autodoc wrote it
def _leading_skip(
    entry: Entry, callee: QualifiedCallable, annotated: QualifiedCallable, parameters: list[Parameter]
) -> int | None:
    if not parameters:
        return 0
    # callers call a class with the signature it declares, while its constructor's starts with the instance
    if (isclass(entry.obj) and callee is not entry.obj) or entry.documents_init:
        return 1
    if entry.what != "method":
        return 0
    if (member_type := class_member_type(entry.name)) is None:
        if "<locals>" in annotated.__qualname__:
            warn(
                "local_function",
                'Cannot handle as a local function: "%s" (use @functools.wraps)',
                entry.name,
                at=annotated,
            )
        return None
    return 0 if issubclass(member_type, staticmethod) or ismethod(callee) else 1


__all__ = [
    "process_signature",
]
