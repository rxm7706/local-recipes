"""Unit tests for ``pyforge.herald.deck_store``."""

from __future__ import annotations

import io
from typing import Any

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.herald.deck_store import (
    DeckStoreConfigurationError,
    MemoryDeckStore,
    S3DeckStore,
    _is_not_found,
    is_sha256_content_key,
    open_deck_store,
)

_SHA_KEY = "sha256/" + "a" * 64


def test_put_if_absent_uploads_once_and_head_matches():
    store = MemoryDeckStore()
    payload = b"hello-deck-export"
    assert store.put_if_absent(_SHA_KEY, io.BytesIO(payload), content_type="text/plain") is True
    assert store.put_if_absent(_SHA_KEY, io.BytesIO(b"other"), content_type="text/plain") is False
    head = store.head(_SHA_KEY)
    assert head is not None
    assert head.size == len(payload)
    assert b"".join(store.open_stream(_SHA_KEY)) == payload


def test_memory_put_bytes_and_open_stream_missing_key():
    store = MemoryDeckStore()
    store.put_bytes(_SHA_KEY, b"manifest", content_type="application/json")
    head = store.head(_SHA_KEY)
    assert head is not None
    assert head.content_type == "application/json"
    with pytest.raises(KeyError, match="object store key not found"):
        b"".join(store.open_stream("missing"))


def test_open_deck_store_uses_memory_when_passed():
    mem = MemoryDeckStore()
    assert open_deck_store(memory=mem) is mem


def test_is_sha256_content_key():
    assert is_sha256_content_key(_SHA_KEY) is True
    assert is_sha256_content_key("manifests/pyforge-herald.json") is False


def test_deck_store_configuration_error_is_pyforge_error():
    assert issubclass(DeckStoreConfigurationError, PyforgeError)


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (Exception("plain"), False),
        (type("E", (Exception,), {"response": {"Error": {"Code": "NoSuchKey"}}})(), True),
        (type("E", (Exception,), {"response": {"ResponseMetadata": {"HTTPStatusCode": 404}}})(), True),
        (type("E", (Exception,), {"response": "not-a-dict"})(), False),
    ],
)
def test_is_not_found(exc: Exception, expected: bool):
    assert _is_not_found(exc) is expected


class _FakeBody:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            chunk, self._data = self._data, b""
            return chunk
        chunk, self._data = self._data[:size], self._data[size:]
        return chunk

    def close(self) -> None:
        self.closed = True


class _FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.head_raises: Exception | None = None

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if self.head_raises is not None:
            raise self.head_raises
        if Key not in self.objects:
            raise type(
                "NotFound",
                (Exception,),
                {"response": {"Error": {"Code": "404"}, "ResponseMetadata": {"HTTPStatusCode": 404}}},
            )()
        data, content_type = self.objects[Key]
        return {"ContentLength": len(data), "ContentType": content_type}

    def upload_fileobj(self, stream: io.BytesIO, bucket: str, key: str, *, ExtraArgs: dict[str, str]) -> None:
        self.objects[key] = (stream.read(), ExtraArgs["ContentType"])

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
    ) -> None:
        self.objects[Key] = (Body, ContentType)

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        data, content_type = self.objects[Key]
        return {"Body": _FakeBody(data)}


def test_s3_adapter_round_trip_and_put_if_absent():
    client = _FakeS3Client()
    store = S3DeckStore(client, bucket="deck-bucket", prefix="herald/decks")
    payload = b"export-bytes"
    assert store.put_if_absent("rel-key", io.BytesIO(payload), content_type="application/octet-stream") is True
    assert store.put_if_absent("rel-key", io.BytesIO(b"x"), content_type="application/octet-stream") is False
    head = store.head("rel-key")
    assert head is not None
    assert head.size == len(payload)
    assert b"".join(store.open_stream("rel-key")) == payload
    store.put_bytes("manifest.json", b"{}", content_type="application/json")
    assert client.objects["herald/decks/manifest.json"][0] == b"{}"


def test_s3_head_raw_reraises_non_not_found():
    client = _FakeS3Client()
    client.head_raises = RuntimeError("upstream")
    store = S3DeckStore(client, bucket="b", prefix="p")
    with pytest.raises(RuntimeError, match="upstream"):
        store.head("missing")


def test_s3_from_environ_refuses_missing_endpoint(monkeypatch):
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


def test_s3_from_environ_builds_client(monkeypatch):
    monkeypatch.setenv("OBJECT_STORAGE_ENDPOINT_URL", "http://127.0.0.1:9000")
    monkeypatch.setenv("OBJECT_STORAGE_ACCESS_KEY", "access")
    monkeypatch.setenv("OBJECT_STORAGE_SECRET_KEY", "secret")
    monkeypatch.setenv("OBJECT_STORAGE_BUCKET", "deck-bucket")
    monkeypatch.setenv("OBJECT_STORAGE_PREFIX", "herald/decks")

    class _FakeBoto3:
        @staticmethod
        def client(*_args: object, **_kwargs: object) -> _FakeS3Client:
            return _FakeS3Client()

    import sys

    fake_boto3 = type(sys)("boto3")
    fake_boto3.client = _FakeBoto3.client
    fake_botocore = type(sys)("botocore.config")
    fake_botocore.Config = lambda **_kw: object()
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore.config", fake_botocore)

    store = S3DeckStore.from_environ()
    assert isinstance(store, S3DeckStore)
    assert store.put_if_absent("k", io.BytesIO(b"x"), content_type="text/plain") is True


def test_open_deck_store_without_memory_calls_from_environ(monkeypatch):
    monkeypatch.setenv("OBJECT_STORAGE_ENDPOINT_URL", "http://127.0.0.1:9000")
    monkeypatch.setenv("OBJECT_STORAGE_ACCESS_KEY", "access")
    monkeypatch.setenv("OBJECT_STORAGE_SECRET_KEY", "secret")
    monkeypatch.setenv("OBJECT_STORAGE_BUCKET", "deck-bucket")
    monkeypatch.setenv("OBJECT_STORAGE_PREFIX", "herald/decks")

    import sys

    fake_boto3 = type(sys)("boto3")

    def _client(*_args: object, **_kwargs: object) -> _FakeS3Client:
        return _FakeS3Client()

    fake_boto3.client = _client
    fake_botocore = type(sys)("botocore.config")
    fake_botocore.Config = lambda **_kw: object()
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore.config", fake_botocore)

    store = open_deck_store()
    assert isinstance(store, S3DeckStore)
