from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Literal, NewType, TypeVar

import pytest
from conftest import normalize_sphinx_text

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

T = TypeVar("T")
W = NewType("W", str)


def expected(expected: str, **options: Any) -> Callable[[T], T]:
    def dec(val: T) -> T:
        val.EXPECTED = expected  # ty: ignore[unresolved-attribute]
        val.OPTIONS = options  # ty: ignore[unresolved-attribute]
        return val

    return dec


ArrayLike = Literal["test"]


class _SchemaMeta(type):  # noqa: PLW1641
    def __eq__(cls, other: object) -> bool:
        return True


class Schema(metaclass=_SchemaMeta):
    pass


@expected(
    """
mod.f(s)

   Do something.

   Parameters:
      **s** ("Schema") -- Some schema.

   Return type:
      "Schema"
"""
)
def f(s: Schema) -> Schema:
    """
    Do something.

    Args:
        s: Some schema.
    """


class AliasedClass: ...


@expected(
    """
mod.g(s)

   Do something.

   Parameters:
      **s** ("Class Alias") -- Some schema.

   Return type:
      "Class Alias"
"""
)
def g(s: AliasedClass) -> AliasedClass:
    """
    Do something.

    Args:
        s: Some schema.
    """


@expected(
    f"""\
mod.function(x, y)

   Function docstring.

   Parameters:
      * **x** ({'Array | "None"' if sys.version_info >= (3, 14) else '"Optional"[Array]'}) -- foo

      * **y** ("Schema") -- boo

   Returns:
      something

   Return type:
      bytes

""",
)
def function(x: ArrayLike | None, y: Schema) -> str:
    """
    Function docstring.

    :param x: foo
    :param y: boo
    :return: something
    :rtype: bytes
    """


# Config settings for each test run.
# Config Name: Sphinx Options as Dict.
configs = {"default_conf": {"autodoc_type_aliases": {"ArrayLike": "Array", "AliasedClass": '"Class Alias"'}}}


@pytest.mark.parametrize("val", [x for x in globals().values() if hasattr(x, "EXPECTED")])
@pytest.mark.parametrize("conf_run", list(configs.keys()))
@pytest.mark.sphinx("text", testroot="integration")
def test_integration(
    app: SphinxTestApp, status: StringIO, warning: StringIO, monkeypatch: pytest.MonkeyPatch, val: Any, conf_run: str
) -> None:
    template = ".. autofunction:: mod.{}"

    (Path(app.srcdir) / "index.rst").write_text(template.format(val.__name__))
    app.config.__dict__.update(configs[conf_run])
    app.config.__dict__.update(val.OPTIONS)
    monkeypatch.setitem(sys.modules, "mod", sys.modules[__name__])
    app.build()
    assert "build succeeded" in status.getvalue()  # Build succeeded

    value = warning.getvalue().strip()
    assert not value or "Inline strong start-string without end-string" in value

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())

    expected = dedent(normalize_sphinx_text(val.EXPECTED)).strip()
    assert result.strip() == expected
