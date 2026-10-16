from __future__ import annotations

from importlib import import_module
from pathlib import Path
from sys import version_info
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, fixture, mark, param
from sphinx import addnodes

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import BuildText, MakeModule
    from sphinx.testing.util import SphinxTestApp

    from _signature.conftest import BuildDoctree

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="headers")

_ALIASED: Final[MarkDecorator] = mark.sphinx(confoverrides={"autodoc_type_aliases": {"Num": "header_module.Num"}})


@mark.parametrize(
    ("rst", "expected"),
    [
        param(".. autodata:: header_module.LIMIT", "header_module.LIMIT: int = 3", id="data"),
        param(".. autoattribute:: header_module.Account.balance", "Account.balance: Decimal", id="attribute"),
        param(".. autoproperty:: header_module.Account.total", "property Account.total: int", id="property"),
        param(".. autoproperty:: header_module.Account.fee", "property Account.fee: Decimal", id="cached-property"),
        param(".. autoproperty:: header_module.Account.kind", "class property Account.kind: str", id="class-property"),
        param(".. autoproperty:: header_module.Proxied.size", "property Proxied.size: int", id="proxied-property"),
        param(".. autoproperty:: header_module.Vault.__code", "property Vault.__code: int", id="mangled-property"),
        param(".. autoproperty:: header_module.Vault.__Lock.pins", "property __Lock.pins: int", id="mangled-owner"),
        param(".. autoattribute:: header_module.Account.owner", "Account.owner: str", id="instance-attribute"),
        param(
            dedent("""\
                .. py:data:: header_module.MANUAL
                   :type: Annotated[int, 'kept']"""),
            "header_module.MANUAL: Annotated[int, 'kept']",
            id="written-by-hand",
        ),
        param(
            ".. autodata:: header_module.RATE",
            "header_module.RATE: decimal.Decimal | None = None",
            marks=mark.sphinx(confoverrides={"typehints_fully_qualified": True}),
            id="fully-qualified",
        ),
        param(
            ".. autoattribute:: header_module.IntBox.value", "IntBox.value: int", id="inherited-type-param-annotation"
        ),
        param(
            ".. autoattribute:: header_module.IntBox.label",
            "IntBox.label: tuple[int, ...] = ()",
            id="inherited-type-param-with-a-value",
        ),
        param(
            ".. autoproperty:: header_module.IntBox.first",
            "property IntBox.first: int",
            id="inherited-type-param-property",
        ),
        param(
            ".. autoattribute:: header_module.StrLegacy.items",
            "StrLegacy.items: list[str]",
            id="inherited-type-param-legacy-generic",
        ),
        param(".. autodata:: header_module.ENGINE", "header_module.ENGINE: Engine[int]", id="arguments-data"),
        param(
            ".. autoattribute:: header_module.Engined.engine", "Engined.engine: Engine[str]", id="arguments-attribute"
        ),
        param(
            ".. autoattribute:: header_module.Engined.backup",
            "Engined.backup: Engine[str] | None = None",
            id="arguments-nested",
        ),
        param(
            ".. autoattribute:: header_module.Engined.starter",
            "Engined.starter: Callable[[Engine[str]], None]",
            id="arguments-callable-parameter",
        ),
        param(
            ".. autoproperty:: header_module.Engined.spare",
            "property Engined.spare: Engine[bytes]",
            id="arguments-property",
        ),
        param(
            ".. autoattribute:: header_module.INSTANCE.engine",
            "INSTANCE.engine: Engine[str]",
            id="arguments-of-an-instance",
        ),
        param(
            ".. autodata:: header_module.SCORE",
            "header_module.SCORE: Num = 1",
            marks=_ALIASED,
            id="configured-alias-data",
        ),
        param(
            ".. autoattribute:: header_module.Scored.points",
            "Scored.points: Num = 0",
            marks=_ALIASED,
            id="configured-alias-attribute",
        ),
        param(
            ".. autoproperty:: header_module.Scored.best",
            "property Scored.best: Num",
            marks=_ALIASED,
            id="configured-alias-property",
        ),
        param(
            ".. autoattribute:: header_module.Totals.count",
            "Totals.count: Num",
            marks=_ALIASED,
            id="configured-alias-typed-dict-key",
        ),
    ],
)
def test_header_type_renders_like_a_field(build_text: BuildText, rst: str, expected: str) -> None:
    assert build_text(rst).splitlines()[0] == expected


@mark.parametrize(
    "owner", [param("SubEngined", id="inherited"), param("Generated", id="inherited-by-a-class-without-source")]
)
def test_header_type_of_an_attribute_a_base_annotates(build_text: BuildText, owner: str) -> None:
    # autodoc finds the attribute only with the guard of the base bound, which documenting the base runs
    text = build_text(
        dedent(f"""\
            .. autoclass:: header_module.Engined

            .. autoattribute:: header_module.{owner}.engine
        """)
    )
    assert f"{owner}.engine: Engine[str]" in text.splitlines()


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_header_type_reads_a_lazy_annotation_as_guarded(  # pragma: >=3.14 cover
    make_module: MakeModule, build_text: BuildText
) -> None:
    make_module(
        "lazy_header_module",
        dedent("""\
            from typing import TYPE_CHECKING, Final

            if TYPE_CHECKING:
                from decimal import Decimal
            else:
                Decimal = float

            class Ledger:
                total: Decimal
                '''The total.'''
        """),
    )

    assert build_text(".. autoattribute:: lazy_header_module.Ledger.total").splitlines()[0] == "Ledger.total: Decimal"


@mark.parametrize(
    ("rst", "expected"),
    [
        param(".. autodata:: header_module.RATE", ["decimal.Decimal", "None"], id="type-checking-import"),
        param(
            dedent("""\
                .. py:type:: header_module.Num

                .. autodata:: header_module.SCORE"""),
            ["header_module.Num"],
            id="alias-documented-before",
        ),
        param(
            dedent("""\
                .. autodata:: header_module.SCORE

                .. py:type:: header_module.Num

                .. autodata:: header_module.LOW"""),
            ["header_module.Num"],
            id="alias-documented-between-headers",
        ),
    ],
)
def test_header_type_links_its_names(build_doctree: BuildDoctree, rst: str, expected: list[str]) -> None:
    signature = list(build_doctree(rst).findall(addnodes.desc_signature))[-1]
    assert [ref["reftarget"] for ref in signature.findall(addnodes.pending_xref)] == expected


def test_header_type_follows_a_rebuild(
    app: SphinxTestApp, build_text: BuildText, make_app: Callable[..., SphinxTestApp]
) -> None:
    build_text(".. autodata:: header_module.SCORE")
    rebuilt = make_app("text", srcdir=app.srcdir, confoverrides={"autodoc_type_aliases": {"Num": "header_module.Num"}})
    rebuilt.build()

    assert (Path(rebuilt.outdir) / "index.txt").read_text().splitlines()[0] == "header_module.SCORE: Num = 1"


def test_header_type_resolves_a_module_once_per_document(
    write_rst: Callable[[str], None], extra_evaluations: Callable[[], int]
) -> None:
    write_rst(
        dedent("""\
            .. autodata:: counted_module.FIRST

            .. autodata:: counted_module.SECOND

            .. autodata:: counted_module.THIRD
        """)
    )

    assert extra_evaluations() == 1


def test_header_type_resolves_a_module_again_in_another_document(
    app: SphinxTestApp, write_rst: Callable[[str], None], extra_evaluations: Callable[[], int]
) -> None:
    write_rst(
        dedent("""\
            .. toctree::

               other

            .. autodata:: counted_module.FIRST

            .. autodata:: counted_module.SECOND""")
    )
    (Path(app.srcdir) / "other.rst").write_text(
        dedent("""\
            Other
            =====

            .. autodata:: counted_module.THIRD
        """)
    )

    assert extra_evaluations() == 2


# beyond the evaluations autodoc makes on its own
@fixture(name="extra_evaluations")
def extra_evaluations_fixture(app: SphinxTestApp, make_app: Callable[..., SphinxTestApp]) -> Callable[[], int]:
    def count() -> int:
        evaluations = import_module("counted_module").EVALUATIONS
        before = len(evaluations)
        app.build()
        with_extension = len(evaluations) - before
        plain = make_app("text", srcdir=app.srcdir, confoverrides={"extensions": ["sphinx.ext.autodoc"]}, freshenv=True)
        before = len(evaluations)
        plain.build()
        return with_extension - (len(evaluations) - before)

    return count
