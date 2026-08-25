"""Host analytical board: one URL, steward filter-then-search (canopy AD-20).

Isolation is server-side only. Identity is this request's IdP token roles
(18.2), never trusted ingress headers on the host.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from django.core.cache import cache
from django.http import HttpRequest
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from pyforge.steward.dashboard.cache import get_master_dataset
from pyforge.steward.dashboard.declarations import AccessDeclaration
from pyforge.steward.dashboard.filtering import filter_by_role
from pyforge.steward.dashboard.filtering import search

from django_pyforge.access import require_station_role
from django_pyforge.roles import roles_from_request

BOARD_CACHE_KEY = "atlas-board-master"
BOARD_DECLARATION = AccessDeclaration(access_column="tenant", roles=("east", "west"))

# In-process fixture master: skewed (more east than west) so isolation is
# not vacuous when two roles share ``/stations/atlas/board/``.
_MASTER_ROWS: tuple[dict[str, Any], ...] = (
    {"id": 1, "tenant": "east", "label": "east-a"},
    {"id": 2, "tenant": "east", "label": "east-b"},
    {"id": 3, "tenant": "east", "label": "east-c"},
    {"id": 4, "tenant": "west", "label": "west-a"},
    {"id": 5, "tenant": "west", "label": "west-b"},
)


def fetch_master_dataset() -> tuple[dict[str, Any], ...]:
    """Return the unfiltered master. The cache stores this frame only."""
    return tuple(copy.deepcopy(row) for row in _MASTER_ROWS)


def row_role_from_token(token_roles: frozenset[str]) -> str | None:
    """Unique intersection of token roles with the declaration vocabulary.

    Zero or multiple matches fail closed (``role=None`` → empty frame).
    Station role ``atlas`` is reachability, not a row tag.
    """
    matched = token_roles & frozenset(BOARD_DECLARATION.roles)
    if len(matched) != 1:
        return None
    return next(iter(matched))


def _keep_all(_row: Mapping[str, Any]) -> bool:
    return True


@require_GET
@require_station_role("atlas")
def board_view(request: HttpRequest) -> JsonResponse:
    """Serve role-sliced rows at one path for every caller (canopy AD-20)."""
    master = get_master_dataset(BOARD_CACHE_KEY, fetch_master_dataset, cache=cache)
    role = row_role_from_token(roles_from_request(request))
    filtered = filter_by_role(master, BOARD_DECLARATION, role)
    rows = search(filtered, _keep_all)
    response = JsonResponse({"rows": [dict(row) for row in rows]})
    response["Cache-Control"] = "no-store"
    return response
