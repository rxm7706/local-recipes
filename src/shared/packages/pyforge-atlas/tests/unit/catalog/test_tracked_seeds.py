"""Story 21.4 (review-pass 1) — the catalog's LITERAL tracked-seed paths resolve.

`discovery_aoss_free_python_raw.filepath` and `discovery_anaconda_dist_2026x_raw.seed_path`
are plain literal strings in catalog.yml (no `${...}` interpolation). A typo there would
leave the air-gap seed silently EMPTY while every other test stayed green — so this
module reads the raw YAML and drives the real datasets/helpers with the exact configured
strings. Offline, local-file only.
"""

from __future__ import annotations

import yaml

from pyforge.atlas.datasets import TrackedSeedDataset, read_tracked_seed

from .conftest import CATALOG_YML, CONF_SOURCE

MEMBER_DIR = CONF_SOURCE.parent


def _raw_catalog() -> dict:
    return yaml.safe_load(CATALOG_YML.read_text(encoding="utf-8"))


def _literal(entry: str, key: str) -> str:
    value = _raw_catalog()[entry][key]
    assert isinstance(value, str) and "${" not in value, (entry, key, value)
    return value


def test_aoss_free_seed_catalog_filepath_resolves_to_a_real_file():
    value = _literal("discovery_aoss_free_python_raw", "filepath")
    assert value.startswith("conf/base/seeds/"), value
    assert (MEMBER_DIR / value).is_file(), f"catalog filepath does not resolve: {MEMBER_DIR / value}"


def test_anaconda_dist_seed_catalog_seed_path_resolves_to_a_real_file():
    value = _literal("discovery_anaconda_dist_2026x_raw", "seed_path")
    assert value.startswith("conf/base/seeds/"), value
    assert (MEMBER_DIR / value).is_file(), f"catalog seed_path does not resolve: {MEMBER_DIR / value}"


def test_tracked_seed_dataset_loads_the_exact_catalog_string(monkeypatch, tmp_path):
    """Drives TrackedSeedDataset (and _resolve_seed_path) with the exact catalog value,
    from a CWD where the relative path does NOT exist (the member-dir fallback)."""
    value = _literal("discovery_aoss_free_python_raw", "filepath")
    monkeypatch.chdir(tmp_path)
    frame = TrackedSeedDataset(filepath=value, name_column="pypi_name").load()
    assert len(frame) >= 1_000, f"air-gap seed loaded only {len(frame)} rows via {value!r}"
    assert list(frame.columns) == ["pypi_name", "source"]


def test_anaconda_dist_seed_parses_from_the_exact_catalog_string(monkeypatch, tmp_path):
    value = _literal("discovery_anaconda_dist_2026x_raw", "seed_path")
    monkeypatch.chdir(tmp_path)
    entries = read_tracked_seed(value)
    assert len(entries) >= 600, f"anaconda dist seed parsed only {len(entries)} entries via {value!r}"
    assert all(isinstance(e, dict) and e.get("conda_name") for e in entries)
