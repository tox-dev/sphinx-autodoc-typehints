"""The forms a rendered type takes in a docstring field and in a signature."""

from __future__ import annotations

__lazy_modules__ = [
    "re",
    "sphinx_autodoc_typehints._render.annotation.markup",
    "sphinx_autodoc_typehints._render.annotation.walker",
]

from re import DOTALL, Match, fullmatch, sub
from typing import TYPE_CHECKING

from sphinx_autodoc_typehints._render.annotation.markup import add_type_css_class
from sphinx_autodoc_typehints._render.annotation.walker import format_annotation

if TYPE_CHECKING:
    from sphinx.config import Config

    from sphinx_autodoc_typehints._refs import WrittenTypeAlias
    from sphinx_autodoc_typehints._types import Hint


def as_field_type(hint: Hint | WrittenTypeAlias, config: Config) -> str:
    """Render `hint` for a docstring field, wrapped in the role giving it the extension's CSS class."""
    return add_type_css_class(format_annotation(hint, config, short_literals=config.python_display_short_literal_types))


def as_signature_type(hint: Hint | WrittenTypeAlias, config: Config) -> str:
    """
    Render `hint` as the plain text a signature holds, such as `~pathlib.Path`, which the Python domain links again.

    A role with an explicit title shows its title there too, as `...` for `Ellipsis`.
    """

    def plain(match: Match[str]) -> str:
        if (role := match["role"]) is not None:
            text = sub(r"\\(.)", r"\1", role)
            return titled[1] if (titled := fullmatch(r"(.*?)\s*<.+>", text, DOTALL)) else text
        if (literal := match["literal"]) is not None:
            return literal
        # an escaped space only separates markup, as between a role and the [ after it
        return "" if match["escaped"] == " " else match["escaped"]

    markup = r":(?:[\w-]+:)+`(?P<role>(?:[^`\\]|\\.)*)`|``(?P<literal>.+?)``|\\(?P<escaped>.)"
    rendered = format_annotation(hint, config, short_literals=config.python_display_short_literal_types)
    return sub(markup, plain, rendered, flags=DOTALL)


__all__ = [
    "as_field_type",
    "as_signature_type",
]
