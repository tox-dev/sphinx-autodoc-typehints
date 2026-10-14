from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.testing.util import SphinxTestApp


@pytest.mark.parametrize(
    ("rst", "expected"),
    [
        pytest.param(".. autoattribute:: typed_dict_module.Movie.year", "NotRequired[int]", id="total-false"),
        pytest.param(".. autoattribute:: typed_dict_module.Movie.title", "str", id="required"),
        pytest.param(".. autoattribute:: typed_dict_module.Movie.rating", "NotRequired[float]", id="not-required"),
        pytest.param(".. autoattribute:: typed_dict_module.Movie.note", "NotRequired[str]", id="annotated"),
        pytest.param(".. autoattribute:: typed_dict_module.Plain.year", "int", id="not-a-typed-dict"),
    ],
)
@pytest.mark.sphinx("text", testroot="typed-dict")
def test_typed_dict_key_shows_whether_it_may_be_left_out(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, expected: str
) -> None:
    write_rst(rst)
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text().splitlines()[0].partition(": ")[2] == expected


@pytest.mark.sphinx("text", testroot="typed-dict", confoverrides={"autodoc_typehints": "none"})
def test_typed_dict_key_without_a_shown_type(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autoattribute:: typed_dict_module.Movie.year")
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text().splitlines()[0] == "Movie.year"


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        pytest.param("Closed", '"Never"', id="closed"),
        pytest.param("ClosedChild", '"Never"', id="inherited"),
        pytest.param("ExtraUnstated", '"int"', id="extra-items"),
        pytest.param("Extra", "counts, documented by hand", id="documented"),
        pytest.param("Reopened", None, id="open"),
        pytest.param("Movie", None, id="unstated"),
    ],
)
@pytest.mark.sphinx("text", testroot="typed-dict")
def test_typed_dict_extra_items(
    app: SphinxTestApp, write_rst: Callable[[str], None], cls: str, expected: str | None
) -> None:
    write_rst(f".. autoclass:: typed_dict_module.{cls}")
    app.build()

    lines = (Path(app.outdir) / "index.txt").read_text().splitlines()
    shown = lines[lines.index("   Extra items:") + 1].strip() if "   Extra items:" in lines else None
    assert shown == expected


@pytest.mark.parametrize(
    ("function", "expected"),
    [
        pytest.param("configure", '"int"', id="pep695"),
        pytest.param("configure_legacy", '"str"', id="legacy"),
    ],
)
@pytest.mark.sphinx("text", testroot="typed-dict")
def test_typed_dict_unpacked_from_a_subscripted_generic(
    app: SphinxTestApp, write_rst: Callable[[str], None], function: str, expected: str
) -> None:
    write_rst(f".. autofunction:: typed_dict_module.{function}")
    app.build()

    lines = [line.strip() for line in (Path(app.outdir) / "index.txt").read_text().splitlines()]
    assert f"**limit** ({expected}) -- the limit" in lines


@pytest.mark.sphinx("text", testroot="typed-dict")
def test_typed_dict_key_inherited_from_a_generic_base(
    app: SphinxTestApp, write_rst: Callable[[str], None], monkeypatch: pytest.MonkeyPatch
) -> None:
    # autodoc lists the keys a TypedDict inherits only on the build importing its module
    monkeypatch.delitem(sys.modules, "typed_dict_module", raising=False)
    write_rst(".. autoclass:: typed_dict_module.IntOptions\n   :members:\n   :undoc-members:")
    app.build()

    lines = (Path(app.outdir) / "index.txt").read_text().splitlines()
    assert [line for line in lines if line.startswith("   ") and ": " in line] == [
        "   extra: NotRequired[list[int]]",
        "   limit: int",
    ]
