from __future__ import annotations

from sys import version_info
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from docutils import nodes
from pytest import MarkDecorator, mark, param
from sphinx import addnodes

if TYPE_CHECKING:
    from conftest import BuildText

    from _signature.conftest import BuildDoctree


pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="type-params")


@mark.parametrize(
    ("rst", "header"),
    [
        param(
            ".. autofunction:: type_params_module.bounded",
            "type_params_module.bounded[T: Path](value)",
            id="bound",
        ),
        param(
            ".. autofunction:: type_params_module.bounded",
            "type_params_module.bounded[T: pathlib.Path](value)",
            marks=mark.sphinx(confoverrides={"typehints_fully_qualified": True}),
            id="fully-qualified",
        ),
        param(
            ".. autofunction:: type_params_module.constrained",
            "type_params_module.constrained[T: (int, str)](value)",
            id="constraints",
        ),
        param(
            ".. autofunction:: type_params_module.variadic",
            "type_params_module.variadic[*Ts, **P](*args)",
            id="variadic",
        ),
        param(
            ".. autoclass:: type_params_module.Stack",
            "class type_params_module.Stack[T](item)",
            id="class",
        ),
        param(
            ".. autoclass:: type_params_module.Sizes",
            "class type_params_module.Sizes[T: Sized]",
            id="bound-imported-for-type-checking",
        ),
        param(
            ".. autoclass:: type_params_module.Unknown",
            # only 3.14 can evaluate a bound into a forward reference
            f"class type_params_module.Unknown[T{': Undefined' if version_info >= (3, 14) else ''}]",
            id="bound-not-defined",
        ),
        param(
            ".. autoclass:: type_params_module.Rejected",
            # 3.14 keeps a bound it cannot evaluate as a forward reference
            f"class type_params_module.Rejected[T{': Rejecting[int]' if version_info >= (3, 14) else ''}]",
            id="bound-raises",
        ),
        param(
            ".. autotype:: type_params_module.Pairs",
            "type type_params_module.Pairs[K] = dict[K, K]",
            id="type-alias",
        ),
        param(
            ".. autoclass:: type_params_module.Legacy",
            "class type_params_module.Legacy[D = int, **DP = [int, str], *DTs = *tuple[int, ...]]",
            id="generic-subclass",
        ),
        param(
            ".. autoclass:: type_params_module.PathDefaults",
            "class type_params_module.PathDefaults[DPath = Path, **DPathP = [Path], *DPathTs = *tuple[Path, ...]]",
            id="defaults-imported-class",
        ),
        param(".. autofunction:: type_params_module.plain", "type_params_module.plain(value)", id="not-generic"),
        param(
            ".. autoclass:: type_params_module.File",
            "class type_params_module.File(*args, **kwargs)",
            id="protocol-not-runtime-checkable-base",
        ),
        param(
            ".. autodata:: type_params_module.default_stack",
            "type_params_module.default_stack: Stack[int] = <type_params_module.Stack object>",
            id="data-holding-a-generic-instance",
        ),
    ],
)
def test_type_params_follow_the_name(build_text: BuildText, rst: str, header: str) -> None:
    assert build_text(rst).splitlines()[0] == header


@mark.parametrize(
    ("rst", "header"),
    [
        param(
            dedent("""\
                .. autofunction:: type_params_module.plain

                .. py:currentmodule:: type_params_module

                .. py:function:: bounded(value)
            """),
            "type_params_module.bounded(value)",
            id="not-documented-by-autodoc",
        ),
        param(
            dedent("""\
                .. autofunction:: type_params_module.bounded

                .. py:currentmodule:: type_params_module

                .. py:function:: bounded[U](value)
                   :no-index:
            """),
            "type_params_module.bounded[U](value)",
            id="writes-its-type-params",
        ),
        param(
            dedent("""\
                .. autofunction:: type_params_module.bounded

                .. js:module:: type_params_module

                .. js:function:: bounded(value)
            """),
            "type_params_module.bounded(value)",
            id="other-domain",
        ),
    ],
)
def test_type_params_not_read_for_a_written_out_signature(build_text: BuildText, rst: str, header: str) -> None:
    # autodoc imported the module, where a lookup would find each handwritten name
    assert build_text(rst).splitlines()[-1] == header


def test_type_params_defaults_cross_reference(build_doctree: BuildDoctree) -> None:
    assert [
        xref["reftarget"]
        for default in build_doctree(".. autoclass:: type_params_module.PathDefaults").findall(nodes.inline)
        if "default_value" in default["classes"]
        for xref in default.findall(addnodes.pending_xref)
    ] == ["pathlib.Path", "pathlib.Path", "tuple", "pathlib.Path"]
