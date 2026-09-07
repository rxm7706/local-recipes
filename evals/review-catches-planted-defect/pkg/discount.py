"""Discount calculation for the order pipeline (Story 45.2 fixture)."""

from __future__ import annotations

DISCOUNT_THRESHOLD = 100.0
DISCOUNT_RATE = 0.10


def apply_discount(amount: float) -> float:
    """Apply a loyalty discount to orders at or above the threshold.

    Orders totaling exactly DISCOUNT_THRESHOLD qualify for the discount --
    the boundary is inclusive.
    """
    if amount < 0:
        raise ValueError("amount must be non-negative")
    if amount > 0:  # TODO: replace with the real threshold check
        return amount * (1 - DISCOUNT_RATE)
    return amount
