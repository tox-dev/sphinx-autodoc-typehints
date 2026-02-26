from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, TypeVar, Union
from unittest.mock import MagicMock

import pytest
from conftest import normalize_sphinx_text
from sphinx.util.inspect import TypeAliasForwardRef

from sphinx_autodoc_typehints import format_annotation

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

T = TypeVar("T")

UserId = Union[int, str]
RequestData = dict[str, Any]

TYPE_PREAMBLE = """\
type mod.UserId

   A user identifier that can be either an integer or a string.

type mod.RequestData

   Request data dictionary.

"""


def expected(expected: str, **options: Any) -> Callable[[T], T]:
    def dec(val: T) -> T:
        val.EXPECTED = expected  # ty: ignore[unresolved-attribute]
        val.OPTIONS = options  # ty: ignore[unresolved-attribute]
        return val

    return dec


@expected(
    TYPE_PREAMBLE
    + """\
mod.get_user(user_id)

   Get a user by ID.

   Parameters:
      **user_id** ("UserId") -- The user identifier

   Return type:
      "str"
"""
)
def get_user(user_id: UserId) -> str:
    """
    Get a user by ID.

    Args:
        user_id: The user identifier
    """


@expected(
    TYPE_PREAMBLE
    + """\
mod.process_request(data)

   Process a request.

   Parameters:
      **data** ("RequestData") -- The request data

   Return type:
      "bool"
"""
)
def process_request(data: RequestData) -> bool:
    """
    Process a request.

    Args:
        data: The request data
    """


configs = {"default_conf": {}}


@pytest.mark.parametrize("val", [x for x in globals().values() if hasattr(x, "EXPECTED")])
@pytest.mark.parametrize("conf_run", list(configs.keys()))
@pytest.mark.sphinx("text", testroot="issue_599")
def test_integration(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    monkeypatch: pytest.MonkeyPatch,
    val: Any,
    conf_run: str,
) -> None:
    template = """\
.. py:type:: mod.UserId

   A user identifier that can be either an integer or a string.

.. py:type:: mod.RequestData

   Request data dictionary.

.. autofunction:: mod.{}
"""

    (Path(app.srcdir) / "index.rst").write_text(template.format(val.__name__))
    app.config.__dict__.update(configs[conf_run])
    app.config.__dict__.update(val.OPTIONS)
    monkeypatch.setitem(sys.modules, "mod", sys.modules[__name__])
    app.build()
    assert "build succeeded" in status.getvalue()

    value = warning.getvalue().strip()
    assert not value or "Inline strong start-string without end-string" in value

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())

    expected_text = dedent(normalize_sphinx_text(val.EXPECTED)).strip()
    assert result.strip() == expected_text


@pytest.mark.sphinx("text", testroot="issue_599")
def test_eager_annotations(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
) -> None:
    """Test that non-deferred annotations (no ``from __future__ import annotations``) also resolve."""
    template = """\
.. py:type:: mod_eager.UserId

   A user identifier.

.. autofunction:: mod_eager.get_user_eager
"""
    (Path(app.srcdir) / "index.rst").write_text(template)
    app.build()
    assert "build succeeded" in status.getvalue()

    value = warning.getvalue().strip()
    assert not value or "Inline strong start-string without end-string" in value

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert '"UserId"' in result


def test_format_annotation_type_alias_without_env() -> None:
    """TypeAliasForwardRef falls back to plain name when no env is available."""
    config = MagicMock()
    config.typehints_formatter = None
    del config._typehints_env  # noqa: SLF001
    annotation = TypeAliasForwardRef("SomeAlias")
    assert format_annotation(annotation, config) == "SomeAlias"
