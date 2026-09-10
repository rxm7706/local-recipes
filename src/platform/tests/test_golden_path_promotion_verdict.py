"""Story 12.5 — golden-path promotion verdict is honest and specific (CAP-4)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest

from tests.policy import readers

if TYPE_CHECKING:
    from pathlib import Path
from tests.test_golden_path_promotion_closure import _ENVIRONMENT
from tests.test_golden_path_promotion_closure import _PLATFORM
from tests.test_golden_path_promotion_closure import _ROOT_PIXI_LOCK
from tests.test_golden_path_promotion_osv_db import _golden_path_job_block
from tests.test_golden_path_promotion_osv_db import _load_osv_db_builder

_REPO_ROOT = readers.REPO_ROOT
_PROMOTION_SCRIPT = _REPO_ROOT / "scripts" / "platform-golden-path-promotion.sh"
_VULN_CRITICAL = (
    _REPO_ROOT
    / "src/shared/packages/pyforge-warden/tests/fixtures/projects/vuln_critical"
)
_CLEAN_PROJECT = (
    _REPO_ROOT / "src/shared/packages/pyforge-warden/tests/fixtures/projects/clean"
)
_OSV_RECORDS = (
    _REPO_ROOT / "src/shared/packages/pyforge-warden/tests/fixtures/osv-db/pypi"
)
_DB_MAX_AGE_SECONDS = 7 * 24 * 3600


def _run_warden_scan(
    target: Path,
    *,
    env: dict[str, str] | None = None,
    extra_args: list[str] | None = None,
) -> tuple[int, dict]:
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
    if extra_args:
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


def _vuln_coverage(report: dict) -> dict:
    for row in report.get("coverage", []):
        if row.get("axis") == "vulnerability":
            return row
    msg = "vulnerability coverage row missing"
    raise AssertionError(msg)


def _provisioned_env(tmp_path: Path) -> dict[str, str]:
    builder = _load_osv_db_builder()
    cache_root = tmp_path / "cache"
    builder.build_offline_db(_OSV_RECORDS, cache_root)
    return {"OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY": str(cache_root)}


def _ambient_warden_env(tmp_path: Path) -> dict[str, str]:
    """Mirror warden test conftest ambient OSV + KEV + currency feeds."""
    env = _provisioned_env(tmp_path)
    feed_root = tmp_path / "feeds"
    runtime_version = ".".join(str(part) for part in sys.version_info[:3])
    setup = f"""
from pyforge.warden.feeds import write_endoflife_cache, write_kev_cache

feed_root = {str(feed_root)!r}

def _clean_cycle(version):
    return [{{
        "cycle": version,
        "releaseDate": "2020-01-01",
        "eol": "2099-01-01",
        "latest": version,
    }}]

write_kev_cache(feed_root, {{"vulnerabilities": []}})
write_endoflife_cache(
    feed_root,
    {{
        "requests": _clean_cycle("2.31.0"),
        "packaging": _clean_cycle("24.0"),
        "python": _clean_cycle({runtime_version!r}),
    }},
)
"""
    subprocess.run(  # noqa: S603 -- fixed argv, no shell
        ["pixi", "run", "-e", "pyforge-warden", "python", "-c", setup],  # noqa: S607 -- resolved via PATH like every other pixi invocation in this suite
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    env["PYFORGE_WARDEN_FEED_CACHE_DIR"] = str(feed_root)
    return env


def _lockfile_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    shutil.copy2(_ROOT_PIXI_LOCK, workspace / "pixi.lock")
    return workspace


@pytest.mark.skipif(not _ROOT_PIXI_LOCK.is_file(), reason="repo root pixi.lock missing")
def test_provisioned_db_assesses_vulnerability_axis(tmp_path: Path) -> None:
    """With OSV DB provisioned, the promotion closure has deps_assessed > 0."""
    workspace = _lockfile_workspace(tmp_path)
    _rc, report = _run_warden_scan(
        workspace,
        env=_provisioned_env(tmp_path),
    )
    vuln = _vuln_coverage(report)
    assert vuln["deps_assessed"] > 0
    assert vuln["deps_total"] == report["inventory_count"]
    status = report["status"]["value"]
    if status == "clean":
        assert vuln["deps_assessed"] == vuln["deps_total"]
    else:
        assert vuln["deps_assessed"] > 0


@pytest.mark.skipif(not _ROOT_PIXI_LOCK.is_file(), reason="repo root pixi.lock missing")
def test_missing_db_names_offline_db_unavailable(tmp_path: Path) -> None:
    """Without OSV DB, vulnerability assessment is zero and gaps are named."""
    workspace = _lockfile_workspace(tmp_path)
    env = {
        k: v
        for k, v in os.environ.items()
        if k != "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY"
    }
    _rc, report = _run_warden_scan(workspace, env=env)
    vuln = _vuln_coverage(report)
    assert vuln["deps_assessed"] == 0
    finding_ids = {finding["id"] for finding in report.get("findings", [])}
    assert any("offline-db-unavailable" in fid for fid in finding_ids)
    assert report["status"]["value"] == "indeterminate"
    driver = report["status"].get("driver") or {}
    assert "offline-db-unavailable" in (driver.get("finding_id") or "")


def test_stale_db_routes_to_vuln_data_stale(tmp_path: Path) -> None:
    """A DB older than db-max-age yields vuln-data-stale, never silent clean."""
    builder = _load_osv_db_builder()
    cache_root = tmp_path / "cache"
    builder.build_offline_db(_OSV_RECORDS, cache_root)
    zip_path = cache_root / "osv-scanner" / "PyPI" / "all.zip"
    stale_mtime = time.time() - _DB_MAX_AGE_SECONDS - 3600
    os.utime(zip_path, (stale_mtime, stale_mtime))

    _rc, report = _run_warden_scan(
        _CLEAN_PROJECT,
        env={"OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY": str(cache_root)},
        extra_args=[],
    )
    finding_ids = {finding["id"] for finding in report.get("findings", [])}
    assert "indeterminate:vuln-data-stale:vuln-database" in finding_ids
    assert report["status"]["value"] == "indeterminate"


def test_vulnerable_pin_surfaces_failing_rung(tmp_path: Path) -> None:
    """A pinned vulnerable version composes a failing rung naming the finding."""
    _rc, report = _run_warden_scan(
        _VULN_CRITICAL,
        env=_provisioned_env(tmp_path),
        extra_args=[],
    )
    finding_id = "vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0"
    finding_ids = {finding["id"] for finding in report.get("findings", [])}
    assert finding_id in finding_ids
    assert report["status"]["value"] == "policy-violation"
    driver = report["status"]["driver"]
    assert driver is not None
    assert driver["finding_id"] == finding_id


def test_clean_status_implies_full_vulnerability_assessment(tmp_path: Path) -> None:
    """When status is clean, vulnerability deps_assessed equals deps_total."""
    _rc, report = _run_warden_scan(
        _CLEAN_PROJECT,
        env=_ambient_warden_env(tmp_path),
        extra_args=[],
    )
    assert report["status"]["value"] == "clean"
    vuln = _vuln_coverage(report)
    assert vuln["deps_assessed"] == vuln["deps_total"]
    assert vuln["deps_total"] == report["inventory_count"]


@pytest.mark.skipif(not _ROOT_PIXI_LOCK.is_file(), reason="repo root pixi.lock missing")
def test_not_clean_verdict_names_unmapped_ecosystem_gaps(tmp_path: Path) -> None:
    """The real promotion closure names UNMAPPED_ECOSYSTEM withholds when not clean."""
    workspace = _lockfile_workspace(tmp_path)
    _rc, report = _run_warden_scan(
        workspace,
        env=_provisioned_env(tmp_path),
    )
    assert report["status"]["value"] != "clean"
    finding_ids = {finding["id"] for finding in report.get("findings", [])}
    assert any("unmapped-ecosystem" in fid for fid in finding_ids)
    driver = report["status"].get("driver") or {}
    assert driver.get("finding_id")


def test_promotion_record_copies_warden_status(tmp_path: Path) -> None:
    """Promotion JSON assembly mirrors warden.status.value to warden_status."""
    warden_path = tmp_path / "warden.json"
    warden_path.write_text(
        json.dumps(
            {
                "status": {
                    "value": "indeterminate",
                    "driver": {"finding_id": "indeterminate:offline-db-unavailable:x"},
                },
                "inventory_count": 1,
            }
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update(
        {
            "PLATFORM_REF": "platform:tag",
            "SIDECAR_REF": "sidecar:tag",
            "MCP_HOST_REF": "mcp:tag",
            "PLATFORM_DIGEST": "sha256:platform",
            "SIDECAR_DIGEST": "sha256:sidecar",
            "MCP_HOST_DIGEST": "sha256:mcp",
            "WARDEN_EXIT": "1",
        }
    )
    out_path = tmp_path / "record.json"
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        [  # noqa: S607 -- resolved via PATH like every other pixi invocation in this suite
            "python",
            "-",
            str(warden_path),
            str(out_path),
        ],
        cwd=_REPO_ROOT,
        env=env,
        input=_PROMOTION_PAYLOAD_SNIPPET,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["warden_status"] == "indeterminate"
    assert payload["warden_exit_code"] == 1
    assert payload["warden"]["status"]["value"] == "indeterminate"


_PROMOTION_PAYLOAD_SNIPPET = """\
import json
import os
import sys
from datetime import UTC, datetime

warden_path = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else ""

payload = {
    "schema": "platform-golden-path-promotion/v1",
    "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    "git_sha": os.environ.get("GITHUB_SHA", ""),
    "run_id": os.environ.get("GITHUB_RUN_ID", ""),
    "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
    "images": {
        "platform": {
            "ref": os.environ["PLATFORM_REF"],
            "digest": os.environ["PLATFORM_DIGEST"],
        },
        "sidecar": {
            "ref": os.environ["SIDECAR_REF"],
            "digest": os.environ["SIDECAR_DIGEST"],
        },
        "mcpHost": {
            "ref": os.environ["MCP_HOST_REF"],
            "digest": os.environ["MCP_HOST_DIGEST"],
        },
    },
    "warden": json.load(open(warden_path, encoding="utf-8")),
}
payload["warden_exit_code"] = int(os.environ.get("WARDEN_EXIT", "0"))
payload["warden_status"] = (payload["warden"].get("status") or {}).get("value")
text = json.dumps(payload, indent=2, sort_keys=True) + "\\n"
if out_path:
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(text)
"""


def test_no_fail_under_coverage_on_golden_path() -> None:
    """CAP-4 forbids a coverage floor — assert absent from script and CI job."""
    script_text = _PROMOTION_SCRIPT.read_text(encoding="utf-8")
    block = _golden_path_job_block()
    combined = script_text + block
    assert "fail-under-coverage" not in combined
    assert "fail_under_coverage" not in combined
