from __future__ import annotations

from typing import Final

_MSG: Final[str] = "this module fails to import"
raise RuntimeError(_MSG)
