from __future__ import annotations

from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, fixture, mark

from sphinx_autodoc_typehints._docstring import process_docstring

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.config import Config
    from sphinx.testing.util import SphinxTestApp

    from sphinx_autodoc_typehints._types import Annotation, Documented

type Process = Callable[[str, str, Documented, list[str]], list[str]]

INT: Final[str] = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``"
STR: Final[str] = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`str\``"
FLOAT: Final[str] = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`float\``"
BOOL: Final[str] = r":sphinx_autodoc_typehints_type:`\:py\:class\:\`bool\``"
NONE: Final[str] = r":sphinx_autodoc_typehints_type:`\:sphinx\_autodoc\_typehints\_constant\:\`None\``"


# a closer sphinx mark replaces the module's confoverrides whole, so each one repeats the base option
def without_rtype(**options: bool | str) -> MarkDecorator:
    return mark.sphinx(confoverrides={"typehints_document_rtype": False, **options})


def hide_type(_annotation: Annotation, _config: Config) -> str:
    return ""


@fixture
def process(app: SphinxTestApp) -> Process:
    def run(what: str, name: str, obj: Documented, lines: list[str]) -> list[str]:
        process_docstring(app, what, name, obj, None, lines)
        return lines

    return run


__all__ = [
    "BOOL",
    "FLOAT",
    "INT",
    "NONE",
    "STR",
    "Process",
    "hide_type",
    "without_rtype",
]
