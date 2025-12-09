"""Patch for attributes."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import sphinx.domains.python
from sphinx.domains.python import PyAttribute

from ._parser import parse

if TYPE_CHECKING:
    from docutils.frontend import Values
    from sphinx.addnodes import desc_signature
    from sphinx.application import Sphinx

# Defensively check for the things we want to patch
_parse_annotation = getattr(sphinx.domains.python, "_parse_annotation", None)

# If we didn't locate the patch target, we will just do nothing.
OKAY_TO_PATCH = bool(_parse_annotation)

# A label we inject to the type string so we know not to try to treat it as a
# type annotation
TYPE_IS_RST_LABEL = "--is-rst--"

orig_handle_signature = PyAttribute.handle_signature


def rst_to_docutils(settings: Values, rst: str) -> Any:
    """Convert rst to a sequence of docutils nodes."""
    doc = parse(rst, settings)
    # Remove top level paragraph node so that there is no line break.
    return doc.children[0].children


def patched_parse_annotation(settings: Values, typ: str, env: Any) -> Any:
    # if typ doesn't start with our label, use original function
    if not typ.startswith(TYPE_IS_RST_LABEL):
        assert _parse_annotation is not None  # noqa: S101
        return _parse_annotation(typ, env)
    # Otherwise handle as rst
    typ = typ[len(TYPE_IS_RST_LABEL) :]
    return rst_to_docutils(settings, typ)


def patched_handle_signature(self: PyAttribute, sig: str, signode: desc_signature) -> tuple[str, str]:
    target = "sphinx.domains.python._parse_annotation"
    new_func = partial(patched_parse_annotation, self.state.document.settings)
    with patch(target, new_func):
        return orig_handle_signature(self, sig, signode)


def patch_attribute_handling(app: Sphinx) -> None:  # noqa: ARG001
    """Patch PyAttribute.handle_signature to format class attribute type annotations."""
    if not OKAY_TO_PATCH:
        return
    PyAttribute.handle_signature = patched_handle_signature  # type:ignore[method-assign]


__all__ = ["patch_attribute_handling"]
