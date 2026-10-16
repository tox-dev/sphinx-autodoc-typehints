"""
Values a rendered type or default shows, as `'fill'` of a `Literal` or a default, colored by the Pygments style.

Each value sits in an inline `.highlight` scope with one Pygments token class per part, so the stylesheet the theme
generates for code blocks colors it, in light and dark alike. The extension's stylesheet only keeps the block layout of
`.highlight` off these inline values.
"""

from __future__ import annotations

__lazy_modules__ = ["docutils", "docutils.utils", "itertools", "operator", "pathlib", "sphinx"]

from itertools import groupby
from operator import itemgetter
from pathlib import Path
from typing import TYPE_CHECKING, Final

from docutils import nodes
from docutils.utils import unescape
from pygments.lexers.python import PythonLexer
from pygments.token import STANDARD_TYPES, Error
from sphinx import addnodes
from sphinx.domains.python import PyXRefRole

if TYPE_CHECKING:
    from docutils.nodes import Node, system_message
    from docutils.parsers.rst import states
    from pygments.token import _TokenType
    from sphinx.application import Sphinx

VALUE_ROLE: Final[str] = "sphinx_autodoc_typehints_value"
CONSTANT_ROLE: Final[str] = "sphinx_autodoc_typehints_constant"
VALUE_STYLESHEET: Final[str] = "sphinx_autodoc_typehints.css"
_LEXER: Final[PythonLexer] = PythonLexer(ensurenl=False)
_XREF_ROLE: Final[PyXRefRole] = PyXRefRole()


def value_markup(text: str) -> str:
    """Wrap the Python source `text` of a value in the role coloring it."""
    # inside a role only a backslash or a backtick is markup, and the source keeps its punctuation readable
    return f":{VALUE_ROLE}:`{text.replace('\\', '\\\\').replace('`', '\\`')}`"


def value_role(
    _role: str,
    rawtext: str,
    text: str,
    _lineno: int,
    _inliner: states.Inliner,
    _options: dict[str, object] | None = None,
    _content: list[str] | None = None,
) -> tuple[list[Node], list[system_message]]:
    return [_scope(_color(nodes.literal(rawtext), unescape(text)))], []


def constant_role(
    _role: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: states.Inliner,
    options: dict[str, object] | None = None,
    content: list[str] | None = None,
) -> tuple[list[Node], list[system_message]]:
    # the Python docs list True and False as data on their constants page
    kind = "py:obj" if text == "None" else "py:data"
    refs, messages = _XREF_ROLE(kind, rawtext, text, lineno, inliner, options or {}, content or [])
    xref = next(ref for ref in refs if isinstance(ref, addnodes.pending_xref))
    _color(xref[0], text)
    return [_scope(ref) if ref is xref else ref for ref in refs], messages


def _color(literal: nodes.Element, source: str) -> nodes.Element:
    del literal[:]
    for ttype, tokens in groupby(_LEXER.get_tokens(source), key=itemgetter(0)):
        text = "".join(part for _, part in tokens)
        # a default's description need not be valid Python, and the error class frames each such character in red
        if token_class := "" if ttype in Error else _token_class(ttype):
            literal += nodes.inline(text, text, classes=[token_class])
        else:
            literal += nodes.Text(text)
    return literal


def _scope(node: nodes.Node) -> nodes.inline:
    return nodes.inline("", "", node, classes=["highlight", "sphinx_autodoc_typehints-value"])


def _token_class(ttype: _TokenType) -> str:
    # a token type without a class of its own takes the one of its nearest parent, as the HTML formatter does
    return next(STANDARD_TYPES[kind] for kind in reversed(ttype.split()) if kind in STANDARD_TYPES)


def add_value_stylesheet(app: Sphinx) -> None:
    """Serve the stylesheet keeping the block layout of `.highlight` off inline values."""
    app.config.html_static_path.append(str(Path(__file__).parents[1] / "_static"))


__all__ = [
    "CONSTANT_ROLE",
    "VALUE_ROLE",
    "VALUE_STYLESHEET",
    "add_value_stylesheet",
    "constant_role",
    "value_markup",
    "value_role",
]
