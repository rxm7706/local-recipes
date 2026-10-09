"""``marshal preserve`` CLI tests (Story 87.3)."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from pyforge.core.preserve_refs import PreserveGitError, PreserveRefConflictError, PreserveRefError
from pyforge.testing_kit.cli_runner import invoke_cli
from pyforge.testing_kit.flags import assert_flag_off_verb, flag_states, flagd_tree

from pyforge.marshal.cli import preserve as preserve_module
from pyforge.marshal.cli.main import main
from pyforge.marshal.core.model import Verdict
from pyforge.marshal.core.verdict import EXIT_USAGE, exit_code_for

_FLAG = "pyforge.marshal.preserve_refs"


def _flag_on(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(root, {_FLAG: "on"})))


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
def test_preserve_tag_and_list_when_flag_on(
    git_repo: Path, flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch
):
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
def test_preserve_refuses_when_flag_off(
    flag_provider: dict[str, bool], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    if flag_provider[_FLAG]:
        pytest.skip("covered by flag-on test")
    flags_path = flagd_tree(tmp_path, {_FLAG: "off"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flags_path))
    assert_flag_off_verb(main, "preserve", usage_code=2, args=["tag"])
    assert_flag_off_verb(main, "preserve", usage_code=2, args=["push"])
    assert_flag_off_verb(
        main,
        "preserve",
        usage_code=2,
        args=["retire", "refs/tags/preserve/x", "--evidence", "story s 1.1 done deadbeef"],
    )


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
    assert (
        main(
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
        )
        == 0
    )
    tags = subprocess.check_output(["git", "tag"], cwd=git_repo, text=True).splitlines()
    assert len([t for t in tags if t.startswith("preserve/pyforge-marshal/87.3/")]) == 1


def test_preserve_tag_rejects_non_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    _flag_on(monkeypatch, tmp_path)
    monkeypatch.setattr(preserve_module, "_is_git_worktree", lambda _path: False)
    code = preserve_module.run_preserve_tag(
        argparse.Namespace(
            from_path=str(tmp_path / "not-a-repo"),
            story=None,
            producer="hand",
            provenance="human",
            reason="hand",
            source="",
            run="",
            journal="",
        )
    )
    assert code == EXIT_USAGE
    assert "not a git worktree" in capsys.readouterr().err


def test_preserve_tag_unbound_and_head_fallback(git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    _flag_on(monkeypatch, git_repo)
    monkeypatch.setattr(preserve_module, "snapshot_worktree_commit", lambda _wt: None)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=git_repo, text=True).strip()
    code = preserve_module.run_preserve_tag(
        argparse.Namespace(
            from_path=str(git_repo),
            story=None,
            producer="hand",
            provenance="human",
            reason="hand",
            source="",
            run="",
            journal="",
        )
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["commit"] == commit
    assert payload["refname"].startswith("refs/tags/preserve/unbound/hand-")


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (PreserveRefConflictError("name taken"), EXIT_USAGE),
        (PreserveRefError("bad ref"), exit_code_for(Verdict.ERROR)),
        (PreserveGitError("git failed"), exit_code_for(Verdict.ERROR)),
    ],
)
def test_preserve_tag_maps_core_errors(
    git_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    exc: BaseException,
    expected: int,
):
    _flag_on(monkeypatch, git_repo)

    def boom(*_a, **_k):
        raise exc

    monkeypatch.setattr(preserve_module, "tag_preserve", boom)
    monkeypatch.setattr(preserve_module, "snapshot_worktree_commit", lambda _wt: "deadbeef")
    monkeypatch.setattr(preserve_module, "render_preserve_ref", lambda **_k: "refs/tags/preserve/x")

    code = preserve_module.run_preserve_tag(
        argparse.Namespace(
            from_path=str(git_repo),
            story=("pyforge-marshal", "87.3"),
            producer="hand",
            provenance="human",
            reason="hand",
            source="",
            run="",
            journal="",
        )
    )
    assert code == expected
    assert "marshal preserve tag:" in capsys.readouterr().err


def test_preserve_list_text_output(git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    _flag_on(monkeypatch, git_repo)
    monkeypatch.setattr(preserve_module, "repo_root", lambda: git_repo)
    row = SimpleNamespace(
        refname="refs/tags/preserve/unbound/hand-deadbeef",
        object_sha="deadbeef",
        project_slug=None,
        story_key=None,
        producer="hand",
        sha8="deadbeef",
        state=SimpleNamespace(value="open"),
        trailers=SimpleNamespace(
            producer="hand",
            provenance="human",
            reason="hand",
            source="/wt",
            run="",
            journal="",
            commit="deadbeef",
        ),
    )
    monkeypatch.setattr(preserve_module, "list_preserves", lambda *_a, **_k: [row])
    assert (
        preserve_module.run_preserve_list(
            argparse.Namespace(format="text", station=None, story=None, producer=None, state=None)
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "refs/tags/preserve/unbound/hand-deadbeef" in out
    assert "open" in out


@pytest.mark.parametrize("fmt", ["text", "json"])
def test_preserve_list_surfaces_git_errors(git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys, fmt: str):
    _flag_on(monkeypatch, git_repo)
    monkeypatch.setattr(preserve_module, "repo_root", lambda: git_repo)

    def fail_list(*_a, **_k):
        raise PreserveGitError("list failed")

    monkeypatch.setattr(preserve_module, "list_preserves", fail_list)
    code = preserve_module.run_preserve_list(
        argparse.Namespace(format=fmt, station=None, story=None, producer=None, state=None)
    )
    assert code == exit_code_for(Verdict.ERROR)
    captured = capsys.readouterr()
    if fmt == "json":
        payload = json.loads(captured.out)
        assert payload["findings"][0]["code"] == "MRS-PRESERVE-001"
    else:
        assert "list failed" in captured.err


def test_preserve_retire_and_list_retired(git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    _flag_on(monkeypatch, git_repo)
    monkeypatch.setattr(preserve_module, "repo_root", lambda: git_repo)
    monkeypatch.setattr(preserve_module, "retirements_path", lambda root: root / "preserve-retirements.yaml")
    ref = "refs/tags/preserve/pyforge-marshal/87.15/hand-deadbeef"
    evidence = "story pyforge-marshal 87.15 done deadbeef"
    rc = main(["preserve", "retire", ref, "--evidence", evidence])
    assert rc == 0
    listed = invoke_cli(main, ["preserve", "list", "--state", "retired", "--format", "json"])
    assert listed.exit_code == 0
    payload = json.loads(listed.output)
    rows = payload["data"]["preserves"]
    assert len(rows) == 1
    assert rows[0]["refname"] == ref
    assert rows[0]["state"] == "retired"


def test_preserve_push_refuses_secret(git_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    _flag_on(monkeypatch, git_repo)
    monkeypatch.setattr(preserve_module, "repo_root", lambda: git_repo)
    purge = git_repo / "docs" / "governance" / "preserve-purge-list.json"
    purge.parent.mkdir(parents=True, exist_ok=True)
    purge.write_text('{"schema_version":1,"commit_shas":[],"paths":[]}', encoding="utf-8")
    (git_repo / "tracked.txt").write_text("sk-ant-api03-SYNTHETICTEST0000000000000000\n", encoding="utf-8")
    _git(git_repo, "add", "tracked.txt")
    _git(git_repo, "commit", "-m", "secret")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=git_repo, text=True).strip()
    _git(
        git_repo,
        "tag",
        "-a",
        "-m",
        "Preserve-Producer: hand\nPreserve-Provenance: human\nPreserve-Reason: hand\n"
        "Preserve-Source: test\nPreserve-Run: r\nPreserve-Journal: j\n"
        f"Preserve-Commit: {commit}\n",
        "preserve/pyforge-marshal/87.15/hand-deadbeef",
        commit,
    )
    ref = "refs/tags/preserve/pyforge-marshal/87.15/hand-deadbeef"
    rc = main(["preserve", "push", ref])
    assert rc != 0
    remote = subprocess.run(["git", "ls-remote", "origin", ref], cwd=git_repo, capture_output=True, text=True)
    assert remote.stdout.strip() == ""


def test_preserve_list_json_pipe_close(monkeypatch: pytest.MonkeyPatch):
    _flag_on(monkeypatch, Path("/tmp"))
    monkeypatch.setattr(preserve_module, "repo_root", lambda: Path("/tmp"))
    monkeypatch.setattr(preserve_module, "list_preserves", lambda *_a, **_k: [])

    def broken_print(*_a, **_k):
        raise OSError("broken pipe")

    monkeypatch.setattr("builtins.print", broken_print)
    monkeypatch.setattr(preserve_module, "_suppress_downstream_pipe_close", lambda: None)
    assert (
        preserve_module.run_preserve_list(
            argparse.Namespace(format="json", station=None, story=None, producer=None, state=None)
        )
        == 0
    )
