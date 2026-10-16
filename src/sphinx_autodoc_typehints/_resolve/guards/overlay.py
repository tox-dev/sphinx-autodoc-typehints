"""
The TYPE_CHECKING overlay, laying what the guard of a module binds over its globals where annotations evaluate.

Autodoc lists module members, so the names stay out of the module.
"""

from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from typing import TYPE_CHECKING, Final

from sphinx_autodoc_typehints._objects import defining_module

if TYPE_CHECKING:
    from collections.abc import Generator

    from sphinx_autodoc_typehints._types import Documented


#: Per module, what its `TYPE_CHECKING` block binds a name to that the module lacks or binds to something else at
#: runtime; kept out of the module, where autodoc would list a name it lacks as a member.
SHADOWED_BY_GUARD: Final[dict[str, dict[str, Documented]]] = {}


def annotation_globals(obj: Documented) -> dict[str, Documented]:
    """
    Return the globals the annotations of `obj` evaluate in, read as a type checker reads them.

    Generated code such as an attrs `__init__` runs in a globals dict of its own, which misses the names the module
    binds afterwards, so the module's names fill the gaps.
    """
    if (module := defining_module(obj)) is None:
        return getattr(obj, "__globals__", {})
    own = getattr(obj, "__globals__", vars(module))
    names = own if own is vars(module) else {**vars(module), **own}
    return {**names, **shadowed} if (shadowed := guarded_names(obj)) else names


def guarded_names(obj: Documented) -> dict[str, Documented]:
    """Return what the `TYPE_CHECKING` block of the module of `obj` binds the names it lacks or rebinds to."""
    if not (module := defining_module(obj)):
        return {}
    return {name: _as_guarded(value) for name, value in SHADOWED_BY_GUARD.get(module.__name__, {}).items()}


def _as_guarded(value: Documented) -> Documented:
    return _GuardedModule(value) if isinstance(value, ModuleType) else value


# reads `_t.Alias` as a type checker does, where only the guard binds `Alias`
class _GuardedModule:
    def __init__(self, module: ModuleType) -> None:
        self._module = module

    def __getattr__(self, name: str) -> Documented:
        if name in (guarded := SHADOWED_BY_GUARD.get(self._module.__name__, {})):
            return _as_guarded(guarded[name])
        return _as_guarded(getattr(self._module, name))


@contextmanager
def guarded_names_bound(obj: Documented) -> Generator[None]:
    """
    Bind the names the guards of the modules defining `obj` and its bases add, only while the block runs.

    What evaluates in the globals of the module itself reads them nowhere else, as autodoc evaluating an annotation and
    the value of a `type` alias do. A name the module binds at runtime keeps that binding.
    """
    added: list[tuple[dict[str, Documented], dict[str, Documented]]] = []
    owners = obj.__mro__ if isinstance(obj, type) else (obj,)
    for module in {module for owner in owners if (module := defining_module(owner))}:
        namespace = vars(module)
        missing = {name: value for name, value in guarded_names(module).items() if name not in namespace}
        namespace.update(missing)
        added.append((namespace, missing))
    try:
        yield
    finally:
        for namespace, missing in added:
            for name, value in missing.items():
                if namespace.get(name) is value:
                    del namespace[name]


__all__ = [
    "SHADOWED_BY_GUARD",
    "annotation_globals",
    "guarded_names",
    "guarded_names_bound",
]
