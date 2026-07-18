"""Upstream-event source + cursor logic for the Story G3 sensors (FR-6, § 5.9).

This is the **dagster-free half** of the event-driven ingestion surface: the
event parsing, the cursor-based dedupe, and the run/skip DECISION all live here,
with NO ``dagster`` import — so the incremental-trigger logic is unit-testable
offline and the AD-1 import-ban stays satisfied (only
``orchestration/definitions.py`` imports ``dagster`` / wraps this decision in a
:class:`dagster.SensorDefinition`). Splitting it this way keeps the C1 rule
"``orchestration/definitions.py`` is the ONE dagster-importing module" exactly
as-is (``tests/catalog/test_no_inline_io.py`` ``AD1_GLUE_EXEMPT``).

**Event source = RSS/poll cursor (resolved at G3, spec § 5.9 / Q2 revisit).**
An :data:`EventSource` is a zero-arg callable returning the CURRENT feed
snapshot (a list of raw event mappings — the shape an Atom/RSS poll of e.g.
``pypi.org/rss/updates.xml`` or a repo's ``releases.atom`` yields once parsed to
dicts). The sensor owns the dedupe: a monotonic ``seq`` per event + a Dagster
cursor holding the last-processed ``seq`` (classic RSS-sensor pattern). Webhooks
were rejected as the default: an inbound webhook needs a bound public ingress,
which drags in the persistent-daemon/networking question and cannot be exercised
offline — an RSS/poll snapshot is injectable as a fixture with NO network.

The default production source (:func:`offline_event_source`) returns ``[]`` — the
LIVE feed poller is the attended daemon bring-up (DW-G3), mirroring DW-C1-1. The
source is INJECTABLE so the gate drives a simulated event with no network.

Incrementality (AD-5) is NOT this module's job: a sensor decision only TRIGGERS
an existing C1 job (:data:`SensorDecision.run` → one ``RunRequest``); the
re-fetch-only-stale-rows behaviour belongs to the job's
``IncrementalParquetDataset`` (Story A3). The sensor never re-fetches anything.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable

# A source is a zero-arg callable returning the current feed snapshot. Kept as a
# plain type alias (no dagster, no typing.Protocol overhead) — anything callable
# that yields a sequence of mappings qualifies (a lambda over a fixture in the
# gate; the deferred live RSS poller in production).
EventSource = Callable[[], Sequence[Mapping[str, Any]]]


@dataclass(frozen=True)
class UpstreamEvent:
    """A single validated upstream change.

    ``seq`` is the monotonic dedupe key (an integer sequence id / feed position —
    strictly increasing per source); ``identifier`` is the human-readable subject
    (a package or repo name) carried only for messaging/observability.
    """

    seq: int
    identifier: str


@dataclass(frozen=True)
class SensorDecision:
    """The pure run/skip verdict a sensor tick resolves to.

    ``run`` True  → the wrapper yields ONE ``RunRequest`` keyed by ``run_key`` and
                    advances the cursor to ``new_cursor``.
    ``run`` False → the wrapper yields a ``SkipReason`` (``skip_reason``); the
                    cursor is left untouched (``new_cursor`` == the input cursor).

    Multiple new events in one tick COALESCE into a single decision (``events``
    holds them all) — the triggered job is incremental (AD-5), so one run drains
    every stale row; firing N runs for N events would be redundant re-work.
    """

    run: bool
    run_key: str | None
    new_cursor: str | None
    skip_reason: str | None
    events: tuple[UpstreamEvent, ...]


def offline_event_source() -> list[Mapping[str, Any]]:
    """The default production source: NO events, NO network (DW-G3).

    The live RSS/poll feed reader is the attended daemon bring-up; until then the
    sensors are wired but yield only ``SkipReason`` (they never fire a spurious
    run). The gate injects its own fixture source instead of this one.
    """
    return []


def _parse_event(raw: Mapping[str, Any]) -> UpstreamEvent | None:
    """Defensively coerce one raw feed item into an :class:`UpstreamEvent`.

    A malformed payload (non-Mapping, missing/non-int/negative ``seq``, or a
    missing/``None`` ``id``) is DROPPED (returns ``None``) rather than raising —
    one bad item in a feed must not sink the whole tick (Reviewer-B: degrade,
    never crash the daemon).
    """
    if not isinstance(raw, Mapping):
        return None
    try:
        seq = int(raw["seq"])
    except (KeyError, TypeError, ValueError):
        return None
    if seq < 0:
        return None
    identifier = raw.get("id")
    if identifier is None:  # missing OR explicit None — no subject to name
        return None
    return UpstreamEvent(seq=seq, identifier=str(identifier))


def _cursor_to_seq(cursor: str | None) -> int:
    """Last-processed ``seq`` from the persisted cursor (``-1`` when unset/garbage
    → every event counts as new on a cold cursor)."""
    if not cursor:
        return -1
    try:
        return int(cursor)
    except (TypeError, ValueError):
        return -1


def evaluate_events(
    raw_events: Sequence[Mapping[str, Any]],
    cursor: str | None,
    *,
    run_key_prefix: str,
) -> SensorDecision:
    """Resolve a feed snapshot + the persisted cursor into a run/skip decision.

    Dedupe is cursor-based: only events with ``seq`` strictly greater than the
    cursor's last-processed ``seq`` are new. Events sharing a ``seq`` within one
    snapshot collapse to one (``seq`` is the identity), so ``event_count`` reflects
    distinct changes. New events coalesce into ONE decision whose ``run_key`` =
    ``f"{run_key_prefix}:{max_seq}"`` (so an identical re-tick that somehow
    re-presents the same events is also deduped at the instance level by run_key)
    and whose ``new_cursor`` = ``str(max_seq)``. No new events → skip, cursor
    unchanged.

    Assumes a MONOTONIC, snapshot-complete feed: the cursor jumps to the snapshot
    max, so an event with a lower ``seq`` that arrives LATE in a subsequent tick is
    not re-triggered. That is acceptable here because the triggered job is
    TTL-incremental (AD-5) — a missed row is picked up by the next scheduled run —
    so the sensor is a latency optimization, never the sole ingestion path.
    """
    last_seq = _cursor_to_seq(cursor)
    parsed = [ev for ev in (_parse_event(r) for r in raw_events) if ev is not None]
    # dedupe by seq (last item for a given seq wins) so event_count counts distinct
    # changes, not repeated feed entries; then order by seq.
    deduped = {ev.seq: ev for ev in parsed if ev.seq > last_seq}
    new = sorted(deduped.values(), key=lambda e: e.seq)
    if not new:
        return SensorDecision(
            run=False,
            run_key=None,
            new_cursor=cursor,
            skip_reason="no new upstream events",
            events=(),
        )
    max_seq = new[-1].seq
    return SensorDecision(
        run=True,
        run_key=f"{run_key_prefix}:{max_seq}",
        new_cursor=str(max_seq),
        skip_reason=None,
        events=tuple(new),
    )
