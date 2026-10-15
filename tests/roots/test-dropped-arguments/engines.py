"""A class whose subscription hands back the class itself, as SQLAlchemy's TypeEngine does."""

from __future__ import annotations

from typing import Any


class Engine:
    """An engine."""

    def __class_getitem__(cls, item: Any) -> type[Engine]:
        return cls
