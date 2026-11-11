"""Story 121.1 (spec-python-foundry-cutover fnd:CAP-9, spec-foundry-capability-ledger fcl:CAP-1): the capability
ledger's generator derives its rows from the live Specs and keeps every decided field.

Every tree here is a fixture under ``tmp_path``: this module never reads the repository, so it runs in steward's
package half.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from pyforge.steward import cutover_ledger as cl
from pyforge.steward.cutover_ledger import (
    CutoverLedgerError,
    LedgerReport,
    append,
    cap_id,
    extract_caps,
    live_caps,
    live_specs,
    marker,
    regenerate,
)

TODAY = date(2026, 11, 10)
SHA = "0123abcd"
LEDGER = Path("docs/foundry/capability-ledger.yaml")


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _spec(root: Path, project: str, slug: str, body: str, status: str = "status: ready") -> str:
    rel = f"_bmad-output/projects/{project}/planning-artifacts/specs/spec-{slug}/SPEC.md"
    _write(root, rel, f"---\nspec: {slug}\n{status}\n---\n\n# SPEC\n\n## Capabilities\n\n{body}\n")
    return rel


def _ledger(root: Path, rows: list[dict[str, Any]], **extra: Any) -> Path:
    doc: dict[str, Any] = {"schema": "pyforge.capability-ledger/v1", "capabilities": rows, **extra}
    return _write(root, LEDGER.as_posix(), yaml.safe_dump(doc, sort_keys=False))


def _rows(root: Path) -> dict[str, dict[str, Any]]:
    data = yaml.safe_load((root / LEDGER).read_text(encoding="utf-8"))
    return {row["id"]: row for row in data["capabilities"]}


def _regen(root: Path) -> LedgerReport:
    return regenerate(root, LEDGER, today=TODAY, source_sha=SHA)


ATLAS = (
    "- **CAP-1 — the DAG is the orchestrator.** (shipped 2026-09-09)\n"
    "  - **intent:** one plane.\n"
    "  - **success:** it runs.\n"
    "- **CAP-2 — all IO is catalog-declared.** (ready 2026-10-18)\n"
)


# ---------------------------------------------------------------------------
# The named behaviours (Story 121.1 AC2)
# ---------------------------------------------------------------------------


def test_regenerate_is_idempotent_and_leaves_the_file_byte_identical(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    first = _regen(tmp_path)
    assert first.changed
    before = (tmp_path / LEDGER).read_bytes()
    again = regenerate(tmp_path, LEDGER, today=date(2027, 1, 1), source_sha="another-head")
    assert again == LedgerReport(changed=False)
    assert (tmp_path / LEDGER).read_bytes() == before


def test_append_is_idempotent_when_no_row_is_missing(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    _regen(tmp_path)
    before = (tmp_path / LEDGER).read_bytes()
    assert append(tmp_path, LEDGER, today=date(2027, 1, 1), source_sha="other") == LedgerReport(changed=False)
    assert (tmp_path / LEDGER).read_bytes() == before


def test_regenerate_adds_a_missing_row_defaulted_rebuild_planned(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    _ledger(tmp_path, [{"id": "pyforge-atlas:CAP-1", "mode": "A-only", "expiry": "steward:121.5"}])
    report = _regen(tmp_path)
    assert report.added == ("pyforge-atlas:CAP-2",)
    rows = _rows(tmp_path)
    assert rows["pyforge-atlas:CAP-2"] == {
        "id": "pyforge-atlas:CAP-2",
        "spec": "pyforge-atlas",
        "station": "pyforge-atlas",
        "heading": "all IO is catalog-declared",
        "path": "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md",
        "mode": "rebuild",
        "state": "planned",
        "defaulted": "2026-11-10",
    }
    assert "defaulted" not in rows["pyforge-atlas:CAP-1"]
    assert ("defaulted-row", "pyforge-atlas:CAP-2") in report.events


def test_prefixed_heading_takes_the_pap_id(tmp_path: Path) -> None:
    body = (
        "- **pap:CAP-1 — The host renders from the accelerator shape.**\n"
        "- **CAP-1 — `django-pyforge`, the shared chrome.**\n"
    )
    _spec(tmp_path, "pyforge-steward", "pyforge-unifying-strategy", body)
    ids = [cap.id for cap in live_caps(tmp_path)]
    assert ids == ["pyforge-unifying-strategy:CAP-1", "pap:CAP-1"]
    _regen(tmp_path)
    row = _rows(tmp_path)["pap:CAP-1"]
    assert row["spec"] == "pyforge-unifying-strategy"
    assert row["station"] == "pyforge-steward"
    assert row["heading"] == "The host renders from the accelerator shape"


def test_unifying_id_is_the_spec_slug_for_an_unprefixed_heading(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-steward", "pyforge-unifying-strategy", "- **CAP-20 — A start tool does the work.**\n")
    assert [cap.id for cap in live_caps(tmp_path)] == ["pyforge-unifying-strategy:CAP-20"]
    assert cap_id("pyforge-unifying-strategy", 20) == "pyforge-unifying-strategy:CAP-20"


def test_commented_status_reads_as_ready(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS, status="status: ready   # note")
    specs = live_specs(tmp_path)
    assert [(spec.slug, spec.status) for spec in specs] == [("pyforge-atlas", "ready")]
    _regen(tmp_path)
    assert set(_rows(tmp_path)) == {"pyforge-atlas:CAP-1", "pyforge-atlas:CAP-2"}


def test_quoted_expiry_and_dates_stay_quoted_strings(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    _write(
        tmp_path,
        LEDGER.as_posix(),
        "schema: pyforge.capability-ledger/v0\n"
        "updated: 2026-11-01\n"
        "capabilities:\n"
        "  - id: pyforge-atlas:CAP-1\n"
        "    mode: A-only\n"
        '    expiry: "steward:44.10"\n'
        "  - id: pyforge-atlas:CAP-2\n"
        "    mode: A-only\n"
        "    expiry: 2026-12-31\n",
    )
    _regen(tmp_path)
    text = (tmp_path / LEDGER).read_text(encoding="utf-8")
    assert 'expiry: "steward:44.10"' in text
    assert 'expiry: "2026-12-31"' in text
    assert 'updated: "2026-11-10"' in text
    assert f'source_sha: "{SHA}"' in text
    rows = _rows(tmp_path)
    assert rows["pyforge-atlas:CAP-1"]["expiry"] == "steward:44.10"
    assert rows["pyforge-atlas:CAP-2"]["expiry"] == "2026-12-31"


def test_retired_marker_remodes_a_row_to_retire(tmp_path: Path) -> None:
    body = (
        "- **CAP-18 — a never-built job.** ← spec-pyforge-atlas CAP-18 (retired 2026-11-10: never built)\n"
        "- **CAP-19 — RETIRED 2026-09-25 the legacy form.**\n"
        "- **CAP-20 — already retired.** (retired 2026-10-10)\n"
    )
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", body)
    _ledger(
        tmp_path,
        [
            {"id": "pyforge-atlas:CAP-18", "mode": "rebuild", "state": "planned", "note": "kept"},
            {"id": "pyforge-atlas:CAP-19", "mode": "A-only", "expiry": "flip", "pending_on": "x Q1"},
            {"id": "pyforge-atlas:CAP-20", "mode": "retire"},
        ],
    )
    report = _regen(tmp_path)
    assert report.remoded == ("pyforge-atlas:CAP-18", "pyforge-atlas:CAP-19")
    rows = _rows(tmp_path)
    assert rows["pyforge-atlas:CAP-18"]["mode"] == "retire"
    assert "state" not in rows["pyforge-atlas:CAP-18"]
    assert rows["pyforge-atlas:CAP-18"]["note"] == "kept"
    assert rows["pyforge-atlas:CAP-19"]["mode"] == "retire"
    assert "expiry" not in rows["pyforge-atlas:CAP-19"] and "pending_on" not in rows["pyforge-atlas:CAP-19"]
    assert rows["pyforge-atlas:CAP-20"]["mode"] == "retire"
    assert ("remoded-by-marker", "pyforge-atlas:CAP-18") in report.events


def test_archive_ignored_and_an_archived_row_leaves(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    archived = "archive/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-lockstep/SPEC.md"
    _write(tmp_path, archived, "---\nstatus: ready\n---\n\n- **CAP-1 — lockstep.** (shipped 2026-09-01)\n")
    _write(
        tmp_path,
        "_bmad-output/projects/archive/planning-artifacts/specs/spec-old/SPEC.md",
        "---\nstatus: ready\n---\n\n- **CAP-1 — old.** (shipped 2026-09-01)\n",
    )
    _ledger(tmp_path, [{"id": "deck-lockstep:CAP-1", "path": archived, "mode": "rebuild"}])
    assert [spec.slug for spec in live_specs(tmp_path)] == ["pyforge-atlas"]
    report = _regen(tmp_path)
    assert report.dropped == ("deck-lockstep:CAP-1",)
    assert "archive/" not in (tmp_path / LEDGER).read_text(encoding="utf-8")


def test_orphan_dropped_by_regenerate_but_kept_by_append(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    orphan = {"id": "pyforge-atlas:CAP-99", "path": "gone/SPEC.md", "mode": "rebuild", "state": "planned"}
    _ledger(tmp_path, [orphan])
    appended = append(tmp_path, LEDGER, today=TODAY, source_sha=SHA)
    assert appended.added == ("pyforge-atlas:CAP-1", "pyforge-atlas:CAP-2")
    assert appended.dropped == ()
    assert "pyforge-atlas:CAP-99" in _rows(tmp_path)
    report = _regen(tmp_path)
    assert report.dropped == ("pyforge-atlas:CAP-99",)
    assert ("orphan-dropped", "pyforge-atlas:CAP-99") in report.events
    assert "pyforge-atlas:CAP-99" not in _rows(tmp_path)


# ---------------------------------------------------------------------------
# The extract (extract.md)
# ---------------------------------------------------------------------------


def test_extract_caps_reads_the_three_heading_forms() -> None:
    text = (
        "- **CAP-1 — em dash title.** (shipped 2026-09-09)\n"
        "* **CAP-2 – en dash title** (ready 2026-10-01)\n"
        "  - **CAP-3 - hyphen title.***\n"
        "- **CAP-4** — plain title ← spec-x CAP-4 (shipped 2026-09-09)\n"
        "- **CAP-5** — plain with marker (minted 2026-09-19)\n"
        "- **CAP-6** (shipped 2026-09-09)\n"
        "**pap:CAP-7 — prefixed, no bullet.**\n"
    )
    caps = extract_caps(text)
    assert [(cap.prefix, cap.n, cap.heading) for cap in caps] == [
        ("", 1, "em dash title"),
        ("", 2, "en dash title"),
        ("", 3, "hyphen title"),
        ("", 4, "plain title"),
        ("", 5, "plain with marker"),
        ("", 6, ""),
        ("pap", 7, "prefixed, no bullet"),
    ]
    assert caps[0].tail == " (shipped 2026-09-09)"
    assert caps[3].tail.startswith(" — plain title")


def test_extract_caps_ignores_bold_that_is_not_a_heading() -> None:
    text = (
        "- **CAP-62:** which duty moves the row?\n"
        "- **CAP-81 keeps the refusal semantics** of Story 17-1.\n"
        "- **CAP-5 (tasks move, never duplicate):** a task name exists once.\n"
        "Prose naming **CAP-9 — not at the line start**.\n"
    )
    assert extract_caps(text) == ()


def test_extract_caps_takes_intent_and_success_before_the_next_heading() -> None:
    text = (
        "- **CAP-1 — one.** (shipped 2026-09-09)\n"
        "  - **intent:** the first intent.\n"
        "  - **success:** the first success.\n"
        "  - **intent:** a second intent is not taken.\n"
        "- **CAP-2 — two.** (ready 2026-09-09)\n"
        "  - **intent:** the second intent.\n"
        "\n## Constraints\n\n"
        "- **success:** a Constraint bullet is not CAP-2's success.\n"
    )
    first, second = extract_caps(text)
    assert (first.intent, first.success) == ("the first intent.", "the first success.")
    assert (second.intent, second.success) == ("the second intent.", "")


def test_extract_caps_keeps_the_first_heading_of_a_number() -> None:
    text = "- **CAP-1 — first.** (shipped 2026-09-09)\n- **CAP-1 — second.** (ready 2026-09-09)\n"
    (cap,) = extract_caps(text)
    assert cap.heading == "first"


@pytest.mark.parametrize(
    ("spec", "n", "prefix", "expected"),
    [
        ("python-foundry-cutover", 9, "", "fnd:CAP-9"),
        ("foundry-regenerate-not-fold", 2, "", "fnr:CAP-2"),
        ("foundry-capability-ledger", 1, "", "fcl:CAP-1"),
        ("pyforge-unifying-strategy", 3, "pap", "pap:CAP-3"),
        ("pyforge-atlas", 68, "", "pyforge-atlas:CAP-68"),
        ("one-chain-per-station", 5, "", "one-chain-per-station:CAP-5"),
    ],
)
def test_cap_id_follows_the_id_rule(spec: str, n: int, prefix: str, expected: str) -> None:
    assert cap_id(spec, n, prefix) == expected


def test_cap_id_refuses_any_other_short_prefix() -> None:
    with pytest.raises(ValueError, match="no short prefix 'hub'"):
        cap_id("intelligence-hub", 1, "hub")


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("- **CAP-1 — t.** (ready 2026-11-10)", ("ready", "2026-11-10")),
        ("- **CAP-1 — t.** (ready 2026-11-10; not met: a run, DW-x-1)", ("ready", "2026-11-10")),
        ("- **CAP-1 — t.** ← spec-x CAP-1 (shipped 2026-09-09)", ("shipped", "2026-09-09")),
        ("- **CAP-1 — t.** (retired 2026-11-10: never built)", ("retired", "2026-11-10")),
        ("- **CAP-1 — t.** (retired 2026-08-21)", ("retired", "2026-08-21")),
        ("- **CAP-7 — RETIRED 2026-09-25 Archive.**", ("retired", "2026-09-25")),
        ("- **CAP-1 — t.** (minted 2026-09-19 (evening); x) (shipped 2026-09-20)", ("shipped", "2026-09-20")),
        ("- **CAP-1** — plain (shipped 2026-09-09)", ("shipped", "2026-09-09")),
        ("(ready 2026-11-10)", ("ready", "2026-11-10")),
    ],
)
def test_marker_reads_the_pinned_forms(line: str, expected: tuple[str, str]) -> None:
    assert marker(line) == expected


@pytest.mark.parametrize(
    ("line", "text"),
    [
        (
            "- **CAP-1 — t.** (minted 2026-09-19 (evening); extends CAP-71)",
            "(minted 2026-09-19 (evening); extends CAP-71)",
        ),
        ("- **CAP-1 — t.** (unbuilt)", "(unbuilt)"),
        ("- **CAP-1 — t.** (deleted 2026-10-01)", "(deleted 2026-10-01)"),
        ("- **CAP-1 — t.** (never built)", "(never built)"),
        ("- **CAP-1 — t.** (retired)", "(retired)"),
        ("- **CAP-1 — t.** (shipped; restored 2026-10-25: x)", "(shipped; restored 2026-10-25: x)"),
        ("- **CAP-1 — t.** (Shipped 2026-09-09)", "(Shipped 2026-09-09)"),
        ("- **CAP-1 — t.** (minted 2026-09-19 and never closed", "(minted 2026-09-19 and never closed"),
    ],
)
def test_marker_names_any_other_status_word_unknown(line: str, text: str) -> None:
    assert marker(line) == ("unknown", text)


@pytest.mark.parametrize(
    "line",
    [
        "- **CAP-1 — Open foundry (Phase 0).**",
        "- **CAP-1 — t.** ← Dream entry 2026-11-10 (The shared floor says what it is)",
        "- **CAP-1 — t (ready check).**",
        "- **CAP-1 — t.**",
    ],
)
def test_marker_is_none_without_a_status(line: str) -> None:
    assert marker(line) is None


# ---------------------------------------------------------------------------
# The scope (extract.md § Scope)
# ---------------------------------------------------------------------------


def test_live_specs_keep_ready_and_in_progress_by_path(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-scribe", "pyforge-scribe", "- **CAP-1 — s.**\n", status="status: in-progress")
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    _spec(tmp_path, "pyforge-herald", "draft-one", "- **CAP-1 — d.**\n", status="status: draft")
    _spec(tmp_path, "pyforge-herald", "shipped-one", "- **CAP-1 — d.**\n", status="status: shipped")
    _spec(tmp_path, "pyforge-herald", "no-status", "- **CAP-1 — d.**\n", status="title: x")
    _spec(tmp_path, "pyforge-herald", "listy", "- **CAP-1 — d.**\n", status="status: [ready]")
    _write(
        tmp_path, "docs/governance/spec-feature-flag-governance/SPEC.md", "---\nstatus: ready\n---\n- **CAP-1 — g.**\n"
    )
    _write(tmp_path, "docs/governance/spec-no-frontmatter/SPEC.md", "# no frontmatter\n- **CAP-1 — n.**\n")
    _write(tmp_path, "docs/governance/spec-unclosed/SPEC.md", "---\nstatus: ready\n- **CAP-1 — n.**\n")
    _write(tmp_path, "docs/governance/spec-scalar/SPEC.md", "---\njust a string\n---\n- **CAP-1 — n.**\n")
    _write(tmp_path, "docs/governance/spec-empty/SPEC.md", "")
    _write(tmp_path, "docs/governance/notaspec/SPEC.md", "---\nstatus: ready\n---\n- **CAP-1 — n.**\n")
    specs = live_specs(tmp_path)
    assert [(spec.path.split("/")[-2], spec.station, spec.status) for spec in specs] == [
        ("spec-pyforge-atlas", "pyforge-atlas", "ready"),
        ("spec-pyforge-scribe", "pyforge-scribe", "in-progress"),
        ("spec-feature-flag-governance", "governance", "ready"),
    ]
    assert live_caps(tmp_path)[-1].id == "feature-flag-governance:CAP-1"


def test_live_specs_refuse_a_frontmatter_that_is_not_yaml(tmp_path: Path) -> None:
    _write(tmp_path, "docs/governance/spec-broken/SPEC.md", "---\nstatus: [ready\n---\n")
    with pytest.raises(CutoverLedgerError, match="spec-broken/SPEC.md: frontmatter is not YAML"):
        live_specs(tmp_path)


def test_live_caps_give_a_repeated_id_to_its_first_holder(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "a-spec", "- **pap:CAP-1 — first.**\n")
    _spec(tmp_path, "pyforge-steward", "b-spec", "- **pap:CAP-1 — second.**\n")
    (cap,) = live_caps(tmp_path)
    assert (cap.id, cap.spec, cap.heading) == ("pap:CAP-1", "a-spec", "first")


# ---------------------------------------------------------------------------
# The ledger file (modes.md § Schema v1)
# ---------------------------------------------------------------------------


def test_regenerate_rewrites_derived_fields_and_keeps_decided_ones(tmp_path: Path) -> None:
    rel = _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    decided = {
        "mode": "rebuild",
        "state": "rebuilding",
        "launch": True,
        "depends_on": ["fnd:CAP-1"],
        "frozen_paths": ["src/x.py"],
        "note": "decided by hand",
        "zz_extra": "kept after the schema keys",
    }
    _ledger(
        tmp_path,
        [{"id": "pyforge-atlas:CAP-1", "spec": "old", "station": "old", "heading": "stale", "path": "x", **decided}],
        never_move=True,
        story_44_1="blocked",
    )
    report = _regen(tmp_path)
    assert report.changed and report.added == ("pyforge-atlas:CAP-2",)
    row = _rows(tmp_path)["pyforge-atlas:CAP-1"]
    assert row == {
        "id": "pyforge-atlas:CAP-1",
        "spec": "pyforge-atlas",
        "station": "pyforge-atlas",
        "heading": "the DAG is the orchestrator",
        "path": rel,
        **decided,
    }
    assert list(row)[-1] == "zz_extra"
    data = yaml.safe_load((tmp_path / LEDGER).read_text(encoding="utf-8"))
    assert list(data) == list(cl.HEADER_KEYS)
    assert data["schema"] == "pyforge.capability-ledger/v1"
    assert data["generated_by"] == "pyforge steward cutover plan"
    assert data["modes"] == list(cl.MODES)
    assert data["frozen_states"] == ["rebuilding"]


def test_regenerate_keeps_cells_and_the_leading_comments(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    cells = [
        {"id": "cell:conda-forge-expert/skill", "path": ".claude/skills/conda-forge-expert/", "mode": "A-only"},
        {"note": "n", "expiry": "mason:39.2", "mode": "A-only", "path": "p/", "id": "cell:conda-forge-expert/data"},
    ]
    path = _ledger(tmp_path, [], cells=cells)
    path.write_text("# Foundry capability ledger.\n# Second line\n" + path.read_text(encoding="utf-8"), "utf-8")
    _regen(tmp_path)
    text = (tmp_path / LEDGER).read_text(encoding="utf-8")
    assert text.startswith("# Foundry capability ledger.\n# Second line\nschema: pyforge.capability-ledger/v1\n")
    assert yaml.safe_load(text)["cells"] == cells
    assert 'expiry: "mason:39.2"' in text
    assert _regen(tmp_path) == LedgerReport(changed=False)


def test_regenerate_creates_a_missing_ledger_with_capabilities_in_order(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-steward", "python-foundry-cutover", "- **CAP-10 — ten.**\n- **CAP-9 — nine.**\n")
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    report = _regen(tmp_path)
    assert report.changed
    assert list(_rows(tmp_path)) == ["pyforge-atlas:CAP-1", "pyforge-atlas:CAP-2", "fnd:CAP-9", "fnd:CAP-10"]
    text = (tmp_path / LEDGER).read_text(encoding="utf-8")
    assert "capabilities:\n  - id: pyforge-atlas:CAP-1\n" in text
    assert text.endswith("cells: []\n")


def test_regenerate_writes_an_absolute_ledger_path(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    target = tmp_path / "out" / "ledger.yaml"
    assert regenerate(tmp_path, target, today=TODAY, source_sha=SHA).changed
    assert target.is_file() and not (tmp_path / LEDGER).exists()


def test_regenerate_drops_a_repeated_row_and_keeps_the_first(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    _ledger(
        tmp_path,
        [
            {"id": "pyforge-atlas:CAP-1", "mode": "A-only", "expiry": "flip"},
            {"id": "pyforge-atlas:CAP-1", "mode": "retire"},
        ],
    )
    report = _regen(tmp_path)
    assert report.dropped == ("pyforge-atlas:CAP-1",)
    assert _rows(tmp_path)["pyforge-atlas:CAP-1"]["mode"] == "A-only"


def test_append_adds_a_retired_capability_as_retire_and_touches_no_other_row(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS + "- **CAP-3 — gone.** (retired 2026-11-10: never built)\n")
    _ledger(tmp_path, [{"id": "pyforge-atlas:CAP-1", "heading": "stale on purpose", "mode": "rebuild"}])
    report = append(tmp_path, LEDGER, today=TODAY, source_sha=SHA)
    assert report.added == ("pyforge-atlas:CAP-2", "pyforge-atlas:CAP-3")
    assert report.remoded == ("pyforge-atlas:CAP-3",)
    rows = _rows(tmp_path)
    assert rows["pyforge-atlas:CAP-1"] == {
        "id": "pyforge-atlas:CAP-1",
        "heading": "stale on purpose",
        "mode": "rebuild",
    }
    assert rows["pyforge-atlas:CAP-3"]["mode"] == "retire"
    assert rows["pyforge-atlas:CAP-3"]["defaulted"] == "2026-11-10"
    assert "state" not in rows["pyforge-atlas:CAP-3"]


def test_an_empty_ledger_file_is_an_empty_ledger(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    _write(tmp_path, LEDGER.as_posix(), "")
    assert _regen(tmp_path).added == ("pyforge-atlas:CAP-1", "pyforge-atlas:CAP-2")


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("capabilities: [\n", "not YAML"),
        ("- a list\n", "not a mapping"),
        ("capabilities: {id: x}\n", "capabilities is not a list of mappings"),
        ("cells: [one]\n", "cells is not a list of mappings"),
        ("capabilities:\n  - mode: rebuild\n", "a capabilities row has no id"),
    ],
)
def test_an_unreadable_ledger_is_refused_and_left_alone(tmp_path: Path, text: str, match: str) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    path = _write(tmp_path, LEDGER.as_posix(), text)
    for write_mode in (regenerate, append):
        with pytest.raises(CutoverLedgerError, match=match):
            write_mode(tmp_path, LEDGER, today=TODAY, source_sha=SHA)
    assert path.read_text(encoding="utf-8") == text


def test_source_sha_is_the_head_the_specs_were_read_at(tmp_path: Path) -> None:
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    git = ["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "--no-verify", "-m", "specs"], check=True)
    head = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    regenerate(tmp_path, LEDGER, today=TODAY)
    assert yaml.safe_load((tmp_path / LEDGER).read_text(encoding="utf-8"))["source_sha"] == head


def test_source_sha_is_empty_off_a_git_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_git(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError("git: not found")

    monkeypatch.setattr(cl.subprocess, "run", no_git)
    assert cl._head_sha(tmp_path) == ""
    monkeypatch.setattr(
        cl.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 128, stdout="", stderr="not a repo")
    )
    _spec(tmp_path, "pyforge-atlas", "pyforge-atlas", ATLAS)
    append(tmp_path, LEDGER, today=TODAY)
    assert yaml.safe_load((tmp_path / LEDGER).read_text(encoding="utf-8"))["source_sha"] == ""


def test_the_report_names_each_row_it_moved() -> None:
    report = LedgerReport(changed=True, added=("a:CAP-1",), dropped=("b:CAP-2",), remoded=("c:CAP-3",))
    assert report.events == (
        ("defaulted-row", "a:CAP-1"),
        ("orphan-dropped", "b:CAP-2"),
        ("remoded-by-marker", "c:CAP-3"),
    )
    assert report.as_dict() == {"changed": True, "added": ["a:CAP-1"], "dropped": ["b:CAP-2"], "remoded": ["c:CAP-3"]}
