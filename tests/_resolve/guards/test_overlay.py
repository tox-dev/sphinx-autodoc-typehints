from __future__ import annotations

from collections import OrderedDict
from decimal import Context, Decimal
from importlib import import_module
from operator import attrgetter
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark, param

from sphinx_autodoc_typehints._resolve import get_all_type_hints
from sphinx_autodoc_typehints._resolve.guards import (
    annotation_globals,
    guarded_names,
    guarded_names_bound,
    resolve_type_guarded_imports,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from types import ModuleType


def test_annotation_globals_reads_the_guarded_type_over_its_runtime_fallback(
    make_module: Callable[[str], ModuleType], decimal_fallback: str
) -> None:
    module = make_module(f"{decimal_fallback}def func(): ...")
    resolve_type_guarded_imports([], module.func)
    assert (annotation_globals(module.func)["Decimal"], module.Decimal) == (Decimal, float)


def test_annotation_globals_reads_a_guarded_class_shadowing_a_runtime_one(
    make_module: Callable[[str], ModuleType],
) -> None:
    module = make_module(
        dedent("""\
            from collections import OrderedDict
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                class Store(OrderedDict): ...

            class Store: ...

            def func(): ...
        """)
    )
    resolve_type_guarded_imports([], module.func)
    guarded = annotation_globals(module.func)["Store"]
    assert (isinstance(guarded, type) and issubclass(guarded, OrderedDict), issubclass(module.Store, OrderedDict)) == (
        True,
        False,
    )


def test_annotation_globals_of_generated_code_fills_in_the_names_of_its_module(
    make_module: Callable[[str], ModuleType],
) -> None:
    # an attrs __init__ runs in a globals dict of its own, which misses the names the module binds afterwards
    module = make_module(
        dedent("""\
            GENERATED = {"__name__": __name__}
            exec("def init(): ...", GENERATED)
            Late = int
        """)
    )
    assert annotation_globals(module.GENERATED["init"]) == {**vars(module), **module.GENERATED}


def test_annotation_globals_of_code_without_a_module() -> None:
    namespace = {"__name__": "nowhere_imported"}
    exec("def orphan(): ...", namespace)  # ruff:ignore[exec-builtin]  # code no imported module defines
    assert annotation_globals(namespace["orphan"]) is namespace


def test_guarded_names_reads_an_aliased_module_as_its_guard_binds_it(
    module_dir: Path, make_module: Callable[[str], ModuleType]
) -> None:
    (module_dir / "guard_rebinding_types.py").write_text(
        dedent("""\
            from typing import TYPE_CHECKING

            Rebound = Runtime = object

            if TYPE_CHECKING:
                from decimal import Decimal as Rebound
        """)
    )
    module = make_module(
        dedent("""\
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                import guard_rebinding_types as _t
        """)
    )
    resolve_type_guarded_imports([], import_module("guard_rebinding_types"))
    resolve_type_guarded_imports([], module)
    assert attrgetter("Rebound", "Runtime")(guarded_names(module)["_t"]) == (Decimal, object)


@mark.parametrize(
    "owner",
    [
        param(lambda parent_module, _: parent_module, id="module"),
        param(lambda _, child_module: child_module.Child, id="subclass-in-another-module"),
    ],
)
def test_guarded_names_bound_binds_what_the_module_lacks_while_the_block_runs(
    module_dir: Path,
    make_module: Callable[[str], ModuleType],
    owner: Callable[[ModuleType, ModuleType], ModuleType | type],
) -> None:
    (module_dir / "bound_base.py").write_text(
        dedent("""\
            from typing import TYPE_CHECKING

            Kept = int

            if TYPE_CHECKING:
                from decimal import Context
                Kept = str

            class Base: ...
        """)
    )
    base = import_module("bound_base")
    child = make_module(
        dedent("""\
            from bound_base import Base

            class Child(Base): ...
        """)
    )
    resolve_type_guarded_imports([], base)
    with guarded_names_bound(owner(base, child)):
        during = (base.Context, base.Kept)
    assert (during, hasattr(base, "Context")) == ((Context, int), False)


def test_guarded_names_bound_keeps_a_name_rebound_while_the_block_runs(
    make_module: Callable[[str], ModuleType],
) -> None:
    module = make_module(
        dedent("""\
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from decimal import Decimal
        """)
    )
    resolve_type_guarded_imports([], module)
    with guarded_names_bound(module):
        bound = vars(module)["Decimal"]
        vars(module)["Decimal"] = float
    assert (bound, vars(module)["Decimal"]) == (Decimal, float)


def test_annotation_globals_types_the_generated_init_of_an_attrs_class(
    make_module: Callable[[str], ModuleType],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    annotations_header: str,
) -> None:
    module = make_module(
        annotations_header
        + dedent("""\
            from typing import TYPE_CHECKING

            import attrs

            if TYPE_CHECKING:
                from decimal import Decimal

            @attrs.define
            class Price:
                amount: Decimal
        """)
    )
    hints = get_all_type_hints([], module.Price.__init__, "mod.Price", {})
    assert (hints, logged_warnings()) == ({"amount": Decimal, "return": type(None)}, [])
