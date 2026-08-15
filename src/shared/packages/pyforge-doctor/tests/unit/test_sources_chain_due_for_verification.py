"""Unit tests for ``pyforge.doctor.sources.chain.gather_due_for_verification``
(Story 11.1, Epic 11/CAP-1) -- covers every row of the spec's I/O &
Edge-Case Matrix against REAL tmp fixture trees, mirroring
``test_sources_chain_deferred_work.py``'s own real-fixture discipline (no
mocks).

Precise day-count assertions go through ``chain._due_for_verification_findings``
directly, using its injectable ``today`` kwarg (Boundaries: "tests never
depend on wall-clock today()"). Finding-shape / wiring-level assertions go
through the public ``chain.gather_due_for_verification`` and deliberately
avoid the ``today`` question altogether by using fixtures whose outcome is
time-invariant: a missing ``verified:`` line (always "never-verified") or a
far-future ``verified:`` date (always "fresh", since ``days_stale`` is
negative for as long as this suite exists).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import chain

# --- fixture helpers ---------------------------------------------------------


def _project_dir(target: Path, project: str) -> Path:
    return target / "_bmad-output" / "projects" / project


def _write_tracked(target: Path, project: str, text: str) -> Path:
    path = _project_dir(target, project) / "planning-artifacts" / "deferred-work-ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- Never verified ------------------------------------------------------------


def test_no_verified_line_reports_never_verified(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["reason"] == "never-verified"
    assert item["project"] == "proj"
    assert item["id"] == "DW-1"


# --- Stale -----------------------------------------------------------------------


def test_stale_verified_date_reports_stale_with_days_stale(tmp_path: Path) -> None:
    # 2026-07-15 is 31 days before 2026-08-15 -- one day past the 30-day
    # threshold (DUE_FOR_VERIFICATION_STALENESS_DAYS).
    _write_tracked(
        tmp_path, "proj",
        "## DW-1\nstatus: open\nverified: 2026-07-15 — checked once\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    item = findings[0]
    assert item["reason"] == "stale"
    assert item["project"] == "proj"
    assert item["id"] == "DW-1"
    assert item["days_stale"] == 31


def test_verified_one_day_past_threshold_reports_stale(tmp_path: Path) -> None:
    assert chain.DUE_FOR_VERIFICATION_STALENESS_DAYS == 30
    _write_tracked(tmp_path, "proj", "## DW-1\nverified: 2026-07-15\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["reason"] == "stale"
    assert findings[0]["days_stale"] == 31


# --- Fresh -----------------------------------------------------------------------


def test_fresh_verified_date_reports_nothing(tmp_path: Path) -> None:
    _write_tracked(
        tmp_path, "proj",
        "## DW-1\nstatus: open\nverified: 2026-08-10 — recently checked\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert findings == []


def test_verified_exactly_at_threshold_reports_nothing(tmp_path: Path) -> None:
    # 2026-07-16 is EXACTLY 30 days before 2026-08-15 -- "more than 30 days"
    # means exactly 30 is still fresh, not stale.
    _write_tracked(tmp_path, "proj", "## DW-1\nverified: 2026-07-16\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert findings == []


def test_entry_with_two_verified_lines_uses_the_most_recent_one(tmp_path: Path) -> None:
    # Reconciliation appends a fresh `verified:` line rather than replacing
    # the old one (review finding, patch) -- an entry re-checked long after
    # a stale first check must read as fresh, not permanently stale.
    _write_tracked(
        tmp_path, "proj",
        "## DW-1\nstatus: open\n"
        "verified: 2026-01-01 — first check, long ago\n"
        "verified: 2026-08-10 — re-checked recently\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert findings == []


# --- Anonymous entry (never selected) ---------------------------------------------


def test_anonymous_headerless_entry_is_never_selected(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "- source_spec: `foo`\n  verified: 2000-01-01\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert findings == []


# --- Closed/done entry (status is irrelevant) -------------------------------------


def test_closed_done_entry_with_no_verified_line_is_selected_same_as_open(
    tmp_path: Path,
) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: done\nno verified line here\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["reason"] == "never-verified"
    assert findings[0]["id"] == "DW-1"


def test_closed_done_entry_with_stale_verified_is_selected(tmp_path: Path) -> None:
    _write_tracked(
        tmp_path, "proj",
        "## DW-1\nstatus: closed\nverified: 2026-07-15 — was closed already\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["reason"] == "stale"


# --- Malformed verified: date ------------------------------------------------------


def test_malformed_verified_date_is_treated_as_never_verified(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nverified: not-a-real-date\n")

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["reason"] == "never-verified"


# --- No ledger for a project -------------------------------------------------------


def test_project_with_no_tracked_ledger_contributes_zero_findings(tmp_path: Path) -> None:
    _project_dir(tmp_path, "proj").mkdir(parents=True, exist_ok=True)

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert findings == []


# --- Multi-project isolation ---------------------------------------------------------


def test_two_projects_only_due_projects_entries_are_reported(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "alpha", "## DW-1\nstatus: open\n")  # never-verified, due
    _write_tracked(
        tmp_path, "beta", "## DW-1\nverified: 2026-08-10 — recent\n",
    )  # fresh, not due

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))

    assert len(findings) == 1
    assert findings[0]["project"] == "alpha"


def test_findings_evidence_project_key_names_its_own_project_via_public_api(
    tmp_path: Path,
) -> None:
    _write_tracked(tmp_path, "alpha", "## DW-1\nstatus: open\n")  # never-verified, due
    _write_tracked(tmp_path, "beta", "## DW-1\nverified: 9999-01-01\n")  # far future, fresh

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.evidence["project"] == "alpha"


# --- No projects tree at all --------------------------------------------------------


def test_no_projects_tree_reports_one_warn(tmp_path: Path) -> None:
    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DUE_FOR_VERIFICATION
    assert finding.check == "due-for-verification-unevaluable"
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence == {"target": str(tmp_path)}
    assert "cannot be evaluated here" in finding.message


# --- Fleet-wide none due -------------------------------------------------------------


def test_fleet_wide_none_due_reports_vacuous_ok_never_empty(tmp_path: Path) -> None:
    _project_dir(tmp_path, "proj").mkdir(parents=True, exist_ok=True)

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DUE_FOR_VERIFICATION
    assert finding.check == "due-for-verification"
    assert finding.status is DoctorStatus.OK
    assert finding.evidence == {"projects_scanned": 0}


def test_fully_fresh_project_reports_vacuous_ok_with_scanned_count(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nverified: 9999-01-01\n")

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"projects_scanned": 1}


# --- Finding shape through the public API (never-verified, time-invariant) -----------


def test_gather_wraps_never_verified_finding_with_correct_shape(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DUE_FOR_VERIFICATION
    assert finding.check == "due-for-verification"
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["reason"] == "never-verified"
    assert finding.evidence["project"] == "proj"
    assert finding.evidence["id"] == "DW-1"


def test_gather_never_emits_fail_status(tmp_path: Path) -> None:
    # A mix of never-verified and definitely-stale (far-past) entries --
    # every one of these must WARN, never FAIL (Boundaries).
    _write_tracked(
        tmp_path, "proj",
        "## DW-1\nstatus: open\n\n## DW-2\nverified: 2000-01-01 — ancient\n",
    )

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 2
    assert all(f.status is DoctorStatus.WARN for f in findings)


# --- Unreadable ledger: isolated WARN, other projects unaffected ---------------------


def test_unreadable_tracked_ledger_directory_is_isolated_as_warn(tmp_path: Path) -> None:
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    pa_dir = _project_dir(tmp_path, "proj") / "planning-artifacts"
    pa_dir.chmod(0o000)
    try:
        findings = chain.gather_due_for_verification(tmp_path)
    finally:
        pa_dir.chmod(0o755)

    assert [f.check for f in findings] == ["due-for-verification-unevaluable"]
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].evidence["project"] == "proj"
    assert "could not be evaluated here" in findings[0].message


def test_one_unevaluable_project_does_not_hide_another_projects_real_finding(
    tmp_path: Path, monkeypatch,
) -> None:
    """Mirrors ``test_sources_chain_deferred_work.py``'s own per-project
    isolation test: one project's unreadable ledger must not discard a
    DIFFERENT, well-formed project's real finding."""
    _write_tracked(tmp_path, "good", "## DW-1\nstatus: open\n")  # real due entry
    _project_dir(tmp_path, "zbroken").mkdir(parents=True, exist_ok=True)

    real = chain._check_project_due_for_verification

    def _explode(target, proj, findings, today):
        if proj.name == "zbroken":
            raise RuntimeError("unanticipated shape")
        return real(target, proj, findings, today)

    monkeypatch.setattr(chain, "_check_project_due_for_verification", _explode)

    findings = chain.gather_due_for_verification(tmp_path)

    by_check: dict[str, list] = {}
    for f in findings:
        by_check.setdefault(f.check, []).append(f)

    assert "due-for-verification" in by_check, (
        f"one project's failure hid another's real finding: {[f.check for f in findings]}"
    )
    good = next(f for f in by_check["due-for-verification"] if f.evidence["project"] == "good")
    assert good.status is DoctorStatus.WARN

    warn = next(f for f in by_check["due-for-verification-unevaluable"])
    assert warn.status is DoctorStatus.WARN
    assert warn.evidence["project"] == "zbroken"


# --- Never raises: non-UTF-8 bytes -----------------------------------------------


def test_non_utf8_tracked_ledger_never_raises(tmp_path: Path) -> None:
    tracked = _project_dir(tmp_path, "proj") / "planning-artifacts" / "deferred-work-ledger.md"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_bytes(b"## DW-1\nverified: caf\xe9\n")

    findings = chain.gather_due_for_verification(tmp_path)

    assert findings  # returned rather than raised
    assert all(f.source is Source.DUE_FOR_VERIFICATION for f in findings)
    assert findings[0].evidence["reason"] == "never-verified"


# --- degrade_on_exception safety net -------------------------------------------------


def test_gather_degrades_on_unexpected_exception(tmp_path: Path, monkeypatch) -> None:
    def _boom(target: Path, *, today=None):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(chain, "_due_for_verification_findings", _boom)

    findings = chain.gather_due_for_verification(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].source is Source.DUE_FOR_VERIFICATION
    assert "RuntimeError" in findings[0].message
