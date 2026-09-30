"""Story 74.1 (steward CAP-163): a station streams bytes to object storage.

`django_pyforge.object_store` is the one contract a portal (or the station API it
serves) uses to reach CAP-97's S3 seam. The round trips here run against a REAL,
ephemeral `silo` -- never a mock -- the way `test_object_storage_client.py` does (own
port, own tmp data dir, the `platform-object-storage` pixi env's binary). A missing
env skips those tests, and a skip for a missing environment is not a pass for this
story: run `pixi install -e platform-object-storage` first.

The rows that need no server -- key refusal, unset settings, the flag OFF, the store
down, what counts as "absent" -- run everywhere, against a factory that fails the test
if anything asks it for a client, or against a small fake.

The flag is exercised through two flagd trees (on and off), written the way
`test_openfeature_file_flags.py` does, until the testing-kit fixture of
`spec-feature-flag-governance` CAP-4 lands. Each tree also carries
`pyforge.three_surfaces`, because `wait_until_ready` keys on it.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.exceptions import EndpointConnectionError
from django.core.exceptions import ImproperlyConfigured
from django_pyforge import object_store
from django_pyforge.flags import FLAG_KEY as THREE_SURFACES_KEY
from django_pyforge.flags import configure_file_provider
from openfeature import api as openfeature_api

from config import object_storage as object_storage_seam

REPO_ROOT = Path(__file__).resolve().parents[3]
_SILO_BINARY = REPO_ROOT / ".pixi" / "envs" / "platform-object-storage" / "bin" / "silo"
_FLAGS_JSON = Path(__file__).resolve().parents[1] / "config" / "flags.json"

_ACCESS_KEY = "objectstoretestaccess"
_SECRET_KEY = "objectstoretestsecret1234567890"  # noqa: S105
_HEALTH_POLL_SECONDS = 30
_HTTP_OK = 200
_HTTP_NOT_FOUND = 404
_HTTP_FORBIDDEN = 403
_HTTP_SERVER_ERROR = 500

_PREFIX = "herald/exports"
_CONTENT_TYPE = "application/vnd.test+bytes"
_A_KEY = "sha256/" + "0" * 64
_SMALL_SPOOL = 64 * 1024
_SMALL_CHUNK = 16 * 1024
_ODD_TAIL = 123  # a payload that is not a whole number of chunks
_TWO = 2

_CALLS = ("put_stream", "open_stream", "stat")


# --- infrastructure -------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _health_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1) as resp:  # noqa: S310
            return resp.status == _HTTP_OK
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


@pytest.fixture(scope="module")
def local_silo(tmp_path_factory):
    """Start a real, ephemeral silo server once per module; yield its access."""
    if not _SILO_BINARY.is_file():
        pytest.skip(
            "platform-object-storage pixi env not installed -- run "
            "`pixi install -e platform-object-storage` to exercise the object-store "
            "round trips (Story 50.1's Silo recipe); a skip is not a pass here"
        )

    api_port = _free_port()
    console_port = _free_port()
    data_dir = tmp_path_factory.mktemp("silo-data")
    env = {
        **os.environ,
        "MINIO_ROOT_USER": _ACCESS_KEY,
        "MINIO_ROOT_PASSWORD": _SECRET_KEY,
    }
    proc = subprocess.Popen(  # noqa: S603
        [
            str(_SILO_BINARY),
            "server",
            str(data_dir),
            "--address",
            f":{api_port}",
            "--console-address",
            f":{console_port}",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    endpoint = f"http://127.0.0.1:{api_port}"
    try:
        for _ in range(_HEALTH_POLL_SECONDS):
            if _health_ok(f"{endpoint}/minio/health/live"):
                break
            time.sleep(1)
        else:
            proc.terminate()
            pytest.fail("ephemeral silo server did not become healthy in time")
        yield endpoint, _ACCESS_KEY, _SECRET_KEY
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _flag_tree(*, on: bool) -> bytes:
    def flag(variant: str) -> dict[str, Any]:
        return {
            "state": "ENABLED",
            "variants": {"on": True, "off": False},
            "defaultVariant": variant,
        }

    return json.dumps(
        {
            "flags": {
                THREE_SURFACES_KEY: flag("on"),
                object_store.FLAG_KEY: flag("on" if on else "off"),
            },
        },
        indent=2,
    ).encode()


def _set_flag(tmp_path: Path, *, on: bool) -> None:
    path = tmp_path / f"flags-{'on' if on else 'off'}.json"
    path.write_bytes(_flag_tree(on=on))
    configure_file_provider(path)


@pytest.fixture(autouse=True)
def _restore_the_checked_in_flag_tree():
    """Leave the process on the tree the host configured, whatever a test swapped in."""
    yield
    configure_file_provider(_FLAGS_JSON)


def _no_client_expected():
    pytest.fail("the client factory was called: nothing should have reached the client")


@pytest.fixture
def configured(settings, monkeypatch, tmp_path):
    """Flag ON, bucket and prefix set, and a factory that fails the test if called."""
    settings.OBJECT_STORAGE_BUCKET = "unused-bucket"
    settings.OBJECT_STORAGE_PREFIX = _PREFIX
    monkeypatch.setattr(
        object_storage_seam, "object_storage_client", _no_client_expected
    )
    _set_flag(tmp_path, on=True)


class _RecordingClient:
    """Delegates every call to a real client, recording each call's name."""

    def __init__(self, real: Any, calls: list[str]) -> None:
        self._real = real
        self._calls = calls

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._real, name)

        def _call(*args: Any, **kwargs: Any) -> Any:
            self._calls.append(name)
            return target(*args, **kwargs)

        return _call


@pytest.fixture
def store(local_silo, settings, monkeypatch, tmp_path):
    """Flag ON, a fresh bucket in a real silo, CAP-97's factory behind a recorder."""
    endpoint, access_key, secret_key = local_silo
    settings.OBJECT_STORAGE_ENDPOINT_URL = endpoint
    settings.OBJECT_STORAGE_ACCESS_KEY = access_key
    settings.OBJECT_STORAGE_SECRET_KEY = secret_key
    settings.OBJECT_STORAGE_BUCKET = f"seam-{uuid.uuid4().hex[:12]}"
    settings.OBJECT_STORAGE_PREFIX = _PREFIX

    real = object_storage_seam.object_storage_client()
    real.create_bucket(Bucket=settings.OBJECT_STORAGE_BUCKET)
    calls: list[str] = []
    monkeypatch.setattr(
        object_storage_seam,
        "object_storage_client",
        lambda: _RecordingClient(real, calls),
    )
    _set_flag(tmp_path, on=True)
    return SimpleNamespace(
        bucket=settings.OBJECT_STORAGE_BUCKET, prefix=_PREFIX, raw=real, calls=calls
    )


class _ChunkCountingStream(io.BytesIO):
    """A caller's stream that records the size of every read asked of it."""

    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.read_sizes: list[int | None] = []

    def read(self, size: int | None = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)


def _call(name: str, stream: io.BytesIO | None = None) -> Any:
    if name == "put_stream":
        return object_store.put_stream(
            stream or io.BytesIO(b"x"), content_type=_CONTENT_TYPE
        )
    if name == "open_stream":
        return object_store.open_stream(_A_KEY)
    return object_store.stat(_A_KEY)


def _stored_bytes(store: SimpleNamespace, key: str) -> tuple[bytes, str]:
    obj = store.raw.get_object(Bucket=store.bucket, Key=f"{store.prefix}/{key}")
    return obj["Body"].read(), obj["ContentType"]


# --- the round trip, against a real silo ----------------------------------------


@pytest.mark.parametrize(
    ("spool", "chunk"),
    [(_SMALL_SPOOL, _SMALL_CHUNK), (None, None)],
    ids=["small-bounds", "shipped-bounds"],
)
def test_large_put_streams_hashes_and_lands_at_the_prefixed_sha256_key(
    store, monkeypatch, spool, chunk
):
    """A stream past the spool threshold lands under its sha256, never in one buffer."""
    if spool is not None:
        monkeypatch.setattr(object_store, "SPOOL_MAX_BYTES", spool)
        monkeypatch.setattr(object_store, "CHUNK_BYTES", chunk)
    payload = os.urandom(
        object_store.SPOOL_MAX_BYTES + _TWO * object_store.CHUNK_BYTES + _ODD_TAIL
    )
    stream = _ChunkCountingStream(payload)

    rollovers = []

    class _SpySpool(tempfile.SpooledTemporaryFile):
        def rollover(self):
            rollovers.append(self.tell())
            super().rollover()

    monkeypatch.setattr(
        object_store, "tempfile", SimpleNamespace(SpooledTemporaryFile=_SpySpool)
    )

    stored = object_store.put_stream(stream, content_type=_CONTENT_TYPE)

    # Computed here, independently of the module under test.
    expected = hashlib.sha256(payload).hexdigest()
    assert stored == object_store.StoredObject(
        key=f"sha256/{expected}",
        sha256=expected,
        size=len(payload),
        content_type=_CONTENT_TYPE,
    )
    body, content_type = _stored_bytes(store, stored.key)
    assert body == payload
    assert content_type == _CONTENT_TYPE
    assert store.calls.count("upload_fileobj") == 1

    # Bounded reads: every read is a positive fixed chunk (never read() / read(-1)), the
    # payload took several, and it spilled to disk rather than sitting in one buffer.
    chunk_bytes = object_store.CHUNK_BYTES
    assert all(size == chunk_bytes for size in stream.read_sizes), stream.read_sizes
    assert (
        len(stream.read_sizes) == math.ceil(len(payload) / chunk_bytes) + 1
    )  # + the empty read at EOF
    assert len(rollovers) == 1


def test_an_empty_stream_stores_the_empty_object(store):
    stored = object_store.put_stream(io.BytesIO(b""), content_type=_CONTENT_TYPE)

    assert stored.sha256 == hashlib.sha256(b"").hexdigest()
    assert stored.size == 0
    assert _stored_bytes(store, stored.key) == (b"", _CONTENT_TYPE)


def test_the_same_bytes_put_twice_land_once(store):
    payload = os.urandom(_SMALL_SPOOL + _ODD_TAIL)

    first = object_store.put_stream(io.BytesIO(payload), content_type=_CONTENT_TYPE)
    store.calls.clear()
    second = object_store.put_stream(io.BytesIO(payload), content_type=_CONTENT_TYPE)

    assert second == first
    assert store.calls == ["head_object"]  # looked, found it, uploaded nothing


def test_open_stream_yields_the_bytes_in_chunks_and_stat_reports_them(
    store, monkeypatch
):
    monkeypatch.setattr(object_store, "CHUNK_BYTES", _SMALL_CHUNK)
    payload = os.urandom(_TWO * _SMALL_CHUNK + _ODD_TAIL)
    stored = object_store.put_stream(io.BytesIO(payload), content_type=_CONTENT_TYPE)

    chunks = list(object_store.open_stream(stored.key))

    assert len(chunks) > 1
    assert all(len(part) <= _SMALL_CHUNK for part in chunks)
    assert b"".join(chunks) == payload
    assert object_store.stat(stored.key) == stored


def test_a_missing_key_raises_the_clients_error_at_the_call_not_on_iteration(store):
    for name in ("open_stream", "stat"):
        with pytest.raises(ClientError) as excinfo:
            _call(name)
        assert (
            excinfo.value.response["ResponseMetadata"]["HTTPStatusCode"]
            == _HTTP_NOT_FOUND
        ), name
    assert store.calls == ["get_object", "head_object"]


# --- refusals before the client -------------------------------------------------------


@pytest.mark.parametrize("name", ["open_stream", "stat"])
@pytest.mark.parametrize(
    "key",
    [
        "SHA256/" + "a" * 64,
        "sha256/" + "A" * 64,
        "sha256/" + "a" * 63,
        "sha256/" + "a" * 65,
        "sha256/" + "a" * 64 + "\n",
        "../sha256/" + "a" * 64,
        "sha256/../" + "a" * 64,
        "/sha256/" + "a" * 64,
        "other/" + "a" * 64,
        "a" * 64,
        "",
        None,
    ],
)
def test_a_malformed_key_is_refused_before_any_client_call(configured, name, key):
    with pytest.raises(ValueError, match="not an object-store key"):
        getattr(object_store, name)(
            key
        )  # the `configured` factory fails the test if it is asked for a client


@pytest.mark.parametrize("name", _CALLS)
@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("OBJECT_STORAGE_BUCKET", None),
        ("OBJECT_STORAGE_BUCKET", ""),
        ("OBJECT_STORAGE_PREFIX", None),
        ("OBJECT_STORAGE_PREFIX", ""),
        ("OBJECT_STORAGE_PREFIX", "/"),
    ],
)
def test_an_unset_bucket_or_prefix_raises_naming_it_before_the_client_or_the_stream(
    configured, settings, name, setting, value
):
    setattr(settings, setting, value)
    stream = _ChunkCountingStream(b"payload")

    with pytest.raises(ImproperlyConfigured, match=setting):
        _call(name, stream)

    assert (
        stream.read_sizes == []
    )  # a misconfigured host refuses before consuming the payload


@pytest.mark.parametrize("name", _CALLS)
def test_flag_off_refuses_every_call_before_the_client(configured, tmp_path, name):
    _set_flag(tmp_path, on=False)
    stream = _ChunkCountingStream(b"payload")

    with pytest.raises(object_store.ObjectStoreDisabled, match=object_store.FLAG_KEY):
        _call(name, stream)

    assert stream.read_sizes == []


@pytest.mark.parametrize("name", _CALLS)
def test_no_flag_provider_reads_off(configured, name):
    """The flag is read with default=False, so a host with no provider fails closed."""
    openfeature_api.clear_providers()

    with pytest.raises(object_store.ObjectStoreDisabled):
        _call(name)


@pytest.mark.parametrize("name", _CALLS)
def test_the_checked_in_tree_ships_the_flag_off(configured, name):
    flag = json.loads(_FLAGS_JSON.read_text(encoding="utf-8"))["flags"][
        object_store.FLAG_KEY
    ]
    assert flag == {
        "state": "ENABLED",
        "variants": {"on": True, "off": False},
        "defaultVariant": "off",
    }
    configure_file_provider(_FLAGS_JSON)

    with pytest.raises(object_store.ObjectStoreDisabled):
        _call(name)


# --- the store down, and what counts as absent ----------------------------------


@pytest.mark.parametrize("name", _CALLS)
def test_an_unreachable_store_raises_the_clients_own_error(
    configured, monkeypatch, name
):
    dead_endpoint = f"http://127.0.0.1:{_free_port()}"  # nothing listens here

    def _dead_client():
        return boto3.client(
            "s3",
            endpoint_url=dead_endpoint,
            aws_access_key_id=_ACCESS_KEY,
            aws_secret_access_key=_SECRET_KEY,
            region_name="us-east-1",
            config=Config(retries={"max_attempts": 1}, connect_timeout=2),
        )

    monkeypatch.setattr(object_storage_seam, "object_storage_client", _dead_client)

    with pytest.raises(EndpointConnectionError):
        _call(name)


class _FakeClientError(Exception):
    """A client error as duck-typed by the seam: only `.response` matters."""

    def __init__(self, response: dict[str, Any]) -> None:
        super().__init__(str(response))
        self.response = response


class _FakeBody:
    def __init__(self, parts: list[bytes]) -> None:
        self._parts = parts
        self.closed = False
        self.close_calls = 0
        self.chunk_sizes: list[int] = []

    def iter_chunks(self, chunk_size: int):
        # Not a generator: the call itself is recorded, so a caller that asks for the
        # chunks before its first read shows up in `chunk_sizes`.
        self.chunk_sizes.append(chunk_size)
        return iter(self._parts)

    def close(self) -> None:
        self.closed = True
        self.close_calls += 1


class _FakeClient:
    def __init__(self, *, head: Any = None, body: _FakeBody | None = None) -> None:
        self._head = head
        self._body = body
        self.calls: list[str] = []
        self.uploaded: dict[str, Any] = {}

    def head_object(self, **_kwargs: Any) -> dict[str, Any]:
        self.calls.append("head_object")
        if isinstance(self._head, Exception):
            raise self._head
        return self._head

    def upload_fileobj(
        self, fileobj: Any, bucket: str, key: str, **kwargs: Any
    ) -> None:
        self.calls.append("upload_fileobj")
        self.uploaded = {
            "body": fileobj.read(),
            "bucket": bucket,
            "key": key,
            "extra": kwargs["ExtraArgs"],
        }

    def get_object(self, **_kwargs: Any) -> dict[str, Any]:
        self.calls.append("get_object")
        return {"Body": self._body}


class _MemoryClient(_FakeClient):
    """A fake that remembers its uploads, so a repeat put finds the first."""

    def __init__(self) -> None:
        super().__init__()
        self.objects: dict[str, dict[str, Any]] = {}

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("head_object")
        stored = self.objects.get(kwargs["Key"])
        if stored is None:
            raise _FakeClientError({"Error": {"Code": "404"}})
        return {
            "ContentLength": len(stored["body"]),
            "ContentType": stored["content_type"],
        }

    def upload_fileobj(
        self, fileobj: Any, bucket: str, key: str, **kwargs: Any
    ) -> None:
        self.calls.append("upload_fileobj")
        self.objects[key] = {
            "body": fileobj.read(),
            "content_type": kwargs["ExtraArgs"]["ContentType"],
        }


@pytest.mark.parametrize(
    "response",
    [
        {"Error": {"Code": "404"}},
        {"Error": {"Code": "NoSuchKey"}},
        {"Error": {"Code": "NotFound"}},
        {
            "Error": {"Code": "Other"},
            "ResponseMetadata": {"HTTPStatusCode": _HTTP_NOT_FOUND},
        },
    ],
)
def test_a_404_shaped_head_error_means_absent_and_the_bytes_are_uploaded(
    configured, monkeypatch, response
):
    client = _FakeClient(head=_FakeClientError(response))
    monkeypatch.setattr(object_storage_seam, "object_storage_client", lambda: client)

    stored = object_store.put_stream(io.BytesIO(b"payload"), content_type=_CONTENT_TYPE)

    assert client.calls == ["head_object", "upload_fileobj"]
    assert client.uploaded == {
        "body": b"payload",
        "bucket": "unused-bucket",
        "key": f"{_PREFIX}/{stored.key}",
        "extra": {"ContentType": _CONTENT_TYPE},
    }


@pytest.mark.parametrize(
    "error",
    [
        _FakeClientError(
            {
                "Error": {"Code": "AccessDenied"},
                "ResponseMetadata": {"HTTPStatusCode": _HTTP_FORBIDDEN},
            }
        ),
        _FakeClientError(
            {
                "Error": {"Code": "InternalError"},
                "ResponseMetadata": {"HTTPStatusCode": _HTTP_SERVER_ERROR},
            }
        ),
        _FakeClientError({}),
        ConnectionError("store down"),
    ],
    ids=["403", "500", "no-code", "no-response"],
)
def test_any_other_head_error_propagates_and_nothing_is_uploaded(
    configured, monkeypatch, error
):
    client = _FakeClient(head=error)
    monkeypatch.setattr(object_storage_seam, "object_storage_client", lambda: client)

    with pytest.raises(type(error)) as excinfo:
        object_store.put_stream(io.BytesIO(b"payload"), content_type=_CONTENT_TYPE)

    assert excinfo.value is error
    assert client.calls == ["head_object"]


def test_a_multi_chunk_put_hashes_reads_in_fixed_chunks_and_keys_by_the_hash(
    configured, monkeypatch
):
    """The sha256, the key and the bounded reads, with no silo to lean on."""
    monkeypatch.setattr(object_store, "CHUNK_BYTES", _SMALL_CHUNK)
    payload = os.urandom(_TWO * _SMALL_CHUNK + _ODD_TAIL)
    stream = _ChunkCountingStream(payload)
    client = _FakeClient(head=_FakeClientError({"Error": {"Code": "404"}}))
    monkeypatch.setattr(object_storage_seam, "object_storage_client", lambda: client)

    stored = object_store.put_stream(stream, content_type=_CONTENT_TYPE)

    expected = hashlib.sha256(payload).hexdigest()  # independent of the module
    assert stored.sha256 == expected
    assert stored.key == f"sha256/{expected}"
    assert stored.size == len(payload)
    assert client.uploaded["key"].endswith(f"/{expected}")
    assert client.uploaded["body"] == payload
    assert len(stream.read_sizes) > _TWO
    assert all(size == _SMALL_CHUNK for size in stream.read_sizes), stream.read_sizes


def test_a_put_of_an_object_already_stored_uploads_nothing_and_returns_it(
    configured, monkeypatch
):
    payload = b"already in the store"
    expected = hashlib.sha256(payload).hexdigest()
    client = _FakeClient(
        head={"ContentLength": len(payload), "ContentType": _CONTENT_TYPE}
    )
    monkeypatch.setattr(object_storage_seam, "object_storage_client", lambda: client)

    stored = object_store.put_stream(io.BytesIO(payload), content_type="text/other")

    assert client.calls == ["head_object"]
    assert stored == object_store.StoredObject(
        key=f"sha256/{expected}",
        sha256=expected,
        size=len(payload),
        content_type=_CONTENT_TYPE,
    )


def test_a_repeat_put_under_another_content_type_returns_the_stored_one(
    configured, monkeypatch
):
    client = _MemoryClient()
    monkeypatch.setattr(object_storage_seam, "object_storage_client", lambda: client)

    first = object_store.put_stream(
        io.BytesIO(b"same bytes"), content_type="text/first"
    )
    second = object_store.put_stream(
        io.BytesIO(b"same bytes"), content_type="text/second"
    )

    assert first.content_type == "text/first"
    assert second == first
    assert client.calls == ["head_object", "upload_fileobj", "head_object"]


def test_open_stream_closes_the_body_when_exhausted_or_closed(configured, monkeypatch):
    def _open(body):
        monkeypatch.setattr(
            object_storage_seam, "object_storage_client", lambda: _FakeClient(body=body)
        )
        return object_store.open_stream(_A_KEY)

    exhausted = _FakeBody([b"ab", b"cd"])
    assert b"".join(_open(exhausted)) == b"abcd"
    assert exhausted.closed
    assert exhausted.close_calls == 1
    assert exhausted.chunk_sizes == [object_store.CHUNK_BYTES]

    abandoned = _FakeBody([b"ab", b"cd"])
    stream = _open(abandoned)
    assert next(stream) == b"ab"
    assert not abandoned.closed
    stream.close()
    assert abandoned.closed


def test_closing_the_iterator_before_the_first_read_closes_the_body(
    configured, monkeypatch
):
    """An unstarted generator would never run its `finally`: HEAD, a client hang-up."""
    body = _FakeBody([b"ab", b"cd"])
    monkeypatch.setattr(
        object_storage_seam, "object_storage_client", lambda: _FakeClient(body=body)
    )

    stream = object_store.open_stream(_A_KEY)
    assert not body.closed
    stream.close()

    assert body.closed
    assert body.chunk_sizes == []  # never started reading
    stream.close()  # idempotent: the body is closed once
    assert body.close_calls == 1
    assert list(stream) == []


# --- the factory setting --------------------------------------------------------------


def _fake_factory():
    return _FakeClient(head={"ContentLength": _ODD_TAIL, "ContentType": _CONTENT_TYPE})


def test_the_client_factory_is_the_one_the_setting_names(configured, settings):
    settings.OBJECT_STORAGE_CLIENT_FACTORY = f"{__name__}.{_fake_factory.__name__}"

    assert object_store.stat(_A_KEY) == object_store.StoredObject(
        key=_A_KEY,
        sha256="0" * 64,
        size=_ODD_TAIL,
        content_type=_CONTENT_TYPE,
    )


def test_a_client_factory_that_cannot_be_imported_raises_naming_the_setting(
    configured, settings
):
    settings.OBJECT_STORAGE_CLIENT_FACTORY = "config.no_such_module.factory"

    with pytest.raises(ImproperlyConfigured, match="OBJECT_STORAGE_CLIENT_FACTORY"):
        object_store.stat(_A_KEY)


def test_the_default_client_factory_is_cap_97s(settings):
    assert settings.OBJECT_STORAGE_CLIENT_FACTORY == object_store.DEFAULT_CLIENT_FACTORY
    assert (
        object_store.DEFAULT_CLIENT_FACTORY
        == "config.object_storage.object_storage_client"
    )
