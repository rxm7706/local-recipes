"""Authorization refusals shared across OIDC call sites.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

__all__ = ["ClaimsRejected"]


class ClaimsRejected(Exception):  # noqa: N818
    """Claims cannot be mapped onto a user."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
