from __future__ import annotations

from typing import TYPE_CHECKING

from typed_dict_unguarded_base import Base

if TYPE_CHECKING:
    from decimal import Decimal as Item
else:
    Item = str


class Child(Base):
    own: Item
