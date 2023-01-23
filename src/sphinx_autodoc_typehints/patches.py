from __future__ import annotations

from functools import lru_cache
from typing import Any

from docutils.parsers.rst.directives.admonitions import BaseAdmonition
from docutils.parsers.rst.states import Text
from sphinx.application import Sphinx
from sphinx.ext.autodoc import Options
from sphinx.ext.napoleon.docstring import GoogleDocstring

from .attributes_patch import patch_attribute_handling


@lru_cache()  # A cute way to make sure the function only runs once.
def fix_autodoc_typehints_for_overloaded_methods() -> None:
    """
    sphinx-autodoc-typehints responds to the "autodoc-process-signature" event
    to remove types from the signature line of functions.

    Normally, `FunctionDocumenter.format_signature` and
    `MethodDocumenter.format_signature` call `super().format_signature` which
    ends up going to `Documenter.format_signature`, and this last method emits
    the `autodoc-process-signature` event. However, if there are overloads,
    `FunctionDocumenter.format_signature` does something else and the event
    never occurs.

    Here we remove this alternative code path by brute force.

    See https://github.com/tox-dev/sphinx-autodoc-typehints/issues/296
    """
    from sphinx.ext.autodoc import FunctionDocumenter, MethodDocumenter

    del FunctionDocumenter.format_signature
    del MethodDocumenter.format_signature


def napoleon_numpy_docstring_return_type_processor(
    app: Sphinx, what: str, name: str, obj: Any, options: Options | None, lines: list[str]  # noqa: U100
) -> None:
    """Insert a : under Returns: to tell napoleon not to look for a return type."""
    if what not in ["function", "method"]:
        return
    if not getattr(app.config, "napoleon_numpy_docstring", False):
        return

    # Search for the returns header:
    # Returns:
    # --------
    for idx, line in enumerate(lines[:-2]):
        if line.lower().strip(":") not in ["return", "returns"]:
            continue
        # Underline detection.
        chars = set(lines[idx + 1].strip())
        # Napoleon allows the underline to consist of a bunch of weirder things...
        if len(chars) != 1 or list(chars)[0] not in "=-~_*+#":
            continue
        idx = idx + 2
        break
    else:
        return

    lines.insert(idx, ":")


def fix_napoleon_numpy_docstring_return_type(app: Sphinx) -> None:
    """
    If no return type is explicitly provided, numpy docstrings will mess up and
    use the return type text as return types.
    """
    # standard priority is 500. Setting priority to 499 ensures this runs before
    # napoleon's docstring processor.
    app.connect("autodoc-process-docstring", napoleon_numpy_docstring_return_type_processor, priority=499)


def patched_lookup_annotation(*_args: Any) -> str:  # noqa: U101
    """GoogleDocstring._lookup_annotation sometimes adds incorrect type
    annotations to constructor parameters (and otherwise does nothing). Disable
    it so we can handle this on our own.
    """
    return ""


def patch_google_docstring_lookup_annotation() -> None:
    """Fix issue 308:
    https://github.com/tox-dev/sphinx-autodoc-typehints/issues/308
    """
    GoogleDocstring._lookup_annotation = patched_lookup_annotation  # type: ignore[assignment]


orig_base_admonition_run = BaseAdmonition.run


def patched_base_admonition_run(self: BaseAdmonition) -> Any:
    result = orig_base_admonition_run(self)
    result[0].line = self.lineno
    return result


orig_text_indent = Text.indent


def patched_text_indent(self: Text, *args: Any) -> Any:
    _, line = self.state_machine.get_source_and_line()
    result = orig_text_indent(self, *args)
    node = self.parent[-1]
    if node.tagname == "system_message":
        node = self.parent[-2]
    node.line = line
    return result


def patch_line_numbers() -> None:
    """Make the rst parser put line numbers on more nodes.

    When the line numbers are missing, we have a hard time placing the :rtype:.
    """
    Text.indent = patched_text_indent
    BaseAdmonition.run = patched_base_admonition_run


def install_patches(app: Sphinx) -> None:
    fix_autodoc_typehints_for_overloaded_methods()
    patch_attribute_handling(app)
    patch_google_docstring_lookup_annotation()
    fix_napoleon_numpy_docstring_return_type(app)
    patch_line_numbers()


___all__ = ["install_patches"]
