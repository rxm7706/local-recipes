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
- ``STUB_CREDENTIALS``    — per-host stub keys (zero network; NFR-2:
  the gate never touches a credentialed endpoint).

Everything is fixture-based, offline, and non-credentialed (AD-11/NFR-1).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest
import yaml

MEMBER_DIR = Path(__file__).resolve().parents[2]
CONF_SOURCE = MEMBER_DIR / "conf"
CATALOG_YML = CONF_SOURCE / "base" / "catalog.yml"
GLOBALS_YML = CONF_SOURCE / "base" / "globals.yml"
PARAMETERS_YML = CONF_SOURCE / "base" / "parameters.yml"
SRC_DIR = MEMBER_DIR / "src"
ATLAS_PKG = SRC_DIR / "pyforge" / "atlas"

# The four node-code dirs policed by the no-inline-IO + AD-1 meta-tests
# (missing dirs are tolerated — the gate stays green against the A1
# scaffold state and arms itself as Wave B lands node code).
NODE_DIRS = ("pipelines", "datasets", "hooks", "mcp")

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
}

# Final implemented counts (drafting target was ~77: 35 sources + ~42
# outputs; implemented = 35 sources + 38 outputs — the 6 purl artifacts
# collapse into ONE partitioned dataset and the repo-scope sbom report is
# deferred to F4 per AD-12; recorded in the Dev Agent Record).
EXPECTED_PIPELINE_COUNTS = {
    "core": 16,
    "pypi_intelligence": 15,
    "vulnerability": 12,
    "vcs_health": 17,
    "universal_sbom": 3,
    "seed_gaps": 8,
    "derived_artifacts": 2,
}
EXPECTED_TOTAL = 73

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
    "pypi_intelligence_enriched",
    "vulnerability_package_rollup",
    "vulnerability_package_version_vulns",
    "vcs_upstream_versions",
    "vcs_registry_versions",
    "vcs_live_health",
}

# AC-4 accounting: the 19 live resolve_*_urls helpers (verified at b18cbb5
# AND against the live tree 2026-07-17) + the reserved 20th BASILISK_BASE_URL.
EXPECTED_OVERRIDE_POINTS = {
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
    "BASILISK_BASE_URL",  # the reserved 20th (A2-A2 / FR-19; nodes = B8)
}

# Extra overrides asserted SEPARATELY (current data access, not helper-backed).
EXPECTED_EXTRA_OVERRIDES = {
    "ANACONDA_API_BASE_URL",  # gap A2-G2 (Phase F direct env override)
    "OSV_VULNS_BUCKET_URL",   # § 3.4 store 2 refresh endpoint (B5)
    "BIGQUERY_BASE_URL",      # Phase P connection base (A2-J1; B3 flips to GBQ)
}

# Per-host credential allowlist (FR-1/AD-2): entry -> the ONLY credential
# key it may carry. No other entry may carry any credentials key, and the
# `jfrog` key may never appear on an entry whose host is not an Artifactory
# host (with shipped public defaults that means: on NO entry at all).
CREDENTIAL_ALLOWLIST = {
    "vcs_github_api_raw": "github_token",
    "pypi_bigquery_downloads_raw": "bigquery_adc",
}

STUB_CREDENTIALS = {
    "github_token": ["x-access-token", "stub-token"],
    "bigquery_adc": ["service-account", "stub-adc"],
    "jfrog": ["stub-user", "stub-key"],
}

# All env vars that could perturb the deterministic default resolution —
# scrubbed once at collection time so the gate always tests the shipped
# public defaults (the env-override behavior has its own dedicated test).
_SCRUB_ENV_VARS = sorted(
    EXPECTED_OVERRIDE_POINTS
    | EXPECTED_EXTRA_OVERRIDES
    | {
        "CISA_KEV_URL",
        "EPSS_FEED_URL",
        "CWE_CATALOG_URL",
        "PYFORGE_ATLAS_SEED_ROOT",
        "VDB_STORE_PATH",
        "OSV_OFFLINE_STORE_PATH",
        "PYPI_CONDA_MAP_PATH",
    }
)
for _var in _SCRUB_ENV_VARS:
    os.environ.pop(_var, None)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def make_config_loader(runtime_params: dict | None = None, **overrides):
    """Build an OmegaConfigLoader EXACTLY as the project wires it —
    through ``pyforge.atlas.settings.CONFIG_LOADER_ARGS`` (so the gate
    exercises the real settings.py resolver wiring, A2-A4)."""
    from kedro.config import OmegaConfigLoader

    from pyforge.atlas.settings import CONFIG_LOADER_ARGS

    kwargs = dict(CONFIG_LOADER_ARGS)
    kwargs.update(overrides)
    if runtime_params is not None:
        kwargs["runtime_params"] = runtime_params
    return OmegaConfigLoader(conf_source=str(CONF_SOURCE), **kwargs)


@pytest.fixture(scope="session")
def config_loader():
    return make_config_loader()


@pytest.fixture(scope="session")
def catalog_config(config_loader) -> dict:
    return dict(config_loader["catalog"])


@pytest.fixture(scope="session")
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


_ENTRY_KEY_RE = re.compile(r"^([a-z][a-z0-9_]*):\s*$")
_A3_MARKER = "# A3: IncrementalParquetDataset"


def parse_flip_markers(raw_text: str) -> set[str]:
    """Entries annotated with the A3 flip marker (marker line above the
    entry key, comment lines in between tolerated)."""
    marked: set[str] = set()
    lines = raw_text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() != _A3_MARKER:
            continue
        for follow in lines[i + 1 :]:
            if follow.startswith("#") or not follow.strip():
                continue
            m = _ENTRY_KEY_RE.match(follow)
            if m:
                marked.add(m.group(1))
            break
    return marked


def pipeline_for(name: str) -> str | None:
    """Longest-prefix match against the declared domain-prefix map."""
    for prefix in sorted(PREFIX_TO_PIPELINE, key=len, reverse=True):
        if name == prefix or name.startswith(prefix + "_"):
            return PREFIX_TO_PIPELINE[prefix]
    return None
