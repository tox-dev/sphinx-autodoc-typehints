from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

master_doc = "index"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
]
