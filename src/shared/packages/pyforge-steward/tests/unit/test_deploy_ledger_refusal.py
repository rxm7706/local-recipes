"""`deploy dashboard`'s tracked-ledger precondition guard — Story 5.2 (AD-71).

Covers the I/O matrix's refusal rows: `steward deploy dashboard` (bare,
`--build`, or `--dry-run`) must refuse with a named `DutyResult(ok=False,
...)` -- never a silent fallback -- when Steward's own tracked
`sprint-status-ledger.yaml` is missing or unshaped, and must never invoke
`build_dashboard()` in that case. `deploy status` is unaffected by the same
missing ledger -- the guard only applies to the `dashboard` verb.
"""

from __future__ import annotations

import os
import sys

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.deploy import _STEWARD_LEDGER_RELATIVE_PATH as _LEDGER_RELATIVE_PATH


def _write_ledger(repo_root, text: str) -> None:
    ledger = repo_root / _LEDGER_RELATIVE_PATH
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(text)


def test_missing_ledger_refuses_before_build(tmp_path, monkeypatch, capsys):
    marker = tmp_path / "built.txt"
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (sys.executable, "-c", f"open({str(marker)!r}, 'w').write('built')"),
    )

    rc = main(["deploy", "dashboard"])

    assert rc == EXIT_FAILED
    assert not marker.exists(), "build_dashboard() must never run on a missing ledger"
    err = capsys.readouterr().err
    assert "refused" in err
    assert str(tmp_path / _LEDGER_RELATIVE_PATH) in err


def test_empty_malformed_ledger_refuses_before_build(tmp_path, monkeypatch, capsys):
    marker = tmp_path / "built.txt"
    _write_ledger(tmp_path, "not_a_ledger: true\n")
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (sys.executable, "-c", f"open({str(marker)!r}, 'w').write('built')"),
    )

    rc = main(["deploy", "dashboard"])

    assert rc == EXIT_FAILED
    assert not marker.exists()
    err = capsys.readouterr().err
    assert "refused" in err


def test_ledger_merely_mentioning_the_key_in_a_comment_still_refuses(tmp_path, monkeypatch, capsys):
    """Review finding (Blind Hunter, reproduced against the real parser): a
    naive substring check (`"development_status:" in text`) is satisfied by
    a COMMENT merely mentioning the key, or any longer identifier ending in
    it -- while `pyforge.doctor.sources.fleet_scan::parse_sprint_status` (the real
    consumer) only recognizes a line whose stripped text is exactly
    `development_status:`. That mismatch would let a malformed ledger pass
    this guard and then silently parse to zero statuses downstream -- the
    exact silent-invisibility this guard exists to prevent. Pins the
    line-exact fix."""
    marker = tmp_path / "built.txt"
    _write_ledger(
        tmp_path,
        "not_a_ledger: true\n# see development_status: elsewhere\nsub_development_status:\n  x: y\n",
    )
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (sys.executable, "-c", f"open({str(marker)!r}, 'w').write('built')"),
    )

    rc = main(["deploy", "dashboard"])

    assert rc == EXIT_FAILED
    assert not marker.exists()
    err = capsys.readouterr().err
    assert "refused" in err


def test_valid_ledger_proceeds_to_build(tmp_path, monkeypatch):
    marker = tmp_path / "built.txt"
    _write_ledger(tmp_path, "development_status:\n  1-1-example: done\n")
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (sys.executable, "-c", f"open({str(marker)!r}, 'w').write('built')"),
    )

    rc = main(["deploy", "dashboard", "--build"])

    assert rc == EXIT_OK
    assert marker.exists(), "build_dashboard() must run once the ledger is valid"


def test_missing_ledger_refuses_with_build_flag(tmp_path, monkeypatch):
    marker = tmp_path / "built.txt"
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (sys.executable, "-c", f"open({str(marker)!r}, 'w').write('built')"),
    )

    rc = main(["deploy", "dashboard", "--build"])

    assert rc == EXIT_FAILED
    assert not marker.exists()


def test_missing_ledger_refuses_with_dry_run_flag(tmp_path, monkeypatch):
    marker = tmp_path / "built.txt"
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (sys.executable, "-c", f"open({str(marker)!r}, 'w').write('built')"),
    )

    rc = main(["deploy", "dashboard", "--dry-run"])

    assert rc == EXIT_FAILED
    assert not marker.exists()


def test_unreadable_ledger_refuses_before_build(tmp_path, monkeypatch, capsys):
    """Review finding (Blind Hunter / Edge Case Hunter): a permission-denied
    ledger raises `OSError` from `read_text` -- must refuse, not crash
    uncaught."""
    marker = tmp_path / "built.txt"
    _write_ledger(tmp_path, "development_status:\n")
    ledger = tmp_path / _LEDGER_RELATIVE_PATH
    ledger.chmod(0o000)
    if os.access(ledger, os.R_OK):
        pytest.skip("cannot simulate an unreadable file while running as root")
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (sys.executable, "-c", f"open({str(marker)!r}, 'w').write('built')"),
    )

    try:
        rc = main(["deploy", "dashboard"])
    finally:
        ledger.chmod(0o644)  # restore so tmp_path teardown can remove it

    assert rc == EXIT_FAILED
    assert not marker.exists()
    err = capsys.readouterr().err
    assert "refused" in err


def test_ledger_with_a_realistic_comment_header_proceeds_to_build(tmp_path, monkeypatch):
    """Review finding (Blind Hunter): the happy-path fixtures elsewhere only
    ever write a bare `development_status:\\n`. The REAL tracked ledger
    (`scripts/promote_sprint_status.py`'s output) carries a multi-line `#`
    comment header before that block -- this proves the guard's line-exact
    match tolerates it rather than only working on the minimal fixture."""
    marker = tmp_path / "built.txt"
    _write_ledger(
        tmp_path,
        "# GENERATED — do not hand-edit. Regenerate with:\n"
        "#     pixi run -e local-recipes sprint-ledger-sync\n"
        "#\n"
        "# project: steward\n"
        "# stories: 49\n"
        "development_status:\n"
        "  1-1-steward-exists-as-an-installable-cli: done\n"
        "  epic-1: done\n",
    )
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (sys.executable, "-c", f"open({str(marker)!r}, 'w').write('built')"),
    )

    rc = main(["deploy", "dashboard", "--build"])

    assert rc == EXIT_OK
    assert marker.exists()


def test_deploy_status_unaffected_by_a_missing_ledger(tmp_path, monkeypatch):
    """The ledger check applies to the `dashboard` verb only -- `status`
    reports the last commit from git history exactly as it does today,
    regardless of the ledger's presence (spec I/O matrix, last row)."""
    import subprocess

    def _git(*args: str):
        return subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True)

    _git("init", "-b", "main")
    _git("config", "user.email", "test@example.com")
    _git("config", "user.name", "Test")
    (tmp_path / "README.md").write_text("scratch\n")
    _git("add", "-A")
    _git("commit", "-m", "init")

    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: tmp_path)

    rc = main(["deploy", "status"])

    assert rc == EXIT_OK
