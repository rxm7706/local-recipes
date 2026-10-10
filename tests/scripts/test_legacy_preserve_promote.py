"""Story 87.12: legacy_preserve_promote.py — fixture git repos, no live legacy inventory."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "legacy_preserve_promote.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import legacy_preserve_promote as lpp  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def bare_origin(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    return remote


@pytest.fixture
def clone(bare_origin: Path, tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", str(bare_origin), str(repo)], check=True)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "fetch", "-q", "origin")
    return repo


def _commit_on(repo: Path, branch: str | None = None) -> str:
    (repo / "f.txt").write_text(f"{branch or 'x'}\n", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-qm", f"tip {branch or 'x'}")
    return _git(repo, "rev-parse", "HEAD")


def test_dry_run_lists_dirty_ref_and_rescue_classification(clone: Path, tmp_path: Path) -> None:
    sha = _commit_on(clone)
    dirty = "refs/attempt-preserve-dirty/run1-deadbeef"
    _git(clone, "update-ref", dirty, sha)

    rescue_sha = _commit_on(clone, "rescue")
    _git(
        clone,
        "tag",
        "-a",
        "-m",
        "WIP on main: rescue tip",
        f"rescue/dangling-20260801-{rescue_sha[:8]}",
        rescue_sha,
    )

    manifest_dir = tmp_path / "manifests"
    assert lpp.run(clone, manifest_dir=manifest_dir, manifest_date="2026-10-04", execute=False, push_reviewed=False) == 0
    manifest = json.loads((manifest_dir / "legacy-preserve-promote-2026-10-04.json").read_text())
    kinds = {r["kind"] for r in manifest["rows"]}
    assert "promote" in kinds
    assert "classify" in kinds
    assert "operator_gate" in kinds
    dirty_rows = [r for r in manifest["rows"] if r["source_ref"] == dirty]
    assert len(dirty_rows) == 1
    assert dirty_rows[0]["twin_ref"].startswith("refs/tags/preserve/")
    assert dirty_rows[0]["action"] == "write_twin"
    classify_rows = [r for r in manifest["rows"] if r["kind"] == "classify"]
    assert classify_rows[0]["classification"] in {
        "synthetic",
        "stash",
        "merge",
        "patch-equivalent",
        "unresolved",
    }
    assert _git(clone, "rev-parse", dirty) == sha


def test_execute_writes_preserve_twin_and_is_idempotent(clone: Path, tmp_path: Path) -> None:
    sha = _commit_on(clone)
    branch = "attempt-preserve/47.1-dispatch-20260920-80e85c57"
    _git(clone, "branch", branch, sha)
    manifest_dir = tmp_path / "manifests"

    assert (
        lpp.run(
            clone,
            manifest_dir=manifest_dir,
            manifest_date="2026-10-04",
            execute=True,
            push_reviewed=False,
        )
        == 0
    )
    manifest = json.loads((manifest_dir / "legacy-preserve-promote-2026-10-04.json").read_text())
    twin = next(r["twin_ref"] for r in manifest["rows"] if r["source_ref"] == f"refs/heads/{branch}")
    assert lpp._tag_exists(clone, twin)
    assert (
        lpp.run(
            clone,
            manifest_dir=manifest_dir,
            manifest_date="2026-10-04",
            execute=True,
            push_reviewed=False,
        )
        == 0
    )


def test_push_reviewed_refuses_unreviewed_row(clone: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sha = _commit_on(clone)
    dirty = "refs/attempt-preserve-dirty/run1-deadbeef"
    _git(clone, "update-ref", dirty, sha)
    manifest_dir = tmp_path / "manifests"
    lpp.run(clone, manifest_dir=manifest_dir, manifest_date="2026-10-04", execute=True, push_reviewed=False)

    def _fail_push(*_a: object, **_k: object) -> object:
        raise AssertionError("push must not run for unreviewed rows")

    monkeypatch.setattr(lpp, "push_preserve_ref", _fail_push)
    notes = lpp.push_reviewed_rows(
        clone,
        [
            lpp.ManifestRow(
                kind="promote",
                source_ref=dirty,
                commit_sha=sha,
                twin_ref="refs/tags/preserve/unbound/hand-deadbeef",
                twin_evidence="test",
                reviewed=False,
                action="write_twin",
            )
        ],
    )
    assert any("not reviewed" in n for n in notes)


def test_classify_synthetic_subject(clone: Path) -> None:
    _git(clone, "commit", "--allow-empty", "-qm", "marshal teardown merged-check (not a real commit)")
    sha = _git(clone, "rev-parse", "HEAD")
    kind, _ = lpp.classify_rescue_dangling(clone, sha, origin_patch_ids=set())
    assert kind == "synthetic"
