from __future__ import annotations

import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

master_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

# a hand-rolled inventory keeps the fixture offline; it documents the class under the name remote re-exports it as
_INVENTORY = pathlib.Path(__file__).parent / "objects.inv"
_INVENTORY.write_bytes(
    b"# Sphinx inventory version 2\n"
    b"# Project: remote\n"
    b"# Version: 1.0\n"
    b"# The remainder of this file is compressed using zlib.\n"
    + zlib.compress(b"remote.Widget py:class 1 api.html#$ -\n")
)
intersphinx_mapping = {"remote": ("https://example.org/remote/", str(_INVENTORY))}
