from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sphinx import addnodes

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.testing.util import SphinxTestApp


@pytest.mark.parametrize(
    ("rst", "expected"),
    [
        pytest.param(".. autodata:: header_module.LIMIT", "header_module.LIMIT: int = 3", id="data"),
        pytest.param(".. autoattribute:: header_module.Account.balance", "Account.balance: Decimal", id="attribute"),
        pytest.param(".. autoproperty:: header_module.Account.total", "property Account.total: int", id="property"),
        pytest.param(
            ".. autoproperty:: header_module.Account.fee", "property Account.fee: Decimal", id="cached-property"
        ),
        pytest.param(
            ".. autoproperty:: header_module.Account.kind", "class property Account.kind: str", id="class-property"
        ),
        pytest.param(
            ".. autoattribute:: header_module.Account.owner",
            "Account.owner: str",
            id="instance-attribute",
        ),
        pytest.param(
            ".. py:data:: header_module.MANUAL\n   :type: Annotated[int, 'kept']",
            "header_module.MANUAL: Annotated[int, 'kept']",
            id="written-by-hand",
        ),
    ],
)
@pytest.mark.sphinx("text", testroot="headers")
def test_header_type_renders_like_a_field(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, expected: str
) -> None:
    write_rst(rst)
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text().splitlines()[0] == expected


@pytest.mark.sphinx("text", testroot="headers")
def test_header_type_links_a_type_checking_import(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autodata:: header_module.RATE")
    app.build()

    signature = next(app.env.get_doctree("index").findall(addnodes.desc_signature))
    assert [ref["reftarget"] for ref in signature.findall(addnodes.pending_xref)] == ["decimal.Decimal", "None"]


@pytest.mark.sphinx("text", testroot="headers", confoverrides={"typehints_fully_qualified": True})
def test_header_type_fully_qualified(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autodata:: header_module.RATE")
    app.build()

    header = (Path(app.outdir) / "index.txt").read_text().splitlines()[0]
    assert header == "header_module.RATE: decimal.Decimal | None = None"


@pytest.mark.parametrize(
    ("rst", "expected"),
    [
        pytest.param(".. autoattribute:: header_module.IntBox.value", "IntBox.value: int", id="annotation-only"),
        pytest.param(
            ".. autoattribute:: header_module.IntBox.label", "IntBox.label: tuple[int, ...] = ()", id="with-a-value"
        ),
        pytest.param(".. autoproperty:: header_module.IntBox.first", "property IntBox.first: int", id="property"),
        pytest.param(
            ".. autoattribute:: header_module.StrLegacy.items", "StrLegacy.items: list[str]", id="legacy-generic"
        ),
    ],
)
@pytest.mark.sphinx("text", testroot="headers")
def test_header_type_binds_an_inherited_type_parameter(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, expected: str
) -> None:
    write_rst(rst)
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text().splitlines()[0] == expected


@pytest.mark.parametrize(
    ("rst", "expected"),
    [
        pytest.param(".. autodata:: header_module.SCORE", "header_module.SCORE: Num = 1", id="data"),
        pytest.param(".. autoattribute:: header_module.Scored.points", "Scored.points: Num = 0", id="attribute"),
        pytest.param(".. autoproperty:: header_module.Scored.best", "property Scored.best: Num", id="property"),
        pytest.param(".. autoattribute:: header_module.Totals.count", "Totals.count: Num", id="typed-dict-key"),
    ],
)
@pytest.mark.sphinx("text", testroot="headers", confoverrides={"autodoc_type_aliases": {"Num": "header_module.Num"}})
def test_header_type_keeps_a_configured_alias(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, expected: str
) -> None:
    write_rst(rst)
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text().splitlines()[0] == expected


@pytest.mark.sphinx("text", testroot="headers")
def test_header_type_links_a_documented_alias(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. py:type:: header_module.Num\n\n.. autodata:: header_module.SCORE")
    app.build()

    signature = list(app.env.get_doctree("index").findall(addnodes.desc_signature))[-1]
    assert [ref["reftarget"] for ref in signature.findall(addnodes.pending_xref)] == ["header_module.Num"]


@pytest.mark.sphinx("text", testroot="headers")
def test_header_type_links_an_alias_documented_between_headers(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. autodata:: header_module.SCORE\n\n.. py:type:: header_module.Num\n\n.. autodata:: header_module.LOW")
    app.build()

    signature = list(app.env.get_doctree("index").findall(addnodes.desc_signature))[-1]
    assert [ref["reftarget"] for ref in signature.findall(addnodes.pending_xref)] == ["header_module.Num"]


@pytest.mark.sphinx("text", testroot="headers")
def test_header_type_follows_a_rebuild(
    app: SphinxTestApp, write_rst: Callable[[str], None], make_app: Callable[..., SphinxTestApp]
) -> None:
    write_rst(".. autodata:: header_module.SCORE")
    app.build()
    rebuilt = make_app("text", srcdir=app.srcdir, confoverrides={"autodoc_type_aliases": {"Num": "header_module.Num"}})
    rebuilt.build()

    assert (Path(rebuilt.outdir) / "index.txt").read_text().splitlines()[0] == "header_module.SCORE: Num = 1"


@pytest.fixture
def extra_evaluations(make_app: Callable[..., SphinxTestApp]) -> Callable[[SphinxTestApp], int]:
    """Count the evaluations of a module's annotations a build makes beyond those autodoc makes on its own."""

    def _count(app: SphinxTestApp) -> int:
        evaluations = importlib.import_module("counted_module").EVALUATIONS
        before = len(evaluations)
        app.build()
        with_extension = len(evaluations) - before
        plain = make_app("text", srcdir=app.srcdir, confoverrides={"extensions": ["sphinx.ext.autodoc"]}, freshenv=True)
        before = len(evaluations)
        plain.build()
        return with_extension - (len(evaluations) - before)

    return _count


@pytest.mark.sphinx("text", testroot="headers")
def test_header_type_resolves_a_module_once_per_document(
    app: SphinxTestApp, write_rst: Callable[[str], None], extra_evaluations: Callable[[SphinxTestApp], int]
) -> None:
    write_rst("\n\n".join(f".. autodata:: counted_module.{name}" for name in ("FIRST", "SECOND", "THIRD")))

    assert extra_evaluations(app) == 1


@pytest.mark.sphinx("text", testroot="headers")
def test_header_type_resolves_a_module_again_in_another_document(
    app: SphinxTestApp, write_rst: Callable[[str], None], extra_evaluations: Callable[[SphinxTestApp], int]
) -> None:
    write_rst(".. toctree::\n\n   other\n\n.. autodata:: counted_module.FIRST\n\n.. autodata:: counted_module.SECOND")
    (Path(app.srcdir) / "other.rst").write_text("Other\n=====\n\n.. autodata:: counted_module.THIRD\n")

    assert extra_evaluations(app) == 2
