"""Dispatch landing via existing Epic 4 machinery (Story 22.4, FR-193 CAP-4).

Impure edge for the dispatch supervisor: after independent verification
passes, land through ``cli/land.py``/``deploy`` composition (PR merge with
FR-187 subject, Story 4.1 spec promotion, Epic 15 ledger). Lives outside
``cli/`` so ``dispatch_supervisor`` may import it (AD-9).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from .adapters.forge_gh import GhForge
from .adapters.fs_local import FsError, LocalFs
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
from .dispatch_verify import compose_dispatch_policy
from .ports.forge import ForgeCommandError, ForgePort, ForgeRef
from .ports.fs import FsPort
from .ports.vcs import VcsPort

_FORGE_REPO = "rxm7706/local-recipes"
_MERGE_BASE = "main"
_MAINTENANCE_LABEL = "maintenance"


@dataclass(frozen=True)
class DispatchLandingResult:
    """Outcome of a dispatch land attempt."""

    verdict: DispatchLandingVerdict
    merge_sha: str | None = None
    pr_number: int | None = None
    subject: str | None = None
    marshal_native: bool = False


def _dispatch_pr_title(slug: str, story_key: StoryKey) -> Redacted:
    return Redacted(f"feat({slug.removeprefix('pyforge-')}): Story {story_key}")


def _dispatch_pr_body(story_key: StoryKey) -> Redacted:
    return Redacted(
        f"Dispatch-landed story {story_key} via marshal factory dispatch (CAP-4)."
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
    effective = effective if effective is not None else compose_dispatch_policy(
        project_slug, repo_root
    )

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

    merged_keys = promotion.merged_story_keys(main_subjects, template, project_slug)
    if key in merged_keys:
        data["already_landed"] = True
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.ALREADY_LANDED), envelope

    if not may_attempt_dispatch_landing(
        verification_verdict, story_merged_on_main=False
    ):
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

    subject = identity.render_merge_subject(key, template)
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
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

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
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

    data["merged"] = True

    try:
        process.run(
            [
                sys.executable,
                "-m",
                "pyforge.marshal.dispatch_land_finalize",
                project_slug,
                render_feed_key(key),
            ],
            cwd=git_repo_root,
        )
    except ProcessError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-020",
                severity=Severity.ERROR,
                message=(
                    f"dispatch land finalize (promote + ledger) failed for "
                    f"{key}: {exc}"
                ),
            )
        )
        envelope = build_envelope(
            command="dispatch land",
            verdict=compute_verdict(tuple(findings)),
            data=data,
            findings=tuple(findings),
        )
        return DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED), envelope

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
