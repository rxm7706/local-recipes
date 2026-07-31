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

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .model import Finding, Severity

_LOOP_BRANCH_PREFIX = "loop/"


@dataclass(frozen=True)
class HomeFacts:
    """Already-gathered state for ONE discovered ``loop/<slug>`` worktree --
    read by ``cli/init.py::run_homes`` via ``VcsPort``/``FsPort`` before this
    pure module ever sees it.

    ``tier3_local_realpath`` is ``None`` when the home's local Tier-3 path is
    not a symlink at all (never provisioned by ``marshal init``) -- absence
    is not a violation, only a resolved value that disagrees with
    ``tier3_canonical_realpath`` is. ``tier3_canonical_realpath`` is always
    known: it is the home's OWN branch-derived slug's canonical store,
    independent of whether the local backlink exists.
    """

    path: Path
    branch: str
    marker_text: str | None
    symlink_target: Path | None
    tier3_local_realpath: Path | None
    tier3_canonical_realpath: Path

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
    HOME-side concept only)."""

    path: Path
    branch: str | None
    marker_text: str | None
    symlink_target: Path | None


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
) -> str | None:
    """The one comparison both checks 1 and 2 (module docstring) share.
    ``branch_slug=None`` is the main checkout's two-way rule (no third leg);
    a ``str`` is a home's three-way rule. Returns a human-readable mismatch
    description, or ``None`` if nothing disagrees.

    Ported from ``cli/init.py``'s own ``MRS-INIT-003`` ordering: an
    unrecognized (but present) symlink shape is evidence of hand
    configuration and is reported on its own, before the value-agreement
    checks below ever run -- mirrors ``init``'s own "refuse before any
    further write" precedence, translated to "report before any further
    comparison" for this read-only command.
    """
    if raw_link_target is not None and link_slug is None:
        return f"unrecognized planning-artifacts symlink target {str(raw_link_target)!r}"
    if marker_slug is not None and link_slug is not None and marker_slug != link_slug:
        return f"marker says {marker_slug!r} but symlink says {link_slug!r}"
    if branch_slug is not None:
        if marker_slug is not None and marker_slug != branch_slug:
            return f"marker says {marker_slug!r} but branch says {branch_slug!r}"
        if link_slug is not None and link_slug != branch_slug:
            return f"symlink says {link_slug!r} but branch says {branch_slug!r}"
    return None


def _tier3_mismatch_reason(
    *, tier3_local_realpath: Path | None, tier3_canonical_realpath: Path
) -> str | None:
    """Check 3 (module docstring). ``None`` local realpath means the home's
    Tier-3 backlink was never provisioned -- absence is not a violation."""
    if tier3_local_realpath is None:
        return None
    if tier3_local_realpath != tier3_canonical_realpath:
        return (
            f"tier-3 backlink resolves to {tier3_local_realpath} but the "
            f"canonical store is {tier3_canonical_realpath}"
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
    )
    tier3_reason = _tier3_mismatch_reason(
        tier3_local_realpath=home.tier3_local_realpath,
        tier3_canonical_realpath=home.tier3_canonical_realpath,
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
