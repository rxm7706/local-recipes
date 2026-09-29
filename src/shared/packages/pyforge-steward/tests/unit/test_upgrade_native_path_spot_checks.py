"""Story 15.4 — CAP-4 dual-path: advisory native spot-checks orbit CAP-5."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pyforge.steward.upgrade import (
    _BMAD_LOOP_UV_GIT_SPEC,
    _INSTALL_MATRIX_REL,
    _MANTICORE_CUSTOM_SOURCE_URL,
    NATIVE_PATH_SPOT_CHECK_CATALOG,
    GateResult,
    build_prove_landed_report,
    format_prove_landed,
    run_native_path_spot_checks,
)

_EXECUTABLE_CLASS_IDS = (
    "npm-cli",
    "own-npx",
    "installer-selection",
    "custom-source",
    "plugin-marketplace",
    "uv-from-git",
)
_DOC_ONLY_CLASS_ID = "build-from-source"


def _seed_matrix(repo: Path) -> Path:
    matrix = repo / _INSTALL_MATRIX_REL
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text(
        "# Dual-path install matrix — test fixture citation source\n"
        "Class → gate spot-check candidates:\n"
        "npm CLI → npx bmad-method --version\n"
        "own-npx → npx bmad-module-skill-forge --help\n"
        "installer-selection → TEA via bmad-tea-install\n"
        "custom-source → manticore dry-run\n"
        "plugin-marketplace → labs npx skills add --help\n"
        "uv-from-git → uv tool install --help (native: uv tool install "
        "bmad-loop[tui] @ git+https://github.com/bmad-code-org/bmad-loop.git@v0.11.1)\n"
        "build-from-source → dashboards excluded from the gate (build cost), "
        "listed check-by-doc.\n",
        encoding="utf-8",
    )
    return matrix


def _ok_runner(argv: list[str] | tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(list(argv), 0, stdout="ok\n", stderr="")


def _fail_one_runner(bad_token: str):
    def runner(argv: list[str] | tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
        joined = " ".join(argv)
        code = 1 if bad_token in joined else 0
        return subprocess.CompletedProcess(list(argv), code, stdout="", stderr="boom" if code else "")

    return runner


def _green_gates(loops: Path):
    (loops / "station-0").mkdir(parents=True)

    def drift() -> GateResult:
        return GateResult(name="bmad-drift-integrity", ok=True, detail="clean")

    def cfe() -> GateResult:
        return GateResult(name="cfe-meta-tests", ok=True, detail="green")

    def loop_home(home: Path, refresh: bool) -> GateResult:
        return GateResult(
            name=f"loop-home:{home.name}",
            ok=True,
            detail="clean",
            mutated=False,
        )

    return drift, cfe, loop_home


def test_catalog_covers_seven_matrix_classes_with_cited_argv():
    ids = [e.class_id for e in NATIVE_PATH_SPOT_CHECK_CATALOG]
    assert ids == [*_EXECUTABLE_CLASS_IDS, _DOC_ONLY_CLASS_ID]
    by_id = {e.class_id: e for e in NATIVE_PATH_SPOT_CHECK_CATALOG}

    assert by_id["npm-cli"].argv == ("npx", "bmad-method", "--version")
    assert by_id["own-npx"].argv == ("npx", "bmad-module-skill-forge", "--help")
    assert by_id["installer-selection"].argv == ("bmad-tea-install", "--help")
    assert by_id["custom-source"].argv == (
        "npx",
        "bmad-method",
        "install",
        "--custom-source",
        _MANTICORE_CUSTOM_SOURCE_URL,
        "--help",
    )
    assert _MANTICORE_CUSTOM_SOURCE_URL == ("https://github.com/bmad-code-org/bmad-manticore")
    assert by_id["plugin-marketplace"].argv == ("npx", "skills", "add", "--help")
    assert by_id["uv-from-git"].argv == ("uv", "tool", "install", "--help")
    assert _BMAD_LOOP_UV_GIT_SPEC in by_id["uv-from-git"].citation
    assert "@v0.11.1" in _BMAD_LOOP_UV_GIT_SPEC
    assert "bmad-loop" in _BMAD_LOOP_UV_GIT_SPEC
    assert "git+https://github.com/bmad-code-org/bmad-loop.git" in _BMAD_LOOP_UV_GIT_SPEC
    assert by_id["build-from-source"].mode == "check-by-doc"
    assert by_id["build-from-source"].argv is None


def test_happy_path_six_executable_plus_dashboard_doc_only(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_matrix(repo)

    results = run_native_path_spot_checks(repo, command_runner=_ok_runner)
    assert len(results) == 7
    assert {r.class_id for r in results} == {
        *_EXECUTABLE_CLASS_IDS,
        _DOC_ONLY_CLASS_ID,
    }
    assert all(r.ok for r in results)
    assert all(r.advisory for r in results)
    doc = next(r for r in results if r.class_id == _DOC_ONLY_CLASS_ID)
    assert doc.mode == "check-by-doc"
    assert doc.status == "check-by-doc"
    assert doc.argv is None


def test_dashboard_class_never_spawns_subprocess(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_matrix(repo)
    calls: list[tuple[str, ...]] = []

    def runner(argv, cwd):
        calls.append(tuple(argv))
        return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")

    results = run_native_path_spot_checks(repo, command_runner=runner)
    doc = next(r for r in results if r.class_id == _DOC_ONLY_CLASS_ID)
    assert doc.mode == "check-by-doc"
    assert doc.ok
    assert all("pnpm" not in " ".join(c) for c in calls)
    assert all("dashboard" not in " ".join(c).lower() for c in calls)
    assert len(calls) == 6  # only executable classes


def test_advisory_fail_does_not_flip_cap5_verdict(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_matrix(repo)
    loops = tmp_path / "loops"
    drift, cfe, loop_home = _green_gates(loops)

    report = build_prove_landed_report(
        repo=repo,
        loops_home=loops,
        refresh_relays=False,
        drift_runner=drift,
        cfe_runner=cfe,
        loop_home_runner=loop_home,
        command_runner=_fail_one_runner("bmad-module-skill-forge"),
    )
    assert report.verdict == "pass"
    assert all(g.ok for g in report.gates)
    assert any(s.class_id == "own-npx" and not s.ok and s.advisory for s in report.native_spot_checks)
    assert any("advisory" in n for n in report.notes)
    text = format_prove_landed(report, as_json=False)
    assert "Native path spot-checks (advisory)" in text
    assert "PASS" in text


def test_missing_matrix_is_named_advisory_only(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    results = run_native_path_spot_checks(repo, command_runner=_ok_runner)
    assert len(results) == 1
    assert results[0].status == "missing-matrix"
    assert results[0].ok is False
    assert results[0].advisory is True

    loops = tmp_path / "loops"
    drift, cfe, loop_home = _green_gates(loops)
    report = build_prove_landed_report(
        repo=repo,
        loops_home=loops,
        refresh_relays=False,
        drift_runner=drift,
        cfe_runner=cfe,
        loop_home_runner=loop_home,
        command_runner=_ok_runner,
    )
    assert report.verdict == "pass"
    assert report.native_spot_checks[0].status == "missing-matrix"


def test_catalog_argv_cited_in_tracked_install_matrix():
    """Matrix remains SoT — catalog argv tokens must appear in the tracked file."""
    import re

    from pyforge.steward.upgrade import repo_root

    matrix = repo_root() / _INSTALL_MATRIX_REL
    assert matrix.is_file(), f"missing tracked matrix: {matrix}"
    text = matrix.read_text(encoding="utf-8")
    # Matrix wraps long lines; collapse whitespace for citation matching.
    compact = re.sub(r"\s+", " ", text)
    assert "npx bmad-method --version" in compact
    assert "npx bmad-module-skill-forge --help" in compact
    assert "bmad-tea-install" in compact
    assert "manticore" in compact.lower() or "custom-source" in compact
    assert "npx skills add --help" in compact
    assert "uv tool install --help" in compact
    # The constant mirrors the matrix's bmad-loop row verbatim (DW-FU-15-4-3).
    assert _BMAD_LOOP_UV_GIT_SPEC in compact
    assert "check-by-doc" in compact
    assert "dashboard" in compact.lower()
    # Executable catalog argv pieces must not invent packages absent from matrix.
    for entry in NATIVE_PATH_SPOT_CHECK_CATALOG:
        if entry.argv is None:
            continue
        joined = " ".join(entry.argv)
        if entry.class_id == "npm-cli":
            assert "bmad-method" in compact and "--version" in joined
        elif entry.class_id == "own-npx":
            assert "bmad-module-skill-forge" in compact
        elif entry.class_id == "installer-selection":
            assert "bmad-tea-install" in compact
        elif entry.class_id == "custom-source":
            assert _MANTICORE_CUSTOM_SOURCE_URL in compact or "bmad-manticore" in compact
        elif entry.class_id == "plugin-marketplace":
            assert "skills add" in compact
        elif entry.class_id == "uv-from-git":
            assert "bmad-loop" in compact and "git+" in compact


def test_advisory_fail_keeps_cli_exit_ok(tmp_path: Path, monkeypatch, capsys):
    """DutyResult.ok / CLI exit must follow Epic 14 gates, not native spot-checks."""
    import pyforge.steward.upgrade as upgrade_mod
    from pyforge.steward.cli import EXIT_OK, main

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "scripts").mkdir()
    (repo / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")
    _seed_matrix(repo)
    loops = tmp_path / "loops"
    drift, cfe, loop_home = _green_gates(loops)

    def fake_build(**kwargs):
        return build_prove_landed_report(
            repo=kwargs["repo"],
            loops_home=kwargs.get("loops_home"),
            refresh_relays=kwargs.get("refresh_relays", False),
            drift_runner=drift,
            cfe_runner=cfe,
            loop_home_runner=loop_home,
            command_runner=_fail_one_runner("bmad-module-skill-forge"),
        )

    monkeypatch.setattr(upgrade_mod, "build_prove_landed_report", fake_build)
    code = main(
        [
            "upgrade",
            "prove-landed",
            "--repo-root",
            str(repo),
            "--loops-home",
            str(loops),
            "--no-init",
            "--json",
        ]
    )
    assert code == EXIT_OK
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["verdict"] == "pass"
    assert "native_spot_checks" in payload
    assert any(s["class_id"] == "own-npx" and s["ok"] is False for s in payload["native_spot_checks"])


def test_to_dict_includes_native_spot_checks(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_matrix(repo)
    loops = tmp_path / "loops"
    drift, cfe, loop_home = _green_gates(loops)
    report = build_prove_landed_report(
        repo=repo,
        loops_home=loops,
        refresh_relays=False,
        drift_runner=drift,
        cfe_runner=cfe,
        loop_home_runner=loop_home,
        command_runner=_ok_runner,
    )
    payload = report.to_dict()
    assert "native_spot_checks" in payload
    assert len(payload["native_spot_checks"]) == 7
    assert payload["native_spot_checks"][0]["advisory"] is True
