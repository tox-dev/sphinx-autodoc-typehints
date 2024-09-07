"""Patch for attributes."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import sphinx.domains.python
import sphinx.ext.autodoc
from sphinx.domains.python import PyAttribute
from sphinx.ext.autodoc import AttributeDocumenter

from ._parser import parse

if TYPE_CHECKING:
    from docutils.frontend import Values
    from sphinx.addnodes import desc_signature
    from sphinx.application import Sphinx

# Defensively check for the things we want to patch
_parse_annotation = getattr(sphinx.domains.python, "_parse_annotation", None)

# We want to patch:
# * sphinx.ext.autodoc.stringify_typehint (in sphinx < 6.1)
# * sphinx.ext.autodoc.stringify_annotation (in sphinx >= 6.1)
STRINGIFY_PATCH_TARGET = ""
for target in ["stringify_typehint", "stringify_annotation"]:
    if hasattr(sphinx.ext.autodoc, target):
        STRINGIFY_PATCH_TARGET = f"sphinx.ext.autodoc.{target}"
        break

# If we didn't locate both patch targets, we will just do nothing.
OKAY_TO_PATCH = bool(_parse_annotation and STRINGIFY_PATCH_TARGET)

# A label we inject to the type string so we know not to try to treat it as a
# type annotation
TYPE_IS_RST_LABEL = "--is-rst--"


orig_add_directive_header = AttributeDocumenter.add_directive_header
orig_handle_signature = PyAttribute.handle_signature


def _stringify_annotation(app: Sphinx, annotation: Any, mode: str = "") -> str:  # noqa: ARG001
    # Format the annotation with sphinx-autodoc-typehints and inject our magic prefix to tell our patched
    # PyAttribute.handle_signature to treat it as rst.
    from . import format_annotation  # noqa: PLC0415

    return TYPE_IS_RST_LABEL + format_annotation(annotation, app.config)


def patch_attribute_documenter(app: Sphinx) -> None:
    """Instead of using stringify_typehint in `AttributeDocumenter.add_directive_header`, use `format_annotation`."""

    def add_directive_header(*args: Any, **kwargs: Any) -> Any:
        with patch(STRINGIFY_PATCH_TARGET, partial(_stringify_annotation, app)):
            return orig_add_directive_header(*args, **kwargs)

    AttributeDocumenter.add_directive_header = add_directive_header  # type:ignore[method-assign]


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


def patch_attribute_handling(app: Sphinx) -> None:
    """Use format_signature to format class attribute type annotations."""
    if not OKAY_TO_PATCH:
        return
    PyAttribute.handle_signature = patched_handle_signature  # type:ignore[method-assign]
    patch_attribute_documenter(app)


__all__ = ["patch_attribute_handling"]
