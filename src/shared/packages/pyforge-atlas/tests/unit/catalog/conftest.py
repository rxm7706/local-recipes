"""Story A2 `kedro-catalog-check` gate — shared fixtures + declared conventions.

This module is the single declaration point for the gate's deterministic
inputs (story Dev Notes "Domain-prefix rule": the chosen prefix->pipeline
map is declared ONCE here so the checks are deterministic, not
red-by-construction):

- ``PREFIX_TO_PIPELINE``  — catalog-name prefix -> spec § 5.2 pipeline.
- ``EXPECTED_PIPELINE_COUNTS`` — per-pipeline entry counts (35 sources +
  38 outputs = 73 total; recorded in the A2 Dev Agent Record).
- ``FLIP_LIST``           — the TTL-gated entries Story A3 flips to
  ``pyforge.atlas.datasets.IncrementalParquetDataset`` (the ``# A3:``
  markers in catalog.yml; part of the A2 -> A3 handoff).
- ``EXPECTED_FLIP_MARKERS`` — the non-A3 ``# FLIP(<story>)`` markers: entries
  declared with an interim standard type that a NAMED later story must
  re-declare (factory/partitioned/custom dataset). Review-pass P2: the
  flip list GREW — these contradictions are explicit, never implicit.
- ``STUB_CREDENTIALS``    — per-host stub keys (zero network; NFR-2:
  the gate never touches a credentialed endpoint).

Everything is fixture-based, offline, and non-credentialed (AD-11/NFR-1).
Env scrubbing is PER-TEST via an autouse monkeypatch fixture (review-pass
P5) — nothing leaks into sibling suites collected in the same run
(kedro-test collects this package too).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

MEMBER_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = MEMBER_DIR.parents[2].parent  # src/shared/packages -> repo root
CONF_SOURCE = MEMBER_DIR / "conf"
CATALOG_YML = CONF_SOURCE / "base" / "catalog.yml"
GLOBALS_YML = CONF_SOURCE / "base" / "globals.yml"
PARAMETERS_YML = CONF_SOURCE / "base" / "parameters.yml"
SRC_DIR = MEMBER_DIR / "src"
ATLAS_PKG = SRC_DIR / "pyforge" / "atlas"

# Files exempt from the whole-package no-inline-IO scan (review-pass P3:
# the scan is now ``ATLAS_PKG.rglob('*.py')`` minus THIS set — coverage is
# complete by construction; a new module anywhere in the package is scanned
# automatically). Paths are relative to ATLAS_PKG; only the five known
# root-level framework files are exempt — subpackage __init__.py files ARE
# scanned (they can carry imports).
NO_INLINE_IO_EXEMPT = {
    "__init__.py",
    "__main__.py",
    "settings.py",
    "pipeline_registry.py",
    # Story 20.1 (CAP-5, query-plane-face ruling 2026-08-26): the ONE boot
    # script that launches the Mosaic duckdb-server HTTP/Arrow face — it must
    # spawn the server process (subprocess, on the denylist). Boot framework
    # code, not a data-access node; its launch surface is gated explicitly by
    # tests/singularity/test_one_duckdb_server_launch_site.py.
    "query_plane_boot.py",
}

LAYERS = {"raw", "intermediate", "primary", "derived"}
OUTPUT_LAYERS = {"intermediate", "primary", "derived"}

# Domain-prefix rule (binding for the convention check; short forms chosen).
PREFIX_TO_PIPELINE = {
    "core": "core",
    "pypi": "pypi_intelligence",
    "vulnerability": "vulnerability",
    "vcs": "vcs_health",
    "sbom": "universal_sbom",
    "seed_gaps": "seed_gaps",
    "seed": "seed_gaps",
    "derived": "derived_artifacts",
    "inventory": "derived_artifacts",  # Story 23.8: inventory_universe
    "trending": "upstream_discovery",
    "org_audit": "upstream_discovery",
    # Story 23.1: Tier 3 OS bulk indexes — SPECIFIC prefixes beat the generic
    # ``discovery`` -> upstream_discovery fallback (longest-prefix match).
    "discovery_homebrew": "pypi_intelligence",
    "discovery_nixpkgs": "pypi_intelligence",
    "discovery_spack": "pypi_intelligence",
    "discovery_debian": "pypi_intelligence",
    "discovery_fedora": "pypi_intelligence",
    "discovery": "upstream_discovery",  # Story 21.4: Tier 1 discovery-shaped sources
    "enterprise": "upstream_discovery",  # Story 21.5: Tier 2 enterprise-universe sources
    "enterprise_jfrog_consumption": "artifactory_downloads",  # Story 23.2: beats `enterprise` via longest-prefix
    "purl_associator": "upstream_discovery",  # Story 21.6: CAP-3 identity join
    "openteams": "upstream_discovery",  # Story 21.6: CAP-3 identity join
    "identity": "upstream_discovery",  # Story 21.6: CAP-3 identity join (identity_packages_primary)
    "identity_complete_export": "derived_artifacts",  # Story 23.5: beats `identity` via longest-prefix
    "artifactory": "artifactory_downloads",
    "query_plane": "query_plane_cache",
    "semantic": "semantic_packages",
}

# Final implemented counts (drafting target was ~77: 35 sources + ~42
# outputs; implemented = 35 sources + 38 outputs — the 6 purl artifacts
# collapse into ONE partitioned dataset and the repo-scope sbom report is
# deferred to F4 per AD-12; recorded in the Dev Agent Record).
EXPECTED_PIPELINE_COUNTS = {
    "core": 18,  # Story 21.4: + core_anaconda_main_channeldata_raw + core_anaconda_main_packages
    "pypi_intelligence": 21,  # Story 23.1: +5 Tier-3 raw stores + pypi_tier3_channel_flags (+6 nodes)
    "vulnerability": 15,  # Story 23.3: + vulnerability_basilisk_rollup (rollup lives under vulnerability_* prefix)
    "vcs_health": 25,  # B10: +5 category-list + vcs_migration_detail_raw + vcs_migration_readiness (FR-21; new-signal, AD-14)
    "universal_sbom": 6,  # F4: + sbom_hygiene_entry + sbom_compliance_report_entry (FR-16/FR-18, AD-12)
    "seed_gaps": 8,
    "derived_artifacts": 7,  # Story 23.8: + inventory_universe; Story 23.3: + inventory_priority_assignments; Story 23.4: + inventory_verified_packages + inventory_aoss_free_queue; Story 23.5: + identity_complete_export
    "upstream_discovery": 18,  # Story 13.1: trending_candidates (CAP-1); Story 13.2: + trending_candidates_classified (CAP-2, FR-65); Story 13.4: + org_audit_candidates + org_audit_candidates_classified (CAP-4, FR-67); Story 21.4: + discovery_anaconda_dist_2026x_raw + discovery_basilisk_packages_raw + discovery_aoss_free_python_raw + discovery_aoss_premium_python_raw (Tier 1); Story 21.5: + discovery_about_maintainers_raw + discovery_curated_groups_seed + enterprise_conda_maintainers + enterprise_jfrog_names (Tier 2 — enterprise_jfrog_names buckets HERE via the `enterprise` prefix even though its producer node lives in artifactory_downloads); Story 21.6: + purl_associator_mappings_raw + openteams_project_1_board_raw + discovery_staged_recipes_prs_raw + discovery_local_recipes_raw + identity_packages_primary + identity_export_parquet (CAP-3 identity join, Phase D)
    "artifactory_downloads": 4,  # Story 15.3: artifactory_downloads_raw + artifactory_downloads_joined; Story 23.2: + artifactory_consumption_raw + enterprise_jfrog_consumption
    "query_plane_cache": 2,  # Story 34.2 (FR-47): query_plane_estate_source + query_plane_estate
    "semantic_packages": 1,  # Story 20.3 (CAP-6): semantic_packages
}
EXPECTED_TOTAL = 125  # Story 23.5: +1 (identity_complete_export)

# The A3 IncrementalParquetDataset flip list (TTL-gated persisted outputs).
FLIP_LIST = {
    "core_downloads",
    "core_downloads_platform_breakdown",
    "core_downloads_pyver_breakdown",
    "core_downloads_channel_breakdown",
    "core_version_download_history",
    "pypi_universe",
    "pypi_current_versions",
    "pypi_downloads_monthly",
    "pypi_cross_channel_flags",
    "pypi_tier3_channel_flags",
    "pypi_intelligence_enriched",
    "vulnerability_package_rollup",
    "vulnerability_package_version_vulns",
    "vcs_upstream_versions",
    "vcs_registry_versions",
    "vcs_live_health",
}

# Review-pass P2: the GROWN flip list — entries whose current declaration is
# an honest interim that a NAMED story must re-declare. `# FLIP(<story>)`
# markers in catalog.yml, pinned here (drift in either direction fails):
#   - one APIDataset = one URL; path-parameterized feeds need a factory /
#     partitioned dataset so nodes never build request URLs (AC-2);
#   - the vdb store is path-only until B5 lands a real read-only VDB
#     dataset class (its format is NOT pickle — see catalog.yml).
# B1 LANDED core_anaconda_downloads_raw's flip (interim api.APIDataset ->
# AnacondaDownloadsDataset), so its `# FLIP(B1)` marker is removed from
# catalog.yml and dropped here. B2 LANDED pypi_json_raw's flip (interim
# api.APIDataset -> PyPIJsonRequestDataset, DW-B1-2 scheduler wiring), so its
# `# FLIP(B2)` marker is removed from catalog.yml and dropped here.
# G-1(B2): pypi_bigquery_downloads_raw's marker is CORRECTED B3 -> B2 (Phase P
# is a B2 pypi phase); it stays an interim (the credentialed GBQ materialization
# is attended-only, NFR-2/AD-11) while B2 authored the cost gate + dataset class
# + fixtures. B5 LANDED vulnerability_vdb_store's flip (interim MemoryDataset ->
# VDBStoreDataset, the read-only VDB store class that wraps refresh + coerce_cvss_score),
# so its `# FLIP(B5)` marker is removed from catalog.yml and dropped here.
EXPECTED_FLIP_MARKERS = {
    "pypi_bigquery_downloads_raw": "B2",
}

# AC-4 accounting (review-pass P7: pinned as 19 live + 1 reserved, not a
# bare 20; Story 21.4 extended it to 19+1+2 = 22): the 19 live
# resolve_*_urls helpers (verified at b18cbb5 AND against the live tree
# 2026-07-17) plus the 2 Story 21.4 Tier-1 discovery points at the end...
EXPECTED_LIVE_OVERRIDE_POINTS = {
    "CONDA_FORGE_BASE_URL",
    "PYPI_BASE_URL",  # live name (corrected from the drafting inventory's PYPI_SIMPLE_BASE_URL)
    "PYPI_JSON_BASE_URL",
    "GITHUB_BASE_URL",
    "GITHUB_RAW_BASE_URL",
    "NPM_BASE_URL",
    "CRAN_BASE_URL",
    "CPAN_BASE_URL",
    "LUAROCKS_BASE_URL",
    "CRATES_BASE_URL",
    "RUBYGEMS_BASE_URL",
    "MAVEN_BASE_URL",
    "NUGET_BASE_URL",
    "ENDOFLIFE_BASE_URL",
    "GITHUB_API_BASE_URL",
    "GITLAB_API_BASE_URL",
    "CODEBERG_API_BASE_URL",
    "ANACONDA_CHANNEL_BASE_URL",
    "S3_PARQUET_BASE_URL",
    # Story 21.4 (Tier 1, CAP-2) — the ONLY 2 new override points the story adds
    # (Anaconda main + Basilisk /v1/packages reuse ANACONDA_CHANNEL_BASE_URL /
    # BASILISK_BASE_URL). No legacy resolve_*_urls helper either way — they follow
    # globals.yml's "new sources add exactly one override point" rule.
    "ANACONDA_DIST_BASE_URL",
    "AOSS_PREMIUM_BASE_URL",
    # Story 23.1 (Tier 3 OS bulk indexes) — five new host bases for the
    # discovery_<source>_packages_raw external-refresh stores in pypi_intelligence.
    "HOMEBREW_BASE_URL",
    "NIXPKGS_BASE_URL",
    "SPACK_RAW_BASE_URL",
    "DEBIAN_BASE_URL",
    "FEDORA_SRC_BASE_URL",
}
# The Story 21.4 additions, named so test_override_points can assert the
# 19 + 2 split inside the "live" set explicitly.
STORY_21_4_OVERRIDE_POINTS = {"ANACONDA_DIST_BASE_URL", "AOSS_PREMIUM_BASE_URL"}
STORY_23_1_OVERRIDE_POINTS = {
    "HOMEBREW_BASE_URL",
    "NIXPKGS_BASE_URL",
    "SPACK_RAW_BASE_URL",
    "DEBIAN_BASE_URL",
    "FEDORA_SRC_BASE_URL",
}
# ...plus the reserved 20th (A2-A2 / FR-19). Story B8 LANDED its nodes, but
# no legacy resolve_*_urls helper ever backed it (the reserved slot was
# pre-declared, not ported) — which is exactly why it stays pinned SEPARATELY
# from the 19 helper-backed live points (same statement as globals.yml).
RESERVED_OVERRIDE_POINTS = {"BASILISK_BASE_URL"}
EXPECTED_OVERRIDE_POINTS = EXPECTED_LIVE_OVERRIDE_POINTS | RESERVED_OVERRIDE_POINTS

# Extra overrides asserted SEPARATELY (current data access, not helper-backed).
EXPECTED_EXTRA_OVERRIDES = {
    "ANACONDA_API_BASE_URL",  # gap A2-G2 (Phase F direct env override)
    "OSV_VULNS_BUCKET_URL",  # § 3.4 store 2 refresh endpoint (B5)
    "BIGQUERY_BASE_URL",  # Phase P connection base (A2-J1; B3 flips to GBQ)
    "PURL_ASSOCIATOR_BASE_URL",  # Story 21.6 (CAP-3 identity join): purl_associator_mappings_raw
}

# Full-URL fetcher settings (outside the 20-count) — set-pinned (P7).
EXPECTED_FETCHER_URLS = {
    "CISA_KEV_URL",
    "EPSS_FEED_URL",
    "CWE_CATALOG_URL",
}

# globals.yml `paths` — exact key -> env-var map (P6/P9; data_root became
# env-overridable in the review pass, P9). Story 21.1 (CAP-1): only the two
# ROOT paths are individually `${env_or:...}`-wrapped now — the three store
# paths below were demoted to plain `${paths.data_root}/stores/…` self-
# references (DERIVED_STORE_PATHS), so PYFORGE_ATLAS_DATA_ROOT is their
# ONLY override point (spec "Always" row).
PATHS_ENV_VARS = {
    "data_root": "PYFORGE_ATLAS_DATA_ROOT",
    "seed_root": "PYFORGE_ATLAS_SEED_ROOT",
    # Story 21.6 (CAP-3 identity join): discovery_local_recipes_raw's live
    # recipes/ tree root (LocalRecipesOverlayDataset).
    "local_recipes_dir": "PYFORGE_ATLAS_LOCAL_RECIPES_DIR",
}

# Story 21.1: the three § 3.4 external-refresh store paths — exact key ->
# expected `${paths.data_root}/<suffix>` suffix. No dedicated env var of
# their own any more (superseded VDB_STORE_PATH / OSV_OFFLINE_STORE_PATH /
# PYPI_CONDA_MAP_PATH — nothing in the codebase reads those names any more).
DERIVED_STORE_PATHS = {
    "vdb_store": "stores/vdb",
    "osv_offline_store": "stores/osv",
    "pypi_conda_map": "stores/pypi_conda_map.json",
}

# Story 21.6 (review finding, patch): `data_root`/`seed_root` are repo-root-
# relative (P9's own convention — correct for the pytest-based gates, which run
# with cwd = repo root). `local_recipes_dir` is the ONE exception: its real
# consumer is a live `kedro run` (`pyforge-atlas-bootstrap`, or a manual `cd
# src/shared/packages/pyforge-atlas && kedro run`), which runs with cwd = the
# KEDRO PROJECT ROOT (the pyforge-atlas member dir) — `kedro` needs its own
# `conf/`/`pyproject.toml` under cwd. `recipes/` only exists at the true repo
# root, so this default is deliberately MEMBER_DIR-relative
# (`../../../../recipes`), not REPO_ROOT-relative like its siblings —
# test_path_defaults_resolve_inside_the_repo_root resolves entries in this set
# against MEMBER_DIR instead of REPO_ROOT (still asserting the result lands
# inside the repo).
#
# `seed_root` joined this set 2026-08-31, landing this Story-21.6 branch: its
# `../../../../.claude/skills/conda-forge-expert/data` default (globals.yml)
# is the SAME MEMBER_DIR-relative depth as `local_recipes_dir`'s, not the
# REPO_ROOT-relative shape this comment originally described it as — that
# shape existed when this fix was authored (2026-08-26) and has since
# changed on main. Resolving it against REPO_ROOT (the original single-key
# set) overshoots four directories above the repo; against MEMBER_DIR it
# lands correctly.
MEMBER_DIR_RELATIVE_PATHS = {"local_recipes_dir", "seed_root"}

# Total env-override surface (review-pass P7 accounting, adjusted +1 by P9's
# data_root, +2 by Story 21.4, +1 extra_override +1 path by Story 21.6):
# endpoint_bases 27 (19 live + 1 reserved + 2 Story 21.4 + 5 Story 23.1) +
# extra_overrides 4 + fetcher_urls 3 + paths 6 = 40. Mirrored by a comment in globals.yml.
EXPECTED_ENV_OVERRIDE_SURFACE = 40

# Per-host credential allowlist (FR-1/AD-2): entry -> the ONLY credential
# key it may carry. No other entry may carry any credentials key, and the
# `jfrog` key may never appear on an entry whose host is not an Artifactory
# host (with shipped public defaults that means: on NO entry at all).
CREDENTIAL_ALLOWLIST = {
    "vcs_github_api_raw": "github_token",
    "pypi_bigquery_downloads_raw": "bigquery_adc",
    # Story 21.6 (CAP-3 identity join): both reuse the EXISTING github_token
    # credential — no second GitHub credential key.
    "openteams_project_1_board_raw": "github_token",
    "discovery_staged_recipes_prs_raw": "github_token",
}

STUB_CREDENTIALS = {
    "github_token": ["x-access-token", "stub-token"],
    "bigquery_adc": ["service-account", "stub-adc"],
    "jfrog": ["stub-user", "stub-key"],
}

# All env vars that could perturb the deterministic default resolution.
# Scrubbed PER-TEST by the autouse fixture below (review-pass P5 — the old
# module-level os.environ.pop mutated the process env for the whole run and
# leaked into kedro-test siblings; monkeypatch restores after every test).
_SCRUB_ENV_VARS = sorted(
    EXPECTED_OVERRIDE_POINTS | EXPECTED_EXTRA_OVERRIDES | EXPECTED_FETCHER_URLS | set(PATHS_ENV_VARS.values())
)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(autouse=True)
def _scrub_env(monkeypatch):
    """Per-test env scrub (P5): the gate always tests the shipped public
    defaults; restoration is automatic via monkeypatch, so the scrub never
    leaks into sibling suites. Tests that assert the env-override behavior
    simply setenv AFTER this fixture (ordinary monkeypatch usage)."""
    for var in _SCRUB_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    yield


def make_config_loader(runtime_params: dict | None = None, **overrides):
    """Build an OmegaConfigLoader EXACTLY as the project wires it —
    through ``pyforge.atlas.settings.CONFIG_LOADER_ARGS`` (so the gate
    exercises the real settings.py resolver wiring, A2-A4) — EXCEPT that
    the run env is pinned to ``base`` (review-pass P5: the gate must be
    immune to whatever sits in conf/local; the project default stays
    ``local`` for real runs)."""
    from kedro.config import OmegaConfigLoader

    from pyforge.atlas.settings import CONFIG_LOADER_ARGS

    kwargs = dict(CONFIG_LOADER_ARGS)
    kwargs["default_run_env"] = "base"  # gate-pinned; overrides may still win
    kwargs.update(overrides)
    if runtime_params is not None:
        kwargs["runtime_params"] = runtime_params
    return OmegaConfigLoader(conf_source=str(CONF_SOURCE), **kwargs)


# NOTE (P5): the config fixtures are FUNCTION-scoped on purpose — they must
# materialize under the per-test scrub above (a session-scoped fixture would
# be set up before a function-scoped autouse fixture and could capture an
# unscrubbed environment). Config loading is cheap enough for the suite.


@pytest.fixture()
def config_loader(_scrub_env):
    return make_config_loader()


@pytest.fixture()
def catalog_config(config_loader) -> dict:
    return dict(config_loader["catalog"])


@pytest.fixture()
def parameters(config_loader) -> dict:
    return dict(config_loader["parameters"])


@pytest.fixture(scope="session")
def catalog_raw_text() -> str:
    return CATALOG_YML.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def globals_raw() -> dict:
    """globals.yml parsed WITHOUT resolver interpolation (raw ${env_or:...}
    strings preserved) — the override-point tests assert the declared
    env-var wiring itself, not just resolved values."""
    return yaml.safe_load(GLOBALS_YML.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def parameters_raw_text() -> str:
    return PARAMETERS_YML.read_text(encoding="utf-8")


_ENTRY_KEY_RE = re.compile(r"^([a-z][a-z0-9_]*):\s*$")
_A3_MARKER = "# A3: IncrementalParquetDataset"
_FLIP_MARKER_RE = re.compile(r"^# FLIP\(([A-Za-z0-9-]+)\):")


def parse_markers(raw_text: str) -> dict[str, str]:
    """All flip markers (``# A3: IncrementalParquetDataset`` and
    ``# FLIP(<story>): ...``) mapped to the entry key each one annotates.

    Hardened per review-pass P5: blank lines and comment lines (indented or
    not) between marker and key are skipped; a marker that attaches to no
    bare top-level entry key FAILS LOUDLY instead of being silently dropped.
    """
    marked: dict[str, str] = {}
    lines = raw_text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == _A3_MARKER:
            marker = "A3"
        else:
            m = _FLIP_MARKER_RE.match(stripped)
            if not m:
                continue
            marker = m.group(1)
        attached = False
        for follow in lines[i + 1 :]:
            s = follow.strip()
            if not s or s.startswith("#"):
                continue  # blank/comment lines between marker and key: skip
            key_match = _ENTRY_KEY_RE.match(follow)
            if key_match is None:
                break  # first payload line is not a bare entry key -> loud fail
            marked[key_match.group(1)] = marker
            attached = True
            break
        if not attached:
            raise AssertionError(
                f"flip marker on line {i + 1} ({stripped!r}) does not attach "
                "to a bare top-level catalog entry key — fix the marker "
                "placement (markers must sit directly above their entry)"
            )
    return marked


def parse_flip_markers(raw_text: str) -> set[str]:
    """Entries annotated with the A3 flip marker (back-compat wrapper)."""
    return {name for name, marker in parse_markers(raw_text).items() if marker == "A3"}


def pipeline_for(name: str) -> str | None:
    """Longest-prefix match against the declared domain-prefix map."""
    for prefix in sorted(PREFIX_TO_PIPELINE, key=len, reverse=True):
        if name == prefix or name.startswith(prefix + "_"):
            return PREFIX_TO_PIPELINE[prefix]
    return None
