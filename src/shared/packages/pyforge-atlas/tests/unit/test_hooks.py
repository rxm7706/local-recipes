"""Story A3 — ``ProjectHooks.after_catalog_created`` unit tests (collected by
``kedro-test``).

Review-pass P5 (HEADLINE): the hook is the ENTIRE production TTL-wiring path, yet
the dataset unit tests set ``.ttl_seconds`` directly and never exercise it — a real
hook bug would ship as "the pipeline silently never re-fetches." These tests drive
``after_catalog_created`` against a REAL kedro 1.5.0 ``DataCatalog`` (keys()/
__getitem__ verified live) and assert the injection, the loud-fail on a missing ttl
(P6), the per-dataset materialization isolation (P7), and the interface guard (P8).

Fixture-based, offline, non-credentialed (NFR-1/AD-11): tmp_path Parquet filepaths,
no HTTP/DB, no ``load()``/``save()`` (construction only).
"""

from __future__ import annotations

import pytest
from kedro.io import DataCatalog

from pyforge.atlas.datasets import IncrementalParquetDataset
from pyforge.atlas.hooks import ProjectHooks

_INCR = "pyforge.atlas.datasets.IncrementalParquetDataset"


def _conf(tmp_path, names):
    """Raw catalog config: an IncrementalParquetDataset per name plus one
    non-matching (plain pandas.ParquetDataset) entry."""
    cfg = {
        name: {"type": _INCR, "filepath": str(tmp_path / name / f"{name}.parquet")}
        for name in names
    }
    cfg["plain_output"] = {
        "type": "pandas.ParquetDataset",
        "filepath": str(tmp_path / "plain_output" / "plain_output.parquet"),
    }
    return cfg


# -- P5: the hook actually injects per-dataset ttls ------------------------


def test_after_catalog_created_injects_matching_and_leaves_others_none(tmp_path):
    conf = _conf(tmp_path, ["ds_a", "ds_b"])
    catalog = DataCatalog.from_config(conf)
    ttls = {"ds_a": 604800, "ds_b": 2592000}

    ProjectHooks().after_catalog_created(
        catalog=catalog, conf_catalog=conf, parameters={"ttls": ttls}
    )

    # matching IncrementalParquetDataset instances received their ttl...
    assert catalog["ds_a"].ttl_seconds == 604800
    assert catalog["ds_b"].ttl_seconds == 2592000
    # ...and the non-matching (plain) dataset was untouched (not an
    # IncrementalParquetDataset, so it has no ttl_seconds attribute at all).
    assert not isinstance(catalog["plain_output"], IncrementalParquetDataset)


def test_after_catalog_created_coerces_string_ttl(tmp_path):
    """A ttls value arriving as a string is coerced by the dataset setter (P3)
    exercised through the real hook path."""
    conf = _conf(tmp_path, ["ds_a"])
    catalog = DataCatalog.from_config(conf)
    ProjectHooks().after_catalog_created(
        catalog=catalog, conf_catalog=conf, parameters={"ttls": {"ds_a": "3600"}}
    )
    assert catalog["ds_a"].ttl_seconds == 3600


def test_no_ttls_namespace_injects_nothing_when_no_flipped_entries(tmp_path):
    """A catalog with no IncrementalParquetDataset entries + no ttls is a no-op."""
    conf = {
        "plain_output": {
            "type": "pandas.ParquetDataset",
            "filepath": str(tmp_path / "p.parquet"),
        }
    }
    catalog = DataCatalog.from_config(conf)
    # parameters with no 'ttls' key at all -> no injection, no raise
    ProjectHooks().after_catalog_created(
        catalog=catalog, conf_catalog=conf, parameters={}
    )


# -- P6: a flipped-but-un-TTL'd entry FAILS LOUDLY -------------------------


def test_flipped_entry_without_ttl_raises(tmp_path):
    """An IncrementalParquetDataset with no params:ttls.<name> would keep
    ttl_seconds=None and SILENTLY never re-fetch. The hook must raise so a
    divergence between the flip list and the ttls namespace fails the run."""
    conf = _conf(tmp_path, ["ds_a", "ds_b"])
    catalog = DataCatalog.from_config(conf)
    # ttls covers ds_a only -> ds_b is a flipped-but-un-TTL'd entry
    with pytest.raises(ValueError, match=r"never re-fetch.*ds_b"):
        ProjectHooks().after_catalog_created(
            catalog=catalog, conf_catalog=conf, parameters={"ttls": {"ds_a": 7}}
        )


def test_all_flipped_entries_covered_does_not_raise(tmp_path):
    conf = _conf(tmp_path, ["ds_a", "ds_b"])
    catalog = DataCatalog.from_config(conf)
    ProjectHooks().after_catalog_created(
        catalog=catalog, conf_catalog=conf, parameters={"ttls": {"ds_a": 7, "ds_b": 9}}
    )


# -- P7: one broken unrelated dataset must not sink the injection ----------


def test_broken_unrelated_dataset_does_not_abort_injection(tmp_path):
    """P7: a ttl-named entry that fails to materialize is isolated (logged, skipped)
    and does NOT prevent injection into the healthy entries. A ttls key that maps to
    no catalog entry (KeyError on access) is the simplest broken-access case."""
    conf = _conf(tmp_path, ["ds_a"])
    catalog = DataCatalog.from_config(conf)
    # 'ghost' is in ttls but not in the catalog -> catalog['ghost'] raises; the
    # hook must swallow it and still inject ds_a. (No flipped-without-ttl entry,
    # so P6 does not fire.)
    ProjectHooks().after_catalog_created(
        catalog=catalog,
        conf_catalog=conf,
        parameters={"ttls": {"ds_a": 11, "ghost": 22}},
    )
    assert catalog["ds_a"].ttl_seconds == 11


def test_non_ttl_entries_are_not_materialized_eagerly(tmp_path, monkeypatch):
    """P7 laziness: the hook short-circuits ``if name not in ttls`` BEFORE
    ``catalog[name]``, so a dataset with no ttl is never materialized by the hook.
    Proven by making __getitem__ record which names it was asked to materialize."""
    conf = _conf(tmp_path, ["ds_a", "ds_b"])
    catalog = DataCatalog.from_config(conf)

    accessed: list[str] = []
    orig_getitem = type(catalog).__getitem__

    def _spy(self, name):
        accessed.append(name)
        return orig_getitem(self, name)

    monkeypatch.setattr(type(catalog), "__getitem__", _spy)
    ProjectHooks().after_catalog_created(
        catalog=catalog, conf_catalog=conf, parameters={"ttls": {"ds_a": 5, "ds_b": 6}}
    )
    # only the ttl-named entries were materialized; 'plain_output' was never touched
    assert "plain_output" not in accessed
    assert set(accessed) == {"ds_a", "ds_b"}


# -- P8: guard the catalog interface --------------------------------------


def test_catalog_without_keys_interface_raises():
    """A catalog lacking keys()/__getitem__ (e.g. a classic pre-1.x catalog with
    only .list()) would silently inject nothing — the hook must fail clearly."""

    class _LegacyCatalogStub:
        def list(self):  # noqa: A003 - mimics the old API deliberately
            return ["ds_a"]

    with pytest.raises(TypeError, match="keys.*__getitem__"):
        ProjectHooks().after_catalog_created(
            catalog=_LegacyCatalogStub(), conf_catalog={}, parameters={"ttls": {}}
        )
