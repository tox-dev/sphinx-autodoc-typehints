from __future__ import annotations

import threading
from typing import Any
from unittest.mock import MagicMock, create_autospec

from sphinx.config import Config

from sphinx_autodoc_typehints import format_annotation
from sphinx_autodoc_typehints._intersphinx import build_type_mapping


def _make_env(inventory_data: dict[str, dict[str, object]] | None = None) -> MagicMock:
    env = MagicMock()
    if inventory_data is None:
        del env.intersphinx_inventory
    else:
        env.intersphinx_inventory.data = inventory_data
    return env


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
