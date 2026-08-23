"""Story 14.2 — CAP-2 deliberate apply: branch-first, refuse legacy, preserve custom."""

from __future__ import annotations

import io
import json
import subprocess
import textwrap
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.upgrade import (
    UpgradeError,
    apply_bmad_core_upgrade,
    assert_clean_tree,
    default_apply_branch,
    fingerprint_custom_tree,
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _write_repo(
    root: Path,
    *,
    with_legacy_custom: bool = False,
    with_team_custom: bool = True,
) -> Path:
    """Minimal installed-shaped repo with git history (clean tree)."""
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")

    manifest_dir = root / "_bmad" / "_config"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(
        "installation:\n  version: 6.10.0\n", encoding="utf-8"
    )
    (manifest_dir / "skill-manifest.csv").write_text(
        'canonicalId,name\n"bmad-dev-auto","bmad-dev-auto"\n',
        encoding="utf-8",
    )

    scripts = root / "_bmad" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "resolve_config.py").write_text(
        "BMAD_ACTIVE_PROJECT = True\nmarker = '.active-project'\n",
        encoding="utf-8",
    )

    # Installer-owned trees start empty / stub — only installer may write them.
    (root / "_bmad" / "bmm").mkdir(parents=True)
    (root / "_bmad" / "bmm" / ".keep").write_text("owned-by-installer\n", encoding="utf-8")
    (root / "_bmad" / "core").mkdir(parents=True)
    (root / "_bmad" / "core" / ".keep").write_text("owned-by-installer\n", encoding="utf-8")

    custom = root / "_bmad" / "custom"
    custom.mkdir(parents=True)
    if with_team_custom:
        (custom / "config.toml").write_text(
            "# team custom — must survive apply\nteam = true\n", encoding="utf-8"
        )
    if with_legacy_custom:
        (custom / "bmad-dev-auto.toml").write_text(
            "# legacy — shim HALT\n", encoding="utf-8"
        )

    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "test")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture baseline")
    return root


def _fake_installer_script(
    path: Path,
    *,
    clobber_custom: bool = False,
    exit_code: int = 0,
) -> Path:
    """Write a tiny 'bmad-method' stand-in that mutates bmm/core only (unless clobber)."""
    body = textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import pathlib, sys
        repo = pathlib.Path.cwd()
        # Mimic argv contract: bmad-method install --action update -y
        assert sys.argv[1:4] == ["install", "--action", "update"], sys.argv
        assert "-y" in sys.argv
        (repo / "_bmad" / "bmm" / "updated.txt").write_text("from-installer\\n", encoding="utf-8")
        (repo / "_bmad" / "core" / "updated.txt").write_text("from-installer\\n", encoding="utf-8")
        if {clobber_custom!r}:
            custom = repo / "_bmad" / "custom" / "config.toml"
            if custom.is_file():
                custom.write_text("# CLOBBERED\\n", encoding="utf-8")
        sys.exit({exit_code})
        """
    )
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_default_apply_branch_name():
    assert default_apply_branch("6.11.0") == "steward/bmad-core-upgrade-6.11.0"


def test_refuse_dirty_tree(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    (repo / "dirty.txt").write_text("nope\n", encoding="utf-8")
    with pytest.raises(UpgradeError, match="clean working tree"):
        assert_clean_tree(repo)


def test_apply_refuses_legacy_custom_before_branch(tmp_path):
    repo = _write_repo(tmp_path / "repo", with_legacy_custom=True)
    installer = _fake_installer_script(tmp_path / "fake-bmad-method")
    before_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    with pytest.raises(UpgradeError, match="legacy-name"):
        apply_bmad_core_upgrade(
            repo=repo,
            target_version="6.11.0",
            installer_bin=str(installer),
        )

    # Must not have created a review branch or mutated trees.
    after_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert after_branch == before_branch
    assert not (repo / "_bmad" / "bmm" / "updated.txt").exists()


def test_apply_branches_first_runs_installer_preserves_custom(tmp_path):
    repo = _write_repo(tmp_path / "repo", with_legacy_custom=False)
    installer = _fake_installer_script(tmp_path / "fake-bmad-method")
    custom_before = fingerprint_custom_tree(repo)
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_bin=str(installer),
        branch="review/test-apply",
    )

    assert report.branch == "review/test-apply"
    assert report.snapshot_sha == base_sha
    assert report.installer_exit == 0
    assert report.custom_identical is True
    assert report.custom_failure_reason is None
    assert fingerprint_custom_tree(repo) == custom_before

    current = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert current == "review/test-apply"
    assert (repo / "_bmad" / "bmm" / "updated.txt").is_file()
    assert (repo / "_bmad" / "core" / "updated.txt").is_file()
    assert any(p.endswith("updated.txt") for p in report.changed_paths)
    assert report.installer_cmd == (str(installer), "install", "--action", "update", "-y")


def test_apply_reports_when_custom_clobbered(tmp_path):
    repo = _write_repo(tmp_path / "repo", with_legacy_custom=False)
    installer = _fake_installer_script(tmp_path / "fake-bmad-method", clobber_custom=True)

    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_bin=str(installer),
        branch="review/clobber",
    )

    assert report.installer_exit == 0
    assert report.custom_identical is False
    assert any("config.toml" in d for d in report.custom_differs)
    assert report.custom_failure_reason is not None
    assert "NOT byte-identical" in report.custom_failure_reason


def test_apply_refuses_existing_review_branch(tmp_path):
    repo = _write_repo(tmp_path / "repo", with_legacy_custom=False)
    installer = _fake_installer_script(tmp_path / "fake-bmad-method")
    _git(repo, "branch", "review/exists")

    with pytest.raises(UpgradeError, match="already exists"):
        apply_bmad_core_upgrade(
            repo=repo,
            target_version="6.11.0",
            installer_bin=str(installer),
            branch="review/exists",
        )


def test_cli_apply_ok(tmp_path, capsys):
    repo = _write_repo(tmp_path / "repo", with_legacy_custom=False)
    installer = _fake_installer_script(tmp_path / "fake-bmad-method")
    rc = main(
        [
            "upgrade",
            "bmad-core",
            "--target",
            "6.11.0",
            "--apply",
            "--repo-root",
            str(repo),
            "--installer",
            str(installer),
            "--branch",
            "review/cli-apply",
            "--json",
        ]
    )
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["branch"] == "review/cli-apply"
    assert payload["custom_identical"] is True
    assert payload["installer_exit"] == 0


def test_cli_apply_refuses_dirty_tree(tmp_path):
    repo = _write_repo(tmp_path / "repo", with_legacy_custom=False)
    installer = _fake_installer_script(tmp_path / "fake-bmad-method")
    (repo / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(
            [
                "upgrade",
                "bmad-core",
                "--target",
                "6.11.0",
                "--apply",
                "--repo-root",
                str(repo),
                "--installer",
                str(installer),
            ]
        )
    assert rc == EXIT_FAILED
    text = out.getvalue() + err.getvalue()
    assert "clean working tree" in text


def test_cli_apply_refuses_legacy_names_paths(tmp_path):
    repo = _write_repo(tmp_path / "repo", with_legacy_custom=True)
    installer = _fake_installer_script(tmp_path / "fake-bmad-method")
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(
            [
                "upgrade",
                "bmad-core",
                "--target",
                "6.11.0",
                "--apply",
                "--repo-root",
                str(repo),
                "--installer",
                str(installer),
            ]
        )
    assert rc == EXIT_FAILED
    text = out.getvalue() + err.getvalue()
    assert "legacy-name" in text
    assert "bmad-dev-auto.toml" in text


def test_steward_never_writes_bmm_core_itself(tmp_path):
    """Installer runner is the only mutator of bmm/core — steward only invokes it."""
    repo = _write_repo(tmp_path / "repo", with_legacy_custom=False)
    calls: list[tuple[str, ...]] = []

    def runner(cwd: Path, cmd) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(cmd))
        # Installer writes; steward must not have written these already.
        assert not (cwd / "_bmad" / "bmm" / "updated.txt").exists()
        (cwd / "_bmad" / "bmm" / "updated.txt").write_text("ok\n", encoding="utf-8")
        return subprocess.CompletedProcess(list(cmd), 0, "", "")

    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_runner=runner,
        branch="review/sole-writer",
    )
    assert calls == [("bmad-method", "install", "--action", "update", "-y")]
    assert report.custom_identical is True
