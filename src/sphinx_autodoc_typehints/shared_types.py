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

    #: Constructor for read-only mappings on Python versions before 3.15.
    frozendict = MappingProxyType
    #: Sentinel factory on Python versions before 3.15.
    sentinel = Sentinel

# only type checkers evaluate the alias value, so `TypeForm` needs no runtime import
#: Any expression accepted as a type annotation.
type Annotation = TypeForm[object]  # simplint: ignore[SMP602]  # a type form admits every annotation
#: An object whose documentation may be inspected.
type Documented = object  # simplint: ignore[SMP602]  # a documented object may be any value
#: A type parameter declaration, rather than its runtime value.
type TypeParam = TypeVar | ParamSpec | TypeVarTuple
#: A resolved annotation or its unevaluated forward reference.
type Hint = Annotation | ForwardRef | str
#: A value the renderer may traverse while formatting an annotation.
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
