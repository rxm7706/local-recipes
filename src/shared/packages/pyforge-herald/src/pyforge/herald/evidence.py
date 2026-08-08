"""Evidence link validation (Story 6.4, AD-15) -- shared infrastructure so
every later Moment (Epic 9's claim publish, Epic 10's notice authoring)
validates evidence links through one library, not a copy each.

**HTTP client reuse.** This module deliberately does not add ``requests``
(or any second HTTP client) as a new dependency: ``mcp`` -- already a
run-dependency since Story 1.2 -- transitively ships ``httpx2`` (an
httpx-compatible client; ``transport/base.py``'s own docstring already
assumes "an ``httpx``-style ``.response.status_code``" for a comparable
Design-side check), so this module uses that. ``validate_link`` and
``schedule_async_validation`` both accept an injectable ``client`` (a plain
duck-typed object exposing ``.head(url)`` -- see ``_HttpClient`` below), so
a test never has to reach the network; the package's own ``deny_network``
autouse fixture (``tests/conftest.py``) would fail any test that forgot to
inject one.

**Sync validation (AD-15's "404 on publish" half).** ``validate_link``
issues one HTTP ``HEAD`` request, following redirects up to
``MAX_REDIRECTS`` hops (``httpx2.Client(max_redirects=3)`` raises
``TooManyRedirects`` on a 4th -- checked via ``len(history) > max_redirects``
inside httpx2 itself, so ``max_redirects=3`` genuinely permits three hops,
not two). ``validate_for_publish`` wraps it and raises ``EvidenceLinkError``
naming the URL when the link is not valid -- the publish-time rejection the
AC describes; **wiring it into an actual publish command is Epic 9's scope**,
same boundary Story 6.3 draws around ``herald success publish``'s own stub.

**Async validation (AD-15's "weekly stale-link check" half).**
``schedule_async_validation`` is a plain synchronous callable, not a real
background job -- per this story's own implementation notes, adding a
scheduler dependency (Celery or similar) for one weekly re-check is exactly
the kind of speculative weight this repo's "lean dependency" doctrine
argues against. The callable itself *is* the schedulable unit: whatever
already triggers periodic work in this repo (a cron entry, a pixi task) can
invoke it directly. It re-validates every entry in ``previous`` and flags
``is_stale=True`` on any whose ``last_validated_at`` was already older than
``stale_after`` *before* this call -- signalling "this one had gone
unchecked past the window" for operator review, per the AC's own "marks
stale for operator review" wording; the actual notification mechanism is
explicitly out of scope (the AC says so directly).

**Deliberately not implemented (see this story's own spec Design Notes for
the full rationale):** a persistent result cache, and rate-limit-aware
batching. Both are scale concerns with no evidence of scale yet (a handful
of claim/notice links, checked at most weekly) -- adding them now would be
speculative weight ahead of the need, not a base this story is required to
lay.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx2

from .errors import EvidenceLinkError

logger = logging.getLogger(__name__)

MAX_REDIRECTS = 3
"""AD-15's "follows up to 3 hops" cap."""

WARN_REDIRECT_CHAIN_LENGTH = 2
"""A chain longer than this (i.e. 3+ hops) is flagged as fragile, per the
AC's "warns if chain > 2" -- still valid if the final hop is 200-299."""

STALE_AFTER = timedelta(days=7)
"""AD-15's "async weekly validation" window."""

DEFAULT_TIMEOUT_SECONDS = 5.0


class _HttpClient(Protocol):
    """The one method this module calls on an HTTP client -- real
    (``httpx2.Client``) or a hand-written test fake. Duck-typed, not an
    ABC, mirroring ``transport/base.py``'s ``ToolCaller``/``DesignTransport``
    convention."""

    def head(self, url: str) -> Any: ...


@dataclass(frozen=True)
class LinkValidation:
    """One evidence link's validation result -- the library's public
    return shape for both the sync and async paths."""

    url: str
    is_valid: bool
    status: int | None
    redirects: int
    last_validated_at: datetime
    is_stale: bool = False


def _make_client(timeout: float) -> httpx2.Client:
    return httpx2.Client(
        follow_redirects=True, max_redirects=MAX_REDIRECTS, timeout=timeout
    )


def validate_link(
    url: str,
    *,
    client: _HttpClient | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> LinkValidation:
    """One evidence link's validation: HTTP ``HEAD``, redirects followed up
    to ``MAX_REDIRECTS`` hops, ``is_valid`` true for a 200-299 final status.

    Never raises for an ordinary "the link is broken" outcome (404, 403,
    connection failure, too many redirects) -- those all resolve to
    ``is_valid=False`` with ``status=None`` when no response was ever
    received. ``validate_for_publish`` is the layer that turns "not valid"
    into a raised error; this function only measures."""
    owns_client = client is None
    active: _HttpClient = client if client is not None else _make_client(timeout)
    try:
        try:
            response = active.head(url)
        except (httpx2.HTTPError, httpx2.InvalidURL):
            return LinkValidation(
                url=url,
                is_valid=False,
                status=None,
                redirects=0,
                last_validated_at=datetime.now(UTC),
            )
        redirects = len(response.history)
        is_valid = 200 <= response.status_code < 300
        if redirects > WARN_REDIRECT_CHAIN_LENGTH:
            logger.warning(
                "evidence link %s has a %d-hop redirect chain; may be fragile",
                url,
                redirects,
            )
        return LinkValidation(
            url=url,
            is_valid=is_valid,
            status=response.status_code,
            redirects=redirects,
            last_validated_at=datetime.now(UTC),
        )
    finally:
        if owns_client:
            active.close()  # type: ignore[attr-defined]


def validate_for_publish(
    url: str,
    *,
    client: _HttpClient | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> LinkValidation:
    """``validate_link`` plus AD-15's publish-time gate: raises
    ``EvidenceLinkError`` naming ``url`` when the link is not valid.

    Not wired into any CLI command yet -- the actual publish flow is Epic
    9's scope (Story 6.3's own stub boundary); this is the library call a
    future story wires in."""
    result = validate_link(url, client=client, timeout=timeout)
    if not result.is_valid:
        raise EvidenceLinkError(
            f"Evidence link broken: {url}. Fix or remove before publishing."
        )
    return result


def schedule_async_validation(
    previous: Sequence[LinkValidation],
    *,
    stale_after: timedelta = STALE_AFTER,
    client: _HttpClient | None = None,
    now: Callable[[], datetime] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[LinkValidation]:
    """Re-validate every entry in ``previous`` (AD-15's weekly job): a fresh
    ``LinkValidation`` per URL, with ``is_stale=True`` on any entry whose
    prior ``last_validated_at`` was already more than ``stale_after`` old
    *before* this run -- the "overdue, worth a look" signal for operator
    review. ``now`` is injectable so a test never depends on the real
    clock."""
    clock = now if now is not None else (lambda: datetime.now(UTC))
    current_time = clock()
    owns_client = client is None
    active: _HttpClient = client if client is not None else _make_client(timeout)
    try:
        results: list[LinkValidation] = []
        for entry in previous:
            was_stale = (current_time - entry.last_validated_at) > stale_after
            fresh = validate_link(entry.url, client=active, timeout=timeout)
            # Stamped with the batch's own `current_time`, not each call's
            # real wall-clock moment -- so every entry in one run shares
            # one `last_validated_at`, and an injected `now` (tests, or a
            # deterministic scheduler) is honored end to end.
            results.append(
                replace(fresh, is_stale=was_stale, last_validated_at=current_time)
            )
        return results
    finally:
        if owns_client:
            active.close()  # type: ignore[attr-defined]
