"""Keeps napoleon from reading a sentence under a NumPy `Returns` header as the return type."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc import Options

    from sphinx_autodoc_typehints._types import Documented


def mark_numpy_returns(
    app: Sphinx,
    what: str,
    _name: str,
    _obj: Documented,
    _options: Options | None,
    lines: list[str],
) -> None:
    """Put a `:` under a NumPy `Returns` header, so napoleon reads no type from the text under it."""
    if what not in {"function", "method"} or not getattr(app.config, "napoleon_numpy_docstring", False):
        return
    # napoleon takes a line repeating any one character of its set as the underline
    under_header = (
        at + 2
        for at, line in enumerate(lines[:-2])
        if line.lower().strip(":") in {"return", "returns"}
        and len(set(underline := lines[at + 1].strip())) == 1
        and underline[0] in "=-~_*+#"
    )
    if (pos := next(under_header, None)) is None:
        return

    end = next((index for index in range(pos, len(lines)) if not lines[index].strip()), len(lines))
    # an unindented sentence reads as a type to napoleon; indented under the empty field it becomes the description.
    # A type line has its description indented under it, so only a paragraph with no indented line is a sentence.
    if (
        (paragraph := lines[pos:end])
        and not any(line[:1].isspace() for line in paragraph)
        and paragraph[-1].rstrip().endswith(".")
    ):
        lines[pos:end] = [f"    {line}" for line in paragraph]
    lines.insert(pos, ":")


__all__ = [
    "mark_numpy_returns",
]
