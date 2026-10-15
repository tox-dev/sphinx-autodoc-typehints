from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING

from pytest import mark, param
from sphinx.ext.autodoc import Options

from sphinx_autodoc_typehints._documented import class_doc_choice, class_member_type, overload_skip

if TYPE_CHECKING:
    from sphinx.testing.util import SphinxTestApp


def _helper(value: int) -> str: ...


class _Members:
    as_static = staticmethod(_helper)

    def plain(self) -> None: ...

    @classmethod
    def made(cls) -> None: ...

    def __hidden(self) -> None: ...


@mark.parametrize(
    ("name", "expected"),
    [
        param(f"{__name__}._Members.as_static", staticmethod, id="staticmethod-of-outside-function"),
        param(f"{__name__}._Members.plain", FunctionType, id="method"),
        param(f"{__name__}._Members.made", classmethod, id="classmethod"),
        param(f"{__name__}._Members.__hidden", FunctionType, id="mangled"),
        param(f"{__name__}._Members.missing", None, id="member-missing"),
        param(f"{__name__}._Missing.plain", None, id="class-missing"),
        param("not_imported._Members.plain", None, id="module-missing"),
    ],
)
def test_class_member_type(name: str, expected: type | None) -> None:
    assert class_member_type(name) is expected


@mark.parametrize(
    ("what", "member", "expected"),
    [
        param("function", "plain", 0, id="function"),
        param("method", "plain", 1, id="method"),
        param("method", "made", 1, id="classmethod"),
        param("method", "as_static", 0, id="staticmethod"),
        param("class", "plain", 1, id="class"),
    ],
)
def test_overload_skip(what: str, member: str, expected: int) -> None:
    assert overload_skip(what, f"{__name__}._Members.{member}") == expected


@mark.parametrize(
    ("options", "expected"),
    [
        param(Options({"class-doc-from": "init"}), "init", id="directive-option"),
        param(Options(), "both", id="config"),
        param(None, "both", id="no-options"),
    ],
)
@mark.sphinx("text", testroot="dummy", confoverrides={"autoclass_content": "both"})
def test_class_doc_choice(app: SphinxTestApp, options: Options | None, expected: str) -> None:
    assert class_doc_choice(app, options) == expected
