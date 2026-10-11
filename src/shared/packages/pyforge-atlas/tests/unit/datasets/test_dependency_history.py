"""Story 25.1 (CAP-61) — repo dependency history dataset and its vcs_health trigger.

Fixture repos are built in the test with ``git`` (offline, non-credentialed). The git-pkgs
tests need the ``git-pkgs`` CLI the ``pyforge-atlas`` env supplies on linux-64; they skip
where it does not resolve. Flag states are driven by two flagd trees (``flagd_tree`` "on"
and "off") read through ``pyforge.core.flags.read_boolean`` -- never a patched reader.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pandas as pd
import pytest
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult
from pyforge.testing_kit.flags import flagd_tree

from pyforge.atlas.datasets.dependency_history import (
    FLAG_KEY,
    HISTORY_COLUMNS,
    SOURCE_ESTATE_PIXI,
    SOURCE_GIT_PKGS,
    STALE,
    UNRESOLVED,
    DependencyHistoryBuildRequest,
    RepoDependencyHistoryDataset,
    RepoSource,
    _parse_pixi_lock,
    _parse_pixi_manifest,
    build_dependency_history_request,
)
from pyforge.atlas.pipelines.vcs_health.nodes import build_repo_dependency_history

MEMBER_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = MEMBER_DIR.parents[2].parent
CONF_SOURCE = MEMBER_DIR / "conf"
FLAGS_TREE = REPO_ROOT / "src" / "platform" / "config" / "flags.json"

needs_git_pkgs = pytest.mark.skipif(shutil.which("git-pkgs") is None, reason="git-pkgs CLI not on PATH")

Intercept = Callable[[list[str]], ProcessResult | None]


class _Proc:
    """A ``PosixProcess`` that records every argv/env and lets a test answer or fail chosen calls."""

    def __init__(self, intercept: Intercept | None = None) -> None:
        self.calls: list[list[str]] = []
        self.envs: list[Mapping[str, str] | None] = []
        self._intercept = intercept
        self._real = PosixProcess()

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_s: float | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        argv_list = list(argv)
        self.calls.append(argv_list)
        self.envs.append(env)
        if self._intercept is not None:
            answer = self._intercept(argv_list)
            if answer is not None:
                return answer
        return self._real.run(argv_list, cwd=cwd, timeout_s=timeout_s, env=env)

    def count(self, *words: str) -> int:
        return sum(1 for call in self.calls if all(word in call for word in words))


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def _commit(repo: Path, files: Mapping[str, str], message: str) -> None:
    for name, text in files.items():
        (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", *files)
    _git(repo, "commit", "-q", "-m", message)


_PYPROJECT = '[project]\nname = "fixture"\nversion = "0.1.0"\ndependencies = [{deps}]\n'
_PIXI = (
    '[workspace]\nname = "fixture"\nchannels = ["conda-forge"]\nplatforms = ["linux-64"]\n\n'
    '[dependencies]\npython = ">=3.12"\n'
)


def _init_fixture_repo(root: Path) -> Path:
    """Commits: init, add requests, bump requests, remove requests (pyproject), add pixi.toml."""
    repo = root / "fixture-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "commit.gpgsign", "false")
    _commit(repo, {"pyproject.toml": _PYPROJECT.format(deps="")}, "init")
    _commit(repo, {"pyproject.toml": _PYPROJECT.format(deps='"requests>=2.0"')}, "add requests")
    _commit(repo, {"pyproject.toml": _PYPROJECT.format(deps='"requests>=2.28"')}, "bump requests")
    _commit(repo, {"pyproject.toml": _PYPROJECT.format(deps="")}, "remove requests")
    _commit(repo, {"pixi.toml": _PIXI}, "add pixi")
    return repo


def _commits(repo: Path) -> list[tuple[str, int]]:
    out = _git(repo, "log", "--reverse", "--format=%H %ct")
    return [(sha, int(ts)) for sha, ts in (line.split() for line in out.splitlines())]


def _tree_digest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _dataset(tmp_path: Path, process: _Proc | None = None) -> RepoDependencyHistoryDataset:
    return RepoDependencyHistoryDataset(
        filepath=str(tmp_path / "store" / "repo_dependency_history"),
        cache_dir=str(tmp_path / "cache"),
        process=process,
    )


def _state(tmp_path: Path) -> dict[str, dict[str, str]]:
    path = tmp_path / "store" / "repo_dependency_history" / ".repo_state.json"
    return json.loads(path.read_text(encoding="utf-8"))["repos"]


def _staleness(tmp_path: Path) -> dict | None:
    path = tmp_path / "store" / "repo_dependency_history" / ".staleness.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _change_set(frame: pd.DataFrame) -> set[tuple[str, ...]]:
    cols = [
        "repo_full_name",
        "commit_sha",
        "manifest_path",
        "manifest_scope",
        "ecosystem",
        "name",
        "requirement_before",
        "requirement_after",
        "change_kind",
        "source",
        "degradation",
    ]
    return {tuple(str(v) for v in row) for row in frame[cols].itertuples(index=False)}


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    return _init_fixture_repo(tmp_path)


@pytest.fixture
def private_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Route ``tempfile`` (git-pkgs' throwaway database) under the test's own directory."""
    scratch = tmp_path / "system-tmp"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    return scratch


# --- AC1 / AC2: one row per change, nothing written into the scanned repo -------------------


@needs_git_pkgs
def test_ac1_exact_rows_for_pyproject_and_pixi_history(tmp_path: Path, fixture_repo: Path, private_tmp: Path):
    ds = _dataset(tmp_path)
    ds.save(DependencyHistoryBuildRequest(repos=(RepoSource("org/fixture", local_path=str(fixture_repo)),)))
    frame = ds.load()

    assert list(frame.columns) == list(HISTORY_COLUMNS)
    (_, _), (add_sha, add_ts), (bump_sha, _), (remove_sha, _), (pixi_sha, pixi_ts) = _commits(fixture_repo)
    name = "org/fixture"
    assert _change_set(frame) == {
        (name, add_sha, "pyproject.toml", "", "pypi", "requests", "", ">=2.0", "added", SOURCE_GIT_PKGS, ""),
        (name, bump_sha, "pyproject.toml", "", "pypi", "requests", ">=2.0", ">=2.28", "modified", SOURCE_GIT_PKGS, ""),
        (name, remove_sha, "pyproject.toml", "", "pypi", "requests", ">=2.28", "", "removed", SOURCE_GIT_PKGS, ""),
        (name, pixi_sha, "pixi.toml", "dependencies", "conda", "python", "", ">=3.12", "added", SOURCE_ESTATE_PIXI, ""),
    }
    times = dict(zip(frame["commit_sha"], frame["commit_time"], strict=True))
    assert times[add_sha] == add_ts and times[pixi_sha] == pixi_ts
    assert not frame.isna().any().any()
    # partitioned by repo: one file per repo under the store directory
    store = tmp_path / "store" / "repo_dependency_history"
    assert sorted(p.name for p in store.glob("*.parquet")) == ["org@fixture.parquet"]


@needs_git_pkgs
def test_ac2_scanned_repo_untouched_and_no_database_left(tmp_path: Path, fixture_repo: Path, private_tmp: Path):
    before = _tree_digest(fixture_repo)  # taken BEFORE the first build
    hooks_before = _tree_digest(fixture_repo / ".git" / "hooks")
    proc = _Proc()
    ds = _dataset(tmp_path, proc)
    request = DependencyHistoryBuildRequest(repos=(RepoSource("org/fixture", local_path=str(fixture_repo)),))
    ds.save(request)
    ds.save(DependencyHistoryBuildRequest(repos=request.repos, force=True))  # a second full walk

    assert proc.count("pkgs", "init") == 2
    assert _tree_digest(fixture_repo) == before
    assert _tree_digest(fixture_repo / ".git" / "hooks") == hooks_before
    assert not list(tmp_path.rglob("*.sqlite*")), "a git-pkgs database (or its -wal/-shm) was left behind"
    assert not list(private_tmp.iterdir()), "the throwaway database directory was not removed"
    db_paths = [env["GIT_PKGS_DB"] for env in proc.envs if env and "GIT_PKGS_DB" in env]
    assert db_paths and all(Path(p).is_relative_to(private_tmp) for p in db_paths)
    # git-pkgs ran against Atlas's own clone, never the working copy
    pkgs_targets = {call[call.index("-C") + 1] for call in proc.calls if "pkgs" in call and "-C" in call}
    assert pkgs_targets == {str((tmp_path / "cache" / "org@fixture").resolve())}


@needs_git_pkgs
def test_ac3_git_pkgs_rows_need_no_duckdb_extension(
    tmp_path: Path, fixture_repo: Path, private_tmp: Path, monkeypatch: pytest.MonkeyPatch
):
    """No DuckDB connection (so no `INSTALL sqlite`): rows come from git-pkgs' own JSON."""
    import duckdb

    def _refuse(*_args, **_kwargs):
        raise AssertionError("dependency history opened a DuckDB connection")

    monkeypatch.setattr(duckdb, "connect", _refuse)
    ds = _dataset(tmp_path)
    ds.save(DependencyHistoryBuildRequest(repos=(RepoSource("org/fixture", local_path=str(fixture_repo)),)))
    frame = ds.load()
    assert (frame["source"] == SOURCE_GIT_PKGS).sum() == 3
    assert _state(tmp_path)["org/fixture"]["degradation"] == ""


# --- AC4: an unmoved head is not re-walked -----------------------------------------------------


@needs_git_pkgs
def test_ac4_unchanged_head_not_rewalked(tmp_path: Path, fixture_repo: Path, private_tmp: Path):
    proc = _Proc()
    ds = _dataset(tmp_path, proc)
    request = DependencyHistoryBuildRequest(repos=(RepoSource("org/fixture", local_path=str(fixture_repo)),))
    ds.save(request)
    first = (proc.count("pkgs", "init"), proc.count("log", "--first-parent"))
    ds.save(request)
    assert (proc.count("pkgs", "init"), proc.count("log", "--first-parent")) == first == (1, 2)
    assert _state(tmp_path)["org/fixture"]["head"] == _commits(fixture_repo)[-1][0]

    _commit(fixture_repo, {"pixi.toml": _PIXI + 'numpy = ">=2"\n'}, "add numpy")
    ds.save(request)  # the head moved: walked again, and the new change lands
    assert proc.count("pkgs", "init") == 2
    added = ds.load().query("name == 'numpy'")
    assert list(added["change_kind"]) == ["added"]


# --- AC5: unreachable repos keep last-good and read `stale`; the run never fails ---------------


def _bare_remote(fixture_repo: Path, where: Path) -> Path:
    subprocess.run(["git", "clone", "-q", "--bare", str(fixture_repo), str(where)], check=True)
    return where


@needs_git_pkgs
def test_ac5_built_repo_whose_remote_vanishes_reads_stale_then_recovers(
    tmp_path: Path, fixture_repo: Path, private_tmp: Path
):
    remote = _bare_remote(fixture_repo, tmp_path / "remote.git")
    ds = _dataset(tmp_path)
    request = DependencyHistoryBuildRequest(repos=(RepoSource("org/fixture", clone_url=f"file://{remote}"),))
    ds.save(request)
    good = ds.load()
    assert len(good) == 4 and set(good["degradation"]) == {""}

    shutil.rmtree(remote)  # the remote of an already-built repo is gone; the head has not moved
    ds.save(request)
    stale = ds.load()
    assert len(stale) == len(good), "the last-good partition was not kept"
    assert set(stale["degradation"]) == {STALE}
    assert _state(tmp_path)["org/fixture"]["degradation"] == STALE
    marker = _staleness(tmp_path)
    assert marker is not None and marker["stale"] is True and marker["repos"] == {"org/fixture": STALE}

    _bare_remote(fixture_repo, remote)  # reachable again, head unchanged
    ds.save(request)
    recovered = ds.load()
    assert set(recovered["degradation"]) == {""}
    assert _staleness(tmp_path) is None


@needs_git_pkgs
def test_ac5_never_cloned_unreachable_repo_reads_stale_and_others_build(
    tmp_path: Path, fixture_repo: Path, private_tmp: Path
):
    ds = _dataset(tmp_path)
    ds.save(
        DependencyHistoryBuildRequest(
            repos=(
                RepoSource("org/gone", clone_url=f"file://{tmp_path / 'no-such-remote.git'}"),
                RepoSource("org/fixture", local_path=str(fixture_repo)),
            )
        )
    )
    state = _state(tmp_path)
    assert state["org/gone"]["degradation"] == STALE
    assert state["org/fixture"]["degradation"] == ""
    assert _staleness(tmp_path)["repos"] == {"org/gone": STALE}
    assert set(ds.load()["repo_full_name"]) == {"org/fixture"}


@needs_git_pkgs
def test_process_error_on_one_repo_never_aborts_the_others(tmp_path: Path, fixture_repo: Path, private_tmp: Path):
    def _hang(argv: list[str]) -> ProcessResult | None:
        if "clone" in argv and any("hung" in part for part in argv):
            raise ProcessError("timed out after 900s")
        return None

    ds = _dataset(tmp_path, _Proc(_hang))
    ds.save(
        DependencyHistoryBuildRequest(
            repos=(
                RepoSource("org/hung", clone_url="https://example.invalid/hung.git"),
                RepoSource("org/fixture", local_path=str(fixture_repo)),
            )
        )
    )
    state = _state(tmp_path)
    assert state["org/hung"]["degradation"] == STALE and "timed out" in state["org/hung"]["reason"]
    assert (ds.load()["repo_full_name"] == "org/fixture").sum() == 4


def test_git_missing_entirely_is_stale_not_a_crash(tmp_path: Path, fixture_repo: Path):
    def _no_git(argv: list[str]) -> ProcessResult | None:
        raise ProcessError(f"executable not found: {argv[0]}")

    ds = _dataset(tmp_path, _Proc(_no_git))
    ds.save(DependencyHistoryBuildRequest(repos=(RepoSource("org/fixture", local_path=str(fixture_repo)),)))
    assert _state(tmp_path)["org/fixture"]["degradation"] == STALE
    assert ds.load().empty


# --- the source is validated before any path or argv is built ---------------------------------


@pytest.mark.parametrize("full_name", ["..", "../x", "a/..", ".", "a/b/c", "noslash", "a/b c"])
def test_invalid_full_name_is_unresolved_and_touches_nothing(tmp_path: Path, full_name: str):
    keep = tmp_path / "keep.txt"
    keep.write_text("sibling data", encoding="utf-8")
    (tmp_path / "cache").mkdir()
    proc = _Proc()
    ds = _dataset(tmp_path, proc)
    ds.save(DependencyHistoryBuildRequest(repos=(RepoSource(full_name, clone_url="https://example.invalid/r.git"),)))
    assert keep.read_text(encoding="utf-8") == "sibling data"
    assert (tmp_path / "cache").is_dir()
    assert proc.calls == []
    assert _state(tmp_path)[full_name]["degradation"] == UNRESOLVED


@pytest.mark.parametrize(
    "url",
    ["--upload-pack=touch /tmp/pwned", "ext::sh -c touch% /tmp/pwned", "http://plain.example/r.git", "-u x"],
)
def test_disallowed_clone_url_is_unresolved_and_never_reaches_git(tmp_path: Path, url: str):
    proc = _Proc()
    ds = _dataset(tmp_path, proc)
    ds.save(DependencyHistoryBuildRequest(repos=(RepoSource("org/r", clone_url=url),)))
    assert proc.calls == []
    assert _state(tmp_path)["org/r"]["degradation"] == UNRESOLVED


def test_clone_url_follows_end_of_options_marker(tmp_path: Path):
    url = "https://example.invalid/org/r.git"

    def _fail_clone(argv: list[str]) -> ProcessResult | None:
        return ProcessResult(returncode=128, stdout="", stderr="unreachable") if "clone" in argv else None

    proc = _Proc(_fail_clone)
    _dataset(tmp_path, proc).save(DependencyHistoryBuildRequest(repos=(RepoSource("org/r", clone_url=url),)))
    (clone,) = [call for call in proc.calls if "clone" in call]
    assert clone[clone.index("--") + 1] == url
    assert clone[-1] == str((tmp_path / "cache" / "org@r").resolve())


# --- git-pkgs absent or out of range: `unresolved`, pixi rows kept, re-walked next run ---------


def _fake_version(version_line: str | None) -> Intercept:
    def _answer(argv: list[str]) -> ProcessResult | None:
        if argv[:2] == ["git", "pkgs"]:
            if version_line is None:
                return ProcessResult(returncode=1, stdout="", stderr="git: 'pkgs' is not a git command")
            if argv[2:] == ["--version"]:
                return ProcessResult(returncode=0, stdout=version_line, stderr="")
        return None

    return _answer


@pytest.mark.parametrize(
    ("version_line", "why"),
    [(None, "not installed"), ("git-pkgs version 0.22.1\n", "outside its tested range")],
)
def test_git_pkgs_absent_or_out_of_range_is_unresolved_and_keeps_pixi_rows(
    tmp_path: Path, fixture_repo: Path, version_line: str | None, why: str
):
    proc = _Proc(_fake_version(version_line))
    ds = _dataset(tmp_path, proc)
    ds.save(DependencyHistoryBuildRequest(repos=(RepoSource("org/fixture", local_path=str(fixture_repo)),)))
    frame = ds.load()
    assert set(frame["source"]) == {SOURCE_ESTATE_PIXI}
    assert set(frame["degradation"]) == {UNRESOLVED}
    entry = _state(tmp_path)["org/fixture"]
    assert entry["degradation"] == UNRESOLVED and why in entry["reason"] and entry["head"] == ""
    assert proc.count("pkgs", "init") == 0
    assert proc.count("log", "--first-parent") == 2  # the head was not recorded ...
    ds.save(DependencyHistoryBuildRequest(repos=(RepoSource("org/fixture", local_path=str(fixture_repo)),)))
    assert proc.count("log", "--first-parent") == 4  # ... so the repo is walked again


@needs_git_pkgs
def test_git_pkgs_in_range_version_is_accepted(tmp_path: Path, fixture_repo: Path, private_tmp: Path):
    proc = _Proc(_fake_version("git-pkgs version 0.21.7\n"))
    ds = _dataset(tmp_path, proc)
    ds.save(DependencyHistoryBuildRequest(repos=(RepoSource("org/fixture", local_path=str(fixture_repo)),)))
    assert _state(tmp_path)["org/fixture"]["degradation"] == ""
    assert proc.count("pkgs", "--version") == 1


# --- the estate pixi parser ------------------------------------------------------------------


def test_pixi_manifest_reads_every_dependency_table_with_its_scope():
    text = """
[workspace]
name = "w"
[dependencies]
python = ">=3.12"
[pypi-dependencies]
rich = { version = ">=13" }
[target.linux-64.dependencies]
git = "*"
[feature.docs.dependencies]
sphinx = { version = ">=8", channel = "conda-forge" }
[feature.docs.pypi-dependencies]
furo = "==2024.8.6"
[feature.docs.target.win-64.host-dependencies]
m2w64-toolchain = "*"
[package.run-dependencies]
pandas = ">=2"
[tasks.lint]
cmd = "ruff"
"""
    assert _parse_pixi_manifest(text) == {
        ("dependencies", "conda", "python"): ">=3.12",
        ("pypi-dependencies", "pypi", "rich"): ">=13",
        ("target.linux-64.dependencies", "conda", "git"): "*",
        ("feature.docs.dependencies", "conda", "sphinx"): '{"channel": "conda-forge", "version": ">=8"}',
        ("feature.docs.pypi-dependencies", "pypi", "furo"): "==2024.8.6",
        ("feature.docs.target.win-64.host-dependencies", "conda", "m2w64-toolchain"): "*",
        ("package.run-dependencies", "conda", "pandas"): ">=2",
    }
    assert _parse_pixi_manifest("[dependencies\npython =") is None


def test_pixi_manifest_reads_the_estate_manifest():
    deps = _parse_pixi_manifest((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    assert deps is not None
    assert len(deps) > 300, "only a fraction of the estate's declarations was read"
    assert deps[("feature.pyforge-atlas.target.linux-64.dependencies", "conda", "git-pkgs")] == ">=0.21.0,<0.22"
    assert any(scope.endswith("pypi-dependencies") for scope, _, _ in deps)
    assert not any(value.startswith("{'") for value in deps.values()), "a table spec stored as a Python repr"
    assert any(value.startswith('{"path": ') for value in deps.values())


_LOCK_V1 = """version: 6
environments:
  default:
    packages:
      linux-64:
      - conda: https://conda.anaconda.org/conda-forge/linux-64/python-3.12.1-h1_0.conda
packages:
- conda: https://conda.anaconda.org/conda-forge/linux-64/python-3.12.1-h1_0.conda
  sha256: aa
- conda: https://conda.anaconda.org/conda-forge/noarch/tzdata-2024a-h0c530f3_0.tar.bz2
- pypi: https://files.pythonhosted.org/packages/requests-2.31.0-py3-none-any.whl
  name: requests
  version: 2.31.0
"""


def test_pixi_lock_resolves_names_and_versions():
    assert _parse_pixi_lock(_LOCK_V1) == {
        ("", "conda", "python"): "3.12.1",
        ("", "conda", "tzdata"): "2024a",
        ("", "pypi", "requests"): "2.31.0",
    }
    two_pythons = _LOCK_V1 + "- conda: https://x/linux-64/python-3.9.18-h2_0.conda\n"
    assert _parse_pixi_lock(two_pythons)[("", "conda", "python")] == "3.9.18,3.12.1"
    assert _parse_pixi_lock("packages: [unclosed") is None


def test_pixi_history_walks_features_pypi_and_the_lock(tmp_path: Path, fixture_repo: Path):
    _commit(
        fixture_repo,
        {
            "pixi.toml": _PIXI + '\n[feature.docs.pypi-dependencies]\nfuro = "==2024.8.6"\n',
            "pixi.lock": _LOCK_V1,
        },
        "feature + lock",
    )
    _commit(
        fixture_repo,
        {
            "pixi.toml": _PIXI + '\n[feature.docs.pypi-dependencies]\nfuro = "==2025.1.1"\n',
            "pixi.lock": _LOCK_V1.replace("2.31.0", "2.32.3"),
        },
        "bump",
    )
    # git-pkgs reported absent: the pixi half must still land
    ds = _dataset(tmp_path, _Proc(_fake_version(None)))
    ds.save(DependencyHistoryBuildRequest(repos=(RepoSource("org/fixture", local_path=str(fixture_repo)),)))
    frame = ds.load()
    pixi = {
        (
            r.manifest_path,
            r.manifest_scope,
            r.ecosystem,
            r.name,
            r.requirement_before,
            r.requirement_after,
            r.change_kind,
        )
        for r in frame.itertuples(index=False)
    }
    assert ("pixi.toml", "feature.docs.pypi-dependencies", "pypi", "furo", "", "==2024.8.6", "added") in pixi
    assert (
        "pixi.toml",
        "feature.docs.pypi-dependencies",
        "pypi",
        "furo",
        "==2024.8.6",
        "==2025.1.1",
        "modified",
    ) in pixi
    assert ("pixi.lock", "", "conda", "python", "", "3.12.1", "added") in pixi
    assert ("pixi.lock", "", "pypi", "requests", "2.31.0", "2.32.3", "modified") in pixi
    assert set(frame["source"]) == {SOURCE_ESTATE_PIXI}


# --- the flag: two flagd trees, read through read_boolean ---------------------------------------


@pytest.mark.parametrize("state", ["on", "off"])
def test_flag_two_states_gate_the_node_and_the_clone(
    tmp_path: Path, fixture_repo: Path, monkeypatch: pytest.MonkeyPatch, state: str
):
    assert FLAG_KEY == "pyforge.atlas.dependency_history"
    if state == "on":
        tree = flagd_tree(tmp_path, {FLAG_KEY: "on"}, name="flags-on.json")
    else:
        tree = flagd_tree(tmp_path, {FLAG_KEY: "off"}, name="flags-off.json")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)

    request = build_repo_dependency_history([{"full_name": "org/fixture", "path": str(fixture_repo)}])
    ds = _dataset(tmp_path, _Proc(_fake_version(None)))
    ds.save(request)
    if state == "off":
        assert request.not_applicable and request.repos == ()
        assert not (tmp_path / "cache").exists(), "a flag-OFF run cloned"
        assert not (tmp_path / "store").exists()
        return
    assert not request.not_applicable
    assert request.repos == (RepoSource("org/fixture", local_path=str(fixture_repo)),)
    assert (tmp_path / "cache" / "org@fixture" / ".git").is_dir()
    assert not ds.load().empty


@pytest.mark.parametrize(("environment", "expected"), [("dev", "on"), ("staging", "on"), ("production", "off")])
def test_flag_renders_the_spec_defaults_per_environment(environment: str, expected: str):
    from pyforge.core.flags import render

    rendered = json.loads(render(environment, flags_path=FLAGS_TREE))
    assert rendered["flags"][FLAG_KEY]["defaultVariant"] == expected


def test_build_request_flag_off_skips():
    req = build_dependency_history_request(flag_on=False, repo_sources=[{"full_name": "org/r", "path": "/tmp/r"}])
    assert req.not_applicable and req.repos == ()


# --- AC6 through Kedro: flag OFF, no Warden inventory file, the node still runs -----------------


def test_ac6_flag_off_kedro_run_needs_no_inventory_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from kedro.config import OmegaConfigLoader
    from kedro.io import DataCatalog, MemoryDataset
    from kedro.runner import SequentialRunner

    from pyforge.atlas.pipelines.vcs_health.pipeline import create_pipeline
    from pyforge.atlas.settings import CONFIG_LOADER_ARGS

    data_root = tmp_path / "data"
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", str(data_root))
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {FLAG_KEY: "off"})))
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    loader = OmegaConfigLoader(conf_source=str(CONF_SOURCE), **{**CONFIG_LOADER_ARGS, "default_run_env": "base"})
    catalog_config = loader["catalog"]
    parameters = loader["parameters"]

    pipe = create_pipeline().only_nodes("build_repo_dependency_history")
    catalog = DataCatalog.from_config(
        {name: catalog_config[name] for name in pipe.datasets() if name in catalog_config}
    )
    for name in pipe.inputs():
        if name.startswith("params:"):
            value = parameters
            for part in name.removeprefix("params:").split("."):
                value = value[part]
            catalog[name] = MemoryDataset(value)

    assert not (data_root / "stores" / "warden_fleet_inventory.json").exists()
    SequentialRunner().run(pipe, catalog)
    assert not (data_root / "cache").exists()
    assert not (data_root / "primary" / "repo_dependency_history").exists()
