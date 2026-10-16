from __future__ import annotations

from pathlib import Path
from sys import path

path.insert(0, str(Path(__file__).parent))

master_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "numpydoc",
    "sphinx_autodoc_typehints",
]
# Disable numpydoc's class members listing to avoid interfering with autodoc
numpydoc_show_class_members = False
