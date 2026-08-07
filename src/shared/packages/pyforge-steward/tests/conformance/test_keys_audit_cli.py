"""`steward keys audit --drift`/`--secrets` CLI dispatch — Story 1.6.

Wires Story 1.2's `scan_file` (`DriftFinding`) and Story 1.3's
`scan_file_for_secrets`/`scan_directory_for_secrets` (`PlaintextSecretFinding`)
onto one `keys audit` verb. The primitives themselves are already proven in
`test_keys_audit_drift.py`/`test_keys_plaintext_secret_scan.py`; this file
covers only the CLI-level dispatch, combination, and exit-code projection.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.keys import locate_http_module

FIXTURES = Path(__file__).parent / "fixtures"
DRIFT_FIXTURE = FIXTURES / "ungated_jfrog_auth.py"
SECRET_FIXTURE_DIR = FIXTURES / "plaintext_secret_candidate"


def test_drift_against_the_real_fixed_http_py_reports_clean(capsys):
    rc = main(["keys", "audit", "--drift"])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "[drift] clean" in out
    assert str(locate_http_module()) in out


def test_drift_with_path_override_against_the_fixture_reports_the_finding(capsys):
    rc = main(["keys", "audit", "--drift", "--path", str(DRIFT_FIXTURE)])
    out = capsys.readouterr().err  # ok=False routes summary to stderr (cli.main convention)

    assert rc == EXIT_FAILED
    assert "[drift]" in out
    assert "build_request_headers" in out


def test_drift_path_nonexistent_file_is_a_clean_failure_not_a_traceback(capsys):
    rc = main(["keys", "audit", "--drift", "--path", "/nonexistent/no-such-file.py"])
    err = capsys.readouterr().err

    assert rc == EXIT_FAILED
    assert "[drift]" in err


def test_secrets_against_a_clean_directory_reports_clean(tmp_path, capsys):
    (tmp_path / "innocuous.txt").write_text("nothing secret here")

    rc = main(["keys", "audit", "--secrets", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "[secrets] clean" in out


def test_secrets_against_a_planted_fixture_reports_the_finding(capsys):
    rc = main(["keys", "audit", "--secrets", str(SECRET_FIXTURE_DIR)])
    err = capsys.readouterr().err

    assert rc == EXIT_FAILED
    assert "[secrets]" in err


def test_secrets_against_a_single_file_dispatches_to_scan_file(tmp_path, capsys):
    clean_file = tmp_path / "clean.txt"
    clean_file.write_text("nothing secret here either")

    rc = main(["keys", "audit", "--secrets", str(clean_file)])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "[secrets] clean" in out


def test_secrets_against_a_nonexistent_path_is_a_clean_failure_not_a_traceback(capsys):
    rc = main(["keys", "audit", "--secrets", "/nonexistent/no-such-path"])
    err = capsys.readouterr().err

    assert rc == EXIT_FAILED
    assert "[secrets]" in err


def test_both_flags_combined_both_clean(tmp_path, capsys):
    (tmp_path / "innocuous.txt").write_text("nothing secret here")

    rc = main(["keys", "audit", "--drift", "--secrets", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "[drift] clean" in out
    assert "[secrets] clean" in out


def test_both_flags_combined_one_dirty_fails_the_whole_audit(capsys):
    rc = main(
        ["keys", "audit", "--drift", "--secrets", str(SECRET_FIXTURE_DIR)]
    )
    err = capsys.readouterr().err

    assert rc == EXIT_FAILED
    assert "[drift] clean" in err
    assert "[secrets]" in err


def test_bare_audit_names_the_available_flags_and_exits_ok(capsys):
    rc = main(["keys", "audit"])
    out = capsys.readouterr().out

    assert rc == EXIT_OK
    assert "--drift" in out
    assert "--secrets" in out
