"""PyO3-shaped reproduction package for discussion #698."""

from __future__ import annotations  # simplint: ignore[SMP407]  # tests read the names from the package itself

from . import _native  # ruff:ignore[unused-import]  # importing the compiled module makes the package load it  # simplint: ignore[SMP407]  # tests read the names from the package itself
from . import warc as warc  # simplint: ignore[SMP407]  # tests read the names from the package itself
