"""Shows an object's `@deprecated` message."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from docutils import nodes
from sphinx import addnodes
from sphinx.locale import _  # ruff:ignore[import-private-name]  # Sphinx documents it as public
from sphinx.util.docutils import SphinxDirective

if TYPE_CHECKING:
    from collections.abc import Callable

    from docutils.nodes import Node


DEPRECATED_DIRECTIVE: Final[str] = "sphinx_autodoc_typehints_deprecated"


def inject_deprecation(obj: Callable[..., object], lines: list[str], summary_end: int) -> None:
    """Add the `@deprecated` message of `obj` below the summary, unless the docstring notes the deprecation."""
    # the object's own, as a subclass of a deprecated class inherits the attribute that @deprecated set on the base
    if not isinstance(message := getattr(obj, "__dict__", {}).get("__deprecated__"), str) or any(
        line.lstrip().startswith(".. deprecated::") for line in lines
    ):
        return
    at = next((at for at, line in enumerate(lines[:summary_end]) if line.startswith(":")), summary_end)
    lines[at:at] = ["", f".. {DEPRECATED_DIRECTIVE}::", "", *(f"   {line}" for line in message.splitlines()), ""]


class DeprecatedDirective(SphinxDirective):
    """
    Render a deprecation notice the way `.. deprecated::` does, without the version that directive requires.

    The message is what the object warns with at runtime, so it shows as written rather than as markup.
    """

    has_content = True

    def run(self) -> list[Node]:
        label = nodes.inline("", _("Deprecated") + ": ", classes=["versionmodified", "deprecated"])
        node = addnodes.versionmodified(type="deprecated")
        node += nodes.paragraph("", "", label, nodes.Text("\n".join(self.content)), translatable=False)
        self.set_source_info(node)
        return [node]


__all__ = [
    "DEPRECATED_DIRECTIVE",
    "DeprecatedDirective",
    "inject_deprecation",
]
