"""Dispatch landing via existing Epic 4 machinery (Story 22.4, FR-193 CAP-4).

Impure edge for the dispatch supervisor: after independent verification
passes, land through ``cli/land.py``/``deploy`` composition (PR merge with
FR-187 subject, Story 4.1 spec promotion, Epic 15 ledger). Lives outside
``cli/`` so ``dispatch_supervisor`` may import it (AD-9).

Story 80.1 (CAP-284): immediately before ``forge.merge_pr`` the landing waits
for the PR head's check runs and refuses on a red one or at the timeout
(``_wait_for_landing_checks``, bounded by the ``dispatch.landing_check_*``
policy keys) -- ``main`` has no branch protection, so nothing else makes a
landing wait for CI.
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from .adapters.forge_gh import GhForge
from .adapters.fs_local import LocalFs
from .adapters.vcs_git import GitVcs, VcsCommandError
from .core import dispatch as dispatch_core
from .core import identity, promotion
from .core.commit_vcs import CommittingVcs
from .core.dispatch_harness_done import FollowupReview
from .core.dispatch_landing import (
    DispatchLandingVerdict,
    may_attempt_dispatch_landing,
    merge_subject_is_marshal_native,
    refuse_unverified_landing,
)
from .core.dispatch_verification import DispatchVerificationVerdict
from .core.egress import Redacted, to_redacted_text
from .core.identity import StoryKey, normalize, render_feed_key
from .core.journal import LANDING_CHECKS_FIELD
from .core.landing_checks import CheckRun, CheckState, classify_check_runs
from .core.model import Envelope, Finding, Severity, Status, build_envelope, status_for
from .core.policy import EffectivePolicy, LandingCheckSettings, resolve_landing_check_settings
from .core.refs import ORIGIN_MAIN as _ORIGIN_MAIN
from .core.refs import ORIGIN_MAIN_SHORT
from .core.verdict import compute_verdict
from .dispatch_land_heal import DispatchLandHealResult, try_heal_dispatch_land_merge
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
# Story 51.1: `_ORIGIN_MAIN` (imported above from `core.refs`, Story 60.1) is
# deliberately never `_MERGE_BASE`, which since Story 72.1 is only the PR's
# base branch, the fetch argument and the heal base -- every merge fact in
# this file reads `_ORIGIN_MAIN`. Verifying against the local `main` would reproduce
# the exact blind spot this story fixes: the 50.4/27.5 incident's
# operator-composed merge commit landed against `origin/main`, not
# whatever a stale local `main` happened to be.
_ORIGIN_REMOTE = "origin"
# `_ORIGIN_MAIN` is the full refname (Story 60.1, CAP-270; the heal's probe since 59.1);
# messages name it `ORIGIN_MAIN_SHORT`, as people read it.
# Story 68.1: how much of a failed finalize's stderr the MRS-DISP-020 message keeps (its tail).
_FINALIZE_DETAIL_MAX_CHARS = 1500


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
            message=(f"cannot determine whether {head_branch!r} is behind {ORIGIN_MAIN_SHORT!r} before landing: {exc}"),
        )
    if behind == 0:
        return None

    try:
        tree_oid = vcs.merge_tree_write(git_repo_root, _ORIGIN_MAIN, head_sha)
    except VcsCommandError as exc:
        return Finding(
            code="MRS-DISP-044",
            severity=Severity.ERROR,
            message=(f"cannot preview the merge of {head_branch!r} onto {ORIGIN_MAIN_SHORT!r} before landing: {exc}"),
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
    story_changed_files: tuple[str, ...] | None = None
    try:
        story_changed_files = vcs.changed_files(git_repo_root, worktree, base=_ORIGIN_MAIN)
    except VcsCommandError, AttributeError:
        story_changed_files = None

    try:
        try:
            vcs.add_worktree_for_tree(
                git_repo_root,
                preview_home,
                tree_oid,
                parent=_ORIGIN_MAIN,
                second_parent=head_sha,
            )
        except VcsCommandError as exc:
            return Finding(
                code="MRS-DISP-044",
                severity=Severity.ERROR,
                message=(
                    f"cannot materialize the merge-tree preview of {head_branch!r} onto {ORIGIN_MAIN_SHORT!r}: {exc}"
                ),
            )

        reports, verify_findings = run_verify_commands_only(
            effective,
            process=process,
            worktree=preview_home,
            repo_root=git_repo_root,
            vcs=vcs,
            story_changed_files=story_changed_files,
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
            f"merge-tree preview of {head_branch!r} onto {ORIGIN_MAIN_SHORT!r} "
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


def _group_surface_findings(surface_findings: Iterable[Any]) -> tuple[dict[str, set[str]], set[str]]:
    """Split a spec-surface verdict into ``({spec: drifted paths}, {specs with
    no stamped baseline})``. Only ``drift``/``drift-presumed`` rows that carry
    both a spec name (recovered from the trailing remedy) and a path count;
    every other check is not reconcile's business."""
    by_spec: dict[str, set[str]] = {}
    no_baseline: set[str] = set()
    for finding in surface_findings:
        if finding.check == "no-baseline":
            # Story 53.2 review (B2/E1): a spec with no stamped baseline
            # entry has no per-file drift breakdown to diff against
            # `changed` at all -- collected separately so it can be
            # failed closed rather than silently skipped.
            match = _SPEC_SURFACE_NAME_RE.search(finding.message)
            if match:
                no_baseline.add(match.group(1))
            continue
        if finding.check not in ("drift", "drift-presumed"):
            continue
        match = _SPEC_SURFACE_NAME_RE.search(finding.message)
        path = finding.evidence.get("path") if finding.evidence else None
        if not match or not path:
            continue
        by_spec.setdefault(match.group(1), set()).add(path)
    return by_spec, no_baseline


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
    vcs: CommittingVcs,
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
    ``scripts/spec_surface_reconcile.py``'s own established pattern.

    Story 82.3 (DW-FU-53-2-3, DW-9-1-1): doctor's verdict keeps ONE row per
    path -- the lowest ``(rank, spec name)`` co-governor -- so a station's
    ``src/`` edit names only ``spec-pyforge-core`` on the first read and the
    station's own spec stays drifted until a later pass. The reconcile is
    therefore a bounded loop: stamp the specs the verdict names, RE-READ the
    verdict, and reconcile any further spec that names one of the branch's own
    paths, until none does. Each pass commits its own memlogs and its stamped
    baseline as it goes, so a later refusal strands nothing uncommitted; the
    branch is pushed once, after the loop. Each pass reconciles a spec no
    earlier pass did, and a reconciled spec governs a path of the branch, so the loop is bounded by the number of specs governing
    those paths: a spec still named after its own stamp (the stamp did not
    settle it), or a re-read that raises, refuses (``MRS-DISP-048``). The
    scoped stamp itself refuses a differing path its spec's memlog does not
    name, so each pass ``--accept``s the branch's own paths (and the memlogs and
    baseline this loop writes) and nothing else: hidden foreign drift refuses
    at the stamp.

    Two families of failure, two tiers (AD-31's established reuse pattern;
    c.f. ``MRS-DEPLOY-003``/``MRS-DEPLOY-024``): failing to even EVALUATE
    drift (the doctor source tree unreachable, or the verdict crashing --
    both should be unreachable in a real dispatch worktree, which is always
    a full checkout, but are defended against here regardless) reports
    through the same non-blocking ``MRS-DISP-047`` tier a successful
    reconcile does, since blocking every landing on an environment gap this
    story is not scoped to fix would be a worse outage than the ritual it
    closes. Failing to safely APPLY a reconcile once drift is already known
    (``VcsPort.changed_files`` failing to tell own from foreign, a memlog
    append erroring on a locked/missing-frontmatter file, the scoped stamp
    subprocess failing, or the reconcile commit failing to push) reports
    through ``MRS-DISP-048`` and refuses: none of THESE may reach
    ``forge.merge_pr`` with known, un-reconciled drift left behind."""
    try:
        doctor_src = worktree / "src" / "shared" / "packages" / "pyforge-doctor" / "src"
        if str(doctor_src) not in sys.path:
            sys.path.insert(0, str(doctor_src))
        from pyforge.doctor.sources.chain import gather_spec_surface
    except ImportError as exc:
        # Unlike the failures below, this fires before we know whether the
        # branch left ANY drift behind at all -- a real dispatch worktree is
        # always a full checkout with the doctor source tree in place, so
        # this is an environmental/wiring gap, not a git fact about this
        # landing. Blocking every landing on it would be a worse outage than
        # the ritual this story closes, so it degrades to the same
        # non-blocking MRS-DISP-047 tier as a successful reconcile (AD-31
        # reuse) rather than refusing via MRS-DISP-048 -- visible, never
        # silent, but never gating on an environment problem this story was
        # not scoped to fix.
        return _SpecSurfaceReconcileOutcome(
            finding=Finding(
                code="MRS-DISP-047",
                severity=Severity.WARN,
                message=(
                    f"cannot reach the spec-surface verdict from {worktree}: "
                    f"{exc} — landing {key} without a drift reconcile"
                ),
            ),
            refuse=False,
        )

    try:
        surface_findings = gather_spec_surface(worktree)
    except Exception as exc:  # noqa: BLE001 -- a read-only judge's own crash
        # `gather_spec_surface` already wraps its own body in
        # `degrade_on_exception` (converts an internal crash to a WARN
        # finding rather than raising), so this is defense-in-depth for an
        # exception escaping that boundary itself -- same "can't evaluate,
        # don't know if there's drift" category as the ImportError above,
        # so the same non-blocking MRS-DISP-047 tier applies.
        return _SpecSurfaceReconcileOutcome(
            finding=Finding(
                code="MRS-DISP-047",
                severity=Severity.WARN,
                message=(
                    f"spec-surface verdict crashed for {worktree}: "
                    f"{exc.__class__.__name__}: {exc} — landing {key} "
                    "without a drift reconcile"
                ),
            ),
            refuse=False,
        )

    by_spec, no_baseline = _group_surface_findings(surface_findings)

    if not by_spec and not no_baseline:
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

    memlog_script = worktree / "_bmad" / "scripts" / "memlog.py"
    stamp_script = worktree / "scripts" / "spec_surface_check.py"
    run_note = f" (run {run_id})" if run_id else ""
    # Story 82.3 (DW-FU-53-2-3): Doctor's verdict keeps ONE row per path -- the
    # lowest (rank, spec name) co-governor -- so the first read names only that
    # spec for a path two specs govern, and the other stays drifted until the
    # first is stamped. The reconcile therefore re-reads the verdict after each
    # stamp and reconciles every further spec that names one of the branch's own
    # paths. `changed` is read once, before any commit; what the loop itself
    # writes (each memlog it appends and the baseline) counts as the branch's own
    # too, so a spec governing those files never reads as foreign on a re-read.
    baseline_rel = (Path("scripts") / ".spec-surface-baseline.json").as_posix()
    written: set[str] = {baseline_rel}
    reconciled: dict[str, set[str]] = {}

    while True:
        own_paths = changed | written
        foreign: dict[str, set[str]] = {}
        own: dict[str, set[str]] = {}
        for name in no_baseline:
            # Story 53.2 review (B2/E1): fail closed rather than silently
            # skip. A never-baselined spec cannot be split into own/foreign
            # paths (no per-file drift to diff), so only refuse when this
            # branch actually touched that spec's own tracked folder --
            # an unrelated repo-wide never-baselined spec stays none of this
            # landing's business, same as zero-overlap drift below.
            project, _, spec_dir = name.partition("/")
            spec_prefix = f"_bmad-output/projects/{project}/planning-artifacts/specs/{spec_dir}/"
            touched = {p for p in own_paths if p.startswith(spec_prefix)}
            if touched:
                foreign[name] = touched
        for name, paths in by_spec.items():
            overlap = paths & own_paths
            if not overlap:
                # Drift with zero overlap against this branch's own changed
                # files is pre-existing and unrelated -- not this landing's to
                # reconcile or refuse on (only a path THIS branch touched makes
                # a spec's drift ours or foreign).
                continue
            not_ours = paths - own_paths
            if not_ours:
                foreign[name] = not_ours
            else:
                own[name] = paths

        if foreign:
            detail = "; ".join(f"{name}: {', '.join(sorted(paths))}" for name, paths in sorted(foreign.items()))
            return _SpecSurfaceReconcileOutcome(
                finding=Finding(
                    code="MRS-DISP-048",
                    severity=Severity.ERROR,
                    message=(
                        f"spec-surface drift on {head_branch!r} cannot be safely "
                        f"reconciled — foreign drift, or a spec with no stamped "
                        f"baseline to diff against — refusing to land rather than "
                        f"absorb it into a scoped stamp: {detail}"
                    ),
                ),
                refuse=True,
            )

        # Nothing of this branch's left to reconcile: every drifted spec had
        # zero overlap with its own paths (all skipped above), or the previous
        # stamp settled the last one. Breaking here (rather than falling
        # through) also guards against building a bare `--write-baseline` with
        # no `--spec` flags below, which Boundaries forbid outright.
        if not own:
            break

        # Every pass reconciles a spec no earlier pass did, and a reconciled
        # spec governs at least one own path, so the loop is bounded by the
        # number of specs governing the branch's own paths. A spec the verdict
        # still names after its own stamp did not settle: refuse BEFORE a second
        # memlog append (a stamp that cannot settle it cannot be helped by one).
        survivors = {name: paths for name, paths in own.items() if name in reconciled}
        if survivors:
            detail = "; ".join(f"{name}: {', '.join(sorted(paths))}" for name, paths in sorted(survivors.items()))
            return _SpecSurfaceReconcileOutcome(
                finding=Finding(
                    code="MRS-DISP-048",
                    severity=Severity.ERROR,
                    message=(
                        f"spec-surface drift on {head_branch!r} survived the scoped "
                        f"stamp of its own spec — the stamp did not settle it — "
                        f"refusing to land: {detail}"
                    ),
                ),
                refuse=True,
            )

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
                        "--by",
                        "marshal",
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
            written.add(memlog_path.relative_to(worktree).as_posix())
            reconciled[name] = paths
            # Story 53.2 review (B4/E2): commit each spec's memlog append as
            # soon as it succeeds, rather than batching every spec's commit
            # until the end -- a later spec's failure then refuses the
            # landing without leaving an earlier spec's already-successful
            # append as an uncommitted working-tree edit a retry could
            # silently under-commit (doctor reads on-disk text regardless of
            # commit state, so a retry would see the earlier spec as already
            # clean and never re-touch, and therefore never re-commit, it).
            try:
                vcs.commit_paths(
                    worktree,
                    (memlog_path.relative_to(worktree),),
                    to_redacted_text(f"marshal: reconcile spec-surface drift for {key} ({name})"),
                )
            except VcsCommandError as exc:
                return _SpecSurfaceReconcileOutcome(
                    finding=Finding(
                        code="MRS-DISP-048",
                        severity=Severity.ERROR,
                        message=(
                            f"cannot commit the spec-surface reconcile memlog "
                            f"for {name} on {head_branch!r}: {exc} — refusing "
                            "to land"
                        ),
                    ),
                    refuse=True,
                )

        # ONE stamp for this pass's specs. Story 82.3 (DW-9-1-1): the scoped
        # stamp refuses a differing path its spec's memlog does not name, and a
        # spec's stamp absorbs ALL its drifted paths -- including ones Doctor
        # reports under a co-governor or hides behind a clean one. Each is the
        # branch's own and is narrated on some memlog, so every path of the
        # branch (and of the loop's own writes) is `--accept`ed; a path the
        # branch did not touch is not, so the stamp itself refuses hidden
        # foreign drift.
        stamp_argv = [sys.executable, str(stamp_script), "--write-baseline"]
        for name in sorted(own):
            stamp_argv.extend(["--spec", name])
        for path in sorted(changed | written):
            stamp_argv.extend(["--accept", path])
        try:
            stamp_result = process.run(stamp_argv, cwd=worktree)
        except ProcessError as exc:
            return _SpecSurfaceReconcileOutcome(
                finding=Finding(
                    code="MRS-DISP-048",
                    severity=Severity.ERROR,
                    message=(f"scoped spec-surface baseline stamp failed on {head_branch!r}: {exc} — refusing to land"),
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

        # Commit the stamped baseline NOW, not after the loop (the Story 53.2
        # B4/E2 reasoning, applied to the baseline): a refusal in a later pass
        # would otherwise strand a stamped, uncommitted baseline that a retry
        # reads as clean and never re-commits, landing a stale baseline on main.
        # The push stays one, after the loop.
        try:
            vcs.commit_paths(
                worktree,
                (Path(baseline_rel),),
                to_redacted_text(f"marshal: reconcile spec-surface drift for {key}"),
            )
        except VcsCommandError as exc:
            return _SpecSurfaceReconcileOutcome(
                finding=Finding(
                    code="MRS-DISP-048",
                    severity=Severity.ERROR,
                    message=(
                        f"cannot commit/push the spec-surface reconcile for {head_branch!r}: {exc} — refusing to land"
                    ),
                ),
                refuse=True,
            )

        # Re-read the verdict over the stamped tree: a co-governor the first
        # read hid behind this pass's specs shows now. A re-read that raises
        # leaves the post-stamp state unverified, so it refuses.
        try:
            surface_findings = gather_spec_surface(worktree)
        except Exception as exc:  # noqa: BLE001 -- a read-only judge's own crash
            return _SpecSurfaceReconcileOutcome(
                finding=Finding(
                    code="MRS-DISP-048",
                    severity=Severity.ERROR,
                    message=(
                        f"cannot re-read the spec-surface verdict on {head_branch!r} "
                        f"after the scoped stamp ({exc.__class__.__name__}: {exc}) — "
                        "the post-stamp state is unverified — refusing to land"
                    ),
                ),
                refuse=True,
            )
        by_spec, no_baseline = _group_surface_findings(surface_findings)

    if not reconciled:
        return _SpecSurfaceReconcileOutcome(finding=None, refuse=False)

    try:
        vcs.push(git_repo_root, head_branch)
    except VcsCommandError as exc:
        return _SpecSurfaceReconcileOutcome(
            finding=Finding(
                code="MRS-DISP-048",
                severity=Severity.ERROR,
                message=(
                    f"cannot commit/push the spec-surface reconcile for {head_branch!r}: {exc} — refusing to land"
                ),
            ),
            refuse=True,
        )

    summary = "; ".join(f"{name}: {', '.join(sorted(paths))}" for name, paths in sorted(reconciled.items()))
    return _SpecSurfaceReconcileOutcome(
        finding=Finding(
            code="MRS-DISP-047",
            severity=Severity.WARN,
            message=(
                f"reconciled spec-surface drift on {head_branch!r} before "
                f"landing {key} — the session left this unreconciled: {summary}"
            ),
        ),
        refuse=False,
    )


# Story 80.1 (CAP-284): `data["landing_checks"]["outcome"]` -- how the wait ended.
_CHECKS_GREEN = "green"
_CHECKS_NO_RUNS = "no-runs"
_CHECKS_RED = "red"
_CHECKS_TIMEOUT = "timeout"
_CHECKS_READ_ERROR = "read-error"

# Story 80.1 (CAP-284): the longest the wait goes without calling `on_wait_tick`. The portal's
# `sweep_lost_runs` marks a published run FAILED `heartbeat_lost` once its heartbeat is older than
# the station time limit (300 s by default), and a landing can wait 45 minutes -- so a wait that
# sleeps `poll_seconds` in one piece must slice it, however large the operator sets that.
_WAIT_TICK_SECONDS = 60.0


@dataclass(frozen=True)
class _LandingChecksOutcome:
    """The end of the landing's check wait (Story 80.1): ``finding`` is the
    refusal (``None`` when the merge may proceed) and ``record`` is the
    plain-JSON account the landing journals -- the ``head_sha`` waited on,
    outcome, polls, seconds waited and every run last read with its status
    and conclusion."""

    finding: Finding | None
    record: dict[str, object]


def _describe_runs(runs: tuple[CheckRun, ...], *, field: str) -> str:
    return ", ".join(f"{run.name} ({getattr(run, field) or 'no conclusion'})" for run in runs)


def _sleep_with_ticks(
    seconds: float,
    *,
    sleep: Callable[[float], None],
    on_wait_tick: Callable[[], None] | None,
) -> None:
    """Sleep ``seconds`` in slices of at most ``_WAIT_TICK_SECONDS``, calling
    ``on_wait_tick`` between slices. No tick after the last slice: the poll
    that follows ticks itself, so a wait of ``poll_seconds <= 60`` ticks once
    per poll and a longer one every minute."""
    remaining = seconds
    while True:
        piece = min(remaining, _WAIT_TICK_SECONDS)
        sleep(piece)
        remaining -= piece
        if remaining <= 0:
            return
        if on_wait_tick is not None:
            on_wait_tick()


def _wait_for_landing_checks(
    *,
    forge: ForgePort,
    repo_ref: ForgeRef,
    head_sha: str,
    pr_number: int,
    settings: LandingCheckSettings,
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    on_wait_tick: Callable[[], None] | None = None,
) -> _LandingChecksOutcome:
    """Story 80.1 (CAP-284, AD-8): wait for ``head_sha``'s check runs before
    the merge. ``main`` has no branch protection and the landing never
    evaluated ``landing_rules``, so nothing else made a landing wait for CI
    (doctor 38.3 merged over a failing ``Detectors / scripts-suite``).

    Polls ``forge.check_runs`` every ``settings.poll_seconds`` for at most
    ``settings.timeout_seconds``. The classifier (``core/landing_checks``) is
    pure; THIS loop owns the clock (``sleep``/``monotonic`` are injected so a
    test drives a fake one). Order inside one poll: read; a read error
    refuses (MRS-DISP-018, never passes); red refuses (MRS-DISP-056, at once,
    even with runs still pending); green proceeds; the empty set proceeds only
    once ``settings.grace_seconds`` have elapsed (workflows register a little
    after a push -- an empty read straight after one is not "no checks");
    otherwise the timeout refuses (MRS-DISP-057, naming the pending runs); else
    sleep ``min(poll, time left)`` and read again. The timeout therefore wins
    over a grace that outlasts it: an empty set never merges past the timeout.

    ``on_wait_tick`` (the supervisor's heartbeat; ``None`` on the CLI landing path,
    which has no run to keep alive) is called after every poll and, via
    ``_sleep_with_ticks``, at least every ``min(poll_seconds, 60)`` seconds of
    waiting -- this loop knows nothing about what a tick does.

    A refusal leaves the PR open -- this function closes and merges nothing --
    so re-running the landing merges once CI is green."""
    timeout_s = settings.timeout_seconds
    started = monotonic()
    polls = 0
    elapsed = 0.0
    runs: tuple[CheckRun, ...] = ()

    def _outcome(outcome: str, finding: Finding | None, **extra: object) -> _LandingChecksOutcome:
        record: dict[str, object] = {
            "head_sha": head_sha,
            "outcome": outcome,
            "polls": polls,
            "waited_seconds": round(elapsed, 3),
            "runs": [run.to_json_dict() for run in runs],
        }
        record.update(extra)
        return _LandingChecksOutcome(finding=finding, record=record)

    while True:
        polls += 1
        try:
            runs = forge.check_runs(repo_ref, ForgeRef(head_sha))
        except ForgeCommandError as exc:
            elapsed = monotonic() - started
            return _outcome(
                _CHECKS_READ_ERROR,
                Finding(
                    code="MRS-DISP-018",
                    severity=Severity.ERROR,
                    message=(
                        f"cannot read the check runs on {head_sha!r} for PR #{pr_number} before landing: "
                        f"{exc} -- refusing to land; the PR stays open"
                    ),
                ),
                error=str(exc),
            )
        elapsed = monotonic() - started
        if on_wait_tick is not None:
            on_wait_tick()
        verdict = classify_check_runs(runs)
        if verdict.state is CheckState.RED:
            return _outcome(
                _CHECKS_RED,
                Finding(
                    code="MRS-DISP-056",
                    severity=Severity.ERROR,
                    message=(
                        f"PR #{pr_number}'s head {head_sha!r} has red check run(s): "
                        f"{_describe_runs(verdict.red, field='conclusion')} -- refusing to merge; "
                        "the PR stays open, re-run the landing once CI is green"
                    ),
                ),
            )
        if verdict.state is CheckState.GREEN:
            return _outcome(_CHECKS_GREEN, None)
        if verdict.state is CheckState.EMPTY and elapsed >= settings.grace_seconds:
            return _outcome(_CHECKS_NO_RUNS, None)
        if elapsed >= timeout_s:
            if verdict.state is CheckState.PENDING:
                reason = f"check run(s) still pending: {_describe_runs(verdict.pending, field='status')}"
            else:
                reason = "no check run was reported"
            return _outcome(
                _CHECKS_TIMEOUT,
                Finding(
                    code="MRS-DISP-057",
                    severity=Severity.ERROR,
                    message=(
                        f"PR #{pr_number}'s head {head_sha!r}: {reason} after waiting "
                        f"{settings.timeout_minutes:g} minute(s) -- refusing to merge; "
                        "the PR stays open, re-run the landing once CI has finished"
                    ),
                ),
            )
        _sleep_with_ticks(
            min(settings.poll_seconds, timeout_s - elapsed),
            sleep=sleep,
            on_wait_tick=on_wait_tick,
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
    vcs: CommittingVcs | None = None,
    forge: ForgePort | None = None,
    process: ProcessPort | None = None,
    sleep: Callable[[float], None] | None = None,
    monotonic: Callable[[], float] | None = None,
    on_wait_tick: Callable[[], None] | None = None,
    followup_review: FollowupReview | None = None,
) -> tuple[DispatchLandingResult, Envelope]:
    """Land a verified dispatch through existing marshal land/deploy semantics.

    Story 73.1 (CAP-281): ``followup_review`` marks the run a follow-up review of a story that already
    landed, so the story key's own merge subject on ``origin/main`` (its FIRST landing) is not evidence the
    review landed. Such a run answers ALREADY_LANDED only when its own head is an ancestor of
    ``origin/main``, and otherwise merges its branch through the path below; when the marker names an open
    ``DW-FRR-<story>`` row, that id and the rendered merge subject go to the finalize subprocess, which
    closes the row. ``None`` (every normal run) is judged exactly as before.

    Story 80.1 (CAP-284): immediately before ``forge.merge_pr`` the landing
    waits for the PR head's check runs (``_wait_for_landing_checks``) and
    refuses on a red one or a timeout -- and so does the head a union heal
    pushes after a failed merge (``try_heal_dispatch_land_merge``'s
    ``await_checks``), which CI has not seen. ``sleep``/``monotonic`` default to
    ``time.sleep``/``time.monotonic``; they are keyword-only seams so a test
    drives a fake clock. ``on_wait_tick`` is called after every poll and at
    least every ``min(poll_seconds, 60)`` seconds of waiting -- the dispatch
    supervisor passes its heartbeat so the portal does not sweep a live run as
    ``heartbeat_lost`` mid-wait; the CLI landing path passes none."""
    sleep = sleep if sleep is not None else time.sleep
    monotonic = monotonic if monotonic is not None else time.monotonic
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

    # Story 72.1 (CAP-280): the ALREADY_LANDED read judges a merge from
    # `origin/main`, never local `main` -- local `main` moves only when
    # finalize can fast-forward the primary checkout, so a story merged on
    # GitHub would read unlanded and be pushed and PR'd again. A failed
    # fetch is tolerated (the read then uses the last-fetched remote-tracking
    # ref); the merge-tree preview's own fetch still refuses a landing it
    # cannot preview.
    try:
        vcs.fetch(git_repo_root, _ORIGIN_REMOTE, _MERGE_BASE)
    except VcsCommandError:
        pass
    try:
        main_subjects = vcs.commit_subjects(git_repo_root, _ORIGIN_MAIN)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-016",
                severity=Severity.ERROR,
                message=f"cannot read {ORIGIN_MAIN_SHORT!r} history for landing: {exc}",
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

    if followup_review is None:
        merged_keys = promotion.corroborated_merged_story_keys(
            main_subjects, template, project_slug, spec_status_for=_spec_status_for
        )
        already_landed = key in merged_keys
    else:
        # Story 73.1 (CAP-281): the story's own merge subject is on `origin/main` from its FIRST landing, so
        # a follow-up review run is judged by its OWN head -- an ancestor of `origin/main` is landed, and
        # anything else merges through the path below.
        try:
            run_head = vcs.resolve_ref(git_repo_root, head_branch)
            already_landed = vcs.merge_base(git_repo_root, run_head, _ORIGIN_MAIN) == run_head
        except VcsCommandError as exc:
            findings.append(
                Finding(
                    code="MRS-DISP-017",
                    severity=Severity.ERROR,
                    message=(
                        f"cannot judge whether the follow-up review branch {head_branch!r} reached "
                        f"{ORIGIN_MAIN_SHORT!r}: {exc}"
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
        data["followup_review"] = True
    if already_landed:
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

    if reconcile_outcome.finding is not None:
        # A non-refusing finding here is MRS-DISP-047: the reconcile
        # actually committed and pushed onto `head_branch`, so the sha
        # captured before this step is stale -- `forge.merge_pr`'s
        # `expected_head_sha` (and the reported `data["head_sha"]`) must
        # reflect the pushed reconcile commit, not the pre-reconcile tip.
        try:
            head_sha = vcs.resolve_ref(git_repo_root, head_branch)
        except VcsCommandError as exc:
            findings.append(
                Finding(
                    code="MRS-DISP-048",
                    severity=Severity.ERROR,
                    message=(
                        f"cannot resolve {head_branch!r} tip after reconciling "
                        f"spec-surface drift: {exc} — refusing to land"
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
        data["head_sha"] = head_sha

    # Story 80.1 (CAP-284): `head_sha` is final here (the reconcile refresh
    # above has run), so this is the commit whose checks gate the merge.
    check_settings = resolve_landing_check_settings(effective)
    checks = _wait_for_landing_checks(
        forge=forge,
        repo_ref=repo_ref,
        head_sha=head_sha,
        pr_number=pr.number,
        settings=check_settings,
        sleep=sleep,
        monotonic=monotonic,
        on_wait_tick=on_wait_tick,
    )
    data[LANDING_CHECKS_FIELD] = checks.record
    if checks.finding is not None:
        findings.append(checks.finding)
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
        # Story 80.1 (CAP-284): the union heal pushes a NEW head (`origin/main` merged into the
        # branch) that the wait above never read, so the heal waits for its checks before it
        # retries the merge. Each head's record is journaled: `landing_checks` holds the first
        # head's, with the healed head's under `heal`.
        heal_waits: list[_LandingChecksOutcome] = []

        def _await_healed_head_checks(new_sha: str) -> Finding | None:
            healed_checks = _wait_for_landing_checks(
                forge=forge,
                repo_ref=repo_ref,
                head_sha=new_sha,
                pr_number=pr.number,
                settings=check_settings,
                sleep=sleep,
                monotonic=monotonic,
                on_wait_tick=on_wait_tick,
            )
            heal_waits.append(healed_checks)
            return healed_checks.finding

        # Story 59.1 (CAP-269): the heal measures against what GitHub merges against, fetched now;
        # a failed fetch skips the heal and the landing refuses as before (MRS-DISP-020).
        heal_skipped = ""
        try:
            vcs.fetch(git_repo_root, _ORIGIN_REMOTE, _MERGE_BASE)
        except VcsCommandError as fetch_exc:
            heal = DispatchLandHealResult(healed=False)
            heal_skipped = f" (heal skipped: could not fetch {ORIGIN_MAIN_SHORT}: {fetch_exc})"
        else:
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
                probe_ref=_ORIGIN_MAIN,
                await_checks=_await_healed_head_checks,
            )
        if heal_waits:
            data[LANDING_CHECKS_FIELD] = {**checks.record, "heal": heal_waits[-1].record}
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
        if heal.checks_refusal is not None:
            # Story 80.1 (CAP-284): the healed head is red or still pending -- the retried merge never
            # ran, so the wait's own finding (MRS-DISP-056/057) is the refusal, not MRS-DISP-020.
            findings.append(heal.checks_refusal)
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
                    message=f"merge of PR #{pr.number} failed: {exc}{heal_skipped}",
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
            if heal_waits:
                # Story 80.1 (CAP-284): the union heal pushed a new head and the retried merge landed IT,
                # so report that head (the one `landing_checks.heal` waited on), not the pre-heal one.
                head_sha = str(heal_waits[-1].record["head_sha"])
                data["head_sha"] = head_sha
        if heal.healed_memlog_paths:
            # Story 78.1 (CAP-283): the Spec memlogs the union merge resolved, beside the flag above.
            data["memlog_union_heal"] = list(heal.healed_memlog_paths)

    data["merged"] = True

    finalize_failure: str | None = None
    finalize_argv = [
        sys.executable,
        "-m",
        "pyforge.marshal.dispatch_land_finalize",
        project_slug,
        render_feed_key(key),
        str(worktree),
    ]
    if followup_review is not None and followup_review.dw_id is not None:
        # Story 73.1 (CAP-281): finalize closes the row this follow-up review served, naming this landing.
        finalize_argv += ["--followup-review-id", followup_review.dw_id, "--landing-subject", subject]
    try:
        finalize_result = process.run(finalize_argv, cwd=git_repo_root)
    except ProcessError as exc:
        finalize_failure = str(exc)
    else:
        # Story 68.1 (CAP-277): `ProcessPort.run` does not raise on a non-zero exit, so a finalize
        # that exited 1 (an ERROR finding -- MRS-DISP-051, its ledger key not `done` on
        # `origin/main`) was read as a clean landing until the exit code was read here.
        if finalize_result.returncode != 0:
            detail = (finalize_result.stderr or finalize_result.stdout or "").strip()
            if len(detail) > _FINALIZE_DETAIL_MAX_CHARS:
                # A crashed finalize's traceback is the tail that matters; keep the finding readable.
                detail = "..." + detail[-_FINALIZE_DETAIL_MAX_CHARS:]
            finalize_failure = f"finalize exited with code {finalize_result.returncode}" + (
                f": {detail}" if detail else ""
            )
    if finalize_failure is not None:
        findings.append(
            Finding(
                code="MRS-DISP-020",
                severity=Severity.ERROR,
                message=(f"dispatch land finalize (promote + ledger) failed for {key}: {finalize_failure}"),
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
