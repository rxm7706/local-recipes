"""Story 20.2 / CAP-2: fleet-picture ATTENTION names baseline-drift recovery inputs.

Proves the loud-defer containment surface (needs lines + healthy silence) without
running full ``fleet-picture`` main (which shells out to marshal/gh/doctor).
Harness style matches CAP-1: importlib-load the script; never import bmad_loop.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FLEET_PATH = REPO_ROOT / "scripts" / "fleet_picture.py"
DETECTOR_PATH = REPO_ROOT / "scripts" / "bmad_loop_baseline_drift_check.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "baseline_drift"

STORY_KEY = "9-6-plan-and-action-types-repo-fingerprint-and-the-plan-builder"
RUN_ID = "20260813-094919-bfcb"
REAL_BASELINE = "523e938c7978"
DRIFTED_BASELINE = "26102ea12c6d"
PRESERVE_REF = f"attempt-preserve/{RUN_ID}-523e938c"


def _load_fleet():
    spec = importlib.util.spec_from_file_location(
        "fleet_picture_baseline_drift_under_test", FLEET_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_baseline_drift_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_detector():
    spec = importlib.util.spec_from_file_location(
        "bmad_loop_baseline_drift_check_fp_test", DETECTOR_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bmad_loop_baseline_drift_check_fp_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / "README").write_text("fixture\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-m", "init")


def _seed_preserve_branch(repo: Path, ref: str = PRESERVE_REF) -> None:
    _git(repo, "branch", ref)


def _seed_loop_home(
    loop_root: Path,
    *,
    journal_fixture: str,
    slug: str = "marshal",
    run_id: str = RUN_ID,
) -> None:
    home = loop_root / f"pyforge-{slug}"
    (home / ".git").mkdir(parents=True)
    run_dir = home / ".bmad-loop" / "runs" / run_id
    run_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / journal_fixture, run_dir / "journal.jsonl")


def _seed_repo_ledger(repo: Path, *, ledger_fixture: str | None) -> None:
    ledger_dir = (
        repo
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "planning-artifacts"
    )
    ledger_dir.mkdir(parents=True, exist_ok=True)
    dest = ledger_dir / "sprint-status-ledger.yaml"
    if ledger_fixture is None:
        dest.write_text("development_status: {}\n", encoding="utf-8")
    else:
        shutil.copy(FIXTURES / ledger_fixture, dest)


def _unrecovered_finding(**overrides) -> dict:
    base = {
        "slug": "marshal",
        "run": RUN_ID,
        "story": STORY_KEY,
        "real": REAL_BASELINE,
        "drifted": DRIFTED_BASELINE,
        "refs": [PRESERVE_REF],
    }
    base.update(overrides)
    return base


def test_needs_lines_name_story_run_baselines_and_preserve_ref():
    """Unrecovered findings → needs text carries recovery inputs + detector pointer."""
    mod = _load_fleet()
    lines = mod._baseline_drift_needs_lines([_unrecovered_finding()])

    assert len(lines) == 1
    line = lines[0]
    assert "1 unrecovered baseline-drift defer" in line
    assert "stuck-orchestrator" in line
    assert STORY_KEY in line
    assert RUN_ID in line
    assert REAL_BASELINE in line
    assert DRIFTED_BASELINE in line
    assert PRESERVE_REF in line
    assert "recover from:" in line
    assert "pixi run -e local-recipes baseline-drift-check" in line
    assert "docs/dreams/bmad-loop-baseline-drift.md" in line


def test_needs_lines_patch_hint_when_no_preserve_ref():
    mod = _load_fleet()
    lines = mod._baseline_drift_needs_lines(
        [_unrecovered_finding(refs=[])]
    )
    assert len(lines) == 1
    assert "changes.patch" in lines[0]
    assert STORY_KEY in lines[0]
    assert "recover from:" not in lines[0]


def test_needs_lines_non_list_refs_still_named():
    """Non-list refs (malformed JSON) still surface as recover-from, not false patch hint."""
    mod = _load_fleet()
    lines = mod._baseline_drift_needs_lines(
        [_unrecovered_finding(refs=PRESERVE_REF)]
    )
    assert PRESERVE_REF in lines[0]
    assert "recover from:" in lines[0]
    assert "changes.patch" not in lines[0]


def test_needs_lines_empty_when_clean():
    """Clean / empty findings → no baseline-drift need line (healthy silence)."""
    mod = _load_fleet()
    assert mod._baseline_drift_needs_lines([]) == []


def test_needs_lines_recovered_equivalent_is_silence(tmp_path, monkeypatch):
    """Recovered ledger → collect_findings empty → needs silence (end-to-end axis)."""
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_preserve_branch(repo)
    _seed_loop_home(loop_root, journal_fixture="journal_9_6_drift.jsonl")
    _seed_repo_ledger(repo, ledger_fixture="sprint_status_ledger_recovered.yaml")

    det = _load_detector()
    monkeypatch.setattr(det, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(det, "REPO", repo)
    findings = det.collect_findings()
    assert findings == []

    mod = _load_fleet()
    assert mod._baseline_drift_needs_lines(findings) == []


def test_needs_lines_sanitize_control_chars():
    mod = _load_fleet()
    lines = mod._baseline_drift_needs_lines(
        [
            _unrecovered_finding(
                story=f"evil\nsecond-line\x1bstory",
                run=f"run\rid",
            )
        ]
    )
    assert len(lines) == 1
    # Newlines must not create extra ATTENTION bullets; controls scrubbed.
    assert "\n" not in lines[0]
    assert "\r" not in lines[0]
    assert "\x1b" not in lines[0]
    assert "second-line" not in lines[0]


def test_needs_lines_sanitize_unicode_line_separators():
    mod = _load_fleet()
    lines = mod._baseline_drift_needs_lines(
        [_unrecovered_finding(story=f"evil\u2028second-line\u2029tail")]
    )
    assert len(lines) == 1
    assert "\u2028" not in lines[0]
    assert "\u2029" not in lines[0]
    assert "second-line" not in lines[0]


def test_baseline_drift_findings_uses_json_and_accepts_exit_1(monkeypatch):
    """Probe path: --json subprocess; exit 1 with findings is success, not degrade."""
    fleet = _load_fleet()
    payload = [_unrecovered_finding()]
    seen: dict = {}

    def _fake_run(cmd, **kwargs):
        seen["cmd"] = list(cmd)
        seen["kwargs"] = kwargs
        assert "--json" in cmd
        assert "bmad_loop_baseline_drift_check.py" in str(cmd[1])
        # CAP-2 load-bearing: check=True would raise on exit 1 and degrade ATTENTION.
        assert kwargs.get("check") is False
        assert kwargs.get("stdin") is fleet.subprocess.DEVNULL
        if kwargs.get("check") is True:
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(
            cmd, 1, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr(fleet.subprocess, "run", _fake_run)
    findings = fleet.baseline_drift_findings(repo=REPO_ROOT)
    assert findings == payload
    assert "--json" in seen["cmd"]
    assert seen["kwargs"].get("check") is False

    needs = fleet._baseline_drift_needs_lines(findings)
    assert STORY_KEY in needs[0]
    assert REAL_BASELINE in needs[0]
    assert DRIFTED_BASELINE in needs[0]
    assert PRESERVE_REF in needs[0]


def test_baseline_drift_findings_raises_outside_0_1(monkeypatch):
    """Exit outside {0, 1} must raise so main() degrades (not healthy silence)."""
    fleet = _load_fleet()

    def _fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 127, stdout="[]", stderr="boom")

    monkeypatch.setattr(fleet.subprocess, "run", _fake_run)
    try:
        fleet.baseline_drift_findings(repo=REPO_ROOT)
        raise AssertionError("expected CalledProcessError")
    except subprocess.CalledProcessError as exc:
        assert exc.returncode == 127


def _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path):
    """Isolate main() from live ledgers / marshal / doctor / gh probes."""
    empty_repo = tmp_path / "empty-repo"
    empty_repo.mkdir()
    monkeypatch.setattr(fleet, "REPO", empty_repo)
    monkeypatch.setattr(fleet, "running_stations", lambda: (set(), {}))
    monkeypatch.setattr(fleet, "loop_home_staleness", lambda: [])
    monkeypatch.setattr(fleet, "bmad_core_drift_findings", lambda: [])
    monkeypatch.setattr(fleet, "verification_staleness_findings", lambda: [])
    monkeypatch.setattr(fleet, "dream_chain_gap_findings", lambda: [])
    monkeypatch.setattr(fleet, "sibling_dreams_drift_findings", lambda: [])
    monkeypatch.setattr(
        fleet.subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )


def test_main_attention_names_recovery_inputs_when_unrecovered(monkeypatch, capsys, tmp_path):
    """main() ATTENTION wiring: unrecovered findings become >> needs, not healthy-only."""
    fleet = _load_fleet()
    finding = _unrecovered_finding()
    _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path)
    monkeypatch.setattr(fleet, "baseline_drift_findings", lambda: [finding])

    rc = fleet.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "ATTENTION:" in out
    assert ">>" in out
    assert STORY_KEY in out
    assert RUN_ID in out
    assert REAL_BASELINE in out
    assert DRIFTED_BASELINE in out
    assert PRESERVE_REF in out
    assert "none of the stations is waiting on you" not in out


def test_main_attention_degrades_when_probe_raises(monkeypatch, capsys, tmp_path):
    fleet = _load_fleet()
    _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path)
    monkeypatch.setattr(
        fleet, "baseline_drift_findings",
        lambda: (_ for _ in ()).throw(RuntimeError("probe boom")),
    )

    rc = fleet.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "could not run baseline-drift-check" in out
    assert STORY_KEY not in out


def test_main_attention_silent_on_baseline_drift_when_clean(monkeypatch, capsys, tmp_path):
    fleet = _load_fleet()
    _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path)
    monkeypatch.setattr(fleet, "baseline_drift_findings", lambda: [])

    rc = fleet.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "unrecovered baseline-drift" not in out
    assert "none of the stations is waiting on you" in out


def test_main_attention_watches_a_warn_mode_scope_advisory(monkeypatch, capsys, tmp_path):
    """Story 28.15 (CAP-17), AC4: fleet-picture renders a warn-mode
    scope-violation advisory (non-blocking -- the `watch` bucket, never
    `needs`), reading it straight off the SAME row `marshal status
    --format json` emits."""
    fleet = _load_fleet()
    _stub_fleet_main_ambient(fleet, monkeypatch, tmp_path)
    ledger_dir = (
        tmp_path
        / "empty-repo"
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "planning-artifacts"
    )
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "sprint-status-ledger.yaml").write_text(
        "development_status: {}\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        fleet,
        "running_stations",
        lambda: (
            set(),
            {
                "marshal": {
                    "state": "idle",
                    "story": "",
                    "escalation_reason": None,
                    "escalation_artifact": None,
                    "scope_advisories": [
                        {
                            "code": "MRS-GATE-012",
                            "message": "...",
                            "path": "src/leak.py",
                        }
                    ],
                }
            },
        ),
    )
    monkeypatch.setattr(fleet, "baseline_drift_findings", lambda: [])

    rc = fleet.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "ATTENTION:" in out
    assert "   - marshal: 1 scope-violation advisory(ies) (warn mode, not blocking) -- MRS-GATE-012" in out
    # The advisory is `watch`, not `needs` -- CAP-17's own "never blocks
    # landing" property -- so `needs` stays empty and this line still
    # renders too (a watch-only item is not the same as nothing to watch).
    assert "none of the stations is waiting on you" in out


def test_no_bmad_loop_import_in_fleet_picture_or_detector():
    """CAP-2: loud defer only — fleet-picture probe path and detector never import bmad_loop."""
    for path in (FLEET_PATH, DETECTOR_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "bmad_loop" not in alias.name, f"{path}: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                modname = node.module or ""
                assert "bmad_loop" not in modname, f"{path}: {modname}"
                for alias in node.names:
                    assert "bmad_loop" not in (alias.name or ""), (
                        f"{path}: {alias.name}"
                    )

    for name in list(sys.modules):
        if name == "bmad_loop" or name.startswith("bmad_loop."):
            del sys.modules[name]

    _load_fleet()
    _load_detector()
    assert not any(
        n == "bmad_loop" or n.startswith("bmad_loop.") for n in sys.modules
    )


def test_dispatch_branch_candidates_do_not_import_marshal():
    """local-recipes env has no pyforge.marshal — ATTENTION must still name branches."""
    tree = ast.parse(FLEET_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "pyforge.marshal" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            assert "pyforge.marshal" not in (node.module or "")
    for name in list(sys.modules):
        if name == "pyforge.marshal" or name.startswith("pyforge.marshal."):
            del sys.modules[name]
    mod = _load_fleet()
    assert mod._dispatch_branch_candidates("steward", "42.5") == (
        "dispatch/pyforge-steward/42.5",
        "marshal/42.5",
    )
    assert not any(
        n == "pyforge.marshal" or n.startswith("pyforge.marshal.")
        for n in sys.modules
    )
