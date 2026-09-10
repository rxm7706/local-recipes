"""Story 12.6 — deploy gate preserved under honest promotion verdicts (CAP-5).

Bridges the promotion record assembly path (Stories 12.3-12.5) to the deploy
verifier (Story 12.1). Synthetic-only regression lives in
``test_deploy_verify_promotion_clean_only.py``; this suite proves the two
halves land together: whatever Warden composed is what deploy judges, and
``warn`` never bypasses the gate.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.test_golden_path_promotion_closure import _ENVIRONMENT
from tests.test_golden_path_promotion_closure import _PLATFORM
from tests.test_golden_path_promotion_closure import _ROOT_PIXI_LOCK
from tests.test_golden_path_promotion_verdict import _PROMOTION_PAYLOAD_SNIPPET
from tests.test_golden_path_promotion_verdict import _ambient_warden_env

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VERIFY_SCRIPT = _REPO_ROOT / "scripts" / "platform-deploy-verify-promotion.py"
_PROMOTION_SCRIPT = _REPO_ROOT / "scripts" / "platform-golden-path-promotion.sh"
_DEPLOY_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "platform-deploy.yml"
_CLEAN_PROJECT = (
    _REPO_ROOT / "src/shared/packages/pyforge-warden/tests/fixtures/projects/clean"
)
_DIGEST = "sha256:" + ("b" * 64)
_DRIVER_ID = "warn:vuln:CVE-2024-9999:pkg"


def _run_warden_scan(
    target: Path,
    *,
    env: dict[str, str] | None = None,
    extra_args: list[str] | None = None,
) -> tuple[int, dict[str, Any]]:
    command = [
        "pixi",
        "run",
        "-e",
        "pyforge-warden",
        "warden",
        "scan",
        str(target),
        "--format",
        "json",
    ]
    if extra_args is not None:
        command.extend(extra_args)
    else:
        command.extend(
            [
                "--pixi-environment",
                _ENVIRONMENT,
                "--pixi-platform",
                _PLATFORM,
            ]
        )
    run_env = os.environ.copy()
    if env is not None:
        run_env.update(env)
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        command,
        cwd=_REPO_ROOT,
        env=run_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1, 2), result.stderr
    return result.returncode, json.loads(result.stdout)


def _assemble_promotion_record(
    tmp_path: Path,
    warden_report: dict[str, Any],
    *,
    warden_exit: int,
) -> Path:
    warden_path = tmp_path / "warden.json"
    warden_path.write_text(json.dumps(warden_report), encoding="utf-8")
    out_path = tmp_path / "golden-path-promotion.json"
    env = os.environ.copy()
    env.update(
        {
            "PLATFORM_REF": "platform:tag",
            "SIDECAR_REF": "sidecar:tag",
            "MCP_HOST_REF": "mcp:tag",
            "PLATFORM_DIGEST": _DIGEST,
            "SIDECAR_DIGEST": _DIGEST,
            "MCP_HOST_DIGEST": _DIGEST,
            "WARDEN_EXIT": str(warden_exit),
        }
    )
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        [sys.executable, "-", str(warden_path), str(out_path)],
        cwd=_REPO_ROOT,
        env=env,
        input=_PROMOTION_PAYLOAD_SNIPPET,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return out_path


def _run_deploy_verifier(promotion_path: Path) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PROMOTION_JSON": str(promotion_path),
        "PLATFORM_DIGEST": _DIGEST,
        "SIDECAR_DIGEST": _DIGEST,
        "MCP_HOST_DIGEST": _DIGEST,
    }
    return subprocess.run(  # noqa: S603 -- fixed argv, no shell
        [sys.executable, str(_VERIFY_SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_refused(result: subprocess.CompletedProcess[str], *, status: str) -> None:
    assert result.returncode != 0
    assert status in result.stderr
    assert "does not promote" in result.stderr
    assert result.stderr.startswith("::error::")


def _scoped_lockfile_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    shutil.copy2(_ROOT_PIXI_LOCK, workspace / "pixi.lock")
    return workspace


@pytest.mark.skipif(not _ROOT_PIXI_LOCK.is_file(), reason="repo root pixi.lock missing")
def test_honest_non_clean_promotion_record_is_refused_by_deploy(
    tmp_path: Path,
) -> None:
    """Real scoped scan → promotion assembly → deploy verifier refuses."""
    workspace = _scoped_lockfile_workspace(tmp_path)
    warden_exit, report = _run_warden_scan(workspace)
    status = (report.get("status") or {}).get("value")
    assert status != "clean", "repo closure unexpectedly clean without full DB"
    promotion_path = _assemble_promotion_record(
        tmp_path, report, warden_exit=warden_exit
    )
    payload = json.loads(promotion_path.read_text(encoding="utf-8"))
    assert payload["warden_status"] == status

    result = _run_deploy_verifier(promotion_path)
    driver = ((report.get("status") or {}).get("driver") or {}).get("finding_id")
    assert driver, "expected driver finding_id on non-clean verdict"
    _assert_refused(result, status=status)
    assert driver in result.stderr


def test_warn_verdict_with_waiver_metadata_still_refused_at_deploy(
    tmp_path: Path,
) -> None:
    """Deploy has no waiver override — warn never promotes."""
    warden_report = {
        "status": {
            "value": "warn",
            "driver": {"finding_id": _DRIVER_ID},
        },
        "waivers": [{"finding_id": _DRIVER_ID, "active": True}],
    }
    promotion_path = _assemble_promotion_record(tmp_path, warden_report, warden_exit=1)
    result = _run_deploy_verifier(promotion_path)
    _assert_refused(result, status="warn")
    assert _DRIVER_ID in result.stderr


def test_clean_promotion_record_from_real_scan_is_accepted_by_deploy(
    tmp_path: Path,
) -> None:
    warden_exit, report = _run_warden_scan(
        _CLEAN_PROJECT,
        env=_ambient_warden_env(tmp_path),
        extra_args=[],
    )
    assert (report.get("status") or {}).get("value") == "clean"
    promotion_path = _assemble_promotion_record(
        tmp_path, report, warden_exit=warden_exit
    )
    result = _run_deploy_verifier(promotion_path)
    assert result.returncode == 0, result.stderr
    assert "clean Warden verdict" in result.stdout


def test_promotion_script_copies_warden_status_to_top_level() -> None:
    """Guard against drift between CI assembly and the shared test heredoc."""
    script_text = _PROMOTION_SCRIPT.read_text(encoding="utf-8")
    assert 'payload["warden_status"]' in script_text
    assert '(payload["warden"].get("status") or {}).get("value")' in script_text


def test_platform_deploy_runs_verifier_before_helm_template() -> None:
    workflow = yaml.safe_load(_DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["deploy"]["steps"]
    step_names = [step.get("name", "") for step in steps]
    verify_idx = next(
        i for i, name in enumerate(step_names) if "Warden verdict" in name
    )
    helm_idx = next(i for i, name in enumerate(step_names) if "helm template" in name)
    download_idx = next(
        i
        for i, step in enumerate(steps)
        if step.get("uses", "").startswith("actions/download-artifact")
    )
    assert download_idx < verify_idx < helm_idx
    verify_step = steps[verify_idx]
    assert "platform-deploy-verify-promotion.py" in (verify_step.get("run") or "")
