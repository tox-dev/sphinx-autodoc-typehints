"""The forms a rendered type takes in a docstring field and in a signature."""

from __future__ import annotations

from re import DOTALL, Match, fullmatch, sub
from typing import TYPE_CHECKING

from ..context import annotation_state
from .markup import add_type_css_class
from .walker import format_annotation

if TYPE_CHECKING:
    from sphinx.config import Config

    from sphinx_autodoc_typehints._refs import WrittenTypeAlias
    from sphinx_autodoc_typehints._types import Hint

    from ..context import AnnotationKind


def as_field_type(hint: Hint | WrittenTypeAlias, config: Config, *, kind: AnnotationKind = "other") -> str:
    """Render `hint` for a docstring field, wrapped in the role giving it the extension's CSS class."""
    return add_type_css_class(_render(hint, config, kind))


def as_signature_type(hint: Hint | WrittenTypeAlias, config: Config, *, kind: AnnotationKind = "other") -> str:
    """
    Render `hint` as the plain text a signature holds, such as `~pathlib.Path`, which the Python domain links again.

    A role with an explicit title shows its title there too, as `...` for `Ellipsis`.
    """
    return as_header_type(hint, config, kind=kind)[0]


def as_header_type(
    hint: Hint | WrittenTypeAlias, config: Config, *, kind: AnnotationKind = "other"
) -> tuple[str, dict[str, str]]:
    """Render `hint` as `as_signature_type` does, along with the Python role of each name it links, keyed by target."""
    roles: dict[str, str] = {}

    def plain(match: Match[str]) -> str:
        if (role := match["role"]) is not None:
            text = sub(r"\\(.)", r"\1", role)
            titled = fullmatch(r"(.*?)\s*<(.+)>", text, DOTALL)
            if (name := match["name"]).startswith("py:"):
                roles[(titled[2] if titled else text).lstrip("~.")] = name.removeprefix("py:").removesuffix(":")
            return titled[1] if titled else text
        if (literal := match["literal"]) is not None:
            return literal
        # an escaped space only separates markup, as between a role and the [ after it
        return "" if match["escaped"] == " " else match["escaped"]

    markup = r":(?P<name>(?:[\w-]+:)+)`(?P<role>(?:[^`\\]|\\.)*)`|``(?P<literal>.+?)``|\\(?P<escaped>.)"
    rendered = _render(hint, config, kind)
    return sub(markup, plain, rendered, flags=DOTALL), roles


def _render(hint: Hint | WrittenTypeAlias, config: Config, kind: AnnotationKind) -> str:
    if not config.typehints_formatter_pass_context or config.typehints_formatter is None:
        return format_annotation(hint, config, short_literals=config.python_display_short_literal_types)
    with annotation_state(config, kind=kind):
        return format_annotation(hint, config, short_literals=config.python_display_short_literal_types)


__all__ = [
    "as_field_type",
    "as_header_type",
    "as_signature_type",
]
