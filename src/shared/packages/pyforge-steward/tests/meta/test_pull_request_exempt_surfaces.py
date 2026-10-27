"""Stories 117.6 and 117.8 (spec-pyforge-steward CAP-175, operator ruling D1 of 2026-10-27): the image builds and the
CFE regression net never run on a pull_request.

The registry (``docs/governance/ci-surfaces.yaml``) says so with ``trigger: main`` on each row; this test reads those rows
and proves three things against the live tree: each job's ``if:`` keeps it off a pull_request, the nightly canary's
matrix (``scripts/ci_canary.py``) builds every high-cost one, and the pull-request lane that replaces the CFE net
(``cfe-meta``) runs only on a pull_request. A row that gains ``trigger: main`` without the workflow following, or a job
that quietly returns to the PR path, reds here.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.live_tree

REPO_ROOT = Path(__file__).resolve().parents[6]
REGISTRY = REPO_ROOT / "docs" / "governance" / "ci-surfaces.yaml"
CANARY = REPO_ROOT / "scripts" / "ci_canary.py"

_OFF_PR = re.compile(r"github\.event_name\s*!=\s*'pull_request'|github\.event_name\s*==\s*'push'")


def _rows() -> list[dict]:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    return [r for r in data["surfaces"] if isinstance(r, dict)]


def _job_if(row: dict) -> str:
    doc = yaml.safe_load((REPO_ROOT / row["workflow"]).read_text(encoding="utf-8"))
    job = doc["jobs"][row["job"]]
    return " ".join(str(job.get("if", "")).split())


def _main_rows() -> list[dict]:
    rows = [r for r in _rows() if r.get("trigger") == "main"]
    assert rows, "no registry row carries trigger: main"
    return rows


def test_the_d1_surfaces_carry_trigger_main() -> None:
    ids = {r["id"] for r in _main_rows()}
    assert {
        "station-tests.guild-container",
        "platform-ci.container",
        "platform-ci.container-dbgpt",
        "platform-ci.golden-path-promotion",
        "cfe-regression-net.cfe-regression-net",
    } <= ids


@pytest.mark.parametrize("row", _main_rows(), ids=lambda r: r["id"])
def test_a_trigger_main_job_never_runs_on_a_pull_request(row: dict) -> None:
    condition = _job_if(row)
    assert _OFF_PR.search(condition), f"{row['id']}: {condition!r} does not keep the job off a pull_request"


def test_the_nightly_canary_builds_every_high_cost_trigger_main_surface() -> None:
    spec = importlib.util.spec_from_file_location("ci_canary_live", CANARY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    built = {entry["id"] for entry in json.loads(module.matrix_json(registry))["include"]}
    expected = {r["id"] for r in _main_rows() if r.get("cost") == "high"}
    assert expected <= built, sorted(expected - built)


def test_the_canary_runs_nightly() -> None:
    doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci-canary.yml").read_text(encoding="utf-8"))
    crons = (
        [entry["cron"] for entry in doc[True]["schedule"]]
        if True in doc
        else [entry["cron"] for entry in doc["on"]["schedule"]]
    )
    assert crons == ["0 4 * * *"], crons


def test_the_cfe_meta_lane_runs_only_on_a_pull_request() -> None:
    row = next(r for r in _rows() if r["id"] == "cfe-regression-net.cfe-meta")
    condition = _job_if(row)
    assert "github.event_name == 'pull_request'" in condition, condition
    doc = yaml.safe_load((REPO_ROOT / row["workflow"]).read_text(encoding="utf-8"))
    runs = " ".join(str(s.get("run", "")) for s in doc["jobs"]["cfe-meta"]["steps"])
    assert "test-ci-meta" in runs
