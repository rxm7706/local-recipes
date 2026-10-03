"""Story 27.1 / DW-FU-23-5 — derived_artifacts via Kedro session (offline fixtures)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pandas as pd
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[8]
_MEMBER_DIR = Path(__file__).resolve().parents[4]
_FIXTURE_CATALOG = _REPO_ROOT / "scripts/tests/fixtures/inventory_universe/catalog"
_REAL_DATA = _MEMBER_DIR / "data"
_LOW_FLOOR = {
    "verification_sets": {"cf_or_pm_floor": 0, "pypi_universe_floor": 0},
    "inventory_verified_packages": {"verification_timestamp_utc": "2026-08-30T12:00:00Z"},
    "inventory_aoss_free_queue": {"verification_timestamp_utc": "2026-08-30T12:00:00Z"},
}
_CREDENTIALS_KEY_RE = re.compile(r"^\s*credentials:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")
_STUB_PAIR = '["stub-user", "not-a-real-credential"]'


def _read(rel: str) -> pd.DataFrame:
    return pd.read_parquet(_FIXTURE_CATALOG / rel)


def _required_credential_keys(catalog: Path) -> list[str]:
    if not catalog.is_file():
        return []
    found = {
        m.group(1)
        for line in catalog.read_text(encoding="utf-8").splitlines()
        if (m := _CREDENTIALS_KEY_RE.match(line))
    }
    return sorted(found)


def _seed_stub_credentials(project_root: Path) -> None:
    cred_path = project_root / "conf" / "local" / "credentials.yml"
    if cred_path.exists():
        return
    keys = _required_credential_keys(project_root / "conf" / "base" / "catalog.yml")
    if not keys:
        return
    cred_path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"{key}: {_STUB_PAIR}" for key in keys)
    cred_path.write_text(f"{body}\n", encoding="utf-8")


def _copy_kedro_project(tmp_path: Path) -> Path:
    dest = tmp_path / "pyforge-atlas"
    ignore = shutil.ignore_patterns(
        "data",
        ".pixi",
        "__pycache__",
        ".pytest_cache",
        "*.egg-info",
        ".venv",
    )
    shutil.copytree(_MEMBER_DIR, dest, ignore=ignore)
    _seed_stub_credentials(dest)
    return dest


def _load_fixture_inputs() -> dict[str, pd.DataFrame]:
    priority = pd.DataFrame(
        [
            {
                "core_python_package_name": "widget",
                "P": "P9",
                "Rank": 1,
                "Score": 90,
                "Work": "Already packaged",
            }
        ]
    )
    empty_jfrog = pd.DataFrame(columns=["core_python_package_name"])
    empty_maint = pd.DataFrame(columns=["core_python_package_name"])
    return {
        "inventory_universe": _read("derived/inventory_universe/inventory_universe.parquet"),
        "core_packages_enumerated": _read("intermediate/core_packages_enumerated/core_packages_enumerated.parquet"),
        "pypi_universe": _read("intermediate/pypi_universe/pypi_universe.parquet"),
        "pypi_conda_mapping": _read("primary/pypi_conda_mapping/pypi_conda_mapping.parquet"),
        "inventory_priority_assignments": priority,
        "enterprise_jfrog_consumption": empty_jfrog,
        "enterprise_conda_maintainers": empty_maint,
    }


@pytest.mark.skipif(not _FIXTURE_CATALOG.is_dir(), reason="fixture catalog missing")
def test_derived_artifacts_inventory_slice_via_kedro_session(tmp_path: Path):
    from kedro.framework.session import KedroSession
    from kedro.framework.startup import bootstrap_project

    marker = _REAL_DATA / "derived/inventory_verified_packages/inventory_verified_packages.parquet"
    mtime_before = marker.stat().st_mtime_ns if marker.is_file() else None

    project_path = _copy_kedro_project(tmp_path)
    bootstrap_project(project_path)
    frames = _load_fixture_inputs()

    with KedroSession.create(project_path=project_path, runtime_params=_LOW_FLOOR) as session:
        catalog = session.load_context().catalog
        for name, frame in frames.items():
            catalog.save(name, frame)

        session.run(
            pipeline_name="derived_artifacts",
            node_names=[
                "build_inventory_verified_packages",
                "build_inventory_aoss_free_queue",
            ],
        )

        verified = catalog.load("inventory_verified_packages")
        queue = catalog.load("inventory_aoss_free_queue")

    assert isinstance(verified, pd.DataFrame) and not verified.empty
    assert isinstance(queue, pd.DataFrame)
    out_verified = project_path / "data/derived/inventory_verified_packages/inventory_verified_packages.parquet"
    out_queue = project_path / "data/derived/inventory_aoss_free_queue/inventory_aoss_free_queue.parquet"
    assert out_verified.is_file()
    assert out_queue.is_file()
    if mtime_before is not None:
        assert marker.stat().st_mtime_ns == mtime_before
