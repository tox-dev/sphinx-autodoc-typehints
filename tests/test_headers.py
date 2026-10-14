from __future__ import annotations

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
