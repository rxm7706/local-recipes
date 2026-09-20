"""Dispatch landing via existing Epic 4 machinery (Story 22.4, FR-193 CAP-4).

Impure edge for the dispatch supervisor: after independent verification
passes, land through ``cli/land.py``/``deploy`` composition (PR merge with
FR-187 subject, Story 4.1 spec promotion, Epic 15 ledger). Lives outside
``cli/`` so ``dispatch_supervisor`` may import it (AD-9).
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from .adapters.forge_gh import GhForge
from .adapters.fs_local import LocalFs
from .adapters.vcs_git import GitVcs, VcsCommandError
from .core import dispatch as dispatch_core
from .core import identity, promotion
from .core.dispatch_landing import (
    DispatchLandingVerdict,
    may_attempt_dispatch_landing,
    merge_subject_is_marshal_native,
    refuse_unverified_landing,
)
from .core.dispatch_verification import DispatchVerificationVerdict
from .core.egress import Redacted
from .core.identity import StoryKey, normalize, render_feed_key
from .core.model import Envelope, Finding, Severity, Status, build_envelope, status_for
from .core.policy import EffectivePolicy
from .core.verdict import compute_verdict
from .dispatch_land_heal import try_heal_dispatch_land_merge
from .dispatch_verify import (
    _SCOPE_BASE as _ORIGIN_MAIN,
)
from .dispatch_verify import (
    compose_dispatch_policy,
    run_verify_commands_only,
)
from .ports.forge import ForgeCommandError, ForgePort, ForgeRef
from .ports.fs import FsPort
from .ports.vcs import VcsPort

_FORGE_REPO = "rxm7706/local-recipes"
_MERGE_BASE = "main"
_MAINTENANCE_LABEL = "maintenance"
# Story 51.1: `_ORIGIN_MAIN` (imported above from `dispatch_verify`'s own
# `_SCOPE_BASE`, that module's established name for this exact value) is
# deliberately never `_MERGE_BASE` (the LOCAL landing base used everywhere
# else in this file). Verifying against the local `main` would reproduce
# the exact blind spot this story fixes: the 50.4/27.5 incident's
# operator-composed merge commit landed against `origin/main`, not
# whatever a stale local `main` happened to be.
_ORIGIN_REMOTE = "origin"


@dataclass(frozen=True)
class DispatchLandingResult:
    """Outcome of a dispatch land attempt.

    ``pr_number``/``subject``/``marshal_native`` are populated on
    ``REFUSED`` too, once each is known (Story 51.2) -- not just on
    ``LANDED``. ``merge_sha`` stays ``None`` on every ``REFUSED`` result;
    it is only ever set once an actual merge SHA exists."""

    verdict: DispatchLandingVerdict
    merge_sha: str | None = None
    pr_number: int | None = None
    subject: str | None = None
    marshal_native: bool = False


def _dispatch_pr_title(slug: str, story_key: StoryKey) -> Redacted:
    return Redacted(f"feat({slug.removeprefix('pyforge-')}): Story {story_key}")


def _dispatch_pr_body(story_key: StoryKey) -> Redacted:
    return Redacted(f"Dispatch-landed story {story_key} via marshal factory dispatch (CAP-4).")


def _tail_lines(text: str, *, limit: int = 20) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-limit:])


def _describe_verify_failures(reports: tuple[dict[str, object], ...], verify_findings: tuple[Finding, ...]) -> str:
    """Names each failing command plus the tail of its captured output, so
    a runtime exception (e.g. the 50.4/27.5 fixture's ``bare_merge.py``
    ``TypeError``) is legible directly from the ``MRS-DISP-044`` finding,
    not just from the envelope's own data blob.

    Review finding (2026-09-19): re-deriving the "ran but failed" phrasing
    from ``reports`` alone reported a signal-killed command as "exited -9"
    instead of "was terminated by signal 9", and a never-ran command's
    reason as a generic "could not be run" -- discarding the real reason
    ``gate.classify_outcome`` already computed. This now reuses each
    failing command's own ``Finding.message`` (already phrased correctly
    for both cases) as the header, only appending the captured
    stdout/stderr tail when the command actually ran -- ``Finding.message``
    itself never carries captured output. ``reports`` and
    ``verify_findings`` come from the same single pass over
    ``effective.verify_commands.value`` (one report per command, one
    finding only for a non-passing command), so filtering ``reports`` down
    to the non-passing ones lines them up with ``verify_findings`` in
    order."""
    failing_reports = [r for r in reports if r.get("returncode") != 0]
    parts: list[str] = []
    for report, finding in zip(failing_reports, verify_findings, strict=True):
        if not report.get("resolvable", True):
            parts.append(finding.message)
            continue
        captured = f"{report.get('stdout') or ''}{report.get('stderr') or ''}"
        parts.append(f"{finding.message}: {_tail_lines(captured)}")
    return "; ".join(parts)


def _refuse_via_merge_tree_preview(
    *,
    git_repo_root: Path,
    worktree: Path,
    head_branch: str,
    head_sha: str,
    effective: EffectivePolicy,
    vcs: VcsPort,
    process: ProcessPort,
) -> Finding | None:
    """Story 51.1: before ``forge.merge_pr``, when the branch's baseline is
    behind ``origin/main`` at all, materialize the tree ``git merge-tree
    --write-tree`` would actually produce into a throwaway worktree and
    re-run the station's own ``verify_commands`` against it -- catching a
    runtime break the branch's own verification never sees, because it only
    ever ran against the branch's own tree (the 2026-09-18 50.4/27.5
    incident this story fixes). Returns an ``MRS-DISP-044`` finding when the
    preview run is red or unevaluable; ``None`` when the branch is already
    even with ``origin/main``, or the preview is clean and green. A real
    (git-detected) merge conflict is untouched: ``merge_tree_write``
    returning ``None`` falls through to the existing ``forge.merge_pr``
    attempt and its ``MRS-DISP-038``/heal path, which already owns it."""
    try:
        vcs.fetch(git_repo_root, _ORIGIN_REMOTE, _MERGE_BASE)
        behind = vcs.commits_behind(worktree, _ORIGIN_MAIN)
    except VcsCommandError as exc:
        return Finding(
            code="MRS-DISP-044",
            severity=Severity.ERROR,
            message=(f"cannot determine whether {head_branch!r} is behind {_ORIGIN_MAIN!r} before landing: {exc}"),
        )
    if behind == 0:
        return None

    try:
        tree_oid = vcs.merge_tree_write(git_repo_root, _ORIGIN_MAIN, head_sha)
    except VcsCommandError as exc:
        return Finding(
            code="MRS-DISP-044",
            severity=Severity.ERROR,
            message=(f"cannot preview the merge of {head_branch!r} onto {_ORIGIN_MAIN!r} before landing: {exc}"),
        )
    if tree_oid is None:
        # A real git-detected conflict -- already owned by the existing
        # MRS-DISP-038/heal path once `forge.merge_pr` itself hits it.
        return None

    preview_home = Path(tempfile.mkdtemp(prefix="marshal-land-verify-"))
    # `git worktree add` refuses to reuse a directory it did not create
    # itself -- mirrors `merge_branch`'s own mkdtemp+rmdir dance.
    preview_home.rmdir()
    # Review finding (2026-09-19): the ORIGINAL version only wrapped
    # `run_verify_commands_only` in this `finally` -- an `add_worktree_for_tree`
    # failure returned immediately with no cleanup attempt at all, violating
    # this story's own acceptance criterion that the preview worktree is
    # always removed (best-effort) on every return-or-raise path. Both calls
    # now share one `try/finally`. The `finally` itself mirrors `merge_branch`'s
    # own two-stage cleanup (`adapters/vcs_git.py`): try `remove_worktree`
    # first; if that fails (or there was nothing to remove, e.g.
    # `add_worktree_for_tree` never got as far as registering the worktree),
    # fall back to a raw `shutil.rmtree` plus `prune_worktrees` -- both
    # swallowing any failure of their own, same as `merge_branch`.
    try:
        try:
            vcs.add_worktree_for_tree(git_repo_root, preview_home, tree_oid, parent=head_sha)
        except VcsCommandError as exc:
            return Finding(
                code="MRS-DISP-044",
                severity=Severity.ERROR,
                message=(f"cannot materialize the merge-tree preview of {head_branch!r} onto {_ORIGIN_MAIN!r}: {exc}"),
            )

        reports, verify_findings = run_verify_commands_only(effective, process=process, worktree=preview_home)
    finally:
        removed = False
        try:
            vcs.remove_worktree(git_repo_root, preview_home, force=True)
            removed = True
        except VcsCommandError:
            pass
        if not removed:
            shutil.rmtree(preview_home, ignore_errors=True)
            try:
                vcs.prune_worktrees(git_repo_root)
            except VcsCommandError:
                pass

    if not verify_findings:
        return None
    return Finding(
        code="MRS-DISP-044",
        severity=Severity.ERROR,
        message=(
            f"merge-tree preview of {head_branch!r} onto {_ORIGIN_MAIN!r} "
            f"failed verification: {_describe_verify_failures(reports, verify_findings)}"
        ),
    )


def execute_dispatch_land(
    *,
    project_slug: str,
    story_key: str,
    worktree: Path,
    repo_root: Path,
    verification_verdict: DispatchVerificationVerdict,
    effective: EffectivePolicy | None = None,
    fs: FsPort | None = None,
    vcs: VcsPort | None = None,
    forge: ForgePort | None = None,
    process: ProcessPort | None = None,
) -> tuple[DispatchLandingResult, Envelope]:
    """Land a verified dispatch through existing marshal land/deploy semantics."""
    process = process if process is not None else PosixProcess()
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    forge = forge if forge is not None else GhForge()
    effective = effective if effective is not None else compose_dispatch_policy(project_slug, repo_root)

    findings: list[Finding] = []
    data: dict[str, object] = {
        "slug": project_slug,
        "story": story_key,
        "worktree": str(worktree),
    }

    if refuse_unverified_landing(verification_verdict):
        findings.append(
            Finding(
                code="MRS-DISP-014",
                severity=Severity.ERROR,
                message=(
                    f"refusing dispatch land for {story_key!r}: independent "
                    f"verification is {verification_verdict.value!r}, not "
                    "'verified' — no landing on self-report (CAP-3/CAP-4)"
                ),
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.SKIPPED_UNVERIFIED), envelope

    try:
        key = normalize(story_key)
    except ValueError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-015",
                severity=Severity.ERROR,
                message=f"malformed story key {story_key!r}: {exc}",
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

    feed_story = render_feed_key(key)
    template = effective.merge_subject_template.value
    merge_strategy = effective.landing_merge_strategy.value
    delete_branch = effective.landing_branch_retirement.value

    git_repo_root = dispatch_core.canonical_repo_root(repo_root)
    # Story 22.9: the branch carries the station. A run that started under
    # the pre-22.9 `marshal/<key>` name still lands from it -- but only when
    # git has THAT branch checked out at THIS run's worktree; a legacy
    # branch belonging to some other station is refused with the land-first
    # remedy, never pushed and merged under this station's story key.
    try:
        branch_resolution = dispatch_core.resolve_dispatch_branch(
            vcs,
            git_repo_root,
            slug=project_slug,
            story_key=feed_story,
            worktree=worktree,
        )
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-017",
                severity=Severity.ERROR,
                message=f"cannot resolve the dispatch branch for {feed_story!r}: {exc}",
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

    head_branch = branch_resolution.effective_branch
    data["branch"] = head_branch
    if branch_resolution.refusal is not None:
        findings.append(
            Finding(
                code="MRS-DISP-030",
                severity=Severity.ERROR,
                message=branch_resolution.refusal,
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

    try:
        main_subjects = vcs.commit_subjects(git_repo_root, _MERGE_BASE)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-016",
                severity=Severity.ERROR,
                message=f"cannot read {_MERGE_BASE!r} history for landing: {exc}",
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

    def _spec_status_for(candidate_key: StoryKey) -> str | None:
        # Story 51.7/CAP-255: a station-branch match reached through a
        # GitHub PR-merge subject only corroborates a landing when the
        # key's tracked spec reads `status: done` on origin/main -- a
        # mint/fallout/fix PR merges it ready/backlog, not done. Fails
        # closed (never corroborates) on any git read failure.
        try:
            spec_text = dispatch_core.spec_text_at_ref(vcs, git_repo_root, project_slug, str(candidate_key))
        except VcsCommandError:
            return None
        return promotion.read_spec_status(spec_text)

    merged_keys = promotion.corroborated_merged_story_keys(
        main_subjects, template, project_slug, spec_status_for=_spec_status_for
    )
    if key in merged_keys:
        data["already_landed"] = True
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.ALREADY_LANDED), envelope

    if not may_attempt_dispatch_landing(verification_verdict, story_merged_on_main=False):
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

    try:
        vcs.push(git_repo_root, head_branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-017",
                severity=Severity.ERROR,
                message=f"cannot push {head_branch!r} before landing: {exc}",
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

    try:
        head_sha = vcs.resolve_ref(git_repo_root, head_branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-017",
                severity=Severity.ERROR,
                message=f"cannot resolve {head_branch!r} tip: {exc}",
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope
    data["head_sha"] = head_sha

    repo_ref = ForgeRef(_FORGE_REPO)
    head_branch_ref = ForgeRef(head_branch)
    try:
        existing = forge.find_open_pr(repo_ref, head_branch_ref)
    except ForgeCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-018",
                severity=Severity.ERROR,
                message=f"cannot look up PR for {head_branch!r}: {exc}",
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

    try:
        if existing is None:
            pr = forge.create_pr(
                repo_ref,
                ForgeRef(_MERGE_BASE),
                head_branch_ref,
                _dispatch_pr_title(project_slug, key),
                _dispatch_pr_body(key),
            )
            data["opened"] = True
        else:
            pr = forge.update_pr(
                repo_ref,
                existing.number,
                _dispatch_pr_title(project_slug, key),
                _dispatch_pr_body(key),
            )
            data["updated"] = True
    except ForgeCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-018",
                severity=Severity.ERROR,
                message=f"cannot open/update PR for {head_branch!r}: {exc}",
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

    data["pr_number"] = pr.number
    data["pr_url"] = pr.url
    try:
        forge.add_labels(repo_ref, pr.number, (_MAINTENANCE_LABEL,))
    except ForgeCommandError:
        pass

    subject = identity.render_merge_subject(key, template, project_slug)
    data["subject"] = subject
    if not merge_subject_is_marshal_native(subject, template, project_slug):
        findings.append(
            Finding(
                code="MRS-DISP-019",
                severity=Severity.ERROR,
                message=(
                    f"rendered merge subject for {key!r} is not marshal-native "
                    f"per marshal_native_merged_keys — refusing to land"
                ),
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return (
            DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED, pr_number=pr.number, subject=subject),
            envelope,
        )

    preview_finding = _refuse_via_merge_tree_preview(
        git_repo_root=git_repo_root,
        worktree=worktree,
        head_branch=head_branch,
        head_sha=head_sha,
        effective=effective,
        vcs=vcs,
        process=process,
    )
    if preview_finding is not None:
        findings.append(preview_finding)
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return (
            DispatchLandingResult(
                verdict=DispatchLandingVerdict.REFUSED,
                pr_number=pr.number,
                subject=subject,
                marshal_native=True,
            ),
            envelope,
        )

    try:
        forge.merge_pr(
            repo_ref,
            pr.number,
            ForgeRef(merge_strategy),
            expected_head_sha=ForgeRef(head_sha),
            delete_branch=delete_branch,
            subject=ForgeRef(subject),
        )
    except ForgeCommandError as exc:
        heal = try_heal_dispatch_land_merge(
            project_slug=project_slug,
            git_repo_root=git_repo_root,
            worktree=worktree,
            base=_MERGE_BASE,
            head_branch=head_branch,
            head_sha=head_sha,
            subject=subject,
            merge_strategy=merge_strategy,
            delete_branch=delete_branch,
            repo_ref=repo_ref,
            pr=pr,
            fs=fs,
            vcs=vcs,
            forge=forge,
        )
        if heal.escalated_paths:
            paths = ", ".join(heal.escalated_paths)
            findings.append(
                Finding(
                    code="MRS-DISP-038",
                    severity=Severity.ERROR,
                    message=(
                        f"merge of PR #{pr.number} has unknown conflict path(s) "
                        f"({paths}) — refusing to merge or heal mechanically "
                        "(CAP-4/Story 28.20)"
                    ),
                )
            )
            envelope = build_envelope(
                command="dispatch land",
                verdict=compute_verdict(tuple(findings)),
                data=data,
                findings=tuple(findings),
            )
            return (
                DispatchLandingResult(
                    verdict=DispatchLandingVerdict.REFUSED,
                    pr_number=pr.number,
                    subject=subject,
                    marshal_native=True,
                ),
                envelope,
            )
        if not heal.healed:
            findings.append(
                Finding(
                    code="MRS-DISP-020",
                    severity=Severity.ERROR,
                    message=f"merge of PR #{pr.number} failed: {exc}",
                )
            )
            envelope = build_envelope(
                command="dispatch land",
                verdict=compute_verdict(tuple(findings)),
                data=data,
                findings=tuple(findings),
            )
            return (
                DispatchLandingResult(
                    verdict=DispatchLandingVerdict.REFUSED,
                    pr_number=pr.number,
                    subject=subject,
                    marshal_native=True,
                ),
                envelope,
            )
        if heal.landed_via_local_merge:
            data["local_main_advance"] = True
        if heal.retried_forge_merge:
            data["ledger_union_heal"] = True

    data["merged"] = True

    try:
        process.run(
            [
                sys.executable,
                "-m",
                "pyforge.marshal.dispatch_land_finalize",
                project_slug,
                render_feed_key(key),
                str(worktree),
            ],
            cwd=git_repo_root,
        )
    except ProcessError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-020",
                severity=Severity.ERROR,
                message=(f"dispatch land finalize (promote + ledger) failed for {key}: {exc}"),
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return (
            DispatchLandingResult(
                verdict=DispatchLandingVerdict.REFUSED,
                pr_number=pr.number,
                subject=subject,
                marshal_native=True,
            ),
            envelope,
        )

    envelope = build_envelope(
        command="dispatch land",
        verdict=compute_verdict(tuple(findings)),
        data=data,
        findings=tuple(findings),
    )
    landed = status_for(envelope.verdict) is Status.OK
    result = DispatchLandingResult(
        verdict=DispatchLandingVerdict.LANDED if landed else DispatchLandingVerdict.REFUSED,
        merge_sha=head_sha,
        pr_number=pr.number,
        subject=subject,
        marshal_native=True,
    )
    return result, envelope
