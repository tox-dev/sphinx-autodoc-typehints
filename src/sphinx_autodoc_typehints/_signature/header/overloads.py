"""Picks the overloads a signature lists."""

from __future__ import annotations

from inspect import Signature, isclass
from typing import TYPE_CHECKING

from sphinx.util.inspect import getdoc

from ..._documented import (  # simplint: ignore[private-import-path]  # root API stays unchanged
    OVERLOADED_KINDS,
    class_doc_choice,
)
from ..._resolve import (  # simplint: ignore[private-import-path]  # root API stays unchanged
    resolve_overloads,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.application import Sphinx
    from sphinx.ext.autodoc import Options

    from . import QualifiedCallable


def signature_overloads(
    app: Sphinx,
    what: str,
    documented: Callable[  # simplint: ignore[callable-ellipsis]  # any documented callable
        ..., object
    ],
    obj: QualifiedCallable,
    options: Options,
) -> list[Signature]:
    if (
        not app.config.typehints_use_signature
        or not app.config.typehints_document_overloads
        or what not in OVERLOADED_KINDS
        or (overloads := resolve_overloads(obj)) is None
    ):
        return []
    # autodoc hands the docstring to process_docstring only after building the signature, so the opt-out is read here
    sources = [documented]
    if isclass(documented) and class_doc_choice(app, options) != "class":
        sources.append(obj)
    if any(
        line.strip() == ":no-overloads:"
        for source in sources
        for line in (getdoc(source, allow_inherited=app.config.autodoc_inherit_docstrings) or "").splitlines()
    ):
        return []
    return overloads


__all__ = [
    "signature_overloads",
]
