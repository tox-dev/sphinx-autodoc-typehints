from __future__ import annotations

import pathlib
import sys

master_doc = "index"
sys.path.insert(0, str(pathlib.Path(__file__).parent))
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
]
