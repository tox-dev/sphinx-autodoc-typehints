from __future__ import annotations

from pathlib import Path
from sys import path
from typing import TYPE_CHECKING, Any
from zlib import compress

path.insert(0, str(Path(__file__).parent))

if TYPE_CHECKING:
    from sphinx.config import Config

master_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

# a hand-rolled inventory keeps the fixture offline
_INVENTORY = Path(__file__).parent / "objects.inv"
_INVENTORY.write_bytes(
    b"# Sphinx inventory version 2\n"
    b"# Project: demo\n"
    b"# Version: 1.0\n"
    b"# The remainder of this file is compressed using zlib.\n" + compress(b"index std:doc -1 index.html Demo\n")
)
intersphinx_mapping = {"demo": ("https://example.org/demo/", str(_INVENTORY))}


def typehints_formatter(annotation: Any, config: Config) -> str | None:  # ruff:ignore[unused-function-argument]
    """Render one annotation as an intersphinx role, which the type role parses on its own."""
    return ":external+demo:doc:`the demo docs <index>`" if annotation is bool else None
