from __future__ import annotations

from pathlib import Path
from sys import path
from typing import Final

# Make dummy_module.py available for autodoc.
path.insert(0, str(Path(__file__).parent))


master_doc: Final[str] = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]
