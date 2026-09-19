"""Post-merge finalize for dispatch land (Story 22.4, CAP-4).

Spawned as a subprocess by ``dispatch_land`` so ``dispatch_supervisor`` never
imports ``cli/`` (AD-9). Composes ``deploy promote`` + ``land``'s sprint
ledger promotion machinery.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.adapters.vcs_git import GitVcs
from pyforge.marshal.cli.config import repo_root
from pyforge.marshal.cli.deploy import (
    _DeployRun,
    _deploy_writer_id,
    _execute_promotion_plan,
    _scan_promotions,
)
from pyforge.marshal.cli.land import _promote_sprint_ledger, _resync_home_branch
from pyforge.marshal.core.identity import MalformedStoryKeyError, normalize
from pyforge.marshal.core.journal import Phase

# Story 51.9 (re-mint of 51.3): distinct journal-kind namespace for this
# module's own resync observation -- never conflated with `cli/land.py`'s
# own `_LAND_*_KIND` constants (a different writer namespace entirely).
_FINALIZE_RESYNC_KIND = "dispatch-land-finalize-resync"


def finalize_dispatch_land(
    project_slug: str, story_key: str, worktree: Path | None = None
) -> int:
    """Run the post-merge finalize sequence for ``story_key``.

    ``worktree`` (Story 51.2), when given, is the dispatch worktree the
    session actually ran in -- its own Tier-3 ``implementation-artifacts/``
    is scanned alongside the primary checkout's, in case the session wrote
    its spec there instead. ``None`` (the default) scans only the primary."""
    root = repo_root()
    fs = LocalFs()
    vcs = GitVcs()
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
        specs_dir = (
            root
            / "_bmad-output"
            / "projects"
            / project_slug
            / "planning-artifacts"
            / "specs"
        )
        _execute_promotion_plan(
            scan.plan.to_promote,
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
    _promote_sprint_ledger(
        fs, vcs, root, project_slug, [key], deploy_run, findings, base="main"
    )
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
    resynced = _resync_home_branch(vcs, True, "merge", root, root, "main", "main", findings)
    deploy_run.write(
        findings,
        kind=_FINALIZE_RESYNC_KIND,
        phase=Phase.OBSERVATION,
        payload={"story_key": str(key), "resynced": resynced},
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
