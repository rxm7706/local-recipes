"""Gate check 1 (AC-1/AC-3): full catalog resolution, zero network.

Every declared entry must instantiate via ``DataCatalog.from_config`` over
the merged conf/base config with STUB credentials, with the network
hard-blocked for the duration (offline by construction, NFR-1)."""

from __future__ import annotations

import socket
from contextlib import contextmanager

import pytest

from .conftest import (
    EXPECTED_PIPELINE_COUNTS,
    EXPECTED_TOTAL,
    STUB_CREDENTIALS,
    pipeline_for,
)


@contextmanager
def _network_blocked():
    """Hard-fail the test on ANY socket connection attempt."""

    def _blocked(*args, **kwargs):  # pragma: no cover - only on violation
        raise AssertionError(
            "network access attempted during catalog resolution (gate is offline-only)"
        )

    orig_connect = socket.socket.connect
    orig_create = socket.create_connection
    socket.socket.connect = _blocked  # type: ignore[method-assign]
    socket.create_connection = _blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = orig_connect  # type: ignore[method-assign]
        socket.create_connection = orig_create  # type: ignore[assignment]


def test_entry_count_is_pinned(catalog_config):
    assert len(catalog_config) == EXPECTED_TOTAL, (
        f"catalog entry count changed: {len(catalog_config)} != {EXPECTED_TOTAL} "
        "(update EXPECTED_* in tests/catalog/conftest.py AND the story record)"
    )


def test_per_pipeline_counts_are_pinned(catalog_config):
    actual: dict[str, int] = {}
    for name in catalog_config:
        pipeline = pipeline_for(name)
        assert pipeline is not None, f"{name}: no declared domain prefix matches"
        actual[pipeline] = actual.get(pipeline, 0) + 1
    assert actual == EXPECTED_PIPELINE_COUNTS


def test_full_catalog_resolves_with_stub_credentials_offline(catalog_config):
    from kedro.io import DataCatalog

    with _network_blocked():
        catalog = DataCatalog.from_config(
            dict(catalog_config), credentials=dict(STUB_CREDENTIALS)
        )
    resolved = set(
        catalog.list() if callable(getattr(catalog, "list", None)) else list(catalog)
    )
    missing = set(catalog_config) - resolved
    assert not missing, f"entries failed to materialize: {sorted(missing)}"


def test_every_entry_instantiates_individually(catalog_config):
    """Per-entry instantiation (sharper failure localization than the
    whole-catalog test when a single entry regresses)."""
    from kedro.io import DataCatalog

    failures: dict[str, str] = {}
    with _network_blocked():
        for name, spec in catalog_config.items():
            try:
                DataCatalog.from_config(
                    {name: dict(spec)}, credentials=dict(STUB_CREDENTIALS)
                )
            except Exception as exc:  # noqa: BLE001 - reported en masse
                failures[name] = f"{type(exc).__name__}: {exc}"
    assert not failures, f"entries failed to instantiate: {failures}"
