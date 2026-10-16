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
    take_over_napoleon_attr_annotations,
)
from ._patches import (
    BUILDING,
    patch_autodoc_type_hints,
    patch_doctest_line_number,
    patch_overload_capture,
    patch_signature_lines,
)
from ._render import (
    ALIAS_CHOICE_ROLE,
    CONSTANT_ROLE,
    ENUM_MEMBER_ROLE,
    VALUE_ROLE,
    VALUE_STYLESHEET,
    AliasChoiceCollector,
    DeferAliasChoice,
    add_value_stylesheet,
    alias_choice_role,
    constant_role,
    enum_member_role,
    link_enum_member_owner,
    note_builder,
    unescape,
    value_role,
)
from ._resolve import SHADOWED_BY_GUARD
from ._signature import add_type_params, process_bases, process_signature, render_header_types
from .version import __version__

if TYPE_CHECKING:
    from docutils.nodes import Node
    from docutils.parsers.rst import states
    from sphinx.application import Sphinx


def setup(app: Sphinx) -> dict[str, bool | int | str]:
    app.setup_extension("sphinx.ext.autodoc")
    for option in OPTIONS:
        app.add_config_value(option.name, option.default, option.rebuild, option.types)
    app.add_role("sphinx_autodoc_typehints_type", sphinx_autodoc_typehints_type_role)
    app.add_role(ALIAS_CHOICE_ROLE, alias_choice_role)
    app.add_role(ENUM_MEMBER_ROLE, enum_member_role)
    app.add_role(VALUE_ROLE, value_role)
    app.add_role(CONSTANT_ROLE, constant_role)
    app.add_css_file(VALUE_STYLESHEET)
    app.add_directive(DEPRECATED_DIRECTIVE, DeprecatedDirective)
    app.add_post_transform(DeferAliasChoice)
    app.add_env_collector(AliasChoiceCollector)
    app.connect("config-inited", cache_fixup_module_name)
    # after Sphinx checked the type of each option against its default
    app.connect("config-inited", take_over_napoleon_attr_annotations, priority=900)
    app.connect("builder-inited", add_value_stylesheet)
    app.connect("builder-inited", note_builder)
    # after intersphinx, at the default priority, had its chance to link the member itself
    app.connect("missing-reference", link_enum_member_owner, priority=900)
    app.connect("env-before-read-docs", validate_config)
    app.connect("env-before-read-docs", store_type_mapping)
    app.connect("autodoc-process-signature", process_signature)
    app.connect("autodoc-process-bases", process_bases)
    # napoleon and numpydoc rewrite the docstring between these, at the default priority of 500; above it the fields
    # they write exist whichever order `extensions` lists them in
    app.connect("autodoc-process-docstring", note_attributes_before_napoleon, priority=499)
    app.connect("autodoc-process-docstring", mark_numpy_returns, priority=499)
    app.connect("autodoc-process-docstring", process_docstring, priority=501)
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
    patch_doctest_line_number()
    return {
        "version": __version__,
        "env_version": 1,
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
