"""``marshal status`` (Story 5.1, FR-36/AD-5) -- a NEW top-level command,
sibling to ``homes``/``deploy``/``land``/``retire``: one row per loop home
across the whole fleet, reporting RUNTIME state (idle/running/paused-on-
escalation/stopped/unsupervised), the current story, elapsed time, and
budget consumed -- derived ENTIRELY from journals and run state, never from
any hand-maintained file (AD-5). ``marshal homes`` (Story 1.6) already
enumerates every home and verifies its Tier-3 ISOLATION; this command is a
DIFFERENT, sibling concern -- runtime state, not structural correctness --
and coexists with it rather than replacing it.

**Fleet enumeration mirrors ``marshal homes``/``marshal retire`` exactly**
(``VcsPort.list_worktrees`` against the repo root resolved from
``Path.cwd()``, every entry whose ``.branch`` starts with ``"loop/"`` names
one project's slug). ``--project SLUG`` scopes the report to one project
(the SAME precedent ``marshal retire`` already establishes) -- a slug
naming no currently-attached loop home reports a clean, empty
``data.homes: []``, never a finding (the spec's own I/O matrix: "a typo/
torn-down project").

**Per-home evidence gathering reuses ``cli/spin.py``'s own established read
sequence** (``_latest_run_dir``, imported locally to avoid the documented
``cli.deploy``/``cli.init`` load-order cycle, mirrored here for the
identical reason ``cli/retire.py``'s own local import already documents):
the most recent Marshal run directory for a project supplies its own
journal, folded via ``core.journal.fold`` (the SAME read mechanism
``cli/spin.py::_resolve_harness_run_id_for_resume`` already established --
never a second, independent journal-reading mechanism) to recover the
supervisor's own self-journaled pid (``cli/spin.py``'s own spin-launch
outcome payload, ``{"pid": spin_result.pid, "harness_run_id": ...}``) and,
best-effort, the last ``"budget-usage"`` observation's ``cost_estimate``
(Story 3.6's own supervisor-journaled quantity -- reported, never
recomputed live, per NFR-14). ``HarnessPort.run_status_snapshot`` (keyed by
the SAME recovered ``harness_run_id``) supplies bmad-loop's own
``paused_stage``/``finished``/``tasks``. ``core.status.derive_home_state``
(Story 5.1's own new pure function) turns those facts into one of the
closed 5-value state vocabulary, with ``ProcessPort.is_alive(pid)``
(Story 3.4's own supervisor-liveness primitive) overriding every other
derived state for a dead supervisor on a run that has not itself finished.

**A malformed/unreadable journal for one home never aborts the sweep**
(mirrors ``marshal retire``'s own "one project's bad data never blocks the
rest of the fleet" precedent): that row alone degrades to an ``"unknown"``-
shaped state with one ``MRS-STATUS-002`` WARN naming the home; every other
home's row is unaffected. The SAME code also covers the coarser failure of
``VcsPort.list_worktrees`` itself raising (the fleet cannot even be
enumerated) -- reported as one WARN over an otherwise-empty report, never a
crash.

No ``sprint-status.yaml``, ledger, or any other hand-maintained feed is ever
read for the fleet summary or ``--run`` detail views above (AD-5's own
explicit prohibition) -- see ``core/status.py``'s own module-level
docstring section for the pure derivation core this module feeds.

**Story 5.4's ``--reconcile-ledger`` view is the ONE deliberate exception**
(FR-39/FR-40): it reads the TRACKED ``sprint-status-ledger.yaml`` twin --
never the gitignored Tier-3 feed AD-5 forbids everywhere else in this
module -- explicitly to compare it against git's own durably-merged story
keys and report any disagreement by name. See ``_reconcile_ledger``'s own
docstring below.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..adapters.clock_system import SystemClock
from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness, HarnessError
from ..adapters.process_posix import PosixProcess
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import policy as policy_core
from ..core import promotion
from ..core import status as status_core
from ..core.identity import MalformedStoryKeyError, normalize
from ..core.journal import Phase, fold
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.clock import ClockPort
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.process import ProcessPort
from ..ports.vcs import VcsPort
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
    repo_root,
)

# This module's own local copy of `cli/spin.py`'s journal-shape constants --
# `cli/retire.py` establishes the identical "each module owns its own copy
# of these small literals" precedent (its own `_DONE_PHASE`/
# `_RETIRE_JOURNAL_FILENAME`) rather than importing spin.py's PRIVATE
# `_JOURNAL_FILENAME`/`_LAUNCH_KIND`/`_RESUME_KIND` attributes.
_JOURNAL_FILENAME = "journal.jsonl"
_LAUNCH_KIND = "run-launch"
_RESUME_KIND = "run-resume"

# Code review (2026-08-07, Blind Hunter, the single most severe finding
# against this story): `run-launch`/`run-resume`'s own journaled `"pid"`
# field is the DETACHED HARNESS PROCESS's pid (`cli/spin.py`'s own
# `spin_result.pid`, what that module itself calls `watched_pid` two lines
# later) -- NOT Marshal's own supervisor sidecar, a SEPARATE process
# (`python -m pyforge.marshal.supervisor`) that journals ITS OWN pid under
# `supervisor/__main__.py`'s own `"supervisor-attach"`/`"supervisor-
# heartbeat"` kinds (payload `{"pid": ..., "watched_pid": ...}`). Probing
# the harness's own pid for liveness silently defeats this story's own
# headline safety guarantee: if the SUPERVISOR crashes while the watched
# harness process keeps running (a fully realistic, independent-process
# failure), the harness pid is still alive, so the original code fed
# `supervisor_alive=True` into `derive_home_state` and a truly dead
# supervisor was reported as a healthy state. These two kinds are the
# supervisor's OWN self-journaled liveness evidence -- the most recent one
# (by timestamp, across both kinds) names the pid this module's own
# `ProcessPort.is_alive` probe must actually check.
_SUPERVISOR_ATTACH_KIND = "supervisor-attach"
_SUPERVISOR_HEARTBEAT_KIND = "supervisor-heartbeat"

# Story 3.6's own supervisor-journaled kind (`supervisor/__main__.py::
# _BUDGET_USAGE_KIND`) -- the ONE journaled quantity this command reads for
# "budget consumed" (the spec's own Design Notes: reported, never computed
# live). Reused as a literal for the identical reason `_DONE_PHASE` is.
_BUDGET_USAGE_KIND = "budget-usage"

_MRS_STATUS_002 = "MRS-STATUS-002"

# Story 5.2 (per-run detail, FR-37/NFR-12): `--run <run_id>` requires
# `--project <slug>` alongside it -- a run id alone does not name which
# project's Tier-3 store to look under (run directories nest per-project).
# Checked BEFORE any I/O, the same pre-I/O shape-gate precedent every
# sibling command's own `MRS-INIT-001`/`MRS-SPIN-001`/`MRS-TEARDOWN-001`
# already establishes.
_MRS_STATUS_003 = "MRS-STATUS-003"

# Story 5.4 (ledger-vs-git reconciliation, FR-39/FR-40): three more codes
# in this same MRS-STATUS-* area. `_MRS_STATUS_005` names a tracked
# `sprint-status-ledger.yaml` that could not be read (missing entirely, or
# a parse failure) -- reported, `data.discrepancies` stays empty, never
# fabricated. `_MRS_STATUS_006` is the `--reconcile-ledger` counterpart to
# `_MRS_STATUS_003`'s `--run` precedent: given without `--project`,
# refused before any I/O. `_MRS_STATUS_007` names a `main` commit-history
# read failure while gathering `core.promotion.merged_story_keys`'s
# durability evidence -- mirrors `cli/deploy.py::_MRS_DEPLOY_003`'s
# identical "a REQUIRED read, not a per-row degradation" rationale.
_MRS_STATUS_005 = "MRS-STATUS-005"
_MRS_STATUS_006 = "MRS-STATUS-006"
_MRS_STATUS_007 = "MRS-STATUS-007"

# The tracked ledger's own conventional, fixed path (Story 5.4) -- NEVER
# the gitignored Tier-3 feed AD-5 forbids this command's other views from
# ever reading (see this module's own docstring's closing paragraph).
_LEDGER_RELPATH = "_bmad-output/projects/{slug}/planning-artifacts/sprint-status-ledger.yaml"

# The base branch git's own durable-merge evidence reads against -- the
# SAME hardcoded `"main"` every other `merged_story_keys` caller in this
# package uses (see `core/status.py`'s own module docstring, `cli/deploy.py`
# `_MERGE_BASE_BRANCH`'s identical precedent).
_MERGE_BASE_BRANCH = "main"

_DONE_STATUS = "done"


def add_status_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``status`` subcommand on ``main.py``'s subparser tree --
    a NEW top-level command, sibling to ``deploy``/``land``/``retire`` (the
    story's own Code Map). No required positional argument -- it reports the
    WHOLE fleet by default."""
    parser = subparsers.add_parser(
        "status",
        help="Fleet-wide runtime status: one row per loop home (FR-36/AD-5).",
        description=(
            "For every project with a currently-attached loop-home worktree "
            "(or just --project SLUG), reports runtime state (idle/running/"
            "paused-on-escalation/stopped/unsupervised), the current story, "
            "elapsed time, and budget consumed -- derived entirely from "
            "journals and run state, never a hand-maintained file (AD-5)."
        ),
    )
    parser.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help="Scope the report to one project slug (default: the whole fleet).",
    )
    parser.add_argument(
        "--run",
        default=None,
        metavar="RUN_ID",
        help=(
            "Show per-run detail for RUN_ID instead of the fleet summary "
            "(Story 5.2, FR-37/NFR-12) -- requires --project SLUG alongside it."
        ),
    )
    parser.add_argument(
        "--escalations",
        action="store_true",
        help=(
            "Fleet-summary only (ignored with --run): filter data.homes to "
            "rows currently paused-on-escalation (Story 5.3, FR-38)."
        ),
    )
    parser.add_argument(
        "--reconcile-ledger",
        action="store_true",
        help=(
            "Compare the tracked sprint-status-ledger.yaml's own status: "
            "done story keys against git's own durably-merged story keys, "
            "reporting any disagreement by name (Story 5.4, FR-39/FR-40) "
            "-- requires --project SLUG alongside it. An opt-in extra "
            "read, never folded into the default fleet/run-detail views."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_status)


@dataclass(frozen=True)
class _RunJournalFacts:
    """Already-extracted facts from one run's own ``journal.jsonl`` (a
    single fold, a single file read). ``launch_pid``/``launched_at`` come
    from the run-launch/run-resume OUTCOME entry ``cli/spin.py`` itself
    journals (``{"pid": ..., "harness_run_id": ...}``) -- this is the
    DETACHED HARNESS process's own pid, used ONLY for ``launched_at`` (an
    elapsed-time reference point) and as this module's own "journal
    readable at all" signal; it is NEVER the supervisor-liveness probe's
    own input (see ``_SUPERVISOR_ATTACH_KIND``'s own module-level comment
    for why conflating the two was this story's own most severe review
    finding). ``supervisor_pid`` is the SEPARATE pid the supervisor sidecar
    itself journals under ``"supervisor-attach"``/``"supervisor-
    heartbeat"`` -- the most recent such entry, by timestamp, across both
    kinds; ``None`` when the supervisor never attached at all (treated by
    the caller identically to a confirmed-dead supervisor, the safe
    direction). ``budget_consumed`` is the last ``"budget-usage"``
    observation's ``cost_estimate``, if any, for THIS run_id only.
    ``launch_pid is None`` is this module's own single "could not recover
    enough to report a real state" signal -- a missing/unreadable journal
    file and a journal that never records a usable launch pid degrade
    identically.

    Story 5.2 (per-run detail, FR-37/NFR-12) adds two more fields off the
    SAME fold this dataclass already carries -- never a second fold of the
    same run's journal (Story 5.1's own adversarial review already flagged
    a double-fold as a real, if low-severity, issue). ``budget_by_story``
    is EVERY ``"budget-usage"`` entry's own ``cost_estimate``, grouped by
    ``payload["story_key"]`` (already rendered in Marshal's own dot form
    by ``supervisor/__main__.py::_feed_key_form`` at journal-write time),
    taking each key's own LATEST entry (fold's own chronological
    ``(ts, id)`` order makes ``by_kind``'s own iteration order
    chronological, so "last write wins" here) -- a genuinely different
    aggregation than ``budget_consumed``'s own single "latest overall"
    value, per the spec's own Design Notes. ``open_intents`` is
    ``core.journal.fold``'s own ``FoldResult.open_intents``, already
    rendered to plain JSON-dicts (``JournalEntry.to_json_dict()``) here at
    the CLI boundary -- ``core/status.py`` stays pure and never imports
    ``JournalEntry`` itself."""

    launch_pid: int | None
    launched_at: datetime | None
    supervisor_pid: int | None
    budget_consumed: int | float | None
    budget_by_story: dict[str, int | float] = field(default_factory=dict)
    open_intents: tuple[dict[str, object], ...] = ()
    # Code review (2026-08-07, Blind Hunter, the single most severe finding
    # against Story 5.2): the SAME launch/resume OUTCOME entry this
    # dataclass already scans for `pid` also carries `harness_run_id` --
    # captured here so callers (`_gather_home_facts`/`_run_detail`) never
    # need `cli/spin.py::_resolve_harness_run_id_for_resume`'s OWN
    # independent read+fold of the identical journal file. The original
    # version of this story called that helper anyway, reintroducing the
    # exact double-fold this dataclass's own docstring already claimed
    # (falsely, in that version) was avoided.
    harness_run_id: str | None = None


def _gather_run_journal_facts(
    fs: FsPort, run_dir: Path, run_id: str
) -> _RunJournalFacts:
    """Read+fold ``run_dir``'s own journal ONCE (mirrors ``cli/spin.py::
    _resolve_harness_run_id_for_resume``'s identical read sequence, applied
    to several different payload fields/kinds off the SAME already-folded
    result -- never a second file read). Never raises: any read failure
    (``FsError``, a missing file) or a journal that never records a usable
    launch pid for this run_id reports ``launch_pid=None``, the caller's
    own "journal unreadable" signal."""
    empty = _RunJournalFacts(
        launch_pid=None, launched_at=None, supervisor_pid=None, budget_consumed=None
    )
    try:
        text = fs.read_text(run_dir / _JOURNAL_FILENAME)
    except FsError:
        return empty
    if text is None:
        return empty

    lines = text.split("\n")
    fold_result = fold(lines)

    launch_pid: int | None = None
    launched_at: datetime | None = None
    harness_run_id: str | None = None
    for kind in (_LAUNCH_KIND, _RESUME_KIND):
        for entry in fold_result.by_kind(kind):
            if entry.run_id != run_id or entry.phase is not Phase.OUTCOME:
                continue
            candidate = entry.payload.get("pid")
            if isinstance(candidate, int) and not isinstance(candidate, bool):
                launch_pid = candidate
                try:
                    launched_at = datetime.fromisoformat(entry.ts)
                except ValueError:
                    launched_at = None
                candidate_run_id = entry.payload.get("harness_run_id")
                if isinstance(candidate_run_id, str) and candidate_run_id:
                    harness_run_id = candidate_run_id
                break
        if launch_pid is not None:
            break

    # The supervisor's OWN self-journaled liveness evidence -- the most
    # recent entry, by timestamp, across BOTH kinds (a heartbeat refreshes
    # over the run's lifetime; a run with only the initial attach and no
    # heartbeat yet is still valid evidence).
    supervisor_pid: int | None = None
    supervisor_pid_ts: str | None = None
    for kind in (_SUPERVISOR_ATTACH_KIND, _SUPERVISOR_HEARTBEAT_KIND):
        for entry in fold_result.by_kind(kind):
            if entry.run_id != run_id:
                continue
            candidate = entry.payload.get("pid")
            if not (isinstance(candidate, int) and not isinstance(candidate, bool)):
                continue
            if supervisor_pid_ts is None or entry.ts > supervisor_pid_ts:
                supervisor_pid = candidate
                supervisor_pid_ts = entry.ts

    budget_consumed: int | float | None = None
    budget_by_story: dict[str, int | float] = {}
    usage_entries = [
        entry
        for entry in fold_result.by_kind(_BUDGET_USAGE_KIND)
        if entry.run_id == run_id
    ]
    if usage_entries:
        candidate_cost = usage_entries[-1].payload.get("cost_estimate")
        if isinstance(candidate_cost, (int, float)) and not isinstance(
            candidate_cost, bool
        ):
            budget_consumed = candidate_cost
    # Story 5.2: the SAME `usage_entries`, grouped by `story_key` instead of
    # collapsed to a single overall latest -- `by_kind`'s own chronological
    # order (fold's `(ts, id)` sort) means iterating in order and
    # overwriting per key naturally keeps each key's own LATEST entry.
    for entry in usage_entries:
        story_key = entry.payload.get("story_key")
        cost = entry.payload.get("cost_estimate")
        if (
            isinstance(story_key, str)
            and story_key
            and isinstance(cost, (int, float))
            and not isinstance(cost, bool)
        ):
            budget_by_story[story_key] = cost

    # Story 5.2: `core.journal.fold`'s own `FoldResult.open_intents` for
    # THIS run_id only, rendered to plain JSON-dicts here (never inside
    # `core/status.py`, which stays pure and never imports `JournalEntry`).
    open_intents = tuple(
        entry.to_json_dict()
        for entry in fold_result.open_intents
        if entry.run_id == run_id
    )

    return _RunJournalFacts(
        launch_pid=launch_pid,
        launched_at=launched_at,
        supervisor_pid=supervisor_pid,
        budget_consumed=budget_consumed,
        budget_by_story=budget_by_story,
        open_intents=open_intents,
        harness_run_id=harness_run_id,
    )


def _gather_home_facts(
    *,
    fs: FsPort,
    harness: HarnessPort,
    process: ProcessPort,
    clock: ClockPort,
    home: Path,
    slug: str,
    branch: str,
    latest_run_dir,
    resolve_harness_run_id,
) -> status_core.FleetHomeFacts:
    """Gathers ONE home's ``FleetHomeFacts`` (Story 5.1) -- every read stays
    local file I/O plus one ``ProcessPort.is_alive`` probe (NFR-14: no
    network, no per-home subprocess call). ``latest_run_dir``/
    ``resolve_harness_run_id`` are ``cli/spin.py``'s own
    ``_latest_run_dir``/``_resolve_harness_run_id_for_resume``, passed in by
    the caller (which imports both locally to avoid the documented
    load-order cycle) -- the SAME read sequence ``cli/retire.py`` already
    established, reused rather than reimplemented."""
    run_dir = latest_run_dir(home, slug)
    if run_dir is None:
        return status_core.FleetHomeFacts(slug=slug, branch=branch, has_run=False)

    run_id = run_dir.name
    journal_facts = _gather_run_journal_facts(fs, run_dir, run_id)
    if journal_facts.launch_pid is None:
        return status_core.FleetHomeFacts(
            slug=slug, branch=branch, has_run=True, journal_unreadable=True
        )

    # Prefer `journal_facts.harness_run_id` (captured off the SAME fold
    # this function already paid for above) over a second, independent
    # read+fold of the identical journal via the injected
    # `resolve_harness_run_id` -- only falls back to that call if the
    # journal's own launch/resume entry never recorded one (should not
    # happen in practice, but the injected seam stays available rather
    # than silently reporting "no run state" for a recoverable gap).
    harness_run_id = journal_facts.harness_run_id or resolve_harness_run_id(
        fs, run_dir, run_id
    )
    snapshot = (
        harness.run_status_snapshot(home, harness_run_id) if harness_run_id else None
    )
    if snapshot is None:
        return status_core.FleetHomeFacts(
            slug=slug, branch=branch, has_run=True, journal_unreadable=True
        )

    # `journal_facts.supervisor_pid` (never `launch_pid`, which names the
    # DETACHED HARNESS process, a different process entirely -- see this
    # module's own `_SUPERVISOR_ATTACH_KIND` comment). `None` (the
    # supervisor never attached at all) is treated identically to a
    # confirmed-dead supervisor -- the safe direction, never silently
    # "alive".
    supervisor_alive = (
        process.is_alive(journal_facts.supervisor_pid)
        if journal_facts.supervisor_pid is not None
        else False
    )

    elapsed_seconds: float | None = None
    if journal_facts.launched_at is not None:
        elapsed_seconds = (clock.now() - journal_facts.launched_at).total_seconds()

    return status_core.FleetHomeFacts(
        slug=slug,
        branch=branch,
        has_run=True,
        finished=snapshot.finished,
        paused_stage=snapshot.paused_stage,
        tasks=snapshot.tasks,
        supervisor_alive=supervisor_alive,
        elapsed_seconds=elapsed_seconds,
        budget_consumed=journal_facts.budget_consumed,
        paused_reason=snapshot.paused_reason,
        escalated_spec_file=snapshot.escalated_spec_file,
        escalated_task_phase=snapshot.escalated_task_phase,
    )


def run_status(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
    harness: HarnessPort | None = None,
    process: ProcessPort | None = None,
    clock: ClockPort | None = None,
) -> int:
    # Local import -- `cli/init.py` imports `from . import deploy`, and
    # `cli/deploy.py`'s own `_gather_claimed_commits`/`cli/retire.py`'s own
    # `run_retire` both document the identical `cli.deploy`/`cli.init`
    # load-order-cycle rationale for why `cli/spin.py` is never imported at
    # module level from a sibling module; mirrored here for the same reason.
    from .spin import _latest_run_dir, _resolve_harness_run_id_for_resume

    vcs = vcs if vcs is not None else GitVcs()
    fs = fs if fs is not None else LocalFs()
    harness = harness if harness is not None else BmadLoopHarness()
    process = process if process is not None else PosixProcess()
    clock = clock if clock is not None else SystemClock()

    run_id = getattr(args, "run", None)
    reconcile_ledger = getattr(args, "reconcile_ledger", False)

    # Story 5.2's own Always bullet: `--run` requires `--project` alongside
    # it -- checked FIRST, before any I/O (the same pre-I/O precedence
    # `cli/deploy.py::run_land_story`'s own `--justification` check
    # establishes for `_MRS_DEPLOY_006`).
    if run_id is not None and args.project is None:
        finding = Finding(
            code=_MRS_STATUS_003,
            severity=Severity.ERROR,
            message=(
                "--run requires --project SLUG alongside it -- a run id "
                "alone does not name which project's Tier-3 store to look "
                "under"
            ),
        )
        data = {"project": None, "run": run_id}
        return _emit(args, data, [finding])

    # Story 5.4's own Always bullet: `--reconcile-ledger` requires
    # `--project` alongside it -- the SAME pre-I/O precedence `--run` above
    # already establishes for this command; a fleet-wide reconciliation
    # sweep is out of this story's own scope.
    if reconcile_ledger and args.project is None:
        finding = Finding(
            code=_MRS_STATUS_006,
            severity=Severity.ERROR,
            message=(
                "--reconcile-ledger requires --project SLUG alongside it "
                "-- a fleet-wide reconciliation sweep is out of this "
                "command's scope"
            ),
        )
        # Code review (2026-08-07, Edge Case Hunter): `discrepancies` is a
        # REQUIRED field in `schemas/status.json`'s own data_version-2
        # shape -- every other data_version-2 return path already includes
        # it; this refusal path was the one exception, so a `--format json`
        # caller of this exact invocation got a payload that failed its
        # own published schema.
        data = {"project": None, "discrepancies": []}
        return _emit(args, data, [finding], _render_text_reconcile, data_version=2)

    # Code review (2026-08-07, Edge Case Hunter): `--run` and
    # `--reconcile-ledger` are mutually exclusive view SELECTORS (fleet
    # summary / run detail / ledger reconciliation are three distinct
    # reports); giving both silently let `--reconcile-ledger` win with no
    # signal that `--run` was ignored -- inconsistent with this module's
    # own "reported, never a silent partial" convention (see the module
    # docstring). Refused before any I/O, same tier as the two precondition
    # checks above.
    if reconcile_ledger and run_id is not None:
        finding = Finding(
            code=_MRS_STATUS_006,
            severity=Severity.ERROR,
            message=(
                "--run and --reconcile-ledger are mutually exclusive -- "
                "each selects a different report; pass only one"
            ),
        )
        data = {"project": args.project, "discrepancies": []}
        return _emit(args, data, [finding], _render_text_reconcile, data_version=2)

    if reconcile_ledger:
        return _reconcile_ledger(args, vcs=vcs, harness=harness)

    if run_id is not None:
        return _run_detail(
            args, run_id=run_id, vcs=vcs, fs=fs, harness=harness
        )

    findings: list[Finding] = []
    data: dict[str, object] = {"project": args.project, "homes": []}

    try:
        git_repo_root = vcs.repo_common_root(Path.cwd())
        worktrees = vcs.list_worktrees(git_repo_root)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_STATUS_002,
                severity=Severity.WARN,
                message=f"cannot enumerate the fleet's loop-home worktrees: {exc}",
            )
        )
        return _emit(args, data, findings)

    fleet: list[tuple[str, Path]] = []
    for entry in worktrees:
        if entry.branch is None or not entry.branch.startswith("loop/"):
            continue
        slug = entry.branch.removeprefix("loop/")
        if args.project is not None and slug != args.project:
            continue
        fleet.append((slug, entry.path))

    rows: list[dict[str, object]] = []
    for slug, home in fleet:
        facts = _gather_home_facts(
            fs=fs,
            harness=harness,
            process=process,
            clock=clock,
            home=home,
            slug=slug,
            branch=f"loop/{slug}",
            latest_run_dir=_latest_run_dir,
            resolve_harness_run_id=_resolve_harness_run_id_for_resume,
        )
        row, finding = status_core.build_fleet_row(facts)
        rows.append(row)
        if finding is not None:
            findings.append(finding)

    # Story 5.3 (FR-38): escalated rows sort first, stable otherwise --
    # ALWAYS applied to the fleet summary (never gated on --escalations,
    # which only additionally FILTERS the same already-sorted list).
    rows = status_core.sort_fleet_rows(rows)
    if getattr(args, "escalations", False):
        rows = [row for row in rows if row.get("state") == "paused-on-escalation"]

    data["homes"] = rows
    return _emit(args, data, findings)


# =============================================================================
# Story 5.2: per-run detail (``marshal status --run <run_id> --project
# <slug>``, FR-37/NFR-12) -- switches this SAME command from the fleet
# summary above to a single-run drill-down. ``run_status`` has already
# confirmed ``args.project`` is present before ever calling this.
# =============================================================================


def _run_detail(
    args: argparse.Namespace,
    *,
    run_id: str,
    vcs: VcsPort,
    fs: FsPort,
    harness: HarnessPort,
) -> int:
    """One run's full detail view (Story 5.2): the FULL story sequence
    (``RunStatusSnapshot.tasks``, in ``state.json``'s own order), each
    story's own gate verdict (``cli/deploy.py::_gather_gate_verdicts``,
    reused verbatim -- the SAME helper ``run_batch_pr`` already calls),
    escalation/deferral state (``RunStatusSnapshot``'s own already-shipped
    fields), per-story consumption (``_gather_run_journal_facts``'s own
    Story 5.2 ``budget_by_story`` field, off the SAME fold Story 5.1's own
    ``budget_consumed`` already reads -- never a second fold), and open
    ``intent``-phase journal entries (the SAME fold's own
    ``FoldResult.open_intents``, rendered to plain dicts). ``core/
    status.py::build_run_detail`` (AD-4) does the actual assembly; this
    function only gathers already-shaped facts via ``VcsPort``/``FsPort``/
    ``HarnessPort``, mirroring ``run_status``'s own fleet-summary gather."""
    # Local imports -- `cli/init.py` imports `from . import deploy`, and
    # `cli/deploy.py`'s own `_gather_claimed_commits`/`cli/retire.py`'s own
    # `run_retire` both document the identical `cli.deploy`/`cli.init`
    # load-order-cycle rationale for why `cli/spin.py`/`cli/deploy.py` are
    # never imported at module level from a sibling module; mirrored here
    # for the same reason `run_status`'s own local import already is.
    from .deploy import _gather_gate_verdicts
    from .spin import _resolve_harness_run_id_for_resume

    slug = args.project
    findings: list[Finding] = []

    try:
        git_repo_root = vcs.repo_common_root(Path.cwd())
    except VcsCommandError as exc:
        # Code review (2026-08-07, Edge Case Hunter): a `VcsCommandError`
        # here means the repo root could not even be RESOLVED -- the
        # filesystem was never consulted, so whether the run exists is
        # genuinely UNKNOWN, not confirmed absent. The original version
        # still built a `found=False` row (via `RunDetailFacts`), which
        # fabricated a second `MRS-STATUS-004` "no run directory found"
        # finding whose own message explicitly (and, in this branch,
        # falsely) claims "reported, never fabricated." Mirrors
        # `run_status`'s own identical `VcsCommandError` handling for the
        # fleet-summary path, which reports the ONE finding and stops --
        # never synthesizes a second, unverified claim.
        findings.append(
            Finding(
                code=_MRS_STATUS_002,
                severity=Severity.WARN,
                message=f"cannot resolve the repo root: {exc}",
            )
        )
        return _emit(
            args,
            {"project": slug, "run": run_id},
            findings,
            _render_text_run_detail,
        )

    run_dir = (
        git_repo_root
        / "_bmad-output"
        / "projects"
        / slug
        / "implementation-artifacts"
        / "runs"
        / run_id
    )
    if not fs.is_dir(run_dir):
        row, not_found_finding = status_core.build_run_detail(
            status_core.RunDetailFacts(project=slug, run_id=run_id, found=False)
        )
        if not_found_finding is not None:
            findings.append(not_found_finding)
        return _emit(args, row, findings, _render_text_run_detail)

    journal_facts = _gather_run_journal_facts(fs, run_dir, run_id)
    gate_verdicts = _gather_gate_verdicts(fs, git_repo_root, slug)

    # The loop home currently attached for `slug`, if any -- needed to read
    # bmad-loop's own live `state.json` (`HarnessPort.run_status_snapshot`).
    # A read failure here is never fatal to the whole detail view: the
    # journal-sourced fields (gate verdicts, consumption, open intents)
    # stay populated regardless (mirrors `run_status`'s own "one bad
    # enumeration never aborts the report" posture).
    try:
        worktrees = vcs.list_worktrees(git_repo_root)
    except VcsCommandError:
        worktrees = ()

    home: Path | None = None
    for entry in worktrees:
        if entry.branch == f"loop/{slug}":
            home = entry.path
            break

    # Code review (2026-08-07, Blind Hunter, the single most severe finding
    # against this story): `journal_facts.harness_run_id` is already
    # captured off the SAME fold `_gather_run_journal_facts` just
    # performed above -- calling `_resolve_harness_run_id_for_resume` here
    # would independently re-read+re-fold the identical `journal.jsonl`,
    # exactly the double-fold this module's own docstrings already claim
    # (elsewhere, correctly) is avoided. Falls back to the resolver only
    # if the journal's own entry never recorded one.
    snapshot = None
    if home is not None:
        harness_run_id = journal_facts.harness_run_id or _resolve_harness_run_id_for_resume(
            fs, run_dir, run_id
        )
        if harness_run_id:
            snapshot = harness.run_status_snapshot(home, harness_run_id)

    facts = status_core.RunDetailFacts(
        project=slug,
        run_id=run_id,
        found=True,
        state_readable=snapshot is not None,
        finished=snapshot.finished if snapshot is not None else False,
        paused_stage=snapshot.paused_stage if snapshot is not None else None,
        paused_story_key=(
            snapshot.paused_story_key if snapshot is not None else None
        ),
        paused_reason=snapshot.paused_reason if snapshot is not None else None,
        escalated_spec_file=(
            snapshot.escalated_spec_file if snapshot is not None else None
        ),
        escalated_task_phase=(
            snapshot.escalated_task_phase if snapshot is not None else None
        ),
        tasks=snapshot.tasks if snapshot is not None else (),
        deferred=snapshot.deferred if snapshot is not None else (),
        gate_verdicts=gate_verdicts,
        budget_by_story=journal_facts.budget_by_story,
        open_intents=journal_facts.open_intents,
    )
    row, finding = status_core.build_run_detail(facts)
    if finding is not None:
        findings.append(finding)
    return _emit(args, row, findings, _render_text_run_detail)


# =============================================================================
# Story 5.4: ledger-vs-git reconciliation (``marshal status --reconcile-
# ledger --project <slug>``, FR-39/FR-40) -- a THIRD switch on this SAME
# command, alongside the fleet summary and ``--run`` detail above.
# ``run_status`` has already confirmed ``args.project`` is present before
# ever calling this. Opt-in only: never folded into the default view (a
# YAML parse plus a `git log`-scale walk over `main`'s full history is a
# genuinely heavier read than either sibling switch, per the spec's own
# Design Notes).
# =============================================================================


def _reconcile_ledger(
    args: argparse.Namespace,
    *,
    vcs: VcsPort,
    harness: HarnessPort,
) -> int:
    """Compares the tracked ``sprint-status-ledger.yaml`` twin's own
    ``status: done`` story keys against git's own durably-merged story keys
    (Story 5.4): reads the ledger via ``HarnessPort.ledger_story_statuses``
    (the SAME ``bmad_loop.sprintstatus.load`` parser
    ``story_feed_keys``/``story_feed_error`` already reuse -- AD-3 forbids
    this module from importing ``bmad_loop`` directly), gathers git's own
    durable-merge evidence via ``VcsPort.commit_subjects``/``core.promotion.
    merged_story_keys`` (Story 4.1's own already-shipped machinery, the SAME
    reuse ``cli/deploy.py``/``cli/retire.py``/``cli/land.py`` already
    establish), and delegates the actual comparison to ``core.status.
    reconcile_ledger_vs_git`` (AD-4). Neither source is ever rewritten
    (AD-33) -- purely diagnostic. ``data_version=2``: a genuinely NEW
    payload shape (AD-39), never additive fields on an already-shipped one."""
    slug = args.project
    findings: list[Finding] = []
    root = repo_root()

    ledger_path = root / _LEDGER_RELPATH.format(slug=slug)
    try:
        raw_statuses = harness.ledger_story_statuses(ledger_path)
    except HarnessError as exc:
        findings.append(
            Finding(
                code=_MRS_STATUS_005,
                severity=Severity.WARN,
                message=(
                    f"project {slug!r}: cannot read the tracked ledger at "
                    f"{ledger_path}: {exc}"
                ),
                path=str(ledger_path),
            )
        )
        data: dict[str, object] = {"project": slug, "discrepancies": []}
        return _emit(args, data, findings, _render_text_reconcile, data_version=2)

    # A raw ledger key that fails to normalize is skipped, never a crash --
    # mirrors every other Epic 5 story's established convention (the spec's
    # own I/O matrix: "A ledger entry with a malformed key").
    ledger_done_keys: set[str] = set()
    for raw_key, raw_status in raw_statuses:
        if raw_status != _DONE_STATUS:
            continue
        try:
            ledger_done_keys.add(str(normalize(raw_key)))
        except MalformedStoryKeyError:
            continue

    project_data: Mapping[str, object] = {}
    if policy_core._is_valid_project_slug(slug):
        policy_path = conventional_project_policy_path(slug)
        try:
            present = policy_path.is_file()
        except OSError:
            present = True
        if present:
            try:
                project_data = _read_project_policy(policy_path)
            except PolicyIOError as exc:
                findings.append(exc.finding)
    effective, policy_findings = policy_core.compose(
        project_slug=slug, project=project_data, flags={}
    )
    findings.extend(policy_findings)
    template = effective.merge_subject_template.value

    # Git's own durable-merge evidence is REQUIRED, not best-effort (mirrors
    # `cli/deploy.py::_scan_promotions`'s identical "cannot honestly
    # determine ANY story's durability this run" rationale for its own
    # `_MRS_DEPLOY_003`) -- a read failure here is a hard, run-wide finding,
    # never a silently-empty `merged_keys` (which would read as "nothing
    # merged yet" and report every ledger `done` key as a false positive).
    try:
        main_subjects = vcs.commit_subjects(root, _MERGE_BASE_BRANCH)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_STATUS_007,
                severity=Severity.ERROR,
                message=(
                    f"cannot read {_MERGE_BASE_BRANCH!r}'s commit history "
                    f"to determine story durability: {exc}"
                ),
            )
        )
        data = {"project": slug, "discrepancies": []}
        return _emit(args, data, findings, _render_text_reconcile, data_version=2)

    merged_keys = frozenset(
        str(key)
        for key in promotion.merged_story_keys(main_subjects, template, slug)
    )

    discrepancies = status_core.reconcile_ledger_vs_git(
        frozenset(ledger_done_keys), merged_keys
    )
    data = {"project": slug, "discrepancies": list(discrepancies)}
    return _emit(args, data, findings, _render_text_reconcile, data_version=2)


def _render_text_reconcile(
    data: Mapping[str, object], findings: tuple[Finding, ...]
) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14/NFR-12), matching every other view
    this command's own ``_render_text*`` convention already establishes."""
    project = data.get("project")
    discrepancies = data.get("discrepancies") or []
    lines = [
        f"status --project {project!r} --reconcile-ledger",
        f"discrepancies: {len(discrepancies)}",
    ]
    for discrepancy in discrepancies:
        lines.append(
            f"  {discrepancy['story_key']} {discrepancy['kind']} "
            f"[{discrepancy.get('confidence', 'unconfirmed')}]"
        )

    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(
                f"  {finding.code} [{finding.severity.value}] {finding.message}"
            )
    return "\n".join(lines)


def _render_text_status(
    data: Mapping[str, object], findings: tuple[Finding, ...]
) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching every other command's
    own ``_render_text*`` convention."""
    project = data.get("project") or "(whole fleet)"
    homes = data.get("homes") or []
    lines = [f"status: {project!r}", f"homes: {len(homes)}"]
    for home in homes:
        # Story 5.3 (FR-38): a `[ESCALATED]` prefix visually distinguishes a
        # paused-on-escalation row from every other state, and names its
        # own reason/artifact inline -- `--format json` output is
        # unaffected (same fields either way, NFR-12).
        escalated = home["state"] == "paused-on-escalation"
        prefix = "[ESCALATED] " if escalated else ""
        line = (
            f"  {prefix}{home['slug']} ({home['branch']}): {home['state']} "
            f"story={home['current_story']} "
            f"elapsed_seconds={home['elapsed_seconds']} "
            f"budget_consumed={home['budget_consumed']}"
        )
        if escalated:
            line += (
                f" reason={home.get('escalation_reason')!r} "
                f"artifact={home.get('escalation_artifact')!r}"
            )
        lines.append(line)

    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(
                f"  {finding.code} [{finding.severity.value}] {finding.message}"
            )
    return "\n".join(lines)


def _render_text_run_detail(
    data: Mapping[str, object], findings: tuple[Finding, ...]
) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (Story 5.2, NFR-12) -- every field this
    prints has an identical machine-readable counterpart in ``data``, never
    a human-only fact. Handles both this command's own ``found: False``
    shape (``build_run_detail``'s "not found" row) and the precondition
    refusal's own bare ``{"project", "run"}`` shape (``run_status``'s own
    ``--run`` without ``--project`` gate, which never reaches
    ``build_run_detail`` at all) via ``Mapping.get``."""
    project = data.get("project")
    run_id = data.get("run") or data.get("run_id")
    lines = [f"status --project {project!r} --run {run_id!r}"]

    if data.get("found") is False:
        lines.append("found: false")
    elif "found" in data:
        lines.append(f"found: {data.get('found')}")
        lines.append(f"state_readable: {data.get('state_readable')}")
        lines.append(f"finished: {data.get('finished')}")
        lines.append(
            f"paused_stage={data.get('paused_stage')} "
            f"paused_story_key={data.get('paused_story_key')} "
            f"paused_reason={data.get('paused_reason')}"
        )
        lines.append(
            f"escalated_spec_file={data.get('escalated_spec_file')} "
            f"escalated_task_phase={data.get('escalated_task_phase')}"
        )

        stories = data.get("stories") or []
        lines.append(f"stories: {len(stories)}")
        for story in stories:
            lines.append(
                f"  {story['story_key']} phase={story['phase']} "
                f"commit_sha={story['commit_sha']} branch={story['branch']!r} "
                f"gate_verdict={story['gate_verdict']} "
                f"budget_consumed={story['budget_consumed']}"
            )

        deferred = data.get("deferred") or []
        lines.append(f"deferred: {len(deferred)}")
        for deferred_story in deferred:
            lines.append(
                f"  {deferred_story['story_key']} "
                f"attempt={deferred_story['attempt']} "
                f"reason={deferred_story['reason']!r} "
                f"branch={deferred_story['branch']!r}"
            )

        open_intents = data.get("open_intents") or []
        lines.append(f"open_intents: {len(open_intents)}")
        for intent in open_intents:
            lines.append(
                f"  {intent.get('kind')} id={intent.get('id')} "
                f"payload={intent.get('payload')}"
            )

    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(
                f"  {finding.code} [{finding.severity.value}] {finding.message}"
            )
    return "\n".join(lines)


def _emit(
    args: argparse.Namespace,
    data: dict[str, object],
    findings: list[Finding],
    render: Callable[[Mapping[str, object], tuple[Finding, ...]], str] = _render_text_status,
    *,
    data_version: int = 1,
) -> int:
    """The envelope-build-then-print tail every ``cli/*.py`` command shares
    (AD-14: one envelope shape per command). ``render`` defaults to
    ``_render_text_status``'s own fleet-summary projection; Story 5.2's
    ``_run_detail`` passes ``_render_text_run_detail`` instead -- the SAME
    "value-returning core, distinct text-render callable per data shape"
    convention ``cli/deploy.py``'s own ``_emit`` (``land-story`` vs.
    ``batch-pr``) already established. ``data_version`` defaults to ``1``
    (every payload shape this command shipped before Story 5.4); Story
    5.4's ``--reconcile-ledger`` view passes ``2`` -- a genuinely NEW
    payload shape (AD-39), never additive fields on an already-shipped
    one, which would leave the version unchanged instead."""
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="status",
        verdict=verdict_value,
        data=data,
        data_version=data_version,
        findings=tuple(findings),
    )

    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = render(envelope.data, envelope.findings)

    try:
        print(rendered, flush=True)
    except OSError:
        _suppress_downstream_pipe_close()

    return exit_code_for(envelope.verdict)
