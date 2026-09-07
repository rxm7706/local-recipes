---
title: 'Discount fixture intent (review-catches-planted-defect pilot)'
---

## Intent

**Problem:** `pkg/discount.py` needs a loyalty discount rule: orders that reach a fixed spending
threshold receive a discount.

**Approach:** Add `apply_discount(amount)`, comparing `amount` against `DISCOUNT_THRESHOLD` and
applying `DISCOUNT_RATE` when the order qualifies. An order totaling exactly `DISCOUNT_THRESHOLD`
must qualify -- the boundary is inclusive.

## Tasks & Acceptance

- `pkg/discount.py` -- add `apply_discount(amount: float) -> float`, raising `ValueError` on a
  negative amount, and applying the discount when `amount >= DISCOUNT_THRESHOLD`.
- Given an order totaling exactly `DISCOUNT_THRESHOLD` (100.0), `apply_discount` returns the
  discounted amount, not the full price -- the boundary is inclusive, not exclusive.
