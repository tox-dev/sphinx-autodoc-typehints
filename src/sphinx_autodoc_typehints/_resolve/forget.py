"""Drop what the last build read from the stub files and the loaded modules, which may have changed since."""

from __future__ import annotations

__lazy_modules__ = [
    f"{__spec__.parent}.backfill.stubs.find",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
    f"{__spec__.parent}.guards.overlay",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
]

from .backfill.stubs.find import STUB_FILES
from .guards.overlay import SHADOWED_BY_GUARD


def forget_reads() -> None:
    SHADOWED_BY_GUARD.clear()
    STUB_FILES.clear()


__all__ = [
    "forget_reads",
]
