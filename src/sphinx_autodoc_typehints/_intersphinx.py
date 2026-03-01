"""Build a reverse mapping from runtime type paths to intersphinx-documented paths."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sphinx.environment import BuildEnvironment

_ROLES = frozenset({"py:class", "py:function", "py:exception", "py:data"})


def build_type_mapping(env: BuildEnvironment) -> dict[str, str]:
    """Map internal ``__module__.__qualname__`` paths to their documented intersphinx names."""
    if not hasattr(env, "intersphinx_inventory"):
        return {}

    inventory_data: dict[str, dict[str, object]] = env.intersphinx_inventory  # ty: ignore[invalid-assignment]
    all_documented: set[str] = set()
    candidates: list[tuple[str, str]] = []

    for role in _ROLES:
        if (entries := inventory_data.get(role)) is None:
            continue
        for documented_name in entries:
            all_documented.add(documented_name)
            mod_path, _, attr_name = documented_name.rpartition(".")
            if not mod_path:
                continue
            try:
                mod = importlib.import_module(mod_path)
                obj = getattr(mod, attr_name)
                internal_path = f"{obj.__module__}.{obj.__qualname__}"
            except Exception:  # noqa: BLE001, S112
                continue
            if internal_path != documented_name:
                candidates.append((internal_path, documented_name))

    return {internal: documented for internal, documented in candidates if internal not in all_documented}
