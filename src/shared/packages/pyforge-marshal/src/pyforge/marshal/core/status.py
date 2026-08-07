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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ..ports.harness import DeferredStory, TaskPhaseSnapshot
from ..ports.process import ProcessResult
from .identity import StoryKey, normalize, render_feed_key
from .model import Finding, Severity

_LOOP_BRANCH_PREFIX = "loop/"


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
        if not isinstance(self.branch, str) or not self.branch.startswith(
            _LOOP_BRANCH_PREFIX
        ):
            raise ValueError(
                f"HomeFacts.branch must be a {_LOOP_BRANCH_PREFIX!r}-prefixed "
                f"branch name, got {self.branch!r}"
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
        return (
            "planning-artifacts is occupied by a real (non-symlink) "
            "directory or file where a symlink belongs"
        )
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
            f"tier-3 backlink resolves to {tier3_local_realpath} but the "
            f"canonical store is {tier3_canonical_realpath}"
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


def evaluate_homes(
    homes: Sequence[HomeFacts], main_checkout: MainCheckoutFacts
) -> HomesEvaluation:
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

    return HomesEvaluation(
        homes=tuple(home_rows), main_checkout=main_row, findings=tuple(findings)
    )


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
            raise ValueError(
                f"DomainField.domain must be 'git' or 'journal', got {self.domain!r}"
            )


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
            message=failure_reason
            or f"landing_resync_commands entry {command!r} could not be run",
        )

    if result.returncode != 0:
        outcome = (
            f"was terminated by signal {-result.returncode}"
            if result.returncode < 0
            else f"exited {result.returncode}"
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
_TERMINAL_TASK_PHASES = frozenset({_DONE_PHASE, _DEFERRED_PHASE, _ESCALATED_PHASE})

#: The closed 5-value state vocabulary the spec's own Boundaries name: the
#: 4 "healthy" states PLUS ``"unsupervised"`` -- never conflated with them
#: (a dead supervisor is never reported as any of the other four).
FLEET_STATES = (
    "idle",
    "running",
    "paused-on-escalation",
    "stopped",
    "unsupervised",
)


def derive_home_state(
    *,
    finished: bool,
    paused_stage: str | None,
    tasks: tuple[TaskPhaseSnapshot, ...],
    supervisor_alive: bool | None,
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
    finished`` together are therefore the ONLY unsupervised trigger --
    exactly the spec's own I/O matrix row ("a home whose supervisor pid is
    dead, run not finished"). ``supervisor_alive is None`` (liveness could
    not be probed, e.g. no pid was ever recovered) never triggers this
    override on its own -- a caller with no pid to check ``cli/status.py``
    degrades to the ``"unknown"``-shaped row via ``journal_unreadable``
    instead of ever reaching this function with a real pid absent.

    Ordering below matches the spec's own I/O matrix exactly:
    ``finished`` -> ``"stopped"``; ``paused_stage == "escalation"`` ->
    ``"paused-on-escalation"``; a task whose ``phase`` is neither
    ``"done"`` nor ``"deferred"`` -> ``"running"`` (mirrors
    ``cli/retire.py``'s own reuse of the identical ``_DONE_PHASE``
    literal); otherwise -> ``"idle"`` (a run that exists but has no
    in-flight task right now -- e.g. between stories -- reads the same as
    "nothing to report" a caller with no run at all would report)."""
    if not finished and supervisor_alive is False:
        return "unsupervised"
    if finished:
        return "stopped"
    if paused_stage == _ESCALATION_PAUSED_STAGE:
        return "paused-on-escalation"
    for task in tasks:
        if task.phase not in _TERMINAL_TASK_PHASES:
            return "running"
    return "idle"


def _current_story_key(tasks: tuple[TaskPhaseSnapshot, ...]) -> str | None:
    """ "Current story" (the spec's own Always bullet): the ``story_key`` of
    the FIRST ``TaskPhaseSnapshot`` whose ``phase`` is neither ``"done"``
    nor ``"deferred"`` -- ``None`` when every task is terminal, or there
    are none at all."""
    for task in tasks:
        if task.phase not in _TERMINAL_TASK_PHASES:
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
    budget-relevant entry has been journaled yet for this run."""

    slug: str
    branch: str
    has_run: bool = False
    journal_unreadable: bool = False
    finished: bool = False
    paused_stage: str | None = None
    tasks: tuple[TaskPhaseSnapshot, ...] = ()
    supervisor_alive: bool | None = None
    elapsed_seconds: float | None = None
    budget_consumed: int | float | None = None


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
    if facts.journal_unreadable:
        row: dict[str, object] = {
            "slug": facts.slug,
            "branch": facts.branch,
            "state": "unknown",
            "current_story": None,
            "elapsed_seconds": None,
            "budget_consumed": None,
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
        return row, finding

    if not facts.has_run:
        row = {
            "slug": facts.slug,
            "branch": facts.branch,
            "state": "idle",
            "current_story": None,
            "elapsed_seconds": None,
            "budget_consumed": None,
        }
        return row, None

    state = derive_home_state(
        finished=facts.finished,
        paused_stage=facts.paused_stage,
        tasks=facts.tasks,
        supervisor_alive=facts.supervisor_alive,
    )
    row = {
        "slug": facts.slug,
        "branch": facts.branch,
        "state": state,
        "current_story": _current_story_key(facts.tasks),
        "elapsed_seconds": facts.elapsed_seconds,
        "budget_consumed": facts.budget_consumed,
    }
    return row, None


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
    open_intents: tuple[dict[str, object], ...] = ()


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
        stories.append(
            {
                "story_key": task.story_key,
                "phase": task.phase,
                "commit_sha": task.commit_sha,
                "branch": task.branch,
                "gate_verdict": facts.gate_verdicts.get(rendered_key),
                "budget_consumed": facts.budget_by_story.get(rendered_key),
            }
        )

    deferred = [
        {
            "story_key": deferred_story.story_key,
            "reason": deferred_story.reason,
            "attempt": deferred_story.attempt,
            "branch": deferred_story.branch,
            "worktree_path": deferred_story.worktree_path,
            "spec_file": deferred_story.spec_file,
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
        "paused_story_key": (
            facts.paused_story_key if facts.state_readable else None
        ),
        "paused_reason": facts.paused_reason if facts.state_readable else None,
        "escalated_spec_file": (
            facts.escalated_spec_file if facts.state_readable else None
        ),
        "escalated_task_phase": (
            facts.escalated_task_phase if facts.state_readable else None
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
