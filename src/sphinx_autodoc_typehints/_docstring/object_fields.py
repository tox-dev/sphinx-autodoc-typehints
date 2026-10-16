"""Adds the fields about the object as a whole, such as its overloads and the member it overrides."""

from __future__ import annotations

from functools import partial
from inspect import Parameter, Signature, isclass, signature, unwrap
from typing import TYPE_CHECKING

from sphinx.util.inspect import object_description

from .._documented import (
    OVERLOADED_KINDS,
    as_written,
    documenting_class,
    overload_skip,
    resolved_type_hints,
    typed_overloads,
)
from .._objects import documented_owner, stored_name
from .._render import as_field_type, fixup_module_name
from .._resolve import bound_type_args, resolve_overloads
from .._state import written_signatures
from .parameters import VARIADIC_STARS

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from sphinx.application import Sphinx

    from .._documented import Entry
    from .._types import Documented, Hint


def inject_overloads(entry: Entry, obj: Callable[..., object], lines: list[str]) -> bool:
    """
    List the overloads of `obj`, the callable `entry` documents, below the summary, and return whether it has some.

    With `typehints_use_signature` the signature lines show them instead, so they are only reported.
    """
    app, what, name = entry.app, entry.what, entry.name
    # strip the directive first, as it must not show even where overloads are not rendered
    if (
        directive_at := next((at for at, line in enumerate(lines) if line.strip() == ":no-overloads:"), None)
    ) is not None:
        del lines[directive_at]
        return False
    if (
        what not in OVERLOADED_KINDS
        or not app.config.typehints_document_overloads
        or (overloads := resolve_overloads(obj)) is None
    ):
        return False
    # the signature lines show them then, unless a written signature took their place
    if app.config.typehints_use_signature and name not in written_signatures(app.env):
        return True
    # a class documents its constructor's overloads, which return the instance like the class signature shows
    if isclass(entry.obj):
        overloads = [overload.replace(return_annotation=Signature.empty) for overload in overloads]
    arguments = bound_type_args(*documenting_class(name, entry.obj))
    render = partial(as_field_type, config=app.config)
    listed = ["", ":Overloads:"]
    for parameters, hints in typed_overloads(app, name, obj, overloads, overload_skip(entry), arguments):
        entries: list[str] = []
        for at, param in enumerate(parameters):
            if param.kind is param.KEYWORD_ONLY and (
                not at or parameters[at - 1].kind in {param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD}
            ):
                entries.append("\\*")
            hint = hints[param.name]
            entries.append(
                f"**{VARIADIC_STARS.get(param.kind.name, '')}{param.name}**"
                f"{f' ({typed})' if hint is not Parameter.empty and (typed := render(hint)) else ''}"
                f"{'' if param.default is param.empty else f' = ``{object_description(param.default)}``'}"
            )
            if param.kind is param.POSITIONAL_ONLY and (
                at + 1 == len(parameters) or parameters[at + 1].kind is not param.POSITIONAL_ONLY
            ):
                entries.append("/")
        returned = (
            f" → {return_type}"
            if (return_hint := hints["return"]) is not Signature.empty and (return_type := render(return_hint))
            else ""
        )
        listed.append(f"   * {', '.join(entries) or '()'}{returned}")
    summary_at = summary_end(lines)
    lines[summary_at:summary_at] = [*listed, ""]
    return True


def summary_end(lines: list[str]) -> int:
    """Return the index past the summary paragraph, so overloads land below it and autosummary still reads it (#730)."""
    if (start := next((i for i, line in enumerate(lines) if line.strip()), None)) is None:
        return len(lines)
    end = next((i for i in range(start, len(lines)) if not lines[i].strip()), len(lines))
    if not lines[end - 1].rstrip().endswith("::"):
        return end
    # a summary introducing a literal block owns the indented lines after it, so nothing can go between them
    return next((i for i in range(end, len(lines)) if lines[i].strip() and not lines[i][:1].isspace()), len(lines))


def inject_setter_type(
    app: Sphinx, name: str, obj: Documented, getter_hints: Mapping[str, Hint], lines: list[str]
) -> None:
    """Show the type a property's setter accepts where it differs from the getter's, the one its header shows."""
    if not isinstance(obj, property) or obj.fset is None or any(line.startswith(":Setter accepts:") for line in lines):
        return
    # property() takes any object as its setter, and pygments passes a docstring there
    if not callable(setter := unwrap(obj.fset)):
        return
    try:
        parameters = list(signature(setter).parameters)
    except (ValueError, TypeError):
        return
    if not parameters:
        return
    resolved = resolved_type_hints(app, name, setter, setter, setter)
    param = parameters[-1]
    accepted = resolved.types.get(param, Parameter.empty)
    if (
        accepted is Parameter.empty
        or accepted == getter_hints.get("return", Parameter.empty)
        or not (accepted_type := as_field_type(as_written(accepted, resolved.written_as.get(param)), app.config))
    ):
        return
    lines.extend(["", f":Setter accepts: {accepted_type}"])


def inject_override(app: Sphinx, what: str, name: str, obj: Callable[..., object], lines: list[str]) -> None:
    if what not in {"method", "property"} or getattr(obj, "__override__", False) is not True:
        return
    owner, attribute = documented_owner(name)
    if not isinstance(owner, type):
        return
    stored = stored_name(owner, attribute)
    # an inherited member overrides what its defining class's bases define, not what that class itself does
    if (base := next(iter([klass for klass in owner.__mro__ if stored in vars(klass)][1:]), None)) is None:
        return
    target = f"{fixup_module_name(app.config, base.__module__)}.{base.__qualname__}.{attribute}"
    # the class names which override this is, a bare member name would not; an explicit title keeps the parentheses
    # Sphinx adds to a bare method reference out of it
    label = target if app.config.typehints_fully_qualified else f"{base.__qualname__}.{attribute}"
    lines.extend(["", f":Overrides: :py:{'attr' if what == 'property' else 'meth'}:`{label} <{target}>`"])


__all__ = [
    "inject_overloads",
    "inject_override",
    "inject_setter_type",
    "summary_end",
]
