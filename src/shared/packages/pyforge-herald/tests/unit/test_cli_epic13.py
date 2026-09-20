"""Story 13.5's ``herald scheduler run`` CLI verb: composes evidence
revalidation and the progress snapshot export behind one command, wired
the same way ``success validate`` is (no operator-role gate, same
``--repo-root``/``--json`` conventions). Every test scopes storage to
``tmp_path`` via ``--repo-root`` -- none ever touches a real ``.herald/``
directory. Mirrors ``tests/test_cli_success.py``'s own fixture pattern.
"""

from __future__ import annotations

import json

import pytest

from pyforge.herald import auth, claims, cli, evidence, progress


@pytest.fixture(autouse=True)
def _stub_evidence_validation(monkeypatch):
    """Every evidence link in this file is a placeholder URL, not a real
    endpoint -- ``deny_network`` would fail any test that let a real
    ``validate_link`` call reach ``httpx2``. Individual tests override this
    stub when they need to exercise a broken-link path."""

    class _AlwaysValid:
        is_valid = True

    monkeypatch.setattr(evidence, "validate_link", lambda url, **_k: _AlwaysValid())


# --- happy path / empty DB --------------------------------------------------


def test_scheduler_run_on_an_empty_db_reports_zero_counts_and_exits_0(capsys, tmp_path):
    rc = cli.main(["scheduler", "run", "--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "0 record(s) aggregated" in out
    assert "0 claim(s) revalidated" in out


def test_scheduler_run_happy_path_revalidates_and_aggregates_in_one_invocation(capsys, tmp_path):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claims.create(
        claims_path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="t")],
    )
    progress_path = tmp_path / progress.DEFAULT_PROGRESS_PATH
    progress.upsert(
        progress_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=["hygiene gate"],
        compute_hours=1.5,
        token_spend=1000,
        wall_clock_hours=2.0,
        unblock_narrative="",
    )

    rc = cli.main(["scheduler", "run", "--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "1 record(s) aggregated" in out
    assert "1 claim(s) revalidated" in out

    snapshot = tmp_path / "web" / "public" / "progress.json"
    assert snapshot.exists()
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["station"] == "warden"


# --- broken evidence link: exit 0, claim named ------------------------------


def test_scheduler_run_names_a_broken_evidence_claim_and_still_exits_0(capsys, tmp_path, monkeypatch):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claim = claims.create(
        claims_path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://broken", label="t")],
    )

    class _Broken:
        is_valid = False

    monkeypatch.setattr(evidence, "validate_link", lambda url, **_k: _Broken())

    rc = cli.main(["scheduler", "run", "--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert claim.id in out
    assert "broken evidence" in out
    updated = claims.read_one(claims_path, claim.id)
    assert updated.evidence[0].validated is False


# --- --json output -----------------------------------------------------------


def test_scheduler_run_json_emits_one_object_with_counts_and_broken_ids(capsys, tmp_path):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claims.create(
        claims_path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="t")],
    )

    rc = cli.main(["scheduler", "run", "--repo-root", str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["claims_checked"] == 1
    assert payload["broken_evidence_claim_ids"] == []
    assert payload["records_aggregated"] == 0
    assert "snapshot_path" in payload


def test_scheduler_run_json_names_a_broken_claim(capsys, tmp_path, monkeypatch):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    claim = claims.create(
        claims_path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://broken", label="t")],
    )

    class _Broken:
        is_valid = False

    monkeypatch.setattr(evidence, "validate_link", lambda url, **_k: _Broken())

    rc = cli.main(["scheduler", "run", "--repo-root", str(tmp_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["broken_evidence_claim_ids"] == [claim.id]


# --- ungated: no operator-role check ----------------------------------------


def test_scheduler_run_never_checks_auth(capsys, tmp_path, monkeypatch):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)
    rc = cli.main(["scheduler", "run", "--repo-root", str(tmp_path)])
    assert rc == 0
    assert "unauthorized" not in capsys.readouterr().err


# --- --out-dir override ------------------------------------------------------


def test_scheduler_run_out_dir_override(tmp_path):
    out_dir = tmp_path / "custom-out"
    rc = cli.main(
        [
            "scheduler",
            "run",
            "--repo-root",
            str(tmp_path),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    assert (out_dir / "progress.json").exists()
    assert not (tmp_path / "web").exists()


# --- OSError surfaces as a structured HeraldError, not a raw traceback ------


def test_scheduler_run_wraps_an_unwritable_out_dir_as_a_herald_error(capsys, tmp_path):
    """``--out-dir`` colliding with an existing file makes ``mkdir`` raise
    ``FileExistsError`` (an ``OSError``) -- this must surface through
    ``dispatch``'s structured error contract (AD-6), not an uncaught
    traceback, since this command now also runs unattended off cron."""
    blocking_file = tmp_path / "blocked"
    blocking_file.write_text("not a directory", encoding="utf-8")

    rc = cli.main(
        [
            "scheduler",
            "run",
            "--repo-root",
            str(tmp_path),
            "--out-dir",
            str(blocking_file / "public"),
        ]
    )
    assert rc != 0
    err = capsys.readouterr().err
    assert "HeraldError" in err
    assert "scheduler run failed" in err


# --- help --------------------------------------------------------------------


@pytest.mark.parametrize("argv", [["scheduler", "--help"], ["scheduler", "run", "--help"]])
def test_scheduler_help_exits_0(argv):
    assert cli.main(argv) == 0


def test_scheduler_with_no_subcommand_is_a_usage_error_exit_2(capsys):
    rc = cli.main(["scheduler"])
    assert rc == 2
