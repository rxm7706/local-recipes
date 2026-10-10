"""Story 87.16: orphan_tip_archive.py — fixture git repos, injected readers, no GitHub."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "orphan_tip_archive.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import orphan_tip_archive as ota  # noqa: E402


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
    (repo / "scripts").mkdir()
    shutil.copy2(SCRIPT, repo / "scripts" / SCRIPT.name)
    return repo


def _orphan_commit(repo: Path, *, label: str = "orphan") -> str:
    path = repo / f"{label}.txt"
    path.write_text(f"{label}\n", encoding="utf-8")
    _git(repo, "add", str(path.name))
    _git(repo, "commit", "-qm", f"orphan tip {label}")
    return _git(repo, "rev-parse", "HEAD")


def _reader(events: list[ota.DeletionEvent]) -> ota.DeletionReader:
    def _read() -> tuple[list[ota.DeletionEvent], str]:
        return list(events), ""

    return _read


def test_dry_run_lists_only_unreachable_tips(clone: Path, tmp_path: Path) -> None:
    orphan_sha = _orphan_commit(clone, label="orphan-a")
    _git(clone, "reset", "--hard", "origin/main")

    merged_sha = _orphan_commit(clone, label="merged-b")
    _git(clone, "checkout", "-q", "main")
    _git(clone, "merge", "-q", "--ff-only", merged_sha)
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "fetch", "-q", "origin")

    orphan2_sha = _orphan_commit(clone, label="orphan-c")
    _git(clone, "reset", "--hard", "origin/main")

    branch_sha = _orphan_commit(clone, label="branch-d")
    _git(clone, "branch", "keep/me", branch_sha)
    _git(clone, "checkout", "-q", "main")
    _git(clone, "reset", "--hard", "origin/main")

    events = [
        ota.DeletionEvent("gone/orphan", orphan_sha, "fixture"),
        ota.DeletionEvent("gone/merged", merged_sha, "fixture"),
        ota.DeletionEvent("gone/orphan2", orphan2_sha, "fixture"),
        ota.DeletionEvent("gone/branch", branch_sha, "fixture"),
    ]
    manifest_dir = tmp_path / "manifests"
    rc = ota.run(
        clone,
        manifest_dir=manifest_dir,
        activity_date="2026-10-04",
        execute=False,
        reader=_reader(events),
    )
    assert rc == 0
    manifest = json.loads((manifest_dir / "orphan-tip-archive-2026-10-04.json").read_text())
    shas = {r["before_sha"] for r in manifest["rows"]}
    assert orphan_sha in shas
    assert orphan2_sha in shas
    assert merged_sha not in shas
    assert branch_sha not in shas
    assert all(r["archive_tag"].startswith("refs/tags/archive/heads/") for r in manifest["rows"])


def test_execute_writes_archive_tags_and_is_idempotent(clone: Path, tmp_path: Path) -> None:
    orphan_sha = _orphan_commit(clone)
    _git(clone, "reset", "--hard", "origin/main")
    events = [ota.DeletionEvent("feat/orphan", orphan_sha, "fixture")]
    manifest_dir = tmp_path / "manifests"

    assert (
        ota.run(
            clone,
            manifest_dir=manifest_dir,
            activity_date="2026-10-04",
            execute=True,
            reader=_reader(events),
        )
        == 0
    )
    tag = "refs/tags/archive/heads/feat/orphan"
    assert ota.tag_exists(clone, tag)
    msg = _git(clone, "cat-file", "-p", tag)
    assert "Archive-From: refs/heads/feat/orphan" in msg
    assert "Archive-Reason:" in msg
    assert "Archive-Evidence:" in msg

    assert (
        ota.run(
            clone,
            manifest_dir=manifest_dir,
            activity_date="2026-10-04",
            execute=True,
            reader=_reader(events),
        )
        == 0
    )
    assert _git(clone, "rev-parse", f"{tag}^{{commit}}") == orphan_sha


def test_execute_skips_tip_that_became_reachable(clone: Path, tmp_path: Path) -> None:
    orphan_sha = _orphan_commit(clone)
    _git(clone, "reset", "--hard", "origin/main")
    events = [ota.DeletionEvent("feat/late", orphan_sha, "fixture")]
    manifest_dir = tmp_path / "manifests"
    assert ota.run(clone, manifest_dir=manifest_dir, activity_date="2026-10-04", execute=False, reader=_reader(events)) == 0
    rows = ota.build_manifest_rows(clone, events)
    assert len(rows) == 1

    _git(clone, "branch", "rescue/late", orphan_sha)
    notes = ota.execute_archive_tags(clone, rows)
    assert any("skipped" in n for n in notes)
    assert not ota.tag_exists(clone, "refs/tags/archive/heads/feat/late")


def test_github_reader_fails_closed_without_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ota, "gh_has_authenticated_quota", lambda: (False, "no quota"))
    reader = ota.github_branch_deletion_reader("rxm7706/local-recipes", "2026-10-04")
    events, err = reader()
    assert events == []
    assert "quota" in err.lower() or "no quota" in err


def test_runtime_reader_failure_exits_two_without_manifest(clone: Path, tmp_path: Path) -> None:
    def _fail() -> tuple[list[ota.DeletionEvent], str]:
        return [], "api down"

    manifest_dir = tmp_path / "manifests"
    rc = ota.run(
        clone,
        manifest_dir=manifest_dir,
        activity_date="2026-10-04",
        execute=False,
        reader=_fail,
    )
    assert rc == 2
    assert not (manifest_dir / "orphan-tip-archive-2026-10-04.json").exists()


def test_retirement_table_merged_into_events() -> None:
    merged = ota.merge_deletion_events([], ota.retirement_table_events())
    assert len(merged) == len(ota.ATTEMPT_PRESERVE_RETIREMENTS)
    assert merged[0].source == "story-87-1-retirement-table"
