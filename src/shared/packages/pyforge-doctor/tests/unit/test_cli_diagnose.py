"""Unit tests for ``pyforge.doctor.__main__``'s ``diagnose`` subcommand
(Story 3.4, FR-9) -- covers every row of the story spec's I/O & Edge-Case
Matrix: ``--target`` required, plain gather-and-report (no ``--prescribe``),
``--prescribe`` wiring the full partition/rank/root-cause pipeline,
``--json`` schema parity (``verb: "diagnose"``, ``prescriptions`` ALWAYS
present, empty when ``--prescribe`` is omitted), and the "target implies an
environment check" directory-detection rule.

``sources.atlas.gather``/``sources.warden.gather``/``checks.env_hygiene.gather``
are monkeypatched throughout -- this suite never spawns a real subprocess,
opens a real MCP session, or scans a real filesystem tree."""

from __future__ import annotations

import json
from importlib import resources

import jsonschema

from pyforge.doctor.__main__ import main
from pyforge.doctor.checks import env_hygiene
from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources import atlas, warden as warden_source


def _schema() -> dict:
    schema_text = (
        resources.files("pyforge.doctor")
        .joinpath("data", "report-schema.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(schema_text)


def _finding(source, check, status=DoctorStatus.WARN, evidence=None):
    return Finding(
        source=source, check=check, status=status, message="stub", evidence=evidence or {}
    )


def _stub_atlas(monkeypatch, by_axis: dict[str, tuple[Finding, ...]]):
    def fake_gather(axis, *, target=None, **kwargs):
        return by_axis.get(axis, ())

    monkeypatch.setattr(atlas, "gather", fake_gather)


def _stub_no_directory_checks(monkeypatch):
    """Neither warden nor env_hygiene should run for a --target that is not
    a real directory -- these stubs would raise if called, proving that."""

    def _forbidden(target):
        raise AssertionError("must not gather engine/env checks for a non-directory target")

    monkeypatch.setattr(warden_source, "gather", _forbidden)
    monkeypatch.setattr(env_hygiene, "gather", _forbidden)


# --- --target is required --------------------------------------------------


def test_diagnose_without_target_is_a_usage_error(capsys, monkeypatch):
    _stub_atlas(monkeypatch, {})
    exit_code = main(["diagnose"])
    assert exit_code == 2
    assert "--target" in capsys.readouterr().err


# --- plain gather-and-report (no --prescribe) -------------------------------


def test_diagnose_without_prescribe_reports_findings_unpartitioned(monkeypatch, capsys):
    _stub_atlas(
        monkeypatch,
        {"staleness": (_finding(Source.STALENESS_REPORT, "pkg-a"),)},
    )
    _stub_no_directory_checks(monkeypatch)
    main(["diagnose", "--target", "not-a-real-directory-xyz"])
    out = capsys.readouterr().out
    assert "pkg-a" in out
    assert "prescription" not in out.lower()  # no --prescribe -- no section


def test_diagnose_json_without_prescribe_has_empty_prescriptions_array(monkeypatch, capsys):
    _stub_atlas(
        monkeypatch,
        {"staleness": (_finding(Source.STALENESS_REPORT, "pkg-a"),)},
    )
    _stub_no_directory_checks(monkeypatch)
    main(["diagnose", "--target", "not-a-real-directory-xyz", "--json"])
    document = json.loads(capsys.readouterr().out)
    jsonschema.validate(document, _schema())
    assert document["verb"] == "diagnose"
    assert document["prescriptions"] == []  # present, empty -- never omitted


# --- --prescribe wiring -----------------------------------------------------


def test_diagnose_prescribe_populates_prescriptions_for_every_finding(monkeypatch, capsys):
    _stub_atlas(
        monkeypatch,
        {
            "staleness": (_finding(Source.STALENESS_REPORT, "pkg-a"),),
            "cve": (
                _finding(
                    Source.CVE_WATCHER,
                    "pkg-b",
                    status=DoctorStatus.FAIL,
                    evidence={"fix_available": False},
                ),
            ),
        },
    )
    _stub_no_directory_checks(monkeypatch)
    main(["diagnose", "--target", "xyz", "--prescribe", "--json"])
    document = json.loads(capsys.readouterr().out)
    assert len(document["prescriptions"]) == 2
    partitions = {p["partition"] for p in document["prescriptions"]}
    assert "blocked" in partitions  # pkg-b's fix_available=False
    assert "actionable" in partitions  # pkg-a


def test_diagnose_prescribe_json_schema_valid_with_rank_and_root_cause(monkeypatch, capsys):
    _stub_atlas(
        monkeypatch,
        {"cve": (_finding(Source.CVE_WATCHER, "pkg-a", status=DoctorStatus.FAIL),)},
    )
    _stub_no_directory_checks(monkeypatch)
    main(["diagnose", "--target", "xyz", "--prescribe", "--json"])
    document = json.loads(capsys.readouterr().out)
    jsonschema.validate(document, _schema())
    prescription = document["prescriptions"][0]
    assert prescription["rank"] == 1
    assert prescription["rank_factors"] is not None
    assert prescription["root_cause"]
    assert prescription["action"]
    assert prescription["finding_ref"] == "cve-watcher:pkg-a"


def test_diagnose_prescribe_blocked_and_accepted_risk_only_still_lists_them(
    monkeypatch, capsys
):
    # Story 3.4 AC3: a target with only blocked/accepted-risk Findings
    # (nothing actionable today) must still list them, never an
    # empty/misleadingly-clean result.
    blocked = _finding(
        Source.CVE_WATCHER,
        "blocked-pkg",
        status=DoctorStatus.FAIL,
        evidence={"fix_available": False},
    )
    accepted = _finding(
        Source.CVE_WATCHER,
        "accepted-pkg",
        status=DoctorStatus.FAIL,
        evidence={"waived": True},
    )
    _stub_atlas(monkeypatch, {"cve": (blocked, accepted)})
    _stub_no_directory_checks(monkeypatch)
    main(["diagnose", "--target", "xyz", "--prescribe", "--json"])
    document = json.loads(capsys.readouterr().out)
    assert len(document["prescriptions"]) == 2
    partitions = sorted(p["partition"] for p in document["prescriptions"])
    assert partitions == ["accepted-risk", "blocked"]
    # Neither is ranked -- rank must be null, not a fabricated integer.
    assert all(p["rank"] is None for p in document["prescriptions"])


def test_diagnose_prescribe_clean_finding_action_is_not_a_remediation_instruction(
    monkeypatch, capsys
):
    """Review finding: a clean (`DoctorStatus.OK`) Finding is classified
    `ACTIONABLE` ("nothing to do" is trivially actionable), but the
    prescription's `action` text used to render `"address X (source)"`
    regardless -- telling the operator to remediate something that already
    passed. It must reflect the underlying `reason` instead, and must not
    receive a rank (ranking a clean Finding is meaningless)."""
    _stub_atlas(
        monkeypatch,
        {"staleness": (_finding(Source.STALENESS_REPORT, "clean-pkg", status=DoctorStatus.OK),)},
    )
    _stub_no_directory_checks(monkeypatch)
    main(["diagnose", "--target", "xyz", "--prescribe", "--json"])
    document = json.loads(capsys.readouterr().out)
    prescription = document["prescriptions"][0]
    assert prescription["partition"] == "actionable"
    assert "address" not in prescription["action"]
    assert prescription["rank"] is None


def test_diagnose_prescribe_human_output_shows_prescription_section(monkeypatch, capsys):
    _stub_atlas(
        monkeypatch,
        {"cve": (_finding(Source.CVE_WATCHER, "pkg-a", status=DoctorStatus.FAIL),)},
    )
    _stub_no_directory_checks(monkeypatch)
    main(["diagnose", "--target", "xyz", "--prescribe"])
    out = capsys.readouterr().out
    assert "prescription(s)" in out
    assert "root cause" in out


# --- "target implies an environment check" ----------------------------------


def test_diagnose_target_that_is_a_real_directory_also_runs_engine_env_checks(
    monkeypatch, tmp_path, capsys
):
    _stub_atlas(monkeypatch, {})
    engine_finding = (_finding(Source.WARDEN_DOCTOR, "deptry", status=DoctorStatus.OK),)
    env_finding = (_finding(Source.ENV_HYGIENE, "credential-scan", status=DoctorStatus.OK),)
    monkeypatch.setattr(warden_source, "gather", lambda target: engine_finding)
    monkeypatch.setattr(env_hygiene, "gather", lambda target: env_finding)

    main(["diagnose", "--target", str(tmp_path), "--json"])
    document = json.loads(capsys.readouterr().out)
    sources = {f["source"] for f in document["findings"]}
    assert Source.WARDEN_DOCTOR.value in sources
    assert Source.ENV_HYGIENE.value in sources


def test_diagnose_target_that_is_not_a_directory_skips_engine_env_checks(
    monkeypatch, capsys
):
    _stub_atlas(monkeypatch, {})
    _stub_no_directory_checks(monkeypatch)  # would raise if called
    main(["diagnose", "--target", "rxm7706", "--json"])
    document = json.loads(capsys.readouterr().out)
    assert document["findings"] == []


def test_diagnose_blank_target_does_not_scope_engine_env_checks_to_cwd(monkeypatch, capsys):
    """Review finding: `Path("").is_dir()` resolves to the CWD and returns
    True -- an empty (but present) `--target ""` used to silently scope the
    local engine/env checks to wherever `doctor` happens to be invoked
    from, rather than refusing like any other non-directory target."""
    _stub_atlas(monkeypatch, {})
    _stub_no_directory_checks(monkeypatch)  # would raise if called
    main(["diagnose", "--target", "", "--json"])
    document = json.loads(capsys.readouterr().out)
    assert document["findings"] == []


# --- exit code / verdict -----------------------------------------------------


def test_diagnose_exit_code_reflects_fail_findings(monkeypatch):
    _stub_atlas(
        monkeypatch,
        {"cve": (_finding(Source.CVE_WATCHER, "pkg-a", status=DoctorStatus.FAIL),)},
    )
    _stub_no_directory_checks(monkeypatch)
    assert main(["diagnose", "--target", "xyz"]) == 2


def test_diagnose_default_axes_are_staleness_and_cve(monkeypatch):
    seen = []

    def fake_gather(axis, *, target=None, **kwargs):
        seen.append(axis)
        return ()

    monkeypatch.setattr(atlas, "gather", fake_gather)
    _stub_no_directory_checks(monkeypatch)
    main(["diagnose", "--target", "xyz"])
    assert seen == ["staleness", "cve"]
