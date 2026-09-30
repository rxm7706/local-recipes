"""Streaming, sha256-addressed object storage for station portals (Story 74.1; steward CAP-163).

`config.object_storage.object_storage_client()` (Story 50.3, CAP-97) is the one S3 client
the platform resolves. This module is the contract a `django-<station>` portal -- or the
station API it serves under `/stations/<name>/api/v1/` -- uses to reach it:

- `put_stream(fileobj, content_type=...)` hashes the caller's stream while spooling it to
  a bounded temporary file, then uploads it under `<prefix>/sha256/<hex>` unless that key
  is already in the store (content-addressed: identical bytes land once).
- `open_stream(key)` yields an object back in chunks, ready for a
  `StreamingHttpResponse`; `stat(key)` returns its size and content type.

Boundaries this module holds, each pinned by a test:

- It imports nothing from the host's `config` package and no boto3 / botocore. The client
  factory is a dotted path in the `OBJECT_STORAGE_CLIENT_FACTORY` setting, resolved with
  `import_string` -- the chrome never builds a second S3 client (steward AD-1).
- Nothing loads a whole object into memory or a model field; nothing is a presigned URL.
  A portal streams every byte behind OIDC and the station role, so the store needs no
  endpoint a browser can reach.
- The store is consumed, never self-hosted (pap:AD-1's 2026-09-10 dated exception).
  Credentials stay the three secret references the chart mounts (canopy:AD-19).

A key is prefix-relative -- `sha256/<64 lowercase hex>`; the object sits at
`<OBJECT_STORAGE_PREFIX>/<key>` -- so a consumer stores the relative key and a
per-environment prefix never invalidates its rows.

Order of checks in every call: the flag (`ObjectStoreDisabled`), the key's shape
(`ValueError`, pure), the settings (`ImproperlyConfigured` naming the setting), then the
factory's client. `put_stream` resolves settings and the client before it reads the
stream, so a misconfigured host refuses before consuming the payload. A store error (an
unreachable endpoint, a missing key on `open_stream` / `stat`) propagates as the client
raised it.
"""

from __future__ import annotations

import hashlib
import re
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from typing import BinaryIO
from typing import Final

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from django_pyforge.flags import evaluate_boolean

__all__ = [
    "BUCKET_SETTING",
    "CHUNK_BYTES",
    "CLIENT_FACTORY_SETTING",
    "DEFAULT_CLIENT_FACTORY",
    "FLAG_KEY",
    "PREFIX_SETTING",
    "SPOOL_MAX_BYTES",
    "ObjectStoreDisabled",
    "StoredObject",
    "open_stream",
    "put_stream",
    "stat",
]

#: The flag this contract ships behind (`spec-feature-flag-governance` CAP-1).
FLAG_KEY: Final[str] = "pyforge.steward.object_store_consumer"

#: Django settings this module reads (config/settings/base.py). Named here so a
#: missing-config error can point at the exact setting.
BUCKET_SETTING: Final[str] = "OBJECT_STORAGE_BUCKET"
PREFIX_SETTING: Final[str] = "OBJECT_STORAGE_PREFIX"
CLIENT_FACTORY_SETTING: Final[str] = "OBJECT_STORAGE_CLIENT_FACTORY"

#: CAP-97's factory: the one client the platform seam resolves.
DEFAULT_CLIENT_FACTORY: Final[str] = "config.object_storage.object_storage_client"

#: A payload up to this size is spooled in memory; above it the spool rolls over to
#: disk. Read at call time, so a test can shrink it.
SPOOL_MAX_BYTES: int = 8 * 1024 * 1024
#: Every read from a caller's stream, and every chunk `open_stream` yields, is this size.
CHUNK_BYTES: int = 1024 * 1024

_KEY_ROOT: Final[str] = "sha256"
_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(rf"{_KEY_ROOT}/[0-9a-f]{{64}}")
_NOT_FOUND_CODES: Final[frozenset[str]] = frozenset({"404", "NoSuchKey", "NotFound"})
_HTTP_NOT_FOUND: Final[int] = 404
_DEFAULT_CONTENT_TYPE: Final[str] = "application/octet-stream"


class ObjectStoreDisabled(RuntimeError):  # noqa: N818 -- the name the story and its consumers bind to
    """The flag `pyforge.steward.object_store_consumer` is OFF: nothing reaches the client."""


@dataclass(frozen=True, slots=True)
class StoredObject:
    """One stored object: the prefix-relative key, its sha256, size and content type."""

    key: str
    sha256: str
    size: int
    content_type: str


def _require_enabled() -> None:
    # `default=False`: a host with no flag provider configured reads OFF, so the seam fails closed.
    if not evaluate_boolean(FLAG_KEY, default=False):
        msg = (
            f"object storage is off: the flag {FLAG_KEY} is not enabled, so nothing reaches the "
            "store. A consumer keeps its exports in git only."
        )
        raise ObjectStoreDisabled(msg)


def _check_key(key: object) -> str:
    """Return *key* when it is exactly `sha256/<64 lowercase hex>`; refuse otherwise, pure."""
    if not isinstance(key, str) or _KEY_PATTERN.fullmatch(key) is None:
        msg = f"not an object-store key (want '{_KEY_ROOT}/<64 lowercase hex>'): {key!r}"
        raise ValueError(msg)
    return key


def _setting(name: str) -> str:
    value = getattr(settings, name, None)
    if not isinstance(value, str) or not value.strip("/ "):
        msg = (
            f"{name} is not configured. Object-storage consumption needs a bucket and a prefix "
            "as configuration -- never a default (see config/settings/base.py; the chart names "
            "them per environment)."
        )
        raise ImproperlyConfigured(msg)
    return value


def _location() -> tuple[str, str]:
    """The configured (bucket, prefix); the prefix carries no leading or trailing slash."""
    return _setting(BUCKET_SETTING), _setting(PREFIX_SETTING).strip("/")


def _client() -> Any:
    """The factory-built client. The factory is named by a setting, never imported here."""
    factory_path = getattr(settings, CLIENT_FACTORY_SETTING, None) or DEFAULT_CLIENT_FACTORY
    try:
        factory = import_string(factory_path)
    except ImportError as exc:
        msg = f"{CLIENT_FACTORY_SETTING} names {factory_path!r}, which cannot be imported: {exc}"
        raise ImproperlyConfigured(msg) from exc
    return factory()


def _is_not_found(exc: Exception) -> bool:
    """A 404-shaped client error, recognised by duck-typing its `.response` (no botocore import)."""
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return False
    code = (response.get("Error") or {}).get("Code")
    status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    return str(code) in _NOT_FOUND_CODES or status == _HTTP_NOT_FOUND


def _head(client: Any, bucket: str, object_key: str) -> dict[str, Any] | None:
    """`head_object`, or None when the key is absent. Any other error propagates unchanged."""
    try:
        return client.head_object(Bucket=bucket, Key=object_key)
    except Exception as exc:
        if _is_not_found(exc):
            return None
        raise


def put_stream(fileobj: BinaryIO, *, content_type: str) -> StoredObject:
    """Store the bytes of *fileobj* under their sha256 and return where they landed.

    The stream is read in `CHUNK_BYTES` reads, hashed as it is read and spooled to a
    `SpooledTemporaryFile` (`SPOOL_MAX_BYTES` in memory, disk above), so the payload is
    never held in one buffer. The spool is then uploaded with the client's managed
    transfer -- unless `head_object` finds the key already there, in which case nothing
    is uploaded and the stored object's size and content type come back.

    Raises:
        ObjectStoreDisabled: the flag is OFF; nothing reached the client.
        ImproperlyConfigured: the bucket, the prefix or the client factory is unusable.
    """
    _require_enabled()
    bucket, prefix = _location()
    client = _client()

    digest = hashlib.sha256()
    size = 0
    with tempfile.SpooledTemporaryFile(max_size=SPOOL_MAX_BYTES) as spool:
        while chunk := fileobj.read(CHUNK_BYTES):
            digest.update(chunk)
            spool.write(chunk)
            size += len(chunk)

        hex_digest = digest.hexdigest()
        key = f"{_KEY_ROOT}/{hex_digest}"
        object_key = f"{prefix}/{key}"

        existing = _head(client, bucket, object_key)
        if existing is not None:
            return StoredObject(
                key=key,
                sha256=hex_digest,
                size=existing["ContentLength"],
                content_type=existing.get("ContentType") or content_type,
            )

        spool.seek(0)
        client.upload_fileobj(spool, bucket, object_key, ExtraArgs={"ContentType": content_type})
    return StoredObject(key=key, sha256=hex_digest, size=size, content_type=content_type)


def open_stream(key: str) -> Iterator[bytes]:
    """Yield the object at *key* in `CHUNK_BYTES` chunks, for a `StreamingHttpResponse`.

    `get_object` is called eagerly, so a missing key raises here -- before a view builds
    its response -- not on first iteration. The returned generator closes the body when it
    is exhausted or closed.

    Raises:
        ObjectStoreDisabled: the flag is OFF; nothing reached the client.
        ValueError: *key* is not `sha256/<64 lowercase hex>`; nothing reached the client.
        ImproperlyConfigured: the bucket, the prefix or the client factory is unusable.
    """
    _require_enabled()
    bucket, prefix = _location()
    body = _client().get_object(Bucket=bucket, Key=f"{prefix}/{key}")["Body"]
    return _chunks(body)


def _chunks(body: Any) -> Iterator[bytes]:
    try:
        yield from body.iter_chunks(CHUNK_BYTES)
    finally:
        body.close()


def stat(key: str) -> StoredObject:
    """Return the size and content type of the object at *key*, from `head_object`.

    Raises:
        ObjectStoreDisabled: the flag is OFF; nothing reached the client.
        ValueError: *key* is not `sha256/<64 lowercase hex>`; nothing reached the client.
        ImproperlyConfigured: the bucket, the prefix or the client factory is unusable.
    """
    _require_enabled()
    _check_key(key)
    bucket, prefix = _location()
    head = _client().head_object(Bucket=bucket, Key=f"{prefix}/{key}")
    return StoredObject(
        key=key,
        sha256=key.removeprefix(f"{_KEY_ROOT}/"),
        size=head["ContentLength"],
        content_type=head.get("ContentType") or _DEFAULT_CONTENT_TYPE,
    )
