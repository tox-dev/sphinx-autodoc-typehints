"""Writes signature text, escapes backslashes for the directive, and spots a signature the reader wrote by hand."""

from __future__ import annotations

from inspect import Parameter
from typing import TYPE_CHECKING

from sphinx.util.inspect import signature_from_str

from .._render import as_signature_type

if TYPE_CHECKING:
    from sphinx.application import Sphinx

    from .._refs import WrittenTypeAlias
    from .._types import Hint


def signature_type(app: Sphinx, hint: Hint | WrittenTypeAlias) -> str | type[Parameter.empty]:
    return hint if hint is Parameter.empty else as_signature_type(hint, app.config)


def directive_text(app: Sphinx, signature: str) -> str:
    # the directive strips one level of backslashes only under this option, so escaping otherwise doubles them
    return signature.replace("\\", "\\\\") if app.config.strip_signature_backslash else signature


def names_other_parameters(signature: str, parameters: list[Parameter]) -> bool:
    """
    Return whether the signature autodoc passes lists other parameters than the object takes.

    That is one written in the directive, `.. autofunction:: f(x, y=3)`, or on a docstring's first line, which the
    reader asked for over the object's own, so it stays as written.
    """
    try:
        written = signature_from_str(signature)
    except SyntaxError:
        # autodoc writes some defaults it introspects, such as <object object>, in a form Python cannot read back
        return False
    kinds = [(param.name, param.kind) for param in written.parameters.values()]
    # autodoc falls back to a catch-all when it can't see a class's parameters, as for a @deprecated class or one whose
    # base's __new__ takes *args and **kwargs, which a reader does not write to hide parameters
    if all(kind in {Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD} for _, kind in kinds):
        return False
    return kinds != [(param.name, param.kind) for param in parameters]


__all__ = [
    "directive_text",
    "names_other_parameters",
    "signature_type",
]
