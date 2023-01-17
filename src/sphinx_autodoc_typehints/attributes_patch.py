from functools import lru_cache, partial
from optparse import Values
from typing import Any, Tuple
from unittest.mock import patch

import sphinx.domains.python
import sphinx.ext.autodoc
from docutils.parsers.rst import Parser as RstParser
from docutils.utils import new_document
from sphinx.addnodes import desc_signature
from sphinx.application import Sphinx
from sphinx.domains.python import PyAttribute
from sphinx.ext.autodoc import AttributeDocumenter

# Defensively check for the things we want to patch
_parse_annotation = getattr(sphinx.domains.python, "_parse_annotation", None)

STRINGIFY_NAME = None
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


def stringify_typehint(app: Sphinx, annotation: Any, mode: str = "") -> str:  # noqa: U100
    """Format the annotation with sphinx-autodoc-typehints and inject our
    magic prefix to tell our patched PyAttribute.handle_signature to treat
    it as rst."""
    from . import format_annotation

    return TYPE_IS_RST_LABEL + format_annotation(annotation, app.config)


def patch_attribute_documenter(app: Sphinx) -> None:
    """Instead of using stringify-typehint in
    `AttributeDocumenter.add_directive_header`, use `format_annotation`.

    We either have to patch sphinx.ext.autodoc.stringify_typehint in sphinx <
    6.1 or sphinx.ext.autodoc.stringify_annotation in sphinx >= 6.1. Bail if
    neither of these exist.
    """

    def add_directive_header(*args: Any, **kwargs: Any) -> Any:
        with patch(STRINGIFY_PATCH_TARGET, partial(stringify_typehint, app)):
            return orig_add_directive_header(*args, **kwargs)

    AttributeDocumenter.add_directive_header = add_directive_header  # type:ignore[assignment]


def rst_to_docutils(settings: Values, rst: str) -> Any:
    """Convert rst to a sequence of docutils nodes"""
    doc = new_document("", settings)
    RstParser().parse(rst, doc)
    # Remove top level paragraph node so that there is no line break.
    return doc.children[0].children


def patched_parse_annotation(settings: Values, typ: str, env: Any) -> Any:
    # if typ doesn't start with our label, use original function
    if not typ.startswith(TYPE_IS_RST_LABEL):
        return _parse_annotation(typ, env)  # type: ignore
    # Otherwise handle as rst
    typ = typ[len(TYPE_IS_RST_LABEL) :]
    return rst_to_docutils(settings, typ)


@lru_cache()
def patch_py_attribute_handle_signature() -> None:
    """
    Patch PyAttribute.handle_signature so that it treats the :type: as rst and
    renders it as-is rather than trying to parse it as a type annotation string.
    """
    orig_handle_signature = PyAttribute.handle_signature

    def handle_signature(self: PyAttribute, sig: str, signode: desc_signature) -> Tuple[str, str]:
        target = "sphinx.domains.python._parse_annotation"
        new_func = partial(patched_parse_annotation, self.state.document.settings)
        with patch(target, new_func):
            return orig_handle_signature(self, sig, signode)

    PyAttribute.handle_signature = handle_signature  # type:ignore[assignment]


def patch_attribute_handling(app: Sphinx) -> None:
    if not OKAY_TO_PATCH:
        return
    patch_py_attribute_handle_signature()
    patch_attribute_documenter(app)


__all__ = ["patch_attribute_handling"]