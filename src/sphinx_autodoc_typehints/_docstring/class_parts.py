"""Splits the fields of a class entry between its class and constructor docstrings when Sphinx shows both."""

from __future__ import annotations

from inspect import Signature, isclass
from typing import TYPE_CHECKING, Literal

from sphinx.util.inspect import getdoc

from .._documented import class_doc_choice
from .._state import class_docstrings
from .formats import detect_format
from .parameters import escape_trailing_underscore

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.ext.autodoc import Options

    from .._types import Documented


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
