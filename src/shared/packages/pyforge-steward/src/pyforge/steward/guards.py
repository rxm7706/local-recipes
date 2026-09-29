"""Guard library (Story 53.4 / hub:CAP-4).

The paper's seven categories, mapped to live PyForge surfaces. Source-Grounding
is the first category added *as a library check* (copy of scribe recall AD-8).
Outcome stays absent until ``build-league-scorecard``'s measure set exists.

No Guard here is a PR verdict. Warden stays the sole gate; doctor stays
advisory. This duty is not a ``detectors`` / ``detectors-ci`` member.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .interfaces import DutyResult

# Paper seven (whitepaper Rev 9). Order is load-bearing: Source-Grounding
# is first *library* addition after the five already-mapped surfaces.
PAPER_CATEGORIES: tuple[str, ...] = (
    "algorithmic",
    "consensus",
    "expert",
    "policy_and_safety",
    "regression_and_drift",
    "source_grounding",
    "outcome",
)

FIRST_LIBRARY_CATEGORY = "source_grounding"

# Every library row: never a second PR verdict.
VERDICT = "never"

_SOURCE_RE = re.compile(r"\[source:\s*([^\]\n]+)\]")
_HUB_GUARDS_RE = re.compile(r"(?m)^hub_guards:\s*\n((?:[ \t]*-[ \t]+\S+[ \t]*\n)+)")
_GUARDS_VERBS: tuple[str, ...] = ("catalog", "lacking", "source-ground")


@dataclass(frozen=True)
class GuardEntry:
    """One paper category in the library (or an explicit gap)."""

    category: str
    in_library: bool
    surfaces: tuple[str, ...]
    blocked_on: str | None = None


LIBRARY: dict[str, GuardEntry] = {
    "algorithmic": GuardEntry(
        category="algorithmic",
        in_library=True,
        surfaces=("*-check detectors", "warden verdict lattice"),
    ),
    "consensus": GuardEntry(
        category="consensus",
        in_library=True,
        surfaces=("parallel review lenses",),
    ),
    "expert": GuardEntry(
        category="expert",
        in_library=True,
        surfaces=("bmad-loop gate_mode", "AGENTS.md operator-confirmation"),
    ),
    "policy_and_safety": GuardEntry(
        category="policy_and_safety",
        in_library=True,
        surfaces=("warden license/vuln/waiver", "marshal MRS-GATEs"),
    ),
    "regression_and_drift": GuardEntry(
        category="regression_and_drift",
        in_library=True,
        surfaces=("bmad-drift-check", "spec_surface_check.py", "doctor frozen_path"),
    ),
    "source_grounding": GuardEntry(
        category="source_grounding",
        in_library=True,
        surfaces=(
            "scribe recall AD-8",
            "steward guards source-ground (dev/review text)",
        ),
    ),
    "outcome": GuardEntry(
        category="outcome",
        in_library=False,
        surfaces=(),
        blocked_on="docs/dreams/build-league-scorecard.md",
    ),
}


@dataclass(frozen=True)
class SourceGroundResult:
    """Library check — never a process exit and never a PR gate."""

    grounded: bool
    citations: tuple[str, ...]
    reason: str | None = None


def library_gaps() -> tuple[str, ...]:
    """Paper categories that still have no library entry."""
    return tuple(name for name in PAPER_CATEGORIES if not LIBRARY[name].in_library)


def spec_gaps(declared: frozenset[str]) -> tuple[str, ...]:
    """Categories a Spec has not named as present."""
    unknown = declared - set(PAPER_CATEGORIES)
    if unknown:
        raise ValueError(f"unknown hub_guards categor(y/ies): {sorted(unknown)}")
    return tuple(name for name in PAPER_CATEGORIES if name not in declared)


def parse_hub_guards(spec_text: str) -> frozenset[str] | None:
    """Read optional ``hub_guards:`` YAML list from a Spec (or companion)."""
    match = _HUB_GUARDS_RE.search(spec_text)
    if match is None:
        return None
    names: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            names.append(stripped[1:].strip())
    return frozenset(names)


def catalog() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in PAPER_CATEGORIES:
        entry = LIBRARY[name]
        rows.append(
            {
                "category": name,
                "in_library": entry.in_library,
                "surfaces": list(entry.surfaces),
                "verdict": VERDICT,
                "blocked_on": entry.blocked_on,
                "first_library_addition": name == FIRST_LIBRARY_CATEGORY,
            }
        )
    return rows


def source_ground(text: str, repo_root: Path) -> SourceGroundResult:
    """AD-8 copy: no synthesized prose without a resolvable ``[source: path]``."""
    found = tuple(item.strip() for item in _SOURCE_RE.findall(text))
    if not found:
        return SourceGroundResult(
            grounded=False,
            citations=(),
            reason="no [source: path] citation",
        )
    resolved: list[str] = []
    for cite in found:
        path = (repo_root / cite).resolve()
        try:
            path.relative_to(repo_root.resolve())
        except ValueError:
            return SourceGroundResult(
                grounded=False,
                citations=found,
                reason=f"citation escapes repo: {cite}",
            )
        if not path.is_file():
            return SourceGroundResult(
                grounded=False,
                citations=found,
                reason=f"unresolvable citation: {cite}",
            )
        resolved.append(cite)
    return SourceGroundResult(grounded=True, citations=tuple(resolved))


class GuardsDuty:
    """``steward guards catalog|lacking|source-ground`` — Story 53.4."""

    name = "guards"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "guards_verb", None)
        if verb not in _GUARDS_VERBS:
            return DutyResult(
                ok=True,
                summary=f"guards: available verbs are {', '.join(_GUARDS_VERBS)}",
            )
        if verb == "catalog":
            rows = catalog()
            return DutyResult(
                ok=True,
                summary=json.dumps(rows, indent=2),
                details={"catalog": rows, "verdict": VERDICT},
            )
        if verb == "lacking":
            spec_path = getattr(ns, "spec", None)
            if spec_path:
                text = Path(spec_path).read_text(encoding="utf-8")
                declared = parse_hub_guards(text)
                if declared is None:
                    return DutyResult(
                        ok=False,
                        summary=f"guards lacking: no hub_guards: list in {spec_path}",
                    )
                gaps = spec_gaps(declared)
            else:
                gaps = library_gaps()
            return DutyResult(
                ok=True,
                summary=" ".join(gaps) if gaps else "(none)",
                details={"lacking": list(gaps)},
            )
        root = Path(ns.repo).resolve() if getattr(ns, "repo", None) else Path.cwd()
        text = Path(ns.text).read_text(encoding="utf-8")
        result = source_ground(text, root)
        return DutyResult(
            ok=result.grounded,
            summary=("source-ground: ok" if result.grounded else f"source-ground: {result.reason}"),
            details={
                "grounded": result.grounded,
                "citations": list(result.citations),
                "reason": result.reason,
                "verdict": VERDICT,
            },
        )
