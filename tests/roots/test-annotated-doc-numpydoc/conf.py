from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

master_doc = "index"
extensions = [
    "sphinx.ext.autodoc",
    "numpydoc",
    "sphinx_autodoc_typehints",
]
numpydoc_show_class_members = False
