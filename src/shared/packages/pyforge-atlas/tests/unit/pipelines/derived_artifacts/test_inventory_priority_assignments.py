"""Story 23.3 — assign_inventory_priority + derive_basilisk_vuln_rollup.

Frozen fixture corpus parity against the inlined pre-23.9 ranking reference on the
same synthetic rows — the story's ``done_checkpoint``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pyforge.atlas.pipelines.derived_artifacts.nodes import (
    _INVENTORY_PRIORITY_COLUMNS,
    _PRI_N,
    _WORK_CREATE,
    _WORK_ISSUE_CF,
    _WORK_RANK,
    _priority_assign_lane,
    _priority_board_maps,
    _priority_num,
    _priority_pep503,
    _priority_percentile_1_100,
    _priority_use_score,
    _priority_work_label,
    assign_inventory_priority,
    derive_basilisk_vuln_rollup,
)


def _identity_row(name: str, **extra) -> dict:
    row = {
        "Core_Python_Package_Name": name,
        "OpenTeams_Title": f"[Conda-Forge Packaging] {name}",
        "OpenTeams_Issue_URL": "",
        "conda_purl": "",
        "Conda-Forge_FeedStock_URL": "",
    }
    row.update(extra)
    return row


def _jfrog_row(name: str, **telemetry) -> dict:
    base = {
        "core_python_package_name": name,
        "platform_env_count": 0,
        "internal_app_count": 0,
        "artifactory_downloads": 0,
        "artifactory_version_count": 0,
        "internal_component_count": 0,
        "internal_lob_count": 0,
    }
    base.update(telemetry)
    return base


def _run_priority_reference(
    identity_rows: list[dict],
    jfrog_rows: list[dict],
    ot_rows: list[dict],
    inv_by: dict[str, dict],
    vuln_by: dict[str, dict],
) -> pd.DataFrame:
    """Mirror the pre-23.9 ranking logic on synthetic rows (no workbook I/O)."""
    jfrog = {}
    for r in jfrog_rows:
        k = _priority_pep503(r.get("core_python_package_name") or r.get("name"))
        if k:
            merged = dict(r)
            v = vuln_by.get(k)
            if v:
                merged.update(v)
            jfrog[k] = merged

    by_url, by_name = _priority_board_maps(ot_rows)
    records = []
    for ident in identity_rows:
        name = _priority_pep503(ident.get("Core_Python_Package_Name")) or str(
            ident.get("Core_Python_Package_Name") or ""
        )
        j = jfrog.get(_priority_pep503(ident.get("Core_Python_Package_Name")) or "")
        plat = int(_priority_num(j.get("platform_env_count")) if j else 0)
        apps = int(_priority_num(j.get("internal_app_count")) if j else 0)
        ic = int(_priority_num(j.get("internal_component_count")) if j else 0)
        lob = int(_priority_num(j.get("internal_lob_count")) if j else 0)
        dl = int(_priority_num(j.get("artifactory_downloads")) if j else 0)
        ver = int(_priority_num(j.get("artifactory_version_count")) if j else 0)
        raw = _priority_use_score(plat, apps, ic, lob, dl, ver)
        inv = inv_by.get(_priority_pep503(ident.get("Core_Python_Package_Name")) or "")
        work = _priority_work_label(ident, inv, j)
        cohort = str((inv or {}).get("OpenTeams_Cohort") or "").strip()
        bucket, src, why = _priority_assign_lane(
            ident, _priority_pep503(ident.get("Core_Python_Package_Name")), j, by_url, by_name
        )
        records.append(
            {
                "name": name,
                "work": work,
                "cohort": cohort,
                "bucket": bucket,
                "src": src,
                "why": why,
                "raw": raw,
                "dl": dl,
                "ver": ver,
            }
        )

    scores = _priority_percentile_1_100([r["raw"] for r in records])
    for r, s in zip(records, scores):
        r["score100"] = s

    remainder = [r for r in records if r["bucket"] is None]
    for r in remainder:
        if r["work"] == _WORK_CREATE:
            tier, src = "P8", "work-create-recipe"
            why = "leftover Create recipe: JFROG consumed, not on conda-forge"
        elif r["work"] == _WORK_ISSUE_CF:
            if r.get("cohort") == "CONDA_ONLY":
                tier, src = "P10", "work-file-issue-conda-only"
                why = "leftover File OpenTeams tracking issue [Conda-Forge Packaging] (CDO-ENT-CONDA)"
            else:
                tier, src = "P9", "work-file-issue-on-cf"
                why = "leftover File OpenTeams tracking issue [Conda-Forge Packaging]"
        else:
            tier, src = "P10", "work-already-tracked-remainder"
            why = "leftover Already tracked"
        r["bucket"] = tier
        r["src"] = src
        r["why"] = f"{why} (score {r['score100']})"

    def sort_key(r: dict):
        return (
            _PRI_N[r["bucket"]],
            _WORK_RANK.get(r["work"], 9),
            -r["score100"],
            -r["raw"],
            -r["dl"],
            -r["ver"],
            r["name"],
        )

    records.sort(key=sort_key)
    for i, r in enumerate(records, start=1):
        r["rank"] = i
        r["P"] = r["bucket"]
        r["Rank"] = r["rank"]
        r["Score"] = r["score100"]
        r["Work"] = r["work"]
    return pd.DataFrame(records)


def _run_kedro_node(
    identity_rows: list[dict],
    jfrog_rows: list[dict],
    ot_rows: list[dict],
    conda_maintainers: list[dict] | None,
    vuln_rollup_rows: list[dict],
) -> pd.DataFrame:
    identity = pd.DataFrame(identity_rows)
    jfrog = pd.DataFrame(jfrog_rows) if jfrog_rows else pd.DataFrame()
    board = pd.DataFrame(ot_rows) if ot_rows else pd.DataFrame()
    maintainers = pd.DataFrame(conda_maintainers) if conda_maintainers else pd.DataFrame()
    rollup = pd.DataFrame(vuln_rollup_rows) if vuln_rollup_rows else pd.DataFrame()
    return assign_inventory_priority(identity, jfrog, maintainers, board, rollup, {})


# --- derive_basilisk_vuln_rollup ------------------------------------------------


def test_derive_basilisk_vuln_rollup_affected_latest_and_count():
    advisories = pd.DataFrame(
        [
            {"conda_name": "numpy", "advisory_id": "A1", "modified": "t"},
            {"conda_name": "numpy", "advisory_id": "A2", "modified": "t"},
        ]
    )
    details = pd.DataFrame(
        [
            {"advisory_id": "A1", "fix_available": "unknown", "severity": {"score": "9.0"}},
            {"advisory_id": "A2", "fix_available": "unknown", "severity": {"score": "5.0"}},
        ]
    )
    out = derive_basilisk_vuln_rollup(advisories, details)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["conda_name"] == "numpy"
    assert row["vuln_status"] == "affected_latest"
    assert row["jfrog_latest_vuln_count"] == 2
    assert row["risk_level"] == "HIGH"


def test_derive_basilisk_vuln_rollup_absent_when_no_advisories():
    advisories = pd.DataFrame(columns=["conda_name", "advisory_id", "modified"])
    out = derive_basilisk_vuln_rollup(advisories, pd.DataFrame())
    assert out.empty


def test_derive_basilisk_vuln_rollup_clean_name_not_in_output():
    advisories = pd.DataFrame([{"conda_name": "clean-pkg", "advisory_id": "X", "modified": "t"}])
    details = pd.DataFrame([{"advisory_id": "Y", "fix_available": "true", "severity": None}])
    out = derive_basilisk_vuln_rollup(advisories, details)
    assert len(out) == 1
    assert out.iloc[0]["conda_name"] == "clean-pkg"


# --- I/O matrix scenarios + done_checkpoint parity ----------------------------


@pytest.fixture
def corpus():
    """Six-scenario fixture corpus aligned with spec I/O matrix."""
    identity = [
        _identity_row("vuln-pkg"),
        _identity_row("board-p2", OpenTeams_Issue_URL="https://github.com/o/i/2"),
        _identity_row("plat-pkg"),
        _identity_row("app-pkg"),
        _identity_row("heavy-dl"),
        _identity_row("mod-dl"),
        _identity_row("create-leftover", OpenTeams_Cohort="JFROG_NEW"),
        _identity_row(
            "issue-on-cf", conda_purl="pkg:conda/issue-on-cf?channel=conda-forge", OpenTeams_Cohort="JFROG_ON_CF"
        ),
        _identity_row(
            "issue-conda-only",
            OpenTeams_Cohort="CONDA_ONLY",
            **{"Conda-Forge_FeedStock_URL": "https://github.com/cf/x"},
        ),
        _identity_row(
            "tracked-leftover",
            OpenTeams_Issue_URL="https://github.com/o/i/9",
            OpenTeams_Coverage="Have_Issue",
        ),
    ]
    jfrog = [
        _jfrog_row("vuln-pkg"),
        _jfrog_row("board-p2"),
        _jfrog_row("plat-pkg", platform_env_count=2),
        _jfrog_row("app-pkg", internal_app_count=3),
        _jfrog_row("heavy-dl", artifactory_downloads=150),
        _jfrog_row("mod-dl", artifactory_downloads=15),
        _jfrog_row("create-leftover"),
        _jfrog_row("issue-on-cf"),
        # issue-conda-only: CDO-ENT-CONDA only — no JFROG telemetry row (CONDA_ONLY cohort)
        _jfrog_row("tracked-leftover"),
    ]
    ot = [
        {
            "Title": "[Conda-Forge Packaging] board-p2",
            "URL": "https://github.com/o/i/2",
            "Priority": "P2 High",
            "title": "[Conda-Forge Packaging] board-p2",
            "url": "https://github.com/o/i/2",
            "priority": "P2 High",
        }
    ]
    inv_by = {
        "vuln-pkg": {},
        "board-p2": {},
        "plat-pkg": {},
        "app-pkg": {},
        "heavy-dl": {},
        "mod-dl": {},
        "create-leftover": {"OpenTeams_Cohort": "JFROG_NEW"},
        "issue-on-cf": {"OpenTeams_Cohort": "JFROG_ON_CF"},
        "issue-conda-only": {"OpenTeams_Cohort": "CONDA_ONLY"},
        "tracked-leftover": {"OpenTeams_Coverage": "Have_Issue"},
    }
    vuln_by = {
        "vuln-pkg": {
            "risk_level": "HIGH",
            "vuln_status": "affected_latest",
            "jfrog_latest_vuln_count": 2,
        }
    }
    vuln_rollup = [
        {
            "conda_name": "vuln-pkg",
            "risk_level": "HIGH",
            "vuln_status": "affected_latest",
            "jfrog_latest_vuln_count": 2,
        }
    ]
    conda_maintainers = [
        {
            "core_python_package_name": "issue-conda-only",
            "role": "Maintainer",
            "feedstock_slug": "x",
            "repository_source": "CDO-ENT-CONDA",
        }
    ]
    return {
        "identity": identity,
        "jfrog": jfrog,
        "ot": ot,
        "inv_by": inv_by,
        "vuln_by": vuln_by,
        "vuln_rollup": vuln_rollup,
        "conda_maintainers": conda_maintainers,
    }


def test_current_vuln_p1(corpus):
    ref = _run_priority_reference(
        [corpus["identity"][0]],
        [corpus["jfrog"][0]],
        [],
        {"vuln-pkg": corpus["inv_by"]["vuln-pkg"]},
        corpus["vuln_by"],
    )
    kedro = _run_kedro_node(
        [corpus["identity"][0]],
        [corpus["jfrog"][0]],
        [],
        None,
        corpus["vuln_rollup"],
    )
    assert kedro.iloc[0]["P"] == "P1"
    assert kedro.iloc[0]["Work"] == "Fix vulnerability"
    assert kedro.iloc[0]["Priority_Source"] == "current-version-vuln"
    assert kedro.iloc[0]["P"] == ref.iloc[0]["P"]
    assert kedro.iloc[0]["Work"] == ref.iloc[0]["Work"]


def test_board_locked_p2_not_overwritten(corpus):
    ref = _run_priority_reference(
        [corpus["identity"][1]],
        [_jfrog_row("board-p2", platform_env_count=5)],
        corpus["ot"],
        {"board-p2": corpus["inv_by"]["board-p2"]},
        {},
    )
    kedro = _run_kedro_node(
        [corpus["identity"][1]],
        [_jfrog_row("board-p2", platform_env_count=5)],
        corpus["ot"],
        None,
        [],
    )
    assert kedro.iloc[0]["P"] == "P2"
    assert kedro.iloc[0]["Priority_Source"] == "openteams-board"
    assert kedro.iloc[0]["P"] == ref.iloc[0]["P"]


def test_platform_p4_and_app_p5(corpus):
    for idx, expected_p in ((2, "P4"), (3, "P5")):
        ref = _run_priority_reference(
            [corpus["identity"][idx]],
            [corpus["jfrog"][idx]],
            [],
            {corpus["identity"][idx]["Core_Python_Package_Name"]: {}},
            {},
        )
        kedro = _run_kedro_node([corpus["identity"][idx]], [corpus["jfrog"][idx]], [], None, [])
        assert kedro.iloc[0]["P"] == expected_p
        assert kedro.iloc[0]["Score"] == ref.iloc[0]["Score"]


def test_download_floors_p6_p7(corpus):
    for idx, expected_p in ((4, "P6"), (5, "P7")):
        ref = _run_priority_reference(
            [corpus["identity"][idx]],
            [corpus["jfrog"][idx]],
            [],
            {corpus["identity"][idx]["Core_Python_Package_Name"]: {}},
            {},
        )
        kedro = _run_kedro_node([corpus["identity"][idx]], [corpus["jfrog"][idx]], [], None, [])
        assert kedro.iloc[0]["P"] == expected_p
        assert kedro.iloc[0]["Score"] == ref.iloc[0]["Score"]


def test_remainder_p8_p9_p10(corpus):
    for idx, expected_p in ((6, "P8"), (7, "P9"), (8, "P10")):
        name = corpus["identity"][idx]["Core_Python_Package_Name"]
        ref = _run_priority_reference(
            [corpus["identity"][idx]],
            [corpus["jfrog"][idx]],
            [],
            {name: corpus["inv_by"][name]},
            {},
        )
        maintainers = corpus["conda_maintainers"] if name == "issue-conda-only" else None
        kedro = _run_kedro_node(
            [corpus["identity"][idx]],
            [corpus["jfrog"][idx]],
            [],
            maintainers,
            [],
        )
        assert kedro.iloc[0]["P"] == expected_p
        assert kedro.iloc[0]["Work"] == ref.iloc[0]["Work"]


def test_done_checkpoint_full_corpus_parity(corpus):
    ref = _run_priority_reference(
        corpus["identity"],
        corpus["jfrog"],
        corpus["ot"],
        corpus["inv_by"],
        corpus["vuln_by"],
    )
    kedro = _run_kedro_node(
        corpus["identity"],
        corpus["jfrog"],
        corpus["ot"],
        corpus["conda_maintainers"],
        corpus["vuln_rollup"],
    )
    ref_by_name = ref.set_index("name")
    kedro_by_name = kedro.set_index("core_python_package_name")
    for name in ref_by_name.index:
        assert kedro_by_name.loc[name, "P"] == ref_by_name.loc[name, "P"]
        assert kedro_by_name.loc[name, "Rank"] == ref_by_name.loc[name, "Rank"]
        assert kedro_by_name.loc[name, "Score"] == ref_by_name.loc[name, "Score"]
        assert kedro_by_name.loc[name, "Work"] == ref_by_name.loc[name, "Work"]


def test_output_carries_contract_columns_and_legacy_aliases():
    out = _run_kedro_node(
        [_identity_row("alpha")],
        [_jfrog_row("alpha", artifactory_downloads=20)],
        [],
        None,
        [],
    )
    expected = {
        "P",
        "Rank",
        "Score",
        "Work",
        "Priority_Bucket_Description",
        "Priority_Source",
        "Priority_Reason",
        "Proposed_Priority",
        "Packaging_Work",
        "Priority_Rank",
        "Priority_Score",
        "core_python_package_name",
        "risk_level",
        "vuln_status",
        "jfrog_latest_vuln_count",
    }
    assert expected <= set(out.columns)
    row = out.iloc[0]
    assert row["Proposed_Priority"] == row["P"]
    assert row["Packaging_Work"] == row["Work"]
    assert row["Priority_Rank"] == row["Rank"]
    assert row["Priority_Score"] == row["Score"]


def test_empty_identity_yields_empty_typed_frame():
    out = assign_inventory_priority(
        pd.DataFrame(columns=["Core_Python_Package_Name"]),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        {},
    )
    assert out.empty
    assert list(out.columns) == list(_INVENTORY_PRIORITY_COLUMNS)
