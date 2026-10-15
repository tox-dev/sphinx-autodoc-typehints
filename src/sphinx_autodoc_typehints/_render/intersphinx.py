"""The inventories intersphinx loaded, and the documented name of each class an inventory lists under another path."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import Inventory


# underscored, so the config pickled with the environment leaves the mapping out
_TYPE_MAPPING: Final[str] = "_intersphinx_type_mapping"


def keep_type_mapping(config: Config, env: BuildEnvironment) -> None:
    """
    Keep on `config`, where rendering reads it, the documented intersphinx name of each internal path.

    An internal path is the `__module__.__qualname__` an inventory entry reports. Leave out a path some inventory
    documents under its own name, and keep an empty mapping without intersphinx.
    """
    all_documented: set[str] = set()
    candidates: list[tuple[str, str]] = []
    for role in frozenset({"py:class", "py:function", "py:exception", "py:data"}):
        if (entries := inventory(env).get(role)) is None:
            continue
        for documented_name in entries:
            all_documented.add(documented_name)
            mod_path, _, attr_name = documented_name.rpartition(".")
            if not mod_path:
                all_documented.add(f"builtins.{documented_name}")
                continue
            try:
                obj = getattr(import_module(mod_path), attr_name)
                internal_path = f"{obj.__module__}.{obj.__qualname__}"
            except Exception:  # ruff:ignore[blind-except]  # an import or an attribute read runs user code
                internal_path = None
            # a union reports the path of its class, types.UnionType or typing.Union, and mapping that one path would
            # retarget every union
            if internal_path is not None and internal_path not in {"types.UnionType", "typing.Union", documented_name}:
                candidates.append((internal_path, documented_name))
    setattr(
        config,
        _TYPE_MAPPING,
        {internal: documented for internal, documented in candidates if internal not in all_documented},
    )


def inventory(env: BuildEnvironment | None) -> Inventory:
    """Return the inventories intersphinx loaded into `env`, empty without intersphinx or an environment."""
    return getattr(env, "intersphinx_inventory", None) or {}


def type_mapping(config: Config) -> dict[str, str]:
    """Return the mapping kept on `config`, empty before a build reads its inventories."""
    return getattr(config, _TYPE_MAPPING, None) or {}


__all__ = [
    "inventory",
    "keep_type_mapping",
    "type_mapping",
]
