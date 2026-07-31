"""Unit tests for ``pyforge.doctor.__main__``'s ``check`` subcommand (Story
1.5, FR-9/NFR-4) -- covers every row of the story spec's I/O & Edge-Case
Matrix: default combined run, ``--engines``/``--env`` filtering (including
the unknown-name usage error and the degraded-vs-clean asymmetry between
the two categories), ``--list``, ``--json`` (schema-valid via
``jsonschema``, no ``prescriptions`` key), ``--version``/``--help`` parity
with ``pyforge-warden``'s ``scan`` subcommand, and ``path`` positional
forwarding. Mirrors ``test_checks_registry.py``'s
monkeypatch-``run_doctor_checks`` idiom for simulating a healthy/degraded
"engines" category without depending on a real warden self-check.
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import jsonschema

from pyforge.doctor.__main__ import __version__, main
from pyforge.doctor.checks.env_hygiene import CHECK_NAME as ENV_CHECK_NAME
from pyforge.warden import engines as engines_mod
from pyforge.warden.engines import DoctorCheck

_HEALTHY_ENGINE_CHECKS = (
    ("deptry", True, "within tested range"),
    ("osv-scanner", True, "within tested range"),
    ("osv-db", True, "snapshot fresh"),
    ("kev-feed", True, "operating air-gapped"),
    ("epss-feed", True, "operating air-gapped"),
    ("endoflife-feed", True, "operating air-gapped"),
)


def _schema() -> dict:
    schema_text = (
        resources.files("pyforge.doctor")
        .joinpath("data", "report-schema.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(schema_text)


def _stub_healthy_warden(monkeypatch) -> None:
    checks = tuple(
        DoctorCheck(name=n, ok=ok, message=m) for n, ok, m in _HEALTHY_ENGINE_CHECKS
    )
    monkeypatch.setattr(engines_mod, "run_doctor_checks", lambda target: checks)


def _stub_degraded_warden(monkeypatch) -> None:
    def _boom(target):
        raise RuntimeError("simulated warden self-check crash")

    monkeypatch.setattr(engines_mod, "run_doctor_checks", _boom)


def _forbid_warden_gather(monkeypatch) -> None:
    def _boom(target):
        raise AssertionError("must never gather/run the 'engines' category here")

    monkeypatch.setattr(engines_mod, "run_doctor_checks", _boom)


# --- default combined run (epics AC1) ----------------------------------------


def test_default_combined_run_reports_both_categories_and_projects_exit(
    monkeypatch, tmp_path: Path, capsys
):
    _stub_healthy_warden(monkeypatch)

    exit_code = main(["check", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "deptry" in captured.out
    assert "warden-doctor" in captured.out
    assert "finding(s)" in captured.out


# --- --json parity (epics AC2) -----------------------------------------------


def test_json_emits_one_schema_valid_document_with_no_prescriptions(
    monkeypatch, tmp_path: Path, capsys
):
    _stub_healthy_warden(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.validate(document, _schema())
    assert exit_code == 0
    assert document["verb"] == "check"
    assert document["schema_version"] == 1
    assert "prescriptions" not in document
    check_names = {finding["check"] for finding in document["findings"]}
    assert "deptry" in check_names


# --- --engines <name> single check (Story 1.3 AC3, reused) -------------------


def test_engines_named_check_matches_full_suite_filtered_to_that_finding(
    monkeypatch, tmp_path: Path, capsys
):
    _stub_healthy_warden(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--engines", "osv-scanner", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 0
    assert len(document["findings"]) == 1
    assert document["findings"][0]["check"] == "osv-scanner"
    assert document["findings"][0]["source"] == "warden-doctor"


def test_unknown_engines_check_name_is_usage_error_never_reaches_gather(
    monkeypatch, tmp_path: Path, capsys
):
    _forbid_warden_gather(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--engines", "bogus-name"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "bogus-name" in captured.err
    assert captured.out == ""


def test_degraded_engines_category_named_check_renders_one_synthetic_fail(
    monkeypatch, tmp_path: Path, capsys
):
    _stub_degraded_warden(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--engines", "osv-scanner", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 2
    assert len(document["findings"]) == 1
    finding = document["findings"][0]
    assert finding["check"] == "osv-scanner"
    assert finding["status"] == "fail"
    assert finding["source"] == "warden-doctor"
    # Never a bare "not found" -- names the degradation and hints a re-run.
    assert "degrad" in finding["message"].lower()
    assert "not found" not in finding["message"].lower()


# --- --env <name>: clean vs. a real match (the category asymmetry) ----------


def test_clean_env_named_check_reports_zero_findings_and_exits_zero(
    tmp_path: Path, capsys
):
    (tmp_path / "benign.py").write_text("x = 1\n", encoding="utf-8")

    exit_code = main(["check", str(tmp_path), "--env", ENV_CHECK_NAME, "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 0
    assert document["findings"] == []


def test_env_named_check_with_a_real_match_forwards_the_path(
    tmp_path: Path, capsys
):
    (tmp_path / "leaky.py").write_text(
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["X"] = os.environ.get("SECRET")\n',
        encoding="utf-8",
    )

    exit_code = main(["check", str(tmp_path), "--env", ENV_CHECK_NAME, "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    # env-hygiene findings are WARN-only in v1 -- never gate the exit code.
    assert exit_code == 0
    assert len(document["findings"]) == 1
    finding = document["findings"][0]
    assert finding["check"] == ENV_CHECK_NAME
    assert finding["status"] == "warn"
    assert str(tmp_path) in finding["message"]


def test_unknown_env_check_name_is_usage_error(tmp_path: Path, capsys):
    exit_code = main(["check", str(tmp_path), "--env", "bogus-env-check"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "bogus-env-check" in captured.err


def test_unknown_check_name_that_is_also_a_real_path_hints_at_ordering(
    monkeypatch, tmp_path: Path, capsys
):
    # Review finding: --engines/--env's nargs="?" is structurally ambiguous
    # with an adjacent bare positional `path` -- `--engines <real-path>`
    # parses the path as the check NAME. The error must name this specific,
    # discoverable cause rather than a bare "unknown check name".
    _forbid_warden_gather(monkeypatch)

    exit_code = main(["check", "--engines", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "looks like a path" in captured.err
    assert "doctor check" in captured.err


# --- --list --------------------------------------------------------------


def test_list_prints_full_catalog_and_exits_zero_without_gathering(
    monkeypatch, capsys
):
    _forbid_warden_gather(monkeypatch)

    exit_code = main(["check", "--list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "osv-scanner" in captured.out
    assert "deptry" in captured.out
    assert ENV_CHECK_NAME in captured.out


def test_list_ignores_engines_and_env_and_json_flags(monkeypatch, capsys):
    _forbid_warden_gather(monkeypatch)

    exit_code = main(
        ["check", "--list", "--engines", "--env", "--json"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    # Plain text catalog, never a JSON document, regardless of --json.
    assert "osv-scanner" in captured.out
    assert not captured.out.lstrip().startswith("{")


def test_list_ignores_an_unknown_engines_check_name_and_a_path(
    monkeypatch, tmp_path: Path, capsys
):
    # Review finding: --list must win even when --engines/--env carries a
    # name that would otherwise be a usage error, and even alongside an
    # explicit path -- its own help text promises "ignores
    # --engines/--env/--json/path" unconditionally.
    _forbid_warden_gather(monkeypatch)

    exit_code = main(
        ["check", str(tmp_path), "--list", "--engines", "bogus-name"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "osv-scanner" in captured.out


# --- --version/--help parity with warden's `scan` subcommand -----------------


def test_top_level_version_returns_zero_and_prints_version(capsys):
    exit_code = main(["--version"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert __version__ in captured.out


def test_check_version_is_a_usage_error_matching_warden_scan_version(capsys):
    # Verified live against pyforge.warden.cli.main(["scan", "--version"]):
    # an argparse usage error, exit 2 -- --version stays top-level only.
    exit_code = main(["check", "--version"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err
    assert captured.out == ""


def test_check_help_exits_zero_and_prints_usage(capsys):
    exit_code = main(["check", "--help"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "usage" in captured.out.lower()


# --- bare `doctor` with no subcommand (epics AC list, cross-checked here) ---


def test_bare_doctor_with_no_subcommand_is_a_usage_error(capsys):
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err


# --- path positional forwarding ----------------------------------------------


def test_path_positional_defaults_to_current_directory(
    monkeypatch, tmp_path: Path, capsys
):
    _stub_healthy_warden(monkeypatch)
    monkeypatch.chdir(tmp_path)

    exit_code = main(["check", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 0
    assert document["findings"]


# --- _write_stdout's sys.stdout is None guard ---------------------------


def test_write_stdout_does_not_crash_when_sys_stdout_is_none(monkeypatch):
    # Review finding: sys.stdout can legitimately be None (e.g. a detached/
    # frozen process) -- _write_stdout must guard this the same way the
    # sibling _stderr already guards sys.stderr.
    from pyforge.doctor import __main__ as main_module

    monkeypatch.setattr(main_module.sys, "stdout", None)
    main_module._write_stdout("doctor: some output\n")
