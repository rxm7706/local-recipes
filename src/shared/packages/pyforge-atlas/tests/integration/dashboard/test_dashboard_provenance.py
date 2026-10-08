"""One page, one Parquet constant: each page's AD-17 stamp is its OWN file's.

Story 27.3, closing DW-FU-20-5-7 / DW-FU-20-5-14. ``build_dashboard`` resolves a
separate ``resolve_for_file`` per page, but nothing proved the pairing: every
stamp came from a tmp root where no file existed, so all 34 pages rendered the
same ``unavailable`` line and a mis-paired constant was invisible.

The gate here gives every constant a DISTINCT mtime, builds the dashboard, and
reads each page's own legibility Card back: a page wired to the wrong constant
renders the wrong page's ISO stamp and reds.
"""

from __future__ import annotations

import datetime
import os
import re

import pandas as pd
import pytest
from vizro import Vizro
from vizro.managers import model_manager

from pyforge.atlas.dashboard import app
from pyforge.atlas.dashboard import data as _data

NOW = 1_700_000_000
STAMP = "2026-01-01T00:00:00+00:00"

# THE PIN. Page id -> the name of the `dashboard.data` Parquet-relpath constant
# whose mtime is that page's AD-17 build stamp. Hand-written on purpose: this is
# the declaration `build_dashboard` is checked against, not a readback of it.
PAGE_PARQUET_CONSTANT: dict[str, str] = {
    "feedstock-health": "FEEDSTOCK_HEALTH_PARQUET",
    "my-feedstocks": "PACKAGE_MAINTAINERS_PARQUET",
    "estate-cache": "ESTATE_CACHE_PARQUET",
    "staleness-report": "PACKAGES_PARQUET",
    "query-atlas": "PACKAGES_PARQUET",
    "detail-cf-atlas": "PACKAGES_PARQUET",
    "cve-watcher": "VULN_HISTORY_PARQUET",
    "version-downloads": "VERSION_DOWNLOADS_PARQUET",
    "release-cadence": "RELEASE_CADENCE_PARQUET",
    "find-alternative": "ALTERNATIVE_CANDIDATES_PARQUET",
    "adoption-stage": "PACKAGES_PARQUET",
    "scan-project": "SCAN_RESULT_LATEST_PARQUET",
    "env-inspect": "ENV_INSPECT_LATEST_PARQUET",
    "distribution-breakdown": "DISTRIBUTION_BREAKDOWN_PARQUET",
    "export-purls": "PURL_EXPORT_MANIFEST_PARQUET",
    "mapping-gap": "MAPPING_GAP_PARQUET",
    "universe-sbom": "UNIVERSE_SBOM_SUMMARY_PARQUET",
    "inventory-match": "INVENTORY_MATCH_LATEST_PARQUET",
    "add-handoff": "ADD_HANDOFF_LATEST_PARQUET",
    "library-futures": "LIBRARY_FUTURES_LATEST_PARQUET",
    "recommend-2027": "RECOMMEND_2027_PARQUET",
    "lts-registry-gap": "LTS_REGISTRY_GAP_PARQUET",
    "cwe-seed-gap": "CWE_SEED_GAP_PARQUET",
    "spdx-schema-gap": "SPDX_SCHEMA_GAP_PARQUET",
    "license-map-gap": "LICENSE_MAP_GAP_PARQUET",
    "identity-catalog": "IDENTITY_COMPLETE_EXPORT_PARQUET",
    "identity-ops": "IDENTITY_COMPLETE_EXPORT_PARQUET",
    "bootstrap-index-health": "BOOTSTRAP_INDEX_HEALTH_PARQUET",
    "identity-export-snapshot": "IDENTITY_EXPORT_PARQUET",
    "live-catalog-coverage": "LIVE_CATALOG_COVERAGE_PARQUET",
}

# `identity-workbook` joins two exports, so its stamp spans both files
# (`app._resolve_two_file_provenance`) -- asserted on its own below.
TWO_FILE_PAGES = {"identity-workbook": ("IDENTITY_COMPLETE_EXPORT_PARQUET", "ENTERPRISE_JFROG_CONSUMPTION_PARQUET")}

# Pages with no backing dataset at all: a declared BSL model does not exist yet,
# so `build_dashboard` passes a fixed "no BSL model" ProvenanceInfo, not a file.
NO_FILE_PAGES = {"behind-upstream", "whodepends"}

# The factory page's stamp is the sprint/epics tree, not a Parquet file.
FACTORY_PAGES = {"factory-status"}

_STAMP_LINE = re.compile(r"\*\*Data build stamp \(AD-17\):\*\*\s+`([^`]+)`")


def _iso(epoch: float) -> str:
    return datetime.datetime.fromtimestamp(epoch, tz=datetime.UTC).isoformat()


@pytest.fixture()
def stamped_root(tmp_path, bmad_fixture):
    """A data root where EVERY paired constant exists with its own distinct mtime."""
    root = tmp_path / "data"
    constants = sorted({*PAGE_PARQUET_CONSTANT.values(), *(c for pair in TWO_FILE_PAGES.values() for c in pair)})
    mtimes: dict[str, float] = {}
    for offset, constant in enumerate(constants, start=1):
        target = root / getattr(_data, constant)
        target.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"probe": [offset]}).to_parquet(target, index=False)
        # A distinct, well-separated mtime per constant: a mis-pairing cannot
        # coincide with its neighbour's second.
        mtime = float(NOW + offset * 3600)
        os.utime(target, (mtime, mtime))
        mtimes[constant] = mtime
    Vizro._reset()
    dashboard = app.build_dashboard(
        build_stamp=STAMP,
        data_root=root,
        now=NOW,
        sprint_status_path=bmad_fixture["sprint"],
        epics_path=bmad_fixture["epics"],
        reset=False,
    )
    return dashboard, mtimes


def _stamp_of(page_id: str) -> str:
    card_id = f"{page_id}--stamp" if page_id in FACTORY_PAGES else f"{page_id}--about"
    text = model_manager[card_id].text
    match = _STAMP_LINE.search(text)
    assert match is not None, f"{page_id}: no AD-17 stamp line in its Card:\n{text}"
    return match.group(1)


def test_the_pin_covers_every_page_exactly_once(stamped_root) -> None:
    """A page added without a row here would otherwise go unchecked."""
    covered = set(PAGE_PARQUET_CONSTANT) | set(TWO_FILE_PAGES) | NO_FILE_PAGES | FACTORY_PAGES
    inventory = {page.id for page in app.PAGE_INVENTORY}
    assert covered == inventory, f"uncovered: {sorted(inventory - covered)}; stale: {sorted(covered - inventory)}"


@pytest.mark.parametrize("page_id", sorted(PAGE_PARQUET_CONSTANT))
def test_each_page_stamps_its_own_parquet_file(page_id: str, stamped_root) -> None:
    _dashboard, mtimes = stamped_root
    expected = _iso(mtimes[PAGE_PARQUET_CONSTANT[page_id]])
    assert _stamp_of(page_id) == expected, (
        f"{page_id} is stamped from the wrong file: expected the mtime of {PAGE_PARQUET_CONSTANT[page_id]}"
    )


def test_the_two_file_page_spans_both_of_its_exports(stamped_root) -> None:
    _dashboard, mtimes = stamped_root
    oldest, newest = TWO_FILE_PAGES["identity-workbook"]
    stamp = _stamp_of("identity-workbook")
    both = {_iso(mtimes[oldest]), _iso(mtimes[newest])}
    assert stamp in both, f"identity-workbook stamp {stamp} is neither export's mtime ({sorted(both)})"
    text = model_manager["identity-workbook--about"].text
    assert "unavailable" not in text


@pytest.mark.parametrize("page_id", sorted(NO_FILE_PAGES))
def test_a_page_with_no_dataset_says_unavailable_and_why(page_id: str, stamped_root) -> None:
    """AD-17's honest-miss branch: never a stamp borrowed from another page's file."""
    text = model_manager[f"{page_id}--about"].text
    assert "unavailable" in text
    assert _STAMP_LINE.search(text) is None


def test_distinct_pairings_really_produce_distinct_stamps(stamped_root) -> None:
    """Guards the gate itself: if every stamp were identical, every case above
    would pass against any pairing at all."""
    _dashboard, _mtimes = stamped_root
    stamps = {page_id: _stamp_of(page_id) for page_id in PAGE_PARQUET_CONSTANT}
    # PACKAGES_PARQUET backs four pages, so count distinct CONSTANTS, not pages.
    assert len(set(stamps.values())) == len(set(PAGE_PARQUET_CONSTANT.values()))
