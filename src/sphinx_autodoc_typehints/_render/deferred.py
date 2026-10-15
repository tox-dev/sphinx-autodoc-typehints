"""
Alias choices wait until every document is read.

A marker role holds each one in the doctree, and a post-transform then puts in the link to the alias or its expanded
value.
"""

from __future__ import annotations

from contextlib import suppress
from hashlib import blake2s
from typing import TYPE_CHECKING, Final, override

from docutils import nodes
from sphinx import addnodes
from sphinx.errors import NoUri
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util import logging
from sphinx.util.docutils import sphinx_domains

from .._state import alias_choices, recorded_alias_choices
from .context import render_context
from .rst import parse, unescape

if TYPE_CHECKING:
    from docutils.nodes import Node
    from docutils.parsers.rst import states
    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment


ALIAS_CHOICE_ROLE: Final[str] = "sphinx_autodoc_typehints_alias"
_ALIAS_CHOICE_KEY: Final[str] = "sphinx_autodoc_typehints_alias_key"
_DEFAULT_DOMAIN_KEY: Final[str] = "sphinx_autodoc_typehints_default_domain"


def alias_choice_role(
    _role: str,
    _rawtext: str,
    text: str,
    lineno: int,
    inliner: states.Inliner,
    _options: dict[str, object] | None = None,
    _content: list[str] | None = None,
) -> tuple[list[Node], list[Node]]:
    # `replace_self` would copy any classes onto whichever rendering wins
    node = nodes.inline("", "")
    node[_ALIAS_CHOICE_KEY] = unescape(text)
    # the docstring the marker came from, which the field list transform no longer keeps on the nodes around it
    node.source, node.line = inliner.reporter.get_source_and_line(lineno)
    # the renderings hold roles written for this spot, such as a formatter's :class:, which the write phase parses
    # outside any document, so it needs the domain they would have resolved in here
    if (domain := inliner.document.settings.env.current_document.default_domain) is not None:
        node[_DEFAULT_DOMAIN_KEY] = domain.name
    return [node], []


def defer_alias_choice(config: Config, linked: str, expanded: str, *, objtype: str | None = None) -> str | None:
    """
    Emit a marker the resolve phase replaces with `linked` or `expanded`, or `None` if it cannot.

    With `objtype`, `linked` wins only where the py domain documents its target as that kind of object.

    The py domain learns a target only once Sphinx reads its document, so while Sphinx still reads documents it cannot
    tell whether an alias has one. Deciding here would tie the rendering of a signature to where its document sorts
    (and to how `-j` hands documents out), so both renderings go to the post-transform, which runs once every
    document is in.
    """
    # signature text is final once written, and names an alias the way Python writes it
    if (context := render_context(config)).signature:
        return linked
    if (env := context.env) is None or linked == expanded:
        return None
    choice = (linked, expanded) if objtype is None else (linked, expanded, objtype)
    # content-addressed, so a doctree read in an earlier build still finds its choice
    key = blake2s("\n".join(choice).encode(), digest_size=8).hexdigest()
    alias_choices(env)[key] = choice
    return f":{ALIAS_CHOICE_ROLE}:`{key}`"


def merge_alias_choices(_app: Sphinx, env: BuildEnvironment, _docnames: list[str], other: BuildEnvironment) -> None:
    if worker_choices := recorded_alias_choices(other):
        alias_choices(env).update(worker_choices)


class DeferAliasChoice(SphinxPostTransform):
    """
    Replace every alias marker once the domain and the inventories can answer for every document.

    It runs ahead of `ReferencesResolver` (priority 10), which still resolves the references this leaves behind.
    """

    default_priority = 5

    @override
    def run(self, **kwargs: object) -> None:
        choices = recorded_alias_choices(self.env)
        pending = self._markers(self.document)
        while pending:
            node = pending.pop()
            if (choice := choices.get(node[_ALIAS_CHOICE_KEY])) is None:
                # a doctree an older version wrote holds markers with no recorded choice
                node.replace_self([])
                continue
            linked, expanded, *objtypes = choice
            doc = self._parse(node, linked)
            # the target is the first reference, and the type arguments after it resolve, or not, like any other
            target = next(doc.findall(addnodes.pending_xref))
            # a role resolves to whatever object has the name, as :py:type: does to a class
            documented = self.env.domains.python_domain.objects.get(target["reftarget"])
            resolved: Node | None = None
            if not objtypes or getattr(documented, "objtype", None) in objtypes:
                contnode = target.children[0].deepcopy() if target.children else nodes.literal(text=target["reftarget"])
                with suppress(NoUri):
                    resolved = self.env.domains[target["refdomain"]].resolve_xref(
                        self.env,
                        target["refdoc"],
                        self.app.builder,
                        target["reftype"],
                        target["reftarget"],
                        target,
                        contnode,
                    )
                    if resolved is None:  # give `missing-reference` handlers (e.g. qualname overrides) their say
                        resolved = self.app.emit_firstresult(
                            "missing-reference", self.env, target, contnode, allowed_exceptions=(NoUri,)
                        )
            if resolved is not None:
                target.replace_self(resolved)
                replacement = doc.children[0].children
            else:
                replacement = self._parse(node, expanded).children[0].children
                # an expanded value can name further aliases, each with its own choice pending
                pending.extend(marker for child in replacement for marker in self._markers(child))
            node.replace_self(list(replacement))

    @staticmethod
    def _markers(node: Node) -> list[nodes.Element]:
        return [n for n in node.findall(nodes.inline) if _ALIAS_CHOICE_KEY in n]

    def _parse(self, marker: nodes.Element, rst: str) -> nodes.document:
        current = self.env.current_document
        default_domain = current.default_domain
        current.default_domain = self.env.domains.get(marker.get(_DEFAULT_DOMAIN_KEY, ""))
        try:
            with sphinx_domains(self.env):
                doc = parse(rst, self.env)
        finally:
            current.default_domain = default_domain
        for message in doc.findall(nodes.system_message):
            if message["level"] >= doc.settings.report_level:
                logging.getLogger(__name__).log(
                    message["type"], message.children[0].astext(), location=marker, type="docutils"
                )
        for nested in self._markers(doc):
            nested.source, nested.line = marker.source, marker.line
        for xref in doc.findall(addnodes.pending_xref):
            xref.setdefault("refdoc", self.env.docname)
        return doc


__all__ = [
    "ALIAS_CHOICE_ROLE",
    "DeferAliasChoice",
    "alias_choice_role",
    "defer_alias_choice",
    "merge_alias_choices",
]
