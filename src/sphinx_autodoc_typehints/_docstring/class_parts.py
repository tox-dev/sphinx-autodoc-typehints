"""Splits the fields of a class entry between its class and constructor docstrings when Sphinx shows both."""

from __future__ import annotations

__lazy_modules__ = [
    "inspect",
    "sphinx",
    "sphinx.util",
    "sphinx.util.inspect",
    "sphinx_autodoc_typehints._docstring.formats",
    "sphinx_autodoc_typehints._docstring.parameters",
    "sphinx_autodoc_typehints._documented",
    "sphinx_autodoc_typehints._state",
]

from inspect import Signature, isclass
from typing import TYPE_CHECKING, Literal

from sphinx.util.inspect import getdoc

from sphinx_autodoc_typehints._docstring.formats import detect_format
from sphinx_autodoc_typehints._docstring.parameters import escape_trailing_underscore
from sphinx_autodoc_typehints._documented import class_doc_choice
from sphinx_autodoc_typehints._state import class_docstrings

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.ext.autodoc import Options

    from sphinx_autodoc_typehints._types import Documented


def docstring_part(
    env: BuildEnvironment, name: str, signature: Signature, options: Options | None, lines: list[str]
) -> tuple[Literal["class", "constructor"], frozenset[str]]:
    """
    Return which part of a class entry `lines` is, and which parameters another part documents.

    Showing the docstrings of both, Sphinx processes a class and its constructor docstring one after the other, as two
    parts of one entry. What the extension adds goes in one of them: only the constructor's lists the parameters that
    neither documents.
    """
    stashed_parts = class_docstrings(env)
    # autodoc hands both parts the options of their directive, so a part another directive left cannot pair up
    if (stashed := stashed_parts.pop(name, None)) is None or stashed[0] is not options:
        stashed_parts[name] = options, lines
        return "class", frozenset(signature.parameters)
    fmt = detect_format(class_lines := stashed[1])
    # the docstring may spell a trailing underscore escaped, as _find_param accepts
    return "constructor", frozenset(
        param
        for param in signature.parameters
        if any(
            fmt.find_param(class_lines, spelling) is not None for spelling in {param, escape_trailing_underscore(param)}
        )
    )


def has_constructor_docstring(app: Sphinx, name: str, cls: Documented, options: Options | None) -> bool:
    """Return whether Sphinx shows the docstring of the class and of its constructor, mirroring how it chooses."""
    # Sphinx documents a class under another name as an alias, with no docstring of the class or its constructor
    if (
        not isclass(cls)
        or name.rpartition(".")[2] != cls.__name__
        or class_doc_choice(app, options) != "both"
        or not getdoc(cls)
    ):
        return False
    inherit = app.config.autodoc_inherit_docstrings
    init_doc = getdoc(cls.__init__, allow_inherited=inherit, cls=cls, name="__init__")
    if init_doc and init_doc != object.__init__.__doc__:
        return True
    new_doc = getdoc(cls.__new__, allow_inherited=inherit, cls=object, name="__new__")
    return bool(new_doc) and new_doc != object.__new__.__doc__


__all__ = [
    "docstring_part",
    "has_constructor_docstring",
]
