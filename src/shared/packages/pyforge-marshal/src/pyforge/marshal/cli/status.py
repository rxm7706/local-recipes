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

No ``sprint-status.yaml``, ledger, or any other hand-maintained feed of
STORY STATE is ever read for the fleet summary or ``--run`` detail views
above (AD-5's own explicit prohibition) -- see ``core/status.py``'s own
module-level docstring section for the pure derivation core this module
feeds.

One narrow, deliberate qualification (Story 4.14, correction 2026-08-10):
the fleet summary DOES now read a hand-maintained tracked file -- each
patch-carrying home's own ``marshal-policy.toml`` -- via
``_merged_keys_for_slug``. That is CONFIGURATION (the project's
``merge_subject_template``), never a claim about any story's state, so
AD-5's prohibition is untouched: the durability answer still comes only
from git. Stated explicitly because the unqualified sentence above was
false for one release and a maintainer reading top-down would otherwise
hit it 1,300 lines before the code that contradicts it.

**Story 5.4's ``--reconcile-ledger`` view is the ONE deliberate exception**
(FR-39/FR-40): it reads the TRACKED ``sprint-status-ledger.yaml`` twin --
never the gitignored Tier-3 feed AD-5 forbids everywhere else in this
module -- explicitly to compare it against git's own durably-merged story
keys and report any disagreement by name. See ``_reconcile_ledger``'s own
docstring below.

**Story 5.5 adds durability as a reported fleet-status DIMENSION**
(FR-62/AD-48): the fleet-summary path runs the EXISTING, already-shipped
``scripts/unpushed_work_check.py --json --branches-only`` detector ONCE
per invocation and folds its own ``unpushed-branch`` findings onto each
home's own row by matching ``ref == f"loop/{slug}"`` -- never a second,
independently-maintained branch-vs-remote diff. See
``_gather_unpushed_work_findings``'s own docstring below.

**Story 4.14 adds a SIBLING durability signal, failed-story patches**
(FR-176): for every home, a bare ``Path.glob`` finds every
``.bmad-loop/runs/*/failed/*/changes.patch`` -- bmad-loop's own on-disk
shape for a session-timeout-killed story's preserved diff, previously read
by nothing in this repo. Each found patch is classified by whether its
story has since landed, via the SAME ``core.promotion.merged_story_keys``
sequence ``_reconcile_ledger`` already establishes (AD-33: git's durable
merge history is the sole authority, never the harness's own
journal/``state.json``) -- ``main``'s own commit-subject read is cached
ONCE for the whole sweep (mirrors ``_gather_unpushed_work_findings``'s own
"one shared detector run" precedent). Because that classifier's NEGATIVE
direction is a known-unreliable signal (``core/status.py``'s own
``CONFIDENCE_UNCONFIRMED`` block), a patch reported as not-landed is
reported as UNCONFIRMED, never as an established fact -- see
``_gather_failed_patches``'s and ``_MRS_STATUS_010``'s own docstrings below.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from ..adapters.clock_system import SystemClock
from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness, HarnessError
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import policy as policy_core
from ..core import promotion
from ..core import status as status_core
from ..core.identity import MalformedStoryKeyError, normalize
from ..core.journal import Phase, fold
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import Verdict, classify, compute_verdict, exit_code_for
from ..ports.clock import ClockPort
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.vcs import VcsPort
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
    repo_root,
)

if TYPE_CHECKING:
    # Story 5.6 (FR-65/AD-50): `run_status`'s `context` parameter below is
    # type-only -- this module's own internal logic is NOT retrofitted to
    # CONSUME it in this pass (see cli/main.py's own module docstring and
    # the spec's Design Notes); a real (non-TYPE_CHECKING) import would add
    # a runtime dependency this module doesn't otherwise need.
    from ..core.context import MarshalContext

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

# Story 5.5 (durability as a reported fleet-status dimension, FR-62/AD-48):
# two more codes for the fleet-summary path's own `scripts/
# unpushed_work_check.py --json --branches-only` fold (AD-48: read from the
# existing detector, never re-derive against git independently).
# `_MRS_STATUS_008` names ONE home's own station branch with local-only
# content the detector confirmed is not on origin -- reported per matching
# home, never silently absorbed into a "clean" verdict.
# `_MRS_STATUS_009` names the detector itself could not be consulted this
# run at all (missing script, launch failure, the documented `UNKNOWN`/
# exit-2 case which prints plain text even with `--json`, or malformed
# JSON) -- ONE WARN for the whole sweep, with every row's `unpushed_work`
# reporting `null` (unknown), never fabricated as "nothing to report" (the
# exact false-green the detector's own docstring names as the 2026-07-31
# incident's root cause).
_MRS_STATUS_008 = "MRS-STATUS-008"
_MRS_STATUS_009 = "MRS-STATUS-009"

# Story 4.14 (the failed-story safety net is reported, FR-176): two more
# codes in this same area, sourced from a bare `Path.glob` over every
# currently-attached home's own `.bmad-loop/runs/*/failed/*/changes.patch`
# files.
#
# `_MRS_STATUS_010` names ONE such patch whose story is NOT CONFIRMED
# durably merged into `main` (per `core.promotion.merged_story_keys`) --
# reported per matching patch, never silently absorbed. It deliberately
# states an UNCONFIRMED direction and WHY, never "has not landed" as an
# established fact: an ABSENCE of a `merged_story_keys` match is exactly
# the direction `core/status.py`'s own `CONFIDENCE_UNCONFIRMED` block
# documents as proving nothing (a GitHub squash-merge's subject is
# free-form prose, and a `land/<station>-<epic>-<seq>` merge subject puts a
# station token where `normalize` anchors at position 0 -- 22 such merges
# exist on this repo's own `main`). Measured 2026-08-10 against the real
# 12-patch fleet: of 3 WARNs the first implementation emitted, 2 were
# false (`pyforge-marshal` 1.6, `pyforge-steward` 8.1 -- both genuinely
# landed). Each reported entry carries the matching
# `core.status.CONFIDENCE_*` value so a consumer can weight it correctly.
#
# `_MRS_STATUS_011` names that a patch's landed-status could not be
# determined AT ALL, from EITHER of two distinct causes:
#   1. `main`'s own commit history could not be read -- ONE WARN for the
#      whole sweep (the read is attempted at most once, lazily, on first
#      need), with EVERY patch found this run reporting `done: null`.
#   2. ONE project slug's own merge-subject policy could not be resolved
#      (a malformed project-policy TOML -- an ERROR-severity
#      `MRS-POLICY-004` from `_merged_keys_for_slug`). This arm is
#      PER-SLUG: it can fire once per affected home, and degrades only
#      THAT project's patches. It exists because a raw `MRS-POLICY-004`
#      would flip this command's exit code to 4 over a best-effort
#      durability read, which this story's own Boundaries forbid.
# Either way the affected patches report `done: null`, never fabricated as
# landed or unlanded.
_MRS_STATUS_010 = "MRS-STATUS-010"
_MRS_STATUS_011 = "MRS-STATUS-011"

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
            "read: the LEDGER read and this whole reconciliation report are "
            "never folded into the default fleet/run-detail views (Story "
            "4.14 does fold the git-side `main` commit-subject walk into "
            "the default fleet sweep, for its own failed-story-patch "
            "classification)."
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


# Story 5.5's own relative path to the EXISTING, already-shipped
# repo-level detector (registered in `scripts/detectors.py`'s own runtime
# registry) -- never a second, independently-maintained copy of its own
# branch-vs-remote diff logic (AD-48).
_UNPUSHED_WORK_SCRIPT_RELPATH = ("scripts", "unpushed_work_check.py")

# A generous but bounded ceiling for the ONE subprocess call the fleet
# summary makes per invocation -- a hung detector must not hang this whole
# command (the same "bounded, never unbounded" rationale `cli/deploy.py::
# _RESYNC_TIMEOUT_S` already establishes for its own single `ProcessPort.
# run` call, though at a different value -- that call's own remedy
# commands can legitimately run longer). Code review (2026-08-07, Edge
# Case Hunter): this value is NOT itself a guarantee of NFR-14's 10-second/
# 7-homes sweep budget -- it is a ceiling against a genuinely hung
# subprocess, not a target the detector is expected to normally approach;
# the detector's own real-world runtime (two git subprocesses per LOCAL
# branch) is the actual determinant of whether NFR-14 holds in practice.
_UNPUSHED_WORK_TIMEOUT_S = 30.0

# The detector's own documented `UNKNOWN` exit code (offline / no remote)
# -- printed as PLAIN TEXT even with `--json` passed (see
# `scripts/unpushed_work_check.py::main`), so it is never JSON-parseable
# and must be special-cased before the JSON parse is even attempted.
_UNPUSHED_WORK_UNKNOWN_EXIT_CODE = 2


def _gather_unpushed_work_findings(
    process: ProcessPort, repo_root: Path
) -> tuple[dict[str, dict[str, object]] | None, Finding | None]:
    """Runs ``scripts/unpushed_work_check.py --json --branches-only`` ONCE
    for the whole fleet sweep (FR-62/AD-48: read from that EXISTING
    detector, never re-derive its branch-vs-remote diff, remote-branch
    enumeration, or shortstat computation a second way). ``--branches-only``
    is always passed -- the detector's own dangling-commit scan (``git
    fsck``) is out of this story's scope (the Design Notes' own NFR-14
    rationale).

    Returns ``(by_ref, None)`` on success: a mapping of branch ref ->
    ``{"files": int, "stat": str, "remedy": str}`` (the detector's own
    ``unpushed-branch`` findings, verbatim -- never a re-derived line
    count), possibly empty when the detector confirms a clean fleet.

    Returns ``(None, finding)`` when the detector could not be consulted
    AT ALL this run: the script could not be launched (missing, permission
    failure), it exited its own documented ``UNKNOWN`` code (offline / no
    remote -- printed as PLAIN TEXT even with ``--json``, so never
    JSON-parseable), or its stdout failed to parse as the expected JSON
    shape. This is never silently treated as "no unpushed work" -- the
    exact false-green the detector's own module docstring names as the
    2026-07-31 incident's root cause; the caller folds the returned
    ``finding`` into the envelope and reports every row's own
    ``unpushed_work`` as ``null`` (unknown, not clean)."""
    script_path = repo_root.joinpath(*_UNPUSHED_WORK_SCRIPT_RELPATH)
    unavailable_finding = Finding(
        code=_MRS_STATUS_009,
        severity=Severity.WARN,
        message=(
            "the unpushed-work detector "
            f"({'/'.join(_UNPUSHED_WORK_SCRIPT_RELPATH)}) could not be "
            "consulted this run -- every home's unpushed_work reports "
            "null (unknown), never fabricated as clean"
        ),
    )

    try:
        result = process.run(
            # Code review (2026-08-07, Edge Case Hunter): `sys.executable`,
            # never a bare `"python3"` -- `cli/spin.py`'s own established
            # precedent for spawning a Python child (`spawn_detached([sys.
            # executable, "-m", ...])`) exists precisely so the child runs
            # under the SAME interpreter/environment Marshal itself is
            # running under. A bare `"python3"` resolved off `PATH` can
            # silently be a DIFFERENT interpreter (or absent entirely) in a
            # pixi/conda env whose activated shell doesn't expose that
            # exact name -- degrading every run to MRS-STATUS-009 in
            # exactly the environments most likely to differ from a
            # developer's default shell.
            [sys.executable, str(script_path), "--json", "--branches-only"],
            cwd=repo_root,
            timeout_s=_UNPUSHED_WORK_TIMEOUT_S,
        )
    except ProcessError:
        return None, unavailable_finding

    if result.returncode == _UNPUSHED_WORK_UNKNOWN_EXIT_CODE:
        return None, unavailable_finding

    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, unavailable_finding

    raw_findings = payload.get("findings") if isinstance(payload, dict) else None
    if not isinstance(raw_findings, list):
        return None, unavailable_finding

    # Code review (2026-08-07, Edge Case Hunter): `files`/`stat`/`remedy`
    # are now type-validated, not merely read via a bare `.get()` -- a
    # structurally-valid-but-incomplete entry (a future detector version,
    # a truncated write) previously still counted as "matched," producing
    # a real MRS-STATUS-008 WARN with garbage content (e.g. "carries None
    # file(s)... (None) -- None") instead of degrading. A malformed entry
    # is now SKIPPED (never surfaced with placeholder content) -- the
    # SWEEP still succeeds on every other well-formed entry; only this one
    # bad entry is dropped, never escalated to a whole-sweep MRS-STATUS-009
    # (a single malformed entry is not evidence the whole detector run is
    # untrustworthy).
    by_ref: dict[str, dict[str, object]] = {}
    for entry in raw_findings:
        if not isinstance(entry, dict) or entry.get("kind") != "unpushed-branch":
            continue
        ref = entry.get("ref")
        if not isinstance(ref, str) or not ref:
            continue
        files = entry.get("files")
        stat = entry.get("stat")
        remedy = entry.get("remedy")
        if (
            not isinstance(files, int)
            or isinstance(files, bool)
            or not isinstance(stat, str)
            or not stat
            or not isinstance(remedy, str)
            or not remedy
        ):
            continue
        by_ref[ref] = {"files": files, "stat": stat, "remedy": remedy}
    return by_ref, None


# Story 4.14's own relative glob for bmad-loop's own on-disk shape (external
# to this repo, defined by bmad-loop itself, never Marshal): a
# session-timeout-killed story's preserved diff, one per failed attempt.
_FAILED_PATCH_GLOB = ".bmad-loop/runs/*/failed/*/changes.patch"


def _gather_failed_patches(home: Path) -> tuple[tuple[Path, int], ...]:
    """Every REPORTABLE ``.bmad-loop/runs/*/failed/*/changes.patch`` under
    this home (Story 4.14, FR-176), as ``(path, size_bytes)`` pairs --
    bmad-loop's own on-disk shape for a session-timeout-killed story's
    preserved diff. A bare ``Path.glob``, never routed through ``FsPort``
    (no directory-listing primitive exists on that port; adding one for
    this single, read-only caller would be disproportionate -- mirrors
    ``cli/spin.py::_latest_run_dir``'s own documented, identical
    precedent). Sorted for a deterministic sweep order; an absent
    ``.bmad-loop`` tree degrades to "none found", the same failure handling
    ``_latest_run_dir`` itself already uses.

    **A permission failure does NOT reach the ``except OSError`` below**
    (review finding, 2026-08-10, pass 5 -- this docstring previously said
    it did, contradicting ``core/status.py::FleetHomeFacts.failed_patches``,
    which states the real behaviour). ``Path.glob`` suppresses the
    ``OSError`` from an unreadable directory mid-traversal and silently
    yields a PARTIAL result: verified on CPython 3.14.6, ``chmod 000`` on
    one ``failed/<story>/`` makes just that patch vanish while its siblings
    are still reported, and ``chmod 000`` on ``failed/`` empties the home
    -- neither raises, so neither is distinguishable here from "clean". The
    ``except OSError`` guards only a failure raised before iteration
    begins. This is a known, recorded limit of this signal, deferred rather
    than reported (closing it honestly needs enumeration-integrity
    reporting under a new finding code); do NOT read ``()`` as proof the
    tree was fully read.

    **EVERY reportability test lives HERE, never at the caller's per-entry
    loop** -- so a non-empty return genuinely means "there is something to
    report", and "nothing reportable" and "nothing found" are the same
    state. Three tests, each of which would otherwise leave the caller's
    ``if patch_paths:`` gate open on a patch it then silently skips --
    paying for the ``main`` commit-subject read and able to emit an
    ORPHANED ``MRS-STATUS-011`` while every row still (correctly) reported
    ``failed_patches: []`` (reproduced live, review pass 3):

    1. ``is_file()`` -- ``Path.glob`` does not distinguish file kind and
       ``.stat()`` on a directory succeeds rather than raising, so a
       directory literally named ``changes.patch`` would be reported as a
       fabricated entry (review pass 2).
    2. ``st_size > 0`` -- a zero-byte patch means the kill landed BEFORE
       any diff was written, so it preserved nothing to recover and
       warning about it would direct an operator at an empty file (review
       pass 2 asked for the skip; pass 3 moved it here, where it belongs).
    3. ``OSError`` on the ``stat()`` itself -- a patch that vanished
       between the glob and the stat is simply not reportable.

    Returning the size alongside the path is what makes 2 and 3 possible
    here at all: the caller must not re-``stat()``, both because that
    would reintroduce the very skip-after-the-gate hole this closes and
    because a second stat could disagree with the first."""
    pairs: list[tuple[Path, int]] = []
    try:
        candidates = sorted(home.glob(_FAILED_PATCH_GLOB))
    except OSError:
        return ()
    for path in candidates:
        try:
            if not path.is_file():
                continue
            size_bytes = path.stat().st_size
        except OSError:
            continue
        if size_bytes == 0:
            continue
        pairs.append((path, size_bytes))
    return tuple(pairs)


# Every C0 control, DEL, and the three non-C0 characters `str.splitlines`
# also breaks on (NEL, LINE SEPARATOR, PARAGRAPH SEPARATOR). See `_one_line`.
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f\x85\u2028\u2029]+")


def _one_line(value: object) -> str:
    """``value`` as a single-line ``str`` (Story 4.14) -- the SAME
    newline-stripping ``_render_text_status`` already applies to
    ``unpushed.stat``, hoisted so every one of this story's own finding
    messages gets it rather than only some of them.

    Required because a ``failed/<story>/`` directory name is a raw POSIX
    filename, which may legally contain a newline, and BOTH the story key
    (when it does not parse, ``_render_story_key_best_effort`` returns the
    raw name) and the patch path (always, on every entry) are interpolated
    into ``Finding.message``. ``_render_text_status``'s own findings block
    prints one finding per line WITHOUT sanitizing, so an unsanitized
    newline forges a findings line no finding emitted -- reproduced live,
    review finding 2026-08-10 pass 4, and the identical class already fixed
    in ``cli/config.py``. The wider, cross-cutting gap this does NOT close
    (``MRS-STATUS-008``'s own ``remedy``/``stat`` interpolation shares it)
    stays recorded in the deferred-work ledger.

    Every character ``str.splitlines`` treats as a line break is collapsed,
    not only ``\\n``/``\\r`` (review finding, 2026-08-10, pass 5). The
    original pair was too narrow for this function's OWN stated threat
    model: if a ``failed/<story>/`` directory name may legally carry a
    newline then it may equally carry ``\\v``, ``\\f``, ``\\x1c``-``\\x1e``,
    ``\\x85``, ``\\u2028`` or ``\\u2029`` -- all legal in a POSIX/UTF-8
    filename, all split by ``splitlines`` (the very method this story's own
    forged-line test asserts with), and several rendered as a line break by
    a terminal. Also collapses the remaining C0 controls and ``\\x7f``,
    which cannot forge a line but can rewrite one already printed."""
    return _CONTROL_RE.sub(" ", str(value)).strip()


def _name_patches(named: list[tuple[str, dict[str, object]]]) -> str:
    """``named`` -- ``(slug, entry)`` pairs -- rendered as a human-readable,
    deterministic phrase naming each patch (Story 4.14, review finding
    2026-08-10 pass 3). The intent contract's Always bullet requires that a
    patch whose landed-status "could not be determined" raise "exactly one
    WARN naming it" -- so the single ``MRS-STATUS-011`` that degrades a set
    of patches has to name them, not merely count them.

    Each patch is named ``<slug>/<story_key>``, never a bare story key
    (review finding, 2026-08-10 pass 4): the sweep-wide arm names patches
    from EVERY home at once, and story numbers repeat across stations by
    construction -- live, ``pyforge-doctor`` and ``pyforge-warden`` both
    carry a ``6-9-*`` patch, so a bare-key rendering emitted ``6.9, 6.9``
    and named neither. Sorted for determinism and ``_one_line``-sanitized,
    since an entry's key may fall back to a raw POSIX directory name.

    ``@<run_id>`` closes the SAME collision one level down (review finding,
    2026-08-10, pass 5): a home accumulates one ``failed/<story>/`` per
    killed attempt, so repeated attempts at ONE story in ONE home rendered
    identically -- live, ``pyforge-steward`` carries three run dirs, and the
    degenerate case read ``(steward/8.1, steward/8.1, steward/8.1)`` and
    located none of them. This is exactly why ``MRS-STATUS-010`` already
    names ``run_id`` (review finding, pass 2); ``MRS-STATUS-011`` is the
    ONLY report a ``done: null`` patch ever gets, since ``010`` fires solely
    for ``done is False``, so the omission bit harder here."""
    keys = sorted(
        f"{_one_line(slug)}/{_one_line(entry.get('story_key'))}"
        f"@{_one_line(entry.get('run_id'))}"
        for slug, entry in named
    )
    if not keys:
        return "no patches"
    return f"{len(keys)} patch(es) ({', '.join(keys)})"


def _merged_keys_for_slug(
    slug: str, main_subjects: tuple[str, ...]
) -> tuple[frozenset[str], tuple[Finding, ...]]:
    """``slug``'s own durably-merged story keys, as canonical dot-form
    ``str``s, plus every ``Finding`` raised while resolving ``slug``'s own
    ``merge_subject_template`` (Story 4.14) -- the ONE policy-read-then-
    ``promotion.merged_story_keys`` sequence, shared by both
    ``_reconcile_ledger`` below (an explicit ``--project`` diagnostic view,
    which surfaces every returned finding, including a policy ERROR, at
    face value) and the failed-story-patch fold in ``run_status``'s fleet
    sweep (which must NOT let an unrelated policy misconfiguration for one
    project promote a best-effort durability check into an ERROR-severity,
    exit-code-changing result on the DEFAULT view -- see that call site's
    own handling of the returned findings). A single independently
    -maintained copy of this sequence would violate this codebase's own
    "one owner for the merge-subject form" rule; review finding, 2026-08-10:
    the first version of this story duplicated it instead of sharing it.

    Note the POSITIVE/NEGATIVE asymmetry of the returned set, which every
    caller must respect (``core/status.py``'s own ``CONFIDENCE_CONFIRMED``/
    ``CONFIDENCE_UNCONFIRMED`` block carries the full rationale): a key
    PRESENT here is the STRONGER direction, while a key ABSENT proves
    nothing -- ``promotion.merged_story_keys`` cannot parse a story key out
    of a GitHub squash-merge's free-form prose subject, nor out of a
    ``land/<station>-<epic>-<seq>`` merge subject.

    "Stronger", not "proof" (review finding, 2026-08-10, pass 4). The
    positive direction has a known, VERIFIED contamination of its own,
    recorded as an open deferral against ``core/promotion.py``:
    ``extract_story_key_from_github_merge_subject`` takes no
    ``project_slug`` at all -- unlike the bmad-loop pattern, scoped after a
    live collision -- so in this repo's single shared ``git log`` one
    station's ``<epic>.<seq>`` is "merged" on the sole evidence of a
    DIFFERENT station's PR-merge subject. Measured 2026-08-10 against
    ``main``'s 2,353 subjects, ``pyforge-mason``, ``pyforge-doctor`` and
    ``pyforge-scribe`` each return ~30 keys, most of them another station's.
    So the honest reading is: ABSENT proves nothing, PRESENT is good
    evidence that is nonetheless cross-project blind. Callers must not
    upgrade "present" to "certainly landed" in prose an operator reads."""
    findings: list[Finding] = []
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
    merged = frozenset(
        str(key) for key in promotion.merged_story_keys(main_subjects, template, slug)
    )
    return merged, tuple(findings)


def run_status(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
    harness: HarnessPort | None = None,
    process: ProcessPort | None = None,
    clock: ClockPort | None = None,
    context: MarshalContext | None = None,
) -> int:
    # Story 5.6 (FR-65/AD-50): `context`, if `cli/main.py`'s dispatch
    # resolved one, is accepted but deliberately UNUSED here -- proving the
    # "resolved once at the front door" plumbing reaches this handler
    # without retrofitting its own internal policy/home-path derivation
    # (see this story's own Design Notes; `cli/main.py`'s module docstring
    # names the exact three already-shipped commands this applies to).
    del context
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

    # Story 5.5 (FR-62/AD-48): the fleet's own unpushed-work evidence,
    # gathered ONCE for the whole sweep (never per-home -- the detector's
    # own read already covers every branch in the ONE physical repo every
    # loop home shares; see this module's own `_gather_unpushed_work_
    # findings` docstring). Skipped entirely when the fleet is empty --
    # nothing to fold it onto. `by_ref is None` means the detector could
    # not be consulted at all this run; every row below then reports
    # `unpushed_work: null` (unknown), never a silent "clean".
    unpushed_by_ref: dict[str, dict[str, object]] | None = {}
    if fleet:
        unpushed_by_ref, unpushed_unavailable_finding = _gather_unpushed_work_findings(
            process, git_repo_root
        )
        if unpushed_unavailable_finding is not None:
            findings.append(unpushed_unavailable_finding)

    # Story 4.14 (FR-176): `main`'s own commit-subject history, read at most
    # ONCE and reused for every home in the sweep -- a `git log`-scale walk
    # is the heavier read `--reconcile-ledger`'s own docs cite as its reason
    # for being opt-in, so reading it once keeps THAT cost paid a single
    # time no matter how many homes carry patches (mirrors
    # `_gather_unpushed_work_findings`'s own "one shared detector run for
    # the whole sweep" precedent). Only the git read is shared: each
    # patch-carrying home still composes its OWN project policy inside the
    # loop, since `merge_subject_template` is per-project by definition
    # (review finding, 2026-08-10, pass 3 -- this comment used to claim the
    # policy compose was cached too). It is resolved LAZILY, on first need,
    # purely so a fleet with genuinely zero failed patches never pays for
    # it at all -- that is a degenerate-case optimization, NOT the common
    # path: measured 2026-08-10, 7 of 8 live loop homes carry at least one
    # patch, so a real sweep performs this read essentially always.
    main_subjects_attempted = False
    main_subjects_available = False
    main_subjects: tuple[str, ...] = ()
    # `_MRS_STATUS_011`'s cause 1 is recorded here and reported ONCE after
    # the whole per-home loop, so the single sweep-wide WARN can NAME every
    # patch it degraded (the intent contract's Always bullet) -- it cannot
    # be emitted at the point of failure, since the homes scanned later in
    # the sweep are not yet known there.
    main_read_error: VcsCommandError | None = None
    main_unavailable: list[tuple[str, dict[str, object]]] = []

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
        if unpushed_by_ref:
            matched = unpushed_by_ref.get(facts.branch)
            if matched is not None:
                facts = replace(facts, unpushed_work=matched)

        # Story 4.14 (FR-176): the failed-story patch safety net -- a
        # session-timeout-killed story's preserved diff, glob'd off this
        # home's own `.bmad-loop/runs/*/failed/*/changes.patch`. Already
        # filtered to real FILES by `_gather_failed_patches` itself, so a
        # non-empty tuple genuinely means "there is something to report"
        # and this gate never opens for a directory named `changes.patch`.
        patch_paths = _gather_failed_patches(home)
        if patch_paths:
            if not main_subjects_attempted:
                main_subjects_attempted = True
                try:
                    main_subjects = vcs.commit_subjects(
                        git_repo_root, _MERGE_BASE_BRANCH
                    )
                    main_subjects_available = True
                except VcsCommandError as exc:
                    # `_MRS_STATUS_011`'s cause 1: an unreadable `main`.
                    # Recorded here, REPORTED once after the whole sweep --
                    # see the emission site below the per-home loop. The
                    # read itself is still attempted at most once.
                    main_read_error = exc

            merged_keys: frozenset[str] = frozenset()
            keys_available = main_subjects_available
            withheld_codes: tuple[str, ...] = ()
            if main_subjects_available:
                merged_keys, keys_findings = _merged_keys_for_slug(slug, main_subjects)
                # `_MRS_STATUS_011`'s cause 2 (review finding, 2026-08-10,
                # Blind Hunter): a malformed project-policy file for `slug`
                # -- entirely unrelated to this durability check -- used to
                # inject `_merged_keys_for_slug`'s raw `PolicyIOError`
                # finding (`MRS-POLICY-004`, `Verdict.ERROR`) straight into
                # this DEFAULT `marshal status` sweep, changing its exit
                # code over a patch this story's own Boundaries say must be
                # WARN-tier at worst ("never blocks or changes marshal
                # status's exit code"). `_reconcile_ledger` (an explicit
                # `--project` diagnostic view) still surfaces such findings
                # verbatim; here, an ERROR-severity result instead degrades
                # THIS slug's own patches to `done: null` (unknown),
                # reported once at this module's own established
                # `_MRS_STATUS_011` WARN tier -- never fabricated as landed
                # OR unlanded. This arm is PER-SLUG, so unlike the
                # unreadable-`main` arm above it can fire once per affected
                # home, and its message is scoped to this project's own
                # patches, never to the whole sweep's.
                # The guard tests the finding's own VERDICT class, not its
                # severity (review finding, 2026-08-10, pass 3). The
                # Boundary being defended is about this command's EXIT
                # CODE, which `core/verdict.py`'s own `_CLASSIFY_TABLE`
                # decides -- severity is merely correlated with it today
                # (every `Verdict.UNEVALUABLE` policy code happens to be
                # constructed at `Severity.ERROR`). Testing `classify`
                # directly means a future policy code registered as
                # UNEVALUABLE-but-WARN cannot silently slip through and
                # change `marshal status`'s exit code.
                blocking = [
                    f
                    for f in keys_findings
                    if classify(f.code) is not Verdict.CLEAN
                    and classify(f.code) is not Verdict.WARN
                ]
                if blocking:
                    keys_available = False
                    # The withheld codes are carried to the `MRS-STATUS-011`
                    # message below rather than dropped (review finding,
                    # 2026-08-10, pass 4). Withholding the finding keeps the
                    # exit code honest, but withholding its NAME too left
                    # the operator of the default view unable to tell WHICH
                    # policy problem degraded the home -- the real
                    # diagnostic was invisible in the only view most sweeps
                    # ever run.
                    withheld_codes = tuple(dict.fromkeys(f.code for f in blocking))
                    # Any NON-blocking policy finding is still reported
                    # verbatim -- only the exit-code-changing ones are
                    # withheld (review finding, 2026-08-10, pass 3: the
                    # branch used to discard `keys_findings` wholesale, so
                    # an unrelated WARN accompanying an ERROR vanished).
                    findings.extend(f for f in keys_findings if f not in blocking)
                else:
                    findings.extend(keys_findings)

            failed_patches: list[dict[str, object]] = []
            for patch, size_bytes in patch_paths:
                # `core/status.py`'s OWN best-effort renderer, never a
                # fourth inline copy of the same try/except (review
                # finding, 2026-08-10, pass 3 -- the same "one owner" class
                # as pass 1's `_merged_keys_for_slug` finding). `cli` may
                # import `core`; it is only the reverse direction AD-3/AD-4
                # forbid, which is why that helper's own docstring explains
                # it cannot import `cli/spin.py`'s twin.
                story_key = status_core._render_story_key_best_effort(
                    patch.parent.name
                )
                done: bool | None = (
                    story_key in merged_keys if keys_available else None
                )
                # `confidence` is `core/status.py`'s OWN already-established
                # vocabulary for this EXACT evidence source, never a third
                # one: a POSITIVE `merged_story_keys` match is the stronger
                # direction (`CONFIDENCE_CONFIRMED`); an absence of a match,
                # and an unavailable comparison, both prove nothing
                # (`CONFIDENCE_UNCONFIRMED`). `CONFIDENCE_CONFIRMED` is this
                # vocabulary's own name for the stronger direction and is
                # reused verbatim rather than qualified with a third value
                # -- but it is NOT unqualified proof, and this module must
                # not read it as such: the positive direction is
                # cross-project blind (an open `core/promotion.py` deferral,
                # verified live), so a `done: true` here can in principle be
                # another station's merge. See `_merged_keys_for_slug`'s own
                # docstring above for the measurement.

                confidence = (
                    status_core.CONFIDENCE_CONFIRMED
                    if done is True
                    else status_core.CONFIDENCE_UNCONFIRMED
                )
                failed_patches.append(
                    {
                        "story_key": story_key,
                        "run_id": patch.parent.parent.parent.name,
                        "path": str(patch),
                        "size_bytes": size_bytes,
                        "done": done,
                        "confidence": confidence,
                    }
                )
            facts = replace(facts, failed_patches=tuple(failed_patches))

            # `_MRS_STATUS_011`'s cause 2, reported HERE -- after this
            # home's own entries exist, so the WARN can NAME the patches it
            # degraded. The intent contract's Always bullet requires that a
            # patch "whose landed-status could not be determined" raise
            # "exactly one WARN naming it"; a WARN that named nothing left
            # an operator with a count and no story keys (review finding,
            # 2026-08-10, pass 3). PER-SLUG, so unlike the
            # unreadable-`main` arm it can fire once per affected home, and
            # it is scoped to this project's own patches, never the sweep's.
            if withheld_codes:
                # The message states WHAT HAPPENED, never a specific cause
                # it has not established (review finding, 2026-08-10, pass
                # 4). The earlier wording -- "cannot resolve this project's
                # own merge-subject policy" -- is false for most of the
                # codes that reach this branch: `MRS-POLICY-001` (an
                # unrecognized key) is `Verdict.UNEVALUABLE` and so blocks,
                # yet `compose` still returns a perfectly good
                # `merge_subject_template`. Degrading anyway is the
                # deliberate conservative choice (this read cannot tell a
                # template that came from the project's own file from one
                # that fell back to the default), but asserting the wrong
                # reason for it is not. Naming the withheld codes is what
                # makes the suppressed diagnostic findable at all.
                findings.append(
                    Finding(
                        code=_MRS_STATUS_011,
                        severity=Severity.WARN,
                        message=(
                            f"{slug}: this project's own merge-subject "
                            "policy did not resolve cleanly "
                            f"({', '.join(withheld_codes)}, withheld here so "
                            "a policy problem cannot change this command's "
                            "exit code -- `marshal status --project "
                            f"{slug} --reconcile-ledger` surfaces the "
                            "finding itself, once that project has a "
                            "readable tracked ledger), so its failed-story "
                            "patches cannot be "
                            "classified against a trusted template: "
                            f"{_name_patches([(slug, e) for e in failed_patches])} "
                            "report done: null (landed-status unknown)"
                        ),
                        path=slug,
                    )
                )
            if main_read_error is not None:
                main_unavailable.extend((slug, entry) for entry in failed_patches)

        row, finding = status_core.build_fleet_row(facts)
        rows.append(row)
        if finding is not None:
            findings.append(finding)
        # Story 5.5's own Always bullet: a home with unpushed work is
        # NEVER reported clean -- gated on the RESULTING row (never on
        # `matched` directly), since `build_fleet_row` itself hardcodes
        # `unpushed_work: None` for a degraded (`journal_unreadable`/
        # `has_run=False`) row, mirroring every other fact-derived field's
        # identical precedent (`budget_consumed`, `escalation_reason`).
        if row.get("unpushed_work") is not None:
            unpushed = row["unpushed_work"]
            findings.append(
                Finding(
                    code=_MRS_STATUS_008,
                    severity=Severity.WARN,
                    message=(
                        f"{slug}: branch {facts.branch!r} carries "
                        f"{unpushed.get('files')} file(s) not on origin "
                        f"({unpushed.get('stat')}) -- {unpushed.get('remedy')}"
                    ),
                    path=facts.branch,
                )
            )
        # Story 4.14's own Always bullet: ONE `MRS-STATUS-010` WARN per
        # failed-story patch this row's own `failed_patches` reports as
        # `done is False` (no confirming durable merge, or a story-dir name
        # that does not even parse as a story key) -- mirrors the
        # `unpushed_work` block immediately above. `done is None` (the
        # landed comparison could not be made at all) never fires this
        # per-patch WARN; that case is already named by `_MRS_STATUS_011`
        # above, once per sweep or once per affected slug depending on which
        # of its two causes fired.
        #
        # The message states the UNCONFIRMED direction and WHY, never "has
        # not landed" as an established fact (review finding, 2026-08-10,
        # pass 2 -- the finding that reverted this story's first
        # implementation): the classifier cannot read a GitHub squash-merge's
        # free-form prose subject, nor a `land/<station>-<epic>-<seq>` merge
        # subject, so on the real fleet 2 of 3 such WARNs were false. It
        # also names `run_id` alongside the story key -- repeated failed
        # attempts at ONE story across runs are otherwise distinguishable
        # only by a long absolute path (live: `pyforge-steward` carries
        # three run dirs).
        for entry in row.get("failed_patches") or ():
            if entry.get("done") is False:
                findings.append(
                    Finding(
                        code=_MRS_STATUS_010,
                        severity=Severity.WARN,
                        message=(
                            f"{slug}: failed-story patch for story "
                            f"{_one_line(entry.get('story_key'))} (run "
                            f"{_one_line(entry.get('run_id'))}) at "
                            f"{_one_line(entry.get('path'))} "
                            f"({entry.get('size_bytes')} bytes) has no "
                            "confirming durable merge on "
                            f"{_MERGE_BASE_BRANCH!r} -- UNCONFIRMED, not "
                            "proof it never landed: the merge-subject "
                            "classifier cannot read GitHub squash-merge "
                            "prose or land/<station>-<epic>-<seq> branch "
                            "merges, and a story-dir name that does not "
                            "parse as a story key can never match at all, "
                            "so verify before recovering or discarding "
                            "this patch"
                        ),
                        path=str(entry.get("path")),
                    )
                )

    # Story 4.14: `_MRS_STATUS_011`'s cause 1 (an unreadable `main`), the
    # ONE WARN for the WHOLE sweep its own I/O matrix row specifies --
    # emitted here, after every home has been scanned, so it can NAME every
    # patch it degraded to `done: null` rather than leaving an operator with
    # a bare count (the intent contract's Always bullet: a patch whose
    # landed-status "could not be determined" raises "exactly one WARN
    # naming it"). The git read itself was still attempted at most once,
    # lazily, on the first home found to carry a reportable patch.
    if main_read_error is not None:
        findings.append(
            Finding(
                code=_MRS_STATUS_011,
                severity=Severity.WARN,
                message=(
                    f"cannot read {_MERGE_BASE_BRANCH!r}'s commit history to "
                    "classify failed-story patches: "
                    # `_one_line` HERE too, not only on the story key and
                    # path (review finding, 2026-08-10, pass 5). This
                    # interpolates git's own stderr, which is routinely
                    # MULTI-LINE -- a missing local `main` yields three
                    # lines ("fatal: ambiguous argument 'main'...", "Use
                    # '--' to separate paths...", "'git <command> ...'").
                    # `_render_text_status`'s findings block prints one
                    # finding per line without escaping, so the unsanitized
                    # form split ONE WARN across three output lines, two of
                    # them starting with git-controlled text and no
                    # `MRS-...` prefix. Pass 4 closed this class for
                    # `MRS-STATUS-010`'s operands and left the arm whose
                    # trigger is the ordinary, non-adversarial one open.
                    f"{_one_line(main_read_error)} -- "
                    f"{_name_patches(main_unavailable)} found this sweep "
                    "report done: null (landed-status unknown)"
                ),
            )
        )

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
# ever calling this. Opt-in only: this REPORT (and its tracked-ledger YAML
# read, which AD-5 forbids the default views from performing at all) is
# never folded into the default view -- a YAML parse plus a `git log`-scale
# walk over `main`'s full history is a genuinely heavier read than either
# sibling switch, per the spec's own Design Notes.
#
# Story 4.14 correction: the GIT half of that read IS now folded into the
# default fleet sweep -- `run_status` performs the same
# `vcs.commit_subjects(root, "main")` walk to classify failed-story
# patches. It is still read at most ONCE per invocation and reused for
# every home, which is what keeps that cost bounded; the earlier "most
# homes carry no failed patches" rationale for making it lazy is
# measurably false (7 of 8 live homes carry at least one patch as of
# 2026-08-10), so laziness is only a degenerate-case optimization for a
# genuinely patch-free fleet, never the common path.
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

    # Git's own durable-merge evidence is REQUIRED, not best-effort (mirrors
    # `cli/deploy.py::_scan_promotions`'s identical "cannot honestly
    # determine ANY story's durability this run" rationale for its own
    # `_MRS_DEPLOY_003`) -- a read failure here is a hard, run-wide finding,
    # never a silently-empty `merged_keys` (which would read as "nothing
    # merged yet" and report every ledger `done` key as a false positive).
    main_subjects: tuple[str, ...] = ()
    git_error: VcsCommandError | None = None
    try:
        main_subjects = vcs.commit_subjects(root, _MERGE_BASE_BRANCH)
    except VcsCommandError as exc:
        git_error = exc

    # Story 4.14 review finding: this project-policy-read-then-
    # `merged_story_keys` sequence used to be duplicated verbatim here and
    # in the failed-story-patch fold in `run_status` -- `_merged_keys_for_
    # slug` is now the ONE shared implementation, called from both. This
    # view surfaces every returned finding at FACE VALUE (including an
    # ERROR-severity `MRS-POLICY-004`); the default sweep's fold cannot,
    # since that would change `marshal status`'s own exit code -- see that
    # call site.
    #
    # Called UNCONDITIONALLY, and its findings appended BEFORE the git
    # failure is reported, so this view's own already-shipped ordering and
    # content are preserved exactly (review finding, 2026-08-10, pass 2):
    # the pre-4.14 code resolved this project's policy BEFORE reading git,
    # so a git failure still reported a malformed project-policy TOML's own
    # `MRS-POLICY-004`. Returning early on the git failure -- before this
    # call -- would silently drop that already-shipped diagnostic. On that
    # path `main_subjects` is empty, so the returned `merged_keys` is
    # meaningless and deliberately unused: the view reports no
    # discrepancies at all when git could not be read.
    merged_keys, keys_findings = _merged_keys_for_slug(slug, main_subjects)
    findings.extend(keys_findings)

    if git_error is not None:
        findings.append(
            Finding(
                code=_MRS_STATUS_007,
                severity=Severity.ERROR,
                message=(
                    f"cannot read {_MERGE_BASE_BRANCH!r}'s commit history "
                    f"to determine story durability: {git_error}"
                ),
            )
        )
        data = {"project": slug, "discrepancies": []}
        return _emit(args, data, findings, _render_text_reconcile, data_version=2)

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
        # Story 5.5 (FR-62/AD-48): the SAME `unpushed_work` dict the
        # `--format json` payload carries -- a pure projection, never a
        # second/independently-derived summary (NFR-12).
        unpushed = home.get("unpushed_work")
        if unpushed is not None:
            # Code review (2026-08-07, Edge Case Hunter): the detector's
            # own `stat` text is sanitized to a single line before
            # interpolation -- an embedded newline would otherwise break
            # this renderer's own "one line per row" contract every other
            # text-format consumer of this output relies on.
            stat_text = str(unpushed.get("stat")).replace("\n", " ").strip()
            line += f" UNPUSHED files={unpushed.get('files')} ({stat_text})"
        # Story 4.14 (FR-176): the SAME `failed_patches` list the
        # `--format json` payload carries -- a pure projection (NFR-12).
        # Only a COUNT here, mirroring `unpushed`'s own single-line
        # convention -- each patch's own story key/path/size/run is already
        # named in its own `MRS-STATUS-010` finding line below when pending,
        # and in the JSON payload always.
        #
        # The `done` TRI-STATE is rendered in full, never collapsed to two
        # states (review finding, 2026-08-10, pass 2): counting only
        # `pending` made an all-`null` sweep -- one where `main` could not
        # be read at all, so nothing was classified -- render
        # `FAILED_PATCHES n=3 pending=0`, byte-identical to all-landed. That
        # fabricates unknown as clean, exactly what this module's own rule
        # for the sibling `unpushed_work` signal forbids ("never fabricated
        # as 'nothing to report'").
        failed = home.get("failed_patches") or ()
        if failed:
            pending = sum(1 for entry in failed if entry.get("done") is False)
            unknown = sum(1 for entry in failed if entry.get("done") is None)
            line += (
                f" FAILED_PATCHES n={len(failed)} pending={pending} "
                f"unknown={unknown}"
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
