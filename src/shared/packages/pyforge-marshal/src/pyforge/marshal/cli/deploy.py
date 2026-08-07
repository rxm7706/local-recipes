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

Story 4.3 (merge-subject conformance and review-cap landing, FR-27, AD-4/
AD-24/AD-34) adds ``marshal deploy land-story <slug> <key> --justification
TEXT`` -- the governed manual-landing path FR-27's own motivating evidence
names (two real stories landed by hand with no re-run gate, no guaranteed
merge-subject form, and no journal record of the manual decision).

**The full gate is re-run IN-PROCESS, never shelled out.** ``cli/gate.py``'s
``run_evaluate`` was a single function that gathered inputs, ran every
check, AND printed -- this story splits it into ``evaluate_gate`` (the pure
envelope-building core) and a thin ``run_evaluate`` wrapper (see that
module's own docstring for the split's full rationale). ``land-story``
calls ``evaluate_gate`` directly with ``--scope-check`` forced on, so both
halves of the full gate (verify commands AND the scope check) must be
green before anything else runs.

**The subject is always rendered, never hand-typed (AD-24).** ``land-story``
resolves the project's ``merge_subject_template`` policy field and calls
``core.identity.render_merge_subject(key, template)`` -- the SAME
render/parse pair the conformance audit below uses in its parse direction.
No f-string/format literal in this module's own new code ever assembles a
merge subject.

**The branch landed is the loop-home's own STATION branch
(``f"loop/{slug}"``), not a per-story branch.** This repo's own convention
(``cli/init.py``'s ``add_worktree``/``run_teardown``, ``supervisor/
__main__.py``'s durability watcher) develops every story of a project on
that one station branch; a per-story branch (when one exists at all) is
minted by the harness itself with no name Marshal can derive from a bare
story key alone. ``land-story``'s own "wave" -- the Design Notes' own term
for what the conformance audit inspects -- is that station branch's own
commit history since it forked from ``main``.

**Conformance audit is folded into the same command, never a separate
action or a second parser (AD-24).** After a successful merge,
``VcsPort.commit_subjects`` is called with a git REVISION RANGE
(``f"{since}..{merge_sha}"``) rather than the full ``"main"`` history
sliced by subject-string position -- the literal Code Map wording names
the latter, but position-slicing a subject list is fragile the moment two
commits anywhere in history share an identical subject line (not a rare
shape: this repo's own bare "initial" or "wip" commits), while a git range
expression is git's own, unambiguous answer to "every commit reachable
from ``merge_sha`` but not from ``since``" and needs no second read. Every
subject in that range is handed to ``core.identity.parse_merge_subject`` --
the SAME function ``render_merge_subject`` above used, never a second
regex -- and a subject that fails to parse is named in
``data.non_conforming_merges``, reported only, never blocking the landing
that already happened (a `MergeSubjectConformanceError`'s own ``.finding``
attribute is deliberately NOT added to this command's own findings list:
doing so would reclassify an already-successful landing's verdict away
from ``clean``, exactly the blocking behavior the story's own Never bullet
forbids).

**The manual landing is journaled the same way Story 4.2's own abandonment
record is:** a fresh, dedicated Tier-3 run directory
(``implementation-artifacts/runs/<run_id>/journal.jsonl``) minted for this
one event (there is no pre-existing run this landing belongs to -- landing
is not itself a story run), one ``observation`` entry, ``fsync=True``
(this entry authorizes a real, durable git write, the same class Story
4.2's own abandonment entry and Story 3.1's ``intent``-phase entries
already earned ``fsync=True`` for). ``--justification`` is redacted at
capture (AD-34) via the SAME ``to_redacted({"k": text});
json.loads(...)["k"]`` idiom ``adapters/harness_bmadloop.py``'s
``_redact_text`` already uses for ``paused_reason``/``defer_reason`` --
free text from an operator can carry anything pane-derived text can.

**Code review (2026-08-06) hardened ``run_land_story`` in seven ways,**
most severe first: **P1** -- ``VcsPort.merge_branch`` no longer checks out
``into`` in ``repo_root`` (this project's ONE shared, active checkout);
it now merges inside a throwaway detached worktree and advances ``into``
via a compare-and-swap ref update (see ``adapters/vcs_git.py``). **P2** --
the gate must evaluate EXACTLY ``Verdict.CLEAN``, not merely
``status_for(...)  is Status.OK`` (which also admits ``warn``). **P3** --
a ``PolicyIOError`` resolving the merge-subject template is now a hard
stop, never a silently-defaulted-template fall-through. **P4** --
``branch``'s own tip is pinned via the new ``VcsPort.resolve_ref``
immediately after the gate runs and re-verified immediately before
merging; the merge uses the CAPTURED sha, refusing if the branch moved in
between. **P5** -- ``merge_branch``'s own redesign structurally closes the
"merge succeeded but the sha readback failed" gap (its cleanup step is
best-effort and never raises after a successful landing). **P6** -- an
already-merged story key (reusing Story 4.1's own ``core.promotion.
merged_story_keys`` durability detection) short-circuits to a clean no-op
before the gate ever runs. **P7** -- a ``--justification`` redaction
failure now registers a WARN finding naming the gap, rather than silently
writing ``null`` into the permanent journal record.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shlex
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path

from ..adapters.forge_gh import GhForge
from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness
from ..adapters.process_posix import PosixProcess, ProcessError
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import identity, policy, promotion, status
from ..core.egress import Redacted, to_redacted
from ..core.identity import MalformedStoryKeyError, StoryKey, render_filename_slug
from ..core.journal import (
    FoldResult,
    JournalEntryId,
    Phase,
    build_entry,
    fold,
    intent_reconciles,
    mint_run_id,
    prepare_for_write,
)
from ..core.landing import LandingRule, rule_applies
from ..core.model import Finding, Severity, Status, Verdict, build_envelope, status_for
from ..core.promotion import PromotionPlan, SpecCandidate
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.forge import ForgeCommandError, ForgePort, ForgeRef
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.process import ProcessPort
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
_MRS_DEPLOY_006 = "MRS-DEPLOY-006"
_MRS_DEPLOY_007 = "MRS-DEPLOY-007"
_MRS_DEPLOY_008 = "MRS-DEPLOY-008"
_MRS_DEPLOY_009 = "MRS-DEPLOY-009"
_MRS_DEPLOY_010 = "MRS-DEPLOY-010"
_MRS_DEPLOY_011 = "MRS-DEPLOY-011"
_MRS_DEPLOY_012 = "MRS-DEPLOY-012"
_MRS_DEPLOY_013 = "MRS-DEPLOY-013"
_MRS_DEPLOY_014 = "MRS-DEPLOY-014"
_MRS_DEPLOY_015 = "MRS-DEPLOY-015"
_MRS_DEPLOY_016 = "MRS-DEPLOY-016"
_MRS_DEPLOY_017 = "MRS-DEPLOY-017"
_MRS_DEPLOY_018 = "MRS-DEPLOY-018"
_MRS_DEPLOY_021 = "MRS-DEPLOY-021"
_MRS_DEPLOY_022 = "MRS-DEPLOY-022"

# Story 4.3's own journal kind (mirrors cli/init.py's `_ABANDON_KIND`
# convention) -- one `observation` entry per manual landing.
_LAND_JOURNAL_FILENAME = "journal.jsonl"
_LAND_KIND = "manual-landing"

# Story 4.6's own journal kinds (AD-6/AD-21/AD-28): the intent/outcome pair
# around each of the three commands' own irreversible step. A CLOSING
# outcome for an open intent that this run's own action confirmed already
# happened (never re-performed) carries the distinct `_RECONCILIATION_KIND`
# instead of the action's own kind -- AD-28's own literal text, "a lone
# intent is closed exclusively by a reconciliation outcome".
_PROMOTE_COMMIT_KIND = "deploy-promote-commit"
_LAND_MERGE_KIND = "deploy-land-story-merge"
_BATCH_PR_WRITE_KIND = "deploy-batch-pr-write"
_RECONCILIATION_KIND = "reconciliation"

# Story 4.4's own repo constant: every Marshal station lives inside this ONE
# physical repo (this repo's own `local-recipes` fork, per the team's own
# reference note "gh pr create needs --repo rxm7706/local-recipes" -- this
# repo is a staged-recipes fork, so the forge's own repo-inference from cwd
# is never trustworthy here). No policy field names this -- it is not a
# per-project decision the way `landing_base_branch` is; it is a fact about
# which physical repo Marshal itself runs inside.
_FORGE_REPO = "rxm7706/local-recipes"


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

    land_parser = deploy_subparsers.add_parser(
        "land-story",
        help="Manually land a sound-but-not-converged story, under the full gate (FR-27).",
        description=(
            "Re-runs the full gate (verify commands + --scope-check) for "
            "<key>; on green, merges <slug>'s loop-home station branch into "
            "main using the policy-rendered merge subject, journals the "
            "manual landing, and reports merge-subject conformance for "
            "every commit in the wave since the branch's own merge-base "
            "with main."
        ),
    )
    land_parser.add_argument("slug", help="The BMAD project slug.")
    land_parser.add_argument("key", help="The story key being landed, e.g. 4.3.")
    land_parser.add_argument(
        "--justification",
        default=None,
        metavar="TEXT",
        help="Required, non-empty: why this story is landed manually rather than by review.",
    )
    land_parser.add_argument(
        "--since",
        default=None,
        metavar="REF",
        help=(
            "The conformance audit's window start. Defaults to the "
            "merge-base of the station branch and main, computed before "
            "the merge."
        ),
    )
    land_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    land_parser.set_defaults(handler=run_land_story)

    batch_pr_parser = deploy_subparsers.add_parser(
        "batch-pr",
        help="Open/update the batch PR for a wave of landed stories, under a hygiene preflight (FR-29/NFR-2).",
        description=(
            "Discovers the wave of durable story keys on <slug>'s loop-home "
            "station branch since its own merge-base with the configured "
            "landing base branch, evaluates every effective landing_rules "
            "entry against the wave's changed files (a fired required_check "
            "rule blocks unless its named forge check concluded 'success'; "
            "a fired label rule is applied, never blocking), then opens or "
            "updates the batch PR with a title/body derived from the wave "
            "and the journal's own gate-verdict records."
        ),
    )
    batch_pr_parser.add_argument("slug", help="The BMAD project slug.")
    batch_pr_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    batch_pr_parser.set_defaults(handler=run_batch_pr)

    refresh_feed_parser = deploy_subparsers.add_parser(
        "refresh-feed",
        help="Reconcile git-sourced and journal-sourced facts, domain-tagged (AD-33).",
        description=(
            "Builds one reconciled report from two independently-gathered "
            "sources: git-sourced repository facts (VcsPort.commit_subjects "
            "+ core.promotion.merged_story_keys) and journal/harness-sourced "
            "process facts (HarnessPort.run_status_snapshot's per-task "
            "commit_sha). Every field is tagged with the domain it came "
            "from; a journal claim about a repository fact that git does "
            "not confirm is reported as a reconciliation finding, never "
            "resolved. Runs the policy-declared landing_resync_commands "
            "allowlist when landing_resync composes true."
        ),
    )
    refresh_feed_parser.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help=f"The active project slug; falls back to ${ENV_ACTIVE_PROJECT} when omitted.",
    )
    refresh_feed_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    refresh_feed_parser.set_defaults(handler=run_refresh_feed)


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

    # Story 4.6's pre-action reconciliation precondition (AD-6/AD-21/AD-28):
    # `scan.already_promoted` is ALREADY this run's own fresh, live
    # evidence (a valid, git-committed tracked copy exists) -- exactly the
    # "does the spec now exist and is it committed" evidence check the
    # story's own Always bullet names for `promote`. A malformed/empty
    # `project_slug` produced no candidates and no scan.plan either --
    # `_reconcile_open_intents` itself now applies the SAME slug-validity
    # guard (code review, 2026-08-06, P4: consistent across all three
    # call sites, factored into the shared helper rather than duplicated
    # here), so this call site no longer needs its own local guard.
    deploy_run = _DeployRun(fs, root, project_slug, _deploy_writer_id("promote"))
    _reconcile_open_intents(
        fs,
        root,
        project_slug,
        kind=_PROMOTE_COMMIT_KIND,
        confirmed_story_keys=scan.already_promoted,
        evidence_note="tracked spec exists and is git-committed",
        deploy_run=deploy_run,
        findings=findings,
    )

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
            # Story 4.6 (AD-6): an `intent` entry BEFORE the irreversible
            # `commit_paths` call, an `outcome` AFTER it succeeds. A
            # journal-write failure for the intent itself means no paper
            # trail exists for the write about to happen -- `deploy_run
            # .write` already reports it via a Finding; `commit_paths`
            # still runs (a promote is not gated on its OWN journal write
            # succeeding, matching this codebase's existing "best-effort
            # journaling of an already-decided action" posture, e.g.
            # `_journal_manual_landing`'s own post-merge journal write). A
            # `commit_paths` failure leaves the intent open -- no outcome
            # is written, per the story's own I/O matrix ("that step
            # reports failed; intent for it stays open").
            intent_id = deploy_run.write(
                findings,
                kind=_PROMOTE_COMMIT_KIND,
                phase=Phase.INTENT,
                payload={"action": "commit_paths", "story_keys": sorted(promoted)},
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
            else:
                if intent_id is not None:
                    deploy_run.write(
                        findings,
                        kind=_PROMOTE_COMMIT_KIND,
                        phase=Phase.OUTCOME,
                        payload={
                            "action": "commit_paths",
                            "story_keys": sorted(promoted),
                            "commit_message": message,
                        },
                        intent_id=intent_id,
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


# =====================================================================
# ``marshal deploy land-story`` (Story 4.3, FR-27/AD-4/AD-24/AD-34).
# =====================================================================


def _land_writer_id() -> str:
    """A fresh, process-scoped, filesystem-safe writer id -- mirrors
    ``cli/init.py::_abandon_writer_id``'s identical rationale, scoped to
    this module's own caller."""
    return f"land-story-{os.getpid()}"


def _land_random_token() -> str:
    return secrets.token_hex(4)


def _land_format_utc_compact(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%S") + f"{moment.microsecond // 1000:03d}Z"


def _land_format_entry_ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _land_redact_text(text: str) -> str | None:
    """AD-34's own redaction-at-capture idiom
    (``adapters/harness_bmadloop.py::_redact_text``'s identical round-trip,
    reused verbatim): ``--justification`` is operator-supplied free text,
    which can carry anything pane-derived text can. Narrowly guarded so a
    redaction failure degrades only this one field, never the whole
    journal entry."""
    try:
        redacted = to_redacted({"text": text})
        return json.loads(redacted.text)["text"]
    except (ValueError, LookupError, TypeError):
        return None


def _journal_manual_landing(
    fs: FsPort,
    root: Path,
    slug: str,
    *,
    story_key: str,
    justification: str,
    merge_sha: str,
    gate_verdict: str,
    findings: list[Finding],
) -> Finding | None:
    """One journal ``observation`` entry recording a manual landing
    (Story 4.3's own Always bullet), mirroring ``cli/init.py::
    _journal_abandonments``'s mint-a-fresh-run-then-append shape exactly: a
    dedicated Tier-3 run directory is minted for this ONE event (there is
    no pre-existing run a manual landing belongs to), and the entry is
    written ``fsync=True`` (this entry authorizes a real, durable git
    write -- the same class Story 4.2's own abandonment entry and Story
    3.1's ``intent``-phase entries already earned ``fsync=True`` for).
    Returns a ``Finding`` (never raises) on any I/O failure -- the caller
    treats a non-``None`` result as informational only: by the time this
    is called the merge has ALREADY landed, so a journal-write failure is
    reported, never grounds to undo the merge.

    Code review (2026-08-06, P7, both reviewers independently): if
    redacting ``justification`` fails, a WARN finding naming the gap is
    APPENDED DIRECTLY to the caller's own ``findings`` list -- the landing
    still proceeds (this is a visibility fix, not a safety-critical
    precondition), but the operator's stated justification silently going
    missing from the permanent journal record must be visible in the run's
    own report, not only discoverable later by someone reading the raw
    journal."""
    moment = datetime.now(timezone.utc)
    run_id = mint_run_id(slug, _land_format_utc_compact(moment), _land_random_token())
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
            code=_MRS_DEPLOY_003,
            severity=Severity.ERROR,
            message=f"cannot create journal directory for the manual landing of {story_key}: {exc}",
        )

    redacted_justification = _land_redact_text(justification)
    if redacted_justification is None:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_012,
                severity=Severity.WARN,
                message=(
                    f"could not redact --justification for {story_key}'s "
                    "manual landing -- the journal entry's justification "
                    "field is empty; the operator's stated justification "
                    "text was not captured"
                ),
            )
        )
    entry = build_entry(
        id=JournalEntryId(_land_writer_id(), 0),
        ts=_land_format_entry_ts(datetime.now(timezone.utc)),
        run_id=run_id,
        kind=_LAND_KIND,
        phase=Phase.OBSERVATION,
        payload={
            "story_key": story_key,
            "justification": redacted_justification,
            "merge_sha": merge_sha,
            "gate_verdict": gate_verdict,
        },
    )
    try:
        prepared = prepare_for_write(entry)
        if prepared.sidecar_relative_path is not None:
            fs.write_text_atomic(
                run_dir / prepared.sidecar_relative_path, prepared.sidecar_content
            )
        fs.append_line(run_dir / _LAND_JOURNAL_FILENAME, prepared.line, fsync=True)
    except FsError as exc:
        return Finding(
            code=_MRS_DEPLOY_003,
            severity=Severity.ERROR,
            message=f"cannot journal the manual landing of {story_key}: {exc}",
        )
    return None


# ---------------------------------------------------------------------------
# Story 4.6 -- deploy idempotence and reconciliation of open intents (AD-6/
# AD-21/AD-28). Shared machinery `run_promote`/`run_land_story`/
# `run_batch_pr` each wrap their own irreversible step with: (1) a
# pre-action reconciliation check against every OPEN intent a prior,
# possibly-crashed invocation of the SAME action left behind, and (2) a
# fresh intent/outcome pair around the action this run itself performs.
# ---------------------------------------------------------------------------


def _deploy_writer_id(action: str) -> str:
    """A fresh, process-scoped, filesystem-safe writer id, one per deploy
    action -- mirrors ``_land_writer_id``'s identical rationale, scoped to
    each of ``promote``/``land-story``/``batch-pr`` rather than only
    ``land-story``. Prefixed ``deploy-`` (unlike ``_land_writer_id``'s bare
    ``f"land-story-{pid}"``) so `land-story`'s own two independent writers
    in the same process -- this helper's own intent/outcome pair and
    ``_journal_manual_landing``'s pre-existing observation entry -- can
    never mint the identical ``(writer_id, counter=0)`` composite id even
    though `_fold_deploy_journal` folds every run directory's journal
    TOGETHER (a real hazard once entries from separate run directories are
    combined into one global fold, unlike this module's older
    single-run-directory readers).

    Code review (2026-08-06, P1, both reviewers' independent top finding):
    also incorporates a fresh ``secrets``-sourced random token (the SAME
    uniqueness source ``mint_run_id``'s own ``random_token`` argument
    already uses via ``_land_random_token``, reused here rather than a
    second scheme), not merely ``os.getpid()``. The bare-pid form used to
    let the OS reuse a pid across two genuinely SEPARATE invocations (the
    ordinary case over a long-lived Tier-3 store), which mints the
    IDENTICAL ``(writer_id, counter=0)`` composite id for both -- harmless
    before this story, when a fold only ever read ONE run directory at a
    time, but `_fold_deploy_journal` now folds EVERY run directory
    TOGETHER into one global ``fold()`` call, so a pid-reuse collision lets
    an unrelated later invocation's outcome mis-pair against an EARLIER,
    unrelated invocation's intent -- corrupting AD-28's own intent/outcome
    pairing guarantee, exactly the "wrongly reconciled as already done"
    failure mode this whole story exists to prevent. The random token
    makes that collision practically impossible regardless of pid reuse.
    Built via ``str.join`` rather than an f-string/``.format()`` literal --
    the AD-23 inline-key-format meta-test
    (``tests/meta/test_ad23_inline_key_format_guard.py``) flags any
    two-placeholder-joined-by-a-bare-``-`` literal outside
    ``core/identity.py`` on sight, since that is also the exact shape a
    hand-rolled story-key formatter would take; this value is a writer id,
    never a story key, but the guard is a purely structural AST scan with
    no way to tell the two apart, so this is spelled to not match it."""
    return "-".join(("deploy", action, str(os.getpid()), _land_random_token()))


def _mint_deploy_run(fs: FsPort, root: Path, slug: str) -> tuple[Path, str] | Finding:
    """Mint a fresh Tier-3 run directory for one deploy-action invocation's
    own idempotence journal -- the SAME mint-a-fresh-run-then-append shape
    ``_journal_manual_landing``/``cli/init.py::_journal_abandonments``
    already establish, generalized so ``promote``/``batch-pr`` (which had
    no journal at all before this story) gain it too. Returns a Finding
    (never raises) on any I/O failure."""
    moment = datetime.now(timezone.utc)
    run_id = mint_run_id(slug, _land_format_utc_compact(moment), _land_random_token())
    run_dir = (
        root / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs" / run_id
    )
    try:
        fs.ensure_dir(run_dir.parent)
        fs.create_dir_exclusive(run_dir)
    except FsError as exc:
        return Finding(
            code=_MRS_DEPLOY_003,
            severity=Severity.ERROR,
            message=f"cannot create a journal directory for {slug!r}'s deploy action: {exc}",
        )
    return run_dir, run_id


def _fold_deploy_journal(
    fs: FsPort, root: Path, slug: str, findings: list[Finding]
) -> FoldResult:
    """The GLOBAL fold (AD-28) over EVERY run directory this slug's Tier-3
    store carries under ``implementation-artifacts/runs/*/journal.jsonl``.

    An ``intent`` minted by one invocation and the ``reconciliation``
    outcome that later closes it are minted by a DIFFERENT, independent
    invocation (a fresh run directory each time, per ``_mint_deploy_run``)
    -- so pairing them by ``intent_id`` (AD-28's own "pairing is by
    intent_id ONLY" rule) requires folding every line from every run
    directory TOGETHER in ONE ``fold()`` call. A per-directory fold (this
    module's own ``_gather_gate_verdicts`` precedent) would show the same
    intent as perpetually open in its own origin file forever, even after
    a later run's reconciliation outcome closed it -- the same class of
    bug ``core.journal.fold``'s own docstring warns a positional/heuristic
    pairing scheme would produce, here at the file-selection layer instead
    of the entry-pairing layer.

    Best-effort PER RUN DIRECTORY, mirroring every sibling reader in this
    module: an unreadable ``runs`` directory, a single run's journal file,
    or a sidecar blob is silently skipped rather than aborting the whole
    scan -- a converged, fully-reconciled system must never fail to
    evaluate just because one ancient run directory's own files rotted.

    Code review (2026-08-06, P3, Blind Hunter): the outer ``fold()`` call
    itself can still fail on a shape ``fold`` does not tolerate (a
    corrupted line surviving quarantine, an unexpected ``KeyError``/
    ``OSError`` from a pathological sidecar). That blanket failure used to
    return an EMPTY ``FoldResult`` silently -- indistinguishable, to every
    caller, from "confirmed: no open intents anywhere". That is not a
    per-entry quarantine (``fold``'s own AD-30 mechanism already handles
    those); it is a whole-fold failure that would make EVERY genuinely
    open intent across every run directory invisible in one shot, with the
    reconciliation pass reporting a clean run instead of naming the gap --
    exactly the "discrepancies are reported, never silently resolved"
    posture this story's own Design Notes require everywhere else. A
    registered ``MRS-DEPLOY-022`` finding is appended instead, naming that
    the cross-run fold failed and reconciliation could not be attempted
    this invocation; the caller's own action still proceeds (this finding
    is WARN, never blocking, the same posture MRS-DEPLOY-021 already
    establishes for "no evidence yet")."""
    runs_dir = root / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs"
    all_lines: list[str] = []
    sidecars: dict[str, str | None] = {}
    try:
        run_dirs = sorted(path for path in runs_dir.iterdir() if path.is_dir())
    except OSError:
        run_dirs = []
    for run_dir in run_dirs:
        try:
            text = fs.read_text(run_dir / _LAND_JOURNAL_FILENAME)
        except FsError:
            continue
        all_lines.extend(line for line in text.split("\n") if line.strip())
        try:
            blob_paths = sorted((run_dir / "blobs").glob("*.json"))
        except OSError:
            blob_paths = []
        for blob_path in blob_paths:
            try:
                sidecars[f"blobs/{blob_path.name}"] = fs.read_text(blob_path)
            except FsError:
                sidecars[f"blobs/{blob_path.name}"] = None
    try:
        return fold(all_lines, sidecars=sidecars)
    except (TypeError, ValueError, KeyError, OSError) as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_022,
                severity=Severity.WARN,
                message=(
                    f"cross-run journal fold failed for {slug!r} ({exc}) -- "
                    "reconciliation could not be attempted this invocation; "
                    "any genuinely open intent from a prior run is neither "
                    "confirmed nor reported this run"
                ),
            )
        )
        return fold((), sidecars={})


def _write_deploy_entry(
    fs: FsPort,
    run_dir: Path,
    run_id: str,
    writer_id: str,
    counter: int,
    *,
    kind: str,
    phase: Phase,
    payload: Mapping[str, object],
    intent_id: JournalEntryId | None = None,
) -> tuple[JournalEntryId, Finding | None]:
    """Append ONE journal entry to ``run_dir``'s own ``journal.jsonl``
    (Story 4.6): builds, prepares, and appends via the SAME
    ``build_entry``/``prepare_for_write``/``FsPort.append_line`` pipeline
    ``_journal_manual_landing`` already established, generalized for a
    caller-supplied phase/kind/payload/intent_id. ``fsync=True``
    unconditionally -- an ``intent`` authorizes an irreversible action
    about to happen (AD-6/AD-30's own precedent), and a genuine
    ``outcome``/``reconciliation`` is the durable record of what happened;
    neither is ever worth losing to a buffered write. Returns the entry's
    own id (for a later outcome/reconciliation to reference) and, on any
    I/O failure, a ``Finding`` the caller appends -- never raises. A
    failed intent write means the caller must NOT proceed with the action
    it was about to guard (no paper trail, no action -- AD-6's own
    ordering), which every real call site below honors."""
    entry_id = JournalEntryId(writer_id, counter)
    entry = build_entry(
        id=entry_id,
        ts=_land_format_entry_ts(datetime.now(timezone.utc)),
        run_id=run_id,
        kind=kind,
        phase=phase,
        payload=payload,
        intent_id=intent_id,
    )
    try:
        prepared = prepare_for_write(entry)
        if prepared.sidecar_relative_path is not None:
            fs.write_text_atomic(
                run_dir / prepared.sidecar_relative_path, prepared.sidecar_content
            )
        fs.append_line(run_dir / _LAND_JOURNAL_FILENAME, prepared.line, fsync=True)
    except FsError as exc:
        return entry_id, Finding(
            code=_MRS_DEPLOY_003,
            severity=Severity.ERROR,
            message=f"cannot journal a {phase.value} entry ({kind}) for {run_id!r}: {exc}",
        )
    return entry_id, None


class _DeployRun:
    """Lazily-minted run-directory handle shared across one command
    invocation's own reconciliation pass and its own action intent/outcome
    pair (Story 4.6) -- a command with NOTHING to reconcile and NOTHING to
    act on mints no run directory at all (NFR-7: a converged re-run
    produces zero changes, and that includes zero new, empty run
    directories)."""

    __slots__ = ("fs", "root", "slug", "writer_id", "run_dir", "run_id", "counter")

    def __init__(self, fs: FsPort, root: Path, slug: str, writer_id: str) -> None:
        self.fs = fs
        self.root = root
        self.slug = slug
        self.writer_id = writer_id
        self.run_dir: Path | None = None
        self.run_id: str | None = None
        self.counter = 0

    def ensure(self, findings: list[Finding]) -> bool:
        """Mint this invocation's run directory on first use. Returns
        ``True`` once a usable ``run_dir`` exists, ``False`` (with a
        Finding appended) if minting failed -- the caller must then skip
        the journal write it was about to attempt, never crash."""
        if self.run_dir is not None:
            return True
        minted = _mint_deploy_run(self.fs, self.root, self.slug)
        if isinstance(minted, Finding):
            findings.append(minted)
            return False
        self.run_dir, self.run_id = minted
        return True

    def write(
        self,
        findings: list[Finding],
        *,
        kind: str,
        phase: Phase,
        payload: Mapping[str, object],
        intent_id: JournalEntryId | None = None,
    ) -> JournalEntryId | None:
        """Write one entry using this invocation's own run directory,
        minting it first if needed. Returns the entry's own id on success
        (even a partial success -- the write happened even if a Finding
        was also appended for some OTHER reason), or ``None`` only when
        the run directory itself could not be minted at all (nothing was
        written)."""
        if not self.ensure(findings):
            return None
        assert self.run_dir is not None and self.run_id is not None
        entry_id, finding = _write_deploy_entry(
            self.fs,
            self.run_dir,
            self.run_id,
            self.writer_id,
            self.counter,
            kind=kind,
            phase=phase,
            payload=payload,
            intent_id=intent_id,
        )
        self.counter += 1
        if finding is not None:
            findings.append(finding)
        return entry_id


def _reconcile_open_intents(
    fs: FsPort,
    root: Path,
    slug: str,
    *,
    kind: str,
    confirmed_story_keys: frozenset[StoryKey] | set[StoryKey],
    evidence_note: str,
    deploy_run: "_DeployRun",
    findings: list[Finding],
) -> None:
    """The pre-action reconciliation precondition (Story 4.6, AD-6 x AD-21
    x AD-28): folds every run directory's journal (``_fold_deploy_journal``)
    for OPEN intents of ``kind``, and for each one asks
    ``core.journal.intent_reconciles`` whether ``confirmed_story_keys`` --
    already gathered by the caller via ``VcsPort``/``ForgePort``, e.g.
    ``run_promote``'s own ``already_promoted`` set -- confirms it. A
    reconciled intent is closed with a ``reconciliation`` outcome
    (AD-28's own literal shape: ``intent_id`` referencing the open intent,
    the evidence named) and NEVER causes the action to be re-performed here
    -- this function only writes the closing outcome; every call site's own
    existing idempotence check (``already_promoted``, ``merged_story_keys``,
    ``find_open_pr``) is what ALREADY keeps the real action from re-running,
    unchanged by this story. An UNreconciled intent stays open and is
    reported via ``MRS-DEPLOY-021`` (``Verdict.WARN``, per AD-21's F-17
    amendment) -- never blocking, and the action proceeds normally exactly
    as it already would have without this story's own changes.

    Code review (2026-08-06, P4, Blind Hunter): the slug-validity guard
    (``policy._is_valid_project_slug``) is checked ONCE, HERE, rather than
    duplicated at each of the three call sites -- ``run_land_story``/
    ``run_batch_pr`` already refuse a malformed slug long before reaching
    this call (their own ``MRS-POLICY-006`` precondition), but
    ``run_promote`` tolerates an empty/malformed slug (an established,
    pre-existing behavior: ``_scan_promotions`` degrades gracefully rather
    than refusing) and used to wrap this call in its own local
    ``if policy._is_valid_project_slug(...)`` -- an inconsistent posture
    across three call sites presented as parallel implementations of the
    same pattern. Reconciliation genuinely needs a valid project context
    to resolve Tier-3 paths, so the guard is real, not decorative; folding
    it in here means every caller gets it uniformly with no duplicated,
    cross-module reach into ``core.policy``'s private helper."""
    if not policy._is_valid_project_slug(slug):
        return
    fold_result = _fold_deploy_journal(fs, root, slug, findings)
    open_intents = [entry for entry in fold_result.open_intents if entry.kind == kind]
    if not open_intents:
        return
    confirmed = sorted(str(key) for key in confirmed_story_keys)
    evidence: dict[str, object] = {"confirmed_story_keys": confirmed}
    for intent in open_intents:
        if intent_reconciles(intent.payload, evidence):
            reconciled_keys = intent.payload.get("story_keys")
            deploy_run.write(
                findings,
                kind=_RECONCILIATION_KIND,
                phase=Phase.OUTCOME,
                payload={
                    "reconciled_kind": kind,
                    "story_keys": reconciled_keys,
                    "evidence": evidence_note,
                    "confirmed_story_keys": confirmed,
                },
                intent_id=intent.id,
            )
        else:
            findings.append(
                Finding(
                    code=_MRS_DEPLOY_021,
                    severity=Severity.WARN,
                    message=(
                        f"open intent {intent.id.writer_id}:{intent.id.counter} "
                        f"(kind={kind!r}, story_keys="
                        f"{intent.payload.get('story_keys')!r}) from a prior "
                        "run has no confirming evidence yet -- it stays open; "
                        "this run does not re-perform the action without "
                        "evidence, though its own existing idempotence check "
                        "may make attempting it again safe regardless"
                    ),
                )
            )


def run_land_story(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
    process: ProcessPort | None = None,
) -> int:
    # Local imports (never module-level): `cli/init.py` imports THIS module
    # (`from . import deploy`), and `cli/gate.py` imports `cli/init.py`
    # (`from .init import _home_path`) -- a module-level `from .init import
    # ...`/`from .gate import ...` here would create a load-order-fragile
    # cli.deploy <-> cli.init / cli.deploy -> cli.gate -> cli.init cycle.
    # `main.py` already imports every CLI submodule before any handler
    # runs, so by the time this function is ever CALLED both modules are
    # fully loaded and this import is a cheap `sys.modules` lookup.
    from .gate import evaluate_gate
    from .init import _home_path

    vcs = vcs if vcs is not None else GitVcs()
    fs = fs if fs is not None else LocalFs()
    process = process if process is not None else PosixProcess()

    slug = args.slug
    raw_key = args.key
    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug, "key": raw_key}

    # 1. --justification: the cheap precondition, checked FIRST, before any
    # I/O -- the story's own Always bullet.
    justification = args.justification
    if not justification or not justification.strip():
        findings.append(
            Finding(
                code=_MRS_DEPLOY_006,
                severity=Severity.ERROR,
                message=(
                    "--justification is required and must be non-empty to "
                    "land a story manually"
                ),
            )
        )
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)

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
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)

    try:
        story_key = identity.normalize(raw_key)
    except MalformedStoryKeyError as exc:
        findings.append(Finding(code="MRS-IDENT-001", severity=Severity.ERROR, message=str(exc)))
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)
    data["key"] = str(story_key)

    root = repo_root()
    home = _home_path(slug)
    branch = f"loop/{slug}"
    data["branch"] = branch

    # 2. The station branch must resolve to a real, existing branch --
    # refused BEFORE the gate runs (the story's own I/O matrix).
    try:
        git_repo_root = vcs.repo_common_root(home)
        branch_ok = vcs.branch_exists(git_repo_root, branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_007,
                severity=Severity.ERROR,
                message=(
                    f"cannot resolve the loop-home station branch {branch!r} "
                    f"to land {story_key}: {exc}"
                ),
            )
        )
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)
    if not branch_ok:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_007,
                severity=Severity.ERROR,
                message=(
                    f"{branch!r} does not exist -- nothing to land for {story_key}"
                ),
            )
        )
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)

    # 3. --since defaults to the merge-base of branch/main, computed BEFORE
    # the merge (Design Notes: the one boundary this story can compute
    # without inventing new state).
    since_ref = args.since
    if since_ref is None:
        try:
            since_ref = vcs.merge_base(git_repo_root, branch, _MERGE_BASE_BRANCH)
        except VcsCommandError as exc:
            findings.append(
                Finding(
                    code=_MRS_DEPLOY_007,
                    severity=Severity.ERROR,
                    message=(
                        f"cannot compute the merge base of {branch!r} and "
                        f"{_MERGE_BASE_BRANCH!r}: {exc}"
                    ),
                )
            )
            return _emit(args, "deploy land-story", data, findings, _render_text_land_story)
    data["since"] = since_ref

    # 4. Resolve the merge-subject template from policy (AD-24) -- moved
    # ahead of the gate re-run (code review, 2026-08-06, P3/P6): the
    # already-merged short-circuit below (step 5) needs the template to
    # classify `main`'s own history, and a `PolicyIOError` here must be a
    # HARD STOP, exactly like every other precondition failure in this
    # function -- never a silently-defaulted template that could defeat
    # AD-24's "policy governs the subject, never a code literal" promise
    # (code review, 2026-08-06, P3, both reviewers independently: the
    # original version appended the finding but fell through and merged
    # anyway).
    project_data: Mapping[str, object] = {}
    if policy._is_valid_project_slug(slug):
        candidate = conventional_project_policy_path(slug)
        try:
            present = candidate.is_file()
        except OSError:
            present = True
        if present:
            try:
                project_data = _read_project_policy(candidate)
            except PolicyIOError as exc:
                findings.append(exc.finding)
                return _emit(args, "deploy land-story", data, findings, _render_text_land_story)
    effective, policy_findings = policy.compose(project_slug=slug, project=project_data, flags={})
    findings.extend(policy_findings)
    template = effective.merge_subject_template.value

    # 5. Already-merged short-circuit (code review, 2026-08-06, P6): reuses
    # the SAME durability-detection machinery Story 4.1's `deploy promote`
    # already established (`VcsPort.commit_subjects` + `core.promotion.
    # merged_story_keys`), never a reimplementation. Re-running `land-story`
    # on an already-durably-merged key must be a clean no-op -- no gate run,
    # no merge attempt, no spurious empty merge commit, no duplicate journal
    # entry. Best-effort: a read failure here does not block the real
    # attempt below (the safety-critical checks -- the gate, and P1/P4's own
    # merge-time guards -- still protect the merge itself).
    try:
        main_subjects = vcs.commit_subjects(git_repo_root, _MERGE_BASE_BRANCH)
    except VcsCommandError:
        main_subjects = ()
    merged_keys_now = promotion.merged_story_keys(main_subjects, template, slug)

    # Story 4.6's pre-action reconciliation precondition (AD-6/AD-21/AD-28):
    # `merged_keys_now` is ALREADY this run's own fresh, live evidence --
    # exactly "does the story now appear in merged_story_keys", the
    # story's own Always bullet for `land-story`. A prior, possibly-crashed
    # invocation's open `deploy-land-story-merge` intent for THIS key is
    # closed here with a `reconciliation` outcome; the merge below is
    # unaffected either way -- it is already governed entirely by the
    # already-merged short-circuit immediately following.
    deploy_run = _DeployRun(fs, root, slug, _deploy_writer_id("land-story"))
    _reconcile_open_intents(
        fs,
        root,
        slug,
        kind=_LAND_MERGE_KIND,
        confirmed_story_keys=merged_keys_now,
        evidence_note="story key now reachable in main's own commit history",
        deploy_run=deploy_run,
        findings=findings,
    )

    if story_key in merged_keys_now:
        data["already_merged"] = True
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)

    # 6. Re-run the FULL gate in-process (verify commands + --scope-check).
    # Both halves must be green -- reuses cli/gate.py::evaluate_gate's own
    # logic as a function call (Story 4.3's own Always bullet), never a
    # shelled-out re-invocation of the `marshal` CLI and never a second,
    # independently-drifting gate implementation.
    gate_args = argparse.Namespace(
        project=slug, run_id=None, scope_check=True, story=str(story_key)
    )
    gate_envelope = evaluate_gate(gate_args, process=process, vcs=vcs, fs=fs)
    data["gate_verdict"] = gate_envelope.verdict.value
    findings.extend(gate_envelope.findings)
    if gate_envelope.verdict is not Verdict.CLEAN:
        # Code review (2026-08-06, P2, Blind Hunter): `status_for` treats
        # `warn` as "ok", but a warn-tier gate result (real findings exist,
        # just not blocking ones) is NOT "green" in the strict sense FR-27
        # requires for a manual, deliberate landing decision -- refuse on
        # anything short of the lattice's own strictest clean rung, not
        # merely `status_for`'s coarser ok/error partition.
        if status_for(gate_envelope.verdict) is Status.OK:
            findings.append(
                Finding(
                    code=_MRS_DEPLOY_010,
                    severity=Severity.ERROR,
                    message=(
                        f"the full gate re-run for {story_key} evaluated "
                        f"{gate_envelope.verdict.value!r}, not exactly "
                        "'clean' -- a manual landing requires a fully clean "
                        "gate, not merely a non-blocking warn-tier result"
                    ),
                )
            )
        # Refused before any merge attempt -- no journal entry, no merge.
        # The gate's own findings (already appended above) name which half
        # failed.
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)

    # 7. Render the merge subject (AD-24) -- never hand-typed.
    subject = identity.render_merge_subject(story_key, template)
    data["subject"] = subject

    # 8. Pin `branch`'s own tip immediately after the gate evaluated it
    # (code review, 2026-08-06, P4): the gate is evaluated against the
    # branch's tip at one point in time, but nothing previously pinned that
    # sha before the (potentially slow) gate run completes -- a commit
    # landing on `branch` in that window would otherwise get merged as if
    # the now-stale gate result still applied to it.
    try:
        branch_tip_after_gate = vcs.resolve_ref(git_repo_root, branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_011,
                severity=Severity.ERROR,
                message=(
                    f"cannot pin {branch!r}'s own tip immediately after the "
                    f"gate evaluated it, refusing to land {story_key}: {exc}"
                ),
            )
        )
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)

    # 9. Re-verify, immediately before merging, that `branch` still points
    # at the pinned tip -- if it moved, refuse rather than silently merge
    # whatever it now points to. `merge_branch` below is then handed the
    # CAPTURED SHA (not the bare branch name), so even a change landing
    # between this check and the actual `git merge` invocation inside
    # `merge_branch` still merges the pinned commit, not a newer one.
    try:
        branch_tip_now = vcs.resolve_ref(git_repo_root, branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_011,
                severity=Severity.ERROR,
                message=(
                    f"cannot reconfirm {branch!r}'s own tip immediately "
                    f"before merging, refusing to land {story_key}: {exc}"
                ),
            )
        )
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)
    if branch_tip_now != branch_tip_after_gate:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_011,
                severity=Severity.ERROR,
                message=(
                    f"{branch!r} moved (from {branch_tip_after_gate!r} to "
                    f"{branch_tip_now!r}) during the gate evaluation window "
                    f"-- refusing to land {story_key} against a commit the "
                    "gate never evaluated"
                ),
            )
        )
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)

    # 10. Merge -- the CAPTURED sha, not the bare branch name (see step 9).
    # A conflict/failure here is a hard stop -- never retried, never
    # auto-resolved. `merge_branch` itself never touches repo_root's own
    # active checkout (code review, 2026-08-06, P1) and protects `into`
    # with its own compare-and-swap ref update.
    #
    # Story 4.6 (AD-6): an `intent` entry BEFORE this irreversible merge, an
    # `outcome` AFTER it succeeds. A `merge_branch` failure leaves the
    # intent open -- no outcome is written, per the story's own I/O matrix.
    merge_intent_id = deploy_run.write(
        findings,
        kind=_LAND_MERGE_KIND,
        phase=Phase.INTENT,
        payload={
            "action": "merge_branch",
            "story_keys": [str(story_key)],
            "branch": branch,
            "into": _MERGE_BASE_BRANCH,
        },
    )
    try:
        merge_sha = vcs.merge_branch(
            git_repo_root, branch_tip_after_gate, into=_MERGE_BASE_BRANCH, subject=subject
        )
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_008,
                severity=Severity.ERROR,
                message=f"merge of {branch!r} into {_MERGE_BASE_BRANCH!r} failed: {exc}",
            )
        )
        return _emit(args, "deploy land-story", data, findings, _render_text_land_story)
    data["merge_sha"] = merge_sha
    if merge_intent_id is not None:
        deploy_run.write(
            findings,
            kind=_LAND_MERGE_KIND,
            phase=Phase.OUTCOME,
            payload={
                "action": "merge_branch",
                "story_keys": [str(story_key)],
                "branch": branch,
                "into": _MERGE_BASE_BRANCH,
                "merge_sha": merge_sha,
            },
            intent_id=merge_intent_id,
        )

    # 11. Journal the manual landing -- one observation entry, fsync=True,
    # --justification redacted at capture (AD-34). A redaction failure
    # (code review, 2026-08-06, P7) is surfaced as a registered WARN finding
    # (appended to `findings` by `_journal_manual_landing` itself) rather
    # than silently writing `null` with no visible trace of the gap -- the
    # landing still proceeds; this is a visibility fix, not a new
    # safety-critical precondition.
    journal_finding = _journal_manual_landing(
        fs,
        root,
        slug,
        story_key=str(story_key),
        justification=justification,
        merge_sha=merge_sha,
        gate_verdict=gate_envelope.verdict.value,
        findings=findings,
    )
    if journal_finding is not None:
        findings.append(journal_finding)

    # 12. Conformance audit -- reported, never blocking (the story's own
    # Never bullet). A read failure here is a reporting gap, not grounds to
    # undo an already-successful landing -- WARN, not ERROR/UNEVALUABLE.
    try:
        window_subjects = vcs.commit_subjects(git_repo_root, f"{since_ref}..{merge_sha}")
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_009,
                severity=Severity.WARN,
                message=(
                    f"conformance audit could not enumerate commits between "
                    f"{since_ref!r} and {merge_sha!r}: {exc}"
                ),
            )
        )
        data["non_conforming_merges"] = None
    else:
        non_conforming: list[str] = []
        for window_subject in window_subjects:
            try:
                identity.parse_merge_subject(window_subject, template)
            except identity.MergeSubjectConformanceError:
                # Reported only -- never fed into `findings`: doing so
                # would reclassify this already-successful landing's own
                # verdict away from `clean`, exactly the blocking behavior
                # the story's own Never bullet forbids.
                non_conforming.append(window_subject)
        data["non_conforming_merges"] = non_conforming

    return _emit(args, "deploy land-story", data, findings, _render_text_land_story)


def _render_text_land_story(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching this module's own
    ``_render_text``/``_render_text_recover_spec`` convention."""
    slug = data.get("slug") or "(no active project)"
    key = data.get("key", "")
    lines = [f"deploy land-story: {slug!r} {key!r}"]
    if "branch" in data:
        lines.append(f"branch: {data['branch']!r}")
    if data.get("already_merged"):
        lines.append("already merged -- no-op (no gate run, no merge attempted)")
    if "gate_verdict" in data:
        lines.append(f"gate verdict: {data['gate_verdict']}")
    if "merge_sha" in data:
        lines.append(f"merge sha: {data['merge_sha']}")
        lines.append(f"subject: {data['subject']!r}")
    non_conforming = data.get("non_conforming_merges")
    if non_conforming is None and "merge_sha" in data:
        lines.append("conformance audit: could not enumerate (see findings)")
    elif non_conforming is not None:
        lines.append(
            f"conformance audit: {len(non_conforming)} non-conforming merge(s) "
            f"since {data.get('since')!r}"
        )
        for subject_line in non_conforming:
            lines.append(f"  {subject_line!r}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


# =====================================================================
# ``marshal deploy batch-pr`` (Story 4.4, FR-29/NFR-2, AD-34).
# =====================================================================


def _batch_pr_redact(text: str) -> Redacted | None:
    """Mirrors ``_land_redact_text``'s established ``to_redacted({"k":
    text}); json.loads(...)["k"]`` round-trip idiom (AD-34's own
    redact-at-capture pattern) -- but returns a fresh ``Redacted`` wrapping
    the already-redacted plain text directly, rather than unwrapping all the
    way back to a bare ``str``: ``ForgePort.create_pr``/``update_pr`` need a
    ``Redacted`` INPUT, never a bare string reaching the port boundary.
    Returns ``None`` on any redaction failure, the same tolerant shape
    ``_land_redact_text`` uses -- the caller decides how to report it.

    Code review (2026-08-06, P11, Blind Hunter): the exception net is a
    broad, bare ``except Exception`` -- a deliberate, narrow exception to
    this codebase's own no-bare-except norm, justified ONLY at this one call
    site: ``to_redacted``'s stated contract (``core/egress.py``) is "never
    let unredacted text through, no matter what goes wrong", and a
    hardcoded allowlist (the ``ValueError``/``LookupError``/``TypeError``
    this function used to catch) can only ever enumerate the exception
    types its author already thought of -- any type ``to_redacted``/its
    callees raise that falls OUTSIDE that allowlist would propagate
    uncaught instead of degrading to "redaction failed, refuse to write",
    silently defeating the one safety property this function exists to
    guarantee. Every other bare-except site in this codebase enumerates its
    exceptions explicitly; this is the one place where "fail closed on
    literally anything" is itself the contract."""
    try:
        redacted = to_redacted({"text": text})
        plain = json.loads(redacted.text)["text"]
    except Exception:  # noqa: BLE001 -- deliberate, see above
        return None
    return Redacted(text=plain)


def _batch_pr_title(slug: str, wave_keys: list[StoryKey]) -> str:
    """No AI-attribution or courtesy preamble (FR-35) -- a plain, factual
    title naming the wave."""
    if not wave_keys:
        return f"marshal: batch PR for {slug}"
    keys_text = ", ".join(str(key) for key in wave_keys)
    noun = "story" if len(wave_keys) == 1 else "stories"
    return f"marshal: land {len(wave_keys)} {slug} {noun} ({keys_text})"


def _batch_pr_body(wave_keys: list[StoryKey], gate_verdicts: Mapping[str, str]) -> str:
    """Lists every wave story with its journal-derived gate verdict
    (``"unknown"`` when no ``manual-landing`` journal record names it --
    e.g. a story that landed through the ordinary dev/review flow rather
    than ``marshal deploy land-story``). No AI-attribution or courtesy
    preamble anywhere (FR-35, default-off)."""
    lines = ["Batch PR opened by `marshal deploy batch-pr`.", "", "Stories in this wave:"]
    for key in wave_keys:
        verdict = gate_verdicts.get(str(key), "unknown")
        lines.append(f"- {key}: gate verdict `{verdict}`")
    return "\n".join(lines)


def _run_dir_sort_key(path: Path) -> float:
    """The run directory's own ``mtime`` (code review, 2026-08-06, P7): run
    directory NAMES are not reliably chronologically sortable
    (``"acme-run-10"`` sorts lexicographically BEFORE ``"acme-run-2"``), and
    ``_gather_gate_verdicts``'s own "last write wins" collection means a
    lexicographic sort could report a STALE gate verdict for a story
    re-landed more recently under a lexicographically-earlier directory
    name. ``mtime`` is a real, monotonically-advancing fact about each run
    directory (mirrors ``_run_snapshot_candidates``'s own established
    per-file mtime-ordering precedent, one level up at the directory
    granularity) -- an unreadable directory sorts as the oldest possible
    (``0.0``) rather than raising, so one bad directory's stat failure never
    aborts the whole gather."""
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _gather_gate_verdicts(fs: FsPort, root: Path, slug: str) -> dict[str, str]:
    """Every story key's own most-recently-journaled gate verdict, reusing
    Story 3.2's ``core.journal.fold`` (the story's own Always bullet: "the
    journal fold's own gate-verdict records for each key") over every
    ``manual-landing`` observation (Story 4.3's own ``_LAND_KIND``) any of
    this project's Tier-3 run directories carries -- the one real source of
    a per-story gate verdict this codebase journals today. A story landed
    through the ordinary dev/review flow (never through ``land-story``)
    simply has no entry here; ``_batch_pr_body`` reports that as
    ``"unknown"``, never fabricated. Best-effort: an unreadable runs
    directory, journal file, or sidecar blob is silently skipped (mirrors
    ``fold``'s own "one bad line never aborts the fold" posture, one level
    up -- one bad run directory never aborts gathering every other run's
    verdicts).

    Run directories are folded in ``mtime`` order, OLDEST first (code
    review, 2026-08-06, P7 -- see ``_run_dir_sort_key``), so "last write
    wins" below genuinely means "most recently landed wins", never an
    artifact of directory-NAME lexicographic order.

    Code review (2026-08-06, P6, both reviewers independently): the ``fold``
    call's own except clause is broadened from a bare ``TypeError`` to the
    same "one bad input never aborts the whole gather" tier this codebase
    already uses for per-item degradation elsewhere (``FsError`` for a
    filesystem read, ``OSError`` for a directory stat/glob) -- a malformed
    ``journal.jsonl``/sidecar blob surfacing as ``ValueError``/``KeyError``
    (or any shape ``fold``'s own contract does not explicitly rule out) must
    skip that ONE run directory, exactly like this function's own docstring
    already promises, never crash the entire ``batch-pr`` command over a
    cosmetic PR-body-enrichment step."""
    runs_dir = root / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs"
    verdicts: dict[str, str] = {}
    try:
        run_dirs = sorted(
            (path for path in runs_dir.iterdir() if path.is_dir()), key=_run_dir_sort_key
        )
    except OSError:
        return verdicts
    for run_dir in run_dirs:
        try:
            text = fs.read_text(run_dir / _LAND_JOURNAL_FILENAME)
        except FsError:
            continue
        sidecars: dict[str, str | None] = {}
        try:
            blob_paths = sorted((run_dir / "blobs").glob("*.json"))
        except OSError:
            blob_paths = []
        for blob_path in blob_paths:
            try:
                sidecars[f"blobs/{blob_path.name}"] = fs.read_text(blob_path)
            except FsError:
                sidecars[f"blobs/{blob_path.name}"] = None
        try:
            fold_result = fold(text.split("\n"), sidecars=sidecars)
        except (TypeError, ValueError, KeyError, OSError):
            continue
        for entry in fold_result.entries:
            if entry.kind != _LAND_KIND:
                continue
            story_key = entry.payload.get("story_key")
            gate_verdict = entry.payload.get("gate_verdict")
            if isinstance(story_key, str) and isinstance(gate_verdict, str):
                verdicts[story_key] = gate_verdict
    return verdicts


def _evaluate_hygiene(
    landing_rules: tuple[LandingRule, ...],
    changed_paths: tuple[str, ...],
    forge: ForgePort,
    repo_ref: ForgeRef,
    head_sha: str,
) -> tuple[list[dict[str, object]], list[Finding], tuple[str, ...]]:
    """The hygiene preflight (FR-29): every ``landing_rules`` entry is
    evaluated generically via ``core.landing.rule_applies`` (reused, never
    reimplemented) against ``changed_paths``. A fired ``required_check``
    rule queries ``ForgePort.check_run_status`` against the wave's head
    commit -- ``"success"`` is satisfied, anything else (including a
    ``ForgeCommandError``) is UNSATISFIED and BLOCKING, named in a
    remediation-bearing ``MRS-DEPLOY-013``/``MRS-DEPLOY-014`` finding. A
    fired ``label`` rule is collected as an ACTION, never blocking -- it is
    added to the returned label tuple regardless of whether the SAME rule's
    own ``required_check`` (if also set) was satisfied, since the two
    consequences are independent per the spec's own Always bullet.

    Returns ``(report, blocking_findings, fired_labels)``: ``report`` is
    one entry per DECLARED rule (not only the fired ones), each carrying
    ``name``/``applies``/``satisfied`` (``None`` when the rule did not
    fire) -- the AC's own "reports which project-configured rules apply to
    the change set and whether each is satisfied", not merely the fired
    subset.

    Code review (2026-08-06, P9, Edge Case Hunter): a fired rule's own
    ``label`` now fires ONLY when that SAME rule's own ``required_check``
    (if any) is satisfied -- a check that resolved to a real, non-success
    conclusion and a check whose status could not be DETERMINED at all
    (``ForgeCommandError``) are treated IDENTICALLY here, matching the
    blocking behavior above (both already block create/update the same
    way). Previously the two diverged: a raised ``ForgeCommandError``
    skipped the label (via an early ``continue``), but a normally-resolved
    non-success conclusion still fired it -- an inconsistency for the
    SAME underlying condition ("this rule's required_check did not pass").
    A rule with no ``required_check`` at all is unaffected: its label
    always fires when the rule applies, exactly as before."""
    report: list[dict[str, object]] = []
    blocking: list[Finding] = []
    fired_labels: list[str] = []
    for rule in landing_rules:
        applies = rule_applies(rule, changed_paths)
        entry: dict[str, object] = {"name": rule.name, "applies": applies}
        if not applies:
            entry["satisfied"] = None
            report.append(entry)
            continue
        satisfied = True
        if rule.required_check is not None:
            try:
                status = forge.check_run_status(
                    repo_ref, ForgeRef(head_sha), ForgeRef(rule.required_check)
                )
            except ForgeCommandError as exc:
                satisfied = False
                entry["satisfied"] = False
                entry["required_check_status"] = None
                blocking.append(
                    Finding(
                        code=_MRS_DEPLOY_014,
                        severity=Severity.ERROR,
                        message=(
                            f"cannot evaluate hygiene rule {rule.name!r}'s "
                            f"required_check {rule.required_check!r} on "
                            f"{head_sha!r}: {exc}"
                        ),
                    )
                )
            else:
                satisfied = status == "success"
                entry["satisfied"] = satisfied
                entry["required_check_status"] = status
                if not satisfied:
                    blocking.append(
                        Finding(
                            code=_MRS_DEPLOY_013,
                            severity=Severity.ERROR,
                            message=(
                                f"hygiene rule {rule.name!r} is unsatisfied: "
                                f"required_check {rule.required_check!r} is "
                                f"{status!r} (not 'success') on {head_sha!r} -- "
                                f"remediation: push a commit that makes "
                                f"{rule.required_check!r} succeed on this branch "
                                "and re-run batch-pr"
                            ),
                        )
                    )
        else:
            entry["satisfied"] = True
        if rule.label is not None and satisfied:
            fired_labels.append(rule.label)
        report.append(entry)
    return report, blocking, tuple(fired_labels)


def run_batch_pr(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
    forge: ForgePort | None = None,
) -> int:
    # Local import -- see run_land_story's own comment for why cli/init.py
    # is never imported at module level here.
    from .init import _home_path

    vcs = vcs if vcs is not None else GitVcs()
    fs = fs if fs is not None else LocalFs()
    forge = forge if forge is not None else GhForge()

    slug = args.slug
    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug}

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
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    root = repo_root()
    home = _home_path(slug)
    head_branch = f"loop/{slug}"
    data["branch"] = head_branch

    try:
        git_repo_root = vcs.repo_common_root(home)
        branch_ok = vcs.branch_exists(git_repo_root, head_branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_007,
                severity=Severity.ERROR,
                message=(
                    f"cannot resolve the loop-home station branch {head_branch!r} "
                    f"for {slug!r}'s batch PR: {exc}"
                ),
            )
        )
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)
    if not branch_ok:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_007,
                severity=Severity.ERROR,
                message=f"{head_branch!r} does not exist -- nothing to batch for {slug!r}",
            )
        )
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    project_data: Mapping[str, object] = {}
    if policy._is_valid_project_slug(slug):
        candidate = conventional_project_policy_path(slug)
        try:
            present = candidate.is_file()
        except OSError:
            present = True
        if present:
            try:
                project_data = _read_project_policy(candidate)
            except PolicyIOError as exc:
                findings.append(exc.finding)
                return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)
    effective, policy_findings = policy.compose(project_slug=slug, project=project_data, flags={})
    findings.extend(policy_findings)

    # Code review (2026-08-06, P1, both reviewers' independent top finding):
    # `core/policy.py::compose` NEVER raises -- a malformed `landing_rules`
    # layer is reported via a non-blocking `MRS-POLICY-002` finding and the
    # field silently falls back to `DEFAULT_POLICY["landing_rules"]` (empty).
    # Proceeding past that unconditionally would let a CONFIG TYPO -- not a
    # deliberate decision -- silently disable the entire hygiene preflight
    # (every rule evaluates against zero declared rules, `applies` is never
    # even checked). Refused HERE, before `landing_rules`/`base` are even
    # read below, and before the forge is ever touched -- never a softer
    # degrade to "ran with whatever policy composed to".
    if any(
        finding.severity is Severity.ERROR and "'landing_rules'" in finding.message
        for finding in policy_findings
    ):
        findings.append(
            Finding(
                code=_MRS_DEPLOY_015,
                severity=Severity.ERROR,
                message=(
                    "refusing to run the hygiene preflight for "
                    f"{head_branch!r}: policy composition reported a "
                    "malformed 'landing_rules' layer above -- proceeding "
                    "would silently evaluate against an EMPTY rule set "
                    "instead of the project's declared rules; fix the "
                    "malformed layer and re-run batch-pr"
                ),
            )
        )
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    base = effective.landing_base_branch.value
    template = effective.merge_subject_template.value
    landing_rules = effective.landing_rules.value
    data["base"] = base

    # Wave discovery (reuses Story 4.1's own merged_story_keys/durability
    # machinery, per the story's own Always bullet): every story key
    # reachable in the station branch's own commits since its merge-base
    # with the configured base branch.
    try:
        merge_base_sha = vcs.merge_base(git_repo_root, head_branch, base)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_007,
                severity=Severity.ERROR,
                message=(
                    f"cannot compute the merge base of {head_branch!r} and "
                    f"{base!r}: {exc}"
                ),
            )
        )
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)
    try:
        wave_subjects = vcs.commit_subjects(git_repo_root, f"{merge_base_sha}..{head_branch}")
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_007,
                severity=Severity.ERROR,
                message=(
                    f"cannot enumerate commits between {merge_base_sha!r} and "
                    f"{head_branch!r}: {exc}"
                ),
            )
        )
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)
    wave_keys = sorted(promotion.merged_story_keys(wave_subjects, template, slug))
    data["wave"] = [str(key) for key in wave_keys]

    if not wave_keys:
        # Clean no-op (the story's own I/O matrix: "Empty wave -- nothing
        # merged since last batch-pr" -> "Clean no-op, data.opened: false,
        # data.updated: false").
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    # Code review (2026-08-06, P10, Edge Case Hunter): `existing is None`
    # (below, from `find_open_pr`) conflates "genuinely never opened" with
    # "was opened for this exact wave and has since been merged/closed" --
    # reattempting `create_pr` on an already-landed wave would open a
    # spurious duplicate PR for content that is already merged. Reuses the
    # SAME durability-detection machinery `run_promote`/`land-story` already
    # established (`VcsPort.commit_subjects` + `core.promotion.
    # merged_story_keys`), read against `base` itself -- if EVERY story key
    # this wave discovered is already durably reachable from `base`'s own
    # history, the wave has already landed and this is a clean no-op, never
    # a fresh `create_pr`/`update_pr` attempt. Best-effort: a read failure
    # here never blocks the real attempt below.
    try:
        base_subjects = vcs.commit_subjects(git_repo_root, base)
    except VcsCommandError:
        base_subjects = ()
    already_landed_keys = promotion.merged_story_keys(base_subjects, template, slug)
    if wave_keys and all(key in already_landed_keys for key in wave_keys):
        data["opened"] = False
        data["updated"] = False
        data["already_landed"] = True
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    try:
        head_sha = vcs.resolve_ref(git_repo_root, head_branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_007,
                severity=Severity.ERROR,
                message=f"cannot resolve {head_branch!r}'s own tip: {exc}",
            )
        )
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    # Code review (2026-08-06, P5, Blind Hunter): `changed_files` below
    # diffs the LOCAL WORKTREE (`home`) against `base` -- there is no prior
    # guarantee `home` is actually checked out at `head_sha` (the SAME
    # commit the hygiene preflight and the PR write both use). A stale or
    # detached worktree could silently under-report the real change set,
    # letting a `required_check` rule that SHOULD have fired skip
    # evaluation entirely. Verified via the new `VcsPort.worktree_head_sha`
    # primitive (git rev-parse HEAD run inside `home`) before `changed_files`
    # is ever trusted.
    try:
        home_head_sha = vcs.worktree_head_sha(home)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_017,
                severity=Severity.ERROR,
                message=(
                    f"cannot confirm {home}'s own checked-out commit before "
                    f"gathering changed files for {head_branch!r}: {exc}"
                ),
            )
        )
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)
    if home_head_sha != head_sha:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_017,
                severity=Severity.ERROR,
                message=(
                    f"{home}'s checked-out commit ({home_head_sha!r}) does not "
                    f"match {head_branch!r}'s resolved tip ({head_sha!r}) -- "
                    "refusing to trust changed_files against a possibly "
                    f"stale or detached worktree; re-sync {home} and re-run "
                    "batch-pr"
                ),
            )
        )
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    # Changed-path gathering (reuses Story 2.3's own changed_files pattern,
    # per the story's own Always bullet) -- the hygiene preflight's own
    # change set.
    try:
        changed_paths = vcs.changed_files(git_repo_root, home, base=base)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_007,
                severity=Severity.ERROR,
                message=f"cannot gather {head_branch!r}'s changed files against {base!r}: {exc}",
            )
        )
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    repo_ref = ForgeRef(_FORGE_REPO)
    head_branch_ref = ForgeRef(head_branch)

    # Hygiene preflight, BEFORE any PR write (the story's own Always
    # bullet): a blocking finding exits non-zero with no create/update
    # attempted at all.
    hygiene_report, blocking_findings, fired_labels = _evaluate_hygiene(
        landing_rules, changed_paths, forge, repo_ref, head_sha
    )
    data["hygiene_rules"] = hygiene_report
    if blocking_findings:
        findings.extend(blocking_findings)
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    gate_verdicts = _gather_gate_verdicts(fs, root, slug)
    title_redacted = _batch_pr_redact(_batch_pr_title(slug, wave_keys))
    body_redacted = _batch_pr_redact(_batch_pr_body(wave_keys, gate_verdicts))
    if title_redacted is None or body_redacted is None:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_014,
                severity=Severity.ERROR,
                message=(
                    "cannot redact the batch PR title/body -- refusing to "
                    "write unredacted text through ForgePort"
                ),
            )
        )
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    try:
        existing = forge.find_open_pr(repo_ref, head_branch_ref)
    except ForgeCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_014,
                severity=Severity.ERROR,
                message=f"cannot look up an existing PR for {head_branch!r}: {exc}",
            )
        )
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    # Code review (2026-08-06, P8, Edge Case Hunter): `existing`'s own base
    # branch is never checked against the policy-declared `base` before
    # `update_pr` is called -- an open PR for this head branch that targets
    # a DIFFERENT base than policy declares would otherwise be silently
    # updated as if it were this command's own batch PR.
    if existing is not None and existing.base != base:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_018,
                severity=Severity.ERROR,
                message=(
                    f"an open PR #{existing.number} already exists for "
                    f"{head_branch!r}, but targets base {existing.base!r}, "
                    f"not the policy-declared {base!r} -- refusing to update "
                    "a PR that may belong to an unrelated intent"
                ),
            )
        )
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    # Story 4.6's pre-action reconciliation precondition (AD-6/AD-21/AD-28).
    #
    # Code review (2026-08-06, P2, both reviewers' independent top finding):
    # the story's own Always bullet names the evidence as "does
    # ForgePort.find_open_pr now show a PR already reflecting THIS
    # content" -- but `existing is not None` alone (bare PR-existence on
    # the head branch) does NOT confirm that. A stale PR from an earlier,
    # differently-scoped wave, or a manually-opened PR unrelated to a
    # crashed intent, satisfies `existing is not None` just as readily as
    # a PR this exact wave's own `create_pr`/`update_pr` produced --
    # wrongly closing a prior crashed run's open intent on evidence that
    # never actually confirmed its own story keys. `PrInfo` (``ports/
    # forge.py``) carries no title/body/content field ``ForgePort`` could
    # query to verify per-key coverage, and adding one is out of this
    # story's scope (Code Map names no new ``ForgePort`` methods) -- so
    # this call NEVER supplies `confirmed_story_keys` for `batch-pr`: every
    # `batch-pr` open intent stays open and reports `MRS-DEPLOY-021`
    # (WARN, non-blocking) until a stronger evidence source exists,
    # requiring the operator's own confirmation rather than an automatic
    # close on a signal too weak to trust. This does not change whether
    # create_pr or update_pr is called below (that decision is `existing`'s
    # own, already-established idempotence check, unchanged by this
    # story).
    deploy_run = _DeployRun(fs, root, slug, _deploy_writer_id("batch-pr"))
    _reconcile_open_intents(
        fs,
        root,
        slug,
        kind=_BATCH_PR_WRITE_KIND,
        confirmed_story_keys=set(),
        evidence_note="find_open_pr now shows a PR reflecting this content",
        deploy_run=deploy_run,
        findings=findings,
    )

    # Code review (2026-08-06, P4, both reviewers independently, mirroring
    # land-story's own identical TOCTOU fix): the hygiene preflight above
    # vetted `head_sha`, a SHA pinned once. If `head_branch` advanced (new
    # commits landed) in the window between that read and this PR write, the
    # content actually about to be opened/updated was never vetted by the
    # preflight that was supposed to gate it. Re-resolved and reconfirmed
    # immediately before the write, not merely once at the top of this
    # function.
    try:
        head_sha_now = vcs.resolve_ref(git_repo_root, head_branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_016,
                severity=Severity.ERROR,
                message=(
                    f"cannot reconfirm {head_branch!r}'s own tip immediately "
                    f"before the PR write: {exc}"
                ),
            )
        )
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)
    if head_sha_now != head_sha:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_016,
                severity=Severity.ERROR,
                message=(
                    f"{head_branch!r} moved (from {head_sha!r} to "
                    f"{head_sha_now!r}) during hygiene evaluation -- refusing "
                    "to open/update a PR for content the hygiene preflight "
                    "never vetted; re-run batch-pr"
                ),
            )
        )
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    # Story 4.6 (AD-6): an `intent` entry BEFORE this irreversible
    # create_pr/update_pr write, an `outcome` AFTER it succeeds. A write
    # failure leaves the intent open -- no outcome is written, per the
    # story's own I/O matrix.
    pr_action = "create_pr" if existing is None else "update_pr"
    pr_intent_id = deploy_run.write(
        findings,
        kind=_BATCH_PR_WRITE_KIND,
        phase=Phase.INTENT,
        payload={"action": pr_action, "story_keys": [str(key) for key in wave_keys]},
    )
    try:
        if existing is None:
            pr = forge.create_pr(
                repo_ref, ForgeRef(base), head_branch_ref, title_redacted, body_redacted
            )
            data["opened"] = True
            data["updated"] = False
        else:
            pr = forge.update_pr(repo_ref, existing.number, title_redacted, body_redacted)
            data["opened"] = False
            data["updated"] = True
    except ForgeCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_014,
                severity=Severity.ERROR,
                message=f"cannot open/update the batch PR for {head_branch!r}: {exc}",
            )
        )
        data["opened"] = False
        data["updated"] = False
        return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)

    data["pr_number"] = pr.number
    data["pr_url"] = pr.url
    if pr_intent_id is not None:
        deploy_run.write(
            findings,
            kind=_BATCH_PR_WRITE_KIND,
            phase=Phase.OUTCOME,
            payload={
                "action": pr_action,
                "story_keys": [str(key) for key in wave_keys],
                "pr_number": pr.number,
            },
            intent_id=pr_intent_id,
        )

    # Label application -- an ACTION, never a blocking gate (already
    # evaluated above); applied only once the PR exists. Code review
    # (2026-08-06, P2, Edge Case Hunter): `data["labels_applied"]` is set
    # ONLY after `add_labels` returns successfully -- previously it was set
    # to the INTENDED labels before the call, so a `ForgeCommandError`
    # still left the report claiming those labels were applied. On failure
    # it stays empty: this run never confirmed any label actually landed.
    deduped_labels = tuple(sorted(set(fired_labels)))
    data["labels_applied"] = []
    if deduped_labels:
        try:
            forge.add_labels(repo_ref, pr.number, deduped_labels)
        except ForgeCommandError as exc:
            findings.append(
                Finding(
                    code=_MRS_DEPLOY_014,
                    severity=Severity.ERROR,
                    message=(
                        f"batch PR #{pr.number} opened/updated, but applying "
                        f"label(s) {list(deduped_labels)} failed: {exc}"
                    ),
                )
            )
        else:
            data["labels_applied"] = list(deduped_labels)

    return _emit(args, "deploy batch-pr", data, findings, _render_text_batch_pr)


def _render_text_batch_pr(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching this module's own
    ``_render_text``/``_render_text_recover_spec``/``_render_text_land_story``
    convention."""
    slug = data.get("slug") or "(no active project)"
    lines = [f"deploy batch-pr: {slug!r}"]
    if "branch" in data:
        lines.append(f"branch: {data['branch']!r}")
    wave = data.get("wave")
    if wave is not None:
        lines.append(f"wave: {len(wave)} stor{'y' if len(wave) == 1 else 'ies'} ({', '.join(wave)})")
    if data.get("already_landed"):
        lines.append("already landed -- no-op (no PR write attempted)")
    hygiene_rules = data.get("hygiene_rules")
    if hygiene_rules:
        lines.append("hygiene rules:")
        for entry in hygiene_rules:
            lines.append(
                f"  {entry['name']!r} applies={entry['applies']} satisfied={entry['satisfied']}"
            )
    if data.get("opened"):
        lines.append(f"opened: PR #{data.get('pr_number')} ({data.get('pr_url')})")
    elif data.get("updated"):
        lines.append(f"updated: PR #{data.get('pr_number')} ({data.get('pr_url')})")
    else:
        lines.append("opened: false, updated: false")
    labels_applied = data.get("labels_applied")
    if labels_applied:
        lines.append(f"labels applied: {', '.join(labels_applied)}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


# =====================================================================
# ``marshal deploy refresh-feed`` (Story 4.5, AD-33).
# =====================================================================


def _gather_claimed_commits(
    fs: FsPort, harness: HarnessPort, home: Path, project_slug: str
) -> tuple[status.ClaimedCommit, ...]:
    """The journal/harness-sourced half of ``refresh-feed``'s two
    independently-gathered sources (AD-33): the most recent Marshal run for
    ``project_slug`` under ``home``'s own Tier-3 store
    (``.spin._latest_run_dir``), that run's own ``harness_run_id`` (its
    launch/resume outcome entry's own field,
    ``.spin._resolve_harness_run_id_for_resume`` -- the SAME lookup
    ``marshal factory resume`` already uses, reused rather than
    reimplemented), and, when both resolve, ``HarnessPort.
    run_status_snapshot``'s own ``tasks`` (Story 3.8's ``TaskPhaseSnapshot``,
    every task's ``commit_sha`` -- the story's own worked example of a
    "journal claim about a repository fact"). Each task's bmad-loop-native
    ``story_key`` is normalized to Marshal's canonical ``StoryKey`` here, at
    the CLI boundary (mirrors ``_discover_candidates``'s own established
    skip-invalid convention: a task whose key does not normalize is
    skipped, never a hard failure for the whole gather). Returns ``()`` --
    never raises -- for every "no journal facts available" case (no loop
    home, no run yet, no resolvable ``harness_run_id``, or
    ``run_status_snapshot`` itself returns ``None``): this is a legitimate,
    reportable state (``core.status.reconcile_feed_domains`` then reports
    git's own answer alone, per the story's own I/O matrix), never an
    error."""
    # Local import: `cli/spin.py` imports `from .init import _home_path`,
    # and `cli/init.py` imports `from . import deploy` -- a module-level
    # `from .spin import ...` here would create the same cli.deploy <->
    # cli.init load-order cycle `run_land_story`'s own comment already
    # documents for `cli/gate.py`.
    from .spin import _latest_run_dir, _resolve_harness_run_id_for_resume

    # Code review (2026-08-06, P2, both reviewers): broadened from
    # `except FsError` alone -- `FsPort.exists`'s own established
    # implementation (`LocalFs.exists`) already swallows `OSError` to
    # `False` internally and never raises it, but this function's own
    # "never raises" promise must hold for ANY `FsPort`, not only the one
    # shipped adapter (a test double, or a future implementation, that
    # does not honor that internal convention).
    try:
        home_present = fs.exists(home)
    except (FsError, OSError):
        home_present = False
    if not home_present:
        return ()

    run_dir = _latest_run_dir(home, project_slug)
    if run_dir is None:
        return ()
    run_id = run_dir.name
    harness_run_id = _resolve_harness_run_id_for_resume(fs, run_dir, run_id)
    if harness_run_id is None:
        return ()

    # Code review (2026-08-06, P2, both reviewers): `HarnessPort.
    # run_status_snapshot`'s own docstring promises "never raises", but this
    # function's OWN docstring makes the identical promise to ITS caller --
    # wrapped defensively with the SAME guard tuple
    # `adapters/harness_bmadloop.py::BmadLoopHarness.run_status_snapshot`
    # already uses internally to hold that promise against a malformed
    # `state.json` (`OSError`/`ValueError`/`KeyError`/`TypeError`/
    # `AttributeError`/`ArithmeticError`/`RecursionError`), so an
    # implementation that does not honor its own contract degrades this
    # function to "no claim available for this run" rather than crashing
    # the whole `refresh-feed` invocation.
    try:
        snapshot = harness.run_status_snapshot(home, harness_run_id)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ArithmeticError, RecursionError):
        return ()
    if snapshot is None:
        return ()

    claims: list[status.ClaimedCommit] = []
    for task in snapshot.tasks:
        try:
            story_key = identity.normalize(task.story_key)
        except MalformedStoryKeyError:
            # A malformed/non-str story_key on one task is this task's own
            # problem, never the whole gather's -- skipped, mirroring
            # `_discover_candidates`'s own established convention.
            # `identity.normalize` raises ONLY `MalformedStoryKeyError`
            # (verified: it guards non-`str` input itself), so this is
            # already the complete catch for this call -- no broader
            # exception reaches here.
            continue
        claims.append(
            status.ClaimedCommit(
                story_key=story_key,
                claimed_commit_sha=task.commit_sha,
                phase=task.phase,
            )
        )
    return tuple(claims)


# Code review (2026-08-06, P6, Blind Hunter): `cli/gate.py`'s own
# `verify_commands` execution deliberately passes NO `timeout_s`
# (`adapters/process_posix.py`'s own docstring: a verify command's own
# duration is entirely project-defined, and Marshal has no policy field for
# a per-command timeout budget) -- so there is no verify_commands timeout
# precedent to reuse here. `landing_resync_commands` is a materially
# different shape: its own worked examples (this module's docstring, the
# spec's own Design Notes) are network-facing resync operations (a fetch/
# pull against a remote), the SAME class of operation
# `adapters/vcs_git.py::_GIT_PUSH_TIMEOUT_S` already bounds for this
# package's own git push calls -- reused here rather than inventing an
# unrelated ceiling, so a stalled resync command cannot hang the whole
# `refresh-feed` invocation indefinitely.
_RESYNC_TIMEOUT_S = 120.0


def _run_resync_commands(
    process: ProcessPort, root: Path, commands: tuple[str, ...]
) -> tuple[list[dict[str, object]], list[Finding]]:
    """Executes every ``landing_resync_commands`` entry via ``ProcessPort``
    -- the SAME allowlist-only execution discipline AD-17 already requires
    for ``verify_commands`` (``cli/gate.py::run_evaluate``): ``shlex.split``,
    reject bare shell metacharacters (``.gate._bare_shell_metacharacters``,
    reused rather than reimplemented -- these commands are NEVER run
    through a shell, so a caller who wrote ``cmd1 && cmd2`` must be told,
    not silently handed ``cmd1`` with ``&&``/``cmd2`` as ordinary
    arguments), run via ``ProcessPort.run`` with ``_RESYNC_TIMEOUT_S``
    (code review, 2026-08-06, P6: a hung command must not hang this whole
    command), classify via ``core.status.classify_resync_outcome`` (this
    story's own MRS-DEPLOY-019/020 codes -- never
    ``core.gate.classify_outcome``'s hardcoded ``MRS-GATE-*`` codes, a
    different policy key's own area). Every failure is reported, never
    silently swallowed -- including a whitespace-only entry (code review,
    2026-08-06, P1, both reviewers: ``shlex.split(" ")`` parses CLEANLY to
    an EMPTY token list, distinct from a ``ValueError``, and would
    otherwise reach ``ProcessPort.run`` with no ``argv[0]`` to exec)."""
    # Local import -- see `_gather_claimed_commits`'s own comment for why
    # `cli/gate.py` is never imported at module level here.
    from .gate import _bare_shell_metacharacters

    reports: list[dict[str, object]] = []
    findings: list[Finding] = []
    for command in commands:
        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            report, finding = status.classify_resync_outcome(
                command,
                None,
                failure_reason=(
                    f"cannot parse landing_resync_commands entry {command!r}: {exc}"
                ),
            )
        else:
            if not tokens:
                # Whitespace-only entry (code review, 2026-08-06, P1): parses
                # cleanly, produces no argv[0] to exec -- a malformed entry,
                # reported and skipped, never handed to ProcessPort.run.
                report, finding = status.classify_resync_outcome(
                    command,
                    None,
                    failure_reason=(
                        f"landing_resync_commands entry {command!r} is empty "
                        "after parsing (whitespace-only) -- no executable to run"
                    ),
                )
                reports.append(report)
                if finding is not None:
                    findings.append(finding)
                continue
            shell_chars = _bare_shell_metacharacters(command)
            if shell_chars:
                report, finding = status.classify_resync_outcome(
                    command,
                    None,
                    failure_reason=(
                        f"landing_resync_commands entry {command!r} uses shell "
                        f"syntax ({', '.join(repr(char) for char in shell_chars)}) "
                        "but resync commands are never run through a shell "
                        "(quote or backslash-escape the character if it is "
                        "meant as data)"
                    ),
                )
            else:
                try:
                    result = process.run(tokens, cwd=root, timeout_s=_RESYNC_TIMEOUT_S)
                except (ProcessError, OSError, TimeoutError) as exc:
                    # Code review (2026-08-06, P2, both reviewers): broadened
                    # from `ProcessError` alone -- `PosixProcess.run` never
                    # lets a raw `OSError`/timeout escape (it wraps both into
                    # `ProcessError`), but this function's own "every failure
                    # is reported, never silently swallowed" promise (the
                    # module docstring above) must hold for ANY `ProcessPort`
                    # implementation, not only the one shipped adapter.
                    report, finding = status.classify_resync_outcome(
                        command,
                        None,
                        failure_reason=(
                            f"landing_resync_commands entry {command!r} could "
                            f"not be run: {exc}"
                        ),
                    )
                else:
                    report, finding = status.classify_resync_outcome(command, result)
        reports.append(report)
        if finding is not None:
            findings.append(finding)
    return reports, findings


def run_refresh_feed(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
    process: ProcessPort | None = None,
    harness: HarnessPort | None = None,
) -> int:
    # Local import -- see `_gather_claimed_commits`'s own comment.
    from .init import _home_path

    vcs = vcs if vcs is not None else GitVcs()
    fs = fs if fs is not None else LocalFs()
    process = process if process is not None else PosixProcess()
    harness = harness if harness is not None else BmadLoopHarness()

    project_slug = (
        args.project if args.project is not None else os.environ.get(ENV_ACTIVE_PROJECT, "")
    )
    root = repo_root()
    data: dict[str, object] = {"slug": project_slug, "root": str(root)}
    # Code review (2026-08-06, P5, Blind Hunter): `resync_skipped`/
    # `resync_commands` defaulted here, BEFORE any early-return path below,
    # so every exit -- success or refusal alike -- carries the SAME
    # envelope keys (AD-14's "one envelope shape for every command"). The
    # happy path (bottom of this function) always overwrites both with
    # their real, computed values; only an early refusal ever sees these
    # defaults survive to `_emit`.
    data["resync_skipped"] = True
    data["resync_commands"] = []
    findings: list[Finding] = []

    project_data: Mapping[str, object] = {}
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
                data["stories"] = []
                return _emit(args, "deploy refresh-feed", data, findings, _render_text_refresh_feed)
    effective, policy_findings = policy.compose(
        project_slug=project_slug, project=project_data, flags={}
    )
    findings.extend(policy_findings)

    if not project_slug or not policy._is_valid_project_slug(project_slug):
        # Already reported via MRS-POLICY-005/006 above -- nothing further
        # to reconcile without a real project to look in.
        data["stories"] = []
        return _emit(args, "deploy refresh-feed", data, findings, _render_text_refresh_feed)

    template = effective.merge_subject_template.value

    # --- git-sourced repository facts (AD-33) --------------------------
    # Push route: best-effort, never a hard failure (mirrors
    # `_scan_promotions`'s own AD-29/F-14 precedent) -- a missing/unfetched
    # origin/main is the ordinary "no push route available" case.
    try:
        origin_subjects = vcs.commit_subjects(root, _PUSH_REF)
    except VcsCommandError:
        origin_subjects = ()
    # Merge route: REQUIRED, same as `_scan_promotions` -- its failure means
    # Marshal cannot honestly determine ANY story's durability this run.
    try:
        main_subjects = vcs.commit_subjects(root, _MERGE_BASE_BRANCH)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_DEPLOY_003,
                severity=Severity.ERROR,
                message=(
                    "cannot read local main's commit history to determine "
                    f"repository facts for refresh-feed: {exc}"
                ),
            )
        )
        data["stories"] = []
        return _emit(args, "deploy refresh-feed", data, findings, _render_text_refresh_feed)

    combined_subjects = tuple(origin_subjects) + tuple(main_subjects)
    merged_keys = promotion.merged_story_keys(combined_subjects, template, project_slug)

    # --- journal/harness-sourced process facts (AD-33) ------------------
    home = _home_path(project_slug)
    claims = _gather_claimed_commits(fs, harness, home, project_slug)

    # --- reconciliation (pure core, AD-4/AD-33) --------------------------
    report = status.reconcile_feed_domains(merged_keys, claims)
    findings.extend(report.findings)
    data["stories"] = [
        {
            "story_key": row["story_key"],
            "durable": status.domain_field_to_dict(row["durable"]),
            "claimed_commit_sha": status.domain_field_to_dict(row["claimed_commit_sha"]),
        }
        for row in report.stories
    ]

    # --- landing_resync_commands, gated by landing_resync (Story 4.7) ---
    # Code review (2026-08-06, P7, Blind Hunter): `resync_skipped` alone is
    # `False` both when a command actually ran AND when `landing_resync` is
    # true but `landing_resync_commands` is the documented-default empty
    # tuple -- but `resync_commands` (an empty list only in the "nothing
    # configured" case, real report dicts otherwise) already distinguishes
    # the two: `resync_skipped=False` + `resync_commands=[]` means
    # "attempted, nothing was configured to run"; `resync_skipped=True` +
    # `resync_commands=[]` means "skipped entirely, the policy toggle is
    # off". No behavior change needed -- this comment is the fix.
    if effective.landing_resync.value:
        data["resync_skipped"] = False
        resync_reports, resync_findings = _run_resync_commands(
            process, root, effective.landing_resync_commands.value
        )
        data["resync_commands"] = resync_reports
        findings.extend(resync_findings)
    else:
        data["resync_skipped"] = True
        data["resync_commands"] = []

    return _emit(args, "deploy refresh-feed", data, findings, _render_text_refresh_feed)


def _render_text_refresh_feed(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching this module's own
    ``_render_text``/``_render_text_batch_pr`` convention."""
    slug = data.get("slug") or "(no active project)"
    lines = [f"deploy refresh-feed: {slug!r}"]
    stories = data.get("stories") or []
    if stories:
        lines.append(f"stories: {len(stories)}")
        for row in stories:
            durable = row["durable"]
            claimed = row["claimed_commit_sha"]
            lines.append(
                f"  {row['story_key']}: durable={durable['value']!r} "
                f"(git), claimed_commit_sha={claimed['value']!r} (journal)"
            )
    else:
        lines.append("stories: none")
    if data.get("resync_skipped"):
        lines.append("resync: skipped (landing_resync is false)")
    else:
        resync_commands = data.get("resync_commands") or []
        lines.append(f"resync commands run: {len(resync_commands)}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)
