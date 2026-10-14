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
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ci_surface_gates"


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
    )


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


def test_fixture_unregistered_pause_var() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    wf_dir = FIXTURES / "unregistered" / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  job1:\n    if: vars.PAUSE_FOO != 'true'\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    reg = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    (FIXTURES / "unregistered" / "registry.yaml").write_text(
        yaml.safe_dump(reg), encoding="utf-8"
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(DETECTOR_PATH),
            "--check",
            "--root",
            str(FIXTURES / "unregistered"),
            "--registry",
            str(FIXTURES / "unregistered" / "registry.yaml"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "PAUSE_FOO" in proc.stdout + proc.stderr


def test_fixture_row_switch_not_in_if() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    root = FIXTURES / "row_drift"
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
    )
    assert proc.returncode == 1
    assert "PAUSE_OTHER" in proc.stdout + proc.stderr


def test_fixture_bad_switch_name() -> None:
    root = FIXTURES / "bad_name"
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
    )
    assert proc.returncode == 1
    assert "SKIP_FOO" in proc.stdout + proc.stderr


def test_fixture_wrong_pause_comparison() -> None:
    root = FIXTURES / "wrong_cmp"
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
    )
    assert proc.returncode == 1
    assert "PAUSE_FOO" in proc.stdout + proc.stderr


def test_fixture_missing_job() -> None:
    root = FIXTURES / "missing_job"
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
    )
    assert proc.returncode == 1
    assert "ghost" in proc.stdout + proc.stderr


def test_fixture_paused_missing_review_by() -> None:
    root = FIXTURES / "paused_no_review"
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


def test_live_fixture_match_exits_zero() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
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
    fixture_path = FIXTURES / "workflows_match.json"
    fixture_path.write_text(json.dumps({"workflows": workflows}), encoding="utf-8")
    proc = _run_detector("--check", "--live", "--fixture-workflows", str(fixture_path))
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_live_extra_disabled_workflow_exits_one() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    workflows = [{"path": "mystery.yml", "state": "disabled_manually"}]
    fixture_path = FIXTURES / "workflows_extra_disabled.json"
    fixture_path.write_text(json.dumps({"workflows": workflows}), encoding="utf-8")
    proc = _run_detector("--check", "--live", "--fixture-workflows", str(fixture_path))
    assert proc.returncode == 1
    assert "mystery.yml" in proc.stdout + proc.stderr


def test_live_paused_manually_row_but_active_exits_one() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    workflows = [{"path": "test-all.yml", "state": "active"}]
    fixture_path = FIXTURES / "workflows_active_mismatch.json"
    fixture_path.write_text(json.dumps({"workflows": workflows}), encoding="utf-8")
    proc = _run_detector("--check", "--live", "--fixture-workflows", str(fixture_path))
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


def test_matrix_wrapped_if_parsed_like_bare() -> None:
    lib = _load_module(LIB_PATH, "ci_surface_lib_matrix")
    root = FIXTURES / "wrapped_if"
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "sample.yml").write_text(
        "jobs:\n  job1:\n    if: ${{ vars.PAUSE_X != 'true' }}\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        encoding="utf-8",
    )
    uses = lib.collect_var_uses(root)
    assert any(u.name == "PAUSE_X" and u.comparison == "!= 'true'" for u in uses)


def test_matrix_multiline_if_collects_both_vars() -> None:
    lib = _load_module(LIB_PATH, "ci_surface_lib_multiline")
    root = FIXTURES / "multiline_if"
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


def test_high_cost_row_without_canary_fails_check() -> None:
    lib = _load_module(LIB_PATH, "ci_surface_lib_canary")
    root = FIXTURES / "missing_canary"
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
