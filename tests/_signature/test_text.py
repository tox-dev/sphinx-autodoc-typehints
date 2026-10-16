from __future__ import annotations

from inspect import Parameter, signature
from pathlib import Path
from typing import TYPE_CHECKING

from pytest import mark, param

from sphinx_autodoc_typehints._signature.text import directive_text, names_other_parameters, signature_type

if TYPE_CHECKING:
    from sphinx.testing.util import SphinxTestApp


@mark.parametrize(
    ("given", "expected"),
    [
        param("(x, y=3)", True, id="other-names"),
        param("(first, *, second)", True, id="other-kinds"),
        param("(first: int, second: float = 0.5)", False, id="introspected"),
        param("(first: int, second: float = <object object>)", False, id="unreadable"),
        param("(**kwargs)", False, id="catch-all-keywords"),
        param("(*args: Any, **kwargs: Any)", False, id="catch-all"),
    ],
)
def test_names_other_parameters(given: str, expected: bool) -> None:
    assert names_other_parameters(given, list(signature(_explicitly_signed).parameters.values())) is expected


def _explicitly_signed(first: int, second: float = 0.5) -> None: ...


@mark.parametrize(
    "expected",
    [
        param(r"(sep='\n')", id="kept-as-is"),
        param(
            r"(sep='\\n')",
            marks=mark.sphinx(confoverrides={"strip_signature_backslash": True}),
            id="escaped-for-stripping",
        ),
    ],
)
@mark.sphinx("text", testroot="dummy")
def test_directive_text_escapes_backslashes_only_for_stripping(app: SphinxTestApp, expected: str) -> None:
    assert directive_text(app, r"(sep='\n')") == expected


@mark.parametrize(
    ("hint", "expected"),
    [
        param(Parameter.empty, Parameter.empty, id="not-annotated"),
        param(Path, "~pathlib.Path", id="annotated"),
    ],
)
@mark.sphinx("text", testroot="dummy")
def test_signature_type(app: SphinxTestApp, hint: type, expected: str | type[Parameter.empty]) -> None:
    assert signature_type(app, hint) == expected
