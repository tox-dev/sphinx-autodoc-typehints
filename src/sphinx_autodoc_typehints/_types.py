"""
Foundation type aliases for annotations, hints, documented objects and type parameters.

It also names the nodes the renderer walks, the PEP 661 sentinel type and the PEP 814 frozendict type.
"""

from __future__ import annotations

from sys import version_info
from typing import TYPE_CHECKING, NewType, ParamSpec, TypeAliasType, TypeVar, TypeVarTuple

if TYPE_CHECKING:
    from typing import ForwardRef

    from sphinx.util.inspect import TypeAliasForwardRef
    from typing_extensions import TypeForm

if version_info >= (3, 15):  # pragma: >=3.15 cover
    from builtins import frozendict, sentinel
else:  # pragma: <3.15 cover
    from types import MappingProxyType

    from typing_extensions import Sentinel

    frozendict = MappingProxyType
    sentinel = Sentinel

# only type checkers evaluate the alias value, so `TypeForm` needs no runtime import
type Annotation = TypeForm[object]
type Documented = object
# a type parameter is a type form only when written, a value holding one is not
type TypeParam = TypeVar | ParamSpec | TypeVarTuple
# what reading a hint yields when evaluating it failed, leaving the reference or the text as written
type Hint = Annotation | ForwardRef | str
# a value holding a NewType or an alias is no type form, and a subscript holds parameter lists and tuples, all of which
# rendering walks
type RenderNode = (
    Hint | NewType | TypeAliasType | TypeAliasForwardRef | list[RenderNode] | tuple[RenderNode, ...] | None
)

__all__ = [
    "Annotation",
    "Documented",
    "Hint",
    "RenderNode",
    "TypeParam",
    "frozendict",
    "sentinel",
]
