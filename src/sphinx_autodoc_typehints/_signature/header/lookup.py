"""Finds the signatures of the objects autodoc documents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx import addnodes

from sphinx_autodoc_typehints._state import is_documented

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sphinx.environment import BuildEnvironment


def documented_signatures(
    env: BuildEnvironment, contentnode: addnodes.desc_content
) -> Iterator[tuple[addnodes.desc_signature, str, str]]:
    """Yield each signature beside `contentnode` that autodoc documents, with its module and its name there."""
    # the signatures are the siblings of the content, which may nest the signatures of members
    for signode in contentnode.parent or ():
        if isinstance(signode, addnodes.desc_signature) and is_documented(
            env, f"{(module := signode.get('module'))}.{(fullname := signode.get('fullname'))}"
        ):
            yield signode, module, fullname


__all__ = [
    "documented_signatures",
]
