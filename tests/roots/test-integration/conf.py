from __future__ import annotations

import pathlib
import sys

# Make dummy_module.py available for autodoc.
sys.path.insert(0, str(pathlib.Path(__file__).parent))


master_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]
