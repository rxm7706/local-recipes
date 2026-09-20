"""``marshal homes``'s pure evaluation core (Story 1.6, FR-4/FR-8, AD-4).

Scoped to this story's "homes view" only -- the architecture's Traceability
Matrix maps "Loop homes & isolation (FR-1..FR-8)" to component ``cli/init``
specifically; a LATER, broader "Fleet visibility (FR-36..FR-40)" view is a
different epic's concern and is expected to grow this module a second
function/shape without this one needing to anticipate it (see the spec's own
Design Notes).

Takes only already-gathered facts (``HomeFacts``/``MainCheckoutFacts``,
below) -- every git/filesystem read happens at the ``cli/init.py`` boundary
first (``run_homes``), via ``ports.VcsPort``/``ports.FsPort``. This module
does no I/O, subprocess, clock, or environment-variable access, and imports
nothing from ``pyforge.marshal.adapters`` (AD-4, enforced by the AD-3/AD-4
import-linter contract).

Three checks, one shared comparison:

1. **Three-way slug agreement** (a home only): the marker's slug, the
   ``planning-artifacts`` symlink's slug, and the home's OWN branch-derived
   slug must all agree. This extends ``cli/init.py``'s own ``MRS-INIT-003``
   two-way check (marker vs. symlink only) with a third, ALWAYS-KNOWN
   reference point -- the branch a ``loop/<slug>`` worktree is checked out
   on is never absent, unlike the marker/symlink pair, which can be
   legitimately partially written mid-provisioning. Using the branch as a
   fixed pivot lets the three-way comparison collapse into two simple
   comparisons (marker-vs-branch, symlink-vs-branch): if a legitimately
   partial home has only ONE of {marker, symlink} written so far, that one
   field was written by ``marshal init`` FROM the branch's own slug, so it
   always already agrees with the pivot -- a real disagreement against the
   pivot can only arise from genuine external corruption (hand-edited
   marker/symlink, or a home's directory being repurposed), exactly the
   condition this check exists to catch (closes the blind spot named in
   deferred-work.md and this story's own spec Intent). This is a strictly
   MORE sensitive check than ``MRS-INIT-003``'s (which requires BOTH marker
   and symlink present before it will compare them to each other) -- by
   design: ``marshal homes`` is a read-only isolation *report*, so
   over-flagging a subtle divergence costs nothing but a line of output,
   unlike ``init``'s own reconcile-then-act check, which must stay
   conservative to avoid newly blocking an in-progress provision.
2. **Two-way slug agreement** (the main checkout only): the SAME comparison
   with no third leg -- the main checkout is never on a ``loop/<slug>``
   branch, so there is no branch-derived pivot to check against. This is
   exactly ``MRS-INIT-003``'s own two-way rule, applied to the main
   checkout's marker/``planning-artifacts`` symlink pair instead of a loop
   home's (see the spec's Design Notes on why this is "self-consistency,
   not a diff": there is no stored pre-run snapshot to compare against).
3. **Tier-3 realpath agreement** (a home only): a home's local Tier-3
   backlink (``_bmad-output/projects/<slug>/implementation-artifacts``) must
   resolve, BY REALPATH, to the same directory as the canonical store at
   ``repo_root/_bmad-output/projects/<slug>/implementation-artifacts`` --
   strengthening ``cli/init.py``'s own ``tier3_backlink`` step, whose
   convergence check compares the RAW (typically relative) symlink target
   string rather than a resolved realpath (that gap stays open in ``init``
   itself; out of this story's scope -- see the spec's Boundaries).

The marker/symlink comparison logic (``_slug_from_marker``,
``_slug_from_symlink_target``, the "unrecognized shape is itself evidence of
hand configuration" rule) is DUPLICATED from ``cli/init.py``, not imported:
this module sits in ``core/``, which never imports from ``cli/`` (the
Structural Seed's dependency direction runs the other way), and the spec's
own Boundaries forbid touching ``cli/init.py``'s own ``MRS-INIT-003`` check
to make it importable-from-here. This mirrors how ``cli/init.py`` itself
PORTS (never imports) logic from ``scripts/bmad-switch`` -- the established
convention in this package for reusing logic across a module boundary that
must not become an import edge.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pyforge.core.process import ProcessResult

from ..ports.harness import DeferredStory, TaskPhaseSnapshot
from .dispatch_supervisor_state import landing_journal_indicates_complete
from .identity import StoryKey, normalize, render_feed_key
from .model import Finding, Severity

_LOOP_BRANCH_PREFIX = "loop/"

DispatchPhase = Literal["building", "verifying", "chaining"]


@dataclass(frozen=True)
class HomeFacts:
    """Already-gathered state for ONE discovered ``loop/<slug>`` worktree --
    read by ``cli/init.py::run_homes`` via ``VcsPort``/``FsPort`` before this
    pure module ever sees it.

    ``tier3_local_realpath`` is ``None`` when genuinely NOTHING occupies the
    home's local Tier-3 path (never provisioned by ``marshal init``) --
    absence is not a violation, only a resolved value that disagrees with
    ``tier3_canonical_realpath`` is. ``tier3_canonical_realpath`` is always
    known: it is the home's OWN branch-derived slug's canonical store,
    independent of whether the local backlink exists.
    ``tier3_canonical_is_dir`` records whether that canonical store really
    exists as a directory -- a backlink that resolves to the RIGHT path but
    a MISSING store is a dangling link every write through it would fail on
    (review finding: previously blessed as clean; ``marshal init``'s own
    convergence check has always required ``is_dir(canonical)``).
    ``link_occupied`` is ``True`` when the ``planning-artifacts`` path
    exists but is NOT a symlink (a real directory or file squats there) --
    distinct from absence (``symlink_target`` ``None``, ``link_occupied``
    ``False``) and from a readable symlink (``symlink_target`` set); a real
    occupant means writes no longer reach the canonical project tree, the
    violation class ``MRS-HOMES-001`` exists to name (review finding:
    previously read as benign absence).
    """

    path: Path
    branch: str
    marker_text: str | None
    symlink_target: Path | None
    tier3_local_realpath: Path | None
    tier3_canonical_realpath: Path
    link_occupied: bool = False
    tier3_canonical_is_dir: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.branch, str) or not self.branch.startswith(_LOOP_BRANCH_PREFIX):
            raise ValueError(
                f"HomeFacts.branch must be a {_LOOP_BRANCH_PREFIX!r}-prefixed branch name, got {self.branch!r}"
            )


@dataclass(frozen=True)
class MainCheckoutFacts:
    """Already-gathered state for the main checkout itself -- no
    branch-derived slug (it is not on a ``loop/<slug>`` branch, so there is
    no third leg to compare) and no Tier-3 check (Story 1.5's backlink is a
    HOME-side concept only). ``link_occupied`` has the same meaning as
    ``HomeFacts.link_occupied``: the main checkout's own
    ``planning-artifacts`` path is occupied by a real (non-symlink)
    directory or file."""

    path: Path
    branch: str | None
    marker_text: str | None
    symlink_target: Path | None
    link_occupied: bool = False


@dataclass(frozen=True)
class HomesEvaluation:
    """``evaluate_homes``'s result: one row per home (``data.homes``), the
    main checkout's own row (``data.main_checkout``), and every finding --
    in ``homes`` order, then the main checkout's finding (if any) last."""

    homes: tuple[dict[str, object], ...]
    main_checkout: dict[str, object]
    findings: tuple[Finding, ...]


def _slug_from_marker(text: str | None) -> str | None:
    """Duplicated from ``cli/init.py`` -- see this module's own docstring
    for why (core/cli layering; ``init``'s own check stays untouched)."""
    if text is None:
        return None
    value = text.strip()
    return value or None


def _slug_from_symlink_target(target: Path | None) -> str | None:
    """Duplicated from ``cli/init.py``'s identically-named function: parses
    ``projects/<slug>/planning-artifacts`` -- any other shape (missing,
    absolute, wrong depth) is unrecognized, not a slug."""
    if target is None:
        return None
    parts = target.parts
    if len(parts) == 3 and parts[0] == "projects" and parts[2] == "planning-artifacts":
        return parts[1]
    return None


def _mismatch_reason(
    *,
    marker_slug: str | None,
    link_slug: str | None,
    raw_link_target: Path | None,
    branch_slug: str | None,
    link_occupied: bool = False,
) -> str | None:
    """The one comparison both checks 1 and 2 (module docstring) share.
    ``branch_slug=None`` is the main checkout's two-way rule (no third leg);
    a ``str`` is a home's three-way rule. Returns a human-readable mismatch
    description naming EVERY disagreeing pair (review finding: naming only
    the first under-reported the multi-corruption case the AC's "naming ...
    the disagreeing values" covers), or ``None`` if nothing disagrees.

    Ported from ``cli/init.py``'s own ``MRS-INIT-003`` ordering: an
    unrecognized (but present) symlink shape -- or, one step further gone, a
    real non-symlink occupant at the symlink's path (``link_occupied``,
    review finding) -- is evidence of hand configuration and is reported on
    its own, before the value-agreement checks below ever run -- mirrors
    ``init``'s own "refuse before any further write" precedence, translated
    to "report before any further comparison" for this read-only command.
    """
    if link_occupied:
        return "planning-artifacts is occupied by a real (non-symlink) directory or file where a symlink belongs"
    if raw_link_target is not None and link_slug is None:
        return f"unrecognized planning-artifacts symlink target {str(raw_link_target)!r}"
    reasons: list[str] = []
    if marker_slug is not None and link_slug is not None and marker_slug != link_slug:
        reasons.append(f"marker says {marker_slug!r} but symlink says {link_slug!r}")
    if branch_slug is not None:
        if marker_slug is not None and marker_slug != branch_slug:
            reasons.append(f"marker says {marker_slug!r} but branch says {branch_slug!r}")
        if link_slug is not None and link_slug != branch_slug:
            reasons.append(f"symlink says {link_slug!r} but branch says {branch_slug!r}")
    if reasons:
        return "; ".join(reasons)
    return None


def _tier3_mismatch_reason(
    *,
    tier3_local_realpath: Path | None,
    tier3_canonical_realpath: Path,
    tier3_canonical_is_dir: bool = True,
) -> str | None:
    """Check 3 (module docstring). ``None`` local realpath means the home's
    Tier-3 backlink was never provisioned -- absence is not a violation. A
    backlink that resolves to the RIGHT path is still a violation when the
    canonical store itself is missing (``tier3_canonical_is_dir`` false):
    every write through it would fail, and ``marshal init``'s own
    convergence check (``fs.is_dir(canonical)``) has never accepted that
    state (review finding: previously blessed as clean)."""
    if tier3_local_realpath is None:
        return None
    if tier3_local_realpath != tier3_canonical_realpath:
        return (
            f"tier-3 backlink resolves to {tier3_local_realpath} but the canonical store is {tier3_canonical_realpath}"
        )
    if not tier3_canonical_is_dir:
        return (
            f"tier-3 backlink resolves to the canonical store path "
            f"{tier3_canonical_realpath}, but that store does not exist "
            "(dangling backlink)"
        )
    return None


def _evaluate_home(home: HomeFacts) -> tuple[dict[str, object], tuple[Finding, ...]]:
    slug = home.branch.removeprefix(_LOOP_BRANCH_PREFIX)
    marker_slug = _slug_from_marker(home.marker_text)
    link_slug = _slug_from_symlink_target(home.symlink_target)

    slug_reason = _mismatch_reason(
        marker_slug=marker_slug,
        link_slug=link_slug,
        raw_link_target=home.symlink_target,
        branch_slug=slug,
        link_occupied=home.link_occupied,
    )
    tier3_reason = _tier3_mismatch_reason(
        tier3_local_realpath=home.tier3_local_realpath,
        tier3_canonical_realpath=home.tier3_canonical_realpath,
        tier3_canonical_is_dir=home.tier3_canonical_is_dir,
    )

    findings: list[Finding] = []
    if slug_reason is not None:
        findings.append(
            Finding(
                code="MRS-HOMES-001",
                severity=Severity.ERROR,
                message=f"{home.path}: {slug_reason}",
                path=str(home.path),
            )
        )
    if tier3_reason is not None:
        findings.append(
            Finding(
                code="MRS-HOMES-002",
                severity=Severity.ERROR,
                message=f"{home.path}: {tier3_reason}",
                path=str(home.path),
            )
        )

    row: dict[str, object] = {
        "path": str(home.path),
        "branch": home.branch,
        "slug": slug,
        "active_project": marker_slug if marker_slug is not None else link_slug,
        "desynced": slug_reason is not None or tier3_reason is not None,
    }
    return row, tuple(findings)


def _evaluate_main_checkout(
    main_checkout: MainCheckoutFacts,
) -> tuple[dict[str, object], tuple[Finding, ...]]:
    marker_slug = _slug_from_marker(main_checkout.marker_text)
    link_slug = _slug_from_symlink_target(main_checkout.symlink_target)

    reason = _mismatch_reason(
        marker_slug=marker_slug,
        link_slug=link_slug,
        raw_link_target=main_checkout.symlink_target,
        branch_slug=None,
        link_occupied=main_checkout.link_occupied,
    )

    findings: tuple[Finding, ...] = ()
    if reason is not None:
        findings = (
            Finding(
                code="MRS-HOMES-001",
                severity=Severity.ERROR,
                message=f"{main_checkout.path} (main checkout): {reason}",
                path=str(main_checkout.path),
            ),
        )

    row: dict[str, object] = {
        "path": str(main_checkout.path),
        "branch": main_checkout.branch,
        "slug": None,
        "active_project": marker_slug if marker_slug is not None else link_slug,
        "desynced": reason is not None,
    }
    return row, findings


def evaluate_homes(homes: Sequence[HomeFacts], main_checkout: MainCheckoutFacts) -> HomesEvaluation:
    """Evaluate every discovered home plus the main checkout (module
    docstring's three checks) and build ``data.homes``/``data.main_checkout``
    rows plus every finding, in ``homes`` order with the main checkout's
    finding (if any) last."""
    home_rows: list[dict[str, object]] = []
    findings: list[Finding] = []
    for home in homes:
        row, home_findings = _evaluate_home(home)
        home_rows.append(row)
        findings.extend(home_findings)

    main_row, main_findings = _evaluate_main_checkout(main_checkout)
    findings.extend(main_findings)

    return HomesEvaluation(homes=tuple(home_rows), main_checkout=main_row, findings=tuple(findings))


# =============================================================================
# Story 4.5: feed refresh with truth partitioned by domain (AD-33).
#
# `cli/deploy.py`'s `marshal deploy refresh-feed` builds ONE reconciled
# report from two INDEPENDENTLY-gathered sources: git-sourced repository
# facts (`VcsPort.commit_subjects` + Story 4.1's own
# `core.promotion.merged_story_keys`) and journal/harness-sourced process
# facts (`HarnessPort.run_status_snapshot`'s `RunStatusSnapshot.tasks`,
# Story 3.8's own `TaskPhaseSnapshot.commit_sha` -- this story's own
# worked example of "a journal claim about a repository fact", per the
# spec's Design Notes). `DomainField` makes "which domain sourced this
# value" a checkable TYPE, not a comment: every field
# `reconcile_feed_domains` emits is wrapped in one, tagged `"git"` or
# `"journal"`, and no field here is ever constructed from the OTHER
# domain's source. `ClaimedCommit` carries the journal's own ASSERTION
# about a repository fact (a `commit_sha`, when the harness has one) --
# informational only; the REPORTED "is this story durable" answer always
# comes from `merged_keys` (git), never from a claim's mere presence. A
# claim that disagrees with git (a non-`None` `claimed_commit_sha` for a
# story `merged_keys` does not confirm) is a registered `MRS-STATUS-001`
# `Finding` -- reported, never silently resolved by trusting either side
# (AD-33's own "a journal claim about a repository fact ... is only ever
# an input to a reconciliation finding, never a rendered value").
# =============================================================================

_CLAIMED_MISMATCH_CODE = "MRS-STATUS-001"


@dataclass(frozen=True)
class DomainField:
    """AD-33's per-field domain partition, made a checkable type rather
    than a comment: every field ``reconcile_feed_domains``'s report emits
    wraps its value in one of these. ``domain`` names which of AD-33's two
    domains the ``value`` was sourced from -- ``"git"`` (populated ONLY
    from ``VcsPort``/``core.promotion.merged_story_keys``) or
    ``"journal"`` (populated ONLY from ``core.journal``/
    ``HarnessPort.run_status_snapshot``). Construction-time validated
    (``__post_init__``), mirroring ``HomeFacts``'s own shape-guard
    convention above -- a caller cannot silently construct one with a
    third, unrecognized domain string."""

    value: object
    domain: Literal["git", "journal"]

    def __post_init__(self) -> None:
        if self.domain not in ("git", "journal"):
            raise ValueError(f"DomainField.domain must be 'git' or 'journal', got {self.domain!r}")


def domain_field_to_dict(field: DomainField) -> dict[str, object]:
    """The canonical ``DomainField`` -> plain-``dict`` conversion (mirrors
    ``core.landing.landing_rule_to_dict``'s own single-owner convention):
    ``cli/deploy.py`` calls this at the CLI/envelope boundary to turn a
    reconciled report's ``DomainField`` values into the JSON-serializable
    shape ``core.model.Envelope`` requires -- this module's own report
    stays typed with real ``DomainField`` instances up to that boundary."""
    return {"value": field.value, "domain": field.domain}


@dataclass(frozen=True)
class ClaimedCommit:
    """One journal-sourced claim about a repository fact (Story 4.5,
    AD-33): ``story_key`` is ALREADY normalized to Marshal's canonical
    ``StoryKey`` by the CLI boundary (``core.identity.normalize`` --
    bmad-loop's own native slug spelling, ``TaskPhaseSnapshot.story_key``,
    is never a Marshal ``StoryKey`` on its own; a task whose raw key does
    not normalize is skipped before reaching this dataclass, mirroring
    ``cli/deploy.py::_discover_candidates``'s own established
    skip-invalid convention). ``claimed_commit_sha`` is
    ``TaskPhaseSnapshot.commit_sha`` verbatim -- ``None`` means the
    harness has no opinion for this story (no claim to reconcile), never
    "git disagrees". ``phase`` is ``TaskPhaseSnapshot.phase`` verbatim
    (``""`` when the caller has no phase to attach, e.g. a hand-built
    ``ClaimedCommit`` in a test) -- used ONLY by
    ``reconcile_feed_domains``'s own duplicate-``story_key`` precedence
    rule below (code review, 2026-08-06, P3, Edge Case Hunter); never
    itself rendered into the report."""

    story_key: StoryKey
    claimed_commit_sha: str | None
    phase: str = ""


@dataclass(frozen=True)
class FeedRefreshReport:
    """``reconcile_feed_domains``'s result: one row per story key present
    in EITHER ``merged_keys`` or ``claims`` (deduplicated, sorted by
    ``StoryKey`` for a deterministic report over a deterministic input --
    the property the story's own provable-no-op requirement depends on),
    plus every reconciliation ``Finding`` (a ``claimed_commit_sha`` whose
    story is NOT in ``merged_keys`` -- AD-33's own named mismatch case).
    Each row is ``{"story_key": str, "durable": DomainField, "claimed_commit_sha": DomainField}``."""

    stories: tuple[dict[str, object], ...]
    findings: tuple[Finding, ...]


# Mirrors `bmad_loop.model.Phase`'s own declaration order verbatim --
# DUPLICATED, not imported (this module sits in `core/`, which AD-3/AD-4
# forbid from ever importing `bmad_loop`; see this module's own docstring
# above for the identical "ported, not imported" convention already used
# for `_slug_from_marker`/`_slug_from_symlink_target`). Used ONLY as a
# same-story_key tie-break (below) when a run's `state.json` carries more
# than one `TaskPhaseSnapshot` for the same story (a real shape: separate
# dev/review/done-phase reads of the same task) -- a later lifecycle phase
# wins over an earlier one, never accidental `dict`/iteration-order luck
# (code review, 2026-08-06, P3, Edge Case Hunter). A phase string this
# tuple does not recognize (e.g. `""`, a hand-built `ClaimedCommit` in a
# test with no phase) ranks LOWEST, via `.get(..., -1)` below.
_PHASE_PRECEDENCE = (
    "pending",
    "dev-running",
    "dev-verify",
    "review-running",
    "review-verify",
    "committing",
    "triage-running",
    "triage-verify",
    "done",
    "deferred",
    "escalated",
)
_PHASE_RANK = {phase: rank for rank, phase in enumerate(_PHASE_PRECEDENCE)}


def _select_claim(claims: tuple[ClaimedCommit, ...]) -> ClaimedCommit:
    """The one ``ClaimedCommit`` that wins when more than one
    ``TaskPhaseSnapshot`` shares a story key (code review, 2026-08-06, P3):
    a claim with a non-``None`` ``claimed_commit_sha`` outranks one with
    ``None`` (AD-33's own claim carries no opinion when there is nothing to
    claim); among multiple non-``None`` entries, the one attached to the
    LATER lifecycle ``phase`` (``_PHASE_RANK`` above) wins. Ties (identical
    sha-presence AND identical/unrecognized phase rank) resolve to the
    FIRST entry in ``claims``'s own iteration order -- ``state.json``'s own
    stable ``tasks`` order, so the result is deterministic for a given,
    unchanged state (the provable-no-op property), never accidental ``dict``
    insertion-order luck."""
    return max(
        claims,
        key=lambda claim: (
            claim.claimed_commit_sha is not None,
            _PHASE_RANK.get(claim.phase, -1),
        ),
    )


def reconcile_feed_domains(
    merged_keys: frozenset[StoryKey],
    claims: tuple[ClaimedCommit, ...],
) -> FeedRefreshReport:
    """The pure reconciliation core of ``marshal deploy refresh-feed``
    (AD-33): for every story key known to either source, tags the git
    answer (``durable``, from ``merged_keys``) and the journal's own claim
    (``claimed_commit_sha``, from ``claims``) with their respective
    ``DomainField`` domain -- never cross-populated. A story whose journal
    claims a landed commit (``claimed_commit_sha is not None``) but that
    ``merged_keys`` does not confirm reports one ``MRS-STATUS-001`` WARN
    finding (the harness believes a commit landed; git disagrees) --
    reported, never used to override ``durable``, which always comes from
    ``merged_keys`` alone. ``claimed_commit_sha is None`` (the harness has
    no opinion) never produces a finding: git's own answer stands alone,
    per the story's own I/O matrix. When ``claims`` carries MORE THAN ONE
    entry for the same ``story_key`` (code review, 2026-08-06, P3, Edge
    Case Hunter -- a realistic shape: a story's own dev/review/done-phase
    snapshots, each potentially carrying a different ``commit_sha``),
    ``_select_claim`` above picks the one that wins by an explicit,
    deterministic precedence, never by which happened to be LAST in a
    dict-comprehension's own iteration order. Pure: no I/O, no ``VcsPort``/
    ``HarnessPort`` -- both arguments are the caller's already-gathered
    facts."""
    claims_by_key: dict[StoryKey, list[ClaimedCommit]] = {}
    for claim in claims:
        claims_by_key.setdefault(claim.story_key, []).append(claim)
    claim_by_key: dict[StoryKey, ClaimedCommit] = {
        key: _select_claim(tuple(group)) for key, group in claims_by_key.items()
    }
    all_keys = sorted(merged_keys | set(claim_by_key))

    stories: list[dict[str, object]] = []
    findings: list[Finding] = []
    for key in all_keys:
        durable = key in merged_keys
        claim = claim_by_key.get(key)
        claimed_sha = claim.claimed_commit_sha if claim is not None else None
        stories.append(
            {
                "story_key": str(key),
                "durable": DomainField(value=durable, domain="git"),
                "claimed_commit_sha": DomainField(value=claimed_sha, domain="journal"),
            }
        )
        if claimed_sha is not None and not durable:
            findings.append(
                Finding(
                    code=_CLAIMED_MISMATCH_CODE,
                    severity=Severity.WARN,
                    message=(
                        f"story {key}: the run harness recorded commit "
                        f"{claimed_sha!r} for this story, but git does not "
                        "confirm it as merged -- reported only; the "
                        "durable answer stays git's own, per AD-33"
                    ),
                )
            )
    return FeedRefreshReport(stories=tuple(stories), findings=tuple(findings))


# --- landing_resync_commands execution classification (AD-17) --------------

# Mirrors `cli/gate.py::classify_outcome`'s shape for `verify_commands`
# exactly (`result is None` means the command never ran at all), but with
# THIS story's own MRS-DEPLOY-019/020 codes -- a `landing_resync_commands`
# entry is a distinct policy-declared allowlist (Story 4.7's own
# `landing_resync` toggle governs it), never `verify_commands`'s own
# `MRS-GATE-001`/`002`/`003`, which `core.gate.classify_outcome` hardcodes
# for its own caller.
_RESYNC_LAUNCH_FAILURE_CODE = "MRS-DEPLOY-019"
_RESYNC_NONZERO_EXIT_CODE = "MRS-DEPLOY-020"


def classify_resync_outcome(
    command: str,
    result: ProcessResult | None,
    *,
    failure_reason: str | None = None,
) -> tuple[dict[str, object], Finding | None]:
    """Classify one ``landing_resync_commands`` entry's already-obtained
    outcome. ``result is None`` means the command never ran at all (it
    could not be ``shlex.split``, used bare shell syntax ``ProcessPort``
    would never honor, or ``ProcessPort.run`` itself raised) --
    ``failure_reason`` is then required and the report carries
    ``resolvable: False``. A non-``None`` ``result`` classifies via its
    ``returncode``: ``0`` is a pass (no finding); non-zero registers one
    ``MRS-DEPLOY-020`` finding, naming a signal-kill distinctly from an
    ordinary non-zero exit (mirrors ``classify_outcome``'s own identical
    signal-vs-exit-code framing)."""
    if result is None:
        report: dict[str, object] = {
            "command": command,
            "resolvable": False,
            "returncode": None,
        }
        return report, Finding(
            code=_RESYNC_LAUNCH_FAILURE_CODE,
            severity=Severity.ERROR,
            message=failure_reason or f"landing_resync_commands entry {command!r} could not be run",
        )

    if result.returncode != 0:
        outcome = (
            f"was terminated by signal {-result.returncode}" if result.returncode < 0 else f"exited {result.returncode}"
        )
        return (
            {
                "command": command,
                "resolvable": True,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
            Finding(
                code=_RESYNC_NONZERO_EXIT_CODE,
                severity=Severity.ERROR,
                message=f"landing_resync_commands entry {command!r} {outcome}",
            ),
        )

    return (
        {
            "command": command,
            "resolvable": True,
            "returncode": 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
        None,
    )


# =============================================================================
# Story 5.1: fleet-wide runtime state (``marshal status``, FR-36/AD-5) -- one
# row per loop home, derived ENTIRELY from journals/run state, never a
# hand-maintained file (this story's own Intent: the exact class of gap that
# let Epic 4's own tracked ledger silently show 4.1-4.7 as ``review`` for
# hours after they'd merged). ``cli/status.py`` gathers every fact via
# ``VcsPort``/``FsPort``/``HarnessPort``/``ProcessPort``/``ClockPort`` first
# -- this module stays pure (AD-4): no I/O, subprocess, or clock read.
# =============================================================================

_MALFORMED_JOURNAL_CODE = "MRS-STATUS-002"
_HARNESS_NATIVE_TERMINAL_CODE = "MRS-STATUS-013"

#: A run whose journal read fine but whose harness snapshot is gone -- the
#: retired-run shape. WARN, never a hard failure, and never `unknown`.
_RETIRED_RUN_STATE_CODE = "MRS-STATUS-012"

_ESCALATION_PAUSED_STAGE = "escalation"

# The exact literal `supervisor/durability.py::_DONE_PHASE` already uses --
# reused, not re-spelled, mirroring `cli/retire.py`'s own identical
# precedent for the same reason (core/ never imports supervisor/, the
# reverse of that package's own import direction).
_DONE_PHASE = "done"
_DEFERRED_PHASE = "deferred"
# Code review (2026-08-07, Edge Case Hunter): `"escalated"` was missing --
# bmad-loop's own authoritative terminal-phase set (`bmad_loop.model.
# TERMINAL_PHASES`) is `{DONE, DEFERRED, ESCALATED}`, not just the first
# two. A task legitimately sitting at `phase="escalated"` (a real,
# persisted value `TaskPhaseSnapshot.phase` can carry) was previously
# treated as still IN-FLIGHT: `derive_home_state` would report `"running"`
# for a home whose only non-terminal task was actually stuck awaiting an
# operator's escalation decision, and `_current_story_key` would report
# that stale escalated story as the "current" one, silently hiding
# whatever task is actually running later in the tuple -- precisely the
# "stuck work reported as healthy" failure this command exists to prevent.
_ESCALATED_PHASE = "escalated"
# Story 25.5 (0.11 status vocabulary, CAP-5): bmad-loop 0.11.0's fourth
# terminal phase -- the story's agent-doable work is finished and COMMITTED,
# but its acceptance criteria include external actions only a human can
# perform; the run moves on rather than halting (`bmad_loop.model.Phase.
# AWAITING_OPERATOR`, deliberately NOT a pause upstream). Mirrored verbatim,
# never re-spelled; `tests/unit/test_bmad_loop_status_vocabulary.py` pins
# this literal against the installed package.
_AWAITING_OPERATOR_PHASE = "awaiting-operator"
# Mirrors `bmad_loop.model.TERMINAL_PHASES` EXACTLY ({done, deferred,
# escalated, awaiting-operator}). Before Story 25.5 `awaiting-operator` was
# missing, so a parked task read as still IN-FLIGHT: `derive_home_state`
# reported `"running"` for a home whose only non-terminal-looking task was
# deliberately parked awaiting `bmad-loop confirm`, and
# `scripts/loop_stall_check.py` read the same run as a 15-minute stall
# (DW-BL011-1) -- the same class of mislabel the 2026-08-07 `"escalated"`
# fix above closed.
_TERMINAL_TASK_PHASES = frozenset({_DONE_PHASE, _DEFERRED_PHASE, _ESCALATED_PHASE, _AWAITING_OPERATOR_PHASE})

#: The ONE spelling of the parked state's human remedy suffix (Story 25.5):
#: every text render projects the machine token ``"awaiting-operator"`` as
#: ``awaiting-operator (run bmad-loop confirm)`` -- the machine field keeps
#: the bare token; this suffix is the human projection, never a second
#: state value.
AWAITING_OPERATOR_REMEDY = "run bmad-loop confirm"

#: The closed 6-value state vocabulary: the 4 "healthy" states PLUS
#: ``"unsupervised"`` (never conflated with them -- a dead supervisor is
#: never reported as any of the healthy four) PLUS ``"awaiting-operator"``
#: (Story 25.5: a parked run -- >=1 task at ``awaiting-operator`` and no
#: task in a non-terminal phase -- is deliberately still, completed via
#: ``bmad-loop confirm``; never "stalled"/"dead"/"unsupervised"/"running").
FLEET_STATES = (
    "idle",
    "running",
    "paused-on-escalation",
    "stopped",
    "unsupervised",
    "awaiting-operator",
)


def derive_home_state(
    *,
    finished: bool,
    paused_stage: str | None,
    tasks: tuple[TaskPhaseSnapshot, ...],
    supervisor_alive: bool | None,
    engine_alive: bool | None = None,
) -> str:
    """The pure state-derivation core of ``marshal status`` (Story 5.1,
    FR-36/AD-5): one of ``FLEET_STATES`` above, from a run's own
    ``HarnessPort.run_status_snapshot`` fields plus a supervisor liveness
    probe -- never engaged when the caller has already determined a home
    has no run at all (``cli/status.py`` reports ``"idle"`` directly in
    that case, without ever calling this function; see this module's own
    ``build_fleet_row``).

    **Supervisor liveness overrides every other derived state** (the
    spec's own Design Notes) -- but ONLY while the run has not itself
    finished: a ``finished`` run's own supervisor sidecar naturally exits
    once its watched harness process does, so checking liveness against an
    already-``finished`` run would misreport every ordinary completed run
    as ``"unsupervised"``. ``supervisor_alive is False`` and ``not
    finished`` together are the trigger -- exactly the spec's own I/O
    matrix row ("a home whose supervisor pid is dead, run not finished")
    -- UNLESS ``engine_alive`` softens it (Story 5.8, below).
    ``supervisor_alive is None`` (liveness could not be probed, e.g. no
    pid was ever recovered) never triggers this override on its own -- a
    caller with no pid to check ``cli/status.py`` degrades to the
    ``"unknown"``-shaped row via ``journal_unreadable`` instead of ever
    reaching this function with a real pid absent.

    **``engine_alive`` is a one-directional softening signal (Story 5.8,
    FR-36/AD-5)**: a bare ``bmad-loop resume`` that never re-spawns a
    supervisor sidecar (or a crashed/``--foreground`` supervisor) leaves
    ``supervisor_alive is False`` on a run whose engine is still working
    -- the 2026-08-11 incident, 5 live stations misreported
    ``"unsupervised"`` for a full session because the branch above fired
    unconditionally. Only ``engine_alive is True`` (a CONFIRMED-alive
    probe of the engine's own already-recovered pid) may soften the
    branch above and fall through to the normal derivation below;
    ``False`` (confirmed dead) or ``None`` (unprobed/unknown) still
    return ``"unsupervised"`` -- mirrors this module's own repeated
    "unproven is reported as the cautious state, never silently
    softened" discipline (the same precedent ``supervisor_alive is None``
    and ``is_run_live``'s own ``journal_unreadable`` handling already
    establish elsewhere in this file). A caller that never passes
    ``engine_alive`` (the default, ``None``) reproduces today's exact
    behavior unchanged.

    **A parked run reports ``"awaiting-operator"`` (Story 25.5, CAP-5,
    absorbing DW-BL011-1).** "Parked" = at least one task at bmad-loop
    0.11's own ``Phase.AWAITING_OPERATOR`` AND no task in a non-terminal
    phase -- a run actively driving another story stays ``"running"`` (a
    park "must never block the stories behind it", bmad-loop's own design).
    Precedence: escalation-pause > parked > finished/unsupervised. The
    escalation pause outranks the park because it is run-halting by design
    (the park never is); but once nothing is active, the confirm is the
    truthful next action even for a ``finished`` run (the park's commit IS
    real -- a re-spin is not the remedy, ``bmad-loop confirm`` is) or a
    supervisor-dead one (a parked run's processes naturally wind down while
    the human actions stay owed -- reporting it ``"unsupervised"``/dead is
    exactly the DW's mislabel).

    Ordering below otherwise matches the spec's own I/O matrix exactly:
    ``finished`` -> ``"stopped"``; ``paused_stage == "escalation"`` ->
    ``"paused-on-escalation"``; a task whose ``phase`` is outside
    bmad-loop's own terminal set -> ``"running"`` (mirrors
    ``cli/retire.py``'s own reuse of the identical ``_DONE_PHASE``
    literal); otherwise -> ``"idle"`` (a run that exists but has no
    in-flight task right now -- e.g. between stories -- reads the same as
    "nothing to report" a caller with no run at all would report)."""
    has_active = any(task.phase not in _TERMINAL_TASK_PHASES for task in tasks)
    parked = not has_active and any(task.phase == _AWAITING_OPERATOR_PHASE for task in tasks)
    if parked:
        if paused_stage == _ESCALATION_PAUSED_STAGE:
            return "paused-on-escalation"
        return "awaiting-operator"
    if not finished and supervisor_alive is False and engine_alive is not True:
        return "unsupervised"
    if finished:
        return "stopped"
    if paused_stage == _ESCALATION_PAUSED_STAGE:
        return "paused-on-escalation"
    if has_active:
        return "running"
    return "idle"


def _current_story_key(tasks: tuple[TaskPhaseSnapshot, ...]) -> str | None:
    """ "Current story" (the spec's own Always bullet): the ``story_key`` of
    the FIRST ``TaskPhaseSnapshot`` whose ``phase`` is outside bmad-loop's
    own terminal set. Story 25.5: when NOTHING is active, falls back to the
    FIRST ``awaiting-operator`` task (the story the operator owes a
    ``bmad-loop confirm`` for) -- the fallback engages only after the full
    active scan, so a parked story can never hide an active one. ``None``
    when every task is terminal with none parked, or there are none at
    all."""
    for task in tasks:
        if task.phase not in _TERMINAL_TASK_PHASES:
            return task.story_key
    for task in tasks:
        if task.phase == _AWAITING_OPERATOR_PHASE:
            return task.story_key
    return None


@dataclass(frozen=True)
class FleetHomeFacts:
    """Already-gathered facts for ONE discovered ``loop/<slug>`` worktree's
    fleet-status row (Story 5.1) -- read by ``cli/status.py`` via
    ``VcsPort``/``FsPort``/``HarnessPort``/``ProcessPort``/``ClockPort``
    before this pure module ever sees them (AD-4).

    ``has_run`` is ``False`` when no Marshal run directory exists yet for
    this project at all (``cli/spin.py``'s own ``_latest_run_dir`` found
    nothing) -- the spec's own "a home with no run yet" row: every other
    field is then a placeholder, and neither ``derive_home_state`` nor
    ``journal_unreadable`` is ever engaged.

    ``journal_unreadable`` is ``True`` when a run WAS found but its own
    journal (or bmad-loop's own ``state.json``, via
    ``HarnessPort.run_status_snapshot``) could not be read far enough to
    recover a supervisor pid and a live snapshot -- the spec's own "a
    home whose journal is malformed/unreadable" row: this row's ``state``
    reports as ``"unknown"``, with one ``MRS-STATUS-002`` WARN naming the
    home, never a hard failure for the rest of the sweep.

    ``finished``/``paused_stage``/``tasks`` mirror
    ``RunStatusSnapshot``'s own same-named fields verbatim (only
    meaningful when ``has_run`` is ``True`` and ``journal_unreadable`` is
    ``False``). ``supervisor_alive`` is
    ``ProcessPort.is_alive(supervisor_pid)`` already resolved to a
    ``bool`` by the caller -- never ``None`` once ``journal_unreadable``
    is ``False`` (a pid was, by construction, successfully recovered in
    that case). ``elapsed_seconds`` is the caller's own
    ``ClockPort.now()``-minus-launch-timestamp computation, or ``None``
    when unavailable. ``budget_consumed`` is the supervisor's own last
    JOURNALED observed quantity (Story 3.6's own ``"budget-usage"``
    observation kind) -- never computed live (the spec's own Design
    Notes: NFR-14 forbids a live harness query per home), ``None`` when no
    budget-relevant entry has been journaled yet for this run.

    ``engine_alive`` (Story 5.8, FR-36/AD-5) is
    ``ProcessPort.is_alive(launch_pid)`` -- the SAME probe already used
    for ``supervisor_alive`` above, applied to the DETACHED HARNESS
    process's own already-recovered pid (``_RunJournalFacts.launch_pid``,
    journaled by every ``run-launch``/``run-resume`` outcome entry)
    rather than the supervisor sidecar's. Also never ``None`` once
    ``journal_unreadable`` is ``False`` (the launch pid is, by
    construction, always recovered by then). This is the fallback signal
    ``derive_home_state`` consults to tell "supervisor sidecar crashed,
    engine still working" (soften) apart from "the whole run is
    genuinely dead" (still ``"unsupervised"``) -- see that function's own
    docstring for the one-directional softening rule."""

    slug: str
    branch: str
    has_run: bool = False
    journal_unreadable: bool = False
    #: The run's own journal READ FINE, but bmad-loop's harness snapshot
    #: for it could not be resolved -- the shape a RETIRED or cleaned run
    #: leaves behind (`.bmad-loop/runs/.retired-*`), where `latest_run_dir`
    #: still selects an entry whose `state.json` is gone. Distinct from
    #: `journal_unreadable` on purpose: there, nothing could be recovered
    #: and `unknown` is the honest answer; here the run is simply OVER and
    #: its evidence was cleaned up, so the home is free and reports `idle`.
    #: Conflating the two left pyforge-steward reading `unknown` from
    #: 2026-08-22 until 2026-09-08 -- and a station stuck at `unknown` is
    #: one whose liveness callers cannot assert, the precondition for the
    #: duplicate-dispatch class recorded on 2026-08-27 (DW-STATUS-2026-09-08-1).
    run_state_retired: bool = False
    #: A run bmad-loop started directly (no recoverable marshal launch pid),
    #: classified terminal via ``HarnessPort.run_terminal_verdict`` (Story
    #: 5.11, FR-196). Distinct from ``journal_unreadable`` (nothing could be
    #: recovered) and ``run_state_retired`` (marshal journal read fine but
    #: the harness snapshot for a resolved id is gone).
    harness_native_terminal: bool = False
    finished: bool = False
    paused_stage: str | None = None
    tasks: tuple[TaskPhaseSnapshot, ...] = ()
    supervisor_alive: bool | None = None
    engine_alive: bool | None = None
    elapsed_seconds: float | None = None
    budget_consumed: int | float | None = None
    # Story 28.4 (CAP-7): Add per-layer savings telemetry alongside budget consumption
    layer_savings: dict[str, object] = field(default_factory=dict)
    # Story 28.10 (CAP-11): advisory dollar estimates when catalog declared
    budget_consumed_usd: float | None = None
    layer_savings_usd: dict[str, float] = field(default_factory=dict)
    # Story 5.3 (FR-38): `RunStatusSnapshot`'s own already-shipped
    # `paused_reason`/`escalated_spec_file`/`escalated_task_phase` fields,
    # threaded through verbatim -- `_gather_home_facts` already reads
    # `snapshot` for Story 5.1's own fields; this story just adds these
    # three, never a second/different read of the same snapshot.
    paused_reason: str | None = None
    escalated_spec_file: str | None = None
    escalated_task_phase: str | None = None
    # Story 25.5 (CAP-5): `RunStatusSnapshot.escalated_preserve_ref`,
    # threaded through verbatim exactly like the three Story-5.3 fields
    # above -- the escalated story's own recovery pointer (an
    # `attempt-preserve/*` git ref, unredacted like `commit_sha`), `None`
    # when no ref was parked or the snapshot predates 0.10.
    escalated_preserve_ref: str | None = None
    # Story 5.5 (FR-62/AD-48): the caller's own already-matched finding from
    # `scripts/unpushed_work_check.py --json --branches-only` (`cli/status.py``
    # runs that detector ONCE per sweep and matches by `ref == branch`) --
    # `{"files": int, "stat": str, "remedy": str}` verbatim, never
    # re-derived. `None` means either no matching finding exists for this
    # home's branch, or the detector could not be consulted this run
    # (indistinguishable at this layer -- `build_fleet_row` only surfaces a
    # non-``None`` value for the fully-resolved row shape below, mirroring
    # `budget_consumed`'s own "hardcoded None in a degraded row" precedent;
    # ``cli/status.py`` is the one that knows which case it is and emits the
    # matching WARN finding).
    unpushed_work: dict[str, object] | None = None
    # Story 4.14 (FR-176): every `.bmad-loop/runs/*/failed/*/changes.patch`
    # `cli/status.py` found under this home (a bare `Path.glob`, gathered
    # once per home regardless of journal readability), each already
    # classified as `{"story_key": str, "run_id": str, "path": str,
    # "size_bytes": int, "done": bool | None, "confidence": str}`. Unlike
    # `unpushed_work`, this field is never hardcoded away in a degraded row
    # (see `build_fleet_row`'s own comment for `unpushed_work` above, which
    # this mirrors): it is an INDEPENDENT filesystem signal, gathered from
    # this home's own directory tree rather than from an external detector
    # that could be missing, so `()` is the ordinary clean answer and there
    # is nothing for a degraded row to suppress.
    #
    # `()` is NOT, however, unconditionally proof that the tree was read
    # (review finding, 2026-08-10, pass 3 -- this comment previously claimed
    # this field had "no could-not-be-consulted case of its own", which the
    # caller contradicts): `cli/status.py::_gather_failed_patches` degrades
    # an unreadable `.bmad-loop` tree to `()` deliberately, following
    # `cli/spin.py::_latest_run_dir`'s own precedent, and `Path.glob` itself
    # silently yields a PARTIAL result when an intermediate directory is
    # unreadable (verified against CPython 3.14). Both are recorded, known
    # limits of this signal, deferred rather than reported; do not read `()`
    # as "the filesystem was definitely consulted and definitely clean".
    #
    # `confidence` is this module's OWN `CONFIDENCE_CONFIRMED`/
    # `CONFIDENCE_UNCONFIRMED` (below), never a third vocabulary: a
    # `done: true` entry is `CONFIDENCE_CONFIRMED` (a POSITIVE
    # `core.promotion.merged_story_keys` match is the stronger direction),
    # while both `done: false` and `done: null` are
    # `CONFIDENCE_UNCONFIRMED` -- an ABSENCE of a match proves nothing (the
    # squash-merge blind spot that constant block documents in full,
    # re-confirmed live on 2026-08-10 before Story 20.10 widened the
    # classifier via ``pyforge.core.landing_evidence``).
    # `reconcile_ledger_vs_git` below already tags the identical evidence
    # source exactly this way.
    #
    # `CONFIDENCE_CONFIRMED` here is NOT unqualified proof, and this field
    # must not be read as such (review finding, 2026-08-10, pass 4 -- the
    # same overclaim-correction this docstring's paragraph above already
    # applied to `()`). The POSITIVE direction previously carried a verified
    # cross-project contamination of its own (`extract_story_key_from_
    # github_merge_subject` took no `project_slug`, so one station's
    # `<epic>.<seq>` could match on another station's PR-merge subject --
    # measured 2026-08-10, `pyforge-mason`/`-doctor`/`-scribe` each resolved
    # ~30 keys, most belonging to other stations) -- CLOSED 2026-08-15
    # (`extract_story_key_from_github_merge_subject` now requires and scopes
    # on `project_slug`, the same live-collision reproduction that closed
    # it, see that function's own docstring). `CONFIDENCE_CONFIRMED` is
    # still not unqualified proof for OTHER reasons (the squash-merge blind
    # spot this docstring's paragraph above documents remains real; recovery
    # and ``land/`` shapes are now recognized via
    # ``pyforge.core.landing_evidence`` as of Story 20.10), but cross-project
    # misattribution is no longer one of them. Both directions of this signal
    # are best-effort; only their failure modes differ (noise vs. silence).
    failed_patches: tuple[dict[str, object], ...] = ()
    # Story 22.1 (factory dispatch, FR-193 CAP-1): an in-flight single-story
    # session launched via ``marshal factory dispatch``, gathered from the
    # canonical Tier-3 ``dispatch-runs/`` store (physical path, never the loop
    # home symlink). ``dispatch_engine_alive`` is
    # ``ProcessPort.is_alive(session_pid)``; when ``True`` and
    # ``dispatch_story`` is set, ``build_fleet_row`` surfaces the station
    # as ``"running"`` even when no bmad-loop run is active.
    dispatch_story: str | None = None
    dispatch_engine_alive: bool = False
    dispatch_elapsed_seconds: float | None = None
    dispatch_run_id: str | None = None
    # Story 22.2 (factory dispatch completion, FR-193 CAP-2): git+process
    # verdict for the latest dispatch run — ``live`` keeps the station
    # surfaced as running even when the session process is dead but git
    # facts show progress (zombie refusal case).
    dispatch_completion_verdict: str | None = None
    # Story 22.3 (factory dispatch verification, FR-193 CAP-3): independent
    # gate verdict before landing — ``verified`` or ``refused`` with named
    # failed gate; self-report is never the verdict input.
    dispatch_verification_verdict: str | None = None
    dispatch_verification_failed_gate: str | None = None
    # Story 28.15 (CAP-17): the station's own `warn`-mode scope-violation
    # advisories from its latest dispatch verification -- visible here (not
    # journal-only), matching AC4.
    dispatch_verification_scope_advisories: tuple[dict[str, object], ...] = ()
    # Story 53.2 review (I1): `execute_dispatch_land`'s envelope findings
    # (MRS-DISP-047/048) -- visible here too, matching the scope-advisories
    # precedent immediately above.
    dispatch_landing_findings: tuple[dict[str, object], ...] = ()
    # Story 22.6 (dispatch operator survival, FR-193 CAP-6): supervision and
    # per-story timing / preserve refs from the dispatch journal alone.
    dispatch_supervisor_alive: bool = False
    dispatch_story_started_at: str | None = None
    dispatch_story_ended_at: str | None = None
    dispatch_baseline_revision: str | None = None
    dispatch_final_revision: str | None = None
    dispatch_preserve_ref: str | None = None
    dispatch_landing_verdict: str | None = None
    # Story 28.16 (CAP-3): parallel wave membership visible in fleet status.
    dispatch_wave_id: str | None = None
    dispatch_in_flight_stories: tuple[str, ...] = ()
    # Story 28.19 (CAP-2): fleet-drain ``MRS-DISP-005`` with remaining backlog
    # must never read as ``idle`` -- the expected tracked spec glob is the
    # operator remedy, never an auto-authored stub.
    missing_spec_escalation_story: str | None = None
    missing_spec_escalation_glob: str | None = None
    # Story 28.23 (CAP-6): unpushed ``dispatch/<slug>/<story>`` (or legacy
    # ``marshal/<story>``) after a terminal verify-fail with a dead tail --
    # the stranded-work signal fleet-picture ATTENTION names alongside the
    # overlay fix in ``derive_dispatch_phase``.
    dispatch_stranded_work: dict[str, object] | None = None
    # Story 28.24 (CAP-7): supervisor finalize shell failed — operator must
    # commit/push/verify in the named worktree.
    finalize_escalation_story: str | None = None
    finalize_escalation_worktree: str | None = None


def _dispatch_tail_still_live(facts: FleetHomeFacts) -> bool:
    """True while a dispatch supervisor or harness session is still attached."""
    return facts.dispatch_supervisor_alive or facts.dispatch_engine_alive


def derive_dispatch_phase(facts: FleetHomeFacts) -> DispatchPhase | None:
    """Factory-dispatch phase for ``marshal status`` / ``fleet-picture``.

    ``building`` — harness session alive.
    ``verifying`` — session dead; verify/land/completion tail still running.
    ``chaining`` — story shipped (land journal or completion) while the
    dispatch supervisor or harness is still winding down / waiting for the
    campaign to hand off — NOT an indefinite post-merge label once both are
    dead (the mason/scribe Aug-28/31 stale-tail incident).
    """
    if not facts.dispatch_story:
        return None
    if facts.dispatch_completion_verdict == "completed":
        return "chaining" if _dispatch_tail_still_live(facts) else None
    if facts.dispatch_completion_verdict in (
        "failed",
        "stopped_externally",
        "blocked",
    ):
        return "verifying" if _dispatch_tail_still_live(facts) else None
    if landing_journal_indicates_complete(facts.dispatch_landing_verdict):
        return "chaining" if _dispatch_tail_still_live(facts) else None
    if facts.dispatch_engine_alive:
        return "building"
    return "verifying"


def _dispatch_terminal_dead_tail(facts: FleetHomeFacts) -> bool:
    """True when factory dispatch ended in terminal failure with no live tail."""
    if not facts.dispatch_story:
        return False
    if facts.dispatch_completion_verdict not in (
        "failed",
        "stopped_externally",
        "blocked",
    ):
        return False
    return derive_dispatch_phase(facts) is None


def derive_dispatch_stranded_work(
    facts: FleetHomeFacts,
    *,
    unpushed_by_ref: dict[str, dict[str, object]] | None,
) -> dict[str, object] | None:
    """Unpushed dispatch branch for a terminal dead-tail verify-fail (28.23).

    ``unpushed_by_ref`` is the fleet-wide map from
    ``scripts/unpushed_work_check.py --json --branches-only`` (``None`` when
    the detector could not run -- indistinguishable from clean at this layer).
    Open unmerged PRs are named separately by ``fleet_picture.py``'s ATTENTION
    block (one ``gh`` query for the whole report).
    """
    if not _dispatch_terminal_dead_tail(facts):
        return None
    if unpushed_by_ref is None:
        return None
    from . import dispatch as dispatch_core

    story_key = facts.dispatch_story
    if not story_key:
        return None
    candidates = (
        dispatch_core.dispatch_worktree_branch(facts.slug, story_key),
        dispatch_core.legacy_dispatch_worktree_branch(story_key),
    )
    for ref in candidates:
        finding = unpushed_by_ref.get(ref)
        if finding is None:
            continue
        return {
            "kind": "unpushed-branch",
            "ref": ref,
            "story": story_key,
            "files": finding.get("files"),
            "stat": finding.get("stat"),
            "remedy": finding.get("remedy") or f"git push origin {ref}",
        }
    return None


def _dispatch_overlay_active(facts: FleetHomeFacts) -> bool:
    """True while factory dispatch has an observable phase for this home."""
    return derive_dispatch_phase(facts) is not None


def _apply_missing_spec_escalation(row: dict[str, object], facts: FleetHomeFacts) -> dict[str, object]:
    """Story 28.19: missing-spec drain refuse surfaces as ``awaiting-operator``."""
    story = facts.missing_spec_escalation_story
    spec_glob = facts.missing_spec_escalation_glob
    if not story or not spec_glob:
        return row
    if _dispatch_overlay_active(facts):
        return row
    state = row.get("state")
    if state not in ("idle", "stopped", "unsupervised", "unknown"):
        return row
    remedy = f"missing tracked spec: author {spec_glob}"
    patched = {
        **row,
        "state": "awaiting-operator",
        "current_story": story,
        "awaiting_operator_remedy": remedy,
        "missing_spec_escalation_glob": spec_glob,
    }
    return patched


def _apply_finalize_escalation(row: dict[str, object], facts: FleetHomeFacts) -> dict[str, object]:
    """Story 28.24: supervisor shell failure surfaces as ``awaiting-operator``."""
    story = facts.finalize_escalation_story
    worktree = facts.finalize_escalation_worktree
    if not story or not worktree:
        return row
    if _dispatch_overlay_active(facts):
        return row
    state = row.get("state")
    if state not in ("idle", "stopped", "unsupervised", "unknown"):
        return row
    remedy = f"supervisor finalize failed: commit/push/verify in {worktree}"
    return {
        **row,
        "state": "awaiting-operator",
        "current_story": story,
        "awaiting_operator_remedy": remedy,
        "finalize_escalation_worktree": worktree,
    }


def _apply_dispatch_overlay(row: dict[str, object], facts: FleetHomeFacts) -> dict[str, object]:
    """Story 22.1/22.2: when a dispatch session is live, surface it in fleet status."""
    phase = derive_dispatch_phase(facts)
    if phase is not None:
        row = {**row, "dispatch_phase": phase}
    if not facts.dispatch_story:
        return row
    dispatch_live = _dispatch_overlay_active(facts)
    if not dispatch_live:
        # Story 28.23 (CAP-6): a terminal dead tail must still publish
        # completion + stranded-work facts for fleet-picture ATTENTION without
        # re-labeling the home as running/STUCK.
        row = _merge_dispatch_row_fields(row, facts)
        if _dispatch_terminal_dead_tail(facts):
            row = {**row, "current_story": facts.dispatch_story}
        return row
    if row.get("state") in ("running", "paused-on-escalation", "awaiting-operator"):
        patched = dict(row)
        patched["current_story"] = facts.dispatch_story
        if facts.dispatch_elapsed_seconds is not None:
            patched["elapsed_seconds"] = facts.dispatch_elapsed_seconds
        return _merge_dispatch_row_fields(patched, facts)
    patched = dict(row)
    patched["state"] = "running"
    patched["current_story"] = facts.dispatch_story
    if facts.dispatch_elapsed_seconds is not None:
        patched["elapsed_seconds"] = facts.dispatch_elapsed_seconds
    return _merge_dispatch_row_fields(patched, facts)


def _merge_dispatch_row_fields(row: dict[str, object], facts: FleetHomeFacts) -> dict[str, object]:
    patched = dict(row)
    if facts.dispatch_run_id is not None:
        patched["dispatch_run_id"] = facts.dispatch_run_id
    if facts.dispatch_completion_verdict is not None:
        patched["dispatch_completion_verdict"] = facts.dispatch_completion_verdict
    if facts.dispatch_verification_verdict is not None:
        patched["dispatch_verification_verdict"] = facts.dispatch_verification_verdict
    if facts.dispatch_verification_failed_gate is not None:
        patched["dispatch_verification_failed_gate"] = facts.dispatch_verification_failed_gate
    if facts.dispatch_verification_scope_advisories:
        patched["dispatch_verification_scope_advisories"] = list(facts.dispatch_verification_scope_advisories)
    if facts.dispatch_landing_findings:
        patched["dispatch_landing_findings"] = list(facts.dispatch_landing_findings)
    patched["dispatch_supervisor_alive"] = facts.dispatch_supervisor_alive
    if facts.dispatch_story_started_at is not None:
        patched["dispatch_story_started_at"] = facts.dispatch_story_started_at
    if facts.dispatch_story_ended_at is not None:
        patched["dispatch_story_ended_at"] = facts.dispatch_story_ended_at
    if facts.dispatch_baseline_revision is not None:
        patched["dispatch_baseline_revision"] = facts.dispatch_baseline_revision
    if facts.dispatch_final_revision is not None:
        patched["dispatch_final_revision"] = facts.dispatch_final_revision
    if facts.dispatch_preserve_ref is not None:
        patched["dispatch_preserve_ref"] = facts.dispatch_preserve_ref
    if facts.dispatch_wave_id is not None:
        patched["dispatch_wave_id"] = facts.dispatch_wave_id
    if facts.dispatch_in_flight_stories:
        patched["dispatch_in_flight_stories"] = list(facts.dispatch_in_flight_stories)
    if facts.dispatch_stranded_work is not None:
        patched["dispatch_stranded_work"] = facts.dispatch_stranded_work
    phase = derive_dispatch_phase(facts)
    if phase is not None:
        patched["dispatch_phase"] = phase
    return patched


def is_run_live(facts: FleetHomeFacts) -> bool:
    """Pure liveness predicate (Story 4.11, "marshal land refuses while a
    run is in flight"): ``True`` when a bmad-loop supervisor/engine run for
    this project is still using its own station branch -- the ONE
    fact ``cli/land.py`` needs before honoring a policy-true ``landing_
    branch_retirement`` and deleting that branch out from under a live run
    (the motivating incident: a live 9-story run, avoided only because a
    human read the source first).

    Reads ``facts`` DIRECTLY, never ``derive_home_state``'s own 5-value
    state string: that string's own ``"idle"`` state deliberately collapses
    two different underlying situations -- "no run ever" and "a live
    supervisor between stories, nothing in flight right now" -- into one
    string (``build_fleet_row`` only needs to display ONE state per row
    either way), and the second case is exactly the live-between-stories
    case this predicate must still catch. ``derive_home_state`` is
    therefore never called here.

    ``True`` when ``facts.has_run`` and either ``facts.journal_unreadable``
    (liveness genuinely cannot be proven either way -- conservatively
    treated as live, mirroring ``core/retire.py``'s own "a fact that cannot
    be proven is refused, never defaulted to delete" precedent for its own
    analogous "can't prove it" case) or (``not facts.finished and facts.
    supervisor_alive is True``). Every other combination -- ``has_run`` is
    ``False``; or the run is readable and either ``finished`` or its
    supervisor is confirmed dead -- is ``False``: safe to retire."""
    if not facts.has_run:
        return False
    if facts.journal_unreadable:
        return True
    # A RETIRED run is conservatively LIVE here, even though `build_fleet_row`
    # reports the same home as `idle`. The two deliberately disagree, because
    # they answer different questions: the row answers "what should an operator
    # SEE" (the run is over, the home is free), while this predicate answers
    # "may I delete a branch out from under it" -- and a retired run's own state
    # is gone, so its clean finish cannot be PROVEN. This function's motivating
    # incident was a live 9-story run nearly losing its branch; an unprovable
    # fact is refused here, never defaulted to safe, exactly as
    # `journal_unreadable` above already does.
    if facts.run_state_retired:
        return True
    return not facts.finished and facts.supervisor_alive is True


def build_fleet_row(facts: FleetHomeFacts) -> tuple[dict[str, object], Finding | None]:
    """One ``data.homes`` row plus an optional ``Finding`` (Story 5.1) --
    mirrors this module's own ``_evaluate_home``/``_evaluate_main_checkout``
    convention (already-gathered facts in, a plain row dict out).

    Precedence mirrors ``FleetHomeFacts``'s own docstring: ``journal_
    unreadable`` first (a malformed/unreadable journal degrades the WHOLE
    row to ``"unknown"``, regardless of any other field -- there is
    nothing else in ``facts`` this function can trust once that flag is
    set), then ``has_run is False`` (a clean, finding-free ``"idle"``
    row), then ``derive_home_state`` over the real run facts."""
    # Code review (2026-08-07, Blind Hunter, the single most severe finding
    # against this story, independently confirmed): `unpushed_work` is
    # NEVER hardcoded to `None` in a degraded row, unlike `escalation_*`/
    # `budget_consumed`/`current_story`. Those fields' ONLY source is the
    # same journal/snapshot that is unreadable or absent in these two
    # branches -- there is genuinely nothing to report. `unpushed_work`'s
    # source is a COMPLETELY INDEPENDENT signal (a git branch-vs-remote
    # diff, gathered once up front by the caller and threaded in via
    # `facts.unpushed_work` regardless of whether this project has ever
    # run bmad-loop or whether its journal is readable). Hardcoding `None`
    # here discarded real evidence Marshal already had in hand for exactly
    # the population most likely to carry real, unrescued local-only work
    # (a home that crashed before ever landing a run, or whose journal
    # write itself got interrupted) -- the precise false-green this
    # story's own motivating incident describes.
    if facts.harness_native_terminal:
        state = derive_home_state(
            finished=facts.finished,
            paused_stage=facts.paused_stage,
            tasks=facts.tasks,
            supervisor_alive=facts.supervisor_alive,
            engine_alive=facts.engine_alive,
        )
        current_story = _current_story_key(facts.tasks)
        escalated = state == "paused-on-escalation"
        row = {
            "slug": facts.slug,
            "branch": facts.branch,
            "state": state,
            "current_story": current_story,
            "elapsed_seconds": facts.elapsed_seconds,
            "budget_consumed": facts.budget_consumed,
            "budget_consumed_usd": facts.budget_consumed_usd,
            "layer_savings": facts.layer_savings if facts.layer_savings else None,
            "layer_savings_usd": facts.layer_savings_usd if facts.layer_savings_usd else None,
            "escalation_reason": facts.paused_reason if escalated else None,
            "escalation_artifact": (
                facts.escalated_spec_file if facts.escalated_spec_file is not None else facts.escalated_task_phase
            )
            if escalated
            else None,
            "escalation_preserve_ref": facts.escalated_preserve_ref if escalated else None,
            "parked_stories": tuple(task.story_key for task in facts.tasks if task.phase == _AWAITING_OPERATOR_PHASE),
            "unpushed_work": facts.unpushed_work,
            "failed_patches": facts.failed_patches,
        }
        finding = Finding(
            code=_HARNESS_NATIVE_TERMINAL_CODE,
            severity=Severity.WARN,
            message=(
                f"{facts.slug}: the most recent run was started directly by "
                "bmad-loop without a marshal launch pid -- this row reports "
                f"'{state}' from the harness snapshot, never a silent healthy "
                "state with no signal"
            ),
            path=facts.slug,
        )
        return _apply_finalize_escalation(
            _apply_missing_spec_escalation(_apply_dispatch_overlay(row, facts), facts),
            facts,
        ), finding

    if facts.journal_unreadable:
        row: dict[str, object] = {
            "slug": facts.slug,
            "branch": facts.branch,
            "state": "unknown",
            "current_story": None,
            "elapsed_seconds": None,
            "budget_consumed": None,
            "escalation_reason": None,
            "escalation_artifact": None,
            "escalation_preserve_ref": None,
            "parked_stories": (),
            "unpushed_work": facts.unpushed_work,
            "failed_patches": facts.failed_patches,
        }
        finding = Finding(
            code=_MALFORMED_JOURNAL_CODE,
            severity=Severity.WARN,
            message=(
                f"{facts.slug}: the most recent run's journal or run state "
                "could not be read -- this row's state is reported as "
                "'unknown', never as one of the healthy states"
            ),
            path=facts.slug,
        )
        row = _apply_dispatch_overlay(row, facts)
        if row.get("state") == "running" and facts.dispatch_story:
            finding = None
        elif facts.dispatch_completion_verdict == "completed" and not _dispatch_tail_still_live(facts):
            row = {
                **row,
                "state": "idle",
                "current_story": None,
                "elapsed_seconds": None,
            }
            finding = None
        row = _apply_dispatch_overlay(row, facts)
        return _apply_finalize_escalation(_apply_missing_spec_escalation(row, facts), facts), finding

    # A RETIRED run: its journal read fine, but bmad-loop's own snapshot for
    # it is gone (`.bmad-loop/runs/.retired-*`). That is not the same thing as
    # an unreadable journal, and reporting it as `unknown` was a real defect --
    # pyforge-steward read `unknown` from 2026-08-22 until 2026-09-08 because
    # `latest_run_dir` kept selecting a retired entry. The run is simply OVER
    # and its evidence was cleaned up, so the home is FREE: `idle` is the
    # operationally true answer, and the same one this function already gives a
    # home that never ran. The WARN still names the home, so the unresolvable
    # run is on the record rather than silently swallowed.
    if facts.run_state_retired:
        row = {
            "slug": facts.slug,
            "branch": facts.branch,
            "state": "idle",
            "current_story": None,
            "elapsed_seconds": None,
            "budget_consumed": None,
            "escalation_reason": None,
            "escalation_artifact": None,
            "escalation_preserve_ref": None,
            "parked_stories": (),
            "unpushed_work": facts.unpushed_work,
            "failed_patches": facts.failed_patches,
        }
        finding = Finding(
            code=_RETIRED_RUN_STATE_CODE,
            severity=Severity.WARN,
            message=(
                f"{facts.slug}: the most recent run's own state could not be "
                "resolved (a retired or cleaned run) -- the journal itself read "
                "fine, so this row reports 'idle' rather than 'unknown'"
            ),
            path=facts.slug,
        )
        return _apply_finalize_escalation(
            _apply_missing_spec_escalation(_apply_dispatch_overlay(row, facts), facts),
            facts,
        ), finding

    if not facts.has_run:
        row = {
            "slug": facts.slug,
            "branch": facts.branch,
            "state": "idle",
            "current_story": None,
            "elapsed_seconds": None,
            "budget_consumed": None,
            "escalation_reason": None,
            "escalation_artifact": None,
            "escalation_preserve_ref": None,
            "parked_stories": (),
            "unpushed_work": facts.unpushed_work,
            "failed_patches": facts.failed_patches,
        }
        return _apply_finalize_escalation(
            _apply_missing_spec_escalation(_apply_dispatch_overlay(row, facts), facts),
            facts,
        ), None

    state = derive_home_state(
        finished=facts.finished,
        paused_stage=facts.paused_stage,
        tasks=facts.tasks,
        supervisor_alive=facts.supervisor_alive,
        engine_alive=facts.engine_alive,
    )
    # Story 5.3 (FR-38): `escalation_artifact` prefers `escalated_spec_file`,
    # falling back to `escalated_task_phase` only when no spec file was
    # recorded -- both already-shipped `RunStatusSnapshot` fields, reused
    # verbatim (the spec's own Boundaries).
    #
    # Code review (2026-08-07, both reviewers independently, the single
    # most severe finding against this story): gated on the DERIVED
    # `state`, never on `facts.paused_reason`'s bare presence. bmad-loop's
    # own `RunState.paused_reason` is populated for EVERY pause kind
    # (spec-approval, epic-boundary, story-gate -- not only escalation),
    # and `derive_home_state` can ALSO derive `"unsupervised"`/`"stopped"`
    # for a run whose `paused_stage` still literally reads `"escalation"`
    # (a crashed supervisor, or a finished run, respectively -- both
    # already-tested precedence rules elsewhere in this module). The
    # original version populated both fields from the raw facts
    # unconditionally, so a home that was BOTH escalated AND had a dead
    # supervisor reported `state: "unsupervised"` (correctly excluded from
    # the sort-to-top and `--escalations` filter, which both key on
    # `state == "paused-on-escalation"`) while STILL carrying a real
    # escalation reason/artifact in its JSON payload -- exactly the "needs
    # a human decision" home this story exists to surface, silently
    # dropped from the one view built to catch it, with a `--format text`/
    # `--format json` divergence on top (only JSON showed the stale
    # fields, since the text marker itself IS gated on `state`).
    escalated = state == "paused-on-escalation"
    escalation_reason = facts.paused_reason if escalated else None
    escalation_artifact = (
        (facts.escalated_spec_file if facts.escalated_spec_file is not None else facts.escalated_task_phase)
        if escalated
        else None
    )
    row = {
        "slug": facts.slug,
        "branch": facts.branch,
        "state": state,
        "current_story": _current_story_key(facts.tasks),
        "elapsed_seconds": facts.elapsed_seconds,
        "budget_consumed": facts.budget_consumed,
        "budget_consumed_usd": facts.budget_consumed_usd,
        "layer_savings": facts.layer_savings if facts.layer_savings else None,
        "layer_savings_usd": facts.layer_savings_usd if facts.layer_savings_usd else None,
        "escalation_reason": escalation_reason,
        "escalation_artifact": escalation_artifact,
        # Story 25.5 (CAP-5): the escalated story's recovery pointer --
        # gated on the DERIVED state exactly like `escalation_reason`/
        # `escalation_artifact` above (same 2026-08-07 review rationale:
        # a stale ref must not leak into a row whose state is not the
        # escalated one).
        "escalation_preserve_ref": (facts.escalated_preserve_ref if escalated else None),
        # Story 25.5 (CAP-5): every task currently parked at bmad-loop
        # 0.11's `awaiting-operator`, in `state.json`'s own task order --
        # populated for ANY state (a park never blocks siblings, so a
        # `running` run can legitimately carry parked stories the operator
        # still owes), `()` when none.
        "parked_stories": tuple(task.story_key for task in facts.tasks if task.phase == _AWAITING_OPERATOR_PHASE),
        # Story 5.5: the caller's own already-matched detector finding,
        # verbatim -- never re-derived here (AD-48). `None` when no
        # matching finding exists, or the detector could not be consulted.
        "unpushed_work": facts.unpushed_work,
        # Story 4.14: the caller's own already-classified failed-story
        # patches, verbatim -- never re-derived here (see `FleetHomeFacts.
        # failed_patches`'s own docstring above).
        "failed_patches": facts.failed_patches,
    }
    row = _apply_dispatch_overlay(row, facts)
    return _apply_finalize_escalation(_apply_missing_spec_escalation(row, facts), facts), None


def sort_fleet_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Escalated rows (``state == "paused-on-escalation"``) sort FIRST in
    ``data.homes``, stable otherwise -- every other row keeps its existing
    relative order (Story 5.3, FR-38). A pure sort applied once, after every
    row is already built (``build_fleet_row``'s own output); never a
    re-ordering of the underlying fleet enumeration itself."""
    return sorted(rows, key=lambda row: row.get("state") != "paused-on-escalation")


# =============================================================================
# Story 5.2: per-run detail (``marshal status --run <run_id> --project
# <slug>``, FR-37/NFR-12) -- extends the SAME ``marshal status`` command with
# a single-run drill-down: the FULL story sequence (``RunStatusSnapshot.
# tasks``, in ``state.json``'s own order, never re-sorted/deduplicated),
# each story's own gate verdict (``cli/deploy.py::_gather_gate_verdicts``,
# reused verbatim), escalation/deferral state (``RunStatusSnapshot``'s own
# already-shipped fields, read never re-derived), per-story consumption
# (Story 3.6's own ``"budget-usage"`` observations, grouped by
# ``payload["story_key"]`` this time rather than Story 5.1's own single
# latest-overall value), and open ``intent``-phase journal entries
# (``core.journal.fold``'s own ``FoldResult.open_intents``, reported
# verbatim). ``cli/status.py`` gathers every fact via ``VcsPort``/``FsPort``/
# ``HarnessPort`` first -- this module stays pure (AD-4): no I/O, subprocess,
# or clock read.
# =============================================================================

_RUN_NOT_FOUND_CODE = "MRS-STATUS-004"


def _render_story_key_best_effort(raw: str) -> str:
    """Marshal's own canonical dot-form rendering of a harness-native story
    key, falling back to ``raw`` unchanged when it does not parse --
    DUPLICATED from ``cli/spin.py``'s own identically-named helper (and
    ``supervisor/__main__.py``'s own ``_feed_key_form``), never imported:
    this module sits in ``core/``, which AD-3/AD-4 forbid from ever
    importing ``cli/``. Used ONLY to look ``TaskPhaseSnapshot.story_key``
    (bmad-loop's native spelling) up against ``gate_verdicts``/
    ``budget_by_story`` (both keyed by Marshal's own dot form, since
    ``_gather_gate_verdicts``'s own ``manual-landing`` payloads and
    ``supervisor/__main__.py``'s own ``_BUDGET_USAGE_KIND`` payloads are
    both already written in that form) -- the STORY SEQUENCE itself
    (``build_run_detail``'s own ``data.stories[*]["story_key"]``) always
    reports ``task.story_key`` verbatim, mirroring ``_current_story_key``'s
    own established convention (Story 5.1) of never rendering the fleet
    row's own ``current_story`` field either."""
    try:
        return render_feed_key(normalize(raw))
    except ValueError:
        return raw


@dataclass(frozen=True, kw_only=True)
class RunDetailFacts:
    """Already-gathered facts for ONE run's own detail view (Story 5.2) --
    read by ``cli/status.py::_run_detail`` via ``VcsPort``/``FsPort``/
    ``HarnessPort`` before this pure module ever sees them (AD-4).

    ``found`` is ``False`` when no run directory exists at all for
    ``project``/``run_id`` -- every other field is then a placeholder, and
    ``build_run_detail`` reports a clean, registered ``MRS-STATUS-004``
    finding rather than crashing (the spec's own "a run id with no matching
    directory" row).

    ``state_readable`` is ``True`` only when bmad-loop's own live
    ``RunStatusSnapshot`` was actually obtained for this run (a loop home is
    currently attached for ``project`` AND its own ``state.json`` read
    cleanly) -- ``False`` degrades ``finished``/``paused_*``/
    ``escalated_*`` to ``None`` and ``tasks``/``deferred`` are then expected
    to be empty (nothing to report), with one reused ``MRS-STATUS-002`` WARN
    naming the gap (mirrors Story 5.1's own ``journal_unreadable``
    precedent: one degraded row, never a crash, never silently reported as
    healthy). ``gate_verdicts``/``budget_by_story``/``open_intents`` are
    sourced independently (the project's own cross-run land journal, and
    THIS run's own ``journal.jsonl`` fold, respectively) and remain
    populated even when ``state_readable`` is ``False`` -- a dead/detached
    loop home does not itself invalidate either journal read.

    ``gate_verdicts``/``budget_by_story`` are both keyed by Marshal's own
    canonical dot-form story key (``_gather_gate_verdicts``'s own
    ``manual-landing`` payloads and ``supervisor/__main__.py``'s own
    ``_BUDGET_USAGE_KIND`` payloads are both already written in that form)
    -- ``build_run_detail`` renders each task's own bmad-loop-native
    ``story_key`` via ``_render_story_key_best_effort`` ONLY to perform
    this lookup; the reported ``story_key`` itself stays verbatim.
    ``open_intents`` is ``core.journal.fold``'s own ``FoldResult.
    open_intents``, already rendered to plain JSON-dicts (``JournalEntry.
    to_json_dict()``) by the caller -- reported verbatim, kind/payload/id
    included, never re-interpreted (this command does not attempt to close
    or reconcile them; that stays ``cli/deploy.py``'s own
    ``_reconcile_open_intents`` machinery, out of scope here)."""

    project: str
    run_id: str
    found: bool = True
    state_readable: bool = True
    finished: bool = False
    paused_stage: str | None = None
    paused_story_key: str | None = None
    paused_reason: str | None = None
    escalated_spec_file: str | None = None
    escalated_task_phase: str | None = None
    tasks: tuple[TaskPhaseSnapshot, ...] = ()
    deferred: tuple[DeferredStory, ...] = ()
    gate_verdicts: Mapping[str, str] = field(default_factory=dict)
    budget_by_story: Mapping[str, int | float] = field(default_factory=dict)
    # Story 28.4 (CAP-7): per-story layer savings keyed by Marshal's own
    # canonical dot-form story key -- absent when no savings were recorded.
    savings_by_story: Mapping[str, Mapping[str, object]] = field(default_factory=dict)
    budget_by_story_usd: Mapping[str, float] = field(default_factory=dict)
    savings_usd_by_story: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    open_intents: tuple[dict[str, object], ...] = ()
    # Story 25.5 (CAP-5): `RunStatusSnapshot.sweeps_refused` verbatim --
    # trigger -> reason slug (the closed `SWEEP_REFUSED_*` vocabulary).
    # `None` = the live run state could not be read at all (the caller had
    # no snapshot), NEVER a fabricated `{}`-clean; `{}` = a readable state
    # that refused nothing.
    sweeps_refused: Mapping[str, str] | None = None


def build_run_detail(facts: RunDetailFacts) -> tuple[dict[str, object], Finding | None]:
    """One run's full detail row (Story 5.2) plus an optional ``Finding`` --
    mirrors this module's own ``build_fleet_row`` convention (already-
    gathered facts in, a plain row dict out). Every field this row carries
    has an identical machine-readable counterpart to whatever
    ``cli/status.py``'s own ``_render_text_run_detail`` prints (NFR-12): the
    text view is a pure projection of this SAME dict, never a second,
    independently-computed rendering."""
    if not facts.found:
        row: dict[str, object] = {
            "project": facts.project,
            "run_id": facts.run_id,
            "found": False,
            "state_readable": None,
            "finished": None,
            "paused_stage": None,
            "paused_story_key": None,
            "paused_reason": None,
            "escalated_spec_file": None,
            "escalated_task_phase": None,
            "sweeps_refused": None,
            "stories": [],
            "deferred": [],
            "open_intents": [],
        }
        finding = Finding(
            code=_RUN_NOT_FOUND_CODE,
            severity=Severity.WARN,
            message=(
                f"project {facts.project!r}: no run directory found for "
                f"run id {facts.run_id!r} -- reported, never fabricated"
            ),
            path=facts.run_id,
        )
        return row, finding

    stories: list[dict[str, object]] = []
    for task in facts.tasks:
        rendered_key = _render_story_key_best_effort(task.story_key)
        story_row: dict[str, object] = {
            "story_key": task.story_key,
            "phase": task.phase,
            "commit_sha": task.commit_sha,
            "branch": task.branch,
            # Story 25.5 (CAP-5): the recovery pointer wherever an
            # escalated/deferred story is surfaced -- reported
            # verbatim for EVERY task (null when none was parked).
            "preserve_ref": task.preserve_ref,
            "gate_verdict": facts.gate_verdicts.get(rendered_key),
            "budget_consumed": facts.budget_by_story.get(rendered_key),
        }
        layer_savings = facts.savings_by_story.get(rendered_key)
        if layer_savings is not None:
            story_row["layer_savings"] = layer_savings
        savings_usd = facts.savings_usd_by_story.get(rendered_key)
        if savings_usd is not None:
            story_row["layer_savings_usd"] = dict(savings_usd)
        budget_usd = facts.budget_by_story_usd.get(rendered_key)
        if budget_usd is not None:
            story_row["budget_consumed_usd"] = budget_usd
        stories.append(story_row)

    deferred = [
        {
            "story_key": deferred_story.story_key,
            "reason": deferred_story.reason,
            "attempt": deferred_story.attempt,
            "branch": deferred_story.branch,
            "worktree_path": deferred_story.worktree_path,
            "spec_file": deferred_story.spec_file,
            # Story 25.5 (CAP-5): same recovery pointer, on the
            # `Phase.DEFERRED` subset's own rows.
            "preserve_ref": deferred_story.preserve_ref,
        }
        for deferred_story in facts.deferred
    ]

    row = {
        "project": facts.project,
        "run_id": facts.run_id,
        "found": True,
        "state_readable": facts.state_readable,
        "finished": facts.finished if facts.state_readable else None,
        "paused_stage": facts.paused_stage if facts.state_readable else None,
        "paused_story_key": (facts.paused_story_key if facts.state_readable else None),
        "paused_reason": facts.paused_reason if facts.state_readable else None,
        "escalated_spec_file": (facts.escalated_spec_file if facts.state_readable else None),
        "escalated_task_phase": (facts.escalated_task_phase if facts.state_readable else None),
        # Story 25.5 (CAP-5): trigger -> reason slug, verbatim. `None` when
        # the live run state could not be read (mirrors the sibling
        # snapshot-sourced fields above), never fabricated as `{}`-clean.
        "sweeps_refused": (
            dict(facts.sweeps_refused) if facts.state_readable and facts.sweeps_refused is not None else None
        ),
        "stories": stories,
        "deferred": deferred,
        "open_intents": list(facts.open_intents),
    }

    finding = None
    if not facts.state_readable:
        finding = Finding(
            code=_MALFORMED_JOURNAL_CODE,
            severity=Severity.WARN,
            message=(
                f"{facts.project}: run {facts.run_id}'s live run state "
                "could not be read -- finished/paused/escalation/story "
                "fields report as null/empty, never fabricated"
            ),
            path=facts.project,
        )
    return row, finding


# =============================================================================
# Story 5.4 (ledger-vs-git reconciliation, FR-39/FR-40): compares the
# tracked ``sprint-status-ledger.yaml`` twin's own ``status: done`` story
# keys against git's own durably-merged story keys (``core.promotion.
# merged_story_keys``), and reports EVERY disagreement in either direction
# by name -- the live incident this story exists to catch (Epic 4's own
# stories sat at ``review`` in the tracked ledger for hours after their PRs
# had actually merged). ``cli/status.py`` gathers both sets via
# ``HarnessPort.ledger_story_statuses``/``VcsPort.commit_subjects`` first --
# this module stays pure (AD-4): no I/O, subprocess, or clock read. Neither
# source is ever rewritten here (AD-33): this is a read-only, diagnostic
# comparison, never a resolution.
# =============================================================================

#: The two named discrepancy directions (the spec's own Always bullet: BOTH
#: reported, neither a lesser-supported afterthought).
DONE_IN_LEDGER_NOT_MERGED = "done-in-ledger-not-merged"
MERGED_NOT_DONE_IN_LEDGER = "merged-not-done-in-ledger"

#: Code review (2026-08-07, both reviewers independently, the single most
#: severe finding against this story -- confirmed LIVE against this repo's
#: own real history): the two directions are NOT equally reliable.
#: ``MERGED_NOT_DONE_IN_LEDGER`` is a POSITIVE match -- `core.promotion.
#: merged_story_keys` found a commit subject that conforms to one of its
#: recognized shapes, so the key genuinely is durably merged; this is the
#: live incident's own exact failure mode (Epic 4's 4.1-4.7 stuck at
#: `review`) and this direction is CONFIRMED. ``DONE_IN_LEDGER_NOT_MERGED``
#: is an ABSENCE of a match -- and `merged_story_keys` has a real, known
#: blind spot: a GitHub squash-merge commit's subject is free-form human
#: prose (this repo's own `sprint-status-ledger.yaml` header comment
#: explicitly documents this exact failure mode as the reason the ledger
#: exists at all: "the archaeology that failed when squash-merging PR #132
#: made Epic 10's bmad-loop merge subjects unreachable from main"). A live
#: run against this repo's own real ledger produced 5 `DONE_IN_LEDGER_
#: NOT_MERGED` rows for stories that ARE genuinely merged (1.2, 1.3, 1.6,
#: 1.10, 5.1) -- zero of them real discrepancies. Reporting this direction
#: with the SAME confidence as the other would train an operator to
#: distrust the ledger over false alarms, defeating this story's own
#: purpose. Both directions are still reported (the AC's own "both
#: reported" requirement, unchanged) but tagged with `confidence` so a
#: consumer can weight them correctly.
CONFIDENCE_CONFIRMED = "confirmed"
CONFIDENCE_UNCONFIRMED = "unconfirmed"


def reconcile_ledger_vs_git(
    ledger_done_keys: frozenset[str], merged_keys: frozenset[str]
) -> tuple[dict[str, object], ...]:
    """The pure reconciliation core of ``marshal status --reconcile-ledger``
    (Story 5.4): one row per story key present in exactly one of the two
    sets -- ``{"story_key": str, "kind": str, "confidence": str}``, ``kind``
    one of ``DONE_IN_LEDGER_NOT_MERGED``/``MERGED_NOT_DONE_IN_LEDGER``
    above. A key present in BOTH (agreement) or NEITHER contributes
    nothing -- the clean case, per the spec's own I/O matrix ("Ledger and
    git agree fully" -> ``data.discrepancies: []``). Sorted by story key
    within each direction (``DONE_IN_LEDGER_NOT_MERGED`` rows first, then
    ``MERGED_NOT_DONE_IN_LEDGER``) for a deterministic report over a
    deterministic input, never dict/set iteration-order luck -- mirrors
    ``reconcile_feed_domains``'s own identical precedent.

    ``confidence`` (code review, 2026-08-07, see this module's own
    ``CONFIDENCE_CONFIRMED``/``CONFIDENCE_UNCONFIRMED`` module-level
    comment for the full rationale): ``MERGED_NOT_DONE_IN_LEDGER`` rows are
    always ``CONFIDENCE_CONFIRMED`` (a positive git match is proof);
    ``DONE_IN_LEDGER_NOT_MERGED`` rows are always ``CONFIDENCE_UNCONFIRMED``
    (an absence of a match does NOT prove the story was never merged --
    ``merged_story_keys`` has a real, documented blind spot for squash-merge
    commit subjects).

    Both arguments are ALREADY-normalized ``str`` forms of Marshal's
    canonical ``StoryKey`` (the caller's job -- ``core.identity.normalize``,
    skipping any raw key that fails to parse, mirrors every other Epic 5
    story's established convention) -- this function does no parsing of its
    own. No ``Finding`` is ever produced here: per the spec's own I/O
    matrix, a discrepancy is reported, never an error -- it is named in
    ``data.discrepancies`` alone."""
    discrepancies: list[dict[str, object]] = []
    for key in sorted(ledger_done_keys - merged_keys):
        discrepancies.append(
            {
                "story_key": key,
                "kind": DONE_IN_LEDGER_NOT_MERGED,
                "confidence": CONFIDENCE_UNCONFIRMED,
            }
        )
    for key in sorted(merged_keys - ledger_done_keys):
        discrepancies.append(
            {
                "story_key": key,
                "kind": MERGED_NOT_DONE_IN_LEDGER,
                "confidence": CONFIDENCE_CONFIRMED,
            }
        )
    return tuple(discrepancies)


# =============================================================================
# Story 5.9 ("a story finished by hand is not invisible to the ledger",
# AD-5/AD-29/AD-33): the two pure cores behind `marshal deploy
# reconcile-completions` -- Story 5.4's own READ-ONLY sibling above
# (`reconcile_ledger_vs_git`) diagnoses the SAME "ledger vs. git" gap but
# never writes; this story's `not_loop_native_completions` decides WHICH
# keys a write-capable command should advance, and `render_ledger_
# advancements` performs the write as a pure text transform. The reported
# completion-path label is `"not-loop-native"`, never `"bmad-quick-dev"`
# (Spec Change Log, 2026-08-12): the detection mechanism only proves "not a
# templated or bmad-loop-native merge subject", which `marshal land`'s own
# plain-PR-shaped landings also satisfy -- see `core.promotion.
# marshal_native_merged_keys`'s own docstring for the full rationale.
# `cli/deploy.py::run_reconcile_completions` gathers every impure input
# first -- `_scan_promotions`'s own already-shipped corroboration pipeline
# (Story 4.1/4.2, reused verbatim, never re-derived), `core.promotion.
# marshal_native_merged_keys`/`merged_story_keys` (the conjunction the
# contract's own "a git match alone never triggers a write" bullet
# requires), and `HarnessPort.ledger_story_statuses`'s raw `(raw_key,
# raw_status)` pairs, all reduced to ALREADY-normalized dot-form `str` keys
# via `core.identity.normalize` at the CLI boundary -- and hands the
# resulting frozensets to `not_loop_native_completions` below. The ledger's
# own raw TEXT (`HarnessPort.ledger_story_statuses` returns only PARSED
# pairs, never the source bytes -- AD-3 forbids this module from importing
# `bmad_loop` directly to get them, so the CLI reads it separately via
# `FsPort.read_text`) is handed to `render_ledger_advancements`. Both
# functions stay pure (AD-4): no I/O, no subprocess, no clock, no
# `..adapters` import.
# =============================================================================

#: The literal ledger status value `render_ledger_advancements` writes.
#: Deliberately a SEPARATE, identically-spelled constant from this module's
#: own `_DONE_PHASE` above (both happen to be the string "done") rather
#: than a shared reference -- `_DONE_PHASE` names a bmad-loop TASK phase
#: (`TaskPhaseSnapshot.phase`), a wholly different vocabulary from the
#: tracked ledger's own `development_status` map value, and this module's
#: own `render_feed_key`/`render_filename_slug` precedent already
#: establishes "distinct functions/constants for distinct external forms,
#: even when today's spelling coincides" as this codebase's convention.
_LEDGER_DONE_STATUS = "done"

#: The one ledger row status `not_loop_native_completions` ever advances
#: from. Deliberately narrower than "anything but `done`" (review fix,
#: 2026-08-12, medium-severity): `blocked`/`in-progress`/`optional` are a
#: DELIBERATE operator/process signal recorded in the ledger, and a
#: git-plus-spec-corroborated completion signal must never silently
#: overwrite one -- only a row nobody has touched yet (the ledger's own
#: default un-started state) is safe to advance purely from that evidence.
_LEDGER_BACKLOG_STATUS = "backlog"

#: Splits ``render_ledger_advancements``'s own ``ledger_text`` on each of
#: its line-ending characters, CAPTURING the separator so it survives in
#: the result list (odd indices) untouched -- ``\r\n`` tried before the
#: bare ``\r``/``\n`` alternatives so a Windows-style ending is captured
#: whole, never split into two separate one-character separators.
_LEDGER_LINE_SPLIT = re.compile(r"(\r\n|\r|\n)")


def not_loop_native_completions(
    ledger_backlog_keys: frozenset[str],
    not_loop_native_candidates: frozenset[str],
) -> frozenset[str]:
    """Every dot-form story key `marshal deploy reconcile-completions`
    should advance to `done` in the tracked ledger THIS run (Story 5.9,
    AD-5/AD-33). Pure set arithmetic over two ALREADY-normalized dot-form
    `frozenset[str]` arguments -- no `StoryKey`/`core.identity.normalize`
    call happens here; the CLI boundary performs every raw-string-to-dot-
    form conversion before calling this function, mirroring `reconcile_
    ledger_vs_git`'s own identical "arguments are ALREADY-normalized str
    forms" contract above. Named for the REPORTED label (Spec Change Log,
    2026-08-12) -- `"not-loop-native"`, not `"bmad-quick-dev"` -- since the
    caller's own `not_loop_native_candidates` set covers every route Marshal
    itself did not drive, not only a genuine `bmad-quick-dev` session (see
    the module comment above).

    `not_loop_native_candidates` is the CALLER's own already-computed
    `(corroborated_keys & full_merged_keys) - marshal_native_keys`
    difference (Story 5.9's own CAP-1 corroboration set -- durable per
    git's FULL three-pattern `core.promotion.merged_story_keys` (`&
    full_merged_keys`: review fix, 2026-08-12, high-severity -- a tracked
    spec alone, via `_already_promoted_keys`, is never sufficient; the
    contract's own "a git match alone never triggers a write" bullet reads
    both directions, and this conjunction is what keeps a spec with NO
    merge evidence at all from being treated as corroborated), AND backed
    by a valid, durable Tier-3/tracked spec -- MINUS `core.promotion.
    marshal_native_merged_keys`'s own two-of-three-pattern durability
    answer, i.e. every story landed via a route Marshal itself did not
    drive). This function no longer re-derives that difference internally
    (review fix, 2026-08-12, low-severity: the identical set difference
    used to be computed independently in two places -- here and again
    inline in `cli/deploy.py::run_reconcile_completions` for its own
    `MRS-DEPLOY-026` finding -- not divergent today, but a future edit to
    either could silently desync them; the caller now computes it exactly
    once and passes the same value to both consumers).

    A key is eligible when BOTH of the following hold:

    1. It is in `not_loop_native_candidates` -- corroborated, backed by real
       merge evidence, AND landed via a route Marshal did not drive (a
       merged key with no valid spec at all is never corroborated -- this
       story's own Boundaries: "a git match alone never triggers a
       write"; a key landed via `deploy land-story` or a bmad-loop-native
       merge is a route Marshal ALREADY knows about -- Story 5.4's own
       read-only sync already owns that case, this story's own Never
       bullet: "never fold this into ... Story 5.4's own sync").
    2. Its CURRENT ledger row status, in `ledger_backlog_keys`, is
       literally `backlog` -- never `done` (already converged, AD-21's
       convergence property: a converged re-run produces zero changes and
       exit 0, never re-reported, never re-committed) and never `blocked`/
       `in-progress`/`optional` either (review fix, 2026-08-12,
       medium-severity: see `_LEDGER_BACKLOG_STATUS`'s own comment). A
       candidate absent from the ledger altogether is neither in
       `ledger_backlog_keys` nor eligible here -- it is instead the
       caller's own `MRS-DEPLOY-026` finding, computed by `cli/deploy.py`
       from the SAME `not_loop_native_candidates` this function takes as an
       argument, against its own separately-gathered `ledger_all_keys`.

    Pure: no I/O, no `HarnessPort`, no `VcsPort` -- every argument is the
    caller's own already-gathered, already-normalized fact."""
    return frozenset(key for key in not_loop_native_candidates if key in ledger_backlog_keys)


def render_ledger_advancements(ledger_text: str, raw_keys: frozenset[str]) -> tuple[str, frozenset[str]]:
    """A targeted LINE REWRITE of the tracked ``sprint-status-ledger.yaml``
    twin's own text (Story 5.9, this story's own Boundaries: "a targeted
    line rewrite, not a re-render"). For every ``development_status:`` map
    entry whose RAW key (the caller's own already-resolved ledger key
    spelling, e.g. ``"5-9-a-story-finished-by-hand-isnt-invisible-to-the-
    ledger"`` -- NEVER Marshal's own dot-form ``StoryKey``, which this
    ledger does not use as a map key at all) matches an entry in
    ``raw_keys``, replaces ONLY that line's status TOKEN with ``done``,
    preserving the line's own leading indentation, the key text, the
    whitespace between the colon and the status, any trailing content
    after the status (e.g. a ``# comment``), and the line's own original
    line-ending character(s) (``\\n``/``\\r\\n``/none) verbatim -- review
    fix, 2026-08-12, medium-severity: the earlier implementation dropped a
    matched line's own trailing comment entirely and, on a CRLF-checked-out
    file, silently downgraded exactly the matched line's ending to bare
    ``\\n`` while every untouched line stayed ``\\r\\n``, producing a
    file with MIXED endings -- both contradicted this function's own
    "byte-identical otherwise" contract. Every OTHER line -- the header
    comment block, every non-matching entry, blank lines, ordering -- is
    reproduced BYTE-FOR-BYTE: this function never invents a new key, never
    re-renders the map, never reorders entries, and never touches the
    header ``scripts/promote_sprint_status.py``/``fleet_scan.py::parse_
    sprint_status`` both depend on (this story's own Boundaries, verbatim).
    No YAML library is used at all -- a full re-render is explicitly
    forbidden by that same Boundaries bullet, so this is plain line-level
    string manipulation, splitting on (and re-joining with) each line's own
    ``\\r\\n``/``\\r``/``\\n`` separator via a capturing ``re.split`` so
    every separator round-trips exactly as found, whether or not the file
    mixes them.

    Matching is EXACT, not a prefix test: each line is split on its FIRST
    ``:`` (a raw ledger key is a hyphenated slug and never contains one),
    and the text before it -- stripped of leading indentation only -- must
    equal a ``raw_keys`` member exactly. A key that happens to be a
    TEXTUAL PREFIX of another (e.g. a hypothetical ``"5-9"`` against a real
    ``"5-9a-..."``) can therefore never cross-match, because the compared
    text is the WHOLE pre-colon segment, never a truncated prefix of it.

    Returns ``(new_text, matched_raw_keys)`` -- ``matched_raw_keys`` is the
    SUBSET of ``raw_keys`` that actually had a matching line (review fix,
    2026-08-12, high-severity: the caller used to publish its own pre-write
    ELIGIBILITY set as "advanced", over-reporting a per-key match failure
    and, on a whole-batch match failure, writing nothing, committing
    nothing and emitting no finding at all -- the caller now derives
    ``data["advanced"]`` from what this function actually matched, and
    reports every requested-but-unmatched key via its own finding). A
    ``raw_keys`` member with no matching line is silently left unmatched in
    the TEXT -- this function never raises and never fabricates a row; it
    is the CALLER's job to report an unmatched key, using the returned set,
    never this function's. The caller's own precondition
    (`not_loop_native_completions`'s own `ledger_backlog_keys` membership
    check, satisfied before a raw key ever reaches this function) is what
    makes an unmatched key the ordinary case of a TOCTOU against the raw
    text rather than a routine occurrence; this function stays correct
    even when that precondition is violated, by doing nothing for the
    unmatched key rather than guessing at a line to rewrite.

    Pure: no I/O, no ``HarnessPort``. ``ledger_text`` is the caller's own
    already-read file content; the caller is responsible for writing the
    result back (``FsPort.write_text_atomic``) and committing it
    (``VcsPort.commit_paths``) -- this function only computes the new
    text."""
    if not raw_keys:
        return ledger_text, frozenset()
    remaining = set(raw_keys)
    matched: set[str] = set()
    # Alternating [content, separator, content, separator, ..., content] --
    # only the CONTENT elements (even indices) are ever rewritten; every
    # separator is carried through unmodified, whatever it is and however
    # it mixes with its neighbors.
    parts = _LEDGER_LINE_SPLIT.split(ledger_text)
    for i in range(0, len(parts), 2):
        content = parts[i]
        stripped = content.lstrip(" ")
        indent = content[: len(content) - len(stripped)]
        colon_index = stripped.find(":")
        key_part = stripped[:colon_index] if colon_index != -1 else None
        if key_part is None or key_part not in remaining:
            continue
        rest = stripped[colon_index + 1 :]
        rest_stripped = rest.lstrip(" ")
        leading_ws = rest[: len(rest) - len(rest_stripped)] or " "
        status_end = 0
        while status_end < len(rest_stripped) and not rest_stripped[status_end].isspace():
            status_end += 1
        trailer = rest_stripped[status_end:]
        parts[i] = f"{indent}{key_part}:{leading_ws}{_LEDGER_DONE_STATUS}{trailer}"
        remaining.discard(key_part)
        matched.add(key_part)
    return "".join(parts), frozenset(matched)
