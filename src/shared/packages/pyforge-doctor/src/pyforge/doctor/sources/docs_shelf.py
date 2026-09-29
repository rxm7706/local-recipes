"""Leftover-shelf occupancy gather (Story 23.7, ``spec-pyforge-doctor`` CAP-54).

Distinct from ``general_docs_consistency`` (Story 22.3): that module is
identity-only — README vs skill-brief, AGENTS.md vs Dream — pinned by frozen
22.3 fixtures. This module is a different detector-family member: it compares
live directory *occupancy* at two leftover-shelf-prone locations against the
allow-list ``docs/MAP.md``'s own "Outside this map" table and Story 23.2's
air-gap fold already established, so a shelf that was already cleared once
(the five files now archived under ``archive/_bmad-output/`` — Story 23.5;
the single air-gap how-to/explanation pair — Story 23.2) is caught if it
regrows. Warn-only, fail-open — never a second PR gate.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = (
    "gather",
    "find_bmad_output_root_leftovers",
    "find_extra_airgap_docs",
)

_CHECK_BMAD_OUTPUT_ROOT = "docs-shelf-bmad-output-root"
_CHECK_AIRGAP_CLUSTER = "docs-shelf-airgap-cluster"
_CHECK_CLEAN = "docs-shelf-occupancy"

# `_bmad-output/` root allow-list. docs/MAP.md's "Outside this map" table
# names `_bmad-output/projects/*/{planning,implementation}-artifacts/` as the
# only in-scope Tier 2/3 homes at this root; every other tracked entry
# living directly at `_bmad-output/` root is one of these fixed artifacts.
# The five dated campaign notes this root used to also carry
# (CHARTER-ALIGNMENT-PLAN.md, DREAM-TRIAGE-2026-08-08.md,
# FLEET-READINESS-2026-08-08.md, FLEET-RUN-2026-07-30.md,
# POLICY_COMPOSITION_README.md) already moved to `archive/_bmad-output/`
# (Story 23.5) — a NEW name appearing here is that shelf regrowing exactly
# where it was already cleared.
_BMAD_OUTPUT_ROOT_ALLOWED_NAMES = frozenset(
    {
        "projects",
        "PROJECTS.md",
        "brainstorming",
        "harness-profiles",
        "policy-defaults.toml",
        "EXEMPLAR-STANDARD.md",
        # Gitignored per-worktree symlinks (AGENTS.md multi-project switch,
        # `_bmad-output/{planning,implementation}-artifacts` -> the active
        # project) — legitimately absent on a fresh clone, legitimately
        # present in any active worktree; never a leftover.
        "planning-artifacts",
        "implementation-artifacts",
    }
)

# Story 23.2's fold left exactly one how-to and one explanation doc for
# air-gap material (docs/MAP.md's own quadrant population notes). A second
# air-gap-named file anywhere in the four Diátaxis quadrants is the cluster
# regrowing — MAP.md's own excluded layers (Dreams, docs/specs/,
# docs/intake/, docs/governance/, ...) are out of scope for this check, same
# as they are out of scope for the map itself.
_AIRGAP_ALLOWED_RELPATHS = frozenset(
    {
        "docs/how-to/air-gapped-mirror-setup.md",
        "docs/explanation/airgap-distribution-contract.md",
    }
)
_MAP_QUADRANT_DIRS = ("tutorials", "how-to", "reference", "explanation")
_AIRGAP_NAME_RE = re.compile(r"\bair[\s_-]?gap\b", re.IGNORECASE)


def find_bmad_output_root_leftovers(target: Path) -> tuple[Finding, ...]:
    """One WARN per entry directly under ``_bmad-output/`` not in the
    allow-list — non-recursive: only root occupancy is judged here."""
    root = target / "_bmad-output"
    if not root.is_dir():
        return ()
    # No try/except here -- an unexpected OSError (e.g. permission denied)
    # must propagate to gather()'s degrade_on_exception wrapper, which turns
    # it into a visible "could not be evaluated here" WARN. Swallowing it
    # locally would silently report "clean" instead.
    entries = sorted(root.iterdir())
    findings: list[Finding] = []
    for entry in entries:
        if entry.name in _BMAD_OUTPUT_ROOT_ALLOWED_NAMES:
            continue
        rel = entry.relative_to(target).as_posix()
        findings.append(
            Finding(
                source=Source.DOCS_SHELF_OCCUPANCY,
                check=_CHECK_BMAD_OUTPUT_ROOT,
                status=DoctorStatus.WARN,
                message=(f"{rel} is not in the doctor-maintained _bmad-output/ root allow-list"),
                evidence={"path": rel},
            )
        )
    return tuple(findings)


def find_extra_airgap_docs(target: Path) -> tuple[Finding, ...]:
    """One WARN per air-gap-named doc outside Story 23.2's two-file cluster,
    scanned across docs/MAP.md's own four Diátaxis quadrant directories."""
    findings: list[Finding] = []
    for quadrant in _MAP_QUADRANT_DIRS:
        quadrant_dir = target / "docs" / quadrant
        if not quadrant_dir.is_dir():
            continue
        # No try/except here -- same rationale as
        # find_bmad_output_root_leftovers above: an unexpected OSError must
        # propagate to gather()'s degrade_on_exception wrapper rather than
        # being swallowed into a silent "clean" result.
        candidates = sorted(quadrant_dir.rglob("*.md"))
        for path in candidates:
            rel = path.relative_to(target).as_posix()
            if rel in _AIRGAP_ALLOWED_RELPATHS:
                continue
            if not _AIRGAP_NAME_RE.search(path.name):
                continue
            findings.append(
                Finding(
                    source=Source.DOCS_SHELF_OCCUPANCY,
                    check=_CHECK_AIRGAP_CLUSTER,
                    status=DoctorStatus.WARN,
                    message=(f"{rel} is a second air-gap doc outside the Story 23.2 cluster"),
                    evidence={"path": rel},
                )
            )
    return tuple(findings)


def _gather_all(target: Path) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    findings.extend(find_bmad_output_root_leftovers(target))
    findings.extend(find_extra_airgap_docs(target))
    if findings:
        return tuple(findings)
    return (
        Finding(
            source=Source.DOCS_SHELF_OCCUPANCY,
            check=_CHECK_CLEAN,
            status=DoctorStatus.OK,
            message="no leftover-shelf occupancy against the MAP allow-list",
            evidence={},
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Leftover-shelf occupancy gather — Story 23.7 / CAP-54."""
    return degrade_on_exception(
        Source.DOCS_SHELF_OCCUPANCY,
        _CHECK_CLEAN,
        lambda: _gather_all(target),
    )
