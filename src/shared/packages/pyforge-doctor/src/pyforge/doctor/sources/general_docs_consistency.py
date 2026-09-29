"""General documentation identity gather (Story 22.3, ``spec-general-docs-consistency`` CAP-3).

Cross-references human-facing documentation claims — station ``README.md`` vs
``.claude/skills/*/skill-brief.yaml``, ``AGENTS.md`` vs a station Dream — and
flags quotable divergences. Bounded, textual, evidence-based (never inferred).
Warn-only, fail-open — never a second PR gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = (
    "gather",
    "check_agents_herald_handoff",
    "check_station_readme_vs_skill_brief",
    "find_station_gate_advisory_contradictions",
    "find_agents_herald_marshal_contradiction",
    "iter_pyforge_station_surfaces",
)

_CHECK_STATION_GATE = "general-docs-station-gate-advisory"
_CHECK_AGENTS_HERALD = "general-docs-agents-herald-marshal"
_CHECK_UNREADABLE = "general-docs-unreadable"

_README_SELF_GATE_RE = re.compile(
    r"\bits\s+own\s+exit-code\s+gate\b|"
    r"\bacting\s+as\s+a\s+strict\s+CI/CD\s+exit-code\s+gate\b",
    re.IGNORECASE,
)
_SKILL_BRIEF_ADVISORY_RE = re.compile(
    r"Findings\s+stay\s+advisory\s*[—\-–]\s*not\s+a\s+second\s+PR\s+gate|"
    r"not\s+a\s+second\s+PR\s+gate",
    re.IGNORECASE,
)

_AGENTS_HERALD_HANDOFF_RE = re.compile(
    r"Dream\s*→\s*spec\s+handoff\s+portable\s+across\s+agents\s+is\s+\*\*Herald'?s?\*\*",
    re.IGNORECASE,
)
_HERALD_DREAM_MARSHAL_RE = re.compile(
    r"cross-agent\s+portability\s+belong(?:s)?\s+to\s+\[\[pyforge-marshal\]\]",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class StationSurface:
    station: str
    readme_path: Path
    skill_brief_path: Path


@dataclass(frozen=True)
class QuotedSide:
    rel_path: str
    line_no: int
    line_text: str


def _rel_path(path: Path, target: Path) -> str:
    try:
        return path.relative_to(target).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path, *, target: Path) -> tuple[str | None, Finding | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        rel = _rel_path(path, target)
        return None, Finding(
            source=Source.GENERAL_DOCS_CONSISTENCY,
            check=_CHECK_UNREADABLE,
            status=DoctorStatus.WARN,
            message=(f"{rel} could not be read — {exc.__class__.__name__}: {exc}"),
            evidence={"path": rel, "reason": str(exc)},
        )


def _quote_for_pattern(
    text: str,
    pattern: re.Pattern[str],
    *,
    rel_path: str,
) -> QuotedSide | None:
    match = pattern.search(text)
    if not match:
        return None
    start = match.start()
    line_no = text.count("\n", 0, start) + 1
    matched = re.sub(r"\s+", " ", match.group(0)).strip()
    line_text = text.splitlines()[line_no - 1].rstrip()
    if matched not in line_text:
        line_text = matched
    return QuotedSide(rel_path=rel_path, line_no=line_no, line_text=line_text)


def iter_pyforge_station_surfaces(target: Path) -> tuple[StationSurface, ...]:
    """Every ``pyforge-*`` package with both README and skill-brief present."""
    packages_root = target / "src" / "shared" / "packages"
    if not packages_root.is_dir():
        return ()
    surfaces: list[StationSurface] = []
    for package_dir in sorted(packages_root.iterdir()):
        if not package_dir.is_dir() or not package_dir.name.startswith("pyforge-"):
            continue
        readme = package_dir / "README.md"
        brief = target / ".claude" / "skills" / package_dir.name / "skill-brief.yaml"
        if readme.is_file() and brief.is_file():
            station = package_dir.name.removeprefix("pyforge-")
            surfaces.append(
                StationSurface(
                    station=station,
                    readme_path=readme,
                    skill_brief_path=brief,
                )
            )
    return tuple(surfaces)


def check_station_readme_vs_skill_brief(
    *,
    station: str,
    readme_text: str,
    skill_brief_text: str,
    readme_rel: str,
    brief_rel: str,
    source: Source,
) -> Finding | None:
    """Return a WARN when README claims a self-gate while the brief is advisory."""
    readme_hit = _quote_for_pattern(readme_text, _README_SELF_GATE_RE, rel_path=readme_rel)
    brief_hit = _quote_for_pattern(skill_brief_text, _SKILL_BRIEF_ADVISORY_RE, rel_path=brief_rel)
    if readme_hit is None or brief_hit is None:
        return None
    readme_quote = readme_hit
    brief_quote = brief_hit
    return Finding(
        source=source,
        check=_CHECK_STATION_GATE,
        status=DoctorStatus.WARN,
        message=(
            f"{readme_quote.rel_path}:{readme_quote.line_no} claims "
            f"{readme_quote.line_text!r} while {brief_quote.rel_path}:"
            f"{brief_quote.line_no} reads {brief_quote.line_text!r}"
        ),
        evidence={
            "station": station,
            "readme_path": readme_quote.rel_path,
            "readme_line": readme_quote.line_no,
            "readme_quote": readme_quote.line_text,
            "skill_brief_path": brief_quote.rel_path,
            "skill_brief_line": brief_quote.line_no,
            "skill_brief_quote": brief_quote.line_text,
        },
    )


def find_station_gate_advisory_contradictions(
    target: Path,
    *,
    source: Source = Source.GENERAL_DOCS_CONSISTENCY,
) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for surface in iter_pyforge_station_surfaces(target):
        readme_rel = _rel_path(surface.readme_path, target)
        brief_rel = _rel_path(surface.skill_brief_path, target)
        readme_text, unreadable = _read_text(surface.readme_path, target=target)
        if unreadable is not None:
            findings.append(unreadable)
            continue
        brief_text, unreadable = _read_text(surface.skill_brief_path, target=target)
        if unreadable is not None:
            findings.append(unreadable)
            continue
        assert readme_text is not None and brief_text is not None
        finding = check_station_readme_vs_skill_brief(
            station=surface.station,
            readme_text=readme_text,
            skill_brief_text=brief_text,
            readme_rel=readme_rel,
            brief_rel=brief_rel,
            source=source,
        )
        if finding is not None:
            findings.append(finding)
    return tuple(findings)


def check_agents_herald_handoff(
    *,
    agents_text: str,
    herald_dream_text: str,
    agents_rel: str,
    dream_rel: str,
    source: Source,
) -> Finding | None:
    """Return a WARN when AGENTS assigns Herald a claim Herald's Dream gives Marshal."""
    agents_hit = _quote_for_pattern(agents_text, _AGENTS_HERALD_HANDOFF_RE, rel_path=agents_rel)
    dream_hit = _quote_for_pattern(herald_dream_text, _HERALD_DREAM_MARSHAL_RE, rel_path=dream_rel)
    if agents_hit is None or dream_hit is None:
        return None
    agents_quote = agents_hit
    dream_quote = dream_hit
    return Finding(
        source=source,
        check=_CHECK_AGENTS_HERALD,
        status=DoctorStatus.WARN,
        message=(
            f"{agents_quote.rel_path}:{agents_quote.line_no} reads "
            f"{agents_quote.line_text!r} while {dream_quote.rel_path}:"
            f"{dream_quote.line_no} reads {dream_quote.line_text!r}"
        ),
        evidence={
            "agents_path": agents_quote.rel_path,
            "agents_line": agents_quote.line_no,
            "agents_quote": agents_quote.line_text,
            "dream_path": dream_quote.rel_path,
            "dream_line": dream_quote.line_no,
            "dream_quote": dream_quote.line_text,
        },
    )


def find_agents_herald_marshal_contradiction(
    target: Path,
    *,
    source: Source = Source.GENERAL_DOCS_CONSISTENCY,
) -> tuple[Finding, ...]:
    agents_path = target / "AGENTS.md"
    dream_path = target / "docs" / "dreams" / "pyforge-herald.md"
    if not agents_path.is_file() or not dream_path.is_file():
        return ()
    agents_text, unreadable = _read_text(agents_path, target=target)
    if unreadable is not None:
        return (unreadable,)
    dream_text, unreadable = _read_text(dream_path, target=target)
    if unreadable is not None:
        return (unreadable,)
    assert agents_text is not None and dream_text is not None
    finding = check_agents_herald_handoff(
        agents_text=agents_text,
        herald_dream_text=dream_text,
        agents_rel=_rel_path(agents_path, target),
        dream_rel=_rel_path(dream_path, target),
        source=source,
    )
    return (finding,) if finding is not None else ()


def _gather_all(target: Path) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    findings.extend(find_station_gate_advisory_contradictions(target))
    findings.extend(find_agents_herald_marshal_contradiction(target))
    if findings:
        return tuple(findings)
    return (
        Finding(
            source=Source.GENERAL_DOCS_CONSISTENCY,
            check="general-docs-consistency",
            status=DoctorStatus.OK,
            message="no general documentation identity contradictions",
            evidence={"scanned_stations": len(iter_pyforge_station_surfaces(target))},
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """General-docs identity gather — Story 22.3 / CAP-3."""
    return degrade_on_exception(
        Source.GENERAL_DOCS_CONSISTENCY,
        "general-docs-consistency",
        lambda: _gather_all(target),
    )
