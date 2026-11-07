from __future__ import annotations

from pathlib import Path
from sys import path
from typing import Final

path.insert(0, str(Path(__file__).parent))

master_doc: Final[str] = "index"
extensions = [
    "sphinx.ext.autodoc",
    "numpydoc",
    "sphinx_autodoc_typehints",
]
numpydoc_show_class_members: Final[bool] = False
