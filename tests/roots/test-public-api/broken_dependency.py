from __future__ import annotations

from typing import Final

msg: Final[str] = "this module fails to import"
raise RuntimeError(msg)
