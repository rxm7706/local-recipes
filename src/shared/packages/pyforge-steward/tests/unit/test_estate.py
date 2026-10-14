"""Story 100.2 — estate plan / refresh / status (AC1–AC5, no live pixi/git/network)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

from pyforge.steward.cli import DUTIES, build_parser, resolve_duty
from pyforge.steward.estate import (
    ESTATE_FLAG_KEY,
    EXIT_ESTATE_REFUSAL,
    SCHEMA_RESOURCE,
    EstateDeps,
    EstateDuty,
    _artifact_version,
    _days_since_last_journal,
    _default_runner,
    _held_by,
    _next_journal_path,
    _parse_pixi_moves,
    _production_deps,
    _row_covers_feature,
    run_plan,
    run_refresh,
    run_status,
)

# The flag-provider fixture lives in this module, not in a conftest: the pip-only lane
# (pyforge-pip-install.yml) installs pyforge-steward without the testing kit and collects
# tests/meta and tests/unit/test_fresh_clone_class_path.py, so any conftest on those paths that
# imports pyforge.testing_kit breaks its collection (PR #2189, twice).
flag_provider = make_flag_provider_fixture()

REPO_ROOT = Path(__file__).resolve().parents[6]
HOOK = REPO_ROOT / ".claude" / "hooks" / "pre-shell.py"
REAL_ROSTER = REPO_ROOT / "docs" / "governance" / "guild-roster.json"

_UPGRADE_JSON = json.dumps(
    {
        "packages": [
            {
                "name": "cron-descriptor",
                "environment": "pyforge-guild",
                "old": "2.1.0",
                "new": "2.2.0",
            }
        ]
    }
)


@dataclass
class FakeProc:
    args: list[str]
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


@dataclass
class RecordingRunner:
    calls: list[list[str]] = field(default_factory=list)
    responses: dict[str, FakeProc] = field(default_factory=dict)

    def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
        self.calls.append(list(argv))
        key = " ".join(argv)
        for prefix, proc in self.responses.items():
            if key.startswith(prefix) or prefix in key:
                return FakeProc(argv, proc.returncode, proc.stdout, proc.stderr)
        if "pin_policy_check.py" in key and "--render-command" in key:
            return FakeProc(argv, 0, "pixi upgrade --pinning-strategy latest-up --exclude pixi\n", "")
        if "upgrade" in key and "--json" in key:
            return FakeProc(argv, 0, _UPGRADE_JSON, "")
        if "--diff" in key:
            return FakeProc(argv, 1, json.dumps([{"kind": "lost-cap", "package": "pyjwt"}]), "")
        if "--fan-out" in key:
            return FakeProc(argv, 0, "[]", "")
        if "pin_policy_restore" in key:
            return FakeProc(argv, 0, "", "")
        if argv[:2] == ["pixi", "lock"]:
            return FakeProc(argv, 0, "", "")
        if "bump_pixi_version" in key:
            return FakeProc(argv, 0, "", "")
        if argv[:2] == ["pixi", "update"]:
            return FakeProc(argv, 0, "", "")
        return FakeProc(argv, 0, "", "")


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "docs" / "governance").mkdir(parents=True)
    (root / "docs" / "governance" / "pin-policy.yaml").write_text(
        "defaults:\n  pinning_strategy: latest-up\nholds:\n"
        "  - package: cron-descriptor\n    hold: floor-only\n    features: '*'\n"
        "    reason: test\n    authority: test\n",
        encoding="utf-8",
    )
    (root / "scripts").mkdir()
    (root / "_bmad" / "_config").mkdir(parents=True)
    (root / "_bmad" / "_config" / "manifest.yaml").write_text(
        "installation:\n  version: 6.12.0\n",
        encoding="utf-8",
    )
    (root / "pixi.toml").write_text(
        '[project]\nname = "x"\n\n[feature.guild.dependencies]\nbmad-method = ">=6.12.2"\n',
        encoding="utf-8",
    )
    (root / ".steward" / "estate-refresh").mkdir(parents=True)
    return root


def _deps(
    root: Path,
    runner: RecordingRunner,
    *,
    dirty: bool = False,
    branch: str = "story-branch",
    flag_on: bool | Callable[[], bool] = True,
    now: datetime | None = None,
    enforce_require: bool = False,
) -> EstateDeps:
    flag_fn = flag_on if callable(flag_on) else (lambda: flag_on)
    return EstateDeps(
        root=root,
        runner=runner,
        branch=lambda: branch,
        dirty=lambda: dirty,
        head_sha=lambda: "abc123",
        flag_on=flag_fn,
        enforce_require=enforce_require,
        bmad_latest=lambda _pkg: None,
        now=lambda: now or datetime(2026, 10, 13, tzinfo=timezone.utc),
    )


def test_ac1_plan_rows_bmad_due_and_json_schema(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    deps = _deps(root, runner)
    result = run_plan(deps, json_out=True, due_only=False)
    assert result.ok
    plan = result.details["plan"]
    assert isinstance(plan, dict)
    assert plan["moves"][0]["package"] == "cron-descriptor"
    assert "held-by" in plan["moves"][0]
    bmad = plan["bmad"]
    core = next(r for r in bmad if r["package"] == "bmad-method")
    assert core["pinned"] == "6.12.2"
    assert core["installed"] == "6.12.0"
    assert core["latest"] == "unknown"
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_RESOURCE.read_text(encoding="utf-8"))
    jsonschema.validate(plan, schema, cls=jsonschema.Draft202012Validator)

    due_none = run_plan(deps, json_out=False, due_only=True)
    assert not due_none.ok

    journal = root / ".steward" / "estate-refresh" / "2026-09-01.json"
    journal.write_text("{}", encoding="utf-8")
    deps_old = _deps(root, runner, now=datetime(2026, 10, 13, tzinfo=timezone.utc))
    due_old = run_plan(deps_old, json_out=False, due_only=True)
    assert not due_old.ok

    journal.unlink()
    (root / ".steward" / "estate-refresh" / "2026-10-12.json").write_text("{}", encoding="utf-8")
    due_fresh = run_plan(deps, json_out=False, due_only=True)
    assert due_fresh.ok
    assert runner.calls, "plan should invoke subprocess conductor"


def test_ac2_refresh_refusals_before_subprocess(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()

    dirty = run_refresh(_deps(root, runner, dirty=True), transitive=False)
    assert dirty.details.get("exit_code") == EXIT_ESTATE_REFUSAL
    assert not runner.calls

    main_branch = run_refresh(_deps(root, runner, branch="main"), transitive=False)
    assert main_branch.details.get("exit_code") == EXIT_ESTATE_REFUSAL
    assert not runner.calls

    flag_off = run_refresh(_deps(root, runner, flag_on=False), transitive=False)
    assert flag_off.details.get("exit_code") == EXIT_ESTATE_REFUSAL
    assert ESTATE_FLAG_KEY in flag_off.summary
    assert not runner.calls


def test_ac3_refresh_path_and_journal(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    runner.responses["--fan-out"] = FakeProc([], 1, json.dumps([{"kind": "fan-out", "package": "x"}]), "")
    result = run_refresh(_deps(root, runner), transitive=False)
    assert not result.ok
    joined = [" ".join(c) for c in runner.calls]
    assert any("upgrade" in line and "--json" in line for line in joined)
    assert any("--diff" in line for line in joined)
    assert any("pin_policy_restore" in line for line in joined)
    assert any(line.startswith("pixi lock") or "pixi lock" in line for line in joined)
    assert any("--fan-out" in line for line in joined)
    assert not any("pixi update" in line for line in joined)
    journals = list((root / ".steward" / "estate-refresh").glob("*.json"))
    assert len(journals) == 1
    doc = json.loads(journals[0].read_text(encoding="utf-8"))
    assert doc["fan_out"]["ok"] is False
    assert len(doc["steps"]) >= 4  # noqa: PLR2004
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_RESOURCE.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema, cls=jsonschema.Draft202012Validator)


def test_ac3_bump_pixi_when_pixi_moves(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    runner.responses["upgrade"] = FakeProc(
        [],
        0,
        json.dumps({"packages": [{"name": "pixi", "environment": "*", "old": "0.80", "new": "0.81"}]}),
        "",
    )
    result = run_refresh(_deps(root, runner), transitive=False)
    assert result.ok
    assert any("bump_pixi_version" in " ".join(c) for c in runner.calls)


def test_ac4_transitive_and_hook(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    run_refresh(_deps(root, runner), transitive=True)
    assert any(c[:2] == ["pixi", "update"] for c in runner.calls)

    real = json.loads(REAL_ROSTER.read_text(encoding="utf-8"))
    assert any(r["id"] == "steward-estate-transitive" for r in real["session_denials"])

    spec = importlib.util.spec_from_file_location("pre_shell_hook_estate", HOOK)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    assert set(mod.MATCHERS) == {r["id"] for r in real["session_denials"]}

    deny_cmd = "pixi run -e pyforge-steward pyforge steward estate refresh --transitive"
    deny_ctx = mod.Context(
        harness="cursor",
        kind="bash",
        command=deny_cmd,
        subcommands=mod.split_subcommands(deny_cmd),
        cwd=str(root),
    )
    rule = mod.load_denial_rules(REPO_ROOT)["steward-estate-transitive"]
    assert mod.match_steward_estate_transitive(deny_ctx, rule)

    allow_cmd = "pixi run -e pyforge-steward pyforge steward estate refresh"
    allow_ctx = mod.Context(
        harness="cursor",
        kind="bash",
        command=allow_cmd,
        subcommands=mod.split_subcommands(allow_cmd),
        cwd=str(root),
    )
    assert mod.match_steward_estate_transitive(allow_ctx, rule) is None
    plan_cmd = "pyforge steward estate plan"
    plan_ctx = mod.Context(
        harness="cursor",
        kind="bash",
        command=plan_cmd,
        subcommands=mod.split_subcommands(plan_cmd),
        cwd=str(root),
    )
    assert mod.match_steward_estate_transitive(plan_ctx, rule) is None


def test_ac5_status_and_duty_count(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    path = root / ".steward" / "estate-refresh" / "2026-10-01.json"
    path.write_text(
        json.dumps(
            {
                "base_sha": "x",
                "result_sha": "",
                "platform": "linux-64",
                "command": "pixi upgrade",
                "moves": [],
                "losses_restored": [],
                "fan_out": {"ok": True, "findings": []},
                "realize_due": [],
                "transitive": False,
                "bmad": {"pinned": "6.12.2", "installed": "6.12.0", "latest": "unknown", "applied": False},
                "steps": [],
                "realize": {},
                "reconcile": {},
                "verify": {},
            }
        ),
        encoding="utf-8",
    )
    runner = RecordingRunner()
    status = run_status(_deps(root, runner), json_out=False, show_all=False)
    assert status.ok
    assert "2026-10-01.json" in status.summary

    assert len(DUTIES) == 29  # noqa: PLR2004
    assert "estate" in DUTIES
    assert isinstance(resolve_duty("estate"), EstateDuty)


def test_cli_projects_refusal_exit_code(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    duty = EstateDuty()
    ns = argparse.Namespace(
        duty="estate",
        estate_verb="refresh",
        transitive=False,
        json=False,
        due=False,
        all=False,
        _estate_deps=_deps(root, RecordingRunner(), dirty=True),
    )
    result = duty.run(ns)
    assert result.details.get("exit_code") == EXIT_ESTATE_REFUSAL


def test_steward_help_lists_estate(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    assert "estate" in capsys.readouterr().out


@flag_states("pyforge.steward.estate_refresh")
def test_estate_verbs_respect_flag_state(tmp_path: Path, flag_provider: dict[str, bool]) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    on = flag_provider["pyforge.steward.estate_refresh"]
    deps = _deps(root, runner, flag_on=lambda: on, enforce_require=True)
    plan = run_plan(deps, json_out=False, due_only=False)
    status = run_status(deps, json_out=False, show_all=False)
    refresh = run_refresh(deps, transitive=False)
    if on:
        assert plan.ok
        assert status.ok
        assert refresh.ok
    else:
        assert not plan.ok and ESTATE_FLAG_KEY in plan.summary
        assert not status.ok and ESTATE_FLAG_KEY in status.summary
        assert not refresh.ok and ESTATE_FLAG_KEY in refresh.summary
        assert not runner.calls


def test_plan_prints_text_rows(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    result = run_plan(_deps(root, RecordingRunner()), json_out=False, due_only=False)
    assert result.ok
    assert "cron-descriptor" in result.summary
    assert "--- bmad ---" in result.summary


def test_status_no_journals(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".steward" / "estate-refresh").mkdir(parents=True)
    result = run_status(_deps(root, RecordingRunner()), json_out=False, show_all=False)
    assert result.ok
    assert "no journals" in result.summary


def test_refresh_restore_refusal(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    runner.responses["--diff"] = FakeProc([], 1, json.dumps([{"kind": "lost-cap", "package": "x"}]), "")
    runner.responses["pin_policy_restore"] = FakeProc([], 1, "", "restore failed")
    result = run_refresh(_deps(root, runner), transitive=False)
    assert not result.ok
    assert "restore refused" in result.summary


def test_refresh_success_and_second_journal_same_day(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    fixed_now = datetime(2026, 10, 13, tzinfo=timezone.utc)
    deps = _deps(root, runner, now=fixed_now)
    first = run_refresh(deps, transitive=False)
    assert first.ok
    second = run_refresh(deps, transitive=False)
    assert second.ok
    names = sorted(p.name for p in (root / ".steward" / "estate-refresh").glob("*.json"))
    assert names == ["2026-10-13-2.json", "2026-10-13.json"]


def test_estate_duty_run_plan_via_namespace(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    duty = EstateDuty()
    ns = argparse.Namespace(
        duty="estate",
        estate_verb="plan",
        json=False,
        due=False,
        transitive=False,
        all=False,
        _estate_deps=_deps(root, RecordingRunner()),
    )
    assert duty.run(ns).ok


def test_estate_duty_unknown_verb() -> None:
    duty = EstateDuty()
    ns = argparse.Namespace(estate_verb="nope")
    result = duty.run(ns)
    assert not result.ok
    assert "plan, refresh, reconcile, verify, realize, or status" in result.summary


def test_parse_pixi_moves_and_policy_helpers() -> None:
    moves = _parse_pixi_moves(
        {"packages": [{"name": "cron-descriptor", "environment": "pyforge-guild", "old": "1", "new": "2"}]}
    )
    assert moves[0]["package"] == "cron-descriptor"
    assert _parse_pixi_moves(None) == []
    assert _parse_pixi_moves({"packages": "bad"}) == []
    assert _parse_pixi_moves([{"package": "x", "from": "1", "to": "2"}])[0]["feature"] == "*"
    policy = {
        "holds": [
            {"package": "cron-descriptor", "hold": "floor-only", "features": ["pyforge-guild"], "authority": "test"}
        ]
    }
    assert _held_by(policy, "cron-descriptor", "pyforge-guild") == "floor-only (test)"
    assert _held_by(policy, "missing", "*") is None
    assert _row_covers_feature("*", "any")
    assert _row_covers_feature(["guild"], "guild.extra")


def test_default_runner_and_production_deps(tmp_path: Path) -> None:
    proc = _default_runner(["true"], tmp_path)
    assert proc.returncode == 0
    deps = _production_deps(REPO_ROOT)
    assert deps.branch()
    assert deps.head_sha() != ""
    assert isinstance(deps.dirty(), bool)


def test_next_journal_path_and_days_since(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    journal_dir = root / ".steward" / "estate-refresh"
    journal_dir.mkdir(parents=True)
    journal_dir.joinpath("2026-10-13.json").write_text("{}", encoding="utf-8")
    assert (
        _next_journal_path(root, today=datetime(2026, 10, 13, tzinfo=timezone.utc).date()).name == "2026-10-13-2.json"
    )
    days = _days_since_last_journal(root, now=datetime(2026, 10, 15, tzinfo=timezone.utc))
    assert days == 2  # noqa: PLR2004


def test_refresh_realize_due_and_fan_json_fallback(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    register = REPO_ROOT / "docs/governance/realization-register.yaml"
    (root / "docs/governance/realization-register.yaml").write_text(
        register.read_text(encoding="utf-8"), encoding="utf-8"
    )
    runner = RecordingRunner()
    runner.responses["upgrade"] = FakeProc(
        [],
        0,
        json.dumps({"packages": [{"name": "bmad-method", "old": "6.12.0", "new": "6.12.2"}]}),
        "",
    )
    runner.responses["--diff"] = FakeProc([], 0, "[]", "")
    runner.responses["--fan-out"] = FakeProc([], 0, "also-not-json", "")
    result = run_refresh(_deps(root, runner), transitive=False)
    assert result.ok
    assert "realize-due" in result.summary
    assert "bmad-method" in result.summary


def test_refresh_refuses_a_diff_that_prints_no_json(tmp_path: Path) -> None:
    """A broken policy diff is a refusal, never a clean pass (Story 100.7 review)."""
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    runner.responses["--diff"] = FakeProc([], 1, "not-json", "")
    result = run_refresh(_deps(root, runner), transitive=False)
    assert not result.ok
    assert "printed no JSON" in result.summary


def test_status_json_out_and_show_all(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    path = root / ".steward" / "estate-refresh" / "2026-10-01.json"
    path.write_text(json.dumps({"base_sha": "x", "moves": [], "fan_out": {"ok": True}}), encoding="utf-8")
    (root / ".steward" / "estate-refresh" / "2026-10-02.json").write_text(
        json.dumps({"base_sha": "y", "moves": [{"p": 1}], "fan_out": {"ok": False}}),
        encoding="utf-8",
    )
    deps = _deps(root, RecordingRunner())
    json_status = run_status(deps, json_out=True, show_all=True)
    assert json_status.ok
    payload = json.loads(json_status.summary)
    assert len(payload["journals"]) == 2  # noqa: PLR2004


def test_estate_duty_reconcile_and_realize(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    register = REPO_ROOT / "docs/governance/realization-register.yaml"
    (root / "docs/governance/realization-register.yaml").write_text(
        register.read_text(encoding="utf-8"), encoding="utf-8"
    )
    journal = tmp_path / "journal.json"
    journal.write_text(json.dumps({"moves": [{"package": "bmad-method", "from": "1", "to": "2"}]}), encoding="utf-8")
    duty = EstateDuty()
    reconcile_ns = argparse.Namespace(
        duty="estate",
        estate_verb="reconcile",
        journal_path=None,
        _estate_deps=_deps(root, RecordingRunner()),
        _reconcile_deps=None,
    )
    duty.run(reconcile_ns)
    from pyforge.steward.estate_realize import RealizeDeps

    realize_ns = argparse.Namespace(
        duty="estate",
        estate_verb="realize",
        plan=True,
        yes=False,
        all=False,
        journal=str(journal),
        _estate_deps=_deps(root, RecordingRunner()),
        _realize_deps=RealizeDeps(root=root, runner=RecordingRunner(), flag_on=lambda: True, enforce_require=False),
    )
    assert duty.run(realize_ns).ok


def test_parse_pixi_moves_environment_shape() -> None:
    """pixi 0.8x ``upgrade --json``: explicit rows only, one per environment (Story 100.7)."""

    def side(version: str) -> dict[str, str]:
        return {"conda": f"https://conda.anaconda.org/conda-forge/noarch/pyjwt-{version}-pyh5ded981_0.conda"}

    payload = {
        "version": 1,
        "environment": {
            "pyforge-steward": {
                "linux-64": [
                    {"name": "pyjwt", "before": side("2.15.0"), "after": side("2.15.1"), "explicit": True},
                    {"name": "idna", "before": side("3.10"), "after": side("3.11"), "explicit": False},
                ],
                "win-64": [
                    {"name": "pyjwt", "before": side("2.15.0"), "after": side("2.15.1"), "explicit": True},
                ],
            }
        },
    }
    moves = _parse_pixi_moves(payload)
    assert moves == [{"package": "pyjwt", "feature": "pyforge-steward", "from": "2.15.0", "to": "2.15.1"}]


def test_refresh_excludes_a_package_whose_floor_the_upgrade_lowered(tmp_path: Path) -> None:
    """A lowered floor reruns the upgrade from base with that package excluded (Story 100.7)."""
    root = _fixture_root(tmp_path)
    diffs = iter(
        [
            FakeProc([], 1, json.dumps([{"kind": "lowered-floor", "package": "cron-descriptor"}]), ""),
            FakeProc([], 0, "[]", ""),
            FakeProc([], 0, "[]", ""),
        ]
    )

    class Runner(RecordingRunner):
        def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
            if "--diff" in " ".join(argv):
                self.calls.append(list(argv))
                proc = next(diffs)
                return FakeProc(argv, proc.returncode, proc.stdout, proc.stderr)
            return super().__call__(argv, cwd)

    runner = Runner()
    result = run_refresh(_deps(root, runner), transitive=False)
    assert result.ok, result.summary
    upgrades = [c for c in runner.calls if c[:2] == ["pixi", "upgrade"]]
    assert len(upgrades) == 2  # noqa: PLR2004
    assert "cron-descriptor" not in upgrades[0]
    assert upgrades[1][-3:] == ["--exclude", "cron-descriptor", "--json"]
    assert ["git", "checkout", "abc123", "--", "pixi.toml", "pixi.lock"] in runner.calls
    assert not any("pin_policy_restore" in " ".join(c) for c in runner.calls)
    doc = json.loads(next((root / ".steward" / "estate-refresh").glob("*.json")).read_text(encoding="utf-8"))
    assert doc["converge"] == {"rounds": 2, "excluded": ["cron-descriptor"], "converged": True, "unresolved": []}
    assert doc["command"].endswith("--exclude cron-descriptor")


def test_refresh_stops_converging_at_the_round_cap(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    counter = iter(range(100))

    class Runner(RecordingRunner):
        def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
            if "--diff" in " ".join(argv):
                self.calls.append(list(argv))
                pkg = f"pkg{next(counter)}"
                return FakeProc(argv, 1, json.dumps([{"kind": "lowered-floor", "package": pkg}]), "")
            return super().__call__(argv, cwd)

    runner = Runner()
    result = run_refresh(_deps(root, runner), transitive=False)
    upgrades = [c for c in runner.calls if c[:2] == ["pixi", "upgrade"]]
    assert len(upgrades) == 4  # noqa: PLR2004
    reverts = [c for c in runner.calls if c[:2] == ["git", "checkout"]]
    assert len(reverts) == 3  # noqa: PLR2004
    # the fourth round's lowered floor reaches the restore, which the fake lets pass
    assert result.ok
    doc = json.loads(next((root / ".steward" / "estate-refresh").glob("*.json")).read_text(encoding="utf-8"))
    assert doc["converge"]["converged"] is False
    assert doc["converge"]["unresolved"] == ["pkg3"]
    assert doc["converge"]["excluded"] == ["pkg0", "pkg1", "pkg2"]


def test_refresh_refuses_when_the_upgrade_fails(tmp_path: Path) -> None:
    """A failed upgrade resets the pixi files, journals the refusal and exits with the refusal code."""
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    runner.responses["pixi upgrade"] = FakeProc([], 1, "", "solve failed")
    result = run_refresh(_deps(root, runner), transitive=False)
    assert not result.ok
    assert result.details["exit_code"] == EXIT_ESTATE_REFUSAL
    assert "pixi upgrade failed in round 1" in result.summary
    assert runner.calls[-1] == ["git", "checkout", "abc123", "--", "pixi.toml", "pixi.lock"]
    assert not any(c[:2] == ["pixi", "lock"] for c in runner.calls)
    doc = json.loads(next((root / ".steward" / "estate-refresh").glob("*.json")).read_text(encoding="utf-8"))
    assert doc["refused"].startswith("pixi upgrade failed")
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(
        doc, json.loads(SCHEMA_RESOURCE.read_text(encoding="utf-8")), cls=jsonschema.Draft202012Validator
    )


def test_refresh_refuses_when_the_lock_fails(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    runner.responses["pixi lock"] = FakeProc([], 1, "", "unsolvable")
    result = run_refresh(_deps(root, runner), transitive=False)
    assert not result.ok
    assert "pixi lock failed" in result.summary
    assert runner.calls[-1][:2] == ["git", "checkout"]


def test_parse_pixi_moves_dashed_names() -> None:
    side = {"conda": "https://conda.anaconda.org/conda-forge/linux-64/gcc_linux-64-14.3.0-h1382650_11.conda"}
    assert _artifact_version(side) == "14.3.0"
    assert _artifact_version({"conda": "https://x/linux-64/clang-18-18.1.8-default_h1.conda"}) == "18.1.8"
    assert _artifact_version({"conda": "https://x/noarch/pip-24.2-pyh8b19718_1.tar.bz2"}) == "24.2"


def test_reconcile_duty_wires_real_memlog_add_and_stamp_seams(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI duty must not run reconcile on the dataclass's no-op seams (Story 100.7)."""
    import pyforge.steward.estate_reconcile as er

    root = _fixture_root(tmp_path)
    runner = RecordingRunner()
    seen: dict[str, object] = {}

    def _capture(rdeps, *, journal_path=None):
        seen["rdeps"] = rdeps
        return None

    monkeypatch.setattr(er, "run_reconcile", _capture)
    ns = argparse.Namespace(duty="estate", estate_verb="reconcile", _estate_deps=_deps(root, runner))
    EstateDuty().run(ns)
    rdeps = seen["rdeps"]
    memlog = root / "_bmad-output/projects/p/planning-artifacts/specs/spec-x/.memlog.md"
    rdeps.memlog_append(memlog, "Surface reconcile")
    rdeps.git_add(root, ["pkg/generated.txt"])
    rdeps.stamp_spec(root, "p/spec-x")
    memlog_call, add_call, stamp_call = runner.calls[-3:]
    assert memlog_call[1:5] == ["_bmad/scripts/memlog.py", "append", "--path", str(memlog)]
    assert memlog_call[-2:] == ["--text", "Surface reconcile"]
    assert add_call == ["git", "add", "--", "pkg/generated.txt"]
    assert stamp_call[1].endswith("spec_surface_check.py")
    assert stamp_call[2:] == ["--write-baseline", "--spec", "p/spec-x"]
