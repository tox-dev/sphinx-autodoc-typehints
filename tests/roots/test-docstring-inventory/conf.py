from __future__ import annotations

from pathlib import Path
from sys import path
from zlib import compress

path.insert(0, str(Path(__file__).parent))

master_doc = "index"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

# an inventory listing types.ModuleType as data, the role the Python 3.12 docs give it, kept offline
_INVENTORY = Path(__file__).parent / "objects.inv"
_INVENTORY.write_bytes(
    b"# Sphinx inventory version 2\n"
    b"# Project: Python\n"
    b"# Version: 3.12\n"
    b"# The remainder of this file is compressed using zlib.\n"
    + compress(b"types.ModuleType py:data 1 library/types.html#$ -\n")
)
intersphinx_mapping = {"python": ("https://docs.python.org/3.12/", str(_INVENTORY))}
