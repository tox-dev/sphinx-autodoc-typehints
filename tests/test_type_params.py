from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.testing.util import SphinxTestApp


@pytest.mark.parametrize(
    ("rst", "header"),
    [
        pytest.param(
            ".. autofunction:: type_params_module.bounded",
            "type_params_module.bounded[T: Path](value)",
            id="bound",
        ),
        pytest.param(
            ".. autofunction:: type_params_module.constrained",
            "type_params_module.constrained[T: (int, str)](value)",
            id="constraints",
        ),
        pytest.param(
            ".. autofunction:: type_params_module.variadic",
            "type_params_module.variadic[*Ts, **P](*args)",
            id="variadic",
        ),
        pytest.param(
            ".. autoclass:: type_params_module.Stack",
            "class type_params_module.Stack[T](item)",
            id="class",
        ),
        pytest.param(
            ".. autoclass:: type_params_module.Sizes",
            "class type_params_module.Sizes[T: Sized]",
            id="bound-imported-for-type-checking",
        ),
        pytest.param(
            ".. autoclass:: type_params_module.Unknown",
            # only 3.14 can evaluate a bound into a forward reference
            f"class type_params_module.Unknown[T{': Undefined' if sys.version_info >= (3, 14) else ''}]",
            id="bound-not-defined",
        ),
        pytest.param(
            ".. autotype:: type_params_module.Pairs",
            "type type_params_module.Pairs[K] = dict[K, K]",
            id="type-alias",
        ),
        pytest.param(
            ".. autoclass:: type_params_module.Legacy",
            "class type_params_module.Legacy[D = int, **DP = [int, str], *DTs = *tuple[int, ...]]",
            id="generic-subclass",
        ),
        pytest.param(".. autofunction:: type_params_module.plain", "type_params_module.plain(value)", id="not-generic"),
        pytest.param(
            ".. py:module:: type_params_module\n\n.. py:function:: bounded[U](value)",
            "type_params_module.bounded[U](value)",
            id="written-out",
        ),
        pytest.param(".. js:function:: bounded(value)", "bounded(value)", id="other-domain"),
    ],
)
@pytest.mark.sphinx("text", testroot="type-params")
def test_type_params_follow_the_name(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, header: str
) -> None:
    write_rst(rst)
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text().splitlines()[0] == header


@pytest.mark.sphinx("text", testroot="type-params", confoverrides={"typehints_fully_qualified": True})
def test_type_params_fully_qualified(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autofunction:: type_params_module.bounded")
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text().splitlines()[0] == (
        "type_params_module.bounded[T: pathlib.Path](value)"
    )
