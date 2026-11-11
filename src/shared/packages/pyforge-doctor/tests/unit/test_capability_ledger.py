"""The capability-ledger source: Stories 55.2, 35.1 and 56.2.

``spec-foundry-capability-ledger:CAP-2``'s extract, ``spec-pyforge-doctor:CAP-87``'s post-PIN rule and
``spec-pyforge-doctor:CAP-95``'s row checks (Spec, heading, path, mode and the expiry clock). Every test builds
the tree it reads under ``tmp_path``, with made-up project names and an injected clock, so this module runs in
the package half on any root. The one read of this repository's own case list lives in
``test_live_capability_ledger_case_list.py``.
"""

from __future__ import annotations

import inspect
import json
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml
from pyforge.core.cutover_root import CUTOVER_FLAG, LOCAL_DEV_RELATIVE

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources import capability_ledger
from pyforge.doctor.sources.capability_ledger import (
    UNIQUE_WHY_FIXTURE_SENTENCE,
    extract_caps,
    gather,
    iter_live_specs,
    parse_case_list_ids,
)

_TODAY = date(2026, 11, 11)

_FIXTURE_SPEC = f"""---
spec: fixture-ledger-spec
status: ready
---

# SPEC — fixture

## Why

**A pain to solve.** {UNIQUE_WHY_FIXTURE_SENTENCE}

## Capabilities

- **CAP-9 — Example capability.**
  - **intent:** classify this heading extract only
  - **success:** CAP-9 is visible and Why is not stored
"""

# Made-up project and Spec names: nothing here names a tracked path.
_SPEC_REL = "_bmad-output/projects/fixture-station/planning-artifacts/specs/spec-fixture-ledger-spec/SPEC.md"
_ROW_ID = "fixture-ledger-spec:CAP-9"
_HEADING = "Example capability"


# --- fixtures -------------------------------------------------------------------------------------------------


def _write_spec(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_ledger(
    root: Path,
    capabilities: list[dict],
    source_sha: str = "",
    *,
    cells: list[dict] | None = None,
) -> None:
    path = root / "docs" / "foundry" / "capability-ledger.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "schema": "pyforge.capability-ledger/v1",
        "source_sha": source_sha,
        "capabilities": capabilities,
    }
    if cells is not None:
        payload["cells"] = cells
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_ledger_text(root: Path, text: str) -> None:
    path = root / "docs" / "foundry" / "capability-ledger.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _row(**extra: object) -> dict:
    row: dict = {
        "id": _ROW_ID,
        "spec": "fixture-ledger-spec",
        "station": "fixture-station",
        "heading": _HEADING,
        "path": _SPEC_REL,
        "mode": "rebuild",
    }
    row.update(extra)
    return row


def _a_only(expiry: object, **extra: object) -> dict:
    return _row(mode="A-only", expiry=expiry, **extra)


def _cell(expiry: object) -> dict:
    return {"id": "cell:fixture/skill", "path": ".fixture/skill/", "mode": "A-only", "expiry": expiry}


def _tree(root: Path, rows: list[dict], *, cells: list[dict] | None = None) -> Path:
    _write_spec(root, _SPEC_REL, _FIXTURE_SPEC)
    _write_ledger(root, rows, cells=cells)
    return root


def _write_station_ledger(root: Path, station: str, statuses: dict[str, str]) -> None:
    path = (
        root / "_bmad-output" / "projects" / f"pyforge-{station}" / "planning-artifacts" / "sprint-status-ledger.yaml"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"development_status": statuses}, sort_keys=False), encoding="utf-8")


def _write_flags(root: Path, variant: str) -> None:
    path = root / LOCAL_DEV_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    flag = {
        "state": "ENABLED",
        "variants": {"local-recipes": "local-recipes", "foundry": "foundry"},
        "defaultVariant": variant,
    }
    path.write_text(json.dumps({"flags": {CUTOVER_FLAG: flag}}), encoding="utf-8")


def _judge(root: Path, today: date = _TODAY) -> tuple[Finding, ...]:
    return gather(root, today=today)


def _not_ok(findings: tuple[Finding, ...]) -> list[Finding]:
    return [f for f in findings if f.status is not DoctorStatus.OK]


def _kinds(findings: tuple[Finding, ...]) -> list[tuple[DoctorStatus, str]]:
    return [(f.status, f.evidence.get("kind", "")) for f in _not_ok(findings)]


def _only_ok(findings: tuple[Finding, ...]) -> bool:
    return [f.status for f in findings] == [DoctorStatus.OK]


# --- the extract (extract.md) ---------------------------------------------------------------------------------


def test_extract_sees_cap_9_not_unique_why_sentence():
    rows = extract_caps(_FIXTURE_SPEC)
    assert [(cap.n, cap.heading) for cap in rows] == [(9, "Example capability")]
    blob = "\n".join(f"{cap.heading}\n{cap.intent}\n{cap.success}" for cap in rows)
    assert UNIQUE_WHY_FIXTURE_SENTENCE not in blob
    assert "classify this heading extract only" in blob
    assert "CAP-9 is visible and Why is not stored" in blob


def test_extract_reads_the_three_heading_forms():
    # extract.md § Heading forms: the title inside the bold, the title after the dash, the `pap:` prefix; the dash
    # an em dash, an en dash or a hyphen; the marker and anything after the bold are not the heading.
    text = (
        "- **CAP-1 — Tracked ledger.** (shipped 2026-09-09)\n"
        "* **CAP-2 – en dash title** (ready 2026-10-01)\n"
        "  - **CAP-3 - hyphen title.***\n"
        "- **CAP-4** — plain title ← spec-x CAP-4 (shipped 2026-09-09)\n"
        "- **CAP-5** — plain with marker (retired 2026-11-10: never built)\n"
        "- **CAP-6** (shipped 2026-09-09)\n"
        "- **pap:CAP-1 — The host renders from the accelerator shape.**\n"
    )
    assert [(cap.prefix, cap.n, cap.heading) for cap in extract_caps(text)] == [
        ("", 1, "Tracked ledger"),
        ("", 2, "en dash title"),
        ("", 3, "hyphen title"),
        ("", 4, "plain title"),
        ("", 5, "plain with marker"),
        ("", 6, ""),
        ("pap", 1, "The host renders from the accelerator shape"),
    ]


def test_extract_ignores_bold_that_is_not_a_heading():
    text = (
        "- **CAP-62:** which duty moves the row?\n"
        "- **CAP-81 keeps the refusal semantics** of Story 17-1.\n"
        "- **CAP-5 (tasks move, never duplicate):** a task name exists once.\n"
        "Prose naming **CAP-9 — not at the line start**.\n"
    )
    assert extract_caps(text) == []


def test_extract_keeps_the_first_heading_of_a_number_and_prefix():
    text = "- **CAP-1 — first.**\n- **CAP-1 — second.**\n- **pap:CAP-1 — prefixed.**\n"
    assert [(cap.prefix, cap.n, cap.heading) for cap in extract_caps(text)] == [
        ("", 1, "first"),
        ("pap", 1, "prefixed"),
    ]


def test_extract_takes_intent_and_success_before_the_next_heading_or_section():
    text = (
        "- **CAP-1 — one.**\n"
        "  - **intent:** the first intent.\n"
        "  - **success:** the first success.\n"
        "  - **intent:** a second intent is not taken.\n"
        "- **CAP-2 — two.**\n"
        "  - **intent:** the second intent.\n"
        "\n## Constraints\n\n"
        "- **success:** a Constraint bullet is not CAP-2's success.\n"
    )
    first, second = extract_caps(text)
    assert (first.intent, first.success) == ("the first intent.", "the first success.")
    assert (second.intent, second.success) == ("the second intent.", "")


@pytest.mark.parametrize(
    ("folder", "body", "expected"),
    [
        ("spec-python-foundry-cutover", "- **CAP-9 — t.**\n", "fnd:CAP-9"),
        ("spec-foundry-regenerate-not-fold", "- **CAP-2 — t.**\n", "fnr:CAP-2"),
        ("spec-foundry-capability-ledger", "- **CAP-1 — t.**\n", "fcl:CAP-1"),
        ("spec-fixture-unifying", "- **pap:CAP-3 — t.**\n", "pap:CAP-3"),
        ("spec-fixture-unifying", "- **CAP-3 — t.**\n", "fixture-unifying:CAP-3"),
    ],
)
def test_cite_id_follows_the_id_rule(tmp_path: Path, folder: str, body: str, expected: str):
    rel = f"_bmad-output/projects/fixture-station/planning-artifacts/specs/{folder}/SPEC.md"
    _write_spec(tmp_path, rel, f"---\nstatus: ready\n---\n\n{body}")
    assert [cap.cite_id for cap in iter_live_specs(tmp_path)] == [expected]


def test_status_with_a_trailing_comment_is_live(tmp_path: Path):
    body = _FIXTURE_SPEC.replace("status: ready\n", "status: ready   # 2026-09-14 — seeded draft, flipped\n")
    _write_spec(tmp_path, _SPEC_REL, body)
    assert [cap.cite_id for cap in iter_live_specs(tmp_path)] == [_ROW_ID]


def test_parse_case_list_ids_reads_the_first_column():
    text = (
        "| id | slice | argv / nodeid | expected row | A-only expiry |\n"
        "|---|---|---|---|---|\n"
        "| k-core-cutover-default | core | node | pass | — |\n"
        "| k-steward-help | steward | node | pass | — |\n"
        "| not-a-case | x | y | z | — |\n"
    )
    assert parse_case_list_ids(text) == frozenset({"k-core-cutover-default", "k-steward-help"})


def test_module_never_calls_node_from_text_file():
    source = inspect.getsource(capability_ledger)
    assert "_node_from_text_file" not in source
    assert "20000" not in source


# --- spec-pyforge-doctor:CAP-87 and the HARD findings it keeps -----------------------------------------------


def test_unclassified_cap_is_hard(tmp_path: Path):
    _tree(tmp_path, [])
    findings = _judge(tmp_path)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert fails
    assert any("unclassified" in f.message for f in fails)
    assert all(f.source is Source.CAPABILITY_LEDGER for f in findings)


def test_a_only_without_expiry_is_hard(tmp_path: Path):
    row = _row(mode="A-only")
    _tree(tmp_path, [row])
    findings = _judge(tmp_path)
    assert _kinds(findings) == [(DoctorStatus.FAIL, "undated-a-only")]
    assert "A-only without expiry" in findings[0].message


def test_classified_a_only_with_expiry_is_ok(tmp_path: Path):
    _tree(tmp_path, [_a_only("2026-12-31")])
    assert _only_ok(_judge(tmp_path))


def _write_case_list(root: Path, ids: tuple[str, ...] = ("k-core-cutover-default",)) -> None:
    path = root / capability_ledger._CASE_LIST
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"| {cid} | core | node | pass | — |" for cid in ids)
    path.write_text(
        "# Thin oracle\n\n| id | slice | argv / nodeid | expected row | A-only expiry |\n"
        "|---|---|---|---|---|\n"
        f"{rows}\n",
        encoding="utf-8",
    )


def test_verified_without_case_id_is_hard(tmp_path: Path):
    _write_case_list(tmp_path)
    _tree(tmp_path, [_row(state="verified-in-foundry")])
    findings = _judge(tmp_path)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert any("without a case-list id" in f.message for f in fails)


def test_verified_with_listed_id_is_not_hard_for_this_reason(tmp_path: Path):
    _write_case_list(tmp_path)
    _tree(tmp_path, [_row(state="verified-in-foundry", case_id="k-core-cutover-default")])
    findings = _judge(tmp_path)
    assert not any(f.evidence.get("kind", "").startswith("verified-") for f in findings)
    assert _only_ok(findings)


def test_verified_frame_preflight_is_hard(tmp_path: Path):
    _write_case_list(tmp_path)
    # A made-up Frame path: a Frame pre-flight is never a case-list id.
    _tree(tmp_path, [_row(state="verified-in-foundry", case_id="docs/foundry/frames/fixture.frame.md")])
    findings = _judge(tmp_path)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert any("not a 54.1 case-list id" in f.message for f in fails)


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        text=True,
    ).strip()


def _pinned_repo(tmp_path: Path) -> tuple[Path, str]:
    """A throwaway git repo whose first commit is the ledger PIN."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "35.1@example.test")
    _git(repo, "config", "user.name", "Story 35.1")
    (repo / "README.md").write_text("pin\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "pin")
    return repo, _git(repo, "rev-parse", "HEAD")


def test_post_pin_spec_without_row_is_append(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    _write_spec(repo, _SPEC_REL, _FIXTURE_SPEC)
    _write_ledger(repo, [], source_sha=pin)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "post-pin spec")

    findings = _judge(repo)
    warns = [f for f in findings if f.status is DoctorStatus.WARN]
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert not fails
    assert any("--append" in f.message for f in warns)
    assert any(f.evidence.get("kind") == "append" for f in warns)


def _post_pin_spec(status: str | None, *, with_cap: bool) -> str:
    frontmatter = "spec: fixture-ledger-spec\n" + (f"status: {status}\n" if status else "")
    cap = (
        "\n- **CAP-9 — Example capability.**\n"
        "  - **intent:** classify this heading extract only\n"
        "  - **success:** CAP-9 is visible\n"
        if with_cap
        else "\nNo capability heading here.\n"
    )
    return f"---\n{frontmatter}---\n\n# SPEC — fixture\n{cap}"


def _commit_post_pin_spec(
    repo: Path,
    pin: str,
    body: str,
    *,
    rows: list[dict] | None = None,
) -> None:
    _write_spec(repo, _SPEC_REL, body)
    _write_ledger(repo, rows or [], source_sha=pin)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "post-pin spec")


@pytest.mark.parametrize("status", ["absorbed", "draft", "shipped", None])
def test_post_pin_non_live_spec_reports_nothing(tmp_path: Path, status: str | None):
    repo, pin = _pinned_repo(tmp_path)
    _commit_post_pin_spec(repo, pin, _post_pin_spec(status, with_cap=True))

    assert _only_ok(_judge(repo))


def test_post_pin_live_spec_without_cap_or_row_is_one_append_warn(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    _commit_post_pin_spec(repo, pin, _post_pin_spec("ready", with_cap=False))

    findings = _judge(repo)

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert findings[0].evidence == {"kind": "append", "path": _SPEC_REL}
    assert _SPEC_REL in findings[0].message


def test_post_pin_in_progress_spec_with_unclassified_cap_keeps_per_cap_warn(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    _commit_post_pin_spec(repo, pin, _post_pin_spec("in-progress", with_cap=True))

    findings = _judge(repo)

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert findings[0].message == "fixture-ledger-spec:CAP-9: post-PIN unclassified --append"
    assert findings[0].evidence["kind"] == "append"


def test_post_pin_live_spec_with_a_row_for_its_path_reports_no_append(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    _commit_post_pin_spec(
        repo,
        pin,
        _post_pin_spec("ready", with_cap=False),
        rows=[_row(id="fixture-ledger-spec:CAP-1")],
    )

    findings = _judge(repo)

    # The row names the path, so the post-PIN rule says nothing; the row itself holds no live capability
    # (spec-pyforge-doctor:CAP-95).
    assert _kinds(findings) == [(DoctorStatus.FAIL, "orphan-row")]


def test_post_pin_spec_gone_from_working_tree_reports_nothing(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    _commit_post_pin_spec(repo, pin, _post_pin_spec("ready", with_cap=False))
    # Committed after the PIN, then deleted without a commit: still in ``PIN..HEAD``.
    (repo / _SPEC_REL).unlink()

    # ``gather`` degrades an unguarded read into a finding, so assert no non-OK finding at all.
    assert _only_ok(_judge(repo))


def test_post_pin_non_live_spec_does_not_mask_a_live_one(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    specs = "_bmad-output/projects/fixture-station/planning-artifacts/specs"
    live_rel = f"{specs}/spec-z-live/SPEC.md"
    # ``sorted(added)`` walks the absorbed Spec first; skipping it must not end the loop.
    _write_spec(repo, f"{specs}/spec-a-absorbed/SPEC.md", _post_pin_spec("absorbed", with_cap=False))
    _write_spec(repo, live_rel, _post_pin_spec("ready", with_cap=False))
    _write_ledger(repo, [], source_sha=pin)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "post-pin specs")

    findings = _judge(repo)

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert findings[0].evidence == {"kind": "append", "path": live_rel}


def test_post_pin_spec_present_but_unreadable_degrades_not_skips(tmp_path: Path):
    repo, pin = _pinned_repo(tmp_path)
    # Off the inventory glob (``specs/spec-*/SPEC.md``), so ``iter_live_specs`` never reads it first.
    rel = "_bmad-output/projects/fixture-station/planning-artifacts/specs/spec-fixture-ledger-spec/nested/SPEC.md"
    _write_spec(repo, rel, _post_pin_spec("ready", with_cap=False))
    _write_ledger(repo, [], source_sha=pin)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "post-pin spec")
    (repo / rel).unlink()
    (repo / rel).mkdir()  # present but not a file: only a *gone* path is skipped

    findings = _judge(repo)

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert "could not be evaluated" in findings[0].message


# --- spec-pyforge-doctor:CAP-95: each row is true to its Spec, its heading, its path and its mode -------------


@pytest.mark.parametrize(
    "row",
    [
        _row(mode="rebuild", state="planned"),
        _row(mode="retire"),
        _row(mode="B-only"),
        _a_only("2027-06-30"),
    ],
    ids=["rebuild", "retire", "B-only", "A-only"],
)
def test_the_four_modes_are_silent(tmp_path: Path, row: dict):
    _tree(tmp_path, [row])
    assert _only_ok(_judge(tmp_path))


def test_heading_drift_is_a_fail(tmp_path: Path):
    _tree(tmp_path, [_row(heading="Example capability, as the ledger once read it")])
    findings = _not_ok(_judge(tmp_path))
    assert [(f.status, f.evidence["kind"]) for f in findings] == [(DoctorStatus.FAIL, "heading-drift")]
    assert findings[0].evidence["spec_heading"] == _HEADING
    assert findings[0].evidence["heading"] == "Example capability, as the ledger once read it"


def test_heading_drift_on_a_missing_heading_is_a_fail(tmp_path: Path):
    row = _row()
    del row["heading"]
    _tree(tmp_path, [row])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "heading-drift")]


def test_archived_spec_row_is_a_fail(tmp_path: Path):
    archived = "archive/_bmad-output/projects/fixture-station/planning-artifacts/specs/spec-fixture-gone/SPEC.md"
    _tree(tmp_path, [_row(), _row(id="fixture-gone:CAP-1", spec="fixture-gone", path=archived)])
    findings = _not_ok(_judge(tmp_path))
    assert [(f.status, f.evidence["kind"]) for f in findings] == [(DoctorStatus.FAIL, "archived-spec-row")]
    assert findings[0].evidence["path"] == archived


def test_orphan_row_is_a_fail(tmp_path: Path):
    _tree(tmp_path, [_row(), _row(id="fixture-ledger-spec:CAP-10", heading="No such capability")])
    findings = _not_ok(_judge(tmp_path))
    assert [(f.status, f.evidence["kind"], f.evidence["id"]) for f in findings] == [
        (DoctorStatus.FAIL, "orphan-row", "fixture-ledger-spec:CAP-10")
    ]


def test_orphan_row_on_a_non_live_spec_is_a_fail(tmp_path: Path):
    _write_spec(tmp_path, _SPEC_REL, _FIXTURE_SPEC.replace("status: ready", "status: absorbed"))
    _write_ledger(tmp_path, [_row()])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "orphan-row")]


@pytest.mark.parametrize("mode", ["move", None, "rebuilding", ["rebuild"]])
def test_bad_mode_is_a_fail(tmp_path: Path, mode: object):
    _tree(tmp_path, [_row(mode=mode)])
    findings = _not_ok(_judge(tmp_path))
    assert [(f.status, f.evidence["kind"]) for f in findings] == [(DoctorStatus.FAIL, "bad-mode")]
    assert findings[0].evidence["mode"] == mode


def test_pending_mode_is_one_warn(tmp_path: Path):
    _tree(tmp_path, [_row(mode="pending", pending_on="fixture Q1")])
    findings = _judge(tmp_path)
    assert [(f.status, f.evidence["kind"]) for f in findings] == [(DoctorStatus.WARN, "mode-pending")]
    assert findings[0].evidence["pending_on"] == "fixture Q1"


def test_governance_spec_row_resolves(tmp_path: Path):
    rel = "docs/governance/spec-fixture-governance/SPEC.md"
    _write_spec(
        tmp_path,
        rel,
        "---\nstatus: ready   # seeded draft, ruled the same day\n---\n\n- **CAP-5 — A governance capability.**\n",
    )
    row = _row(
        id="fixture-governance:CAP-5",
        spec="fixture-governance",
        station="governance",
        heading="A governance capability",
        path=rel,
    )
    _write_ledger(tmp_path, [row])
    assert _only_ok(_judge(tmp_path))


def test_governance_spec_row_with_a_drifted_heading_is_a_fail(tmp_path: Path):
    rel = "docs/governance/spec-fixture-governance/SPEC.md"
    _write_spec(tmp_path, rel, "---\nstatus: ready\n---\n\n- **CAP-5 — A governance capability.**\n")
    row = _row(id="fixture-governance:CAP-5", spec="fixture-governance", heading="Another title", path=rel)
    _write_ledger(tmp_path, [row])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "heading-drift")]


@pytest.mark.parametrize(
    ("status", "expected"),
    [("done", [(DoctorStatus.FAIL, "a-only-expiry-lapsed")]), ("blocked", [])],
)
def test_cells_entry_expiry_is_judged_like_a_row(tmp_path: Path, status: str, expected: list):
    _write_station_ledger(tmp_path, "mason", {"39-2-fixture-conda-forge-expert-gets-its-own-spec": status})
    _tree(tmp_path, [_row()], cells=[_cell("mason:39.2")])
    assert _kinds(_judge(tmp_path)) == expected


def test_cells_entry_without_expiry_is_hard(tmp_path: Path):
    _tree(tmp_path, [_row()], cells=[_cell(None)])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "undated-a-only")]


def test_no_ledger_is_unevaluable(tmp_path: Path):
    _write_spec(tmp_path, _SPEC_REL, _FIXTURE_SPEC)
    findings = _judge(tmp_path)
    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert findings[0].evidence["unevaluable"] is True
    assert findings[0].check == "capability-ledger-unevaluable"
    assert not any(f.status is DoctorStatus.OK for f in findings)


@pytest.mark.parametrize(
    "text",
    [
        "schema: pyforge.capability-ledger/v1\n",
        "schema: pyforge.capability-ledger/v1\ncapabilities:\n  id: not-a-list\n",
        "- a list, not a mapping\n",
        "capabilities: [unclosed\n",
    ],
    ids=["no-key", "not-a-list", "not-a-mapping", "not-yaml"],
)
def test_no_capabilities_is_unevaluable(tmp_path: Path, text: str):
    _write_spec(tmp_path, _SPEC_REL, _FIXTURE_SPEC)
    _write_ledger_text(tmp_path, text)
    findings = _judge(tmp_path)
    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert findings[0].evidence["unevaluable"] is True
    assert findings[0].check == "capability-ledger-unevaluable"


# --- spec-pyforge-doctor:CAP-95: the expiry clock (modes.md § Expiry) ------------------------------------------


def _date_expiry_kinds(tmp_path: Path, days: int) -> list[tuple[DoctorStatus, str]]:
    _tree(tmp_path, [_a_only((_TODAY + timedelta(days=days)).isoformat())])
    return _kinds(_judge(tmp_path))


def test_date_expiry_31_days_out_is_silent(tmp_path: Path):
    assert _date_expiry_kinds(tmp_path, 31) == []


def test_date_expiry_30_days_out_warns_a_only_expiring(tmp_path: Path):
    assert _date_expiry_kinds(tmp_path, 30) == [(DoctorStatus.WARN, "a-only-expiring")]


def test_date_expiry_today_warns_a_only_expiring(tmp_path: Path):
    assert _date_expiry_kinds(tmp_path, 0) == [(DoctorStatus.WARN, "a-only-expiring")]


def test_date_expiry_yesterday_fails_a_only_expired(tmp_path: Path):
    assert _date_expiry_kinds(tmp_path, -1) == [(DoctorStatus.FAIL, "a-only-expired")]


def test_date_expiry_reads_the_real_clock_when_none_is_injected(tmp_path: Path):
    _tree(tmp_path, [_a_only((date.today() - timedelta(days=1)).isoformat())])
    assert _kinds(gather(tmp_path)) == [(DoctorStatus.FAIL, "a-only-expired")]


def test_impossible_date_expiry_is_unresolved(tmp_path: Path):
    _tree(tmp_path, [_a_only("2026-02-30")])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "a-only-expiry-unresolved")]


def test_story_expiry_done_fails_a_only_expiry_lapsed(tmp_path: Path):
    _write_station_ledger(tmp_path, "steward", {"44-8-the-working-set": "done"})
    _tree(tmp_path, [_a_only("steward:44.8")])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "a-only-expiry-lapsed")]


@pytest.mark.parametrize("status", ["blocked", "backlog", "in-progress"])
def test_story_expiry_not_done_is_silent(tmp_path: Path, status: str):
    _write_station_ledger(tmp_path, "steward", {"44-8-the-working-set": status})
    _tree(tmp_path, [_a_only("steward:44.8")])
    assert _only_ok(_judge(tmp_path))


def test_story_expiry_absent_key_fails_a_only_expiry_unresolved(tmp_path: Path):
    _write_station_ledger(tmp_path, "steward", {"44-9-mason-submits": "blocked"})
    _tree(tmp_path, [_a_only("steward:44.8")])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "a-only-expiry-unresolved")]


def test_story_expiry_prefix_needs_its_dash(tmp_path: Path):
    # `44.1` resolves to the key prefix `44-1-`, never to `44-14-...`.
    _write_station_ledger(tmp_path, "steward", {"44-14-rebuild-harness-and-oracle-gate": "done"})
    _tree(tmp_path, [_a_only("steward:44.1")])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "a-only-expiry-unresolved")]


def test_story_expiry_of_a_station_with_no_ledger_is_unresolved(tmp_path: Path):
    _tree(tmp_path, [_a_only("nowhere:1.1")])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "a-only-expiry-unresolved")]


def test_mason_row_steward_story_expiry_resolves_in_stewards_ledger(tmp_path: Path):
    # A mason row naming steward's 44.8: the station in the expiry, not the row's own, holds the key.
    _write_station_ledger(tmp_path, "steward", {"44-8-the-working-set": "done"})
    _write_station_ledger(tmp_path, "mason", {"44-8-a-mason-story-of-the-same-number": "backlog"})
    _tree(tmp_path, [_a_only("steward:44.8", station="pyforge-mason")])
    findings = _not_ok(_judge(tmp_path))
    assert [(f.status, f.evidence["kind"]) for f in findings] == [(DoctorStatus.FAIL, "a-only-expiry-lapsed")]
    assert findings[0].evidence["expiry"] == "steward:44.8"


@pytest.mark.parametrize(
    ("status", "expected"),
    [("done", [(DoctorStatus.FAIL, "a-only-expiry-lapsed")]), ("backlog", [])],
)
def test_qualified_story_expiry_resolves_in_its_own_stations_ledger(tmp_path: Path, status: str, expected: list):
    _write_station_ledger(tmp_path, "mason", {"39-2-conda-forge-expert-gets-its-own-spec": status})
    _write_station_ledger(tmp_path, "steward", {"39-2-a-steward-story-of-the-same-number": "done"})
    _tree(tmp_path, [_a_only("mason:39.2")])
    assert _kinds(_judge(tmp_path)) == expected


def test_bare_story_expiry_is_unresolved_never_a_steward_key(tmp_path: Path):
    _write_station_ledger(tmp_path, "steward", {"44-8-the-working-set": "done"})
    _tree(tmp_path, [_a_only("44.8")])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "a-only-expiry-unresolved")]


def test_unknown_form_expiry_is_unresolved(tmp_path: Path):
    _tree(tmp_path, [_a_only("when the platform moves")])
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "a-only-expiry-unresolved")]


def test_float_expiry_fails_a_only_expiry_unquoted(tmp_path: Path):
    # YAML reads an unquoted 44.10 as the number 44.1: the Story it meant cannot be recovered.
    _write_spec(tmp_path, _SPEC_REL, _FIXTURE_SPEC)
    row = yaml.safe_dump([_row(mode="A-only")], sort_keys=False)
    _write_ledger_text(tmp_path, "capabilities:\n" + row.replace("mode: A-only\n", "mode: A-only\n  expiry: 44.10\n"))
    findings = _not_ok(_judge(tmp_path))
    assert [(f.status, f.evidence["kind"]) for f in findings] == [(DoctorStatus.FAIL, "a-only-expiry-unquoted")]
    assert findings[0].evidence["expiry"] == 44.1


def test_unquoted_date_expiry_fails_a_only_expiry_unquoted(tmp_path: Path):
    _write_spec(tmp_path, _SPEC_REL, _FIXTURE_SPEC)
    row = yaml.safe_dump([_row(mode="A-only")], sort_keys=False)
    _write_ledger_text(
        tmp_path, "capabilities:\n" + row.replace("mode: A-only\n", "mode: A-only\n  expiry: 2027-01-31\n")
    )
    assert _kinds(_judge(tmp_path)) == [(DoctorStatus.FAIL, "a-only-expiry-unquoted")]


def test_expiry_on_a_row_that_is_not_a_only_is_not_judged(tmp_path: Path):
    # The form of a row is the control-plane validator's (`bad-expiry-form`); this source judges A-only time.
    _tree(tmp_path, [_row(mode="rebuild", expiry="2000-01-01")])
    assert _only_ok(_judge(tmp_path))


def test_flip_expiry_is_silent_under_local_recipes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    _write_flags(tmp_path, "local-recipes")
    _tree(tmp_path, [_a_only("flip")], cells=[_cell("flip")])
    assert _only_ok(_judge(tmp_path))


def test_flip_expiry_fails_a_only_expiry_flipped_under_foundry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    _write_flags(tmp_path, "foundry")
    _tree(tmp_path, [_a_only("flip")], cells=[_cell("flip")])
    findings = _not_ok(_judge(tmp_path))
    assert [(f.status, f.evidence["kind"], f.evidence["id"]) for f in findings] == [
        (DoctorStatus.FAIL, "a-only-expiry-flipped", _ROW_ID),
        (DoctorStatus.FAIL, "a-only-expiry-flipped", "cell:fixture/skill"),
    ]


def test_flip_expiry_on_an_unreadable_flag_tree_is_one_unevaluable_warn(tmp_path: Path):
    # No flag tree under the target: CutoverRootError, one cannot-evaluate WARN for the flip rows only.
    _tree(tmp_path, [_a_only("flip"), _row(id="fixture-ledger-spec:CAP-10", heading="x")], cells=[_cell("flip")])
    findings = _not_ok(_judge(tmp_path))
    unevaluable = [f for f in findings if f.evidence.get("unevaluable") is True]
    assert len(unevaluable) == 1
    assert unevaluable[0].status is DoctorStatus.WARN
    assert unevaluable[0].check == "capability-ledger-unevaluable"
    assert unevaluable[0].evidence["ids"] == [_ROW_ID, "cell:fixture/skill"]
    # Every other row is still judged.
    assert [f.evidence.get("kind") for f in findings if f not in unevaluable] == ["orphan-row"]


def test_flip_expiry_absent_reads_no_flag_tree(tmp_path: Path):
    # No flip row, no flag tree: nothing to read, nothing to report.
    _tree(tmp_path, [_a_only("2027-06-30")])
    assert not (tmp_path / LOCAL_DEV_RELATIVE).exists()
    assert _only_ok(_judge(tmp_path))
