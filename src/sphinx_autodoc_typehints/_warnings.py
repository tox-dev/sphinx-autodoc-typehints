"""
Foundation helper that emits the extension's warnings under suppressible categories.

Each category is `sphinx_autodoc_typehints.<subtype>`.
"""

from __future__ import annotations

__lazy_modules__ = ["sphinx", "sphinx.util", "sphinx_autodoc_typehints._objects"]

from typing import TYPE_CHECKING, Literal

from sphinx.util import logging

from sphinx_autodoc_typehints._objects import get_obj_location

if TYPE_CHECKING:
    from sphinx_autodoc_typehints._types import Documented

type WarningSubtype = Literal["comment", "forward_reference", "guarded_import", "local_function", "multiple_ast_nodes"]


def warn(subtype: WarningSubtype, message: str, *args: object, at: Documented) -> None:
    """Warn about `at`, located where its source is, under `sphinx_autodoc_typehints.<subtype>`."""
    logging.getLogger(__name__).warning(
        message, *args, type="sphinx_autodoc_typehints", subtype=subtype, location=get_obj_location(at)
    )


__all__ = [
    "warn",
]
