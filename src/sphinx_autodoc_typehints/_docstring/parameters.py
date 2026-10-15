"""
Types the parameter fields of a docstring.

It also adds a field for a parameter the docstring leaves out when `always_document_param_types` is on or a
`typing.Doc` describes it, and places each default where `typehints_defaults` puts it.
"""

from __future__ import annotations

from dataclasses import dataclass
from inspect import Parameter, Signature
from keyword import iskeyword
from typing import TYPE_CHECKING, Final, Literal, Unpack, get_args, get_origin

from .._documented import as_written
from .._render import as_field_type
from .._resolve import typed_dict_keys
from .._types import frozendict
from .formats import (
    STAR_PREFIXES,
    add_combined_field_entry,
    field_keyword_and_argument,
    format_default,
    last_paragraph_end,
    type_combined_field_entry,
)
from .returns import description_from_doc

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sphinx.application import Sphinx

    from .._documented import ResolvedHints
    from .._refs import WrittenTypeAlias
    from .._types import Hint
    from .formats import FieldListFormat

VARIADIC_STARS: Final[Mapping[str, str]] = frozendict({"VAR_POSITIONAL": "\\*", "VAR_KEYWORD": "\\*\\*"})


def inject_parameters(
    app: Sphinx,
    lines: list[str],
    fmt: FieldListFormat,
    signature: Signature,
    hints: ResolvedHints,
    *,
    documented_elsewhere: frozenset[str],
) -> None:
    """
    Type the parameter fields of a docstring, adding those it leaves out where the configuration asks for them.

    `documented_elsewhere` names the parameters the other docstring of a class entry documents.
    """
    fields = _Fields(app, lines, fmt, signature, hints.types)
    for arg_name in signature.parameters:
        fields.type_parameter(
            arg_name,
            written=hints.written_as.get(arg_name),
            documented_elsewhere=arg_name in documented_elsewhere,
            field="param",
        )
    # the keys of `**kwargs: Unpack[TD]`, which PEP 692 lets callers pass by keyword only, follow the parameters, as a
    # docstring describes **kwargs before its keys
    if (
        not (params := list(signature.parameters.values()))
        or (kwargs := params[-1]).kind is not Parameter.VAR_KEYWORD
        or get_origin(unpacked := hints.types.get(kwargs.name)) is not Unpack
    ):
        return
    keys = {
        key: annotation
        for key, annotation in typed_dict_keys(get_args(unpacked)[0], {}).items()
        if key.isidentifier() and not iskeyword(key) and key not in signature.parameters
    }
    if not keys:
        return
    keywords = Signature([Parameter(key, Parameter.KEYWORD_ONLY) for key in keys])
    # the keys go with the part documenting **kwargs, or the one listing what neither part documents
    keys_elsewhere = kwargs.name in documented_elsewhere and fmt.find_param(lines, kwargs.name) is None
    key_fields = _Fields(app, lines, fmt, keywords, keys)
    for key in keys:
        key_fields.type_parameter(
            key, written=None, documented_elsewhere=keys_elsewhere or key in documented_elsewhere, field="keyword"
        )


@dataclass(frozen=True, slots=True)
class _Fields:
    app: Sphinx
    lines: list[str]
    fmt: FieldListFormat
    signature: Signature
    hints: Mapping[str, Hint]

    def type_parameter(
        self,
        arg_name: str,
        *,
        written: WrittenTypeAlias | None,
        documented_elsewhere: bool,
        field: Literal["param", "keyword"],
    ) -> None:
        annotation = self.hints.get(arg_name)
        signature_param = self.signature.parameters[arg_name]
        param = _Parameter(
            annotation,
            as_written(annotation, written),
            signature_param.default,
            VARIADIC_STARS.get(signature_param.kind.name, ""),
        )
        doc_name, at = _find_param(self.lines, arg_name, self.fmt)
        inline_type = ""
        if at is not None:
            # the annotation replaces a type a `:param type name:` field writes, which otherwise becomes the type a
            # default joins
            _, directive_and_name, description = self.lines[at].split(":", maxsplit=2)
            if (
                star := next(
                    (star for star in STAR_PREFIXES if directive_and_name.endswith(f" {star}{doc_name}")), None
                )
            ) is not None:
                keyword, _, inline_type = directive_and_name.removesuffix(f" {star}{doc_name}").partition(" ")
                self.lines[at], inline_type = f":{keyword} {star}{doc_name}:{description}", inline_type.strip()
            doc_name = parsed[1] if (parsed := field_keyword_and_argument(self.lines[at])) and parsed[1] else doc_name
        elif type_combined_field_entry(self.app, self.lines, doc_name, param.shown, param.default):
            return
        elif not documented_elsewhere and (
            (doc_description := description_from_doc(annotation))
            or (annotation is not None and self.app.config.always_document_param_types)
        ):
            # taken by the signature's own name, as the docstring may spell it escaped (`x\_`)
            names = list(self.signature.parameters)
            later_names = names[names.index(arg_name) + 1 :]
            entry = f"**{param.stars}{doc_name}**{f' -- {doc_description}' if doc_description else ''}"
            # joining napoleon's combined field leaves no field of its own to type
            if add_combined_field_entry(self.lines, field, entry, later_names):
                type_combined_field_entry(self.app, self.lines, doc_name, param.shown, param.default)
            else:
                # before the first later parameter the docstring documents, so fields keep signature order
                at = self.fmt.add_undocumented_param(
                    self.lines,
                    doc_name,
                    doc_description or "",
                    before=min(
                        (index for name in later_names if (index := self.fmt.find_param(self.lines, name)) is not None),
                        default=None,
                    ),
                    field=field,
                )
        if at is not None:
            self._write_type(at, doc_name, param, inline_type)

    def _write_type(self, at: int, doc_name: str, param: _Parameter, inline_type: str) -> None:
        # napoleon types a keyword argument with kwtype, and paramtype works for both parameter kinds
        fields = tuple(f":{field} {doc_name}: " for field in ("type", "paramtype", "kwtype"))
        preexisting_line, has_preexisting = next(
            ((line, True) for line in self.lines if line.startswith(fields)), (fields[0], False)
        )
        if param.annotation is None or param.shown is None:
            type_annotation = (
                f":type {doc_name}: {inline_type}" if inline_type and not has_preexisting else preexisting_line
            )
        else:
            # napoleon gives keyword arguments a field of their own, which reads paramtype but not type
            type_field = "paramtype" if self.lines[at].startswith((":keyword ", ":kwarg ", ":kwparam ")) else "type"
            type_annotation = f":{type_field} {doc_name}: {as_field_type(param.shown, self.app.config)}"
        # a braces-after default goes on the :param: line, so append it while at still points there
        if self.app.config.typehints_defaults and (
            formatted_default := format_default(
                self.app, param.default, annotated=param.annotation is not None or has_preexisting or bool(inline_type)
            )
        ):
            if not self.app.config.typehints_defaults.endswith("after"):
                type_annotation += formatted_default
            # a paragraph introducing a literal block keeps its :: last
            elif (line := self.lines[end := last_paragraph_end(self.lines, at)]).endswith("::"):
                self.lines[end] = f"{line[:-2].rstrip()}{formatted_default}::"
            else:
                self.lines[end] += formatted_default
        if has_preexisting:
            idx = self.lines.index(preexisting_line)
            end = idx + 1
            while end < len(self.lines) and self.lines[end] and self.lines[end][0].isspace():
                end += 1
            # without an annotation, the docstring's type stays as written, continuation lines and all, and only gains
            # the default at its end
            if param.annotation is None:
                self.lines[end - 1] += type_annotation.removeprefix(preexisting_line)
            else:
                self.lines[idx:end] = [type_annotation]
        else:
            self.lines.insert(at, type_annotation)


# `shown` is the type as the annotation names it, an alias by its own name
@dataclass(frozen=True, slots=True)
class _Parameter:
    annotation: Hint | None
    shown: Hint | WrittenTypeAlias | None
    default: object
    stars: str


def _find_param(lines: list[str], arg_name: str, fmt: FieldListFormat) -> tuple[str, int | None]:
    if not arg_name.endswith("_"):
        return arg_name, fmt.find_param(lines, arg_name)
    escaped_name = escape_trailing_underscore(arg_name)
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


def escape_trailing_underscore(name: str) -> str:
    r"""Spell a trailing underscore the way docutils needs it, `x\_`, as it reads a bare one as a reference."""
    return f"{name[:-1]}\\_" if name.endswith("_") else name


__all__ = [
    "VARIADIC_STARS",
    "escape_trailing_underscore",
    "inject_parameters",
]
