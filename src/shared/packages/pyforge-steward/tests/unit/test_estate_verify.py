"""Story 100.4 — estate verify (AC1–AC6; faked git/pixi only)."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
import pytest
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

flag_provider = make_flag_provider_fixture()

from pyforge.steward.estate import ESTATE_FLAG_KEY, SCHEMA_RESOURCE
from pyforge.steward.estate_verify import (
    DEFAULT_TIER,
    GUILD_SIZE_BOUND_MB,
    VerifyDeps,
    run_verify,
)
from pyforge.steward.preflight_ci import LaneVerdict, Selection

FIXTURE_PIXI = """
[project]
name = "estate-verify-fixture"

[environments]
pyforge-guild = ["guild"]
pyforge-core = ["core"]
pyforge-testing-kit = ["kit"]
pyforge-atlas = ["atlas"]
pyforge-doctor = ["doctor"]
pyforge-herald = ["herald"]
pyforge-marshal = ["marshal"]
pyforge-mason = ["mason"]
pyforge-scribe = ["scribe"]
pyforge-steward = ["steward"]
pyforge-warden = ["warden"]
platform-ci-test = ["platform"]
pyforge-foundry-full = ["full"]
dbgpt-sidecar = { features = ["sidecar"], platforms = ["linux-64"] }
osx = { features = ["osx"], platforms = ["osx-arm64-min"] }
local-recipes = ["recipes"]

[feature.recipes.tasks.verify-env]
cmd = "echo verify-env"

[feature.guild-tasks.tasks.pr-preflight-lanes]
depends-on = ["lint-types", "guild-container"]

[feature.guild-tasks.tasks.lint-types]
cmd = "echo lint-types"

[feature.guild-tasks.tasks.guild-container]
cmd = "echo guild-container"
"""


@dataclass
class FakeProc:
    args: list[str]
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


@dataclass
class RecordingRunner:
    root: Path | None = None
    calls: list[tuple[list[str], Path]] = field(default_factory=list)
    responses: dict[str, FakeProc] = field(default_factory=dict)
    du_mb: int = 512

    def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
        self.calls.append((list(argv), cwd))
        key = " ".join(argv)
        if argv[:2] == ["du", "-sm"]:
            return FakeProc(argv, 0, f"{self.du_mb}\t.\n", "")
        for prefix, proc in self.responses.items():
            if prefix in key:
                return FakeProc(argv, proc.returncode, proc.stdout, proc.stderr)
        if argv[:4] == ["git", "worktree", "add", "--detach"]:
            wt = Path(argv[4])
            wt.mkdir(parents=True, exist_ok=True)
            if self.root is not None:
                for rel in ("pixi.toml", "pixi.lock"):
                    shutil.copy2(self.root / rel, wt / rel)
                for sub in ("_bmad", "scripts", "docs"):
                    src = self.root / sub
                    if src.is_dir():
                        shutil.copytree(src, wt / sub, dirs_exist_ok=True)
            return FakeProc(argv, 0, "", "")
        if argv[:3] == ["git", "worktree", "remove"]:
            return FakeProc(argv, 0, "", "")
        if argv[:3] == ["pixi", "lock", "--check"]:
            return FakeProc(argv, 0, "", "")
        if argv[:3] == ["pixi", "install", "--frozen"]:
            return FakeProc(argv, 0, "", "")
        if argv[:3] == ["pixi", "run", "--frozen"]:
            return FakeProc(argv, 0, "", "")
        if "pin_policy_check.py" in key and "--fan-out" in key:
            return FakeProc(argv, 0, "[]", "")
        return FakeProc(argv, 0, "", "")


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pixi.toml").write_text(FIXTURE_PIXI, encoding="utf-8")
    (root / "pixi.lock").write_text("version: 6\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "docs/governance").mkdir(parents=True)
    (root / "docs/governance/realization-register.yaml").write_text(
        "version: 1\nrows:\n"
        "  - package: bmad-method\n    env: pyforge-guild\n    class: installer-tree\n"
        "    probe:\n      expect: locked-version\n      path: _bmad/_config/manifest.yaml\n"
        "      key: installation.version\n    test: [bmad-drift-check]\n",
        encoding="utf-8",
    )
    (root / "_bmad/_config").mkdir(parents=True)
    (root / "_bmad/_config/manifest.yaml").write_text("installation:\n  version: 6.12.0\n", encoding="utf-8")
    (root / ".steward/estate-refresh").mkdir(parents=True)
    (root / ".github/workflows").mkdir(parents=True)
    (root / ".github/workflows/lint-types.yml").write_text(
        "on:\n  pull_request:\n    paths:\n      - 'pixi.toml'\n"
        "jobs:\n  lint:\n    steps:\n      - run: pixi run -e pyforge-guild lint-types\n",
        encoding="utf-8",
    )
    (root / ".github/workflows/station-tests.yml").write_text(
        "on:\n  pull_request:\n    paths:\n      - 'pixi.toml'\n"
        "jobs:\n  guild-container:\n    steps:\n      - run: pixi run -e pyforge-guild guild-container\n",
        encoding="utf-8",
    )
    return root


def _deps(root: Path, runner: RecordingRunner, **kwargs: object) -> VerifyDeps:
    fields = {
        "root": root,
        "runner": runner,
        "head_sha": lambda: "abc123",
        "platform": lambda: "linux-64",
        "flag_on": lambda: True,
        "enforce_require": False,
    }
    fields.update(kwargs)
    return VerifyDeps(**fields)  # type: ignore[arg-type]


def _worktree(root: Path) -> Path:
    return root / ".steward/estate-verify/worktree"


def _install_envs(runner: RecordingRunner, root: Path) -> list[str]:
    wt = _worktree(root)
    return [argv[4] for argv, cwd in runner.calls if argv[:3] == ["pixi", "install", "--frozen"] and cwd == wt]


@flag_states("pyforge.steward.estate_refresh")
def test_verify_refuses_when_estate_refresh_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag_provider: dict[str, bool]
) -> None:
    root = _fixture_root(tmp_path)
    monkeypatch.setattr("pyforge.steward.estate_realize._locked_version", lambda *a, **k: "6.12.0")
    on = flag_provider["pyforge.steward.estate_refresh"]
    runner = RecordingRunner(root=root)
    result = run_verify(
        _deps(root, runner, flag_on=lambda: on),
        env_filter=None,
        lane_filter=None,
        probe_filter=None,
        all_envs=False,
        keep=False,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    if on:
        assert "refused" not in result.summary
        assert runner.calls[0][0][:4] == ["git", "worktree", "add", "--detach"]
    else:
        assert not result.ok
        assert ESTATE_FLAG_KEY in result.summary
        assert not runner.calls


def test_format_status_platforms_and_load_latest(tmp_path: Path) -> None:
    from pyforge.steward.estate_verify import format_status_platforms, load_latest_verify_platforms

    root = _fixture_root(tmp_path)
    journal_dir = root / ".steward/estate-refresh"
    journal_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "verify": {
            "platforms": {
                "linux-64": {"lock_sha": "abc", "verdict": "ok"},
                "osx-arm64": {"lock_sha": "def", "verdict": "lock-solved"},
            }
        }
    }
    (journal_dir / "2026-10-13.json").write_text(json.dumps(doc), encoding="utf-8")
    loaded = load_latest_verify_platforms(root)
    assert loaded["linux-64"]["verdict"] == "ok"
    lines = format_status_platforms(doc)
    assert any("linux-64" in line and "abc" in line for line in lines)


def test_worktree_first_then_default_tier_installs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_root(tmp_path)
    monkeypatch.setattr("pyforge.steward.estate_realize._locked_version", lambda *a, **k: "6.12.0")
    runner = RecordingRunner(root=root)
    result = run_verify(
        _deps(root, runner),
        env_filter=None,
        lane_filter=None,
        probe_filter=None,
        all_envs=False,
        keep=False,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    assert result.ok
    assert runner.calls[0][0][:4] == ["git", "worktree", "add", "--detach"]
    installed = _install_envs(runner, root)
    for env in DEFAULT_TIER:
        assert env in installed


def test_no_install_argv_targets_working_tree(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner(root=root)
    run_verify(
        _deps(root, runner),
        env_filter="pyforge-guild",
        lane_filter=None,
        probe_filter=None,
        all_envs=False,
        keep=False,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    wt = _worktree(root)
    for argv, cwd in runner.calls:
        if argv[:3] == ["pixi", "install", "--frozen"]:
            assert cwd == wt
            assert cwd != root


def test_platform_excluded_env_is_lock_solved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_root(tmp_path)
    monkeypatch.setattr("pyforge.steward.estate_realize._locked_version", lambda *a, **k: "6.12.0")
    runner = RecordingRunner(root=root)
    result = run_verify(
        _deps(root, runner),
        env_filter=None,
        lane_filter=None,
        probe_filter=None,
        all_envs=True,
        keep=False,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    rows = result.details["verify"]["rows"]
    osx_row = next(r for r in rows if r.get("name") == "osx" and r.get("kind") == "environment")
    assert osx_row["verdict"] == "lock-solved"
    assert "osx" not in _install_envs(runner, root)


def test_paused_lane_skipped_and_ignore_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_root(tmp_path)
    pauses = {"guild-container": ("PAUSE_CONTAINER_BUILDS", "2026-10-04")}

    def _selection(*_a, **_k):
        return Selection(
            base_ref="refs/remotes/origin/main",
            all_reason=None,
            changed_paths=("pixi.toml",),
            dirty_paths=(),
            verdicts=(LaneVerdict("guild-container", "pyforge-guild", True, "fixture"),),
        )

    import pyforge.steward.estate_verify as ev

    monkeypatch.setattr(ev, "select_lanes_for_paths", _selection)

    runner = RecordingRunner(root=root)
    result = run_verify(
        _deps(root, runner, pause_overrides=pauses),
        env_filter=None,
        lane_filter="guild-container",
        probe_filter=None,
        all_envs=False,
        keep=False,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    row = next(r for r in result.details["verify"]["rows"] if r.get("name") == "guild-container")
    assert "PAUSE_CONTAINER_BUILDS" in row["verdict"]
    assert not any("guild-container" in " ".join(a) and a[:3] == ["pixi", "run", "--frozen"] for a, _ in runner.calls)

    runner2 = RecordingRunner(root=root)
    run_verify(
        _deps(root, runner2, pause_overrides=pauses),
        env_filter=None,
        lane_filter="guild-container",
        probe_filter=None,
        all_envs=False,
        keep=False,
        ignore_ci_pauses=True,
        budget_minutes=None,
    )
    assert any("guild-container" in " ".join(a) for a, _ in runner2.calls)


def test_manual_rows_and_stale_probe_red_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner(root=root)
    monkeypatch.setattr(
        "pyforge.steward.estate_realize._locked_version",
        lambda *a, **k: "6.12.2",
    )
    result = run_verify(
        _deps(root, runner),
        env_filter=None,
        lane_filter=None,
        probe_filter=None,
        all_envs=False,
        keep=False,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    manual = [r for r in result.details["verify"]["rows"] if r.get("verdict") == "manual"]
    assert len(manual) == 3
    assert not result.ok
    probe = next(
        r for r in result.details["verify"]["rows"] if r.get("kind") == "probe" and r.get("name") == "bmad-method"
    )
    assert probe["verdict"] == "stale"


def test_probe_filter_runs_one_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_root(tmp_path)
    monkeypatch.setattr("pyforge.steward.estate_realize._locked_version", lambda *a, **k: "6.12.0")
    runner = RecordingRunner(root=root)
    result = run_verify(
        _deps(root, runner),
        env_filter=None,
        lane_filter=None,
        probe_filter="bmad-method",
        all_envs=False,
        keep=False,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    probes = [r for r in result.details["verify"]["rows"] if r.get("kind") == "probe"]
    assert len(probes) == 1
    assert probes[0]["name"] == "bmad-method"


def test_red_lane_reds_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner(
        root=root,
        responses={
            "pixi run --frozen --skip-deps -e pyforge-guild lint-types": FakeProc([], 1, "", "fail"),
        },
    )

    def _selection(*_a, **_k):
        return Selection(
            base_ref="refs/remotes/origin/main",
            all_reason=None,
            changed_paths=("pixi.toml",),
            dirty_paths=(),
            verdicts=(LaneVerdict("lint-types", "pyforge-guild", True, "fixture"),),
        )

    import pyforge.steward.estate_verify as ev

    monkeypatch.setattr(ev, "select_lanes_for_paths", _selection)
    result = run_verify(
        _deps(root, runner),
        env_filter=None,
        lane_filter="lint-types",
        probe_filter=None,
        all_envs=False,
        keep=False,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    assert not result.ok


def test_journal_validates_and_keep_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner(root=root)

    def _selection(*_a, **_k):
        return Selection(
            base_ref="refs/remotes/origin/main",
            all_reason=None,
            changed_paths=("pixi.toml",),
            dirty_paths=(),
            verdicts=(LaneVerdict("lint-types", "pyforge-guild", True, "fixture"),),
        )

    import pyforge.steward.estate_verify as ev

    monkeypatch.setattr(ev, "select_lanes_for_paths", _selection)
    result = run_verify(
        _deps(root, runner),
        env_filter="pyforge-guild",
        lane_filter="lint-types",
        probe_filter=None,
        all_envs=False,
        keep=True,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    assert "worktree kept at" in result.summary
    journal_path = next(root.glob(".steward/estate-refresh/*.json"))
    doc = json.loads(journal_path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_RESOURCE.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    plats = doc["verify"]["platforms"]
    assert plats["osx-arm64"]["verdict"] == "lock-solved"


def test_guild_bound_row(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner(root=root, du_mb=GUILD_SIZE_BOUND_MB + 1)
    result = run_verify(
        _deps(root, runner),
        env_filter="pyforge-guild",
        lane_filter=None,
        probe_filter=None,
        all_envs=False,
        keep=False,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    bound = next(r for r in result.details["verify"]["rows"] if r.get("kind") == "guild-bound")
    assert bound["verdict"] == "red"
    assert not result.ok
    du = next(argv for argv, _cwd in runner.calls if argv[:2] == ["du", "-sm"])
    # the env itself, not .pixi (whose bld/ cache is about 1 GB of path-dependency builds)
    assert du[-1].endswith(".pixi/envs/pyforge-guild")


def test_scoped_env_and_lane_skips_probes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner(root=root)

    def _selection(*_a, **_k):
        return Selection(
            base_ref="refs/remotes/origin/main",
            all_reason=None,
            changed_paths=("pixi.toml",),
            dirty_paths=(),
            verdicts=(LaneVerdict("lint-types", "pyforge-guild", True, "fixture"),),
        )

    import pyforge.steward.estate_verify as ev

    monkeypatch.setattr(ev, "select_lanes_for_paths", _selection)
    result = run_verify(
        _deps(root, runner),
        env_filter="pyforge-guild",
        lane_filter="lint-types",
        probe_filter=None,
        all_envs=False,
        keep=False,
        ignore_ci_pauses=False,
        budget_minutes=None,
    )
    assert not any(r.get("kind") == "probe" for r in result.details["verify"]["rows"])


def _verify(root: Path, runner: RecordingRunner, **kwargs: object):
    args = {
        "env_filter": None,
        "lane_filter": None,
        "probe_filter": None,
        "all_envs": False,
        "keep": False,
        "ignore_ci_pauses": False,
        "budget_minutes": None,
    }
    args.update(kwargs)
    return run_verify(_deps(root, runner), **args)  # type: ignore[arg-type]


def test_register_test_given_as_a_string_is_one_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A `test:` string is one lane, not one lane per character (Story 100.7 live run)."""
    root = _fixture_root(tmp_path)
    reg = root / "docs/governance/realization-register.yaml"
    reg.write_text(reg.read_text(encoding="utf-8").replace("test: [bmad-drift-check]", "test: marshal seed check"))
    monkeypatch.setattr("pyforge.steward.estate_realize._locked_version", lambda *a, **k: "6.12.0")
    runner = RecordingRunner(root=root)
    result = _verify(root, runner, probe_filter="bmad-method")
    tests = [r for r in result.details["verify"]["rows"] if r.get("kind") == "register-test"]
    assert [r["name"] for r in tests] == ["marshal seed check"]
    assert tests[0]["argv"][-3:] == ["marshal", "seed", "check"]


def test_lanes_resolve_from_the_pr_preflight_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A lane with no explicit env runs where pr-preflight runs (pyforge-guild), not in the verify env."""
    root = _fixture_root(tmp_path)
    import pyforge.steward.estate_verify as ev

    seen: dict[str, object] = {}

    def _lanes(pixi_data, **kwargs):
        seen.update(kwargs)
        return []

    monkeypatch.setattr(ev, "list_preflight_lanes", _lanes)
    monkeypatch.setattr("pyforge.steward.estate_realize._locked_version", lambda *a, **k: "6.12.0")
    _verify(root, RecordingRunner(root=root))
    assert seen.get("invoking_env") == "pyforge-guild"


def test_verify_writes_into_the_latest_refresh_journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The verify block lands in the refresh it verifies; a same-day second journal is the latest."""
    root = _fixture_root(tmp_path)
    jdir = root / ".steward/estate-refresh"
    for name in ("2026-10-14.json", "2026-10-14-2.json"):
        (jdir / name).write_text(json.dumps({"base_sha": name, "verify": {}}), encoding="utf-8")
    monkeypatch.setattr("pyforge.steward.estate_realize._locked_version", lambda *a, **k: "6.12.0")
    result = _verify(root, RecordingRunner(root=root), probe_filter="bmad-method")
    assert sorted(p.name for p in jdir.glob("*.json")) == ["2026-10-14-2.json", "2026-10-14.json"]
    assert json.loads((jdir / "2026-10-14-2.json").read_text())["verify"]["rows"]
    assert json.loads((jdir / "2026-10-14.json").read_text())["verify"] == {}
    assert result.details["journal_path"].endswith("2026-10-14-2.json")


def test_red_lane_keeps_its_output_tail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner(
        root=root,
        responses={
            "pixi run --frozen --skip-deps -e pyforge-guild lint-types": FakeProc([], 1, "", "boom: lint failed")
        },
    )
    import pyforge.steward.estate_verify as ev

    monkeypatch.setattr(
        ev,
        "select_lanes_for_paths",
        lambda *_a, **_k: Selection(
            base_ref="refs/remotes/origin/main",
            all_reason=None,
            changed_paths=("pixi.toml",),
            dirty_paths=(),
            verdicts=(LaneVerdict("lint-types", "pyforge-guild", True, "fixture"),),
        ),
    )
    result = _verify(root, runner, lane_filter="lint-types")
    lane = next(r for r in result.details["verify"]["rows"] if r.get("name") == "lint-types")
    assert lane["output_tail"] == "boom: lint failed"
