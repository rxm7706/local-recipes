"""Story 100.2 — estate plan / refresh / status (AC1–AC5, no live pixi/git/network)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.steward.cli import DUTIES, build_parser, resolve_duty
from pyforge.steward.estate import (
    ESTATE_FLAG_KEY,
    EXIT_ESTATE_REFUSAL,
    SCHEMA_RESOURCE,
    EstateDeps,
    EstateDuty,
    run_plan,
    run_refresh,
    run_status,
)

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
    flag_on: bool = True,
    now: datetime | None = None,
) -> EstateDeps:
    return EstateDeps(
        root=root,
        runner=runner,
        branch=lambda: branch,
        dirty=lambda: dirty,
        head_sha=lambda: "abc123",
        flag_on=lambda: flag_on,
        enforce_require=False,
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

    assert len(DUTIES) == 28  # noqa: PLR2004
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
