"""Request-time reads of tracked repo artifacts (runtime-reproducible homes)."""

from __future__ import annotations

from pathlib import Path

_FRONT_DOOR = Path(__file__).resolve().parent
REPO_ROOT = _FRONT_DOOR.parents[3]


def catalog_entries(surface_id: str, root: Path | None = None) -> list[str]:
    base = root or REPO_ROOT
    mapping = {
        "dreams": _stems(base / "docs" / "dreams", "*.md"),
        "specs": _stems(base / "docs" / "specs", "*.md"),
        "story_specs": _story_specs(base),
        "guild": _stems(base / "docs" / "dreams", "*.md"),
        "backlog": _ledger_titles(base),
        "open_work": _ledger_titles(base),
        "archived": _stems(base / "docs" / "dreams", "*.md"),
        "program_story_status": _projects(base),
        "in_build_realized_membership": _projects(base),
    }
    return mapping.get(surface_id, [])


def _stems(directory: Path, pattern: str) -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(path.stem for path in directory.glob(pattern) if path.is_file())


def _story_specs(root: Path) -> list[str]:
    specs = (
        root
        / "_bmad-output"
        / "projects"
        / "pyforge-steward"
        / "planning-artifacts"
        / "specs"
    )
    return _stems(specs, "spec-*-*.md")[:40]


def _ledger_titles(root: Path) -> list[str]:
    projects = root / "_bmad-output" / "projects"
    if not projects.is_dir():
        return []
    ledgers = sorted(projects.glob("*/planning-artifacts/deferred-work-ledger.md"))
    return [ledger.parent.parent.name for ledger in ledgers]


def _projects(root: Path) -> list[str]:
    projects = root / "_bmad-output" / "projects"
    if not projects.is_dir():
        return []
    return sorted(
        path.name
        for path in projects.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
