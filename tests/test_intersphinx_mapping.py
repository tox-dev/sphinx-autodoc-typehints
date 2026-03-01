from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import create_autospec

from sphinx.config import Config

from sphinx_autodoc_typehints import format_annotation
from sphinx_autodoc_typehints._intersphinx import build_type_mapping

if TYPE_CHECKING:
    from sphinx.environment import BuildEnvironment


def _make_env(inventory_data: dict[str, dict[str, object]] | None = None) -> BuildEnvironment:
    if inventory_data is None:
        return cast("BuildEnvironment", SimpleNamespace())
    return cast("BuildEnvironment", SimpleNamespace(intersphinx_inventory=inventory_data))


def test_build_type_mapping_threading_local() -> None:
    inventory_data: dict[str, dict[str, Any]] = {
        "py:class": {"threading.local": ("", "", "", "")},
    }
    result = build_type_mapping(_make_env(inventory_data))
    assert result["_thread._local"] == "threading.local"


def test_build_type_mapping_no_intersphinx_inventory() -> None:
    assert build_type_mapping(_make_env()) == {}


def test_build_type_mapping_skips_already_documented() -> None:
    inventory_data: dict[str, dict[str, Any]] = {
        "py:class": {
            "threading.local": ("", "", "", ""),
            "_thread._local": ("", "", "", ""),
        },
    }
    result = build_type_mapping(_make_env(inventory_data))
    assert "_thread._local" not in result


def test_build_type_mapping_skips_unimportable() -> None:
    inventory_data: dict[str, dict[str, Any]] = {
        "py:class": {"nonexistent_module.SomeClass": ("", "", "", "")},
    }
    assert build_type_mapping(_make_env(inventory_data)) == {}


def test_build_type_mapping_skips_missing_attr() -> None:
    inventory_data: dict[str, dict[str, Any]] = {
        "py:class": {"threading.NoSuchAttribute": ("", "", "", "")},
    }
    assert build_type_mapping(_make_env(inventory_data)) == {}


def test_build_type_mapping_skips_same_path() -> None:
    inventory_data: dict[str, dict[str, Any]] = {
        "py:class": {"int": ("", "", "", "")},
    }
    result = build_type_mapping(_make_env(inventory_data))
    assert "builtins.int" not in result


def test_build_type_mapping_multiple_roles() -> None:
    inventory_data: dict[str, dict[str, Any]] = {
        "py:class": {"threading.local": ("", "", "", "")},
        "py:function": {},
        "py:exception": {},
    }
    result = build_type_mapping(_make_env(inventory_data))
    assert result["_thread._local"] == "threading.local"


def test_format_annotation_applies_intersphinx_mapping() -> None:
    conf = create_autospec(
        Config,
        _intersphinx_type_mapping={"_thread._local": "threading.local"},
        always_use_bars_union=False,
    )
    result = format_annotation(threading.local, conf)
    assert result == ":py:class:`~threading.local`"


def test_format_annotation_without_mapping() -> None:
    conf = create_autospec(Config, always_use_bars_union=False)
    result = format_annotation(threading.local, conf)
    assert result == ":py:class:`~_thread._local`"
