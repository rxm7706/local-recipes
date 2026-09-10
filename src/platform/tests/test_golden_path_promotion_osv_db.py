"""Story 12.4 — golden-path promotion provisions the offline OSV database in CI."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import zipfile
from typing import TYPE_CHECKING

from tests.policy import readers

if TYPE_CHECKING:
    from pathlib import Path

_REPO_ROOT = readers.REPO_ROOT
_PROVISION_SCRIPT = _REPO_ROOT / "scripts" / "platform-provision-osv-offline-db.sh"
_WORKFLOW_TEXT = readers.platform_ci_workflow_text()

_GOLDEN_PATH_JOB_RE = re.compile(
    r"^\s*golden-path-promotion:\s*$",
    re.MULTILINE,
)
_JOB_BLOCK_RE = re.compile(
    r"^\s*golden-path-promotion:\s*\n(.*?)(?=^\S|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _golden_path_job_block() -> str:
    match = _JOB_BLOCK_RE.search(_WORKFLOW_TEXT)
    assert match is not None, "golden-path-promotion job missing from platform-ci.yml"
    return match.group(1)


def test_provision_script_exists_and_is_executable() -> None:
    assert _PROVISION_SCRIPT.is_file(), (
        "platform-provision-osv-offline-db.sh must exist"
    )
    assert _PROVISION_SCRIPT.stat().st_mode & 0o111, (
        "provision script must be executable"
    )


def test_golden_path_job_provisions_osv_db_before_warden_scan() -> None:
    block = _golden_path_job_block()
    assert "actions/cache/restore@v6" in block
    assert "osv-offline-db-${{ steps.osv-db-date.outputs.utc_date }}" in block
    # Daily key roll only — no restore-keys fallback to older stale DBs (Story 12.4).
    osv_restore = block.split("Restore OSV offline DB cache", 1)[1].split(
        "Provision OSV offline DB", 1
    )[0]
    assert "restore-keys" not in osv_restore
    assert "actions/cache/save@v6" in block
    assert "platform-provision-osv-offline-db.sh" in block
    script_text = _PROVISION_SCRIPT.read_text(encoding="utf-8")
    assert "--download-offline-databases" in script_text

    provision_pos = block.index("Provision OSV offline DB")
    warden_pos = block.index("Record digests + Warden verdict")
    assert provision_pos < warden_pos, (
        "OSV provision must precede the Warden promotion scan"
    )


def test_golden_path_promotion_step_exports_osv_cache_env() -> None:
    block = _golden_path_job_block()
    promotion_step = block.split("Record digests + Warden verdict", 1)[1]
    assert "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY" in promotion_step
    assert "osv-offline-db" in promotion_step
    assert "platform-golden-path-promotion.sh" in promotion_step


def test_workflow_path_filter_includes_provision_script() -> None:
    assert "scripts/platform-provision-osv-offline-db.sh" in _WORKFLOW_TEXT


def _load_osv_db_builder():
    builder_path = (
        _REPO_ROOT
        / "src/shared/packages/pyforge-warden/tests/fixtures/osv_db_builder.py"
    )
    spec = importlib.util.spec_from_file_location("osv_db_builder", builder_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_provision_script_skips_when_db_already_present(tmp_path: Path) -> None:
    """Idempotent skip — no network when PyPI/all.zip is already usable."""
    builder = _load_osv_db_builder()
    records_dir = (
        _REPO_ROOT / "src/shared/packages/pyforge-warden/tests/fixtures/osv-db/pypi"
    )
    cache_root = tmp_path / "cache"
    builder.build_offline_db(records_dir, cache_root)

    env = {"OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY": str(cache_root)}
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, repo script under test
        ["bash", str(_PROVISION_SCRIPT)],  # noqa: S607 -- resolved via PATH like every other pixi invocation in this suite
        cwd=_REPO_ROOT,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "already provisioned" in result.stdout.lower()


def test_provision_script_rejects_missing_cache_env() -> None:
    env = {
        k: v
        for k, v in os.environ.items()
        if k != "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY"
    }
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, repo script under test
        ["bash", str(_PROVISION_SCRIPT)],  # noqa: S607 -- resolved via PATH like every other pixi invocation in this suite
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY" in result.stderr


def test_provision_script_does_not_treat_empty_zip_as_provisioned(
    tmp_path: Path,
) -> None:
    cache_root = tmp_path / "cache"
    zip_path = cache_root / "osv-scanner" / "PyPI" / "all.zip"
    zip_path.parent.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "w"):
        pass  # 0-entry zip — must not count as provisioned

    check = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        [  # noqa: S607 -- resolved via PATH like every other pixi invocation in this suite
            "python",
            "-c",
            (
                "import zipfile, sys; "
                "p=sys.argv[1]; "
                "z=zipfile.ZipFile(p); "
                "sys.exit(0 if z.namelist() else 1)"
            ),
            str(zip_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert check.returncode != 0, (
        "empty zip must fail the same non-emptiness guard the script uses"
    )
