"""Acceptance tests for scripts/bmad_loop_baseline_drift_check.py (Story 20.1 / CAP-1).

Covers the I/O matrix: DRIFT_FIRE, CLEAN_SILENT, RECOVERED_SILENT, READ_ONLY.
Harness style matches the loop-stall-check meta-test: importlib-load the
script, monkeypatch LOOP_ROOT / REPO, seed a mini ~/.bmad-loops tree under
tmp_path. Never imports bmad_loop (the detector must not either).

Preserve refs are discovered via real ``git for-each-ref`` against a mini
git REPO (not a monkeypatched ``preserve_refs``) so CAP-1's recover-from
line cannot go green while the live helper is broken.
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
DETECTOR_PATH = REPO_ROOT / "scripts" / "bmad_loop_baseline_drift_check.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "baseline_drift"

STORY_KEY = "9-6-plan-and-action-types-repo-fingerprint-and-the-plan-builder"
RUN_ID = "20260813-094919-bfcb"
REAL_BASELINE = "523e938c7978"
DRIFTED_BASELINE = "26102ea12c6d"
# CAP-1 contracted preserve-ref shape (short hash of the real basis).
PRESERVE_REF = f"attempt-preserve/{RUN_ID}-523e938c"


def _load_detector():
    spec = importlib.util.spec_from_file_location(
        "bmad_loop_baseline_drift_check_under_test", DETECTOR_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bmad_loop_baseline_drift_check_under_test"] = mod
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
    """Empty git repo under ``repo`` so ``preserve_refs`` can for-each-ref."""
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
) -> Path:
    """Mini loop-home tree: pyforge-<slug>/.git + .bmad-loop/runs/<run>/journal.jsonl."""
    home = loop_root / f"pyforge-{slug}"
    (home / ".git").mkdir(parents=True)
    run_dir = home / ".bmad-loop" / "runs" / run_id
    run_dir.mkdir(parents=True)
    shutil.copy(
        FIXTURES / journal_fixture,
        run_dir / "journal.jsonl",
    )
    return home


def _seed_repo_ledger(repo: Path, *, ledger_fixture: str | None) -> Path:
    """Tracked sprint-status-ledger under a fake REPO for recovered/silence tests."""
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
    return dest


def _run_main(mod, loop_root: Path, repo: Path, monkeypatch) -> int:
    """Run main with injectable roots; leave ``preserve_refs`` unpatched."""
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    return mod.main()


def test_drift_fire_names_story_baselines_and_preserve_ref(
    tmp_path, monkeypatch, capsys
):
    """Matrix row DRIFT_FIRE: 9-6-shaped defer → exit 1 with story + both baselines + ref."""
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_preserve_branch(repo)
    _seed_loop_home(loop_root, journal_fixture="journal_9_6_drift.jsonl")
    _seed_repo_ledger(repo, ledger_fixture=None)

    mod = _load_detector()
    rc = _run_main(mod, loop_root, repo, monkeypatch)
    out = capsys.readouterr().out

    assert rc == 1, out
    assert STORY_KEY in out
    assert f"real basis {REAL_BASELINE}" in out
    assert f"orchestrator-recorded {DRIFTED_BASELINE}" in out
    assert PRESERVE_REF in out
    assert "recover from:" in out
    assert "[unrecovered]" in out


def test_clean_silent_exits_zero_with_no_finding(tmp_path, monkeypatch, capsys):
    """Matrix row CLEAN_SILENT: journal lacks baseline-drift defer → exit 0."""
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_loop_home(loop_root, journal_fixture="journal_clean.jsonl")
    _seed_repo_ledger(repo, ledger_fixture=None)

    mod = _load_detector()
    rc = _run_main(mod, loop_root, repo, monkeypatch)
    out = capsys.readouterr().out

    assert rc == 0, out
    assert "OK: no unrecovered baseline-drift defer" in out
    assert "[unrecovered]" not in out
    assert REAL_BASELINE not in out


def test_recovered_silent_when_ledger_marks_story_done(
    tmp_path, monkeypatch, capsys
):
    """Matrix row RECOVERED_SILENT: drift defer present but story done in ledger → exit 0."""
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_preserve_branch(repo)
    _seed_loop_home(loop_root, journal_fixture="journal_9_6_drift.jsonl")
    _seed_repo_ledger(repo, ledger_fixture="sprint_status_ledger_recovered.yaml")

    mod = _load_detector()
    rc = _run_main(mod, loop_root, repo, monkeypatch)
    out = capsys.readouterr().out

    assert rc == 0, out
    assert "[unrecovered]" not in out
    assert "OK: no unrecovered baseline-drift defer" in out


def test_read_only_no_bmad_loop_import_and_no_mutation(tmp_path, monkeypatch, capsys):
    """Matrix row READ_ONLY: no bmad_loop import; loop home + journal unchanged."""
    tree = ast.parse(DETECTOR_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "bmad_loop" not in alias.name, alias.name
        elif isinstance(node, ast.ImportFrom):
            modname = node.module or ""
            assert "bmad_loop" not in modname, modname
            for alias in node.names:
                assert "bmad_loop" not in (alias.name or ""), alias.name

    assert DETECTOR_PATH.read_text(encoding="utf-8").count(
        'DETECTOR = {"scope": "runtime"}'
    ) == 1

    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    home = _seed_loop_home(loop_root, journal_fixture="journal_9_6_drift.jsonl")
    journal = home / ".bmad-loop" / "runs" / RUN_ID / "journal.jsonl"
    before = journal.read_bytes()
    marker = home / "READ_ONLY_MARKER"
    marker.write_text("untouched\n", encoding="utf-8")
    ledger = _seed_repo_ledger(repo, ledger_fixture=None)
    ledger_before = ledger.read_bytes()

    for name in list(sys.modules):
        if name == "bmad_loop" or name.startswith("bmad_loop."):
            del sys.modules[name]

    mod = _load_detector()
    assert not any(
        n == "bmad_loop" or n.startswith("bmad_loop.") for n in sys.modules
    )

    rc = _run_main(mod, loop_root, repo, monkeypatch)
    _ = capsys.readouterr()

    assert rc == 1  # drift still fires; read-only is about side effects
    assert journal.read_bytes() == before
    assert ledger.read_bytes() == ledger_before
    assert marker.read_text(encoding="utf-8") == "untouched\n"
    assert not any(
        n == "bmad_loop" or n.startswith("bmad_loop.") for n in sys.modules
    )


def test_detector_scope_is_runtime_not_repo():
    """Confirm DETECTOR.scope keeps this out of detectors-ci / --scope repo."""
    mod = _load_detector()
    assert mod.DETECTOR == {"scope": "runtime"}

    det_spec = importlib.util.spec_from_file_location(
        "detectors_under_test", REPO_ROOT / "scripts" / "detectors.py"
    )
    det = importlib.util.module_from_spec(det_spec)
    det_spec.loader.exec_module(det)
    found, _gaps = det.discover()
    matches = [
        row
        for row in found
        if "bmad_loop_baseline_drift_check" in str(row.get("path", ""))
        or row.get("name") == "bmad_loop_baseline_drift_check"
    ]
    assert matches, f"detector not discovered; sample={found[:3]!r}"
    assert all(m.get("scope") == "runtime" for m in matches)
    assert not any(m.get("scope") == "repo" for m in matches)


def test_collect_findings_returns_unrecovered_dicts(tmp_path, monkeypatch):
    """Story 20.2: collect_findings() is the shared list for human/--json/ATTENTION."""
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_preserve_branch(repo)
    _seed_loop_home(loop_root, journal_fixture="journal_9_6_drift.jsonl")
    _seed_repo_ledger(repo, ledger_fixture=None)

    mod = _load_detector()
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)

    findings = mod.collect_findings()
    assert len(findings) == 1
    f = findings[0]
    assert f["slug"] == "marshal"
    assert f["story"] == STORY_KEY
    assert f["run"] == RUN_ID
    assert f["real"] == REAL_BASELINE
    assert f["drifted"] == DRIFTED_BASELINE
    assert PRESERVE_REF in f["refs"]


def test_collect_findings_empty_when_recovered(tmp_path, monkeypatch):
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_preserve_branch(repo)
    _seed_loop_home(loop_root, journal_fixture="journal_9_6_drift.jsonl")
    _seed_repo_ledger(repo, ledger_fixture="sprint_status_ledger_recovered.yaml")

    mod = _load_detector()
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)

    assert mod.collect_findings() == []


def test_json_flag_prints_findings_and_exits_nonzero(tmp_path, monkeypatch, capsys):
    """--json: machine list only; exit 1 when unrecovered (CAP-1 loud exit preserved)."""
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_preserve_branch(repo)
    _seed_loop_home(loop_root, journal_fixture="journal_9_6_drift.jsonl")
    _seed_repo_ledger(repo, ledger_fixture=None)

    mod = _load_detector()
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    rc = mod.main(["--json"])
    out = capsys.readouterr().out

    assert rc == 1
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["story"] == STORY_KEY
    assert data[0]["real"] == REAL_BASELINE
    assert data[0]["drifted"] == DRIFTED_BASELINE
    assert PRESERVE_REF in data[0]["refs"]
    assert "[unrecovered]" not in out  # no human banner mixed into --json


def test_json_flag_empty_array_on_clean(tmp_path, monkeypatch, capsys):
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_loop_home(loop_root, journal_fixture="journal_clean.jsonl")
    _seed_repo_ledger(repo, ledger_fixture=None)

    mod = _load_detector()
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    rc = mod.main(["--json"])
    out = capsys.readouterr().out

    assert rc == 0
    assert json.loads(out) == []
