from __future__ import annotations

from importlib import import_module
from sys import modules
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_metaclass_call_blacklist_keeps_the_value_of_sphinx_9_1_when_sphinx_moves_it(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delattr("sphinx.ext.autodoc._dynamic._signatures._METACLASS_CALL_BLACKLIST")
    monkeypatch.delitem(modules, "sphinx_autodoc_typehints._private_imports", raising=False)

    compat = import_module("sphinx_autodoc_typehints._private_imports")

    assert frozenset({"enum.EnumType.__call__"}) == compat.METACLASS_CALL_BLACKLIST
