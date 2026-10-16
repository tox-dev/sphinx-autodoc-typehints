"""Types and extends the combined field napoleon writes when one field lists every parameter."""

from __future__ import annotations

import re  # a from-import of compile would shadow the builtin
from itertools import accumulate
from typing import TYPE_CHECKING, Literal

from sphinx_autodoc_typehints._private_imports import translate
from sphinx_autodoc_typehints._render import as_field_type

from ..base import format_default, last_paragraph_end, line_indent

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sphinx.application import Sphinx

    from sphinx_autodoc_typehints._refs import WrittenTypeAlias
    from sphinx_autodoc_typehints._types import Hint


def type_combined_field_entry(
    app: Sphinx, lines: list[str], arg_name: str, annotation: Hint | WrittenTypeAlias | None, default: object
) -> bool:
    """
    Type the `**name** -- text` entry of a combined field, where one field lists every parameter.

    Napoleon writes these with `napoleon_use_param` or `napoleon_use_keyword` off, and puts a docstring type in
    parentheses right after the name, which a type from the annotation follows too. Return whether the entry has a type
    now, `False` when the docstring lists no such entry.
    """
    names = "|".join(re.escape(f"{prefix}{arg_name}") for prefix in ("", "\\*", "\\*\\*"))
    entry = re.compile(rf"^(?::[^:]+: +|\s+)(?:\* )?\*\*(?:{names})\*\*(?P<typed> \()?")
    found = next(
        ((at, match) for at in _combined_field_entries(lines) if (match := entry.match(lines[at]))),
        None,
    )
    if found is None:
        return False
    at, match = found
    if match["typed"]:
        depths = accumulate((({"(": 1, ")": -1}.get(char, 0) for char in lines[at][match.end() :])), initial=1)
        type_end = next((match.end() + offset for offset, depth in enumerate(depths) if not depth), None)
    elif annotation is None:
        return False
    elif not (field_type := as_field_type(annotation, app.config)):
        # a type a formatter hides leaves the entry as written, with no parentheses for a default to join
        return True
    else:
        typed = f" ({field_type})"
        lines[at] = f"{lines[at][: match.end()]}{typed}{lines[at][match.end() :]}"
        type_end = match.end() + len(typed)
    if (
        type_end is None
        or not app.config.typehints_defaults
        or not (formatted_default := format_default(app, default, annotated=True))
    ):
        return True
    if app.config.typehints_defaults == "comma":
        lines[at] = f"{lines[at][: type_end - 1]}{formatted_default}{lines[at][type_end - 1 :]}"
    elif app.config.typehints_defaults == "braces":
        lines[at] = f"{lines[at][:type_end]}{formatted_default}{lines[at][type_end:]}"
    else:
        entry_end = next(
            (
                after
                for after in range(at + 1, len(lines))
                if lines[after].strip() and (not lines[after][:1].isspace() or lines[after].lstrip().startswith("* **"))
            ),
            len(lines),
        )
        lines[last_paragraph_end(lines[:entry_end], at)] += formatted_default
    return True


# the same `**name** -- text` markup in a code example, an overload or a returned value's name is no parameter entry
def _combined_field_entries(lines: list[str]) -> Iterator[int]:
    headings = tuple(f":{translate(label)}:" for label in ("Parameters", "Keyword Arguments", "Other Parameters"))
    in_field, bullet_indent = False, None
    for at, line in enumerate(lines):
        if line.startswith(headings):
            in_field, bullet_indent = True, None
            yield at
        elif in_field and line[:1].isspace():
            indent = line_indent(line)
            if line.lstrip().startswith("* ") and (bullet_indent is None or indent == bullet_indent):
                bullet_indent = indent
                yield at
        elif line:
            in_field = False


def add_combined_field_entry(
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
    if (at := next((at for at in range(start, end) if later_names and later.match(lines[at])), end)) == start:
        # the first entry shares its line with the heading, which the new entry takes over
        lines[start] = f"{indent}{lines[start][len(heading) :]}"
        lines.insert(start, f"{heading}* {entry}")
    else:
        lines.insert(at, f"{indent}* {entry}")
    return True


__all__ = [
    "add_combined_field_entry",
    "type_combined_field_entry",
]
