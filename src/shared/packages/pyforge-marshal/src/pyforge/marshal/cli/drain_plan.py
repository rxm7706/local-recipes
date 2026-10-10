"""``marshal factory drain --plan`` (Story 65.1, spec-pyforge-marshal CAP-274).

Nothing in marshal could say what a drain would do before it did it:
``dispatch_once``'s first write is ``git worktree add``, and many refusals are
decidable long before that yet fire only after a whole session (``MRS-GATE-010``
/ ``011`` against the primary checkout's tracked spec, ``MRS-GATE-003`` against a
verify command's shape, ``MRS-DISP-019`` against the rendered merge subject).

This module answers the question READ-ONLY. It runs each station's queue
computation through ``dispatch.plan_station_cycle`` -- the function
``execute_fleet_cycle`` itself calls, so the plan cannot drift from the drain --
as a fresh campaign's first cycle would (no campaign blocks), then evaluates,
for each station's next story (and every queued story with ``--all-stories``),
every refusal the launch path would raise, through the functions the launch
path itself uses. It never calls ``dispatch_once``, ``_journal_dispatch_wave``
or any other writer, and takes no advisory lock: ``run_fleet_drain`` answers
``--plan`` before a campaign id, run directory, lock, journal entry or
supervisor exists.

The harness binary / authcheck walk and the session-precondition probe run
only with ``--check-env``. The declared skip (``skip_policies``) stays the one
park mechanism: a prose park is REPORTED (``MRS-DRAINPLAN-001``/``002``), never
honoured. Pure predicates live in ``core/dispatch_prelaunch.py`` (AD-4); the
reads live here.
"""

from __future__ import annotations

import argparse
import json
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pyforge.core.process import ProcessError, ProcessPort

from ..adapters.fs_local import FsError
from ..adapters.harness_bmadloop import HarnessError
from ..adapters.vcs_git import VcsCommandError
from ..core import dispatch as dispatch_core
from ..core import dispatch_fleet, dispatch_prelaunch, identity, policy
from ..core import promotion as promotion_core
from ..core.dispatch_harness_done import (
    followup_review_recommended,
    parse_blocking_condition,
    parse_spec_status,
    evaluate_land_only_spec_gate,
    land_only_spec_refusal_message,
    should_take_harness_done_land_only,
    should_take_verification_refusal_land_only,
)
from ..core.dispatch_landing import merge_subject_is_marshal_native
from ..core.dispatch_retry import exclude_harness_profiles_after_transient_failure
from ..core.identity import StoryKey, normalize, render_feed_key
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from ..dispatch_verify import _bare_shell_metacharacters, _verify_commands_with_surface_guard
from ..ports.build_harness import BuildHarnessPort
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.vcs import VcsPort
from . import dispatch as dispatch_cli
from .config import _suppress_downstream_pipe_close

_COMMAND = "factory drain"

#: The wave id a plan hands ``plan_station_cycle``: a wave is built to be
#: reported, never journaled, so it carries no minted id.
_PLAN_WAVE_ID = "drain-plan"

#: The would-be code of a refusal that is not a registered finding code.
CODE_ALREADY_LANDED = "already-landed"
CODE_PROSE_PARK = "prose-park"


def plan_usage_error(args: argparse.Namespace) -> str | None:
    """A usage error for a ``--plan`` invocation, or ``None`` (exit 2).

    ``--once``, ``--campaign``, ``--max-cycles`` and ``--tick-seconds`` are
    launch-only: they shape the campaign a drain mints, and a plan mints
    nothing. ``--max-cycles`` / ``--tick-seconds`` default to
    ``argparse.SUPPRESS``, so an explicitly given value -- even ``0`` -- is
    told apart from an absent flag by the attribute's presence. ``--all-stories``
    and ``--check-env`` only modify a plan, so they are a usage error without
    ``--plan`` (a silent no-op would let an operator believe the environment
    had been checked)."""
    if not bool(getattr(args, "plan", False)):
        stray = [
            flag
            for flag, attr in (("--all-stories", "all_stories"), ("--check-env", "check_env"))
            if bool(getattr(args, attr, False))
        ]
        if stray:
            return f"{' and '.join(stray)} only apply with --plan"
        return None
    launch_only: list[str] = []
    if bool(getattr(args, "once", False)):
        launch_only.append("--once")
    if getattr(args, "campaign", None) is not None:
        launch_only.append("--campaign")
    if hasattr(args, "max_cycles"):
        launch_only.append("--max-cycles")
    if hasattr(args, "tick_seconds"):
        launch_only.append("--tick-seconds")
    if launch_only:
        return (
            f"--plan cannot be combined with {', '.join(launch_only)}: a plan launches nothing, "
            "so it has no campaign to bound, resume or tick"
        )
    return None


@dataclass(frozen=True)
class Refusal:
    """One reason a queued story would not dispatch cleanly.

    ``code`` is the would-be finding code the launch path (or the post-session
    gate) raises -- ``MRS-DISP-041/005/045/030/036/039/019/003/002``,
    ``MRS-GATE-010/011/003`` -- or ``already-landed`` / ``prose-park``."""

    story: str
    code: str
    reason: str

    def to_payload(self) -> dict[str, str]:
        return {"story": self.story, "code": self.code, "reason": self.reason}


@dataclass(frozen=True)
class StoryEvaluation:
    """Every refusal decidable before launch for one queued story."""

    story: str
    refusals: tuple[Refusal, ...] = ()
    land_only: bool = False
    prose_park: dispatch_prelaunch.ProsePark | None = None

    @property
    def would_dispatch(self) -> bool:
        return not self.refusals


@dataclass
class _StationReads:
    """Lazy READ-ONLY facts shared by every story one station's plan evaluates."""

    repo_root: Path
    slug: str
    cycle: dispatch_cli.StationCyclePlan
    fs: FsPort
    vcs: VcsPort
    _epics_blocks: dict[StoryKey, str] | None = field(default=None, init=False)
    _merged: frozenset[StoryKey] | None = field(default=None, init=False)

    @property
    def effective_policy(self) -> policy.EffectivePolicy:
        assert self.cycle.effective_policy is not None
        return self.cycle.effective_policy

    @property
    def station_skips(self) -> Mapping[str, str]:
        return self.cycle.station_skips

    @property
    def merge_subject_template(self) -> str:
        return str(self.effective_policy.merge_subject_template.value)

    def verify_commands(self) -> tuple[str, ...]:
        """Pre-launch binding: policy widened with derived guard, ``lint-types``, and whole-tree checks (no coverage gates -- those need the story diff)."""
        return _verify_commands_with_surface_guard(self.effective_policy)

    def epics_block(self, key: StoryKey) -> str | None:
        if self._epics_blocks is None:
            merged: dict[StoryKey, str] = {}
            for path in dispatch_fleet.station_epics_paths(self.repo_root, self.slug):
                text = self.fs.read_text(path)
                if text is None:
                    continue
                for story_key, block in dispatch_prelaunch.story_epics_blocks(text).items():
                    merged[story_key] = f"{merged[story_key]}\n{block}" if story_key in merged else block
            self._epics_blocks = merged
        return self._epics_blocks.get(key)

    def merged_keys(self) -> frozenset[StoryKey]:
        """Stories corroborated merged on ``main`` -- the read
        ``_reconcile_campaign_blocked`` makes, so the same corroboration gate
        (a landing's promoted spec reads ``done`` there) applies."""
        if self._merged is None:
            slug = self.slug
            subjects = self.vcs.commit_subjects(self.repo_root, dispatch_cli._BASE_REF)

            def _spec_status_for(candidate_key: StoryKey) -> str | None:
                try:
                    spec_text = dispatch_core.spec_text_at_ref(self.vcs, self.repo_root, slug, str(candidate_key))
                except VcsCommandError:
                    return None
                return promotion_core.read_spec_status(spec_text)

            self._merged = promotion_core.corroborated_merged_story_keys(
                subjects,
                self.merge_subject_template,
                slug,
                spec_status_for=_spec_status_for,
            )
        return self._merged


def _as_str_tuple(value: object) -> tuple[str, ...]:
    """A policy value that is a list of names, as a tuple of ``str``."""
    return tuple(str(item) for item in value) if isinstance(value, (list, tuple)) else ()


def _command_shape_problem(command: str) -> str | None:
    """The ``MRS-GATE-003`` reason for a verify command the gate cannot run,
    the same two checks ``dispatch_verify._run_verify_command`` makes before it
    spawns anything: it must tokenize, and it is never run through a shell."""
    try:
        shlex.split(command)
    except ValueError as exc:
        return f"cannot parse verify command {command!r}: {exc}"
    shell_chars = _bare_shell_metacharacters(command)
    if shell_chars:
        return (
            f"verify command {command!r} uses shell syntax "
            f"({', '.join(repr(c) for c in shell_chars)}) "
            "but verify commands are never run through a shell"
        )
    return None


def _read_spec_text(spec_path: Path) -> tuple[str | None, str | None]:
    """``(text, error)`` for a tracked spec."""
    try:
        return spec_path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, f"cannot read spec {spec_path!r}: {exc}"


def evaluate_story(reads: _StationReads, story: str) -> StoryEvaluation:
    """Every refusal decidable without launching, for one queued ``story``.

    Composes the functions the launch path uses, in the launch path's own
    order: the scope check (``MRS-DISP-041``), spec presence (``MRS-DISP-005``),
    the legacy-branch / leftover-worktree reads (``MRS-DISP-030/036/039/045``,
    or the ``MRS-DISP-040`` land-only path), the post-session gate's binding
    (``MRS-GATE-010/011``) and command-shape (``MRS-GATE-003``) checks, the
    landing's merge-subject check (``MRS-DISP-019``), and the two facts no
    refusal code exists for (already merged on ``main``; a prose park).

    Reads only: it asks ``vcs`` / ``fs`` questions and never adds a worktree,
    creates a directory or runs a command. A git read that fails raises
    ``VcsCommandError``; the station's plan turns that into
    ``MRS-DRAINPLAN-005``."""
    repo_root, slug, vcs, fs = reads.repo_root, reads.slug, reads.vcs, reads.fs
    refusals: list[Refusal] = []

    def refuse(code: str, reason: str) -> None:
        refusals.append(Refusal(story=story, code=code, reason=reason))

    try:
        key = normalize(story)
    except ValueError as exc:
        refuse("MRS-DISP-002", f"malformed story key {story!r}: {exc}")
        return StoryEvaluation(story=story, refusals=tuple(refusals))
    feed = render_feed_key(key)

    scope_refusal = dispatch_cli._dispatch_scope_refusal(slug)
    if scope_refusal is not None:
        refuse(scope_refusal.code, scope_refusal.message)

    spec_path = dispatch_core.resolve_story_spec_path(repo_root, slug, story)
    spec_text: str | None = None
    if spec_path is None:
        refuse(
            "MRS-DISP-005",
            f"no tracked spec found for story {feed!r} under {dispatch_core.planning_specs_dir(repo_root, slug)!r}",
        )
    else:
        spec_text, read_error = _read_spec_text(spec_path)
        if read_error is not None:
            refuse("MRS-DISP-005", read_error)

    land_only = False
    worktree_path = dispatch_core.dispatch_worktree_path(repo_root, slug, feed)
    branch = dispatch_core.resolve_dispatch_branch(vcs, repo_root, slug=slug, story_key=feed, worktree=worktree_path)
    if branch.refusal is not None:
        refuse("MRS-DISP-030", branch.refusal)
    else:
        # `_ensure_dispatch_worktree`'s own read-only half: an existing worktree
        # (git's registry, then the conventional path) is reused; otherwise
        # dispatch would ADD one -- the write the plan never makes.
        existing = vcs.worktree_path_for_branch(repo_root, branch.effective_branch)
        worktree = existing if existing is not None else (worktree_path if worktree_path.exists() else None)
        if worktree is not None:
            baseline = vcs.worktree_head_sha(worktree)
            wip = dispatch_cli._surface_worktree_wip_before_dispatch(
                vcs=vcs, repo_root=repo_root, worktree=worktree, baseline_head_sha=baseline
            )
            if wip is not None:
                blocked = dispatch_cli._redispatch_blocked_pending_supervisor_finalize(
                    fs=fs, repo_root=repo_root, slug=slug, story_key=feed, worktree=worktree
                )
                if blocked is not None:
                    refuse("MRS-DISP-039", blocked)
                else:
                    refuse("MRS-DISP-036", f"{wip.message} -- a launch would proceed over that unfinalized work")
            if spec_path is not None and spec_text is not None:
                live = dispatch_cli._spec_text_prefer_worktree(spec_path, repo_root, worktree, spec_text)
                status = parse_spec_status(live)
                latest_landing_verdict: str | None = None
                latest_journal = None
                latest_run_dir = dispatch_cli._latest_story_run_dir(fs, repo_root, slug, feed)
                if latest_run_dir is not None:
                    latest_journal = dispatch_cli.gather_dispatch_journal_facts(fs, latest_run_dir, latest_run_dir.name)
                    latest_landing_verdict = latest_journal.landing_verdict
                followup = followup_review_recommended(live)
                if should_take_harness_done_land_only(
                    status,
                    followup,
                    latest_landing_verdict=latest_landing_verdict,
                ):
                    # MRS-DISP-040's CAP-4 path: dispatch lands the finished
                    # work instead of launching a session -- reported as
                    # land-only, never as a refusal.
                    land_only = True
                if not land_only and latest_journal is not None:
                    try:
                        current_head = vcs.worktree_head_sha(worktree)
                    except VcsCommandError:
                        current_head = None
                    if should_take_verification_refusal_land_only(
                        status,
                        followup,
                        completion_verdict=latest_journal.completion_verdict,
                        verification_verdict=latest_journal.verification_verdict,
                        verification_failed_gate=latest_journal.verification_failed_gate,
                        refusal_head_sha=latest_journal.final_revision or latest_journal.baseline_head_sha,
                        current_head_sha=current_head,
                    ):
                        land_only = True
                if land_only and spec_path is not None:
                    blame = dispatch_cli._spec_line_blame_for_worktree(
                        vcs,
                        repo_root=repo_root,
                        worktree=worktree,
                        spec_path=spec_path,
                    )
                    gate = evaluate_land_only_spec_gate(
                        spec_text=live,
                        spec_status=status,
                        blame=blame,
                    )
                    if not gate.permitted:
                        land_only = False
                        refuse(
                            "MRS-DISP-063",
                            land_only_spec_refusal_message(story_key=feed, verdict=gate),
                        )
                if not land_only and status == "blocked":
                    refuse(
                        "MRS-DISP-045",
                        f"story {feed!r} worktree spec is status: blocked -- not relaunching "
                        "bmad-build-auto without an operator decision "
                        f"(blocking condition: {parse_blocking_condition(live) or 'not stated'})",
                    )

    verify_commands = reads.verify_commands()
    if spec_text is not None:
        for finding in dispatch_prelaunch.spec_binding_findings(spec_text, verify_commands):
            refuse(finding.code, finding.message)
    for command in verify_commands:
        problem = _command_shape_problem(command)
        if problem is not None:
            refuse("MRS-GATE-003", problem)

    template = reads.merge_subject_template
    subject: str | None = None
    native = False
    detail = ""
    try:
        subject = identity.render_merge_subject(key, template, slug)
        native = merge_subject_is_marshal_native(subject, template, slug)
    except ValueError as exc:
        detail = f": {exc}"
    if not native:
        rendered = f"rendered merge subject {subject!r}" if subject is not None else "merge_subject_template"
        refuse(
            "MRS-DISP-019",
            f"{rendered} for {feed!r} is not marshal-native per marshal_native_merged_keys "
            f"-- landing would be refused{detail}",
        )

    # A follow-up review entry (Story 73.2, CAP-281) is a `done` story BY DESIGN: it is judged by its open
    # `DW-FRR` row, so the story's first landing on `main` is not "already landed" for it.
    if story not in reads.cycle.followup_stories and key in reads.merged_keys():
        refuse(
            CODE_ALREADY_LANDED,
            f"{feed!r} is corroborated merged on {dispatch_cli._BASE_REF} while its tracked ledger row is not done "
            "-- a session would re-implement landed work",
        )

    park = dispatch_prelaunch.find_prose_park(
        story=story,
        station_skips=reads.station_skips,
        epics_block=reads.epics_block(key),
        spec_text=spec_text,
    )
    if park is not None:
        refuse(CODE_PROSE_PARK, _prose_park_reason(park))
    return StoryEvaluation(story=story, refusals=tuple(refusals), land_only=land_only, prose_park=park)


def _prose_park_reason(park: dispatch_prelaunch.ProsePark) -> str:
    return (
        f"parked only in prose ({park.source}: {park.excerpt!r}) -- no skip_policies entry mirrors it, "
        "so a drain would still dispatch it; declare the skip in fleet-drain-queue.yaml"
    )


def _serial_deps_graph(reads: _StationReads) -> dict[str, tuple[StoryKey, ...]]:
    """``feed story key -> declared Deps`` from the docs the serial ordering
    reads (``_load_station_story_deps``: every epics-family doc)."""
    declared = dispatch_cli._load_station_story_deps(reads.fs, reads.repo_root, reads.slug)
    if not declared:
        return {}
    return {render_feed_key(key): parsed.story_keys for key, parsed in declared.items()}


def _check_environment(
    *,
    reads: _StationReads,
    first_story: str,
    spec_text: str | None,
    build_harness: BuildHarnessPort,
) -> tuple[list[Refusal], list[Finding], dict[str, object]]:
    """The harness binary + authcheck walk ``dispatch_once`` makes (``--check-env``
    only). Mirrors its preference derivation -- the tier-mapped lead, an
    explicit ``--harness`` outranking it, transient-failure exclusions -- and
    relays the walk's own ``MRS-DISP-027/028`` WARNs; a walk that finds no
    candidate is ``MRS-DISP-003``."""
    effective = reads.effective_policy
    feed = render_feed_key(normalize(first_story))
    difficulty = dispatch_core.read_declared_difficulty(spec_text) if spec_text is not None else None
    session_log = dispatch_cli._last_failed_dispatch_session_log(reads.fs, reads.repo_root, reads.slug, feed)
    tier = dispatch_core.resolve_tier_harness(effective, difficulty=difficulty, session_log=session_log)
    configured = _as_str_tuple(effective.harness_preference.value)
    preference = configured
    explicit_flag = effective.harness_preference.layer == policy.PolicyLayer.FLAG
    if tier.harness_profile is not None and not explicit_flag:
        preference = (tier.harness_profile,) + tuple(name for name in preference if name != tier.harness_profile)
    preference = exclude_harness_profiles_after_transient_failure(preference, session_log)
    if not preference:
        preference = configured
    resolution = build_harness.binary_present(preference, repo_root=reads.repo_root)
    findings: list[Finding] = []
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
    refusals: list[Refusal] = []
    if not resolution:
        tried = (
            "; ".join(f"{s.profile}: {s.reason}" for s in resolution.skipped)
            or "empty harness_preference -- no candidate to try"
        )
        refusals.append(
            Refusal(
                story=first_story,
                code="MRS-DISP-003",
                reason=f"no dispatchable session-harness profile ({tried})",
            )
        )
    env: dict[str, object] = {
        "harness_profile": resolution.profile,
        "preference": list(preference),
        "skipped": [{"profile": s.profile, "reason": s.reason} for s in resolution.skipped],
    }
    return refusals, findings, env


def _finding_for_refusal(slug: str, refusal: Refusal, *, is_next: bool) -> Finding:
    if is_next:
        return Finding(
            code="MRS-DRAINPLAN-001",
            severity=Severity.ERROR,
            message=(
                f"station {slug!r}: next story {refusal.story!r} would not dispatch cleanly "
                f"({refusal.code}): {refusal.reason}"
            ),
        )
    return Finding(
        code="MRS-DRAINPLAN-002",
        severity=Severity.WARN,
        message=(
            f"station {slug!r}: queued story {refusal.story!r} would not dispatch cleanly "
            f"({refusal.code}): {refusal.reason}"
        ),
    )


def _held_reason(reads: _StationReads, story: str, deps_graph: Mapping[str, tuple[StoryKey, ...]]) -> str:
    cycle = reads.cycle
    return dispatch_prelaunch.held_reason(story, cycle.statuses, deps_graph, cycle.wave)


def _station_row(
    slug: str,
    mode: dispatch_fleet.FleetCampaignMode,
    *,
    parallel_cap: int | None,
    backlog: Sequence[str],
    env_checked: bool,
) -> dict[str, object]:
    """The one skeleton of a station row, so a computed plan and an
    ``MRS-DRAINPLAN-005`` row always carry the same keys (a consumer indexing a
    row must not ``KeyError`` on exactly the rows that report a failure)."""
    return {
        "slug": slug,
        "mode": mode.value,
        "parallel_cap": parallel_cap,
        "backlog": list(backlog),
        "outcome": "",
        "next_story": None,
        "stories": [],
        "wave": None,
        "held": [],
        "followups": [],
        "would_dispatch": False,
        "land_only": [],
        "refusals": [],
        "prose_parks": [],
        "skipped": [],
        "deps": {},
        "evaluated": [],
        "env_checked": env_checked,
    }


def _plan_station(
    *,
    reads: _StationReads,
    mode: dispatch_fleet.FleetCampaignMode,
    order_override: Sequence[str] | None,
    explicit_stories: tuple[str, ...] | None,
    all_stories: bool,
    check_env: bool,
    build_harness: BuildHarnessPort,
) -> tuple[dict[str, object], list[Finding]]:
    """One station's plan payload and findings (raises on an unreadable git/fs)."""
    cycle = reads.cycle
    slug = reads.slug
    findings: list[Finding] = []
    payload = _station_row(slug, mode, parallel_cap=cycle.parallel_cap, backlog=cycle.backlog, env_checked=check_env)
    payload["followups"] = list(cycle.followup_stories)

    queue = cycle.queue
    station_skips = cycle.station_skips
    skipped: list[dict[str, str]] = []
    seen_skipped: set[str] = set()
    if queue is not None:
        for story, reason in queue.skipped:
            seen_skipped.add(story)
            skipped.append(
                {
                    "story": story,
                    "reason": reason,
                    "basis": dispatch_cli.skip_basis(
                        story=story,
                        reason=reason,
                        station_skips=station_skips,
                        block_classes=cycle.block_classes,
                        mode=mode,
                    ),
                }
            )
    for story in cycle.backlog:
        if story in station_skips and story not in seen_skipped:
            seen_skipped.add(story)
            skipped.append({"story": story, "reason": station_skips[story], "basis": "declared skip policy"})
    payload["skipped"] = skipped

    # An `order_overrides` list changes nothing yet switches the Deps sort off.
    if explicit_stories is None:
        inert = dispatch_prelaunch.inert_override_keys(order_override, cycle.statuses)
        if inert:
            findings.append(
                Finding(
                    code="MRS-DRAINPLAN-003",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: order_overrides lists only done or absent keys ({', '.join(inert)}) -- "
                        "it reorders nothing, but a non-empty list switches the Deps sort off; prune it from "
                        "fleet-drain-queue.yaml"
                    ),
                )
            )

    head = queue.next_story if queue is not None else None
    payload["next_story"] = head
    targets: tuple[str, ...] = ()
    if cycle.finalize_pending is not None:
        pending_story, evidence = cycle.finalize_pending
        payload.update(outcome="in-flight", detail=evidence, story=pending_story)
    elif queue is not None and queue.outcome is dispatch_fleet.StationQueueOutcome.BLOCKED:
        payload.update(outcome="blocked", blocked_story=queue.blocked_story, detail=queue.blocked_reason)
    elif queue is not None and head is None:
        payload["outcome"] = queue.outcome.value
    elif cycle.live_stories:
        if cycle.parallel_cap <= 1:
            detail = (
                f"dispatch in flight: {', '.join(cycle.live_stories)} (waiting for terminal outcome before next launch)"
            )
        else:
            detail = (
                f"wave in flight: {', '.join(cycle.live_stories)} (waiting for terminal outcomes before next batch)"
            )
        payload.update(outcome="in-flight", detail=detail)
    else:
        targets = cycle.stories_to_dispatch
        payload["outcome"] = "dispatch" if targets else "held"
        payload["stories"] = list(targets)
        if cycle.wave is not None:
            payload["wave"] = {
                "max_parallel": cycle.wave.max_parallel,
                "members": list(cycle.wave.members),
                "refused": [
                    {
                        "story": r.story,
                        "reason": r.reason,
                        **({"overlap_with": r.overlap_with} if r.overlap_with else {}),
                    }
                    for r in cycle.wave.refused
                ],
            }

    # Deps readiness, in the mode's own terms: serial mode only ORDERS by Deps
    # (`station_backlog`) and never gates on them; only the parallel wave gates
    # (`ordered_ready_backlog`).
    parallel = cycle.parallel_cap > 1
    deps_graph: Mapping[str, tuple[StoryKey, ...]] = {}
    if head is not None:
        if parallel:
            deps_graph = (
                cycle.deps_graph
                if cycle.deps_graph is not None
                else dispatch_cli._load_station_deps_graph(reads.repo_root, slug)
            )
        else:
            deps_graph = _serial_deps_graph(reads)
        head_unmet = dispatch_prelaunch.unmet_deps(head, cycle.statuses, deps_graph)
        try:
            head_feed = render_feed_key(normalize(head))
        except ValueError:
            head_feed = head
        deps_payload = payload["deps"]
        assert isinstance(deps_payload, dict)
        deps_payload[head] = {
            "declared": [render_feed_key(dep) for dep in deps_graph.get(head_feed, ())],
            "unmet": [render_feed_key(dep) for dep in head_unmet],
        }
        if head_unmet:
            unmet_text = ", ".join(render_feed_key(dep) for dep in head_unmet)
            consequence = (
                f"parallel mode (max_parallel = {cycle.parallel_cap}) holds it out of the wave until they are done"
                if parallel
                else "serial mode (max_parallel = 1) dispatches it anyway: Deps only order the queue, they never gate it"
            )
            findings.append(
                Finding(
                    code="MRS-DRAINPLAN-004",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: next story {head!r} declares Deps that are not all done "
                        f"({unmet_text}) -- {consequence}"
                    ),
                )
            )
        if parallel and cycle.wave is not None:
            # Everything the wave holds out: the queue head when unmet Deps keep
            # it from the ready set, and every story the wave itself refused.
            held = payload["held"]
            assert isinstance(held, list)
            held.extend(
                {"story": story, "reason": _held_reason(reads, story, deps_graph)}
                for story in dispatch_cli.wave_held_stories(cycle)
            )

    # Which stories get the full evaluation: what the cycle would hand
    # `dispatch_once` (the first of them is "the next story"), and every queued
    # story with --all-stories.
    to_evaluate: list[str] = list(targets)
    if head is not None and head not in to_evaluate and cycle.finalize_pending is None and not cycle.live_stories:
        # A head the parallel wave holds out (unmet Deps, an unknown surface,
        # a cap): it is not handed to `dispatch_once` this cycle, but the
        # refusals it would meet once released are the very thing an operator
        # reads a plan for -- reported as a queued story, never as "the next".
        to_evaluate.append(head)
    if all_stories:
        for story in cycle.backlog:
            if story not in station_skips and story not in to_evaluate:
                to_evaluate.append(story)
    evaluations: list[StoryEvaluation] = []
    first_spec_text: str | None = None
    for index, story in enumerate(to_evaluate):
        evaluation = evaluate_story(reads, story)
        evaluations.append(evaluation)
        if index == 0:
            spec_path = dispatch_core.resolve_story_spec_path(reads.repo_root, slug, story)
            if spec_path is not None:
                first_spec_text, _error = _read_spec_text(spec_path)
    refusals: list[Refusal] = [refusal for evaluation in evaluations for refusal in evaluation.refusals]
    env_findings: list[Finding] = []
    if check_env and to_evaluate:
        env_refusals, env_findings, env = _check_environment(
            reads=reads,
            first_story=to_evaluate[0],
            spec_text=first_spec_text,
            build_harness=build_harness,
        )
        refusals.extend(env_refusals)
        payload["env"] = env
    findings.extend(env_findings)
    # Every story the cycle would hand to `dispatch_once` -- one in serial mode,
    # every wave member in parallel mode -- is graded as "next": a refusal on
    # wave member 2+ is as fatal to its launch as one on the first.
    handed = frozenset(targets)
    for refusal in refusals:
        findings.append(_finding_for_refusal(slug, refusal, is_next=refusal.story in handed))
    payload["refusals"] = [refusal.to_payload() for refusal in refusals]
    payload["land_only"] = [evaluation.story for evaluation in evaluations if evaluation.land_only]
    payload["would_dispatch"] = bool(handed) and not any(r.story in handed for r in refusals)

    # Prose parks are reported ALWAYS: every backlog story a park marker names
    # that no skip_policies entry mirrors. An evaluated story's park is already
    # one of its refusals above; the rest of the backlog is read here.
    evaluated = {evaluation.story: evaluation for evaluation in evaluations}
    parks: list[dict[str, str]] = []
    for story in cycle.backlog:
        if story in station_skips:
            continue
        known = evaluated.get(story)
        if known is not None:
            park = known.prose_park
        else:
            park = _scan_prose_park(reads, story)
            if park is not None:
                findings.append(
                    Finding(
                        code="MRS-DRAINPLAN-002",
                        severity=Severity.WARN,
                        message=(f"station {slug!r}: queued story {story!r} is {_prose_park_reason(park)}"),
                    )
                )
        if park is not None:
            parks.append({"story": story, "source": park.source, "excerpt": park.excerpt})
    payload["prose_parks"] = parks
    payload["evaluated"] = [
        {"story": e.story, "would_dispatch": e.would_dispatch, "land_only": e.land_only} for e in evaluations
    ]
    return payload, findings


def _scan_prose_park(reads: _StationReads, story: str) -> dispatch_prelaunch.ProsePark | None:
    try:
        key = normalize(story)
    except ValueError:
        return None
    spec_text: str | None = None
    spec_path = dispatch_core.resolve_story_spec_path(reads.repo_root, reads.slug, story)
    if spec_path is not None:
        spec_text, _error = _read_spec_text(spec_path)
    return dispatch_prelaunch.find_prose_park(
        story=story,
        station_skips=reads.station_skips,
        epics_block=reads.epics_block(key),
        spec_text=spec_text,
    )


def _unevaluable(
    slug: str, mode: dispatch_fleet.FleetCampaignMode, cause: str, *, path: str | None = None
) -> tuple[dict[str, object], Finding]:
    finding = Finding(
        code="MRS-DRAINPLAN-005",
        severity=Severity.ERROR,
        message=f"station {slug!r}: the plan could not be computed -- {cause}; this is never a clean plan",
        path=path,
    )
    payload = _station_row(slug, mode, parallel_cap=None, backlog=(), env_checked=False)
    payload.update(outcome="unevaluable", detail=cause)
    return payload, finding


def _emit_plan(args: argparse.Namespace, data: dict[str, object], findings: list[Finding]) -> int:
    envelope = build_envelope(
        command=_COMMAND,
        verdict=compute_verdict(tuple(findings)),
        data=data,
        findings=tuple(findings),
    )
    try:
        if getattr(args, "format", "text") == "json":
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True), flush=True)
        else:
            print(render_plan_text(envelope.verdict.value, data, findings), flush=True)
    except OSError, UnicodeEncodeError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def render_plan_text(verdict: str, data: Mapping[str, object], findings: Sequence[Finding]) -> str:
    """The text form: a header, one block per station, then the findings."""
    lines = [f"command: {_COMMAND} --plan", f"verdict: {verdict}", f"mode: {data.get('mode')}"]
    stations = data.get("stations")
    for row in stations if isinstance(stations, list) else []:
        if not isinstance(row, dict):
            continue
        next_story = row.get("next_story") or "-"
        backlog = row.get("backlog")
        remaining = len(backlog) if isinstance(backlog, list) else 0
        lines.append(
            f"  {row.get('slug')!s:<18} {row.get('outcome')!s:<14} next={next_story} "
            f"would_dispatch={'yes' if row.get('would_dispatch') else 'no'} remaining={remaining}"
        )
        detail = row.get("detail")
        if detail:
            lines.append(f"      detail: {detail}")
        for refusal in row.get("refusals") or []:
            lines.append(f"      refuses {refusal['story']}: {refusal['code']} -- {refusal['reason']}")
        for held in row.get("held") or []:
            lines.append(f"      held {held['story']}: {held['reason']}")
        for story in row.get("land_only") or []:
            lines.append(f"      land-only {story} (MRS-DISP-040 path: lands finished work, launches no session)")
        for story in row.get("followups") or []:
            lines.append(f"      follow-up review {story} (an open DW-FRR row; queued after the backlog)")
        for skip in row.get("skipped") or []:
            lines.append(f"      skipped {skip['story']} ({skip['basis']}): {skip['reason']}")
    for finding in findings:
        lines.append(f"finding {finding.code}: {finding.message}")
    return "\n".join(lines)


def run_drain_plan(
    args: argparse.Namespace,
    *,
    data: dict[str, object],
    findings: list[Finding],
    repo_root: Path,
    mode: dispatch_fleet.FleetCampaignMode,
    leave_remaining: int,
    station: str | None,
    explicit_stories: tuple[str, ...] | None,
    policy_flags: dict[str, object] | None,
    fs: FsPort,
    vcs: VcsPort,
    build_harness: BuildHarnessPort,
    process: ProcessPort,
    harness: HarnessPort,
) -> int:
    """``marshal factory drain --plan`` -- report, launch nothing.

    ``data`` / ``findings`` arrive holding what ``run_fleet_drain`` already
    recorded (mode, station, stories, the harness override). Each station is
    planned independently: one whose plan cannot be computed reports
    ``MRS-DRAINPLAN-005`` and never stops the others. The exit comes from the
    AD-7 lattice via ``compute_verdict`` -- ERROR (4) when any station's next
    story would not dispatch cleanly, UNEVALUABLE (1) when a plan cannot be
    computed, 0 otherwise."""
    all_stories = bool(getattr(args, "all_stories", False))
    check_env = bool(getattr(args, "check_env", False))
    max_in_flight = getattr(args, "max_in_flight", None)
    retry_environment_blocks = bool(getattr(args, "retry_environment_blocks", False))
    data["plan"] = True
    data["check_env"] = check_env
    data["all_stories"] = all_stories
    data["stations"] = []
    stations: list[dict[str, object]] = []

    overrides, configured_skips, config_findings = dispatch_cli._read_fleet_queue_config(fs, repo_root)
    findings.extend(config_findings)
    cycle_slugs = dispatch_cli.resolve_cycle_slugs(repo_root, station)
    if cycle_slugs.finding is not None:
        findings.append(cycle_slugs.finding)

    # Story 73.2 (CAP-281): the follow-up reviews a fresh campaign's first cycle would queue -- the very read
    # `execute_fleet_cycle` makes (`--plan` has no campaign, so nothing is launched yet), and never under `--stories`.
    # `fetch=False`: the drain refreshes `origin/main` before it re-reads a row, but a plan never writes a ref or
    # reaches a remote (CAP-274), so it reads `origin/main` as this checkout holds it.
    followup_plan = dispatch_cli.FollowupPlan()
    if explicit_stories is None and cycle_slugs.slugs:
        followup_plan = dispatch_cli.plan_followup_reviews(
            repo_root=repo_root, slugs=cycle_slugs.slugs, vcs=vcs, policy_flags=policy_flags, fetch=False
        )
        findings.extend(followup_plan.findings)

    for slug in cycle_slugs.slugs:
        try:
            cycle = dispatch_cli.plan_station_cycle(
                repo_root=repo_root,
                slug=slug,
                mode=mode,
                leave_remaining=leave_remaining,
                campaign_blocked={},
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
                mint_wave_id=lambda: _PLAN_WAVE_ID,
                followups=followup_plan.selected.get(slug, ()),
            )
            if cycle.ledger_error is not None:
                payload, finding = _unevaluable(
                    slug,
                    mode,
                    f"cannot read the tracked ledger at {cycle.ledger_path}: {cycle.ledger_error}",
                    path=str(cycle.ledger_path),
                )
                stations.append(payload)
                findings.append(finding)
                continue
            reads = _StationReads(repo_root=repo_root, slug=slug, cycle=cycle, fs=fs, vcs=vcs)
            payload, station_findings = _plan_station(
                reads=reads,
                mode=mode,
                order_override=overrides.get(slug),
                explicit_stories=explicit_stories,
                all_stories=all_stories,
                check_env=check_env,
                build_harness=build_harness,
            )
        except (VcsCommandError, FsError, HarnessError, ProcessError, OSError, ValueError) as exc:
            payload, finding = _unevaluable(slug, mode, f"{type(exc).__name__}: {exc}")
            stations.append(payload)
            findings.append(finding)
            continue
        stations.append(payload)
        findings.extend(station_findings)

    if check_env and any(row.get("stories") for row in stations):
        # The session-precondition probe is repo-level, not per station: once,
        # and only when there is a launch to be ready for.
        session_finding = dispatch_cli._surface_session_precondition_findings(process=process, repo_root=repo_root)
        data["session_check"] = "ok" if session_finding is None else session_finding.message
        if session_finding is not None:
            findings.append(session_finding)
    data["stations"] = stations
    return _emit_plan(args, data, findings)
