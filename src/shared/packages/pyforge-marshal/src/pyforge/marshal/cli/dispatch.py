"""``marshal factory dispatch`` (Story 22.1, FR-193 CAP-1) -- launch exactly
one worktree-isolated ``bmad-build-auto`` session under marshal governance.

Story 22.7 (FR-193 CAP-7) adds ``marshal factory drain``: the fleet-wide
campaign mode that reads every pyforge station's ordered backlog from its
TRACKED ``sprint-status-ledger.yaml`` (plus optional in-repo order
overrides), applies a campaign mode, and hands each station its next story
by calling ``dispatch_once`` -- the same primitive, once per station per
cycle, so the CAP-2 zombie refusal, the CAP-5 one-per-station guard, and the
CAP-5 cross-station overlap advisory are INHERITED, never re-implemented.
Chaining is structural rather than scripted: a detached campaign supervisor
re-runs the cycle, and a station whose story finished merge-through-finalize
(CAP-4: CI-green merge, scoped ``sprint-ledger-sync --project <station>``,
spec promotion) has an advanced ledger and a free slot, so the next cycle
dispatches its next story. This supersedes ``.cursor/pyforge-fleet-drain/``'s
hand-driven coordinator; campaign state lives in-repo under
``pyforge-marshal``, never in session-local ``.cursor/`` YAML.

Story 22.11 (FR-193 CAP-10) extends this same surface with two pure
read-scope/read-order overrides -- never a second campaign implementation:
``drain --station <slug>`` restricts one cycle to exactly one station's own
tracked backlog (``execute_fleet_cycle``'s ``station`` argument), and
``dispatch <slug> --stories k1,k2,...`` chains a caller-supplied ordered
sequence on that station instead of its ledger order
(``execute_fleet_cycle``'s ``explicit_stories`` argument, backed by
``dispatch_fleet.explicit_story_backlog``). ``dispatch --stories`` is a thin
translation layer over ``run_fleet_drain`` itself -- both surfaces share one
preflight/journal/campaign-supervisor implementation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError, ProcessPort, ProcessResult

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadbuild import BmadBuildHarness, BuildHarnessError
from ..adapters.harness_bmadloop import HarnessError, resolve_loop_runner
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import (
    deferred_work,
    dispatch_flag_gate,
    dispatch_fleet,
    dispatch_prelaunch,
    dispatch_re_preflight,
    gate,
    harness_profile,
    policy,
)
from ..core import dispatch as dispatch_core
from ..core import promotion as promotion_core
from ..core.commit_vcs import CommittingVcs
from ..core.dispatch_completion import (
    DispatchGitFacts,
    DispatchSessionVerdict,
    is_spec_only_narration,
    narration_spec_path,
    zombie_redispatch_evidence,
)
from ..core.dispatch_harness_done import (
    FollowupReview,
    followup_review_recommended,
    is_followup_review_spec,
    land_fail_operator_message,
    parse_blocking_condition,
    parse_spec_status,
    should_take_harness_done_land_only,
    should_take_verification_refusal_land_only,
)
from ..core.dispatch_landing import DispatchLandingVerdict
from ..core.dispatch_retry import (
    DispatchBlockKind,
    classify_dispatch_block,
    exclude_harness_profiles_after_transient_failure,
    format_verification_refusal_park_reason,
    is_dispatch_verification_refusal,
    prune_blocked_stories_merged_on_main,
    verification_refusal_head_unchanged,
)
from ..core.dispatch_supervisor_finalize import (
    finalize_attempt_failed,
    finalize_attempt_journaled,
    finalize_failure_worktree_path,
)
from ..core.dispatch_verification import (
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    judge_dispatch_verification,
)
from ..core.identity import (
    MalformedStoryKeyError,
    StoryKey,
    normalize,
    render_feed_key,
)
from ..core.journal import (
    LANDING_CHECKS_FIELD,
    FoldResult,
    JournalEntryId,
    Phase,
    build_entry,
    fold,
    mint_run_id,
    prepare_for_write,
    resolve_land_findings_from_payload,
    resolve_scope_violation_advisories_from_payload,
    sidecar_texts_for_lines,
)
from ..core.model import Envelope, Finding, Severity, build_envelope
from ..core.model_cost import (
    adapter_provider,
    catalog_declared,
    is_harness_default_model,
    provider_declaring_model,
)
from ..core.refs import ORIGIN_MAIN, ORIGIN_MAIN_SHORT
from ..core.spec_deps import story_deps_from_epics, story_transitively_depends_on
from ..core.spec_surface import SurfaceParseError, parse_declared_surface
from ..core.supervise import count_unified_diff_lines, resolve_terminal_session_verdict
from ..core.verdict import EXIT_USAGE, compute_verdict, exit_code_for
from ..dispatch_land import execute_dispatch_land
from ..dispatch_supervisor.__main__ import gather_dispatch_git_facts
from ..dispatch_verify import evaluate_dispatch_verification, run_dispatch_ruff_format_before_verify
from ..ports.build_harness import BuildHarnessPort
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.vcs import VcsPort
from ..scope import format_scope_drift, verify_scope
from ..seed.detect.kit import layer_enabled, probe_instrument
from ..seed.model.kit import CODEGRAPH_INDEX_RELPATH, KitItemId, kit_item
from ..seed.verbs.kit import IndexBuilder, build_codegraph_index, render_deployed_skill
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
    read_repo_policy_defaults,
)
from .land import _parse_sprint_ledger_statuses
from .seed import packaged_seed_model_version

if TYPE_CHECKING:
    from ..core.context import MarshalContext


@dataclass(frozen=True)
class DispatchPreflightConflict:
    """A dispatch refusal with its registered finding code (Story 22.2/22.5)."""

    code: str
    message: str
    in_flight_story_key: str
    overlap_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class DispatchAttempt:
    """One ``dispatch_once`` outcome: envelope ``data`` plus its findings."""

    data: dict[str, object]
    findings: tuple[Finding, ...]

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == Severity.ERROR)

    @property
    def launched(self) -> bool:
        """True when a session pid was recorded and nothing blocked it."""
        return not self.errors and self.data.get("session_pid") is not None


@dataclass(frozen=True)
class FleetCycleReport:
    """One fleet-drain cycle's per-station results, findings, and data."""

    results: tuple[dispatch_fleet.StationCycleResult, ...]
    findings: tuple[Finding, ...]
    data: dict[str, object]

    @property
    def complete(self) -> bool:
        return dispatch_fleet.campaign_complete(self.results)


_JOURNAL_FILENAME = "journal.jsonl"
_LOG_FILENAME = "session.log"
_SUPERVISOR_LOG_FILENAME = "dispatch-supervisor.log"
_FLEET_SUPERVISOR_LOG_FILENAME = "fleet-drain-supervisor.log"
_BASE_REF = ORIGIN_MAIN  # Story 60.1 (CAP-270): the full refname, never a short name a local ref can shadow

#: How long the detached campaign supervisor waits between cycles -- passed
#: to it, never slept on here. A cycle is cheap (ledger reads + git/process
#: facts) and a story takes minutes to hours, so this matches the per-story
#: supervisor's own 60 s tick.
_FLEET_TICK_SECONDS = 60

#: Short, matching `cli/land.py`'s own advisory-lock convention: a cycle is
#: cheap and the supervisor re-ticks, so waiting long buys nothing over
#: refusing and letting the next cycle retry.
_FLEET_CYCLE_LOCK_TIMEOUT_S = 5.0

#: The run-id shape `mint_run_id` produces. `--campaign` names a DIRECTORY
#: under the campaign runs tree, so anything path-shaped is refused.
_SAFE_CAMPAIGN_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _is_safe_campaign_id(raw: str) -> bool:
    return bool(_SAFE_CAMPAIGN_ID_RE.match(raw)) and raw not in {".", ".."}


def add_factory_dispatch_subparser(factory_subparsers: argparse._SubParsersAction) -> None:
    parser = factory_subparsers.add_parser(
        "dispatch",
        help="Launch one detached bmad-build-auto story session (Story 22.1).",
        description=(
            "Provisions a fresh isolated worktree from origin/main, launches "
            "exactly one detached session harness run with BMAD_ACTIVE_PROJECT "
            "per-invocation and physical artifact paths, journals the launch, "
            "and returns promptly. With --stories (Story 22.11, FR-193 "
            "CAP-10), chains a caller-supplied ordered sequence on this one "
            "station instead -- a thin translation over `factory drain`'s own "
            "campaign machinery (fleet-wide advisory lock, journal, detached "
            "supervisor), never a second implementation."
        ),
    )
    parser.add_argument("slug", help="The BMAD project slug (station).")
    parser.add_argument(
        "story",
        nargs="?",
        default=None,
        help="The backlog story key to dispatch (omit when passing --stories).",
    )
    parser.add_argument(
        "--stories",
        default=None,
        help=(
            "Comma-separated ordered story keys to chain on this station "
            "instead of a single story (Story 22.11, FR-193 CAP-10) -- "
            "launched one dispatch at a time via the same chaining "
            "`factory drain` already uses. Every key must already be "
            "eligible on the station's TRACKED backlog (not done, not "
            "unknown) or the whole sequence is refused before any "
            "worktree is provisioned."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--harness",
        default=None,
        help=(
            "Ordered session-harness preference for this invocation only "
            "(comma-separated profile names, e.g. cursor,claude). Overrides "
            "project/repo defaults without editing marshal-policy.toml."
        ),
    )
    parser.set_defaults(handler=run_dispatch)


def _writer_id() -> str:
    return f"dispatch-{os.getpid()}"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc_compact(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%S") + f"{moment.microsecond // 1000:03d}Z"


def _format_entry_ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _random_token() -> str:
    return secrets.token_hex(4)


def _dispatch_scope_refusal(slug: str) -> Finding | None:
    """Story 33.9 / FR-190 CAP-1 third call site: refuse before any launch work
    when the parent shell's own ``BMAD_ACTIVE_PROJECT`` disagrees with the
    dispatch slug.

    Story 64.1 (CAP-273, FR-219) retires the primary-checkout
    ``verify_scope`` branch this function used to also run here: the
    PRIMARY checkout's marker/links are never read or written by dispatch
    at all now (another station may own the shared marker with no effect
    on this launch). The triangle that actually matters is the dispatch
    WORKTREE's own, checked once ``_ensure_dispatch_worktree`` resolves it
    -- see ``_seed_dispatch_worktree_scope`` below.
    """
    env_slug = os.environ.get("BMAD_ACTIVE_PROJECT", "").strip()
    if env_slug and env_slug != slug:
        return Finding(
            code="MRS-DISP-041",
            severity=Severity.ERROR,
            message=(
                f"scope drift: dispatch resolved project {slug!r} disagrees with "
                f"BMAD_ACTIVE_PROJECT env {env_slug!r} -- use physical paths under "
                f"_bmad-output/projects/{slug}/ and never scripts/bmad-switch"
            ),
        )
    return None


def _seed_dispatch_worktree_scope(*, fs: FsPort, worktree: Path, slug: str) -> Finding | None:
    """Story 64.1 (CAP-273, FR-219): give the dispatch WORKTREE its own
    scope triangle -- never the shared primary checkout's -- then refuse
    via the unmodified ``verify_scope`` (``scope.py``) on any drift that
    remains.

    Mirrors ``cli/init.py``'s MRS-INIT-003 loop-home seeding shape but is
    strictly narrower: a corner that already exists here -- correct,
    foreign, or unrecognized -- is NEVER repointed or overwritten; only a
    corner that is genuinely absent gets written, through ``FsPort`` only
    (AD-11). ``fs.read_text``/``fs.read_symlink_target`` return ``None``
    for "missing"; a link corner also needs ``fs.exists`` to tell a
    dangling/absent path apart from a real, non-symlink file squatting
    there (which counts as an existing corner too, per
    ``ports/fs.py``'s own ``exists`` docstring) -- never touched either
    way. A write failure degrades to ``MRS-DISP-006`` ("cannot provision"),
    matching this module's other worktree-provisioning failures; it never
    raises past this function.
    """
    marker_path = worktree / "_bmad" / "custom" / ".active-project"
    planning_link = worktree / "_bmad-output" / "planning-artifacts"
    implementation_link = worktree / "_bmad-output" / "implementation-artifacts"
    try:
        if fs.read_text(marker_path) is None:
            fs.write_text_atomic(marker_path, f"{slug}\n")
        for link, name in (
            (planning_link, "planning-artifacts"),
            (implementation_link, "implementation-artifacts"),
        ):
            if fs.read_symlink_target(link) is None and not fs.exists(link):
                fs.repoint_symlink_atomic(link, Path("projects") / slug / name)
    except FsError as exc:
        return Finding(
            code="MRS-DISP-006",
            severity=Severity.ERROR,
            message=f"cannot provision dispatch worktree scope triangle at {worktree!r}: {exc}",
        )
    drift = verify_scope(worktree, slug)
    if drift is not None:
        return Finding(
            code="MRS-DISP-041",
            severity=Severity.ERROR,
            message=f"{format_scope_drift(drift)} (dispatch worktree {worktree!r})",
        )
    return None


def _append_entry(fs: FsPort, run_dir: Path, entry, *, fsync: bool) -> None:
    prepared = prepare_for_write(entry)
    if prepared.sidecar_relative_path is not None:
        fs.write_text_atomic(run_dir / prepared.sidecar_relative_path, prepared.sidecar_content)
    fs.append_line(run_dir / _JOURNAL_FILENAME, prepared.line, fsync=fsync)


def _emit(
    args: argparse.Namespace,
    data: dict[str, object],
    findings: list[Finding],
    *,
    command: str = "factory dispatch",
) -> int:
    envelope = build_envelope(
        command=command,
        verdict=compute_verdict(tuple(findings)),
        data=data,
        findings=tuple(findings),
    )
    try:
        if args.format == "json":
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True), flush=True)
        else:
            lines = [f"command: {command}", f"verdict: {envelope.verdict.value}"]
            for key, value in data.items():
                lines.append(f"{key}: {value}")
            for finding in findings:
                lines.append(f"finding {finding.code}: {finding.message}")
            print("\n".join(lines), flush=True)
    except OSError, UnicodeEncodeError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _policy_flags_from_harness_arg(raw: str | None) -> dict[str, object]:
    if raw is None or not str(raw).strip():
        return {}
    profiles = tuple(part.strip() for part in str(raw).split(",") if part.strip())
    if not profiles:
        return {}
    return {"harness_preference": profiles}


def _compose_policy(slug: str, *, flags: dict[str, object] | None = None) -> policy.EffectivePolicy:
    # Story 22.8: the repo-defaults layer (AD-16 layer 2) composes here too
    # -- `harness_preference` is repo-expressed on this machine
    # (`_bmad-output/policy-defaults.toml`). An unreadable file degrades to
    # an empty layer, the same silent-tolerant posture this helper already
    # takes for the project layer (run_config is the loud boundary).
    repo_defaults, _repo_finding = read_repo_policy_defaults()
    project_data: dict[str, object] = {}
    candidate = conventional_project_policy_path(slug)
    if candidate.is_file():
        try:
            project_data = dict(_read_project_policy(candidate))
        except PolicyIOError:
            project_data = {}
    effective, _findings = policy.compose(
        project_slug=slug,
        repo_defaults=repo_defaults,
        project=project_data,
        flags=dict(flags or {}),
    )
    return effective


def _surface_worktree_wip_before_dispatch(
    *,
    vcs: VcsPort,
    repo_root: Path,
    worktree: Path,
    baseline_head_sha: str,
) -> Finding | None:
    """Story 28.13 (CAP-15): report existing WIP before touching the worktree."""
    try:
        changed = vcs.changed_files(repo_root, worktree, base=baseline_head_sha)
    except VcsCommandError:
        return None
    if not changed:
        return None
    line_count: int | None
    try:
        patch = vcs.worktree_unified_patch(worktree, baseline_sha=baseline_head_sha)
        line_count = count_unified_diff_lines(patch)
    except VcsCommandError:
        line_count = None
    file_count = len(changed)
    detail = f"{file_count} changed file(s)"
    if line_count is not None:
        detail += f", {line_count} diff line(s)"
    else:
        detail += " (diff line count unavailable)"
    return Finding(
        code="MRS-DISP-036",
        severity=Severity.WARN,
        message=(f"worktree {worktree!r} already carries uncommitted changes before this dispatch proceeds: {detail}"),
    )


_SESSION_CHECK_ARGV = ("pixi", "run", "--frozen", "-e", "pyforge-guild", "steward", "session", "check", "--json")
_SESSION_CHECK_TIMEOUT_S = 60.0
#: Story 83.6: when steward's only non-ok rows are the kit aggregate and the
#: codegraph-index row reporting a stale index, prelaunch may resync before
#: re-checking. Any other non-ok name keeps today's warn-only path.
_STALE_CODEGRAPH_RESYNC_FINDING_NAMES = frozenset({"token-kit", "codegraph-index"})


def _run_steward_session_check(*, process: ProcessPort, repo_root: Path) -> ProcessResult:
    """Shell ``steward session check --json`` once."""
    return process.run(list(_SESSION_CHECK_ARGV), cwd=repo_root, timeout_s=_SESSION_CHECK_TIMEOUT_S)


def _session_report_payload(stdout: str | None, stderr: str | None) -> dict[str, Any] | None:
    """``steward session check --json``'s report, from whichever stream carries it.

    Steward prints a passing duty's summary to stdout and a failed one's to stderr
    (``steward``'s ``cli.py::main``), so the non-ok report this caller acts on arrives
    on stderr. Reading stdout alone fell back to the last stderr line, ``}``, on every
    real run (Story 79.1). Stdout is read first. Within a stream the report is the first
    JSON object that opens at the start of a line and carries ``findings``, so a warning
    (even a JSON log line) printed before it, or a line after it, does not hide it; a
    stream with no such object is skipped.
    """
    decoder = json.JSONDecoder()
    for stream in (stdout, stderr):
        if not stream:
            continue
        offset = 0
        for line in stream.splitlines(keepends=True):
            if line.startswith("{"):
                try:
                    payload, _end = decoder.raw_decode(stream, offset)
                except json.JSONDecodeError:
                    payload = None
                if isinstance(payload, dict) and "findings" in payload:
                    return payload
            offset += len(line)
    return None


def _session_check_only_stale_codegraph(payload: Mapping[str, object]) -> bool:
    """True when every non-ok steward finding is the kit/codegraph stale pair."""
    try:
        rows = payload.get("findings", [])
        if not isinstance(rows, list):
            return False
        non_ok = [row for row in rows if isinstance(row, Mapping) and not row.get("ok", True)]
    except AttributeError, TypeError:
        return False
    if not non_ok:
        return False
    names = {row.get("name") for row in non_ok}
    if not names or not names <= _STALE_CODEGRAPH_RESYNC_FINDING_NAMES:
        return False
    codegraph = next((row for row in non_ok if row.get("name") == "codegraph-index"), None)
    if codegraph is None:
        return False
    detail = str(codegraph.get("detail") or "").lower()
    return "stale" in detail


def _resync_stale_codegraph_index(
    repo_root: Path,
    *,
    index_builder: IndexBuilder = build_codegraph_index,
) -> None:
    """Run the kit's incremental resync and stamp the index mtime (Story 83.6).

    Failures are ignored here: the follow-up session check decides whether to
    warn. Never blocks a launch."""
    error = index_builder(repo_root, stale=True)
    if error is not None:
        return
    try:
        os.utime(repo_root / CODEGRAPH_INDEX_RELPATH, None)
    except OSError:
        pass


def _finding_from_session_check_result(result: ProcessResult) -> Finding | None:
    """Fold one ``steward session check`` subprocess result into MRS-DISP-049."""
    if result.returncode == 0:
        return None
    detail: str | None = None
    payload = _session_report_payload(result.stdout, result.stderr)
    if payload is not None:
        try:
            non_ok = [row.get("name", "?") for row in payload.get("findings", []) if not row.get("ok", True)]
            detail = f"non-ok findings: {', '.join(non_ok)}" if non_ok else "reported findings"
        except AttributeError, TypeError:
            detail = None
    if detail is None:
        tail_lines = (result.stderr or result.stdout or "").strip().splitlines()
        detail = tail_lines[-1] if tail_lines else "steward session check reported findings"
    return Finding(
        code="MRS-DISP-049",
        severity=Severity.WARN,
        message=f"steward session check reported a non-ok session-precondition verdict: {detail}",
    )


def _surface_session_precondition_findings(
    *,
    process: ProcessPort,
    repo_root: Path,
    index_builder: IndexBuilder = build_codegraph_index,
) -> Finding | None:
    """Story 63.4 (spec-pyforge-steward CAP-5): shell ``steward session check
    --json`` right after ``repo_root`` resolves and fold a non-ok
    session-precondition verdict (pixi/pyforge-guild, bmad-method drift, the
    token-economy kit + codegraph index, gh auth/rate-limit, the Tier-3
    sprint-status feed) into a WARN finding -- non-blocking, mirroring
    ``_surface_worktree_wip_before_dispatch``'s shape. Never escalated to
    ERROR: a session-precondition gap is worth flagging before a dispatch
    launches, not worth refusing the launch over.

    Story 83.6: when the only non-ok rows are ``token-kit`` and
    ``codegraph-index`` reporting a stale index, run the kit's incremental
    ``codegraph sync`` (via ``build_codegraph_index(..., stale=True)``),
    re-check once, and omit MRS-DISP-049 when the second check passes. A
    resync failure or timeout leaves today's warning; any other non-ok row
    skips the resync entirely.
    """
    try:
        result = _run_steward_session_check(process=process, repo_root=repo_root)
    except ProcessError as exc:
        return Finding(
            code="MRS-DISP-049",
            severity=Severity.WARN,
            message=f"steward session check could not run: {exc} -- session preconditions unverified",
        )
    if result.returncode != 0:
        payload = _session_report_payload(result.stdout, result.stderr)
        if payload is not None and _session_check_only_stale_codegraph(payload):
            _resync_stale_codegraph_index(repo_root, index_builder=index_builder)
            try:
                result = _run_steward_session_check(process=process, repo_root=repo_root)
            except ProcessError as exc:
                return Finding(
                    code="MRS-DISP-049",
                    severity=Severity.WARN,
                    message=f"steward session check could not run: {exc} -- session preconditions unverified",
                )
    return _finding_from_session_check_result(result)


_FLAG_GATE_TIMEOUT_S = 60.0


def _consult_flag_gate(*, fs: FsPort, process: ProcessPort, repo_root: Path, spec_path: Path) -> Finding | None:
    """Story 74.2 (spec-feature-flag-governance CAP-3): consult the Guild's flag
    gate on the story's tracked spec before any worktree or session exists.

    Runs ``<this interpreter> scripts/flag_gate_check.py --spec <spec>`` from
    ``repo_root`` through ``process`` -- the gate is a process, never an import
    (Charter Section 6: it belongs to no station) -- and hands its exit code and
    JSON to ``core.dispatch_flag_gate``, which decides. The result: an ERROR
    ``MRS-DISP-052`` (the gate reds the spec, or could not judge it -- a timeout
    included), a WARN ``MRS-DISP-055`` (a pre-rule spec; the gate script absent
    from this repository), or ``None`` (the gate passes). No policy key turns
    the consult off: CI reds regardless."""
    if not fs.exists(repo_root / dispatch_flag_gate.GATE_SCRIPT_REL):
        return dispatch_flag_gate.gate_absent_finding()
    try:
        spec_arg = spec_path.relative_to(dispatch_core.canonical_repo_root(repo_root)).as_posix()
    except ValueError:
        spec_arg = str(spec_path)
    argv = [sys.executable, dispatch_flag_gate.GATE_SCRIPT_REL, "--spec", spec_arg]
    try:
        result = process.run(argv, cwd=repo_root, timeout_s=_FLAG_GATE_TIMEOUT_S)
    except ProcessError as exc:
        return dispatch_flag_gate.decide_gate_failure(spec_arg, str(exc))
    return dispatch_flag_gate.decide_gate_result(
        spec_arg, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr
    )


def _seed_dispatch_output_layer(*, fs: FsPort, worktree: Path, context_payload: Mapping[str, object]) -> Finding | None:
    """Story 28.30 (CAP-3, dispatch half of the ``output`` layer): deploy
    the caveman output-compression skill into a fresh dispatch worktree
    when ``[context].output`` is enabled.

    Reuses ``seed/verbs/kit.py``'s own packaged-payload resolution
    (``probe_instrument``) and render step (``render_deployed_skill``) --
    the loop-home APPLY step itself (``_apply_caveman_skill``) is out of
    reach here: ``seed/``'s AD-11 write boundary is scoped to a loop home,
    and a dispatch worktree is not one, so this function writes directly
    through the same ``FsPort`` the rest of ``dispatch_once`` already uses.

    Never raises: an unavailable instrument or any write failure degrades
    to a named WARN finding -- Story 28.3's own
    ``kit-instrument-unavailable``/``kit-item-missing`` degrade shape --
    and the caller proceeds with the session unwrapped either way, matching
    every other layer's "an unavailable instrument disables its layer with
    a named finding, never blocks a run" contract. A layer declared off
    (the default) deploys nothing -- today's behavior, byte-identical."""
    item = kit_item(KitItemId.CAVEMAN_SKILL)
    layer = context_payload.get(item.layer)
    if not isinstance(layer, Mapping) or not layer.get("enabled", False):
        return None
    probe = probe_instrument(item)
    if not probe.available or probe.payload is None:
        return Finding(
            code="MRS-DISP-042",
            severity=Severity.WARN,
            message=(
                f"the {item.layer!r} layer is enabled but "
                f"{probe.reason or 'its instrument payload did not resolve'} -- "
                "this dispatch session runs unwrapped"
            ),
        )
    try:
        upstream = probe.payload.read_text(encoding="utf-8")
        model_version = packaged_seed_model_version()
        target = worktree / item.relpath
        fs.ensure_dir(target.parent)
        fs.write_text_atomic(target, render_deployed_skill(upstream, model_version))
    except (OSError, UnicodeDecodeError, ValueError, PyforgeError) as exc:
        return Finding(
            code="MRS-DISP-042",
            severity=Severity.WARN,
            message=(
                f"could not deploy the caveman {item.layer!r}-layer skill into "
                f"{worktree!r}: {type(exc).__name__}: {exc} -- this dispatch "
                "session runs unwrapped"
            ),
        )
    return None


#: The command MRS-DISP-053 names as the fix for a missing base index
#: (Story 46.1, CAP-192): it builds -- or fetches -- the substrate's
#: `.codegraph/` on the primary checkout, which every later dispatch then
#: copies and syncs instead of indexing from scratch.
_CONTEXT_BOOTSTRAP_COMMAND = "pixi run -e pyforge-guild marshal context bootstrap"

_STRUCTURE_GRAPH_MODE_SYNC = "sync"
_STRUCTURE_GRAPH_MODE_INIT = "init"
_STRUCTURE_GRAPH_MODE_SKIPPED = "skipped"


@dataclass(frozen=True)
class StructureGraphSeed:
    """``_seed_dispatch_structure_graph``'s outcome for ONE dispatch (Story
    77.1, CAP-282), the ``structure-graph`` twin of ``harness_profile.WireWrap``.

    ``mode`` is ``sync`` (a base index was copied or already there, and
    ``codegraph sync -q`` refreshed it), ``init`` (``codegraph init -y`` built
    one in the worktree) or ``skipped`` (no index was seeded). ``applied`` is
    true for the first two only. ``reason`` is ``None`` for the plain
    ``sync`` path and the layer-off shape; otherwise it says why the path was
    not the plain one (why the run built instead of synced, or why nothing was
    seeded). ``findings`` are the WARNs the dispatch folds into its envelope.

    The default instance is the layer-off shape: nothing was copied or run
    and no finding is raised, but the payload still reports ``applied: false``
    (the envelope and the ``dispatch-launch`` OUTCOME entry always carry the
    key). ``journal_payload()`` is the one spelling of the payload both carry."""

    applied: bool = False
    mode: str = _STRUCTURE_GRAPH_MODE_SKIPPED
    reason: str | None = None
    seconds: float = 0.0
    findings: tuple[Finding, ...] = ()

    def journal_payload(self) -> dict[str, object]:
        """A fresh plain ``dict`` per call, so the echoed envelope and the
        journal entry can never alias one another."""
        return {
            "applied": self.applied,
            "mode": self.mode,
            "reason": self.reason,
            "seconds": self.seconds,
        }


def _codegraph_files(directory: Path) -> list[Path]:
    """Every regular file under ``directory`` (sorted), never following a
    symlink -- a symlinked file is skipped and a symlinked directory is not
    entered. Read-only."""
    found: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(directory, followlinks=False):
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink() or not path.is_file():
                continue
            found.append(path)
    return sorted(found)


def _discard_worktree_index(fs: FsPort, index_dir: Path) -> None:
    """Best-effort removal of a worktree's ``.codegraph/`` that this dispatch
    created and could not finish.

    Two callers need it. A ``codegraph init -y`` over an existing
    ``.codegraph/`` is a silent no-op that exits 0 ("Already initialized" --
    measured 2026-09-29, even over a corrupt db), so the fallback that follows
    a failed sync must clear the copied index first or it would report a build
    that never ran. And a session must not open on a half-built index:
    ``bmad-build-auto``'s step 01 prefers ``.codegraph/codegraph.db`` whenever
    it exists (Story 28.33), and a timeout can leave a partial db behind. Only
    called for a directory this run created; a re-dispatched worktree's own
    index is never touched. Never raises."""
    for path in _codegraph_files(index_dir):
        try:
            path.unlink()
        except OSError:
            pass
    for dirpath, _dirnames, _filenames in os.walk(index_dir, topdown=False):
        try:
            fs.remove_empty_dir(Path(dirpath))
        except OSError, PyforgeError:
            pass


def _seed_dispatch_structure_graph(
    *,
    fs: FsPort,
    process: ProcessPort,
    worktree: Path,
    repo_root: Path,
    context_payload: Mapping[str, Mapping[str, Any]],
) -> StructureGraphSeed:
    """Story 77.1 (spec-pyforge-marshal CAP-282, dispatch half of the
    ``structure-graph`` layer): give a fresh dispatch worktree a codegraph
    index, the way Story 28.31's spike measured it -- ``codegraph sync -q``
    from a shared base (~4 s) rather than ``codegraph init -y`` per worktree
    (~19 s, ~222 MiB). Mirrors ``_seed_dispatch_output_layer`` (Story 28.30):
    never raises, a layer that is off does nothing, an instrument that is
    unavailable or a step that fails becomes a named WARN, and the dispatch
    proceeds without an index either way.

    Order: (1) layer off -> the off shape. (2) ``codegraph`` not on PATH ->
    ``skipped``, MRS-DISP-054, nothing copied. (3) the worktree already holds
    an index (a re-dispatch) -> ``sync -q`` only, never a copy over it. (4)
    the primary checkout holds a base -> copy its files, then ``sync -q``.
    (5) no base -> ``init -y`` here, and MRS-DISP-053 names ``marshal context
    bootstrap`` as the fix.

    **Copy, never link, never write the primary (Story 64.1).** ``sync``
    writes the index, so the base is copied file by file (sqlite's ``-wal`` /
    ``-shm`` sidecars travel with the db because the whole directory is
    enumerated) and only read. The build itself is ``build_codegraph_index``,
    the one builder ``marshal seed kit`` and ``marshal context bootstrap``
    share, run through the injected ``ProcessPort`` (AD-20).

    **Failure ladder.** A ``sync`` that fails for any reason but its ceiling
    falls back to ``init -y`` once (MRS-DISP-053, carrying the sync reason)
    after the copied index is cleared; a copied index that answers only for
    the primary's paths would fail exactly this way. A timeout on either verb
    ends in ``skipped`` with reason ``timeout`` and no fallback -- init's 900 s
    ceiling must not stack on a timed-out sync. Anything ``skipped`` after this
    run created the worktree's index leaves no index behind. The mode that
    finally applied is what is journaled.

    Measured 2026-09-29 (Story 77.1): an index copied from a sibling directory
    and synced answers with worktree files only -- its db holds no absolute
    path, and a symbol added in the worktree is found there and not in the
    base -- so a root-bound copy is unreachable and there is no runtime probe
    for it."""
    item = kit_item(KitItemId.CODEGRAPH_INDEX)
    if not layer_enabled(context_payload, item.layer):
        return StructureGraphSeed()

    started = time.monotonic()

    def _elapsed() -> float:
        return round(time.monotonic() - started, 2)

    def _unseeded(reason: str, cause: str, *, index_kept: bool = False) -> StructureGraphSeed:
        # A re-dispatched worktree's own index is left on disk when its sync
        # fails, and step 01 opens on it -- so the tail says that, not "no index".
        outcome = (
            "the worktree's existing codegraph index was left in place, unsynced (possibly stale)"
            if index_kept
            else "this dispatch session runs without a codegraph index"
        )
        return StructureGraphSeed(
            applied=False,
            mode=_STRUCTURE_GRAPH_MODE_SKIPPED,
            reason=reason,
            seconds=_elapsed(),
            findings=(
                Finding(
                    code="MRS-DISP-054",
                    severity=Severity.WARN,
                    message=f"the {item.layer!r} layer is enabled but {cause} -- {outcome}",
                ),
            ),
        )

    probe = probe_instrument(item)
    if not probe.available:
        why = probe.reason or f"{item.instrument} is not available"
        return _unseeded(why, why)

    index_rel = Path(item.relpath).parent
    base_dir = repo_root / index_rel
    worktree_dir = worktree / index_rel
    worktree_db = worktree / item.relpath
    base_db = repo_root / item.relpath

    # A re-dispatched worktree keeps its own index: sync it, never copy over
    # it, never delete it. Only an index this run creates is this run's to
    # clear when the run cannot finish it.
    already_indexed = fs.exists(worktree_db)
    owned_dir = None if already_indexed else worktree_dir

    def _fail(reason: str, cause: str) -> StructureGraphSeed:
        if owned_dir is not None:
            _discard_worktree_index(fs, owned_dir)
        return _unseeded(reason, cause, index_kept=owned_dir is None and fs.exists(worktree_db))

    stale = True  # `sync -q` refreshes an index; `init -y` creates one
    if not already_indexed and fs.exists(base_db):
        try:
            for source in _codegraph_files(base_dir):
                fs.copy_file(source, worktree_dir / source.relative_to(base_dir))
        except (OSError, PyforgeError) as exc:
            why = f"the base index at {base_dir} could not be copied into {worktree_dir}: {type(exc).__name__}: {exc}"
            return _fail(why, why)
    elif not already_indexed:
        stale = False

    sync_failure: str | None = None
    error = build_codegraph_index(worktree, stale=stale, process=process)
    if error is not None and "timed out" in error:
        return _fail("timeout", error)
    if error is not None and stale:
        if already_indexed:
            # `init -y` over an index this run did not create is the silent
            # no-op `_discard_worktree_index` describes, and the index is the
            # session's own: leave it and say the sync failed.
            why = f"the worktree's existing index could not be synced: {error}"
            return _fail(why, why)
        sync_failure = error
        stale = False
        _discard_worktree_index(fs, worktree_dir)
        error = build_codegraph_index(worktree, stale=False, process=process)
        if error is not None:
            error = f"{error} (after the copied base index failed to sync: {sync_failure})"
    if error is not None:
        return _fail("timeout" if "timed out" in error else error, error)
    if not fs.exists(worktree_db):
        why = f"`codegraph {'sync' if stale else 'init'}` exited 0 but {item.relpath} does not exist in {worktree}"
        return _fail(why, why)

    findings: list[Finding] = []
    reason: str | None = None
    if sync_failure is not None:
        reason = sync_failure
        findings.append(
            Finding(
                code="MRS-DISP-053",
                severity=Severity.WARN,
                message=(
                    f"the {item.layer!r} layer's copied base index could not be synced in {worktree} "
                    f"({sync_failure}) -- rebuilt it there with `codegraph init -y`; run "
                    f"`{_CONTEXT_BOOTSTRAP_COMMAND}` on the primary checkout if the base is stale or damaged"
                ),
            )
        )
    elif not stale:
        reason = f"no base index at {base_db}"
        findings.append(
            Finding(
                code="MRS-DISP-053",
                severity=Severity.WARN,
                message=(
                    f"the {item.layer!r} layer is enabled but the primary checkout has no base index at "
                    f"{base_db} -- built one in {worktree} with `codegraph init -y`; run "
                    f"`{_CONTEXT_BOOTSTRAP_COMMAND}` so later dispatches sync instead"
                ),
            )
        )
    return StructureGraphSeed(
        applied=True,
        mode=_STRUCTURE_GRAPH_MODE_SYNC if stale else _STRUCTURE_GRAPH_MODE_INIT,
        reason=reason,
        seconds=_elapsed(),
        findings=tuple(findings),
    )


def _resolve_origin_main_tip(vcs: VcsPort, repo_root: Path) -> str:
    """``origin/main``'s tip commit sha, by its full refname.

    ``VcsPort.resolve_ref`` reads ``refs/heads/<name>`` -- a LOCAL branch name only, so handing it
    ``ORIGIN_MAIN`` raises on real git (the trap ``cli/init.py`` documents at its own ``resolve_ref`` call, and
    that a fake which returns whatever it is told never shows). ``merge_base`` takes any revision, and a commit's
    merge base with itself is that commit."""
    return vcs.merge_base(repo_root, ORIGIN_MAIN, ORIGIN_MAIN)


def _deferred_work_ledger_rel(slug: str) -> str:
    """A station's tracked deferred-work ledger, repo-relative (where its ``DW-FRR`` rows live)."""
    return f"_bmad-output/projects/{slug}/planning-artifacts/deferred-work-ledger.md"


def _derive_followup_review(
    *, vcs: VcsPort, repo_root: Path, slug: str, story_key: StoryKey, spec_text: str
) -> FollowupReview | None:
    """Story 73.1 (spec-pyforge-marshal CAP-281): the follow-up review marker of a launch, or ``None``.

    A launch is a follow-up review run when the story's tracked spec (``spec_text``, the primary's) reads
    ``status: done`` with ``followup_review_recommended`` an explicit truthy -- the pairing Story 29.2 lets
    through to a fresh review. The marker is derived, never declared, from two ``origin/main`` reads made
    after the launch's own fetch (best effort, as ``dispatch land`` and the supervisor fetch it; a stale
    remote-tracking ref reads an older tip and ledger, never a newer one):

    * ``launch_origin_main_sha`` -- ``origin/main``'s resolved tip, the point after which a merge is this
      run's own (``core.dispatch_completion.merge_subject_ref``). Raises ``VcsCommandError`` when it cannot
      be resolved: a follow-up run with no launch tip could not be judged by its own branch.
    * ``dw_id`` -- the open ``DW-FRR-<story>`` row the station's deferred-work ledger holds AT
      ``origin/main``, not the primary's working copy, which lags a carry's publish until the next resync.
      ``None`` when it holds none or cannot be read -- the launch proceeds either way."""
    if not is_followup_review_spec(spec_text):
        return None
    try:
        vcs.fetch(repo_root, "origin", "main")
    except VcsCommandError:
        pass
    launch_tip = _resolve_origin_main_tip(vcs, repo_root)
    ledger_rel = _deferred_work_ledger_rel(slug)
    try:
        ledger_text = vcs.file_text_at_ref(repo_root, ORIGIN_MAIN, ledger_rel)
    except VcsCommandError:
        ledger_text = None
    dw_id = deferred_work.open_followup_review_id(ledger_text, story_key) if ledger_text is not None else None
    return FollowupReview(dw_id=dw_id, launch_origin_main_sha=launch_tip)


def _spec_text_prefer_worktree(spec_path: Path, repo_root: Path, worktree: Path, main_text: str) -> str:
    """Prefer the worktree copy: main often still says ready-for-dev."""
    try:
        worktree_spec = dispatch_core.relocated_spec_path(spec_path, repo_root, worktree)
    except ValueError:
        return main_text
    try:
        if worktree_spec.is_file():
            return worktree_spec.read_text(encoding="utf-8")
    except OSError:
        return main_text
    return main_text


def _verification_verdict_for_cap4(
    *,
    slug: str,
    story_key: StoryKey,
    worktree: Path,
    repo_root: Path,
    effective_policy: policy.EffectivePolicy,
    spec_text: str,
    process: ProcessPort,
    vcs: CommittingVcs,
) -> DispatchVerificationVerdict:
    """Independent verify only — never a harness self-report (CAP-3)."""
    if callable(getattr(vcs, "commit_paths", None)):
        run_dispatch_ruff_format_before_verify(
            worktree=worktree,
            repo_root=repo_root,
            vcs=vcs,  # CommittingVcs duck type
            process=process,
        )
    try:
        envelope = evaluate_dispatch_verification(
            project_slug=slug,
            story_key=story_key,
            worktree=worktree,
            repo_root=repo_root,
            effective=effective_policy,
            spec_text=spec_text,
            process=process,
            vcs=vcs,
            committing_vcs=vcs,
        )
    except ProcessError, VcsCommandError, OSError, TypeError, AttributeError:
        return DispatchVerificationVerdict.REFUSED
    return judge_dispatch_verification(DispatchVerificationInput(findings=tuple(envelope.findings)))


def _attempt_harness_done_cap4(
    *,
    slug: str,
    story_key: StoryKey,
    worktree: Path,
    repo_root: Path,
    effective_policy: policy.EffectivePolicy,
    spec_text: str,
    fs: FsPort,
    vcs: CommittingVcs,
    process: ProcessPort,
    followup_review: FollowupReview | None = None,
) -> tuple[DispatchLandingVerdict, str, object]:
    """Compose with the existing CAP-4 land path — never a second lander.

    ``followup_review`` (Story 73.1, CAP-281) is the marker of the story's latest run when that run was a
    follow-up review: the landing then judges ALREADY_LANDED by the run's own head and closes its row,
    exactly as the supervisor's landing does -- never by the story's first merge. ``None`` (a normal run)
    hands the landing nothing."""
    verification = _verification_verdict_for_cap4(
        slug=slug,
        story_key=story_key,
        worktree=worktree,
        repo_root=repo_root,
        effective_policy=effective_policy,
        spec_text=spec_text,
        process=process,
        vcs=vcs,
    )
    result, envelope = execute_dispatch_land(
        project_slug=slug,
        story_key=render_feed_key(story_key),
        worktree=worktree,
        repo_root=repo_root,
        verification_verdict=verification,
        effective=effective_policy,
        fs=fs,
        vcs=vcs,
        process=process,
        **_followup_review_kwargs(followup_review),
    )
    named = envelope.data.get("pr_url")
    if named is None and result.pr_number is not None:
        named = f"PR #{result.pr_number}"
    if named is None:
        named = str(worktree)
    return result.verdict, str(named), envelope


def _latest_story_run_dir(fs: FsPort, repo_root: Path, slug: str, story_key: str) -> Path | None:
    feed_story = render_feed_key(normalize(story_key))
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key == feed_story:
            return run_dir
    return None


def _latest_story_followup_review(fs: FsPort, repo_root: Path, slug: str, story_key: str) -> FollowupReview | None:
    """Story 73.1 (CAP-281): the follow-up review marker of the story's latest dispatch run, or ``None``.

    The CAP-4 land-only retry launches no session and so writes no launch INTENT of its own; the run it
    lands is the story's latest one, and the marker is the one that run's launch INTENT carries."""
    run_dir = _latest_story_run_dir(fs, repo_root, slug, story_key)
    if run_dir is None:
        return None
    return gather_dispatch_journal_facts(fs, run_dir, run_dir.name).followup_review


def _followup_review_kwargs(followup_review: FollowupReview | None) -> dict[str, FollowupReview]:
    """``{"followup_review": marker}`` for a follow-up review run, ``{}`` otherwise -- so a normal run's
    call to a landing or CAP-4 seam carries no new keyword at all (Story 73.1, CAP-281)."""
    return {"followup_review": followup_review} if followup_review is not None else {}


def _redispatch_blocked_pending_supervisor_finalize(
    *,
    fs: FsPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
) -> str | None:
    """Story 28.24: refuse redispatch over MRS-DISP-036 dirt until finalize."""
    run_dir = _latest_story_run_dir(fs, repo_root, slug, story_key)
    if run_dir is None:
        return None
    journal_path = run_dir / _JOURNAL_FILENAME
    text = fs.read_text(journal_path)
    if text is None:
        return None
    folded = fold(text.splitlines())
    if finalize_attempt_journaled(folded, run_dir.name):
        return None
    journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
    if journal.worktree_path is not None and Path(journal.worktree_path) != worktree:
        return None
    if journal.completion_verdict == DispatchSessionVerdict.COMPLETED.value:
        return None
    return (
        f"worktree {worktree!r} carries uncommitted changes from run "
        f"{run_dir.name!r}; supervisor finalize (commit/push/verify) has "
        "not been attempted yet — redispatch blocked (Story 28.24)"
    )


def gather_fleet_finalize_escalations(
    *,
    fs: FsPort,
    repo_root: Path,
) -> dict[str, dispatch_fleet.FinalizeEscalation]:
    """Active supervisor-finalize shell failures (Story 28.24, CAP-7).

    Examines only the newest dispatch run per station (Story 28.25) -- an
    older failed finalize that a later run has since superseded is not an
    active escalation, so the search does not walk past it. A failure whose
    worktree has since been removed (e.g. a manual push+PR recovery) is
    likewise treated as resolved rather than reported forever.
    """
    escalations: dict[str, dispatch_fleet.FinalizeEscalation] = {}
    for slug in dispatch_core.list_station_slugs(repo_root):
        feed_slug = dispatch_fleet.normalize_station_slug(slug)
        run_dir = latest_dispatch_run_dir(repo_root, slug)
        if run_dir is None:
            continue
        journal_path = run_dir / _JOURNAL_FILENAME
        text = fs.read_text(journal_path)
        if text is None:
            continue
        folded = fold(text.splitlines())
        if not finalize_attempt_failed(folded, run_dir.name):
            continue
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key is None:
            continue
        worktree = finalize_failure_worktree_path(folded, run_dir.name)
        if worktree is None:
            worktree = journal.worktree_path
        if worktree is None:
            continue
        if not Path(worktree).is_dir():
            continue
        escalations[feed_slug] = dispatch_fleet.FinalizeEscalation(
            story=journal.story_key,
            worktree_path=worktree,
        )
    return escalations


def _last_failed_dispatch_session_log(fs: FsPort, repo_root: Path, slug: str, story_key: str) -> str | None:
    feed_story = render_feed_key(normalize(story_key))
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key != feed_story:
            continue
        if journal.completion_verdict != DispatchSessionVerdict.FAILED.value:
            return None
        return fs.read_text(run_dir / _LOG_FILENAME)
    return None


def _count_prior_failed_dispatch_attempts(fs: FsPort, repo_root: Path, slug: str, story_key: str) -> int:
    """Count failed dispatch runs for this story since the last completion.

    Story 33.6 (CAP-2): mirrors spin's per-run struggle counter — a
    successful completion resets the streak so an old failure history does
    not floor-raise an unrelated later retry.
    """
    feed_story = render_feed_key(normalize(story_key))
    count = 0
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key != feed_story:
            continue
        if journal.completion_verdict == DispatchSessionVerdict.COMPLETED.value:
            break
        if journal.completion_verdict == DispatchSessionVerdict.FAILED.value:
            # Story 83.10: verification refusals are not session failures for
            # Story 33.6's floor-raise counter.
            if is_dispatch_verification_refusal(
                completion_verdict=journal.completion_verdict,
                verification_verdict=journal.verification_verdict,
                verification_failed_gate=journal.verification_failed_gate,
            ):
                continue
            count += 1
    return count


@dataclass(frozen=True)
class DispatchWorktreeResolution:
    """A provisioned dispatch worktree, or the refusal that stopped it (22.9)."""

    branch: str
    worktree: Path | None = None
    legacy: bool = False
    refusal: str | None = None


def _ensure_dispatch_worktree(vcs: VcsPort, repo_root: Path, slug: str, story_key: str) -> DispatchWorktreeResolution:
    """Provision (or reuse) this station's dispatch worktree.

    Story 22.9: the branch carries the station, so two stations sharing a
    story key can no longer resolve each other's tree. A pre-22.9
    ``marshal/<key>`` branch is still reused when git shows it checked out
    at THIS station's dispatch worktree; otherwise it refuses loudly with
    the land-first remedy rather than attaching to a tree it cannot
    attribute.
    """
    # Derive the attribution path ONCE and hand it to the resolver, rather
    # than letting the resolver compute its own default and recomputing the
    # same thing here -- the other two callers already pass `worktree=`
    # explicitly, and a single basis cannot drift from itself.
    worktree = dispatch_core.dispatch_worktree_path(repo_root, slug, story_key)
    resolution = dispatch_core.resolve_dispatch_branch(
        vcs, repo_root, slug=slug, story_key=story_key, worktree=worktree
    )
    if resolution.refusal is not None:
        return DispatchWorktreeResolution(branch=resolution.branch, refusal=resolution.refusal)
    branch = resolution.effective_branch
    existing = vcs.worktree_path_for_branch(repo_root, branch)
    if existing is not None:
        return DispatchWorktreeResolution(branch=branch, worktree=existing, legacy=resolution.legacy)
    if worktree.exists():
        return DispatchWorktreeResolution(branch=branch, worktree=worktree, legacy=resolution.legacy)
    vcs.add_worktree(repo_root, worktree, branch, base=_BASE_REF)
    return DispatchWorktreeResolution(branch=branch, worktree=worktree, legacy=resolution.legacy)


#: Parallel-wave journals live under ``dispatch-runs/waves/<wave-id>/``
#: (Story 28.16). That container must never be treated as a per-story run
#: dir: sorted-by-name, ``waves`` sorts after every ``<slug>-<ts>-<hex>``
#: run id, so ``latest_dispatch_run_dir`` would otherwise return the empty
#: container and ``marshal status`` / ``fleet-picture`` go blind to a live
#: headroom/claude session (found 2026-09-18 on pyforge-marshal 46.4).
_DISPATCH_WAVES_DIRNAME = "waves"


def iter_dispatch_run_dirs(repo_root: Path, slug: str) -> tuple[Path, ...]:
    runs_parent = dispatch_core.dispatch_runs_dir(repo_root, slug)
    if not runs_parent.is_dir():
        return ()
    return tuple(
        sorted(
            (
                p
                for p in runs_parent.iterdir()
                if p.is_dir() and p.name != _DISPATCH_WAVES_DIRNAME and (p / _JOURNAL_FILENAME).is_file()
            ),
            key=lambda p: p.name,
        )
    )


def latest_dispatch_run_dir(repo_root: Path, slug: str) -> Path | None:
    dirs = iter_dispatch_run_dirs(repo_root, slug)
    if not dirs:
        return None
    return dirs[-1]


def gather_dispatch_journal_facts(fs: FsPort, run_dir: Path, run_id: str) -> dispatch_core.DispatchJournalFacts:
    journal_path = run_dir / _JOURNAL_FILENAME
    text = fs.read_text(journal_path)
    if text is None:
        return dispatch_core.DispatchJournalFacts(
            story_key=None,
            session_pid=None,
            model=None,
            launched_at=None,
            worktree_path=None,
        )
    lines = text.splitlines()
    sidecars = sidecar_texts_for_lines(
        lines,
        read_sidecar=lambda ref: fs.read_text(run_dir / ref),
    )
    folded = fold(lines, sidecars=sidecars)
    story_key: str | None = None
    session_pid: int | None = None
    model: str | None = None
    worktree_path: str | None = None
    launched_at: datetime | None = None
    baseline_head_sha: str | None = None
    followup_review: FollowupReview | None = None
    supervisor_pid: int | None = None
    completion_verdict: str | None = None
    completion_stop_reason: str | None = None
    verification_verdict: str | None = None
    verification_failed_gate: str | None = None
    verification_scope_advisories: tuple[dict[str, object], ...] = ()
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH):
        if entry.phase == Phase.INTENT:
            # Story 73.1 (CAP-281): the follow-up review marker rides the launch INTENT, read back here for
            # every reader of this run's merge facts.
            followup_review = FollowupReview.from_intent_payload(entry.payload)
            raw_story = entry.payload.get("story_key")
            story_key = raw_story if isinstance(raw_story, str) else None
            model_val = entry.payload.get("model")
            model = model_val if isinstance(model_val, str) else None
            wt = entry.payload.get("worktree_path")
            worktree_path = wt if isinstance(wt, str) else None
            baseline_val = entry.payload.get("baseline_head_sha")
            baseline_head_sha = baseline_val if isinstance(baseline_val, str) else None
            try:
                launched_at = datetime.fromisoformat(entry.ts.replace("Z", "+00:00"))
            except ValueError:
                launched_at = None
        elif entry.phase == Phase.OUTCOME:
            pid_val = entry.payload.get("session_pid")
            if isinstance(pid_val, int):
                session_pid = pid_val
            elif isinstance(pid_val, str) and pid_val.isdigit():
                session_pid = int(pid_val)
            sup_val = entry.payload.get("supervisor_pid")
            if isinstance(sup_val, int):
                supervisor_pid = sup_val
            elif isinstance(sup_val, str) and sup_val.isdigit():
                supervisor_pid = int(sup_val)
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_COMPLETION):
        if entry.phase == Phase.OUTCOME:
            verdict_val = entry.payload.get("verdict")
            if isinstance(verdict_val, str):
                completion_verdict = verdict_val
            stop_val = entry.payload.get("stop_reason")
            if isinstance(stop_val, str):
                completion_stop_reason = stop_val
    landing_verdict: str | None = None
    landing_findings: tuple[dict[str, object], ...] = ()
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAND):
        if entry.phase == Phase.OUTCOME:
            verdict_val = entry.payload.get("verdict")
            if isinstance(verdict_val, str):
                # Story 83.7: refused outcomes carry ``ok: false`` but still
                # record ``verdict: refused`` for the land-only re-dispatch gate.
                if entry.payload.get("ok") or verdict_val == DispatchLandingVerdict.REFUSED.value:
                    landing_verdict = verdict_val
            # Story 53.2 review (I1): read regardless of `ok` -- a refused
            # landing (MRS-DISP-048) is exactly the case this must surface.
            landing_findings = resolve_land_findings_from_payload(entry.payload, sidecars=sidecars)
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFICATION):
        if entry.phase == Phase.OUTCOME:
            vval = entry.payload.get("verdict")
            if isinstance(vval, str):
                verification_verdict = vval
            gate_val = entry.payload.get("failed_gate")
            if isinstance(gate_val, str):
                verification_failed_gate = gate_val
            # Story 28.15 (CAP-17): best-effort, matching every other
            # journal-payload read in this function -- a malformed/missing
            # entry degrades to the empty tuple rather than raising, never
            # a fabricated advisory.
            verification_scope_advisories = resolve_scope_violation_advisories_from_payload(
                entry.payload, sidecars=sidecars
            )
    story_started_at: str | None = None
    story_ended_at: str | None = None
    baseline_revision: str | None = None
    final_revision: str | None = None
    preserve_ref: str | None = None
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_TIMING):
        if entry.phase == Phase.OUTCOME:
            raw_started = entry.payload.get("story_started_at")
            if isinstance(raw_started, str):
                story_started_at = raw_started
            raw_ended = entry.payload.get("story_ended_at")
            if isinstance(raw_ended, str):
                story_ended_at = raw_ended
            raw_baseline = entry.payload.get("baseline_revision")
            if isinstance(raw_baseline, str):
                baseline_revision = raw_baseline
            raw_final = entry.payload.get("final_revision")
            if isinstance(raw_final, str):
                final_revision = raw_final
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_PRESERVE):
        if entry.phase == Phase.OUTCOME:
            raw_ref = entry.payload.get("preserve_ref")
            if isinstance(raw_ref, str):
                preserve_ref = raw_ref
    if baseline_revision is None and baseline_head_sha is not None:
        baseline_revision = baseline_head_sha
    if story_started_at is None and launched_at is not None:
        story_started_at = _format_entry_ts(launched_at)
    return dispatch_core.DispatchJournalFacts(
        story_key=story_key,
        session_pid=session_pid,
        model=model,
        launched_at=launched_at,
        worktree_path=worktree_path,
        baseline_head_sha=baseline_head_sha,
        followup_review=followup_review,
        supervisor_pid=supervisor_pid,
        completion_verdict=completion_verdict,
        completion_stop_reason=completion_stop_reason,
        verification_verdict=verification_verdict,
        verification_failed_gate=verification_failed_gate,
        verification_scope_advisories=verification_scope_advisories,
        landing_verdict=landing_verdict,
        landing_findings=landing_findings,
        story_started_at=story_started_at,
        story_ended_at=story_ended_at,
        baseline_revision=baseline_revision,
        final_revision=final_revision,
        preserve_ref=preserve_ref,
    )


def _is_dispatch_session_alive(
    process: ProcessPort,
    journal: dispatch_core.DispatchJournalFacts,
) -> bool:
    """Check if a dispatch session is genuinely alive, not just a reused PID.

    Returns True only if:
    1. The journal has a session PID
    2. That PID is alive according to ProcessPort.is_alive (which now checks it's a process, not thread)
    3. The process start time is consistent with the journal launch time (within tolerance)

    Story 83.1: Fix the defect where a reused PID or thread ID can hold a wave
    on a story that finished weeks ago.
    """
    if journal.session_pid is None:
        return False

    if not process.is_alive(journal.session_pid):
        return False

    # Additional verification: check process start time matches launch time within tolerance
    if journal.launched_at is not None:
        process_start_time = process.process_start_time(journal.session_pid)
        if process_start_time is not None:
            # Convert journal launch time to timestamp
            journal_timestamp = journal.launched_at.timestamp()

            # Allow up to 30 seconds tolerance for the process to start after the journal entry
            # This accounts for the time between journaling the launch and the process actually starting
            tolerance_seconds = 30.0
            time_diff = process_start_time - journal_timestamp

            # Process should have started within tolerance after the journal launch time
            # But not significantly before it (which would indicate PID reuse)
            if time_diff < -tolerance_seconds or time_diff > tolerance_seconds:
                return False
    return True


def resolve_dispatch_session_verdict(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    journal: dispatch_core.DispatchJournalFacts,
    effective_policy: policy.EffectivePolicy,
    run_dir: Path | None = None,
    spec_relative_path: str | None = None,
) -> DispatchSessionVerdict | None:
    if journal.completion_verdict in {
        DispatchSessionVerdict.COMPLETED.value,
        DispatchSessionVerdict.FAILED.value,
        DispatchSessionVerdict.STOPPED_EXTERNALLY.value,
        # Story 51.11 (CAP-258): an already-committed `blocked` verdict must
        # not be re-derived from fresh git facts, which would re-introduce
        # the exact bug this story fixes (stale facts read STOPPED_EXTERNALLY).
        DispatchSessionVerdict.BLOCKED.value,
    }:
        return DispatchSessionVerdict(journal.completion_verdict)
    from ..core.dispatch_supervisor_state import landing_journal_indicates_complete

    if landing_journal_indicates_complete(journal.landing_verdict):
        return DispatchSessionVerdict.COMPLETED
    if journal.story_key is None or journal.worktree_path is None:
        return None
    session_alive = _is_dispatch_session_alive(process, journal)
    if journal.baseline_head_sha is None:
        return DispatchSessionVerdict.LIVE if session_alive else None
    try:
        git_facts = gather_dispatch_git_facts(
            vcs,
            fs=fs,
            repo_root=repo_root,
            worktree=Path(journal.worktree_path),
            story_key=journal.story_key,
            project_slug=slug,
            baseline_head_sha=journal.baseline_head_sha,
            merge_subject_template=effective_policy.merge_subject_template.value,
            # Story 73.1 (CAP-281): a follow-up review run is judged by its own branch, never by the
            # story's first merge -- the marker comes off the run's own launch INTENT.
            followup_review=journal.followup_review,
        )
    except VcsCommandError, ValueError:
        return DispatchSessionVerdict.LIVE if session_alive else None
    session_log: str | None = None
    if run_dir is not None:
        session_log = fs.read_text(run_dir / _LOG_FILENAME)
    return resolve_terminal_session_verdict(
        session_alive=session_alive,
        git=git_facts,
        verification_verdict=journal.verification_verdict,
        detach_reason=journal.completion_stop_reason,
        session_log=session_log,
        spec_relative_path=narration_spec_path(spec_relative_path, followup_review=journal.followup_review),
    )


def _live_dispatch_evidence(
    *,
    journal: dispatch_core.DispatchJournalFacts,
    verdict: DispatchSessionVerdict,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    effective_policy: policy.EffectivePolicy,
    harness_reported_failure: bool = False,
) -> str:
    story_key = journal.story_key or "unknown"
    if journal.baseline_head_sha is None or journal.worktree_path is None:
        return (
            zombie_redispatch_evidence(
                story_key=story_key,
                verdict=verdict,
                git=DispatchGitFacts(
                    baseline_head_sha="",
                    current_head_sha="",
                    changed_paths=(),
                    branch_merged=False,
                    story_merged_on_main=False,
                ),
                session_alive=_is_dispatch_session_alive(process, journal),
                harness_reported_failure=harness_reported_failure,
            )
            or f"story {story_key!r} dispatch session is still live"
        )
    git_facts = gather_dispatch_git_facts(
        vcs,
        fs=fs,
        repo_root=repo_root,
        worktree=Path(journal.worktree_path),
        story_key=journal.story_key,
        project_slug=slug,
        baseline_head_sha=journal.baseline_head_sha,
        merge_subject_template=effective_policy.merge_subject_template.value,
        followup_review=journal.followup_review,
    )
    return (
        zombie_redispatch_evidence(
            story_key=story_key,
            verdict=verdict,
            git=git_facts,
            session_alive=_is_dispatch_session_alive(process, journal),
            harness_reported_failure=harness_reported_failure,
        )
        or f"story {story_key!r} dispatch session is still live"
    )


def _epics_path(repo_root: Path, slug: str) -> Path:
    return (
        dispatch_core.canonical_repo_root(repo_root)
        / "_bmad-output"
        / "projects"
        / slug
        / "planning-artifacts"
        / "epics.md"
    )


def _load_station_deps_graph(repo_root: Path, slug: str) -> dict[str, tuple]:
    path = _epics_path(repo_root, slug)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    return story_deps_from_epics(text)


def _effective_surface_for_spec(
    *,
    spec_text: str,
    story_key: StoryKey,
    slug: str,
    effective_policy: policy.EffectivePolicy,
) -> tuple[str, ...] | None:
    """Effective frozen surface for wave/conflict checks (AD-27).

    Returns ``None`` when the spec's surface declaration is unsupported
    (multi-line YAML block) -- conservative: never fan out unknown surfaces.
    """
    try:
        spec_surface = parse_declared_surface(spec_text)
    except SurfaceParseError:
        return None
    policy_surface = gate.resolve_policy_surface(effective_policy.epic_surfaces.value, story_key.epic, slug)
    return gate.compute_effective_surface(policy_surface, spec_surface)


def resolve_max_parallel(
    effective_policy: policy.EffectivePolicy,
    *,
    cli_override: int | None = None,
    policy_flags: dict[str, object] | None = None,
) -> int:
    """Factory-dispatch parallel cap (Story 28.16, CAP-4; Story 33.8, CAP-6).

    Reads ``dispatch.max_parallel`` only -- never bmad-loop scm
    ``max_parallel`` (SEED). Default serial (=1)."""
    del policy_flags  # compose() already merged flags into ``effective_policy``.
    if cli_override is not None:
        return max(1, int(cli_override))
    dispatch_block = effective_policy.dispatch.value
    if not isinstance(dispatch_block, Mapping):
        return 1
    raw = dispatch_block.get("max_parallel", 1)
    validated = policy._valid_parallel_count(raw)
    return max(1, int(validated if validated is not None else 1))


def _live_dispatch_story_keys(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    effective_policy: policy.EffectivePolicy,
) -> tuple[str, ...]:
    """Every LIVE factory-dispatch story key on ``slug`` (Story 28.16)."""
    live: list[str] = []
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key is None:
            continue
        verdict = resolve_dispatch_session_verdict(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            journal=journal,
            effective_policy=effective_policy,
            run_dir=run_dir,
        )
        if verdict == DispatchSessionVerdict.LIVE:
            live.append(journal.story_key)
    return tuple(live)


def station_finalize_pending_story(
    *,
    fs: FsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    backlog: Sequence[str],
    effective_policy: policy.EffectivePolicy,
) -> tuple[str, str] | None:
    """``(story, evidence)`` when this station's head is mid-finalize (50.1).

    Part A's impure half: walk the MOST RECENT dispatch run, read the four
    facts the journal already carries (``story_key``, ``supervisor_pid``,
    ``completion_verdict``, ``landing_verdict``), and hand them plus the
    tracked-ledger fact to the pure ``is_finalize_pending``.

    This is deliberately NOT a second completion judgment:
    ``resolve_dispatch_session_verdict`` / ``judge_dispatch_completion``
    are untouched, and nothing here reads the session's own self-report.
    ``spin``'s in-flight probe has treated a live ``supervisor_pid`` as in
    flight since Story 34.1; the dispatch path simply never learned it.
    """
    # The verdict stays on journal + process facts (Epic 50 HARD boundary);
    # the policy is accepted for call-site symmetry with every other
    # station-level probe, never consulted.
    del effective_policy
    from ..core.dispatch_supervisor_state import landing_journal_indicates_complete

    run_dir = latest_dispatch_run_dir(repo_root, slug)
    if run_dir is None:
        return None
    journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
    if journal.story_key is None:
        return None
    on_backlog: str | None = None
    for raw in backlog:
        try:
            if render_feed_key(normalize(raw)) == journal.story_key:
                on_backlog = raw
                break
        except MalformedStoryKeyError:
            continue
    supervisor_alive = journal.supervisor_pid is not None and process.is_alive(journal.supervisor_pid)
    landing_complete = landing_journal_indicates_complete(journal.landing_verdict)
    session_alive = _is_dispatch_session_alive(process, journal)
    if session_alive and not landing_complete:
        # A session still running is plain in-flight, not finalize-pending:
        # CAP-2's own verdict already reads LIVE and the MRS-DISP-011 relay
        # reports it. Clause (a) is about the window AFTER the session exits,
        # so it must never pre-empt that already-correct path.
        return None
    if not dispatch_fleet.is_finalize_pending(
        supervisor_alive=supervisor_alive,
        completion_journaled=journal.completion_verdict is not None,
        landing_complete=landing_complete,
        story_on_backlog=on_backlog is not None,
    ):
        return None
    assert on_backlog is not None
    if landing_complete:
        evidence = (
            f"run {run_dir.name!r} journaled dispatch-land "
            f"{journal.landing_verdict!r} and the tracked ledger still says "
            "backlog -- finalize (ledger sync + spec promotion) is mid-flight"
        )
    else:
        evidence = (
            f"run {run_dir.name!r} has a live supervisor "
            f"(pid {journal.supervisor_pid}) and no dispatch-completion "
            "entry -- the landing path has not finished"
        )
    return on_backlog, evidence


def _dispatch_git_facts_for_journal(
    *,
    vcs: VcsPort,
    fs: FsPort,
    repo_root: Path,
    slug: str,
    journal: dispatch_core.DispatchJournalFacts,
    effective_policy: policy.EffectivePolicy,
) -> DispatchGitFacts | None:
    if journal.baseline_head_sha is None or journal.worktree_path is None:
        return None
    try:
        return gather_dispatch_git_facts(
            vcs,
            fs=fs,
            repo_root=repo_root,
            worktree=Path(journal.worktree_path),
            story_key=journal.story_key,
            project_slug=slug,
            baseline_head_sha=journal.baseline_head_sha,
            merge_subject_template=effective_policy.merge_subject_template.value,
            followup_review=journal.followup_review,
        )
    except VcsCommandError, ValueError:
        return None


def _refused_landing_open_pr(
    journal: dispatch_core.DispatchJournalFacts,
    git_facts: DispatchGitFacts | None,
) -> bool:
    """Story 83.4: landing refused with an unmerged branch (open PR)."""
    if journal.landing_verdict != "refused":
        return False
    if git_facts is None:
        return False
    return not git_facts.branch_merged and not git_facts.story_merged_on_main


def _refused_landing_open_pr_story_keys(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    effective_policy: policy.EffectivePolicy,
) -> frozenset[str]:
    keys: set[str] = set()
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key is None:
            continue
        verdict = resolve_dispatch_session_verdict(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            journal=journal,
            effective_policy=effective_policy,
            run_dir=run_dir,
        )
        if verdict == DispatchSessionVerdict.LIVE:
            continue
        git_facts = _dispatch_git_facts_for_journal(
            vcs=vcs,
            fs=fs,
            repo_root=repo_root,
            slug=slug,
            journal=journal,
            effective_policy=effective_policy,
        )
        if _refused_landing_open_pr(journal, git_facts):
            keys.add(journal.story_key)
    return frozenset(keys)


def station_in_flight_conflict(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    effective_policy: policy.EffectivePolicy,
    harness_reported_failure: bool = False,
    candidate_spec_text: str | None = None,
    deps_graph: Mapping[str, tuple] | None = None,
    parallel_dispatch: bool = False,
) -> DispatchPreflightConflict | None:
    """Refuse when an in-flight story blocks this candidate (22.5 / 28.16).

    Story 28.16 narrows the 22.5 guard when ``parallel_dispatch`` is true:
    unrelated LIVE stories with disjoint surfaces do NOT refuse. With
    ``parallel_dispatch`` false (``max_parallel`` unset or ``1``), behavior
    stays byte-identical to today's serial drain (``MRS-DISP-021`` on any
    other LIVE story).
    """
    feed_story = render_feed_key(normalize(story_key))
    candidate_surface: tuple[str, ...] | None = None
    if candidate_spec_text is not None:
        try:
            candidate_surface = _effective_surface_for_spec(
                spec_text=candidate_spec_text,
                story_key=normalize(story_key),
                slug=slug,
                effective_policy=effective_policy,
            )
        except ValueError:
            candidate_surface = None
    graph = dict(deps_graph or {})
    refused_landing_open = _refused_landing_open_pr_story_keys(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        effective_policy=effective_policy,
    )
    candidate_refused_landing_open = feed_story in refused_landing_open
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key is None:
            continue
        verdict = resolve_dispatch_session_verdict(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            journal=journal,
            effective_policy=effective_policy,
            run_dir=run_dir,
        )
        git_facts = _dispatch_git_facts_for_journal(
            vcs=vcs,
            fs=fs,
            repo_root=repo_root,
            slug=slug,
            journal=journal,
            effective_policy=effective_policy,
        )
        is_live = verdict == DispatchSessionVerdict.LIVE
        is_refused_landing_open = not is_live and _refused_landing_open_pr(journal, git_facts)
        if not is_live and not is_refused_landing_open:
            continue
        if is_live:
            evidence = _live_dispatch_evidence(
                journal=journal,
                verdict=verdict,
                fs=fs,
                vcs=vcs,
                process=process,
                repo_root=repo_root,
                slug=slug,
                effective_policy=effective_policy,
                harness_reported_failure=harness_reported_failure,
            )
        else:
            blocked_story_key = journal.story_key or "unknown"
            evidence = f"story {blocked_story_key!r} finished but was refused at landing with open PR"
        in_flight = journal.story_key
        if in_flight == feed_story:
            # CAP-2: only a LIVE session refuses redispatch of the same story.
            # Story 83.4: refused+open-PR occupies surfaces for *other* stories;
            # the operator re-dispatches the refused story to land fixes.
            if is_live:
                return DispatchPreflightConflict(
                    code="MRS-DISP-011",
                    message=f"refusing redispatch: {evidence}",
                    in_flight_story_key=in_flight,
                )
            continue
        if is_refused_landing_open and candidate_refused_landing_open:
            # Story 83.4: refused stories never hold each other (only LIVE holds refused).
            continue
        if not parallel_dispatch and is_live:
            return DispatchPreflightConflict(
                code="MRS-DISP-021",
                message=(f"refusing dispatch: station {slug!r} already has in-flight story {in_flight!r} ({evidence})"),
                in_flight_story_key=in_flight,
            )
        if story_transitively_depends_on(feed_story, in_flight, graph):
            return DispatchPreflightConflict(
                code="MRS-DISP-035",
                message=(
                    f"refusing dispatch: story {feed_story!r} depends on in-flight story {in_flight!r} ({evidence})"
                ),
                in_flight_story_key=in_flight,
            )
        if candidate_surface is not None:
            in_flight_spec = dispatch_core.resolve_story_spec_path(repo_root, slug, in_flight)
            if in_flight_spec is not None:
                try:
                    in_flight_text = in_flight_spec.read_text(encoding="utf-8")
                except OSError:
                    in_flight_text = None
                if in_flight_text is not None:
                    in_flight_surface = _effective_surface_for_spec(
                        spec_text=in_flight_text,
                        story_key=normalize(in_flight),
                        slug=slug,
                        effective_policy=effective_policy,
                    )
                    overlapping = dispatch_core.find_declared_surface_overlaps(candidate_surface, in_flight_surface)
                    if overlapping:
                        pair_desc = ", ".join(f"{left!r} ∩ {right!r}" for left, right in overlapping)
                        paths = tuple(f"{left} ∩ {right}" for left, right in overlapping)
                        return DispatchPreflightConflict(
                            code="MRS-DISP-034",
                            message=(
                                f"refusing dispatch: effective surfaces of "
                                f"{feed_story!r} and in-flight {in_flight!r} "
                                f"intersect ({pair_desc}); {evidence}"
                            ),
                            in_flight_story_key=in_flight,
                            overlap_paths=paths,
                        )
    return None


def _iter_spin_run_dirs(home: Path, slug: str) -> tuple[Path, ...]:
    """Marshal spin run directories under a loop home (Story 34.1).

    Mirrors ``cli/spin.py::_latest_run_dir``'s own glob location and sort
    order, but returns every matching directory so a guard can walk newest-
    first rather than inspecting only the lexicographically latest id.
    """
    runs_dir = home / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs"
    try:
        return tuple(
            sorted(
                (path for path in runs_dir.glob(f"{slug}-*") if path.is_dir()),
                key=lambda path: path.name,
            )
        )
    except OSError:
        return ()


def spin_loop_home_in_flight_conflict(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    harness: HarnessPort,
    home: Path,
    slug: str,
    story_key: str,
    effective_policy: policy.EffectivePolicy,
) -> DispatchPreflightConflict | None:
    """Refuse ``factory spin`` when this loop home already has a live run (34.1).

    A narrowed call into ``station_in_flight_conflict`` for live factory-
    dispatch sessions on the SAME home, then the spin-specific ``runs/``
    journals dispatch's guard does not walk. Reuses ``DispatchPreflightConflict``
    and ``MRS-DISP-021`` -- never a second, independently-drifting guard.
    """
    dispatch_conflict = station_in_flight_conflict(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=home,
        slug=slug,
        story_key=story_key,
        effective_policy=effective_policy,
        parallel_dispatch=False,
    )
    if dispatch_conflict is not None:
        return dispatch_conflict

    from .status import _gather_run_journal_facts

    for run_dir in reversed(_iter_spin_run_dirs(home, slug)):
        run_id = run_dir.name
        journal_facts = _gather_run_journal_facts(fs, run_dir, run_id)
        launch_pid = journal_facts.launch_pid
        supervisor_pid = journal_facts.supervisor_pid
        launch_alive = launch_pid is not None and process.is_alive(launch_pid)
        supervisor_alive = supervisor_pid is not None and process.is_alive(supervisor_pid)
        if not launch_alive and not supervisor_alive:
            continue
        harness_run_id = journal_facts.harness_run_id
        snapshot = harness.run_status_snapshot(home, harness_run_id) if harness_run_id else None
        if snapshot is not None and snapshot.finished:
            continue
        evidence_parts = [f"run {run_id!r}"]
        if launch_pid is not None:
            evidence_parts.append(f"pid {launch_pid}")
        if supervisor_pid is not None:
            evidence_parts.append(f"supervisor pid {supervisor_pid}")
        evidence = ", ".join(evidence_parts)
        return DispatchPreflightConflict(
            code="MRS-DISP-021",
            message=(f"refusing spin: station {slug!r} already has in-flight spin ({evidence})"),
            in_flight_story_key=run_id,
        )
    return None


def cross_station_surface_overlap_advisories(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    requested_slug: str,
    requested_story_key: str,
    requested_spec_text: str,
) -> tuple[Finding, ...]:
    """Loud WARN advisories for overlapping declared surfaces (Story 22.5)."""
    requested_surface = parse_declared_surface(requested_spec_text)
    feed_requested = render_feed_key(normalize(requested_story_key))
    advisories: list[Finding] = []
    for station_slug in dispatch_core.list_station_slugs(repo_root):
        station_policy = _compose_policy(station_slug)
        for run_dir in reversed(iter_dispatch_run_dirs(repo_root, station_slug)):
            journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
            if journal.story_key is None:
                continue
            if station_slug == requested_slug and journal.story_key == feed_requested:
                continue
            verdict = resolve_dispatch_session_verdict(
                fs=fs,
                vcs=vcs,
                process=process,
                repo_root=repo_root,
                slug=station_slug,
                journal=journal,
                effective_policy=station_policy,
                run_dir=run_dir,
            )
            if verdict != DispatchSessionVerdict.LIVE:
                continue
            in_flight_spec = dispatch_core.resolve_story_spec_path(repo_root, station_slug, journal.story_key)
            if in_flight_spec is None:
                continue
            try:
                in_flight_text = in_flight_spec.read_text(encoding="utf-8")
            except OSError:
                continue
            in_flight_surface = parse_declared_surface(in_flight_text)
            overlapping = dispatch_core.find_declared_surface_overlaps(requested_surface, in_flight_surface)
            if not overlapping:
                continue
            advisories.append(
                Finding(
                    code="MRS-DISP-022",
                    severity=Severity.WARN,
                    message=dispatch_core.format_surface_overlap_advisory(
                        in_flight_station=station_slug,
                        in_flight_story_key=journal.story_key,
                        requested_station=requested_slug,
                        requested_story_key=feed_requested,
                        overlapping=overlapping,
                    ),
                )
            )
            break
    return tuple(advisories)


def station_story_block_facts(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    effective_policy: policy.EffectivePolicy,
    followup_entry: bool = False,
) -> dispatch_fleet.StationBlockEvidence | None:
    """Evidence + environment/story classification for a blocked story (34.3).

    Story 22.7: the fleet driver needs to know "is this station's next story
    blocked?" without inventing a second completion judgment. It reuses
    CAP-2's own verdict resolution verbatim -- only the MOST RECENT run for
    that story counts, so a story that failed once and was later re-driven to
    ``live``/``completed`` is not treated as blocked forever.

    ``followup_entry`` (Story 73.2, CAP-281): the queue entry is a follow-up review of an already-landed story,
    judged by its open ``DW-FRR`` row and never by the story's first landing -- so Part B's already-landed
    advance below does not apply to it. Only the follow-up's OWN runs judge it: a run whose launch journal
    carries no follow-up review marker is the story's first life (a failed implementation that later landed
    another way), and reading it as the follow-up's failure would block the entry on every cycle and campaign.
    A follow-up run that failed is a block like any story's.
    """
    feed_story = render_feed_key(normalize(story_key))
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key != feed_story:
            continue
        if followup_entry and journal.followup_review is None:
            continue

        # Story 51.4 (CAP-252): resolve the worktree's own tracked spec once
        # per run, before verdict resolution -- a deliberate `status: blocked`
        # (the 27.3 incident) or a diff that collapses to just that spec file
        # (narration, not work -- the 51.3 incident) must both read as
        # no-progress to `resolve_dispatch_session_verdict` itself, not only
        # to the block-reason checks below it (2026-09-19 review pass: the
        # original placement inside the `verdict == FAILED` branch meant
        # `resolve_dispatch_session_verdict`'s own `has_git_progress` call
        # never saw a narration-only diff as no-progress, so the campaign
        # could resolve LIVE/STOPPED_EXTERNALLY instead of FAILED for it).
        spec_status: str | None = None
        spec_blocking_condition: str | None = None
        spec_relative_path: str | None = None
        if journal.worktree_path is not None:
            worktree_path = Path(journal.worktree_path)
            spec_path = dispatch_core.resolve_story_spec_path(repo_root, slug, feed_story)
            if spec_path is not None:
                try:
                    worktree_spec_path = dispatch_core.relocated_spec_path(spec_path, repo_root, worktree_path)
                except ValueError:
                    worktree_spec_path = None
                if worktree_spec_path is not None:
                    spec_text = fs.read_text(worktree_spec_path)
                    if spec_text is not None:
                        spec_status = parse_spec_status(spec_text)
                        spec_blocking_condition = parse_blocking_condition(spec_text)
                    try:
                        spec_relative_path = str(worktree_spec_path.resolve().relative_to(worktree_path.resolve()))
                    except ValueError:
                        spec_relative_path = None

        verdict = resolve_dispatch_session_verdict(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            journal=journal,
            effective_policy=effective_policy,
            run_dir=run_dir,
            spec_relative_path=spec_relative_path,
        )
        if verdict == DispatchSessionVerdict.FAILED:
            session_log = fs.read_text(run_dir / _LOG_FILENAME)
            changed_path_count = 0
            git_progress_unknown = False
            git_changed_paths: tuple[str, ...] = ()
            if journal.worktree_path is not None and journal.baseline_head_sha:
                try:
                    git_facts = gather_dispatch_git_facts(
                        vcs,
                        fs=fs,
                        repo_root=repo_root,
                        worktree=Path(journal.worktree_path),
                        story_key=feed_story,
                        project_slug=slug,
                        baseline_head_sha=journal.baseline_head_sha,
                        merge_subject_template=effective_policy.merge_subject_template.value,
                        followup_review=journal.followup_review,
                    )
                    changed_path_count = len(git_facts.changed_paths)
                    git_changed_paths = git_facts.changed_paths
                except VcsCommandError, ValueError:
                    git_progress_unknown = True

            # Story 50.1 Part B: ahead of the transient/terminal split, so
            # an already-landed head is never re-dispatched (TRANSIENT) NOR
            # halts the station (TERMINAL) -- it advances, exactly the way
            # MRS-DISP-040 does. ``git_progress_unknown`` means the campaign
            # could not observe the changed paths at all, and an unobserved
            # zero is never treated as an observed one. Checked before the
            # blocked-spec check below (2026-09-19 review pass) so a worktree
            # that is both already-landed and carries a stale `blocked` spec
            # still reports the more definitive, terminal fact.
            if (
                not followup_entry
                and not git_progress_unknown
                and dispatch_fleet.is_already_landed_self_refusal(
                    changed_path_count=changed_path_count,
                    session_log=session_log,
                )
            ):
                return dispatch_fleet.StationBlockEvidence(
                    reason=(
                        f"{dispatch_fleet.ALREADY_LANDED_ADVANCE_PREFIX}: the "
                        f"last dispatch of {feed_story!r} (run "
                        f"{run_dir.name!r}) refused itself with zero changed "
                        "paths and merged evidence in its session log -- the "
                        "work is already landed, so the station advances "
                        "instead of relaunching it"
                    ),
                    block_class=dispatch_fleet.FleetBlockClass.STORY,
                )

            # Story 51.4 (CAP-252): the worktree's own tracked spec may name
            # the block reason itself -- a deliberate `status: blocked` (the
            # 27.3 incident) surfaces here, before the transient/terminal
            # classification below.
            if spec_status == "blocked":
                return dispatch_fleet.StationBlockEvidence(
                    reason=(
                        f"the last dispatch of {feed_story!r} (run "
                        f"{run_dir.name!r}) left its tracked spec "
                        f"status: blocked (blocking condition: "
                        f"{spec_blocking_condition or 'not stated'})"
                    ),
                    block_class=dispatch_fleet.FleetBlockClass.STORY,
                )
            # Story 51.4 (CAP-252): a diff that collapses to just the
            # tracked spec file is narration, not work -- read it as
            # zero-progress here so a harness-ceiling termination (the
            # 51.3 incident) classifies TRANSIENT/re-dispatchable via the
            # existing session-log check below, not TERMINAL.
            classify_changed_path_count = changed_path_count
            if not git_progress_unknown and is_spec_only_narration(
                git_changed_paths, narration_spec_path(spec_relative_path, followup_review=journal.followup_review)
            ):
                classify_changed_path_count = 0
            if is_dispatch_verification_refusal(
                completion_verdict=journal.completion_verdict,
                verification_verdict=journal.verification_verdict,
                verification_failed_gate=journal.verification_failed_gate,
            ):
                current_head: str | None = None
                if journal.worktree_path is not None:
                    try:
                        current_head = vcs.worktree_head_sha(Path(journal.worktree_path))
                    except VcsCommandError:
                        current_head = None
                refusal_head = journal.final_revision or journal.baseline_head_sha
                if not verification_refusal_head_unchanged(
                    refusal_head_sha=refusal_head,
                    current_head_sha=current_head,
                ):
                    return None
                return dispatch_fleet.StationBlockEvidence(
                    reason=format_verification_refusal_park_reason(
                        story_key=feed_story,
                        run_id=run_dir.name,
                        failed_gate=journal.verification_failed_gate,
                    ),
                    block_class=dispatch_fleet.FleetBlockClass.STORY,
                )
            block_kind = classify_dispatch_block(
                session_log=session_log,
                failed_gate=journal.verification_failed_gate,
                changed_path_count=classify_changed_path_count,
            )
            if block_kind is DispatchBlockKind.TRANSIENT:
                return None
            gate = journal.verification_failed_gate
            detail = f", failed gate {gate}" if gate else ""
            reason = (
                f"the last dispatch of {feed_story!r} (run {run_dir.name!r}) "
                f"ended 'failed' by git and process facts{detail}"
            )
            block_class = dispatch_fleet.classify_fleet_block(
                changed_path_count=changed_path_count,
                has_review_verify_evidence=dispatch_fleet.has_review_verify_cycle_evidence(
                    verification_verdict=journal.verification_verdict,
                    verification_failed_gate=journal.verification_failed_gate,
                    completion_stop_reason=journal.completion_stop_reason,
                ),
            )
            if git_progress_unknown:
                block_class = dispatch_fleet.FleetBlockClass.STORY
            return dispatch_fleet.StationBlockEvidence(reason=reason, block_class=block_class)
        return None
    return None


def station_story_blocked_evidence(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    effective_policy: policy.EffectivePolicy,
) -> str | None:
    facts = station_story_block_facts(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        effective_policy=effective_policy,
    )
    return facts.reason if facts is not None else None


def live_dispatch_conflict(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    effective_policy: policy.EffectivePolicy,
    harness_reported_failure: bool = False,
) -> str | None:
    """Same-story live redispatch refusal (Story 22.2); delegates to CAP-5 guard."""
    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        effective_policy=effective_policy,
        harness_reported_failure=harness_reported_failure,
    )
    if conflict is None or conflict.code != "MRS-DISP-011":
        return None
    return conflict.message.removeprefix("refusing redispatch: ")


def run_dispatch(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    vcs: CommittingVcs | None = None,
    build_harness: BuildHarnessPort | None = None,
    process: ProcessPort | None = None,
    harness: HarnessPort | None = None,
    context: MarshalContext | None = None,
) -> int:
    """``marshal factory dispatch <slug> <story>`` -- or, with ``--stories``
    (Story 22.11, FR-193 CAP-10), a caller-supplied ordered sequence chained
    on this one station via ``run_fleet_drain``'s existing campaign machinery
    -- never a second preflight, landing, or campaign-journal path.
    """
    del context
    raw_story = getattr(args, "story", None)
    raw_stories = getattr(args, "stories", None)
    if raw_story and raw_stories:
        finding = Finding(
            code="MRS-DISP-032",
            severity=Severity.ERROR,
            message="pass exactly one of a `story` positional or `--stories` -- not both",
        )
        return _emit(args, {"slug": args.slug}, [finding])
    if not raw_story and not raw_stories:
        finding = Finding(
            code="MRS-DISP-032",
            severity=Severity.ERROR,
            message="pass exactly one of a `story` positional or `--stories`",
        )
        return _emit(args, {"slug": args.slug}, [finding])
    if raw_stories:
        # Extend the surface, don't fork it (the spec's own Approach): a
        # caller-supplied sequence is just `drain --mode drain_to_zero
        # --station <slug> --stories <raw_stories>` under the hood -- the
        # SAME chaining/preflight/journal machinery Story 22.7 built,
        # scoped to this one station's explicit list instead of its ledger
        # order.
        drain_args = argparse.Namespace(
            mode=dispatch_fleet.FleetCampaignMode.DRAIN_TO_ZERO.value,
            station=args.slug,
            stories=raw_stories,
            leave_remaining=0,
            once=False,
            max_cycles=0,
            tick_seconds=_FLEET_TICK_SECONDS,
            campaign=None,
            format=getattr(args, "format", "text"),
            harness=getattr(args, "harness", None),
            max_in_flight=getattr(args, "max_in_flight", None),
        )
        return run_fleet_drain(
            drain_args,
            fs=fs,
            vcs=vcs,
            build_harness=build_harness,
            process=process,
            harness=harness,
        )
    policy_flags = _policy_flags_from_harness_arg(getattr(args, "harness", None))
    attempt = dispatch_once(
        slug=args.slug,
        story=raw_story,
        fs=fs,
        vcs=vcs,
        build_harness=build_harness,
        process=process,
        policy_flags=policy_flags or None,
    )
    return _emit(args, dict(attempt.data), list(attempt.findings))


def dispatch_once(
    *,
    slug: str,
    story: str,
    fs: FsPort | None = None,
    vcs: CommittingVcs | None = None,
    build_harness: BuildHarnessPort | None = None,
    process: ProcessPort | None = None,
    policy_flags: dict[str, object] | None = None,
    parallel_dispatch: bool = False,
) -> DispatchAttempt:
    """Launch exactly one governed story session and report data + findings.

    The whole body of ``marshal factory dispatch`` minus its envelope
    rendering -- extracted verbatim (Story 22.7) so the fleet-drain mode can
    call the SAME primitive once per station per cycle instead of shelling
    out and re-parsing an envelope, or (worse) re-implementing the CAP-2
    zombie refusal, the CAP-5 per-station guard, or the CAP-5 cross-station
    overlap advisory. ``run_dispatch`` is now the thin argparse/emit shell
    over this function; its behavior is unchanged.
    """
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    build_harness = build_harness if build_harness is not None else BmadBuildHarness()
    process = process if process is not None else PosixProcess()

    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug, "story": story}

    def _done() -> DispatchAttempt:
        return DispatchAttempt(data=data, findings=tuple(findings))

    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-DISP-001",
                severity=Severity.ERROR,
                message=f"malformed project slug {slug!r}",
            )
        )
        return _done()

    try:
        story_key = normalize(story)
    except ValueError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-002",
                severity=Severity.ERROR,
                message=f"malformed story key {story!r}: {exc}",
            )
        )
        return _done()
    data["story_key"] = render_feed_key(story_key)

    try:
        repo_root = vcs.repo_common_root(Path.cwd())
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-004",
                severity=Severity.ERROR,
                message=f"cannot resolve repository root: {exc}",
            )
        )
        return _done()

    session_finding = _surface_session_precondition_findings(process=process, repo_root=repo_root)
    if session_finding is not None:
        findings.append(session_finding)

    scope_refusal = _dispatch_scope_refusal(slug)
    if scope_refusal is not None:
        findings.append(scope_refusal)
        return _done()

    spec_path = dispatch_core.resolve_story_spec_path(repo_root, slug, story)
    if spec_path is None:
        findings.append(
            Finding(
                code="MRS-DISP-005",
                severity=Severity.ERROR,
                message=(
                    f"no tracked spec found for story {render_feed_key(story_key)!r} "
                    f"under {dispatch_core.planning_specs_dir(repo_root, slug)!r}"
                ),
            )
        )
        return _done()
    data["spec_path"] = str(spec_path)

    try:
        spec_text = spec_path.read_text(encoding="utf-8")
    except OSError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-005",
                severity=Severity.ERROR,
                message=f"cannot read spec {spec_path!r}: {exc}",
            )
        )
        return _done()

    # Story 74.2 (spec-feature-flag-governance CAP-3): the Guild's flag gate is
    # consulted before the policy composes and before any worktree or harness
    # session exists -- a story the gate would red is refused here, with zero
    # changed paths, instead of by MRS-GATE-010 after the work is done.
    flag_finding = _consult_flag_gate(fs=fs, process=process, repo_root=repo_root, spec_path=spec_path)
    if flag_finding is not None:
        findings.append(flag_finding)
        if flag_finding.severity == Severity.ERROR:
            return _done()

    effective_policy = _compose_policy(slug, flags=policy_flags)
    difficulty = dispatch_core.read_declared_difficulty(spec_text)
    session_log = _last_failed_dispatch_session_log(fs, repo_root, slug, render_feed_key(story_key))
    prior_failed_attempts = _count_prior_failed_dispatch_attempts(fs, repo_root, slug, render_feed_key(story_key))
    tier_resolution = dispatch_core.resolve_tier_harness(
        effective_policy,
        difficulty=difficulty,
        session_log=session_log,
    )
    model, escalated, from_model, to_model = dispatch_core.resolve_dispatch_model_with_retry_escalation(
        effective_policy,
        difficulty=difficulty,
        prior_failed_attempts=prior_failed_attempts,
    )
    budget_env = dispatch_core.build_budget_env(effective_policy)
    data["model"] = model
    data["budget_env"] = dict(budget_env)
    if escalated:
        data["escalated"] = True
        data["from_model"] = from_model
        data["to_model"] = to_model
    if tier_resolution.resolved_models:
        data["resolved_models"] = dict(tier_resolution.resolved_models)
    if tier_resolution.serving_pools:
        data["serving_pool"] = dict(tier_resolution.serving_pools)
    # Story 28.1 (SPEC-marshal-token-economy CAP-1): the SAME composition
    # site `adapters/harness_bmadloop.py::render_policy_toml` (bmad-loop
    # spin) resolves its `[context]` block from -- one function, both
    # engines. Story 28.2 (CAP-2) makes the `wire` entry of this SAME
    # payload load-bearing on this engine: it is handed to
    # `BuildHarnessPort.dispatch` below, which resolves the profile's
    # declared wrapper against it. Every other layer stays declaration-only
    # until its own story lands.
    context_payload = policy.resolve_context_layers(effective_policy)
    data["context"] = context_payload
    # Story 28.2 (CAP-2): seed the wire disposition to OFF here, the moment
    # the `[context]` payload it derives from exists, so `data["wire"]` is
    # present on EVERY envelope this verb can still emit -- including the
    # `BuildHarnessError` path below, which returns without ever reaching
    # the launch result and so used to omit the key from precisely the
    # envelope an operator most wants to inspect. `ports/build_harness.py`
    # promises the disposition is "a recorded fact of every dispatch", and
    # `cli/spin.py` echoes its own unconditionally; a key that is sometimes
    # absent makes every consumer guard a read that was specified not to
    # need one. Overwritten with the real decision once a launch returns.
    data["wire"] = harness_profile.WireWrap(applied=False).journal_payload()
    # Story 77.1 (CAP-282): the same guarantee, from the same point, for the
    # `structure-graph` layer's disposition -- present on every envelope
    # emitted from the policy composition onward (the argument, repo-root,
    # scope and spec-lookup refusals return earlier, as they do for `wire`),
    # including every refusal before a worktree exists. Overwritten with the
    # real outcome once the worktree is provisioned.
    structure_graph = StructureGraphSeed()
    data["structure_graph"] = structure_graph.journal_payload()

    # Story 22.8 (FR-193 CAP-8): profile-aware harness resolution -- the
    # policy's ordered `harness_preference` walked to the first profile
    # whose binary resolves AND whose authcheck passes. Binary presence
    # alone was necessary-but-insufficient (2026-08-27: three real
    # dispatches died on cursor's auth wall with the binary on PATH), so
    # every skipped candidate is a structured finding, never silent.
    # Story 28.11 (CAP-12): when the tier map names a harness for dev,
    # that profile leads the walk instead of the flat preference alone.
    # Story 50.3 (CAP-246): an EXPLICIT `--harness` (the composed
    # `harness_preference` FLAG layer, never the default/repo/project
    # layer) outranks that tier-map lead -- the walk starts from the
    # flag's own profiles and a tier-map harness the flag does not name
    # contributes nothing to it. Without the flag (layer stays default/
    # repo_defaults/project) this is unchanged: the tier map still leads.
    preference = tuple(effective_policy.harness_preference.value)
    explicit_harness_flag = effective_policy.harness_preference.layer == policy.PolicyLayer.FLAG
    if tier_resolution.harness_profile is not None and not explicit_harness_flag:
        preference = (tier_resolution.harness_profile,) + tuple(
            name for name in preference if name != tier_resolution.harness_profile
        )
    preference = exclude_harness_profiles_after_transient_failure(preference, session_log)
    if not preference:
        preference = tuple(effective_policy.harness_preference.value)
    resolution = build_harness.binary_present(preference, repo_root=repo_root)
    for profile_error in resolution.profile_errors:
        findings.append(Finding(code="MRS-DISP-028", severity=Severity.WARN, message=profile_error))
    for skip in resolution.skipped:
        findings.append(
            Finding(
                code="MRS-DISP-027",
                severity=Severity.WARN,
                message=f"harness profile {skip.profile!r} skipped: {skip.reason}",
            )
        )
    if not resolution:
        tried = (
            "; ".join(f"{s.profile}: {s.reason}" for s in resolution.skipped)
            or "empty harness_preference -- no candidate to try"
        )
        findings.append(
            Finding(
                code="MRS-DISP-003",
                severity=Severity.ERROR,
                message=f"no dispatchable session-harness profile ({tried})",
            )
        )
        return _done()
    data["harness_profile"] = resolution.profile

    # 2026-09-12 (dispatch-tier-routing-fails-safe): the tier-mapped model
    # was resolved BEFORE this live binary+authcheck walk ran, from a
    # bare-string model_tier_map entry that carries no harness of its own
    # (see core/tier_routing.py::resolve_tier_launch) -- so it can name a
    # model that belongs to a DIFFERENT provider than whichever profile the
    # walk above actually landed on (harness_preference has no bmad-loop
    # counterpart, a candidate's auth/binary failed, a transient exclusion
    # kicked in, etc.). render_policy_toml (the bmad-loop `spin` engine)
    # already guards this same mismatch at render time; this is the SAME
    # guard for the `dispatch` engine, applied once the REAL harness is
    # known. A mismatch drops the model override entirely (never launches a
    # real, live-verified harness with a model it was never meant to
    # receive) rather than block the dispatch outright -- the harness's own
    # default model is always a safe fallback.
    resolved_provider = adapter_provider(resolution.profile)
    catalog = effective_policy.model_cost_catalog.value
    model_provider = provider_declaring_model(catalog, data["model"]) if data["model"] else None
    # Story 51.5 (CAP-253): `provider_declaring_model` returns `None` both
    # for a genuinely uncatalogued model id and, by documented design, for
    # the harness's own default/alias ids (`sonnet`/`opus`/`haiku` -- the
    # catalog is a declared PRICE snapshot, not a model registry, see
    # `is_harness_default_model`). The ORIGINAL guard below only fired on
    # the cross-provider case (`model_provider` names a DIFFERENT
    # provider); widen it so a model catalogued under NO provider at all,
    # and not one of the harness's own default/alias ids, ALSO WARNs --
    # a genuinely foreign or mistyped model id must not reach a live
    # launch uncaught -- while the cross-provider case and the harness's
    # own default/alias ids stay exactly as before.
    #
    # `provider_declaring_model` also returns `None` whenever NO catalog is
    # declared at all -- most stations (e.g. a cursor-only
    # `harness_preference` with no `model_cost_catalog` block) never
    # declare one. Without gating on `catalog_declared`, a correctly
    # tier-mapped, correctly resolved model on one of those stations reads
    # as "uncatalogued" too and gets its override dropped on every real
    # dispatch. There is nothing to compare against when no catalog was
    # ever declared, so that case must stay silent, same as pre-story --
    # only a DECLARED catalog that omits the model is suspicious.
    model_uncatalogued = (
        data["model"] is not None
        and model_provider is None
        and not is_harness_default_model(data["model"])
        and catalog_declared(catalog)
    )
    model_cross_provider = model_provider is not None and model_provider != resolved_provider
    if model_cross_provider or model_uncatalogued:
        if model_provider is not None:
            provider_clause = (
                f"is catalogued under provider {model_provider!r}, but the "
                f"live-verified harness {resolution.profile!r} resolves to "
                f"provider {resolved_provider!r}"
            )
        else:
            provider_clause = (
                "is catalogued under no known provider despite a declared "
                "cost catalog, and is not the live-verified harness "
                f"{resolution.profile!r}'s own default/alias model id"
            )
        findings.append(
            Finding(
                code="MRS-DISP-043",
                severity=Severity.WARN,
                message=(
                    f"tier-mapped model {data['model']!r} {provider_clause} "
                    "-- dropping the model override for this dispatch; the "
                    "harness's own default applies"
                ),
            )
        )
        # Story 50.3: `model` (not just `data["model"]`) must drop too --
        # it is what the intent journal entry and the live
        # `build_harness.dispatch(model=model, ...)` call below actually
        # use. Leaving the local variable at its mismatched value would
        # journal and LAUNCH the foreign-provider model even though the
        # envelope's own `data["model"]` correctly reported the drop.
        model = None
        # The escalation triple is read straight from these locals when the
        # intent entry is built further down (`if escalated: ...`) -- if
        # only `model` were reset, a run that had escalated before the
        # mismatch fired would journal `model: null` alongside a stale
        # `escalated: true`/`from_model`/`to_model`, a self-contradictory
        # persisted entry.
        escalated = False
        from_model = None
        to_model = None
        data["model"] = None
        data.pop("escalated", None)
        data.pop("from_model", None)
        data.pop("to_model", None)
        if "resolved_models" in data:
            data["resolved_models"] = {
                stage: stage_model for stage, stage_model in data["resolved_models"].items() if stage != "dev"
            }

    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        story_key=render_feed_key(story_key),
        effective_policy=effective_policy,
        candidate_spec_text=spec_text,
        deps_graph=_load_station_deps_graph(repo_root, slug),
        parallel_dispatch=parallel_dispatch,
    )
    if conflict is not None:
        findings.append(
            Finding(
                code=conflict.code,
                severity=Severity.ERROR,
                message=conflict.message,
            )
        )
        data["in_flight_story"] = conflict.in_flight_story_key
        return _done()

    findings.extend(
        cross_station_surface_overlap_advisories(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            requested_slug=slug,
            requested_story_key=render_feed_key(story_key),
            requested_spec_text=spec_text,
        )
    )

    try:
        provisioned = _ensure_dispatch_worktree(vcs, repo_root, slug, render_feed_key(story_key))
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-006",
                severity=Severity.ERROR,
                message=f"cannot provision dispatch worktree: {exc}",
            )
        )
        return _done()
    data["branch"] = provisioned.branch
    if provisioned.refusal is not None:
        findings.append(
            Finding(
                code="MRS-DISP-030",
                severity=Severity.ERROR,
                message=provisioned.refusal,
            )
        )
        return _done()
    if provisioned.legacy:
        findings.append(
            Finding(
                code="MRS-DISP-031",
                severity=Severity.WARN,
                message=(
                    f"story {render_feed_key(story_key)!r} is still on the "
                    f"pre-22.9 branch name {provisioned.branch!r} and lands "
                    "from there; it migrates to "
                    f"{dispatch_core.dispatch_worktree_branch(slug, render_feed_key(story_key))!r} "
                    "once that legacy branch is landed AND deleted — while "
                    "it survives, a later dispatch of this story is refused "
                    "(MRS-DISP-030) rather than migrated"
                ),
            )
        )
    worktree = provisioned.worktree
    if worktree is None:
        findings.append(
            Finding(
                code="MRS-DISP-006",
                severity=Severity.ERROR,
                message=(
                    "cannot provision dispatch worktree: branch "
                    f"{provisioned.branch!r} resolved with neither a worktree "
                    "nor a refusal"
                ),
            )
        )
        return _done()
    data["worktree_path"] = str(worktree)
    worktree_scope_refusal = _seed_dispatch_worktree_scope(fs=fs, worktree=worktree, slug=slug)
    if worktree_scope_refusal is not None:
        findings.append(worktree_scope_refusal)
        return _done()
    output_finding = _seed_dispatch_output_layer(fs=fs, worktree=worktree, context_payload=context_payload)
    if output_finding is not None:
        findings.append(output_finding)
    # Story 77.1 (CAP-282): give the worktree a codegraph index -- a copy of
    # the primary checkout's base, synced -- so `bmad-build-auto`'s step 01
    # finds `.codegraph/codegraph.db` (Story 28.33). Never blocks: every
    # failure is a named WARN and the session runs without the index.
    structure_graph = _seed_dispatch_structure_graph(
        fs=fs,
        process=process,
        worktree=worktree,
        repo_root=repo_root,
        context_payload=context_payload,
    )
    findings.extend(structure_graph.findings)
    data["structure_graph"] = structure_graph.journal_payload()
    try:
        spec_path = dispatch_core.relocated_spec_path(spec_path, repo_root, worktree)
    except ValueError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-005",
                severity=Severity.ERROR,
                message=f"cannot relocate spec into dispatch worktree: {exc}",
            )
        )
        return _done()
    data["spec_path"] = str(spec_path)

    try:
        baseline_head_sha = vcs.worktree_head_sha(worktree)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-012",
                severity=Severity.ERROR,
                message=f"cannot read dispatch worktree baseline head: {exc}",
            )
        )
        return _done()
    data["baseline_head_sha"] = baseline_head_sha

    wip_finding = _surface_worktree_wip_before_dispatch(
        vcs=vcs,
        repo_root=repo_root,
        worktree=worktree,
        baseline_head_sha=baseline_head_sha,
    )
    if wip_finding is not None:
        block_detail = _redispatch_blocked_pending_supervisor_finalize(
            fs=fs,
            repo_root=repo_root,
            slug=slug,
            story_key=render_feed_key(story_key),
            worktree=worktree,
        )
        if block_detail is not None:
            findings.append(
                Finding(
                    code="MRS-DISP-039",
                    severity=Severity.ERROR,
                    message=block_detail,
                )
            )
            return _done()
        findings.append(wip_finding)

    # Story 29.2: worktree spec status: done (follow-up not recommended)
    # is session-terminal. CAP-4 only — never another bmad-build-auto
    # because main's ledger is still backlog.
    live_spec_text = _spec_text_prefer_worktree(spec_path, repo_root, worktree, spec_text)
    spec_status_rewrite: dict[str, str] | None = None
    rewritten_spec_text, spec_status_rewrite = dispatch_core.rewrite_worktree_spec_status_for_bmad_build_auto(
        live_spec_text
    )
    if spec_status_rewrite is not None:
        try:
            fs.write_text_atomic(spec_path, rewritten_spec_text)
        except FsError as exc:
            findings.append(
                Finding(
                    code="MRS-DISP-005",
                    severity=Severity.ERROR,
                    message=f"cannot rewrite worktree spec status for harness launch: {exc}",
                )
            )
            return _done()
        live_spec_text = rewritten_spec_text
    latest_landing_verdict: str | None = None
    latest_journal: dispatch_core.DispatchJournalFacts | None = None
    latest_run_dir = _latest_story_run_dir(fs, repo_root, slug, render_feed_key(story_key))
    if latest_run_dir is not None:
        latest_journal = gather_dispatch_journal_facts(fs, latest_run_dir, latest_run_dir.name)
        latest_landing_verdict = latest_journal.landing_verdict
    spec_status = parse_spec_status(live_spec_text)
    followup = followup_review_recommended(live_spec_text)
    take_land_only = should_take_harness_done_land_only(
        spec_status,
        followup,
        latest_landing_verdict=latest_landing_verdict,
    )
    if not take_land_only and latest_journal is not None:
        try:
            current_head = vcs.worktree_head_sha(worktree)
        except VcsCommandError:
            current_head = None
        take_land_only = should_take_verification_refusal_land_only(
            spec_status,
            followup,
            completion_verdict=latest_journal.completion_verdict,
            verification_verdict=latest_journal.verification_verdict,
            verification_failed_gate=latest_journal.verification_failed_gate,
            refusal_head_sha=latest_journal.final_revision or latest_journal.baseline_head_sha,
            current_head_sha=current_head,
        )
    if take_land_only:
        data["harness_done_land_only"] = True
        land_verdict, named_target, land_envelope = _attempt_harness_done_cap4(
            slug=slug,
            story_key=story_key,
            worktree=worktree,
            repo_root=repo_root,
            effective_policy=effective_policy,
            spec_text=live_spec_text,
            fs=fs,
            vcs=vcs,
            process=process,
            # Story 73.1 (CAP-281): a story whose latest run was a follow-up review lands as one.
            **_followup_review_kwargs(_latest_story_followup_review(fs, repo_root, slug, render_feed_key(story_key))),
        )
        data["land_verdict"] = land_verdict.value
        data["land_named_target"] = named_target
        # Story 80.1 (CAP-284): the check wait's record -- a refused landing is re-run through this path.
        land_checks = land_envelope.data.get(LANDING_CHECKS_FIELD) if isinstance(land_envelope, Envelope) else None
        if land_checks is not None:
            data[LANDING_CHECKS_FIELD] = land_checks
        if land_verdict in {
            DispatchLandingVerdict.LANDED,
            DispatchLandingVerdict.ALREADY_LANDED,
        }:
            return _done()
        findings.append(
            Finding(
                code="MRS-DISP-040",
                severity=Severity.ERROR,
                message=land_fail_operator_message(
                    story_key=render_feed_key(story_key),
                    named_target=named_target,
                    land_verdict=land_verdict.value,
                ),
            )
        )
        return _done()

    # Story 51.4 (spec-pyforge-marshal CAP-252): a worktree spec left
    # `status: blocked` by its last session (the 27.3 incident) must not be
    # relaunched without an operator decision -- distinct from the `done`
    # branch above, this never attempts a CAP-4 land either.
    if parse_spec_status(live_spec_text) == "blocked":
        data["harness_blocked_no_relaunch"] = True
        findings.append(
            Finding(
                code="MRS-DISP-045",
                severity=Severity.ERROR,
                message=(
                    f"story {render_feed_key(story_key)!r} worktree spec is "
                    f"status: blocked -- not relaunching bmad-build-auto without "
                    f"an operator decision (blocking condition: "
                    f"{parse_blocking_condition(live_spec_text) or 'not stated'})"
                ),
            )
        )
        return _done()

    # Story 73.1 (CAP-281): a launch on a `done` spec whose flag is still true is a follow-up review run --
    # derived here, journaled on the launch INTENT below, and read back by the supervisor, the landing and
    # every other reader of the run's merge facts.
    try:
        followup_review = _derive_followup_review(
            vcs=vcs, repo_root=repo_root, slug=slug, story_key=story_key, spec_text=spec_text
        )
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-016",
                severity=Severity.ERROR,
                message=(
                    f"cannot resolve {ORIGIN_MAIN_SHORT!r} to scope the follow-up review run of story "
                    f"{render_feed_key(story_key)!r} to its own branch: {exc}"
                ),
            )
        )
        return _done()

    writer_id = _writer_id()
    mint_moment = _now_utc()
    run_id = mint_run_id(slug, _format_utc_compact(mint_moment), _random_token())
    data["run_id"] = run_id
    run_dir = dispatch_core.dispatch_run_dir(repo_root, slug, run_id)

    try:
        fs.ensure_dir(run_dir.parent)
        fs.create_dir_exclusive(run_dir)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-007",
                severity=Severity.ERROR,
                message=f"cannot create dispatch run directory {run_dir!r}: {exc}",
            )
        )
        return _done()

    intent_entry = build_entry(
        id=JournalEntryId(writer_id, 0),
        ts=_format_entry_ts(mint_moment),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={
            "story_key": render_feed_key(story_key),
            "spec_path": str(spec_path),
            "worktree_path": str(worktree),
            "model": model,
            "budget_env": dict(budget_env),
            "bmad_active_project": slug,
            "baseline_head_sha": baseline_head_sha,
            "harness_profile": resolution.profile,
            "context": context_payload,
            **(
                {
                    "escalated": True,
                    "from_model": from_model,
                    "to_model": to_model,
                }
                if escalated
                else {}
            ),
            **(followup_review.to_intent_payload() if followup_review is not None else {}),
            **({"spec_status_rewrite": spec_status_rewrite} if spec_status_rewrite is not None else {}),
        },
    )
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-007",
                severity=Severity.ERROR,
                message=f"cannot journal dispatch intent: {exc}",
            )
        )
        return _done()

    log_path = run_dir / _LOG_FILENAME
    data["log"] = str(log_path)
    try:
        launch = build_harness.dispatch(
            worktree,
            resolution=resolution,
            project_slug=slug,
            story_key=render_feed_key(story_key),
            spec_path=spec_path,
            model=model,
            budget_env=budget_env,
            log_path=log_path,
            # Story 28.2 (CAP-2): the wire layer's own resolved entry --
            # never the whole `[context]` payload. The launch seam has no
            # business reading a layer it does not implement.
            wire_layer=context_payload[harness_profile.WIRE_LAYER_NAME],
        )
    except BuildHarnessError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-008",
                severity=Severity.ERROR,
                message=f"cannot launch session harness: {exc}",
            )
        )
        outcome_entry = build_entry(
            id=JournalEntryId(writer_id, 1),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=intent_entry.id,
            payload={"ok": False, "error": str(exc)},
        )
        try:
            _append_entry(fs, run_dir, outcome_entry, fsync=False)
        except FsError:
            pass
        return _done()

    data["session_pid"] = launch.pid
    data["session_model"] = launch.model
    if launch.model_omitted_reason is not None:
        findings.append(
            Finding(
                code="MRS-DISP-029",
                severity=Severity.WARN,
                message=launch.model_omitted_reason,
            )
        )
    # Story 28.2 (CAP-2): what the wire layer actually did to THIS launch --
    # echoed and journaled whether it applied, degraded, or stayed off, so
    # "was this session wrapped?" is a recorded fact rather than an
    # inference from an argv nobody kept. A degradation over an ENABLED
    # layer additionally raises MRS-DISP-033 (WARN): the layer disabling
    # itself is always named, never silent -- and never blocking, the
    # session is already live and unwrapped.
    # A harness that returns no decision at all (the port's field is
    # optional) composes the SAME off-shape through `WireWrap` rather than a
    # hand-spelled literal -- `journal_payload()` is the one spelling of
    # this payload, so adding a field to `WireWrap` cannot silently leave a
    # call site behind.
    wire = launch.wire if launch.wire is not None else harness_profile.WireWrap(applied=False)
    data["wire"] = wire.journal_payload()
    if wire.reason is not None:
        findings.append(
            Finding(
                code="MRS-DISP-033",
                severity=Severity.WARN,
                message=wire.reason,
            )
        )
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, 1),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload={
            "ok": True,
            "session_pid": launch.pid,
            "model": launch.model,
            "budget_env": dict(launch.budget_env),
            "harness_profile": launch.profile,
            # A fresh dict per call (never the one already in `data`), so
            # the journal payload and the echoed envelope can never alias.
            "wire": wire.journal_payload(),
            # Story 77.1 (CAP-282): what the `structure-graph` layer did for
            # THIS worktree -- sync / init / skipped, and why -- so "did this
            # session open on an index?" is a recorded fact. A fresh dict,
            # like `wire`'s, so the journal and the envelope never alias.
            "structure_graph": structure_graph.journal_payload(),
        },
    )
    try:
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-009",
                severity=Severity.WARN,
                message=(f"session launched (pid {launch.pid}) but outcome journal write failed: {exc}"),
            )
        )

    if not process.is_alive(launch.pid):
        findings.append(
            Finding(
                code="MRS-DISP-010",
                severity=Severity.WARN,
                message=(
                    f"session harness reported pid {launch.pid} but the process is not alive immediately after launch"
                ),
            )
        )

    supervisor_log = run_dir / _SUPERVISOR_LOG_FILENAME
    data["supervisor_log"] = str(supervisor_log)
    try:
        supervisor_pid = process.spawn_detached(
            [
                sys.executable,
                "-m",
                "pyforge.marshal.dispatch_supervisor",
                str(repo_root),
                slug,
                run_id,
                str(launch.pid),
                str(worktree),
                render_feed_key(story_key),
                baseline_head_sha,
                effective_policy.merge_subject_template.value,
                str(supervisor_log),
            ],
            cwd=repo_root,
            log_path=supervisor_log,
        )
    except ProcessError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-013",
                severity=Severity.WARN,
                message=(
                    f"session launched (pid {launch.pid}) but dispatch "
                    f"completion supervisor could not be spawned: {exc} "
                    f"(supervisor log: {str(supervisor_log)!r})"
                ),
            )
        )
    else:
        data["supervisor_pid"] = supervisor_pid
        supervisor_outcome = build_entry(
            id=JournalEntryId(writer_id, 2),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=intent_entry.id,
            payload={"supervisor_pid": supervisor_pid},
        )
        try:
            _append_entry(fs, run_dir, supervisor_outcome, fsync=False)
        except FsError:
            pass

    return _done()


def _spawn_dispatch_supervisor(
    *,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    run_id: str,
    session_pid: int,
    worktree: Path,
    story_key: str,
    baseline_head_sha: str,
    merge_subject_template: str,
    run_dir: Path,
) -> int | None:
    supervisor_log = run_dir / _SUPERVISOR_LOG_FILENAME
    try:
        return process.spawn_detached(
            [
                sys.executable,
                "-m",
                "pyforge.marshal.dispatch_supervisor",
                str(repo_root),
                slug,
                run_id,
                str(session_pid),
                str(worktree),
                story_key,
                baseline_head_sha,
                merge_subject_template,
                str(supervisor_log),
            ],
            cwd=repo_root,
            log_path=supervisor_log,
        )
    except ProcessError:
        return None


def _load_latest_dispatch_context(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    slug: str,
) -> tuple[Path, Path, str, dispatch_core.DispatchJournalFacts, policy.EffectivePolicy] | None:
    del process
    try:
        repo_root = vcs.repo_common_root(Path.cwd())
    except VcsCommandError:
        return None
    run_dir = latest_dispatch_run_dir(repo_root, slug)
    if run_dir is None:
        return None
    journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
    if journal.story_key is None or journal.worktree_path is None:
        return None
    if journal.session_pid is None or journal.baseline_head_sha is None:
        return None
    return repo_root, run_dir, run_dir.name, journal, _compose_policy(slug)


def _ensure_dispatch_supervision(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    run_dir: Path,
    run_id: str,
    slug: str,
    journal: dispatch_core.DispatchJournalFacts,
    effective_policy: policy.EffectivePolicy,
    operator_kind: str,
) -> tuple[int | None, list[Finding], dict[str, object]]:
    """Re-spawn dispatch supervisor when dead; journal operator attach/resume."""
    findings: list[Finding] = []
    data: dict[str, object] = {
        "slug": slug,
        "run_id": run_id,
        "story_key": journal.story_key,
    }
    session_alive = _is_dispatch_session_alive(process, journal)
    supervisor_alive = journal.supervisor_pid is not None and process.is_alive(journal.supervisor_pid)
    verdict = resolve_dispatch_session_verdict(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        journal=journal,
        effective_policy=effective_policy,
        run_dir=run_dir,
    )
    data["session_alive"] = session_alive
    data["supervisor_alive"] = supervisor_alive
    data["completion_verdict"] = verdict.value if verdict is not None else None
    if verdict not in {DispatchSessionVerdict.LIVE, None}:
        findings.append(
            Finding(
                code="MRS-DISP-023",
                severity=Severity.ERROR,
                message=(
                    f"no live dispatch to recover on station {slug!r}: "
                    f"completion verdict is {verdict.value if verdict else 'unknown'!r}"
                ),
            )
        )
        return None, findings, data
    if not session_alive and verdict != DispatchSessionVerdict.LIVE:
        findings.append(
            Finding(
                code="MRS-DISP-023",
                severity=Severity.ERROR,
                message=(
                    f"no live dispatch session on station {slug!r} (session pid {journal.session_pid} is not alive)"
                ),
            )
        )
        return None, findings, data
    new_supervisor_pid: int | None = journal.supervisor_pid
    if not supervisor_alive:
        respawned = _spawn_dispatch_supervisor(
            process=process,
            repo_root=repo_root,
            slug=slug,
            run_id=run_id,
            session_pid=journal.session_pid,
            worktree=Path(journal.worktree_path),
            story_key=journal.story_key,
            baseline_head_sha=journal.baseline_head_sha,
            merge_subject_template=effective_policy.merge_subject_template.value,
            run_dir=run_dir,
        )
        if respawned is None:
            findings.append(
                Finding(
                    code="MRS-DISP-024",
                    severity=Severity.WARN,
                    message=(
                        "dispatch session is live but completion supervisor "
                        "could not be re-spawned; run continues unsupervised"
                    ),
                )
            )
        else:
            new_supervisor_pid = respawned
            data["supervisor_pid"] = respawned
            writer_id = _writer_id()
            kind = (
                dispatch_core.KIND_DISPATCH_OPERATOR_ATTACH
                if operator_kind == "attach"
                else dispatch_core.KIND_DISPATCH_OPERATOR_RESUME
            )
            entry = build_entry(
                id=JournalEntryId(writer_id, 0),
                ts=_format_entry_ts(_now_utc()),
                run_id=run_id,
                kind=kind,
                phase=Phase.OBSERVATION,
                payload={
                    "supervisor_pid": respawned,
                    "session_pid": journal.session_pid,
                    "reconciled_unsupervised": not supervisor_alive,
                },
            )
            try:
                _append_entry(fs, run_dir, entry, fsync=True)
            except FsError as exc:
                findings.append(
                    Finding(
                        code="MRS-DISP-025",
                        severity=Severity.WARN,
                        message=f"supervision recovered but operator journal failed: {exc}",
                    )
                )
    data["log"] = str(run_dir / _LOG_FILENAME)
    return new_supervisor_pid, findings, data


def add_factory_dispatch_attach_subparser(factory_subparsers: argparse._SubParsersAction) -> None:
    parser = factory_subparsers.add_parser(
        "dispatch-attach",
        help="Recover supervision and follow a live dispatch session log (Story 22.6).",
        description=(
            "Re-spawns the dispatch completion supervisor when it died, journals "
            "the operator attach, then execs tail on the session log — never "
            "busy-waits in Python."
        ),
    )
    parser.add_argument("slug", help="The BMAD project slug (station).")
    parser.set_defaults(handler=run_dispatch_attach)


def add_factory_dispatch_resume_subparser(factory_subparsers: argparse._SubParsersAction) -> None:
    parser = factory_subparsers.add_parser(
        "dispatch-resume",
        help="Re-spawn dispatch supervision without blocking (Story 22.6).",
        description=(
            "Re-spawns the dispatch completion supervisor when it died and "
            "returns promptly — unsupervised git progress is reconciled by "
            "the supervisor from facts, not operator session state."
        ),
    )
    parser.add_argument("slug", help="The BMAD project slug (station).")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_dispatch_resume)


def run_dispatch_attach(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    vcs: VcsPort | None = None,
    process: ProcessPort | None = None,
) -> int:
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    process = process if process is not None else PosixProcess()
    slug = args.slug
    if not policy._is_valid_project_slug(slug):
        finding = Finding(
            code="MRS-DISP-001",
            severity=Severity.ERROR,
            message=f"malformed project slug {slug!r}",
        )
        try:
            print(
                f"error: {finding.code} [{finding.severity.value}] {finding.message}",
                file=sys.stderr,
                flush=True,
            )
        except OSError, UnicodeEncodeError:
            _suppress_downstream_pipe_close()
        return exit_code_for(compute_verdict((finding,)))
    loaded = _load_latest_dispatch_context(fs=fs, vcs=vcs, process=process, slug=slug)
    if loaded is None:
        finding = Finding(
            code="MRS-DISP-023",
            severity=Severity.ERROR,
            message=f"no dispatch run found for station {slug!r}",
        )
        try:
            print(
                f"error: {finding.code} [{finding.severity.value}] {finding.message}",
                file=sys.stderr,
                flush=True,
            )
        except OSError, UnicodeEncodeError:
            _suppress_downstream_pipe_close()
        return exit_code_for(compute_verdict((finding,)))
    repo_root, run_dir, run_id, journal, effective_policy = loaded
    _, findings, data = _ensure_dispatch_supervision(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        run_dir=run_dir,
        run_id=run_id,
        slug=slug,
        journal=journal,
        effective_policy=effective_policy,
        operator_kind="attach",
    )
    if any(f.severity == Severity.ERROR for f in findings):
        try:
            for finding in findings:
                if finding.severity == Severity.ERROR:
                    print(
                        f"error: {finding.code} [{finding.severity.value}] {finding.message}",
                        file=sys.stderr,
                        flush=True,
                    )
        except OSError, UnicodeEncodeError:
            _suppress_downstream_pipe_close()
        return exit_code_for(compute_verdict(tuple(findings)))
    log_path = Path(str(data["log"]))
    try:
        # Story 14.4, CAP-6: stays raw os.execvp, exempted file-level in
        # test_process_sole_ownership.py -- REPLACES this process's own
        # image with `tail -F` so `marshal attach` hands the user's
        # terminal straight to the live dispatch log (Ctrl-C exits tail,
        # not a subprocess). pyforge.core.process's ProcessPort has no
        # analog: it launches and either waits (run) or detaches
        # (spawn_detached) a CHILD, never replaces the caller's own
        # process -- a fundamentally different primitive, not a second
        # implementation of subprocess launching.
        os.execvp("tail", ["tail", "-F", str(log_path)])
    except OSError as exc:
        finding = Finding(
            code="MRS-DISP-026",
            severity=Severity.ERROR,
            message=f"cannot exec tail on dispatch log {log_path!r}: {exc}",
        )
        try:
            print(
                f"error: {finding.code} [{finding.severity.value}] {finding.message}",
                file=sys.stderr,
                flush=True,
            )
        except OSError, UnicodeEncodeError:
            _suppress_downstream_pipe_close()
        return exit_code_for(compute_verdict((finding,)))
    return 0


def run_dispatch_resume(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    vcs: VcsPort | None = None,
    process: ProcessPort | None = None,
) -> int:
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    process = process if process is not None else PosixProcess()
    slug = args.slug
    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug}
    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-DISP-001",
                severity=Severity.ERROR,
                message=f"malformed project slug {slug!r}",
            )
        )
        return _emit(args, data, findings)
    loaded = _load_latest_dispatch_context(fs=fs, vcs=vcs, process=process, slug=slug)
    if loaded is None:
        findings.append(
            Finding(
                code="MRS-DISP-023",
                severity=Severity.ERROR,
                message=f"no dispatch run found for station {slug!r}",
            )
        )
        return _emit(args, data, findings)
    repo_root, run_dir, run_id, journal, effective_policy = loaded
    _, sup_findings, sup_data = _ensure_dispatch_supervision(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        run_dir=run_dir,
        run_id=run_id,
        slug=slug,
        journal=journal,
        effective_policy=effective_policy,
        operator_kind="resume",
    )
    findings.extend(sup_findings)
    data.update(sup_data)
    return _emit(args, data, findings)


# =============================================================================
# Story 22.7 (FR-193 CAP-7): fleet-wide drain as a marshal-orchestrated mode.
#
# Everything below COMPOSES already-shipped primitives and adds exactly one
# new decision -- "which story does this station get next" -- whose pure core
# lives in `core/dispatch_fleet.py`:
#
#   queue      <- HarnessPort.ledger_story_statuses over each station's
#                 TRACKED sprint-status-ledger.yaml (the same parser
#                 `marshal status --reconcile-ledger` already uses), plus an
#                 OPTIONAL in-repo override file. Never `.cursor/…/queues.yaml`.
#   preflight  <- dispatch_once -> station_in_flight_conflict (CAP-2/CAP-5)
#   parallel   <- dispatch_once launches DETACHED and returns, so issuing one
#                 dispatch per station in a cycle leaves eight sessions
#                 running concurrently. FR-184's in-loop max_parallel clamp
#                 is not read, written, or referenced anywhere here.
#   land+chain <- the per-story dispatch supervisor each launch spawns already
#                 owns verify -> land -> `dispatch_land_finalize` (merge,
#                 scoped `sprint-ledger-sync --project <station>`, spec
#                 promotion). The fleet mode adds no landing path at all: it
#                 re-reads the advanced ledger on the next cycle, finds the
#                 station's slot free, and dispatches the next story.
# =============================================================================


def add_factory_drain_subparser(factory_subparsers: argparse._SubParsersAction) -> None:
    parser = factory_subparsers.add_parser(
        "drain",
        help="Fleet-wide drain across every pyforge station (Story 22.7).",
        description=(
            "Reads each pyforge station's ordered backlog from its TRACKED "
            "sprint-status-ledger.yaml (plus optional in-repo order "
            "overrides), applies the named campaign mode, preflights every "
            "dispatch through the shipped zombie/in-flight refusals, and "
            "launches one story per station -- detached, so stations run in "
            "parallel. Unless --once is given, a detached campaign "
            "supervisor re-runs the cycle so each station's next story is "
            "chained once its predecessor's merge-through-finalize advances "
            "the tracked ledger. --mode is REQUIRED and never defaulted."
        ),
    )
    parser.add_argument(
        "--mode",
        default=None,
        help=(
            "Campaign mode: "
            + " | ".join(dispatch_fleet.CAMPAIGN_MODES)
            + " (required -- a missing or unknown mode is refused, never "
            "silently defaulted)."
        ),
    )
    parser.add_argument(
        "--station",
        default=None,
        help=(
            "Restrict this campaign to exactly one station's own tracked "
            "backlog (Story 22.11, FR-193 CAP-10) -- accepts either the "
            "bare name (`scribe`) or the full slug (`pyforge-scribe`). "
            "Every other station is untouched by this invocation. Omit "
            "for the fleet-wide default (all live pyforge stations)."
        ),
    )
    parser.add_argument(
        "--stories",
        default=None,
        help=(
            "Chain a caller-supplied ordered story-key sequence on "
            "--station's own backlog instead of its ledger order (Story "
            "22.11, FR-193 CAP-10) -- comma-separated, requires --station. "
            "Normally reached via `marshal factory dispatch <slug> "
            "--stories ...`; --once/--campaign chaining consumes this "
            "same flag across supervised cycles."
        ),
    )
    parser.add_argument(
        "--leave-remaining",
        type=int,
        default=1,
        help=("Under --mode leave_one, how many backlog stories to leave untouched per station (default: 1)."),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one cycle and return; spawn no campaign supervisor.",
    )
    # `--max-cycles` / `--tick-seconds` default to SUPPRESS so `--plan` can tell
    # an explicit `--max-cycles 0` from an absent flag (both are launch-only
    # and a usage error beside `--plan`); `run_fleet_drain` reads each with
    # `getattr(args, ..., default)`, so a drain's own behaviour is unchanged.
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=argparse.SUPPRESS,
        help="Campaign-supervisor cycle ceiling (default 0 = until the campaign completes).",
    )
    parser.add_argument(
        "--tick-seconds",
        type=int,
        default=argparse.SUPPRESS,
        help=f"Campaign-supervisor delay between cycles (default: {_FLEET_TICK_SECONDS}).",
    )
    parser.add_argument(
        "--campaign",
        default=None,
        help=(
            "Reuse an existing campaign run id instead of minting one -- how "
            "the detached campaign supervisor keeps every cycle on one "
            "journal (and so remembers which stations are blocked)."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--harness",
        default=None,
        help=(
            "Ordered session-harness preference for every dispatch this "
            "campaign launches (comma-separated profile names, e.g. "
            "cursor,claude). Overrides project/repo defaults without "
            "editing marshal-policy.toml."
        ),
    )
    parser.add_argument(
        "--max-in-flight",
        type=int,
        default=None,
        dest="max_in_flight",
        help=(
            "Within-station parallel dispatch cap for this campaign (Story "
            "28.16) -- overrides project policy max_parallel. Default: "
            "policy value or 1 (serial, byte-identical to today's drain)."
        ),
    )
    parser.add_argument(
        "--retry-environment-blocks",
        action="store_true",
        help=(
            "Under drain_to_zero or leave_one, skip past environment-classified "
            "blocks (zero git progress, zero review/verify evidence) so the "
            "next story dispatches. Story-classified failures still halt the "
            "station. Also honored under skip_on_blocked (the default there)."
        ),
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help=(
            "Story 65.1 (CAP-274): report what this drain would do -- each "
            "station's next story (or parallel wave) and every refusal "
            "decidable before launch -- and launch nothing: no worktree, run "
            "directory, journal entry, lock or supervisor. Takes --mode, "
            "--station, --stories, --leave-remaining, --max-in-flight, "
            "--harness and --retry-environment-blocks; --once, --campaign, "
            "--max-cycles and --tick-seconds are launch-only (usage error). "
            "Exits 4 when a station's next story would not dispatch cleanly, "
            "1 when a plan cannot be computed, 0 otherwise."
        ),
    )
    parser.add_argument(
        "--all-stories",
        action="store_true",
        help=(
            "With --plan: evaluate every queued story, not only each "
            "station's next one (queued stories report as MRS-DRAINPLAN-002)."
        ),
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help=(
            "With --plan: also probe the environment a launch needs -- the "
            "session-harness binary and authcheck walk (MRS-DISP-003) and the "
            "steward session-precondition check (MRS-DISP-049). Off by "
            "default: the plan otherwise runs no harness, authcheck or probe."
        ),
    )
    parser.set_defaults(handler=run_fleet_drain)


def _preflight_explicit_story_specs(repo_root: Path, slug: str, stories: tuple[str, ...]) -> tuple[str, ...]:
    """Stories in ``stories`` with no tracked spec -- fast-fail before mint."""
    missing: list[str] = []
    for story in stories:
        if dispatch_core.resolve_story_spec_path(repo_root, slug, story) is None:
            missing.append(story)
    return tuple(missing)


def _predicate_payload(predicate: dispatch_re_preflight.RefusePredicate) -> dict[str, str]:
    return {
        "gate": predicate.gate,
        "spec_fingerprint": predicate.spec_fingerprint,
        "verify_fingerprint": predicate.verify_fingerprint,
        "digest": predicate.digest(),
    }


def _predicate_from_payload(raw: object) -> dispatch_re_preflight.RefusePredicate | None:
    if not isinstance(raw, dict):
        return None
    gate = raw.get("gate")
    spec = raw.get("spec_fingerprint")
    verify = raw.get("verify_fingerprint")
    if not isinstance(gate, str) or not isinstance(spec, str) or not isinstance(verify, str):
        return None
    return dispatch_re_preflight.RefusePredicate(
        gate=gate,
        spec_fingerprint=spec,
        verify_fingerprint=verify,
    )


def _primary_checkout_is_clean_main(vcs: VcsPort, repo_root: Path) -> bool:
    """``True`` only when the primary checkout (``repo_root``) is a clean,
    unmoved local ``main`` -- the same "is this checkout safe to trust"
    gate ``cli/land.py::_resync_home_branch`` already encodes for
    fast-forwarding (Story 51.9, re-mint of 51.3). Any git failure is
    treated as "not safe to trust" rather than propagated -- the caller
    falls back to reading ``origin/main`` directly in that case, never
    crashes the campaign's own ledger read."""
    try:
        if vcs.has_uncommitted_changes(repo_root):
            return False
        return vcs.worktree_head_sha(repo_root) == vcs.resolve_ref(repo_root, "main")
    except VcsCommandError:
        return False


def _station_ledger_statuses(
    *,
    harness: HarnessPort,
    vcs: VcsPort,
    repo_root: Path,
    ledger_path: Path,
) -> tuple[tuple[str, str], ...]:
    """One station's ledger statuses (Story 51.9, re-mint of 51.3).

    ``_promote_sprint_ledger`` (CAP-5) publishes a promotion onto
    ``origin/main`` WITHOUT ever touching the primary checkout's own
    working tree -- so a sibling station's finalize can promote a story to
    ``done`` while this campaign's primary checkout sits stale, dirty, or
    on a different branch. Trusts the local ``HarnessPort`` read only when
    ``repo_root`` is verifiably a clean, unmoved ``main`` (byte-identical
    to before this story); otherwise reads ``origin/main``'s own copy of
    the ledger via ``VcsPort.file_text_at_ref`` and the pre-existing
    ``_parse_sprint_ledger_statuses`` text scanner, falling back to the
    local ``HarnessPort`` read when the remote read fails or the ledger is
    absent at ``origin/main``. Raises only what
    ``HarnessPort.ledger_story_statuses`` itself already raises -- every
    call site's own pre-existing exception handling is unchanged."""
    if _primary_checkout_is_clean_main(vcs, repo_root):
        return harness.ledger_story_statuses(ledger_path)
    remote_text: str | None = None
    try:
        rel_path = ledger_path.relative_to(dispatch_core.canonical_repo_root(repo_root)).as_posix()
        # Review pass 2026-09-19 (VG1): refresh the local cache of
        # `origin/main` first -- without this, a stale cached ref could
        # silently defeat the fallback in exactly the scenario it exists
        # to fix. Same swallow-and-fall-back handling as the read itself.
        vcs.fetch(repo_root, "origin", "main")
        remote_text = vcs.file_text_at_ref(repo_root, _BASE_REF, rel_path)
    except VcsCommandError, ValueError:
        remote_text = None
    if remote_text is None:
        return harness.ledger_story_statuses(ledger_path)
    return tuple(_parse_sprint_ledger_statuses(remote_text).items())


def gather_fleet_missing_spec_escalations(
    *,
    fs: FsPort,
    harness: HarnessPort,
    vcs: VcsPort,
    repo_root: Path,
) -> dict[str, dispatch_fleet.MissingSpecEscalation]:
    """Active ``MRS-DISP-005`` campaign blocks that still lack a tracked spec.

    Story 28.19 (CAP-2): operators must never read ``idle`` while remaining
    backlog is blocked on a missing spec. Reads the latest fleet-drain
    campaign journal only -- never auto-authors specs.
    """
    run_id = dispatch_fleet.latest_fleet_campaign_run_id(repo_root)
    if run_id is None:
        return {}
    run_dir = dispatch_fleet.fleet_run_dir(repo_root, run_id)
    blocked, _predicates = _campaign_blocked_from_journal(fs, run_dir, run_id)
    escalations: dict[str, dispatch_fleet.MissingSpecEscalation] = {}
    for slug, stories in blocked.items():
        for story, detail in stories.items():
            gate = dispatch_re_preflight.parse_refuse_gate(detail)
            if gate != "MRS-DISP-005":
                continue
            if dispatch_core.resolve_story_spec_path(repo_root, slug, story) is not None:
                continue
            expected = dispatch_core.expected_story_spec_glob(repo_root, slug, story)
            if expected is None:
                continue
            ledger_path = dispatch_fleet.station_ledger_path(repo_root, slug)
            try:
                statuses = _station_ledger_statuses(
                    harness=harness, vcs=vcs, repo_root=repo_root, ledger_path=ledger_path
                )
            except HarnessError, OSError, ValueError:
                continue
            backlog = dispatch_fleet.station_backlog(statuses)
            if not backlog:
                continue
            try:
                blocked_key = normalize(story)
            except ValueError:
                continue
            if not any(normalize(raw_key) == blocked_key for raw_key in backlog):
                continue
            escalations[slug] = dispatch_fleet.MissingSpecEscalation(
                story=render_feed_key(blocked_key),
                expected_spec_glob=expected,
            )
            break
    return escalations


def _reconcile_campaign_blocked_for_re_preflight(
    *,
    repo_root: Path,
    blocked: dict[str, dict[str, str]],
    prior_predicates: dict[str, dict[str, dispatch_re_preflight.RefusePredicate]],
    policy_flags: dict[str, object] | None,
) -> tuple[dict[str, dict[str, str]], list[Finding]]:
    """Drop or rate-limit campaign blocks whose refuse predicate can change."""
    findings: list[Finding] = []
    reconciled: dict[str, dict[str, str]] = {}
    for slug, station_blocked in blocked.items():
        effective_policy = _compose_policy(slug, flags=policy_flags)
        verify_commands = effective_policy.verify_commands.value
        prior = prior_predicates.get(slug, {})
        kept, results = dispatch_re_preflight.reconcile_station_re_preflight(
            repo_root=repo_root,
            slug=slug,
            blocked=station_blocked,
            verify_commands=verify_commands,
            prior_predicates=prior,
        )
        if kept:
            reconciled[slug] = kept
        for result in results:
            if result.decision is dispatch_re_preflight.RePreflightDecision.CLEARED:
                continue
            if result.decision is dispatch_re_preflight.RePreflightDecision.RATE_LIMITED:
                findings.append(
                    Finding(
                        code="MRS-DRAIN-017",
                        severity=Severity.WARN,
                        message=(
                            f"station {slug!r}: story {result.story!r} remains "
                            f"blocked on {result.gate} with an unchanged refuse "
                            "predicate -- rate-limited this tick, not re-dispatched"
                        ),
                    )
                )
    return reconciled, findings


def _open_followup_row_keys(vcs: VcsPort, repo_root: Path, slug: str) -> frozenset[StoryKey]:
    """The stories whose ``DW-FRR`` row is open in ``slug``'s deferred-work ledger at ``origin/main``.

    An absent or unreadable ledger is none: the row gate only ever keeps a follow-up in play, never adds one."""
    try:
        text = vcs.file_text_at_ref(repo_root, ORIGIN_MAIN, _deferred_work_ledger_rel(slug))
    except VcsCommandError:
        return frozenset()
    return frozenset(deferred_work.open_followup_review_story_keys(text)) if text else frozenset()


def _reconcile_campaign_blocked(
    *,
    vcs: VcsPort,
    repo_root: Path,
    blocked: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    """Drop blocked entries for stories already merged on origin/main.

    A follow-up review entry (Story 73.2, CAP-281) is judged by its row, not by the story's first merge: a
    story whose ``DW-FRR`` row is still open on ``origin/main`` is not "already landed", so its block stays."""
    if not blocked:
        return blocked
    fetch = getattr(vcs, "fetch", None)
    if fetch is None:
        return blocked
    try:
        fetch(repo_root, "origin", "main")
        subjects = vcs.commit_subjects(repo_root, _BASE_REF)
    except VcsCommandError, AttributeError:
        return blocked
    reconciled: dict[str, dict[str, str]] = {}
    for slug, station_blocked in blocked.items():
        effective_policy = _compose_policy(slug)

        def _spec_status_for(candidate_key: StoryKey, *, _slug: str = slug) -> str | None:
            # Story 51.7/CAP-255: the same station-branch corroboration
            # `dispatch_land`/`dispatch_supervisor` apply -- a mint/
            # fallout/fix PR's station-branch merge must not prune a
            # campaign's blocked entry as though it had actually landed.
            # Fails closed (never corroborates) on any git read failure.
            try:
                spec_text = dispatch_core.spec_text_at_ref(vcs, repo_root, _slug, str(candidate_key))
            except VcsCommandError:
                return None
            return promotion_core.read_spec_status(spec_text)

        merged = promotion_core.corroborated_merged_story_keys(
            subjects,
            effective_policy.merge_subject_template.value,
            slug,
            spec_status_for=_spec_status_for,
        )
        open_followups = _open_followup_row_keys(vcs, repo_root, slug)
        merged_feed = frozenset(render_feed_key(key) for key in merged if key not in open_followups)
        reconciled[slug] = prune_blocked_stories_merged_on_main(
            station_blocked,
            merged_story_keys=merged_feed,
        )
    return reconciled


def _load_station_story_deps(
    fs: FsPort, repo_root: Path, slug: str
) -> dict[StoryKey, dispatch_fleet.ParsedStoryDeps] | None:
    """Read declared ``Deps:`` edges for one station (Story 28.12).

    Returns ``None`` when no epics doc could be read -- ``station_backlog``
    keeps its legacy story-key ordering. Returns a (possibly empty) mapping
    when at least one epics-family doc parsed successfully.
    """
    combined: dict[StoryKey, dispatch_fleet.ParsedStoryDeps] = {}
    read_any = False
    for path in dispatch_fleet.station_epics_paths(repo_root, slug):
        text = fs.read_text(path)
        if text is None:
            continue
        read_any = True
        combined.update(dispatch_fleet.parse_epics_dependencies(text))
    if not read_any:
        return None
    return combined


def _read_fleet_queue_config(
    fs: FsPort, repo_root: Path
) -> tuple[dict[str, tuple[str, ...]], dict[str, dict[str, str]], list[Finding]]:
    """Read the OPTIONAL in-repo order-override / skip-policy file.

    The in-repo analog of the interim runner's ``queues.yaml``
    ``order_overrides``/``skip_policies`` blocks -- minus its ``stations:``
    block, which was a regenerated copy of state the tracked ledgers already
    hold. Absent (the default) means "ledger order, no skips"; unreadable or
    malformed is reported, never silently treated as absent.

    Every ``skip_policies`` entry is an operator's DECLARED skip, honored
    under every campaign mode -- the interim runner's own entries all carried
    ``action: skip_on_blocked`` while the campaign ran ``drain_to_zero``.
    Mode governs DERIVED blocks (CAP-2 failure evidence), not these.
    """
    findings: list[Finding] = []
    path = dispatch_fleet.queue_config_path(repo_root)
    text = fs.read_text(path)
    if text is None:
        return {}, {}, findings
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        findings.append(
            Finding(
                code="MRS-DRAIN-008",
                severity=Severity.WARN,
                message=(
                    f"cannot parse fleet queue overrides at {path}: {exc} "
                    "-- falling back to tracked-ledger order with no skips"
                ),
                path=str(path),
            )
        )
        return {}, {}, findings
    if document is None:
        return {}, {}, findings
    if not isinstance(document, dict):
        findings.append(
            Finding(
                code="MRS-DRAIN-008",
                severity=Severity.WARN,
                message=(
                    f"fleet queue overrides at {path} must be a mapping, got "
                    f"{type(document).__name__} -- falling back to "
                    "tracked-ledger order with no skips"
                ),
                path=str(path),
            )
        )
        return {}, {}, findings

    overrides: dict[str, tuple[str, ...]] = {}
    raw_overrides = document.get("order_overrides") or {}
    if isinstance(raw_overrides, dict):
        for raw_station, raw_keys in raw_overrides.items():
            if not isinstance(raw_keys, list):
                continue
            slug = dispatch_fleet.normalize_station_slug(str(raw_station))
            overrides[slug] = tuple(str(k) for k in raw_keys if isinstance(k, str))

    skips: dict[str, dict[str, str]] = {}
    raw_skips = document.get("skip_policies") or []
    if isinstance(raw_skips, list):
        for entry in raw_skips:
            if not isinstance(entry, dict):
                continue
            raw_station = entry.get("station")
            raw_story = entry.get("story")
            if not isinstance(raw_station, str) or not isinstance(raw_story, str):
                continue
            slug = dispatch_fleet.normalize_station_slug(raw_station)
            reason = entry.get("reason")
            skips.setdefault(slug, {})[raw_story] = (
                str(reason) if isinstance(reason, str) and reason else "declared skip policy"
            )
    return overrides, skips, findings


def _station_blocked_map(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    backlog: tuple[str, ...],
    configured_skips: Mapping[str, str],
    campaign_blocked: Mapping[str, str],
    effective_policy: policy.EffectivePolicy,
    followups: frozenset[str] = frozenset(),
) -> tuple[dict[str, str], dict[str, dispatch_fleet.FleetBlockClass]]:
    """DERIVED blocks at the HEAD of ``backlog``, with their evidence.

    Walks the backlog only as far as the first dispatchable story: under
    every mode the queue decision stops there, so probing the tail would be
    pure cost. A story is blocked when this campaign already saw a
    non-liveness refusal for it, or when CAP-2's own facts say its last
    dispatch ended ``failed``.

    ``configured_skips`` is read here ONLY to keep walking past a story the
    operator declared skipped -- those never enter the returned map, because
    a hand-declared skip is honored under every mode while a derived block
    is what the campaign mode governs (see ``plan_station_queue``).

    ``followups`` (Story 73.2): the queue entries that are follow-up reviews, which
    ``station_story_block_facts`` judges by their open row, not by the story's first landing.
    """
    blocked: dict[str, str] = {}
    block_classes: dict[str, dispatch_fleet.FleetBlockClass] = {}
    for story in backlog:
        if story in configured_skips:
            continue
        if story in campaign_blocked:
            blocked[story] = campaign_blocked[story]
            block_classes[story] = dispatch_fleet.FleetBlockClass.STORY
            continue
        try:
            facts = station_story_block_facts(
                fs=fs,
                vcs=vcs,
                process=process,
                repo_root=repo_root,
                slug=slug,
                story_key=story,
                effective_policy=effective_policy,
                followup_entry=story in followups,
            )
        except VcsCommandError, ValueError:
            facts = None
        if facts is None:
            break
        blocked[story] = facts.reason
        block_classes[story] = facts.block_class
    return blocked, block_classes


def _classify_attempt(
    slug: str, story: str, attempt: DispatchAttempt
) -> tuple[dispatch_fleet.StationCycleStatus, str | None, list[Finding]]:
    """Turn one ``dispatch_once`` outcome into a station status + findings.

    A liveness refusal (CAP-2's MRS-DISP-011, CAP-5's MRS-DISP-021) is the
    NORMAL state of a healthy campaign -- eight stations working means eight
    busy stations -- so it is relayed as a campaign-level WARN that names the
    original code and the in-flight story verbatim, rather than surfaced at
    its own ERROR tier, which would red every cycle. Every other refusal is
    relayed as-is, keeping its own registered code and severity: a missing
    spec is a real problem the operator must see.
    """
    findings: list[Finding] = []
    errors = attempt.errors
    if not errors:
        # Advisories (e.g. CAP-5's MRS-DISP-022 overlap) still surface.
        findings.extend(attempt.findings)
        return dispatch_fleet.StationCycleStatus.DISPATCHED, None, findings
    liveness = next((f for f in errors if f.code in {"MRS-DISP-011", "MRS-DISP-021"}), None)
    if liveness is not None:
        in_flight = attempt.data.get("in_flight_story")
        findings.append(
            Finding(
                code="MRS-DRAIN-006",
                severity=Severity.WARN,
                message=(f"station {slug!r}: no dispatch this cycle -- {liveness.code} {liveness.message}"),
            )
        )
        detail = f"{liveness.code}: in flight {in_flight!r}" if in_flight else liveness.code
        return dispatch_fleet.StationCycleStatus.IN_FLIGHT, detail, findings
    findings.extend(attempt.findings)
    first = errors[0]
    return (
        dispatch_fleet.StationCycleStatus.REFUSED,
        f"{first.code}: {first.message}",
        findings,
    )


def _member_outcome(
    *,
    repo_root: Path,
    slug: str,
    story: str,
    status: dispatch_fleet.StationCycleStatus,
    detail: str | None,
    verify_commands: Sequence[str],
) -> dispatch_fleet.MemberOutcome:
    """One wave member's own outcome (Story 82.10): its story, status and detail, and for a REFUSED member at a
    re-preflightable gate the refuse predicate computed from THAT detail for THAT story -- never another member's."""
    predicate_payload: dict[str, str] | None = None
    if status is dispatch_fleet.StationCycleStatus.REFUSED and detail:
        gate = dispatch_re_preflight.parse_refuse_gate(detail)
        if dispatch_re_preflight.is_re_preflightable_gate(gate):
            assert gate is not None
            predicate_payload = _predicate_payload(
                dispatch_re_preflight.compute_refuse_predicate(
                    repo_root=repo_root,
                    slug=slug,
                    story=story,
                    gate=gate,
                    verify_commands=verify_commands,
                )
            )
    return dispatch_fleet.MemberOutcome(story=story, status=status, detail=detail, refuse_predicate=predicate_payload)


def _mint_wave_id(slug: str) -> str:
    """A fresh dispatch-wave id for ``slug`` (the cycle's own; a plan never mints one)."""
    return mint_run_id(slug, _format_utc_compact(_now_utc()), _random_token())


def _wave_journal_writer_id(wave_id: str) -> str:
    """Filesystem-safe journal writer id for a dispatch wave (Story 33.8).

    ``wave_id`` embeds ISO-8601 timestamps with uppercase ``T``/``Z`` that
    violate ``core.journal``'s ``writer_id`` pattern; hash instead.
    """
    import hashlib

    digest = hashlib.sha256(wave_id.encode()).hexdigest()[:24]
    return f"wave-{digest}"


def _journal_dispatch_wave(
    fs: FsPort,
    repo_root: Path,
    slug: str,
    wave: dispatch_fleet.WaveBatch,
    *,
    surfaces: Mapping[str, tuple[str, ...] | None],
) -> None:
    """Record one parallel wave intent (Story 28.16, CAP-3)."""
    import hashlib

    members_payload = []
    for story in wave.members:
        surface = surfaces.get(story) or ()
        digest = hashlib.sha256(repr(surface).encode()).hexdigest()
        members_payload.append({"story": story, "surfaces_hash": digest})
    refused_payload = [
        {
            "story": r.story,
            "reason": r.reason,
            **({"overlap_with": r.overlap_with} if r.overlap_with else {}),
            **({"paths": list(r.paths)} if r.paths else {}),
        }
        for r in wave.refused
    ]
    wave_run = dispatch_core.dispatch_runs_dir(repo_root, slug) / _DISPATCH_WAVES_DIRNAME / wave.wave_id
    fs.ensure_dir(wave_run)
    intent = build_entry(
        id=JournalEntryId(_wave_journal_writer_id(wave.wave_id), 0),
        ts=_format_entry_ts(_now_utc()),
        run_id=wave.wave_id,
        kind=dispatch_core.KIND_DISPATCH_WAVE,
        phase=Phase.INTENT,
        payload={
            "wave_id": wave.wave_id,
            "station": slug,
            "max_parallel": wave.max_parallel,
            "members": members_payload,
            "refused": refused_payload,
        },
    )
    _append_entry(fs, wave_run, intent, fsync=True)


@dataclass(frozen=True)
class CycleSlugs:
    """The stations one drain cycle walks (Story 65.1: extracted from
    ``execute_fleet_cycle`` so ``factory drain --plan`` resolves them the same
    way). ``finding`` is ``MRS-DRAIN-013`` (``station`` names no live pyforge
    station -- ``unknown_station`` is then true and the cycle stops) or
    ``MRS-DRAIN-012`` (no stations found at all -- the cycle walks none)."""

    slugs: tuple[str, ...]
    finding: Finding | None = None
    unknown_station: bool = False


def resolve_cycle_slugs(repo_root: Path, station: str | None) -> CycleSlugs:
    """The live pyforge stations one cycle walks, ``station`` narrowing to one."""
    slugs = dispatch_fleet.fleet_station_slugs(dispatch_core.list_station_slugs(repo_root))
    if station is not None:
        normalized_station = dispatch_fleet.normalize_station_slug(station)
        if normalized_station not in slugs:
            return CycleSlugs(
                slugs=(),
                finding=Finding(
                    code="MRS-DRAIN-013",
                    severity=Severity.ERROR,
                    message=(
                        f"unknown station {normalized_station!r}: not among "
                        f"the live pyforge stations ({', '.join(slugs) or 'none found'})"
                    ),
                ),
                unknown_station=True,
            )
        slugs = (normalized_station,)
    if not slugs:
        # Distinct from "every station is drained": `campaign_complete(())`
        # is vacuously True, so without this the operator would get a clean,
        # findings-free "campaign complete" from a repo where the projects
        # tree was simply unreadable or absent -- a false green.
        return CycleSlugs(
            slugs=(),
            finding=Finding(
                code="MRS-DRAIN-012",
                severity=Severity.ERROR,
                message=(
                    "no pyforge stations found under "
                    f"{dispatch_core.canonical_repo_root(repo_root)}"
                    "/_bmad-output/projects -- an empty fleet is reported, "
                    "never treated as a drained one"
                ),
            ),
        )
    return CycleSlugs(slugs=slugs)


@dataclass(frozen=True)
class FollowupPlan:
    """What a drain campaign does about the follow-up reviews landed stories recommended (Story 73.2, CAP-281).

    ``selected`` maps each station to the follow-ups it queues after its implementable backlog, newest landing
    first; ``waiting`` are the qualifying rows beyond the per-campaign cap (they wait for a later campaign);
    ``stale`` are open rows whose spec no longer qualifies (named, never dispatched); ``cap`` is
    ``dispatch.max_followup_reviews_per_campaign`` as the repository's layers resolve it and ``launched`` how
    many follow-ups the campaign already launched. ``findings`` are the facts the cycle emits -- the unreadable
    ledger, the stale rows, a station layer that sets the cap and the waiting count -- empty when a drain has
    no follow-up facts at all, so such a drain is byte-identical to one before this story."""

    selected: Mapping[str, tuple[dispatch_fleet.FollowupCandidate, ...]] = field(default_factory=dict)
    waiting: tuple[dispatch_fleet.FollowupCandidate, ...] = ()
    stale: tuple[dispatch_fleet.StaleFollowupRow, ...] = ()
    findings: tuple[Finding, ...] = ()
    cap: int = policy.DEFAULT_MAX_FOLLOWUP_REVIEWS_PER_CAMPAIGN
    launched: int = 0


def _repository_followup_review_cap() -> int:
    """``dispatch.max_followup_reviews_per_campaign`` from the repository's layers only: Marshal's default, then
    ``_bmad-output/policy-defaults.toml``. The cap bounds a CAMPAIGN, not a station, so no station's project
    layer or invocation flag is composed in (``plan_followup_reviews`` names a project layer that sets it)."""
    repo_defaults, _repo_finding = read_repo_policy_defaults()
    effective, _findings = policy.compose(
        project_slug=dispatch_fleet.FLEET_JOURNAL_SLUG, repo_defaults=repo_defaults, project={}, flags={}
    )
    return policy.resolve_followup_review_cap(effective)


def _project_layer_followup_cap_path(slug: str) -> Path | None:
    """``slug``'s project ``marshal-policy.toml`` when it sets ``[dispatch].max_followup_reviews_per_campaign``."""
    candidate = conventional_project_policy_path(slug)
    if not candidate.is_file():
        return None
    try:
        project_data = _read_project_policy(candidate)
    except PolicyIOError:
        return None
    block = project_data.get("dispatch")
    if isinstance(block, Mapping) and policy.MAX_FOLLOWUP_REVIEWS_KEY in block:
        return candidate
    return None


def plan_followup_reviews(
    *,
    repo_root: Path,
    slugs: Sequence[str],
    vcs: VcsPort,
    launched: frozenset[tuple[str, StoryKey]] = frozenset(),
    policy_flags: dict[str, object] | None = None,
    fetch: bool = True,
) -> FollowupPlan:
    """The campaign's follow-up review decision for ``slugs`` (Story 73.2, spec-pyforge-marshal CAP-281).

    One campaign-wide read before the per-station loop, shared by ``execute_fleet_cycle`` and ``factory drain
    --plan`` so the plan cannot drift from the drain. For each station it reads the tracked deferred-work ledger
    AT ``origin/main`` (a row the finalize published and the primary has not pulled yet still counts; an absent
    ledger holds no rows, an unreadable one is a WARN and no follow-ups for that station) and each open
    ``DW-FRR`` row's story spec at ``origin/main`` (``dispatch_core.spec_text_at_ref``).

    ``fetch`` is the one thing here that is not a read. With ``fetch=True`` (the drain) and any row open, it runs
    ``git fetch origin main`` and reads the ledger again: a stale remote-tracking ref would show a row a landed
    review already closed, and the drain would run the review a second time. The fetch writes
    ``refs/remotes/origin/main`` and uses the network, so it is best effort -- a failed fetch is tolerated, not
    named, and the reads simply use the ref as it stands. ``factory drain --plan`` passes ``fetch=False``
    (CAP-274: a plan writes nothing and touches no remote) and so reads ``origin/main`` as the checkout holds it.

    The pure core decides: ``station_followup_queue`` (row gate x spec ``done`` with the flag true; the rest
    stale), ``landing_positions`` (the newest-first position of each story's corroborated merge subject in
    ``commit_subjects(ORIGIN_MAIN)``) and ``select_campaign_followups`` (newest landing first, at most the cap
    minus ``launched``). ``launched`` is what the campaign journal says earlier cycles already launched
    (``_followups_launched_from_journal``). Apart from the optional fetch nothing here writes, and an unreadable
    ledger or history degrades to a named finding."""
    findings: list[Finding] = []
    for slug in slugs:
        layer_path = _project_layer_followup_cap_path(slug)
        if layer_path is not None:
            findings.append(
                Finding(
                    code="MRS-DRAIN-018",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: {layer_path} sets dispatch.{policy.MAX_FOLLOWUP_REVIEWS_KEY} -- not "
                        "applied: the cap bounds a campaign, not a station, so only Marshal's default and "
                        "_bmad-output/policy-defaults.toml set it"
                    ),
                    path=str(layer_path),
                )
            )

    def read_rows() -> dict[str, tuple[StoryKey, ...] | Finding]:
        rows: dict[str, tuple[StoryKey, ...] | Finding] = {}
        for slug in slugs:
            ledger_rel = _deferred_work_ledger_rel(slug)
            try:
                text = vcs.file_text_at_ref(repo_root, ORIGIN_MAIN, ledger_rel)
            except VcsCommandError as exc:
                rows[slug] = Finding(
                    code="MRS-DRAIN-018",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: cannot read the deferred-work ledger {ledger_rel} at {ORIGIN_MAIN}: "
                        f"{exc} -- no follow-up reviews are queued for it this cycle"
                    ),
                    path=ledger_rel,
                )
                continue
            rows[slug] = deferred_work.open_followup_review_story_keys(text) if text else ()
        return rows

    rows = read_rows()
    if fetch and any(isinstance(value, tuple) and value for value in rows.values()):
        try:
            vcs.fetch(repo_root, "origin", "main")
        except VcsCommandError:
            pass
        rows = read_rows()

    candidates: list[dispatch_fleet.FollowupCandidate] = []
    stale: list[dispatch_fleet.StaleFollowupRow] = []
    spec_cache: dict[tuple[str, StoryKey], str | None] = {}

    def spec_text(slug: str, key: StoryKey) -> str | None:
        if (slug, key) not in spec_cache:
            try:
                spec_cache[(slug, key)] = dispatch_core.spec_text_at_ref(vcs, repo_root, slug, str(key))
            except VcsCommandError:
                spec_cache[(slug, key)] = None
        return spec_cache[(slug, key)]

    for slug in slugs:
        station_rows = rows.get(slug, ())
        if isinstance(station_rows, Finding):
            findings.append(station_rows)
            continue
        if not station_rows:
            continue
        station_candidates, station_stale = dispatch_fleet.station_followup_queue(
            slug, station_rows, {key: spec_text(slug, key) for key in station_rows}
        )
        candidates.extend(station_candidates)
        stale.extend(station_stale)

    for row in stale:
        findings.append(
            Finding(
                code="MRS-DRAIN-018",
                severity=Severity.WARN,
                message=(
                    f"station {row.slug!r}: the open follow-up review row {row.row_id} is not dispatched -- "
                    f"{row.reason}; it stays open and is never queued while that holds"
                ),
            )
        )

    cap = _repository_followup_review_cap()
    positions: dict[tuple[str, StoryKey], int] = {}
    if candidates and cap - len(launched) > 0:
        try:
            subjects = vcs.commit_subjects(repo_root, _BASE_REF)
        except VcsCommandError as exc:
            subjects = ()
            findings.append(
                Finding(
                    code="MRS-DRAIN-018",
                    severity=Severity.WARN,
                    message=(
                        f"cannot read {_BASE_REF}'s history: {exc} -- the follow-up reviews are taken in ledger "
                        "order, not newest landing first"
                    ),
                )
            )
        for slug in dict.fromkeys(candidate.slug for candidate in candidates):
            template = _compose_policy(slug, flags=policy_flags).merge_subject_template.value

            def _spec_status_for(key: StoryKey, *, _slug: str = slug) -> str | None:
                # `_reconcile_campaign_blocked`'s corroboration reader: a station-branch merge counts as a
                # landing only when the story's spec reads done at origin/main (fails closed on a git error).
                return promotion_core.read_spec_status(spec_text(_slug, key))

            found = dispatch_fleet.landing_positions(
                subjects,
                template,
                slug,
                wanted={candidate.key for candidate in candidates if candidate.slug == slug},
                spec_status_for=_spec_status_for,
            )
            positions.update({(slug, key): index for key, index in found.items()})

    selection = dispatch_fleet.select_campaign_followups(candidates, positions, cap=cap, launched=launched)
    if selection.waiting:
        findings.append(
            Finding(
                code="MRS-DRAIN-019",
                severity=Severity.INFO,
                message=(
                    f"{len(selection.waiting)} follow-up review(s) wait for a later campaign: "
                    f"dispatch.{policy.MAX_FOLLOWUP_REVIEWS_KEY} is {cap} ({len(launched)} already launched this "
                    "campaign), newest landings first"
                ),
            )
        )
    selected: dict[str, tuple[dispatch_fleet.FollowupCandidate, ...]] = {}
    for candidate in selection.selected:
        selected[candidate.slug] = (*selected.get(candidate.slug, ()), candidate)
    return FollowupPlan(
        selected=selected,
        waiting=selection.waiting,
        stale=tuple(stale),
        findings=tuple(findings),
        cap=cap,
        launched=len(launched),
    )


@dataclass(frozen=True)
class StationCyclePlan:
    """One station's queue computation for one drain cycle (Story 65.1).

    FACTS only -- ledger, backlog, blocked map, queue decision and (parallel
    mode) the wave -- never a finding and never a write, so
    ``execute_fleet_cycle`` keeps every emission and every writer in its
    existing order while ``factory drain --plan`` reads the very same facts.
    Each early return of ``plan_station_cycle`` leaves the later fields at
    their defaults; the fields that ARE set say why the cycle stops there:

    * ``ledger_error`` -- the tracked ledger could not be read;
    * ``finalize_pending`` -- the head is mid-finalize (Story 50.1 Part A);
    * ``queue`` with no ``next_story`` -- blocked, drained, left-remaining or
      everything skipped;
    * ``live_stories`` -- a parallel wave is still in flight;
    * otherwise ``stories_to_dispatch`` -- serial: the queue head; parallel:
      ``wave.members`` (possibly empty).

    ``backlog`` is the implementable backlog followed by ``followup_stories`` (Story 73.2, CAP-281): the
    follow-up reviews of already-landed stories the campaign selected for this station, newest landing first.
    They are queue entries only -- their ledger rows stay ``done``."""

    slug: str
    ledger_path: Path
    ledger_error: str | None = None
    statuses: tuple[tuple[str, str], ...] = ()
    backlog: tuple[str, ...] = ()
    followup_stories: tuple[str, ...] = ()
    effective_policy: policy.EffectivePolicy | None = None
    station_skips: Mapping[str, str] = field(default_factory=dict)
    finalize_pending: tuple[str, str] | None = None
    blocked: Mapping[str, str] = field(default_factory=dict)
    block_classes: Mapping[str, dispatch_fleet.FleetBlockClass] = field(default_factory=dict)
    queue: dispatch_fleet.StationQueuePlan | None = None
    parallel_cap: int = 1
    live_stories: tuple[str, ...] = ()
    deps_graph: Mapping[str, tuple[StoryKey, ...]] | None = None
    ready: tuple[str, ...] = ()
    surfaces: Mapping[str, tuple[str, ...] | None] = field(default_factory=dict)
    wave: dispatch_fleet.WaveBatch | None = None
    stories_to_dispatch: tuple[str, ...] = ()


def plan_station_cycle(
    *,
    repo_root: Path,
    slug: str,
    mode: dispatch_fleet.FleetCampaignMode,
    leave_remaining: int,
    campaign_blocked: Mapping[str, str],
    order_override: Sequence[str] | None,
    station_skips: Mapping[str, str],
    explicit_stories: tuple[str, ...] | None,
    policy_flags: dict[str, object] | None,
    max_in_flight: int | None,
    retry_environment_blocks: bool,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    harness: HarnessPort,
    mint_wave_id: Callable[[], str],
    followups: Sequence[dispatch_fleet.FollowupCandidate] = (),
) -> StationCyclePlan:
    """One station's per-cycle queue computation -- READ-ONLY (Story 65.1).

    The body ``execute_fleet_cycle`` used to hold inline, moved verbatim: the
    tracked-ledger read, ``station_backlog`` with the queue file's override and
    Deps, ``station_finalize_pending_story``, ``_station_blocked_map``,
    ``plan_station_queue`` and, in parallel mode, ``ordered_ready_backlog`` and
    ``build_wave_batch``. ``factory drain --plan`` calls this same function, so
    the plan cannot drift from the drain. It reads (ledger, journals, git,
    process liveness) and never writes: the wave id is minted through
    ``mint_wave_id`` only when a wave is actually built, and journaling that
    wave stays the caller's.

    ``followups`` (Story 73.2, CAP-281) are this station's selected follow-up reviews
    (``plan_followup_reviews``): each is appended to the queue AFTER the implementable backlog, in the order
    given (newest landing first), before ``plan_station_queue`` runs -- so mode accounting, declared skips, the
    blocked map and campaign blocks apply to it as to any story. Never under ``explicit_stories``
    (``--stories`` is unchanged)."""
    ledger_path = dispatch_fleet.station_ledger_path(repo_root, slug)
    try:
        statuses = _station_ledger_statuses(harness=harness, vcs=vcs, repo_root=repo_root, ledger_path=ledger_path)
    except (HarnessError, OSError, ValueError) as exc:
        return StationCyclePlan(slug=slug, ledger_path=ledger_path, ledger_error=str(exc))

    backlog = (
        dispatch_fleet.explicit_story_backlog(statuses, explicit_stories)
        if explicit_stories is not None
        else dispatch_fleet.station_backlog(
            statuses,
            order_override=order_override,
            deps_by_story=(None if order_override else _load_station_story_deps(fs, repo_root, slug)),
        )
    )
    followup_stories: tuple[str, ...] = ()
    if explicit_stories is None and followups:
        followup_stories = dispatch_fleet.followup_backlog_entries(followups, statuses, backlog)
        backlog = backlog + followup_stories
    effective_policy = _compose_policy(slug, flags=policy_flags)
    # Story 50.1 Part A: the ~45 s window between session exit and ledger
    # promotion. Reported IN_FLIGHT (deliberately absent from
    # TERMINAL_STATION_STATUSES), so this station provisions nothing this
    # cycle and the campaign chains its next ready story on the following
    # one instead of re-dispatching or blocking on the story it just landed.
    finalize_pending = station_finalize_pending_story(
        fs=fs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        backlog=backlog,
        effective_policy=effective_policy,
    )
    base = StationCyclePlan(
        slug=slug,
        ledger_path=ledger_path,
        statuses=tuple(statuses),
        backlog=backlog,
        followup_stories=followup_stories,
        effective_policy=effective_policy,
        station_skips=station_skips,
    )
    if finalize_pending is not None:
        return replace(base, finalize_pending=finalize_pending)
    blocked, block_classes = _station_blocked_map(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        backlog=backlog,
        configured_skips=station_skips,
        campaign_blocked=campaign_blocked,
        effective_policy=effective_policy,
        followups=frozenset(followup_stories),
    )
    queue = dispatch_fleet.plan_station_queue(
        slug=slug,
        backlog=backlog,
        mode=mode,
        leave_remaining=leave_remaining,
        blocked=blocked,
        block_classes=block_classes,
        retry_environment_blocks=retry_environment_blocks,
        declared_skips=station_skips,
    )
    base = replace(base, blocked=blocked, block_classes=block_classes, queue=queue)
    if queue.outcome is dispatch_fleet.StationQueueOutcome.BLOCKED or queue.next_story is None:
        return base

    parallel_cap = resolve_max_parallel(
        effective_policy,
        cli_override=max_in_flight,
        policy_flags=policy_flags,
    )
    base = replace(base, parallel_cap=parallel_cap)
    if parallel_cap <= 1:
        return replace(base, stories_to_dispatch=(queue.next_story,))

    live_stories = _live_dispatch_story_keys(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        effective_policy=effective_policy,
    )
    if live_stories:
        return replace(base, live_stories=live_stories)
    deps_graph = _load_station_deps_graph(repo_root, slug)
    ready = dispatch_fleet.ordered_ready_backlog(backlog, statuses, deps_graph)
    eligible = tuple(story for story in ready if story not in blocked and story not in station_skips)
    surfaces: dict[str, tuple[str, ...] | None] = {}
    for story in eligible:
        spec_path = dispatch_core.resolve_story_spec_path(repo_root, slug, story)
        if spec_path is None:
            surfaces[story] = None
            continue
        try:
            spec_text = spec_path.read_text(encoding="utf-8")
        except OSError:
            surfaces[story] = None
            continue
        try:
            surfaces[story] = _effective_surface_for_spec(
                spec_text=spec_text,
                story_key=normalize(story),
                slug=slug,
                effective_policy=effective_policy,
            )
        except ValueError:
            surfaces[story] = None
    wave = dispatch_fleet.build_wave_batch(
        wave_id=mint_wave_id(),
        ready=eligible,
        cap=parallel_cap,
        surfaces=surfaces,
        deps_graph=deps_graph,
    )
    return replace(
        base,
        deps_graph=deps_graph,
        ready=ready,
        surfaces=surfaces,
        wave=wave,
        stories_to_dispatch=wave.members,
    )


def wave_held_stories(cycle: StationCyclePlan) -> tuple[str, ...]:
    """Every story a parallel wave holds out of this cycle (pure, Story 81.1).

    Each story the wave itself refused, and the queue head when the wave neither
    admitted nor refused it (its Deps are not all done, so it never reached the
    ready set) -- the stories ``factory drain --plan`` lists as ``held`` and the
    cycle's ``held`` result and ``MRS-DRAIN-016`` name."""
    wave = cycle.wave
    if wave is None:
        return ()
    held = [refused.story for refused in wave.refused]
    head = cycle.queue.next_story if cycle.queue is not None else None
    if head is not None and head not in cycle.stories_to_dispatch and head not in held:
        held.insert(0, head)
    return tuple(held)


def skip_basis(
    *,
    story: str,
    reason: str,
    station_skips: Mapping[str, str],
    block_classes: Mapping[str, dispatch_fleet.FleetBlockClass],
    mode: dispatch_fleet.FleetCampaignMode,
) -> str:
    """Why ``plan_station_queue`` stepped past ``story`` -- the wording the
    cycle's ``MRS-DRAIN-004`` names and ``factory drain --plan`` reports."""
    if story in station_skips:
        return "declared skip policy"
    if dispatch_fleet.is_harness_done_advance_reason(reason):
        return "harness-done CAP-4 (MRS-DISP-040); remaining backlog continues"
    if reason.startswith(dispatch_fleet.ALREADY_LANDED_ADVANCE_PREFIX):
        # Story 50.1 Part B: named for what it is -- an advance past
        # work that already landed -- never mislabelled "blocked".
        return "already landed (Story 50.1); remaining backlog continues"
    if block_classes.get(story) is dispatch_fleet.FleetBlockClass.ENVIRONMENT:
        return "environment-classified block"
    return f"blocked, and {mode.value} skips past it"


def execute_fleet_cycle(
    *,
    repo_root: Path,
    mode: dispatch_fleet.FleetCampaignMode,
    leave_remaining: int,
    campaign_blocked: dict[str, dict[str, str]],
    fs: FsPort,
    vcs: CommittingVcs,
    build_harness: BuildHarnessPort,
    process: ProcessPort,
    harness: HarnessPort,
    station: str | None = None,
    explicit_stories: tuple[str, ...] | None = None,
    policy_flags: dict[str, object] | None = None,
    max_in_flight: int | None = None,
    retry_environment_blocks: bool = False,
    followups_launched: frozenset[tuple[str, StoryKey]] = frozenset(),
) -> FleetCycleReport:
    """One fleet-drain cycle: plan every station, dispatch the eligible ones.

    Story 22.11 (FR-193 CAP-10): ``station``, when given, restricts this
    cycle to exactly one station's own tracked backlog -- every other
    station's ledger is never even read, so it is provably untouched by
    this invocation. ``explicit_stories``, when given (only meaningful
    alongside ``station``), replaces that one station's ledger-derived
    backlog with the caller's own ordered sequence (re-filtered to
    not-yet-``done`` every cycle) instead of reordering the full backlog
    the way ``order_override`` does.

    Story 73.2 (CAP-281): ``followups_launched`` is every ``(station, story)`` follow-up review the campaign's
    earlier cycles launched (``_followups_launched_from_journal``). With it, ``plan_followup_reviews`` decides
    which open ``DW-FRR`` rows this cycle queues after each station's backlog -- the per-campaign cap minus
    those already launched -- and the cycle records the follow-ups it launches on the station result, which is
    what the next cycle's count is folded from. ``explicit_stories`` (``--stories``) queues none.
    """
    if explicit_stories is not None and station is None:
        # Story 22.11 patch pass (review finding): `explicit_stories` is
        # only meaningful scoped to one station -- without this guard, a
        # future caller passing it alone would silently apply the caller's
        # sequence as every station's own backlog instead of just one.
        raise ValueError("explicit_stories requires station")
    findings: list[Finding] = []
    results: list[dispatch_fleet.StationCycleResult] = []
    overrides, configured_skips, config_findings = _read_fleet_queue_config(fs, repo_root)
    findings.extend(config_findings)

    cycle_slugs = resolve_cycle_slugs(repo_root, station)
    if cycle_slugs.finding is not None:
        findings.append(cycle_slugs.finding)
        if cycle_slugs.unknown_station:
            return FleetCycleReport(
                results=(),
                findings=tuple(findings),
                data={
                    "mode": mode.value,
                    "stations": [],
                    "remaining_total": 0,
                    "dispatched": [],
                    "unresolved": [],
                },
            )
    followup_plan = FollowupPlan()
    if explicit_stories is None and cycle_slugs.slugs:
        followup_plan = plan_followup_reviews(
            repo_root=repo_root,
            slugs=cycle_slugs.slugs,
            vcs=vcs,
            launched=followups_launched,
            policy_flags=policy_flags,
        )
        findings.extend(followup_plan.findings)
    for slug in cycle_slugs.slugs:
        # Story 65.1: the per-station queue computation lives in ONE read-only
        # planner that `factory drain --plan` calls too; everything below
        # (every finding, every result, every writer) stays here, in order.
        cycle = plan_station_cycle(
            repo_root=repo_root,
            slug=slug,
            mode=mode,
            leave_remaining=leave_remaining,
            campaign_blocked=campaign_blocked.get(slug, {}),
            order_override=overrides.get(slug),
            station_skips=configured_skips.get(slug, {}),
            explicit_stories=explicit_stories,
            policy_flags=policy_flags,
            max_in_flight=max_in_flight,
            retry_environment_blocks=retry_environment_blocks,
            fs=fs,
            vcs=vcs,
            process=process,
            harness=harness,
            mint_wave_id=lambda: _mint_wave_id(slug),
            followups=followup_plan.selected.get(slug, ()),
        )
        if cycle.ledger_error is not None:
            findings.append(
                Finding(
                    code="MRS-DRAIN-003",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: cannot read the tracked ledger at "
                        f"{cycle.ledger_path}: {cycle.ledger_error} -- station excluded from this "
                        "campaign (its backlog is unknown, never assumed empty)"
                    ),
                    path=str(cycle.ledger_path),
                )
            )
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.StationCycleStatus.LEDGER_UNREADABLE,
                    remaining=0,
                    detail=cycle.ledger_error,
                )
            )
            continue

        backlog = cycle.backlog
        effective_policy = cycle.effective_policy
        assert effective_policy is not None
        station_skips = cycle.station_skips
        block_classes = cycle.block_classes
        if cycle.finalize_pending is not None:
            pending_story, pending_evidence = cycle.finalize_pending
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.StationCycleStatus.IN_FLIGHT,
                    remaining=len(backlog),
                    story=pending_story,
                    detail=pending_evidence,
                )
            )
            findings.append(
                Finding(
                    code="MRS-DRAIN-006",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: no dispatch this cycle -- story "
                        f"{pending_story!r} is finalizing: {pending_evidence}"
                    ),
                )
            )
            continue
        plan = cycle.queue
        assert plan is not None
        for story, reason in plan.skipped:
            basis = skip_basis(
                story=story,
                reason=reason,
                station_skips=station_skips,
                block_classes=block_classes,
                mode=mode,
            )
            findings.append(
                Finding(
                    code="MRS-DRAIN-004",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: skipping story {story!r} "
                        f"({basis}) -- {reason}. It stays in the backlog "
                        "and is never auto-retried."
                    ),
                )
            )
        if plan.outcome is dispatch_fleet.StationQueueOutcome.BLOCKED:
            blocked_class = (
                block_classes.get(plan.blocked_story or "")
                if plan.blocked_story
                else dispatch_fleet.FleetBlockClass.STORY
            )
            retry_hint = (
                f"re-run with --mode "
                f"{dispatch_fleet.FleetCampaignMode.SKIP_ON_BLOCKED.value} "
                "or --retry-environment-blocks"
                if blocked_class is dispatch_fleet.FleetBlockClass.ENVIRONMENT
                else (
                    f"re-run with --mode "
                    f"{dispatch_fleet.FleetCampaignMode.SKIP_ON_BLOCKED.value} "
                    "does not skip genuine story failures -- manual override "
                    "required"
                )
            )
            findings.append(
                Finding(
                    code="MRS-DRAIN-005",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: story {plan.blocked_story!r} is "
                        f"blocked ({blocked_class.value}) -- "
                        f"{plan.blocked_reason}. It stays in the "
                        "backlog, is never auto-retried, and is never forced "
                        f"past; {retry_hint} to move on to this station's "
                        "next story."
                    ),
                )
            )
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.StationCycleStatus.BLOCKED,
                    remaining=len(backlog),
                    story=plan.blocked_story,
                    detail=plan.blocked_reason,
                    skipped=plan.skipped,
                )
            )
            continue
        if plan.next_story is None:
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.idle_station_status(plan.outcome),
                    remaining=len(backlog),
                    skipped=plan.skipped,
                )
            )
            continue

        parallel_cap = cycle.parallel_cap
        stories_to_dispatch = cycle.stories_to_dispatch
        wave_detail: str | None = None
        if parallel_cap > 1:
            if cycle.live_stories:
                results.append(
                    dispatch_fleet.StationCycleResult(
                        slug=slug,
                        status=dispatch_fleet.StationCycleStatus.IN_FLIGHT,
                        remaining=len(backlog),
                        story=cycle.live_stories[0],
                        detail=(
                            f"wave in flight: {', '.join(cycle.live_stories)} "
                            "(waiting for terminal outcomes before next batch)"
                        ),
                        skipped=plan.skipped,
                    )
                )
                findings.append(
                    Finding(
                        code="MRS-DRAIN-006",
                        severity=Severity.WARN,
                        message=(
                            f"station {slug!r}: no dispatch this cycle -- "
                            f"waiting on in-flight wave member(s) "
                            f"{', '.join(cycle.live_stories)!r}"
                        ),
                    )
                )
                continue
            wave = cycle.wave
            assert wave is not None
            if wave.members:
                _journal_dispatch_wave(fs, repo_root, slug, wave, surfaces=cycle.surfaces)
            for ref in wave.refused:
                overlap = f" (overlap with {ref.overlap_with}: {', '.join(ref.paths)})" if ref.overlap_with else ""
                findings.append(
                    Finding(
                        code="MRS-DRAIN-016",
                        severity=Severity.WARN,
                        message=(f"station {slug!r}: wave {wave.wave_id} refused {ref.story!r}: {ref.reason}{overlap}"),
                    )
                )
            if wave.members:
                wave_detail = f"wave {wave.wave_id}: {', '.join(wave.members)} (max_parallel={parallel_cap})"

        if not stories_to_dispatch:
            # Story 81.1: the queue walk named an eligible story and the wave then held every candidate out.
            held_wave = cycle.wave
            assert held_wave is not None
            refused_stories = {ref.story for ref in held_wave.refused}
            held_detail: list[str] = []
            for held_story in wave_held_stories(cycle):
                reason = dispatch_prelaunch.held_reason(held_story, cycle.statuses, cycle.deps_graph or {}, held_wave)
                held_detail.append(f"{held_story}: {reason}")
                if held_story in refused_stories:
                    continue  # the refusal loop above already named it
                findings.append(
                    Finding(
                        code="MRS-DRAIN-016",
                        severity=Severity.WARN,
                        message=f"station {slug!r}: wave {held_wave.wave_id} holds {held_story!r} out: {reason}",
                    )
                )
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.idle_station_status(plan.outcome),
                    remaining=len(backlog),
                    story=plan.next_story,
                    detail="; ".join(held_detail),
                    skipped=plan.skipped,
                )
            )
            continue

        dispatched_any = False
        in_flight_any = False
        refused_any = False
        followup_dispatched: list[str] = []
        last_detail: str | None = wave_detail
        primary_story = stories_to_dispatch[0]
        pending = list(stories_to_dispatch)
        seen_dispatch: set[str] = set()
        member_outcomes: list[dispatch_fleet.MemberOutcome] = []
        while pending:
            story = pending.pop(0)
            if story in seen_dispatch:
                continue
            seen_dispatch.add(story)
            try:
                attempt = dispatch_once(
                    slug=slug,
                    story=story,
                    fs=fs,
                    vcs=vcs,
                    build_harness=build_harness,
                    process=process,
                    policy_flags=policy_flags,
                    parallel_dispatch=parallel_cap > 1,
                )
            except (VcsCommandError, FsError, ProcessError, OSError, ValueError) as exc:
                reason = f"dispatch raised {type(exc).__name__}: {exc}"
                findings.append(
                    Finding(
                        code="MRS-DRAIN-011",
                        severity=Severity.ERROR,
                        message=(
                            f"station {slug!r}: dispatching {story!r} "
                            f"failed unexpectedly -- {reason}. The station is "
                            "left in backlog and the rest of the fleet continues."
                        ),
                    )
                )
                campaign_blocked.setdefault(slug, {})[story] = reason
                refused_any = True
                last_detail = reason
                member_outcomes.append(
                    _member_outcome(
                        repo_root=repo_root,
                        slug=slug,
                        story=story,
                        status=dispatch_fleet.StationCycleStatus.REFUSED,
                        detail=reason,
                        verify_commands=effective_policy.verify_commands.value,
                    )
                )
                continue
            status, detail, attempt_findings = _classify_attempt(slug, story, attempt)
            findings.extend(attempt_findings)
            member_outcomes.append(
                _member_outcome(
                    repo_root=repo_root,
                    slug=slug,
                    story=story,
                    status=status,
                    detail=detail,
                    verify_commands=effective_policy.verify_commands.value,
                )
            )
            if status is dispatch_fleet.StationCycleStatus.REFUSED:
                campaign_blocked.setdefault(slug, {})[story] = detail or "dispatch refused"
                refused_any = True
                if parallel_cap <= 1 and dispatch_fleet.is_harness_done_advance_reason(detail or ""):
                    follow_blocked, follow_classes = _station_blocked_map(
                        fs=fs,
                        vcs=vcs,
                        process=process,
                        repo_root=repo_root,
                        slug=slug,
                        backlog=backlog,
                        configured_skips=station_skips,
                        campaign_blocked=campaign_blocked.get(slug, {}),
                        effective_policy=effective_policy,
                        followups=frozenset(cycle.followup_stories),
                    )
                    follow = dispatch_fleet.plan_station_queue(
                        slug=slug,
                        backlog=backlog,
                        mode=mode,
                        leave_remaining=leave_remaining,
                        blocked=follow_blocked,
                        block_classes=follow_classes,
                        retry_environment_blocks=retry_environment_blocks,
                        declared_skips=station_skips,
                    )
                    if follow.next_story and follow.next_story not in seen_dispatch:
                        pending.append(follow.next_story)
                        findings.append(
                            Finding(
                                code="MRS-DRAIN-004",
                                severity=Severity.WARN,
                                message=(
                                    f"station {slug!r}: skipping story {story!r} "
                                    "(harness-done CAP-4 (MRS-DISP-040); "
                                    "remaining backlog continues) -- "
                                    f"{detail}. Dispatching {follow.next_story!r} "
                                    "this cycle."
                                ),
                            )
                        )
            elif status is dispatch_fleet.StationCycleStatus.DISPATCHED:
                dispatched_any = True
                if story in cycle.followup_stories:
                    followup_dispatched.append(story)
            elif status is dispatch_fleet.StationCycleStatus.IN_FLIGHT:
                in_flight_any = True
            if detail:
                last_detail = detail

        if dispatched_any:
            cycle_status = dispatch_fleet.StationCycleStatus.DISPATCHED
        elif in_flight_any:
            cycle_status = dispatch_fleet.StationCycleStatus.IN_FLIGHT
        elif refused_any:
            cycle_status = dispatch_fleet.StationCycleStatus.REFUSED
        else:
            cycle_status = dispatch_fleet.StationCycleStatus.IN_FLIGHT
        # Story 82.10: the aggregate predicate is the PRIMARY member's own -- the old `last_detail` + `primary_story`
        # pairing described another story's gate once a second member refused. A REFUSED station refused every
        # attempted member, the primary (always attempted first) included.
        refuse_predicate_payload: dict[str, str] | None = None
        if cycle_status is dispatch_fleet.StationCycleStatus.REFUSED and member_outcomes:
            refuse_predicate_payload = member_outcomes[0].refuse_predicate
        results.append(
            dispatch_fleet.StationCycleResult(
                slug=slug,
                status=cycle_status,
                remaining=len(backlog),
                story=primary_story,
                detail=last_detail,
                skipped=plan.skipped,
                refuse_predicate=refuse_predicate_payload,
                followup_reviews=tuple(followup_dispatched),
                members=tuple(member_outcomes) if len(member_outcomes) > 1 else (),
            )
        )

    unresolved = dispatch_fleet.unresolved_stations(results)
    data: dict[str, object] = {
        "mode": mode.value,
        "stations": [result.to_payload() for result in results],
        "remaining_total": sum(result.remaining for result in results),
        "dispatched": [
            result.slug for result in results if result.status is dispatch_fleet.StationCycleStatus.DISPATCHED
        ],
        # What `complete` does NOT mean: `complete` is "this campaign can do
        # nothing more", and these stations still have work marshal could not
        # take (unreadable ledger, blocked head story, everything skipped,
        # `leave_one`'s deliberate tail, a parallel wave that held every candidate).
        "unresolved": [{"station": r.slug, "status": r.status.value, "remaining": r.remaining} for r in unresolved],
    }
    return FleetCycleReport(results=tuple(results), findings=tuple(findings), data=data)


def _campaign_blocked_from_journal(
    fs: FsPort, run_dir: Path, run_id: str
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, dispatch_re_preflight.RefusePredicate]]]:
    """Rebuild campaign blocks and last refuse predicates from the journal.

    Campaign state lives in the journal (the Spec's in-repo store), never in
    a driver process's memory: each cycle runs in its own process under the
    detached supervisor, and without this a station whose queued story was
    refused for a non-liveness reason (no tracked spec, an unlaunchable
    harness) would be retried on every single tick forever.

    Story 82.10: a station row that carries per-member outcomes (a wave attempted more than one story) yields a
    block and its refuse predicate for every REFUSED member, whatever the row's aggregate status -- a refused
    primary beside a dispatched sibling is still blocked next cycle. A row without members is its own outcome.
    """
    blocked: dict[str, dict[str, str]] = {}
    predicates: dict[str, dict[str, dispatch_re_preflight.RefusePredicate]] = {}
    folded = _fold_campaign_journal(fs, run_dir)
    if folded is None:
        return blocked, predicates
    for entry in folded.by_kind(dispatch_fleet.KIND_FLEET_CYCLE):
        if entry.run_id != run_id or entry.phase != Phase.OUTCOME:
            continue
        stations = entry.payload.get("stations")
        if not isinstance(stations, list):
            continue
        for row in stations:
            if not isinstance(row, dict):
                continue
            slug = row.get("station")
            if not isinstance(slug, str):
                continue
            # Story 82.10: a row that carries member outcomes is folded from them alone (its aggregate `story` is
            # the primary and its `detail` the last member's, so reading both would pin one story's block to another
            # story's detail); an older row, or a single-story one, is its own one outcome. Either way every
            # REFUSED outcome is a block, whatever the station's aggregate status.
            raw_members = row.get(dispatch_fleet.MEMBERS_PAYLOAD_KEY)
            members = [m for m in raw_members if isinstance(m, dict)] if isinstance(raw_members, list) else []
            for outcome in members or [row]:
                if outcome.get("status") != dispatch_fleet.StationCycleStatus.REFUSED.value:
                    continue
                story = outcome.get("story")
                if not isinstance(story, str):
                    continue
                detail = outcome.get("detail")
                blocked.setdefault(slug, {})[story] = (
                    detail if isinstance(detail, str) and detail else "dispatch refused"
                )
                predicate = _predicate_from_payload(outcome.get("refuse_predicate"))
                if predicate is not None:
                    predicates.setdefault(slug, {})[story] = predicate
    return blocked, predicates


def _followups_launched_from_journal(fs: FsPort, run_dir: Path, run_id: str) -> frozenset[tuple[str, StoryKey]]:
    """Every ``(station, story)`` follow-up review this campaign's earlier cycles launched (Story 73.2, CAP-281).

    Folded from the campaign journal's fleet-cycle OUTCOME rows the way ``_campaign_blocked_from_journal`` folds
    its blocks -- campaign state lives in the journal, never in a process, so the per-campaign cap
    ``dispatch.max_followup_reviews_per_campaign`` holds across every cycle of one campaign (each supervised
    tick is its own process). An absent or unreadable journal is no launches."""
    folded = _fold_campaign_journal(fs, run_dir)
    if folded is None:
        return frozenset()
    rows: list[object] = []
    for entry in folded.by_kind(dispatch_fleet.KIND_FLEET_CYCLE):
        if entry.run_id != run_id or entry.phase != Phase.OUTCOME:
            continue
        stations = entry.payload.get("stations")
        if isinstance(stations, list):
            rows.extend(stations)
    return dispatch_fleet.followups_launched(rows)


def _fold_campaign_journal(fs: FsPort, run_dir: Path) -> FoldResult | None:
    """The campaign journal folded, sidecars resolved, or ``None`` when it is absent or unreadable."""
    try:
        text = fs.read_text(run_dir / _JOURNAL_FILENAME)
    except FsError, ValueError:
        return None
    if text is None:
        return None
    lines = text.split("\n")
    # AD-30 sidecars are NOT optional on this read side. A cycle payload
    # carries one row per station plus every skip reason and refusal detail,
    # and eight stations cross `SIDECAR_THRESHOLD_BYTES` (4 KiB) well before
    # a real campaign finishes -- at which point `prepare_for_write` writes
    # the payload to `blobs/` and leaves a `{"sidecar_ref": ...}` pointer.
    # Folding without resolving those pointers quarantines the very entries
    # this function exists to read, so a station refused for a non-liveness
    # reason (no tracked spec) would be silently retried on every 60 s tick
    # forever and the campaign could never report itself complete.
    # Deferred import, matching `cli/deploy.py`'s own `.gate` convention: a
    # module-level `from .gate import ...` here would be load-order fragile
    # (gate -> spin -> dispatch). The helper is reused rather than re-copied.
    from .gate import _sidecar_refs_for_fold

    sidecars: dict[str, str | None] = {}
    for ref in _sidecar_refs_for_fold(lines):
        try:
            sidecars[ref] = fs.read_text(run_dir / ref)
        except FsError, ValueError:
            sidecars[ref] = None
    return fold(lines, sidecars=sidecars)


def _journal_fleet_cycle(
    fs: FsPort,
    run_dir: Path,
    run_id: str,
    report: FleetCycleReport,
    findings: list[Finding],
) -> None:
    """Journal one cycle's intent/outcome pair under ``pyforge-marshal``.

    ``writer_id`` carries this process's pid, so successive supervised cycles
    (each its own process, all sharing one campaign run id) never collide on
    a journal entry id.
    """
    writer_id = f"fleet-drain-{os.getpid()}"
    intent = build_entry(
        id=JournalEntryId(writer_id, 0),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_fleet.KIND_FLEET_CYCLE,
        phase=Phase.INTENT,
        payload={"mode": report.data.get("mode")},
    )
    outcome = build_entry(
        id=JournalEntryId(writer_id, 1),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_fleet.KIND_FLEET_CYCLE,
        phase=Phase.OUTCOME,
        intent_id=intent.id,
        payload={
            "ok": True,
            "complete": report.complete,
            "stations": [result.to_payload() for result in report.results],
        },
    )
    try:
        _append_entry(fs, run_dir, intent, fsync=True)
        _append_entry(fs, run_dir, outcome, fsync=False)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DRAIN-009",
                severity=Severity.WARN,
                message=f"the fleet cycle ran but could not be journaled: {exc}",
            )
        )


def _spawn_campaign_supervisor(
    *,
    process: ProcessPort,
    repo_root: Path,
    run_dir: Path,
    run_id: str,
    mode: dispatch_fleet.FleetCampaignMode,
    leave_remaining: int,
    max_cycles: int,
    tick_seconds: int,
    station: str | None = None,
    stories: tuple[str, ...] | None = None,
    harness: str | None = None,
    max_in_flight: int | None = None,
    retry_environment_blocks: bool = False,
) -> int:
    """Detach the campaign supervisor -- the loop that chains next stories.

    Mirrors the per-story dispatch supervisor's own shape (AD-22/Story 3.4):
    the operator's foreground invocation runs ONE cycle and returns, and all
    waiting lives in ``pyforge.marshal.dispatch_fleet_supervisor`` -- so the
    ~600 s watchdog that killed the hand ritual's busy-waiting parent has
    nothing to kill here. Raises ``ProcessError`` when the spawn fails; the
    cycle that already ran still stands.

    Story 22.11 (FR-193 CAP-10): ``station``/``stories`` are threaded
    through so every SUPERVISED tick re-runs the SAME scoped/sequenced
    campaign -- omitting them here would silently widen a station-scoped or
    explicit-sequence campaign back to fleet-wide/ledger-order on its very
    first re-tick.

    Story 81.3: ``retry_environment_blocks`` rides the same way, as a trailing
    ``--retry-environment-blocks`` flag (a boolean has no useful empty-string
    positional form) appended only when true -- the default argv is
    byte-identical. Without it a campaign launched with the flag skips an
    environment-classified block in its foreground cycle only, and every
    supervised tick after it stops on the same block (MRS-DRAIN-005).
    """
    argv = [
        sys.executable,
        "-m",
        "pyforge.marshal.dispatch_fleet_supervisor",
        str(repo_root),
        run_id,
        mode.value,
        str(leave_remaining),
        str(max_cycles),
        str(tick_seconds),
        station or "",
        ",".join(stories) if stories else "",
        harness or "",
        str(max_in_flight) if max_in_flight is not None else "",
    ]
    if retry_environment_blocks:
        argv.append("--retry-environment-blocks")
    return process.spawn_detached(
        argv,
        cwd=repo_root,
        log_path=run_dir / _FLEET_SUPERVISOR_LOG_FILENAME,
    )


def run_fleet_drain(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    vcs: CommittingVcs | None = None,
    build_harness: BuildHarnessPort | None = None,
    process: ProcessPort | None = None,
    harness: HarnessPort | None = None,
    context: MarshalContext | None = None,
) -> int:
    """``marshal factory drain`` -- the one documented fleet-drain command.

    Runs exactly ONE cycle and returns; unless ``--once`` is given (or the
    campaign is already complete) it then detaches
    ``pyforge.marshal.dispatch_fleet_supervisor``, which re-runs this same
    command on a tick until the campaign completes. Nothing here waits.

    Story 65.1 (CAP-274): with ``--plan`` it answers "what would this drain
    do?" instead -- ``cli/drain_plan.py`` computes each station's queue through
    ``plan_station_cycle`` (the very code a cycle runs) and reports every
    refusal decidable before launch, before anything below is minted: no run
    directory, lock, journal entry, worktree or supervisor.
    """
    del context
    # Function-local, the `cli/gate.py` precedent: `drain_plan` imports this
    # module's planner, so a module-level import would be load-order fragile.
    from .drain_plan import plan_usage_error, run_drain_plan

    usage_error = plan_usage_error(args)
    if usage_error is not None:
        print(f"marshal factory drain: error: {usage_error}", file=sys.stderr)
        return EXIT_USAGE
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    build_harness = build_harness if build_harness is not None else BmadBuildHarness()
    process = process if process is not None else PosixProcess()
    harness = harness if harness is not None else resolve_loop_runner()

    findings: list[Finding] = []
    data: dict[str, object] = {}

    try:
        mode = dispatch_fleet.parse_campaign_mode(getattr(args, "mode", None))
    except dispatch_fleet.InvalidCampaignModeError as exc:
        findings.append(Finding(code="MRS-DRAIN-001", severity=Severity.ERROR, message=str(exc)))
        return _emit(args, data, findings, command="factory drain")
    data["mode"] = mode.value
    if bool(getattr(args, "plan", False)):
        data["plan"] = True

    leave_remaining = max(0, int(getattr(args, "leave_remaining", 1) or 0))
    once = bool(getattr(args, "once", False))
    # A NEGATIVE ceiling is refused rather than clamped: `max(0, -1)` is 0,
    # and 0 means UNBOUNDED here -- silently the opposite of what the
    # operator asked for.
    raw_max_cycles = int(getattr(args, "max_cycles", 0) or 0)
    if raw_max_cycles < 0:
        findings.append(
            Finding(
                code="MRS-DRAIN-001",
                severity=Severity.ERROR,
                message=(
                    f"--max-cycles must be >= 0, got {raw_max_cycles} "
                    "(0 means 'until the campaign completes', so a negative "
                    "value cannot be clamped to it without inverting the ask)"
                ),
            )
        )
        return _emit(args, data, findings, command="factory drain")
    max_cycles = raw_max_cycles
    tick_seconds = max(1, int(getattr(args, "tick_seconds", _FLEET_TICK_SECONDS) or 1))

    try:
        repo_root = vcs.repo_common_root(Path.cwd())
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DRAIN-002",
                severity=Severity.ERROR,
                message=f"cannot resolve repository root: {exc}",
            )
        )
        return _emit(args, data, findings, command="factory drain")

    # Story 22.11 (FR-193 CAP-10): --station restricts this campaign to one
    # station's own tracked backlog (unknown-station refusal lives inside
    # `execute_fleet_cycle`, which re-checks it every cycle -- cheap and
    # correct on every supervised tick, not just the first). --stories
    # names an explicit ordered sequence on that station instead of its
    # ledger order; it REQUIRES --station, since a sequence names exactly
    # one station's backlog.
    raw_station = getattr(args, "station", None)
    station: str | None = None
    if raw_station is not None and str(raw_station).strip():
        station = dispatch_fleet.normalize_station_slug(str(raw_station))
        data["station"] = station

    raw_stories = getattr(args, "stories", None)
    explicit_stories: tuple[str, ...] | None = None
    if raw_stories:
        explicit_stories = dispatch_fleet.parse_story_sequence(raw_stories)
        if not explicit_stories:
            findings.append(
                Finding(
                    code="MRS-DISP-032",
                    severity=Severity.ERROR,
                    message="--stories must name at least one non-blank story key",
                )
            )
            return _emit(args, data, findings, command="factory drain")
        data["stories"] = list(explicit_stories)
        if station is None:
            findings.append(
                Finding(
                    code="MRS-DRAIN-014",
                    severity=Severity.ERROR,
                    message=(
                        "--stories requires --station -- an explicit "
                        "sequence names exactly one station's backlog, "
                        "never the whole fleet's"
                    ),
                )
            )
            return _emit(args, data, findings, command="factory drain")

    raw_campaign = getattr(args, "campaign", None)
    if raw_campaign is not None and not _is_safe_campaign_id(str(raw_campaign)):
        # `--campaign` names a DIRECTORY under the campaign runs tree, so an
        # unvalidated value escapes it (`--campaign ../../x`) and `ensure_dir`
        # would happily create it.
        findings.append(
            Finding(
                code="MRS-DRAIN-001",
                severity=Severity.ERROR,
                message=(
                    f"malformed campaign id {raw_campaign!r}: expected the "
                    "run-id shape marshal mints (letters, digits, '.', '_', "
                    "'-'), never a path"
                ),
            )
        )
        return _emit(args, data, findings, command="factory drain")

    if explicit_stories is not None:
        # First cycle of a FRESH campaign only: every named key must
        # already be eligible on the station's tracked backlog before
        # anything is minted or provisioned. A later supervised tick
        # always passes --campaign naming a run this SAME flow already
        # minted, so it is deliberately NOT re-validated then -- a key
        # that legitimately landed (flipped to `done`) between cycles
        # must not be misread as an unknown/invalid one;
        # `explicit_story_backlog`'s own per-cycle re-derivation already
        # drops it correctly. An operator-typed `--campaign` id that
        # never actually ran (no run directory on disk) is still a first
        # launch in every way that matters here, so it is validated like
        # one rather than trusted as a resume (review finding, Story
        # 22.11 patch pass).
        is_resumed = raw_campaign is not None and fs.is_dir(dispatch_fleet.fleet_run_dir(repo_root, str(raw_campaign)))
        if not is_resumed:
            assert station is not None  # enforced above: --stories requires --station
            # Check station liveness BEFORE touching the filesystem for its
            # ledger -- an unknown `--station` must surface as MRS-DRAIN-013
            # ("not among the live stations") rather than as a misleading
            # MRS-DRAIN-015 ledger-read failure (review finding, Story 22.11
            # patch pass; `execute_fleet_cycle` re-checks this too, cheaply,
            # on every cycle).
            live_slugs = dispatch_fleet.fleet_station_slugs(dispatch_core.list_station_slugs(repo_root))
            if station not in live_slugs:
                findings.append(
                    Finding(
                        code="MRS-DRAIN-013",
                        severity=Severity.ERROR,
                        message=(
                            f"unknown station {station!r}: not among the live "
                            f"pyforge stations ({', '.join(live_slugs) or 'none found'})"
                        ),
                    )
                )
                return _emit(args, data, findings, command="factory drain")
            ledger_path = dispatch_fleet.station_ledger_path(repo_root, station)
            try:
                statuses = _station_ledger_statuses(
                    harness=harness, vcs=vcs, repo_root=repo_root, ledger_path=ledger_path
                )
            except (HarnessError, OSError, ValueError) as exc:
                findings.append(
                    Finding(
                        code="MRS-DRAIN-015",
                        severity=Severity.ERROR,
                        message=(
                            f"station {station!r}: cannot read the tracked "
                            f"ledger at {ledger_path}: {exc} -- nothing was "
                            "provisioned"
                        ),
                        path=str(ledger_path),
                    )
                )
                return _emit(args, data, findings, command="factory drain")
            backlog = dispatch_fleet.station_backlog(statuses)
            unresolved = dispatch_fleet.unresolved_story_sequence_keys(explicit_stories, backlog)
            if unresolved:
                findings.append(
                    Finding(
                        code="MRS-DISP-032",
                        severity=Severity.ERROR,
                        message=(
                            f"refusing dispatch: --stories names key(s) unknown "
                            f"or already done on station {station!r}'s tracked "
                            f"backlog: {', '.join(unresolved)} -- nothing was "
                            "provisioned"
                        ),
                    )
                )
                return _emit(args, data, findings, command="factory drain")
            missing_specs = _preflight_explicit_story_specs(repo_root, station, explicit_stories)
            if missing_specs:
                findings.append(
                    Finding(
                        code="MRS-DISP-004",
                        severity=Severity.ERROR,
                        message=(
                            f"refusing dispatch: --stories names key(s) with "
                            f"no tracked spec on station {station!r}: "
                            f"{', '.join(missing_specs)} -- nothing was "
                            "provisioned"
                        ),
                    )
                )
                return _emit(args, data, findings, command="factory drain")

    policy_flags = _policy_flags_from_harness_arg(getattr(args, "harness", None))
    if policy_flags:
        data["harness_preference_override"] = list(policy_flags.get("harness_preference", ()))

    if bool(getattr(args, "plan", False)):
        # Story 65.1: answered HERE, before a campaign id, run directory,
        # advisory lock, journal entry or supervisor exists -- the plan is
        # read-only by construction, so nothing below this branch runs.
        return run_drain_plan(
            args,
            data=data,
            findings=findings,
            repo_root=repo_root,
            mode=mode,
            leave_remaining=leave_remaining,
            station=station,
            explicit_stories=explicit_stories,
            policy_flags=policy_flags or None,
            fs=fs,
            vcs=vcs,
            build_harness=build_harness,
            process=process,
            harness=harness,
        )

    run_id = raw_campaign or mint_run_id(
        dispatch_fleet.FLEET_JOURNAL_SLUG,
        _format_utc_compact(_now_utc()),
        _random_token(),
    )
    data["campaign"] = run_id
    run_dir = dispatch_fleet.fleet_run_dir(repo_root, run_id)
    try:
        fs.ensure_dir(run_dir)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DRAIN-009",
                severity=Severity.WARN,
                message=f"cannot create campaign run directory {run_dir}: {exc}",
            )
        )

    # The interim runner's singleton-coordinator rule (COORDINATOR.md's
    # hand-maintained STATUS.md owner/state table), made STRUCTURAL: one
    # FLEET-WIDE advisory lock, held for the whole cycle, so two concurrent
    # drains can never both see the same station's slot free and both call
    # `dispatch_once` on it. The lock is deliberately not scoped to the
    # campaign id -- two DIFFERENT campaigns racing is the exact duplicate-
    # dispatch shape this guard exists to prevent. A refusal is cheap to
    # recover from: the detached supervisor simply ticks again.
    try:
        cycle_lock = fs.acquire_advisory_lock(
            dispatch_fleet.fleet_cycle_lock_path(repo_root),
            timeout_s=_FLEET_CYCLE_LOCK_TIMEOUT_S,
        )
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DRAIN-010",
                severity=Severity.ERROR,
                message=(
                    f"another fleet-drain cycle holds the campaign lock "
                    f"(waited {_FLEET_CYCLE_LOCK_TIMEOUT_S}s): {exc}. Exactly "
                    "one drain cycle runs at a time fleet-wide -- nothing was "
                    "dispatched, and no campaign supervisor was spawned."
                ),
            )
        )
        # Readable "not complete" so a detached campaign supervisor ticks
        # again instead of counting this refusal toward the unreadable ceiling.
        data["complete"] = False
        return _emit(args, data, findings, command="factory drain")

    retry_environment_blocks = bool(getattr(args, "retry_environment_blocks", False))
    try:
        campaign_blocked, prior_predicates = _campaign_blocked_from_journal(fs, run_dir, run_id)
        followups_launched = _followups_launched_from_journal(fs, run_dir, run_id)
        campaign_blocked = _reconcile_campaign_blocked(
            vcs=vcs,
            repo_root=repo_root,
            blocked=campaign_blocked,
        )
        campaign_blocked, re_preflight_findings = _reconcile_campaign_blocked_for_re_preflight(
            repo_root=repo_root,
            blocked=campaign_blocked,
            prior_predicates=prior_predicates,
            policy_flags=policy_flags or None,
        )
        findings.extend(re_preflight_findings)
        report = execute_fleet_cycle(
            repo_root=repo_root,
            mode=mode,
            leave_remaining=leave_remaining,
            campaign_blocked=campaign_blocked,
            fs=fs,
            vcs=vcs,
            build_harness=build_harness,
            process=process,
            harness=harness,
            station=station,
            explicit_stories=explicit_stories,
            policy_flags=policy_flags or None,
            max_in_flight=getattr(args, "max_in_flight", None),
            retry_environment_blocks=retry_environment_blocks,
            followups_launched=followups_launched,
        )
        _journal_fleet_cycle(fs, run_dir, run_id, report, findings)
    finally:
        try:
            fs.release_advisory_lock(cycle_lock)
        except FsError:
            pass

    data.update(report.data)
    data["complete"] = report.complete
    findings.extend(report.findings)

    if not once and not report.complete:
        try:
            data["supervisor_pid"] = _spawn_campaign_supervisor(
                process=process,
                repo_root=repo_root,
                run_dir=run_dir,
                run_id=run_id,
                mode=mode,
                leave_remaining=leave_remaining,
                max_cycles=max_cycles,
                tick_seconds=tick_seconds,
                station=station,
                stories=explicit_stories,
                harness=getattr(args, "harness", None),
                max_in_flight=getattr(args, "max_in_flight", None),
                retry_environment_blocks=retry_environment_blocks,
            )
            data["supervisor_log"] = str(run_dir / _FLEET_SUPERVISOR_LOG_FILENAME)
        except ProcessError as exc:
            # Story 22.11 patch pass: a station-scoped/sequenced campaign's
            # recovery command must repeat --station/--stories, or following
            # this message literally silently widens the resumed cycle back
            # to fleet-wide/ledger-order (review finding). Story 81.3: the
            # same holds for --retry-environment-blocks -- a manual resume
            # without it stops on the block the campaign was told to skip.
            recovery_flags = ""
            if station:
                recovery_flags += f" --station {station}"
            if explicit_stories:
                recovery_flags += f" --stories {','.join(explicit_stories)}"
            # The supervisor spawn carries --harness and --max-in-flight, so
            # the hint that literally resumes the campaign must too.
            if getattr(args, "harness", None):
                recovery_flags += f" --harness {args.harness}"
            if getattr(args, "max_in_flight", None) is not None:
                recovery_flags += f" --max-in-flight {args.max_in_flight}"
            if retry_environment_blocks:
                recovery_flags += " --retry-environment-blocks"
            findings.append(
                Finding(
                    code="MRS-DRAIN-007",
                    severity=Severity.WARN,
                    message=(
                        f"the cycle completed but the campaign supervisor "
                        f"could not be spawned: {exc} -- re-run "
                        f"`marshal factory drain --mode {mode.value}"
                        f"{recovery_flags} --campaign {run_id}` to advance "
                        "THIS campaign (omitting --campaign mints a new one, "
                        "which starts with an empty blocked map and spawns a "
                        "second supervisor)"
                    ),
                )
            )

    if getattr(args, "format", "text") != "json":
        try:
            print(dispatch_fleet.render_cycle_summary(report.results), flush=True)
        except OSError, UnicodeEncodeError:
            _suppress_downstream_pipe_close()
    return _emit(args, data, findings, command="factory drain")
