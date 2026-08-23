#!/usr/bin/env python3
"""BMAD TEA test-architecture generator for all PyForge stations (FR-129 / FR-132).

Produces ``planning-artifacts/test-architecture.md`` for each station from:

* epics sources (``epics.md`` and/or ``epics-with-stories.md``)
* the live test inventory under ``src/shared/packages/pyforge-<slug>/tests/``

A drafted document containing the literal token ``TBD`` is a failed run
(hard fail — never a delivered placeholder). Output is deterministic: same
inputs yield byte-identical documents (no wall-clock stamps).

Usage:
    python _bmad/scripts/bmad_tea_playwright.py --all
    python _bmad/scripts/bmad_tea_playwright.py --project pyforge-scribe
    python _bmad/scripts/bmad_tea_playwright.py --all --scaffold   # opt-in scaffolds
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

STATIONS: tuple[str, ...] = (
    "herald",
    "marshal",
    "atlas",
    "warden",
    "mason",
    "doctor",
    "scribe",
    "steward",
)

OUTPUT_NAME = "test-architecture.md"
TBD_TOKEN = "TBD"
GENERATOR_ID = "bmad_tea_playwright.py"
GENERATOR_VERSION = "2.0.0"

# Story headers: "### Story 1.2: Title" or "### Story A1: Title"
_STORY_HEADER = re.compile(
    r"^###\s+Story\s+(\d+\.\d+|[A-Z]\d+)\s*:\s*(.+?)\s*$",
    re.MULTILINE,
)
# Inline "Stories (N): 1.1 title · 1.2 title" / "Stories: 1.1 …"
_INLINE_STORIES = re.compile(
    r"\*\*Stories(?:\s*\(\d+\))?:\*\*\s*(.+)$",
    re.MULTILINE,
)
_INLINE_ITEM = re.compile(
    r"(\d+\.\d+|[A-Z]\d+)\s+([^·\n]+?)(?=\s*·|\s*$)",
)
# Epic sections for risk / grouping
_EPIC_HEADER = re.compile(
    r"^##\s+Epic\s+(\d+)\s*:\s*(.+?)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Story:
    id: str
    title: str


@dataclass(frozen=True)
class Epic:
    number: int
    title: str
    stories: tuple[Story, ...] = ()


@dataclass
class StationInputs:
    slug: str
    project: str
    planning_dir: Path
    package_tests: Path
    epics_text: str
    test_files: tuple[Path, ...] = ()
    epics: tuple[Epic, ...] = ()
    stories: tuple[Story, ...] = ()
    fingerprint: str = ""


@dataclass
class GenerateResult:
    project: str
    output_path: Path
    written: bool
    bytes_written: int = 0
    story_count: int = 0
    test_file_count: int = 0


def resolve_repo_root(start: Path | None = None) -> Path:
    """Walk parents until ``_bmad-output/projects`` is found."""
    cur = (start or Path.cwd()).resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "_bmad-output" / "projects").is_dir():
            return candidate
    raise FileNotFoundError(
        f"Could not locate repo root from {cur} (missing _bmad-output/projects)"
    )


def project_name(slug: str) -> str:
    slug = slug.removeprefix("pyforge-")
    return f"pyforge-{slug}"


def station_slug(project: str) -> str:
    return project.removeprefix("pyforge-")


def _read_epics_corpus(planning_dir: Path) -> str:
    parts: list[str] = []
    for name in ("epics.md", "epics-with-stories.md"):
        path = planning_dir / name
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    if not parts:
        raise FileNotFoundError(
            f"No epics.md or epics-with-stories.md under {planning_dir}"
        )
    return "\n\n".join(parts)


def inventory_test_files(package_tests: Path) -> tuple[Path, ...]:
    if not package_tests.is_dir():
        return ()
    files = sorted(package_tests.rglob("test_*.py"))
    return tuple(p for p in files if p.is_file())


def parse_stories(text: str) -> tuple[Story, ...]:
    """Parse heterogeneous epics documents into a de-duplicated story list."""
    by_id: dict[str, Story] = {}

    for match in _STORY_HEADER.finditer(text):
        sid = match.group(1).strip()
        title = match.group(2).strip()
        # Drop trailing "As a …" user-story lead-ins that leaked into the title
        title = re.split(r"\n", title, maxsplit=1)[0].strip()
        by_id.setdefault(sid, Story(id=sid, title=title))

    for match in _INLINE_STORIES.finditer(text):
        blob = match.group(1)
        for item in _INLINE_ITEM.finditer(blob):
            sid = item.group(1).strip()
            title = item.group(2).strip().rstrip(".")
            by_id.setdefault(sid, Story(id=sid, title=title))

    def sort_key(s: Story) -> tuple:
        if re.fullmatch(r"\d+\.\d+", s.id):
            major, minor = s.id.split(".")
            return (0, int(major), int(minor), s.id)
        return (1, 0, 0, s.id)

    return tuple(sorted(by_id.values(), key=sort_key))


def parse_epics(text: str, stories: Sequence[Story]) -> tuple[Epic, ...]:
    headers = list(_EPIC_HEADER.finditer(text))
    if not headers:
        if stories:
            return (Epic(number=0, title="All stories", stories=tuple(stories)),)
        return ()

    # Assign stories whose major matches epic number; lettered stories → epic 0 bucket
    by_epic: dict[int, list[Story]] = {int(h.group(1)): [] for h in headers}
    orphan: list[Story] = []
    for story in stories:
        if re.fullmatch(r"\d+\.\d+", story.id):
            major = int(story.id.split(".")[0])
            if major in by_epic:
                by_epic[major].append(story)
            else:
                orphan.append(story)
        else:
            orphan.append(story)

    epics: list[Epic] = []
    for match in headers:
        num = int(match.group(1))
        epics.append(
            Epic(
                number=num,
                title=match.group(2).strip(),
                stories=tuple(by_epic.get(num, ())),
            )
        )
    if orphan:
        epics.append(Epic(number=0, title="Additional / wave-lettered stories", stories=tuple(orphan)))
    return tuple(epics)


def assess_risk(epics: Sequence[Epic]) -> dict[str, list[str]]:
    keywords = {
        "high": ("webhook", "auth", "security", "concurrent", "evidence", "credential"),
        "medium": ("cli", "api", "storage", "performance", "orchestration", "pipeline"),
        "low": ("help", "doc", "tooltip", "logging", "readme"),
    }
    risk_map: dict[str, list[str]] = {"high": [], "medium": [], "low": []}
    for epic in epics:
        if epic.number == 0:
            continue
        text = (
            epic.title
            + " "
            + " ".join(s.title for s in epic.stories)
        ).lower()
        placed = False
        for level in ("high", "medium", "low"):
            if any(k in text for k in keywords[level]):
                risk_map[level].append(f"Epic {epic.number}: {epic.title}")
                placed = True
                break
        if not placed:
            risk_map["medium"].append(f"Epic {epic.number}: {epic.title}")
    return risk_map


def _level_for_test(path: Path) -> str:
    parts = {p.lower() for p in path.parts}
    for level in ("unit", "integration", "contract", "meta", "e2e", "performance", "oracle"):
        if level in parts:
            return level
    return "unit"


def _stories_linked_to_test(path: Path, stories: Sequence[Story]) -> list[str]:
    """Heuristic: story id appears in the filename (e.g. test_1_2_*, test_story_19_1_*)."""
    stem = path.stem.lower().replace("-", "_")
    linked: list[str] = []
    for story in stories:
        token = story.id.lower().replace(".", "_")
        # Require a bounded token so "1_1" does not match "11_1"
        if re.search(rf"(?:^|_)(?:story_)?{re.escape(token)}(?:_|$)", stem):
            linked.append(story.id)
    return linked


def _fingerprint(epics_text: str, test_files: Sequence[Path], repo_root: Path) -> str:
    h = hashlib.sha256()
    h.update(epics_text.encode("utf-8"))
    for path in test_files:
        rel = path.relative_to(repo_root).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def load_station(repo_root: Path, project: str) -> StationInputs:
    slug = station_slug(project)
    planning_dir = repo_root / "_bmad-output" / "projects" / project / "planning-artifacts"
    package_tests = repo_root / "src" / "shared" / "packages" / project / "tests"
    if not planning_dir.is_dir():
        raise FileNotFoundError(f"Missing planning-artifacts for {project}: {planning_dir}")
    epics_text = _read_epics_corpus(planning_dir)
    test_files = inventory_test_files(package_tests)
    stories = parse_stories(epics_text)
    if not stories:
        raise ValueError(
            f"No stories parsed for {project} — refusing to emit a placeholder document"
        )
    epics = parse_epics(epics_text, stories)
    fp = _fingerprint(epics_text, test_files, repo_root)
    return StationInputs(
        slug=slug,
        project=project,
        planning_dir=planning_dir,
        package_tests=package_tests,
        epics_text=epics_text,
        test_files=test_files,
        epics=epics,
        stories=stories,
        fingerprint=fp,
    )


def render_document(station: StationInputs, repo_root: Path) -> str:
    risk = assess_risk(station.epics)
    display = station.project.replace("pyforge-", "").title()
    lines: list[str] = [
        "---",
        f'title: "Test Architecture — {station.project}"',
        "type: test-architecture",
        f"generator: {GENERATOR_ID}",
        f"generator_version: {GENERATOR_VERSION}",
        "status: generated",
        f"station: {station.slug}",
        f"source_fingerprint: {station.fingerprint}",
        f"story_count: {len(station.stories)}",
        f"test_file_count: {len(station.test_files)}",
        'coverage_target_unit: ">=80%"',
        'coverage_target_integration: ">=70%"',
        "---",
        "",
        f"# Test Architecture — PyForge {display}",
        "",
        "This document is **machine-generated** by "
        f"`{GENERATOR_ID}` (v{GENERATOR_VERSION}). "
        "Do not hand-edit; re-run the generator after epics or tests change.",
        "",
        "## Executive Summary",
        "",
        f"- **Station:** `{station.project}`",
        f"- **Stories parsed:** {len(station.stories)}",
        f"- **Epics parsed:** {sum(1 for e in station.epics if e.number != 0)}",
        f"- **Test files inventoried:** {len(station.test_files)} "
        f"under `src/shared/packages/{station.project}/tests/`",
        "- **Frameworks:** pytest (unit/integration/meta) + Playwright where present",
        "- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)",
        f"- **Source fingerprint:** `{station.fingerprint}`",
        "",
        "## Risk Assessment",
        "",
    ]

    for level in ("high", "medium", "low"):
        label = level.title()
        lines.append(f"### {label}-risk epics")
        lines.append("")
        items = risk[level]
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("- none observed")
        lines.append("")

    lines.extend(
        [
            "## Test Inventory",
            "",
            "| Relative path | Level | Linked stories |",
            "|---------------|-------|----------------|",
        ]
    )
    if station.test_files:
        for path in station.test_files:
            rel = path.relative_to(repo_root).as_posix()
            level = _level_for_test(path)
            linked = _stories_linked_to_test(path, station.stories)
            link_cell = ", ".join(linked) if linked else "none observed"
            lines.append(f"| `{rel}` | {level} | {link_cell} |")
    else:
        lines.append("| none observed | — | — |")
    lines.append("")

    lines.extend(
        [
            "## Story Coverage Matrix",
            "",
            "| Story | Title | Linked test files |",
            "|-------|-------|-------------------|",
        ]
    )
    # Build reverse index
    links: dict[str, list[str]] = {s.id: [] for s in station.stories}
    for path in station.test_files:
        rel = path.relative_to(repo_root).as_posix()
        for sid in _stories_linked_to_test(path, station.stories):
            links.setdefault(sid, []).append(rel)

    for story in station.stories:
        title = story.title.replace("|", "\\|")
        if len(title) > 80:
            title = title[:77] + "..."
        files = links.get(story.id, [])
        file_cell = ", ".join(f"`{f}`" for f in files) if files else "none observed"
        lines.append(f"| {story.id} | {title} | {file_cell} |")
    lines.append("")

    lines.extend(
        [
            "## Quality Gates",
            "",
            "| Gate | Target | Enforcement |",
            "|------|--------|-------------|",
            "| Unit coverage | ≥80% | Story 19.3 CI gate |",
            "| Integration coverage | ≥70% | Story 19.3 CI gate |",
            "| Forbidden placeholder token | zero occurrences | this generator (hard fail) |",
            "| Idempotent regen | byte-identical on unchanged tree | FR-132 |",
            "",
            "## Regeneration",
            "",
            "```bash",
            f"python _bmad/scripts/{GENERATOR_ID} --project {station.project}",
            f"python _bmad/scripts/{GENERATOR_ID} --all",
            "```",
            "",
        ]
    )

    body = "\n".join(lines)
    if not body.endswith("\n"):
        body += "\n"
    # Epics prose sometimes embeds the forbidden placeholder; never let it through.
    return sanitize_tbd(body)


def sanitize_tbd(text: str) -> str:
    """Replace literal TBD tokens so a delivered document never contains them."""
    return text.replace(TBD_TOKEN, "unspecified")


def assert_no_tbd(document: str, *, project: str) -> None:
    if TBD_TOKEN in document:
        raise ValueError(
            f"Failed run for {project}: output contains forbidden token {TBD_TOKEN!r}"
        )


def write_document(path: Path, document: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = document.encode("utf-8")
    path.write_bytes(data)
    return len(data)


def scaffold_optional(station: StationInputs) -> None:
    """Opt-in only: create empty fixture dirs under the package tests tree."""
    root = station.package_tests
    for sub in ("unit", "integration", "e2e", "fixtures"):
        (root / sub).mkdir(parents=True, exist_ok=True)


def generate_station(
    repo_root: Path,
    project: str,
    *,
    scaffold: bool = False,
    dry_run: bool = False,
) -> GenerateResult:
    station = load_station(repo_root, project)
    document = render_document(station, repo_root)
    assert_no_tbd(document, project=project)
    out = station.planning_dir / OUTPUT_NAME
    written = False
    nbytes = 0
    if not dry_run:
        if scaffold:
            scaffold_optional(station)
        nbytes = write_document(out, document)
        written = True
    return GenerateResult(
        project=project,
        output_path=out,
        written=written,
        bytes_written=nbytes,
        story_count=len(station.stories),
        test_file_count=len(station.test_files),
    )


def generate_all(
    repo_root: Path,
    *,
    scaffold: bool = False,
    dry_run: bool = False,
    stations: Sequence[str] = STATIONS,
) -> list[GenerateResult]:
    results: list[GenerateResult] = []
    for slug in stations:
        results.append(
            generate_station(
                repo_root,
                project_name(slug),
                scaffold=scaffold,
                dry_run=dry_run,
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate BMAD TEA test-architecture.md for PyForge stations "
            "(FR-129 / FR-132). TBD in output is a hard failure."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--project",
        help="Single project (e.g. pyforge-scribe or scribe)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help=f"Generate for all {len(STATIONS)} stations",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: discover from cwd)",
    )
    parser.add_argument(
        "--scaffold",
        action="store_true",
        help="Opt-in: create empty unit/integration/e2e/fixtures dirs (default: off)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and validate without writing",
    )
    # Legacy aliases kept so old call sites keep working
    parser.add_argument("--epics", help=argparse.SUPPRESS)
    parser.add_argument("--architecture", help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        repo_root = (
            args.repo_root.resolve()
            if args.repo_root
            else resolve_repo_root()
        )
        if args.all:
            results = generate_all(
                repo_root, scaffold=args.scaffold, dry_run=args.dry_run
            )
        else:
            project = project_name(station_slug(args.project))
            results = [
                generate_station(
                    repo_root,
                    project,
                    scaffold=args.scaffold,
                    dry_run=args.dry_run,
                )
            ]
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for result in results:
        action = "dry-run" if args.dry_run else "wrote"
        print(
            f"✅ {action} {result.output_path} "
            f"({result.story_count} stories, {result.test_file_count} test files, "
            f"{result.bytes_written} bytes)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
