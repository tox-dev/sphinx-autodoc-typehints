"""Custom patches to make the world work."""

from __future__ import annotations

from functools import lru_cache, wraps
from typing import TYPE_CHECKING, Any, Final, cast

from docutils import nodes
from docutils.parsers.rst.directives.admonitions import BaseAdmonition
from docutils.parsers.rst.states import Body, Text
from sphinx.directives import ObjectDescription
from sphinx.ext.napoleon.docstring import GoogleDocstring

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.ext.autodoc import Options


def napoleon_numpy_docstring_return_type_processor(  # ruff:ignore[too-many-arguments, too-many-positional-arguments]
    app: Sphinx,
    what: str,
    name: str,  # ruff:ignore[unused-function-argument]
    obj: Any,  # ruff:ignore[unused-function-argument]
    options: Options | None,  # ruff:ignore[unused-function-argument]
    lines: list[str],
) -> None:
    """Insert a : under Returns: to tell napoleon not to look for a return type."""
    if what not in {"function", "method"}:
        return
    if not getattr(app.config, "napoleon_numpy_docstring", False):
        return

    # Search for the returns header:
    # Returns:
    # --------
    for pos, line in enumerate(lines[:-2]):
        if line.lower().strip(":") not in {"return", "returns"}:
            continue
        # Underline detection.
        chars = set(lines[pos + 1].strip())
        # Napoleon allows the underline to consist of a bunch of weirder things...
        if len(chars) != 1 or next(iter(chars)) not in "=-~_*+#":
            continue
        pos += 2  # ruff:ignore[redefined-loop-name]
        break
    else:
        return

    end = next((index for index in range(pos, len(lines)) if not lines[index].strip()), len(lines))
    # an unindented sentence reads as a type to napoleon; indented under the empty field it becomes the description.
    # A type line has its description indented under it, so only a paragraph with no indented line is a sentence.
    if (
        (paragraph := lines[pos:end])
        and not any(line[:1].isspace() for line in paragraph)
        and paragraph[-1].rstrip().endswith(".")
    ):
        lines[pos:end] = [f"    {line}" for line in paragraph]
    lines.insert(pos, ":")


def fix_napoleon_numpy_docstring_return_type(app: Sphinx) -> None:
    """If no return type is explicitly set, numpy docstrings will use the return type text as return types."""
    # standard priority is 500. Setting priority to 499 ensures this runs before
    # napoleon's docstring processor.
    app.connect("autodoc-process-docstring", napoleon_numpy_docstring_return_type_processor, priority=499)


@wraps(GoogleDocstring._lookup_annotation)
def _patched_lookup_annotation(*_args: Any) -> str:
    """
    GoogleDocstring._lookup_annotation sometimes adds incorrect type annotations to constructor parameters.

    Disable it so we can handle this on our own.
    """
    return ""


def _patch_google_docstring_lookup_annotation() -> None:
    """Fix issue https://github.com/tox-dev/sphinx-autodoc-typehints/issues/308."""
    # the extension types the attributes of a class or module itself, rendered like its other fields
    GoogleDocstring._lookup_annotation = _patched_lookup_annotation  # type: ignore[assignment]


orig_base_admonition_run = BaseAdmonition.run


@wraps(orig_base_admonition_run)
def _patched_base_admonition_run(self: BaseAdmonition) -> Any:
    result = orig_base_admonition_run(self)
    # the directive counts lines across included files, the node names its place within its own source file
    result[0].source, result[0].line = self.state_machine.get_source_and_line(self.lineno)
    return result


orig_text_indent = Text.indent


@wraps(orig_text_indent)
def _patched_text_indent(self: Text, *args: Any) -> Any:
    _, line = self.state_machine.get_source_and_line()  # ty: ignore[unresolved-attribute]
    result = orig_text_indent(self, *args)
    node = self.parent[-1]  # ty: ignore[not-subscriptable]
    if node.tagname == "system_message":
        node = self.parent[-2]  # ty: ignore[not-subscriptable]
    node.line = line
    return result


@wraps(Body.doctest)
def _patched_body_doctest(
    self: Body, _match: None, _context: None, next_state: str | None
) -> tuple[list[Any], str | None, list[Any]]:
    assert self.document.current_line is not None  # ruff:ignore[assert]
    line = self.document.current_line  # get_text_block moves past the block
    data = "\n".join(self.state_machine.get_text_block())  # ty: ignore[unresolved-attribute]
    n = nodes.doctest_block(data, data)
    n.line = line
    self.parent += n  # ty: ignore[unsupported-operator]
    return [], next_state, []


def _patch_line_numbers() -> None:
    """
    Make the rst parser put line numbers on more nodes.

    When the line numbers are missing, we have a hard time placing the :rtype:.
    """
    Text.indent = _patched_text_indent  # type: ignore[method-assign]
    BaseAdmonition.run = _patched_base_admonition_run  # type: ignore[method-assign,assignment]
    Body.doctest = _patched_body_doctest  # type: ignore[method-assign]


_OVERLOADS_CACHE: dict[str, dict[Any, Any]] = {}
_BUILDING: set[int] = set()


@lru_cache
def fix_directive_based_signature_formatting() -> None:
    """
    Patch Sphinx 9's new directive-based autodoc to cache and clear overload detection.

    Overloads are cached before being cleared so we can render them in docstrings with
    proper type formatting instead of in signatures where types can't be cross-referenced.
    """
    from sphinx.pycode import ModuleAnalyzer  # ruff:ignore[import-outside-top-level]

    original_analyze = ModuleAnalyzer.analyze

    @wraps(original_analyze)
    def patched_analyze(self: Any) -> None:
        original_analyze(self)
        if self.overloads:
            _OVERLOADS_CACHE[self.modname] = dict(self.overloads)
        # every app in the process shares the analyzer, so hide the overloads only while an app using us builds
        self.overloads = {} if _BUILDING else dict(_OVERLOADS_CACHE.get(self.modname, {}))

    ModuleAnalyzer.analyze = patched_analyze  # type: ignore[method-assign]


_SIGNATURE_LINES: Final = "sphinx_autodoc_typehints_signature_lines"


def add_signature_lines(env: BuildEnvironment, name: str, signatures: list[str]) -> None:
    """Have the directive autodoc writes for ``name`` with the first of ``signatures`` show each on its own line."""
    _signature_lines(env)[f"{name}{signatures[0]}"] = signatures


@lru_cache
def _patch_signature_lines() -> None:
    """
    Add the signature lines autodoc-process-signature cannot return to the directive autodoc writes.

    The event replaces only the first line, and a line break in it breaks the directive, while the Python domain
    parses each line of the directive into a signature of its own, linking only the first as the target.
    """
    # patched where it is defined, so the Python domain's directives list no member of their own
    original_get_signatures = ObjectDescription.get_signatures

    @wraps(original_get_signatures)
    def get_signatures(self: ObjectDescription[Any]) -> list[str]:
        line = self.arguments[0]
        key = f"{self.options.get('module')}.{line}"
        if signatures := _signature_lines(self.env).pop(key, None):
            name = line.removesuffix(signatures[0])
            self.arguments[0] = "\n".join(f"{name}{signature}" for signature in signatures)
        return original_get_signatures(self)

    ObjectDescription.get_signatures = get_signatures  # type: ignore[method-assign]


def _signature_lines(env: BuildEnvironment) -> dict[str, list[str]]:
    return cast("dict[str, list[str]]", env.temp_data.setdefault(_SIGNATURE_LINES, {}))


def install_patches(app: Sphinx) -> None:
    """
    Install the patches.

    :param app: the Sphinx app
    """
    # For Sphinx 9+ directive-based architecture
    fix_directive_based_signature_formatting()
    _patch_signature_lines()
    app.connect("builder-inited", lambda app: _BUILDING.add(id(app)))
    app.connect("build-finished", lambda app, _exception: _BUILDING.discard(id(app)))
    _patch_google_docstring_lookup_annotation()
    fix_napoleon_numpy_docstring_return_type(app)
    _patch_line_numbers()


__all__ = [
    "_OVERLOADS_CACHE",
    "add_signature_lines",
    "install_patches",
]
