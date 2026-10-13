"""Story 100.5 — estate realize (AC2–AC4, faked subprocess only)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit import make_flag_provider_fixture

from pyforge.steward.estate_realize import RealizeDeps, run_probe, run_realize

REPO_ROOT = Path(__file__).resolve().parents[6]

flag_provider = make_flag_provider_fixture()


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
            if prefix in key:
                return FakeProc(argv, proc.returncode, proc.stdout, proc.stderr)
        return FakeProc(argv, 0, "", "")


def _journal_with_moves() -> dict:
    return {
        "moves": [
            {"package": "bmad-method", "from": "6.12.0", "to": "6.12.2", "feature": "*"},
            {"package": "bmad-loop", "from": "0.11.0", "to": "0.12.0", "feature": "*"},
            {"package": "caveman-installer", "from": "1", "to": "2", "feature": "*"},
            {"package": "pre-commit", "from": "1", "to": "2", "feature": "*"},
            {"package": "pixi", "from": "0.80", "to": "0.81", "feature": "*"},
        ]
    }


def test_plan_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag_provider) -> None:  # noqa: ARG001
    journal_path = tmp_path / "journal.json"
    journal_path.write_text(json.dumps(_journal_with_moves()), encoding="utf-8")
    runner = RecordingRunner()
    deps = RealizeDeps(root=REPO_ROOT, runner=runner, flag_on=lambda: True, loop_homes=list)
    result = run_realize(deps, plan=True, yes=False, all_rows=False, journal_path=journal_path)
    assert result.ok
    assert "bmad-method" in result.summary
    assert not any("upgrade" in " ".join(c) for c in runner.calls)


def test_operator_gate_skipped_without_yes(tmp_path: Path, flag_provider) -> None:  # noqa: ARG001
    journal_path = tmp_path / "journal.json"
    journal_path.write_text(json.dumps(_journal_with_moves()), encoding="utf-8")
    runner = RecordingRunner()
    deps = RealizeDeps(root=REPO_ROOT, runner=runner, flag_on=lambda: True, loop_homes=list)
    run_realize(deps, plan=False, yes=False, all_rows=False, journal_path=journal_path)
    assert not any("bmad-core" in " ".join(c) and "--apply" in c for c in runner.calls)
    doc = json.loads(journal_path.read_text())
    assert doc["realize"]["bmad-method"]["realize"] == "skipped-operator-gate"


def test_operator_gate_runs_with_yes(tmp_path: Path, flag_provider) -> None:  # noqa: ARG001
    journal_path = tmp_path / "journal.json"
    journal_path.write_text(json.dumps(_journal_with_moves()), encoding="utf-8")
    runner = RecordingRunner()
    deps = RealizeDeps(root=REPO_ROOT, runner=runner, flag_on=lambda: True, loop_homes=list)
    run_realize(deps, plan=False, yes=True, all_rows=False, journal_path=journal_path)
    joined = [" ".join(c) for c in runner.calls]
    assert any("upgrade bmad-core --apply" in s.replace("  ", " ") for s in joined)


def test_realize_argv_per_moved_class(tmp_path: Path, flag_provider) -> None:  # noqa: ARG001
    journal_path = tmp_path / "journal.json"
    journal_path.write_text(json.dumps(_journal_with_moves()), encoding="utf-8")
    runner = RecordingRunner()
    deps = RealizeDeps(
        root=REPO_ROOT,
        runner=runner,
        flag_on=lambda: True,
        loop_homes=lambda: [Path("/tmp/loop-home-a")],
    )
    run_realize(deps, plan=False, yes=True, all_rows=False, journal_path=journal_path)
    joined = " | ".join(" ".join(c) for c in runner.calls)
    assert "bump_pixi_version.py" in joined
    assert "pre-commit install" in joined
    assert "caveman-install --only claude --with-hooks" in joined
    assert "marshal refresh --project loop-home-a" in joined


def test_probe_never_writes_on_realize_path(tmp_path: Path, flag_provider) -> None:  # noqa: ARG001
    journal_path = tmp_path / "journal.json"
    journal_path.write_text(json.dumps(_journal_with_moves()), encoding="utf-8")
    runner = RecordingRunner()
    deps = RealizeDeps(root=REPO_ROOT, runner=runner, flag_on=lambda: True, loop_homes=list)
    run_realize(deps, plan=False, yes=False, all_rows=False, journal_path=journal_path)
    for argv in runner.calls:
        text = " ".join(argv).lower()
        if "pipeline-truth" in text or "seed check" in text:
            assert "install" not in text
            assert "apply" not in text


def test_manifest_stale_probe(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "_bmad" / "_config"
    manifest_dir.mkdir(parents=True)
    manifest_dir.joinpath("manifest.yaml").write_text(
        "installation:\n  version: 6.12.0\n", encoding="utf-8"
    )
    row = {
        "env": "pyforge-guild",
        "probe": {
            "expect": "locked-version",
            "path": "_bmad/_config/manifest.yaml",
            "key": "installation.version",
        },
    }

    def fake_locked(root: Path, env: str, package: str, platform: str) -> str | None:
        return "6.12.2"

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("pyforge.steward.estate_realize._locked_version", fake_locked)
    deps = RealizeDeps(root=tmp_path, runner=RecordingRunner(), flag_on=lambda: True)
    assert run_probe(deps, row, package="bmad-method") == "stale"
    monkeypatch.undo()


def test_kit_missing_probe() -> None:
    kit_json = json.dumps(
        {
            "verb": "check",
            "ok": False,
            "result": {
                "kit": [
                    {"item": "caveman-skill", "status": "ok"},
                    {"item": "ccr-store", "status": "ok"},
                    {"item": "codegraph-index", "status": "missing"},
                ]
            },
        }
    )
    runner = RecordingRunner(responses={"seed check": FakeProc([], 1, kit_json)})
    row = {"env": "pyforge-guild", "probe": {"expect": "kit-ok", "item": "codegraph-index"}}
    deps = RealizeDeps(root=REPO_ROOT, runner=runner, flag_on=lambda: True)
    assert run_probe(deps, row, package="codegraph") == "missing"


def test_pipeline_truth_stale_for_tea() -> None:
    payload = {
        "packages": [
            {
                "name": "bmad-method-test-architecture-enterprise",
                "installed": {"value": "ok"},
                "wired": {"value": "fail"},
            }
        ]
    }
    runner = RecordingRunner(
        responses={"pipeline-truth": FakeProc([], 0, json.dumps(payload))}
    )
    row = {
        "env": "pyforge-guild",
        "probe": {
            "expect": "stage-ok",
            "stages": ["installed", "wired"],
            "member": "bmad-method-test-architecture-enterprise",
        },
    }
    deps = RealizeDeps(root=REPO_ROOT, runner=runner, flag_on=lambda: True)
    assert run_probe(deps, row, package="bmad-method-test-architecture-enterprise") == "stale"


def test_bmad_loop_version_live(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = RecordingRunner(responses={"bmad-loop --version": FakeProc([], 0, "0.12.0\n")})
    monkeypatch.setattr(
        "pyforge.steward.estate_realize._locked_version", lambda *a, **k: "0.12.0"
    )
    row = {
        "env": "pyforge-marshal",
        "probe": {"expect": "locked-version", "command": ["bmad-loop", "--version"]},
    }
    deps = RealizeDeps(root=REPO_ROOT, runner=runner, flag_on=lambda: True)
    assert run_probe(deps, row, package="bmad-loop") == "live"
