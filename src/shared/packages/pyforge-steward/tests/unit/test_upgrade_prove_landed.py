"""Story 14.5 — CAP-5: one command proves the upgrade landed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.upgrade import (
    TRAP_LOOP_RELAY,
    WORKED_EXAMPLE_LOOP_HOME_COUNT,
    GateResult,
    build_prove_landed_report,
    format_prove_landed,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_homes(root: Path, n: int = WORKED_EXAMPLE_LOOP_HOME_COUNT) -> list[Path]:
    homes: list[Path] = []
    for i in range(n):
        home = root / f"station-{i}"
        (home / ".bmad-loop").mkdir(parents=True)
        (home / ".bmad-loop" / "policy.toml").write_text(
            "[limits]\n", encoding="utf-8"
        )
        homes.append(home)
    return homes


def test_worked_example_8_of_8_clean_passes(tmp_path: Path):
    """Scaled fixture of the 2026-08-21 8/8-homes-clean shape."""
    repo = tmp_path / "repo"
    repo.mkdir()
    loops = tmp_path / "loops"
    homes = _make_homes(loops)
    assert len(homes) == WORKED_EXAMPLE_LOOP_HOME_COUNT

    init_calls: list[str] = []

    def drift() -> GateResult:
        return GateResult(name="bmad-drift-integrity", ok=True, detail="clean")

    def cfe() -> GateResult:
        return GateResult(name="cfe-meta-tests", ok=True, detail="green")

    def loop_home(home: Path, refresh: bool) -> GateResult:
        if refresh:
            init_calls.append(home.name)
        return GateResult(
            name=f"loop-home:{home.name}",
            ok=True,
            detail="validate clean (warnings=0, problems=0)",
            warnings=0,
            mutated=refresh,
        )

    report = build_prove_landed_report(
        repo=repo,
        loops_home=loops,
        refresh_relays=True,
        drift_runner=drift,
        cfe_runner=cfe,
        loop_home_runner=loop_home,
    )
    assert report.verdict == "pass"
    assert report.homes_ok == WORKED_EXAMPLE_LOOP_HOME_COUNT
    assert report.homes_total == WORKED_EXAMPLE_LOOP_HOME_COUNT
    assert report.trap_id == TRAP_LOOP_RELAY
    assert sorted(init_calls) == sorted(h.name for h in homes)
    assert all(g.ok for g in report.gates)


def test_single_failing_gate_fails_verdict(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    loops = tmp_path / "loops"
    _make_homes(loops, n=2)

    report = build_prove_landed_report(
        repo=repo,
        loops_home=loops,
        refresh_relays=False,
        drift_runner=lambda: GateResult(
            name="bmad-drift-integrity", ok=True, detail="clean"
        ),
        cfe_runner=lambda: GateResult(
            name="cfe-meta-tests", ok=False, detail="meta red", exit_code=1
        ),
        loop_home_runner=lambda home, refresh: GateResult(
            name=f"loop-home:{home.name}",
            ok=True,
            detail="clean",
            mutated=False,
        ),
    )
    assert report.verdict == "fail"
    assert any(g.name == "cfe-meta-tests" and not g.ok for g in report.gates)


def test_loop_home_warning_fails_that_home(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    loops = tmp_path / "loops"
    _make_homes(loops, n=2)

    def loop_home(home: Path, refresh: bool) -> GateResult:
        bad = home.name.endswith("0")
        return GateResult(
            name=f"loop-home:{home.name}",
            ok=not bad,
            detail="warnings=1" if bad else "clean",
            warnings=1 if bad else 0,
            mutated=False,
        )

    report = build_prove_landed_report(
        repo=repo,
        loops_home=loops,
        refresh_relays=False,
        drift_runner=lambda: GateResult(
            name="bmad-drift-integrity", ok=True, detail="clean"
        ),
        cfe_runner=lambda: GateResult(name="cfe-meta-tests", ok=True, detail="green"),
        loop_home_runner=loop_home,
    )
    assert report.verdict == "fail"
    assert report.homes_ok == 1
    assert report.homes_total == 2


def test_no_init_skips_relay_mutation_marker(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    loops = tmp_path / "loops"
    _make_homes(loops, n=1)
    foreign_marker = loops / "station-0" / ".bmad-loop" / "policy.toml"
    before = _sha(foreign_marker)

    report = build_prove_landed_report(
        repo=repo,
        loops_home=loops,
        refresh_relays=False,
        drift_runner=lambda: GateResult(
            name="bmad-drift-integrity", ok=True, detail="clean"
        ),
        cfe_runner=lambda: GateResult(name="cfe-meta-tests", ok=True, detail="green"),
        loop_home_runner=lambda home, refresh: GateResult(
            name=f"loop-home:{home.name}",
            ok=True,
            detail="clean",
            mutated=refresh,
        ),
    )
    assert report.verdict == "pass"
    assert all(not g.mutated for g in report.gates)
    assert before == _sha(foreign_marker)
    assert any("--no-init" in n for n in report.notes)


def test_format_and_cli_json(tmp_path: Path, capsys, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "scripts").mkdir()
    (repo / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")
    loops = tmp_path / "loops"
    _make_homes(loops, n=WORKED_EXAMPLE_LOOP_HOME_COUNT)

    # Patch builders used by the CLI path via upgrade module.
    import pyforge.steward.upgrade as upgrade_mod

    def fake_build(**kwargs):
        return build_prove_landed_report(
            repo=kwargs["repo"],
            loops_home=kwargs.get("loops_home"),
            refresh_relays=kwargs.get("refresh_relays", True),
            drift_runner=lambda: GateResult(
                name="bmad-drift-integrity", ok=True, detail="clean"
            ),
            cfe_runner=lambda: GateResult(
                name="cfe-meta-tests", ok=True, detail="green"
            ),
            loop_home_runner=lambda home, refresh: GateResult(
                name=f"loop-home:{home.name}",
                ok=True,
                detail="clean",
                mutated=refresh,
            ),
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
            "--json",
        ]
    )
    assert code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "pass"
    assert payload["homes_ok"] == WORKED_EXAMPLE_LOOP_HOME_COUNT
    assert payload["trap_id"] == TRAP_LOOP_RELAY

    text = format_prove_landed(
        fake_build(repo=repo, loops_home=loops, refresh_relays=True),
        as_json=False,
    )
    assert "CAP-5" in text
    assert "PASS" in text


def test_cli_fail_exit(tmp_path: Path, capsys, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "scripts").mkdir()
    (repo / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")
    loops = tmp_path / "loops"
    loops.mkdir()

    import pyforge.steward.upgrade as upgrade_mod

    monkeypatch.setattr(
        upgrade_mod,
        "build_prove_landed_report",
        lambda **kwargs: build_prove_landed_report(
            repo=kwargs["repo"],
            loops_home=kwargs.get("loops_home"),
            refresh_relays=False,
            drift_runner=lambda: GateResult(
                name="bmad-drift-integrity", ok=False, detail="HARD"
            ),
            cfe_runner=lambda: GateResult(
                name="cfe-meta-tests", ok=True, detail="green"
            ),
        ),
    )
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
    assert code == EXIT_FAILED
    # Duty failures print the summary on stderr (AD-8 projection).
    payload = json.loads(capsys.readouterr().err)
    assert payload["verdict"] == "fail"


def test_drift_gate_falls_back_to_pixi_task_when_doctor_missing(tmp_path: Path, monkeypatch):
    """Trap 15 (2026-09-06): the steward env has no pyforge.doctor — the gate
    must take the verdict from `pixi run -e pyforge-guild bmad-drift-check`,
    not fail on the import."""
    import subprocess

    from pyforge.steward import upgrade as upgrade_mod

    def _no_doctor():
        raise ImportError("No module named 'pyforge.doctor'")

    monkeypatch.setattr(upgrade_mod, "_import_drift_factory", _no_doctor)
    seen: list[tuple[tuple[str, ...], Path]] = []

    def runner(argv, cwd):
        seen.append((tuple(argv), Path(cwd)))
        return subprocess.CompletedProcess(list(argv), 0, stdout="[bmad-drift] ok\n", stderr="")

    result = upgrade_mod.run_bmad_drift_integrity(tmp_path, fallback_runner=runner)
    assert result.ok is True
    assert "pixi run -e pyforge-guild bmad-drift-check" in result.detail
    assert seen and seen[0][0] == upgrade_mod._BMAD_DRIFT_TASK_ARGV
    assert seen[0][1] == tmp_path

    def findings(argv, cwd):
        return subprocess.CompletedProcess(list(argv), 1, stdout="[bmad-drift] x: fail -- boom\n", stderr="")

    failed = upgrade_mod.run_bmad_drift_integrity(tmp_path, fallback_runner=findings)
    assert failed.ok is False
    assert "findings" in failed.detail and "boom" in failed.detail

    def could_not_run(argv, cwd):
        return subprocess.CompletedProcess(list(argv), 2, stdout="", stderr="no pixi env")

    cnr = upgrade_mod.run_bmad_drift_integrity(tmp_path, fallback_runner=could_not_run)
    assert cnr.ok is False and "could-not-run" in cnr.detail
