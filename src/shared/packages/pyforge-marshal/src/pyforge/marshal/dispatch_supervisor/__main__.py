"""Dispatch completion supervisor entry point (Story 22.2)."""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pyforge.core.process import PosixProcess, ProcessPort

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.publisher_host import HostPublisher
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import dispatch as dispatch_core
from ..core import gate as gate_core
from ..core import promotion as promotion_core
from ..core.commit_vcs import CommittingVcs
from ..core.dispatch_completion import (
    DispatchGitFacts,
    DispatchSessionVerdict,
    has_git_progress,
    is_spec_only_narration,
    merge_subject_ref,
    narration_spec_path,
)
from ..core.dispatch_harness_done import (
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
    primary_gate_failure,
)
from ..core.egress import to_redacted_text
from ..core.identity import MalformedStoryKeyError, StoryKey, normalize, resolve_feed
from ..core.journal import (
    LAND_FINDINGS_FIELD,
    LANDING_CHECKS_FIELD,
    SCOPE_VIOLATION_ADVISORIES_FIELD,
    JournalEntryId,
    Phase,
    build_entry,
    fold,
    prepare_for_write,
    prepare_for_write_offloading_fields,
    sidecar_texts_for_lines,
)
from ..core.model import Finding, Severity
from ..core.publish import dispatch_complete_result, shape_dispatch_publish
from ..core.refs import ORIGIN_MAIN
from ..core.supervise import resolve_terminal_session_verdict
from ..core.worktree_checkpoint import (
    commit_worktree_checkpoint,
    should_checkpoint_on_idle,
)
from ..dispatch_land import execute_dispatch_land
from ..dispatch_verify import (
    compose_dispatch_policy,
    evaluate_dispatch_verification,
    resolve_spec_text_for_story,
    run_dispatch_ruff_format_before_verify,
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
) -> None:
    try:
        if not vcs.has_uncommitted_changes(worktree):
            return
        changed = vcs.changed_files(repo_root, worktree, base="HEAD")
        if not changed:
            return
        vcs.commit_paths(
            worktree,
            tuple(Path(path) for path in changed),
            to_redacted_text("marshal: pre-verify WIP checkpoint"),
        )
    except VcsCommandError as exc:
        print(
            f"dispatch supervisor: pre-verify WIP commit skipped: {exc}",
            file=sys.stderr,
        )


def _launch_story_started_ts(folded, run_id: str) -> str | None:
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH):
        if entry.run_id == run_id and entry.phase == Phase.INTENT:
            return entry.ts
    return None


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
    default, ``None``) reads ``origin/main`` whole, as before."""
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


def _verification_already_journaled(folded, run_id: str) -> bool:
    return any(
        entry.run_id == run_id and entry.phase == Phase.OUTCOME
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFICATION)
    )


def _dispatch_push_already_journaled(folded, run_id: str) -> bool:
    return any(
        entry.run_id == run_id and entry.phase == Phase.OUTCOME
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_PUSH)
    )


def _landing_already_journaled(folded, run_id: str) -> bool:
    return any(
        entry.run_id == run_id and entry.phase == Phase.OUTCOME
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAND)
    )


def _verification_outcome_verdict(folded, run_id: str) -> str | None:
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFICATION):
        if entry.run_id == run_id and entry.phase == Phase.OUTCOME:
            verdict_val = entry.payload.get("verdict")
            if isinstance(verdict_val, str):
                return verdict_val
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
    try:
        changed = vcs.changed_files(repo_root, worktree, base="HEAD")
    except VcsCommandError:
        return counter, False
    patch_paths = _attempted_change_patch_paths(worktree)
    paths_to_commit = tuple(Path(path) for path in changed) + tuple(p.relative_to(worktree) for p in patch_paths)
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
) -> tuple[int, bool]:
    """Commit, push, and verify harness-leftover work (Story 28.24).

    ``followup_review`` (Story 73.1, CAP-281) is the run's follow-up review marker, or ``None``: it scopes
    the repository facts this sequence re-gathers and the spec-only block check to the run's own branch."""
    trigger = classify_finalize_trigger(session_log).value
    committed = False
    pushed = False
    verified = False
    failed_step: str | None = None
    failed_message: str | None = None
    try:
        if vcs.has_uncommitted_changes(worktree):
            changed = vcs.changed_files(repo_root, worktree, base="HEAD")
            if changed:
                vcs.commit_paths(
                    worktree,
                    tuple(Path(path) for path in changed),
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

    counter = _journal_finalize_attempt(
        fs=fs,
        run_dir=run_dir,
        run_id=run_id,
        writer_id=writer_id,
        counter=counter,
        story_key=story_key,
        worktree=worktree,
        trigger=trigger,
        committed=committed or git_facts.current_head_sha != git_facts.baseline_head_sha,
        pushed=pushed,
        verified=verified,
        ok=True,
    )
    return counter, True


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
        "ok": landing_result.verdict == DispatchLandingVerdict.LANDED,
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
    verification_verdict = judge_dispatch_verification(DispatchVerificationInput(findings=envelope.findings))
    failed = primary_gate_failure(envelope.findings)
    # Story 28.15 (CAP-17): a `warn`-mode scope-violation advisory never
    # becomes `failed` above (it classifies Verdict.WARN, ok-status) -- so
    # without this it would be invisible outside the raw journal, exactly
    # the "unless anyone reads findings" risk CAP-17's own Gates named.
    # Named codes only (never the raw MRS-GATE-007/008, which `warn` mode
    # never emits in the first place): a plain, JSON-safe list threaded to
    # `marshal status`/`fleet-picture` via `gather_dispatch_journal_facts`.
    scope_advisories = [
        {"code": finding.code, "path": finding.path}
        for finding in envelope.findings
        if finding.code in gate_core._SCOPE_VIOLATION_ADVISORY_CODES.values()
    ]
    intent_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
        phase=Phase.INTENT,
        payload={
            "verdict": verification_verdict.value,
            "gate_verdict": envelope.verdict.value,
            "failed_gate": failed.code if failed is not None else None,
            "finding_count": len(envelope.findings),
        },
    )
    counter += 1
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload={
            "verdict": verification_verdict.value,
            "ok": verification_verdict == DispatchVerificationVerdict.VERIFIED,
            "failed_gate": failed.code if failed is not None else None,
            "failed_message": failed.message if failed is not None else None,
            "scope_violation_advisories": scope_advisories,
        },
    )
    counter += 1
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
        _append_entry(
            fs,
            run_dir,
            outcome_entry,
            fsync=False,
            offload_fields=frozenset({SCOPE_VIOLATION_ADVISORIES_FIELD}),
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

        session_alive = process.is_alive(session_pid)
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
