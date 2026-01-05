from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "Hold",
    "MapDef",
    "Move",
    "Order",
    "Support",
    "adjudicate_orders",
    "legal_orders",
    "validate_map",
]

if TYPE_CHECKING:
    from .adjudicator import adjudicate_orders
    from .map import MapDef, validate_map
    from .orders import Hold, Move, Order, Support, legal_orders


def __getattr__(name: str):
    if name in {"Hold", "Move", "Order", "Support", "legal_orders"}:
        from .orders import Hold, Move, Order, Support, legal_orders

        return {
            "Hold": Hold,
            "Move": Move,
            "Order": Order,
            "Support": Support,
            "legal_orders": legal_orders,
        }[name]
    if name in {"MapDef", "validate_map"}:
        from .map import MapDef, validate_map

        return {"MapDef": MapDef, "validate_map": validate_map}[name]
    if name == "adjudicate_orders":
        from .adjudicator import adjudicate_orders

        return adjudicate_orders
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
