"""Picking between a reference to a type alias and its expanded value, once every document is read."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes
from sphinx import addnodes
from sphinx.errors import NoUri
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util.docutils import sphinx_domains

from ._annotations import ALIAS_CHOICE_ENV_ATTR, ALIAS_CHOICE_KEY, unescape
from ._parser import parse

if TYPE_CHECKING:
    from docutils.nodes import Node
    from docutils.parsers.rst import states
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment


def alias_choice_role(
    _role: str,
    _rawtext: str,
    text: str,
    _lineno: int,
    _inliner: states.Inliner,
    _options: dict[str, Any] | None = None,
    _content: list[str] | None = None,
) -> tuple[list[Node], list[Node]]:
    """Mark a spot :class:`DeferAliasChoice` fills in, naming the choice made for it while reading."""
    # No classes: `replace_self` would copy them onto whichever rendering wins
    node = nodes.inline("", "")
    node[ALIAS_CHOICE_KEY] = unescape(text)
    return [node], []


def merge_alias_choices(app: Sphinx, env: BuildEnvironment, docnames: list[str], other: BuildEnvironment) -> None:
    """Carry the choices a parallel read recorded in a worker over into the main environment."""
    del app, docnames
    if not (worker_choices := getattr(other, ALIAS_CHOICE_ENV_ATTR, None)):
        return
    choices = getattr(env, ALIAS_CHOICE_ENV_ATTR, None)
    if not isinstance(choices, dict):
        choices = {}
        setattr(env, ALIAS_CHOICE_ENV_ATTR, choices)
    choices.update(worker_choices)


class DeferAliasChoice(SphinxPostTransform):
    """
    Replace every alias marker with a reference to the alias, or with its expanded value.

    Runs ahead of ``ReferencesResolver`` (priority 10), so the domain and the inventories can answer
    for every document, and the references this leaves behind are still resolved normally.
    """

    default_priority = 5

    def run(self, **kwargs: Any) -> None:
        del kwargs
        choices = getattr(self.env, ALIAS_CHOICE_ENV_ATTR, None) or {}
        pending = self._markers(self.document)
        while pending:
            node = pending.pop()
            if (choice := choices.get(node[ALIAS_CHOICE_KEY])) is None:
                node.replace_self([])  # nothing recorded this choice, e.g. a doctree from an older version
                continue
            linked, expanded = choice
            replacement = self._reference(linked)
            if replacement is None:
                replacement = self._parse(expanded).children[0].children
                # An expanded value can name further aliases, whose choices are still to be made
                pending.extend(marker for child in replacement for marker in self._markers(child))
            node.replace_self(list(replacement))

    @staticmethod
    def _markers(node: Node) -> list[nodes.Element]:
        return [n for n in node.findall(nodes.inline) if ALIAS_CHOICE_KEY in n]

    def _parse(self, rst: str) -> nodes.document:
        with sphinx_domains(self.env):
            doc = parse(rst, self.document.settings)
        for xref in doc.findall(addnodes.pending_xref):
            xref.setdefault("refdoc", self.env.docname)
        return doc

    def _reference(self, linked: str) -> list[Node] | None:
        """Render the reference ``linked`` describes, or ``None`` if nothing documents its target."""
        doc = self._parse(linked)
        for xref in list(doc.findall(addnodes.pending_xref)):
            if (resolved := self._resolve(xref)) is None:
                return None
            xref.replace_self(resolved)
        return list(doc.children[0].children) if doc.children else []

    def _resolve(self, xref: addnodes.pending_xref) -> Node | None:
        contnode = xref.children[0].deepcopy() if xref.children else nodes.literal(text=xref["reftarget"])
        try:
            domain = self.env.domains[xref["refdomain"]]
            node = domain.resolve_xref(
                self.env, xref["refdoc"], self.app.builder, xref["reftype"], xref["reftarget"], xref, contnode
            )
            if node is None:  # give `missing-reference` handlers (e.g. qualname overrides) their say
                node = self.app.emit_firstresult(
                    "missing-reference", self.env, xref, contnode, allowed_exceptions=(NoUri,)
                )
        except NoUri:
            return None
        return node


__all__ = [
    "DeferAliasChoice",
    "alias_choice_role",
    "merge_alias_choices",
]
