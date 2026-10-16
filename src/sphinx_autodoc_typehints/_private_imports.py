"""Foundation module importing the private and undocumented names the extension reads from its dependencies."""

from __future__ import annotations

# ruff:ignore[import-private-name]  # no public name
from dataclasses import (
    _HAS_DEFAULT_FACTORY as HAS_DEFAULT_FACTORY,  # ty: ignore[unresolved-import]  # typeshed leaves it out
)
from typing import Final

from sphinx.domains.python._annotations import (  # ruff:ignore[import-private-name]  # Sphinx has no public parser
    _parse_annotation as parse_annotation,
)
from sphinx.domains.python._annotations import (  # ruff:ignore[import-private-name]  # Sphinx has no public parser
    _parse_type_list as parse_type_list,
)
from sphinx.pycode.parser import VariableCommentPicker  # undocumented, yet the only reader of `#:` comments
from sphinx.util.docutils import sphinx_domains  # undocumented, yet the only way to parse reST with Sphinx's roles
from sphinx.util.logging import suppress_logging  # undocumented, yet the only way to silence a trial parse

try:
    from sphinx.ext.autodoc._dynamic._signatures import (
        _METACLASS_CALL_BLACKLIST as METACLASS_CALL_BLACKLIST,
    )
except ImportError:  # Sphinx moves its private autodoc modules between releases, so keep loading with 9.1's value
    METACLASS_CALL_BLACKLIST: Final[frozenset[str]] = frozenset({"enum.EnumType.__call__"})

__all__ = [
    "HAS_DEFAULT_FACTORY",
    "METACLASS_CALL_BLACKLIST",
    "VariableCommentPicker",
    "parse_annotation",
    "parse_type_list",
    "sphinx_domains",
    "suppress_logging",
]
