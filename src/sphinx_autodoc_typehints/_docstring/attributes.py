"""
Types the variable fields and attribute directives of a class or module docstring.

The types come from the annotations of the class or module body and of `__init__`.
"""

from __future__ import annotations

import re  # a from-import of compile would shadow the builtin
from contextlib import suppress
from inspect import unwrap
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from .._objects import is_attrs_class
from .._render import as_field_type
from .._resolve import (
    bound_type_args,
    get_body_annotations,
    get_instance_var_annotations,
    resolve_type_guarded_imports,
    specialize,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from sphinx.application import Sphinx

    from .._types import Annotation

# the lazy type leaves the last token before the closing colon to the name; a line this does not match, such as a bare
# `:ivar :`, is no field to type and must not crash the parse (#683)
_IVAR_FIELD_RE: Final[re.Pattern[str]] = re.compile(
    dedent(r"""
        ^:(?:ivar|cvar|var)
        (?:\s+(?P<type>\S.*?))?
        \s+(?P<name>\w+)
        \s*:
    """),
    re.VERBOSE,
)
_ATTRIBUTE_DIRECTIVE_RE: Final[re.Pattern[str]] = re.compile(r"\.\. attribute:: (\w+)$")


def class_attribute_annotations(
    app: Sphinx, cls: type, written: frozenset[str] | None
) -> tuple[dict[str, Annotation | str], dict[str, Annotation | str]]:
    """Return the annotations that type the `:ivar:` fields of `cls` and those that type its attribute entries."""
    # class and instance variable annotations evaluate in the modules defining the class and its __init__, so
    # their guarded imports must be bound first
    resolve_type_guarded_imports(app.config.autodoc_mock_imports, cls)
    resolve_type_guarded_imports(app.config.autodoc_mock_imports, unwrap(cls.__init__))
    if is_attrs_class(cls):
        from attrs import fields  # ruff:ignore[import-outside-top-level]  # optional, and installed for any class it made

        # PEP 649 evaluates annotations on first read, so one naming something undefined fails here; such a class keeps
        # its annotations as written rather than failing the build
        with suppress(Exception):
            if (declared := getattr(cls, "__annotations__", None)) is None:
                declared = cls.__annotations__ = {}
            # attrs types a field through its `type` argument, which the class body may leave unannotated
            for field in fields(cls):
                if field.type is not None:
                    declared.setdefault(field.name, field.type)
    # one inherited from a generic base reads as `cls` binds it
    body: dict[str, Annotation] = {
        attribute: specialize(hint, arguments) if (arguments := bound_type_args(cls, attribute)) else hint
        for attribute, hint in get_body_annotations(cls).items()
    }
    # one an inherited `__init__` assigns reads as `cls` binds the base defining it
    assigned = get_instance_var_annotations(cls)
    if arguments := bound_type_args(cls, "__init__"):
        assigned = {attribute: specialize(hint, arguments) for attribute, hint in assigned.items()}
    # an assignment in __init__ is the more specific declaration of the two; with napoleon_attr_annotations off,
    # napoleon's :ivar: fields still take its type for backward compatibility, while its attribute entries stay untyped
    return _without_napoleon_entries(body, written) | assigned, _without_napoleon_entries(body | assigned, written)


def _without_napoleon_entries[Value](hints: dict[str, Value], written: frozenset[str] | None) -> dict[str, Value]:
    return hints if written is None else {name: hint for name, hint in hints.items() if name in written}


def documented_attributes(lines: list[str]) -> Iterator[str]:
    """Yield the name of each attribute `lines` document with a variable field or an `.. attribute::` entry."""
    for line in lines:
        if field := _IVAR_FIELD_RE.match(line):
            yield field["name"]
        elif directive := _ATTRIBUTE_DIRECTIVE_RE.match(line):
            yield directive[1]


def inject_ivar_types(ivar_annotations: Mapping[str, Annotation | str], app: Sphinx, lines: list[str]) -> None:
    """Add a `:vartype:` field above each variable field that states no type, where an annotation gives one."""
    line_index = 0
    while line_index < len(lines):
        if (match := _IVAR_FIELD_RE.match(lines[line_index])) is None:
            line_index += 1
            continue
        attr_name = match["name"]
        if (
            match["type"] is not None
            or any(existing.startswith(f":vartype {attr_name}:") for existing in lines)
            or attr_name not in ivar_annotations
        ):
            line_index += 1
            continue
        lines.insert(line_index, f":vartype {attr_name}: {as_field_type(ivar_annotations[attr_name], app.config)}")
        line_index += 2


def inject_attribute_types(ivar_annotations: Mapping[str, Annotation | str], app: Sphinx, lines: list[str]) -> None:
    """
    Type the `.. attribute::` entries napoleon writes for an `Attributes` section with `napoleon_use_ivar` off.

    Napoleon types them from the class body's annotations; one annotated where `__init__` assigns it gets its type
    here, as a `:type:` field closing the entry the way napoleon writes one.
    """
    at = 0
    while at < len(lines):
        if not (directive := _ATTRIBUTE_DIRECTIVE_RE.match(lines[at])) or directive[1] not in ivar_annotations:
            at += 1
            continue
        end = at + 1
        while end < len(lines) and (not lines[end] or lines[end][:1].isspace()):
            end += 1
        while not lines[end - 1].strip():
            end -= 1
        if not any(line.strip().startswith(":type:") for line in lines[at:end]):
            lines[end:end] = ["", f"   :type: {as_field_type(ivar_annotations[directive[1]], app.config)}"]
        at = end


__all__ = [
    "class_attribute_annotations",
    "documented_attributes",
    "inject_attribute_types",
    "inject_ivar_types",
]
