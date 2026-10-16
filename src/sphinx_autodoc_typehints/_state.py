"""
Foundation record of the state the event handlers share.

Most of it lives in the environment's `current_document` for the document being read; the alias choices live in an
environment attribute, so the cached environment keeps them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from sphinx.ext.autodoc import Options

if TYPE_CHECKING:
    from sphinx.environment import BuildEnvironment

_DOCUMENTED: Final[str] = "sphinx_autodoc_typehints_documented"
_TYPES_DOCUMENTED: Final[str] = "sphinx_autodoc_typehints_types_documented"
# an environment attribute rather than current_document, so the pickled environment keeps the choices across builds
_ALIAS_CHOICES: Final[str] = "_typehints_alias_choices"


def note_documented(env: BuildEnvironment, name: str) -> None:
    """Remember that autodoc documents `name` on the page being read, so its header is the extension's to render."""
    _record(env, _DOCUMENTED, set[str]()).add(name)


def is_documented(env: BuildEnvironment, name: str) -> bool:
    """
    Tell whether autodoc documents `name` on the page being read.

    autodoc already looked such a name up, so looking it up again runs no package `__getattr__` autodoc did not run;
    looking up a name written by hand could import, raise, or rename what autodoc documents later.
    """
    return name in (env.current_document.get(_DOCUMENTED) or ())


def _record[Record](env: BuildEnvironment, key: str, empty: Record) -> Record:
    if (record := env.current_document.get(key)) is None:
        record = env.current_document[key] = empty
    return record


def written_signatures(env: BuildEnvironment) -> set[str]:
    """Name the objects whose signature autodoc kept as written, so their overloads show as a field."""
    return _record(env, "sphinx_autodoc_typehints_written_signatures", set[str]())


def add_signature_lines(env: BuildEnvironment, name: str, signatures: list[str]) -> None:
    """Have the directive autodoc writes for `name` with the first of `signatures` show each on its own line."""
    signature_lines(env)[f"{name}{signatures[0]}"] = signatures


def signature_lines(env: BuildEnvironment) -> dict[str, list[str]]:
    """Map the first line of each directive that shows overloads to all of its lines."""
    return _record(env, "sphinx_autodoc_typehints_signature_lines", dict[str, list[str]]())


def note_type_documented(env: BuildEnvironment) -> None:
    env.current_document[_TYPES_DOCUMENTED] = types_documented(env) + 1


def types_documented(env: BuildEnvironment) -> int:
    return env.current_document.get(_TYPES_DOCUMENTED) or 0


def class_docstrings(env: BuildEnvironment) -> dict[str, tuple[Options | None, list[str]]]:
    """Hold the class docstring of each entry until autodoc hands over its constructor docstring."""
    return _record(env, "sphinx_autodoc_typehints_class_docstrings", dict[str, tuple[Options | None, list[str]]]())


def alias_choices(env: BuildEnvironment) -> dict[str, tuple[str, ...]]:
    """Return the alias choices recorded on the environment, adding the record on first use."""
    if (choices := getattr(env, _ALIAS_CHOICES, None)) is None:
        choices = {}
        setattr(env, _ALIAS_CHOICES, choices)
    return choices


def recorded_alias_choices(env: BuildEnvironment) -> dict[str, tuple[str, ...]]:
    """Return the alias choices an environment recorded, without adding a record to one holding none."""
    return getattr(env, _ALIAS_CHOICES, None) or {}


__all__ = [
    "add_signature_lines",
    "alias_choices",
    "class_docstrings",
    "is_documented",
    "note_documented",
    "note_type_documented",
    "recorded_alias_choices",
    "signature_lines",
    "types_documented",
    "written_signatures",
]
