from __future__ import annotations

from pathlib import Path
from sys import path

master_doc = "index"
path.insert(0, str(Path(__file__).parent))
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
]
