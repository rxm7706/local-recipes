"""Dispatch landing via existing Epic 4 machinery (Story 22.4, FR-193 CAP-4).

Impure edge for the dispatch supervisor: after independent verification
passes, land through ``cli/land.py``/``deploy`` composition (PR merge with
FR-187 subject, Story 4.1 spec promotion, Epic 15 ledger). Lives outside
``cli/`` so ``dispatch_supervisor`` may import it (AD-9).
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from .adapters.forge_gh import GhForge
from .adapters.fs_local import FsError, LocalFs
from .adapters.vcs_git import GitVcs, VcsCommandError
from .core import dispatch as dispatch_core
from .core import identity, promotion
from .dispatch_land_heal import try_heal_dispatch_land_merge
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
from .dispatch_verify import (
    _SCOPE_BASE as _ORIGIN_MAIN,
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
    return Redacted(
        f"Dispatch-landed story {story_key} via marshal factory dispatch (CAP-4)."
    )


def _tail_lines(text: str, *, limit: int = 20) -> str:
    lines = text.strip().splitlines()
    return "\n".join(lines[-limit:])


def _describe_verify_failures(
    reports: tuple[dict[str, object], ...], verify_findings: tuple[Finding, ...]
) -> str:
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
            message=(
                f"cannot determine whether {head_branch!r} is behind "
                f"{_ORIGIN_MAIN!r} before landing: {exc}"
            ),
        )
    if behind == 0:
        return None

    try:
        tree_oid = vcs.merge_tree_write(git_repo_root, _ORIGIN_MAIN, head_sha)
    except VcsCommandError as exc:
        return Finding(
            code="MRS-DISP-044",
            severity=Severity.ERROR,
            message=(
                f"cannot preview the merge of {head_branch!r} onto "
                f"{_ORIGIN_MAIN!r} before landing: {exc}"
            ),
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
                message=(
                    f"cannot materialize the merge-tree preview of "
                    f"{head_branch!r} onto {_ORIGIN_MAIN!r}: {exc}"
                ),
            )

        reports, verify_findings = run_verify_commands_only(
            effective, process=process, worktree=preview_home
        )
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


#: The trailing `--write-baseline --spec {name}` remedy suffix every
#: `drift`/`drift-presumed` finding message ends with (verbatim from
#: `pyforge.doctor.sources.chain._drift_findings`) -- the one place the
#: spec name is recoverable from, since the Finding's own `evidence` carries
#: only `{"path": ...}`. `\S+` is safe: a spec name is `<project>/<spec-dir>`
#: and neither segment contains whitespace.
_SPEC_SURFACE_NAME_RE = re.compile(r"--write-baseline --spec (\S+)\s*$")


@dataclass(frozen=True)
class _SpecSurfaceReconcileOutcome:
    """Result of ``_reconcile_spec_surface_drift``. ``finding`` is ``None``
    when there was nothing to reconcile (no drift at all, or the session
    already reconciled itself); otherwise it is exactly one aggregate
    finding -- ``MRS-DISP-047`` (WARN, non-blocking) on success, or
    ``MRS-DISP-048`` (ERROR) when ``refuse`` is also ``True``."""

    finding: Finding | None
    refuse: bool


def _reconcile_spec_surface_drift(
    *,
    git_repo_root: Path,
    worktree: Path,
    head_branch: str,
    key: StoryKey,
    run_id: str | None,
    vcs: VcsPort,
    process: ProcessPort,
) -> _SpecSurfaceReconcileOutcome:
    """Story 53.2 (spec-pyforge-marshal CAP-261b): before ``forge.merge_pr``,
    run the spec-surface verdict over the branch's own tree and reconcile
    any drift that consists ONLY of this branch's own changed files --
    appending one memlog event per drifted spec (naming the story key, the
    run id, and every path) and scoped-stamping exactly those specs -- so a
    session that lands with drift on its own governed files no longer goes
    green while leaving ``main`` red until a human runs the "Story X landed:
    <paths>" ritual by hand (the four fallout PRs of 2026-09-20 this story
    closes). A spec whose drift ALSO names a path this branch did not touch
    is foreign drift: refused (``MRS-DISP-048``) rather than silently
    absorbed into a scoped stamp -- scoping the stamp would accept that
    unrelated drift as reconciled too.

    Reads ``pyforge.doctor.sources.chain.gather_spec_surface`` install-free
    (this checkout's own files on ``sys.path``, never modified -- Boundaries:
    doctor's verdict is read-only here, and stays doctor's alone), mirroring
    ``scripts/spec_surface_reconcile.py``'s own established pattern. Every
    failure of this reconcile machinery itself (the doctor source tree
    unreachable, the verdict crashing, ``VcsPort.changed_files`` failing, a
    memlog append erroring on a locked/missing-frontmatter file, the scoped
    stamp subprocess failing, or the reconcile commit failing to push) also
    reports through ``MRS-DISP-048`` -- the same code, several triggering
    shapes, one tier (AD-31's established reuse pattern; c.f.
    ``MRS-DEPLOY-003``/``MRS-DEPLOY-024``): none of them may reach
    ``forge.merge_pr`` with the branch's own drift left unreconciled."""
    try:
        doctor_src = worktree / "src" / "shared" / "packages" / "pyforge-doctor" / "src"
        if str(doctor_src) not in sys.path:
            sys.path.insert(0, str(doctor_src))
        from pyforge.doctor.sources.chain import gather_spec_surface
    except ImportError as exc:
        return _SpecSurfaceReconcileOutcome(
            finding=Finding(
                code="MRS-DISP-048",
                severity=Severity.ERROR,
                message=(
                    f"cannot reach the spec-surface verdict from {worktree}: "
                    f"{exc} — refusing to land {key} without a drift reconcile"
                ),
            ),
            refuse=True,
        )

    try:
        surface_findings = gather_spec_surface(worktree)
    except Exception as exc:  # noqa: BLE001 -- a read-only judge's own crash
        # must refuse the landing, never be swallowed into a silent merge.
        return _SpecSurfaceReconcileOutcome(
            finding=Finding(
                code="MRS-DISP-048",
                severity=Severity.ERROR,
                message=(
                    f"spec-surface verdict crashed for {worktree}: "
                    f"{exc.__class__.__name__}: {exc} — refusing to land "
                    f"{key} without a drift reconcile"
                ),
            ),
            refuse=True,
        )

    by_spec: dict[str, set[str]] = {}
    for finding in surface_findings:
        if finding.check not in ("drift", "drift-presumed"):
            continue
        match = _SPEC_SURFACE_NAME_RE.search(finding.message)
        path = finding.evidence.get("path") if finding.evidence else None
        if not match or not path:
            continue
        by_spec.setdefault(match.group(1), set()).add(path)

    if not by_spec:
        return _SpecSurfaceReconcileOutcome(finding=None, refuse=False)

    try:
        changed = set(vcs.changed_files(git_repo_root, worktree, base=_ORIGIN_MAIN))
    except VcsCommandError as exc:
        return _SpecSurfaceReconcileOutcome(
            finding=Finding(
                code="MRS-DISP-048",
                severity=Severity.ERROR,
                message=(
                    f"cannot determine {head_branch!r}'s own changed files to "
                    f"reconcile spec-surface drift: {exc} — refusing to land"
                ),
            ),
            refuse=True,
        )

    foreign: dict[str, set[str]] = {}
    own: dict[str, set[str]] = {}
    for name, paths in by_spec.items():
        not_ours = paths - changed
        if not_ours:
            foreign[name] = not_ours
        else:
            own[name] = paths

    if foreign:
        detail = "; ".join(
            f"{name}: {', '.join(sorted(paths))}" for name, paths in sorted(foreign.items())
        )
        return _SpecSurfaceReconcileOutcome(
            finding=Finding(
                code="MRS-DISP-048",
                severity=Severity.ERROR,
                message=(
                    f"spec-surface drift on {head_branch!r} names path(s) this "
                    f"branch did not change — foreign drift, refusing to land "
                    f"rather than absorb it into a scoped stamp: {detail}"
                ),
            ),
            refuse=True,
        )

    memlog_script = worktree / "_bmad" / "scripts" / "memlog.py"
    stamp_script = worktree / "scripts" / "spec_surface_check.py"
    run_note = f" (run {run_id})" if run_id else ""
    committed_paths: list[Path] = []
    for name, paths in sorted(own.items()):
        project, _, spec_dir = name.partition("/")
        memlog_path = (
            worktree
            / "_bmad-output"
            / "projects"
            / project
            / "planning-artifacts"
            / "specs"
            / spec_dir
            / ".memlog.md"
        )
        text = f"Story {key} landed{run_note}: {', '.join(sorted(paths))}"
        try:
            result = process.run(
                [
                    sys.executable,
                    str(memlog_script),
                    "append",
                    "--path",
                    str(memlog_path),
                    "--type",
                    "event",
                    "--text",
                    text,
                ],
                cwd=worktree,
            )
        except ProcessError as exc:
            return _SpecSurfaceReconcileOutcome(
                finding=Finding(
                    code="MRS-DISP-048",
                    severity=Severity.ERROR,
                    message=(
                        f"memlog append failed for {name} while reconciling "
                        f"spec-surface drift on {head_branch!r}: {exc} — "
                        "refusing to land"
                    ),
                ),
                refuse=True,
            )
        if result.returncode != 0:
            return _SpecSurfaceReconcileOutcome(
                finding=Finding(
                    code="MRS-DISP-048",
                    severity=Severity.ERROR,
                    message=(
                        f"memlog append refused for {name} while reconciling "
                        f"spec-surface drift on {head_branch!r} "
                        f"(exit {result.returncode}): {result.stderr.strip()} "
                        "— refusing to land"
                    ),
                ),
                refuse=True,
            )
        committed_paths.append(memlog_path.relative_to(worktree))

    stamp_argv = [sys.executable, str(stamp_script), "--write-baseline"]
    for name in sorted(own):
        stamp_argv.extend(["--spec", name])
    try:
        stamp_result = process.run(stamp_argv, cwd=worktree)
    except ProcessError as exc:
        return _SpecSurfaceReconcileOutcome(
            finding=Finding(
                code="MRS-DISP-048",
                severity=Severity.ERROR,
                message=(
                    f"scoped spec-surface baseline stamp failed on "
                    f"{head_branch!r}: {exc} — refusing to land"
                ),
            ),
            refuse=True,
        )
    if stamp_result.returncode != 0:
        return _SpecSurfaceReconcileOutcome(
            finding=Finding(
                code="MRS-DISP-048",
                severity=Severity.ERROR,
                message=(
                    f"scoped spec-surface baseline stamp refused on "
                    f"{head_branch!r} (exit {stamp_result.returncode}): "
                    f"{stamp_result.stderr.strip()} — refusing to land"
                ),
            ),
            refuse=True,
        )
    committed_paths.append(Path("scripts") / ".spec-surface-baseline.json")

    try:
        vcs.commit_paths(
            worktree,
            tuple(committed_paths),
            f"marshal: reconcile spec-surface drift for {key}",
        )
        vcs.push(git_repo_root, head_branch)
    except VcsCommandError as exc:
        return _SpecSurfaceReconcileOutcome(
            finding=Finding(
                code="MRS-DISP-048",
                severity=Severity.ERROR,
                message=(
                    f"cannot commit/push the spec-surface reconcile for "
                    f"{head_branch!r}: {exc} — refusing to land"
                ),
            ),
            refuse=True,
        )

    reconciled = "; ".join(
        f"{name}: {', '.join(sorted(paths))}" for name, paths in sorted(own.items())
    )
    return _SpecSurfaceReconcileOutcome(
        finding=Finding(
            code="MRS-DISP-047",
            severity=Severity.WARN,
            message=(
                f"reconciled spec-surface drift on {head_branch!r} before "
                f"landing {key} — the session left this unreconciled: {reconciled}"
            ),
        ),
        refuse=False,
    )


def execute_dispatch_land(
    *,
    project_slug: str,
    story_key: str,
    worktree: Path,
    repo_root: Path,
    verification_verdict: DispatchVerificationVerdict,
    run_id: str | None = None,
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

    def _spec_status_for(candidate_key: StoryKey) -> str | None:
        # Story 51.7/CAP-255: a station-branch match reached through a
        # GitHub PR-merge subject only corroborates a landing when the
        # key's tracked spec reads `status: done` on origin/main -- a
        # mint/fallout/fix PR merges it ready/backlog, not done. Fails
        # closed (never corroborates) on any git read failure.
        try:
            spec_text = dispatch_core.spec_text_at_ref(
                vcs, git_repo_root, project_slug, str(candidate_key)
            )
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
            DispatchLandingResult(
                verdict=DispatchLandingVerdict.REFUSED, pr_number=pr.number, subject=subject
            ),
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

    reconcile_outcome = _reconcile_spec_surface_drift(
        git_repo_root=git_repo_root,
        worktree=worktree,
        head_branch=head_branch,
        key=key,
        run_id=run_id,
        vcs=vcs,
        process=process,
    )
    if reconcile_outcome.finding is not None:
        findings.append(reconcile_outcome.finding)
    if reconcile_outcome.refuse:
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
