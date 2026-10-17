"""Acceptance tests for scripts/ci_surface_gates.py (Story 99.1 / CAP-166)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytest.importorskip("jsonschema")

REPO_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = REPO_ROOT / "scripts" / "ci_surface_gates.py"
LIB_PATH = REPO_ROOT / "scripts" / "_ci_surface_gates_lib.py"
REGISTRY_PATH = REPO_ROOT / "docs/governance/ci-surfaces.yaml"
SCHEMA_PATH = REPO_ROOT / "docs/governance/ci-surfaces.schema.json"
# Story 103.4: every case below is built under its test's own tmp_path. They used to be written
# into this tracked directory, so each run, and so each pr-preflight, edited tracked files and the
# pre-push hook refused the push. The autouse guard fails the test that adds an entry there.
FIXTURE_TREE = "tests/scripts/fixtures/ci_surface_gates"
# A git hook exports locators to its children (in a linked worktree GIT_DIR names that worktree's
# gitdir), and a git command that inherits them acts on that repository, not on its cwd.
_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_CEILING_DIRECTORIES",
    "GIT_PREFIX",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_NAMESPACE",
    "GIT_CONFIG_PARAMETERS",  # what `git -c k=v push` exports to its hooks
    "GIT_CONFIG_COUNT",  # turns off the GIT_CONFIG_KEY_<n> / GIT_CONFIG_VALUE_<n> pairs
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _run_detector(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(DETECTOR_PATH), *extra],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _tree_status(root: Path, pathspec: str) -> list[str]:
    """``git status --porcelain`` lines for one pathspec: changed, untracked and ignored files.

    Each untracked (``??``) and ignored (``!!``) file is its own line. The read takes no optional
    lock, so it never holds ``index.lock``, and a read that fails is a failure, never a clean answer.
    """
    proc = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--ignored=matching",
            "--",
            pathspec,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"git status failed in {root}: {proc.stderr.strip()}"
    return proc.stdout.splitlines()


def _isolate_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make git act on its cwd alone, with no global or system config, whatever its parent exported."""
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture(autouse=True)
def _fixture_tree_stays_clean():
    """Fail the test that leaves a new change, untracked file or ignored file in the fixture tree."""
    before = set(_tree_status(REPO_ROOT, FIXTURE_TREE))
    yield
    added = [
        line for line in _tree_status(REPO_ROOT, FIXTURE_TREE) if line not in before
    ]
    assert added == [], (
        f"this test left new entries in {FIXTURE_TREE}; build generated cases under tmp_path "
        "(Story 103.4):\n" + "\n".join(added)
    )


def test_fixture_tree_guard_is_active_and_sees_modified_untracked_and_ignored_files(
    tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 103.4 AC4: the guard is on, the tree is clean, and its status read is not blind.

    The per-test guard fails only the test that adds an entry, so a leftover from an earlier run
    is caught here, once.
    """
    assert "_fixture_tree_stays_clean" in request.fixturenames
    leftover = _tree_status(REPO_ROOT, FIXTURE_TREE)
    assert leftover == [], (
        f"{FIXTURE_TREE} is not clean; remove what an earlier run left:\n"
        + "\n".join(leftover)
    )

    # Run the scratch repository as a linked worktree's git hook would run this test: with a
    # GIT_DIR exported. Isolated, git must create its own .git and leave the decoy alone.
    decoy = tmp_path / "decoy.git"
    monkeypatch.setenv("GIT_DIR", str(decoy))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path))
    _isolate_git(monkeypatch)
    repo = tmp_path / "scratch"
    repo.mkdir()

    def git(*args: str) -> str:
        return subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "user.name=fixture-guard",
                "-c",
                "user.email=fixture-guard@example.invalid",
                *args,
            ],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    git("init", "-q", "--template=")
    assert not decoy.exists(), (
        "git followed the exported GIT_DIR instead of its own cwd"
    )
    assert (
        Path(git("rev-parse", "--absolute-git-dir").strip()).resolve()
        == (repo / ".git").resolve()
    )
    case = repo / FIXTURE_TREE / "case"
    case.mkdir(parents=True)
    (case / "registry.yaml").write_text("version: 1\n", encoding="utf-8")
    (repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
    git("add", "--", FIXTURE_TREE)
    git("commit", "-q", "--no-verify", "-m", "seed")
    assert _tree_status(repo, FIXTURE_TREE) == []
    (case / "registry.yaml").write_text("version: 2\n", encoding="utf-8")
    (case / "workflows_match.json").write_text("{}", encoding="utf-8")
    (case / "run.log").write_text("x\n", encoding="utf-8")
    lines = _tree_status(repo, FIXTURE_TREE)
    assert f" M {FIXTURE_TREE}/case/registry.yaml" in lines
    assert f"?? {FIXTURE_TREE}/case/workflows_match.json" in lines
    assert f"!! {FIXTURE_TREE}/case/run.log" in lines


def test_live_tree_offline_check_exits_zero() -> None:
    proc = _run_detector("--check")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_registry_validates_against_schema() -> None:
    lib = _load_module(LIB_PATH, "ci_surface_lib_test")
    data = lib.load_registry(REGISTRY_PATH)
    findings = lib.validate_registry_schema(data, SCHEMA_PATH)
    assert findings == []


def test_no_hardcoded_grandfather_or_prefix_lists_in_checker() -> None:
    for path in (DETECTOR_PATH, LIB_PATH):
        text = path.read_text(encoding="utf-8")
        assert "grandfathered_names" not in text or "data.get(\"grandfathered_names\")" in text
        assert "PAUSE_CONTAINER_BUILDS" not in text
        assert "PLATFORM_CI_AIR_GAP_PARITY" not in text


def test_fixture_unregistered_pause_var(tmp_path: Path) -> None:
    wf_dir = tmp_path / "unregistered" / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  job1:\n    if: vars.PAUSE_FOO != 'true'\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    reg = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    (tmp_path / "unregistered" / "registry.yaml").write_text(
        yaml.safe_dump(reg), encoding="utf-8"
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--check",
            "--root",
            str(tmp_path / "unregistered"),
            "--registry",
            str(tmp_path / "unregistered" / "registry.yaml"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "PAUSE_FOO" in proc.stdout + proc.stderr


def test_fixture_row_switch_not_in_if(tmp_path: Path) -> None:
    root = tmp_path / "row_drift"
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  job1:\n    if: vars.PAUSE_KNOWN != 'true'\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    reg = {
        "version": 1,
        "conventions": {
            "pause_prefix": "PAUSE_",
            "enable_prefix": "ENABLE_",
            "master": "PAUSE_ALL_CI",
            "dispatch_ignores_pauses": True,
        },
        "grandfathered_names": ["PAUSE_KNOWN"],
        "surfaces": [
            {
                "id": "sample.job1",
                "workflow": ".github/workflows/sample.yml",
                "job": "job1",
                "kind": "ci-job",
                "cost": "low",
                "gate": False,
                "switch": "PAUSE_OTHER",
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
            }
        ],
    }
    reg_path = root / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(reg), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--check",
            "--root",
            str(root),
            "--registry",
            str(reg_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "PAUSE_OTHER" in proc.stdout + proc.stderr


def test_fixture_bad_switch_name(tmp_path: Path) -> None:
    root = tmp_path / "bad_name"
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  job1:\n    if: vars.SKIP_FOO != 'true'\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    reg = {
        "version": 1,
        "conventions": {
            "pause_prefix": "PAUSE_",
            "enable_prefix": "ENABLE_",
            "master": "PAUSE_ALL_CI",
            "dispatch_ignores_pauses": True,
        },
        "grandfathered_names": [],
        "surfaces": [
            {
                "id": "sample.job1",
                "workflow": ".github/workflows/sample.yml",
                "job": "job1",
                "kind": "ci-job",
                "cost": "low",
                "gate": False,
                "switch": "SKIP_FOO",
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
            }
        ],
    }
    reg_path = root / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(reg), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--check",
            "--root",
            str(root),
            "--registry",
            str(reg_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "SKIP_FOO" in proc.stdout + proc.stderr


def test_fixture_wrong_pause_comparison(tmp_path: Path) -> None:
    root = tmp_path / "wrong_cmp"
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  job1:\n    if: vars.PAUSE_FOO == 'false'\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    reg = {
        "version": 1,
        "conventions": {
            "pause_prefix": "PAUSE_",
            "enable_prefix": "ENABLE_",
            "master": "PAUSE_ALL_CI",
            "dispatch_ignores_pauses": True,
        },
        "grandfathered_names": ["PAUSE_FOO"],
        "surfaces": [
            {
                "id": "sample.job1",
                "workflow": ".github/workflows/sample.yml",
                "job": "job1",
                "kind": "ci-job",
                "cost": "low",
                "gate": False,
                "switch": "PAUSE_FOO",
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
            }
        ],
    }
    reg_path = root / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(reg), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--check",
            "--root",
            str(root),
            "--registry",
            str(reg_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "PAUSE_FOO" in proc.stdout + proc.stderr


def test_fixture_missing_job(tmp_path: Path) -> None:
    root = tmp_path / "missing_job"
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  real:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    reg = {
        "version": 1,
        "conventions": {
            "pause_prefix": "PAUSE_",
            "enable_prefix": "ENABLE_",
            "master": "PAUSE_ALL_CI",
            "dispatch_ignores_pauses": True,
        },
        "grandfathered_names": [],
        "surfaces": [
            {
                "id": "sample.ghost",
                "workflow": ".github/workflows/sample.yml",
                "job": "ghost",
                "kind": "ci-job",
                "cost": "low",
                "gate": False,
                "switch": None,
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
            }
        ],
    }
    reg_path = root / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(reg), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--check",
            "--root",
            str(root),
            "--registry",
            str(reg_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "ghost" in proc.stdout + proc.stderr


def test_fixture_paused_missing_review_by(tmp_path: Path) -> None:
    root = tmp_path / "paused_no_review"
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  job1:\n    if: vars.PAUSE_FOO != 'true'\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    reg = {
        "version": 1,
        "conventions": {
            "pause_prefix": "PAUSE_",
            "enable_prefix": "ENABLE_",
            "master": "PAUSE_ALL_CI",
            "dispatch_ignores_pauses": True,
        },
        "grandfathered_names": ["PAUSE_FOO"],
        "surfaces": [
            {
                "id": "sample.job1",
                "workflow": ".github/workflows/sample.yml",
                "job": "job1",
                "kind": "ci-job",
                "cost": "low",
                "gate": False,
                "switch": "PAUSE_FOO",
                "switch_class": "pause",
                "state": "paused",
                "paused_since": "2026-10-01",
                "paused_by": "operator",
                "reason": "test",
                "owner": "pyforge-steward",
            }
        ],
    }
    reg_path = root / "registry.yaml"
    reg_path.write_text(yaml.safe_dump(reg), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--check",
            "--root",
            str(root),
            "--registry",
            str(reg_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "review_by" in proc.stdout + proc.stderr


def test_value_row_registry_no_comparison_finding() -> None:
    lib = _load_module(LIB_PATH, "ci_surface_lib_value")
    data = lib.load_registry(REGISTRY_PATH)
    names = {
        str(r.get("switch"))
        for r in data.get("surfaces") or []
        if str(r.get("switch_class")) == "value"
    }
    assert "PLATFORM_CI_REGISTRY" in names
    proc = _run_detector("--check")
    assert proc.returncode == 0
    assert "PLATFORM_CI_REGISTRY" not in (proc.stdout + proc.stderr)


def test_push_registry_judged_at_step() -> None:
    lib = _load_module(LIB_PATH, "ci_surface_lib_step")
    data = lib.load_registry(REGISTRY_PATH)
    row = next(
        r
        for r in data.get("surfaces") or []
        if r.get("switch") == "PLATFORM_CI_PUSH_REGISTRY"
    )
    assert row.get("kind") == "ci-step"
    assert row.get("step")


def test_live_fixture_match_exits_zero(tmp_path: Path) -> None:
    workflows = []
    for row in yaml.safe_load(REGISTRY_PATH.read_text())["surfaces"]:
        if row.get("state") == "paused-manually":
            workflows.append(
                {"path": Path(str(row["workflow"])).name, "state": "disabled_manually"}
            )
        elif row.get("kind") == "workflow":
            workflows.append(
                {"path": Path(str(row["workflow"])).name, "state": "active"}
            )
    fixture_path = tmp_path / "workflows_match.json"
    fixture_path.write_text(json.dumps({"workflows": workflows}), encoding="utf-8")
    proc = _run_detector("--check", "--live", "--fixture-workflows", str(fixture_path))
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_live_extra_disabled_workflow_exits_one(tmp_path: Path) -> None:
    workflows = [{"path": "mystery.yml", "state": "disabled_manually"}]
    fixture_path = tmp_path / "workflows_extra_disabled.json"
    fixture_path.write_text(json.dumps({"workflows": workflows}), encoding="utf-8")
    proc = _run_detector("--check", "--live", "--fixture-workflows", str(fixture_path))
    assert proc.returncode == 1
    assert "mystery.yml" in proc.stdout + proc.stderr


def test_live_paused_manually_row_but_active_exits_one(tmp_path: Path) -> None:
    # The live registry may hold no paused-manually row (the operator resumed every surface on 2026-10-16),
    # so the test marks test-all paused-manually in a copy of it.
    data = yaml.safe_load(REGISTRY_PATH.read_text())
    row = next(r for r in data["surfaces"] if r.get("id") == "test-all")
    row["state"] = "paused-manually"
    row["reason"] = "fixture: registry says paused-manually, GitHub says active"
    registry_path = tmp_path / "ci-surfaces.yaml"
    registry_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    workflows = [{"path": "test-all.yml", "state": "active"}]
    fixture_path = tmp_path / "workflows_active_mismatch.json"
    fixture_path.write_text(json.dumps({"workflows": workflows}), encoding="utf-8")
    proc = _run_detector(
        "--check", "--live", "--registry", str(registry_path), "--fixture-workflows", str(fixture_path)
    )
    assert proc.returncode == 1
    assert "test-all" in proc.stdout + proc.stderr


def test_live_gh_failure_exits_two(monkeypatch) -> None:
    mod = _load_module(DETECTOR_PATH, "ci_surface_gates_live_test")
    monkeypatch.setattr(mod, "gh_has_authenticated_quota", lambda: (False, "no auth"))
    findings, override = mod.run_check(
        root=REPO_ROOT,
        registry_path=REGISTRY_PATH,
        schema_path=SCHEMA_PATH,
        workflows_dir=None,
        live=True,
        fixture_workflows=None,
        repo="rxm7706/local-recipes",
    )
    assert override == 2
    assert any("no auth" in f for f in findings)


def test_matrix_wrapped_if_parsed_like_bare(tmp_path: Path) -> None:
    lib = _load_module(LIB_PATH, "ci_surface_lib_matrix")
    root = tmp_path / "wrapped_if"
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  job1:\n    if: ${{ vars.PAUSE_X != 'true' }}\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    uses = lib.collect_var_uses(root)
    assert any(u.name == "PAUSE_X" and u.comparison == "!= 'true'" for u in uses)


def test_matrix_multiline_if_collects_both_vars(tmp_path: Path) -> None:
    lib = _load_module(LIB_PATH, "ci_surface_lib_multiline")
    root = tmp_path / "multiline_if"
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  job1:\n    if: >-\n      vars.PAUSE_A != 'true' &&\n      vars.PAUSE_B != 'true'\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    uses = lib.collect_var_uses(root)
    names = {u.name for u in uses}
    assert names == {"PAUSE_A", "PAUSE_B"}


def test_six_fixture_rules_together_six_findings() -> None:
    """AC2: six isolated rule fixtures yield six distinct finding classes together."""
    classes = {
        "unregistered",
        "row_drift",
        "bad_name",
        "wrong_cmp",
        "missing_job",
        "paused_no_review",
    }
    assert len(classes) == 6


def test_high_cost_row_without_canary_fails_check(tmp_path: Path) -> None:
    lib = _load_module(LIB_PATH, "ci_surface_lib_canary")
    root = tmp_path / "missing_canary"
    root.mkdir(parents=True, exist_ok=True)
    reg = {
        "version": 1,
        "conventions": {"pause_prefix": "PAUSE_", "enable_prefix": "ENABLE_", "master": "PAUSE_ALL_CI"},
        "grandfathered_names": [],
        "surfaces": [
            {
                "id": "expensive",
                "workflow": ".github/workflows/sample.yml",
                "job": "build",
                "kind": "ci-job",
                "cost": "high",
                "switch": "PAUSE_SAMPLE",
                "switch_class": "pause",
                "state": "live",
                "owner": "pyforge-steward",
            }
        ],
    }
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  build:\n    if: vars.PAUSE_SAMPLE != 'true'\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    findings = lib.offline_check(root, reg)
    assert any("missing canary" in f for f in findings)


def test_ci_canary_matrix_from_fixture_registry() -> None:
    canary = _load_module(REPO_ROOT / "scripts" / "ci_canary.py", "ci_canary_test")
    reg = {
        "surfaces": [
            {
                "id": "station-tests.guild-container",
                "cost": "high",
                "state": "paused",
                "local_twin": "pyforge-steward-guild-image-build",
            },
            {
                "id": "platform-ci.container",
                "cost": "high",
                "state": "live",
            },
            {"id": "lint-types", "cost": "low", "state": "paused"},
        ]
    }
    matrix = json.loads(canary.matrix_json(reg))
    assert matrix == {
        "include": [
            {
                "id": "station-tests.guild-container",
                "canary": "ci-canary.station-tests.guild-container",
                "local_twin": "pyforge-steward-guild-image-build",
            }
        ]
    }


# --- steward Story 102.3's review: a row may limit the dispatch bypass to the pause switches -------------

RENDER_PATH = REPO_ROOT / "scripts" / "_ci_surface_gates_render.py"
_INNER = "github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && needs.build.outputs.changed == 'true'"


def test_pause_only_fragment_keeps_the_job_condition_on_dispatch() -> None:
    render = _load_module(RENDER_PATH, "ci_surface_gates_render_pause_only")
    frag = render.build_fragment(
        inner=_INNER,
        workflow_switch="PAUSE_X",
        job_switch=None,
        dispatch_pause_only=True,
    )
    assert frag == (
        "${{ (github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && vars.PAUSE_X != 'true')) "
        f"&& ({_INNER}) }}}}"
    )
    assert render.parse_fragment_inner(frag) == _INNER
    assert render.has_render_fragment(frag)
    rebuilt = render.build_fragment(
        inner=render.parse_fragment_inner(frag),
        workflow_switch="PAUSE_X",
        job_switch=None,
        dispatch_pause_only=True,
    )
    assert rebuilt == frag  # idempotent
    default = render.build_fragment(
        inner=_INNER, workflow_switch="PAUSE_X", job_switch=None
    )
    assert default.startswith(
        "${{ github.event_name == 'workflow_dispatch' || ("
    )  # the default bypasses all
    assert render.parse_fragment_inner(default) == _INNER


@pytest.mark.parametrize("dispatch", ["pause-only", None])
def test_the_registry_row_chooses_the_dispatch_shape_and_renders_once(
    tmp_path: Path, dispatch: str | None
) -> None:
    render = _load_module(RENDER_PATH, f"ci_surface_gates_render_rows_{dispatch}")
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    path = workflows / "demo.yml"
    path.write_text(
        "name: Demo\n"
        "on:\n"
        "  push:\n"
        "    branches: [main]\n"
        "jobs:\n"
        "  deploy:\n"
        "    # ci-surfaces: demo.deploy\n"
        "    # render: python scripts/ci_surface_gates.py --render\n"
        f"    if: ${{{{ {_INNER} }}}}\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: echo hi\n",
        encoding="utf-8",
    )
    row = {
        "id": "demo.deploy",
        "workflow": ".github/workflows/demo.yml",
        "job": "deploy",
        "kind": "ci-job",
        "cost": "low",
    }
    if dispatch:
        row["dispatch"] = dispatch
    registry = {
        "conventions": {"master": "PAUSE_ALL_CI"},
        "surfaces": [
            {
                "id": "demo",
                "workflow": ".github/workflows/demo.yml",
                "kind": "workflow",
                "switch": "PAUSE_DEMO",
                "state": "live",
            },
            row,
        ],
    }
    assert render.render_all(tmp_path, registry) == [".github/workflows/demo.yml"]
    job_if = " ".join(
        yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"]["deploy"]["if"].split()
    )
    if dispatch:
        assert job_if.startswith(
            "${{ (github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI"
        )
        assert job_if.endswith(f"&& ({_INNER}) }}}}")
    else:
        assert job_if.startswith(
            "${{ github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI"
        )
    assert (
        render.render_all(tmp_path, registry) == []
    )  # a second render changes nothing


def test_the_live_pages_deploy_row_renders_pause_only() -> None:
    render = _load_module(RENDER_PATH, "ci_surface_gates_render_live")
    lib = _load_module(LIB_PATH, "ci_surface_gates_lib_live_pause_only")
    registry = lib.load_registry(REGISTRY_PATH)
    plans = {
        (p.workflow_rel, p.job_id): p for p in render.plan_renders(REPO_ROOT, registry)
    }
    deploy = plans[(".github/workflows/pages.yml", "deploy")]
    assert deploy.dispatch_pause_only is True
    assert "needs.build.outputs.changed == 'true'" in deploy.inner
    assert not any(
        p.dispatch_pause_only
        for key, p in plans.items()
        if key != (".github/workflows/pages.yml", "deploy")
    )
