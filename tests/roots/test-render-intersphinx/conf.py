from __future__ import annotations

from pathlib import Path
from sys import path
from typing import Final

master_doc: Final[str] = "index"
path.insert(0, str(Path(__file__).parent))
extensions = [
    "sphinx.ext.intersphinx",
]
