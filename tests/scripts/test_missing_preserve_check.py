"""Acceptance tests for scripts/missing_preserve_check.py (Story 20.5 / CAP-3).

Matrix:
  MISSING_FIRE  — intent-gap escalation, no preserve artifact → finding
  PRESENT_CLEAN — intent-gap escalation + attempt-preserve branch → clean
  PATCH_CLEAN   — intent-gap escalation + failed/<story>/changes.patch → clean
  FAILED_FIRE   — intent-gap-preserve-failed journal kind → finding
  NON_GAP_SILENT — non-intent-gap escalation → clean

Harness style matches baseline-drift / loop-stall meta-tests: importlib-load
the script, monkeypatch LOOP_ROOT / REPO, seed a mini ~/.bmad-loops tree.
Never imports bmad_loop.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = REPO_ROOT / "scripts" / "missing_preserve_check.py"

STORY_KEY = "20-5-missing-preserve-detector"
RUN_ID = "20260823-153000-abcd"
PRESERVE_REF = f"attempt-preserve/{RUN_ID}-deadbeef"


def _load_detector():
    spec = importlib.util.spec_from_file_location(
        "missing_preserve_check_under_test", DETECTOR_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["missing_preserve_check_under_test"] = mod
    assert spec.loader is not None
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


def _journal_line(kind: str, payload: dict) -> str:
    return json.dumps({"kind": kind, "phase": "observation", "payload": payload})


def _seed_marshal_journal(
    loop_root: Path,
    *,
    lines: list[str],
    slug: str = "marshal",
    run_id: str = RUN_ID,
) -> Path:
    """Mini loop home with a marshal journal under the S-3.x Tier-3 path."""
    home = loop_root / f"pyforge-{slug}"
    run_dir = (
        home
        / "_bmad-output"
        / "projects"
        / f"pyforge-{slug}"
        / "implementation-artifacts"
        / "runs"
        / run_id
    )
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return home


def _seed_failed_patch(
    home: Path, story: str = STORY_KEY, body: str = "diff --git a/x\n"
) -> Path:
    patch = (
        home
        / ".bmad-loop"
        / "runs"
        / RUN_ID
        / "failed"
        / story
        / "changes.patch"
    )
    patch.parent.mkdir(parents=True)
    patch.write_text(body, encoding="utf-8")
    return patch


def test_missing_artifact_fires(tmp_path, monkeypatch, capsys):
    """CAP-3: intent-gap halt with no preserve artifact → finding (exit 1)."""
    mod = _load_detector()
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_marshal_journal(
        loop_root,
        lines=[
            _journal_line(
                "escalation-detected",
                {
                    "story_key": STORY_KEY,
                    "reason": "Blocking condition: intent gap in contract",
                    "spec_file": "spec-20-5.md",
                },
            )
        ],
    )
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "missing-preserve" in out
    assert STORY_KEY in out


def test_present_branch_passes_clean(tmp_path, monkeypatch, capsys):
    """CAP-3: intent-gap halt with attempt-preserve branch → clean (exit 0)."""
    mod = _load_detector()
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_preserve_branch(repo)
    _seed_marshal_journal(
        loop_root,
        lines=[
            _journal_line(
                "escalation-detected",
                {
                    "story_key": STORY_KEY,
                    "reason": "intent_gap: contradictions in Boundaries",
                    "spec_file": "spec-20-5.md",
                    "preserve_ref": PRESERVE_REF,
                },
            )
        ],
    )
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    assert mod.main() == 0
    assert "OK:" in capsys.readouterr().out


def test_present_patch_passes_clean(tmp_path, monkeypatch):
    """CAP-3: intent-gap halt with failed/<story>/changes.patch → clean."""
    mod = _load_detector()
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    home = _seed_marshal_journal(
        loop_root,
        lines=[
            _journal_line(
                "escalation-detected",
                {
                    "story_key": STORY_KEY,
                    "reason": "intent-gap halt",
                    "spec_file": "spec-20-5.md",
                },
            )
        ],
    )
    _seed_failed_patch(home)
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    assert mod.main() == 0


def test_preserve_failed_kind_fires(tmp_path, monkeypatch):
    """Park failure journaled by 20.4 → finding even without escalation reason."""
    mod = _load_detector()
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_marshal_journal(
        loop_root,
        lines=[
            _journal_line(
                "intent-gap-preserve-failed",
                {"story_key": STORY_KEY},
            )
        ],
    )
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    assert mod.main() == 1


def test_non_intent_gap_escalation_silent(tmp_path, monkeypatch):
    """Ordinary escalation without intent-gap markers → no finding."""
    mod = _load_detector()
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_marshal_journal(
        loop_root,
        lines=[
            _journal_line(
                "escalation-detected",
                {
                    "story_key": "3-7-escalation",
                    "reason": "the frozen spec contradicts itself",
                    "spec_file": "spec-3-7.md",
                },
            )
        ],
    )
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    assert mod.main() == 0


def test_json_mode_lists_findings(tmp_path, monkeypatch, capsys):
    mod = _load_detector()
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_marshal_journal(
        loop_root,
        lines=[
            _journal_line(
                "escalation-detected",
                {
                    "story_key": STORY_KEY,
                    "reason": "intent gap",
                    "spec_file": "spec.md",
                },
            )
        ],
    )
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    assert mod.main(["--json"]) == 1
    findings = json.loads(capsys.readouterr().out)
    assert len(findings) == 1
    assert findings[0]["story"] == STORY_KEY


def test_empty_planes_exit_two(tmp_path, monkeypatch, capsys):
    """Story 33.7: neither plane has journals → exit 2, never 0."""
    mod = _load_detector()
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    rc = mod.main()
    out = capsys.readouterr().out
    assert rc == 2, out
    assert "could-not-observe" in out


def test_dispatch_plane_missing_preserve_fires(tmp_path, monkeypatch, capsys):
    """Story 33.7: intent-gap halt in dispatch-runs without artifact → exit 1."""
    mod = _load_detector()
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    run_dir = (
        repo
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "implementation-artifacts"
        / "dispatch-runs"
        / RUN_ID
    )
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text(
        _journal_line(
            "escalation-detected",
            {
                "story_key": STORY_KEY,
                "reason": "Blocking condition: intent gap",
                "spec_file": "spec-20-5.md",
            },
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "missing-preserve" in out
    assert STORY_KEY in out


def test_dispatch_plane_present_patch_passes_clean(tmp_path, monkeypatch):
    """Story 33.7: dispatch-runs failed/<story>/changes.patch satisfies preserve."""
    mod = _load_detector()
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    run_dir = (
        repo
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "implementation-artifacts"
        / "dispatch-runs"
        / RUN_ID
    )
    run_dir.mkdir(parents=True)
    patch = run_dir / "failed" / STORY_KEY / "changes.patch"
    patch.parent.mkdir(parents=True)
    patch.write_text("diff --git a/x\n", encoding="utf-8")
    (run_dir / "journal.jsonl").write_text(
        _journal_line(
            "escalation-detected",
            {
                "story_key": STORY_KEY,
                "reason": "intent gap halt",
                "spec_file": "spec-20-5.md",
            },
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    assert mod.main() == 0


def test_placement_is_scripts_runtime_not_doctor():
    """Placement decision: scripts/*_check.py + scope=runtime (not doctor)."""
    source = DETECTOR_PATH.read_text(encoding="utf-8")
    assert 'DETECTOR = {"scope": "runtime"}' in source
    assert "PLACEMENT" in source
    assert "pyforge.doctor.sources" in source
    assert "loop-stall-check" in source


# --- Story 87.9: every preserve reader sees preserve tags and origin ----------------------------

PRESERVE_TAG = "preserve/pyforge-marshal/87.9/bmad-loop-deadbeef"


def _gap_with_ref(tmp_path: Path, monkeypatch, ref: str):
    """Intent-gap escalation naming ``ref`` as its preserve artifact; returns ``(mod, repo)``."""
    mod = _load_detector()
    loop_root = tmp_path / "loops"
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _seed_marshal_journal(
        loop_root,
        lines=[
            _journal_line(
                "escalation-detected",
                {
                    "story_key": STORY_KEY,
                    "reason": "intent_gap: contradictions in Boundaries",
                    "spec_file": "spec-20-5.md",
                    "preserve_ref": ref,
                },
            )
        ],
    )
    monkeypatch.setattr(mod, "LOOP_ROOT", loop_root)
    monkeypatch.setattr(mod, "REPO", repo)
    return mod, repo


def _bare_origin(tmp_path: Path, repo: Path) -> Path:
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True, text=True)
    _git(repo, "remote", "add", "origin", str(bare))
    return bare


def test_preserve_tag_is_a_present_artifact(tmp_path, monkeypatch, capsys):
    """A ``preserve/`` tag the journal names counts as present -- not only an attempt-preserve branch."""
    mod, repo = _gap_with_ref(tmp_path, monkeypatch, PRESERVE_TAG)
    _git(repo, "tag", PRESERVE_TAG)
    assert mod.main() == 0
    assert "OK:" in capsys.readouterr().out


def test_named_preserve_tag_that_exists_nowhere_still_fires(tmp_path, monkeypatch, capsys):
    mod, _repo = _gap_with_ref(tmp_path, monkeypatch, PRESERVE_TAG)
    assert mod.main() == 1
    assert STORY_KEY in capsys.readouterr().out


def test_origin_only_attempt_preserve_branch_is_a_present_artifact(tmp_path, monkeypatch, capsys):
    """The branch was pushed and pruned locally: ``origin`` still holds the work, so nothing is missing."""
    mod, repo = _gap_with_ref(tmp_path, monkeypatch, PRESERVE_REF)
    _bare_origin(tmp_path, repo)
    _seed_preserve_branch(repo)
    _git(repo, "push", "origin", PRESERVE_REF)
    _git(repo, "branch", "-D", PRESERVE_REF)
    assert mod.main() == 0
    assert "OK:" in capsys.readouterr().out


def test_origin_read_is_what_clears_an_origin_only_branch(tmp_path, monkeypatch, capsys):
    """Mutation guard: with the origin read blinded the same fixture fires, so the pass above is
    earned by ``ls-remote`` and not by a local-ref inference."""
    mod, repo = _gap_with_ref(tmp_path, monkeypatch, PRESERVE_REF)
    _bare_origin(tmp_path, repo)
    _seed_preserve_branch(repo)
    _git(repo, "push", "origin", PRESERVE_REF)
    _git(repo, "branch", "-D", PRESERVE_REF)
    monkeypatch.setattr(mod.preserve_refs, "ref_on_origin", lambda *a, **k: False)
    assert mod.main() == 1
    assert STORY_KEY in capsys.readouterr().out


def test_local_branch_alone_clears_without_any_remote(tmp_path, monkeypatch):
    """Offline-durable (AD-29): a repo with no ``origin`` still reads its own branch as present."""
    mod, repo = _gap_with_ref(tmp_path, monkeypatch, PRESERVE_REF)
    _seed_preserve_branch(repo)
    assert mod.main() == 0
