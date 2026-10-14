from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from docutils import nodes
from sphinx import addnodes

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
            ".. autoclass:: type_params_module.Rejected",
            # 3.14 keeps a bound it cannot evaluate as a forward reference
            f"class type_params_module.Rejected[T{': Rejecting[int]' if sys.version_info >= (3, 14) else ''}]",
            id="bound-raises",
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
        pytest.param(
            ".. autoclass:: type_params_module.PathDefaults",
            "class type_params_module.PathDefaults[DPath = Path, **DPathP = [Path], *DPathTs = *tuple[Path, ...]]",
            id="defaults-imported-class",
        ),
        pytest.param(".. autofunction:: type_params_module.plain", "type_params_module.plain(value)", id="not-generic"),
        pytest.param(
            ".. py:module:: type_params_module\n\n.. py:function:: bounded[U](value)",
            "type_params_module.bounded[U](value)",
            id="written-out",
        ),
        pytest.param(".. js:function:: bounded(value)", "bounded(value)", id="other-domain"),
        pytest.param(
            ".. autodata:: type_params_module.default_stack",
            "type_params_module.default_stack: Stack[int] = <type_params_module.Stack object>",
            id="data-holding-a-generic-instance",
        ),
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


@pytest.mark.sphinx("text", testroot="type-params")
def test_type_params_defaults_cross_reference(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst(".. autoclass:: type_params_module.PathDefaults")
    app.build()

    assert [
        xref["reftarget"]
        for default in app.env.get_doctree("index").findall(nodes.inline)
        if "default_value" in default["classes"]
        for xref in default.findall(addnodes.pending_xref)
    ] == ["pathlib.Path", "pathlib.Path", "tuple", "pathlib.Path"]


@pytest.mark.parametrize(
    ("rst", "return_type"),
    [
        pytest.param(".. autofunction:: type_params_module.bounded", '"T"', id="function"),
        pytest.param(".. automethod:: type_params_module.Stack.peek", '"T"', id="class"),
        pytest.param(".. automethod:: type_params_module.Legacy.first", '"D"', id="generic-subclass"),
        pytest.param(".. autofunction:: type_params_module.loose", '"TypeVar"("L")', id="undeclared"),
    ],
)
@pytest.mark.sphinx("text", testroot="type-params")
def test_type_params_declared_in_the_signature_show_by_name(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, return_type: str
) -> None:
    write_rst(rst)
    app.build()

    lines = (Path(app.outdir) / "index.txt").read_text().splitlines()
    assert lines[lines.index("   Return type:") + 1].strip() == return_type


@pytest.mark.sphinx("text", testroot="type-params")
def test_type_params_declared_param_spec_components_show_by_name(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. autofunction:: type_params_module.forward")
    app.build()

    lines = (Path(app.outdir) / "index.txt").read_text().splitlines()
    assert [line.strip() for line in lines if "args**" in line] == [
        '* **args** ("P.args") -- positional',
        '* **kwargs** ("P.kwargs") -- by keyword',
    ]


@pytest.mark.parametrize(
    ("rst", "return_type"),
    [
        pytest.param(".. automethod:: type_params_module.IntBox.get", '"int"', id="legacy"),
        pytest.param(".. automethod:: type_params_module.IntStack.peek", '"int"', id="pep695"),
        pytest.param(".. automethod:: type_params_module.IntListing.get", '"list"["int"]', id="through-two-bases"),
        pytest.param(".. automethod:: type_params_module.Listing.get", '"list"["U"]', id="to-own-param"),
        pytest.param(".. automethod:: type_params_module.Restack.peek", '"V"', id="to-own-param-of-the-name"),
    ],
)
@pytest.mark.sphinx("text", testroot="type-params")
def test_type_params_bound_by_the_documenting_subclass_return(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, return_type: str
) -> None:
    write_rst(rst)
    app.build()

    lines = (Path(app.outdir) / "index.txt").read_text().splitlines()
    assert lines[lines.index("   Return type:") + 1].strip() == return_type


@pytest.mark.parametrize(
    ("rst", "parameter"),
    [
        pytest.param(
            ".. automethod:: type_params_module.IntBox.get", '**default** ("int") -- returned when empty', id="method"
        ),
        pytest.param(".. autoclass:: type_params_module.IntStack", '**item** ("int")', id="constructor"),
    ],
)
@pytest.mark.sphinx("text", testroot="type-params", confoverrides={"always_document_param_types": True})
def test_type_params_bound_by_the_documenting_subclass_parameter(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, parameter: str
) -> None:
    write_rst(rst)
    app.build()

    assert parameter in [line.strip() for line in (Path(app.outdir) / "index.txt").read_text().splitlines()]


@pytest.mark.sphinx(
    "text",
    testroot="type-params",
    confoverrides={"typehints_use_signature": True, "typehints_use_signature_return": True},
)
def test_type_params_bound_by_the_documenting_subclass_signature(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. automethod:: type_params_module.IntBox.get")
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text().splitlines()[0] == ("IntBox.get(default: int) -> int")
