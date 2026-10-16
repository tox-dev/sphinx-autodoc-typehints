"""Looks up how a class stores a documented member and which docstrings autodoc shows for a class."""

from __future__ import annotations

from inspect import getattr_static
from typing import TYPE_CHECKING

from .._objects import documented_owner, stored_name

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.ext.autodoc import Options


def overload_skip(what: str, name: str) -> int:
    """Count the leading parameters to drop from an overload, which lists a method's self or cls as parsed."""
    return int(what != "function" and (what != "method" or class_member_type(name) is not staticmethod))


def class_member_type(name: str) -> type | None:
    """
    Return the type of the member `name` as its class stores it, `None` where the class or the member is missing.

    The documented name finds the class even for `add = staticmethod(helper)`, whose `__qualname__` names another.
    """
    owner, attribute = documented_owner(name)
    if owner is None:
        return None
    member = getattr_static(owner, stored_name(owner, attribute), None)
    return None if member is None else type(member)


def class_doc_choice(app: Sphinx, options: Options | None) -> str:
    """Name the docstrings autodoc shows for a class, which the directive's `:class-doc-from:` picks first."""
    return getattr(options, "class_doc_from", None) or app.config.autoclass_content


__all__ = [
    "class_doc_choice",
    "class_member_type",
    "overload_skip",
]
