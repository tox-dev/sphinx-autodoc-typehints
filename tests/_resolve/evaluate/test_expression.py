from __future__ import annotations

from decimal import Decimal
from importlib import import_module
from pathlib import Path
from sys import version_info
from textwrap import dedent
from types import GenericAlias, ModuleType
from typing import TYPE_CHECKING, ForwardRef, Union, get_args, get_origin

from pytest import fixture, mark, param
from sphinx.ext.autodoc.mock import mock

from sphinx_autodoc_typehints._resolve.evaluate import (
    evaluate_annotation,
    resolve_string_annotations,
    unevaluated_annotations,
)
from sphinx_autodoc_typehints._resolve.guards import resolve_type_guarded_imports

if TYPE_CHECKING:
    from collections.abc import Callable

    from _resolve.conftest import AsWritten
    from sphinx_autodoc_typehints._types import Annotation, Documented, Hint


class _Engine:
    def __class_getitem__(cls, item: type) -> type[_Engine]:
        # as SQLAlchemy's TypeEngine does, dropping the arguments
        return cls


@mark.parametrize(
    ("source", "expected"),
    [
        param("_Engine[int]", GenericAlias(_Engine, int), id="subscription-dropping-the-arguments"),
        param("list[int]", list[int], id="subscription"),
        param("[_Engine[kind] for kind in (int,)][0]", GenericAlias(_Engine, int), id="nested-scope"),
        param("_Sized[1:2]", slice(1, 2), id="slice"),
        param("_Sized[1:2, 3]", (slice(1, 2), 3), id="slice-in-a-tuple"),
    ],
)
def test_evaluate_annotation_keeps_the_arguments_a_class_drops(source: str, expected: Annotation) -> None:
    assert evaluate_annotation(source, {"_Engine": _Engine, "_Sized": _Sized}, {}) == expected


class _Sized:
    def __class_getitem__(cls, item: slice) -> slice:
        return item


def test_evaluate_annotation_reads_the_helpers_of_a_nested_scope_from_a_copy_of_the_globals() -> None:
    namespace = {"_Engine": _Engine}
    hint = evaluate_annotation("[_Engine[kind] for kind in (int,)][0]", namespace, {})
    assert (hint, namespace) == (GenericAlias(_Engine, int), {"_Engine": _Engine})


@mark.parametrize(
    ("source", "argument"),
    [
        param("Gen[int] | None", "absent_generics.Gen.<class 'int'>", id="subscribed"),
        param("Gen[3 * 3] | None", "absent_generics.Gen.9", id="beside-arithmetic"),
    ],
)
def test_evaluate_annotation_reads_a_pipe_of_a_mocked_type_as_a_union(source: str, argument: str) -> None:
    with mock(["absent_generics"]):
        generic = import_module("absent_generics").Gen
    hint = evaluate_annotation(source, {"Gen": generic}, {})
    assert (get_origin(hint), [getattr(arg, "__display_name__", arg) for arg in get_args(hint)]) == (
        Union,
        [argument, type(None)],
    )


@mark.parametrize(
    ("hints", "localns", "owner_module", "expected"),
    [
        param({"value": "Path"}, {}, "", {"value": Path}, id="string"),
        param({"value": "'Path'"}, {}, "", {"value": Path}, id="quoted"),
        param({"value": ForwardRef("Path")}, {}, "", {"value": Path}, id="forward-reference"),
        param({"value": int, "return": str}, {}, "", {"value": int, "return": str}, id="evaluated"),
        param(
            {"value": "NoSuchType", "other": "int"}, {}, "", {"value": "NoSuchType", "other": int}, id="unresolvable"
        ),
        param({"value": "'NoSuchType'"}, {}, "", {"value": "NoSuchType"}, id="quoted-unresolvable"),
        param({"value": "Given"}, {"Given": Decimal}, "", {"value": Decimal}, id="names-it-is-given"),
        # a C extension function may live in a child module of the package its stub describes
        param({"value": "Decimal"}, {}, "decimal", {"value": Decimal}, id="owner-module"),
        param({"value": "Decimal"}, {}, "not_imported_anywhere", {"value": "Decimal"}, id="owner-not-imported"),
    ],
)
def test_resolve_string_annotations(
    path_function: Callable[[], None],
    hints: dict[str, Hint],
    localns: dict[str, Documented],
    owner_module: str,
    expected: dict[str, Hint],
) -> None:
    assert resolve_string_annotations(path_function, hints, localns, owner_module) == expected


@fixture(name="path_function")
def path_function_fixture(make_module: Callable[[str], ModuleType]) -> Callable[[], None]:
    return make_module(
        dedent("""\
            from pathlib import Path

            def func(): ...
        """)
    ).func


def test_resolve_string_annotations_reads_the_globals_of_the_module_defining_a_reexported_function(
    module_dir: Path,
) -> None:
    (package := module_dir / "reexporting").mkdir()
    (package / "impl.py").write_text(
        dedent("""\
            import decimal

            def func(): ...
        """)
    )
    (package / "__init__.py").write_text(
        dedent("""\
            from reexporting.impl import func

            func.__module__ = __name__
        """)
    )
    func = import_module("reexporting").func
    assert resolve_string_annotations(func, {"value": "decimal.Decimal"}, {}) == {"value": Decimal}


@mark.parametrize(
    ("source", "expected"),
    [
        param(
            dedent("""\
                from __future__ import annotations

                def func(value: Undefined) -> None: ...
            """),
            {"value": "Undefined", "return": "None"},
            id="stringified",
        ),
        param(
            "def func(value: Undefined) -> None: ...",
            {"value": "Undefined", "return": None},
            marks=mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14"),
            id="lazy-failing-as-a-forward-reference",
        ),
        param(
            "def func(value: 1 / 0) -> None: ...",
            {},
            marks=mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14"),
            id="lazy-raising-on-any-read",
        ),
    ],
)
def test_unevaluated_annotations(
    make_module: Callable[[str], ModuleType], as_written: AsWritten, source: str, expected: dict[str, Hint]
) -> None:
    assert as_written(unevaluated_annotations(make_module(source).func)) == expected


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
@mark.parametrize(
    ("source", "expected"),
    [
        param(
            "{fallback}def func(value: Decimal, count: int) -> None: ...",
            {"value": "Decimal", "count": int, "return": None},
            id="shadowed-name-read-again",
        ),
        param("def func(count: int) -> None: ...", {"count": int, "return": None}, id="no-guard"),
        param(
            dedent("""\
                from __future__ import annotations
                {fallback}def func(count: int) -> None: ...
            """),
            {"count": "int", "return": "None"},
            id="stringified",
        ),
    ],
)
def test_unevaluated_annotations_after_the_guard_ran(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType],
    decimal_fallback: str,
    as_written: AsWritten,
    source: str,
    expected: dict[str, Hint],
) -> None:
    module = make_module(source.format(fallback=decimal_fallback))
    resolve_type_guarded_imports([], module.func)
    assert as_written(unevaluated_annotations(module.func)) == expected
