"""Meta: `docs/dashboard/generate.py` wall-clock fallback (marshal Story 23.1,
FR-194 CAP-1 — wall-clock ceiling from promoted-spec revision fields).

Loads the REAL `generate.py` via importlib (same pattern as
`test_dashboard_resolve_project.py`) and covers every I/O & Edge-Case Matrix
row from `spec-23-1-wall-clock-fallback-derivation-from-promoted-spec-revision-fields`:

  * Happy path — done + resolvable baseline/final + zero journals → wall-clock
  * Journal wins — closed journal session blocks wall-clock overwrite
  * Unresolvable rev — missing / NO_VCS / unknown rev → absent (never fabricate)
  * Refresh — derived: true recomputes; never freezes stale minutes
  * Curated preserved — non-derived timing+velocity stay byte-identical

Wall-clock minutes never land on `velocity.bars`; metric/note name the
final−baseline ceiling bound.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
GENERATE_PY = REPO_ROOT / "docs" / "dashboard" / "generate.py"


def _load_generate():
    spec = importlib.util.spec_from_file_location(
        "_test_dashboard_generate_scan_timing_wall_clock", GENERATE_PY)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    return mod


@pytest.fixture
def gen():
    if not GENERATE_PY.is_file():
        pytest.skip("docs/dashboard/generate.py not present in this checkout")
    return _load_generate()


def _write_story_spec(
    root: Path,
    project_dir: str,
    epic: str,
    num: str,
    *,
    baseline: str | None,
    final: str | None,
    slug: str = "example",
) -> Path:
    specs = (
        root / "_bmad-output" / "projects" / project_dir
        / "planning-artifacts" / "specs"
    )
    specs.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"title: 'Story {epic}.{num}'", "status: 'done'"]
    if baseline is not None:
        lines.append(f"baseline_revision: '{baseline}'")
    if final is not None:
        lines.append(f"final_revision: '{final}'")
    lines.append("---")
    lines.append("")
    path = specs / f"spec-{epic}-{num}-{slug}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _proj(stories: list[list]) -> dict:
    """Minimal board project with one epic of dashboard story rows."""
    return {
        "label": "Fixture",
        "epics": [{"badge": "E8", "title": "Epic", "stories": stories}],
        "timing": "",
        "velocity": "",
    }


def _git_init_with_two_commits(tmp_path: Path) -> tuple[str, str, int]:
    """Return (baseline_sha, final_sha, expected_ceiling_minutes).

    Uses two commits with forced author/committer dates one hour apart so the
    ceiling is deterministic (60 minutes).
    """
    repo = tmp_path / "gitrepo"
    repo.mkdir()
    env = {
        **dict(**{k: v for k, v in __import__("os").environ.items()}),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True, capture_output=True)
    env1 = {**env, "GIT_AUTHOR_DATE": "2026-08-15T10:00:00",
            "GIT_COMMITTER_DATE": "2026-08-15T10:00:00"}
    subprocess.run(
        ["git", "commit", "-m", "baseline"], cwd=repo, check=True,
        capture_output=True, env=env1)
    baseline = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    subprocess.run(["git", "add", "b.txt"], cwd=repo, check=True, capture_output=True)
    env2 = {**env, "GIT_AUTHOR_DATE": "2026-08-15T11:00:00",
            "GIT_COMMITTER_DATE": "2026-08-15T11:00:00"}
    subprocess.run(
        ["git", "commit", "-m", "final"], cwd=repo, check=True,
        capture_output=True, env=env2)
    final = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    return baseline, final, 60


# --- helpers: happy / unresolvable -------------------------------------------


def test_wall_clock_ceiling_minutes_happy(gen, tmp_path):
    baseline, final, expected = _git_init_with_two_commits(tmp_path)
    repo = tmp_path / "gitrepo"
    assert gen.wall_clock_ceiling_minutes(baseline, final, cwd=repo) == expected


def test_git_commit_timestamp_rejects_no_vcs_and_unknown(gen, tmp_path):
    repo = tmp_path / "gitrepo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    assert gen.git_commit_timestamp("NO_VCS", cwd=repo) is None
    assert gen.git_commit_timestamp("", cwd=repo) is None
    assert gen.git_commit_timestamp("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                                    cwd=repo) is None


# --- I/O Matrix: Happy path --------------------------------------------------


def test_happy_path_done_story_gets_wall_clock_timing(gen, tmp_path, monkeypatch):
    baseline, final, expected = _git_init_with_two_commits(tmp_path)
    git_cwd = tmp_path / "gitrepo"
    root = tmp_path / "tree"
    _write_story_spec(root, "pyforge-fixture", "8", "1",
                      baseline=baseline, final=final)
    (root / "_bmad-output" / "projects" / "pyforge-fixture").mkdir(
        parents=True, exist_ok=True)

    monkeypatch.setattr(gen, "REPO_ROOT", root)
    monkeypatch.setattr(gen, "LOOP_HOMES", {})
    original_ceiling = gen.wall_clock_ceiling_minutes
    monkeypatch.setattr(
        gen, "wall_clock_ceiling_minutes",
        lambda b, f, *, cwd=None: original_ceiling(b, f, cwd=git_cwd))

    projects = {
        "fixture": _proj([["8.1", "done", "Happy path"]]),
    }
    gen.scan_timing(projects)
    timing = projects["fixture"]["timing"]
    assert timing["derived"] is True
    assert timing["perStory"]["8.1"] == expected
    assert "ceiling" in timing["metric"].lower()
    assert "final" in timing["metric"].lower()
    assert "baseline" in timing["metric"].lower()
    # Wall-clock must NOT appear on velocity.bars
    assert projects["fixture"]["velocity"] == ""


# --- I/O Matrix: Journal wins ------------------------------------------------


def test_journal_wins_no_wall_clock_overwrite(gen, tmp_path, monkeypatch):
    baseline, final, _expected = _git_init_with_two_commits(tmp_path)
    git_cwd = tmp_path / "gitrepo"
    root = tmp_path / "tree"
    _write_story_spec(root, "pyforge-fixture", "8", "1",
                      baseline=baseline, final=final)

    loop_home = tmp_path / "loop-home"
    run = loop_home / ".bmad-loop" / "runs" / "r1"
    run.mkdir(parents=True)
    # 120 seconds active compute → 2 minutes
    journal = [
        {"kind": "session-start", "ts": 1_000.0, "task_id": "t1",
         "story_key": "8-1-happy"},
        {"kind": "session-end", "ts": 1_120.0, "task_id": "t1"},
    ]
    (run / "journal.jsonl").write_text(
        "\n".join(json.dumps(e) for e in journal) + "\n", encoding="utf-8")

    monkeypatch.setattr(gen, "REPO_ROOT", root)
    monkeypatch.setattr(gen, "LOOP_HOMES", {"fixture": loop_home})
    original_ceiling = gen.wall_clock_ceiling_minutes

    def ceiling(b, f, *, cwd=None):
        return original_ceiling(b, f, cwd=git_cwd)

    monkeypatch.setattr(gen, "wall_clock_ceiling_minutes", ceiling)

    projects = {"fixture": _proj([["8.1", "done", "Journal story"]])}
    gen.scan_timing(projects)
    timing = projects["fixture"]["timing"]
    assert timing["perStory"]["8.1"] == 2  # journal, not wall-clock 60
    bars = {sid: m for sid, m in projects["fixture"]["velocity"]["bars"]}
    assert bars["8.1"] == 2
    # Metric stays journal-class (no wall-clock marks added)
    assert "wall-clock ceiling" not in timing["metric"]


# --- I/O Matrix: Unresolvable rev --------------------------------------------


@pytest.mark.parametrize("baseline,final", [
    (None, "abc"),                     # missing baseline field
    ("NO_VCS", "abc123"),               # sentinel
    ("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
     "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"),  # not in local history
])
def test_unresolvable_rev_stays_absent(gen, tmp_path, monkeypatch, baseline, final):
    root = tmp_path / "tree"
    if baseline is None:
        _write_story_spec(root, "pyforge-fixture", "8", "2",
                          baseline=None, final=final)
        # Manually omit baseline from an otherwise valid file
        spec = (
            root / "_bmad-output" / "projects" / "pyforge-fixture"
            / "planning-artifacts" / "specs" / "spec-8-2-example.md"
        )
        spec.write_text(
            "---\ntitle: x\nstatus: done\nfinal_revision: 'abc'\n---\n",
            encoding="utf-8")
    else:
        _write_story_spec(root, "pyforge-fixture", "8", "2",
                          baseline=baseline, final=final)

    monkeypatch.setattr(gen, "REPO_ROOT", root)
    monkeypatch.setattr(gen, "LOOP_HOMES", {})
    # Point ceiling at an empty git repo so unknown SHAs fail.
    empty = tmp_path / "emptygit"
    empty.mkdir()
    subprocess.run(["git", "init"], cwd=empty, check=True, capture_output=True)
    original_ceiling = gen.wall_clock_ceiling_minutes

    def ceiling(b, f, *, cwd=None):
        return original_ceiling(b, f, cwd=empty)

    monkeypatch.setattr(gen, "wall_clock_ceiling_minutes", ceiling)

    projects = {"fixture": _proj([["8.2", "done", "Unresolvable"]])}
    gen.scan_timing(projects)
    # No timing marks fabricated
    assert projects["fixture"]["timing"] == ""
    assert projects["fixture"]["velocity"] == ""


# --- I/O Matrix: Refresh -----------------------------------------------------


def test_refresh_recomputes_derived_wall_clock(gen, tmp_path, monkeypatch):
    baseline, final, expected = _git_init_with_two_commits(tmp_path)
    git_cwd = tmp_path / "gitrepo"
    root = tmp_path / "tree"
    _write_story_spec(root, "pyforge-fixture", "8", "3",
                      baseline=baseline, final=final)

    monkeypatch.setattr(gen, "REPO_ROOT", root)
    monkeypatch.setattr(gen, "LOOP_HOMES", {})
    original_ceiling = gen.wall_clock_ceiling_minutes
    call_count = {"n": 0}

    def ceiling(b, f, *, cwd=None):
        call_count["n"] += 1
        return original_ceiling(b, f, cwd=git_cwd)

    monkeypatch.setattr(gen, "wall_clock_ceiling_minutes", ceiling)

    projects = {
        "fixture": _proj([["8.3", "done", "Refresh"]]),
    }
    # Stale derived value that must be overwritten on re-run
    projects["fixture"]["timing"] = {
        "derived": True,
        "metric": "stale",
        "total": 999,
        "totalLabel": "stale",
        "note": "stale",
        "perStory": {"8.3": 999},
        "epicMin": {"E8": 999},
    }
    gen.scan_timing(projects)
    assert projects["fixture"]["timing"]["perStory"]["8.3"] == expected
    assert projects["fixture"]["timing"]["perStory"]["8.3"] != 999
    assert projects["fixture"]["timing"]["derived"] is True
    assert call_count["n"] >= 1
    # Second pass still refreshes
    projects["fixture"]["timing"]["perStory"]["8.3"] = 1
    gen.scan_timing(projects)
    assert projects["fixture"]["timing"]["perStory"]["8.3"] == expected


# --- I/O Matrix: Curated preserved -------------------------------------------


def test_curated_timing_and_velocity_byte_identical(gen, tmp_path, monkeypatch):
    baseline, final, _ = _git_init_with_two_commits(tmp_path)
    root = tmp_path / "tree"
    _write_story_spec(root, "pyforge-fixture", "8", "4",
                      baseline=baseline, final=final)

    curated_timing = {
        "metric": "curated wall-clock",
        "total": 42,
        "totalLabel": "42 min",
        "note": "hand",
        "perStory": {"8.4": 42},
        "epicMin": {"E8": 42},
    }
    curated_velocity = {
        "sub": "curated",
        "bars": [["8.4", 42]],
        "foot": [["42", "x", ""]],
    }
    projects = {
        "fixture": {
            **_proj([["8.4", "done", "Curated"]]),
            "timing": dict(curated_timing),
            "velocity": {
                "sub": curated_velocity["sub"],
                "bars": [list(curated_velocity["bars"][0])],
                "foot": [list(curated_velocity["foot"][0])],
            },
        },
    }
    before_t = json.dumps(projects["fixture"]["timing"], sort_keys=True)
    before_v = json.dumps(projects["fixture"]["velocity"], sort_keys=True)

    monkeypatch.setattr(gen, "REPO_ROOT", root)
    monkeypatch.setattr(gen, "LOOP_HOMES", {})
    gen.scan_timing(projects)

    assert json.dumps(projects["fixture"]["timing"], sort_keys=True) == before_t
    assert json.dumps(projects["fixture"]["velocity"], sort_keys=True) == before_v


# --- Bound naming + velocity isolation ---------------------------------------


def test_metric_names_ceiling_bound_not_unqualified_duration(
        gen, tmp_path, monkeypatch):
    baseline, final, _ = _git_init_with_two_commits(tmp_path)
    git_cwd = tmp_path / "gitrepo"
    root = tmp_path / "tree"
    _write_story_spec(root, "pyforge-fixture", "8", "1",
                      baseline=baseline, final=final)
    monkeypatch.setattr(gen, "REPO_ROOT", root)
    monkeypatch.setattr(gen, "LOOP_HOMES", {})
    original_ceiling = gen.wall_clock_ceiling_minutes
    monkeypatch.setattr(
        gen, "wall_clock_ceiling_minutes",
        lambda b, f, *, cwd=None: original_ceiling(b, f, cwd=git_cwd))

    projects = {"fixture": _proj([["8.1", "done", "Bound name"]])}
    gen.scan_timing(projects)
    metric = projects["fixture"]["timing"]["metric"].lower()
    note = projects["fixture"]["timing"]["note"].lower()
    assert "ceiling" in metric
    assert "duration" not in metric
    assert "baseline" in metric and ("final" in metric or "final_revision" in metric)
    assert "ceiling" in note
    assert projects["fixture"]["velocity"] == ""


# --- Mixed journal + wall-clock (doctor-shaped) ------------------------------


def test_mixed_journal_and_wall_clock_keeps_velocity_journal_only(
        gen, tmp_path, monkeypatch):
    """Journal story A + revision-only story B: timing has both; bars = {A}."""
    baseline, final, expected_wc = _git_init_with_two_commits(tmp_path)
    git_cwd = tmp_path / "gitrepo"
    root = tmp_path / "tree"
    # Only B has a promoted spec — A is journal-measured.
    _write_story_spec(root, "pyforge-fixture", "8", "2",
                      baseline=baseline, final=final)

    loop_home = tmp_path / "loop-home"
    run = loop_home / ".bmad-loop" / "runs" / "r1"
    run.mkdir(parents=True)
    journal = [
        {"kind": "session-start", "ts": 1_000.0, "task_id": "t1",
         "story_key": "8-1-journal"},
        {"kind": "session-end", "ts": 1_180.0, "task_id": "t1"},  # 3 min
    ]
    (run / "journal.jsonl").write_text(
        "\n".join(json.dumps(e) for e in journal) + "\n", encoding="utf-8")

    monkeypatch.setattr(gen, "REPO_ROOT", root)
    monkeypatch.setattr(gen, "LOOP_HOMES", {"fixture": loop_home})
    original_ceiling = gen.wall_clock_ceiling_minutes
    monkeypatch.setattr(
        gen, "wall_clock_ceiling_minutes",
        lambda b, f, *, cwd=None: original_ceiling(b, f, cwd=git_cwd))

    projects = {
        "fixture": _proj([
            ["8.1", "done", "Journal story"],
            ["8.2", "done", "Wall-clock story"],
        ]),
    }
    gen.scan_timing(projects)
    timing = projects["fixture"]["timing"]
    velocity = projects["fixture"]["velocity"]
    bars = {sid: m for sid, m in velocity["bars"]}
    assert bars == {"8.1": 3}
    assert "8.2" not in bars
    assert timing["perStory"]["8.1"] == 3
    assert timing["perStory"]["8.2"] == expected_wc
    assert "wall-clock ceiling" in timing["metric"].lower()
    assert "journal" in timing["metric"].lower()
    assert "ceiling" in timing["note"].lower()
    assert timing["derived"] is True


def test_zero_or_equal_timestamps_stay_absent(gen, tmp_path):
    repo = tmp_path / "gitrepo"
    repo.mkdir()
    env = {
        **dict(**{k: v for k, v in __import__("os").environ.items()}),
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        "GIT_AUTHOR_DATE": "2026-08-15T10:00:00",
        "GIT_COMMITTER_DATE": "2026-08-15T10:00:00",
    }
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "only"], cwd=repo, check=True,
                   capture_output=True, env=env)
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    assert gen.wall_clock_ceiling_minutes(sha, sha, cwd=repo) is None


def test_ambiguous_multi_spec_match_stays_absent(gen, tmp_path, monkeypatch):
    baseline, final, _ = _git_init_with_two_commits(tmp_path)
    git_cwd = tmp_path / "gitrepo"
    root = tmp_path / "tree"
    _write_story_spec(root, "pyforge-fixture", "8", "1",
                      baseline=baseline, final=final, slug="one")
    _write_story_spec(root, "pyforge-fixture", "8", "1",
                      baseline=baseline, final=final, slug="two")
    monkeypatch.setattr(gen, "REPO_ROOT", root)
    monkeypatch.setattr(gen, "LOOP_HOMES", {})
    original_ceiling = gen.wall_clock_ceiling_minutes
    monkeypatch.setattr(
        gen, "wall_clock_ceiling_minutes",
        lambda b, f, *, cwd=None: original_ceiling(b, f, cwd=git_cwd))
    projects = {"fixture": _proj([["8.1", "done", "Ambiguous"]])}
    gen.scan_timing(projects)
    assert projects["fixture"]["timing"] == ""


def test_asymmetric_curated_velocity_allows_derived_timing(
        gen, tmp_path, monkeypatch):
    """Curated velocity must stay untouched while derived timing can fill."""
    baseline, final, expected = _git_init_with_two_commits(tmp_path)
    git_cwd = tmp_path / "gitrepo"
    root = tmp_path / "tree"
    _write_story_spec(root, "pyforge-fixture", "8", "1",
                      baseline=baseline, final=final)
    curated_v = {
        "sub": "curated velocity",
        "bars": [["9.9", 7]],
        "foot": [["7", "x", ""]],
    }
    projects = {
        "fixture": {
            **_proj([["8.1", "done", "Asym"]]),
            "timing": "",
            "velocity": {
                "sub": curated_v["sub"],
                "bars": [list(curated_v["bars"][0])],
                "foot": [list(curated_v["foot"][0])],
            },
        },
    }
    before_v = json.dumps(projects["fixture"]["velocity"], sort_keys=True)
    monkeypatch.setattr(gen, "REPO_ROOT", root)
    monkeypatch.setattr(gen, "LOOP_HOMES", {})
    original_ceiling = gen.wall_clock_ceiling_minutes
    monkeypatch.setattr(
        gen, "wall_clock_ceiling_minutes",
        lambda b, f, *, cwd=None: original_ceiling(b, f, cwd=git_cwd))
    gen.scan_timing(projects)
    assert json.dumps(projects["fixture"]["velocity"], sort_keys=True) == before_v
    assert projects["fixture"]["timing"]["perStory"]["8.1"] == expected
    assert "8.1" not in {
        sid for sid, _ in projects["fixture"]["velocity"]["bars"]}
