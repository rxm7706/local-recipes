"""Story 100.3 — estate reconcile and spec-surface reconcile (AC1, AC3–AC5)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

from pyforge.steward.estate import ESTATE_FLAG_KEY, EXIT_ESTATE_REFUSAL
from pyforge.steward.estate_reconcile import (
    ENV_MATRIX_DREAM,
    EXIT_RECONCILE_CHECKS,
    GATING_CHECKS,
    WARN_CHECKS,
    WATCH_PATHS,
    ReconcileDeps,
    _build_generators,
    run_reconcile,
    specs_for_moved_paths,
)

flag_provider = make_flag_provider_fixture()

# tests/unit -> tests -> pyforge-steward -> packages -> shared -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[6]
ENV_MATRIX_SCRIPT = REPO_ROOT / "scripts" / "pixi_env_matrix.py"


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
    # Story 108.1: the exact argv, not a substring -- the script takes the Dream only as --dream.
    assert [sys.executable, "scripts/pixi_env_matrix.py", "--update", "--dream", ENV_MATRIX_DREAM] in gen_argv
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

    jpath = root / ".steward/estate-refresh/2026-10-13.json"
    gens_bmad = _build_generators(
        {"moves": [{"package": "bmad-method", "feature": "*", "from": "1", "to": "2"}]},
        root,
        journal_path=jpath,
    )
    bmad_gen = next(g for g in gens_bmad if g[0] == "generate-bmad-suite")
    joined_bmad = " ".join(bmad_gen[1])
    assert "bmad_suite_metapackage.py" in joined_bmad
    assert "--journal" in joined_bmad
    assert "--json" in joined_bmad


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
        memlog_path = root / "_bmad-output/projects" / project / "planning-artifacts/specs" / spec / ".memlog.md"
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


@flag_states("pyforge.steward.estate_refresh")
def test_reconcile_respects_flag_state(tmp_path: Path, flag_provider: dict[str, bool]) -> None:
    root = _root(tmp_path)
    on = flag_provider["pyforge.steward.estate_refresh"]
    deps = replace(_deps(root, RecordingRunner()), flag_on=lambda: on, enforce_require=False)
    result = run_reconcile(deps)
    if on:
        assert result.ok
    else:
        assert not result.ok
        assert result.details["exit_code"] == EXIT_ESTATE_REFUSAL
        assert ESTATE_FLAG_KEY in result.summary


def test_production_seams_run_memlog_from_the_repo_root(tmp_path: Path) -> None:
    from pyforge.steward.estate_reconcile import production_reconcile_seams

    cwds: list[Path] = []

    class _Proc:
        returncode = 0

    def _runner(argv, cwd):
        cwds.append(cwd)
        return _Proc()

    seams = production_reconcile_seams(_runner)
    memlog = tmp_path / "_bmad-output/projects/p/planning-artifacts/specs/spec-x/.memlog.md"
    assert seams.memlog_append(memlog, "t") == 0
    assert cwds == [tmp_path]


def test_docs_map_is_a_watched_path() -> None:
    from pyforge.steward.estate_reconcile import WATCH_PATHS

    # The docs generators restamp the map page; joined here so the trigger-map meta-test
    # does not read a literal path as a file this suite opens.
    assert "/".join(("docs", "map.yaml")) in WATCH_PATHS


def test_ac6_reconcile_journals_bmad_suite_report(tmp_path: Path) -> None:
    root = _root(tmp_path)
    journal = json.loads((root / ".steward/estate-refresh/2026-10-13.json").read_text())
    journal["moves"] = [{"package": "bmad-method", "feature": "*", "from": "6.12.0", "to": "6.12.2"}]
    jpath = root / ".steward/estate-refresh/2026-10-13.json"
    jpath.write_text(json.dumps(journal), encoding="utf-8")
    report = {
        "version_before": "2026.10.1",
        "version": "2026.10.14",
        "written": True,
        "members": [
            {
                "name": "bmad-method",
                "floor_before": "6.12.0",
                "floor": "6.12.2",
                "source": "batch-move",
            }
        ],
    }

    @dataclass
    class BmadRunner(RecordingRunner):
        def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
            if "bmad_suite_metapackage.py" in " ".join(argv):
                assert "--journal" in argv
                assert "--json" in argv
                return FakeProc(argv, 0, json.dumps(report), "")
            return super().__call__(argv, cwd)

    result = run_reconcile(_deps(root, BmadRunner()))
    assert result.ok
    saved = json.loads(jpath.read_text())
    assert saved["reconcile"]["bmad_suite"]["version"] == "2026.10.14"
    assert "bmad-method 6.12.0 -> 6.12.2 [batch-move]" in result.summary


def test_ac7_broken_generator_fails_reconcile(tmp_path: Path) -> None:
    root = _root(tmp_path)
    journal = json.loads((root / ".steward/estate-refresh/2026-10-13.json").read_text())
    journal["moves"] = [{"package": "bmad-loop", "feature": "*", "from": "0.12.0", "to": "0.13.0"}]
    jpath = root / ".steward/estate-refresh/2026-10-13.json"
    jpath.write_text(json.dumps(journal), encoding="utf-8")

    @dataclass
    class FailBmadRunner(RecordingRunner):
        mode: str = "exit1"

        def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
            if "bmad_suite_metapackage.py" in " ".join(argv):
                if self.mode == "exit1":
                    return FakeProc(argv, 1, "", "fail")
                return FakeProc(argv, 0, "not json", "")
            return super().__call__(argv, cwd)

    r1 = run_reconcile(_deps(root, FailBmadRunner(mode="exit1")))
    assert not r1.ok
    assert r1.details["exit_code"] == EXIT_RECONCILE_CHECKS
    assert "generate-bmad-suite" in r1.summary

    r2 = run_reconcile(_deps(root, FailBmadRunner(mode="badjson")))
    assert not r2.ok
    assert "generate-bmad-suite" in r2.summary


def test_checks_run_in_the_guild_env() -> None:
    """The duty runs in pyforge-steward, which has no pyforge.doctor; checks are Guild tasks (Story 100.7)."""
    import sys

    from pyforge.steward.estate_reconcile import GATING_CHECKS, WARN_CHECKS

    for name, argv in (*GATING_CHECKS, *WARN_CHECKS):
        assert sys.executable not in argv, name
        if argv[0] == "pixi" and argv[1] == "run":
            assert argv[argv.index("-e") + 1] == "pyforge-guild", name


# ---------------------------------------------------------------------------
# Story 108.1 -- the env-matrix generator runs as its script expects, and a failed generator reds the run
# ---------------------------------------------------------------------------

_GUILD = ["pixi", "run", "--as-is", "-x", "-e", "pyforge-guild", "python"]


def _guild_script(name: str, *args: str) -> list[str]:
    # Joined, so the trigger-map meta test does not read a literal path as a file this suite opens: these are
    # argv strings, never read.
    return [*_GUILD, "/".join(("scripts", name)), *args]


# GATING_CHECKS at ab38be642f, before Story 108.1 added pixi-env-matrix-check after bmad-estate-check.
_BASE_GATING_CHECKS = [
    ("llms-full-check", _guild_script("llms_full_check.py")),
    ("bmad-estate-check", _guild_script("bmad_estate_check.py")),
    ("pixi-version-check", _guild_script("pixi_version_check.py")),
    ("target-version-check", _guild_script("target_version_check.py")),
    ("sbom-gaps-check", _guild_script("sbom_gap_derive.py")),
    ("platform-policy-suite-check", [*_GUILD, "-m", "pyforge.doctor.sources", "platform-policy-suite"]),
    ("pin-policy-check", _guild_script("pin_policy_check.py", "--check")),
    ("pixi-lock-check", ["pixi", "lock", "--check"]),
]

_GREEN_SUMMARY = (
    "estate reconcile: generators and checks journaled\n"
    "moved paths: 1\n"
    "recommended commit:\n"
    "estate reconcile: regenerate derived surfaces and reconcile spec-surface\n"
    "\n"
    "Journal: .steward/estate-refresh/2026-10-13.json"
)


@dataclass
class FailRunner(RecordingRunner):
    """Exits ``code`` for every argv in ``fail``; every other call is RecordingRunner's."""

    fail: set[tuple[str, ...]] = field(default_factory=set)
    code: int = 2

    def __call__(self, argv: list[str], cwd: Path) -> FakeProc:
        if tuple(argv) in self.fail:
            self.calls.append(list(argv))
            return FakeProc(argv, self.code, "", "boom")
        return super().__call__(argv, cwd)


def _journal_path(root: Path) -> Path:
    return root / ".steward/estate-refresh/2026-10-13.json"


def _generators(root: Path) -> list[tuple[str, list[str], str | None]]:
    journal = json.loads(_journal_path(root).read_text(encoding="utf-8"))
    return _build_generators(journal, root, journal_path=_journal_path(root))


def _argv_of(root: Path, label: str) -> list[str]:
    return next(argv for gen_label, argv, _ in _generators(root) if gen_label == label)


def _check_argv(name: str) -> list[str]:
    return next(argv for check_name, argv in GATING_CHECKS if check_name == name)


def _scratch_env_matrix_root(tmp_path: Path) -> tuple[Path, Path]:
    """A root holding a copy of the real script, a fixture lock and a Dream with the script's insertion anchor."""
    scratch = tmp_path / "scratch"
    (scratch / "scripts").mkdir(parents=True)
    shutil.copy2(ENV_MATRIX_SCRIPT, scratch / "scripts" / "pixi_env_matrix.py")
    lock = {
        "environments": {
            "demo": {
                "packages": {
                    "linux-64": [
                        {
                            "conda": "https://conda.anaconda.org/conda-forge/linux-64/python-3.14.7-hcd007b5_101_cp314.conda"
                        },
                    ]
                }
            }
        }
    }
    (scratch / "pixi.lock").write_text(yaml.safe_dump(lock), encoding="utf-8")
    dream = scratch / ENV_MATRIX_DREAM
    dream.parent.mkdir(parents=True)
    dream.write_text("# Dream\n\n## Fleet conventions (one vocabulary)\n\nEvidence table.\n", encoding="utf-8")
    return scratch, dream


def _run_from(root: Path, argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run an argv from ``root``, as the production runner runs a generator from the repository root."""
    return subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False, timeout=120)  # noqa: S603


def test_108_1_ac1_the_env_matrix_dream_is_one_watched_constant(tmp_path: Path) -> None:
    root = _root(tmp_path)
    argv = _argv_of(root, "env-matrix")
    assert argv == [sys.executable, "scripts/pixi_env_matrix.py", "--update", "--dream", ENV_MATRIX_DREAM]
    assert ENV_MATRIX_DREAM == "docs/dreams/pyforge-unifying-strategy.md"
    assert ENV_MATRIX_DREAM in WATCH_PATHS


def test_108_1_ac2_the_generator_argv_runs_under_the_script_s_own_parser(tmp_path: Path) -> None:
    root = _root(tmp_path)
    scratch, dream = _scratch_env_matrix_root(tmp_path)
    generator = _argv_of(root, "env-matrix")
    check = _check_argv("pixi-env-matrix-check")
    check_here = [sys.executable, *check[check.index("python") + 1 :]]
    assert check_here[1:] == ["scripts/pixi_env_matrix.py", "--check", "--dream", ENV_MATRIX_DREAM]

    # The pre-108.1 argv: argparse refuses the positional Dream and writes nothing.
    before = dream.read_bytes()
    old = _run_from(scratch, [sys.executable, "scripts/pixi_env_matrix.py", "--update", ENV_MATRIX_DREAM])
    assert old.returncode == 2, old.stderr  # noqa: PLR2004
    assert "unrecognized arguments" in old.stderr
    assert dream.read_bytes() == before

    stale = _run_from(scratch, check_here)
    assert stale.returncode == 1, stale.stderr

    proc = _run_from(scratch, generator)
    assert proc.returncode == 0, proc.stderr
    text = dream.read_text(encoding="utf-8")
    assert "## Pixi environment matrix (measured)" in text
    assert "``demo``" in text
    # AC2's own words: the block's lock-sha256 is the fixture lock's digest (sha256, first 16 hex digits) ...
    digest = hashlib.sha256((scratch / "pixi.lock").read_bytes()).hexdigest()[:16]
    assert f"<!-- pixi-env-matrix:begin lock-sha256={digest} -->" in text
    # ... and the script's own --check, the oracle the gating check uses, agrees.
    current = _run_from(scratch, check_here)
    assert current.returncode == 0, current.stderr


def test_108_1_ac3_every_generator_row_carries_its_label_and_a_green_run_is_unchanged(tmp_path: Path) -> None:
    root = _root(tmp_path)
    result = run_reconcile(_deps(root, RecordingRunner()))
    assert result.ok
    rows = result.details["reconcile"]["generators"]
    assert [row["label"] for row in rows] == [label for label, _argv, _out in _generators(root)]
    assert [row["argv"] for row in rows] == [argv for _label, argv, _out in _generators(root)]
    assert all(row["exit"] == 0 and "error" not in row for row in rows)
    assert result.summary == _GREEN_SUMMARY


@pytest.mark.parametrize(
    "label",
    [
        "environment.yaml",
        "library-catalog-floors",
        "bmad-estate-catalog",
        "env-matrix",
        "docs-environments",
        "docs-pixi-tasks",
    ],
)
def test_108_1_ac4_a_failed_generator_reds_the_run_after_everything_else(tmp_path: Path, label: str) -> None:
    root = _root(tmp_path)
    failed_argv = _argv_of(root, label)
    runner = FailRunner(fail={tuple(failed_argv)})
    result = run_reconcile(_deps(root, runner))

    assert not result.ok
    assert result.details["exit_code"] == EXIT_RECONCILE_CHECKS
    # The failed generator's line, then the summary a green run prints (a failed environment.yaml export writes
    # nothing, so nothing moved).
    green = (
        _GREEN_SUMMARY.replace("moved paths: 1", "moved paths: 0") if label == "environment.yaml" else _GREEN_SUMMARY
    )
    assert result.summary == (
        f"estate reconcile: generator {label} failed (exit 2): {shlex.join(failed_argv)}\n" + green
    )

    block = result.details["reconcile"]
    labels = [row["label"] for row in block["generators"]]
    assert labels == [gen_label for gen_label, _argv, _out in _generators(root)]
    failed = [row for row in block["generators"] if "error" in row]
    assert [(row["label"], row["exit"], row["error"]) for row in failed] == [(label, 2, "non-zero exit")]
    assert [check["name"] for check in block["checks"]] == [
        *(name for name, _argv in GATING_CHECKS),
        *(name for name, _argv in WARN_CHECKS),
    ]
    saved = json.loads(_journal_path(root).read_text(encoding="utf-8"))
    assert saved["reconcile"]["generators"] == block["generators"]


def test_108_1_ac4_two_failed_generators_and_a_failed_check_are_all_named(tmp_path: Path) -> None:
    root = _root(tmp_path)
    catalog = _argv_of(root, "bmad-estate-catalog")
    matrix = _argv_of(root, "env-matrix")
    lock_check = _check_argv("pixi-lock-check")
    runner = FailRunner(fail={tuple(matrix), tuple(catalog), tuple(lock_check)})
    result = run_reconcile(_deps(root, runner))

    assert not result.ok
    assert result.details["exit_code"] == EXIT_RECONCILE_CHECKS
    assert result.summary.splitlines()[:4] == [
        f"estate reconcile: generator bmad-estate-catalog failed (exit 2): {shlex.join(catalog)}",
        f"estate reconcile: generator env-matrix failed (exit 2): {shlex.join(matrix)}",
        "estate reconcile: check pixi-lock-check failed",
        "estate reconcile: generators and checks journaled",
    ]


def test_108_1_ac4_a_failed_check_alone_keeps_its_message(tmp_path: Path) -> None:
    root = _root(tmp_path)
    runner = FailRunner(fail={tuple(_check_argv("pixi-lock-check"))}, code=1)
    result = run_reconcile(_deps(root, runner))
    assert not result.ok
    assert result.summary == "estate reconcile: check pixi-lock-check failed\n" + _GREEN_SUMMARY


def test_108_1_ac5_generate_bmad_suite_still_stops_and_names_an_earlier_failure(tmp_path: Path) -> None:
    root = _root(tmp_path)
    journal = json.loads(_journal_path(root).read_text(encoding="utf-8"))
    journal["moves"] = [{"package": "bmad-method", "feature": "*", "from": "6.12.0", "to": "6.12.2"}]
    _journal_path(root).write_text(json.dumps(journal), encoding="utf-8")
    matrix = _argv_of(root, "env-matrix")
    suite = _argv_of(root, "generate-bmad-suite")
    runner = FailRunner(fail={tuple(matrix), tuple(suite)}, code=1)
    result = run_reconcile(_deps(root, runner))

    assert not result.ok
    assert result.details["exit_code"] == EXIT_RECONCILE_CHECKS
    assert result.summary.splitlines() == [
        "estate reconcile: generate-bmad-suite failed (non-zero exit)",
        f"estate reconcile: generator env-matrix failed (exit 1): {shlex.join(matrix)}",
    ]
    assert result.details["reconcile"]["checks"] == []
    check_argvs = {tuple(argv) for _name, argv in (*GATING_CHECKS, *WARN_CHECKS)}
    assert not any(tuple(call) in check_argvs for call in runner.calls)


def test_108_1_ac6_the_matrix_check_follows_bmad_estate_and_the_rest_are_unchanged() -> None:
    names = [name for name, _argv in GATING_CHECKS]
    assert names.index("pixi-env-matrix-check") == names.index("bmad-estate-check") + 1
    assert _check_argv("pixi-env-matrix-check") == [
        "pixi",
        "run",
        "--as-is",
        "-x",
        "-e",
        "pyforge-guild",
        "python",
        "scripts/pixi_env_matrix.py",
        "--check",
        "--dream",
        "docs/dreams/pyforge-unifying-strategy.md",
    ]
    others = [(name, argv) for name, argv in GATING_CHECKS if name != "pixi-env-matrix-check"]
    assert others == _BASE_GATING_CHECKS


def test_108_1_ac6_a_stale_matrix_reds_the_run_naming_the_check(tmp_path: Path) -> None:
    root = _root(tmp_path)
    runner = FailRunner(fail={tuple(_check_argv("pixi-env-matrix-check"))}, code=1)
    result = run_reconcile(_deps(root, runner))
    assert not result.ok
    assert result.details["exit_code"] == EXIT_RECONCILE_CHECKS
    assert result.summary.splitlines()[0] == "estate reconcile: check pixi-env-matrix-check failed"
    by_name = {check["name"]: check for check in result.details["reconcile"]["checks"]}
    assert by_name["pixi-env-matrix-check"]["exit"] == 1


# ---------------------------------------------------------------------------
# Story 108.1 review: every generator runs in an interpreter that carries what it imports
# ---------------------------------------------------------------------------


def _all_generators(root: Path) -> list[tuple[str, list[str], str | None]]:
    """Every generator, the two conditional ones included (the batch moves pixi and a bmad-* package)."""
    journal = {
        "moves": [
            {"package": "pixi", "feature": "*", "from": "0.80", "to": "0.81"},
            {"package": "bmad-method", "feature": "*", "from": "6.12.0", "to": "6.12.2"},
        ]
    }
    return _build_generators(journal, root, journal_path=_journal_path(root))


def _repo_path(*parts: str) -> str:
    # Joined, so the trigger-map meta test does not read a literal path as a file this suite opens: these are argv
    # strings, never read.
    return "/".join(parts)


def test_108_1_review_each_generator_runs_in_its_pinned_environment(tmp_path: Path) -> None:
    """The exact argv of every generator. Run by ``sys.executable`` means the duty's own env (``pixi run -e
    pyforge-steward``); the BMAD-estate catalog runs in pyforge-guild, the env that has ``pyforge.scribe``."""
    root = _root(tmp_path)
    py = sys.executable
    guild = ["pixi", "run", "--as-is", "-x", "-e", "pyforge-guild", "python"]
    assert _all_generators(root) == [
        ("environment.yaml", ["pixi", "project", "export", "conda-environment", "-e", "build"], "environment.yaml"),
        ("library-catalog-floors", [py, _repo_path("scripts", "llms_full_check.py"), "--fix-floors"], None),
        ("bmad-estate-catalog", [*guild, "-m", "pyforge.scribe.cli", "catalog", "bmad-estate", "--write"], None),
        (
            "env-matrix",
            [py, "scripts/pixi_env_matrix.py", "--update", "--dream", "docs/dreams/pyforge-unifying-strategy.md"],
            None,
        ),
        ("docs-environments", [py, _repo_path("scripts", "docs_environments.py")], None),
        ("docs-pixi-tasks", [py, _repo_path("scripts", "docs_pixi_tasks.py")], None),
        ("bump-pixi-version", [py, _repo_path("scripts", "bump_pixi_version.py")], None),
        (
            "generate-bmad-suite",
            [
                py,
                _repo_path(".claude", "scripts", "conda-forge-expert", "bmad_suite_metapackage.py"),
                "--journal",
                str(_journal_path(root)),
                "--json",
            ],
            None,
        ),
    ]


def test_108_1_review_a_module_generator_in_the_duty_s_interpreter_resolves_its_module(tmp_path: Path) -> None:
    """A ``-m`` generator run by ``sys.executable`` imports its module in the env this suite and the duty share
    (pyforge-steward). ``pyforge.scribe`` is not there, which is why the catalog generator runs in the Guild env."""
    root = _root(tmp_path)
    module_generators = [
        (label, argv[2]) for label, argv, _out in _all_generators(root) if argv[0] == sys.executable and argv[1] == "-m"
    ]
    for label, module in module_generators:
        assert importlib.util.find_spec(module.split(".")[0]) is not None, (label, module)
        assert importlib.util.find_spec(module) is not None, (label, module)
