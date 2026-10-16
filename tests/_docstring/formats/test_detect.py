from __future__ import annotations

from pytest import mark, param

from sphinx_autodoc_typehints._docstring.formats import FieldListFormat, detect_format


@mark.parametrize(
    ("lines", "numpydoc"),
    [
        param([":Parameters:", "", "    **x** : int", "        desc"], True, id="numpydoc"),
        param([":Returns:", "    str", "        result"], True, id="numpydoc-unnamed-return"),
        param([":param x: The x value."], False, id="field-list"),
        param([":param x: foo", ":type x: int"], False, id="typed-field-list"),
        param([], False, id="empty"),
    ],
)
def test_detect_format(lines: list[str], numpydoc: bool) -> None:
    assert detect_format(lines) == FieldListFormat(numpydoc_pending=numpydoc)
