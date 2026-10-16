"""
Foundation types for the names an annotation refers to, which render as those names.

It also holds the helpers that read written annotations.
"""

from __future__ import annotations

__lazy_modules__ = ["types"]

from sys import version_info
from types import GenericAlias
from typing import TYPE_CHECKING, TypeAliasType, Union, get_origin, override

from sphinx.util.inspect import TypeAliasForwardRef

if TYPE_CHECKING:
    from typing import TypeIs

    from sphinx_autodoc_typehints._types import Annotation, Hint


class MyTypeAliasForwardRef(TypeAliasForwardRef):
    """
    A name an annotation refers to, which renders as that name.

    `configured` marks a target of `autodoc_type_aliases`, `crossref` an alias a `py:type` documents, which
    renders as a reference to it.
    """

    def __init__(self, name: str, *, configured: bool = False, crossref: bool = False) -> None:
        super().__init__(name)
        self.configured = configured
        self.crossref = crossref

    @override
    def __or__(self, other: object) -> Annotation:
        # ruff:ignore[non-pep604-annotation-union]  # | would recurse here
        return _written_with_bars(
            Union[self, other]  # ty: ignore[invalid-type-form]  # https://github.com/astral-sh/ty/issues/727
        )

    @override
    def __ror__(self, other: object) -> Annotation:
        # ruff:ignore[non-pep604-annotation-union]  # | would recurse here
        return _written_with_bars(
            Union[other, self]  # ty: ignore[invalid-type-form]  # https://github.com/astral-sh/ty/issues/727
        )

    def __getitem__(self, item: Annotation) -> GenericAlias:
        # evaluating "Pair[int]" subscripts the stand-in for Pair, and a TypeError there would drop the hint
        return GenericAlias(self, item)  # ty: ignore[invalid-argument-type]  # any origin works at runtime


class WrittenTypeAlias(MyTypeAliasForwardRef):
    """A module-level alias such as `Count = int` that an annotation names; it stands for `value`."""

    def __init__(self, name: str, value: Hint) -> None:
        super().__init__(name)
        self.value = value


def _written_with_bars(union: Annotation) -> Annotation:
    if version_info >= (3, 14):  # pragma: >=3.14 cover
        return union
    if get_origin(union) is not Union:  # pragma: <3.14 cover  # equal members collapse into one
        return union
    # typing caches unions, so mark a copy built past the cache: the same union written as Optional must not pick
    # the mark up
    marked = type(union)(union.__origin__, union.__args__)  # pragma: <3.14 cover
    marked.__typehints_bars__ = True  # pragma: <3.14 cover
    return marked  # pragma: <3.14 cover


def split_arguments(text: str) -> list[str]:
    """Split the written arguments `text` at the commas outside brackets, so a nested subscript stays one argument."""
    parts, depth, start = [], 0, 0
    for index, char in enumerate(text):
        depth += (char in "[(") - (char in "])")
        if char == "," and not depth:
            parts.append(text[start:index])
            start = index + 1
    return [*parts, text[start:]]


def is_type_alias(annotation: object) -> TypeIs[TypeAliasType]:
    # typing_extensions keeps its own TypeAliasType class, and it is not a dependency to import it from
    return isinstance(annotation, TypeAliasType) or ((kind := type(annotation)).__module__, kind.__qualname__) == (
        "typing_extensions",
        "TypeAliasType",
    )


__all__ = [
    "MyTypeAliasForwardRef",
    "WrittenTypeAlias",
    "is_type_alias",
    "split_arguments",
]
