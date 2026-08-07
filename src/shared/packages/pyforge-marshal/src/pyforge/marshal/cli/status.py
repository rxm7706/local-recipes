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
read (AD-5's own explicit prohibition) -- see ``core/status.py``'s own
module-level docstring section for the pure derivation core this module
feeds.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..adapters.clock_system import SystemClock
from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness
from ..adapters.process_posix import PosixProcess
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import status as status_core
from ..core.journal import Phase, fold
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.clock import ClockPort
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.process import ProcessPort
from ..ports.vcs import VcsPort
from .config import _suppress_downstream_pipe_close

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
    identically."""

    launch_pid: int | None
    launched_at: datetime | None
    supervisor_pid: int | None
    budget_consumed: int | float | None


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

    return _RunJournalFacts(
        launch_pid=launch_pid,
        launched_at=launched_at,
        supervisor_pid=supervisor_pid,
        budget_consumed=budget_consumed,
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

    harness_run_id = resolve_harness_run_id(fs, run_dir, run_id)
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

    data["homes"] = rows
    return _emit(args, data, findings)


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
        lines.append(
            f"  {home['slug']} ({home['branch']}): {home['state']} "
            f"story={home['current_story']} "
            f"elapsed_seconds={home['elapsed_seconds']} "
            f"budget_consumed={home['budget_consumed']}"
        )

    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(
                f"  {finding.code} [{finding.severity.value}] {finding.message}"
            )
    return "\n".join(lines)


def _emit(
    args: argparse.Namespace, data: dict[str, object], findings: list[Finding]
) -> int:
    """The envelope-build-then-print tail every ``cli/*.py`` command shares
    (AD-14: one envelope shape per command)."""
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="status", verdict=verdict_value, data=data, findings=tuple(findings)
    )

    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = _render_text_status(envelope.data, envelope.findings)

    try:
        print(rendered, flush=True)
    except OSError:
        _suppress_downstream_pipe_close()

    return exit_code_for(envelope.verdict)
