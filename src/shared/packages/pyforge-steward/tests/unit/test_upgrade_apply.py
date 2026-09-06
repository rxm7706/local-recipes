"""Story 14.2 — CAP-2 deliberate apply: branch-first, refuse legacy, preserve custom.

Story 14.6 — CAP-6: the installer is driven on purpose (``--directory`` /
``--modules`` from the manifest, stdin closed, pixi-bin PATH fallback) and an
exit-0 apply that changed nothing is a refusal (trap 12), never a green.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import textwrap
from collections.abc import Sequence
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.upgrade import (
    UpgradeError,
    apply_bmad_core_upgrade,
    assert_clean_tree,
    default_apply_branch,
    default_installer_runner,
    fingerprint_custom_tree,
    format_apply,
    read_installed_modules,
    resolve_installer_environment,
)

_DEFAULT_MODULES: tuple[str, ...] = ("core", "bmm", "skf")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _manifest_text(modules: Sequence[str] | None) -> str:
    """Installed manifest in the real shape: ``modules:`` is a list of mappings.

    ``None`` omits the key entirely; ``()`` writes an empty list.
    """
    lines = ["installation:", "  version: 6.10.0"]
    if modules is not None:
        lines.append("modules:" if modules else "modules: []")
        for name in modules:
            lines.extend(
                [
                    f"  - name: {name}",
                    "    version: 6.10.0",
                    f"    source: {'custom' if name == 'skf' else 'built-in'}",
                ]
            )
    return "\n".join(lines) + "\n"


def _write_repo(
    root: Path,
    *,
    with_legacy_custom: bool = False,
    with_team_custom: bool = True,
    modules: Sequence[str] | None = _DEFAULT_MODULES,
) -> Path:
    """Minimal installed-shaped repo with git history (clean tree)."""
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "bmad-loop-worktree").write_text("#!/bin/sh\n", encoding="utf-8")

    manifest_dir = root / "_bmad" / "_config"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(
        _manifest_text(modules), encoding="utf-8"
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
    no_changes: bool = False,
    record: Path | None = None,
) -> Path:
    """Write a tiny 'bmad-method' stand-in that mutates bmm/core only (unless clobber).

    ``no_changes`` mimics trap 12 (exit 0 having written nothing); ``record``
    dumps the argv the fake received as JSON so tests can assert the exact shape.
    """
    record_str = str(record) if record is not None else ""
    body = textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        import json, pathlib, sys
        repo = pathlib.Path.cwd()
        # Mimic argv contract (CAP-6):
        #   bmad-method install --action update -y --directory <repo> --modules <csv>
        assert sys.argv[1:4] == ["install", "--action", "update"], sys.argv
        assert "-y" in sys.argv
        directory = pathlib.Path(sys.argv[sys.argv.index("--directory") + 1])
        assert directory.resolve() == repo.resolve(), sys.argv
        assert sys.argv[sys.argv.index("--modules") + 1], sys.argv
        if {record_str!r}:
            pathlib.Path({record_str!r}).write_text(json.dumps(sys.argv), encoding="utf-8")
        if {no_changes!r}:
            sys.exit({exit_code})
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
    assert report.installer_cmd == (
        str(installer),
        "install",
        "--action",
        "update",
        "-y",
        "--directory",
        str(repo),
        "--modules",
        "core,bmm,skf",
    )
    assert report.zero_diff is False


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
    record = tmp_path / "argv.json"
    installer = _fake_installer_script(tmp_path / "fake-bmad-method", record=record)
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
    # CAP-6: the fake received --directory <repo> / --modules core,bmm,skf and
    # the payload records the same argv; a real diff is not zero-diff.
    expected_cmd = [
        str(installer),
        "install",
        "--action",
        "update",
        "-y",
        "--directory",
        str(repo),
        "--modules",
        "core,bmm,skf",
    ]
    assert payload["installer_cmd"] == expected_cmd
    assert json.loads(record.read_text(encoding="utf-8")) == expected_cmd
    assert payload["zero_diff"] is False


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
    """Installer runner is the only mutator of bmm/core — steward only invokes it.

    The runner is a pre-14.6 two-positional fake: it must still be accepted and
    called without ``env`` (a keyword would raise TypeError here).
    """
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
    assert calls == [
        (
            "bmad-method",
            "install",
            "--action",
            "update",
            "-y",
            "--directory",
            str(repo),
            "--modules",
            "core,bmm,skf",
        )
    ]
    assert report.custom_identical is True


# ── Story 14.6 / CAP-6 — the installer is driven on purpose ────────────────


def test_read_installed_modules_core_first_and_deduplicated(tmp_path):
    repo = _write_repo(tmp_path / "repo", modules=("bmm", "skf", "core", "bmm"))
    assert read_installed_modules(repo) == ("core", "bmm", "skf")


def test_apply_argv_carries_directory_and_manifest_modules_core_first(tmp_path):
    repo = _write_repo(tmp_path / "repo", modules=("bmm", "skf", "core"))
    record = tmp_path / "argv.json"
    installer = _fake_installer_script(tmp_path / "fake-bmad-method", record=record)

    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_bin=str(installer),
        branch="review/argv",
    )

    expected = (
        str(installer),
        "install",
        "--action",
        "update",
        "-y",
        "--directory",
        str(repo),
        "--modules",
        "core,bmm,skf",
    )
    assert report.installer_cmd == expected
    assert tuple(json.loads(record.read_text(encoding="utf-8"))) == expected
    assert report.installer_exit == 0
    assert report.zero_diff is False
    assert report.to_dict()["installer_cmd"] == list(expected)
    assert any("core,bmm,skf" in n and "trap 13" in n for n in report.notes)


@pytest.mark.parametrize("modules", [None, ()], ids=["missing", "empty"])
def test_apply_refuses_manifest_without_modules_before_branch(tmp_path, modules):
    repo = _write_repo(tmp_path / "repo", modules=modules)
    installer = _fake_installer_script(tmp_path / "fake-bmad-method")
    before_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    with pytest.raises(UpgradeError, match="trap 13"):
        apply_bmad_core_upgrade(
            repo=repo,
            target_version="6.11.0",
            installer_bin=str(installer),
            branch="review/no-modules",
        )

    # Refused before the review branch existed; installer never ran.
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == before_branch
    assert not _git(repo, "branch", "--list", "review/no-modules").stdout.strip()
    assert not (repo / "_bmad" / "bmm" / "updated.txt").exists()


def test_apply_zero_diff_exit_zero_is_a_refusal(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    installer = _fake_installer_script(tmp_path / "fake-bmad-method", no_changes=True)

    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_bin=str(installer),
        branch="review/zero-diff",
    )

    assert report.installer_exit == 0
    assert report.changed_paths == ()
    assert report.zero_diff is True
    assert report.to_dict()["zero_diff"] is True
    note = next(n for n in report.notes if "trap 12" in n)
    assert "exited 0 but changed nothing" in note
    assert "refuse to call this green" in note
    assert "review/zero-diff" in note
    # The review branch is left in place for the operator.
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "review/zero-diff"
    text = format_apply(report, as_json=False)
    assert "zero-diff: REFUSED" in text
    assert "review/zero-diff" in text


def test_apply_non_zero_exit_without_changes_is_not_zero_diff(tmp_path):
    """A non-zero exit already fails through the exit gate — never double-reported as trap 12."""
    repo = _write_repo(tmp_path / "repo")
    installer = _fake_installer_script(
        tmp_path / "fake-bmad-method", no_changes=True, exit_code=2
    )

    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_bin=str(installer),
        branch="review/exit-2",
    )

    assert report.installer_exit == 2
    assert report.changed_paths == ()
    assert report.zero_diff is False
    assert not any("trap 12" in n for n in report.notes)
    assert "zero-diff: REFUSED" not in format_apply(report, as_json=False)


def test_cli_apply_zero_diff_returns_failed_and_names_trap_12(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    installer = _fake_installer_script(tmp_path / "fake-bmad-method", no_changes=True)
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
                "--branch",
                "review/cli-zero-diff",
                "--json",
            ]
        )
    assert rc == EXIT_FAILED
    # ok=False routes the summary to stderr.
    payload = json.loads(err.getvalue())
    assert payload["zero_diff"] is True
    assert payload["installer_exit"] == 0
    assert payload["changed_paths"] == []
    assert any(
        "trap 12" in n and "review/cli-zero-diff" in n for n in payload["notes"]
    )
    assert _git(repo, "branch", "--list", "review/cli-zero-diff").stdout.strip()


def test_cli_apply_zero_diff_text_prints_refused_line(tmp_path):
    repo = _write_repo(tmp_path / "repo")
    installer = _fake_installer_script(tmp_path / "fake-bmad-method", no_changes=True)
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
    assert "zero-diff: REFUSED" in out.getvalue() + err.getvalue()


def test_apply_passes_env_to_keyword_aware_runner_and_prepends_pixi_bin(
    tmp_path, monkeypatch
):
    repo = _write_repo(tmp_path / "repo")
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)
    seen: dict[str, object] = {}

    def runner(cwd: Path, cmd, *, env=None) -> subprocess.CompletedProcess[str]:
        seen["env"] = env
        seen["cmd"] = tuple(cmd)
        (cwd / "_bmad" / "bmm" / "updated.txt").write_text("ok\n", encoding="utf-8")
        return subprocess.CompletedProcess(list(cmd), 0, "", "")

    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_runner=runner,
        branch="review/env",
    )

    pixi_bin = repo / ".pixi" / "envs" / "local-recipes" / "bin"
    env = seen["env"]
    assert isinstance(env, dict)
    assert env["PATH"] == f"{pixi_bin}{os.pathsep}{os.environ['PATH']}"
    note = next(n for n in report.notes if "not on PATH" in n)
    assert str(pixi_bin) in note
    assert "bmad-method" in note and "node" in note
    assert report.zero_diff is False


def test_apply_env_untouched_when_binaries_on_path(tmp_path, monkeypatch):
    repo = _write_repo(tmp_path / "repo")
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: f"/resolved/{name}")
    seen: dict[str, object] = {}

    def runner(cwd: Path, cmd, **kwargs) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs)
        (cwd / "_bmad" / "bmm" / "updated.txt").write_text("ok\n", encoding="utf-8")
        return subprocess.CompletedProcess(list(cmd), 0, "", "")

    report = apply_bmad_core_upgrade(
        repo=repo,
        target_version="6.11.0",
        installer_runner=runner,
        branch="review/env-on-path",
    )

    env = seen["env"]
    assert isinstance(env, dict)
    assert env["PATH"] == os.environ["PATH"]
    assert any("resolved from PATH" in n for n in report.notes)


def test_resolve_installer_environment_pixi_bin_is_derived_from_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    pixi_bin = repo / ".pixi" / "envs" / "local-recipes" / "bin"

    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)
    env, note = resolve_installer_environment(repo, "bmad-method")
    assert env["PATH"].startswith(f"{pixi_bin}{os.pathsep}")
    assert env["PATH"].endswith(os.environ["PATH"])
    assert str(pixi_bin) in note and "bmad-method" in note and "node" in note

    monkeypatch.setattr(
        shutil, "which", lambda name, *a, **k: None if name == "node" else f"/bin/{name}"
    )
    env, note = resolve_installer_environment(repo, "bmad-method")
    assert env["PATH"].startswith(f"{pixi_bin}{os.pathsep}")
    assert "(node)" in note  # only the missing name is listed

    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: f"/bin/{name}")
    env, note = resolve_installer_environment(repo, "bmad-method")
    assert env["PATH"] == os.environ["PATH"]
    assert "resolved from PATH" in note


def test_default_installer_runner_closes_stdin_and_uses_resolved_env(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None)
    env, _note = resolve_installer_environment(repo, "bmad-method")
    pixi_bin = repo / ".pixi" / "envs" / "local-recipes" / "bin"

    seen: dict[str, object] = {}

    def fake_run(args, **kwargs):
        seen["args"] = list(args)
        seen.update(kwargs)
        return subprocess.CompletedProcess(list(args), 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = default_installer_runner(repo, ("bmad-method", "install"), env=env)

    assert result.returncode == 0
    assert seen["args"] == ["bmad-method", "install"]
    assert seen["cwd"] == repo
    assert seen["stdin"] is subprocess.DEVNULL
    assert seen["capture_output"] is True and seen["text"] is True
    run_env = seen["env"]
    assert isinstance(run_env, dict)
    assert run_env["PATH"].startswith(f"{pixi_bin}{os.pathsep}")


def test_read_installed_modules_accepts_bare_string_entries(tmp_path):
    """The installer's manifest writer also allows bare ``- name`` entries."""
    repo = tmp_path / "repo"
    manifest_dir = repo / "_bmad" / "_config"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(
        "installation:\n  version: 6.10.0\n"
        "modules:\n"
        "  - bmm\n"
        "  - name: skf\n    source: custom\n"
        "  - core\n"
        "  - name: bmm\n    source: built-in\n",
        encoding="utf-8",
    )
    assert read_installed_modules(repo) == ("core", "bmm", "skf")


def test_apply_refuses_unresolvable_installer_binary_before_branch(tmp_path):
    """Default runner: a binary steward cannot resolve is a pre-branch refusal, not a crash."""
    repo = _write_repo(tmp_path / "repo")
    missing_bin = tmp_path / "nonexistent" / "bmad-method"
    before_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    with pytest.raises(UpgradeError, match="not found") as excinfo:
        apply_bmad_core_upgrade(
            repo=repo,
            target_version="6.11.0",
            installer_bin=str(missing_bin),
            branch="review/no-binary",
        )

    message = str(excinfo.value)
    assert str(missing_bin) in message
    assert str(repo / ".pixi" / "envs" / "local-recipes" / "bin") in message
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == before_branch
    assert not _git(repo, "branch", "--list", "review/no-binary").stdout.strip()
    assert not (repo / "_bmad" / "bmm" / "updated.txt").exists()
