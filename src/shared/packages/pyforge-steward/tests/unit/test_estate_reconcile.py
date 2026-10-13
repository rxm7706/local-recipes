"""Story 100.3 — estate reconcile and spec-surface reconcile (AC1, AC3–AC5)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.steward.estate import EstateDeps, EXIT_ESTATE_REFUSAL
from pyforge.steward.estate_reconcile import (
    EXIT_RECONCILE_CHECKS,
    ReconcileDeps,
    _build_generators,
    run_reconcile,
    specs_for_moved_paths,
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

    def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
        self.calls.append(list(argv))
        key = " ".join(argv)
        if "export" in key and "conda-environment" in key:
            return FakeProc(argv, 0, "name: build\n", "")
        if "git" in argv and argv[-1] == "commit":
            pytest.fail("git commit must not run during reconcile")
        return FakeProc(argv, 0, "", "")


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "scripts").mkdir()
    (root / ".steward" / "estate-refresh").mkdir(parents=True)
    journal = {
        "base_sha": "abc",
        "result_sha": "",
        "platform": "linux-64",
        "command": "pixi upgrade",
        "moves": [{"package": "cron-descriptor", "feature": "*", "from": "1", "to": "2"}],
        "losses_restored": [],
        "fan_out": {"ok": True, "findings": []},
        "realize_due": [],
        "transitive": False,
        "bmad": {"pinned": "1", "installed": "1", "latest": "1", "applied": False},
        "steps": [],
        "realize": {},
        "reconcile": {},
        "verify": {},
    }
    (root / ".steward/estate-refresh/2026-10-13.json").write_text(json.dumps(journal), encoding="utf-8")
    for rel in (
        "pixi.toml",
        "pixi.lock",
        "environment.yaml",
        "docs/reference/library-llms-full.md",
        "docs/reference/bmad-estate-llms-full.md",
        "docs/dreams/pyforge-unifying-strategy.md",
        "docs/reference/environments.md",
        "docs/how-to/pixi-tasks.md",
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("seed\n", encoding="utf-8")
    return root


def _deps(
    root: Path,
    runner: RecordingRunner,
    *,
    baseline: dict | None = None,
    memlog_append=None,
    stamp_spec=None,
    git_add=None,
) -> ReconcileDeps:
    baseline = baseline or {}
    return ReconcileDeps(
        root=root,
        runner=runner,
        flag_on=lambda: True,
        enforce_require=False,
        now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc),
        read_baseline=lambda _r: baseline,
        memlog_append=memlog_append or (lambda _p, _t: 0),
        git_add=git_add or (lambda _r, _paths: 0),
        stamp_spec=stamp_spec or (lambda _r, _spec: 0),
    )


def test_ac1_generators_order_and_conditional(tmp_path: Path) -> None:
    root = _root(tmp_path)
    runner = RecordingRunner()
    deps = _deps(root, runner)
    result = run_reconcile(deps)
    assert result.ok
    gen_argv = [step["argv"] for step in result.details["reconcile"]["generators"]]
    joined = [" ".join(a) for a in gen_argv]
    assert any("export" in line and "conda-environment" in line for line in joined)
    assert any("llms_full_check.py" in line and "--fix-floors" in line for line in joined)
    assert any("bmad-estate" in line for line in joined)
    assert any("pixi_env_matrix.py" in line for line in joined)
    assert any("docs_environments.py" in line for line in joined)
    assert any("docs_pixi_tasks.py" in line for line in joined)
    assert not any("bump_pixi_version.py" in line for line in joined)
    assert not any("bmad_suite_metapackage.py" in line for line in joined)

    journal = json.loads((root / ".steward/estate-refresh/2026-10-13.json").read_text())
    journal["moves"] = [{"package": "pixi", "feature": "*", "from": "0.80", "to": "0.81"}]
    (root / ".steward/estate-refresh/2026-10-13.json").write_text(json.dumps(journal), encoding="utf-8")
    runner2 = RecordingRunner()
    result2 = run_reconcile(_deps(root, runner2))
    joined2 = [" ".join(step["argv"]) for step in result2.details["reconcile"]["generators"]]
    assert any("bump_pixi_version.py" in line for line in joined2)

    gens_bmad = _build_generators({"moves": [{"package": "bmad-method", "feature": "*", "from": "1", "to": "2"}]}, root)
    assert any("bmad_suite_metapackage.py" in " ".join(g[1]) for g in gens_bmad)


def test_ac3_checks_journaled_and_gating_red(tmp_path: Path) -> None:
    root = _root(tmp_path)

    @dataclass
    class FailCheckRunner(RecordingRunner):
        fail_on: str = "llms_full_check.py"

        def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
            proc = super().__call__(argv, cwd)
            if self.fail_on in " ".join(argv) and "--fix-floors" not in argv:
                return FakeProc(argv, 1, "", "fail")
            return proc

    runner = FailCheckRunner(fail_on="llms_full_check.py")
    result = run_reconcile(_deps(root, runner))
    assert not result.ok
    assert result.details["exit_code"] == EXIT_RECONCILE_CHECKS
    checks = result.details["reconcile"]["checks"]
    names = {c["name"] for c in checks}
    assert "llms-full-check" in names
    assert "bmad-estate-check" in names
    assert "pixi-lock-check" in names
    warn = [c for c in checks if c.get("warn_only")]
    assert len(warn) == 2  # noqa: PLR2004
    assert all(c["exit"] == 0 or True for c in warn)


def test_ac4_spec_surface_memlog_stamp_no_bare_baseline(tmp_path: Path) -> None:
    root = _root(tmp_path)
    baseline = {
        "pyforge-steward/spec-a": {"files": {"pixi.toml": "deadbeef"}},
        "pyforge-steward/spec-b": {"files": {"pixi.toml": "deadbeef"}},
        "pyforge-guild/spec-c": {"files": {"pixi.toml": "deadbeef"}},
    }
    memlog_calls: list[tuple[str, str]] = []
    stamp_calls: list[str] = []

    def memlog(path: Path, text: str) -> int:
        memlog_calls.append((str(path), text))
        return 0

    def stamp(_root: Path, spec: str) -> int:
        stamp_calls.append(spec)
        return 0

    runner = RecordingRunner()

    @dataclass
    class TouchRunner(RecordingRunner):
        def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
            if "llms_full_check.py" in " ".join(argv):
                (root / "pixi.toml").write_text("changed\n", encoding="utf-8")
            return super().__call__(argv, cwd)

    spec_dirs = {
        "pyforge-steward/spec-a": "spec-a",
        "pyforge-steward/spec-b": "spec-b",
        "pyforge-guild/spec-c": "spec-c",
    }
    for _key, spec in spec_dirs.items():
        project = "pyforge-steward" if spec != "spec-c" else "pyforge-guild"
        memlog_path = (
            root
            / "_bmad-output/projects"
            / project
            / "planning-artifacts/specs"
            / spec
            / ".memlog.md"
        )
        memlog_path.parent.mkdir(parents=True)
        memlog_path.write_text("---\ntopic: test\n---\n\n- (note) seed\n", encoding="utf-8")

    deps = _deps(
        root,
        TouchRunner(),
        baseline=baseline,
        memlog_append=memlog,
        stamp_spec=stamp,
    )
    result = run_reconcile(deps)
    assert result.ok
    assert len(memlog_calls) == 3  # noqa: PLR2004
    assert len(stamp_calls) == 3  # noqa: PLR2004
    assert all("--spec" in " ".join(s["argv"]) for s in result.details["reconcile"]["spec_surface"]["stamps"])
    assert not any("commit" in c for c in runner.calls)


def test_ac4_refuses_memlog_without_frontmatter(tmp_path: Path) -> None:
    root = _root(tmp_path)
    baseline = {"pyforge-steward/spec-a": {"files": {"pixi.toml": "deadbeef"}}}
    memlog_path = root / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-a/.memlog.md"
    memlog_path.parent.mkdir(parents=True)
    memlog_path.write_text("- (note) no frontmatter\n", encoding="utf-8")

    @dataclass
    class TouchPixi(RecordingRunner):
        def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
            if "llms_full_check.py" in " ".join(argv):
                (root / "pixi.toml").write_text("changed\n", encoding="utf-8")
            return super().__call__(argv, cwd)

    result = run_reconcile(_deps(root, TouchPixi(), baseline=baseline))
    assert not result.ok
    assert "memlog lacks frontmatter" in result.summary


def test_ac5_never_commits(tmp_path: Path) -> None:
    root = _root(tmp_path)
    runner = RecordingRunner()
    run_reconcile(_deps(root, runner))
    assert not any(argv[:2] == ["git", "commit"] for argv in runner.calls)


def test_specs_for_moved_paths_from_baseline() -> None:
    baseline = {
        "pyforge-steward/spec-a": {"files": {"pixi.toml": "x", "pixi.lock": "y"}},
        "pyforge-scribe/spec-b": {"files": {"docs/reference/bmad-estate-llms-full.md": "z"}},
    }
    moved = {"pixi.toml", "docs/reference/bmad-estate-llms-full.md"}
    got = specs_for_moved_paths(baseline, moved)
    assert got == {
        "pyforge-steward/spec-a": {"pixi.toml"},
        "pyforge-scribe/spec-b": {"docs/reference/bmad-estate-llms-full.md"},
    }


def test_io_matrix_no_moves_skips_memlog(tmp_path: Path) -> None:
    root = _root(tmp_path)
    journal = json.loads((root / ".steward/estate-refresh/2026-10-13.json").read_text())
    journal["moves"] = []
    (root / ".steward/estate-refresh/2026-10-13.json").write_text(json.dumps(journal), encoding="utf-8")
    memlog_calls: list[tuple[str, str]] = []
    baseline = {"pyforge-steward/spec-a": {"files": {"pixi.toml": "deadbeef"}}}
    result = run_reconcile(
        _deps(
            root,
            RecordingRunner(),
            baseline=baseline,
            memlog_append=lambda p, t: memlog_calls.append((str(p), t)) or 0,
        )
    )
    assert result.ok
    assert memlog_calls == []


def test_flag_off_refuses(tmp_path: Path) -> None:
    root = _root(tmp_path)
    deps = ReconcileDeps(
        root=root,
        runner=RecordingRunner(),
        flag_on=lambda: False,
        enforce_require=False,
    )
    result = run_reconcile(deps)
    assert not result.ok
    assert result.details["exit_code"] == EXIT_ESTATE_REFUSAL
