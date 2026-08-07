"""``marshal retire`` (Story 4.10, FR-63/AD-47) -- a NEW top-level command
that sweeps EVERY project's loop home for bmad-loop-minted, worktree-
isolated per-story branches provably safe to delete, and proposes
(dry-run by default) or deletes (``--execute``) exactly those.

**The gap this closes.** ``marshal land``/``land-story`` (Stories 4.8/4.3)
already retire the ONE station branch (``loop/<slug>``) their own wave
landed through (``ForgePort.merge_pr(..., delete_branch=True)``). A project
running bmad-loop's worktree-isolated mode mints a SEPARATE branch per story
task (``ports/harness.py::TaskPhaseSnapshot.branch``, Story 3.8) -- none of
Marshal's own shipped commands ever proposed deleting THOSE. This command
never re-proposes a station branch: the structural ``loop/*`` exclusion
(``core.retire.is_structurally_excluded``) makes the two mechanisms'
candidate sets disjoint by construction, so they can never disagree.

**Fleet enumeration mirrors ``marshal homes`` exactly** (``VcsPort.
list_worktrees`` against the repo root resolved from ``Path.cwd()``, every
entry whose ``.branch`` starts with ``"loop/"`` names one project's slug) --
each such entry's own ``.path`` IS that project's loop home; no second,
convention-derived path (``cli/init.py::_home_path``) is consulted, since
the worktree git itself already reports is the one git-truthful answer to
"where is this project's loop home" (the identical trust ``run_homes``
already places in ``entry.path`` for its own home-state reads).

**Per-project evidence gathering reads ``TaskPhaseSnapshot`` directly, not
through ``ClaimedCommit``.** ``cli/deploy.py``'s ``_gather_claimed_commits``
(Story 4.5) already established the exact read sequence this command
needs (``_latest_run_dir``/``_resolve_harness_run_id_for_resume``, imported
from ``cli/spin.py`` the same local-import way ``_gather_claimed_commits``
itself does, to avoid the documented ``cli.deploy``/``cli.init`` load-order
cycle) -- reused here, not reimplemented. But ``ClaimedCommit`` deliberately
drops ``TaskPhaseSnapshot.branch`` (Story 4.5's own scope never needed it),
so this command reads ``snapshot.tasks`` directly instead of going through
that narrower projection.

**Why "run concluded" is a worktree check, not a harness run-status
field.** ``RunStatusSnapshot`` has run-level pause/deferred state (Story
3.7), but nothing that says "this SPECIFIC task's own branch's worktree has
been torn down" more directly than asking git itself --
``VcsPort.worktree_path_for_branch(...) is None`` is the same git-truthful
signal ``marshal homes``'s own isolation checks already trust.

**No ``--force`` flag exists on this command at all** (mirrors ``marshal
land``'s own precedent): every proposal this command makes is, by
construction, already three-ways provably safe -- there is no "I know
better than the evidence" case to support. An operator's only recourse for
a branch this sweep refuses to propose is a direct ``git branch -D`` outside
Marshal entirely.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import identity, policy
from ..core.identity import MalformedStoryKeyError
from ..core.journal import JournalEntryId, Phase, build_entry, mint_run_id, prepare_for_write
from ..core.model import Finding, Severity, build_envelope
from ..core.retire import (
    InsufficientEvidence,
    RetirementCandidate,
    RetirementProposal,
    classify_retirement,
    is_structurally_excluded,
)
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.vcs import VcsPort
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
    repo_root,
)

_MRS_RETIRE_001 = "MRS-RETIRE-001"
_MRS_RETIRE_002 = "MRS-RETIRE-002"
_MRS_RETIRE_003 = "MRS-RETIRE-003"

# The exact literal `supervisor/durability.py::_DONE_PHASE` already uses --
# reused, not re-spelled, for the "the harness's own recorded terminus"
# check (the spec's own Always bullet: "the exact literal ... already uses").
_DONE_PHASE = "done"

# One journal `observation` entry per project per `--execute` run that
# actually deleted at least one branch -- mirrors `cli/deploy.py`'s
# `_journal_manual_landing`'s own "mint a fresh Tier-3 run directory, then
# append one entry" shape (there is no pre-existing run a retirement sweep
# belongs to, exactly like a manual landing).
_RETIRE_JOURNAL_FILENAME = "journal.jsonl"
_RETIRE_KIND = "branch-retirement"


def add_retire_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``retire`` subcommand on ``main.py``'s subparser tree --
    a NEW top-level command, sibling to ``deploy``/``land``/``gate`` (the
    story's own Code Map). No required positional argument -- it sweeps the
    WHOLE fleet by default."""
    parser = subparsers.add_parser(
        "retire",
        help="Sweep every project's loop home for provably-safe-to-delete per-story branches (FR-63/AD-47).",
        description=(
            "For every project with a currently-attached loop-home worktree "
            "(or just --project SLUG), reads the most recent bmad-loop run's "
            "per-task branch/phase/commit_sha and proposes exactly the "
            "branches provably safe to delete: merged by patch-id into the "
            "policy-declared landing_base_branch, no live worktree "
            "currently checked out on it, and the harness's own phase == "
            "done with a recorded commit sha. Dry-run by default (report "
            "only); --execute deletes every proposed branch."
        ),
    )
    parser.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help="Scope the sweep to one project slug (default: the whole fleet).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Actually delete every proposed branch (default: dry-run/report-only).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_retire)


def _retire_random_token() -> str:
    return secrets.token_hex(4)


def _retire_format_utc_compact(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%S") + f"{moment.microsecond // 1000:03d}Z"


def _retire_format_entry_ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _retire_writer_id() -> str:
    """A fresh, process-scoped, filesystem-safe writer id -- mirrors
    ``cli/deploy.py::_deploy_writer_id``'s identical rationale (a random
    token alongside the pid, so a pid-reused-across-invocations collision
    can never mint the identical composite journal-entry id)."""
    return "-".join(("retire", str(os.getpid()), _retire_random_token()))


def _journal_retirement(
    fs: FsPort, root: Path, slug: str, deleted: list[dict[str, object]]
) -> Finding | None:
    """One journal ``observation`` entry recording every branch actually
    deleted for ``slug`` this run (the story's own Always bullet: "every
    deletion is journaled") -- mirrors ``cli/deploy.py::
    _journal_manual_landing``'s mint-a-fresh-run-then-append shape exactly:
    a dedicated Tier-3 run directory is minted for this ONE event (there is
    no pre-existing run a retirement sweep belongs to), written
    ``fsync=True`` (this entry records real, durable git deletes -- the
    same class ``_journal_manual_landing``'s own entry already earns
    ``fsync=True`` for). Returns a ``Finding`` (never raises) on any I/O
    failure -- by the time this is called every branch in ``deleted`` has
    ALREADY been removed, so a journal-write failure is reported, never
    grounds to undo anything."""
    moment = datetime.now(timezone.utc)
    run_id = mint_run_id(slug, _retire_format_utc_compact(moment), _retire_random_token())
    run_dir = (
        root
        / "_bmad-output"
        / "projects"
        / slug
        / "implementation-artifacts"
        / "runs"
        / run_id
    )
    try:
        fs.ensure_dir(run_dir.parent)
        fs.create_dir_exclusive(run_dir)
    except FsError as exc:
        return Finding(
            code=_MRS_RETIRE_003,
            severity=Severity.WARN,
            message=(
                f"{len(deleted)} branch(es) for {slug!r} were deleted but "
                f"the retirement could not be journaled: {exc}"
            ),
        )

    entry = build_entry(
        id=JournalEntryId(_retire_writer_id(), 0),
        ts=_retire_format_entry_ts(datetime.now(timezone.utc)),
        run_id=run_id,
        kind=_RETIRE_KIND,
        phase=Phase.OBSERVATION,
        payload={"deleted": deleted},
    )
    try:
        prepared = prepare_for_write(entry)
        if prepared.sidecar_relative_path is not None:
            fs.write_text_atomic(
                run_dir / prepared.sidecar_relative_path, prepared.sidecar_content
            )
        fs.append_line(run_dir / _RETIRE_JOURNAL_FILENAME, prepared.line, fsync=True)
    except FsError as exc:
        return Finding(
            code=_MRS_RETIRE_003,
            severity=Severity.WARN,
            message=(
                f"{len(deleted)} branch(es) for {slug!r} were deleted but "
                f"could not be journaled: {exc}"
            ),
        )
    return None


def run_retire(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
    harness: HarnessPort | None = None,
) -> int:
    # Local imports -- `cli/init.py` imports `from . import deploy`, and
    # `cli/deploy.py`'s own `_gather_claimed_commits` documents the identical
    # `cli.deploy` <-> `cli.init` load-order-cycle rationale for why
    # `cli/spin.py` is never imported at module level from a sibling module
    # (see that function's own comment); mirrored here for the same reason.
    from .spin import _latest_run_dir, _resolve_harness_run_id_for_resume

    vcs = vcs if vcs is not None else GitVcs()
    fs = fs if fs is not None else LocalFs()
    harness = harness if harness is not None else BmadLoopHarness()

    findings: list[Finding] = []
    data: dict[str, object] = {
        "project": args.project,
        "executed": bool(args.execute),
        "proposals": [],
        "insufficient_evidence": [],
        "deleted": [],
    }

    if args.project is not None and not policy._is_valid_project_slug(args.project):
        findings.append(
            Finding(
                code=_MRS_RETIRE_001,
                severity=Severity.ERROR,
                message=(
                    f"malformed --project slug {args.project!r} -- must be "
                    "one safe path segment (letters, digits, '.', '_', '-'; "
                    "not '.' or '..'; at most 255 characters)"
                ),
            )
        )
        return _emit(args, data, findings)

    root = repo_root()

    try:
        git_repo_root = vcs.repo_common_root(Path.cwd())
        worktrees = vcs.list_worktrees(git_repo_root)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_RETIRE_002,
                severity=Severity.WARN,
                message=f"cannot enumerate the fleet's loop-home worktrees: {exc}",
            )
        )
        return _emit(args, data, findings)

    fleet: list[tuple[str, Path]] = []
    for entry in worktrees:
        if entry.branch is None or not entry.branch.startswith("loop/"):
            continue
        slug = entry.branch.removeprefix("loop/")
        if args.project is not None and slug != args.project:
            continue
        fleet.append((slug, entry.path))

    proposals: list[RetirementProposal] = []
    insufficient: list[InsufficientEvidence] = []
    deleted: list[dict[str, object]] = []

    for slug, home in fleet:
        project_data: Mapping[str, object] = {}
        if policy._is_valid_project_slug(slug):
            policy_path = conventional_project_policy_path(slug)
            try:
                present = policy_path.is_file()
            except OSError:
                present = True
            if present:
                try:
                    project_data = _read_project_policy(policy_path)
                except PolicyIOError as exc:
                    findings.append(exc.finding)
        effective, policy_findings = policy.compose(
            project_slug=slug, project=project_data, flags={}
        )
        findings.extend(policy_findings)
        base = effective.landing_base_branch.value

        run_dir = _latest_run_dir(home, slug)
        if run_dir is None:
            continue
        run_id = run_dir.name
        harness_run_id = _resolve_harness_run_id_for_resume(fs, run_dir, run_id)
        if harness_run_id is None:
            continue
        try:
            snapshot = harness.run_status_snapshot(home, harness_run_id)
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            ArithmeticError,
            RecursionError,
        ):
            continue
        if snapshot is None:
            continue

        slug_proposals: list[RetirementProposal] = []
        # Code review (2026-08-06, Edge Case Hunter): two `TaskPhaseSnapshot`
        # entries in the same run (or, more plausibly, a harness anomaly)
        # naming the SAME branch would otherwise gather evidence twice,
        # double-report the branch in `proposals`, and -- under `--execute`
        # -- attempt `delete_branch` twice, the second call necessarily
        # failing (the branch is already gone) and producing a spurious
        # MRS-RETIRE-003 WARN even though nothing actually went wrong. A
        # branch already classified this run (proposed OR refused) is never
        # re-evaluated.
        seen_branches: set[str] = set()
        for task in snapshot.tasks:
            branch = task.branch
            if not branch or is_structurally_excluded(branch):
                continue
            if branch in seen_branches:
                continue
            seen_branches.add(branch)
            try:
                story_key = identity.normalize(task.story_key)
            except MalformedStoryKeyError:
                continue

            candidate = RetirementCandidate(
                slug=slug, branch=branch, story_key=str(story_key)
            )

            try:
                merged_by_patch_id = vcs.is_branch_merged(git_repo_root, branch, into=base)
            except VcsCommandError as exc:
                findings.append(
                    Finding(
                        code=_MRS_RETIRE_002,
                        severity=Severity.WARN,
                        message=(
                            f"cannot confirm {branch!r} ({slug!r}) is merged "
                            f"by patch-id into {base!r}: {exc}"
                        ),
                        path=branch,
                    )
                )
                merged_by_patch_id = False

            try:
                worktree_path = vcs.worktree_path_for_branch(git_repo_root, branch)
                run_concluded = worktree_path is None
            except VcsCommandError as exc:
                findings.append(
                    Finding(
                        code=_MRS_RETIRE_002,
                        severity=Severity.WARN,
                        message=(
                            f"cannot confirm {branch!r} ({slug!r}) has no "
                            f"live worktree checked out: {exc}"
                        ),
                        path=branch,
                    )
                )
                run_concluded = False

            recorded_merge_sha = task.commit_sha if task.phase == _DONE_PHASE else None

            outcome = classify_retirement(
                candidate,
                merged_by_patch_id=merged_by_patch_id,
                run_concluded=run_concluded,
                recorded_merge_sha=recorded_merge_sha,
            )
            if isinstance(outcome, RetirementProposal):
                proposals.append(outcome)
                slug_proposals.append(outcome)
            else:
                insufficient.append(outcome)

        if args.execute and slug_proposals:
            slug_deleted: list[dict[str, object]] = []
            for proposal in slug_proposals:
                branch = proposal.candidate.branch
                try:
                    # Code review (2026-08-06, both reviewers independently,
                    # the single most severe finding against this story):
                    # `force=True`, not `False`. `VcsPort.delete_branch`'s
                    # own docstring is explicit that `-d`'s ancestry-based
                    # check "would spuriously refuse a branch this port's
                    # own `is_branch_merged` already proved safe by CONTENT
                    # (the squash-merge case)" and that "a caller that
                    # trusts its own merged-check passes `force=True`" --
                    # this proposal's own `merged_by_patch_id` fact IS that
                    # trusted check. `cli/init.py::run_teardown` (this
                    # module's own precedent) already does exactly this.
                    # `force=False` here would make `--execute` a near-total
                    # no-op against this repo's own squash-merge landing
                    # convention -- every proposal correctly PROVEN safe,
                    # but the actual `git branch -d` refusing every one of
                    # them with a spurious "not fully merged".
                    vcs.delete_branch(git_repo_root, branch, force=True)
                except VcsCommandError as exc:
                    findings.append(
                        Finding(
                            code=_MRS_RETIRE_003,
                            severity=Severity.WARN,
                            message=f"cannot delete {branch!r} ({slug!r}): {exc}",
                            path=branch,
                        )
                    )
                    continue
                entry_dict: dict[str, object] = {
                    "slug": slug,
                    "branch": branch,
                    "story_key": proposal.candidate.story_key,
                    "recorded_merge_sha": proposal.recorded_merge_sha,
                }
                slug_deleted.append(entry_dict)
                deleted.append(entry_dict)
            if slug_deleted:
                journal_finding = _journal_retirement(fs, root, slug, slug_deleted)
                if journal_finding is not None:
                    findings.append(journal_finding)

    data["proposals"] = [
        {
            "slug": proposal.candidate.slug,
            "branch": proposal.candidate.branch,
            "story_key": proposal.candidate.story_key,
            "merged_by_patch_id": True,
            "worktree": None,
            "recorded_merge_sha": proposal.recorded_merge_sha,
        }
        for proposal in proposals
    ]
    data["insufficient_evidence"] = [
        {
            "slug": entry.candidate.slug,
            "branch": entry.candidate.branch,
            "story_key": entry.candidate.story_key,
            "missing": list(entry.missing),
        }
        for entry in insufficient
    ]
    data["deleted"] = deleted

    return _emit(args, data, findings)


def _render_text_retire(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching every other command's
    own ``_render_text*`` convention."""
    project = data.get("project") or "(whole fleet)"
    lines = [f"retire: {project!r}", f"executed: {data.get('executed')}"]

    proposals = data.get("proposals") or []
    lines.append(f"proposals: {len(proposals)}")
    for proposal in proposals:
        lines.append(
            f"  {proposal['slug']}/{proposal['branch']!r} "
            f"(story {proposal['story_key']}, "
            f"merge_sha {proposal['recorded_merge_sha']!r})"
        )

    insufficient = data.get("insufficient_evidence") or []
    lines.append(f"insufficient evidence: {len(insufficient)}")
    for entry in insufficient:
        lines.append(
            f"  {entry['slug']}/{entry['branch']!r}: "
            f"missing {', '.join(entry['missing'])}"
        )

    deleted = data.get("deleted") or []
    lines.append(f"deleted: {len(deleted)}")
    for entry in deleted:
        lines.append(f"  {entry['slug']}/{entry['branch']!r}")

    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


def _emit(args: argparse.Namespace, data: dict[str, object], findings: list[Finding]) -> int:
    """The envelope-build-then-print tail every ``cli/*.py`` command shares
    (AD-14: one envelope shape per command)."""
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="retire", verdict=verdict_value, data=data, findings=tuple(findings)
    )

    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = _render_text_retire(envelope.data, envelope.findings)

    try:
        print(rendered, flush=True)
    except OSError:
        _suppress_downstream_pipe_close()

    return exit_code_for(envelope.verdict)
