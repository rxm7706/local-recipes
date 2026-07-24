"""Unit tests — the ``--doctor`` CLI surface (Story 5.1, D8).

The exit-code matrix (healthy=0; engine missing/out-of-range=2 via a
monkeypatched ``subprocess.run`` — mirrors ``test_engine_env_deptry.py``'s
own ``_fake_run_version`` convention; NEVER 1), ``--format json``'s ad-hoc
(non-``ComplianceReport``) shape, the "operating air-gapped" wording when
the KEV/EPSS feed cache is absent, and that ``--doctor`` short-circuits
BEFORE any discovery/extraction/policy work (a malformed manifest under the
target is never even opened). SIGINT/argparse-usage-error paths are
untouched by ``--doctor``'s addition — pinned here too.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import time
import types
from pathlib import Path

import pytest

from pyforge.warden import feeds
from pyforge.warden.cli import main
from pyforge.warden.vuln import DB_MAX_AGE_DAYS, OSV_DB_CACHE_ENV_VAR, db_zip_path

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
_OSV_RECORDS_DIR = _FIXTURES / "osv-db" / "pypi"


def _load_osv_db_builder():
    """Import ``fixtures/osv_db_builder`` by path -- mirrors
    ``tests/conformance/test_osv_engine.py``'s own ``_load_builder`` (the
    fixtures dir is data, not an importable package)."""
    module_path = _FIXTURES / "osv_db_builder.py"
    spec = importlib.util.spec_from_file_location("osv_db_builder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_version_run(
    *, missing: str | None = None, out_of_range: str | None = None
):
    """A ``subprocess.run`` stand-in answering ONLY the ``--version``
    pre-flight calls ``engines.run_doctor_checks`` makes — distinguished by
    ``argv[0]`` (mirrors ``test_engine_env_deptry.py``'s own
    ``_fake_run_version`` convention). ``missing`` names an engine whose
    call raises ``FileNotFoundError`` (binary absent from PATH);
    ``out_of_range`` names an engine whose ``--version`` reports a version
    outside the tested range."""

    def fake_run(argv, **kwargs):
        owner = argv[0]
        if missing == owner:
            raise FileNotFoundError(owner)
        if owner == "deptry":
            version = "9.9.9" if out_of_range == "deptry" else "0.25.3"
            stdout = f"deptry {version}\n".encode()
        else:
            version = "9.9.9" if out_of_range == "osv-scanner" else "2.4.1"
            stdout = f"osv-scanner version: {version}\n".encode()
        return types.SimpleNamespace(returncode=0, stdout=stdout, stderr=b"")

    return fake_run


@pytest.fixture(autouse=True)
def _healthy_engines_by_default(monkeypatch):
    """Every test in this module gets a healthy deptry+osv-scanner
    ``--version`` response unless it re-patches ``subprocess.run`` itself
    afterwards (monkeypatch's own last-setattr-wins semantics)."""
    monkeypatch.setattr(subprocess, "run", _fake_version_run())


def test_doctor_healthy_environment_exits_0_and_reports_every_check_ok(
    capsys, tmp_path
):
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 0
    lines = captured.out.splitlines()
    assert lines[0] == "warden: doctor status=ok checks=5"
    assert len(lines) == 6  # header + 5 checks
    for line in lines[1:]:
        assert " ok -- " in line
    assert captured.err == ""


def test_doctor_healthy_environment_format_json_is_a_small_ad_hoc_document(
    capsys, tmp_path
):
    rc = main(["scan", str(tmp_path), "--doctor", "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 0
    document = json.loads(captured.out)
    assert document["tool"] == "warden"
    assert document["doctor"] is True
    assert document["status"] == "ok"
    assert len(document["checks"]) == 5
    assert all(check["ok"] is True for check in document["checks"])
    for check in document["checks"]:
        assert set(check) == {"name", "ok", "message"}
    # Never ComplianceReport-shaped/schema-validated (Boundaries): pure
    # stdout, exactly one document, none of the frozen report's own keys.
    assert "schema_version" not in document
    assert "exit_code" not in document
    assert "findings" not in document
    names = [check["name"] for check in document["checks"]]
    assert names == sorted(names)  # --format json sorts by name


def test_doctor_missing_engine_exits_2_never_1_and_names_the_engine(
    monkeypatch, capsys, tmp_path
):
    monkeypatch.setattr(subprocess, "run", _fake_version_run(missing="osv-scanner"))
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    assert rc != 1
    assert "warden: doctor status=problem checks=5" in captured.out
    matches = [
        line for line in captured.out.splitlines() if "osv-scanner" in line
    ]
    assert any(
        "problem -- " in line and "not found on PATH" in line for line in matches
    )


def test_doctor_out_of_range_engine_exits_2_never_1(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(subprocess, "run", _fake_version_run(out_of_range="deptry"))
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    assert rc != 1
    assert "outside tested range" in captured.out


def test_doctor_unreadable_osv_db_exits_2_naming_the_problem(
    monkeypatch, capsys, tmp_path
):
    """No ``OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`` at all — the ambient
    fixture's own ``setenv`` is overridden here (composes with, and wins
    over, the autouse fixture per ``tests/conftest.py``'s own documented
    precedent)."""
    monkeypatch.delenv("OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY", raising=False)
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    assert rc != 1
    problem_lines = [
        line for line in captured.out.splitlines() if "osv-db" in line
    ]
    assert any("problem -- " in line for line in problem_lines)


def test_doctor_stale_osv_db_exits_2_naming_the_problem(
    monkeypatch, capsys, tmp_path
):
    """Review finding (2026-07-24): the pre-existing suite only ever
    exercised the DB-ABSENT branch of ``_doctor_check_osv_db`` -- the
    equally real "present but stale" branch (``is_db_stale`` -- FR12) was
    completely uncovered. Builds a FUNCTION-scoped DB cache (never mutates
    the session-scoped ambient fixture other tests rely on staying fresh --
    mirrors ``test_osv_engine.py``'s own ``test_stale_db_forces_...``
    pattern exactly) and backdates its zip past ``DB_MAX_AGE_DAYS``."""
    builder = _load_osv_db_builder()
    cache_root = builder.build_offline_db(_OSV_RECORDS_DIR, tmp_path / "db-cache")
    zip_path = db_zip_path(cache_root)
    assert zip_path is not None
    stale_mtime = time.time() - (DB_MAX_AGE_DAYS + 1) * 86400
    os.utime(zip_path, (stale_mtime, stale_mtime))
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(cache_root))

    rc = main(["scan", str(tmp_path), "--doctor"])

    captured = capsys.readouterr()
    assert rc == 2
    assert rc != 1
    problem_lines = [
        line for line in captured.out.splitlines() if "osv-db" in line
    ]
    assert any(
        "problem -- " in line and "stale" in line for line in problem_lines
    )


def test_doctor_kev_and_epss_feed_absent_is_still_exit_0(
    monkeypatch, capsys, tmp_path
):
    """Absent KEV/EPSS feeds are never a doctor failure — NFR-U2's air-gap
    framing — so the overall exit stays 0 as long as the engine/DB checks
    are healthy."""
    monkeypatch.delenv(feeds.FEED_CACHE_DIR_ENV_VAR, raising=False)
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "operating air-gapped: kev feed not present" in captured.out
    assert "operating air-gapped: epss feed not present" in captured.out


def test_doctor_never_reads_the_scan_targets_pyproject_toml(capsys, tmp_path):
    """``--doctor`` short-circuits BEFORE discovery/extraction/policy — a
    malformed ``pyproject.toml`` (which a REAL scan would surface as a
    ``config-parse``/``unparsable-manifest`` error) is never even opened."""
    (tmp_path / "pyproject.toml").write_text(
        "[project\nname = 'broken", encoding="utf-8"
    )
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "config-parse" not in captured.out
    assert "unparsable" not in captured.out


def test_doctor_empty_path_is_early_fatal_exit_2(capsys):
    rc = main(["scan", " ", "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert "not an existing directory" in captured.err


def test_doctor_nonexistent_target_is_exit_2(capsys, tmp_path):
    missing = tmp_path / "does-not-exist"
    rc = main(["scan", str(missing), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""


def test_doctor_never_exits_1_across_every_scenario(monkeypatch, capsys, tmp_path):
    """The never-exit-1 assertion, swept across every failure mode this
    module exercises."""
    scenarios = [
        _fake_version_run(),
        _fake_version_run(missing="deptry"),
        _fake_version_run(missing="osv-scanner"),
        _fake_version_run(out_of_range="deptry"),
        _fake_version_run(out_of_range="osv-scanner"),
    ]
    for fake_run in scenarios:
        monkeypatch.setattr(subprocess, "run", fake_run)
        rc = main(["scan", str(tmp_path), "--doctor"])
        capsys.readouterr()
        assert rc != 1
        assert rc in (0, 2)


def test_doctor_bypass_without_reason_is_still_a_usage_error(capsys, tmp_path):
    """``--doctor`` coexists with argparse's own pre-existing usage-error
    path (SIGINT/parse-error paths unaffected) — ``--bypass`` without
    ``--reason`` is still the one usage error ``cli.py`` itself adds,
    never even reaching ``_run_doctor``."""
    rc = main(["scan", str(tmp_path), "--doctor", "--bypass"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert "--bypass requires --reason" in captured.err
