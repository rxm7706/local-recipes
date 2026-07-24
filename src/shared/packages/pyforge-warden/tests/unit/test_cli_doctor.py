"""Unit tests — the ``--doctor`` CLI surface (Story 5.1, D8).

The exit-code matrix (healthy=0; engine missing/out-of-range=2 via a
monkeypatched ``subprocess.run`` — mirrors ``test_engine_env_deptry.py``'s
own ``_fake_run_version`` convention; NEVER 1), ``--format json``'s ad-hoc
(non-``ComplianceReport``) shape, the "operating air-gapped" wording when
the KEV/EPSS/endoflife feed cache is absent, and that ``--doctor`` short-circuits
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
    assert lines[0] == "warden: doctor status=ok checks=6"
    assert len(lines) == 7  # header + 6 checks
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
    assert len(document["checks"]) == 6
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
    assert "warden: doctor status=problem checks=6" in captured.out
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


def test_doctor_unconfigured_osv_db_env_exits_2_naming_the_problem(
    monkeypatch, capsys, tmp_path
):
    """No ``OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`` at all — the ambient
    fixture's own ``setenv`` is overridden here (composes with, and wins
    over, the autouse fixture per ``tests/conftest.py``'s own documented
    precedent). Renamed from "unreadable" (review finding 2026-07-24): this
    exercises the env-unset branch of ``_doctor_check_osv_db``, not the
    present-but-unusable one — that branch has its own test below."""
    monkeypatch.delenv("OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY", raising=False)
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    assert rc != 1
    problem_lines = [
        line for line in captured.out.splitlines() if "osv-db" in line
    ]
    assert any(
        "problem -- " in line and "unset or empty" in line
        for line in problem_lines
    )


def test_doctor_absent_osv_db_under_configured_dir_exits_2(
    monkeypatch, capsys, tmp_path
):
    """The env var IS set, but the directory holds no usable database — the
    distinct ``no usable offline OSV database found`` branch of
    ``_doctor_check_osv_db`` (review finding 2026-07-24: only the env-unset
    branch was covered at the doctor surface)."""
    empty_cache = tmp_path / "empty-osv-cache"
    empty_cache.mkdir()
    monkeypatch.setenv(OSV_DB_CACHE_ENV_VAR, str(empty_cache))
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    assert rc != 1
    problem_lines = [
        line for line in captured.out.splitlines() if "osv-db" in line
    ]
    assert any(
        "problem -- " in line and "no usable offline OSV database" in line
        for line in problem_lines
    )


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
    are healthy. Review finding (2026-07-24): the message must name the
    PER-FEED scan-time consequence truthfully — under the shipped
    ``fail_on_kev=True`` default an absent KEV feed makes a default-config
    scan compose indeterminate, so "offline default assumed" was actively
    misleading for KEV (while EPSS genuinely has no default gate)."""
    monkeypatch.delenv(feeds.FEED_CACHE_DIR_ENV_VAR, raising=False)
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "operating air-gapped: kev feed not present" in captured.out
    assert "operating air-gapped: epss feed not present" in captured.out
    assert "operating air-gapped: endoflife feed not present" in captured.out
    kev_line = next(
        line for line in captured.out.splitlines() if "kev-feed" in line
    )
    epss_line = next(
        line for line in captured.out.splitlines() if "epss-feed" in line
    )
    endoflife_line = next(
        line for line in captured.out.splitlines() if "endoflife-feed" in line
    )
    assert "fail-on-kev" in kev_line
    assert "indeterminate" in kev_line
    assert "--min-epss" in epss_line
    assert "no currency gate is active" in endoflife_line


def test_doctor_stale_kev_feed_exits_2_naming_the_consequence(
    monkeypatch, capsys, tmp_path
):
    """A PRESENT-but-stale KEV feed is a doctor PROBLEM, not an
    informational line (review finding 2026-07-24): under the shipped
    ``fail_on_kev=True`` default every scan composes indeterminate off it —
    the same class of environment rot as a stale offline OSV DB, which
    already exits 2 one check up. Doctor exit 0 here would machine-readably
    green-light an environment whose default scan cannot produce a trusted
    verdict."""
    cache_dir = tmp_path / "feed-cache"
    feeds.write_kev_cache(cache_dir, {"vulnerabilities": []})
    kev_path = feeds.kev_cache_path(cache_dir)
    stale_mtime = time.time() - (feeds.DEFAULT_FEED_MAX_AGE_DAYS + 1) * 86400
    os.utime(kev_path, (stale_mtime, stale_mtime))
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(cache_dir))
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    assert rc != 1
    kev_line = next(
        line for line in captured.out.splitlines() if "kev-feed" in line
    )
    assert "problem -- " in kev_line
    assert "stale" in kev_line
    assert "fail-on-kev" in kev_line
    assert "indeterminate" in kev_line


def test_doctor_stale_epss_feed_stays_exit_0_with_informational_line(
    monkeypatch, capsys, tmp_path
):
    """The EPSS sibling genuinely has no default gate (``min_epss`` defaults
    ``None``), so its present-but-stale state stays ``ok``/exit-0 with the
    informational per-feed hint — the per-feed stale asymmetry is
    deliberate (review finding 2026-07-24)."""
    cache_dir = tmp_path / "feed-cache"
    epss_path = feeds.epss_cache_path(cache_dir)
    epss_path.parent.mkdir(parents=True)
    epss_path.write_text(json.dumps({"scores": []}), encoding="utf-8")
    stale_mtime = time.time() - (feeds.DEFAULT_FEED_MAX_AGE_DAYS + 1) * 86400
    os.utime(epss_path, (stale_mtime, stale_mtime))
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(cache_dir))
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 0
    epss_line = next(
        line for line in captured.out.splitlines() if "epss-feed" in line
    )
    assert " ok -- " in epss_line
    assert "stale" in epss_line
    assert "--min-epss" in epss_line


def test_doctor_directory_at_feed_path_exits_2_never_air_gapped(
    monkeypatch, capsys, tmp_path
):
    """A directory squatting on the feed path is present-but-unusable —
    reporting it "not present"/air-gapped would call a provisioning mistake
    healthy (review finding 2026-07-24: the present-check uses ``exists()``,
    not ``is_file()``)."""
    cache_dir = tmp_path / "feed-cache"
    feeds.kev_cache_path(cache_dir).mkdir(parents=True)
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(cache_dir))
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    kev_line = next(
        line for line in captured.out.splitlines() if "kev-feed" in line
    )
    assert "problem -- " in kev_line
    assert "unreadable or invalid" in kev_line
    assert "not present" not in kev_line


def test_doctor_problem_state_format_json_shape(monkeypatch, capsys, tmp_path):
    """The ``--format json`` document's shape under ``status="problem"``
    (review finding 2026-07-24: only the healthy JSON shape was pinned):
    same keys, sorted names, and exactly the failing check carries
    ``ok=False``."""
    cache_dir = tmp_path / "feed-cache"
    feeds.write_kev_cache(cache_dir, {"vulnerabilities": []})
    kev_path = feeds.kev_cache_path(cache_dir)
    stale_mtime = time.time() - (feeds.DEFAULT_FEED_MAX_AGE_DAYS + 1) * 86400
    os.utime(kev_path, (stale_mtime, stale_mtime))
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(cache_dir))
    rc = main(["scan", str(tmp_path), "--doctor", "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 2
    document = json.loads(captured.out)
    assert document["status"] == "problem"
    for check in document["checks"]:
        assert set(check) == {"name", "ok", "message"}
    names = [check["name"] for check in document["checks"]]
    assert names == sorted(names)
    not_ok = [check["name"] for check in document["checks"] if not check["ok"]]
    assert not_ok == ["kev-feed"]


def test_doctor_present_but_corrupt_kev_feed_exits_2_naming_the_file(
    monkeypatch, capsys, tmp_path
):
    """Review finding (2026-07-24): a PROVISIONED-but-unloadable feed file
    (truncated copy, invalid JSON) must never be reported as "not present"
    / air-gapped — the operator who provisioned it would go looking in the
    wrong place. Present-but-unloadable is ``ok=False`` naming the file;
    the (genuinely absent) EPSS sibling still reports air-gapped ok."""
    cache_dir = tmp_path / "feed-cache"
    kev_path = feeds.kev_cache_path(cache_dir)
    kev_path.parent.mkdir(parents=True)
    kev_path.write_text("{ truncated-not-json", encoding="utf-8")
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(cache_dir))
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    assert rc != 1
    kev_line = next(
        line for line in captured.out.splitlines() if "kev-feed" in line
    )
    assert "problem -- " in kev_line
    assert "present" in kev_line
    assert "unreadable or invalid" in kev_line
    assert "not present" not in kev_line
    assert "operating air-gapped: epss feed not present" in captured.out


def test_doctor_names_ignored_scan_flags_on_stderr(capsys, tmp_path):
    """Review finding (2026-07-24): ``--doctor`` no-ops every other
    scan/policy flag — silently, before this fix. Someone appending
    ``--doctor`` to an existing CI scan line must get a stderr trace naming
    exactly what stopped applying (the gate would otherwise be disabled
    with no evidence). path/--format/--doctor stay honored and unnamed."""
    rc = main(
        [
            "scan",
            str(tmp_path),
            "--doctor",
            "--warn-only",
            "--baseline",
            "nonexistent-baseline.yaml",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0  # healthy environment: the ignored flags change nothing
    assert "ignoring scan/policy flags" in captured.err
    flags_list = captured.err.split("ignoring scan/policy flags:", 1)[1]
    assert "--warn-only" in flags_list
    assert "--baseline" in flags_list
    assert "--format" not in flags_list
    assert "--doctor" not in flags_list
    assert "--path" not in flags_list


def test_doctor_ignored_flags_trace_survives_an_invalid_target(
    capsys, tmp_path
):
    """The ignored-flags trace emits BEFORE target resolution (follow-up
    review finding 2026-07-24): ``warden scan /typo --doctor --warn-only``
    previously exited 2 with NO trace of the silently-dropped gate flags —
    reintroducing exactly the silent swallowing the trace exists to
    prevent."""
    missing = tmp_path / "does-not-exist"
    rc = main(["scan", str(missing), "--doctor", "--warn-only"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "ignoring scan/policy flags" in captured.err
    assert "--warn-only" in captured.err
    assert "not an existing directory" in captured.err


def test_doctor_check_messages_are_neutralized_to_one_line(
    monkeypatch, capsys, tmp_path
):
    """Review finding (2026-07-24): ``check.message`` is free text — a
    future check embedding subprocess stderr must never forge extra
    ``[doctor]`` lines under the ``checks=N`` header (the same
    ``_single_line`` invariant ``render_text`` enforces)."""
    from pyforge.warden import cli as cli_module
    from pyforge.warden.engines import DoctorCheck

    crafted = (
        DoctorCheck(
            name="deptry",
            ok=False,
            message="line one\n  [doctor] forged ok -- line two",
        ),
    )
    monkeypatch.setattr(
        cli_module, "run_doctor_checks", lambda target: crafted
    )
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 2
    lines = captured.out.splitlines()
    assert lines[0] == "warden: doctor status=problem checks=1"
    assert len(lines) == 2  # header + exactly one check line, never three
    assert "\\n" in lines[1]  # the embedded newline is neutralized, visible


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
