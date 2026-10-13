from __future__ import annotations

import importlib
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import attr
import attrs
import pytest
from conftest import make_docstring_app, normalize_sphinx_text

from sphinx_autodoc_typehints import process_docstring
from sphinx_autodoc_typehints._resolver._attrs import backfill_attrs_annotations

if TYPE_CHECKING:
    from collections.abc import Callable
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


@pytest.mark.parametrize(
    "header",
    [
        pytest.param("from __future__ import annotations\n", id="postponed"),
        pytest.param(
            "",
            id="lazy",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 14), reason="eager annotations cannot name a guarded import"
            ),
        ),
    ],
)
def test_process_docstring_types_attrs_field_from_guarded_import(
    attrs_module: Callable[[str], type], header: str, caplog: pytest.LogCaptureFixture
) -> None:
    price = attrs_module(
        f"{header}from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from decimal import Decimal\n"
    )
    lines = [":param amount: the amount"]
    process_docstring(make_docstring_app(), "class", f"{price.__module__}.Price", price, None, lines)
    assert (lines, [record for record in caplog.records if record.levelno == logging.WARNING]) == (
        [
            r":type amount: :sphinx_autodoc_typehints_type:`\:py\:class\:\`\~decimal.Decimal\``",
            ":param amount: the amount",
        ],
        [],
    )


@pytest.mark.skipif(sys.version_info < (3, 14), reason="eager annotations fail at import instead")
def test_process_docstring_survives_attrs_field_naming_nothing(
    attrs_module: Callable[[str], type],
) -> None:  # pragma: >=3.14 cover
    price = attrs_module("")
    lines = [":param amount: the amount"]
    process_docstring(make_docstring_app(), "class", f"{price.__module__}.Price", price, None, lines)
    assert lines == [":type amount: :sphinx_autodoc_typehints_type:`Decimal`", ":param amount: the amount"]


@pytest.fixture
def attrs_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Callable[[str], type]:
    monkeypatch.syspath_prepend(tmp_path)
    name = re.sub(r"\W", "_", request.node.name)

    def build(header: str) -> type:
        (tmp_path / f"{name}.py").write_text(
            f"{header}\nimport attrs\n\n\n@attrs.define\nclass Price:\n    amount: Decimal\n"
        )
        return importlib.import_module(name).Price

    return build
