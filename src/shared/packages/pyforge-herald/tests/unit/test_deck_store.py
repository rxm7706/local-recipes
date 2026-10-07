"""Unit tests for ``pyforge.herald.deck_store``."""

from __future__ import annotations

import io

import pytest

from pyforge.herald.deck_store import MemoryDeckStore


def test_put_if_absent_uploads_once_and_head_matches():
    store = MemoryDeckStore()
    payload = b"hello-deck-export"
    assert store.put_if_absent("sha256/" + "a" * 64, io.BytesIO(payload), content_type="text/plain") is True
    assert store.put_if_absent("sha256/" + "a" * 64, io.BytesIO(b"other"), content_type="text/plain") is False
    head = store.head("sha256/" + "a" * 64)
    assert head is not None
    assert head.size == len(payload)
    assert b"".join(store.open_stream("sha256/" + "a" * 64)) == payload


def test_open_deck_store_uses_memory_when_passed():
    from pyforge.herald.deck_store import open_deck_store

    mem = MemoryDeckStore()
    assert open_deck_store(memory=mem) is mem


def test_s3_from_environ_refuses_missing_endpoint(monkeypatch):
    from pyforge.herald.deck_store import DeckStoreConfigurationError, S3DeckStore

    for key in (
        "OBJECT_STORAGE_ENDPOINT_URL",
        "OBJECT_STORAGE_ACCESS_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
        "OBJECT_STORAGE_BUCKET",
        "OBJECT_STORAGE_PREFIX",
    ):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(DeckStoreConfigurationError, match="OBJECT_STORAGE_ENDPOINT_URL"):
        S3DeckStore.from_environ()
