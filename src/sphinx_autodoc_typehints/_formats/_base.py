"""Abstract base class for docstring format handlers and shared types used across all format implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sphinx.application import Sphinx


@dataclass
class InsertIndexInfo:
    insert_index: int
    found_param: bool = False
    found_return: bool = False
    found_directive: bool = False


class DocstringFormat(ABC):
    @staticmethod
    @abstractmethod
    def detect(lines: list[str]) -> bool:
        """Return True if lines are in this format."""

    @abstractmethod
    def find_param(self, lines: list[str], arg_name: str) -> int | None:
        """Find the line index where arg_name is documented."""

    @abstractmethod
    def inject_param_type(self, lines: list[str], arg_name: str, formatted_type: str, at: int) -> None:
        """Insert type annotation for a parameter at the given index."""

    @abstractmethod
    def add_undocumented_param(self, lines: list[str], arg_name: str) -> int:
        """Add a :param: line for an undocumented parameter, return its index."""

    @abstractmethod
    def find_preexisting_type(self, lines: list[str], arg_name: str) -> tuple[str, bool]:
        """Check if a type annotation already exists for arg_name."""

    @abstractmethod
    def get_rtype_insert_info(self, app: Sphinx, lines: list[str]) -> InsertIndexInfo | None:
        """Find where to insert return type information."""

    @abstractmethod
    def inject_rtype(
        self,
        lines: list[str],
        formatted_annotation: str,
        info: InsertIndexInfo,
        *,
        use_rtype: bool,
    ) -> None:
        """Insert return type annotation."""

    @abstractmethod
    def append_default(
        self,
        lines: list[str],
        insert_index: int,
        type_annotation: str,
        formatted_default: str,
        *,
        after: bool,
    ) -> str:
        """Append a default value to a parameter annotation, return the (possibly modified) type_annotation."""
