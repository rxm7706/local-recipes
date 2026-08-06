"""``marshal deploy promote`` (Story 4.1, FR-30/FR-31, AD-4/AD-12/AD-13/
AD-24/AD-29/AD-33) -- automates the manual promotion workflow this
session's own PRs #266/#267/#269 performed by hand three times: find a
merged-but-unpromoted story, copy its Tier-3 spec into the tracked
``planning-artifacts/specs/`` archive, and commit it in one dedicated
commit containing only promotion paths.

**Candidate discovery is Tier-3-native; the promotion DECISION is
git-native (AD-33).** Every ``_bmad-output/projects/<slug>/
implementation-artifacts/spec-<key>*.md`` file is a candidate; whether a
candidate's story is DURABLE is answered ONLY from git
(``VcsPort.commit_subjects`` + ``core.promotion.merged_story_keys``) --
never from ``sprint-status.yaml``'s process-level ``development_status``.

**Two of AD-29's three reachability routes.** "Pushed to the remote" is
``commit_subjects(root, "origin/main")``, best-effort: a missing/unfetched
``origin`` is the ordinary case and falls back to the "merged to the
integration branch" route (``commit_subjects(root, "main")``) silently, no
finding -- AD-29's own "durability must not require the network" amendment
(F-14). The local-``main`` route is REQUIRED: its own failure is
``MRS-DEPLOY-003``, ``Verdict.UNEVALUABLE`` -- Marshal cannot honestly
promote anything without it. The third route, "reachable from the declared
durable local ref", is explicitly OUT of scope here (see
``deferred-work.md``) -- no code anywhere in this package names a real
mechanism for it yet.

**The pure/impure split (AD-4).** This module gathers every impure input --
the project's policy layer (for ``merge_subject_template``, AD-24's own
render/parse owner), the Tier-3 candidate files' bytes, the tracked
archive's own existing bytes (to decide "already promoted"), and
``VcsPort.commit_subjects`` -- then hands it to ``core.promotion``'s pure
``merged_story_keys``/``classify_promotion_candidates`` for classification.
The only further impure step is executing the plan: ``FsPort.copy_file``
per promoted spec, then one ``VcsPort.commit_paths`` call for the whole
batch (AD-29: "a single 'promote N specs' run is one paper-trail event",
never one commit per file).

**Validation before promotion (AD-13).** A candidate's content is judged by
``core.promotion.is_valid_spec_text`` -- both for the Tier-3 SOURCE (a
zero-byte/truncated source is reported via ``MRS-DEPLOY-002`` and never
promoted) and, symmetrically, for an EXISTING tracked copy (a candidate
counts as "already promoted" only when the tracked copy itself passes the
same check -- a broken tracked copy never blocks re-promoting a good
Tier-3 one, and no `Finding` is needed for that case: the current promotion
run simply proceeds and overwrites it).

**No promotion-state flag is cached anywhere.** "Promoted" is answered
fresh from git and the tracked archive's own bytes on every invocation --
mirrors AD-29's own sibling rule for teardown.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from pathlib import Path

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import identity, policy, promotion
from ..core.identity import MalformedStoryKeyError, render_filename_slug
from ..core.model import Finding, Severity, build_envelope
from ..core.promotion import SpecCandidate
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.fs import FsPort
from ..ports.vcs import VcsPort
from .config import (
    ENV_ACTIVE_PROJECT,
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
    repo_root,
)

# The base branch every story merges to in this repo's own landing
# convention -- the same `into="main"` hardcode `is_branch_merged`/
# teardown/`--scope-check` callers already use (see deferred-work.md for
# the pre-existing, story-2.3-logged "no --base override" limitation this
# inherits, not introduces).
_MERGE_BASE_BRANCH = "main"
_PUSH_REF = "origin/main"

_MRS_DEPLOY_003 = "MRS-DEPLOY-003"


def add_deploy_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``deploy`` subcommand on ``main.py``'s subparser tree,
    with a nested ``promote`` action -- mirrors ``cli/gate.py``'s own
    nested-subparser shape for ``gate evaluate``."""
    parser = subparsers.add_parser(
        "deploy",
        help="Promote merged story specs into the tracked archive (AD-13/AD-29).",
        description=(
            "Copies every durable, not-yet-promoted Tier-3 story spec into "
            "the tracked planning-artifacts/specs/ archive and commits the "
            "whole batch in one dedicated commit."
        ),
    )
    deploy_subparsers = parser.add_subparsers(dest="deploy_command", required=True)
    promote_parser = deploy_subparsers.add_parser(
        "promote",
        help="Promote every durable, not-yet-promoted Tier-3 story spec (AD-29).",
        description=(
            "Determines durability git-truthfully (pushed to origin/main, "
            "or merged to local main), copies each durable candidate's "
            "Tier-3 spec into the tracked archive, and commits the whole "
            "batch in one dedicated commit containing only promotion paths."
        ),
    )
    promote_parser.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help=f"The active project slug; falls back to ${ENV_ACTIVE_PROJECT} when omitted.",
    )
    promote_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    promote_parser.set_defaults(handler=run_promote)


def _discover_candidates(fs: FsPort, tier3_dir: Path) -> tuple[SpecCandidate, ...]:
    """Every ``spec-*.md`` file directly under ``tier3_dir`` (the Tier-3
    "run scratch" AD-12 names), parsed into a ``SpecCandidate`` per file.
    Directory ENUMERATION uses plain ``pathlib`` (``FsPort`` has no
    directory-listing primitive -- mirrors ``cli/gate.py::_find_spec_text``'s
    own established precedent of globbing directly at the CLI boundary);
    each file's CONTENT is read through ``FsPort`` for testability. A
    filename whose ``spec-`` prefix is not followed by a parseable story key
    (``MalformedStoryKeyError``) is silently skipped -- not every file
    matching the glob need be a story spec."""
    try:
        spec_paths = sorted(tier3_dir.glob("spec-*.md"))
    except OSError:
        spec_paths = []
    candidates: list[SpecCandidate] = []
    for spec_path in spec_paths:
        raw_key = spec_path.stem[len("spec-") :]
        try:
            story_key = identity.normalize(raw_key)
        except MalformedStoryKeyError:
            continue
        try:
            text = fs.read_text(spec_path)
        except FsError:
            text = None
        candidates.append(SpecCandidate(story_key=story_key, path=str(spec_path), text=text))
    return tuple(candidates)


def _already_promoted_keys(
    fs: FsPort,
    vcs: VcsPort,
    repo_root: Path,
    specs_dir: Path,
    candidates: tuple[SpecCandidate, ...],
) -> frozenset[identity.StoryKey]:
    """Which of ``candidates``' story keys already have a VALID, COMMITTED
    tracked copy at ``specs_dir`` (the bare ``spec-<key>.md`` form, or a
    titled ``spec-<key>-<title>.md`` -- mirrors
    ``cli/gate.py::_find_spec_text``'s own glob shape). A tracked copy that
    exists but fails ``core.promotion.is_valid_spec_text`` does NOT count as
    promoted -- see this module's own docstring for why a broken tracked
    copy never blocks re-promoting a good Tier-3 one.

    Nor does a tracked copy that exists and parses valid but was never
    actually committed (review finding, both reviewers independently: a
    partial-batch failure -- ``copy_file`` succeeding into ``specs_dir``
    immediately before the batched ``commit_paths`` call fails -- used to
    leave an orphaned, uncommitted file that this check, when it only asked
    the filesystem "does this path exist", permanently mistook for
    "promoted" on every future run, with no retry path ever committing it.
    ``vcs.path_has_uncommitted_changes`` is git's own answer to "is this
    SPECIFIC file's content safely captured in a commit" -- a candidate
    only counts as already-promoted when the tracked copy is BOTH valid
    content AND git-confirmed committed."""
    already: set[identity.StoryKey] = set()
    for candidate in candidates:
        stem = f"spec-{render_filename_slug(candidate.story_key)}"
        try:
            titled = sorted(specs_dir.glob(f"{stem}-*.md"))
        except OSError:
            titled = []
        for tracked_path in (specs_dir / f"{stem}.md", *titled):
            try:
                tracked_text = fs.read_text(tracked_path)
            except FsError:
                continue
            if not promotion.is_valid_spec_text(tracked_text):
                continue
            try:
                dirty = vcs.path_has_uncommitted_changes(repo_root, tracked_path)
            except VcsCommandError:
                # Cannot positively confirm this tracked copy is committed --
                # never trust an unconfirmed file as "already promoted"
                # (the same "fail safe, not silently trusting" shape as the
                # content-validity check just above).
                continue
            if not dirty:
                already.add(candidate.story_key)
                break
    return frozenset(already)


def run_promote(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
) -> int:
    vcs = vcs if vcs is not None else GitVcs()
    fs = fs if fs is not None else LocalFs()

    # Same is-not-None precedence as cli/gate.py::run_evaluate -- an
    # explicit `--project ""` must win over BMAD_ACTIVE_PROJECT.
    project_slug = (
        args.project if args.project is not None else os.environ.get(ENV_ACTIVE_PROJECT, "")
    )

    # Policy resolution mirrors cli/config.py::run_config's own simple
    # convention lookup (not cli/gate.py's elevated containment check --
    # this command never EXECUTES anything the policy declares, it only
    # reads one string field, merge_subject_template, so gate.py's
    # arbitrary-command-injection threat model does not apply here).
    project_data: Mapping[str, object] = {}
    io_findings: list[Finding] = []
    if project_slug and policy._is_valid_project_slug(project_slug):
        candidate = conventional_project_policy_path(project_slug)
        try:
            present = candidate.is_file()
        except OSError:
            present = True
        if present:
            try:
                project_data = _read_project_policy(candidate)
            except PolicyIOError as exc:
                io_findings.append(exc.finding)

    effective, policy_findings = policy.compose(
        project_slug=project_slug, project=project_data, flags={}
    )
    findings: list[Finding] = [*io_findings, *policy_findings]

    root = repo_root()
    data: dict[str, object] = {"slug": project_slug, "root": str(root)}
    promoted: list[str] = []
    already_promoted_list: list[str] = []
    gap_count = 0
    # Diagnostic-only (review finding): distinguishes a genuinely clean
    # "nothing has merged yet" from "the detection mechanism examined N
    # commit subjects and none conformed to either recognized merge-subject
    # pattern" -- both previously reported an identical promoted_count: 0
    # with no way to tell them apart.
    subjects_examined = 0
    subjects_matched = 0

    if project_slug and policy._is_valid_project_slug(project_slug):
        tier3_dir = root / "_bmad-output" / "projects" / project_slug / "implementation-artifacts"
        specs_dir = (
            root / "_bmad-output" / "projects" / project_slug / "planning-artifacts" / "specs"
        )

        candidates = _discover_candidates(fs, tier3_dir)
        already_promoted = _already_promoted_keys(fs, vcs, root, specs_dir, candidates)
        already_promoted_list = [str(key) for key in sorted(already_promoted)]

        # Push route: best-effort, never a hard failure (AD-29/F-14) -- a
        # missing/unfetched origin/main is the ordinary "no push route
        # available" case, per the story's own I/O matrix.
        try:
            origin_subjects = vcs.commit_subjects(root, _PUSH_REF)
        except VcsCommandError:
            origin_subjects = ()

        # Merge route: REQUIRED. Its failure means Marshal cannot honestly
        # determine ANY story's durability this run -- a hard, run-wide
        # finding, never a silently-empty merged_keys (which would read as
        # "nothing merged yet" and promote nothing without saying why).
        try:
            main_subjects = vcs.commit_subjects(root, _MERGE_BASE_BRANCH)
        except VcsCommandError as exc:
            findings.append(
                Finding(
                    code=_MRS_DEPLOY_003,
                    severity=Severity.ERROR,
                    message=(
                        "cannot read local main's commit history to determine "
                        f"promotion durability: {exc}"
                    ),
                )
            )
            main_subjects = None

        if main_subjects is not None:
            template = effective.merge_subject_template.value
            combined_subjects = tuple(origin_subjects) + tuple(main_subjects)
            merged_keys = promotion.merged_story_keys(combined_subjects, template)
            subjects_examined = len(combined_subjects)
            subjects_matched = promotion.count_conforming_subjects(combined_subjects, template)
            plan = promotion.classify_promotion_candidates(
                candidates=candidates,
                merged_keys=merged_keys,
                already_promoted=already_promoted,
            )
            findings.extend(plan.gaps)
            gap_count = len(plan.gaps)

            commit_targets: list[Path] = []
            for spec_candidate in plan.to_promote:
                # Preserve the Tier-3 file's own descriptive filename
                # (e.g. "spec-2-3-frozen-surface-scope-check-narrowing-
                # only.md") rather than deriving a bare "spec-<key>.md" --
                # every prior promotion in this archive (Epic 3's 8
                # specs, promoted by hand) used the source's own title
                # slug, and a bare rename here would be the one
                # promoted spec in the whole tracked archive without a
                # human-readable title (live finding, first real run of
                # this command against this repo, 2026-08-06).
                dest = specs_dir / Path(spec_candidate.path).name
                try:
                    fs.copy_file(Path(spec_candidate.path), dest)
                except FsError as exc:
                    findings.append(
                        Finding(
                            code=_MRS_DEPLOY_003,
                            severity=Severity.ERROR,
                            message=(
                                f"cannot copy {spec_candidate.path!r} into the "
                                f"tracked archive at {str(dest)!r}: {exc}"
                            ),
                        )
                    )
                    continue
                commit_targets.append(dest)
                promoted.append(str(spec_candidate.story_key))

            if commit_targets:
                message = (
                    f"marshal: promote {len(commit_targets)} story spec(s) to "
                    "tracked artifacts"
                )
                try:
                    vcs.commit_paths(root, tuple(commit_targets), message)
                except VcsCommandError as exc:
                    findings.append(
                        Finding(
                            code=_MRS_DEPLOY_003,
                            severity=Severity.ERROR,
                            message=f"cannot commit promoted specs: {exc}",
                        )
                    )

    data["promoted"] = sorted(promoted)
    data["promoted_count"] = len(promoted)
    data["already_promoted"] = already_promoted_list
    data["gap_count"] = gap_count
    data["subjects_examined"] = subjects_examined
    data["subjects_matched"] = subjects_matched

    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="deploy promote", verdict=verdict_value, data=data, findings=tuple(findings)
    )

    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = _render_text(envelope.data, envelope.findings)

    # flush=True + the broken-pipe guard mirror cli/gate.py::run_evaluate's
    # own convention exactly -- see that function's comment for the full
    # rationale.
    try:
        print(rendered, flush=True)
    except OSError:
        _suppress_downstream_pipe_close()

    return exit_code_for(envelope.verdict)


def _render_text(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching ``cli/gate.py``'s own
    ``_render_text`` convention."""
    slug = data["slug"] or "(no active project)"
    promoted = data["promoted"]
    # `!r` on slug/root and every path-shaped or attacker-controlled value
    # (mirrors cli/gate.py::_render_text's own rationale): a newline in a
    # project slug, a story key, or a Tier-3 path could otherwise forge a
    # `findings:` block or a fake "promoted" line.
    lines = [
        f"deploy promote: {slug!r}",
        f"root: {str(data['root'])!r}",
        f"promoted: {data['promoted_count']} "
        f"({', '.join(promoted) if promoted else 'none'})",
        f"already promoted: {len(data['already_promoted'])}",
        f"gaps: {data['gap_count']}",
        f"subjects examined: {data['subjects_examined']} "
        f"(matched: {data['subjects_matched']})",
    ]
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)
