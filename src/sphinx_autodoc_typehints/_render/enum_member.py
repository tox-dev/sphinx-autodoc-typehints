"""
Enum members inside a `Literal` link to the member, or to its enum when the member has no entry.

autodoc gives a member without a docstring no entry unless `:undoc-members:` asks for one, while the enum itself is
documented, so a marker role flags the member reference and a `missing-reference` handler points it at the enum.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from sphinx import addnodes
from sphinx.domains.python import PyXRefRole

if TYPE_CHECKING:
    from docutils.nodes import Element, Node, TextElement, system_message
    from docutils.parsers.rst import states
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment

ENUM_MEMBER_ROLE: Final[str] = "sphinx_autodoc_typehints_enum_member"
_ENUM_MEMBER_KEY: Final[str] = "sphinx_autodoc_typehints_enum_member"
_ATTR_ROLE: Final[PyXRefRole] = PyXRefRole()


def enum_member_role(
    _role: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: states.Inliner,
    options: dict[str, object] | None = None,
    content: list[str] | None = None,
) -> tuple[list[Node], list[system_message]]:
    refs, messages = _ATTR_ROLE("py:attr", rawtext, text, lineno, inliner, options or {}, content or [])
    next(ref for ref in refs if isinstance(ref, addnodes.pending_xref))[_ENUM_MEMBER_KEY] = True
    return refs, messages


def link_enum_member_owner(
    app: Sphinx, env: BuildEnvironment, node: addnodes.pending_xref, contnode: TextElement
) -> Element | None:
    if not node.get(_ENUM_MEMBER_KEY):
        return None
    owner = node["reftarget"].rpartition(".")[0]
    return env.domains.python_domain.resolve_xref(env, node["refdoc"], app.builder, "class", owner, node, contnode)


__all__ = [
    "ENUM_MEMBER_ROLE",
    "enum_member_role",
    "link_enum_member_owner",
]
