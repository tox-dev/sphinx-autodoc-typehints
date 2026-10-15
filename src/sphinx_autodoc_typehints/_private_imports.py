"""Foundation module importing the private names the extension reads from its dependencies and the standard library."""

from __future__ import annotations

# ruff:ignore[import-private-name]  # no public name
from dataclasses import (
    _HAS_DEFAULT_FACTORY as HAS_DEFAULT_FACTORY,  # ty: ignore[unresolved-import]  # typeshed leaves it out
)
from typing import Final

from docutils.parsers.rst import directives
from sphinx.domains.python._annotations import (  # ruff:ignore[import-private-name]  # Sphinx has no public parser
    _parse_annotation as parse_annotation,
)
from sphinx.domains.python._annotations import (  # ruff:ignore[import-private-name]  # Sphinx has no public parser
    _parse_type_list as parse_type_list,
)
from sphinx.locale import _ as translate  # ruff:ignore[import-private-name]  # Sphinx's own translations
from sphinx.util.typing import (
    _INVALID_BUILTIN_CLASSES as INVALID_BUILTIN_CLASSES,  # ruff:ignore[import-private-name]  # no public name
)

try:
    from sphinx.ext.autodoc._dynamic._signatures import (
        _METACLASS_CALL_BLACKLIST as METACLASS_CALL_BLACKLIST,
    )
except ImportError:  # Sphinx moves its private autodoc modules between releases, so keep loading with 9.1's value
    METACLASS_CALL_BLACKLIST: Final[frozenset[str]] = frozenset({"enum.EnumType.__call__"})

#: the directives docutils defines, which a docstring parse may run, unlike those of Sphinx and its extensions
BUILTIN_DIRECTIVES: Final[frozenset[str]] = frozenset(
    directives._directive_registry  # ruff:ignore[private-member-access]  # docutils has no public listing
)

__all__ = [
    "BUILTIN_DIRECTIVES",
    "HAS_DEFAULT_FACTORY",
    "INVALID_BUILTIN_CLASSES",
    "METACLASS_CALL_BLACKLIST",
    "parse_annotation",
    "parse_type_list",
    "translate",
]
