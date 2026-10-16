"""
What the extension works out about the object autodoc documents.

That covers its types and overloads, how its class stores a member, and the scope its types render in. The package
sits below `_docstring` and `_signature` and above `_render` and `_resolve`.
"""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._documented.entry",
    "sphinx_autodoc_typehints._documented.factory_defaults",
    "sphinx_autodoc_typehints._documented.hints",
    "sphinx_autodoc_typehints._documented.members",
    "sphinx_autodoc_typehints._documented.overloads",
    "sphinx_autodoc_typehints._documented.scope",
]

from sphinx_autodoc_typehints._documented.entry import Entry
from sphinx_autodoc_typehints._documented.factory_defaults import show_factory_defaults
from sphinx_autodoc_typehints._documented.hints import ResolvedHints, as_written, documenting_class, resolved_type_hints
from sphinx_autodoc_typehints._documented.members import class_doc_choice, class_member_type, overload_skip
from sphinx_autodoc_typehints._documented.overloads import OVERLOADED_KINDS, typed_overloads
from sphinx_autodoc_typehints._documented.scope import render_scope

__all__ = [
    "OVERLOADED_KINDS",
    "Entry",
    "ResolvedHints",
    "as_written",
    "class_doc_choice",
    "class_member_type",
    "documenting_class",
    "overload_skip",
    "render_scope",
    "resolved_type_hints",
    "show_factory_defaults",
    "typed_overloads",
]
