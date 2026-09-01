"""Dispatch completion supervisor entry point (Story 22.2)."""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessPort

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import dispatch as dispatch_core
from ..core import gate as gate_core
from ..core import promotion as promotion_core
from ..core.dispatch_completion import (
    DispatchCompletionInput,
    DispatchGitFacts,
    DispatchSessionVerdict,
    has_git_progress,
    judge_dispatch_completion,
)
from ..core.dispatch_preserve import (
    failed_patch_path,
    relative_preserve_ref,
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
from ..core.dispatch_landing import DispatchLandingVerdict
from ..core.journal import (
    JournalEntryId,
    Phase,
    SCOPE_VIOLATION_ADVISORIES_FIELD,
    build_entry,
    fold,
    prepare_for_write,
    prepare_for_write_offloading_fields,
    sidecar_texts_for_lines,
)
from ..core.identity import normalize, resolve_feed
from ..dispatch_verify import (
    compose_dispatch_policy,
    evaluate_dispatch_verification,
    resolve_spec_text_for_story,
)
from ..dispatch_land import execute_dispatch_land
from ..ports.fs import FsPort
from ..ports.vcs import VcsPort

_JOURNAL_FILENAME = "journal.jsonl"
_TICK_SECONDS = 60
_BASE_REF = "origin/main"
_MERGE_INTO = "main"


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
        prepared = prepare_for_write_offloading_fields(
            entry, offload_fields=offload_fields
        )
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


def _launch_story_started_ts(folded, run_id: str) -> str | None:
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH):
        if entry.run_id == run_id and entry.phase == Phase.INTENT:
            return entry.ts
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


def gather_dispatch_git_facts(
    vcs: VcsPort,
    *,
    repo_root: Path,
    worktree: Path,
    story_key: str,
    project_slug: str,
    baseline_head_sha: str,
    merge_subject_template: str,
) -> DispatchGitFacts:
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
    raw_branch_merged = (
        vcs.is_branch_merged(repo_root, resolution.resolved, into=_MERGE_INTO)
        if resolution.resolved is not None
        else False
    )
    branch_merged = raw_branch_merged and current_head_sha != baseline_head_sha
    subjects = vcs.commit_subjects(repo_root, _MERGE_INTO)
    merged_keys = promotion_core.merged_story_keys(
        subjects, merge_subject_template, project_slug
    )
    story_merged = normalize(story_key) in merged_keys
    return DispatchGitFacts(
        baseline_head_sha=baseline_head_sha,
        current_head_sha=current_head_sha,
        changed_paths=changed_paths,
        branch_merged=branch_merged,
        story_merged_on_main=story_merged,
    )


def _verification_already_journaled(folded, run_id: str) -> bool:
    return any(
        entry.run_id == run_id and entry.phase == Phase.OUTCOME
        for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFICATION)
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


def _run_and_journal_landing(
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
    verification_verdict: DispatchVerificationVerdict,
    merge_subject_template: str,
) -> int:
    """Land a verified dispatch via Epic 4 machinery and journal (Story 22.4)."""
    effective = compose_dispatch_policy(slug, repo_root)
    landing_result, envelope = execute_dispatch_land(
        project_slug=slug,
        story_key=story_key,
        worktree=worktree,
        repo_root=repo_root,
        verification_verdict=verification_verdict,
        effective=effective,
        fs=fs,
        vcs=vcs,
        process=process,
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
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, counter),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_LAND,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload={
            "verdict": landing_result.verdict.value,
            "ok": landing_result.verdict == DispatchLandingVerdict.LANDED,
            "envelope_verdict": envelope.verdict.value,
            "pr_number": landing_result.pr_number,
            "merge_sha": landing_result.merge_sha,
            "marshal_native": landing_result.marshal_native,
        },
    )
    counter += 1
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        print(
            f"dispatch supervisor: cannot journal landing for {run_id!r}: {exc}",
            file=sys.stderr,
        )
    return counter


def _session_awaits_verification(
    session_alive: bool, git: DispatchGitFacts
) -> bool:
    return (
        not session_alive
        and has_git_progress(git)
        and not git.branch_merged
        and not git.story_merged_on_main
    )


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
    )
    verification_verdict = judge_dispatch_verification(
        DispatchVerificationInput(findings=envelope.findings)
    )
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
    vcs: VcsPort | None = None,
    process: ProcessPort | None = None,
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
    if not any(
        entry.run_id == run_id and entry.phase in (Phase.INTENT, Phase.OUTCOME)
        for entry in launch_entries
    ):
        print(
            f"dispatch supervisor: no dispatch-launch for run {run_id!r}; exiting inert",
            file=sys.stderr,
        )
        return 0

    writer_id = _writer_id()
    counter = 0
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

    while True:
        try:
            git_facts = gather_dispatch_git_facts(
                vcs,
                repo_root=repo_root,
                worktree=worktree,
                story_key=story_key,
                project_slug=slug,
                baseline_head_sha=baseline_head_sha,
                merge_subject_template=merge_subject_template,
            )
        except (VcsCommandError, ValueError) as exc:
            print(
                f"dispatch supervisor: git fact gather failed: {exc}",
                file=sys.stderr,
            )
            time.sleep(_TICK_SECONDS)
            continue

        session_alive = process.is_alive(session_pid)
        verdict = judge_dispatch_completion(
            DispatchCompletionInput(session_alive=session_alive, git=git_facts)
        )
        if verdict == DispatchSessionVerdict.LIVE:
            if _session_awaits_verification(session_alive, git_facts):
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
                    text = fs.read_text(journal_path)
                    if text is not None:
                        folded = _fold_dispatch_journal(fs, run_dir, text)
                v_outcome = _verification_outcome_verdict(folded, run_id)
                if (
                    v_outcome == DispatchVerificationVerdict.VERIFIED.value
                    and not git_facts.story_merged_on_main
                    and not _landing_already_journaled(folded, run_id)
                ):
                    counter = _run_and_journal_landing(
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
                        verification_verdict=DispatchVerificationVerdict.VERIFIED,
                        merge_subject_template=merge_subject_template,
                    )
                    text = fs.read_text(journal_path)
                    if text is not None:
                        folded = _fold_dispatch_journal(fs, run_dir, text)
                    try:
                        git_facts = gather_dispatch_git_facts(
                            vcs,
                            repo_root=repo_root,
                            worktree=worktree,
                            story_key=story_key,
                            project_slug=slug,
                            baseline_head_sha=baseline_head_sha,
                            merge_subject_template=merge_subject_template,
                        )
                        verdict = judge_dispatch_completion(
                            DispatchCompletionInput(
                                session_alive=session_alive, git=git_facts
                            )
                        )
                    except (VcsCommandError, ValueError):
                        pass
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
            counter += 1
            try:
                _append_entry(fs, run_dir, heartbeat, fsync=False)
            except FsError:
                pass
            time.sleep(_TICK_SECONDS)
            continue

        v_outcome = _verification_outcome_verdict(folded, run_id)
        if (
            v_outcome == DispatchVerificationVerdict.VERIFIED.value
            and not git_facts.story_merged_on_main
            and not _landing_already_journaled(folded, run_id)
        ):
            counter = _run_and_journal_landing(
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
                verification_verdict=DispatchVerificationVerdict.VERIFIED,
                merge_subject_template=merge_subject_template,
            )
            text = fs.read_text(journal_path)
            if text is not None:
                folded = _fold_dispatch_journal(fs, run_dir, text)
            try:
                git_facts = gather_dispatch_git_facts(
                    vcs,
                    repo_root=repo_root,
                    worktree=worktree,
                    story_key=story_key,
                    project_slug=slug,
                    baseline_head_sha=baseline_head_sha,
                    merge_subject_template=merge_subject_template,
                )
                verdict = judge_dispatch_completion(
                    DispatchCompletionInput(session_alive=session_alive, git=git_facts)
                )
            except (VcsCommandError, ValueError):
                pass

        intent_entry = build_entry(
            id=JournalEntryId(writer_id, counter),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.INTENT,
            payload={
                "verdict": verdict.value,
                "session_alive": session_alive,
                "baseline_head_sha": git_facts.baseline_head_sha,
                "current_head_sha": git_facts.current_head_sha,
                "changed_paths": list(git_facts.changed_paths),
                "branch_merged": git_facts.branch_merged,
                "story_merged_on_main": git_facts.story_merged_on_main,
            },
        )
        counter += 1
        outcome_entry = build_entry(
            id=JournalEntryId(writer_id, counter),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.OUTCOME,
            intent_id=intent_entry.id,
            payload={"verdict": verdict.value, "ok": True},
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
        ended_at = _format_entry_ts(_now_utc())
        started_at = _launch_story_started_ts(folded, run_id) or ended_at
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
        if verdict == DispatchSessionVerdict.FAILED and has_git_progress(git_facts):
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
