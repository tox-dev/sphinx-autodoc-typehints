"""Types what a callable returns and yields, and adds the description a `typing.Doc` return carries."""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
from inspect import isclass, isdatadescriptor
from types import NoneType
from typing import TYPE_CHECKING, Annotated, Final, get_args, get_origin

from .._documented import as_written
from .._render import as_field_type
from .formats import reads_as_type, write_rtype

if TYPE_CHECKING:
    from sphinx.application import Sphinx

    from .._documented import Entry, ResolvedHints
    from .._types import Hint
    from .formats import FieldListFormat

_YIELDS_FIELDS: Final[tuple[str, ...]] = (":Yields:", ":yields:", ":yield:")


def inject_rtype(entry: Entry, lines: list[str], fmt: FieldListFormat, hints: ResolvedHints) -> None:
    """Type what the documented callable returns, and what it yields where its docstring has a Yields section."""
    app = entry.app
    if (
        isclass(entry.obj)
        or isdatadescriptor(entry.obj)
        or entry.documents_init
        or not app.config.typehints_document_rtype
    ):
        return
    type_hints = hints.types
    if any(line.startswith(_YIELDS_FIELDS) for line in lines):
        origin = getattr(produced := _unannotated(type_hints["return"]), "__origin__", None)
        # a generator or iterator, sync or async, matched by identity, as a set lookup would hash the annotation, which
        # Annotated with dict metadata cannot do
        if any(
            kind is origin or kind is produced
            for kind in (
                Generator,
                Iterator,
                AsyncGenerator,
                AsyncIterator,
            )
        ):
            # asked first, as it turns numpydoc's sections into the fields the Yields entry is read from
            described = fmt.has_return_description(lines)
            _type_yields(produced, app, lines)
            # the Yields section covers what it produces, leaving the value its return statement gives, the R of
            # Generator[Y, S, R], for a Returns section that describes it
            match get_args(produced) if get_origin(produced) is Generator else ():
                case (_, _, returned) if returned is not None and returned is not NoneType and described:
                    type_hints = {**type_hints, "return": returned}
                case _:
                    return

    if (return_doc := description_from_doc(type_hints["return"])) and not fmt.has_return_description(lines):
        lines.append(f":return: {return_doc}")

    # a Doc on a None return still describes it, so the description stays and only the type drops out
    if not app.config.typehints_document_rtype_none and _unannotated(type_hints["return"]) is NoneType:
        return

    info = fmt.get_rtype_insert_info(app, lines)
    formatted_annotation = as_field_type(as_written(type_hints["return"], hints.written_as.get("return")), app.config)
    write_rtype(lines, formatted_annotation, info, use_rtype=app.config.typehints_use_rtype)


def _unannotated(annotation: Hint) -> Hint:
    # Annotated only attaches metadata to the type it wraps, which is what the function returns
    return get_args(annotation)[0] if get_origin(annotation) is Annotated else annotation


def _type_yields(annotation: Hint, app: Sphinx, lines: list[str]) -> None:
    # found again, as reading the return description above may have converted the sections before it
    at = next(at for at, line in enumerate(lines) if line.startswith(_YIELDS_FIELDS))
    _, field, text = lines[at].split(":", 2)
    text = text.strip()
    # the text before -- or the whole entry may already be a type, as numpydoc writes an entry holding the type alone,
    # and a bullet, which starts one of several entries, reads as one too
    if not (args := get_args(annotation)) or (text and reads_as_type(text)):
        return
    # numpydoc lists several yielded values as typed bullets under an empty entry
    following = next((stripped for line in lines[at + 1 :] if (stripped := line.strip())), "")
    if not text and following.startswith("* ") and reads_as_type(following[2:]):
        return
    formatted = as_field_type(args[0], app.config)
    if text:
        lines[at] = f":{field}: {formatted} -- {text}"
    else:
        # the description starts on the next line, and a block such as a list cannot follow inline text
        lines[at : at + 1] = [f":{field}: {formatted} --", ""]


def description_from_doc(annotation: Hint | None) -> str | None:
    """Return the text of the `typing.Doc` an `Annotated` type carries, `None` for a type without one."""
    if get_origin(annotation) is not Annotated:
        return None
    return next(
        (
            meta.documentation
            for meta in get_args(annotation)[1:]
            if type(meta).__qualname__ == "Doc" and type(meta).__module__ in {"typing_extensions", "typing"}
        ),
        None,
    )


__all__ = [
    "description_from_doc",
    "inject_rtype",
]
