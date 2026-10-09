"""``marshal preserve`` CLI tests (Story 87.3)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli.main import main
from pyforge.marshal.cli.preserve import PRESERVE_FLAG_KEY
from pyforge.testing_kit.flags import assert_flag_off_verb, flag_states, flagd_tree
from pyforge.testing_kit.cli_runner import invoke_cli

_FLAG = PRESERVE_FLAG_KEY


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    bare = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", str(bare)], cwd=tmp_path, check=True)
    subprocess.run(["git", "init", str(repo)], cwd=tmp_path, check=True)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "f.txt").write_text("one\n", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-m", "init")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-u", "origin", "HEAD:main")
    _git(repo, "fetch", "origin")
    return repo


@flag_states(_FLAG)
def test_preserve_tag_and_list_when_flag_on(git_repo: Path, flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch):
    if not flag_provider[_FLAG]:
        pytest.skip("covered by flag-off test")
    flags_path = flagd_tree(git_repo, {_FLAG: "on"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flags_path))
    monkeypatch.setattr("pyforge.marshal.cli.preserve.repo_root", lambda: git_repo)
    (git_repo / "f.txt").write_text("two\n", encoding="utf-8")
    (git_repo / "u.txt").write_text("u\n", encoding="utf-8")
    head_before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=git_repo, text=True).strip()
    rc = main(
        [
            "preserve",
            "tag",
            "--story",
            "pyforge-marshal",
            "87.3",
            "--producer",
            "hand",
            "--from",
            str(git_repo),
        ]
    )
    assert rc == 0
    head_after = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=git_repo, text=True).strip()
    assert head_after == head_before
    listed = invoke_cli(main, ["preserve", "list", "--format", "json"])
    assert listed.exit_code == 0
    payload = json.loads(listed.output)
    rows = payload["data"]["preserves"]
    assert len(rows) == 1
    assert rows[0]["station"] == "pyforge-marshal"
    assert rows[0]["story"] == "87.3"
    assert rows[0]["trailers"]["Preserve-Producer"] == "hand"


@flag_states(_FLAG)
def test_preserve_refuses_when_flag_off(flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    if flag_provider[_FLAG]:
        pytest.skip("covered by flag-on test")
    flags_path = flagd_tree(tmp_path, {_FLAG: "off"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flags_path))
    assert_flag_off_verb(main, "preserve", usage_code=2, args=["tag"])


def test_preserve_tag_dedup_mutation(git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    flags_path = flagd_tree(git_repo, {_FLAG: "on"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flags_path))
    argv = [
        "preserve",
        "tag",
        "--story",
        "pyforge-marshal",
        "87.3",
        "--producer",
        "hand",
        "--from",
        str(git_repo),
    ]
    assert main(argv) == 0
    assert main(argv) == 0
    tags = subprocess.check_output(["git", "tag"], cwd=git_repo, text=True).splitlines()
    assert len([t for t in tags if t.startswith("preserve/")]) == 1


def test_preserve_tag_story_tree_dedup_mutation(git_repo: Path, monkeypatch: pytest.MonkeyPatch):
    flags_path = flagd_tree(git_repo, {_FLAG: "on"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flags_path))
    (git_repo / "f.txt").write_text("dedup\n", encoding="utf-8")
    base_argv = [
        "preserve",
        "tag",
        "--story",
        "pyforge-marshal",
        "87.3",
        "--producer",
        "hand",
        "--from",
        str(git_repo),
    ]
    assert main(base_argv) == 0
    assert main(
        [
            "preserve",
            "tag",
            "--story",
            "pyforge-marshal",
            "87.3",
            "--producer",
            "dispatch",
            "--from",
            str(git_repo),
        ]
    ) == 0
    tags = subprocess.check_output(["git", "tag"], cwd=git_repo, text=True).splitlines()
    assert len([t for t in tags if t.startswith("preserve/pyforge-marshal/87.3/")]) == 1
