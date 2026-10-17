# ruff:file-ignore[implicit-namespace-package, import-private-name]  # a docs extension on sys.path, using internals
"""The `confval` directive for this extension's options: the type its annotation renders to, and the rebuild value."""

from __future__ import annotations

from collections.abc import Callable
from functools import reduce
from inspect import isclass
from operator import getitem, or_
from types import UnionType
from typing import TYPE_CHECKING, ClassVar, Final, ForwardRef, Literal, Protocol, Union, get_args, get_origin

from docutils.nodes import field, field_body, field_list, field_name, paragraph
from docutils.parsers.rst import directives
from sphinx.domains.std import ConfigurationValue

from sphinx_autodoc_typehints._render import format_annotation
from sphinx_autodoc_typehints._render.context import ContextualTypehintsFormatter, FixupModuleName, TypehintsFormatter
from sphinx_autodoc_typehints._resolve import resolve_annotations
from sphinx_autodoc_typehints._types import RenderNode

if TYPE_CHECKING:
    from docutils.nodes import system_message
    from sphinx.addnodes import desc_content
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata, OptionSpec


# the extension registers these options by their default, which tells a bool apart but not the values a string or a
# callable takes; the callables are the protocols the extension calls them through
OPTION_TYPES: Final[dict[str, RenderNode]] = {
    "always_document_param_types": bool,
    "always_use_bars_union": bool,
    "simplify_optional_unions": bool,
    "typehints_defaults": Literal["comma", "braces", "braces-after", "optional", False] | None,
    "typehints_annotated_metadata": tuple[type, ...],
    "typehints_annotated_description": Callable[[object], str | None] | None,
    "typehints_document_overloads": bool,
    "typehints_document_rtype": bool,
    "typehints_document_rtype_none": bool,
    "typehints_fixup_module_name": FixupModuleName | None,
    "typehints_formatter": TypehintsFormatter | ContextualTypehintsFormatter | None,
    "typehints_formatter_pass_context": bool,
    "typehints_fully_qualified": bool,
    "typehints_modernize_annotations": bool,
    "typehints_use_rtype": bool,
    "typehints_use_signature": bool,
    "typehints_use_signature_return": bool,
}


def documented_type(name: str) -> RenderNode:
    """Return the type the reference shows for option `name`, each protocol replaced by the signature it calls."""
    if get_origin(annotation := OPTION_TYPES[name]) in {Union, UnionType}:
        return reduce(or_, map(_as_callable, get_args(annotation)))
    return annotation


def _as_callable(member: RenderNode) -> RenderNode:
    # a protocol renders as its name, while a reader setting the option needs the parameters it gets called with
    if not (isclass(member) and issubclass(member, Protocol)):
        return member
    call = member.__call__
    hints = resolve_annotations([], call, f"{call.__module__}.{call.__qualname__}", {})
    returns = hints.pop("return")
    # the alias lives in a private module, so the reference names the parameter plainly and describes it in prose
    hints = {name: ForwardRef("annotation") if hint is RenderNode else hint for name, hint in hints.items()}
    # written as a subscript, the parameters would have to be a type expression rather than the values read here
    return getitem(Callable, (list(hints.values()), returns))  # ty: ignore[no-matching-overload]  # a special form


class OptionReference(ConfigurationValue):
    """Show an option's type as this extension renders its annotation, and what a change to the option rebuilds."""

    option_spec: ClassVar[OptionSpec] = {**ConfigurationValue.option_spec, "rebuild": directives.unchanged_required}

    def transform_content(self, content_node: desc_content) -> None:
        """Fill the type in from `OPTION_TYPES`, then add the rebuild field after the type and the default."""
        self.options["type"] = format_annotation(documented_type(self.names[0]), self.config)
        super().transform_content(content_node)
        if rebuild := self.options.get("rebuild"):
            parsed, messages = self.parse_inline(rebuild, lineno=self.lineno)
            fields = next(content_node.findall(field_list))
            fields += [field("", field_name("", "Rebuild"), field_body("", paragraph("", "", *parsed))), *messages]

    def format_type(self, type_: str) -> tuple[field, list[system_message]]:
        """Wrap the type in a paragraph, as the HTML writer accepts a link only inside one."""
        parsed, messages = self.parse_inline(type_, lineno=self.lineno)
        return field("", field_name("", "Type"), field_body("", paragraph("", "", *parsed))), messages


def setup(app: Sphinx) -> ExtensionMetadata:
    """Replace the `confval` directive with one that renders the type and shows the rebuild value."""
    app.add_directive_to_domain("std", "confval", OptionReference, override=True)
    return {"parallel_read_safe": True, "parallel_write_safe": True}


__all__ = [
    "OPTION_TYPES",
    "OptionReference",
    "documented_type",
]
