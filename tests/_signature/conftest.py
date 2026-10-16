from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pytest import fixture
from sphinx.ext.autodoc import Options

from sphinx_autodoc_typehints._signature import process_signature

if TYPE_CHECKING:
    from collections.abc import Callable

    from docutils import nodes
    from sphinx.testing.util import SphinxTestApp


type BuildDoctree = Callable[[str], nodes.document]


class SignatureOf(Protocol):
    def __call__(
        self, what: str, name: str, obj: Callable[..., object], given: str | None = ""
    ) -> tuple[str, None] | None: ...


@fixture
def signature_of(app: SphinxTestApp) -> SignatureOf:
    def process(what: str, name: str, obj: Callable[..., object], given: str | None = "") -> tuple[str, None] | None:
        return process_signature(app, what, name, obj, Options(), given, "")

    return process


@fixture
def build_doctree(app: SphinxTestApp, write_rst: Callable[[str], None]) -> BuildDoctree:
    def build(rst: str) -> nodes.document:
        write_rst(rst)
        app.build()
        return app.env.get_doctree("index")

    return build


__all__ = [
    "BuildDoctree",
    "SignatureOf",
]
