"""``herald deck watch`` -- Epic 4's CAP-4 (Design -> repo autopull).

Story 4.1: the poll loop + quiescence debounce (4.2's idle backoff and 4.3's
halt-on-auth-error land in this same module, in their own stories). Each
watched deck is polled independently, on its own schedule, for its
prototype's etag via ``transport.read_file`` with
``if_none_match`` set to the deck's last confirmed-stable etag -- a
steady-state poll (nothing has changed since that etag) therefore never
transfers a body: the ``if_none_match`` hit short-circuits to
``{unchanged: true}`` (``bridge-protocol.md`` /
``transport.base.parse_read_response``). The one case that DOES transfer a
body without landing a pull is a poll that finds the file still mid-edit
(the candidate etag recorded on the PREVIOUS poll no longer matches) -- the
port has no lighter-weight "etag only, always" primitive than
``read_file``'s own conditional-read short-circuit, so settling on a
still-changing file necessarily costs one body transfer per settling
attempt. That is the unavoidable cost of the debounce itself, not the
steady-state cost FR-14/NFR-08 target -- the true idle path (the common
case for a long-quiet deck) transfers nothing.

**Debounce (Story 4.1, FR-15).** Each deck tracks a ``confirmed_etag`` (the
etag ``pull`` last landed, seeded from ``state.py``) and an optional
``pending_etag`` (a candidate seen on the previous poll, not yet landed):

* No pending candidate: poll ``if_none_match=confirmed_etag``. Unchanged ->
  truly idle, nothing to do. Changed -> a candidate etag was seen; record it
  as ``pending_etag`` and wait -- do not pull yet.
* A pending candidate: poll ``if_none_match=pending_etag``. Unchanged -> the
  candidate has now held across one full poll interval (FR-15's "settled"
  test) -- trigger the real pull (``deck_pipeline.pull_prototype``, which
  re-reads, re-derives, and records the new ``confirmed_etag`` in
  ``state.py``). Changed again -> the edit is still in flight; replace
  ``pending_etag`` with the newer candidate and keep waiting.

**Halt on auth error (Story 4.3, FR-17).** ``AuthError`` (a
``TransportError`` subclass) is never caught here -- it propagates out of
``watch`` exactly like every other ``HeraldError`` bridge-core raises (AD-6:
``cli.dispatch`` is the sole catch point), which is what stops the WHOLE
loop -- every watched deck, not just the one whose poll failed -- with no
retry: the loop simply never resumes after the exception leaves this
function.

Time is injected (``now``/``sleep``), mirroring ``deck_pipeline.py``'s own
``now: Callable[[], datetime]`` convention, so tests drive N simulated poll
cycles with no real wall-clock wait."""

from __future__ import annotations

import time as _time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from . import state
from .deck_pipeline import (
    PROTOTYPE_ARTIFACT_KEY,
    PullResult,
    _persona_from_slug,
    _require_seeded_state,
    pull_prototype,
)

if TYPE_CHECKING:
    # Mirrors bridge.py's own TYPE_CHECKING-only import: `watch`'s signature
    # needs `DesignTransport` only as a type annotation, never at runtime
    # (every call against `transport` below goes through the protocol's
    # methods directly, with no isinstance check) -- importing the package
    # eagerly here would execute `transport/__init__.py`, which re-exports
    # the concrete `McpTransport` (AD-3/AD-4's determinism boundary).
    from .transport.base import DesignTransport

DEFAULT_POLL_INTERVAL = 60.0
"""FR-14's default poll interval, in seconds."""

MIN_POLL_INTERVAL = 30.0
"""NFR-09's hard floor -- a caller-requested interval below this is clamped
up, never honored as given."""


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class WatchEvent:
    """One observable step of the watch loop, reported to ``on_event`` when
    a caller supplies one -- tests assert on the sequence; an interactive
    CLI could log it. Never required for the loop's own correctness."""

    slug: str
    kind: str  # "idle" | "settling" | "pulled"
    interval: float


@dataclass
class _DeckWatch:
    slug: str
    project_id: str
    remote_path: str
    interval: float
    confirmed_etag: str | None
    pending_etag: str | None = None


def _clamp_interval(interval: float) -> float:
    return max(interval, MIN_POLL_INTERVAL)


def _make_deck(slug: str, *, state_path: Path, interval: float) -> _DeckWatch:
    existing = _require_seeded_state(state_path, slug)
    persona = _persona_from_slug(slug)
    remote_path = f"PyForge {persona}.dc.html"
    return _DeckWatch(
        slug=slug,
        project_id=existing.project_id,
        remote_path=remote_path,
        interval=interval,
        confirmed_etag=existing.etags.get(PROTOTYPE_ARTIFACT_KEY),
    )


def _poll_deck(
    transport: DesignTransport,
    deck: _DeckWatch,
    *,
    repo_root: Path,
    state_path: Path,
    pull: Callable[..., PullResult],
    now: Callable[[], datetime],
    on_event: Callable[[WatchEvent], None] | None,
) -> None:
    reference_etag = deck.pending_etag or deck.confirmed_etag
    file_read = transport.read_file(
        project_id=deck.project_id,
        path=deck.remote_path,
        if_none_match=reference_etag,
    )
    if file_read.unchanged:
        if deck.pending_etag is not None:
            # The candidate seen last poll has now held across one full
            # interval (FR-15) -- pull for real.
            deck.pending_etag = None
            result = pull(
                transport,
                slug=deck.slug,
                repo_root=repo_root,
                state_path=state_path,
                now=now,
            )
            deck.confirmed_etag = result.etag or deck.confirmed_etag
            if on_event is not None:
                on_event(WatchEvent(deck.slug, "pulled", deck.interval))
            return
        # Truly idle: nothing has changed since the last confirmed etag.
        if on_event is not None:
            on_event(WatchEvent(deck.slug, "idle", deck.interval))
        return
    # Changed since the reference etag: a new (or still-moving) candidate.
    deck.pending_etag = file_read.etag
    if on_event is not None:
        on_event(WatchEvent(deck.slug, "settling", deck.interval))


def watch(
    transport: DesignTransport,
    *,
    slugs: Sequence[str],
    repo_root: Path,
    interval: float = DEFAULT_POLL_INTERVAL,
    state_path: Path | None = None,
    max_polls_per_deck: int | None = None,
    pull: Callable[..., PullResult] | None = None,
    now: Callable[[], datetime] | None = None,
    sleep: Callable[[float], None] | None = None,
    on_event: Callable[[WatchEvent], None] | None = None,
) -> None:
    """CAP-4: poll every deck in ``slugs`` forever (or ``max_polls_per_deck``
    polls each, for tests), pulling only once an edit has settled.

    Each deck runs on its own schedule (initially ``interval``, clamped to
    ``MIN_POLL_INTERVAL`` -- NFR-09): the loop always services whichever
    watched deck is next due, sleeping exactly the gap via the injected
    ``sleep``. Every watched deck must already be seeded
    (``_require_seeded_state``, the same precondition ``pull_prototype``
    itself enforces) -- raised before the loop's first poll, so a typo'd
    slug fails immediately rather than mid-loop.

    Raises whatever ``HeraldError`` a poll or a pull raises -- in particular
    ``AuthError`` (Story 4.3) is never caught here, so it halts every
    watched deck at once, with no retry of the failed poll."""
    if not slugs:
        raise ValueError("watch requires at least one slug")
    resolved_now = now or _default_now
    resolved_sleep = sleep or _time.sleep
    resolved_pull = pull or pull_prototype
    resolved_state_path = (
        repo_root / state.DEFAULT_STATE_PATH if state_path is None else state_path
    )
    clamped = _clamp_interval(interval)

    decks = {
        slug: _make_deck(slug, state_path=resolved_state_path, interval=clamped)
        for slug in slugs
    }
    poll_counts = {slug: 0 for slug in slugs}
    due_in = {slug: 0.0 for slug in slugs}  # seconds until each deck's next poll

    while True:
        next_slug = min(due_in, key=lambda s: due_in[s])
        wait = due_in[next_slug]
        if wait > 0:
            resolved_sleep(wait)
            for slug in due_in:
                due_in[slug] -= wait
        deck = decks[next_slug]
        _poll_deck(
            transport,
            deck,
            repo_root=repo_root,
            state_path=resolved_state_path,
            pull=resolved_pull,
            now=resolved_now,
            on_event=on_event,
        )
        poll_counts[next_slug] += 1
        due_in[next_slug] = deck.interval
        if (
            max_polls_per_deck is not None
            and poll_counts[next_slug] >= max_polls_per_deck
        ):
            if all(count >= max_polls_per_deck for count in poll_counts.values()):
                return
            due_in[next_slug] = float("inf")  # this deck is done; let others catch up
