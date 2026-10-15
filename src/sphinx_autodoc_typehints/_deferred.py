"""Picking between a reference to a type alias and its expanded value, once every document is read."""

from __future__ import annotations

from hashlib import blake2s
from typing import TYPE_CHECKING, Any, Final

from docutils import nodes
from docutils.frontend import get_default_settings
from sphinx import addnodes
from sphinx.errors import NoUri
from sphinx.parsers import RSTParser
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util import logging
from sphinx.util.docutils import sphinx_domains

from ._parser import parse, unescape

if TYPE_CHECKING:
    from docutils.nodes import Node
    from docutils.parsers.rst import states
    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment


#: Role marking a spot where the resolve phase picks between a reference and an expanded alias value.
ALIAS_CHOICE_ROLE: Final = "sphinx_autodoc_typehints_alias"
#: Node attribute and build environment attribute the two renderings are looked up through.
ALIAS_CHOICE_KEY: Final = "sphinx_autodoc_typehints_alias_key"
ALIAS_CHOICE_ENV_ATTR: Final = "_typehints_alias_choices"
_DEFAULT_DOMAIN_KEY: Final = "sphinx_autodoc_typehints_default_domain"

_LOGGER = logging.getLogger(__name__)


def alias_choice_role(
    _role: str,
    _rawtext: str,
    text: str,
    lineno: int,
    inliner: states.Inliner,
    _options: dict[str, Any] | None = None,
    _content: list[str] | None = None,
) -> tuple[list[Node], list[Node]]:
    """Mark a spot :class:`DeferAliasChoice` fills in, naming the choice made for it while reading."""
    # No classes: `replace_self` would copy them onto whichever rendering wins
    node = nodes.inline("", "")
    node[ALIAS_CHOICE_KEY] = unescape(text)
    # the docstring the marker came from, which the field list transform no longer keeps on the nodes around it
    node.source, node.line = inliner.reporter.get_source_and_line(lineno)
    # the renderings hold roles written for this spot, such as a formatter's :class:, which the write phase parses
    # outside any document, so it needs the domain they would have resolved in here
    if (domain := inliner.document.settings.env.current_document.default_domain) is not None:
        node[_DEFAULT_DOMAIN_KEY] = domain.name
    return [node], []


def defer_alias_choice(config: Config, linked: str, expanded: str, *, objtype: str | None = None) -> str | None:
    """
    Emit a marker the resolve phase replaces with ``linked`` or ``expanded``, or ``None`` if it cannot.

    With ``objtype``, ``linked`` wins only where its target is documented as that kind of object.

    Whether an alias is documented has no answer while documents are still being read: the py domain
    only learns a target once its own document is read, so deciding here would tie the rendering of a
    signature to where its document sorts (and to how ``-j`` hands documents out). Hand both renderings
    to the post-transform instead, which runs once every document is in.
    """
    # signature text is final once written, and names an alias the way Python writes it
    if getattr(config, "_typehints_signature", False):
        return linked
    env = getattr(config, "_typehints_env", None)
    if env is None or linked == expanded:
        return None
    choices = getattr(env, ALIAS_CHOICE_ENV_ATTR, None)
    if not isinstance(choices, dict):
        choices = {}
        setattr(env, ALIAS_CHOICE_ENV_ATTR, choices)
    choice = (linked, expanded) if objtype is None else (linked, expanded, objtype)
    # Content-addressed, so a doctree read in an earlier build still finds its choice
    key = blake2s("\n".join(choice).encode(), digest_size=8).hexdigest()
    choices[key] = choice
    return f":{ALIAS_CHOICE_ROLE}:`{key}`"


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
            linked, expanded, *objtype = choice
            replacement = self._reference(node, linked, objtype)
            if replacement is None:
                replacement = self._parse(node, expanded).children[0].children
                # An expanded value can name further aliases, whose choices are still to be made
                pending.extend(marker for child in replacement for marker in self._markers(child))
            node.replace_self(list(replacement))

    @staticmethod
    def _markers(node: Node) -> list[nodes.Element]:
        return [n for n in node.findall(nodes.inline) if ALIAS_CHOICE_KEY in n]

    def _parse(self, marker: nodes.Element, rst: str) -> nodes.document:
        # the document being written carries its writer's settings, which lack the rST parser's (man has no tab_width)
        settings = get_default_settings(RSTParser())
        settings.env = self.env
        # reported through Sphinx below, against the spot in the document rather than this detached snippet
        settings.warning_stream = False
        current = self.env.current_document
        default_domain = current.default_domain
        current.default_domain = self.env.domains.get(marker.get(_DEFAULT_DOMAIN_KEY, ""))
        try:
            with sphinx_domains(self.env):
                doc = parse(rst, settings)
        finally:
            current.default_domain = default_domain
        for message in doc.findall(nodes.system_message):
            if message["level"] >= settings.report_level:
                _LOGGER.log(message["type"], message.children[0].astext(), location=marker, type="docutils")
        for nested in self._markers(doc):
            nested.source, nested.line = marker.source, marker.line
        for xref in doc.findall(addnodes.pending_xref):
            xref.setdefault("refdoc", self.env.docname)
        return doc

    def _reference(self, marker: nodes.Element, linked: str, objtypes: list[str]) -> list[Node] | None:
        """
        Render the reference ``linked`` describes, or ``None`` if nothing documents its target (as one of ``objtypes``).

        The target is the first reference: the type arguments after it resolve, or not, like any other reference.
        """
        doc = self._parse(marker, linked)
        target = next(doc.findall(addnodes.pending_xref))
        # a role resolves to whatever object has the name, as :py:type: does to a class
        documented = self.env.get_domain("py").objects.get(target["reftarget"])  # ty: ignore[unresolved-attribute]
        if objtypes and getattr(documented, "objtype", None) not in objtypes:
            return None
        if (resolved := self._resolve(target)) is None:
            return None
        target.replace_self(resolved)
        return list(doc.children[0].children)

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
    "defer_alias_choice",
    "merge_alias_choices",
]
