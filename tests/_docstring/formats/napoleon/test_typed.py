from __future__ import annotations

from pytest import mark, param

from sphinx_autodoc_typehints._docstring.formats.napoleon import reads_as_type


@mark.parametrize(
    ("text", "expected"),
    [
        param("*int*", True, id="napoleon-emphasis"),
        param(":class:`int`", True, id="role"),
        param("``int``", True, id="literal"),
        param("int", True, id="single-token"),
        param("dict[str, list[int | None]]", True, id="nested-brackets"),
        param("the value", False, id="sentence"),
        param("list[int] or None", False, id="sentence-after-brackets"),
    ],
)
def test_reads_as_type(text: str, expected: bool) -> None:
    assert reads_as_type(text) is expected
