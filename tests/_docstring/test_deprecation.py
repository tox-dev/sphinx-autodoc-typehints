from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, mark, param

if TYPE_CHECKING:
    from conftest import BuildText

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="deprecated")


@mark.parametrize(
    ("rst", "expected"),
    [
        param(
            ".. autofunction:: deprecated_module.stale",
            dedent("""\
                deprecated_module.stale(value)

                   Do the stale thing.

                   Deprecated: Use fresh() instead, *really*.

                   More words.

                   Return type:
                      "int"
            """),
            id="function",
        ),
        param(
            ".. autoclass:: deprecated_module.Stale",
            dedent("""\
                class deprecated_module.Stale(**kwargs)

                   A stale class.

                   Deprecated: Use Fresh. It is faster.
            """),
            id="class",
        ),
        param(
            ".. autoclass:: deprecated_module.Child",
            dedent("""\
                class deprecated_module.Child(**kwargs)

                   Not deprecated itself.
            """),
            id="subclass",
        ),
        param(
            ".. autofunction:: deprecated_module.noted",
            dedent("""\
                deprecated_module.noted(value)

                   Do the noted thing.

                   Deprecated since version 2.0: Use fresh().

                   Return type:
                      "int"
            """),
            id="documented-deprecation",
        ),
        param(
            ".. autofunction:: deprecated_module.shown",
            dedent("""\
                deprecated_module.shown(value)

                   Use it like this:

                      shown(1)

                   Deprecated: Use fresh() instead.

                   Return type:
                      "int"
            """),
            id="summary-introducing-a-literal-block",
        ),
    ],
)
def test_deprecated_message_follows_the_summary(build_text: BuildText, rst: str, expected: str) -> None:
    assert build_text(rst) == expected


@mark.sphinx("html")
def test_deprecated_message_renders_as_a_version_change(build_text: BuildText) -> None:
    assert dedent("""\
        <div class="deprecated">
        <p><span class="versionmodified deprecated">Deprecated: </span>Use fresh() instead, *really*.</p>
        </div>""") in build_text(".. autofunction:: deprecated_module.stale")
