"""Policy test: long-poll / streaming views are ``non_atomic_requests`` (Story 43.3)."""

from __future__ import annotations

import importlib

import pytest
from django.db import transaction
from django_pyforge.non_atomic import NON_ATOMIC_VIEW_NAMES


def _resolve_view(qualified: str):
    module_name, attr = qualified.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr)


@pytest.mark.parametrize("qualified", sorted(NON_ATOMIC_VIEW_NAMES))
def test_listed_view_is_non_atomic(qualified: str) -> None:
    view = _resolve_view(qualified)
    marker = getattr(view, "_non_atomic_requests", False)
    assert marker, (
        f"{qualified} must be wrapped with transaction.non_atomic_requests"
    )


def test_registry_matches_transaction_helper() -> None:
    """Every listed view name resolves and is marked non-atomic."""
    assert NON_ATOMIC_VIEW_NAMES, "policy registry must not be empty"
    for qualified in NON_ATOMIC_VIEW_NAMES:
        view = _resolve_view(qualified)
        assert transaction.non_atomic_requests.__name__ in repr(view) or getattr(
            view,
            "_non_atomic_requests",
            False,
        )
