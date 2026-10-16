from __future__ import annotations

from pathlib import Path
from sys import path

path.insert(0, str(Path(__file__).parent))

master_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]
intersphinx_mapping: dict[str, tuple[str, str]] = {}
