"""Post-merge finalize for dispatch land (Story 22.4, CAP-4).

Spawned as a subprocess by ``dispatch_land`` so ``dispatch_supervisor`` never
imports ``cli/`` (AD-9). Composes ``deploy promote`` + ``land``'s sprint
ledger promotion machinery, then (Story 79.1) carries the promotion to the files that machinery never
reached: the story's Tier-3 feed row, its tracked spec, and (Story 22.13)
its ``epics.md`` ``**Status:**`` line when that section carries one, including when the tracked spec
is already ``done`` on ``origin/main`` (Story 22.15).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from pyforge.marshal.adapters.clock_system import SystemClock
from pyforge.marshal.adapters.fs_local import FsError, LocalFs
from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.cli.config import repo_root
from pyforge.marshal.cli.deploy import (
    _deploy_writer_id,
    _DeployRun,
    _execute_promotion_plan,
    _PromotionScan,
    _scan_promotions,
)
from pyforge.marshal.cli.land import (
    _LEDGER_DONE_STATUS,
    _parse_sprint_ledger_statuses,
    _promote_sprint_ledger,
    _resync_home_branch,
)
from pyforge.marshal.core import deferred_work, promotion
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.commit_vcs import CommittingVcs
from pyforge.marshal.core.egress import to_redacted_text
from pyforge.marshal.core.identity import MalformedStoryKeyError, StoryKey, normalize
from pyforge.marshal.core.journal import Phase
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.refs import ORIGIN_MAIN, ORIGIN_MAIN_SHORT
from pyforge.marshal.core.status import render_ledger_advancements
from pyforge.marshal.ports.clock import ClockPort
from pyforge.marshal.ports.commit import VcsRef
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


@dataclass
class _FollowupReviewCarry:
    """Story 66.1 (spec-pyforge-marshal CAP-275): the one ``DW-FRR-<story>`` row ``_run_deferred_work_intake``
    publishes beside the intake's own rows, and what came of it. ``candidate`` and ``promoted_date`` go in;
    ``promoted_id`` (set only once the row is on ``origin/main``) and ``finding`` (a WARN the intake's own
    single return value has no room for) come back -- the out-parameter shape ``_execute_promotion_plan``'s
    ``findings`` / ``data`` already use."""

    candidate: deferred_work.FollowupReviewCandidate
    promoted_date: str
    promoted_id: str | None = None
    finding: Finding | None = None


@dataclass
class _FollowupReviewClose:
    """Story 73.1 (spec-pyforge-marshal CAP-281): the open ``DW-FRR-<story>`` row a landed follow-up review
    run served, to be rendered closed in the same locked publish. ``dw_id``, ``landing`` (the merge subject
    the landing rendered) and ``resolved_date`` go in; ``closed_id`` (set only once the closure is on
    ``origin/main``) and ``finding`` (the WARN the intake's single return value has no room for) come
    back -- ``_FollowupReviewCarry``'s own in/out shape."""

    dw_id: str
    landing: str
    resolved_date: str
    closed_id: str | None = None
    finding: Finding | None = None


def _run_intake_script(process: ProcessPort, root: Path, short_slug: str) -> Finding | None:
    """Run ``scripts/deferred_work_intake.py --fix`` (Story 53.2): ``None`` on a clean run, an
    ``MRS-DISP-047`` WARN when it cannot launch or refuses."""
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
    return None


def _restore_ledger_copy(fs: FsPort, path: Path, text: str | None) -> None:
    """Put ``path`` back to ``text`` -- the file is removed when it did not exist (``None``)."""
    if text is None:
        path.unlink(missing_ok=True)
    else:
        fs.write_text_atomic(path, text)


def _ledger_publish_base(
    vcs: VcsPort,
    root: Path,
    ledger_rel: str,
    original_text: str | None,
    new_text: str | None,
    *,
    retry: str,
) -> tuple[str | None, str | None]:
    """The ledger text a row edit is built on (Story 66.1's base-text rule, shared by Story 73.1's closure):
    ``(base, None)``, or ``(None, reason)`` when the edit must be skipped. ``retry`` is the verb the skip
    reason's re-run hint uses (``carries`` / ``closes``).

    ``commit_paths_onto_remote_tip`` writes the caller's text over the fetched ``origin/main`` tip, so the
    base is the tip's ledger -- fetched and read here, under the lock the caller holds -- never the primary's
    possibly stale copy: ``remote_text`` when the intake changed nothing (``new_text == original_text``);
    ``new_text`` when the intake changed a primary copy that was the tip's text
    (``original_text == remote_text``); otherwise no base, because two texts are never merged. A tip that
    cannot be fetched or read, and a ledger absent at the tip (one row never creates it), give no base."""
    try:
        vcs.fetch(root, "origin", "main")
        remote_text = vcs.file_text_at_ref(root, ORIGIN_MAIN, ledger_rel)
    except VcsCommandError as exc:
        return None, f"cannot read the deferred-work ledger {ledger_rel!r} at {ORIGIN_MAIN_SHORT}: {exc}"
    if remote_text is None:
        return (
            None,
            f"the deferred-work ledger {ledger_rel!r} does not exist at {ORIGIN_MAIN_SHORT} (one row never creates it)",
        )
    if new_text == original_text:
        return remote_text, None
    if original_text == remote_text:
        return new_text or "", None
    return None, (
        f"the deferred-work ledger {ledger_rel!r} at {ORIGIN_MAIN_SHORT} is not the copy the intake just "
        f"changed, so the two are not merged; a re-run of finalize {retry} it"
    )


def _carry_followup_row(
    vcs: VcsPort,
    root: Path,
    ledger_rel: str,
    original_text: str | None,
    new_text: str | None,
    followup: _FollowupReviewCarry,
) -> tuple[str | None, str | None]:
    """Story 66.1 (CAP-275): the ledger text to publish with ``followup``'s ``DW-FRR-<story>`` row appended,
    and that row's id -- or ``(new_text, None)`` when there is no row to publish (already carried, or skipped
    with a WARN on ``followup.finding``).

    The row is built on the ledger the publish REPLACES, never on the primary's working copy:
    ``commit_paths_onto_remote_tip`` writes the caller's whole text over the fetched ``origin/main`` tip, and
    the primary's copy is stale whenever finalize skipped its resync (a dirty or non-``main`` primary) or a
    concurrent finalize published since. So the tip is fetched and its ledger read here, under the lock the
    caller holds, and the base is:

    * ``remote_text`` when the intake changed nothing (``new_text == original_text``);
    * ``new_text`` when the intake changed the primary's copy and that copy was the tip's text
      (``original_text == remote_text``) -- a faithful successor of the tip;
    * neither otherwise: the intake changed a copy that is not the tip's, and merging two texts is never
      attempted -- the row is skipped (a re-run of finalize carries it).

    A tip that cannot be fetched or read, and a ledger absent at the tip (one row never creates it), skip the
    row the same way. Idempotency (``followup_review_to_promote``) is judged on the base. A skip never touches
    the intake's own publish."""
    story = followup.candidate.story_key
    row_id = deferred_work.followup_review_id(story)
    base, skip_reason = _ledger_publish_base(vcs, root, ledger_rel, original_text, new_text, retry="carries")
    if base is None:
        followup.finding = Finding(
            code="MRS-DISP-047",
            severity=Severity.WARN,
            message=f"story {story}'s recommended follow-up review row ({row_id}) was not carried: {skip_reason}",
            path=ledger_rel,
        )
        return new_text, None
    row = deferred_work.followup_review_to_promote(followup.candidate, base)
    if row is None:
        return new_text, None
    entry = deferred_work.render_followup_review_entry(row, promoted_date=followup.promoted_date)
    return deferred_work.append_ledger_entry(base, entry), row_id


def _close_followup_row(
    vcs: VcsPort,
    root: Path,
    ledger_rel: str,
    original_text: str | None,
    new_text: str | None,
    publish_text: str | None,
    carried: bool,
    close: _FollowupReviewClose,
) -> tuple[str | None, str | None]:
    """Story 73.1 (CAP-281): the ledger text to publish with ``close``'s ``DW-FRR-<story>`` row rendered closed,
    and that row's id -- or ``(publish_text, None)`` when there is nothing to close (the row is absent or no
    longer ``open``, so a re-run closes nothing twice) or the closure was skipped with a WARN on
    ``close.finding``. A skip never touches the text already built for the intake's own publish.

    It rides the same base as the carry (``_ledger_publish_base``): ``publish_text`` itself when the carry
    just built it on the tip's ledger (``carried``), else the tip's ledger the closure fetches and reads."""
    row_id = close.dw_id
    if carried:
        base: str | None = publish_text
        skip_reason: str | None = None
    else:
        base, skip_reason = _ledger_publish_base(vcs, root, ledger_rel, original_text, new_text, retry="closes")
    if base is None:
        close.finding = Finding(
            code="MRS-DISP-047",
            severity=Severity.WARN,
            message=f"the follow-up review row ({row_id}) was not closed: {skip_reason}",
            path=ledger_rel,
        )
        return publish_text, None
    closed = deferred_work.close_followup_review_row(
        base, row_id, resolved_date=close.resolved_date, landing=close.landing
    )
    if closed is None:
        return publish_text, None
    return closed, row_id


def _run_deferred_work_intake(
    process: ProcessPort,
    fs: FsPort,
    vcs: CommittingVcs,
    root: Path,
    project_slug: str,
    story_key: str,
    *,
    followup: _FollowupReviewCarry | None = None,
    close: _FollowupReviewClose | None = None,
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
    ``root`` is never left dirty by this step.

    Story 66.1 (CAP-275): ``followup``, when given, is the landed story's
    recommended follow-up review. Its ``DW-FRR-<story>`` row is added to the
    text this step publishes, in ONE publish with the intake's own rows, so
    neither can drop the other, and a refused or no-op intake still
    publishes the row. ``_carry_followup_row`` builds it on ``origin/main``'s
    ledger -- the text the publish replaces -- never on the primary's
    possibly stale copy. A script that refused or could not launch leaves the
    primary's copy as it read before the script (a half-written ledger is
    put back). Any failure to carry the row is a WARN on ``followup.finding``
    and never touches the intake's own publish; a publish that fails after a
    refused intake has no return slot of its own (the refusal holds it) and
    lands there too.

    Story 73.1 (CAP-281): ``close``, when given, is the open ``DW-FRR-<story>`` row a landed follow-up review
    run served. It is rendered ``status: closed`` (``resolved:`` naming the landing) on the same
    ``origin/main``-based text, inside the same lock and the same single publish, by ``_close_followup_row``;
    its failures are a WARN on ``close.finding`` and never touch the intake's own publish."""
    short_slug = project_slug.removeprefix(_PROJECT_SLUG_PREFIX)
    tracked_path = root / "_bmad-output" / "projects" / project_slug / "planning-artifacts" / "deferred-work-ledger.md"
    tracked_rel = f"_bmad-output/projects/{project_slug}/planning-artifacts/deferred-work-ledger.md"
    try:
        lock = fs.acquire_advisory_lock(tracked_path, timeout_s=_FINALIZE_DEFERRED_WORK_LOCK_TIMEOUT_S)
    except FsError as exc:
        not_carried = ""
        if followup is not None:
            story = followup.candidate.story_key
            not_carried = (
                f"; story {story}'s recommended follow-up review row "
                f"({deferred_work.followup_review_id(story)}) was not carried"
            )
        if close is not None:
            not_carried += f"; the follow-up review row ({close.dw_id}) was not closed"
        return Finding(
            code="MRS-DISP-047",
            severity=Severity.WARN,
            message=(
                f"cannot acquire the deferred-work-ledger lock on "
                f"{str(tracked_path)!r} within "
                f"{_FINALIZE_DEFERRED_WORK_LOCK_TIMEOUT_S}s -- another "
                f"finalize is plausibly running concurrently for "
                f"{short_slug!r}; deferred-work intake skipped this run: {exc}{not_carried}"
            ),
        )
    try:
        original_text = fs.read_text(tracked_path)
        intake_finding = _run_intake_script(process, root, short_slug)
        if intake_finding is None:
            new_text = fs.read_text(tracked_path)
        else:
            # A refused or unlaunchable run leaves the ledger as it read before the script: a script that
            # wrote before it failed must not leave the primary dirty, nor feed a half-written ledger on.
            new_text = original_text
            if fs.read_text(tracked_path) != original_text:
                _restore_ledger_copy(fs, tracked_path, original_text)
        publish_text, row_id = new_text, None
        if followup is not None:
            publish_text, row_id = _carry_followup_row(vcs, root, tracked_rel, original_text, new_text, followup)
        closed_id: str | None = None
        if close is not None:
            publish_text, closed_id = _close_followup_row(
                vcs, root, tracked_rel, original_text, new_text, publish_text, row_id is not None, close
            )
        if row_id is None and closed_id is None and publish_text == original_text:
            return intake_finding
        intake_rows = new_text != original_text
        if closed_id is not None:
            # Story 73.1: the closure names every edit this one publish carries.
            actions = [
                *(["promote deferred-work intake"] if intake_rows else []),
                *([f"carry follow-up review row {row_id}"] if row_id is not None else []),
                f"close follow-up review row {closed_id}",
            ]
            kinds = [
                *(["intake"] if intake_rows else []),
                *(["follow-up review carry"] if row_id is not None else []),
                "follow-up review closure",
            ]
            commit_message = f"marshal: {' and '.join(actions)} for {short_slug!r}"
            skip_reason = f"marshal deferred-work {' and '.join(kinds)} for {short_slug!r}, story {story_key}"
            published = " and ".join(
                [
                    *(["deferred-work intake"] if intake_rows else []),
                    *([f"follow-up review row {row_id}"] if row_id is not None else []),
                    f"closure of follow-up review row {closed_id}",
                ]
            )
        elif row_id is None:
            commit_message = f"marshal: promote deferred-work intake for {short_slug!r}"
            skip_reason = f"marshal deferred-work intake for {short_slug!r}, story {story_key}"
            published = "deferred-work intake"
        elif intake_rows:
            commit_message = (
                f"marshal: promote deferred-work intake and carry follow-up review row {row_id} for {short_slug!r}"
            )
            skip_reason = (
                f"marshal deferred-work intake and follow-up review carry for {short_slug!r}, story {story_key}"
            )
            published = f"deferred-work intake and follow-up review row {row_id}"
        else:
            commit_message = (
                f"marshal: carry follow-up review row {row_id} into the deferred-work ledger for {short_slug!r}"
            )
            skip_reason = f"marshal deferred-work follow-up review carry for {short_slug!r}, story {story_key}"
            published = f"deferred-work ledger update (follow-up review row {row_id})"
        commit_finding: Finding | None = None
        try:
            vcs.commit_paths_onto_remote_tip(
                root,
                remote=VcsRef("origin"),
                ref=VcsRef("main"),
                writes=((tracked_rel, publish_text or ""),),
                message=to_redacted_text(commit_message),
                # Story 68.1 (CAP-277): a planning-artifacts-only publish, named by its story;
                # the adapter proves the commit's paths before it sets the journaled opt-out.
                preflight_skip_reason=to_redacted_text(skip_reason),
            )
        except VcsCommandError as exc:
            commit_finding = Finding(
                code="MRS-DISP-047",
                severity=Severity.WARN,
                message=(
                    f"{published} for {short_slug!r} wrote "
                    f"{str(tracked_path)!r} but could not be "
                    f"published to 'origin/main': {exc}"
                ),
            )
        else:
            if followup is not None and row_id is not None:
                followup.promoted_id = row_id
            if close is not None and closed_id is not None:
                close.closed_id = closed_id
        finally:
            _restore_ledger_copy(fs, tracked_path, original_text)
        if intake_finding is None:
            return commit_finding
        # A refused run publishes only the follow-up rows, so a failed publish has no other place to go.
        if commit_finding is not None:
            if followup is not None:
                followup.finding = commit_finding
            elif close is not None:
                close.finding = commit_finding
        return intake_finding
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


def _origin_main_spec_status(vcs: VcsPort, root: Path, project_slug: str, candidate_key: StoryKey) -> str | None:
    """Story 79.1: a story's tracked-spec ``status:`` as ``origin/main`` holds it -- ``spec_text_at_ref``
    read through ``read_spec_status``, the same reader the Tier-3 gate in ``finalize_dispatch_land``
    builds inline (that gate stays exactly as it was; this is the landing gate's own copy of it). Fails
    closed (``None``, never corroborating) on any git read failure."""
    try:
        spec_text = dispatch_core.spec_text_at_ref(vcs, root, project_slug, str(candidate_key))
    except VcsCommandError:
        return None
    return promotion.read_spec_status(spec_text)


def _landing_corroboration(
    vcs: VcsPort, root: Path, project_slug: str, key: StoryKey, scan: _PromotionScan
) -> tuple[bool, Finding | None]:
    """Story 79.1 (spec-pyforge-marshal CAP-229/CAP-255): is ``key``'s landing corroborated -- the gate for
    the two writes this story adds (the Tier-3 feed row and the tracked spec)?

    Judged by ``promotion.corroborated_merged_story_keys`` over ``origin/main``'s commit subjects as they
    are NOW joined with the scan's own, and over the same ``origin/main`` spec-status reader the Tier-3
    gate uses. The scan reads its subjects before finalize's first fetch, so right after a GitHub merge
    neither ``origin/main`` nor local ``main`` holds the landing's merge subject (reproduced with real git,
    2026-10-01). This gate therefore fetches ``origin/main`` ITSELF, immediately before it reads the
    subjects -- it does not lean on any earlier step (``_landed_key_not_done_finding`` happens to fetch
    too, but an edit there must not reopen the stale-gate defect). A scan with no plan
    (``MRS-DEPLOY-003``) fails closed, silently: its own finding is already collected. A fetch or a
    history read that fails is an ``MRS-DISP-047`` WARN naming the ref -- the non-gating post-merge
    bookkeeping tier -- and nothing moves."""
    if scan.plan is None:
        return False, None
    try:
        vcs.fetch(root, "origin", "main")
        fresh_subjects = vcs.commit_subjects(root, ORIGIN_MAIN)
    except VcsCommandError as exc:
        return False, Finding(
            code="MRS-DISP-047",
            severity=Severity.WARN,
            message=(
                f"cannot fetch and read {ORIGIN_MAIN_SHORT}'s commit history ({ORIGIN_MAIN}) to corroborate the "
                f"landing of story {key}; its Tier-3 feed row and tracked spec were not promoted: {exc}"
            ),
        )

    def _spec_status_for(candidate_key: StoryKey) -> str | None:
        # Only the landed key's membership is read back below, so every other key answers "not done"
        # without its own git read -- `fresh_subjects` is the whole history, not one merge.
        if candidate_key != key:
            return None
        return _origin_main_spec_status(vcs, root, project_slug, candidate_key)

    corroborated = promotion.corroborated_merged_story_keys(
        tuple(fresh_subjects) + tuple(scan.combined_subjects),
        scan.template,
        project_slug,
        spec_status_for=_spec_status_for,
    )
    return key in corroborated, None


def _status_token(status: str) -> str:
    """A feed row's status TOKEN: the text before any ``#`` comment, stripped (Story 79.1)."""
    return status.partition("#")[0].strip()


def _promote_tier3_feed_row(fs: FsPort, root: Path, project_slug: str, key: StoryKey) -> tuple[bool, Finding | None]:
    """Story 79.1 (spec-pyforge-marshal CAP-229/CAP-277): write the landed ``key`` ``done`` in the story's
    Tier-3 feed (``implementation-artifacts/sprint-status.yaml``), the file ``_promote_sprint_ledger``
    reads, syncs INTO the tracked twin and never writes back. Left at ``backlog`` it makes the next plain
    ``sprint-ledger-sync`` refuse ("feed would un-finish") until someone aligns it by hand
    (DW-OPS-2026-10-01-1).

    A row whose status TOKEN (the text before any ``#`` comment) is ``done`` or ``blocked`` is left
    exactly as it is -- a promotion never moves a row backwards, and ``blocked`` is the operator's. The
    rewrite is ``render_ledger_advancements``'s line rewrite (the feed has the ledger's
    ``development_status:`` shape): only the matched row's status token changes, and the file is written
    through ``FsPort.write_text_atomic`` (a temp file in the same directory, then ``os.replace``). The file
    is read and written as text, so line endings come back LF-normalised (the feed is generated on Linux).
    The feed is gitignored Tier-3, so it is written in place and never published (CAP-233: the operator
    checkout's tracked files are never touched). No lock: a concurrent feed writer inside the
    read-to-replace window can lose one update, and the feed is re-derivable.

    Never creates the file or a row. Returns ``(True, None)`` when it wrote the feed, ``(False, None)``
    for a no-op, and ``(False, finding)`` when an absent feed, an absent row, an unreadable or unwritable
    feed, or a row the rewrite cannot match or leaves short of done, is an ``MRS-DISP-047`` WARN naming the path -- the post-merge
    bookkeeping tier this module already uses, never a crash and never a second landing refusal this far
    past the merge."""
    feed_path = root / "_bmad-output" / "projects" / project_slug / "implementation-artifacts" / "sprint-status.yaml"

    def _warn(message: str) -> tuple[bool, Finding]:
        return False, Finding(code="MRS-DISP-047", severity=Severity.WARN, message=message, path=str(feed_path))

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
                rows.append((raw_key, _status_token(status)))
        except MalformedStoryKeyError:
            continue
    if not rows:
        return _warn(f"the Tier-3 sprint feed at {str(feed_path)!r} has no row for story {key}; none was created")
    behind = frozenset(raw_key for raw_key, token in rows if token not in (_LEDGER_DONE_STATUS, _LEDGER_BLOCKED_STATUS))
    if not behind:
        return False, None
    new_text, matched = render_ledger_advancements(feed_text, behind)
    if matched != behind:
        return _warn(
            f"the Tier-3 sprint feed at {str(feed_path)!r} has a row for story {key} that could not be "
            f"rewritten to done ({sorted(behind - matched)}); the feed was left as it was"
        )
    # Story 83.22: rewrites are limited to ``development_status:``; judge the result with the sync parser.
    reparsed = _parse_sprint_ledger_statuses(new_text)
    not_done = sorted(raw_key for raw_key in behind if _status_token(reparsed.get(raw_key, "")) != _LEDGER_DONE_STATUS)
    if not_done:
        return _warn(
            f"the Tier-3 sprint feed at {str(feed_path)!r} still reads {not_done} short of done for story {key} "
            f"after the rewrite; the feed was left as it was"
        )
    try:
        fs.write_text_atomic(feed_path, new_text)
    except FsError as exc:
        return _warn(f"cannot write the Tier-3 sprint feed at {str(feed_path)!r} to mark story {key} done: {exc}")
    return True, None


def _local_spec_rel_path(root: Path, worktree: Path | None, project_slug: str, key: StoryKey) -> str | None:
    """Story 66.1 (lifted out of ``_promote_tracked_spec``, Story 79.1): the landed story's tracked spec path,
    repo-relative, resolved against ``root`` and then the dispatch ``worktree`` -- the primary's local tree may
    not hold a spec the merged PR added until the resync later in a finalize run. ``None`` when neither does."""
    for base in (root, worktree):
        if base is None:
            continue
        rel = dispatch_core.story_spec_rel_path(base, project_slug, str(key))
        if rel is not None:
            return rel
    return None


def _followup_review_carry(
    vcs: VcsPort,
    root: Path,
    project_slug: str,
    key: StoryKey,
    worktree: Path | None,
    clock: ClockPort,
    findings: list[Finding],
) -> _FollowupReviewCarry | None:
    """Story 66.1 (spec-pyforge-marshal CAP-275): the landed story's recommended follow-up review, ready for
    ``_run_deferred_work_intake`` to publish -- or ``None``. The spec is read at ``ORIGIN_MAIN`` (the ref the
    landing's own bookkeeping reads) through the two halves ``dispatch_core.spec_text_at_ref`` is made of
    (``_local_spec_rel_path`` + ``file_text_at_ref``), so the path resolves through the dispatch worktree too.
    A story with no local spec, a spec absent at ``ORIGIN_MAIN``, a spec that does not read ``status: done``
    and an absent, ``false`` or unreadable flag all answer ``None`` silently. A spec that cannot be read at
    ``ORIGIN_MAIN`` is an ``MRS-DISP-047`` WARN appended to ``findings`` -- the post-merge bookkeeping tier,
    never a landing refusal this far past the merge."""
    rel = _local_spec_rel_path(root, worktree, project_slug, key)
    if rel is None:
        return None
    try:
        spec_text = vcs.file_text_at_ref(root, ORIGIN_MAIN, rel)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-047",
                severity=Severity.WARN,
                message=(
                    f"cannot read story {key}'s tracked spec {rel!r} at {ORIGIN_MAIN_SHORT} to carry its "
                    f"recommended follow-up review: {exc}"
                ),
                path=rel,
            )
        )
        return None
    candidate = deferred_work.followup_review_candidate(spec_text, key, rel)
    if candidate is None:
        return None
    return _FollowupReviewCarry(candidate=candidate, promoted_date=clock.now().date().isoformat())


def _promote_landed_story_epics_status(
    vcs: CommittingVcs, root: Path, project_slug: str, key: StoryKey, worktree: Path | None
) -> tuple[bool, Finding | None]:
    """Story 22.15: match the landed story's ``epics.md`` ``**Status:**`` line to ``done`` even when the
    tracked spec already reads ``done`` at ``ORIGIN_MAIN``, or when the Tier-3 route promoted the spec this
    run. A ``blocked`` or ``superseded`` tracked spec leaves ``epics.md`` alone. Idempotent when the line
    already reads ``done``."""
    epics_rel = f"_bmad-output/projects/{project_slug}/planning-artifacts/epics.md"
    rel = _local_spec_rel_path(root, worktree, project_slug, key)
    if rel is not None:
        try:
            spec_text = vcs.file_text_at_ref(root, ORIGIN_MAIN, rel)
        except VcsCommandError:
            spec_text = None
        if spec_text is not None:
            spec_status = promotion.read_spec_status(spec_text)
            if spec_status in ("blocked", "superseded"):
                return False, None

    def _epics_gap(message: str) -> Finding:
        return Finding(code="MRS-DISP-047", severity=Severity.WARN, message=message, path=epics_rel)

    epics_gap: Finding | None = None
    epics_text: str | None
    try:
        epics_text = vcs.file_text_at_ref(root, ORIGIN_MAIN, epics_rel)
    except VcsCommandError as exc:
        epics_gap = _epics_gap(
            f"story {key}'s epics.md could not be read at {epics_rel!r} on {ORIGIN_MAIN_SHORT} to match its "
            f"**Status:** line: {exc}"
        )
        epics_text = None
    writes: list[tuple[str, str]] = []
    if epics_gap is None:
        if epics_text is None:
            epics_gap = _epics_gap(
                f"story {key}'s epics.md does not exist at {epics_rel!r} on {ORIGIN_MAIN_SHORT}; its "
                f"**Status:** line was not updated"
            )
        elif not promotion.epics_has_story_heading(epics_text, key):
            epics_gap = _epics_gap(
                f"story {key}'s epics.md has no ### Story {key}: heading at {epics_rel!r} on "
                f"{ORIGIN_MAIN_SHORT}; its **Status:** line was not updated"
            )
        else:
            epics_done = promotion.set_epics_story_status(epics_text, key, promotion.SPEC_STATUS_DONE)
            if epics_done != epics_text:
                writes.append((epics_rel, epics_done))
    if not writes:
        if epics_gap is not None:
            return False, epics_gap
        return False, None
    try:
        vcs.commit_paths_onto_remote_tip(
            root,
            remote=VcsRef("origin"),
            ref=VcsRef("main"),
            writes=tuple(writes),
            message=to_redacted_text(f"marshal: promote story {key}'s epics status to done"),
            preflight_skip_reason=to_redacted_text(
                f"marshal epics-status promotion for {project_slug!r}, story {key}"
            ),
        )
    except VcsCommandError as exc:
        gap = _epics_gap(
            f"story {key}'s epics.md **Status:** line could not be promoted to done on {ORIGIN_MAIN_SHORT}: {exc}"
        )
        return False, gap
    if epics_gap is not None:
        return True, epics_gap
    return True, None


def _promote_tracked_spec(
    vcs: CommittingVcs, root: Path, project_slug: str, key: StoryKey, worktree: Path | None
) -> tuple[bool, Finding | None]:
    """Story 79.1 (spec-pyforge-marshal CAP-229/CAP-261b, DW-FU-53-2-4): set the landed story's TRACKED spec
    ``status: done`` on ``origin/main``. The Tier-3 promotion (``_execute_promotion_plan``) only reaches a
    spec the session left in ``implementation-artifacts/``; a session that committed the tracked spec
    itself and left no Tier-3 twin got no promotion at all, and scribe 25.1's spec stayed ``backlog`` on
    ``main`` with an empty Review Triage Log until a hand edit.

    The path is resolved against ``root`` and then the dispatch ``worktree`` (the primary's local tree may
    not hold a spec the merged PR added until the resync later in this run), and read at ``ORIGIN_MAIN``
    -- the ref the caller has just fetched. A terminal status (``done``, ``blocked``, ``superseded``) and a
    story with no local spec are left alone, silently. A spec absent at ``origin/main``, a status
    ``read_spec_status`` cannot parse (``status: 'backlog' # note`` -- a trailing comment is not a token
    the reader or the writer accepts) and a status that is neither pre-done nor terminal are an
    ``MRS-DISP-047`` WARN naming the path, and nothing moves. Otherwise the one-token rewrite
    (``promotion.set_spec_status``) is published as its own ``commit_paths_onto_remote_tip`` commit --
    ``_promote_sprint_ledger``'s commit returns early whenever the twin is already converged, and it is
    shared with ``marshal land`` -- so ``origin/main`` moves and the operator checkout never does
    (CAP-233). If a publish fails a re-run of finalize repairs it: the gate and the status check are
    idempotent.

    Returns ``(True, None)`` when it published, ``(False, None)`` for a no-op, ``(False, finding)`` when the
    spec itself could not be promoted, and ``(True, finding)`` when the spec published but ``epics.md`` could
    not be matched (Story 22.13 -- epics gaps never roll back the spec publish)."""
    rel = _local_spec_rel_path(root, worktree, project_slug, key)
    if rel is None:
        return False, None

    epics_rel = f"_bmad-output/projects/{project_slug}/planning-artifacts/epics.md"

    def _warn(message: str, *, path: str | None = None) -> tuple[bool, Finding]:
        return False, Finding(code="MRS-DISP-047", severity=Severity.WARN, message=message, path=path or rel)

    def _epics_gap(message: str) -> Finding:
        return Finding(code="MRS-DISP-047", severity=Severity.WARN, message=message, path=epics_rel)

    try:
        text = vcs.file_text_at_ref(root, ORIGIN_MAIN, rel)
    except VcsCommandError as exc:
        return _warn(f"cannot read story {key}'s tracked spec {rel!r} at {ORIGIN_MAIN_SHORT} to mark it done: {exc}")
    if text is None:
        return _warn(f"story {key}'s tracked spec {rel!r} does not exist at {ORIGIN_MAIN_SHORT}; it was not promoted")
    status = promotion.read_spec_status(text)
    if status == promotion.SPEC_STATUS_DONE:
        return _promote_landed_story_epics_status(vcs, root, project_slug, key, worktree)
    if status in ("blocked", "superseded"):
        return False, None
    if status not in promotion.PRE_DONE_SPEC_STATUSES:
        detail = (
            "its frontmatter status could not be read"
            if status is None
            else f"its status {status!r} is not one a landing advances"
        )
        return _warn(f"story {key}'s tracked spec {rel!r} at {ORIGIN_MAIN_SHORT} was not promoted to done: {detail}")
    spec_done_text = promotion.set_spec_status(text, promotion.SPEC_STATUS_DONE)
    writes: list[tuple[str, str]] = [(rel, spec_done_text)]
    epics_gap: Finding | None = None
    epics_text: str | None
    try:
        epics_text = vcs.file_text_at_ref(root, ORIGIN_MAIN, epics_rel)
    except VcsCommandError as exc:
        epics_gap = _epics_gap(
            f"story {key}'s tracked spec {rel!r} will be promoted to done on {ORIGIN_MAIN_SHORT}, but epics.md "
            f"could not be read at {epics_rel!r} to match its **Status:** line: {exc}"
        )
        epics_text = None
    if epics_gap is None:
        if epics_text is None:
            epics_gap = _epics_gap(
                f"story {key}'s tracked spec {rel!r} will be promoted to done on {ORIGIN_MAIN_SHORT}, but epics.md "
                f"does not exist at {epics_rel!r}; its **Status:** line was not updated"
            )
        elif not promotion.epics_has_story_heading(epics_text, key):
            epics_gap = _epics_gap(
                f"story {key}'s tracked spec {rel!r} will be promoted to done on {ORIGIN_MAIN_SHORT}, but epics.md "
                f"has no ### Story {key}: heading at {epics_rel!r}; its **Status:** line was not updated"
            )
        else:
            epics_done = promotion.set_epics_story_status(epics_text, key, promotion.SPEC_STATUS_DONE)
            if epics_done != epics_text:
                writes.append((epics_rel, epics_done))
    try:
        vcs.commit_paths_onto_remote_tip(
            root,
            remote=VcsRef("origin"),
            ref=VcsRef("main"),
            writes=tuple(writes),
            message=to_redacted_text(f"marshal: promote story {key}'s tracked spec to done"),
            # The adapter proves this is a planning-artifacts-only commit before it sets the opt-out.
            preflight_skip_reason=to_redacted_text(f"marshal tracked-spec promotion for {project_slug!r}, story {key}"),
        )
    except VcsCommandError as exc:
        return _warn(f"story {key}'s tracked spec {rel!r} could not be promoted to done on {ORIGIN_MAIN_SHORT}: {exc}")
    if epics_gap is not None:
        return True, epics_gap
    return True, None


def finalize_dispatch_land(
    project_slug: str,
    story_key: str,
    worktree: Path | None = None,
    process: ProcessPort | None = None,
    clock: ClockPort | None = None,
    followup_review_id: str | None = None,
    landing: str | None = None,
) -> int:
    """Run the post-merge finalize sequence for ``story_key``.

    ``worktree`` (Story 51.2), when given, is the dispatch worktree the
    session actually ran in -- its own Tier-3 ``implementation-artifacts/``
    is scanned alongside the primary checkout's, in case the session wrote
    its spec there instead; it is also the second place the tracked spec is
    looked for (Story 79.1). ``None`` (the default) scans only the primary.
    ``clock`` (Story 66.1) dates the follow-up review row; ``None`` is the
    system clock. ``followup_review_id`` and ``landing`` (Story 73.1, CAP-281)
    are the open ``DW-FRR-<story>`` row a landed follow-up review run served and
    the merge subject that landed it: the row is closed in the intake step's own
    locked publish. ``None`` (every normal landing) closes nothing."""
    root = repo_root()
    fs = LocalFs()
    vcs = GitVcs()
    process = process if process is not None else PosixProcess()
    clock = clock if clock is not None else SystemClock()
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
    # Story 68.1 (CAP-277): the promotion above reports a failed publish as a WARN and an empty
    # tuple -- the same as an already-converged ledger -- so what it returned says nothing about
    # whether the key reached `done`. Read `origin/main`'s ledger for that; a key that does not
    # read `done` there is an ERROR finding, which the exit rule below turns into exit 1.
    not_done = _landed_key_not_done_finding(vcs, root, project_slug, key)
    landing_corroborated = feed_row_promoted = tracked_spec_promoted = False
    tier3_promoted_keys = frozenset(candidate.story_key for candidate in to_promote)
    if not_done is not None:
        findings.append(not_done)
    else:
        # Story 79.1 (DW-OPS-2026-10-01-1, DW-FU-53-2-4): the twin reads `done` on `origin/main` -- so, once
        # the landing is corroborated against `origin/main` as the gate itself fetches it, the two
        # files that promotion never reached follow it: the story's Tier-3 feed row (else the next plain
        # `sprint-ledger-sync` refuses "feed would un-finish") and its tracked spec (when the session
        # committed it itself and left no Tier-3 twin to promote). The gate reads `origin/main`, never
        # `_promote_sprint_ledger`'s return value, so a re-run of finalize repairs a feed an earlier run left
        # behind. Every step is WARN-only: the PR has already merged. An uncorroborated landing moves
        # neither, and says so on the journal (`landing_corroborated`), never as a finding.
        landing_corroborated, step_finding = _landing_corroboration(vcs, root, project_slug, key, scan)
        if step_finding is not None:
            findings.append(step_finding)
        if landing_corroborated:
            feed_row_promoted, step_finding = _promote_tier3_feed_row(fs, root, project_slug, key)
            if step_finding is not None:
                findings.append(step_finding)
            # A key the Tier-3 route promoted in THIS run already has its spec copied into the primary's
            # `specs/` and committed locally (`_execute_promotion_plan`), so the local path resolves while
            # `origin/main` may not hold the copy yet -- a misleading "absent" WARN, or a second status-only
            # publish. That route owns the spec; the tracked-spec step is for the session that left no twin.
            # Story 22.15: epics still matches even when the spec step is skipped or the spec already reads
            # `done` on `origin/main`.
            if key not in tier3_promoted_keys:
                tracked_spec_promoted, step_finding = _promote_tracked_spec(vcs, root, project_slug, key, worktree)
            else:
                tracked_spec_promoted, step_finding = _promote_landed_story_epics_status(
                    vcs, root, project_slug, key, worktree
                )
            if step_finding is not None:
                findings.append(step_finding)
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
    # Story 66.1 (CAP-275): the landed story's recommended follow-up review rides the intake's own locked
    # publish, read after the resync so the primary holds the spec the merged PR may have added. Every
    # failure is a WARN: the PR has already merged.
    followup = _followup_review_carry(vcs, root, project_slug, key, worktree, clock, findings)
    # Story 73.1 (CAP-281): the follow-up review run that just landed closes the row it served, in the
    # same locked publish as the carry above -- a normal landing passes no row id and closes nothing.
    close = (
        _FollowupReviewClose(
            dw_id=followup_review_id,
            landing=landing or "",
            resolved_date=clock.now().date().isoformat(),
        )
        if followup_review_id is not None
        else None
    )
    intake_finding = _run_deferred_work_intake(
        process, fs, vcs, root, project_slug, str(key), followup=followup, close=close
    )
    if intake_finding is not None:
        findings.append(intake_finding)
    if followup is not None and followup.finding is not None:
        findings.append(followup.finding)
    if close is not None and close.finding is not None:
        findings.append(close.finding)
    deploy_run.write(
        findings,
        kind=_FINALIZE_RESYNC_KIND,
        phase=Phase.OBSERVATION,
        payload={
            "story_key": str(key),
            "resynced": resynced,
            "deferred_work_intake_finding": (intake_finding.to_json_dict() if intake_finding is not None else None),
            # Story 79.1: booleans, so a skipped promotion reads differently on the journal from a done one
            # (an uncorroborated landing leaves no finding). True only when THIS run wrote the feed row /
            # published the spec -- never for a row or a spec that was already `done`.
            "landing_corroborated": landing_corroborated,
            "feed_row_promoted": feed_row_promoted,
            "tracked_spec_promoted": tracked_spec_promoted,
            # Story 66.1 (CAP-275): the `DW-FRR-<story>` row THIS run published onto origin/main, else null
            # (not flagged, already carried, or a failed read/publish -- the WARN names which).
            "followup_review_promoted_id": followup.promoted_id if followup is not None else None,
            # Story 73.1 (CAP-281): the `DW-FRR-<story>` row THIS run closed on origin/main, else null (a
            # normal landing, a row already closed or absent, or a failed publish -- the WARN names which).
            "followup_review_closed_id": close.closed_id if close is not None else None,
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
    # Story 73.1 (CAP-281): a follow-up review run's landing names the row it closes and the merge subject.
    parser.add_argument("--followup-review-id", dest="followup_review_id", default=None)
    parser.add_argument("--landing-subject", dest="landing_subject", default=None)
    args = parser.parse_args(argv)
    worktree = Path(args.worktree) if args.worktree is not None else None
    if args.followup_review_id is None:
        return finalize_dispatch_land(args.project_slug, args.story_key, worktree)
    return finalize_dispatch_land(
        args.project_slug,
        args.story_key,
        worktree,
        followup_review_id=args.followup_review_id,
        landing=args.landing_subject,
    )


if __name__ == "__main__":
    raise SystemExit(main())
