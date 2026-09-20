"""Story 23.4 — build_inventory_verified_packages parity vs legacy reference."""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    _INVENTORY_VERIFIED_PACKAGES_COLUMNS,
    build_inventory_verified_packages,
    norm_pkg,
    packaging_status,
    primary_source,
    role_for_package,
)

_FIXED_TS = "2026-08-30T12:00:00Z"
_PARAMS = {"inventory_verified_packages": {"verification_timestamp_utc": _FIXED_TS}}


def _universe_row(
    pkg: str,
    *,
    sources: list[str] | None = None,
    input_names: list[str] | None = None,
    role: str = "N/A",
) -> dict:
    return {
        "core_python_package_name": pkg,
        "package_input_names": input_names or [pkg],
        "sources": sources or ["tab:Conda-Forge"],
        "in_cdo_ent_jfrog": False,
        "in_cdo_ent_conda": False,
        "in_openteams": False,
        "in_conda_forge": "tab:Conda-Forge" in (sources or []),
        "in_basilisk": False,
        "in_anaconda_main": False,
        "in_anaconda_dist": False,
        "in_aoss_free": False,
        "in_aoss_premium": False,
        "role": role,
        "openteams_universe_member": False,
    }


def _run_both(
    universe_rows: list[dict],
    *,
    cf_names: list[str],
    pypi_names: list[str],
    parselmouth: list[str] | None = None,
    priority_rows: list[dict] | None = None,
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    inventory_universe = pd.DataFrame(universe_rows)
    core_packages_enumerated = pd.DataFrame([{"conda_name": n} for n in cf_names])
    pypi_universe = pd.DataFrame([{"pypi_name": n} for n in pypi_names])
    pypi_conda_mapping = pd.DataFrame([{"pypi_name": n} for n in (parselmouth or [])])
    priority = pd.DataFrame(priority_rows or [], columns=["core_python_package_name", "P"])

    out = build_inventory_verified_packages(
        inventory_universe,
        core_packages_enumerated,
        pypi_universe,
        pypi_conda_mapping,
        priority,
        _PARAMS,
    )

    cf_or_pm = {norm_pkg(n) for n in cf_names} | {norm_pkg(n) for n in (parselmouth or [])}
    pypi_index = {norm_pkg(n) for n in pypi_names}
    priority_map = {}
    for r in priority_rows or []:
        key = norm_pkg(r["core_python_package_name"])
        if r.get("P"):
            priority_map[key] = r["P"]
    maint = {norm_pkg(r["core_python_package_name"]) for r in universe_rows if r.get("role") == "Maintainer"}
    co = {norm_pkg(r["core_python_package_name"]) for r in universe_rows if r.get("role") == "Co-Maintainer"}

    ref_rows: list[dict[str, str]] = []
    for rec in sorted(universe_rows, key=lambda r: norm_pkg(r["core_python_package_name"])):
        pkg = norm_pkg(rec["core_python_package_name"])
        pypi_ok = pkg in pypi_index
        cf_ok = pkg in cf_or_pm
        pbucket = priority_map.get(pkg, "P9")
        status = packaging_status(pypi_ok, cf_ok, pbucket)
        src = primary_source(set(rec.get("sources") or []))
        inputs = sorted(rec.get("package_input_names") or [])
        first_input = inputs[0] if inputs else pkg
        ref_rows.append(
            {
                "Repository_Source": src,
                "Role": role_for_package(pkg, maint, co),
                "Package_Input_Name": first_input,
                "Core_Python_Package_Name": pkg,
                "PyPI_Verified": "Yes" if pypi_ok else "No",
                "CondaForge_Verified": "Yes" if cf_ok else "No",
                "Priority_Bucket": pbucket,
                "Packaging_Candidate_Status": status,
                "PyPI_PURL": f"pkg:pypi/{pkg}" if pypi_ok else "N/A",
                "PyPI_Package_URL": f"https://pypi.org/project/{pkg}/" if pypi_ok else "N/A",
                "Conda-forge_PURL": f"pkg:conda/{pkg}?channel=conda-forge" if cf_ok else "N/A",
                "Conda-Forge_Package_URL": f"https://anaconda.org/conda-forge/{pkg}/" if cf_ok else "N/A",
                "Conda-Forge_FeedStock_URL": (f"https://github.com/conda-forge/{pkg}-feedstock" if cf_ok else "N/A"),
                "Verification_Timestamp_UTC": _FIXED_TS,
            }
        )
    return out, ref_rows


@pytest.mark.parametrize(
    "pkg,pbucket,expected_status",
    [
        ("already-packaged", "P5", "Already Packaged"),
        ("high-priority", "P3", "High Priority Candidate"),
        ("low-priority", "P9", "Low Priority Candidate"),
        ("conda-only", "P9", "Conda-Forge Only"),
        ("not-on-pypi", "P9", "Not on PyPI"),
    ],
)
def test_packaging_candidate_status_branches(pkg, pbucket, expected_status):
    on_pypi = expected_status not in ("Conda-Forge Only", "Not on PyPI")
    on_cf = expected_status in ("Already Packaged", "Conda-Forge Only")
    out, ref = _run_both(
        [_universe_row(pkg, sources=["tab:GAOSS-Free" if on_pypi and not on_cf else "tab:Conda-Forge"])],
        cf_names=[pkg] if on_cf else [],
        pypi_names=[pkg] if on_pypi else [],
        priority_rows=[{"core_python_package_name": pkg, "P": pbucket}],
    )
    assert list(out.columns) == list(_INVENTORY_VERIFIED_PACKAGES_COLUMNS)
    assert out.iloc[0]["Packaging_Candidate_Status"] == expected_status
    assert out.to_dict(orient="records") == ref


def test_malformed_priority_bucket_empty_defaults_to_p9_low_priority():
    out, ref = _run_both(
        [_universe_row("orphan-pkg", sources=["tab:GAOSS-Free"])],
        cf_names=[],
        pypi_names=["orphan-pkg"],
        priority_rows=[{"core_python_package_name": "orphan-pkg", "P": ""}],
    )
    row = out.iloc[0]
    assert row["Priority_Bucket"] == "P9"
    assert row["Packaging_Candidate_Status"] == "Low Priority Candidate"
    assert out.to_dict(orient="records") == ref


@pytest.mark.parametrize(
    "bad_bucket",
    ["PX", "bad", "P"],
)
def test_malformed_priority_bucket_non_digit_uses_p9_for_status_only(bad_bucket):
    out, ref = _run_both(
        [_universe_row("orphan-pkg", sources=["tab:GAOSS-Free"])],
        cf_names=[],
        pypi_names=["orphan-pkg"],
        priority_rows=[{"core_python_package_name": "orphan-pkg", "P": bad_bucket}],
    )
    row = out.iloc[0]
    assert row["Priority_Bucket"] == bad_bucket
    assert row["Packaging_Candidate_Status"] == "Low Priority Candidate"
    assert out.to_dict(orient="records") == ref


def test_missing_priority_assignment_defaults_to_p9():
    out, ref = _run_both(
        [_universe_row("no-priority", sources=["tab:GAOSS-Free"])],
        cf_names=[],
        pypi_names=["no-priority"],
        priority_rows=[],
    )
    assert out.iloc[0]["Priority_Bucket"] == "P9"
    assert out.to_dict(orient="records") == ref


def test_parselmouth_mapping_counts_as_conda_forge_verified():
    out, ref = _run_both(
        [_universe_row("mapped-only", sources=["tab:GAOSS-Free"])],
        cf_names=[],
        pypi_names=["mapped-only"],
        parselmouth=["mapped-only"],
        priority_rows=[{"core_python_package_name": "mapped-only", "P": "P1"}],
    )
    assert out.iloc[0]["CondaForge_Verified"] == "Yes"
    assert out.iloc[0]["Packaging_Candidate_Status"] == "Already Packaged"
    assert out.to_dict(orient="records") == ref


def test_done_checkpoint_full_corpus_matches_metrics_reference():
    universe = [
        _universe_row("already-packaged", sources=["tab:Conda-Forge"]),
        _universe_row("high-priority", sources=["tab:GAOSS-Free"]),
        _universe_row("low-priority", sources=["tab:GAOSS-Free"]),
        _universe_row("conda-only", sources=["tab:Conda-Forge"]),
        _universe_row("not-on-pypi", sources=["tab:Basilisk"]),
    ]
    out, ref = _run_both(
        universe,
        cf_names=["already-packaged", "conda-only"],
        pypi_names=["already-packaged", "high-priority", "low-priority"],
        priority_rows=[
            {"core_python_package_name": "already-packaged", "P": "P5"},
            {"core_python_package_name": "high-priority", "P": "P2"},
            {"core_python_package_name": "low-priority", "P": "P10"},
            {"core_python_package_name": "conda-only", "P": "P9"},
            {"core_python_package_name": "not-on-pypi", "P": "P9"},
        ],
    )
    assert out.to_dict(orient="records") == ref
