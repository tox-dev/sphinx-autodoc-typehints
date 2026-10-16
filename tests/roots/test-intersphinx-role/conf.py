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

# the Python docs list types.FunctionType as py:data up to 3.12 and as py:class from 3.13 on; a test picks which
# version's inventory to link against by pointing intersphinx_mapping at one of these offline files
for _role in ("class", "data"):
    (Path(__file__).parent / f"{_role}.inv").write_bytes(
        b"# Sphinx inventory version 2\n"
        b"# Project: Python\n"
        b"# Version: 3\n"
        b"# The remainder of this file is compressed using zlib.\n"
        + compress(f"types.FunctionType py:{_role} 1 library/types.html#$ -\n".encode())
    )
