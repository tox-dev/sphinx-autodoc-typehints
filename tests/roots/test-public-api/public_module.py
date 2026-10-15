from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import broken_dependency  # a guarded import of a module that fails to import is the case under test


def unparseable_comment(value):
    # type: (int) int
    """Unparsable."""


one_of_two = lambda value: value; second = 1  # fmt: skip


def forward_reference(value: Undefined) -> None:
    """Forward."""


def _make() -> type:
    class Local:
        def method(self, value: int) -> int:
            """Local."""
            return value

    return Local


Exported = _make()


def count(value: int, label: str) -> int:
    """
    Count.

    :param value: the value
    :param label: the label
    """
    return value + len(label)
