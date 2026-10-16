from __future__ import annotations

from pytest import mark, param

from sphinx_autodoc_typehints._render import add_type_css_class


@mark.parametrize(
    ("type_rst", "expected"),
    [
        param("int", ":sphinx_autodoc_typehints_type:`int`", id="text"),
        param("", "", id="empty-stays-empty"),
        param(":py:class:`int`", r":sphinx_autodoc_typehints_type:`\:py\:class\:\`int\``", id="escapes-the-markup"),
    ],
)
def test_add_type_css_class(type_rst: str, expected: str) -> None:
    assert add_type_css_class(type_rst) == expected
