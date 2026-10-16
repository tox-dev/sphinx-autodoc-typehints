"""Finds and adds parameter fields in a reST field list and writes the return type into it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from ..base import InsertIndexInfo
from ..napoleon import reads_as_type
from ..numpydoc import convert_to_field_list
from .keywords import PARAM_SYNONYMS, STAR_PREFIXES, field_keyword_and_argument
from .rtype import RTYPE_MARKER

if TYPE_CHECKING:
    from sphinx.application import Sphinx


@dataclass(slots=True)
class FieldListFormat:
    """
    Read and extend the field list of a docstring.

    `numpydoc_pending` marks a docstring holding numpydoc's sections, which become a field list on the first read.
    """

    numpydoc_pending: bool = False

    def find_param(self, lines: list[str], arg_name: str) -> int | None:
        self._convert(lines)
        for at, line in enumerate(lines):
            if (field := field_keyword_and_argument(line)) is None or (doc_name := field[1]) is None:
                continue
            # a `:param type name:` field writes its type before the name
            if f"{field[0]} " in PARAM_SYNONYMS and any(
                doc_name == f"{prefix}{arg_name}" or doc_name.endswith(f" {prefix}{arg_name}")
                for prefix in STAR_PREFIXES
            ):
                return at
        return None

    def _convert(self, lines: list[str]) -> None:
        if self.numpydoc_pending:
            convert_to_field_list(lines)
            self.numpydoc_pending = False

    def add_undocumented_param(
        self,
        lines: list[str],
        arg_name: str,
        description: str = "",
        *,
        before: int | None = None,
        field: Literal["param", "keyword"] = "param",
    ) -> int:
        """Add a field, `:param:` unless told otherwise, for an undocumented parameter, return its index."""
        self._convert(lines)
        # beside the documented parameters, not after whatever the docstring ends with, such as its examples
        if before is not None:
            at = before
        elif (
            last := max(
                (
                    at
                    for at, line in enumerate(lines)
                    if (parsed := field_keyword_and_argument(line))
                    and (parsed[0] == "type" or f"{parsed[0]} " in PARAM_SYNONYMS)
                ),
                default=None,
            )
        ) is not None:
            at = _field_end(lines, last)
        else:
            # the first field after text, which a blank line has to separate a field list from
            if lines and lines[-1].strip():
                lines.append("")
            at = len(lines)
        lines.insert(at, f":{field} {arg_name}: {description}".rstrip())
        return at

    def has_return_description(self, lines: list[str]) -> bool:
        self._convert(lines)
        return any(line.startswith((":return:", ":returns:")) for line in lines)

    def get_rtype_insert_info(self, app: Sphinx, lines: list[str]) -> InsertIndexInfo:
        self._convert(lines)
        # the annotation replaces the docstring's :rtype: field
        if (rtype_at := next((at for at, line in enumerate(lines) if line.startswith(":rtype:")), None)) is not None:
            del lines[rtype_at : _field_end(lines, rtype_at)]
        return_at = next((i for i, line in enumerate(lines) if line.startswith((":return:", ":returns:"))), None)
        # inline mode merges the type into the return entry, so it replaces a preexisting rtype field only without one
        if rtype_at is not None and (app.config.typehints_use_rtype or return_at is None):
            return InsertIndexInfo(insert_index=rtype_at)
        if return_at is not None:
            return InsertIndexInfo(insert_index=return_at, found_return=True, found_rtype=rtype_at is not None)

        return InsertIndexInfo(insert_index=len(lines), deferred=True)


def write_rtype(
    lines: list[str],
    formatted_annotation: str,
    info: InsertIndexInfo,
    *,
    use_rtype: bool,
) -> None:
    """Write the return type at `info`, as an `:rtype:` field or, without `use_rtype`, in the return field."""
    if info.deferred:
        # the field goes where the docstring's nodes put it, once Sphinx parsed them
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f":{RTYPE_MARKER}: {formatted_annotation}")
        return
    insert_index = info.insert_index
    # the return field's line stays the one at insert_index as blank lines go in above it
    description = lines[insert_index].split(":", 2)[2].strip() if info.found_return else ""
    # a returns text stating its type, as napoleon writes `:returns: X -- text` with no rtype field, keeps it;
    # beside an rtype field it describes the value instead, and text not reading as a type, such as a description
    # that itself contains ` -- `, keeps getting the type
    if (
        not use_rtype
        and info.found_return
        and not info.found_rtype
        and " -- " in description
        and reads_as_type(description)
    ):
        return

    if 0 < insert_index <= len(lines) and lines[insert_index - 1].strip():
        lines.insert(insert_index, "")
        insert_index += 1

    if use_rtype or not info.found_return:
        lines.insert(insert_index, f":rtype: {formatted_annotation}")
    elif description:
        lines[insert_index] = f":return: {formatted_annotation} -- {description}"
    else:
        # the description starts on the next line, and a block such as a list cannot follow inline text
        lines[insert_index : insert_index + 1] = [f":return: {formatted_annotation} --", ""]


def _field_end(lines: list[str], at: int) -> int:
    end = at + 1
    while end < len(lines) and lines[end][:1].isspace() and lines[end].strip():
        end += 1
    return end


__all__ = [
    "FieldListFormat",
    "write_rtype",
]
