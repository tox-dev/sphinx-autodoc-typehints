from __future__ import annotations

from pathlib import Path
from sys import path
from zlib import compress

path.insert(0, str(Path(__file__).parent))

master_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]

# an offline stand-in for the inventory of the Python docs, listing the types a return type of the stubs uses
(Path(__file__).parent / "python.inv").write_bytes(
    b"# Sphinx inventory version 2\n"
    b"# Project: Python\n"
    b"# Version: 3\n"
    b"# The remainder of this file is compressed using zlib.\n"
    + compress(b"list py:class 1 library/stdtypes.html#$ -\nstr py:class 1 library/stdtypes.html#$ -\n")
)
intersphinx_mapping = {"python": ("https://docs.python.org/3", "python.inv")}
