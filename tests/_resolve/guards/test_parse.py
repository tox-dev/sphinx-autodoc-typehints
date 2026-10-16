from __future__ import annotations

import sys  # a module without source under test
from ast import parse, unparse
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import mark, param

from sphinx_autodoc_typehints._resolve.guards.parse import (
    defined_names,
    guard_binds,
    guarded_statements,
    module_source,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

_DECIMAL_GUARD: Final[str] = dedent("""\
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from decimal import Decimal
""")


@mark.parametrize(
    ("source", "expected"),
    [
        param(
            dedent("""\
                import typing as t

                if t.TYPE_CHECKING:
                    from decimal import Decimal
            """),
            ["from decimal import Decimal"],
            id="module-alias",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if TYPE_CHECKING: from decimal import Decimal
            """),
            ["from decimal import Decimal"],
            id="one-line",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if TYPE_CHECKING:
                    import os
                # a note
                    from decimal import Decimal
            """),
            ["import os", "from decimal import Decimal"],
            id="column-zero-comment",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if TYPE_CHECKING:
                    DOC = '''
                text
                '''
                    import os
            """),
            ["DOC = '\\ntext\\n'", "import os"],
            id="multi-line-string",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if not TYPE_CHECKING:
                    pass
                else:
                    import os
            """),
            ["import os"],
            id="negated-else",
        ),
        param(
            dedent("""\
                import typing
                from typing import TYPE_CHECKING

                if TYPE_CHECKING and typing.TYPE_CHECKING:
                    import os
            """),
            ["import os"],
            id="compound-and",
        ),
        param(
            dedent("""\
                import sys
                from typing import TYPE_CHECKING

                if TYPE_CHECKING or sys.version_info < (3, 0):
                    import os
            """),
            ["import os"],
            id="compound-or",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if TYPE_CHECKING and False:
                    import os
            """),
            [],
            id="compound-and-false",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if TYPE_CHECKING and 0:
                    import os
                else:
                    import sys
            """),
            ["import sys"],
            id="compound-and-zero",
        ),
        param(
            dedent("""\
                import sys
                from typing import TYPE_CHECKING

                if TYPE_CHECKING and sys.platform == "win32":
                    import os
                else:
                    import decimal
            """),
            ["import os"] if sys.platform == "win32" else ["import decimal"],
            id="compound-and-platform",
        ),
        param(
            dedent("""\
                import sys
                from typing import TYPE_CHECKING

                if TYPE_CHECKING and sys.platform != "win32":
                    import os
                else:
                    import decimal
            """),
            ["import decimal"] if sys.platform == "win32" else ["import os"],
            id="compound-and-other-platform",
        ),
        param(
            dedent("""\
                import sys
                from typing import TYPE_CHECKING

                if TYPE_CHECKING and sys.platform in {"win32", "linux"}:
                    import os
            """),
            [],
            id="compound-unsupported-platform-test",
        ),
        param(
            dedent("""\
                import sys
                from typing import TYPE_CHECKING

                if TYPE_CHECKING and "win32" == sys.platform:
                    import os
            """),
            [],
            id="compound-reversed-platform-comparison",
        ),
        param(
            dedent("""\
                import sys
                from typing import TYPE_CHECKING

                if TYPE_CHECKING and "win32" == sys.platform == "linux":
                    import os
            """),
            [],
            id="compound-chained-platform-comparison",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if not TYPE_CHECKING or 0:
                    import os
                else:
                    import decimal
            """),
            ["import decimal"],
            id="compound-or-false",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if TYPE_CHECKING and condition():
                    import os
                else:
                    import decimal
            """),
            [],
            id="compound-and-unknown",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if TYPE_CHECKING and False:
                    import os
                else:
                    import sys
            """),
            ["import sys"],
            id="compound-and-false-else",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if TYPE_CHECKING or True:
                    import os
            """),
            ["import os"],
            id="compound-or-true",
        ),
        param(
            dedent("""\
                from typing import TYPE_CHECKING

                if False:
                    import os
                if TYPE_CHECKING:
                    import sys
            """),
            ["import sys"],
            id="unrelated-constant-guard",
        ),
        param(
            dedent("""\
                import sys
                from typing import TYPE_CHECKING

                if not sys.argv:
                    import os
                if sys.argv and sys.path:
                    import os
            """),
            [],
            id="runtime-conditions",
        ),
        param("import os", [], id="no-guard"),
        # pytest turns warnings into errors, as -W error does
        param(f'{_DECIMAL_GUARD}PATTERN = "\\d"', ["from decimal import Decimal"], id="syntax-warning"),
        # what a stale linecache entry or a transpiling loader hands inspect.getsource
        param(
            _DECIMAL_GUARD
            + dedent("""\
                else:
                    Decimal = float
                this is not python (
            """),
            ["from decimal import Decimal"],
            id="unparsable-statement",
        ),
        param(
            _DECIMAL_GUARD
            + dedent("""\
                else:
                    Decimal = float
                if ready:
                    this is not python (
            """),
            ["from decimal import Decimal"],
            id="unparsable-if-statement",
        ),
    ],
)
def test_guarded_statements_of_a_guard_form(source: str, expected: list[str]) -> None:
    statements, errors = guarded_statements(source)
    assert ([unparse(statement) for statement in statements], errors) == (expected, ())


def test_guarded_statements_reports_a_guard_that_does_not_parse() -> None:
    _, errors = guarded_statements(
        _DECIMAL_GUARD
        + dedent("""\

            if TYPE_CHECKING:
                this is not python (
        """)
    )
    assert [(type(error), error.msg) for error in errors] == [(SyntaxError, "'(' was never closed")]


def test_guarded_statements_parses_a_source_once() -> None:
    # every importer of a module asks again while its guard binds none of the names imported
    source = f"{_DECIMAL_GUARD}Value = int"
    statements, errors = parsed = guarded_statements(source)
    assert ([unparse(statement) for statement in statements], errors, guarded_statements(source) is parsed) == (
        ["from decimal import Decimal"],
        (),
        True,
    )


@mark.parametrize(
    ("statement", "expected"),
    [
        param("class Store: ...", ["Store"], id="class"),
        param("def pick(): ...", ["pick"], id="function"),
        param("async def fetch(): ...", ["fetch"], id="async-function"),
        param("first = second.attribute = third = 1", ["first", "third"], id="assignment"),
        param("Alias: TypeAlias = int", ["Alias"], id="annotated-name"),
        param("holder.size: int = 1", [], id="annotated-attribute"),
        param("import os.path, json as serial", ["os", "serial"], id="import"),
        param("from decimal import Decimal, Context as Ctx", ["Decimal", "Ctx"], id="import-from"),
        param(
            dedent("""\
                if ready:
                    Fast = int
                else:
                    Slow = int"""),
            ["Fast", "Slow"],
            id="nested-statements",
        ),
        param("REGISTRY = {kind: kind for kind in (int, str)}", ["REGISTRY"], id="comprehension-variable"),
        param("print(1)", [], id="expression"),
    ],
)
def test_defined_names(statement: str, expected: list[str]) -> None:
    assert list(defined_names(parse(statement).body[0])) == expected


@mark.parametrize(
    ("names", "expected"),
    [param({"Decimal", "Other"}, True, id="binds"), param({"Other"}, False, id="binds-none")],
)
def test_guard_binds(make_module: Callable[[str], ModuleType], names: set[str], expected: bool) -> None:
    assert guard_binds(make_module(_DECIMAL_GUARD), names) is expected


@mark.parametrize(
    ("module", "expected"),
    [
        param(lambda make: make(_DECIMAL_GUARD), _DECIMAL_GUARD, id="with-source"),
        param(lambda _: sys, "", id="without-source"),
    ],
)
def test_module_source(
    make_module: Callable[[str], ModuleType],
    module: Callable[[Callable[[str], ModuleType]], ModuleType],
    expected: str,
) -> None:
    assert module_source(module(make_module)) == expected
