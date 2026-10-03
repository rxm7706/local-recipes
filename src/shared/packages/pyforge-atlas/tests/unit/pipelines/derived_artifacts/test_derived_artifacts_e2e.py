"""Story 27.1 / DW-FU-23-5 — the derived_artifacts inventory + export slice through a Kedro session.

Runs every inventory and export node of ``derived_artifacts`` (universe, Basilisk rollup,
priority, verified packages, AOSS-free queue, identity complete export) through a real
``KedroSession`` over materialized fixture Parquet, offline and non-credentialed:

- the session runs against a copy of the project in ``tmp_path`` (``pyproject.toml``,
  ``conf/base``, ``src``); ``conf/local`` is never copied -- the test seeds stub
  credentials and a ``catalog.yml`` that points every free input at fixture Parquet;
- the verification floors are non-zero and the fixture meets them;
- ``sys.path``, ``PYTHONPATH`` and Kedro's project settings are restored by monkeypatch;
- the member's real ``data/`` tree is fingerprinted (file list + sha256) before and after.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

_MEMBER_DIR = Path(__file__).resolve().parents[4]
_REAL_DATA = _MEMBER_DIR / "data"
_TS = "2026-08-30T12:00:00Z"
_FLOORS = {"core_packages_enumerated_floor": 3, "pypi_universe_floor": 5}
_RUNTIME_PARAMS = {
    "verification_sets": _FLOORS,
    "inventory_verified_packages": {"verification_timestamp_utc": _TS},
    "identity_complete_export": {"verification_timestamp_utc": _TS},
}
_SLICE_NODES = [
    "build_inventory_universe",
    "derive_basilisk_vuln_rollup",
    "assign_inventory_priority",
    "build_inventory_verified_packages",
    "build_inventory_aoss_free_queue",
    "build_identity_complete_export",
]
_CREDENTIALS_KEY_RE = re.compile(r"^\s*credentials:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")
_STUB_PAIR = '["stub-user", "not-a-real-credential"]'


def _tree_fingerprint(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _identity_row(name: str, **extra: str) -> dict[str, str]:
    row = {
        "Core_Python_Package_Name": name,
        "OpenTeams_Title": f"[Conda-Forge Packaging] {name}",
        "identity_source": "inventory",
        "associator_key": name,
        "associator_status": "inventory-derived",
        "primary_purl": f"pkg:pypi/{name}",
        "primary_type": "pypi",
        "alternative_purls": "",
        "cpes": "",
        "conda_purl": "",
        "source_repository_url": "",
        "OpenTeams_Issue_URL": "",
        "Conda-Forge_FeedStock_URL": "",
        "Conda-Forge_Metadata_URL": "",
        "Staged_Recipes_PR_URL": "",
        "Local_Recipes_URL": "",
        "Local_Build_Status": "",
    }
    row.update(extra)
    return row


def _jfrog_row(name: str, **telemetry: int) -> dict[str, object]:
    row: dict[str, object] = {
        "core_python_package_name": name,
        "platform_env_count": 0,
        "internal_app_count": 0,
        "artifactory_downloads": 0,
        "artifactory_version_count": 0,
        "internal_component_count": 0,
        "internal_lob_count": 0,
    }
    row.update(telemetry)
    return row


def _fixture_inputs() -> dict[str, pd.DataFrame]:
    """Every free input of the slice. ``aossfreepkg`` is the one AOSS-free name that is on
    PyPI, off conda-forge (core and mapping) and outside CDO consumption -- the queue's
    only row; ``widget`` (on conda-forge), ``aosstracked`` (CDO-consumed), ``mappedaoss``
    (mapped to conda-forge) and ``notonpypi`` each fall out for a different reason."""
    return {
        "core_packages_enumerated": pd.DataFrame(
            {"conda_name": ["widget", "Numpy_ish", "condaonly"], "latest_version": ["1.0", "2.0", "3.0"]}
        ),
        "pypi_universe": pd.DataFrame(
            {"pypi_name": ["widget", "numpy-ish", "aossfreepkg", "aosstracked", "mappedaoss"]}
        ),
        "pypi_conda_mapping": pd.DataFrame({"pypi_name": ["mappedaoss"], "conda_name": ["mappedaoss"]}),
        "core_anaconda_main_packages": pd.DataFrame({"conda_name": ["anacondamainpkg"]}),
        "discovery_anaconda_dist_2026x_raw": pd.DataFrame({"conda_name": ["anacondadistpkg"]}),
        "discovery_basilisk_packages_raw": pd.DataFrame({"conda_name": ["widget"]}),
        "discovery_aoss_free_python_raw": pd.DataFrame(
            {"pypi_name": ["aossfreepkg", "widget", "aosstracked", "mappedaoss", "notonpypi"]}
        ),
        "discovery_aoss_premium_python_raw": pd.DataFrame({"pypi_name": ["aosspremiumpkg"]}),
        "enterprise_jfrog_names": pd.DataFrame(
            {"pypi_name": ["widget", "aosstracked"], "conda_name": ["widget", None]}
        ),
        "enterprise_conda_maintainers": pd.DataFrame(
            {
                "core_python_package_name": ["maintpkg"],
                "role": ["Maintainer"],
                "feedstock_slug": ["maintpkg"],
                "repository_source": ["CDO-ENT-CONDA"],
            }
        ),
        "openteams_project_1_board_raw": pd.DataFrame(
            {"title": ["[Conda-Forge Packaging] aosstracked"], "url": ["https://example.invalid/issues/7"]}
        ),
        "vulnerability_basilisk_advisories": pd.DataFrame({"conda_name": ["widget"], "advisory_id": ["GHSA-0000"]}),
        "vulnerability_basilisk_details": pd.DataFrame({"advisory_id": ["GHSA-0000"], "severity": [9.8]}),
        "identity_packages_primary": pd.DataFrame(
            [
                _identity_row("widget", conda_purl="pkg:conda/widget?channel=conda-forge"),
                _identity_row("aosstracked"),
            ]
        ),
        "enterprise_jfrog_consumption": pd.DataFrame(
            [
                _jfrog_row("widget", platform_env_count=3, artifactory_downloads=500),
                _jfrog_row("aosstracked", internal_app_count=1),
            ]
        ),
        "pypi_cross_channel_flags": pd.DataFrame(
            [
                {
                    "conda_name": "widget",
                    "in_selfexplainml": False,
                    "in_bioconda": False,
                    "in_pytorch": True,
                    "in_nvidia": False,
                    "in_robostack": False,
                }
            ]
        ),
        "pypi_tier3_channel_flags": pd.DataFrame(
            [
                {
                    "pypi_name": "widget",
                    "in_homebrew": True,
                    "in_nixpkgs": False,
                    "in_spack": False,
                    "in_debian": False,
                    "in_fedora": False,
                }
            ]
        ),
    }


def _copy_kedro_project(tmp_path: Path) -> Path:
    """Copy only what a session needs; ``conf/local`` and ``data`` never leave the member."""
    dest = tmp_path / "pyforge-atlas"
    dest.mkdir()
    shutil.copy2(_MEMBER_DIR / "pyproject.toml", dest / "pyproject.toml")
    shutil.copytree(_MEMBER_DIR / "conf" / "base", dest / "conf" / "base")
    shutil.copytree(
        _MEMBER_DIR / "src",
        dest / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"),
    )
    return dest


def _seed_conf_local(project: Path, inputs: dict[str, pd.DataFrame]) -> None:
    local = project / "conf" / "local"
    local.mkdir(parents=True)
    keys = sorted(
        {
            m.group(1)
            for line in (project / "conf" / "base" / "catalog.yml").read_text(encoding="utf-8").splitlines()
            if (m := _CREDENTIALS_KEY_RE.match(line))
        }
    )
    (local / "credentials.yml").write_text("".join(f"{key}: {_STUB_PAIR}\n" for key in keys), encoding="utf-8")
    entries = []
    for name, frame in inputs.items():
        path = project / "data" / "fixture_inputs" / f"{name}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        entries.append(f"{name}:\n  type: pandas.ParquetDataset\n  filepath: {path.as_posix()}\n")
    (local / "catalog.yml").write_text("\n".join(entries), encoding="utf-8")


@pytest.fixture
def _isolated_kedro_state(monkeypatch, tmp_path):
    """Undo everything ``bootstrap_project`` / a session mutates in this process."""
    from kedro.framework import project as kedro_project

    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("PYTHONPATH", os.environ.get("PYTHONPATH", ""))
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", str(tmp_path / "pyforge-atlas" / "data"))
    monkeypatch.setattr(kedro_project, "PACKAGE_NAME", kedro_project.PACKAGE_NAME)
    monkeypatch.setattr(kedro_project.settings, "_wrapped", kedro_project.settings._wrapped)
    for attr in ("_pipelines_module", "_is_data_loaded", "_content", "_requested_pipelines"):
        if hasattr(kedro_project.pipelines, attr):
            monkeypatch.setattr(kedro_project.pipelines, attr, getattr(kedro_project.pipelines, attr))


@pytest.mark.usefixtures("_isolated_kedro_state")
def test_derived_artifacts_inventory_and_export_slice_via_kedro_session(tmp_path: Path):
    from kedro.framework.session import KedroSession
    from kedro.framework.startup import bootstrap_project

    real_before = _tree_fingerprint(_REAL_DATA)

    project = _copy_kedro_project(tmp_path)
    inputs = _fixture_inputs()
    _seed_conf_local(project, inputs)
    bootstrap_project(project)

    with KedroSession.create(project_path=project, runtime_params=_RUNTIME_PARAMS) as session:
        session.run(pipeline_name="derived_artifacts", node_names=_SLICE_NODES)
        catalog = session.load_context().catalog
        outputs = {
            name: catalog.load(name)
            for name in (
                "inventory_universe",
                "inventory_priority_assignments",
                "inventory_verified_packages",
                "inventory_aoss_free_queue",
                "identity_complete_export",
            )
        }

    derived = project / "data" / "derived"
    for name in outputs:
        assert (derived / name / f"{name}.parquet").is_file(), name

    universe = set(outputs["inventory_universe"]["core_python_package_name"])
    assert {"widget", "numpy-ish", "aossfreepkg", "maintpkg", "anacondamainpkg"} <= universe

    queue = outputs["inventory_aoss_free_queue"]
    assert queue.to_dict(orient="records") == [
        {
            "Package_Name": "aossfreepkg",
            "Reason": "On PyPI, not on conda-forge, not in CDO consumption (GAOSS-Free)",
            "Verification_Timestamp_UTC": _TS,
        }
    ]

    verified = outputs["inventory_verified_packages"].set_index("Core_Python_Package_Name")
    assert verified.loc["widget", "CondaForge_Verified"] == "Yes"
    assert verified.loc["aossfreepkg", "PyPI_Verified"] == "Yes"
    assert verified.loc["aossfreepkg", "CondaForge_Verified"] == "No"

    priority = outputs["inventory_priority_assignments"].set_index("core_python_package_name")
    assert priority.loc["widget", "P"] == "P1"
    assert priority.loc["widget", "Work"] == "Fix vulnerability"

    export = outputs["identity_complete_export"].set_index("Core_Python_Package_Name")
    assert list(export.index) == ["widget", "aosstracked"]
    assert export.loc["widget", "P"] == "P1"
    assert export.loc["widget", "JFROG_risk_level"] == "HIGH"
    assert export.loc["widget", "CondaForge_Verified"] == "Yes"
    assert export.loc["widget", "Platforms"] == 3
    assert bool(export.loc["widget", "in_pytorch"]) and bool(export.loc["widget", "in_homebrew"])
    assert set(export["Verification_Timestamp_UTC"]) == {_TS}

    assert _tree_fingerprint(_REAL_DATA) == real_before, "the session wrote into the member's real data/ tree"


@pytest.mark.usefixtures("_isolated_kedro_state")
def test_slice_refuses_a_hollow_core_set_through_the_session(tmp_path: Path):
    """The same session with the core set under its floor refuses -- and writes no queue."""
    from kedro.framework.session import KedroSession
    from kedro.framework.startup import bootstrap_project

    from pyforge.atlas.pipelines.derived_artifacts.inventory_verification import HollowVerificationSetError

    project = _copy_kedro_project(tmp_path)
    inputs = _fixture_inputs()
    inputs["core_packages_enumerated"] = inputs["core_packages_enumerated"].head(2)
    _seed_conf_local(project, inputs)
    bootstrap_project(project)

    with KedroSession.create(project_path=project, runtime_params=_RUNTIME_PARAMS) as session:
        with pytest.raises(HollowVerificationSetError, match="hollow_core_packages_enumerated"):
            session.run(pipeline_name="derived_artifacts", node_names=_SLICE_NODES)

    assert not (project / "data/derived/inventory_aoss_free_queue/inventory_aoss_free_queue.parquet").exists()
