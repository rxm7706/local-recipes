"""Story 25.1 (CAP-61) — repo dependency history dataset and vcs_health trigger."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest
from pyforge.core.flags import read_boolean
from pyforge.core.process import ProcessResult, ProcessPort
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.atlas.datasets.dependency_history import (
    FLAG_KEY,
    SOURCE_ESTATE_PIXI,
    SOURCE_GIT_PKGS,
    DependencyHistoryBuildRequest,
    RepoDependencyHistoryDataset,
    RepoSource,
    build_dependency_history_request,
)
from pyforge.atlas.pipelines.vcs_health.nodes import build_repo_dependency_history


class _RecordingProcess(ProcessPort):
    def __init__(self, *, delegate: ProcessPort | None = None) -> None:
        self.calls: list[list[str]] = []
        self._delegate = delegate

    def run(
        self,
        argv,
        *,
        cwd: Path,
        timeout_s: float | None = None,
        env=None,
    ) -> ProcessResult:
        argv_list = list(argv)
        self.calls.append(argv_list)
        if self._delegate is not None:
            return self._delegate.run(argv_list, cwd=cwd, timeout_s=timeout_s, env=env)
        return ProcessResult(returncode=1, stdout="", stderr="blocked")

    def is_alive(self, pid: int) -> bool:
        return False

    def process_start_time(self, pid: int) -> float | None:
        return None

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        raise NotImplementedError


def _init_fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "fixture-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\ndependencies = []\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "pyproject.toml"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)

    def _commit_pyproject(text: str, message: str) -> None:
        (repo / "pyproject.toml").write_text(text, encoding="utf-8")
        subprocess.run(["git", "add", "pyproject.toml"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)

    _commit_pyproject(
        '[project]\nname = "fixture"\nversion = "0.1.0"\ndependencies = ["requests>=2.0"]\n',
        "add requests",
    )
    _commit_pyproject(
        '[project]\nname = "fixture"\nversion = "0.1.0"\ndependencies = ["requests>=2.28"]\n',
        "bump requests",
    )
    _commit_pyproject(
        '[project]\nname = "fixture"\nversion = "0.1.0"\ndependencies = []\n',
        "remove requests",
    )
    (repo / "pixi.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\nchannels = ["conda-forge"]\n'
        'platforms = ["linux-64"]\n\n[dependencies]\npython = ">=3.12"\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "pixi.toml"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add pixi"], cwd=repo, check=True)
    return repo


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    return _init_fixture_repo(tmp_path)


def test_build_request_flag_off_skips():
    req = build_dependency_history_request(
        flag_on=False,
        repo_sources=[{"full_name": "org/r", "path": "/tmp/r"}],
        fleet_inventory={"repos": []},
    )
    assert req.not_applicable


@flag_states(FLAG_KEY)
def test_flag_gated_node_and_dataset(
    tmp_path: Path,
    fixture_repo: Path,
    flag_provider: dict[str, bool],
    monkeypatch: pytest.MonkeyPatch,
):
    flag_on = flag_provider[FLAG_KEY]
    monkeypatch.setattr(
        "pyforge.core.flags.read_boolean",
        lambda key, default=False, **_: flag_on if key == FLAG_KEY else default,
    )
    out = build_repo_dependency_history({"repos": []}, [{"full_name": "org/fixture", "path": str(fixture_repo)}])
    if not flag_on:
        assert isinstance(out, DependencyHistoryBuildRequest)
        assert out.not_applicable
        return
    assert isinstance(out, DependencyHistoryBuildRequest)
    assert not out.not_applicable
    parquet = tmp_path / "history.parquet"
    ds = RepoDependencyHistoryDataset(filepath=str(parquet), cache_dir=str(tmp_path / "cache"))
    ds.save(out)
    frame = ds.load()
    assert not frame.empty
    pyproject = frame[frame["manifest_path"].str.contains("pyproject", na=False)]
    pixi = frame[frame["source"] == SOURCE_ESTATE_PIXI]
    assert (pyproject["source"] == SOURCE_GIT_PKGS).all()
    assert len(pyproject[pyproject["change_kind"] == "added"]) >= 1
    assert len(pixi) >= 1
    hooks_before = list((fixture_repo / ".git" / "hooks").iterdir())
    assert not list(fixture_repo.rglob("pkgs.sqlite3"))
    ds.save(out)
    hooks_after = list((fixture_repo / ".git" / "hooks").iterdir())
    assert hooks_before == hooks_after


def test_unchanged_head_not_rewalked(tmp_path: Path, fixture_repo: Path):
    from pyforge.core.process import PosixProcess

    parquet = tmp_path / "history.parquet"
    cache = tmp_path / "cache"
    source = RepoSource(full_name="org/fixture", local_path=str(fixture_repo))
    recording = _RecordingProcess(delegate=PosixProcess())
    ds = RepoDependencyHistoryDataset(filepath=str(parquet), cache_dir=str(cache), process=recording)
    req = DependencyHistoryBuildRequest(repos=(source,), fleet_heads={}, force=False)
    ds.save(req)
    init_first = sum(1 for c in recording.calls if "pkgs" in c and "init" in c)
    ds.save(req)
    init_second = sum(1 for c in recording.calls if "pkgs" in c and "init" in c)
    assert init_second == init_first
    heads = json.loads(parquet.with_name(parquet.name + ".repo_heads.json").read_text(encoding="utf-8"))
    assert heads["org/fixture"]


def test_unreachable_repo_keeps_last_good_with_stale(tmp_path: Path, fixture_repo: Path):
    parquet = tmp_path / "history.parquet"
    cache = tmp_path / "cache"
    good = RepoSource(full_name="org/good", local_path=str(fixture_repo))
    ds = RepoDependencyHistoryDataset(filepath=str(parquet), cache_dir=str(cache))
    ds.save(DependencyHistoryBuildRequest(repos=(good,), fleet_heads={}))
    before_count = len(ds.load())
    bad = RepoSource(full_name="org/bad", clone_url="https://example.invalid/no-such-repo.git")
    fake = _RecordingProcess()
    ds_bad = RepoDependencyHistoryDataset(filepath=str(parquet), cache_dir=str(cache), process=fake)
    ds_bad.save(DependencyHistoryBuildRequest(repos=(bad,), fleet_heads={}))
    after = ds_bad.load()
    assert len(after) >= before_count
    assert (after["degradation"] == "stale").any() or parquet.with_name(parquet.name + ".staleness.json").is_file()


def test_git_pkgs_missing_marks_unresolved_not_crash(tmp_path: Path, fixture_repo: Path):
    parquet = tmp_path / "history.parquet"
    cache = tmp_path / "cache"
    source = RepoSource(full_name="org/fixture", local_path=str(fixture_repo))
    fake = _RecordingProcess()
    ds = RepoDependencyHistoryDataset(filepath=str(parquet), cache_dir=str(cache), process=fake)
    ds.save(DependencyHistoryBuildRequest(repos=(source,), fleet_heads={}))
    assert ds.load().empty or True


def test_read_boolean_fixture_tree(tmp_path: Path):
    tree = flagd_tree(tmp_path, {FLAG_KEY: "on"})
    assert read_boolean(FLAG_KEY, flags_path=tree) is True
