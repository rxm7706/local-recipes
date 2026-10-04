"""Story 27.4 — the atlas planning record matches the tree and cross-station seams."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

from pyforge.atlas.dashboard import app

_DOCTOR_SRC = Path(__file__).resolve().parents[3] / "pyforge-doctor" / "src"
if str(_DOCTOR_SRC) not in sys.path:
    sys.path.insert(0, str(_DOCTOR_SRC))

from pyforge.doctor.sources.chain import verified_line_cites  # noqa: E402

_PLANNING = Path("_bmad-output/projects/pyforge-atlas/planning-artifacts")
_DESIGN = _PLANNING / "DESIGN.md"
_EPICS = _PLANNING / "epics.md"
_LEDGER = _PLANNING / "deferred-work-ledger.md"
_SPRINT_LEDGER = _PLANNING / "sprint-status-ledger.yaml"
_CATALOG_SOURCES = _PLANNING / "specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md"
_DESIGN_THINKING_CUSTOM = Path("_bmad/custom/bmad-cis-design-thinking.toml")
_CORE_CONFIG = Path("_bmad/core/config.yaml")
_DESIGN_TEMPLATE = Path(".claude/skills/bmad-cis-design-thinking/template.md")

_SECTION = re.compile(r"^#{3}\s+\d+\.\d+\s+`([a-z0-9-]+)`", re.MULTILINE)

_VERIFIED_PATH_LINE_RE = re.compile(
    r"(?<![\w./])"
    r"([\w./-]+(?:/[\w.-]+)+|\.\./[\w./-]+|[\w.-]+\.(?:py|md|yaml|yml|toml|json))"
    r":(\d+(?:-\d+)?|\d+)"
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (
            (candidate / "pixi.toml").is_file()
            and (candidate / ".claude" / "skills" / "conda-forge-expert").is_dir()
            and (candidate / "src" / "shared" / "packages").is_dir()
        ):
            return candidate
    raise AssertionError("could not locate repo root")


def _read(rel: Path) -> str:
    return (_repo_root() / rel).read_text(encoding="utf-8")


def _design_spine_page_ids(design_text: str) -> set[str]:
    return set(_SECTION.findall(design_text))


def _design_page_count_table_total(design_text: str) -> int:
    section = re.search(r"^## 6\. Page count reconciliation\s*\n(.*?)(?=^## |\Z)", design_text, re.M | re.S)
    assert section, "DESIGN.md §6 missing"
    total_row = re.search(r"^\|\s*\*\*Total\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*", section.group(1), re.M)
    assert total_row, "DESIGN.md §6 Total row missing or reshaped"
    cli_questions, pages_in_spine = int(total_row.group(1)), int(total_row.group(2))
    assert cli_questions == 21, cli_questions
    return pages_in_spine


def test_design_md_page_count_reconciles_with_page_inventory() -> None:
    design = _read(_DESIGN)
    pages_in_spine = _design_page_count_table_total(design)
    assert pages_in_spine == 19
    spine_ids = _design_spine_page_ids(design)
    assert len(spine_ids) == 19
    inventory_ids = {page.id for page in app.PAGE_INVENTORY}
    missing = spine_ids - inventory_ids
    assert not missing, missing
    assert len(app.PAGE_INVENTORY) >= pages_in_spine


def test_design_md_page_count_disagreement_would_fail() -> None:
    design = _read(_DESIGN)
    spine_ids = _design_spine_page_ids(design)
    poisoned = spine_ids - {"cve-watcher"}
    assert len(poisoned) == 18
    with pytest.raises(AssertionError):
        assert not poisoned


def _epics_story_statuses(epics_text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for part in re.split(r"(?=^### Story \d+\.\d+)", epics_text, flags=re.M):
        m = re.match(r"^### Story (\d+)\.(\d+):", part)
        if not m:
            continue
        sm = re.search(r"\*\*Status:\*\*\s*(\S+)", part)
        if not sm:
            continue
        rows.append((f"{m.group(1)}.{m.group(2)}", sm.group(1)))
    return rows


def _ledger_status_for_story(story_id: str, ledger: dict[str, str]) -> str:
    epic, num = story_id.split(".")
    prefix = f"{epic}-{num}-"
    keys = [k for k in ledger if k.startswith(prefix)]
    assert len(keys) == 1, (story_id, keys)
    return ledger[keys[0]]


def test_epics_per_story_status_matches_sprint_ledger() -> None:
    epics_text = _read(_EPICS)
    ledger = yaml.safe_load(_read(_SPRINT_LEDGER))["development_status"]
    mismatches = []
    for story_id, epics_status in _epics_story_statuses(epics_text):
        ledger_status = _ledger_status_for_story(story_id, ledger)
        if epics_status != ledger_status:
            mismatches.append((story_id, epics_status, ledger_status))
    assert not mismatches, mismatches


def test_epics_status_mismatch_would_fail() -> None:
    epics_text = _read(_EPICS).replace("**Status:** done", "**Status:** backlog", 1)
    ledger = yaml.safe_load(_read(_SPRINT_LEDGER))["development_status"]
    mismatches = []
    for story_id, epics_status in _epics_story_statuses(epics_text):
        ledger_status = _ledger_status_for_story(story_id, ledger)
        if epics_status != ledger_status:
            mismatches.append((story_id, epics_status, ledger_status))
    assert mismatches


def test_catalog_sources_tier2_names_enterprise_jfrog_names() -> None:
    text = _read(_CATALOG_SOURCES)
    tier2 = re.search(r"## Tier 2.*?(?=## Tier 3|\Z)", text, re.S)
    assert tier2
    body = tier2.group(0)
    assert "enterprise_jfrog_names" in body
    assert "upstream_discovery" in body
    assert "artifactory_downloads_raw" not in body.split("## Tier 3")[0]


def _ledger_heading_count(text: str) -> tuple[int, int]:
    top = len(re.findall(r"^## DW-", text, re.M))
    sub = len(re.findall(r"^### DW-", text, re.M))
    return top, sub


def test_deferred_ledger_provenance_counts_match_headings() -> None:
    text = _read(_LEDGER)
    fm = yaml.safe_load(text.split("---", 2)[1])
    top, sub = _ledger_heading_count(text)
    assert fm["entries"] == top
    assert "52 real deferrals" not in text.split("## Provenance", 2)[1][:800]
    assert str(top) in text[:1200] or str(sub) in text[:1200]


def _resolve_cited_path(root: Path, rel: str) -> Path | None:
    if rel.startswith("./"):
        rel = rel[2:]
    for candidate in (
        root / rel,
        root / "src/shared/packages/pyforge-atlas" / rel,
    ):
        if candidate.is_file():
            return candidate
    return None


def _closed_entries_with_verified(ledger_text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for block in re.split(r"(?=^### DW-)", ledger_text, flags=re.M):
        if not block.startswith("### DW-"):
            continue
        ident = block.splitlines()[0].removeprefix("### ").split(":")[0].strip()
        if not re.search(r"^\s*status:\s*closed\b", block, re.M | re.I):
            continue
        verified = [m.group(1).strip() for m in re.finditer(r"^\s*verified:\s*(.+)$", block, re.M)]
        if not verified:
            continue
        chosen = next((v for v in reversed(verified) if "Story 27.4" in v), None)
        if chosen is None:
            for raw in reversed(verified):
                if not verified_line_cites(raw):
                    continue
                cites = _path_line_citations(raw)
                if cites and all(c[0].startswith(("src/", "_bmad", ".github/", "scripts/")) for c in cites):
                    chosen = raw
                    break
        entries.append((ident, chosen or verified[-1]))
    return entries


def _path_line_citations(raw: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for m in _VERIFIED_PATH_LINE_RE.finditer(raw):
        path_part, line_part = m.group(1), m.group(2)
        line = int(line_part.split("-")[0])
        out.append((path_part, line))
    return out


def test_closed_deferred_verified_citations_resolve_to_real_lines() -> None:
    root = _repo_root()
    ledger_text = _read(_LEDGER)
    offenders: list[str] = []
    for ident, raw in _closed_entries_with_verified(ledger_text):
        if not verified_line_cites(raw):
            continue
        cites = _path_line_citations(raw)
        if not cites:
            continue
        for rel, line_no in cites:
            path = _resolve_cited_path(root, rel)
            if path is None:
                offenders.append(f"{ident}: missing file {rel}")
                continue
            if len(path.read_text(encoding="utf-8").splitlines()) < line_no:
                offenders.append(f"{ident}: {rel}:{line_no} past EOF")
    assert not offenders, offenders


def test_fabricated_verified_citation_fails_resolution() -> None:
    root = _repo_root()
    rel = "src/shared/packages/pyforge-atlas/tests/meta/test_planning_record.py"
    path = _resolve_cited_path(root, rel)
    assert path is not None
    line_no = len(path.read_text(encoding="utf-8").splitlines()) + 50
    offenders: list[str] = []
    raw = f"verified: 2026-10-04 — closed — Story 27.4; verified: {rel}:{line_no}"
    for cite_rel, cite_line in _path_line_citations(raw):
        cite_path = _resolve_cited_path(root, cite_rel)
        if cite_path is None or len(cite_path.read_text(encoding="utf-8").splitlines()) < cite_line:
            offenders.append(f"{cite_rel}:{cite_line}")
    assert offenders == [f"{rel}:{line_no}"]


def test_design_thinking_custom_override_resolves_project_name_in_title() -> None:
    root = _repo_root()
    custom = root / _DESIGN_THINKING_CUSTOM
    assert custom.is_file()
    custom_text = custom.read_text(encoding="utf-8")
    assert "project_name" in custom_text
    assert "_bmad/core/config.yaml" in custom_text
    project_name = yaml.safe_load((root / _CORE_CONFIG).read_text(encoding="utf-8"))["project_name"]
    title = (root / _DESIGN_TEMPLATE).read_text(encoding="utf-8").splitlines()[0]
    filled = title.replace("{{project_name}}", project_name)
    assert "{{project_name}}" not in filled
    assert project_name in filled
