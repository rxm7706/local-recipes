"""Post-merge finalize for dispatch land (Story 22.4, CAP-4).

Spawned as a subprocess by ``dispatch_land`` so ``dispatch_supervisor`` never
imports ``cli/`` (AD-9). Composes ``deploy promote`` + ``land``'s sprint
ledger promotion machinery.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from pyforge.marshal.adapters.fs_local import FsError, LocalFs
from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.cli.config import repo_root
from pyforge.marshal.cli.deploy import (
    _deploy_writer_id,
    _DeployRun,
    _execute_promotion_plan,
    _scan_promotions,
)
from pyforge.marshal.cli.land import _promote_sprint_ledger, _resync_home_branch
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import promotion
from pyforge.marshal.core.identity import MalformedStoryKeyError, StoryKey, normalize
from pyforge.marshal.core.journal import Phase
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.ports.fs import FsPort
from pyforge.marshal.ports.vcs import VcsPort

# Story 53.2 review (B5/B6/B7): mirrors `_LAND_DEFERRED_WORK_LOCK_TIMEOUT_S`
# (cli/land.py) -- same class of lock, same timeout, a distinct constant
# only because this module never imports that one (AD-9).
_FINALIZE_DEFERRED_WORK_LOCK_TIMEOUT_S = 5.0

# Story 51.9 (re-mint of 51.3): distinct journal-kind namespace for this
# module's own resync observation -- never conflated with `cli/land.py`'s
# own `_LAND_*_KIND` constants (a different writer namespace entirely).
_FINALIZE_RESYNC_KIND = "dispatch-land-finalize-resync"

#: `deferred_work_intake.py`'s own `--project` flag takes the SHORT slug
#: (`_project_slug_map` strips this prefix) -- never the full
#: `_bmad-output/projects/<slug>` directory name.
_PROJECT_SLUG_PREFIX = "pyforge-"


def _run_deferred_work_intake(
    process: ProcessPort, fs: FsPort, vcs: VcsPort, root: Path, project_slug: str
) -> Finding | None:
    """Story 53.2 (spec-pyforge-marshal CAP-261b): promote this landing's
    story spec's own frontmatter ``deferred:`` entries into the project's
    tracked ``deferred-work-ledger.md`` via ``scripts/deferred_work_intake.py
    --fix`` -- the hand-driven gap that script's own module docstring names
    (bmad-loop's harvest only covers loop runs, never a dispatch land).

    Returns ``None`` on a clean or no-op intake run. Never blocking -- the
    PR has already merged by the time this runs, so an intake refusal (e.g.
    a deferral with no resolvable ``location:``) is journaled through the
    same non-gating ``MRS-DISP-047`` tier ``_reconcile_spec_surface_drift``
    (``dispatch_land.py``) uses, never silently dropped, and never a second
    landing refusal this far past the merge.

    Review pass 2026-09-20 (B5/B6/B7): the script's own ``--fix`` writes the
    tracked ledger directly to ``root``'s working tree (``os.replace``) with
    no commit and no lock -- left as-is, this both loses the promotion (B5)
    and poisons the NEXT finalize's ``has_uncommitted_changes`` gate with
    dirt that was never actually committed on ``main`` (B6). Held under the
    same advisory-lock primitive ``_promote_sprint_ledger``/
    ``_promote_deferred_work`` already use (B7), this now: reads the
    ledger's pre-``--fix`` text, runs ``--fix``, and -- only when the text
    actually changed -- publishes the new text onto ``origin/main`` via
    ``commit_paths_onto_remote_tip`` (CAP-5: an isolated detached worktree,
    never a commit on ``root`` itself) and restores ``root``'s own working
    -tree copy back to its pre-``--fix`` text. The authoritative write now
    lives on ``origin/main``; a later resync picks it up the normal way, and
    ``root`` is never left dirty by this step."""
    short_slug = project_slug.removeprefix(_PROJECT_SLUG_PREFIX)
    tracked_path = root / "_bmad-output" / "projects" / project_slug / "planning-artifacts" / "deferred-work-ledger.md"
    tracked_rel = f"_bmad-output/projects/{project_slug}/planning-artifacts/deferred-work-ledger.md"
    try:
        lock = fs.acquire_advisory_lock(tracked_path, timeout_s=_FINALIZE_DEFERRED_WORK_LOCK_TIMEOUT_S)
    except FsError as exc:
        return Finding(
            code="MRS-DISP-047",
            severity=Severity.WARN,
            message=(
                f"cannot acquire the deferred-work-ledger lock on "
                f"{str(tracked_path)!r} within "
                f"{_FINALIZE_DEFERRED_WORK_LOCK_TIMEOUT_S}s -- another "
                f"finalize is plausibly running concurrently for "
                f"{short_slug!r}; deferred-work intake skipped this run: {exc}"
            ),
        )
    try:
        original_text = fs.read_text(tracked_path)
        try:
            result = process.run(
                [
                    sys.executable,
                    str(root / "scripts" / "deferred_work_intake.py"),
                    "--fix",
                    "--project",
                    short_slug,
                ],
                cwd=root,
            )
        except ProcessError as exc:
            return Finding(
                code="MRS-DISP-047",
                severity=Severity.WARN,
                message=f"deferred-work intake could not run for {short_slug!r}: {exc}",
            )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            return Finding(
                code="MRS-DISP-047",
                severity=Severity.WARN,
                message=(f"deferred-work intake refused (exit {result.returncode}) for {short_slug!r}: {detail}"),
            )
        new_text = fs.read_text(tracked_path)
        if new_text == original_text:
            return None
        commit_finding: Finding | None = None
        try:
            vcs.commit_paths_onto_remote_tip(
                root,
                remote="origin",
                ref="main",
                writes=((tracked_rel, new_text or ""),),
                message=f"marshal: promote deferred-work intake for {short_slug!r}",
            )
        except VcsCommandError as exc:
            commit_finding = Finding(
                code="MRS-DISP-047",
                severity=Severity.WARN,
                message=(
                    f"deferred-work intake for {short_slug!r} wrote "
                    f"{str(tracked_path)!r} but could not be published to "
                    f"'origin/main': {exc}"
                ),
            )
        finally:
            if original_text is None:
                tracked_path.unlink(missing_ok=True)
            else:
                fs.write_text_atomic(tracked_path, original_text)
        return commit_finding
    finally:
        fs.release_advisory_lock(lock)


def finalize_dispatch_land(
    project_slug: str,
    story_key: str,
    worktree: Path | None = None,
    process: ProcessPort | None = None,
) -> int:
    """Run the post-merge finalize sequence for ``story_key``.

    ``worktree`` (Story 51.2), when given, is the dispatch worktree the
    session actually ran in -- its own Tier-3 ``implementation-artifacts/``
    is scanned alongside the primary checkout's, in case the session wrote
    its spec there instead. ``None`` (the default) scans only the primary."""
    root = repo_root()
    fs = LocalFs()
    vcs = GitVcs()
    process = process if process is not None else PosixProcess()
    try:
        key = normalize(story_key)
    except MalformedStoryKeyError as exc:
        print(f"dispatch land finalize: {exc}", file=sys.stderr)
        return 1

    findings: list = []
    data: dict[str, object] = {"lock_contended": False}
    deploy_run = _DeployRun(fs, root, project_slug, _deploy_writer_id("dispatch-land-finalize"))
    scan = _scan_promotions(root, project_slug, vcs=vcs, fs=fs, worktree=worktree)
    findings.extend(scan.findings)
    if scan.plan is not None and scan.plan.to_promote:

        def _spec_status_for(candidate_key: StoryKey) -> str | None:
            # Story 51.7/CAP-255: `_scan_promotions` (cli/deploy.py) still
            # classifies durability through the uncorroborated
            # `merged_story_keys` -- untouched deliberately, per this
            # story's own Binding. Re-gate its `to_promote` output HERE,
            # against the same `origin/main`-anchored spec-status
            # corroboration `dispatch_land`/`dispatch_supervisor` already
            # apply, so a mint/fallout/fix PR's station-branch merge can no
            # longer promote a Tier-3 spec that was never actually landed.
            # Fails closed (never corroborates) on any git read failure.
            try:
                spec_text = dispatch_core.spec_text_at_ref(vcs, root, project_slug, str(candidate_key))
            except VcsCommandError:
                return None
            return promotion.read_spec_status(spec_text)

        corroborated = promotion.corroborated_merged_story_keys(
            scan.combined_subjects,
            scan.template,
            project_slug,
            spec_status_for=_spec_status_for,
        )
        to_promote = tuple(candidate for candidate in scan.plan.to_promote if candidate.story_key in corroborated)
    else:
        to_promote = ()
    if to_promote:
        specs_dir = root / "_bmad-output" / "projects" / project_slug / "planning-artifacts" / "specs"
        _execute_promotion_plan(
            to_promote,
            project_slug=project_slug,
            fs=fs,
            vcs=vcs,
            root=root,
            specs_dir=specs_dir,
            deploy_run=deploy_run,
            findings=findings,
            data=data,
        )

    # CAP-5 made ``base`` keyword-only. Omitting it crashed finalize
    # after a green merge, so the tracked ledger stayed backlog/review
    # and drain re-implemented the landed story (42.2 / 42.3).
    _promote_sprint_ledger(fs, vcs, root, project_slug, [key], deploy_run, findings, base="main")
    # Story 51.9 (re-mint of 51.3): `_promote_sprint_ledger` deliberately
    # never touches the primary checkout's own working tree (CAP-5) -- so
    # nothing else picked up that promotion either, and the fleet
    # campaign's next cycle kept reading the primary's stale on-disk
    # ledger copy until a human ran `git pull`. Reuse
    # `_resync_home_branch` VERBATIM (same primitive `marshal land` already
    # uses to keep a loop-home current with `origin/main`) to fast-forward
    # THIS primary checkout too, whenever it is safely a clean `main` at
    # its own tip -- a dirty or non-`main` checkout is refused exactly as
    # `_resync_home_branch` already refuses one, via its own pre-existing
    # `_MRS_LAND_009` WARN, never a second write path.
    #
    # Review pass 2026-09-19: `_resync_home_branch` only checks SHA-match,
    # never dirtiness -- a dirty checkout sitting exactly at local `main`'s
    # own tip would pass that check unchanged and still get fast-forwarded
    # with the dirty changes in place. Gate on dirtiness HERE, before even
    # calling it, rather than modifying that shared primitive.
    if vcs.has_uncommitted_changes(root):
        resynced = False
    else:
        resynced = _resync_home_branch(vcs, True, "merge", root, root, "main", "main", findings)
    intake_finding = _run_deferred_work_intake(process, fs, vcs, root, project_slug)
    if intake_finding is not None:
        findings.append(intake_finding)
    deploy_run.write(
        findings,
        kind=_FINALIZE_RESYNC_KIND,
        phase=Phase.OBSERVATION,
        payload={
            "story_key": str(key),
            "resynced": resynced,
            "deferred_work_intake_finding": (intake_finding.to_json_dict() if intake_finding is not None else None),
        },
    )
    blocking = [f for f in findings if f.severity.name == "ERROR"]
    if blocking:
        for finding in blocking:
            print(f"finding {finding.code}: {finding.message}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dispatch land finalize (Story 22.4)")
    parser.add_argument("project_slug")
    parser.add_argument("story_key")
    parser.add_argument("worktree", nargs="?", default=None)
    args = parser.parse_args(argv)
    worktree = Path(args.worktree) if args.worktree is not None else None
    return finalize_dispatch_land(args.project_slug, args.story_key, worktree)


if __name__ == "__main__":
    raise SystemExit(main())
