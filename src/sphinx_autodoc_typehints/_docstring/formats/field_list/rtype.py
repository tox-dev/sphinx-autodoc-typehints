"""Places the `:rtype:` field a docstring has no text position for, in the field list of the docstring's nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from docutils import nodes

from .keywords import PARAM_SYNONYMS

if TYPE_CHECKING:
    from sphinx.application import Sphinx

RTYPE_MARKER: Final[str] = "sphinx_autodoc_typehints_rtype"


def place_rtype(_app: Sphinx, _domain: str, _objtype: str, contentnode: nodes.Element) -> None:
    """
    Name the marked field `rtype` and put it where Sphinx puts the types it adds with `autodoc_typehints="description"`.

    That is the end of the first list with parameters, else of the last field list, else of a new list at the end of the
    content.
    """
    marked = (node for node in contentnode.findall(nodes.field) if node[0].astext() == RTYPE_MARKER)
    if (field := next(marked, None)) is None:
        return
    field[0].children = [nodes.Text("rtype")]
    holder = field.parent
    lists = [node for node in contentnode.children if isinstance(node, nodes.field_list)]
    # the marker opens a list of its own where the docstring does not end in one, which an earlier list takes over, and
    # inside a section nothing groups its fields
    candidates = lists[: lists.index(holder) + 1] if holder in lists else lists
    others = [node for node in candidates if node is not holder]
    if (target := next((node for node in candidates if _has_params(node)), None)) is None:
        if holder in candidates and (holder.index(field) != 0 or not others):
            return
        if others:
            target = others[-1]
        else:
            contentnode.append(target := nodes.field_list())
    if target is not holder:
        holder.remove(field)
        target.append(field)
        if not holder.children:
            holder.parent.remove(holder)


def _has_params(node: nodes.field_list) -> bool:
    return any(field[0].astext().startswith(PARAM_SYNONYMS) for field in node)


__all__ = [
    "RTYPE_MARKER",
    "place_rtype",
]
