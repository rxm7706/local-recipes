"""Story 71.8: preflight scratch lives outside the checkout."""

from __future__ import annotations

import re
import shutil
import signal
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest import mock

import pytest

from pyforge.steward import preflight

_NOOP_INSTALL = lambda _env: 0  # noqa: E731


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _mini_pixi(*tasks: str) -> str:
    body = "[feature.guild-tasks.tasks.pr-preflight-lanes]\ndepends-on = [\n"
    body += ",\n".join(f'  "{name}"' for name in tasks)
    body += "\n]\n\n"
    for name in tasks:
        body += f'[feature.guild-tasks.tasks.{name}]\ncmd = "true"\n\n'
    return body


def _parse_pytest_addopts(addopts: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for match in re.finditer(r"--basetemp=(\S+)", addopts):
        out["basetemp"] = match.group(1)
    for match in re.finditer(r"cache_dir=(\S+)", addopts):
        out["cache_dir"] = match.group(1)
    return out


def _paths_outside_repo(repo: Path, ctx: preflight.LaneRunContext) -> list[Path]:
    repo_resolved = repo.resolve()
    addopts = _parse_pytest_addopts(ctx.env["PYTEST_ADDOPTS"])
    candidates = [
        Path(ctx.env["TMPDIR"]),
        Path(ctx.env["COVERAGE_FILE"]),
        Path(addopts["basetemp"]),
        Path(addopts["cache_dir"]),
        ctx.log_path,
    ]
    resolved = [p.resolve() for p in candidates]
    assert all(not p.is_relative_to(repo_resolved) for p in resolved)
    return resolved


def test_lane_scratch_paths_are_outside_repo_and_distinct(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a", "b"))
    scratch_parent = tmp_path / "scratch"
    contexts: list[preflight.LaneRunContext] = []

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        contexts.append(ctx)
        _paths_outside_repo(repo, ctx)
        return 0

    assert (
        preflight.run_preflight(
            repo,
            jobs=2,
            install_environment=_NOOP_INSTALL,
            run_lane_ctx=run_ctx,
            scratch_parent=scratch_parent,
        )
        == preflight.EXIT_OK
    )
    assert len(contexts) == 2
    paths_a = _paths_outside_repo(repo, contexts[0])
    paths_b = _paths_outside_repo(repo, contexts[1])
    assert paths_a[0] != paths_b[0]
    assert paths_a[1] != paths_b[1]


def test_pytest_sees_no_git_work_tree_outside_checkout(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("lane"))
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    test_file = repo / "test_outside_tree.py"
    _write(
        test_file,
        textwrap.dedent(
            f"""
            import subprocess
            from pathlib import Path

            def test_git_not_inside_work_tree():
                r = subprocess.run(
                    ["git", "-C", {str(tmp_path)!r}, "rev-parse", "--is-inside-work-tree"],
                    capture_output=True,
                    text=True,
                )
                assert r.returncode != 0
            """
        ),
    )

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q", "-p", "no:cacheprovider"],
            env=ctx.env,
            cwd=repo,
        )
        return int(proc.returncode)

    assert (
        preflight.run_preflight(
            repo,
            jobs=1,
            install_environment=_NOOP_INSTALL,
            run_lane_ctx=run_ctx,
            scratch_parent=tmp_path / "scratch",
        )
        == preflight.EXIT_OK
    )


def test_pytest_fails_when_scratch_lives_inside_checkout_mutation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    test_file = repo / "test_outside_tree.py"
    _write(
        test_file,
        textwrap.dedent(
            f"""
            import subprocess

            def test_git_not_inside_work_tree():
                r = subprocess.run(
                    ["git", "-C", {str(tmp_path)!r}, "rev-parse", "--is-inside-work-tree"],
                    capture_output=True,
                    text=True,
                )
                assert r.returncode != 0
            """
        ),
    )
    inside_lane = repo / ".steward" / "preflight" / "old-run" / "lane"
    env = preflight._lane_scratch_env(inside_lane)  # noqa: SLF001 — mutation of pre-71.8 layout
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q", "-p", "no:cacheprovider"],
        env=env,
        cwd=repo,
    )
    assert proc.returncode != 0


def test_green_run_removes_scratch_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a"))
    scratch_parent = tmp_path / "scratch"
    seen_root: list[Path] = []

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        seen_root.append(Path(ctx.env["TMPDIR"]).resolve().parent)
        return 0

    assert (
        preflight.run_preflight(
            repo,
            jobs=1,
            install_environment=_NOOP_INSTALL,
            run_lane_ctx=run_ctx,
            scratch_parent=scratch_parent,
        )
        == preflight.EXIT_OK
    )
    assert len(seen_root) == 1
    assert not seen_root[0].exists()
    assert not (repo / ".steward" / "preflight").exists()


def test_red_run_keeps_scratch_and_names_logs(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a"))
    scratch_parent = tmp_path / "scratch"
    kept: list[Path] = []

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        kept.append(Path(ctx.env["TMPDIR"]).resolve().parent)
        ctx.log_path.write_text("lane log\n", encoding="utf-8")
        return 1

    code = preflight.run_preflight(
        repo,
        jobs=1,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=scratch_parent,
    )
    assert code == preflight.EXIT_LANE_RED
    root = kept[0]
    assert root.is_dir()
    assert (root / "a.log").is_file()
    err = capsys.readouterr().err
    assert "lane logs and scratch kept at" in err
    assert str(root / "a.log") in err


def test_scratch_inside_checkout_exits_2_before_lanes(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a"))
    ran = {"lane": False}

    def run_ctx(_ctx: preflight.LaneRunContext) -> int:
        ran["lane"] = True
        return 0

    code = preflight.run_preflight(
        repo,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=run_ctx,
        scratch_parent=repo / "inside",
    )
    assert code == preflight.EXIT_CONFIG
    assert not ran["lane"]
    assert not list(repo.rglob("pyforge-preflight-*"))
    err = capsys.readouterr().err
    assert "inside the checkout" in err


def test_removal_failure_on_green_run_still_exits_0(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a"))
    scratch_parent = tmp_path / "scratch"

    with mock.patch.object(shutil, "rmtree", side_effect=OSError("busy")):
        code = preflight.run_preflight(
            repo,
            jobs=1,
            install_environment=_NOOP_INSTALL,
            run_lane_ctx=lambda _ctx: 0,
            scratch_parent=scratch_parent,
        )
    assert code == preflight.EXIT_OK
    assert "could not remove scratch" in capsys.readouterr().err


def test_gitignore_covers_legacy_steward_preflight_tree() -> None:
    repo_root = Path(__file__).resolve().parents[6]
    probe = repo_root / ".steward" / "preflight" / "x" / "lane" / "pytest-basetemp" / "t0" / "f.txt"
    proc = subprocess.run(
        ["git", "check-ignore", "-q", str(probe)],
        cwd=repo_root,
        capture_output=True,
    )
    assert proc.returncode == 0


@pytest.mark.skipif(not hasattr(signal, "SIGINT"), reason="SIGINT required")
def test_sigint_keeps_scratch_root(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "pixi.toml", _mini_pixi("a", "b"))
    scratch_parent = tmp_path / "scratch"
    release = __import__("threading").Event()
    roots: list[Path] = []

    def run_ctx(ctx: preflight.LaneRunContext) -> int:
        roots.append(Path(ctx.env["TMPDIR"]).resolve().parent)
        if ctx.lane.task == "a":
            release.wait(timeout=2)
        return 0

    def interrupt() -> None:
        release.set()
        import os

        os.kill(os.getpid(), signal.SIGINT)

    import threading

    timer = threading.Timer(0.3, interrupt)
    timer.start()
    try:
        code = preflight.run_preflight(
            repo,
            jobs=2,
            install_environment=_NOOP_INSTALL,
            run_lane_ctx=run_ctx,
            scratch_parent=scratch_parent,
        )
    finally:
        timer.cancel()
    assert code == preflight.EXIT_INTERRUPT
    assert roots and roots[0].is_dir()
    assert "lane logs and scratch kept at" in capsys.readouterr().err
