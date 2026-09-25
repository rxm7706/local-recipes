"""FR-39 / canopy AD-14: 03 five-tier completeness is checkable.

Reports all eight roster stations across CLI, portal, service, skill, and
persona (denominator 8 × 5 = 40). Fails only when an **03** station is
declared complete with fewer than five. 01/02 work is outside this AD.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pyforge.core.dispatch import script_map_from_packages_root
from pyforge.core.roster import STATIONS as _ROSTER_STATIONS

TIERS: tuple[str, ...] = ("cli", "portal", "service", "skill", "persona")
# Alphabetical, not roster declaration order (Story 59.6 / CAP-137): this
# module reports a table, and a stable sort order for that table's rows is
# its own concern, independent of the one declared roster's own ordering.
STATIONS: tuple[str, ...] = tuple(sorted(_ROSTER_STATIONS))
DENOMINATOR = len(STATIONS) * len(TIERS)

# Roster drain (2026-08-26): all eight 03 stations are declared complete.
# Mason's skill cell is conda-forge-expert (Epic 11: CFE stays; no second
# recipe skill). Losing any cell fails CI.
DECLARED_COMPLETE: frozenset[str] = frozenset(STATIONS)


class FiveTierCompleteError(AssertionError):
    """An 03 station was declared complete with fewer than five tiers."""


@dataclass(frozen=True)
class WorkItem:
    """A unit of work the check may be asked about (roster or fixture)."""

    token: str
    work_class: str
    declared_complete: bool = False
    present: dict[str, bool] | None = None


@dataclass(frozen=True)
class TierPresence:
    station: str
    cells: dict[str, bool] = field(compare=False)

    def missing(self) -> tuple[str, ...]:
        return tuple(tier for tier in TIERS if not self.cells.get(tier, False))

    @property
    def complete(self) -> bool:
        return not self.missing()


@dataclass(frozen=True)
class FiveTierReport:
    matrix: tuple[TierPresence, ...]
    failures: tuple[str, ...]

    @property
    def denominator(self) -> int:
        return DENOMINATOR


def _packages_root(repo_root: Path) -> Path:
    return repo_root / "src" / "shared" / "packages"


def _portal_apps_py(repo_root: Path, station: str) -> Path:
    packages = _packages_root(repo_root)
    if station == "warden":
        return packages / "django-warden" / "src" / "django_warden_fabric" / "apps.py"
    return packages / f"django-{station}" / "src" / f"django_{station}_portal" / "apps.py"


def _only_returns_none(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = [node for node in fn.body if not isinstance(node, ast.Expr | ast.Pass)]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return False
    value = body[0].value
    return value is None or (isinstance(value, ast.Constant) and value.value is None)


def _has_real_mcp_asgi_app(apps_py: Path) -> bool:
    if not apps_py.is_file():
        return False
    tree = ast.parse(apps_py.read_text(encoding="utf-8"), filename=str(apps_py))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == "mcp_asgi_app":
            return not _only_returns_none(node)
    return False


def detect_tiers(repo_root: Path, station: str) -> dict[str, bool]:
    packages = _packages_root(repo_root)
    scripts = script_map_from_packages_root(packages) if packages.is_dir() else {}
    portal_dir = packages / f"django-{station}"
    skill_root = repo_root / ".claude" / "skills" / f"pyforge-{station}"
    persona = repo_root / ".claude" / "skills" / f"bmad-agent-{station}" / "SKILL.md"
    skill_present = skill_root.is_dir() and any(skill_root.rglob("SKILL.md"))
    # Mason 11.1: CFE is the domain skill. Do not require pyforge-mason/.
    if station == "mason":
        skill_present = (repo_root / ".claude" / "skills" / "conda-forge-expert" / "SKILL.md").is_file()
    return {
        "cli": station in scripts,
        "portal": portal_dir.is_dir(),
        "service": _has_real_mcp_asgi_app(_portal_apps_py(repo_root, station)),
        "skill": skill_present,
        "persona": persona.is_file(),
    }


def _presence_for(repo_root: Path, item: WorkItem) -> TierPresence:
    cells = dict(item.present) if item.present is not None else detect_tiers(repo_root, item.token)
    for tier in TIERS:
        cells.setdefault(tier, False)
    return TierPresence(station=item.token, cells=cells)


def _fail_message(item: WorkItem, presence: TierPresence) -> str:
    missing = ", ".join(presence.missing()) or "(none)"
    return f"03 station {item.token!r} declared complete with fewer than five tiers; missing: {missing}"


def report(
    repo_root: Path,
    *,
    extra: Sequence[WorkItem] = (),
    declared_complete: Iterable[str] | None = None,
) -> FiveTierReport:
    """Enumerate the 8×5 matrix. Extra 01/02/03 items are evaluated for
    fail-on-false-complete but are not added to the denominator.
    """
    complete = frozenset(declared_complete) if declared_complete is not None else DECLARED_COMPLETE
    roster = tuple(
        WorkItem(
            token=station,
            work_class="03",
            declared_complete=station in complete,
        )
        for station in STATIONS
    )
    matrix = tuple(_presence_for(repo_root, item) for item in roster)
    failures: list[str] = []

    def consider(item: WorkItem, presence: TierPresence) -> None:
        if item.work_class != "03":
            return
        if item.declared_complete and not presence.complete:
            failures.append(_fail_message(item, presence))

    for item, presence in zip(roster, matrix, strict=True):
        consider(item, presence)
    for item in extra:
        consider(item, _presence_for(repo_root, item))
    return FiveTierReport(matrix=matrix, failures=tuple(failures))


def check(
    repo_root: Path,
    *,
    extra: Sequence[WorkItem] = (),
    declared_complete: Iterable[str] | None = None,
) -> FiveTierReport:
    result = report(repo_root, extra=extra, declared_complete=declared_complete)
    if result.failures:
        raise FiveTierCompleteError("\n".join(result.failures))
    return result
