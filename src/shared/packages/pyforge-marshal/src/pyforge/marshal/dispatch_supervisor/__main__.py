"""Dispatch completion supervisor entry point (Story 22.2)."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pyforge.core.process import PosixProcess, ProcessPort

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadbuild import BmadBuildHarness, BuildHarnessError
from ..adapters.publisher_host import HostPublisher
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import dispatch as dispatch_core
from ..core import gate as gate_core
from ..core import identity as identity_core
from ..core import promotion as promotion_core
from ..core.commit_vcs import CommittingVcs
from ..core.dispatch_cfe_commit import (
    CFE_BRANCH_COMMIT_GATE_CODE,
    non_retro_commit_paths,
    unsanctioned_cfe_commit_entries,
)
from ..core.dispatch_completion import (
    DispatchGitFacts,
    DispatchSessionVerdict,
    has_git_progress,
    is_spec_only_narration,
    merge_subject_ref,
    narration_spec_path,
    run_head_reached_ref,
)
from ..core.dispatch_harness_done import (
    HOLD_LANDING_PAYLOAD_KEY,
    FollowupReview,
    has_auto_run_result,
    parse_baseline_revision,
    parse_blocking_condition,
    parse_spec_status,
)
from ..core.dispatch_landing import DispatchLandingVerdict, blocked_twin_promotion_text
from ..core.dispatch_preserve import (
    failed_patch_path,
    relative_preserve_ref,
)
from ..core.dispatch_push import may_push_dispatch_branch_before_verify
from ..core.dispatch_supervisor_finalize import (
    classify_finalize_trigger,
    finalize_attempt_journaled,
    supervisor_should_finalize_harness_work,
)
from ..core.dispatch_supervisor_state import (
    landing_journal_indicates_complete,
    should_retry_stuck_land,
    should_terminalize_verify_refusal,
    supervisor_should_exit,
)
from ..core.dispatch_survival import (
    build_timing_record,
    timing_record_payload,
)
from ..core.dispatch_verification import (
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    judge_dispatch_verification,
)
from ..core.dispatch_verification_journal import build_dispatch_verification_journal_entries_from_envelope
from ..core.dispatch_verify_fix import (
    FIX_TURN_REVERIFY_REFUSED_CODE,
    FIX_TURN_START_FAILED_CODE,
    FIX_TURN_TIMEOUT_CODE,
    FailedVerifyCommand,
    build_verify_fix_prompt,
    choose_verify_fix_launch_mode,
    decide_verify_fix_turn,
    extract_failed_verify_commands,
    fix_intent_ref,
    fix_turn_park_message,
    fix_turn_remaining_budget_s,
    in_flight_verify_fix_turn,
    pending_verify_fix_intent,
    scrub_then_tail_bytes,
)
from ..core.egress import redact_raw_text, to_redacted_text
from ..core.identity import MalformedStoryKeyError, StoryKey, normalize, resolve_feed
from ..core.journal import (
    LAND_FINDINGS_FIELD,
    LANDING_CHECKS_FIELD,
    SCOPE_VIOLATION_ADVISORIES_FIELD,
    VERIFY_FAILED_COMMANDS_FIELD,
    JournalEntryId,
    Phase,
    build_entry,
    fold,
    prepare_for_write,
    prepare_for_write_offloading_fields,
    resolve_verify_failed_commands_from_payload,
    sidecar_texts_for_lines,
)
from ..core.model import Finding, Severity
from ..core.policy import resolve_verify_fix_settings
from ..core.publish import dispatch_complete_result, shape_dispatch_publish
from ..core.refs import ORIGIN_MAIN
from ..core.supervise import resolve_terminal_session_verdict
from ..core.worktree_checkpoint import (
    commit_worktree_checkpoint,
    should_checkpoint_on_idle,
)
from ..dispatch_land import _reconcile_spec_surface_drift, execute_dispatch_land
from ..dispatch_verify import (
    ProcessWaitResult,
    TerminateProcessGroupResult,
    check_unsanctioned_cfe_commits,
    compose_dispatch_policy,
    dispatch_session_alive,
    evaluate_dispatch_verification,
    fix_session_alive,
    resolve_spec_text_for_story,
    run_dispatch_ruff_format_before_verify,
    terminate_process_group,
    verify_fix_loop_enabled,
    wait_for_process,
)
from ..ports.commit import VcsRef
from ..ports.fs import FsPort
from ..ports.publisher import RunPublisherPort
from ..ports.vcs import VcsPort

_JOURNAL_FILENAME = "journal.jsonl"
#: Story 68.1 (CAP-277): the observation a failed blocked-twin publish is journaled under.
_BLOCKED_TWIN_PUBLISH_KIND = "dispatch-blocked-twin-publish"
_SESSION_LOG_FILENAME = "session.log"
_TICK_SECONDS = 60
_FETCH_EVERY_N_TICKS = 5
#: Story 85.3: how often a fix turn calls the run publisher's heartbeat at most (the portal marks a run
#: `heartbeat_lost` after 300 s), and how often the progress thread does during the turn's re-verification. The
#: fix wait polls every second, but its journal heartbeat keeps the tick rate: at most one per `_TICK_SECONDS`
#: (Story 85.4).
_FIX_TURN_PUBLISH_INTERVAL_S = 30.0
_BASE_REF = ORIGIN_MAIN  # Story 60.1 (CAP-270): the full refname, never a short name a local ref can shadow


def _writer_id() -> str:
    return f"dispatch-supervisor-{os.getpid()}"


def _format_entry_ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _append_entry(
    fs: FsPort,
    run_dir: Path,
    entry,
    *,
    fsync: bool,
    offload_fields: frozenset[str] | None = None,
) -> None:
    if offload_fields:
        prepared = prepare_for_write_offloading_fields(entry, offload_fields=offload_fields)
    else:
        prepared = prepare_for_write(entry)
    if prepared.sidecar_relative_path is not None:
        fs.write_text_atomic(run_dir / prepared.sidecar_relative_path, prepared.sidecar_content)
    fs.append_line(run_dir / _JOURNAL_FILENAME, prepared.line, fsync=fsync)


def _fold_dispatch_journal(fs: FsPort, run_dir: Path, text: str):
    lines = text.splitlines()
    sidecars = sidecar_texts_for_lines(
        lines,
        read_sidecar=lambda ref: fs.read_text(run_dir / ref),
    )
    return fold(lines, sidecars=sidecars)


def _fetch_origin_main(vcs: VcsPort, repo_root: Path) -> None:
    """Fetch ``origin main``, tolerating a failed fetch (Story 72.1, CAP-280).

    Every merge fact the supervisor judges reads ``origin/main``; a failed
    fetch leaves the last-fetched remote-tracking ref in place, never local
    ``main``."""
    try:
        vcs.fetch(repo_root, "origin", "main")
    except VcsCommandError:
        pass


def _maybe_fetch_origin_main(vcs: VcsPort, repo_root: Path, *, tick: int) -> None:
    if tick % _FETCH_EVERY_N_TICKS != 0:
        return
    _fetch_origin_main(vcs, repo_root)


def _commit_pre_verify_wip(
    vcs: CommittingVcs,
    *,
    repo_root: Path,
    worktree: Path,
) -> tuple[bool, str | None]:
    """Commit the worktree's uncommitted edits before a re-verification (Story 85.2).

    Returns ``(committed, refusal)``: ``refusal`` names why the tree is NOT clean afterwards -- a failed git call,
    or edits the commit left behind -- and is ``None`` once it is clean. A failure is reported, never swallowed
    (review H2): a re-verification of a dirty tree would verify what landing never pushes.

    Story 83.19: conda-forge-expert surface paths are left out of the commit and do not count as left
    behind -- the re-verification commits them once as ``retro(cfe):`` or refuses on Rule 2."""
    committed = False
    try:
        if not vcs.has_uncommitted_changes(worktree):
            return False, None
        to_commit = non_retro_commit_paths(vcs, worktree=worktree, repo_root=repo_root)
        if to_commit:
            vcs.commit_paths(
                worktree,
                to_commit,
                to_redacted_text("marshal: pre-verify WIP checkpoint"),
            )
            committed = True
        if vcs.has_uncommitted_changes(worktree):
            remaining_commit = non_retro_commit_paths(vcs, worktree=worktree, repo_root=repo_root)
            if remaining_commit:
                return committed, "the worktree still has uncommitted changes after the pre-verify WIP commit"
            if not vcs.changed_files(repo_root, worktree, base="HEAD"):
                return committed, "the worktree still has uncommitted changes after the pre-verify WIP commit"
    except VcsCommandError as exc:
        return committed, f"pre-verify WIP commit failed: {exc}"
    return committed, None


def _launch_story_started_ts(folded, run_id: str) -> str | None:
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH):
        if entry.run_id == run_id and entry.phase == Phase.INTENT:
            return entry.ts
    return None


def _hold_landing_from_launch(folded, run_id: str) -> bool:
    """Story 83.18: ``--hold-landing`` journaled on the launch INTENT."""
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH):
        if entry.run_id == run_id and entry.phase == Phase.INTENT:
            return entry.payload.get(HOLD_LANDING_PAYLOAD_KEY) is True
    return False


def _followup_review_from_launch(folded, run_id: str) -> FollowupReview | None:
    """The follow-up review marker this run's own launch INTENT carries (Story 73.1, CAP-281), or ``None``
    for a normal run -- the marker is read back from the journal, never re-derived from a spec the run
    itself rewrites (the review flips its own flag to ``false``)."""
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH):
        if entry.run_id == run_id and entry.phase == Phase.INTENT:
            return FollowupReview.from_intent_payload(entry.payload)
    return None


def _journal_dispatch_timing(
    *,
    fs: FsPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    story_key: str,
    story_started_at: str,
    story_ended_at: str,
    baseline_revision: str,
    final_revision: str,
) -> int:
    record = build_timing_record(
        story_key=story_key,
        story_started_at=story_started_at,
        story_ended_at=story_ended_at,
        baseline_revision=baseline_revision,
        final_revision=final_revision,
    )
    intent_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=story_ended_at,
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_TIMING,
        phase=Phase.INTENT,
        payload=timing_record_payload(record),
    )
    counter += 1
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=story_ended_at,
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_TIMING,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload={**timing_record_payload(record), "ok": True},
    )
    counter += 1
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot journal timing for {run_id!r}: {exc}",
            file=sys.stderr,
        )
    return counter


def _journal_dispatch_preserve(
    *,
    fs: FsPort,
    vcs: VcsPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    story_key: str,
    worktree: Path,
    baseline_head_sha: str,
) -> int:
    try:
        patch_body = vcs.worktree_unified_patch(worktree, baseline_sha=baseline_head_sha)
    except VcsCommandError as exc:
        print(
            f"dispatch supervisor: preserve capture failed for {run_id!r}: {exc}",
            file=sys.stderr,
        )
        return counter
    if not patch_body.strip():
        return counter
    patch_path = failed_patch_path(run_dir, story_key)
    try:
        fs.ensure_dir(patch_path.parent)
        fs.write_text_atomic(patch_path, patch_body)
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot write preserve patch for {run_id!r}: {exc}",
            file=sys.stderr,
        )
        return counter
    preserve_ref = relative_preserve_ref(run_dir, patch_path)
    intent_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_PRESERVE,
        phase=Phase.INTENT,
        payload={"preserve_ref": preserve_ref, "story_key": story_key},
    )
    counter += 1
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_PRESERVE,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload={"preserve_ref": preserve_ref, "ok": True},
    )
    counter += 1
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot journal preserve for {run_id!r}: {exc}",
            file=sys.stderr,
        )
    return counter


def _load_known_story_keys(fs: FsPort, *, repo_root: Path, project_slug: str) -> frozenset[StoryKey]:
    """Every ``StoryKey`` ``project_slug``'s OWN tracked ledger already
    knows about (Story 35.1,
    spec-marshal-templated-merge-subject-cross-project-collision CAP-1) --
    the corroborating, project-scoped signal ``merged_story_keys``'s
    templated-shape branch needs, since the bare "Merge {key} into main"
    subject carries no station token of its own. Degrades to
    ``frozenset()`` (no corroboration available -- fails CLOSED, trusting
    nothing from the templated shape) on a missing or malformed ledger,
    never raises: a ledger read failure must not crash dispatch
    verification, and an empty result is the SAFE direction to degrade in
    (excludes everything from the templated shape) rather than the
    dangerous one (trusting everything, today's bug)."""
    ledger_path = (
        repo_root / "_bmad-output" / "projects" / project_slug / "planning-artifacts" / "sprint-status-ledger.yaml"
    )
    text = fs.read_text(ledger_path)
    if text is None:
        return frozenset()
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return frozenset()
    if not isinstance(data, dict):
        return frozenset()
    development_status = data.get("development_status")
    if not isinstance(development_status, dict):
        return frozenset()
    keys: set[StoryKey] = set()
    for raw_key in development_status:
        if not isinstance(raw_key, str) or raw_key.startswith("epic-"):
            continue
        try:
            keys.add(normalize(raw_key))
        except MalformedStoryKeyError:
            continue
    return frozenset(keys)


def gather_dispatch_git_facts(
    vcs: VcsPort,
    *,
    fs: FsPort,
    repo_root: Path,
    worktree: Path,
    story_key: str,
    project_slug: str,
    baseline_head_sha: str,
    merge_subject_template: str,
    followup_review: FollowupReview | None = None,
) -> DispatchGitFacts:
    """``followup_review`` (Story 73.1, CAP-281): the run's follow-up review marker, read off its launch
    INTENT. The run reviews a story that already landed, so ``story_merged_on_main`` counts only the merge
    subjects that reached ``origin/main`` after ``origin/main``'s tip at launch (``merge_subject_ref``) --
    the story's first merge is not this run's, whatever the worktree's baseline is. A normal run (the
    default, ``None``) reads ``origin/main`` whole.

    Story 83.14: even when corroborated merge subjects name this story, ``story_merged_on_main`` is true
    only when this run's *current* worktree head is on ``origin/main`` — a manual merge of an earlier tip
    while the session keeps committing must not declare completion."""
    current_head_sha = vcs.worktree_head_sha(worktree)
    changed_paths = vcs.changed_files(repo_root, worktree, base=_BASE_REF)
    # Story 22.9: the ONE branch derivation, station-scoped, with the
    # pre-22.9 `marshal/<key>` name still resolved for runs that were
    # already in flight (this run's own `worktree` is the attribution
    # fact, so a legacy branch checked out elsewhere is never adopted).
    #
    # NEVER ask git about a branch the resolver did not resolve.
    # `resolved is None` means no branch of this story's exists in the repo
    # -- a refusal (an unattributable legacy branch), a not-yet-provisioned
    # run, or a branch already retired after landing. `is_branch_merged`
    # shells `git merge-base --is-ancestor`, which exits 128 on a missing
    # ref and so raises `VcsCommandError`; the supervisor loop swallows that
    # and `continue`s inside `while True`, spinning forever without ever
    # judging the run complete. A branch that does not exist is not merged,
    # and that is a fact, not a default.
    resolution = dispatch_core.resolve_dispatch_branch(
        vcs,
        repo_root,
        slug=project_slug,
        story_key=story_key,
        worktree=worktree,
    )
    # `is_branch_merged` shells `git merge-base --is-ancestor branch into`,
    # which is trivially true the instant a dispatch branch is forked from
    # `into`'s current tip -- a freshly-provisioned branch with ZERO new
    # commits IS already "an ancestor of main" (it literally is main's tip),
    # which is not evidence anything was merged, only that nothing has
    # happened yet. Ask the question regardless (existing branch-derivation
    # callers rely on the ask itself), but only trust a "yes" once the
    # branch has actually diverged from its own launch baseline.
    #
    # Story 72.1 (CAP-280): every merge fact reads `origin/main`
    # (`ORIGIN_MAIN`, the full refname), never local `main` -- local `main`
    # moves only when finalize can fast-forward the primary checkout, so a
    # story merged by another route would read unmerged and be landed again.
    raw_branch_merged = (
        vcs.is_branch_merged(repo_root, resolution.resolved, into="main", into_ref=ORIGIN_MAIN)
        if resolution.resolved is not None
        else False
    )
    branch_merged = raw_branch_merged and current_head_sha != baseline_head_sha
    subject_ref = merge_subject_ref(ORIGIN_MAIN, followup_review=followup_review)
    subjects = vcs.commit_subjects(repo_root, subject_ref) if subject_ref is not None else ()
    known_keys = _load_known_story_keys(fs, repo_root=repo_root, project_slug=project_slug)

    def _spec_status_for(candidate_key: StoryKey) -> str | None:
        # Story 51.7/CAP-255: a station-branch match reached through a
        # GitHub PR-merge subject only corroborates a landing when the
        # key's tracked spec reads `status: done` on origin/main -- a
        # mint/fallout/fix PR merges it ready/backlog, not done. Fails
        # closed (never corroborates) on any git read failure.
        try:
            spec_text = dispatch_core.spec_text_at_ref(vcs, repo_root, project_slug, str(candidate_key))
        except VcsCommandError:
            return None
        return promotion_core.read_spec_status(spec_text)

    merged_keys = promotion_core.corroborated_merged_story_keys(
        subjects,
        merge_subject_template,
        project_slug,
        spec_status_for=_spec_status_for,
        known_keys=known_keys,
    )
    story_merged = normalize(story_key) in merged_keys
    if story_merged and not run_head_reached_ref(vcs, repo_root, current_head_sha, ORIGIN_MAIN):
        story_merged = False
    return DispatchGitFacts(
        baseline_head_sha=baseline_head_sha,
        current_head_sha=current_head_sha,
        changed_paths=changed_paths,
        branch_merged=branch_merged,
        story_merged_on_main=story_merged,
    )


def _landing_outcome_verdict(folded, run_id: str) -> str | None:
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAND):
        if entry.run_id != run_id or entry.phase != Phase.OUTCOME:
            continue
        if not entry.payload.get("ok"):
            return None
        verdict_val = entry.payload.get("verdict")
        return verdict_val if isinstance(verdict_val, str) else None
    return None


def _landing_succeeded(folded, run_id: str) -> bool:
    return landing_journal_indicates_complete(_landing_outcome_verdict(folded, run_id))


def _completed_verify_fix_outcome(folded, run_id: str):
    """The run's first fix-turn OUTCOME when it reads ``ok`` -- the turn's session finished -- else ``None``."""
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFY_FIX):
        if entry.run_id == run_id and entry.phase == Phase.OUTCOME:
            return entry if entry.payload.get("ok") else None
    return None


def _verify_fix_turn_completed(folded, run_id: str) -> bool:
    return _completed_verify_fix_outcome(folded, run_id) is not None


def _fix_turn_park_journaled(folded, run_id: str, fix_intent_id: dict[str, object] | None) -> bool:
    """Whether MRS-DISP-060 is already journaled for the fix-turn INTENT ``fix_intent_id`` names (Story 85.2)."""
    return any(
        entry.run_id == run_id
        and entry.phase == Phase.OBSERVATION
        and entry.payload.get("code") == FIX_TURN_REVERIFY_REFUSED_CODE
        and entry.payload.get("fix_intent_id") == fix_intent_id
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFY_FIX)
    )


def _verify_fix_turn_journaled(folded, run_id: str) -> bool:
    return any(
        entry.run_id == run_id and entry.phase == Phase.OUTCOME
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFY_FIX)
    )


def _verification_already_journaled(folded, run_id: str) -> bool:
    outcomes = [
        entry
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFICATION)
        if entry.run_id == run_id and entry.phase == Phase.OUTCOME
    ]
    if not outcomes:
        return False
    if len(outcomes) >= 2:
        return True
    if _verify_fix_turn_completed(folded, run_id):
        return False
    return True


def _dispatch_push_already_journaled(folded, run_id: str) -> bool:
    return any(
        entry.run_id == run_id and entry.phase == Phase.OUTCOME
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_PUSH)
    )


def _dispatch_push_succeeded(folded, run_id: str) -> bool:
    """Whether the run's first journaled push OUTCOME reads ``pushed`` -- the record finalize reads (Story 85.2)."""
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_PUSH):
        if entry.run_id == run_id and entry.phase == Phase.OUTCOME:
            return entry.payload.get("outcome") == "pushed"
    return False


def _landing_already_journaled(folded, run_id: str) -> bool:
    return any(
        entry.run_id == run_id and entry.phase == Phase.OUTCOME
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAND)
    )


def _verification_outcome_verdict(folded, run_id: str) -> str | None:
    for entry in reversed(folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFICATION)):
        if entry.run_id == run_id and entry.phase == Phase.OUTCOME:
            verdict_val = entry.payload.get("verdict")
            if isinstance(verdict_val, str):
                return verdict_val
    return None


def _verification_failed_gate(folded, run_id: str) -> str | None:
    for entry in reversed(folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFICATION)):
        if entry.run_id == run_id and entry.phase == Phase.OUTCOME:
            gate = entry.payload.get("failed_gate")
            if isinstance(gate, str):
                return gate
    return None


def _journal_finalize_attempt(
    *,
    fs: FsPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    story_key: str,
    worktree: Path,
    trigger: str,
    committed: bool,
    pushed: bool,
    verified: bool,
    ok: bool,
    failed_step: str | None = None,
    failed_message: str | None = None,
) -> int:
    """Journal one supervisor finalize attempt (Story 28.24, CAP-7)."""
    intent_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_FINALIZE,
        phase=Phase.INTENT,
        payload={
            "story_key": story_key,
            "worktree_path": str(worktree),
            "trigger": trigger,
        },
    )
    counter += 1
    outcome_payload: dict[str, object] = {
        "story_key": story_key,
        "worktree_path": str(worktree),
        "trigger": trigger,
        "committed": committed,
        "pushed": pushed,
        "verified": verified,
        "ok": ok,
    }
    if failed_step is not None:
        outcome_payload["failed_step"] = failed_step
    if failed_message is not None:
        outcome_payload["failed_message"] = failed_message
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_FINALIZE,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload=outcome_payload,
    )
    counter += 1
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot journal finalize for {run_id!r}: {exc}",
            file=sys.stderr,
        )
    return counter


def _worktree_story_spec(
    *, fs: FsPort, repo_root: Path, slug: str, story_key: str, worktree: Path
) -> tuple[str | None, str | None]:
    """Resolve the story's tracked spec as seen by the worktree (Story 51.4,
    spec-pyforge-marshal CAP-252).

    Returns ``(worktree_relative_path, text)`` -- either half is ``None``
    when the spec cannot be resolved, relocated, or read; callers then
    treat "no signal" as not-blocked, never as blocked.
    """
    spec_path = dispatch_core.resolve_story_spec_path(repo_root, slug, story_key)
    if spec_path is None:
        return None, None
    try:
        worktree_spec_path = dispatch_core.relocated_spec_path(spec_path, repo_root, worktree)
    except ValueError:
        return None, None
    text = fs.read_text(worktree_spec_path)
    try:
        relative = str(worktree_spec_path.resolve().relative_to(worktree.resolve()))
    except ValueError:
        relative = None
    return relative, text


def _spec_land_block_reason(
    *,
    fs: FsPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
    git_facts: DispatchGitFacts,
    followup_review: FollowupReview | None = None,
) -> str | None:
    """Non-``None`` when the worktree spec blocks verify/land (Story 51.4).

    A deliberate ``status: blocked`` always blocks (the 27.3 incident); so
    does a diff that collapses to the tracked spec file itself -- narration,
    not work (the 51.3 incident: a harness-ceiling termination that only
    ever rewrote its own spec's ``ready -> in-progress`` flip). A follow-up
    review run (Story 73.1, CAP-281) is the exception to the second: a review
    that patches nothing changes only its own spec, which is its record.
    """
    spec_relative_path, spec_text = _worktree_story_spec(
        fs=fs,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        worktree=worktree,
    )
    if spec_text is None:
        return None
    if not (
        parse_spec_status(spec_text) == "blocked"
        or is_spec_only_narration(
            git_facts.changed_paths, narration_spec_path(spec_relative_path, followup_review=followup_review)
        )
    ):
        return None
    return parse_blocking_condition(spec_text) or ("harness produced no changes beyond the tracked spec")


def _journal_dispatch_blocked(
    *,
    fs: FsPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    story_key: str,
    worktree: Path,
    reason: str,
) -> int:
    """Journal the supervisor halting before verify/land (Story 51.4, CAP-252):
    the worktree spec is ``blocked``, or the whole diff is spec-only
    narration with no code progress behind it.
    """
    intent_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_BLOCKED,
        phase=Phase.INTENT,
        payload={"story_key": story_key, "worktree_path": str(worktree)},
    )
    counter += 1
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_BLOCKED,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload={"story_key": story_key, "reason": reason, "ok": True},
    )
    counter += 1
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot journal blocked halt for {run_id!r}: {exc}",
            file=sys.stderr,
        )
    return counter


def _blocked_halt_reason(
    *,
    fs: FsPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
    git_facts: DispatchGitFacts,
) -> tuple[str | None, bool]:
    """Classify an unexplained session exit against the worktree's own tracked
    spec (Story 51.11, spec-pyforge-marshal CAP-258).

    Returns ``(reason, stale)``:
    - ``(reason, False)`` -- the worktree spec reads ``status: blocked`` with
      an ``## Auto Run Result`` whose ``baseline_revision`` matches this
      run's own baseline: a genuine self-halt the session never got to
      commit. ``reason`` is the spec's own blocking condition, never
      invented (Always bullet 3 -- no self-report is trusted, only the spec
      file, git status and the process).
    - ``(None, True)`` -- the spec reads ``blocked`` but its Auto Run
      Result's ``baseline_revision`` does not match this run: a stale spec
      left over from an earlier dispatch pass on the same story (Never
      bullet 3) -- advisory only, never a block.
    - ``(None, False)`` -- no reliable blocked signal (missing spec, a
      different status, no Auto Run Result section, or no recorded
      baseline to verify against).
    """
    _, spec_text = _worktree_story_spec(
        fs=fs,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        worktree=worktree,
    )
    if spec_text is None or parse_spec_status(spec_text) != "blocked":
        return None, False
    if not has_auto_run_result(spec_text):
        return None, False
    baseline = parse_baseline_revision(spec_text)
    if baseline is None:
        return None, False
    if baseline != git_facts.baseline_head_sha:
        return None, True
    reason = parse_blocking_condition(spec_text) or ("harness halted on its own tracked spec's status: blocked")
    return reason, False


def _attempted_change_patch_paths(worktree: Path) -> tuple[Path, ...]:
    """``*attempted-change*.patch`` files under the worktree, excluding the
    backlinked ``implementation-artifacts`` Tier-3 store (Story 51.11).

    That store already survives worktree teardown on the primary checkout
    and must never be git-tracked (AGENTS.md: "only implementation-
    artifacts/ is the backlinked Tier-3 store"; "nothing there may be
    git-tracked"). A patch dropped anywhere else in the worktree has no
    such protection, so it is committed onto the dispatch branch alongside
    the blocked spec so it survives teardown too.
    """
    found: list[Path] = []
    for candidate in worktree.rglob("*attempted-change*.patch"):
        try:
            relative = candidate.relative_to(worktree)
        except ValueError:
            continue
        if "implementation-artifacts" in relative.parts:
            continue
        found.append(candidate)
    return tuple(sorted(found))


def _commit_and_journal_blocked_halt(
    *,
    fs: FsPort,
    vcs: CommittingVcs,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
    reason: str,
) -> tuple[int, bool]:
    """Commit the worktree's uncommitted blocked-halt state onto the dispatch
    branch and journal ``dispatch-blocked`` (Story 51.11).

    Returns ``(counter, committed)``. ``committed`` is ``False`` on any git
    failure, or when there is nothing to commit -- the classifier must never
    claim a durable blocked record without one (narrows, never widens): the
    caller must not adopt the ``blocked`` verdict unless this returns
    ``True``.
    """
    patch_paths = _attempted_change_patch_paths(worktree)
    rel_patch = tuple(p.relative_to(worktree).as_posix() for p in patch_paths)
    try:
        paths_to_commit = non_retro_commit_paths(vcs, worktree=worktree, extra_paths=rel_patch, repo_root=repo_root)
    except VcsCommandError:
        return counter, False
    if not paths_to_commit:
        return counter, False
    try:
        vcs.commit_paths(
            worktree,
            paths_to_commit,
            to_redacted_text("marshal: supervisor blocked halt (Story 51.11)"),
        )
    except VcsCommandError:
        return counter, False
    counter = _journal_dispatch_blocked(
        fs=fs,
        run_dir=run_dir,
        run_id=run_id,
        writer_id=writer_id,
        counter=counter,
        story_key=story_key,
        worktree=worktree,
        reason=reason,
    )
    return counter, True


def _promote_blocked_twin(
    *,
    fs: FsPort,
    vcs: CommittingVcs,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
) -> int:
    """Best-effort: push the primary's tracked twin of the story spec to
    ``blocked`` so the fleet picture shows it (Story 51.11).

    Never raises -- the branch commit in ``_commit_and_journal_blocked_halt``
    is the load-bearing durability guarantee; this is an additional
    visibility promotion and must not unwind an already-committed blocked
    verdict on failure. Pushes via a throwaway detached worktree onto
    ``origin/main`` (AGENTS.md: never commit on the shared checkout) --
    exactly like ``cli/land.py``'s sprint-status-ledger promotion, and like
    it under the adapter's checked, journaled preflight opt-out naming the
    story (Story 68.1, CAP-277). A publish that fails is journaled as a
    WARN observation naming the story and the error (never silent); the
    verdict is untouched. Returns the journal counter, advanced by the
    entry written (unchanged when nothing was)."""
    spec_path = dispatch_core.resolve_story_spec_path(repo_root, slug, story_key)
    if spec_path is None:
        return counter
    try:
        worktree_spec_path = dispatch_core.relocated_spec_path(spec_path, repo_root, worktree)
    except ValueError:
        return counter
    try:
        worktree_text = fs.read_text(worktree_spec_path)
    except FsError:
        return counter
    if worktree_text is None:
        return counter
    try:
        primary_text = fs.read_text(spec_path)
    except FsError:
        return counter
    promoted = blocked_twin_promotion_text(primary_text=primary_text, worktree_text=worktree_text)
    if promoted is None:
        return counter
    try:
        canonical_root = dispatch_core.canonical_repo_root(repo_root)
        relative = spec_path.resolve().relative_to(canonical_root)
    except ValueError, OSError:
        return counter
    try:
        vcs.commit_paths_onto_remote_tip(
            canonical_root,
            remote=VcsRef("origin"),
            ref=VcsRef("main"),
            writes=((relative.as_posix(), promoted),),
            message=to_redacted_text("marshal: promote blocked spec twin (Story 51.11)"),
            preflight_skip_reason=to_redacted_text(f"marshal blocked-twin promotion for story {story_key}"),
        )
    except VcsCommandError as exc:
        finding = Finding(
            code="MRS-LAND-011",
            severity=Severity.WARN,
            message=(
                f"blocked spec twin for story {story_key!r} could not be published to origin/main; "
                f"the fleet picture will not show it blocked until it is: {exc}"
            ),
        )
        entry = build_entry(
            id=JournalEntryId(writer_id, counter),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=_BLOCKED_TWIN_PUBLISH_KIND,
            phase=Phase.OBSERVATION,
            payload={"story_key": story_key, "finding": finding.to_json_dict()},
        )
        try:
            _append_entry(fs, run_dir, entry, fsync=False)
        except FsError as fs_exc:
            print(
                f"dispatch supervisor: cannot journal blocked-twin publish failure for {run_id!r}: {fs_exc}",
                file=sys.stderr,
            )
        return counter + 1
    return counter


def _launch_context_from_folded(
    folded, run_id: str
) -> tuple[str | None, str | None, dict[str, object] | None, str | None]:
    profile_name: str | None = None
    model: str | None = None
    wire_layer: dict[str, object] | None = None
    harness_session_id: str | None = None
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH):
        if entry.run_id != run_id:
            continue
        if entry.phase == Phase.INTENT:
            raw_model = entry.payload.get("model")
            model = raw_model if isinstance(raw_model, str) else None
            context = entry.payload.get("context")
            if isinstance(context, dict):
                wire = context.get("wire")
                wire_layer = wire if isinstance(wire, dict) else None
        elif entry.phase == Phase.OUTCOME:
            raw_profile = entry.payload.get("harness_profile")
            profile_name = raw_profile if isinstance(raw_profile, str) else None
            raw_hsid = entry.payload.get("harness_session_id")
            if isinstance(raw_hsid, str) and raw_hsid.strip():
                harness_session_id = raw_hsid.strip()
    return profile_name, model, wire_layer, harness_session_id


def _journal_sidecars(*, fs: FsPort, run_dir: Path) -> dict[str, str | None]:
    text = fs.read_text(run_dir / _JOURNAL_FILENAME)
    if text is None:
        return {}
    return sidecar_texts_for_lines(
        text.splitlines(),
        read_sidecar=lambda ref: fs.read_text(run_dir / ref),
    )


def _failed_commands_from_verification_journal(
    folded,
    run_id: str,
    *,
    fs: FsPort,
    run_dir: Path,
) -> tuple[dict[str, object], ...]:
    sidecars = _journal_sidecars(fs=fs, run_dir=run_dir)
    for entry in reversed(folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFICATION)):
        if entry.run_id != run_id or entry.phase != Phase.OUTCOME:
            continue
        return resolve_verify_failed_commands_from_payload(entry.payload, sidecars=sidecars)
    return ()


class _FixTurnPublisherHeartbeat:
    """The run publisher's heartbeat during a fix turn (Story 85.3): at most one call per ``interval_s`` -- the
    wait polls every second, the publisher needs one call well inside the portal's 300 s -- and every call, from
    the supervisor's thread or the re-verification's progress thread, made under one lock, so two publisher calls
    never overlap."""

    def __init__(self, publish: Callable[[], None], *, interval_s: float | None = None) -> None:
        self._publish = publish
        self._interval_s = _FIX_TURN_PUBLISH_INTERVAL_S if interval_s is None else interval_s
        self._lock = threading.Lock()
        self._last: float | None = None

    def __call__(self) -> None:
        with self._lock:
            now = time.monotonic()
            if self._last is not None and now - self._last < self._interval_s:
                return
            self._last = now
            self._publish()


@dataclass(frozen=True)
class _FixTurnResult:
    """What one pass of ``_maybe_run_verify_fix_turn`` did (Story 85.2).

    ``failed_step``/``failed_message`` carry a shell failure the finalize record must report the way it reports
    its own commit step (``ok: false``) -- a fix turn's edits that could not be committed, or a fix-turn INTENT
    that could not be journaled."""

    counter: int
    verified: bool
    folded: object
    committed: bool = False
    failed_step: str | None = None
    failed_message: str | None = None


def _fix_turn_head_before(intent_payload: dict[str, object]) -> str | None:
    raw = intent_payload.get("worktree_head_before_turn")
    return raw if isinstance(raw, str) and raw else None


def _reconcile_fix_turn_spec_surface(
    *,
    vcs: CommittingVcs,
    process: ProcessPort,
    repo_root: Path,
    worktree: Path,
    slug: str,
    story_key: str,
    run_id: str,
    head_before_turn: str,
    fix_intent_id: dict[str, object] | None,
    journal_fix: Callable[[Phase, dict[str, object]], None],
) -> tuple[bool, str | None]:
    """Story 85.5: reconcile spec-surface drift on the paths this fix turn committed.

    Returns ``(ok, refusal_message)``. ``ok`` is False when the reconcile cannot be applied and the
    supervisor must park without re-verifying."""
    try:
        fix_turn_paths = frozenset(vcs.changed_files(repo_root, worktree, base=head_before_turn))
    except VcsCommandError as exc:
        message = f"cannot list the fix turn's changed paths for spec-surface reconcile: {exc}"
        journal_fix(
            Phase.OBSERVATION,
            {
                "ok": False,
                "step": "reconcile",
                "error": message,
                "fix_intent_id": fix_intent_id,
            },
        )
        return False, message

    if not fix_turn_paths:
        journal_fix(
            Phase.OBSERVATION,
            {
                "ok": True,
                "step": "reconcile",
                "skipped": True,
                "reason": "the fix turn changed no paths since its recorded HEAD",
                "fix_intent_id": fix_intent_id,
            },
        )
        return True, None

    head_branch = dispatch_core.dispatch_worktree_branch(slug, story_key)
    reconcile_outcome = _reconcile_spec_surface_drift(
        git_repo_root=repo_root,
        worktree=worktree,
        head_branch=head_branch,
        key=identity_core.normalize(story_key),
        run_id=run_id,
        vcs=vcs,
        process=process,
        own_changed_paths=fix_turn_paths,
        push_when_done=False,
        foreign_drift_refuses=False,
    )
    if reconcile_outcome.refuse:
        finding = reconcile_outcome.finding
        message = finding.message if finding is not None else "spec-surface reconcile refused"
        journal_fix(
            Phase.OBSERVATION,
            {
                "ok": False,
                "step": "reconcile",
                "error": message,
                "fix_intent_id": fix_intent_id,
            },
        )
        return False, message

    payload: dict[str, object] = {
        "ok": True,
        "step": "reconcile",
        "outcome": "reconciled" if reconcile_outcome.finding is not None else "nothing_to_reconcile",
        "paths": sorted(fix_turn_paths),
        "fix_intent_id": fix_intent_id,
    }
    if reconcile_outcome.finding is not None:
        payload["finding"] = reconcile_outcome.finding.to_json_dict()
    journal_fix(Phase.OBSERVATION, payload)
    return True, None


def _journal_fix_turn_park(
    *,
    fs: FsPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    folded,
    fix_intent_id: dict[str, object] | None,
) -> int:
    """Journal MRS-DISP-060 -- verification still refused after the one fix turn, the story parked -- naming the
    still-failing command and the fix-turn INTENT it belongs to (Story 85.2 AC2). Returns the next counter."""
    failed_after = _failed_commands_from_verification_journal(folded, run_id, fs=fs, run_dir=run_dir)
    # A verification OUTCOME written with the flag off keeps main's five keys and carries no failed_commands, so a
    # park owed after a flag flip names no command (failed_command None); the message still says the story parked.
    failed_command = str(failed_after[0]["command"]) if failed_after and failed_after[0].get("command") else None
    finding = Finding(
        code=FIX_TURN_REVERIFY_REFUSED_CODE,
        severity=Severity.ERROR,
        message=fix_turn_park_message(failed_command=failed_command),
    )
    entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=Phase.OBSERVATION,
        payload={
            "ok": False,
            "code": FIX_TURN_REVERIFY_REFUSED_CODE,
            "failed_command": failed_command,
            "finding": finding.to_json_dict(),
            "fix_intent_id": fix_intent_id,
        },
    )
    try:
        _append_entry(fs, run_dir, entry, fsync=True)
    except FsError:
        pass
    return counter + 1


def _maybe_run_verify_fix_turn(
    *,
    fs: FsPort,
    vcs: CommittingVcs,
    process: ProcessPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
    git_facts: DispatchGitFacts,
    folded,
    session_alive: bool,
    publish_heartbeat: Callable[[], None] | None = None,
) -> _FixTurnResult:
    """Run at most one fix turn; re-verify once.

    Story 85.2: a fix turn a killed supervisor left in flight -- an open INTENT -- is settled here and never
    relaunched. With the flag on, its session is waited for within what is left of its budget (measured from the
    INTENT's UTC timestamp) and stopped once that is spent; with the flag off it is only stopped, journaled and
    parked -- never committed, re-verified or landed. An INTENT that never recorded a pid is closed."""
    v_outcome = _verification_outcome_verdict(folded, run_id)
    if publish_heartbeat is not None:
        publish_heartbeat = _FixTurnPublisherHeartbeat(publish_heartbeat)
    flag_enabled, flag_warning = verify_fix_loop_enabled(repo_root=repo_root)
    if flag_warning is not None:
        warn_entry = build_entry(
            id=JournalEntryId(writer_id, counter),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
            phase=Phase.OBSERVATION,
            payload={"warning": flag_warning, "ok": True},
        )
        counter += 1
        try:
            _append_entry(fs, run_dir, warn_entry, fsync=False)
        except FsError:
            pass

    def _journal_fix(phase: Phase, payload: dict[str, object], *, intent_id: JournalEntryId | None = None) -> None:
        nonlocal counter
        entry = build_entry(
            id=JournalEntryId(writer_id, counter),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
            phase=phase,
            intent_id=intent_id,
            payload=payload,
        )
        counter += 1
        try:
            _append_entry(fs, run_dir, entry, fsync=phase is not Phase.OUTCOME)
        except FsError:
            pass

    head_before_turn: str | None = None
    in_flight = in_flight_verify_fix_turn(folded, run_id)
    if in_flight is not None:
        intent_entry = in_flight.intent
        started_at = in_flight.started_at
        head_before_turn = _fix_turn_head_before(intent_entry.payload)
        if in_flight.session_pid is None:
            # Review M3: the launch never recorded a pid -- nothing to wait for or stop. Close the INTENT so no
            # reader keeps reading the turn in flight; the turn is never relaunched.
            _journal_fix(
                Phase.OUTCOME,
                {
                    "ok": False,
                    "code": FIX_TURN_START_FAILED_CODE,
                    "error": "fix-turn session pid not recorded; the turn is closed, never relaunched",
                },
                intent_id=intent_entry.id,
            )
            return _FixTurnResult(counter=counter, verified=False, folded=folded)
        fix_pid = in_flight.session_pid
        if not flag_enabled:
            stopped = fix_session_alive(process, fix_pid, launched_at=started_at)
            if stopped:
                terminate_process_group(fix_pid, process=process)
            _journal_fix(
                Phase.OUTCOME,
                {
                    "ok": False,
                    "session_pid": fix_pid,
                    "stopped": stopped,
                    "reason": "verify_fix_loop flag off: the in-flight fix turn is stopped and the story parked",
                },
                intent_id=intent_entry.id,
            )
            return _FixTurnResult(counter=counter, verified=False, folded=folded)
        fix_policy = resolve_verify_fix_settings(compose_dispatch_policy(slug, repo_root))
        raw_budget = intent_entry.payload.get("wall_clock_budget_s")
        budget_s = (
            float(raw_budget)
            if isinstance(raw_budget, (int, float)) and not isinstance(raw_budget, bool)
            else fix_policy.wall_clock_seconds
        )
        wait_budget_s = fix_turn_remaining_budget_s(budget_s=budget_s, started_at=started_at, now=_now_utc())
    else:
        failed_rows = _failed_commands_from_verification_journal(folded, run_id, fs=fs, run_dir=run_dir)
        failed_cmds = tuple(
            FailedVerifyCommand(
                command=str(row.get("command", "")),
                stdout=str(row.get("output_tail") or ""),
                stderr="",
                exit_code=row.get("exit_code") if isinstance(row.get("exit_code"), int) else None,
            )
            for row in failed_rows
            if row.get("command")
        )
        decision = decide_verify_fix_turn(
            flag_enabled=flag_enabled,
            verification_verdict=v_outcome,
            has_git_progress=has_git_progress(git_facts),
            fix_turn_already_ran=_verify_fix_turn_journaled(folded, run_id),
            session_alive=session_alive,
            has_failed_commands=bool(failed_cmds),
            verification_failed_gate=_verification_failed_gate(folded, run_id),
        )
        if not decision.run:
            # Final landing review L1: a supervisor killed after the turn's ok OUTCOME but before its re-verify was
            # journaled leaves the re-verify to this pass's normal finalize. When that reads refused, the park is
            # still owed its MRS-DISP-060 -- once per INTENT, never a second turn. Only a turn the flag let run
            # can have that OUTCOME, so a run that never had the flag on never reaches this.
            completed = _completed_verify_fix_outcome(folded, run_id)
            if completed is not None and v_outcome == DispatchVerificationVerdict.REFUSED.value:
                owed_ref = fix_intent_ref(completed.intent_id) if completed.intent_id is not None else None
                if not _fix_turn_park_journaled(folded, run_id, owed_ref):
                    counter = _journal_fix_turn_park(
                        fs=fs,
                        run_dir=run_dir,
                        run_id=run_id,
                        writer_id=writer_id,
                        counter=counter,
                        folded=folded,
                        fix_intent_id=owed_ref,
                    )
            return _FixTurnResult(counter=counter, verified=False, folded=folded)

        effective = compose_dispatch_policy(slug, repo_root)
        fix_policy = resolve_verify_fix_settings(effective)
        budget_env = dispatch_core.build_budget_env(effective)
        profile_name, model, wire_layer, harness_session_id = _launch_context_from_folded(folded, run_id)
        preference: tuple[str, ...] = tuple(effective.harness_preference.value)
        if profile_name and profile_name in preference:
            preference = (profile_name, *(p for p in preference if p != profile_name))
        harness = BmadBuildHarness()
        resolution = harness.binary_present(preference, repo_root=repo_root)
        _spec_relative, story_spec_text = _worktree_story_spec(
            fs=fs, repo_root=repo_root, slug=slug, story_key=story_key, worktree=worktree
        )
        prompt = build_verify_fix_prompt(
            failed_cmds,
            output_tail_bytes=fix_policy.output_tail_bytes,
            story_spec_text=story_spec_text,
        )
        launch_mode = choose_verify_fix_launch_mode(
            resume_argv=resolution.spec.resume_argv if resolution.spec else None,
            harness_session_id=harness_session_id,
            launch_profile=profile_name,
            resolved_profile=resolution.profile,
        )
        fix_log = run_dir / "verify-fix.log"
        started_at = _now_utc()
        wait_budget_s = fix_policy.wall_clock_seconds
        head_before_turn = vcs.worktree_head_sha(worktree)
        intent_entry = build_entry(
            id=JournalEntryId(writer_id, counter),
            ts=_format_entry_ts(started_at),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
            phase=Phase.INTENT,
            payload={
                "launch_mode": launch_mode.value,
                "prompt_bytes": len(prompt.encode("utf-8")),
                "failed_command_count": len(failed_cmds),
                "wall_clock_budget_s": fix_policy.wall_clock_seconds,
                "worktree_head_before_turn": head_before_turn,
            },
        )
        counter += 1
        try:
            _append_entry(fs, run_dir, intent_entry, fsync=True)
        except FsError as exc:
            # Review M4: journal every step before it acts -- an INTENT that is not on disk would leave a
            # running session no restarted supervisor can find, wait for or stop. No launch.
            message = f"cannot journal the fix-turn INTENT, so no fix turn is launched: {exc}"
            print(f"dispatch supervisor: {message}", file=sys.stderr)
            return _FixTurnResult(
                counter=counter,
                verified=False,
                folded=folded,
                failed_step="verify-fix-intent",
                failed_message=message,
            )

        launch_error: str | None = None
        launched_pid: int | None = None
        try:
            launch = harness.dispatch_verify_fix(
                worktree,
                resolution=resolution,
                prompt=prompt,
                model=model,
                log_path=fix_log,
                wire_layer=wire_layer,
                launch_mode=launch_mode.value,
                project_slug=slug,
                budget_env=budget_env,
                harness_session_id=harness_session_id or "",
                run_dir=run_dir,
            )
            launched_pid = launch.pid
        except BuildHarnessError as exc:
            launch_error = str(exc)

        if launch_error is not None or launched_pid is None:
            _journal_fix(
                Phase.OUTCOME,
                {
                    "ok": False,
                    "code": FIX_TURN_START_FAILED_CODE,
                    "error": launch_error or "launch returned no pid",
                    "elapsed_s": (_now_utc() - started_at).total_seconds(),
                },
                intent_id=intent_entry.id,
            )
            return _FixTurnResult(counter=counter, verified=False, folded=folded)
        fix_pid = launched_pid
        # The pid a restarted supervisor waits for or stops (review H1/M3), journaled before the wait.
        _journal_fix(
            Phase.OBSERVATION,
            {"session_pid": fix_pid, "ok": True, "fix_intent_id": fix_intent_ref(intent_entry.id)},
        )

    journal_heartbeat_at: float | None = None

    def _fix_turn_heartbeat() -> None:
        # Called on every one-second poll of the wait: the journal heartbeat is written at most once per
        # `_TICK_SECONDS` (Story 85.4); the publisher heartbeat throttles itself (`_FixTurnPublisherHeartbeat`).
        nonlocal counter, journal_heartbeat_at
        now = time.monotonic()
        if journal_heartbeat_at is None or now - journal_heartbeat_at >= _TICK_SECONDS:
            journal_heartbeat_at = now
            counter = _journal_heartbeat(
                fs=fs,
                run_dir=run_dir,
                run_id=run_id,
                writer_id=writer_id,
                counter=counter,
                session_alive=False,
                git_facts=git_facts,
            )
        if publish_heartbeat is not None:
            publish_heartbeat()

    wait_result: ProcessWaitResult = wait_for_process(
        process,
        fix_pid,
        timeout_s=wait_budget_s,
        on_poll=_fix_turn_heartbeat,
        launched_at=started_at,
    )
    elapsed = (_now_utc() - started_at).total_seconds()
    if not wait_result.exited:
        stop_result: TerminateProcessGroupResult = terminate_process_group(fix_pid, process=process)
        _journal_fix(
            Phase.OBSERVATION,
            {
                "ok": True,
                "step": "terminate_process_group",
                "session_pid": fix_pid,
                "signalled_term": stop_result.signalled_term,
                "signalled_kill": stop_result.signalled_kill,
                "reaped": stop_result.reaped,
                "returncode": stop_result.returncode,
            },
        )
        _journal_fix(
            Phase.OUTCOME,
            {"ok": False, "code": FIX_TURN_TIMEOUT_CODE, "session_pid": fix_pid, "elapsed_s": elapsed},
            intent_id=intent_entry.id,
        )
        return _FixTurnResult(counter=counter, verified=False, folded=folded)

    # A known non-zero exit fails the turn. An unknown exit code -- always the case for a session a restarted
    # supervisor did not launch, whose exit status only its parent could reap -- leaves the decision to the
    # re-verification, the same oracle every landing answers to.
    session_ok = wait_result.returncode in (0, None)
    _journal_fix(
        Phase.OUTCOME,
        {
            "ok": session_ok,
            "session_pid": fix_pid,
            "session_returncode": wait_result.returncode,
            "elapsed_s": elapsed,
            "launch_mode": intent_entry.payload.get("launch_mode"),
        },
        intent_id=intent_entry.id,
    )
    if not session_ok:
        return _FixTurnResult(counter=counter, verified=False, folded=folded)

    committed, commit_refusal = _commit_pre_verify_wip(vcs, repo_root=repo_root, worktree=worktree)
    if commit_refusal is not None:
        # Review H2: never re-verify (or land) a tree whose edits are not committed -- park, the way the
        # finalize commit step does.
        _journal_fix(
            Phase.OBSERVATION,
            {
                "ok": False,
                "step": "commit",
                "error": commit_refusal,
                "fix_intent_id": fix_intent_ref(intent_entry.id),
            },
        )
        return _FixTurnResult(
            counter=counter,
            verified=False,
            folded=folded,
            committed=committed,
            failed_step="commit",
            failed_message=commit_refusal,
        )

    if head_before_turn is not None:
        reconcile_ok, reconcile_refusal = _reconcile_fix_turn_spec_surface(
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            worktree=worktree,
            slug=slug,
            story_key=story_key,
            run_id=run_id,
            head_before_turn=head_before_turn,
            fix_intent_id=fix_intent_ref(intent_entry.id),
            journal_fix=_journal_fix,
        )
        if not reconcile_ok:
            return _FixTurnResult(
                counter=counter,
                verified=False,
                folded=folded,
                committed=committed,
                failed_step="reconcile",
                failed_message=reconcile_refusal,
            )

    if publish_heartbeat is not None:
        publish_heartbeat()

    counter = _run_and_journal_verification(
        fs=fs,
        vcs=vcs,
        process=process,
        run_dir=run_dir,
        run_id=run_id,
        writer_id=writer_id,
        counter=counter,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        worktree=worktree,
        on_progress=publish_heartbeat,
    )
    if publish_heartbeat is not None:
        publish_heartbeat()
    text = fs.read_text(run_dir / _JOURNAL_FILENAME)
    if text is not None:
        folded = _fold_dispatch_journal(fs, run_dir, text)
    v_after = _verification_outcome_verdict(folded, run_id)
    verified = v_after == DispatchVerificationVerdict.VERIFIED.value
    if not verified:
        counter = _journal_fix_turn_park(
            fs=fs,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            folded=folded,
            fix_intent_id=fix_intent_ref(intent_entry.id),
        )
    return _FixTurnResult(counter=counter, verified=verified, folded=folded, committed=committed)


def verify_fix_turn_in_flight(folded, run_id: str) -> bool:
    """True when a fix-turn INTENT is open without a terminal OUTCOME (Story 85.2)."""
    return pending_verify_fix_intent(folded, run_id) is not None


def _run_supervisor_finalize_sequence(
    *,
    fs: FsPort,
    vcs: CommittingVcs,
    process: ProcessPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
    git_facts: DispatchGitFacts,
    session_log: str | None,
    merge_subject_template: str,
    folded,
    followup_review: FollowupReview | None = None,
    publish_heartbeat: Callable[[], None] | None = None,
) -> tuple[int, bool]:
    """Commit, push, and verify harness-leftover work (Story 28.24).

    ``followup_review`` (Story 73.1, CAP-281) is the run's follow-up review marker, or ``None``: it scopes
    the repository facts this sequence re-gathers and the spec-only block check to the run's own branch."""
    trigger = classify_finalize_trigger(session_log).value
    if pending_verify_fix_intent(folded, run_id) is not None:
        # Story 85.2 (review H1): a fix turn a killed supervisor left in flight is settled FIRST -- waited for or
        # stopped -- before the leftover commit below could commit the half-written tree its session may still
        # be editing. Push, the spec block check and the first verification all ran on the pass that launched it.
        fix = _maybe_run_verify_fix_turn(
            fs=fs,
            vcs=vcs,
            process=process,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            repo_root=repo_root,
            slug=slug,
            story_key=story_key,
            worktree=worktree,
            git_facts=git_facts,
            folded=folded,
            session_alive=False,
            publish_heartbeat=publish_heartbeat,
        )
        counter = _journal_finalize_attempt(
            fs=fs,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=fix.counter,
            story_key=story_key,
            worktree=worktree,
            trigger=trigger,
            committed=fix.committed or git_facts.current_head_sha != git_facts.baseline_head_sha,
            pushed=_dispatch_push_succeeded(fix.folded, run_id),
            verified=fix.verified,
            ok=fix.failed_step is None,
            failed_step=fix.failed_step,
            failed_message=fix.failed_message,
        )
        return counter, fix.failed_step is None
    committed = False
    pushed = False
    verified = False
    failed_step: str | None = None
    failed_message: str | None = None
    try:
        if vcs.has_uncommitted_changes(worktree):
            to_commit = non_retro_commit_paths(vcs, worktree=worktree, repo_root=repo_root)  # Story 83.19/83.24
            if to_commit:
                vcs.commit_paths(
                    worktree,
                    to_commit,
                    to_redacted_text("marshal: supervisor finalize (Story 28.24)"),
                )
                committed = True
    except VcsCommandError as exc:
        counter = _journal_finalize_attempt(
            fs=fs,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            story_key=story_key,
            worktree=worktree,
            trigger=trigger,
            committed=False,
            pushed=False,
            verified=False,
            ok=False,
            failed_step="commit",
            failed_message=str(exc),
        )
        return counter, False

    try:
        git_facts = gather_dispatch_git_facts(
            vcs,
            fs=fs,
            repo_root=repo_root,
            worktree=worktree,
            story_key=story_key,
            project_slug=slug,
            baseline_head_sha=git_facts.baseline_head_sha,
            merge_subject_template=merge_subject_template,
            followup_review=followup_review,
        )
    except VcsCommandError, ValueError:
        pass

    # Story 83.24: refuse push when the branch already carries an unsanctioned CFE commit.
    cfe_findings, cfe_report = check_unsanctioned_cfe_commits(worktree=worktree, process=process, base=ORIGIN_MAIN)
    cfe_unsanctioned = cfe_report.get("unsanctioned")
    if isinstance(cfe_unsanctioned, list) and unsanctioned_cfe_commit_entries(cfe_unsanctioned):
        branch_msg = next(
            (finding.message for finding in cfe_findings if finding.code == CFE_BRANCH_COMMIT_GATE_CODE),
            "unsanctioned conda-forge-expert commit on the story branch",
        )
        counter = _journal_finalize_attempt(
            fs=fs,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            story_key=story_key,
            worktree=worktree,
            trigger=trigger,
            committed=committed,
            pushed=False,
            verified=False,
            ok=False,
            failed_step="push",
            failed_message=branch_msg,
        )
        return counter, False

    if not _dispatch_push_already_journaled(folded, run_id):
        counter = _run_and_journal_dispatch_push(
            fs=fs,
            vcs=vcs,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            repo_root=repo_root,
            slug=slug,
            story_key=story_key,
            worktree=worktree,
            git_facts=git_facts,
        )
        text = fs.read_text(run_dir / _JOURNAL_FILENAME)
        if text is not None:
            folded = _fold_dispatch_journal(fs, run_dir, text)
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_PUSH):
            if entry.run_id != run_id or entry.phase != Phase.OUTCOME:
                continue
            if entry.payload.get("outcome") == "pushed":
                pushed = True
            elif entry.payload.get("outcome") == "push-failed":
                failed_step = "push"
                raw = entry.payload.get("failed_message")
                failed_message = raw if isinstance(raw, str) else "push failed"
            break
    else:
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_PUSH):
            if entry.run_id != run_id or entry.phase != Phase.OUTCOME:
                continue
            if entry.payload.get("outcome") == "pushed":
                pushed = True
            elif entry.payload.get("outcome") == "push-failed":
                failed_step = "push"
                raw = entry.payload.get("failed_message")
                failed_message = raw if isinstance(raw, str) else "push failed"
            break

    if failed_step == "push":
        counter = _journal_finalize_attempt(
            fs=fs,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            story_key=story_key,
            worktree=worktree,
            trigger=trigger,
            committed=committed,
            pushed=False,
            verified=False,
            ok=False,
            failed_step=failed_step,
            failed_message=failed_message,
        )
        return counter, False

    # Story 51.4 (spec-pyforge-marshal CAP-252): stop before verify/land on a
    # blocked or narration-only worktree spec -- the 27.3 incident (deliberate
    # `status: blocked`, reverted to baseline) and the 51.3 incident (harness
    # print-mode background-wait ceiling, spec-frontmatter-only diff). Since
    # `_run_and_journal_verification` is only ever called from this sequence,
    # gating it here also keeps `v_outcome` from ever reading "verified" for
    # either fixture, which is what both tick-loop land triggers require.
    block_reason = _spec_land_block_reason(
        fs=fs,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        worktree=worktree,
        git_facts=git_facts,
        followup_review=followup_review,
    )
    if block_reason is not None:
        counter = _journal_dispatch_blocked(
            fs=fs,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            story_key=story_key,
            worktree=worktree,
            reason=block_reason,
        )
        return counter, False

    if not _verification_already_journaled(folded, run_id):
        counter = _run_and_journal_verification(
            fs=fs,
            vcs=vcs,
            process=process,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            repo_root=repo_root,
            slug=slug,
            story_key=story_key,
            worktree=worktree,
        )
        text = fs.read_text(run_dir / _JOURNAL_FILENAME)
        if text is not None:
            folded = _fold_dispatch_journal(fs, run_dir, text)
        v_outcome = _verification_outcome_verdict(folded, run_id)
        verified = v_outcome == DispatchVerificationVerdict.VERIFIED.value
    else:
        v_outcome = _verification_outcome_verdict(folded, run_id)
        verified = v_outcome == DispatchVerificationVerdict.VERIFIED.value

    fix_committed = False
    fix_failed_step: str | None = None
    fix_failed_message: str | None = None
    if not verified:
        fix = _maybe_run_verify_fix_turn(
            fs=fs,
            vcs=vcs,
            process=process,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            repo_root=repo_root,
            slug=slug,
            story_key=story_key,
            worktree=worktree,
            git_facts=git_facts,
            folded=folded,
            session_alive=False,
            publish_heartbeat=publish_heartbeat,
        )
        counter, verified, folded = fix.counter, fix.verified, fix.folded
        fix_committed, fix_failed_step, fix_failed_message = fix.committed, fix.failed_step, fix.failed_message

    counter = _journal_finalize_attempt(
        fs=fs,
        run_dir=run_dir,
        run_id=run_id,
        writer_id=writer_id,
        counter=counter,
        story_key=story_key,
        worktree=worktree,
        trigger=trigger,
        committed=committed or fix_committed or git_facts.current_head_sha != git_facts.baseline_head_sha,
        pushed=pushed,
        verified=verified,
        ok=fix_failed_step is None,
        failed_step=fix_failed_step,
        failed_message=fix_failed_message,
    )
    return counter, fix_failed_step is None


def _journal_heartbeat(
    *,
    fs: FsPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    session_alive: bool,
    git_facts: DispatchGitFacts,
) -> int:
    """Append the tick loop's heartbeat observation; return the next counter.

    The one builder of that entry: the loop writes it once per tick, and (Story 80.1, CAP-284) the
    landing's check wait writes it on every wait tick. A journal write failure is swallowed -- a
    heartbeat is liveness evidence, never a reason to stop the run."""
    heartbeat = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_SUPERVISOR_ATTACH,
        phase=Phase.OBSERVATION,
        payload={
            "heartbeat": True,
            "session_alive": session_alive,
            "current_head_sha": git_facts.current_head_sha,
            "changed_path_count": len(git_facts.changed_paths),
        },
    )
    try:
        _append_entry(fs, run_dir, heartbeat, fsync=False)
    except FsError:
        pass
    return counter + 1


@dataclass(frozen=True)
class _WaitHeartbeat:
    """What one tick of a landing's check wait does (Story 80.1, CAP-284): the journal heartbeat
    observation (``session_alive`` and ``git_facts`` as the tick loop read them) and, when the run
    is published, ``publish`` -- the publisher heartbeat. The portal's ``sweep_lost_runs`` marks a
    live run ``heartbeat_lost`` once its heartbeat is older than the station time limit (300 s by
    default), and the landing's wait can outlast that."""

    session_alive: bool
    git_facts: DispatchGitFacts
    publish: Callable[[], None] | None = None


def _run_and_journal_landing(
    *,
    fs: FsPort,
    vcs: CommittingVcs,
    process: ProcessPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
    verification_verdict: DispatchVerificationVerdict,
    merge_subject_template: str,
    wait_heartbeat: _WaitHeartbeat | None = None,
    followup_review: FollowupReview | None = None,
    hold_landing_cli: bool = False,
    story_spec_text: str | None = None,
) -> int:
    """Land a verified dispatch via Epic 4 machinery and journal (Story 22.4).

    ``followup_review`` (Story 73.1, CAP-281), when the run is a follow-up review, is handed to
    ``execute_dispatch_land`` so it judges ALREADY_LANDED by the run's own head and closes the row; a
    normal run passes the landing nothing.

    ``wait_heartbeat`` (Story 80.1, CAP-284) is what the landing's check wait does on each tick; the
    counter the ticks consume carries on into the landing's own intent and outcome entries."""

    def _wait_tick() -> None:
        nonlocal counter
        if wait_heartbeat is None:
            return
        counter = _journal_heartbeat(
            fs=fs,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            session_alive=wait_heartbeat.session_alive,
            git_facts=wait_heartbeat.git_facts,
        )
        if wait_heartbeat.publish is not None:
            wait_heartbeat.publish()

    effective = compose_dispatch_policy(slug, repo_root)
    followup_kwargs: dict[str, FollowupReview] = (
        {"followup_review": followup_review} if followup_review is not None else {}
    )
    landing_result, envelope = execute_dispatch_land(
        project_slug=slug,
        story_key=story_key,
        worktree=worktree,
        repo_root=repo_root,
        verification_verdict=verification_verdict,
        run_id=run_id,
        effective=effective,
        on_wait_tick=_wait_tick if wait_heartbeat is not None else None,
        fs=fs,
        vcs=vcs,
        process=process,
        hold_landing_cli=hold_landing_cli,
        story_spec_text=story_spec_text,
        **followup_kwargs,
    )
    intent_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_LAND,
        phase=Phase.INTENT,
        payload={
            "verdict": landing_result.verdict.value,
            "verification_verdict": verification_verdict.value,
            "pr_number": landing_result.pr_number,
            "subject": landing_result.subject,
            "marshal_native": landing_result.marshal_native,
        },
    )
    counter += 1
    outcome_payload: dict[str, object] = {
        "verdict": landing_result.verdict.value,
        "ok": landing_result.verdict in {DispatchLandingVerdict.LANDED, DispatchLandingVerdict.HELD_FOR_REVIEW},
        "envelope_verdict": envelope.verdict.value,
        "pr_number": landing_result.pr_number,
        "merge_sha": landing_result.merge_sha,
        "marshal_native": landing_result.marshal_native,
        # Story 53.2 review (I1): `envelope.findings` (MRS-DISP-047/048)
        # must reach the journal payload, not just the coarse verdict
        # strings above -- mirrors `scope_violation_advisories` (Story
        # 28.15) so `marshal status`/`fleet-picture` can render it too.
        "land_findings": [f.to_json_dict() for f in envelope.findings],
    }
    # Story 80.1 (CAP-284): the check runs the landing waited on and their
    # conclusions -- absent when the landing never reached the wait.
    landing_checks = envelope.data.get(LANDING_CHECKS_FIELD)
    if landing_checks is not None:
        outcome_payload[LANDING_CHECKS_FIELD] = landing_checks
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_LAND,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload=outcome_payload,
    )
    counter += 1
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
        _append_entry(
            fs,
            run_dir,
            outcome_entry,
            fsync=False,
            offload_fields=frozenset({LAND_FINDINGS_FIELD, LANDING_CHECKS_FIELD}),
        )
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot journal landing for {run_id!r}: {exc}",
            file=sys.stderr,
        )
    return counter


def _land_or_journal_block(
    *,
    fs: FsPort,
    vcs: CommittingVcs,
    process: ProcessPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
    git_facts: DispatchGitFacts,
    verification_verdict: DispatchVerificationVerdict,
    merge_subject_template: str,
    session_alive: bool = False,
    publish_heartbeat: Callable[[], None] | None = None,
    followup_review: FollowupReview | None = None,
    folded=None,
) -> int:
    """Land, unless the worktree spec is blocked/narration-only (Story 51.4,
    spec-pyforge-marshal CAP-252 -- defense in depth).

    ``followup_review`` (Story 73.1, CAP-281) is the run's follow-up review marker, or ``None``: a spec-only
    diff is that run's record, not narration, and the landing is told it is a follow-up.

    ``session_alive`` and ``publish_heartbeat`` (Story 80.1, CAP-284) feed the landing's wait tick:
    the heartbeat observation as the tick loop would write it, and the run publisher's heartbeat.

    ``_run_supervisor_finalize_sequence`` already stops before verification
    is ever journaled "verified" for a blocked or narration-only spec, so
    ``verification_verdict`` reaching this function as VERIFIED should never
    coincide with a block reason in practice. This is a second, independent
    read of the same worktree facts at the tick loop's own land trigger --
    the surface the Binding names explicitly -- rather than the sole guard.
    """
    block_reason = _spec_land_block_reason(
        fs=fs,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        worktree=worktree,
        git_facts=git_facts,
        followup_review=followup_review,
    )
    if block_reason is not None:
        return _journal_dispatch_blocked(
            fs=fs,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            story_key=story_key,
            worktree=worktree,
            reason=block_reason,
        )
    hold_landing_cli = _hold_landing_from_launch(folded, run_id) if folded is not None else False
    spec_text: str | None = None
    spec_path = dispatch_core.resolve_story_spec_path(worktree, slug, story_key)
    if spec_path is not None:
        try:
            spec_text = spec_path.read_text(encoding="utf-8")
        except OSError:
            spec_text = None
    return _run_and_journal_landing(
        fs=fs,
        vcs=vcs,
        process=process,
        run_dir=run_dir,
        run_id=run_id,
        writer_id=writer_id,
        counter=counter,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        worktree=worktree,
        verification_verdict=verification_verdict,
        merge_subject_template=merge_subject_template,
        wait_heartbeat=_WaitHeartbeat(
            session_alive=session_alive,
            git_facts=git_facts,
            publish=publish_heartbeat,
        ),
        followup_review=followup_review,
        hold_landing_cli=hold_landing_cli,
        story_spec_text=spec_text,
    )


def _session_awaits_verification(session_alive: bool, git: DispatchGitFacts) -> bool:
    return not session_alive and has_git_progress(git) and not git.branch_merged and not git.story_merged_on_main


def _run_and_journal_dispatch_push(
    *,
    fs: FsPort,
    vcs: VcsPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
    git_facts: DispatchGitFacts,
) -> int:
    """Push the dispatch branch before verify (Story 28.21, CAP-4)."""
    git_repo_root = dispatch_core.canonical_repo_root(repo_root)
    try:
        branch_resolution = dispatch_core.resolve_dispatch_branch(
            vcs,
            git_repo_root,
            slug=slug,
            story_key=story_key,
            worktree=worktree,
        )
    except VcsCommandError as exc:
        print(
            f"dispatch supervisor: cannot resolve branch before push for {run_id!r}: {exc}",
            file=sys.stderr,
        )
        return counter

    if not may_push_dispatch_branch_before_verify(
        git_facts,
        branch_refusal=branch_resolution.refusal,
    ):
        return counter

    head_branch = branch_resolution.effective_branch
    outcome = "pushed"
    failed_message: str | None = None
    try:
        vcs.push(git_repo_root, head_branch)
    except VcsCommandError as exc:
        outcome = "push-failed"
        failed_message = str(exc)
    intent_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_PUSH,
        phase=Phase.INTENT,
        payload={"branch": head_branch, "story_key": story_key},
    )
    counter += 1
    outcome_payload: dict[str, object] = {
        "branch": head_branch,
        "outcome": outcome,
        "ok": outcome == "pushed",
    }
    if failed_message is not None:
        outcome_payload["failed_message"] = failed_message
        outcome_payload["finding"] = Finding(
            code="MRS-DISP-037",
            severity=Severity.WARN,
            message=(f"pre-verify dispatch push failed for branch {head_branch!r}: {failed_message}"),
        ).to_json_dict()
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_PUSH,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload=outcome_payload,
    )
    counter += 1
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot journal dispatch push for {run_id!r}: {exc}",
            file=sys.stderr,
        )
    return counter


def _run_and_journal_ruff_format(
    *,
    fs: FsPort,
    vcs: CommittingVcs,
    process: ProcessPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    repo_root: Path,
    story_key: str,
    worktree: Path,
) -> int:
    """Story 83.9: format story-scoped ``.py`` files and journal when anything changed."""
    result = run_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=repo_root,
        vcs=vcs,
        process=process,
    )
    if not result.reformatted_paths:
        return counter
    intent_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_RUFF_FORMAT,
        phase=Phase.INTENT,
        payload={"story_key": story_key, "paths": list(result.reformatted_paths)},
    )
    counter += 1
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_RUFF_FORMAT,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload={
            "story_key": story_key,
            "paths": list(result.reformatted_paths),
            "committed": result.committed,
            "ok": result.committed,
        },
    )
    counter += 1
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot journal ruff format for {run_id!r}: {exc}",
            file=sys.stderr,
        )
    return counter


def _run_and_journal_verification(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
    on_progress: Callable[[], None] | None = None,
) -> int:
    """Run independent gate verification and journal the outcome (Story 22.3)."""
    if callable(getattr(vcs, "commit_paths", None)):
        counter = _run_and_journal_ruff_format(
            fs=fs,
            vcs=vcs,  # CommittingVcs duck type
            process=process,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter,
            repo_root=repo_root,
            story_key=story_key,
            worktree=worktree,
        )
    effective = compose_dispatch_policy(slug, repo_root)
    resolution = resolve_feed([story_key])
    if not resolution.resolved:
        return counter
    story_key_obj = resolution.resolved[0]
    spec_text = resolve_spec_text_for_story(repo_root, slug, story_key_obj)
    # Story 85.3: a fix turn's re-verification can outlast the portal's 300 s, so ``on_progress`` (the turn's
    # throttled, lock-serialized publisher heartbeat) is called from a progress thread while it runs.
    progress_stop = threading.Event()
    progress_thread: threading.Thread | None = None
    if on_progress is not None:
        progress = on_progress

        def _verification_progress() -> None:
            while not progress_stop.wait(_FIX_TURN_PUBLISH_INTERVAL_S):
                progress()

        progress_thread = threading.Thread(target=_verification_progress, daemon=True)
        progress_thread.start()
    try:
        envelope = evaluate_dispatch_verification(
            project_slug=slug,
            story_key=story_key_obj,
            worktree=worktree,
            repo_root=repo_root,
            effective=effective,
            spec_text=spec_text,
            process=process,
            vcs=vcs,
            committing_vcs=vcs,
        )
    finally:
        progress_stop.set()
        if progress_thread is not None and progress_thread.is_alive():
            # The stop event ends the loop at once; the join only waits out a heartbeat already in flight, so no
            # publisher call of this thread can overlap the supervisor's next one.
            progress_thread.join()
    built = build_dispatch_verification_journal_entries_from_envelope(
        envelope=envelope,
        repo_root=repo_root,
        effective=effective,
        run_id=run_id,
        writer_id=writer_id,
        counter=counter,
        ts=_format_entry_ts(_now_utc()),
    )
    intent_entry = built.intent_entry
    outcome_entry = built.outcome_entry
    counter = built.next_counter
    offload_fields = built.offload_fields
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
        _append_entry(
            fs,
            run_dir,
            outcome_entry,
            fsync=False,
            offload_fields=offload_fields,
        )
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot journal verification for {run_id!r}: {exc}",
            file=sys.stderr,
        )
    return counter


def run_dispatch_supervisor(
    *,
    repo_root: Path,
    slug: str,
    run_id: str,
    session_pid: int,
    worktree: Path,
    story_key: str,
    baseline_head_sha: str,
    merge_subject_template: str,
    fs: FsPort | None = None,
    vcs: CommittingVcs | None = None,
    process: ProcessPort | None = None,
    publisher: RunPublisherPort | None = None,
) -> int:
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    process = process if process is not None else PosixProcess()
    run_dir = dispatch_core.dispatch_run_dir(repo_root, slug, run_id)
    journal_path = run_dir / _JOURNAL_FILENAME
    text = fs.read_text(journal_path)
    if text is None:
        print(
            f"dispatch supervisor: no journal at {journal_path!r}; exiting inert",
            file=sys.stderr,
        )
        return 0
    folded = _fold_dispatch_journal(fs, run_dir, text)
    launch_entries = folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH)
    if not any(entry.run_id == run_id and entry.phase in (Phase.INTENT, Phase.OUTCOME) for entry in launch_entries):
        print(
            f"dispatch supervisor: no dispatch-launch for run {run_id!r}; exiting inert",
            file=sys.stderr,
        )
        return 0
    # Story 73.1 (CAP-281): a follow-up review run is judged by its own branch, never by the story's
    # first landing -- the marker is the one `dispatch_once` journaled on this run's launch INTENT.
    followup_review = _followup_review_from_launch(folded, run_id)

    writer_id = _writer_id()
    counter = 0
    run_publish_handle: str | None = None

    def _journal_publish_finding(operation: str, message: str) -> None:
        nonlocal counter
        finding = Finding(
            code="MRS-SUPV-010",
            severity=Severity.WARN,
            message=f"run-state {operation} failed: {message}",
        )
        entry = build_entry(
            id=JournalEntryId(writer_id, counter),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind="run-state-publish",
            phase=Phase.OBSERVATION,
            payload={"operation": operation, "finding": finding.to_json_dict()},
        )
        counter += 1
        try:
            _append_entry(fs, run_dir, entry, fsync=False)
        except FsError:
            pass

    _publisher = (
        publisher
        if publisher is not None
        else HostPublisher(
            on_finding=_journal_publish_finding,
        )
    )

    attach_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_SUPERVISOR_ATTACH,
        phase=Phase.OBSERVATION,
        payload={
            "pid": os.getpid(),
            "session_pid": session_pid,
            "baseline_head_sha": baseline_head_sha,
        },
    )
    counter += 1
    try:
        _append_entry(fs, run_dir, attach_entry, fsync=True)
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot journal attach for {run_id!r}: {exc}",
            file=sys.stderr,
        )
        return 1

    run_publish_handle = _publisher.publish(
        shape_dispatch_publish(
            station_slug=slug,
            run_id=run_id,
            story_key=story_key,
            commit_sha=baseline_head_sha,
        )
    )

    def _publish_heartbeat() -> None:
        if run_publish_handle is not None:
            _publisher.heartbeat(run_publish_handle)

    try:
        vcs.fetch(repo_root, "origin", "main")
    except VcsCommandError:
        pass

    tick_count = 0
    stuck_land_ticks = 0
    last_session_log_snapshot: str | None = None
    last_session_activity_monotonic = time.monotonic()
    # Story 51.4 (CAP-252): the worktree-relative path of the story's own
    # tracked spec, resolved once (the worktree path is fixed for the run) --
    # threaded into every terminal-verdict read so a diff collapsing to just
    # this file is judged as no progress, not live/stopped-externally work.
    spec_relative_path, _initial_spec_text = _worktree_story_spec(
        fs=fs,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        worktree=worktree,
    )
    # Story 73.1 (CAP-281): a follow-up review run's spec-only diff is its record, so every narration
    # read below takes the path through `narration_spec_path` (None for that run, the spec path otherwise).
    narration_path = narration_spec_path(spec_relative_path, followup_review=followup_review)
    session_launched_at: datetime | None = None
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH):
        if entry.run_id == run_id and entry.phase == Phase.INTENT:
            try:
                session_launched_at = datetime.fromisoformat(entry.ts.replace("Z", "+00:00"))
            except ValueError:
                session_launched_at = None
            break

    while True:
        tick_count += 1
        _maybe_fetch_origin_main(vcs, repo_root, tick=tick_count)
        try:
            git_facts = gather_dispatch_git_facts(
                vcs,
                fs=fs,
                repo_root=repo_root,
                worktree=worktree,
                story_key=story_key,
                project_slug=slug,
                baseline_head_sha=baseline_head_sha,
                merge_subject_template=merge_subject_template,
                followup_review=followup_review,
            )
        except (VcsCommandError, ValueError) as exc:
            print(
                f"dispatch supervisor: git fact gather failed: {exc}",
                file=sys.stderr,
            )
            time.sleep(_TICK_SECONDS)
            continue

        session_alive = dispatch_session_alive(process, session_pid, launched_at=session_launched_at)
        session_log = fs.read_text(run_dir / _SESSION_LOG_FILENAME)
        if session_alive:
            current_log = session_log
            if current_log != last_session_log_snapshot:
                last_session_log_snapshot = current_log
                last_session_activity_monotonic = time.monotonic()
            idle_elapsed_s = time.monotonic() - last_session_activity_monotonic
            try:
                dirty = vcs.has_uncommitted_changes(worktree)
            except VcsCommandError:
                dirty = False
            if should_checkpoint_on_idle(
                idle_elapsed_s=idle_elapsed_s,
                threshold_s=float(_TICK_SECONDS),
                has_uncommitted_changes=dirty,
            ):
                commit_worktree_checkpoint(
                    vcs,
                    repo_root=repo_root,
                    worktree=worktree,
                    story_key=story_key,
                )
        v_outcome = _verification_outcome_verdict(folded, run_id)
        if _landing_succeeded(folded, run_id):
            verdict = DispatchSessionVerdict.COMPLETED
        else:
            verdict = resolve_terminal_session_verdict(
                session_alive=session_alive,
                git=git_facts,
                verification_verdict=v_outcome,
                session_log=session_log,
                spec_relative_path=narration_path,
            )
        landing_done = _landing_succeeded(folded, run_id)
        if supervisor_should_finalize_harness_work(
            session_alive=session_alive,
            git=git_facts,
            session_log=session_log,
            verification_verdict=v_outcome,
            landing_complete=landing_done,
        ) and not finalize_attempt_journaled(folded, run_id):
            counter, _finalize_ok = _run_supervisor_finalize_sequence(
                fs=fs,
                vcs=vcs,
                process=process,
                run_dir=run_dir,
                run_id=run_id,
                writer_id=writer_id,
                counter=counter,
                repo_root=repo_root,
                slug=slug,
                story_key=story_key,
                worktree=worktree,
                git_facts=git_facts,
                session_log=session_log,
                merge_subject_template=merge_subject_template,
                folded=folded,
                followup_review=followup_review,
                publish_heartbeat=_publish_heartbeat,
            )
            text = fs.read_text(journal_path)
            if text is not None:
                folded = _fold_dispatch_journal(fs, run_dir, text)
            v_outcome = _verification_outcome_verdict(folded, run_id)
            try:
                git_facts = gather_dispatch_git_facts(
                    vcs,
                    fs=fs,
                    repo_root=repo_root,
                    worktree=worktree,
                    story_key=story_key,
                    project_slug=slug,
                    baseline_head_sha=baseline_head_sha,
                    merge_subject_template=merge_subject_template,
                    followup_review=followup_review,
                )
            except VcsCommandError, ValueError:
                pass
            landing_done = _landing_succeeded(folded, run_id)
            if landing_done:
                verdict = DispatchSessionVerdict.COMPLETED
            else:
                verdict = resolve_terminal_session_verdict(
                    session_alive=session_alive,
                    git=git_facts,
                    verification_verdict=v_outcome,
                    session_log=session_log,
                    spec_relative_path=narration_path,
                )
        if verdict == DispatchSessionVerdict.LIVE:
            if _session_awaits_verification(session_alive, git_facts):
                if should_terminalize_verify_refusal(
                    session_alive=session_alive,
                    verification_verdict=v_outcome,
                    git=git_facts,
                ):
                    verdict = DispatchSessionVerdict.FAILED
                elif (
                    v_outcome == DispatchVerificationVerdict.VERIFIED.value
                    and not git_facts.story_merged_on_main
                    and not _landing_already_journaled(folded, run_id)
                ):
                    stuck_land_ticks += 1
                else:
                    stuck_land_ticks = 0
                if verdict == DispatchSessionVerdict.LIVE and (
                    (
                        v_outcome == DispatchVerificationVerdict.VERIFIED.value
                        and not git_facts.story_merged_on_main
                        and not _landing_already_journaled(folded, run_id)
                    )
                    or should_retry_stuck_land(
                        verification_verdict=v_outcome,
                        story_merged_on_main=git_facts.story_merged_on_main,
                        landing_journaled=_landing_already_journaled(folded, run_id),
                        stuck_land_ticks=stuck_land_ticks,
                    )
                ):
                    counter = _land_or_journal_block(
                        fs=fs,
                        vcs=vcs,
                        process=process,
                        run_dir=run_dir,
                        run_id=run_id,
                        writer_id=writer_id,
                        counter=counter,
                        repo_root=repo_root,
                        slug=slug,
                        story_key=story_key,
                        worktree=worktree,
                        git_facts=git_facts,
                        verification_verdict=DispatchVerificationVerdict.VERIFIED,
                        merge_subject_template=merge_subject_template,
                        session_alive=session_alive,
                        publish_heartbeat=_publish_heartbeat,
                        followup_review=followup_review,
                        folded=folded,
                    )
                    # Story 72.1 (CAP-280): fetch `origin main` so the re-gather
                    # reads the supervisor's own land, never a stale remote-tracking ref.
                    _fetch_origin_main(vcs, repo_root)
                    text = fs.read_text(journal_path)
                    if text is not None:
                        folded = _fold_dispatch_journal(fs, run_dir, text)
                    stuck_land_ticks = 0
                    try:
                        git_facts = gather_dispatch_git_facts(
                            vcs,
                            fs=fs,
                            repo_root=repo_root,
                            worktree=worktree,
                            story_key=story_key,
                            project_slug=slug,
                            baseline_head_sha=baseline_head_sha,
                            merge_subject_template=merge_subject_template,
                            followup_review=followup_review,
                        )
                        verdict = resolve_terminal_session_verdict(
                            session_alive=session_alive,
                            git=git_facts,
                            verification_verdict=v_outcome,
                            session_log=session_log,
                            spec_relative_path=narration_path,
                        )
                    except VcsCommandError, ValueError:
                        pass
            if verdict == DispatchSessionVerdict.LIVE:
                counter = _journal_heartbeat(
                    fs=fs,
                    run_dir=run_dir,
                    run_id=run_id,
                    writer_id=writer_id,
                    counter=counter,
                    session_alive=session_alive,
                    git_facts=git_facts,
                )
                _publish_heartbeat()
                time.sleep(_TICK_SECONDS)
                continue

        v_outcome = _verification_outcome_verdict(folded, run_id)
        landing_journaled = _landing_already_journaled(folded, run_id)
        if (
            v_outcome == DispatchVerificationVerdict.VERIFIED.value
            and not git_facts.story_merged_on_main
            and not landing_journaled
        ):
            stuck_land_ticks += 1
        if (
            v_outcome == DispatchVerificationVerdict.VERIFIED.value
            and not git_facts.story_merged_on_main
            and not landing_journaled
        ) or should_retry_stuck_land(
            verification_verdict=v_outcome,
            story_merged_on_main=git_facts.story_merged_on_main,
            landing_journaled=landing_journaled,
            stuck_land_ticks=stuck_land_ticks,
        ):
            counter = _land_or_journal_block(
                fs=fs,
                vcs=vcs,
                process=process,
                run_dir=run_dir,
                run_id=run_id,
                writer_id=writer_id,
                counter=counter,
                repo_root=repo_root,
                slug=slug,
                story_key=story_key,
                worktree=worktree,
                git_facts=git_facts,
                verification_verdict=DispatchVerificationVerdict.VERIFIED,
                merge_subject_template=merge_subject_template,
                session_alive=session_alive,
                publish_heartbeat=_publish_heartbeat,
                followup_review=followup_review,
                folded=folded,
            )
            # Story 72.1 (CAP-280): fetch `origin main` so the re-gather reads
            # the supervisor's own land, never a stale remote-tracking ref.
            _fetch_origin_main(vcs, repo_root)
            text = fs.read_text(journal_path)
            if text is not None:
                folded = _fold_dispatch_journal(fs, run_dir, text)
            stuck_land_ticks = 0
            try:
                git_facts = gather_dispatch_git_facts(
                    vcs,
                    fs=fs,
                    repo_root=repo_root,
                    worktree=worktree,
                    story_key=story_key,
                    project_slug=slug,
                    baseline_head_sha=baseline_head_sha,
                    merge_subject_template=merge_subject_template,
                    followup_review=followup_review,
                )
                verdict = resolve_terminal_session_verdict(
                    session_alive=session_alive,
                    git=git_facts,
                    verification_verdict=v_outcome,
                    session_log=session_log,
                    spec_relative_path=narration_path,
                )
            except VcsCommandError, ValueError:
                pass
            # Story 67.1 (CAP-276): the repository facts can lag a landing -- they
            # read `origin/main` (Story 72.1), and a failed post-land fetch leaves
            # that ref stale -- so the facts alone can read a landed run
            # `stopped_externally`. The journaled land decides the process verdict
            # (the loop head's and the post-finalize re-read's rule); git keeps the
            # facts the completion INTENT records (AD-33).
            if _landing_succeeded(folded, run_id):
                verdict = DispatchSessionVerdict.COMPLETED

        stale_blocked_finding: dict[str, object] | None = None
        if verdict is DispatchSessionVerdict.STOPPED_EXTERNALLY:
            # Story 51.11 (CAP-258): before classifying an unexplained exit as
            # an operator stop, read the worktree's own tracked spec -- a
            # session that halted `blocked` correctly but exited before
            # committing that halt is a blocked outcome, not an operator stop.
            blocked_reason, stale = _blocked_halt_reason(
                fs=fs,
                repo_root=repo_root,
                slug=slug,
                story_key=story_key,
                worktree=worktree,
                git_facts=git_facts,
            )
            if blocked_reason is not None:
                counter, committed = _commit_and_journal_blocked_halt(
                    fs=fs,
                    vcs=vcs,
                    run_dir=run_dir,
                    run_id=run_id,
                    writer_id=writer_id,
                    counter=counter,
                    repo_root=repo_root,
                    slug=slug,
                    story_key=story_key,
                    worktree=worktree,
                    reason=blocked_reason,
                )
                if committed:
                    verdict = DispatchSessionVerdict.BLOCKED
                    try:
                        git_facts = gather_dispatch_git_facts(
                            vcs,
                            fs=fs,
                            repo_root=repo_root,
                            worktree=worktree,
                            story_key=story_key,
                            project_slug=slug,
                            baseline_head_sha=baseline_head_sha,
                            merge_subject_template=merge_subject_template,
                            followup_review=followup_review,
                        )
                    except VcsCommandError, ValueError:
                        pass
                    counter = _promote_blocked_twin(
                        fs=fs,
                        vcs=vcs,
                        run_dir=run_dir,
                        run_id=run_id,
                        writer_id=writer_id,
                        counter=counter,
                        repo_root=repo_root,
                        slug=slug,
                        story_key=story_key,
                        worktree=worktree,
                    )
            elif stale:
                stale_blocked_finding = Finding(
                    code="MRS-DISP-046",
                    severity=Severity.WARN,
                    message=(
                        f"story {story_key!r} worktree spec reads status: "
                        f"blocked but its baseline_revision does not match "
                        f"this run's baseline {git_facts.baseline_head_sha!r} "
                        f"-- treating as stopped_externally, not "
                        f"re-attributing a stale blocked spec from an earlier "
                        f"dispatch pass (Story 51.11)"
                    ),
                ).to_json_dict()

        stop_reason: str | None = None
        if verdict is DispatchSessionVerdict.STOPPED_EXTERNALLY:
            stop_reason = "external-operator-stop"
        elif verdict is DispatchSessionVerdict.FAILED:
            stop_reason = "failed"
        intent_payload: dict[str, object] = {
            "verdict": verdict.value,
            "stop_reason": stop_reason,
            "session_alive": session_alive,
            "baseline_head_sha": git_facts.baseline_head_sha,
            "current_head_sha": git_facts.current_head_sha,
            "changed_paths": list(git_facts.changed_paths),
            "branch_merged": git_facts.branch_merged,
            "story_merged_on_main": git_facts.story_merged_on_main,
        }
        if stale_blocked_finding is not None:
            intent_payload["finding"] = stale_blocked_finding
        intent_entry = build_entry(
            id=JournalEntryId(writer_id, counter),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.INTENT,
            payload=intent_payload,
        )
        counter += 1
        completion_outcome_payload: dict[str, object] = {
            "verdict": verdict.value,
            "stop_reason": stop_reason,
            "ok": True,
        }
        if stale_blocked_finding is not None:
            completion_outcome_payload["finding"] = stale_blocked_finding
        outcome_entry = build_entry(
            id=JournalEntryId(writer_id, counter),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.OUTCOME,
            intent_id=intent_entry.id,
            payload=completion_outcome_payload,
        )
        ended_at = _format_entry_ts(_now_utc())
        started_at = _launch_story_started_ts(folded, run_id) or ended_at
        if run_publish_handle is not None:
            _publisher.complete(
                run_publish_handle,
                status=verdict.value,
                result=dispatch_complete_result(
                    verdict=verdict.value,
                    stop_reason=stop_reason,
                    baseline_head_sha=git_facts.baseline_head_sha,
                    current_head_sha=git_facts.current_head_sha,
                    story_key=story_key,
                    started_at=started_at,
                    ended_at=ended_at,
                ),
            )
        try:
            _append_entry(fs, run_dir, intent_entry, fsync=True)
            _append_entry(fs, run_dir, outcome_entry, fsync=False)
        except FsError as exc:
            print(
                f"dispatch supervisor: cannot journal completion for {run_id!r}: {exc}",
                file=sys.stderr,
            )
            return 1
        counter = _journal_dispatch_timing(
            fs=fs,
            run_dir=run_dir,
            run_id=run_id,
            writer_id=writer_id,
            counter=counter + 1,
            story_key=story_key,
            story_started_at=started_at,
            story_ended_at=ended_at,
            baseline_revision=git_facts.baseline_head_sha,
            final_revision=git_facts.current_head_sha,
        )
        if verdict == DispatchSessionVerdict.FAILED and has_git_progress(git_facts, spec_relative_path=narration_path):
            counter = _journal_dispatch_preserve(
                fs=fs,
                vcs=vcs,
                run_dir=run_dir,
                run_id=run_id,
                writer_id=writer_id,
                counter=counter,
                story_key=story_key,
                worktree=worktree,
                baseline_head_sha=baseline_head_sha,
            )
        if supervisor_should_exit(
            completion_verdict=verdict.value,
            story_merged_on_main=git_facts.story_merged_on_main,
            landing_verdict=_landing_outcome_verdict(folded, run_id),
        ):
            return 0
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dispatch completion supervisor (Story 22.2)")
    parser.add_argument("repo_root")
    parser.add_argument("slug")
    parser.add_argument("run_id")
    parser.add_argument("session_pid", type=int)
    parser.add_argument("worktree_path")
    parser.add_argument("story_key")
    parser.add_argument("baseline_head_sha")
    parser.add_argument("merge_subject_template")
    parser.add_argument("log_path")
    args = parser.parse_args(argv)
    return run_dispatch_supervisor(
        repo_root=Path(args.repo_root),
        slug=args.slug,
        run_id=args.run_id,
        session_pid=args.session_pid,
        worktree=Path(args.worktree_path),
        story_key=args.story_key,
        baseline_head_sha=args.baseline_head_sha,
        merge_subject_template=args.merge_subject_template,
    )


if __name__ == "__main__":
    raise SystemExit(main())
