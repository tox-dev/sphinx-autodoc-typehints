"""PyO3-shaped reproduction package for discussion #698."""

from __future__ import annotations

from . import _native  # ruff:ignore[unused-import]  # importing the compiled module makes the package load it
from . import warc as warc
