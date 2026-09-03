"""Policy registry for views exempted from ``ATOMIC_REQUESTS`` (Story 43.3).

Streaming and long-poll portal views must not hold a PostgreSQL transaction
open while awaiting station work or HTMX re-polls.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from django.db import transaction

View = TypeVar("View", bound=Callable[..., object])

# Fully-qualified ``module.view_name`` strings — the policy test enumerates this set.
NON_ATOMIC_VIEW_NAMES: frozenset[str] = frozenset(
    {
        "django_warden_fabric.views.get_audit",
        "django_atlas_portal.views.chrome_home",
        "platformapp.front_door.views.runs_board",
    },
)


def non_atomic_view(view: View) -> View:
    """Mark a view ``non_atomic_requests`` and record it in the policy registry."""
    wrapped = transaction.non_atomic_requests(view)
    name = f"{view.__module__}.{view.__name__}"
    if name not in NON_ATOMIC_VIEW_NAMES:
        msg = f"{name!r} is not listed in NON_ATOMIC_VIEW_NAMES"
        raise ValueError(msg)
    return wrapped  # type: ignore[return-value]
