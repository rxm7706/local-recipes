"""Object-store port for deck publish (CAP-54 D2; steward Story 74.1's env contract).

The only herald module that talks to the store. Configuration comes from the
process environment only — the three settings the platform seam reads plus
bucket and prefix — never from Django or ``config.object_storage``.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from typing import BinaryIO
from typing import Final
from typing import Protocol

__all__ = [
    "ACCESS_KEY_ENV",
    "BUCKET_ENV",
    "DeckStore",
    "DeckStoreConfigurationError",
    "ENDPOINT_URL_ENV",
    "MemoryDeckStore",
    "PREFIX_ENV",
    "SECRET_KEY_ENV",
    "S3DeckStore",
    "open_deck_store",
]

ENDPOINT_URL_ENV: Final[str] = "OBJECT_STORAGE_ENDPOINT_URL"
ACCESS_KEY_ENV: Final[str] = "OBJECT_STORAGE_ACCESS_KEY"
SECRET_KEY_ENV: Final[str] = "OBJECT_STORAGE_SECRET_KEY"  # noqa: S105
BUCKET_ENV: Final[str] = "OBJECT_STORAGE_BUCKET"
PREFIX_ENV: Final[str] = "OBJECT_STORAGE_PREFIX"

_CHUNK_BYTES: Final[int] = 1024 * 1024
_SHA256_KEY: Final[re.Pattern[str]] = re.compile(r"sha256/[0-9a-f]{64}")
_NOT_FOUND_CODES: Final[frozenset[str]] = frozenset({"404", "NoSuchKey", "NotFound"})
_HTTP_NOT_FOUND: Final[int] = 404
_REGION_NAME: Final[str] = "us-east-1"


class DeckStoreConfigurationError(RuntimeError):
    """A required object-storage setting is missing or empty."""


@dataclass(frozen=True, slots=True)
class HeadResult:
    size: int
    content_type: str


class DeckStore(Protocol):
    def put_if_absent(self, key: str, stream: BinaryIO, *, content_type: str) -> bool:
        """Upload when *key* is absent; return True when an upload ran."""

    def head(self, key: str) -> HeadResult | None:
        """Return metadata when *key* exists, else None."""

    def open_stream(self, key: str) -> Iterator[bytes]:
        """Yield the object at *key* in bounded chunks."""

    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        """Replace *key* with *data* (manifest writes)."""


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not isinstance(value, str) or not value.strip():
        msg = (
            f"{name} is not configured. Deck publish needs object storage "
            "settings in the environment (see config/settings/base.py); "
            "run `pixi run -e platform-object-storage platform-object-storage-up` "
            "for a local backend."
        )
        raise DeckStoreConfigurationError(msg)
    return value.strip()


def _is_not_found(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return False
    code = (response.get("Error") or {}).get("Code")
    status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    return str(code) in _NOT_FOUND_CODES or status == _HTTP_NOT_FOUND


def _object_key(prefix: str, key: str) -> str:
    return f"{prefix.strip('/')}/{key}"


class S3DeckStore:
    """S3 adapter configured from the process environment."""

    def __init__(self, client: Any, *, bucket: str, prefix: str) -> None:
        self._client = client
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    @classmethod
    def from_environ(cls) -> S3DeckStore:
        endpoint = _env(ENDPOINT_URL_ENV)
        access_key = _env(ACCESS_KEY_ENV)
        secret_key = _env(SECRET_KEY_ENV)
        bucket = _env(BUCKET_ENV)
        prefix = _env(PREFIX_ENV)
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            msg = "boto3 is required for the S3 deck store adapter but is not installed"
            raise DeckStoreConfigurationError(msg) from exc
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=_REGION_NAME,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        return cls(client, bucket=bucket, prefix=prefix)

    def _head_raw(self, key: str) -> dict[str, Any] | None:
        try:
            return self._client.head_object(Bucket=self._bucket, Key=_object_key(self._prefix, key))
        except Exception as exc:
            if _is_not_found(exc):
                return None
            raise

    def head(self, key: str) -> HeadResult | None:
        meta = self._head_raw(key)
        if meta is None:
            return None
        return HeadResult(
            size=int(meta["ContentLength"]),
            content_type=str(meta.get("ContentType") or "application/octet-stream"),
        )

    def put_if_absent(self, key: str, stream: BinaryIO, *, content_type: str) -> bool:
        if self._head_raw(key) is not None:
            return False
        self._client.upload_fileobj(
            stream,
            self._bucket,
            _object_key(self._prefix, key),
            ExtraArgs={"ContentType": content_type},
        )
        return True

    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=_object_key(self._prefix, key),
            Body=data,
            ContentType=content_type,
        )

    def open_stream(self, key: str) -> Iterator[bytes]:
        body = self._client.get_object(Bucket=self._bucket, Key=_object_key(self._prefix, key))["Body"]

        def _iter() -> Iterator[bytes]:
            try:
                while chunk := body.read(_CHUNK_BYTES):
                    yield chunk
            finally:
                body.close()

        return _iter()


class MemoryDeckStore:
    """In-memory fake for the herald test suite."""

    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}

    def head(self, key: str) -> HeadResult | None:
        entry = self._objects.get(key)
        if entry is None:
            return None
        data, content_type = entry
        return HeadResult(size=len(data), content_type=content_type)

    def put_if_absent(self, key: str, stream: BinaryIO, *, content_type: str) -> bool:
        if key in self._objects:
            return False
        data = stream.read()
        self._objects[key] = (data, content_type)
        return True

    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        self._objects[key] = (data, content_type)

    def open_stream(self, key: str) -> Iterator[bytes]:
        entry = self._objects.get(key)
        if entry is None:
            msg = f"object store key not found: {key!r}"
            raise KeyError(msg)
        data, _ = entry
        yield data


def open_deck_store(*, memory: MemoryDeckStore | None = None) -> DeckStore:
    """Return the in-memory fake when given, else build the S3 adapter from the environment."""
    if memory is not None:
        return memory
    return S3DeckStore.from_environ()


def is_sha256_content_key(key: str) -> bool:
    return _SHA256_KEY.fullmatch(key) is not None
