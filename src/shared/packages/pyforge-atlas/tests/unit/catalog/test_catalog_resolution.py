"""Gate check 1 (AC-1/AC-3): full catalog resolution, zero network.

Every declared entry must MATERIALIZE via ``DataCatalog.from_config`` over
the merged conf/base config with STUB credentials, with the network
hard-blocked for the duration (offline by construction, NFR-1).

Review-pass P1: Kedro 1.5.0's ``DataCatalog.from_config`` is LAZY — config
parsing alone validates nothing (a bogus ``type:`` only explodes when the
entry is accessed). The tests below therefore materialize EVERY entry
(``catalog[name]``), asserting the dataset OBJECT constructs. They do not
call ``load()`` — construction only; loading would touch disk/network by
design and the gate is offline.
"""

from __future__ import annotations

import socket
from contextlib import contextmanager

from .conftest import (
    EXPECTED_PIPELINE_COUNTS,
    EXPECTED_TOTAL,
    STUB_CREDENTIALS,
    pipeline_for,
)


@contextmanager
def _network_blocked():
    """Hard-fail the test on ANY network attempt (connect, name resolution,
    connect_ex probing, UDP sendto — review-pass P1 widened the block)."""

    def _blocked(*args, **kwargs):  # pragma: no cover - only on violation
        raise AssertionError(
            "network access attempted during catalog resolution (gate is offline-only)"
        )

    orig_connect = socket.socket.connect
    orig_connect_ex = socket.socket.connect_ex
    orig_sendto = socket.socket.sendto
    orig_create = socket.create_connection
    orig_getaddrinfo = socket.getaddrinfo
    socket.socket.connect = _blocked  # type: ignore[method-assign]
    socket.socket.connect_ex = _blocked  # type: ignore[method-assign]
    socket.socket.sendto = _blocked  # type: ignore[method-assign]
    socket.create_connection = _blocked  # type: ignore[assignment]
    socket.getaddrinfo = _blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = orig_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = orig_connect_ex  # type: ignore[method-assign]
        socket.socket.sendto = orig_sendto  # type: ignore[method-assign]
        socket.create_connection = orig_create  # type: ignore[assignment]
        socket.getaddrinfo = orig_getaddrinfo  # type: ignore[assignment]


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


def test_full_catalog_materializes_with_stub_credentials_offline(catalog_config):
    """Every entry's dataset object must CONSTRUCT (P1: `catalog[name]`
    forces the lazy catalog to instantiate the dataset — construction only,
    never load())."""
    from kedro.io import DataCatalog

    failures: dict[str, str] = {}
    with _network_blocked():
        catalog = DataCatalog.from_config(
            dict(catalog_config), credentials=dict(STUB_CREDENTIALS)
        )
        for name in catalog_config:
            try:
                dataset = catalog[name]
                assert dataset is not None
            except Exception as exc:  # noqa: BLE001 - reported en masse
                failures[name] = f"{type(exc).__name__}: {exc}"
    assert not failures, f"entries failed to materialize: {failures}"


def test_every_entry_instantiates_individually(catalog_config):
    """Per-entry materialization (sharper failure localization than the
    whole-catalog test when a single entry regresses)."""
    from kedro.io import DataCatalog

    failures: dict[str, str] = {}
    with _network_blocked():
        for name, spec in catalog_config.items():
            try:
                catalog = DataCatalog.from_config(
                    {name: dict(spec)}, credentials=dict(STUB_CREDENTIALS)
                )
                dataset = catalog[name]  # force materialization (P1)
                assert dataset is not None
            except Exception as exc:  # noqa: BLE001 - reported en masse
                failures[name] = f"{type(exc).__name__}: {exc}"
    assert not failures, f"entries failed to instantiate: {failures}"
