from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from conftest import pytest_ignore_collect

if TYPE_CHECKING:
    from pathlib import Path


def test_ignore_collect_skips_future_python_version(tmp_path: Path) -> None:
    path = tmp_path / "test_something_py99.py"
    assert pytest_ignore_collect(path, MagicMock()) is True  # ty: ignore[invalid-argument-type]


def test_ignore_collect_allows_current_or_past_version(tmp_path: Path) -> None:
    path = tmp_path / "test_something_py30.py"
    assert pytest_ignore_collect(path, MagicMock()) is None  # ty: ignore[invalid-argument-type]


def test_ignore_collect_ignores_non_versioned_files(tmp_path: Path) -> None:
    path = tmp_path / "test_regular.py"
    assert pytest_ignore_collect(path, MagicMock()) is None  # ty: ignore[invalid-argument-type]
