"""
The top layer: `setup` wires the extension into Sphinx.

It registers the options, roles, directive, post-transform and event handlers, and installs the monkeypatches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes

from ._config import OPTIONS, cache_fixup_module_name, store_type_mapping, validate_config
from ._docstring import (
    DEPRECATED_DIRECTIVE,
    DeprecatedDirective,
    mark_numpy_returns,
    note_attributes_before_napoleon,
    process_docstring,
)
from ._patches import (
    BUILDING,
    patch_autodoc_type_hints,
    patch_line_numbers,
    patch_lookup_annotation,
    patch_overload_capture,
    patch_signature_lines,
)
from ._render import (
    ALIAS_CHOICE_ROLE,
    ENUM_MEMBER_ROLE,
    DeferAliasChoice,
    alias_choice_role,
    enum_member_role,
    link_enum_member_owner,
    merge_alias_choices,
    unescape,
)
from ._resolve import SHADOWED_BY_GUARD
from ._signature import add_type_params, process_signature, render_header_types
from .version import __version__

if TYPE_CHECKING:
    from docutils.nodes import Node
    from docutils.parsers.rst import states
    from sphinx.application import Sphinx


def setup(app: Sphinx) -> dict[str, bool | str]:
    app.setup_extension("sphinx.ext.autodoc")
    for option in OPTIONS:
        app.add_config_value(option.name, option.default, option.rebuild, option.types)
    app.add_role("sphinx_autodoc_typehints_type", sphinx_autodoc_typehints_type_role)
    app.add_role(ALIAS_CHOICE_ROLE, alias_choice_role)
    app.add_role(ENUM_MEMBER_ROLE, enum_member_role)
    app.add_directive(DEPRECATED_DIRECTIVE, DeprecatedDirective)
    app.add_post_transform(DeferAliasChoice)
    app.connect("config-inited", cache_fixup_module_name)
    app.connect("env-merge-info", merge_alias_choices)
    # after intersphinx, at the default priority, had its chance to link the member itself
    app.connect("missing-reference", link_enum_member_owner, priority=900)
    app.connect("env-before-read-docs", validate_config)
    app.connect("env-before-read-docs", store_type_mapping)
    app.connect("autodoc-process-signature", process_signature)
    # napoleon rewrites the docstring between these, at the default priority of 500
    app.connect("autodoc-process-docstring", note_attributes_before_napoleon, priority=499)
    app.connect("autodoc-process-docstring", mark_numpy_returns, priority=499)
    app.connect("autodoc-process-docstring", process_docstring, priority=500)
    app.connect("object-description-transform", add_type_params)
    app.connect("object-description-transform", render_header_types)
    patch_overload_capture()
    patch_signature_lines()
    patch_autodoc_type_hints()
    # `builder-inited` fires while the app is created, so an app never built would count as building for good
    app.connect("env-before-read-docs", lambda sphinx_app, _env, _docnames: BUILDING.add(id(sphinx_app)))
    # a module edited and imported again since the last build in this process binds other names in its guard
    app.connect("env-before-read-docs", lambda _sphinx_app, _env, _docnames: SHADOWED_BY_GUARD.clear())
    app.connect("build-finished", lambda sphinx_app, _exception: BUILDING.discard(id(sphinx_app)))
    patch_lookup_annotation()
    patch_line_numbers()
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


def sphinx_autodoc_typehints_type_role(
    _role: str,
    _rawtext: str,
    text: str,
    lineno: int,
    inliner: states.Inliner,
    _options: dict[str, object] | None = None,
    _content: list[str] | None = None,
) -> tuple[list[Node], list[Node]]:
    # a type is inline text, a block parse would turn one such as `- item` into a list
    children, messages = inliner.parse(unescape(text), lineno, inliner, inliner.parent)
    return [nodes.inline(text, "", *children, classes=["sphinx_autodoc_typehints-type"])], messages


__all__ = [
    "setup",
]
