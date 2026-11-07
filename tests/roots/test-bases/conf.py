from __future__ import annotations

from pathlib import Path
from sys import path
from typing import Final

path.insert(0, str(Path(__file__).parent))

master_doc: Final[str] = "index"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
]
autodoc_mock_imports = ["bases_dependency"]
