from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import attr
import attrs
import pytest
from conftest import normalize_sphinx_text

from sphinx_autodoc_typehints._resolver._attrs import backfill_attrs_annotations

if TYPE_CHECKING:
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

ATTRS_ROOT = Path(__file__).parent.parent / "roots" / "test-attrs"


@attr.s
class _ClassicAttrs:
    name = attr.ib(type=str)
    age = attr.ib(type=int)
    untyped = attr.ib()


@attr.s(auto_attribs=True)
class _AutoAttribs:
    name: str
    age: int


@attrs.define
class _ModernAttrs:
    name: str
    age: int


def test_backfill_classic_attrs() -> None:
    backfill_attrs_annotations(_ClassicAttrs)
    annotations = _ClassicAttrs.__annotations__
    assert annotations["name"] is str
    assert annotations["age"] is int
    assert "untyped" not in annotations


def test_backfill_does_not_override_existing_annotations() -> None:
    original = _AutoAttribs.__annotations__.copy()
    backfill_attrs_annotations(_AutoAttribs)
    assert _AutoAttribs.__annotations__ == original


def test_backfill_modern_attrs() -> None:
    original = _ModernAttrs.__annotations__.copy()
    backfill_attrs_annotations(_ModernAttrs)
    assert _ModernAttrs.__annotations__ == original


def test_backfill_non_attrs_class() -> None:
    class Plain:
        pass

    backfill_attrs_annotations(Plain)
    assert not hasattr(Plain, "__annotations__") or Plain.__annotations__ == {}


def test_backfill_without_attrs_installed() -> None:
    saved = sys.modules.copy()
    sys.modules["attrs"] = None  # type: ignore[assignment]
    try:

        class Dummy:
            pass

        backfill_attrs_annotations(Dummy)
    finally:
        sys.modules.update(saved)


def test_backfill_classic_attrs_creates_annotations_when_missing() -> None:
    @attr.s
    class NoAnnotations:
        x = attr.ib(type=int)

    NoAnnotations.__annotations__ = None  # type: ignore[assignment]
    backfill_attrs_annotations(NoAnnotations)
    assert NoAnnotations.__annotations__["x"] is int


@pytest.mark.sphinx("text", testroot="attrs")
def test_sphinx_build_nested_attrs_forward_ref(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    template = """\
.. autoclass:: attrs_mod.Outer
   :members:
   :undoc-members:

.. autoclass:: attrs_mod.Outer.Bar
   :members:
   :undoc-members:
"""
    (Path(app.srcdir) / "index.rst").write_text(template)
    app.build()
    assert "build succeeded" in status.getvalue()
    assert "Foo" in normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert "forward reference" not in warning.getvalue()


@pytest.mark.sphinx("text", testroot="attrs")
def test_sphinx_build_attrs_types(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    template = """\
.. autoclass:: attrs_mod.ClassicAttrs
   :members:
   :undoc-members:

.. autoclass:: attrs_mod.AutoAttribs
   :members:
   :undoc-members:

.. autoclass:: attrs_mod.ModernAttrs
   :members:
   :undoc-members:
"""
    (Path(app.srcdir) / "index.rst").write_text(template)
    app.build()
    assert "build succeeded" in status.getvalue()
    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    assert "str" in result
    assert "int" in result
    warn_text = warning.getvalue()
    assert "attrs_mod" not in warn_text or "forward reference" not in warn_text
