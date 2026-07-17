"""Gate check 5 (AC-4): endpoint-override accounting.

Exactly 20 `<HOST>_BASE_URL` override points (the 19 live resolve_*_urls
helpers + the reserved BASILISK_BASE_URL) survive as dataset-level endpoint
config, each env-var-overridable with a public default. The A2-G2 extra
(ANACONDA_API_BASE_URL) is asserted SEPARATELY, outside the 20-count.
"""

from __future__ import annotations

import re

from .conftest import (
    CATALOG_YML,
    EXPECTED_EXTRA_OVERRIDES,
    EXPECTED_OVERRIDE_POINTS,
    make_config_loader,
)

_ENV_OR_RE = re.compile(r"^\$\{env_or:([A-Z0-9_]+),\S.*\}$")


def test_exactly_20_override_points(globals_raw):
    bases = globals_raw.get("endpoint_bases") or {}
    assert len(bases) == 20, f"endpoint_bases must carry exactly 20 keys, got {len(bases)}"
    assert set(bases) == EXPECTED_OVERRIDE_POINTS


def test_each_override_point_is_env_overridable_with_default(globals_raw):
    bad = {}
    for section in ("endpoint_bases", "extra_overrides", "fetcher_urls"):
        for key, value in (globals_raw.get(section) or {}).items():
            m = _ENV_OR_RE.match(str(value))
            if not m or m.group(1) != key:
                bad[f"{section}.{key}"] = value
    assert not bad, f"override wiring violations (want ${{env_or:<KEY>,<default>}}): {bad}"


def test_anaconda_api_extra_override_survives(globals_raw, catalog_config):
    """Gap A2-G2: Phase F's ANACONDA_API_BASE_URL is current data access but
    NOT one of the 20 helper-backed points — asserted separately here, and it
    must actually back the core_anaconda_downloads_raw entry."""
    extras = globals_raw.get("extra_overrides") or {}
    assert set(extras) == EXPECTED_EXTRA_OVERRIDES
    assert "ANACONDA_API_BASE_URL" in extras
    # with no env override, the entry resolves to the public api.anaconda.org
    url = catalog_config["core_anaconda_downloads_raw"]["url"]
    assert url.startswith("https://api.anaconda.org")


def test_catalog_never_hardcodes_a_host():
    """AD-13: catalog entries reference ${globals:...} — no literal host."""
    raw = CATALOG_YML.read_text(encoding="utf-8")
    assert "https://" not in raw and "http://" not in raw


def test_env_override_reaches_resolved_catalog(monkeypatch):
    """End-to-end: an explicit env var beats the public default (spine
    Config row — os.environ.setdefault semantics)."""
    monkeypatch.setenv("CONDA_FORGE_BASE_URL", "https://mirror.corp/artifactory/conda-forge")
    loader = make_config_loader()
    url = dict(loader["catalog"])["core_repodata_raw"]["url"]
    assert url.startswith("https://mirror.corp/artifactory/conda-forge")


def test_runtime_parameterized_entry_dataset(monkeypatch):
    """§ 3.4: user-supplied intake is an entry-scoped, runtime-parameterized
    dataset — `kedro run --params sbom_intake_path=...` re-points it."""
    loader = make_config_loader(runtime_params={"sbom_intake_path": "/tmp/my-intake.json"})
    assert dict(loader["catalog"])["sbom_intake_entry"]["filepath"] == "/tmp/my-intake.json"
