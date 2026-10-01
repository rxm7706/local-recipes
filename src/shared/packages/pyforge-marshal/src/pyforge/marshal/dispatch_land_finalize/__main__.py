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
from pyforge.marshal.cli.land import (
    _LEDGER_DONE_STATUS,
    _parse_sprint_ledger_statuses,
    _promote_sprint_ledger,
    _resync_home_branch,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import promotion
from pyforge.marshal.core.identity import MalformedStoryKeyError, StoryKey, normalize
from pyforge.marshal.core.journal import Phase
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.refs import ORIGIN_MAIN, ORIGIN_MAIN_SHORT
from pyforge.marshal.core.status import render_ledger_advancements
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

#: Story 79.1: a Tier-3 feed row that reads this is a deliberate state the landing never moves
#: (`_LEDGER_DONE_STATUS`, imported above, is the other one).
_LEDGER_BLOCKED_STATUS = "blocked"


def _run_deferred_work_intake(
    process: ProcessPort, fs: FsPort, vcs: VcsPort, root: Path, project_slug: str, story_key: str
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
                # Story 68.1 (CAP-277): a planning-artifacts-only publish, named by its story;
                # the adapter proves the commit's paths before it sets the journaled opt-out.
                preflight_skip_reason=f"marshal deferred-work intake for {short_slug!r}, story {story_key}",
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


def _landed_key_not_done_finding(vcs: VcsPort, root: Path, project_slug: str, key: StoryKey) -> Finding | None:
    """Story 68.1 (spec-pyforge-marshal CAP-277): read ``origin/main``'s tracked
    ``sprint-status-ledger.yaml`` -- the ref ``_promote_sprint_ledger`` writes, fetched now, by its
    full refname -- and return ``MRS-DISP-051`` (ERROR) unless every row for the landed ``key``
    reads ``done``. "Reached ``done``" is judged here from the remote's own bytes, never from
    ``_promote_sprint_ledger``'s return value: that function reports a failed publish as a WARN
    and an empty tuple, exactly as it reports an already-converged ledger. An absent key, another
    status, an absent ledger and an unreadable one all fail the same way -- a landing that
    cannot prove its bookkeeping reached ``origin/main`` is never a clean one."""
    ledger_rel = f"_bmad-output/projects/{project_slug}/planning-artifacts/sprint-status-ledger.yaml"
    prefix = f"the landed story's ledger key does not read done on {ORIGIN_MAIN_SHORT}"
    try:
        vcs.fetch(root, "origin", "main")
        text = vcs.file_text_at_ref(root, ORIGIN_MAIN, ledger_rel)
    except VcsCommandError as exc:
        return Finding(
            code="MRS-DISP-051",
            severity=Severity.ERROR,
            message=f"{prefix}: cannot read {ledger_rel} at {ORIGIN_MAIN_SHORT} for {key}: {exc}",
        )
    if text is None:
        return Finding(
            code="MRS-DISP-051",
            severity=Severity.ERROR,
            message=f"{prefix}: {ledger_rel} does not exist at {ORIGIN_MAIN_SHORT} (story {key})",
        )
    rows: list[tuple[str, str]] = []
    for raw_key, status in _parse_sprint_ledger_statuses(text).items():
        try:
            if normalize(raw_key) == key:
                rows.append((raw_key, status))
        except MalformedStoryKeyError:
            continue
    if not rows:
        return Finding(
            code="MRS-DISP-051",
            severity=Severity.ERROR,
            message=f"{prefix}: {ledger_rel} has no row for story {key}",
        )
    not_done = [f"{raw_key} reads {status!r}" for raw_key, status in rows if status != _LEDGER_DONE_STATUS]
    if not_done:
        return Finding(
            code="MRS-DISP-051",
            severity=Severity.ERROR,
            message=f"{prefix}: {'; '.join(not_done)} -- the promote + ledger is still owed",
        )
    return None


def _promote_tier3_feed_row(fs: FsPort, root: Path, project_slug: str, key: StoryKey) -> Finding | None:
    """Story 79.1 (spec-pyforge-marshal CAP-229/CAP-277): write the landed ``key`` ``done`` in the story's
    Tier-3 feed (``implementation-artifacts/sprint-status.yaml``), the file ``_promote_sprint_ledger``
    reads, syncs INTO the tracked twin and never writes back. Left at ``backlog`` it makes the next plain
    ``sprint-ledger-sync`` refuse ("feed would un-finish") until someone aligns it by hand
    (DW-OPS-2026-10-01-1).

    A row already ``done`` or ``blocked`` is left exactly as it is -- a promotion never moves a row
    backwards, and ``blocked`` is the operator's. The rewrite is ``render_ledger_advancements``'s
    byte-preserving line rewrite (the feed has the ledger's ``development_status:`` shape), written
    through ``FsPort.write_text_atomic`` (a temp file in the same directory, then ``os.replace``). The
    feed is gitignored Tier-3, so it is written in place and never published (CAP-233: the operator
    checkout's tracked files are never touched). No lock: a concurrent feed writer inside the
    read-to-replace window can lose one update, and the feed is re-derivable.

    Never creates the file or a row. Returns ``None`` on a write or a no-op; an absent feed, an absent
    row, an unreadable or unwritable feed and a row the rewrite cannot match are ``MRS-DISP-047`` WARN
    findings naming the path -- the post-merge bookkeeping tier this module already uses, never a crash
    and never a second landing refusal this far past the merge."""
    feed_path = root / "_bmad-output" / "projects" / project_slug / "implementation-artifacts" / "sprint-status.yaml"

    def _warn(message: str) -> Finding:
        return Finding(code="MRS-DISP-047", severity=Severity.WARN, message=message, path=str(feed_path))

    try:
        feed_text = fs.read_text(feed_path)
    except FsError as exc:
        return _warn(f"cannot read the Tier-3 sprint feed at {str(feed_path)!r} to mark story {key} done: {exc}")
    if feed_text is None:
        return _warn(f"no Tier-3 sprint feed at {str(feed_path)!r}; story {key}'s feed row was not promoted")
    rows: list[tuple[str, str]] = []
    for raw_key, status in _parse_sprint_ledger_statuses(feed_text).items():
        try:
            if normalize(raw_key) == key:
                rows.append((raw_key, status))
        except MalformedStoryKeyError:
            continue
    if not rows:
        return _warn(f"the Tier-3 sprint feed at {str(feed_path)!r} has no row for story {key}; none was created")
    behind = frozenset(
        raw_key for raw_key, status in rows if status not in (_LEDGER_DONE_STATUS, _LEDGER_BLOCKED_STATUS)
    )
    if not behind:
        return None
    new_text, matched = render_ledger_advancements(feed_text, behind)
    if matched != behind:
        return _warn(
            f"the Tier-3 sprint feed at {str(feed_path)!r} has a row for story {key} that could not be "
            f"rewritten to done ({sorted(behind - matched)}); the feed was left as it was"
        )
    try:
        fs.write_text_atomic(feed_path, new_text)
    except FsError as exc:
        return _warn(f"cannot write the Tier-3 sprint feed at {str(feed_path)!r} to mark story {key} done: {exc}")
    return None


def _promote_tracked_spec(
    vcs: VcsPort, root: Path, project_slug: str, key: StoryKey, worktree: Path | None
) -> Finding | None:
    """Story 79.1 (spec-pyforge-marshal CAP-229/CAP-261b, DW-FU-53-2-4): set the landed story's TRACKED spec
    ``status: done`` on ``origin/main``. The Tier-3 promotion (``_execute_promotion_plan``) only reaches a
    spec the session left in ``implementation-artifacts/``; a session that committed the tracked spec
    itself and left no Tier-3 twin got no promotion at all, and scribe 25.1's spec stayed ``backlog`` on
    ``main`` with an empty Review Triage Log until a hand edit.

    The path is resolved against ``root`` and then the dispatch ``worktree`` (the primary's local tree may
    not hold a spec the merged PR added until the resync later in this run), and read at ``ORIGIN_MAIN``
    -- the ref the caller has just fetched. A status outside ``PRE_DONE_SPEC_STATUSES`` (``done``,
    ``blocked``, ``superseded``, unreadable) and a spec that cannot be found are left alone, silently.
    Otherwise the one-token rewrite (``promotion.set_spec_status``) is published as its own
    ``commit_paths_onto_remote_tip`` commit -- the ledger commit returns early whenever the twin is
    already converged -- so ``origin/main`` moves and the operator checkout never does (CAP-233).

    Returns ``None`` on a publish or a no-op; a failed read or publish is an ``MRS-DISP-047`` WARN."""
    rel: str | None = None
    for base in (root, worktree):
        if base is None:
            continue
        rel = dispatch_core.story_spec_rel_path(base, project_slug, str(key))
        if rel is not None:
            break
    if rel is None:
        return None

    def _warn(message: str) -> Finding:
        return Finding(code="MRS-DISP-047", severity=Severity.WARN, message=message, path=rel)

    try:
        text = vcs.file_text_at_ref(root, ORIGIN_MAIN, rel)
    except VcsCommandError as exc:
        return _warn(f"cannot read story {key}'s tracked spec {rel!r} at {ORIGIN_MAIN_SHORT} to mark it done: {exc}")
    if text is None or promotion.read_spec_status(text) not in promotion.PRE_DONE_SPEC_STATUSES:
        return None
    new_text = promotion.set_spec_status(text, promotion.SPEC_STATUS_DONE)
    if new_text == text:
        return None
    try:
        vcs.commit_paths_onto_remote_tip(
            root,
            remote="origin",
            ref="main",
            writes=((rel, new_text),),
            message=f"marshal: promote story {key}'s tracked spec to done",
            # The adapter proves this is a planning-artifacts-only commit before it sets the opt-out.
            preflight_skip_reason=f"marshal tracked-spec promotion for {project_slug!r}, story {key}",
        )
    except VcsCommandError as exc:
        return _warn(f"story {key}'s tracked spec {rel!r} could not be promoted to done on {ORIGIN_MAIN_SHORT}: {exc}")
    return None


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
    # Story 79.1: corroboration is computed whenever the scan has a plan -- it used to be computed only when
    # `to_promote` was non-empty -- because it now also gates the landed key's Tier-3 feed row and tracked
    # spec below, and a session that committed the tracked spec itself leaves `to_promote` empty. A scan
    # with no plan (`MRS-DEPLOY-003`) corroborates nothing: it fails closed, so neither write happens.
    corroborated: frozenset[StoryKey] = frozenset()
    to_promote: tuple = ()
    if scan.plan is not None:

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
    # Story 68.1 (CAP-277): the promotion above reports a failed publish as a WARN and an empty
    # tuple -- the same as an already-converged ledger -- so what it returned says nothing about
    # whether the key reached `done`. Read `origin/main`'s ledger for that; a key that does not
    # read `done` there is an ERROR finding, which the exit rule below turns into exit 1.
    not_done = _landed_key_not_done_finding(vcs, root, project_slug, key)
    if not_done is not None:
        findings.append(not_done)
    elif key in corroborated:
        # Story 79.1 (DW-OPS-2026-10-01-1, DW-FU-53-2-4): the twin reads `done` on `origin/main` and the
        # landing is corroborated -- so the two files that promotion never reached follow it: the story's
        # Tier-3 feed row (else the next plain `sprint-ledger-sync` refuses "feed would un-finish") and
        # its tracked spec (when the session committed it itself and left no Tier-3 twin to promote). The
        # gate reads `origin/main`, never `_promote_sprint_ledger`'s return value, so a re-run of finalize
        # repairs a feed an earlier run left behind. Both are WARN-only: the PR has already merged.
        feed_finding = _promote_tier3_feed_row(fs, root, project_slug, key)
        if feed_finding is not None:
            findings.append(feed_finding)
        spec_finding = _promote_tracked_spec(vcs, root, project_slug, key, worktree)
        if spec_finding is not None:
            findings.append(spec_finding)
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
    intake_finding = _run_deferred_work_intake(process, fs, vcs, root, project_slug, str(key))
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
            # Story 68.1 (CAP-277): every finding this run collected, all severities -- the
            # promotion's MRS-LAND-011, the resync's MRS-LAND-009, MRS-DISP-051 -- so a failed
            # step is on the journal, not only in a stderr nobody reads.
            "findings": [finding.to_json_dict() for finding in findings],
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
