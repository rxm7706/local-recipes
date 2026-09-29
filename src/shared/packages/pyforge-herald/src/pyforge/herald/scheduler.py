"""Scheduled-job composition (Story 13.5): the operator/cron-facing
``herald scheduler run`` entry point composes the two operations Story
8.2/9.5 already scaled down to on-demand CLI verbs -- evidence
revalidation (``claims.revalidate_all``, the same call ``herald success
validate --all`` makes) and the progress snapshot export
(``progress.write_snapshot``) -- into one invocation, so a single cron
line keeps both AD-15's 7-day evidence-staleness window and the web
dashboard's Progress tab current without an operator remembering to run
either by hand.

**No new scheduler dependency.** ``evidence.py``'s own module docstring
already settled this: adding a scheduler dependency (APScheduler, Celery,
or similar) for one weekly re-check is exactly the kind of speculative
weight this repo's lean-dependency doctrine argues against. This module
*is* the schedulable unit -- "whatever already triggers periodic work in
this repo (a cron entry, a pixi task) can invoke it directly," per that
same docstring. ``cli.py``'s ``herald scheduler run`` is the invocable
command; a documented local ``crontab`` entry
(``docs/cli-runbooks.md``) is the trigger -- never a GitHub Actions
workflow (see this story's spec Design Notes: a GH-hosted runner would
never have populated the gitignored, operator-local ``.herald/herald.db``
it would be validating).

**Both jobs run unconditionally, every invocation.** Neither job filters
by the 7-day staleness window in code -- that window is enforced entirely
by the *trigger's* cadence (a ~weekly cron line), exactly the framing
``evidence.schedule_async_validation``'s own docstring already uses. A
claim whose evidence was checked five minutes ago is revalidated again
exactly like one checked five weeks ago; the cron cadence, not in-code
filtering, is the whole enforcement mechanism.

**Never gated on the operator role.** Mirrors ``success validate``'s own
ungated behavior (AD-16): revalidation/export only refresh derived state
(``validated``/``validated_at``, the progress snapshot) -- neither creates
or modifies claim/progress content, so neither needs the write gate real
content mutations require.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import claims, progress
from . import evidence as evidence_mod
from .errors import HeraldError


def _default_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class EvidenceRevalidationResult:
    """``run_evidence_revalidation``'s return shape."""

    claims_checked: int
    broken_evidence_claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class ProgressAggregationResult:
    """``run_progress_aggregation``'s return shape."""

    records_aggregated: int
    snapshot_path: Path


@dataclass(frozen=True)
class SchedulerRunResult:
    """``run_scheduled_jobs``'s return shape -- both jobs' results composed
    into one object, exactly the shape ``cli.py``'s ``herald scheduler
    run`` prints (plain text) or serializes (``--json``)."""

    claims_checked: int
    broken_evidence_claim_ids: tuple[str, ...]
    records_aggregated: int
    snapshot_path: Path


def run_evidence_revalidation(
    claims_path: Path,
    *,
    validate: Callable[[str], evidence_mod.LinkValidation] | None = None,
    now: Callable[[], datetime] = _default_now,
) -> EvidenceRevalidationResult:
    """Thin wrapper over ``claims.revalidate_all`` -- same semantics as
    ``herald success validate --all`` (never raises on a broken link;
    updates ``validated``/``validated_at`` for every claim's evidence).

    A claim id lands in ``broken_evidence_claim_ids`` when, after this
    run, it carries at least one evidence entry that was actually
    revalidated (stamped with this run's own timestamp) and found
    invalid -- the set of claims worth an operator's attention right now.
    This is not a diff against a prior run: ``revalidate_all`` does not
    track "was this already broken before," and computing that would mean
    a second read of the pre-run state for no behavioral gain (the
    Boundaries constraint is "name the claim," not "distinguish
    newly-broken from still-broken").

    Filtering on this run's own timestamp (rather than any
    ``validated=False`` entry) matters because ``revalidate_all`` leaves a
    claim byte-for-byte unchanged when a concurrent writer raced it (its
    own docstring's discard-stale-on-conflict rule) -- such a claim can
    still carry ``validated=False`` evidence from before this call ever
    ran, e.g. a brand new claim created mid-run whose evidence was never
    checked at all. Naming it here would misreport "broken" for a claim
    this run never actually touched.

    ``validate`` passes straight through to ``claims.revalidate_all``
    unchanged (resolved to a real default there, not here -- see that
    function's own docstring for why) -- injectable so a test never
    reaches the network. ``now`` is resolved once, here, and pinned for
    the whole call -- ``revalidate_all`` already shares one timestamp
    across its own batch (its own docstring), so pinning it here too
    means every entry this run actually revalidates carries the exact
    stamp compared against below."""
    resolved_now = now()
    updated = claims.revalidate_all(claims_path, validate=validate, now=lambda: resolved_now)
    stamp = resolved_now.isoformat()
    broken_ids = tuple(
        claim.id for claim in updated if any(not e.validated and e.validated_at == stamp for e in claim.evidence)
    )
    return EvidenceRevalidationResult(claims_checked=len(updated), broken_evidence_claim_ids=broken_ids)


def run_progress_aggregation(progress_path: Path, out_dir: Path) -> ProgressAggregationResult:
    """Thin wrapper over ``progress.write_snapshot`` -- writes
    ``out_dir/progress.json`` from every currently-stored progress record,
    the same shape ``scripts/export_progress_snapshot.py`` has always
    produced (that script now delegates to the same
    ``progress.write_snapshot`` call this makes).

    Reads ``progress.list_records`` once more than ``write_snapshot``
    itself does, purely to report ``records_aggregated`` in the summary --
    an acceptable second read for a job that runs, at most, weekly against
    a handful of local rows (Simplicity First: threading a count out of
    ``write_snapshot`` itself would change its signature for every other
    caller for one extra integer)."""
    records_aggregated = len(progress.list_records(progress_path))
    snapshot_path = progress.write_snapshot(progress_path, out_dir)
    return ProgressAggregationResult(records_aggregated=records_aggregated, snapshot_path=snapshot_path)


def run_scheduled_jobs(
    *,
    claims_path: Path,
    progress_path: Path,
    out_dir: Path,
    validate: Callable[[str], evidence_mod.LinkValidation] | None = None,
    now: Callable[[], datetime] = _default_now,
) -> SchedulerRunResult:
    """``herald scheduler run``'s whole job: evidence revalidation, then
    progress aggregation, composed into one result. Both run
    unconditionally on every call (module docstring) -- there is no
    early-return or skip path for either job here.

    The two jobs are independent (composed, not chained): if evidence
    revalidation raises a ``HeraldError`` (e.g. a claims-store problem),
    progress aggregation still runs before the error is re-raised, so a
    broken claims store never silently stops the progress snapshot from
    refreshing on its own cadence. An aggregation failure propagates
    immediately, same as before -- there is nothing after it to still
    attempt."""
    revalidation_error: HeraldError | None = None
    try:
        revalidation = run_evidence_revalidation(claims_path, validate=validate, now=now)
    except HeraldError as exc:
        revalidation_error = exc
        revalidation = EvidenceRevalidationResult(claims_checked=0, broken_evidence_claim_ids=())
    aggregation = run_progress_aggregation(progress_path, out_dir)
    if revalidation_error is not None:
        raise revalidation_error
    return SchedulerRunResult(
        claims_checked=revalidation.claims_checked,
        broken_evidence_claim_ids=revalidation.broken_evidence_claim_ids,
        records_aggregated=aggregation.records_aggregated,
        snapshot_path=aggregation.snapshot_path,
    )
