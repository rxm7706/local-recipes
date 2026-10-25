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
import legacy_preserve_promote as lpp


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


def _non_utf8_commit(repo: Path) -> str:
    """A commit whose diff carries a byte that is not UTF-8.

    git re-encodes the commit message to UTF-8 (it assumes Latin-1), so only the diff
    stays non-UTF-8; ``_raw_non_utf8_commit`` covers the subject.
    """
    (repo / "latin1.txt").write_bytes(b"caf\xe9\n")
    _git(repo, "add", "latin1.txt")
    message = repo / "msg.bin"
    message.write_bytes(b"tip caf\xe9\n")
    _git(repo, "commit", "-q", "-F", str(message))
    message.unlink()
    return _git(repo, "rev-parse", "HEAD")


def test_patch_id_reads_a_non_utf8_diff(clone: Path) -> None:
    """Story 87.17: `git show` of `e09f50352d` on `origin/main` is not UTF-8."""
    sha = _non_utf8_commit(clone)
    pid = lpp._patch_id(clone, sha)
    assert pid is not None and len(pid) == 40
    show = subprocess.run(
        ["git", "-C", str(clone), "show", "--format=email", "--no-prefix", "--binary", sha],
        check=True,
        capture_output=True,
    ).stdout
    expected = subprocess.run(
        ["git", "patch-id"], input=show, check=True, capture_output=True
    ).stdout.split()[0].decode("ascii")
    assert pid == expected


def test_dry_run_survives_a_non_utf8_commit_on_origin_main(clone: Path, tmp_path: Path) -> None:
    """Story 87.17: one non-UTF-8 commit on `origin/main` used to stop the run before the manifest."""
    _non_utf8_commit(clone)
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "fetch", "-q", "origin")
    rescue_sha = _commit_on(clone, "rescue")
    _git(clone, "tag", "-a", "-m", "rescue tip", f"rescue/dangling-20260801-{rescue_sha[:8]}", rescue_sha)
    dirty = "refs/attempt-preserve-dirty/run2-feedface"
    _git(clone, "update-ref", dirty, rescue_sha)

    manifest_dir = tmp_path / "manifests"
    assert lpp.run(clone, manifest_dir=manifest_dir, manifest_date="2026-10-22", execute=False, push_reviewed=False) == 0
    manifest = json.loads((manifest_dir / "legacy-preserve-promote-2026-10-22.json").read_text())
    assert [r for r in manifest["rows"] if r["source_ref"] == dirty]
    assert [r for r in manifest["rows"] if r["kind"] == "classify"]


def _raw_non_utf8_commit(repo: Path) -> str:
    """A commit object whose message bytes are not UTF-8, written without `git commit`'s repair."""
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    parent = _git(repo, "rev-parse", "HEAD")
    body = (
        f"tree {tree}\nparent {parent}\n"
        "author T <t@example.com> 1700000000 +0000\n"
        "committer T <t@example.com> 1700000000 +0000\n\n"
    ).encode() + b"raw caf\xe9\n"
    return subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=body,
        check=True,
        capture_output=True,
    ).stdout.decode().strip()


def test_classify_reads_a_non_utf8_subject(clone: Path) -> None:
    """Story 87.17: `_git` reads git's text with errors="replace", so a raw subject cannot raise."""
    sha = _raw_non_utf8_commit(clone)
    raw = subprocess.run(
        ["git", "-C", str(clone), "cat-file", "commit", sha], check=True, capture_output=True
    ).stdout
    assert b"caf\xe9" in raw
    classification, _evidence = lpp.classify_rescue_dangling(clone, sha, origin_patch_ids=set())
    assert classification == "unresolved"


def test_inventory_reads_nested_legacy_refs(clone: Path, bare_origin: Path) -> None:
    """Story 87.18: nested branch and tag names, and the kept branches on origin, are listed."""
    sha = _commit_on(clone)
    kept = "attempt-preserve/20260712-125315-0aaa-c2605ff1"
    _git(clone, "push", "-q", "origin", f"{sha}:refs/heads/{kept}")
    _git(clone, "fetch", "-q", "origin")
    _git(clone, "update-ref", "refs/heads/backup/bmad-suite-updates-2026-09-26", sha)
    _git(clone, "update-ref", "refs/heads/archive/crewai-toolkit-wip-2026", sha)
    _git(clone, "tag", "-a", "-m", "legacy", "bmad-loop-preserve/5-9-intent-gap-2026-08-12", sha)
    _git(clone, "tag", "-a", "-m", "legacy", "archive/recover-scribe-1-3", sha)
    _git(clone, "tag", "-a", "-m", "legacy", "archive/scribe-1-3-dangling-91d3571f", sha)

    sources = {r.source_ref: r for r in lpp.collect_promotion_rows(clone)}
    assert f"refs/remotes/origin/{kept}" in sources
    assert sources[f"refs/remotes/origin/{kept}"].twin_ref.startswith("refs/tags/preserve/")
    # The backup name carries a date, which AD-81 bars, so it falls back to a hand twin.
    assert sources["refs/heads/backup/bmad-suite-updates-2026-09-26"].twin_ref.startswith(
        "refs/tags/preserve/unbound/hand-"
    )
    assert sources["refs/heads/archive/crewai-toolkit-wip-2026"].twin_ref == (
        "refs/tags/archive/heads/archive/crewai-toolkit-wip-2026"
    )
    assert sources["refs/tags/bmad-loop-preserve/5-9-intent-gap-2026-08-12"].twin_ref.startswith(
        "refs/tags/preserve/pyforge-marshal/5.9/"
    )
    assert sources["refs/tags/archive/recover-scribe-1-3"].twin_ref.startswith("refs/tags/archive/tags/")
    assert "refs/tags/archive/scribe-1-3-dangling-91d3571f" in sources


def test_push_reviewed_ac9_skips_origin_rows_and_continues_after_git_error(
    clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 87.19 AC9: cap 20/run, skip twins already on origin, survive ``PreserveGitError``."""
    from pyforge.core.preserve_refs import PreserveGitError, PushPreserveResult

    commit = _commit_on(clone)
    rows: list[lpp.ManifestRow] = []
    on_origin: set[str] = set()
    for i in range(25):
        twin = f"refs/tags/preserve/unbound/hand-{i:04d}"
        _git(clone, "tag", "-a", "-m", "t", twin.removeprefix("refs/tags/"), commit)
        if i < 3:
            _git(clone, "push", "-q", "origin", f"{twin}:{twin}")
            on_origin.add(twin)
        rows.append(
            lpp.ManifestRow(
                kind="promote",
                source_ref=f"refs/heads/x{i}",
                commit_sha=commit,
                twin_ref=twin,
                twin_evidence="test",
                reviewed=True,
                action="write_twin",
            )
        )

    listed_on_origin: set[str] = set(on_origin)
    push_calls: list[str] = []

    def _fake_remote(repo: Path, patterns: object, **kwargs: object) -> frozenset[str]:
        return frozenset(listed_on_origin)

    def _fake_push(repo: Path, refname: str, **kwargs: object) -> PushPreserveResult:
        push_calls.append(refname)
        if refname.endswith("hand-0010"):
            raise PreserveGitError("simulated push failure")
        listed_on_origin.add(refname)
        return PushPreserveResult(refname, True, ())

    monkeypatch.setattr(lpp, "remote_ref_names", _fake_remote)
    monkeypatch.setattr(lpp, "push_preserve_ref", _fake_push)
    notes1 = lpp.push_reviewed_rows(clone, rows)
    assert len(push_calls) == 20
    notes2 = lpp.push_reviewed_rows(clone, rows)
    assert len(push_calls) == 22
    assert sum(1 for n in notes2 if n.startswith("skipped push")) >= 3
    assert any("simulated push failure" in n for n in notes1)
