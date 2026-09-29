"""Per-station governed tool-surface coverage (Story 18.2, FR-156 / CAP-4).

The Dream's 2026-07-28 measurement was **2 of 6** stations with realized
capability on the factory-governed surface (mason + atlas). That number was
prose until this module; coverage is now computed and published — never
hard-asserted to 100%.

Stations are the one Guild roster of eight (``pyforge.core.roster``,
Story 59.6 / CAP-137) — ``DREAM_STATIONS`` used to be a hand-kept
six-station subset that silently omitted doctor and scribe; that omission
was the defect a single shared list closes, so this module now measures
against the full roster rather than a locally-scoped copy of part of it.
A station counts as covered when it has a governed MCP tool surface under
factory ownership:

* **mason** — craft tools on ``.claude/tools/conda_forge_server.py``
* **other stations** — a package ``mcp/`` package with ``server.py`` or
  ``tools.py`` (e.g. ``pyforge.atlas.mcp``, ``pyforge.marshal.mcp``)

Warden's two scanning tools living on mason's server without a warden
``mcp/`` package stay *uncovered* under this rule — matching the Dream's
table that counted only mason + atlas toward the historical 2-of-6.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pyforge.core.roster import STATIONS as DREAM_STATIONS


@dataclass(frozen=True, slots=True)
class StationCoverage:
    """One station's governed-surface presence."""

    name: str
    covered: bool
    evidence: str


def resolve_repo_root(start: Path | None = None) -> Path:
    """Walk parents from ``start`` (default: this file) to the repo root."""
    here = Path(start) if start is not None else Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pixi.toml").is_file() and (parent / ".claude").is_dir():
            return parent
    raise FileNotFoundError(f"could not locate repo root (pixi.toml + .claude) from {here}")


def _package_mcp_dir(repo_root: Path, station: str) -> Path:
    return repo_root / "src" / "shared" / "packages" / f"pyforge-{station}" / "src" / "pyforge" / station / "mcp"


def station_governed_surface(
    station: str,
    *,
    repo_root: Path | None = None,
) -> StationCoverage:
    """Detect whether ``station`` has a factory-governed MCP tool surface."""
    if repo_root is not None and not str(repo_root).strip():
        raise ValueError("repo_root must be non-empty")
    root = resolve_repo_root() if repo_root is None else Path(repo_root)
    if station == "mason":
        craft = root / ".claude" / "tools" / "conda_forge_server.py"
        if craft.is_file():
            return StationCoverage(
                name=station,
                covered=True,
                evidence=str(craft.relative_to(root)),
            )
        return StationCoverage(
            name=station,
            covered=False,
            evidence="missing .claude/tools/conda_forge_server.py",
        )

    mcp_dir = _package_mcp_dir(root, station)
    for leaf in ("server.py", "tools.py"):
        candidate = mcp_dir / leaf
        if candidate.is_file():
            return StationCoverage(
                name=station,
                covered=True,
                evidence=str(candidate.relative_to(root)),
            )
    return StationCoverage(
        name=station,
        covered=False,
        evidence=f"no package mcp/ under pyforge-{station}",
    )


def tool_surface_coverage_report(
    *,
    stations: Sequence[str] | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Publish per-station coverage as a structured number (FR-156).

    Returns ``covered / total`` as ``coverage`` (float in ``[0, 1]``) plus
    the integer counts and per-station rows. Callers must not treat
    ``coverage == 1.0`` as a gate — measurement is the contract.
    """
    if repo_root is not None and not str(repo_root).strip():
        raise ValueError("repo_root must be non-empty")
    root = resolve_repo_root() if repo_root is None else Path(repo_root)
    # Preserve order; drop duplicates so coverage cannot be inflated.
    raw: Iterable[str] = DREAM_STATIONS if stations is None else stations
    names = list(dict.fromkeys(raw))
    rows = [station_governed_surface(name, repo_root=root) for name in names]
    total = len(rows)
    covered = sum(1 for row in rows if row.covered)
    coverage = (covered / total) if total else 0.0
    return {
        "ok": True,
        "total": total,
        "covered": covered,
        "coverage": coverage,
        "ratio": f"{covered}/{total}",
        "stations": [asdict(row) for row in rows],
        "repo_root": str(root),
    }


def format_coverage_report(report: Mapping[str, Any] | None = None) -> str:
    """Pretty-print a coverage report (JSON) for humans / CI logs."""
    payload = tool_surface_coverage_report() if report is None else report
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main() -> None:
    """``python -m pyforge.marshal.mcp.coverage`` — print the coverage number."""
    print(format_coverage_report(), end="")


if __name__ == "__main__":
    main()
