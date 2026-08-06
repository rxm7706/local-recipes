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

Story 4.2 (teardown reachability and spec-recovery assistance, AD-29) adds
two more surfaces to this module:

``unreachable_promotions_for_slug(root, project_slug)`` -- the SAME
candidate-discovery + classification pipeline ``run_promote`` uses
(refactored into ``_scan_promotions``, the one shared implementation of
"is this slug's story durable" both callers delegate to, per the story's
own "not a reimplementation" requirement), reporting every key that is
``plan.to_promote`` (durable, not yet promoted, valid spec),
``plan.missing_spec_keys`` (durable, no Tier-3 spec at all), or
``plan.invalid_spec_keys`` (durable, Tier-3 spec present but
zero-byte/truncated -- code review, 2026-08-06, P3: a corrupt paper trail
is at least as concerning as a missing one, so it is folded into the
unreachable set too, deliberately widening the story's original Always
bullet). Computed fresh on every call -- no caching, mirroring
``run_promote``'s own "no promotion-state flag is cached anywhere" rule and
AD-29's teardown-side "reachability computed at teardown time, never a
journal flag".

Returns ``None`` -- rather than ``()`` -- when the pipeline's REQUIRED
local-``main`` read fails and reachability genuinely cannot be determined
(code review, 2026-08-06, P1, both reviewers' independent top finding): the
function used to fail OPEN in this case, silently degrading to "confirmed
nothing unreachable" with no findings channel to explain why -- a
destructive command's caller (``cli/init.py::run_teardown``) would then
proceed as if the AD-29 safety check had run clean. See this function's own
docstring below for the full contract.

``marshal deploy recover-spec <slug> <key>`` -- reports (never silently
picks) every surviving Tier-3 run-worktree snapshot for a story's spec
(``<tier3>/runs/*/spec-<key>*.md``, most-recent mtime first), and, only
when none exist, falls back to a contract-only regeneration parsed from
``epics.md``'s own Intent + Acceptance Criteria for that story (never
overwriting an existing file at either the snapshot paths -- read-only --
or its own ``spec-<key>-recovered.md`` target). A story with neither a
snapshot nor an ``epics.md`` section is reported as a genuinely orphaned key
(``MRS-DEPLOY-004``), never fabricated.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import identity, policy, promotion
from ..core.identity import MalformedStoryKeyError, StoryKey, render_filename_slug
from ..core.model import Finding, Severity, build_envelope
from ..core.promotion import PromotionPlan, SpecCandidate
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
_MRS_DEPLOY_004 = "MRS-DEPLOY-004"
_MRS_DEPLOY_005 = "MRS-DEPLOY-005"


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

    recover_parser = deploy_subparsers.add_parser(
        "recover-spec",
        help="Report snapshot candidates, or regenerate a contract-only spec (Story 4.2).",
        description=(
            "Searches this slug's own Tier-3 runs/*/ scratch tree for a "
            "surviving spec-<key>*.md snapshot, most-recent first, and "
            "reports every match without picking one. When none exist, "
            "falls back to a contract-only regeneration from epics.md's "
            "own Intent + Acceptance Criteria, written to a NEW "
            "spec-<key>-recovered.md (never overwriting an existing file, "
            "never touching planning-artifacts/specs/)."
        ),
    )
    recover_parser.add_argument("slug", help="The BMAD project slug.")
    recover_parser.add_argument("key", help="The story key whose spec to recover, e.g. 4.2.")
    recover_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    recover_parser.set_defaults(handler=run_recover_spec)


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


class _PromotionScan:
    """The result of ``_scan_promotions`` (Story 4.2): everything both
    ``run_promote`` and ``unreachable_promotions_for_slug`` need from the
    ONE shared candidate-discovery + classification pipeline (the story's
    own "not a reimplementation" requirement, AD-24/AD-33). ``plan`` is
    ``None`` only when the REQUIRED local-``main`` route could not be read
    (``findings`` then carries the ``MRS-DEPLOY-003`` explaining why) --
    every other field is still populated for reporting."""

    __slots__ = ("already_promoted", "combined_subjects", "findings", "plan", "template")

    def __init__(
        self,
        *,
        plan: PromotionPlan | None,
        findings: tuple[Finding, ...],
        combined_subjects: tuple[str, ...],
        template: str,
        already_promoted: frozenset[StoryKey] = frozenset(),
    ) -> None:
        self.plan = plan
        self.findings = findings
        self.combined_subjects = combined_subjects
        self.template = template
        self.already_promoted = already_promoted


def _scan_promotions(
    root: Path, project_slug: str, *, vcs: VcsPort, fs: FsPort
) -> _PromotionScan:
    """The ONE implementation of "which of this slug's stories are durable,
    and what should happen to each of their Tier-3 specs" (Story 4.2's own
    Always bullet: "a DELIBERATE reuse, not a reimplementation"). Resolves
    the project's policy (for ``merge_subject_template``), discovers Tier-3
    candidates and already-promoted keys, reads both AD-29 reachability
    routes, and delegates classification to ``core.promotion``'s pure
    functions -- exactly what ``run_promote`` did inline before this story;
    ``unreachable_promotions_for_slug`` is the second real caller."""
    project_data: Mapping[str, object] = {}
    findings: list[Finding] = []
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
                findings.append(exc.finding)

    effective, policy_findings = policy.compose(
        project_slug=project_slug, project=project_data, flags={}
    )
    findings.extend(policy_findings)

    # An empty/malformed slug already produced its own MRS-POLICY-005/006
    # finding via policy.compose above (this module's own established
    # behavior, predating this story) -- nothing further to discover
    # without a real project directory to look in.
    if not project_slug or not policy._is_valid_project_slug(project_slug):
        return _PromotionScan(
            plan=None, findings=tuple(findings), combined_subjects=(), template=""
        )

    tier3_dir = root / "_bmad-output" / "projects" / project_slug / "implementation-artifacts"
    specs_dir = root / "_bmad-output" / "projects" / project_slug / "planning-artifacts" / "specs"

    candidates = _discover_candidates(fs, tier3_dir)
    already_promoted = _already_promoted_keys(fs, vcs, root, specs_dir, candidates)

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
        return _PromotionScan(
            plan=None, findings=tuple(findings), combined_subjects=(), template=""
        )

    template = effective.merge_subject_template.value
    combined_subjects = tuple(origin_subjects) + tuple(main_subjects)
    merged_keys = promotion.merged_story_keys(combined_subjects, template, project_slug)
    plan = promotion.classify_promotion_candidates(
        candidates=candidates,
        merged_keys=merged_keys,
        already_promoted=already_promoted,
    )
    return _PromotionScan(
        plan=plan,
        findings=tuple(findings),
        combined_subjects=combined_subjects,
        template=template,
        already_promoted=already_promoted,
    )


def unreachable_promotions_for_slug(
    root: Path,
    project_slug: str,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
) -> tuple[StoryKey, ...] | None:
    """Story 4.2's own AD-29 reachability answer for ``cli/init.py``'s
    ``_unreachable_promotions``: every ``StoryKey`` for ``project_slug``
    that is durable-but-unpromoted (``plan.to_promote``),
    durable-with-no-spec-at-all (``plan.missing_spec_keys``), or
    durable-with-a-corrupt-spec (``plan.invalid_spec_keys``, folded in by a
    2026-08-06 review fix, P3 -- a truncated paper trail is at least as
    concerning as a missing one) -- via the SAME ``_scan_promotions``
    pipeline ``run_promote`` uses, computed fresh on every call (no caching,
    AD-29: "reachability computed at teardown time, never a journal flag").

    Returns THREE distinct shapes, never raises:

    - ``()`` -- CONFIRMED empty: nothing unreachable, or a malformed/empty
      ``project_slug`` (checked, and refused with its own
      ``MRS-TEARDOWN-001``, long before ``run_teardown`` ever calls this
      far -- this branch is a defensive fallback for other/direct callers,
      not a real teardown path);
    - a non-empty tuple -- CONFIRMED unreachable keys;
    - ``None`` -- UNDETERMINED: ``_scan_promotions`` could not read local
      ``main``'s commit history at all (its own ``plan is None`` case,
      ``MRS-DEPLOY-003``). Code review, 2026-08-06, P1 (both reviewers'
      independent top finding): this function used to degrade to ``()``
      here too, which a caller with no findings channel of its own could
      only read as "confirmed nothing unreachable" -- silently treating an
      UNDETERMINED safety-check result the same as a CONFIRMED-clean one,
      for a command that destroys a git worktree and branch. ``None`` gives
      ``cli/init.py::_unreachable_promotions``/``run_teardown`` a way to
      tell the two apart and refuse at least as strictly as a real
      unreachable set (see that function's own comment for the override
      discipline it now requires).

    Teardown's OTHER refusal channels (dirty worktree, unmerged branch) are
    unaffected by either degrade -- only the AD-29 check itself is being
    reported on here."""
    vcs = vcs if vcs is not None else GitVcs()
    fs = fs if fs is not None else LocalFs()
    if not project_slug or not policy._is_valid_project_slug(project_slug):
        return ()
    scan = _scan_promotions(root, project_slug, vcs=vcs, fs=fs)
    if scan.plan is None:
        return None
    keys = {candidate.story_key for candidate in scan.plan.to_promote}
    keys.update(scan.plan.missing_spec_keys)
    keys.update(scan.plan.invalid_spec_keys)
    return tuple(sorted(keys))


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

    root = repo_root()
    data: dict[str, object] = {"slug": project_slug, "root": str(root)}
    findings: list[Finding] = []
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

    specs_dir = root / "_bmad-output" / "projects" / project_slug / "planning-artifacts" / "specs"
    scan = _scan_promotions(root, project_slug, vcs=vcs, fs=fs)
    findings.extend(scan.findings)

    already_promoted_list = [str(key) for key in sorted(scan.already_promoted)]

    if scan.plan is not None:
        plan = scan.plan
        subjects_examined = len(scan.combined_subjects)
        subjects_matched = promotion.count_conforming_subjects(
            scan.combined_subjects, scan.template, project_slug
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

    return _emit(args, "deploy promote", data, findings, _render_text)


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


def _emit(
    args: argparse.Namespace,
    command: str,
    data: dict[str, object],
    findings: list[Finding],
    render_text: Callable[[Mapping[str, object], tuple[Finding, ...]], str],
) -> int:
    """The one envelope-build-then-print tail both ``run_promote`` and
    ``run_recover_spec`` (Story 4.2) share -- factored out rather than
    duplicated a second time, matching AD-14's "one envelope for every
    command" rule at the module's own call-site level too."""
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command=command, verdict=verdict_value, data=data, findings=tuple(findings)
    )

    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = render_text(envelope.data, envelope.findings)

    # flush=True + the broken-pipe guard mirror cli/gate.py::run_evaluate's
    # own convention exactly -- see that function's comment for the full
    # rationale.
    try:
        print(rendered, flush=True)
    except OSError:
        _suppress_downstream_pipe_close()

    return exit_code_for(envelope.verdict)


# =====================================================================
# ``marshal deploy recover-spec`` (Story 4.2, FR-31/AD-29).
# =====================================================================

_STORY_HEADING_RE = re.compile(r"^### Story (?P<key>[0-9]+\.[0-9]+):", re.MULTILINE)
_AC_MARKER = "**Acceptance Criteria:**"
_TYPE_MARKER = "**Type:**"


def _epics_story_section(epics_text: str, story_key: identity.StoryKey) -> str | None:
    """The smallest ``epics.md`` story-section reader that answers exactly
    this story's question -- no existing epics.md story-section parser was
    found anywhere in this codebase to reuse (grepped: ``core/gate.py``'s
    own ``_find_spec_text`` reads a TRACKED SPEC's text, never epics.md
    itself). Returns the raw markdown from ``story_key``'s own
    ``### Story <key>: ...`` heading up to (not including) the next
    ``### Story`` heading, or ``None`` if no heading matches ``story_key``
    exactly (``### Story 4.2`` must never match a lookup for ``4.20``)."""
    target = str(story_key)
    headings = list(_STORY_HEADING_RE.finditer(epics_text))
    for index, match in enumerate(headings):
        if match.group("key") != target:
            continue
        start = match.start()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(epics_text)
        return epics_text[start:end].strip()
    return None


def _split_intent_and_acceptance_criteria(section_text: str) -> tuple[str, str]:
    """Splits one story's epics.md section into its Intent ("As the
    operator, ... So that ...") and Acceptance Criteria blocks, VERBATIM --
    the story's own Always bullet ("extract ... verbatim"). The heading
    line and the ``**Type:** ... **Surface:** ...`` metadata line are
    dropped from Intent (neither is part of the As/I want/So that
    contract); everything from ``**Acceptance Criteria:**`` onward is the
    AC block, unmodified."""
    ac_index = section_text.find(_AC_MARKER)
    intent_part = section_text if ac_index == -1 else section_text[:ac_index]
    acceptance_criteria = "" if ac_index == -1 else section_text[ac_index + len(_AC_MARKER) :].strip()

    lines = intent_part.splitlines()[1:]  # drop the "### Story ..." heading
    intent_lines: list[str] = []
    for line in lines:
        if line.strip().startswith(_TYPE_MARKER):
            break
        intent_lines.append(line)
    intent = "\n".join(intent_lines).strip()
    return intent, acceptance_criteria


def _render_recovered_spec(story_key: identity.StoryKey, intent: str, acceptance_criteria: str) -> str:
    """The reduced, contract-only spec ``recover-spec``'s fallback writes
    (Story 4.2's own Always bullet): frontmatter carries ``status: 'draft'``
    and ``recovery_source: 'epics-derived-contract-only'`` so it is
    structurally distinguishable from a hand-authored spec at a glance; the
    body carries ONLY Intent + Acceptance Criteria -- deliberately no Code
    Map, no Design Notes, no Boundaries & Constraints. Must never claim to
    be more than what it is."""
    return (
        "---\n"
        f"title: 'Recovered contract for story {story_key}'\n"
        "type: 'feature'\n"
        "status: 'draft'\n"
        "recovery_source: 'epics-derived-contract-only'\n"
        "---\n\n"
        "<intent-contract>\n\n"
        "## Intent\n\n"
        f"{intent}\n\n"
        "## Acceptance Criteria\n\n"
        f"{acceptance_criteria}\n\n"
        "</intent-contract>\n"
    )


def _run_snapshot_candidates(root: Path, project_slug: str, story_key: identity.StoryKey) -> list[dict[str, object]]:
    """Every ``<tier3>/runs/*/spec-<key>*.md`` snapshot for ``story_key``,
    most-recent ``mtime`` first (the story's own Always bullet: "surviving
    run-worktree snapshots first"). Directory enumeration uses plain
    ``pathlib`` (mirrors ``_discover_candidates``'s own established
    precedent, and ``cli/spin.py::_spec_size_bytes``'s own titled-spec glob
    shape) -- read-only, this function never writes."""
    runs_dir = root / "_bmad-output" / "projects" / project_slug / "implementation-artifacts" / "runs"
    stem = f"spec-{render_filename_slug(story_key)}"
    # Boundary anchor (code review, 2026-08-06, P4, both reviewers): a bare
    # `*/{stem}*.md` glob has no boundary after the key's own digits, so a
    # lookup for key 1.2 (stem "spec-1-2") also matched "spec-1-20-*.md" /
    # "spec-1-23-*.md" -- any key sharing "1-2" as a numeric PREFIX. The
    # segment immediately after `stem` must be either end-of-name (the bare
    # "spec-1-2.md" form) or a "-" (a title separator), never another digit
    # -- filtered here rather than trusting the glob alone.
    _boundary_re = re.compile(re.escape(stem) + r"(?:-.*)?\.md")
    try:
        matches = sorted(
            path for path in runs_dir.glob(f"*/{stem}*.md") if _boundary_re.fullmatch(path.name)
        )
    except OSError:
        matches = []
    dated: list[tuple[float, Path]] = []
    for match in matches:
        try:
            mtime = match.stat().st_mtime
        except OSError:
            continue
        dated.append((mtime, match))
    dated.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {
            "path": str(path),
            "mtime": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
        }
        for mtime, path in dated
    ]


def run_recover_spec(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
) -> int:
    fs = fs if fs is not None else LocalFs()

    slug = args.slug
    raw_key = args.key
    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug, "key": raw_key}

    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-POLICY-006",
                severity=Severity.ERROR,
                message=(
                    f"malformed project slug {slug!r} -- must be one safe "
                    "path segment (letters, digits, '.', '_', '-'; not '.' "
                    "or '..'; at most 255 characters)"
                ),
            )
        )
        return _emit(args, "deploy recover-spec", data, findings, _render_text_recover_spec)

    try:
        story_key = identity.normalize(raw_key)
    except MalformedStoryKeyError as exc:
        findings.append(Finding(code="MRS-IDENT-001", severity=Severity.ERROR, message=str(exc)))
        return _emit(args, "deploy recover-spec", data, findings, _render_text_recover_spec)
    data["key"] = str(story_key)

    root = repo_root()
    snapshots = _run_snapshot_candidates(root, slug, story_key)
    data["snapshots"] = snapshots
    if snapshots:
        return _emit(args, "deploy recover-spec", data, findings, _render_text_recover_spec)

    # --- fallback: epics-derived contract-only regeneration -----------------
    tier3_dir = root / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    dest = tier3_dir / f"spec-{render_filename_slug(story_key)}-recovered.md"
    data["recovered_path"] = str(dest)

    try:
        already_present = fs.exists(dest)
    except FsError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_003,
                severity=Severity.ERROR,
                message=f"cannot check whether {dest} already exists: {exc}",
            )
        )
        return _emit(args, "deploy recover-spec", data, findings, _render_text_recover_spec)
    if already_present:
        data["already_present"] = True
        return _emit(args, "deploy recover-spec", data, findings, _render_text_recover_spec)

    epics_path = (
        root / "_bmad-output" / "projects" / slug / "planning-artifacts" / "epics.md"
    )
    try:
        epics_text = fs.read_text(epics_path)
    except FsError:
        epics_text = None

    section = _epics_story_section(epics_text, story_key) if epics_text else None
    if section is None:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_004,
                severity=Severity.WARN,
                message=(
                    f"story {story_key} has no Tier-3 run-worktree snapshot "
                    "and no epics.md section -- genuinely orphaned; nothing "
                    "written"
                ),
            )
        )
        return _emit(args, "deploy recover-spec", data, findings, _render_text_recover_spec)

    intent, acceptance_criteria = _split_intent_and_acceptance_criteria(section)
    content = _render_recovered_spec(story_key, intent, acceptance_criteria)
    try:
        fs.write_text_atomic(dest, content)
    except FsError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_003,
                severity=Severity.ERROR,
                message=f"cannot write recovered spec {dest}: {exc}",
            )
        )
        return _emit(args, "deploy recover-spec", data, findings, _render_text_recover_spec)

    # Code review, 2026-08-06, P5 (Edge Case Hunter): a parsing miss, or a
    # genuinely sparse epics.md section, can leave Intent and/or Acceptance
    # Criteria empty after the split above -- the file above is still
    # written (this command "reports, never fabricates": an empty section
    # is itself reported, not silently hidden -- see the module's own
    # docstring), but `recovered: true` alone would let an operator trust a
    # hollow recovery silently. Warn, naming what came back empty, rather
    # than reporting success with no caveat.
    empty_parts = [
        name
        for name, text in (("Intent", intent), ("Acceptance Criteria", acceptance_criteria))
        if not text.strip()
    ]
    if empty_parts:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_005,
                severity=Severity.WARN,
                message=(
                    f"recovered spec {dest} was written, but its "
                    f"{' and '.join(empty_parts)} section(s) came back empty "
                    f"from epics.md -- likely a hollow, low-confidence "
                    "recovery; review before trusting it"
                ),
                path=str(dest),
            )
        )

    data["recovered"] = True
    return _emit(args, "deploy recover-spec", data, findings, _render_text_recover_spec)


def _render_text_recover_spec(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching ``_render_text``'s own
    convention for ``deploy promote``."""
    slug = data.get("slug") or "(no active project)"
    key = data.get("key", "")
    lines = [f"deploy recover-spec: {slug!r} {key!r}"]
    snapshots = data.get("snapshots") or []
    if snapshots:
        lines.append("snapshot candidates (most recent first):")
        for entry in snapshots:
            lines.append(f"  {entry['path']!r} (mtime: {entry['mtime']})")
    else:
        lines.append("snapshot candidates: none")
        if "recovered_path" in data:
            lines.append(f"recovered_path: {data['recovered_path']!r}")
        if data.get("already_present"):
            lines.append("already present -- not overwritten")
        elif data.get("recovered"):
            lines.append("recovered: epics-derived contract-only spec written")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)
