"""The inventories intersphinx loaded, and the documented name of each class an inventory lists under another path."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from importlib import import_module
from sys import modules
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import Inventory


# underscored, so the config pickled with the environment leaves the mapping out
_TYPE_MAPPING: Final[str] = "_intersphinx_type_mapping"
# a union reports the path of its class, `types.UnionType` or `typing.Union`, and mapping that one path would retarget
# every union
_UNION_PATHS: Final[frozenset[str]] = frozenset({"types.UnionType", "typing.Union"})


@dataclass(frozen=True, slots=True, kw_only=True)
class _TypeMapping:
    documented: set[str] = field(default_factory=set)
    rank: dict[str, int] = field(default_factory=dict)
    modules_by_leaf: dict[str, dict[str, None]] = field(default_factory=dict)
    unread: dict[str, list[str]] = field(default_factory=dict)
    found: dict[str, str] = field(default_factory=dict)
    answers: dict[str, str | None] = field(default_factory=dict)

    def lookup(self, internal_path: str) -> str | None:
        if internal_path in self.documented:
            return None
        if internal_path not in self.answers:
            # importing a module runs its code, so import only those listing a name with the same leaf, and find an
            # object documented under another leaf, such as `threading.local`, in the modules already imported
            for module_name in self.modules_by_leaf.get(internal_path.rpartition(".")[2], {}):
                # an import runs user code, which may raise anything
                with suppress(Exception):
                    import_module(module_name)
            self._read_imported()
            # kept, so a module imported later cannot change the name a type already rendered with
            self.answers[internal_path] = self.found.get(internal_path)
        return self.answers[internal_path]

    def _read_imported(self) -> None:
        for module_name in [name for name in self.unread if name in modules]:
            module = modules[module_name]
            for documented_name in self.unread.pop(module_name):
                try:
                    obj = getattr(module, documented_name.rpartition(".")[2])
                    internal_path = f"{obj.__module__}.{obj.__qualname__}"
                except Exception:  # ruff:ignore[blind-except]  # an attribute read runs user code
                    internal_path = None
                if internal_path is None or internal_path in _UNION_PATHS or internal_path == documented_name:
                    continue
                # the earliest role wins, so a class an inventory also lists as data links to its class entry
                if (kept := self.found.get(internal_path)) is None or self.rank[documented_name] < self.rank[kept]:
                    self.found[internal_path] = documented_name


def keep_type_mapping(config: Config, env: BuildEnvironment) -> None:
    """
    Keep on `config`, where rendering reads it, the documented intersphinx name of each internal path.

    An internal path is the `__module__.__qualname__` an inventory entry reports. Leave out a path some inventory
    documents under its own name, and keep an empty mapping without intersphinx. Index the entries without importing
    anything, `mapped_name` imports a module only once a rendered type may be listed in it.
    """
    mapping = _TypeMapping()
    # a fixed role order, so the documented name an internal path maps to does not follow string hash order
    for role in ("py:class", "py:function", "py:exception", "py:data"):
        for documented_name in inventory(env).get(role, {}):
            mapping.documented.add(documented_name)
            mod_path, _, attr_name = documented_name.rpartition(".")
            if not mod_path:
                mapping.documented.add(f"builtins.{documented_name}")
            elif documented_name not in mapping.rank:
                mapping.rank[documented_name] = len(mapping.rank)
                mapping.modules_by_leaf.setdefault(attr_name, {})[mod_path] = None
                mapping.unread.setdefault(mod_path, []).append(documented_name)
    setattr(config, _TYPE_MAPPING, mapping)


def inventory(env: BuildEnvironment | None) -> Inventory:
    """Return the inventories intersphinx loaded into `env`, empty without intersphinx or an environment."""
    return getattr(env, "intersphinx_inventory", None) or {}


def mapped_name(config: Config, internal_path: str) -> str | None:
    """Return the documented name of `internal_path`, `None` when no inventory lists it elsewhere or before a build."""
    if (mapping := getattr(config, _TYPE_MAPPING, None)) is None:
        return None
    return mapping.lookup(internal_path)


__all__ = [
    "inventory",
    "keep_type_mapping",
    "mapped_name",
]
