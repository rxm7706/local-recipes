"""Story 34.1 (CAP-64): the two seed-gap raw sources are JSONSourceDataset entries."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("entry", "expect", "key"),
    [("pypi_endoflife_raw", "list", None), ("seed_spdx_upstream_list_raw", "dict", "licenses")],
)
def test_the_catalog_wires_both_entries(catalog_config: dict, entry: str, expect: str, key: str | None) -> None:
    cfg = catalog_config[entry]

    assert cfg["type"] == "pyforge.atlas.datasets.JSONSourceDataset"
    assert cfg["expect"] == expect
    assert cfg.get("require_key") == key
    assert "credentials" not in cfg  # public: no credential is ever attached (AD-2)
    assert str(cfg["filepath"]).endswith(f"/raw/{entry}")
