"""Story 121.6 (spec-foundry-capability-ledger fcl:CAP-1 and fcl:CAP-2): the capability ledger's check refuses a row
that contradicts its Spec or the written rules of ``modes.md``, and writes nothing.

Every tree here is a fixture under ``tmp_path`` and every flag tree is passed by path: this module never reads the
repository, so it runs in steward's package half.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from pyforge.core.cutover_root import CutoverRootError

from pyforge.steward.cutover_ledger import EXTRACT_PATH, FROZEN_STATES, MODES, STATES, CutoverLedgerError
from pyforge.steward.cutover_ledger_check import (
    CASE_LIST,
    FINDING_CODES,
    WARNING_CODES,
    CheckReport,
    case_ids,
    check,
    citing_stories,
    expiry_form_problem,
)

# Story 124.2: tracked paths are spelled as joins here -- steward's trigger-map scan counts a bare
# tracked-path literal as a read of the live tree, and this module reads none.
LEDGER = Path("docs", "foundry", "capability-ledger.yaml")
PROJECT = "pyforge-atlas"
SPEC_PATH = f"_bmad-output/projects/{PROJECT}/planning-artifacts/specs/spec-{PROJECT}/SPEC.md"
EPICS_PATH = f"_bmad-output/projects/{PROJECT}/planning-artifacts/epics.md"
SPRINT_PATH = f"_bmad-output/projects/{PROJECT}/planning-artifacts/sprint-status-ledger.yaml"
CASE = "k-core-cutover-default"

ATLAS = (
    "- **CAP-1 — the DAG is the orchestrator.** (shipped 2026-09-09)\n"
    "- **CAP-2 — all IO is catalog-declared.** (ready 2026-10-18)\n"
    "- **CAP-3 — the old board.** (retired 2026-11-10: never built)\n"
)
HEADINGS = {1: "the DAG is the orchestrator", 2: "all IO is catalog-declared", 3: "the old board"}

EPICS = (
    "# Epics\n\n## Epic 2: Catalog IO\n\n### Story 2.1: The catalog declares the IO\n\n"
    "**Type:** feature • **Effort:** S • **FR/AD:** spec-pyforge-atlas CAP-2 (FR-1) • AD-1\n"
    "**Flag:** none\n"
)
SPRINT = {"2-1-the-catalog-declares-the-io": "done"}

CELL = {
    "id": "cell:conda-forge-expert/skill",
    "path": "/".join((".claude", "skills", "conda-forge-expert", "")),
    "mode": "A-only",
    "expiry": "mason:39.2",
}

_DROP = object()


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _row(n: int, mode: str = "rebuild", **decided: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": f"{PROJECT}:CAP-{n}",
        "spec": PROJECT,
        "station": PROJECT,
        "heading": HEADINGS.get(n, f"capability {n}"),
        "path": SPEC_PATH,
        "mode": mode,
    }
    if mode == "rebuild":
        row["state"] = "planned"
    row.update(decided)
    return {key: value for key, value in row.items() if value is not _DROP}


def _rows() -> list[dict[str, Any]]:
    return [_row(1), _row(2), _row(3, "retire")]


def _ledger(
    root: Path,
    rows: list[dict[str, Any]] | None = None,
    cells: list[dict[str, Any]] | None = None,
    **header: Any,
) -> Path:
    doc: dict[str, Any] = {
        "schema": "pyforge.capability-ledger/v1",
        "generated_by": "pyforge steward cutover plan",
        "updated": "2026-11-10",
        "source_sha": "0123abcd",
        "extract": EXTRACT_PATH,
        "modes": list(MODES),
        "states": list(STATES),
        "frozen_states": list(FROZEN_STATES),
        "capabilities": _rows() if rows is None else rows,
        "cells": [dict(CELL)] if cells is None else cells,
    }
    for key, value in header.items():
        if value is _DROP:
            doc.pop(key, None)
        else:
            doc[key] = value
    return _write(root, LEDGER.as_posix(), yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))


def _tree(
    root: Path,
    *,
    rows: list[dict[str, Any]] | None = None,
    cells: list[dict[str, Any]] | None = None,
    body: str = ATLAS,
    epics: str = EPICS,
    sprint: dict[str, str] | None = None,
    **header: Any,
) -> Path:
    _write(root, SPEC_PATH, f"---\nspec: {PROJECT}\nstatus: ready\n---\n\n# SPEC\n\n## Capabilities\n\n{body}\n")
    _write(root, EPICS_PATH, epics)
    _write(root, SPRINT_PATH, yaml.safe_dump({"development_status": SPRINT if sprint is None else sprint}))
    _write(
        root,
        CASE_LIST.as_posix(),
        f"| id | slice | argv / nodeid |\n|---|---|---|\n| {CASE} | core | `…/test_cutover_root.py` |\n",
    )
    return _ledger(root, rows, cells, **header)


def _flags(directory: Path, root_of_record: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "flags.json"
    entry = {
        "state": "ENABLED",
        "variants": {"local-recipes": "local-recipes", "foundry": "foundry"},
        "defaultVariant": root_of_record,
    }
    path.write_text(json.dumps({"flags": {"pyforge.cutover_root": entry}}), encoding="utf-8")
    return path


def _codes(issues: tuple[tuple[str, str, str], ...]) -> list[tuple[str, str]]:
    return [(code, item) for code, item, _ in issues]


def _findings(root: Path, **kwargs: Any) -> list[tuple[str, str]]:
    return _codes(check(root, LEDGER, **kwargs).findings)


@pytest.fixture(autouse=True)
def _no_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    monkeypatch.delenv("PYFORGE_FLAGS_PATH", raising=False)


# ---------------------------------------------------------------------------
# The contract: a clean ledger, nothing written, the closed code lists
# ---------------------------------------------------------------------------


def test_a_clean_ledger_has_no_finding_and_no_warning(tmp_path: Path) -> None:
    _tree(tmp_path)
    report = check(tmp_path, LEDGER)
    assert report == CheckReport()
    assert report.ok


def test_check_writes_nothing(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1), _row(2, "retire"), _row(9)])
    before = {path: path.read_bytes() for path in sorted(tmp_path.rglob("*")) if path.is_file()}
    report = check(tmp_path, LEDGER)
    assert not report.ok
    after = {path: path.read_bytes() for path in sorted(tmp_path.rglob("*")) if path.is_file()}
    assert after == before


def test_an_absolute_ledger_path_is_read_as_given(tmp_path: Path) -> None:
    _tree(tmp_path)
    assert check(tmp_path, tmp_path / LEDGER) == CheckReport()


def test_the_codes_are_the_written_set() -> None:
    assert len(FINDING_CODES) == len(set(FINDING_CODES)) == 24
    assert len(WARNING_CODES) == len(set(WARNING_CODES)) == 3
    assert not set(FINDING_CODES) & set(WARNING_CODES)


def test_findings_and_warnings_are_sorted_code_id_message_triples(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, heading="x"), _row(2, mode="move"), _row(3, "retire")])
    report = check(tmp_path, LEDGER)
    assert list(report.findings) == sorted(report.findings)
    assert all(len(issue) == 3 and all(isinstance(part, str) for part in issue) for issue in report.findings)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (None, "no capability ledger"),
        ("capabilities: [unclosed\n", "not YAML"),
        ("- a list\n", "not a mapping"),
    ],
)
def test_an_unreadable_ledger_is_a_named_error(tmp_path: Path, text: str | None, message: str) -> None:
    _tree(tmp_path)
    if text is None:
        (tmp_path / LEDGER).unlink()
    else:
        _write(tmp_path, LEDGER.as_posix(), text)
    with pytest.raises(CutoverLedgerError, match=message):
        check(tmp_path, LEDGER)


def test_an_unreadable_sprint_ledger_is_a_named_error(tmp_path: Path) -> None:
    _tree(tmp_path)
    _write(tmp_path, SPRINT_PATH, "development_status: [unclosed\n")
    with pytest.raises(CutoverLedgerError, match="not YAML"):
        check(tmp_path, LEDGER)


# ---------------------------------------------------------------------------
# rebuild-never-built: ruling 3 as modes.md rule 7 writes it
# ---------------------------------------------------------------------------


def test_rebuild_never_built_fires_when_the_only_citing_story_is_blocked(tmp_path: Path) -> None:
    _tree(tmp_path, sprint={"2-1-the-catalog-declares-the-io": "blocked"})
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("rebuild-never-built", "pyforge-atlas:CAP-2")]
    message = report.findings[0][2]
    assert "2.1 (blocked)" in message
    assert "B-only (carried by 2.1)" in message


def test_rebuild_never_built_is_silent_when_one_citing_story_is_done(tmp_path: Path) -> None:
    epics = EPICS + (
        "\n### Story 2.2: The catalog checks the IO\n\n**Type:** feature • **FR/AD:** spec-pyforge-atlas CAP-2 • AD-1\n"
    )
    sprint = {"2-1-the-catalog-declares-the-io": "blocked", "2-2-the-catalog-checks-the-io": "done"}
    _tree(tmp_path, epics=epics, sprint=sprint)
    assert check(tmp_path, LEDGER) == CheckReport()


def test_rebuild_never_built_settles_b_only_when_a_backlog_story_carries_it(tmp_path: Path) -> None:
    # modes.md rule 7: a backlog Story is live, as a blocked one is, so it carries the row to B-only.
    _tree(tmp_path, sprint={"2-1-the-catalog-declares-the-io": "backlog"})
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("rebuild-never-built", "pyforge-atlas:CAP-2")]
    message = report.findings[0][2]
    assert "2.1 (backlog)" in message
    assert "B-only (carried by 2.1)" in message


def test_rebuild_never_built_settles_retire_when_no_live_story_carries_it(tmp_path: Path) -> None:
    _tree(tmp_path, sprint={"2-1-the-catalog-declares-the-io": "in-progress"})
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("rebuild-never-built", "pyforge-atlas:CAP-2")]
    assert "retire, marker (retired <date>: never built)" in report.findings[0][2]


def test_rebuild_never_built_fires_when_no_story_cites_the_capability(tmp_path: Path) -> None:
    _tree(tmp_path, epics="# Epics\n")
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("rebuild-never-built", "pyforge-atlas:CAP-2")]
    assert "citing: none" in report.findings[0][2]


def test_rebuild_never_built_names_a_story_with_no_ledger_key(tmp_path: Path) -> None:
    _tree(tmp_path, sprint={})
    message = check(tmp_path, LEDGER).findings[0][2]
    assert "2.1 (no ledger key)" in message


def test_rebuild_never_built_reads_done_among_several_keys_of_one_story(tmp_path: Path) -> None:
    # Two ledger keys share the 2-1- prefix; the first one read is blocked, the other done: done wins. An epic key
    # names no story and is skipped.
    sprint = {"2-1-a-stale-slug": "blocked", "2-1-the-catalog-declares-the-io": "done", "epic-2": "in-progress"}
    _tree(tmp_path, sprint=sprint)
    assert check(tmp_path, LEDGER) == CheckReport()


def test_rebuild_never_built_judges_each_ready_row_of_one_station(tmp_path: Path) -> None:
    body = ATLAS + "- **CAP-4 — a second ready capability.** (ready 2026-10-18)\n"
    epics = EPICS.replace("CAP-2 (FR-1)", "CAP-2 and CAP-4 (FR-1)")
    rows = [*_rows(), _row(4, heading="a second ready capability")]
    _tree(tmp_path, body=body, epics=epics, rows=rows, sprint={"2-1-the-catalog-declares-the-io": "backlog"})
    assert _findings(tmp_path) == [
        ("rebuild-never-built", "pyforge-atlas:CAP-2"),
        ("rebuild-never-built", "pyforge-atlas:CAP-4"),
    ]


def test_rebuild_never_built_names_a_citing_story_when_the_station_has_no_sprint_ledger(tmp_path: Path) -> None:
    _tree(tmp_path)
    (tmp_path / SPRINT_PATH).unlink()
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("rebuild-never-built", "pyforge-atlas:CAP-2")]
    assert "2.1 (no ledger key)" in report.findings[0][2]


def test_rebuild_never_built_reads_a_station_with_no_epics_or_ledger(tmp_path: Path) -> None:
    _tree(tmp_path)
    (tmp_path / EPICS_PATH).unlink()
    (tmp_path / SPRINT_PATH).unlink()
    assert _findings(tmp_path) == [("rebuild-never-built", "pyforge-atlas:CAP-2")]


def test_rebuild_never_built_reads_only_a_ready_heading(tmp_path: Path) -> None:
    # spec-pyforge-atlas CAP-1 reads (shipped and no story cites it: a shipped capability was built.
    _tree(tmp_path, epics="# Epics\n", rows=[_row(1), _row(2, "B-only"), _row(3, "retire")])
    assert check(tmp_path, LEDGER) == CheckReport()


def test_rebuild_never_built_reads_a_parent_line(tmp_path: Path) -> None:
    epics = "### Story 2.1: The catalog declares the IO\n\nParent: spec-pyforge-atlas CAP-2\n"
    _tree(tmp_path, epics=epics, sprint={"2-1-the-catalog-declares-the-io": "blocked"})
    assert "B-only (carried by 2.1)" in check(tmp_path, LEDGER).findings[0][2]


# ---------------------------------------------------------------------------
# Citing stories: the FR/AD or Parent line of a `### Story E.S` block
# ---------------------------------------------------------------------------


def test_citing_stories_reads_prefixes_specs_ranges_and_the_station_default() -> None:
    epics = (
        "### Story 121.6: The check\n\n"
        "**Type:** feature • **FR/AD:** spec-foundry-capability-ledger fcl:CAP-1 and fcl:CAP-2 • fnd:AD-25\n"
        "### Story 121.7: The modes\n\n"
        "**FR/AD:** spec-pyforge-atlas CAP-18..CAP-20 and spec-pyforge-mason CAP-8 to CAP-9 • pap:CAP-1\n"
        "### Story 121.8: The station's own\n\n"
        "**Parent:** CAP-4–5 and spec-pyforge-core:CAP-13\n"
    )
    cites = citing_stories(epics, "pyforge-steward")
    assert cites == {
        "fcl:CAP-1": ("121.6",),
        "fcl:CAP-2": ("121.6",),
        "pyforge-atlas:CAP-18": ("121.7",),
        "pyforge-atlas:CAP-19": ("121.7",),
        "pyforge-atlas:CAP-20": ("121.7",),
        "pyforge-mason:CAP-8": ("121.7",),
        "pyforge-mason:CAP-9": ("121.7",),
        "pap:CAP-1": ("121.7",),
        "pyforge-steward:CAP-4": ("121.8",),
        "pyforge-steward:CAP-5": ("121.8",),
        "pyforge-core:CAP-13": ("121.8",),
    }


def test_citing_stories_reads_past_a_bullet_inside_the_label() -> None:
    epics = (
        "### Story 9.1: A fix\n\n"
        "**Type:** fix • **FR/AD:** — (a `fix`, so no new CAP) • spec-pyforge-atlas CAP-8 (the read surface) • AD-11\n"
    )
    assert citing_stories(epics, PROJECT) == {"pyforge-atlas:CAP-8": ("9.1",)}


def test_citing_stories_reads_only_the_fr_ad_and_parent_labels() -> None:
    epics = (
        "### Story 3.1: Elsewhere\n\n"
        "**Type:** feature • **Surface:** CAP-7 • **FR/AD:** spec-pyforge-atlas CAP-2 • **Flag:** CAP-8\n"
        "**Given** CAP-9 has no judge\n"
        "## Epic 4\n\n**FR/AD:** spec-pyforge-atlas CAP-10\n"
    )
    assert citing_stories(epics, PROJECT) == {"pyforge-atlas:CAP-2": ("3.1",)}


def test_citing_stories_continues_a_wrapped_label() -> None:
    epics = "### Story 3.1: Wrapped\n\n**FR/AD:** spec-pyforge-atlas CAP-2 and\n  CAP-3 (the rest)\n\n**Flag:** none\n"
    assert citing_stories(epics, PROJECT) == {"pyforge-atlas:CAP-2": ("3.1",), "pyforge-atlas:CAP-3": ("3.1",)}


def test_citing_stories_keeps_file_order_and_names_a_story_once() -> None:
    epics = "### Story 5.2: Second\n\n**FR/AD:** CAP-1 • **Parent:** CAP-1\n### Story 5.1: First\n\n**FR/AD:** CAP-1\n"
    assert citing_stories(epics, PROJECT) == {"pyforge-atlas:CAP-1": ("5.2", "5.1")}


def test_citing_stories_reads_a_bare_cap_only_after_a_spec_off_station() -> None:
    epics = "### Story 1.1: Governance\n\n**FR/AD:** CAP-1 and spec-one-chain-per-station CAP-5\n"
    assert citing_stories(epics, "governance") == {"one-chain-per-station:CAP-5": ("1.1",)}


@pytest.mark.parametrize("span", ["CAP-9..CAP-3", "CAP-1..CAP-500"])
def test_citing_stories_reads_an_impossible_range_as_its_start(span: str) -> None:
    epics = f"### Story 1.1: Range\n\n**FR/AD:** {span}\n"
    start = span.split("..")[0]
    assert citing_stories(epics, PROJECT) == {f"pyforge-atlas:{start}": ("1.1",)}


# ---------------------------------------------------------------------------
# The rows against the live Specs
# ---------------------------------------------------------------------------


def test_unclassified_live_capability_with_no_row(tmp_path: Path) -> None:
    _tree(tmp_path, body=ATLAS + "- **CAP-4 — a new capability.** (shipped 2026-11-01)\n")
    assert _findings(tmp_path) == [("unclassified", "pyforge-atlas:CAP-4")]


def test_orphan_row_with_no_live_capability(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[*_rows(), _row(9)])
    assert _findings(tmp_path) == [("orphan-row", "pyforge-atlas:CAP-9")]


def test_archived_spec_row_is_refused_not_orphaned(tmp_path: Path) -> None:
    archived = _row(1, id="hub:CAP-1", path="archive/_bmad-output/projects/pyforge-old/specs/spec-hub/SPEC.md")
    _tree(tmp_path, rows=[*_rows(), archived])
    assert _findings(tmp_path) == [("archived-spec-row", "hub:CAP-1")]


def test_heading_drift_from_the_spec_title(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, heading="the DAG orchestrates"), _row(2), _row(3, "retire")])
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("heading-drift", "pyforge-atlas:CAP-1")]
    assert "'the DAG is the orchestrator'" in report.findings[0][2]


@pytest.mark.parametrize("where", ["rows", "cells"])
def test_duplicate_cap_id_across_rows_and_cells(tmp_path: Path, where: str) -> None:
    twin = _row(1, mode="A-only", state=_DROP, expiry="steward:121.5")
    if where == "rows":
        _tree(tmp_path, rows=[*_rows(), twin])
    else:
        _tree(tmp_path, cells=[dict(CELL), {**CELL, "id": "pyforge-atlas:CAP-1"}])
    assert ("duplicate-cap-id", "pyforge-atlas:CAP-1") in _findings(tmp_path)


# ---------------------------------------------------------------------------
# The header: schema v1, every key, in order
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "detail"),
    [
        ({"move": []}, "'move' is not in schema v1"),
        ({"source_sha": _DROP}, "'source_sha' is missing"),
        ({"schema": "pyforge.capability-ledger/v2"}, "schema is"),
        ({"modes": ["rebuild", "retire", "A-only", "B-only"]}, "modes is"),
        ({"updated": date(2026, 11, 10)}, "not a quoted YYYY-MM-DD"),
        ({"source_sha": 123}, "not a quoted string"),
        ({"capabilities": {"id": "x"}}, "capabilities is not a list"),
        ({"cells": ["cell:loose"]}, "not a mapping with an id"),
    ],
)
def test_bad_header(tmp_path: Path, header: dict[str, Any], detail: str) -> None:
    _tree(tmp_path, **header)
    report = check(tmp_path, LEDGER)
    bad = [message for code, _, message in report.findings if code == "bad-header"]
    assert any(detail in message for message in bad), report.findings


def test_bad_header_names_keys_out_of_order(tmp_path: Path) -> None:
    _tree(tmp_path)
    data = yaml.safe_load((tmp_path / LEDGER).read_text(encoding="utf-8"))
    reordered = {"generated_by": data.pop("generated_by"), **data}
    _write(tmp_path, LEDGER.as_posix(), yaml.safe_dump(reordered, sort_keys=False, allow_unicode=True))
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("bad-header", "header")]
    assert "out of the schema v1 order" in report.findings[0][2]


def test_a_ledger_with_no_capability_list_reads_every_capability_unclassified(tmp_path: Path) -> None:
    _tree(tmp_path, capabilities=None)
    findings = _findings(tmp_path)
    assert ("unclassified", "pyforge-atlas:CAP-1") in findings
    assert ("unclassified", "pyforge-atlas:CAP-3") in findings


# ---------------------------------------------------------------------------
# Modes, states and the decided keys
# ---------------------------------------------------------------------------


def test_bad_mode_on_a_row_and_on_a_cell(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, mode="move"), _row(2), _row(3, "retire")], cells=[{**CELL, "mode": "rebuild"}])
    findings = _findings(tmp_path)
    assert ("bad-mode", "pyforge-atlas:CAP-1") in findings
    assert ("bad-mode", "cell:conda-forge-expert/skill") in findings


@pytest.mark.parametrize(
    ("row", "detail"),
    [
        (_row(1, state="shipped"), "is not one of"),
        (_row(1, mode="B-only", state="planned"), "a state is for rebuild rows only"),
    ],
)
def test_bad_state(tmp_path: Path, row: dict[str, Any], detail: str) -> None:
    _tree(tmp_path, rows=[row, _row(2), _row(3, "retire")])
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("bad-state", "pyforge-atlas:CAP-1")]
    assert detail in report.findings[0][2]


def test_rebuild_without_state(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, state=_DROP), _row(2), _row(3, "retire")])
    assert _findings(tmp_path) == [("rebuild-without-state", "pyforge-atlas:CAP-1")]


def test_a_only_without_expiry(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, mode="A-only", state=_DROP), _row(2), _row(3, "retire")])
    assert _findings(tmp_path) == [("a-only-without-expiry", "pyforge-atlas:CAP-1")]


@pytest.mark.parametrize("expiry", [None, ""])
def test_cell_without_expiry(tmp_path: Path, expiry: str | None) -> None:
    _tree(tmp_path, cells=[{**CELL, "expiry": expiry}])
    assert _findings(tmp_path) == [("cell-without-expiry", "cell:conda-forge-expert/skill")]


@pytest.mark.parametrize("expiry", ["steward:121.5", "mason:39.2", "2026-12-01", "flip"])
def test_the_three_expiry_forms_are_accepted(expiry: str) -> None:
    assert expiry_form_problem(expiry) is None


@pytest.mark.parametrize(
    ("expiry", "detail"),
    [
        (44.1, "not a quoted string"),
        (date(2026, 12, 1), "not a quoted string"),
        ("44.10", "none of"),
        ("steward:44", "none of"),
        ("pyforge-steward:44.10", "none of"),
        ("nobody:1.2", "none of"),
        ("2026-02-30", "not a calendar date"),
        ("soon", "none of"),
    ],
)
def test_bad_expiry_form(tmp_path: Path, expiry: Any, detail: str) -> None:
    problem = expiry_form_problem(expiry)
    assert problem is not None and detail in problem
    _tree(tmp_path, rows=[_row(1, mode="A-only", state=_DROP, expiry=expiry), _row(2), _row(3, "retire")])
    assert _findings(tmp_path) == [("bad-expiry-form", "pyforge-atlas:CAP-1")]


def test_bad_expiry_form_on_a_row_that_is_not_a_only(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, expiry="steward:121.5"), _row(2), _row(3, "retire")])
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("bad-expiry-form", "pyforge-atlas:CAP-1")]
    assert "an expiry is for A-only rows only" in report.findings[0][2]


def test_bad_expiry_form_on_a_cell(tmp_path: Path) -> None:
    _tree(tmp_path, cells=[{**CELL, "expiry": "39.2"}])
    assert _findings(tmp_path) == [("bad-expiry-form", "cell:conda-forge-expert/skill")]


def test_verified_without_case(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, state="verified-in-foundry"), _row(2), _row(3, "retire")])
    assert _findings(tmp_path) == [("verified-without-case", "pyforge-atlas:CAP-1")]


@pytest.mark.parametrize("case", ["k-not-on-the-list", "docs/foundry/frames/x.frame.md", ""])
def test_unknown_case(tmp_path: Path, case: str) -> None:
    _tree(tmp_path, rows=[_row(1, case_id=case), _row(2), _row(3, "retire")])
    assert _findings(tmp_path) == [("unknown-case", "pyforge-atlas:CAP-1")]


def test_a_verified_row_with_a_listed_case_passes(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, state="verified-in-foundry", case_id=CASE), _row(2), _row(3, "retire")])
    assert check(tmp_path, LEDGER) == CheckReport()


def test_case_ids_read_the_first_column_of_the_case_list(tmp_path: Path) -> None:
    assert case_ids(tmp_path) == frozenset()
    _write(
        tmp_path,
        CASE_LIST.as_posix(),
        "| id | slice |\n|---|---|\n| k-one | core |\n|k-two|core|\n| not-a-case | core |\nk-three in prose\n",
    )
    assert case_ids(tmp_path) == frozenset({"k-one", "k-two"})


@pytest.mark.parametrize("frozen", [_DROP, [], [""], "src/x"])
def test_rebuilding_without_frozen_paths(tmp_path: Path, frozen: Any) -> None:
    _tree(tmp_path, rows=[_row(1, state="rebuilding", frozen_paths=frozen), _row(2), _row(3, "retire")])
    assert _findings(tmp_path) == [("rebuilding-without-frozen-paths", "pyforge-atlas:CAP-1")]


def test_a_rebuilding_row_with_frozen_paths_passes(tmp_path: Path) -> None:
    row = _row(1, state="rebuilding", frozen_paths=["/".join(("src", "shared", "packages", "pyforge-atlas", ""))])
    _tree(tmp_path, rows=[row, _row(2), _row(3, "retire")])
    assert check(tmp_path, LEDGER) == CheckReport()


def test_launch_not_rebuild(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, launch=True), _row(2, "B-only", launch=True), _row(3, "retire")])
    assert _findings(tmp_path) == [("launch-not-rebuild", "pyforge-atlas:CAP-2")]


def test_pending_without_question(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, mode="pending", state=_DROP), _row(2), _row(3, "retire")])
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("pending-without-question", "pyforge-atlas:CAP-1")]
    assert report.warnings == ()


@pytest.mark.parametrize("question", ["", "   "])
def test_pending_without_question_when_the_question_is_blank(tmp_path: Path, question: str) -> None:
    _tree(tmp_path, rows=[_row(1, mode="pending", state=_DROP, pending_on=question), _row(2), _row(3, "retire")])
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("pending-without-question", "pyforge-atlas:CAP-1")]
    assert report.warnings == ()


def test_mode_pending_with_a_question_is_a_warning(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, mode="pending", state=_DROP, pending_on="steward Q3"), _row(2), _row(3, "retire")])
    report = check(tmp_path, LEDGER)
    assert report.ok
    assert _codes(report.warnings) == [("mode-pending", "pyforge-atlas:CAP-1")]
    assert "'steward Q3'" in report.warnings[0][2]


def test_defaulted_row_is_a_warning_every_run(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, defaulted="2026-11-10"), _row(2), _row(3, "retire")])
    for _ in range(2):
        report = check(tmp_path, LEDGER)
        assert report.ok
        assert _codes(report.warnings) == [("defaulted-row", "pyforge-atlas:CAP-1")]


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("deps", [["pyforge-atlas:CAP-99"], [7], "pyforge-atlas:CAP-2"])
def test_unresolved_dependency(tmp_path: Path, deps: Any) -> None:
    _tree(tmp_path, rows=[_row(1, depends_on=deps), _row(2), _row(3, "retire")])
    assert _findings(tmp_path) == [("unresolved-dependency", "pyforge-atlas:CAP-1")]


def test_a_dependency_on_a_row_or_a_cell_resolves(tmp_path: Path) -> None:
    row = _row(1, depends_on=["pyforge-atlas:CAP-2", "cell:conda-forge-expert/skill"])
    _tree(tmp_path, rows=[row, _row(2), _row(3, "retire")])
    assert check(tmp_path, LEDGER) == CheckReport()


def test_dependency_cycle_is_named_once(tmp_path: Path) -> None:
    rows = [
        _row(1, depends_on=["pyforge-atlas:CAP-2"]),
        _row(2, depends_on=["pyforge-atlas:CAP-1"]),
        _row(3, "retire", depends_on=["pyforge-atlas:CAP-3"]),
    ]
    _tree(tmp_path, rows=rows)
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [
        ("dependency-cycle", "pyforge-atlas:CAP-1"),
        ("dependency-cycle", "pyforge-atlas:CAP-3"),
    ]
    assert report.findings[0][2] == "pyforge-atlas:CAP-1 -> pyforge-atlas:CAP-2 -> pyforge-atlas:CAP-1"


def test_a_dependency_chain_without_a_cycle_passes(tmp_path: Path) -> None:
    rows = [
        _row(1, depends_on=["pyforge-atlas:CAP-2", "pyforge-atlas:CAP-3"]),
        _row(2, depends_on=["pyforge-atlas:CAP-3"]),
        _row(3, "retire", depends_on=[]),
    ]
    _tree(tmp_path, rows=rows)
    assert check(tmp_path, LEDGER) == CheckReport()


# ---------------------------------------------------------------------------
# The flip expiry: lapses only when the root of record is foundry
# ---------------------------------------------------------------------------


def _flip_tree(root: Path) -> None:
    rows = [_row(1, mode="A-only", state=_DROP, expiry="flip"), _row(2), _row(3, "retire")]
    _tree(root, rows=rows, cells=[{**CELL, "expiry": "flip"}])


def test_flip_expiry_lapses_when_the_root_of_record_is_foundry(tmp_path: Path) -> None:
    _flip_tree(tmp_path)
    flags = _flags(tmp_path / "flags", "foundry")
    assert _findings(tmp_path, flags_path=flags) == [
        ("flip-expiry-lapsed", "cell:conda-forge-expert/skill"),
        ("flip-expiry-lapsed", "pyforge-atlas:CAP-1"),
    ]


def test_flip_expiry_holds_while_the_root_of_record_is_local_recipes(tmp_path: Path) -> None:
    _flip_tree(tmp_path)
    flags = _flags(tmp_path / "flags", "local-recipes")
    assert check(tmp_path, LEDGER, flags_path=flags) == CheckReport()


def test_flip_expiry_reads_no_flag_tree_when_no_row_carries_one(tmp_path: Path) -> None:
    _tree(tmp_path)
    assert check(tmp_path, LEDGER, flags_path=tmp_path / "absent" / "flags.json") == CheckReport()


def test_flip_expiry_with_an_unreadable_flag_tree_is_a_named_error(tmp_path: Path) -> None:
    _flip_tree(tmp_path)
    with pytest.raises(CutoverRootError):
        check(tmp_path, LEDGER, flags_path=tmp_path / "absent" / "flags.json")


# ---------------------------------------------------------------------------
# Markers: the Spec heading against the row's mode
# ---------------------------------------------------------------------------


def test_retire_without_marker(tmp_path: Path) -> None:
    _tree(tmp_path, rows=[_row(1, "retire"), _row(2), _row(3, "retire")])
    assert _findings(tmp_path) == [("retire-without-marker", "pyforge-atlas:CAP-1")]


def test_retire_without_marker_accepts_the_legacy_retired_form(tmp_path: Path) -> None:
    body = ATLAS + "- **CAP-4 — RETIRED 2026-11-10 the old export.**\n"
    _tree(tmp_path, body=body, rows=[*_rows(), _row(4, "retire", heading="RETIRED 2026-11-10 the old export")])
    assert check(tmp_path, LEDGER) == CheckReport()


@pytest.mark.parametrize("mode", ["rebuild", "A-only", "B-only"])
def test_marker_contradicts_mode(tmp_path: Path, mode: str) -> None:
    row = _row(3, mode, **({"expiry": "steward:121.5"} if mode == "A-only" else {}))
    _tree(tmp_path, rows=[_row(1), _row(2), row])
    assert _findings(tmp_path) == [("marker-contradicts-mode", "pyforge-atlas:CAP-3")]


@pytest.mark.parametrize(
    "token",
    ["(minted 2026-09-19)", "(unbuilt)", "(deleted 2026-10-01)", "(never built)", "(retired)", "(ready)"],
)
def test_unknown_marker_is_a_finding(tmp_path: Path, token: str) -> None:
    body = ATLAS + f"- **CAP-4 — a capability with a stray token.** {token}\n"
    _tree(tmp_path, body=body, rows=[*_rows(), _row(4, heading="a capability with a stray token")])
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("unknown-marker", "pyforge-atlas:CAP-4")]
    assert token.rstrip(")") in report.findings[0][2]
    assert report.warnings == ()


def test_unknown_marker_is_not_read_where_a_pinned_marker_wins(tmp_path: Path) -> None:
    body = ATLAS + "- **CAP-4 — a capability.** (minted 2026-09-19) (shipped 2026-10-01)\n"
    _tree(tmp_path, body=body, rows=[*_rows(), _row(4, heading="a capability")])
    assert check(tmp_path, LEDGER) == CheckReport()


def test_no_marker_is_a_warning_not_a_finding(tmp_path: Path) -> None:
    body = ATLAS + "- **CAP-4 — a capability with no status.**\n"
    _tree(tmp_path, body=body, rows=[*_rows(), _row(4, heading="a capability with no status")])
    report = check(tmp_path, LEDGER)
    assert report.ok
    assert _codes(report.warnings) == [("no-marker", "pyforge-atlas:CAP-4")]


def test_no_marker_on_a_retire_row_is_also_retire_without_marker(tmp_path: Path) -> None:
    body = ATLAS + "- **CAP-4 — a capability with no status.**\n"
    _tree(tmp_path, body=body, rows=[*_rows(), _row(4, "retire", heading="a capability with no status")])
    report = check(tmp_path, LEDGER)
    assert _codes(report.findings) == [("retire-without-marker", "pyforge-atlas:CAP-4")]
    assert _codes(report.warnings) == [("no-marker", "pyforge-atlas:CAP-4")]
