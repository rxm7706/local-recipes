"""``webhook.py``'s HMAC-verified CI handlers (Story 13.4, closing Epic
13's LB-2): ``verify_signature``, ``resolve_webhook_secret``,
``handle_on_ship``/``handle_on_pr_close`` (the sync core), the retry/
backoff helper, the structured-alert log, and ``create_app``'s raw ASGI3
callable.

Every case uses an explicit ``tmp_path``-derived ``repo_root`` --
``webhook.py`` never assumes a cwd, mirroring ``progress.py``/
``claims.py``'s own convention (and their test suites' shape). No test
opens a real socket: the ASGI cases hand-construct a ``scope``/``receive``/
``send`` triple instead of a real server, which needs none and so never
trips the package's autouse ``deny_network`` fixture."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from pyforge.herald import claims, progress, webhook
from pyforge.herald.errors import HeraldError

# --- ASGI test helpers --------------------------------------------------------


def _timestamp() -> str:
    """A fresh ``X-Hub-Timestamp`` value -- real wall-clock seconds, well
    inside ``webhook.MAX_TIMESTAMP_SKEW_SECONDS`` for the whole (fast,
    synchronous) duration of one test."""
    return str(int(time.time()))


def _sign(secret: bytes, timestamp: str, body: bytes) -> str:
    """The signature over ``timestamp + "." + body`` -- the signed content
    ``webhook.verify_signature`` now expects (Story 13.6, closing
    DW-FU-13-4)."""
    return "sha256=" + hmac.new(secret, timestamp.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()


def _signed_headers(secret: bytes, body: bytes, *, timestamp: str | None = None) -> list[tuple[bytes, bytes]]:
    """The ``X-Hub-Signature-256``/``X-Hub-Timestamp`` header pair a real
    producer would send -- the one helper every ASGI-level signed-request
    test below builds its ``scope["headers"]`` from."""
    ts = timestamp if timestamp is not None else _timestamp()
    return [
        (b"x-hub-signature-256", _sign(secret, ts, body).encode()),
        (b"x-hub-timestamp", ts.encode()),
    ]


def _scope(path: str, *, method: str = "POST", headers: list[tuple[bytes, bytes]] | None = None) -> dict[str, Any]:
    return {"type": "http", "method": method, "path": path, "headers": headers or []}


def _receive_once(body: bytes):
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


async def _boom_receive() -> dict[str, Any]:
    raise AssertionError("the body must not be read for this request")


class _Recorder:
    """A recording ASGI ``send`` -- callable, per the ASGI3 protocol."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def __call__(self, message: dict[str, Any]) -> None:
        self.messages.append(message)

    @property
    def status(self) -> int:
        return next(m["status"] for m in self.messages if m["type"] == "http.response.start")

    @property
    def json_body(self) -> Any:
        body = b"".join(m["body"] for m in self.messages if m["type"] == "http.response.body")
        return json.loads(body)


# --- verify_signature ---------------------------------------------------------


def test_verify_signature_accepts_a_valid_signature():
    secret = b"shared-secret"
    body = b'{"station": "warden"}'
    ts = _timestamp()
    assert webhook.verify_signature(secret, body, _sign(secret, ts, body), ts) is True


def test_verify_signature_rejects_a_mismatched_signature():
    secret = b"shared-secret"
    body = b'{"station": "warden"}'
    assert webhook.verify_signature(secret, body, "sha256=" + "0" * 64, _timestamp()) is False


def test_verify_signature_rejects_a_missing_header():
    assert webhook.verify_signature(b"secret", b"body", None, _timestamp()) is False


def test_verify_signature_rejects_a_header_with_no_sha256_prefix():
    assert webhook.verify_signature(b"secret", b"body", "deadbeef", _timestamp()) is False


# --- resolve_webhook_secret -----------------------------------------------


def test_resolve_webhook_secret_reads_the_injected_env():
    assert webhook.resolve_webhook_secret({"HERALD_WEBHOOK_SECRET": "shh"}) == b"shh"


def test_resolve_webhook_secret_raises_when_unset():
    with pytest.raises(HeraldError, match="HERALD_WEBHOOK_SECRET"):
        webhook.resolve_webhook_secret({})


def test_resolve_webhook_secret_raises_when_empty():
    with pytest.raises(HeraldError, match="HERALD_WEBHOOK_SECRET"):
        webhook.resolve_webhook_secret({"HERALD_WEBHOOK_SECRET": ""})


# --- the generic retry/backoff helper ------------------------------------


def test_retry_with_backoff_stops_at_the_first_success():
    calls = 0

    def succeeds_second_time() -> str:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise HeraldError("nope")
        return "ok"

    sleeps: list[float] = []
    assert webhook._retry_with_backoff(succeeds_second_time, sleep=sleeps.append) == "ok"
    assert calls == 2
    assert sleeps == [1.0]


def test_retry_with_backoff_raises_the_last_error_after_the_budget_is_exhausted():
    def always_fails() -> None:
        raise HeraldError("nope")

    sleeps: list[float] = []
    with pytest.raises(HeraldError, match="nope"):
        webhook._retry_with_backoff(always_fails, sleep=sleeps.append)
    # 3 attempts, sleeping between each pair -- never after the last one.
    assert sleeps == [1.0, 2.0]


def test_retry_with_backoff_never_retries_a_non_herald_error():
    def raises_type_error() -> None:
        raise TypeError("not a HeraldError")

    with pytest.raises(TypeError):
        webhook._retry_with_backoff(raises_type_error, sleep=lambda _: None)


# --- handle_on_ship -------------------------------------------------------


def test_handle_on_ship_minimal_payload_uses_the_same_defaults_as_the_cli(
    tmp_path: Path,
):
    result = webhook.handle_on_ship(tmp_path, {"station": "warden"})
    assert result.status == 201
    records = progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)
    assert len(records) == 1
    record = records[0]
    assert record.station == "warden"
    assert record.date == datetime.now(UTC).date().isoformat()
    assert record.shipped_capabilities == []
    assert record.compute_hours == 0.0
    assert record.token_spend == 0
    assert record.wall_clock_hours == 0.0
    assert record.unblock_narrative == ""


def test_handle_on_ship_full_payload_stores_every_field(tmp_path: Path):
    payload = {
        "station": "atlas",
        "shipped_capabilities": ["a", "b"],
        "compute_hours": 3.5,
        "token_spend": 1000,
        "wall_clock_hours": 2.0,
        "unblock_narrative": "none",
    }
    result = webhook.handle_on_ship(tmp_path, payload)
    assert result.status == 201
    record = progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)[0]
    assert record.shipped_capabilities == ["a", "b"]
    assert record.compute_hours == 3.5
    assert record.token_spend == 1000
    assert record.wall_clock_hours == 2.0
    assert record.unblock_narrative == "none"


def test_handle_on_ship_matches_what_the_cli_update_would_create(tmp_path: Path):
    """AC: "matching what `herald progress <station> --update` would
    create for the same inputs" -- proven by calling `progress.upsert`
    directly with the CLI's own argument shape and comparing every field
    but the generated id/timestamps."""
    payload = {"station": "warden", "compute_hours": 1.5}
    webhook.handle_on_ship(tmp_path, payload)
    via_webhook = progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)[0]

    cli_record = progress.upsert(
        tmp_path / "cli" / progress.DEFAULT_PROGRESS_PATH,
        station="warden",
        date=datetime.now(UTC).date().isoformat(),
        shipped_capabilities=[],
        compute_hours=1.5,
        token_spend=0,
        wall_clock_hours=0.0,
        unblock_narrative="",
    )
    assert via_webhook.station == cli_record.station
    assert via_webhook.date == cli_record.date
    assert via_webhook.shipped_capabilities == cli_record.shipped_capabilities
    assert via_webhook.compute_hours == cli_record.compute_hours
    assert via_webhook.token_spend == cli_record.token_spend
    assert via_webhook.wall_clock_hours == cli_record.wall_clock_hours
    assert via_webhook.unblock_narrative == cli_record.unblock_narrative


@pytest.mark.parametrize(
    ("payload", "fragment"),
    [
        ({}, "station"),
        ({"station": 5}, "station"),
        ("not-a-dict", "JSON object"),
        ({"station": "warden", "shipped_capabilities": "nope"}, "shipped_capabilities"),
        ({"station": "warden", "shipped_capabilities": [1, 2]}, "shipped_capabilities"),
        ({"station": "warden", "compute_hours": "nope"}, "compute_hours"),
        ({"station": "warden", "compute_hours": float("nan")}, "compute_hours"),
        ({"station": "warden", "token_spend": 1.5}, "token_spend"),
        ({"station": "warden", "wall_clock_hours": True}, "wall_clock_hours"),
        ({"station": "warden", "wall_clock_hours": float("inf")}, "wall_clock_hours"),
        ({"station": "warden", "unblock_narrative": 5}, "unblock_narrative"),
    ],
)
def test_handle_on_ship_malformed_payload_is_400_before_any_storage_call(
    tmp_path: Path, payload: object, fragment: str
):
    result = webhook.handle_on_ship(tmp_path, payload)
    assert result.status == 400
    assert fragment in result.body["error"]
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_handle_on_ship_retries_once_then_recovers(tmp_path: Path, monkeypatch):
    real_upsert = progress.upsert
    calls = 0

    def flaky_upsert(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise HeraldError("transient")
        return real_upsert(*args, **kwargs)

    monkeypatch.setattr(progress, "upsert", flaky_upsert)
    sleeps: list[float] = []
    result = webhook.handle_on_ship(tmp_path, {"station": "warden"}, sleep=sleeps.append)
    assert result.status == 201
    assert calls == 2
    assert sleeps == [1.0]
    assert len(progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)) == 1


def test_handle_on_ship_retry_exhausted_emits_one_alert_and_returns_500(tmp_path: Path, monkeypatch, caplog):
    calls = 0

    def always_fails(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise HeraldError("boom")

    monkeypatch.setattr(progress, "upsert", always_fails)
    sleeps: list[float] = []
    with caplog.at_level("ERROR", logger="pyforge.herald.webhook"):
        result = webhook.handle_on_ship(tmp_path, {"station": "warden"}, sleep=sleeps.append)
    assert result.status == 500
    assert calls == 3
    assert sleeps == [1.0, 2.0]
    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_records) == 1
    logged = json.loads(error_records[0].message)
    assert logged["event"] == "herald.webhook.retries_exhausted"
    assert logged["webhook"] == "on-ship"
    assert "boom" in logged["error"]
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


# --- handle_on_pr_close ----------------------------------------------------


def test_handle_on_pr_close_shipped_creates_a_draft_claim_matching_cli_create(
    tmp_path: Path,
):
    payload = {
        "merged": True,
        "gates_passed": True,
        "project_name": "Marshal S-1.10",
        "evidence": [{"type": "test_results", "url": "https://ci.example/run/1", "label": "tests"}],
    }
    result = webhook.handle_on_pr_close(tmp_path, payload)
    assert result.status == 201
    stored = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert len(stored) == 1
    claim = stored[0]
    assert claim.id == result.body["claim_id"]
    assert claim.project_name == "Marshal S-1.10"
    assert claim.status == "draft"
    assert len(claim.evidence) == 1
    assert claim.evidence[0].type == "test_results"
    assert claim.evidence[0].url == "https://ci.example/run/1"
    assert claim.evidence[0].label == "tests"


def test_handle_on_pr_close_with_no_evidence(tmp_path: Path):
    payload = {"merged": True, "gates_passed": True, "project_name": "Marshal S-1.10"}
    result = webhook.handle_on_pr_close(tmp_path, payload)
    assert result.status == 201
    claim = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)[0]
    assert claim.evidence == ()


@pytest.mark.parametrize(("merged", "gates_passed"), [(False, True), (True, False), (False, False)])
def test_handle_on_pr_close_not_shipped_is_a_202_no_op(tmp_path: Path, merged: bool, gates_passed: bool):
    payload = {"merged": merged, "gates_passed": gates_passed}
    result = webhook.handle_on_pr_close(tmp_path, payload)
    assert result.status == 202
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


@pytest.mark.parametrize(
    ("payload", "fragment"),
    [
        ({}, "merged"),
        ({"merged": True}, "gates_passed"),
        ({"merged": "true", "gates_passed": True}, "merged"),
        ({"merged": True, "gates_passed": 1}, "gates_passed"),
        ("not-a-dict", "JSON object"),
    ],
)
def test_handle_on_pr_close_malformed_gate_fields_is_400_before_any_storage_call(
    tmp_path: Path, payload: object, fragment: str
):
    result = webhook.handle_on_pr_close(tmp_path, payload)
    assert result.status == 400
    assert fragment in result.body["error"]
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


@pytest.mark.parametrize(
    ("extra", "fragment"),
    [
        ({}, "project_name"),
        ({"project_name": 5}, "project_name"),
        ({"project_name": ""}, "project_name"),
        ({"project_name": "   "}, "project_name"),
        ({"project_name": "x", "shipped_date": 5}, "shipped_date"),
        ({"project_name": "x", "evidence": "nope"}, "evidence"),
        ({"project_name": "x", "evidence": [{"type": "test_results"}]}, "evidence"),
        (
            {
                "project_name": "x",
                "evidence": [{"type": 5, "url": "u", "label": "l"}],
            },
            "evidence",
        ),
        (
            {
                "project_name": "x",
                "evidence": [{"type": "bogus", "url": "u", "label": "l"}],
            },
            "evidence",
        ),
    ],
)
def test_handle_on_pr_close_malformed_shipped_payload_is_400(tmp_path: Path, extra: Mapping[str, Any], fragment: str):
    payload = {"merged": True, "gates_passed": True, **extra}
    result = webhook.handle_on_pr_close(tmp_path, payload)
    assert result.status == 400
    assert fragment in result.body["error"]
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


def test_handle_on_pr_close_retries_once_then_recovers(tmp_path: Path, monkeypatch):
    real_create = claims.create
    calls = 0

    def flaky_create(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise HeraldError("transient")
        return real_create(*args, **kwargs)

    monkeypatch.setattr(claims, "create", flaky_create)
    sleeps: list[float] = []
    payload = {"merged": True, "gates_passed": True, "project_name": "x"}
    result = webhook.handle_on_pr_close(tmp_path, payload, sleep=sleeps.append)
    assert result.status == 201
    assert calls == 2
    assert sleeps == [1.0]
    assert len(claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)) == 1


def test_handle_on_pr_close_retry_exhausted_emits_one_alert_and_returns_500(tmp_path: Path, monkeypatch, caplog):
    def always_fails(*args, **kwargs):
        raise HeraldError("boom")

    monkeypatch.setattr(claims, "create", always_fails)
    sleeps: list[float] = []
    payload = {"merged": True, "gates_passed": True, "project_name": "x"}
    with caplog.at_level("ERROR", logger="pyforge.herald.webhook"):
        result = webhook.handle_on_pr_close(tmp_path, payload, sleep=sleeps.append)
    assert result.status == 500
    assert sleeps == [1.0, 2.0]
    error_records = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_records) == 1
    logged = json.loads(error_records[0].message)
    assert logged["webhook"] == "on-pr-close"
    assert "boom" in logged["error"]
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


def test_handle_on_pr_close_redelivery_is_idempotent_across_separate_http_calls(
    tmp_path: Path,
):
    """A genuine CI webhook redelivery is a SECOND, INDEPENDENT top-level
    call -- not a retry inside one call's own retry loop, which
    `test_handle_on_pr_close_retry_is_idempotent_when_the_first_attempt_actually_committed`
    already covers. The pre-existing `read_one`-before-`create` guard only
    catches that within-one-call case; a random `uuid.uuid4()` id per call
    would sail past it here and create a second, duplicate draft claim. The
    claim id must instead be derived deterministically from the payload
    (`_claim_id_for`) so two independent calls with the identical payload
    compute the SAME id and the SAME guard catches this case too."""
    payload = {
        "merged": True,
        "gates_passed": True,
        "project_name": "Marshal S-1.10",
        "shipped_date": "2026-08-13",
    }
    first = webhook.handle_on_pr_close(tmp_path, payload)
    second = webhook.handle_on_pr_close(tmp_path, payload)
    assert first.status == 201
    assert second.status == 201
    assert first.body["claim_id"] == second.body["claim_id"]
    stored = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert len(stored) == 1
    assert stored[0].id == first.body["claim_id"]


def test_handle_on_pr_close_retry_is_idempotent_when_the_first_attempt_actually_committed(tmp_path: Path, monkeypatch):
    """Design Notes: `claims.id` has no schema-level uniqueness, so a naive
    retry that generated a fresh id per attempt (or blindly re-called
    `create`) would silently create a SECOND draft claim for one CI event
    once the first attempt's write had actually landed before it raised.
    Proven here by making `create` genuinely write, then raise anyway on
    its first call -- the retry must find the already-committed row via
    the pre-generated id rather than creating a duplicate."""
    real_create = claims.create
    calls = 0

    def flaky_create(*args, **kwargs):
        nonlocal calls
        calls += 1
        claim = real_create(*args, **kwargs)  # the write actually lands...
        if calls == 1:
            raise HeraldError("...but the response never made it back")
        return claim

    monkeypatch.setattr(claims, "create", flaky_create)
    sleeps: list[float] = []
    payload = {"merged": True, "gates_passed": True, "project_name": "Marshal S-1.10"}
    result = webhook.handle_on_pr_close(tmp_path, payload, sleep=sleeps.append)
    assert result.status == 201
    # `create` was called exactly once: the retry's second attempt found
    # the committed row via `claims.read_one` and never re-called `create`.
    assert calls == 1
    assert sleeps == [1.0]
    stored = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert len(stored) == 1
    assert stored[0].id == result.body["claim_id"]


# --- create_app / the ASGI3 boundary ---------------------------------------


def test_create_app_rejects_a_blank_secret(tmp_path: Path):
    """`resolve_webhook_secret` already refuses a blank env var, but that
    guard is opt-in -- a caller who resolves `secret` some other way must
    not silently get an `app` whose `verify_signature` accepts a forged
    signature computed from an empty key."""
    with pytest.raises(HeraldError, match="secret"):
        webhook.create_app(tmp_path, b"")


def test_asgi_app_valid_signed_on_ship_post_creates_a_progress_record(tmp_path: Path):
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden", "compute_hours": 2.0}).encode("utf-8")
    scope = _scope(
        webhook.ON_SHIP_PATH,
        headers=_signed_headers(secret, body),
    )
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 201
    assert recorder.json_body["station"] == "warden"
    records = progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)
    assert len(records) == 1
    assert records[0].compute_hours == 2.0


def test_asgi_app_valid_signed_on_pr_close_post_creates_a_claim(tmp_path: Path):
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"merged": True, "gates_passed": True, "project_name": "Marshal S-1.10"}).encode("utf-8")
    scope = _scope(
        webhook.ON_PR_CLOSE_PATH,
        headers=_signed_headers(secret, body),
    )
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 201
    stored = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert len(stored) == 1
    assert stored[0].project_name == "Marshal S-1.10"


def test_asgi_app_unknown_path_is_404_and_never_reads_the_body(tmp_path: Path):
    app = webhook.create_app(tmp_path, b"secret")
    recorder = _Recorder()
    asyncio.run(app(_scope("/nope"), _boom_receive, recorder))
    assert recorder.status == 404


def test_asgi_app_wrong_method_on_a_known_path_is_405_and_never_reads_the_body(
    tmp_path: Path,
):
    app = webhook.create_app(tmp_path, b"secret")
    recorder = _Recorder()
    scope = _scope(webhook.ON_SHIP_PATH, method="GET")
    asyncio.run(app(scope, _boom_receive, recorder))
    assert recorder.status == 405


def test_asgi_app_missing_signature_is_401_and_makes_no_storage_call(tmp_path: Path):
    app = webhook.create_app(tmp_path, b"secret")
    body = json.dumps({"station": "warden"}).encode("utf-8")
    recorder = _Recorder()
    asyncio.run(app(_scope(webhook.ON_SHIP_PATH), _receive_once(body), recorder))
    assert recorder.status == 401
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_asgi_app_wrong_secret_signature_is_401(tmp_path: Path):
    app = webhook.create_app(tmp_path, b"the-real-secret")
    body = json.dumps({"station": "warden"}).encode("utf-8")
    scope = _scope(
        webhook.ON_SHIP_PATH,
        headers=_signed_headers(b"a-different-secret", body),
    )
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 401
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_asgi_app_malformed_json_body_is_400(tmp_path: Path):
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = b"not json"
    scope = _scope(
        webhook.ON_SHIP_PATH,
        headers=_signed_headers(secret, body),
    )
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 400
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_asgi_app_oversized_body_is_413_before_signature_check(tmp_path: Path, monkeypatch):
    """The body-size cap is enforced BEFORE authentication -- an
    unauthenticated caller must not be able to force unbounded memory
    buffering just by streaming an oversized body. Proven the same way the
    existing `_boom_receive`-style tests prove "never reads the body": here
    `verify_signature` itself is made to raise if it is ever reached."""
    app = webhook.create_app(tmp_path, b"secret")

    def _boom_verify_signature(*args, **kwargs):
        raise AssertionError("verify_signature must not run for an oversized body")

    monkeypatch.setattr(webhook, "verify_signature", _boom_verify_signature)

    # Two chunks, each just over half the cap -- the second chunk pushes
    # the accumulated body over MAX_BODY_BYTES without needing to allocate
    # a single huge bytes object.
    chunk = b"a" * (webhook.MAX_BODY_BYTES // 2 + 1)

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": chunk, "more_body": True}

    recorder = _Recorder()
    asyncio.run(app(_scope(webhook.ON_SHIP_PATH), receive, recorder))
    assert recorder.status == 413
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_asgi_app_unexpected_exception_is_a_500_not_an_uncaught_propagation(tmp_path: Path, monkeypatch):
    """An ASGI app must always send a response. Anything other than the
    deliberately-handled cases (`_BodyTooLarge`, malformed JSON, each
    handler's own `errors.HeraldError` handling) is a bug this module did
    not anticipate -- `json.loads` raising something outside the
    `except (ValueError, RecursionError)` clause stands in for one here.
    (`RecursionError` was the original stand-in and is now a real, handled
    400 -- deep nesting is malformed input, not a bug -- so the stand-in
    has to be something genuinely unanticipated.)"""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden"}).encode("utf-8")
    scope = _scope(
        webhook.ON_SHIP_PATH,
        headers=_signed_headers(secret, body),
    )

    def _boom_loads(*args, **kwargs):
        raise RuntimeError("neither a ValueError nor a RecursionError")

    monkeypatch.setattr(webhook.json, "loads", _boom_loads)
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 500
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_asgi_app_ignores_a_non_http_scope(tmp_path: Path):
    app = webhook.create_app(tmp_path, b"secret")
    recorder = _Recorder()
    asyncio.run(app({"type": "lifespan"}, _boom_receive, recorder))
    assert recorder.messages == []


# --- review pass 2: hardening the boundary --------------------------------


@pytest.mark.parametrize(
    "header",
    [
        "sha256=" + "\xff" * 64,  # non-ASCII: `compare_digest` RAISES on this
        "sha256=" + "z" * 64,  # ASCII, right length, not hex
        "sha256=" + "0" * 63,  # hex, one digit short
        "sha256=" + "0" * 65,  # hex, one digit long
        "sha256=",  # prefix only
    ],
)
def test_verify_signature_rejects_a_malformed_hex_half_without_raising(header: str):
    """`hmac.compare_digest` on two `str`s raises `TypeError` for a
    non-ASCII character rather than returning `False`, and the header is
    attacker-controlled. `verify_signature`'s contract is "returns `False`
    rather than raising", so the hex half is shape-checked first."""
    assert webhook.verify_signature(b"secret", b"body", header, _timestamp()) is False


def test_asgi_app_non_ascii_signature_is_401_not_a_500_with_an_alert(tmp_path: Path, caplog):
    """The 401/500 distinction is the whole point: ERROR logging is this
    module's ONLY operator-alert channel, so an unauthenticated caller able
    to force one ERROR record per request could drown the real
    `retries_exhausted` alerts without ever holding the secret."""
    app = webhook.create_app(tmp_path, b"shared-secret")
    body = json.dumps({"station": "warden"}).encode("utf-8")
    scope = _scope(
        webhook.ON_SHIP_PATH,
        headers=[(b"x-hub-signature-256", b"sha256=" + b"\xff" * 64)],
    )
    recorder = _Recorder()
    with caplog.at_level("ERROR", logger=webhook.logger.name):
        asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 401
    assert [r for r in caplog.records if r.levelname == "ERROR"] == []
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_handle_on_pr_close_two_different_prs_on_one_day_create_two_claims(
    tmp_path: Path,
):
    """Keyed on project+date ALONE, two real same-day ships computed one
    id, so the second was silently swallowed by the idempotency guard and
    answered 201 with its evidence dropped -- the "an unrecorded ship is
    indistinguishable from no ship" failure this story exists to close."""
    first = {
        "merged": True,
        "gates_passed": True,
        "project_name": "Marshal",
        "shipped_date": "2026-08-13",
        "evidence": [{"type": "other", "url": "https://ci/pr/100", "label": "PR 100"}],
    }
    second = dict(
        first,
        evidence=[{"type": "other", "url": "https://ci/pr/101", "label": "PR 101"}],
    )
    assert webhook.handle_on_pr_close(tmp_path, first).status == 201
    assert webhook.handle_on_pr_close(tmp_path, second).status == 201
    stored = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert len(stored) == 2
    assert sorted(e.url for c in stored for e in c.evidence) == [
        "https://ci/pr/100",
        "https://ci/pr/101",
    ]


def test_handle_on_pr_close_distinct_event_ids_create_distinct_claims(tmp_path: Path):
    """`event_id` is the precise discriminator (what Story 13.6's workflow
    step should send) -- it tells two ships apart even when nothing else in
    the payload does."""
    payload = {
        "merged": True,
        "gates_passed": True,
        "project_name": "Marshal",
        "shipped_date": "2026-08-13",
    }
    first = webhook.handle_on_pr_close(tmp_path, dict(payload, event_id="pr-100"))
    second = webhook.handle_on_pr_close(tmp_path, dict(payload, event_id="pr-101"))
    assert (first.status, second.status) == (201, 201)
    assert len(claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)) == 2


def test_handle_on_pr_close_redelivery_with_the_same_event_id_is_idempotent(
    tmp_path: Path,
):
    payload = {
        "merged": True,
        "gates_passed": True,
        "project_name": "Marshal",
        "shipped_date": "2026-08-13",
        "event_id": "pr-100",
    }
    first = webhook.handle_on_pr_close(tmp_path, payload)
    second = webhook.handle_on_pr_close(tmp_path, dict(payload))
    assert first.body["claim_id"] == second.body["claim_id"]
    assert len(claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)) == 1


def test_handle_on_pr_close_claim_id_is_recomputable_from_the_stored_record(
    tmp_path: Path,
):
    """`claims.create`'s own default for an omitted `shipped_date` is the
    LOCAL `date.today()`, while this module computes UTC everywhere. Each
    side falling back on its own clock stored a record whose `shipped_date`
    the id could not be recomputed from -- and made a redelivery straddling
    the two clocks' midnight compute a different id, creating the duplicate
    the deterministic id exists to prevent."""
    payload = {"merged": True, "gates_passed": True, "project_name": "Marshal"}
    result = webhook.handle_on_pr_close(tmp_path, payload)
    (stored,) = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert stored.shipped_date == datetime.now(UTC).date().isoformat()
    recomputed = webhook._claim_id_for(payload, stored.shipped_date)
    assert recomputed == result.body["claim_id"]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"station": "   "}, "must not be blank"),
        ({"station": "warden", "compute_hours": -5.0}, "must not be negative"),
        ({"station": "warden", "token_spend": -1}, "must not be negative"),
        ({"station": "warden", "wall_clock_hours": -0.5}, "must not be negative"),
        ({"station": "warden", "compute_hours": 10**400}, "out of range"),
        ({"station": "warden", "token_spend": 2**63}, "out of range"),
        ({"station": "warden", "token_spend": -(2**63) - 1}, "out of range"),
        # `event_id` is an `on-pr-close` field, so on THIS route it is an
        # unknown one -- a 400, not a silent ignore (see
        # `_problem_unknown_fields`).
        ({"station": "warden", "event_id": "irrelevant here"}, "unknown field(s)"),
        ({"station": "warden", "token_spend": 2**63 - 1}, None),
    ],
)
def test_handle_on_ship_rejects_out_of_range_values_as_400(
    tmp_path: Path, payload: dict[str, Any], expected: str | None
):
    """Both range cases used to escape as an opaque 500: `math.isfinite`
    RAISES `OverflowError` for an int too large to convert to a float, and
    an int outside SQLite's signed-64-bit range raises `OverflowError` at
    bind time -- neither is a `HeraldError`, so neither reached the retry
    helper's translation. The negative cases WERE `HeraldError`s, which is
    worse in its own way: indistinguishable from a transient storage
    failure, so they burned all 3 attempts, raised one alert blaming
    storage, and returned a 500 that invites CI to re-fire forever."""
    result = webhook.handle_on_ship(tmp_path, payload, sleep=lambda _: None)
    if expected is None:
        assert result.status == 201
        return
    assert result.status == 400
    assert expected in result.body["error"]
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_handle_on_pr_close_rejects_a_non_string_event_id(tmp_path: Path):
    result = webhook.handle_on_pr_close(
        tmp_path,
        {
            "merged": True,
            "gates_passed": True,
            "project_name": "Marshal",
            "event_id": 100,
        },
    )
    assert result.status == 400
    assert "event_id" in result.body["error"]
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


def test_log_retry_exhausted_emits_valid_json_for_a_non_finite_payload_value(tmp_path: Path, caplog):
    """`json.dumps` emits bare `NaN`/`Infinity` tokens, which RFC 8259 does
    not allow and strict consumers reject -- and `json.loads` accepts those
    literals on the way in, through any field `_problem_on_ship` does not
    know about. A "structured JSON record" nobody can parse is not an
    alert."""
    with caplog.at_level("ERROR", logger=webhook.logger.name):
        webhook._log_retry_exhausted(
            "on-ship",
            {"station": "warden", "unknown_extra": float("nan")},
            HeraldError("boom"),
        )
    (record,) = [r for r in caplog.records if r.levelname == "ERROR"]
    parsed = json.loads(record.getMessage())  # would raise on a bare NaN token
    assert parsed["payload"]["unknown_extra"] == "nan"


def test_asgi_app_duplicate_json_keys_are_400(tmp_path: Path):
    """`json.loads` keeps the LAST value for a repeated key, so a duplicated
    `gates_passed` flips the ship gate on a payload that also says it should
    not -- the same AD-6 reasoning `progress`/`claims`/`state` already apply
    to the documents they read."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = b'{"merged": true, "gates_passed": false, "gates_passed": true, "project_name": "M"}'
    scope = _scope(
        webhook.ON_PR_CLOSE_PATH,
        headers=_signed_headers(secret, body),
    )
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 400
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


def test_asgi_app_routes_correctly_when_mounted_under_a_root_path(tmp_path: Path):
    """`scope["path"]` includes the prefix the host mounted this app under,
    so exact-matching the route literals 404s every delivery the moment
    Story 13.6 mounts it anywhere but the root."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden"}).encode("utf-8")
    scope = _scope(
        "/herald" + webhook.ON_SHIP_PATH,
        headers=_signed_headers(secret, body),
    )
    scope["root_path"] = "/herald"
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 201
    assert len(progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)) == 1


def test_asgi_app_client_disconnect_mid_body_answers_nothing(tmp_path: Path, caplog):
    """`http.disconnect` carries no `more_body` key, so the drain loop read
    it as "body complete" and handed a TRUNCATED body to
    `verify_signature` -- answering a network truncation with `401 invalid
    or missing HMAC signature` and sending an operator hunting a secret
    mismatch that never happened. There is also nobody left to answer."""
    app = webhook.create_app(tmp_path, b"shared-secret")
    messages: list[dict[str, Any]] = [
        {"type": "http.request", "body": b'{"stat', "more_body": True},
        {"type": "http.disconnect"},
    ]

    async def receive() -> dict[str, Any]:
        return messages.pop(0)

    recorder = _Recorder()
    with caplog.at_level("ERROR", logger=webhook.logger.name):
        asyncio.run(app(_scope(webhook.ON_SHIP_PATH), receive, recorder))
    assert recorder.messages == []
    assert [r for r in caplog.records if r.levelname == "ERROR"] == []
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_asgi_app_send_failure_mid_response_does_not_start_a_second_response(tmp_path: Path, caplog):
    """The last-resort guard had no "response already started" flag, so a
    send failure after `http.response.start` -- an ordinary mid-response
    client disconnect -- made it issue a SECOND `http.response.start`; the
    host rejects that, and the rejection then propagated out of `app`,
    which is exactly the uncaught escape the guard exists to prevent."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden"}).encode("utf-8")
    scope = _scope(
        webhook.ON_SHIP_PATH,
        headers=_signed_headers(secret, body),
    )
    sent: list[str] = []

    async def flaky_send(message: Mapping[str, Any]) -> None:
        sent.append(message["type"])
        if message["type"] == "http.response.body":
            raise RuntimeError("client went away mid-response")

    with caplog.at_level("ERROR", logger=webhook.logger.name):
        asyncio.run(app(scope, _receive_once(body), flaky_send))  # must not raise
    assert sent == ["http.response.start", "http.response.body"]
    assert len([r for r in caplog.records if r.levelname == "ERROR"]) == 1


# --- third review pass: trust, storability, and routing boundaries -----------


def test_verify_signature_accepts_an_uppercase_hex_signature():
    """`hexdigest()` is lowercase, but `_HEX_DIGITS` admits uppercase
    through the shape gate -- so an otherwise-correct signature from a
    producer rendering hex uppercase (Go's `%X`, Java's `%02X`,
    PowerShell's `[BitConverter]::ToString`) reached `compare_digest` and
    was guaranteed to fail, answering a bare 401 and sending whoever
    writes Story 13.6's producer hunting a secret mismatch that never
    happened."""
    secret, body = b"shared-secret", b'{"station":"warden"}'
    ts = _timestamp()
    lower = _sign(secret, ts, body)
    upper = "sha256=" + lower[len("sha256=") :].upper()
    assert webhook.verify_signature(secret, body, upper, ts) is True
    assert webhook.verify_signature(secret, body, lower, ts) is True


@pytest.mark.parametrize("shipped_date", ["13/08/2026", "yesterday", "", "2026-13-45", "2026-08-13T10:00:00Z"])
def test_handle_on_pr_close_rejects_a_malformed_shipped_date(tmp_path: Path, shipped_date: str):
    """`claims.create` performs NO date validation, and `claims.list_claims`
    then calls `date.fromisoformat` on whatever was stored with no guard --
    so one such delivery made every subsequent `herald success list
    --date-range ...` raise a bare `ValueError` out of `cli.main`
    (`cli.dispatch` translates only `HeraldError`). Type-checking the field
    was never enough."""
    result = webhook.handle_on_pr_close(
        tmp_path,
        {
            "merged": True,
            "gates_passed": True,
            "project_name": "Marshal",
            "shipped_date": shipped_date,
        },
    )
    assert result.status == 400
    assert "shipped_date" in result.body["error"]
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


def test_handle_on_pr_close_rejects_a_blank_event_id(tmp_path: Path):
    """A blank `event_id` is strictly WORSE than none: `_claim_id_for`
    branches on `is not None`, so `""` -- what an unset workflow input or a
    `${{ github.event.number }}` on a non-PR trigger renders to -- became
    the CONSTANT discriminator `"event:"` AND suppressed the evidence
    fallback, collapsing every same-day ship for a project onto one claim,
    answered 201, with the loser's evidence dropped."""
    base = {"merged": True, "gates_passed": True, "project_name": "Marshal"}
    first = webhook.handle_on_pr_close(
        tmp_path,
        {
            **base,
            "event_id": "",
            "evidence": [{"type": "other", "url": "https://ci/pr/100", "label": "PR"}],
        },
    )
    second = webhook.handle_on_pr_close(
        tmp_path,
        {
            **base,
            "event_id": "   ",
            "evidence": [{"type": "other", "url": "https://ci/pr/101", "label": "PR"}],
        },
    )
    assert (first.status, second.status) == (400, 400)
    assert "event_id" in first.body["error"]
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


@pytest.mark.parametrize(
    "payload",
    [
        {"station": "war\ud800den"},
        {"station": "warden", "unblock_narrative": "\ud800"},
        {"station": "warden", "shipped_capabilities": ["ok", "\ud800"]},
    ],
)
def test_handle_on_ship_rejects_an_unstorable_string_as_400(tmp_path: Path, payload: Mapping[str, Any], caplog):
    """`json.loads` accepts a lone surrogate escape and hands back a `str`
    no UTF-8 encoder will take. Left to `progress.upsert`, it arrived as a
    `HeraldError` indistinguishable from a transient storage fault: 3
    attempts, ~3s of real blocking, one ERROR alert blaming storage for a
    payload fault, and the 500 this module's contract invites CI to re-fire
    forever -- for a request that can never succeed. Same close
    `_problem_number` already made for the numeric fields."""
    sleeps: list[float] = []
    with caplog.at_level("ERROR", logger=webhook.logger.name):
        result = webhook.handle_on_ship(tmp_path, payload, sleep=sleeps.append)
    assert result.status == 400
    assert "UTF-8" in result.body["error"]
    assert sleeps == []
    assert [r for r in caplog.records if r.levelname == "ERROR"] == []
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


@pytest.mark.parametrize(
    "extra",
    [
        {"project_name": "ship-\ud800"},
        {
            "project_name": "Marshal",
            "evidence": [{"type": "other", "url": "https://\ud800", "label": "l"}],
        },
    ],
)
def test_handle_on_pr_close_rejects_an_unstorable_string_as_400(tmp_path: Path, extra: Mapping[str, Any], caplog):
    """The same close on the claim side -- and here it never even reached
    the retry helper: `_claim_id_for` feeds these values to `uuid.uuid5`,
    which encodes UTF-8, so the `UnicodeEncodeError` escaped as a plain
    exception into the catch-all 500 plus one `unexpected_exception` ERROR
    record per delivery."""
    sleeps: list[float] = []
    with caplog.at_level("ERROR", logger=webhook.logger.name):
        result = webhook.handle_on_pr_close(
            tmp_path,
            {"merged": True, "gates_passed": True, **extra},
            sleep=sleeps.append,
        )
    assert result.status == 400
    assert "UTF-8" in result.body["error"]
    assert sleeps == []
    assert [r for r in caplog.records if r.levelname == "ERROR"] == []
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


def test_handle_on_ship_stores_the_station_stripped(tmp_path: Path):
    """The validator already `.strip()`s to reject a blank station, but the
    raw value was stored -- so `"warden"`, `" warden"` and `"warden\\n"`
    became three separate rows, and `progress.latest_for_station` matches
    exactly, making two of those three ships records no station-scoped
    reader or dashboard can ever find. (Whitespace normalization is not the
    "Never re-validate against `progress.STATIONS`" constraint: an
    unrecognized station is still accepted, and case is left alone.)"""
    for station in ("warden", " warden", "warden\n", "\twarden "):
        assert webhook.handle_on_ship(tmp_path, {"station": station}).status == 201
    stored = progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)
    assert [r.station for r in stored] == ["warden"]
    assert progress.latest_for_station(tmp_path / progress.DEFAULT_PROGRESS_PATH, "warden") is not None


def test_create_app_rejects_a_str_secret(tmp_path: Path):
    """The likelier half of the "resolved some other way" mistake the
    blank-secret guard exists for: `os.environ["HERALD_WEBHOOK_SECRET"]`
    passed directly is a `str`, which is truthy, so it built an `app` that
    then died in `hmac.new` on EVERY request -- a silent 100% outage
    answered 500, one `unexpected_exception` ERROR record per delivery."""
    with pytest.raises(HeraldError, match="must be bytes"):
        webhook.create_app(tmp_path, "shared-secret")  # type: ignore[arg-type]


def test_asgi_app_routes_correctly_when_root_path_is_a_bare_slash(tmp_path: Path):
    """A host started with `--root-path /` reports `root_path == "/"`,
    which as a bare string prefix matched every path and left
    `api/herald/...` with no leading slash -- 404ing every delivery under
    an ordinary configuration. Stripping on segment boundaries, after
    normalizing the trailing slash away, is what the prefix means."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden"}).encode("utf-8")
    scope = _scope(
        webhook.ON_SHIP_PATH,
        headers=_signed_headers(secret, body),
    )
    recorder = _Recorder()
    asyncio.run(app({**scope, "root_path": "/"}, _receive_once(body), recorder))
    assert recorder.status == 201


def test_asgi_app_declines_a_websocket_scope_instead_of_returning_silently(
    tmp_path: Path,
):
    """ASGI requires a websocket app to answer the handshake; returning
    without one is an application error the host reports (uvicorn: "ASGI
    callable returned without sending handshake") once per connection.
    This HTTP-only leaf app declines the connection instead."""
    app = webhook.create_app(tmp_path, b"secret")
    recorder = _Recorder()
    scope = {"type": "websocket", "path": webhook.ON_SHIP_PATH, "headers": []}
    asyncio.run(app(scope, _boom_receive, recorder))
    assert [m["type"] for m in recorder.messages] == ["websocket.close"]


def test_asgi_app_deeply_nested_json_is_400_not_a_500_with_an_alert(tmp_path: Path, caplog):
    """`[` x 100_000 is only 200 KB -- well under `MAX_BODY_BYTES`, so it
    passes the 413 gate and the HMAC check, then blows the stack in
    `json.loads`. `RecursionError` is not a `ValueError`, so it fell to the
    last-resort guard as a 500 plus one `unexpected_exception` ERROR record
    -- for input that is simply malformed, and which this module's contract
    then invites CI to re-fire forever, one record each time.
    `progress.py`/`claims.py` already pair the two exceptions when they
    parse, for exactly this."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = b'{"station":"warden","x":' + b"[" * 100_000 + b"]" * 100_000 + b"}"
    scope = _scope(
        webhook.ON_SHIP_PATH,
        headers=_signed_headers(secret, body),
    )
    recorder = _Recorder()
    with caplog.at_level("ERROR", logger=webhook.logger.name):
        asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 400
    assert [r for r in caplog.records if r.levelname == "ERROR"] == []


def test_asgi_app_assembles_a_chunked_body_and_stays_linear(tmp_path: Path):
    """`_read_body` accumulated with `body += chunk` on immutable `bytes`,
    which copies the whole accumulated body per chunk -- quadratic in the
    chunk count. `MAX_BODY_BYTES` bounds the memory but not that work, and
    this is the one part of the request that cannot leave the event-loop
    thread, so an UNAUTHENTICATED caller could stall every other in-flight
    request just by streaming a capped-size body in tiny chunks. Asserts
    both halves: the join reassembles correctly, and the read stays linear.

    Sized at exactly `MAX_BODY_MESSAGES` chunks, because that cap is now
    the worst chunk count a caller can reach -- this is the most quadratic
    work anyone can still ask for, so it is the right thing to bound. (The
    original measurement used 800_000 one-byte chunks: 16.57s before the
    fix, 0.23s after. That shape is a 413 now, so the same 800 KB arrives
    as `MAX_BODY_MESSAGES` equal chunks instead, which is still ~5e9 bytes
    of copying under the old quadratic behavior.)"""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden", "unblock_narrative": "x" * 800_000}).encode("utf-8")
    headers = _signed_headers(secret, body)
    chunk_size = -(-len(body) // webhook.MAX_BODY_MESSAGES)  # ceil

    def receive_in_single_bytes():
        offsets = iter(range(0, len(body), chunk_size))

        async def receive() -> dict[str, Any]:
            index = next(offsets)
            return {
                "type": "http.request",
                "body": body[index : index + chunk_size],
                "more_body": index + chunk_size < len(body),
            }

        return receive

    recorder = _Recorder()
    started = time.monotonic()
    asyncio.run(
        app(
            _scope(webhook.ON_SHIP_PATH, headers=headers),
            receive_in_single_bytes(),
            recorder,
        )
    )
    elapsed = time.monotonic() - started
    # The signature only verifies if every chunk was reassembled in order.
    assert recorder.status == 201
    (stored,) = progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)
    assert stored.unblock_narrative == "x" * 800_000
    assert elapsed < 4.0, f"quadratic body accumulation is back ({elapsed:.1f}s)"


def test_claim_id_with_an_event_id_does_not_depend_on_the_date(tmp_path: Path):
    """A redelivery is by design a LATER call (the non-2xx contract invites
    CI to re-fire), and `shipped_date` falls back to the SERVER's clock
    when the payload omits it -- so folding a server-computed date into the
    name made a redelivery that merely crossed UTC midnight compute a
    DIFFERENT id and create the duplicate the deterministic id exists to
    prevent. `event_id` already identifies the event, so the date is left
    out on that branch; without one, the evidence fallback still needs it."""
    payload = {
        "merged": True,
        "gates_passed": True,
        "project_name": "Marshal",
        "event_id": "pr-100",
    }
    assert webhook._claim_id_for(payload, "2026-08-13") == webhook._claim_id_for(payload, "2026-08-14")
    no_event = {k: v for k, v in payload.items() if k != "event_id"}
    assert webhook._claim_id_for(no_event, "2026-08-13") != webhook._claim_id_for(no_event, "2026-08-14")


def test_handle_on_pr_close_redelivery_across_utc_midnight_is_idempotent(tmp_path: Path, monkeypatch):
    """The same property end to end: the first delivery lands at 23:59:50Z
    and the re-fire at 00:00:20Z the next day. Before the fix this stored
    two claims with two `shipped_date`s for one merged PR."""
    payload = {
        "merged": True,
        "gates_passed": True,
        "project_name": "Marshal",
        "event_id": "pr-100",
    }
    clock = iter(
        [
            datetime(2026, 8, 13, 23, 59, 50, tzinfo=UTC),
            datetime(2026, 8, 14, 0, 0, 20, tzinfo=UTC),
        ]
    )

    class _FakeDatetime:
        @staticmethod
        def now(tz=None):
            return next(clock)

    monkeypatch.setattr(webhook, "datetime", _FakeDatetime)
    first = webhook.handle_on_pr_close(tmp_path, payload)
    second = webhook.handle_on_pr_close(tmp_path, dict(payload))
    assert (first.status, second.status) == (201, 201)
    assert first.body["claim_id"] == second.body["claim_id"]
    assert len(claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)) == 1


# --- unknown payload fields (the AD-6 convention) ------------------------------


def test_handle_on_ship_rejects_an_unknown_field_instead_of_wiping_the_day(
    tmp_path: Path,
):
    """A misspelled field used to be ignored, which on THIS route is not a
    harmless no-op: a same-day delivery REPLACES, so `{"token_spends": ...}`
    answered 201 while resetting the real figure recorded minutes earlier.
    The producer is a hand-written workflow YAML with no schema and no
    linter, so nothing else would ever catch the typo. `progress
    ._fields_problem` and `claims._claim_from_dict` both already reject
    unknown fields; this route is now consistent with them."""
    good = {"station": "warden", "token_spend": 900_000, "compute_hours": 4.0}
    assert webhook.handle_on_ship(tmp_path, good).status == 201

    typo = {"station": "warden", "token_spends": 250_000, "compute_hrs": 12.5}
    result = webhook.handle_on_ship(tmp_path, typo, sleep=lambda _: None)
    assert result.status == 400
    assert "unknown field(s) 'compute_hrs', 'token_spends'" in result.body["error"]

    # The real figures survived, because the typo never reached `upsert`.
    (stored,) = progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)
    assert (stored.token_spend, stored.compute_hours) == (900_000, 4.0)


@pytest.mark.parametrize(
    "payload",
    [
        # Rejected even when the gate says not-shipped: a typo is a producer
        # bug worth one loud 400 whichever way the gate falls that day.
        {"merged": False, "gates_passed": False, "evidences": []},
        {"merged": True, "gates_passed": True, "project_name": "M", "evidences": []},
        {"merged": True, "gates_passed": True, "project_name": "M", "eventId": "1"},
    ],
)
def test_handle_on_pr_close_rejects_an_unknown_field(tmp_path: Path, payload: dict[str, Any]):
    result = webhook.handle_on_pr_close(tmp_path, payload, sleep=lambda _: None)
    assert result.status == 400
    assert "unknown field(s)" in result.body["error"]
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


def test_handle_on_pr_close_rejects_an_unknown_evidence_field(tmp_path: Path):
    """`claims._evidence_from_dict` rejects an unknown evidence field; a
    misspelled `urls` here would otherwise have been dropped silently while
    the entry still claimed to be evidence."""
    result = webhook.handle_on_pr_close(
        tmp_path,
        {
            "merged": True,
            "gates_passed": True,
            "project_name": "Marshal",
            "evidence": [
                {
                    "type": "other",
                    "url": "https://example.com/pr/1",
                    "label": "pr",
                    "urls": "https://example.com/typo",
                }
            ],
        },
        sleep=lambda _: None,
    )
    assert result.status == 400
    assert "unknown field(s) 'urls'" in result.body["error"]
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


# --- body read: the message-count bound ---------------------------------------


def test_asgi_app_bounds_the_number_of_body_chunks(tmp_path: Path):
    """`MAX_BODY_BYTES` alone never bounds a stream of ZERO-length chunks:
    they add nothing to the byte counter, never satisfy `more_body`, and
    never end -- so an UNAUTHENTICATED caller (this is before
    `verify_signature`) held the request open forever while the chunk list
    grew one slot per message. Measured before this bound: 3,000,001 empty
    chunks drained without ever tripping the byte cap."""
    app = webhook.create_app(tmp_path, b"shared-secret")
    delivered = 0

    async def receive() -> dict[str, Any]:
        nonlocal delivered
        delivered += 1
        return {"type": "http.request", "body": b"", "more_body": True}

    recorder = _Recorder()
    asyncio.run(app(_scope(webhook.ON_SHIP_PATH), receive, recorder))
    assert recorder.status == 413
    assert "chunks" in recorder.json_body["error"]
    # It terminated, and did so at the cap rather than by exhausting anything.
    assert delivered == webhook.MAX_BODY_MESSAGES + 1


# --- shipped_date must be the canonical YYYY-MM-DD -----------------------------


@pytest.mark.parametrize("value", ["20260813", "2026-W33-4", "2026-W33"])
def test_handle_on_pr_close_rejects_a_non_canonical_iso_date(tmp_path: Path, value: str):
    """`date.fromisoformat` accepts every ISO 8601 date form on 3.11+, so a
    parse-only check kept the promise its own error message makes
    ("YYYY-MM-DD") for the shapes it rejected and broke it for these. The
    value is stored verbatim and `SuccessPanel.jsx` filters `shipped_date`
    by raw STRING comparison -- `"20260813" > "2026-12-31"` is true -- so
    such a claim vanishes from every date-filtered dashboard view."""
    result = webhook.handle_on_pr_close(
        tmp_path,
        {
            "merged": True,
            "gates_passed": True,
            "project_name": "Marshal",
            "shipped_date": value,
        },
        sleep=lambda _: None,
    )
    assert result.status == 400
    assert "YYYY-MM-DD" in result.body["error"]
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


def test_handle_on_pr_close_accepts_the_canonical_iso_date(tmp_path: Path):
    result = webhook.handle_on_pr_close(
        tmp_path,
        {
            "merged": True,
            "gates_passed": True,
            "project_name": "Marshal",
            "shipped_date": "2026-08-13",
        },
    )
    assert result.status == 201
    (stored,) = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert stored.shipped_date == "2026-08-13"


# --- notice evidence must name a notice that exists ----------------------------


def _notice_payload(component: str) -> dict[str, Any]:
    return {
        "merged": True,
        "gates_passed": True,
        "project_name": "Marshal",
        "evidence": [{"type": "notice", "url": component, "label": "notice"}],
    }


def test_handle_on_pr_close_rejects_evidence_naming_a_nonexistent_notice(
    tmp_path: Path,
):
    """A `notice` entry's `url` is a Notice COMPONENT NAME, and both
    `claims.publish` and `claims._revalidated_entry` short-circuit it as
    trivially valid -- stamped `validated=True` without a single check. The
    CLI compensates by calling `notices.get_notice` first; without the same
    check here this route was a way to attach evidence that passes Story
    9.5's entire evidence gate while referring to nothing."""
    result = webhook.handle_on_pr_close(tmp_path, _notice_payload("never-authored"), sleep=lambda _: None)
    assert result.status == 400
    assert "notice" in result.body["error"]
    assert claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH) == []


def test_handle_on_pr_close_accepts_evidence_naming_a_real_notice(tmp_path: Path):
    from pyforge.herald import notices

    notices.author_notice(
        tmp_path,
        notice_type="deprecation",
        component="auth-api-v1",
        what="auth-api-v1 is deprecated",
        why="superseded by auth-api-v2",
        migration="swap the base URL",
        deadline=None,
        reason_link=None,
        publish=False,
    )
    result = webhook.handle_on_pr_close(tmp_path, _notice_payload("auth-api-v1"))
    assert result.status == 201
    (stored,) = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert stored.evidence[0].url == "auth-api-v1"


# --- project_name whitespace and claim-id encoding -----------------------------


def test_handle_on_pr_close_strips_project_name_so_a_redelivery_still_dedupes(
    tmp_path: Path,
):
    """`station` was already stored stripped; `project_name` was not -- so a
    `${{ }}` expansion picking up a trailing newline computed a DIFFERENT
    uuid5 and created a duplicate claim, on the one surface with no dedupe
    key to recover with."""
    base = {
        "merged": True,
        "gates_passed": True,
        "project_name": "Marshal",
        "event_id": "pr-1",
    }
    first = webhook.handle_on_pr_close(tmp_path, dict(base))
    second = webhook.handle_on_pr_close(tmp_path, {**base, "project_name": "Marshal\n"})
    assert (first.status, second.status) == (201, 201)
    assert first.body["claim_id"] == second.body["claim_id"]
    stored = claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)
    assert [c.project_name for c in stored] == ["Marshal"]


def test_claim_id_does_not_collide_across_its_two_name_parts(tmp_path: Path):
    """The name was built by joining caller-controlled strings around a bare
    `|`, so `{"project_name": "A|event:B", "event_id": "C"}` and
    `{"project_name": "A", "event_id": "B|event:C"}` rendered the identical
    name -- two distinct events computing one id, and the second silently
    swallowed by the idempotency guard at 201."""
    left = {"merged": True, "gates_passed": True, "project_name": "A|event:B", "event_id": "C"}
    right = {"merged": True, "gates_passed": True, "project_name": "A", "event_id": "B|event:C"}
    assert webhook._claim_id_for(left, "2026-08-13") != webhook._claim_id_for(right, "2026-08-13")
    assert webhook.handle_on_pr_close(tmp_path, left).status == 201
    assert webhook.handle_on_pr_close(tmp_path, right).status == 201
    assert len(claims.read_all(tmp_path / claims.DEFAULT_CLAIMS_PATH)) == 2


# --- the alert record stays bounded --------------------------------------------


def test_retry_exhausted_alert_truncates_an_oversized_payload(tmp_path: Path, caplog, monkeypatch):
    """The alert log IS this module's only operator-alert channel, and it
    embedded the whole caller-controlled payload -- so one signed delivery
    near `MAX_BODY_BYTES` wrote a ~1 MB log line, and the module's own
    contract then invites CI to re-fire it. Measured before this bound: a
    200 KB field produced a 200,141-byte record."""

    def always_fails(*args: Any, **kwargs: Any):
        raise HeraldError("storage is down")

    monkeypatch.setattr(progress, "upsert", always_fails)
    payload = {"station": "warden", "unblock_narrative": "x" * 500_000}
    with caplog.at_level("ERROR", logger=webhook.logger.name):
        result = webhook.handle_on_ship(tmp_path, payload, sleep=lambda _: None)
    assert result.status == 500
    (record,) = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(record.getMessage()) < 10_000
    # Still a real, parseable JSON record that names what was dropped.
    document = json.loads(record.getMessage())
    assert document["payload"]["truncated"] is True
    assert document["payload"]["serialized_chars"] > 500_000


def test_retry_exhausted_alert_keeps_a_small_payload_verbatim(tmp_path: Path, caplog, monkeypatch):
    """The cap must not cost the ordinary case its detail -- every real
    payload is small, and the record is only useful if it shows one."""

    def always_fails(*args: Any, **kwargs: Any):
        raise HeraldError("storage is down")

    monkeypatch.setattr(progress, "upsert", always_fails)
    with caplog.at_level("ERROR", logger=webhook.logger.name):
        webhook.handle_on_ship(tmp_path, {"station": "warden"}, sleep=lambda _: None)
    (record,) = [r for r in caplog.records if r.levelname == "ERROR"]
    assert json.loads(record.getMessage())["payload"] == {"station": "warden"}


# --- every response send is inside the ASGI contract guard ---------------------


@pytest.mark.parametrize(
    ("scope", "label"),
    [
        (_scope("/nope"), "404"),
        (_scope(ON_SHIP := webhook.ON_SHIP_PATH, method="GET"), "405"),
        ({"type": "websocket", "path": webhook.ON_SHIP_PATH, "headers": []}, "ws"),
    ],
)
def test_asgi_app_never_propagates_a_send_failure(tmp_path: Path, caplog, scope: dict[str, Any], label: str):
    """The 404, 405 and websocket-close sends sat OUTSIDE `app()`'s
    last-resort guard, so a `send` that raises there escaped the callable --
    the exact uncaught escape the guard exists to prevent, per the module
    docstring's "Uncaught exceptions" section. It is reachable: uvicorn's
    websocket `send` raises `ClientDisconnected` up front when the peer is
    already gone."""
    app = webhook.create_app(tmp_path, b"shared-secret")

    async def exploding_send(message: dict[str, Any]) -> None:
        raise RuntimeError("client disconnected")

    with caplog.at_level("ERROR", logger=webhook.logger.name):
        asyncio.run(app(scope, _boom_receive, exploding_send))  # must not raise
    assert len([r for r in caplog.records if r.levelname == "ERROR"]) == 1


# --- route normalization -------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        webhook.ON_SHIP_PATH,
        webhook.ON_SHIP_PATH + "/",
        "/" + webhook.ON_SHIP_PATH,
        "/stations/herald/api/v1//webhooks/on-ship",
    ],
)
def test_asgi_app_normalizes_the_request_path(tmp_path: Path, path: str):
    """A routing 404 is indistinguishable from "the endpoint isn't
    deployed", which is why the mount prefix is normalized so carefully --
    the request path now gets the same treatment, so a correctly-signed
    delivery is not lost to a producer's trailing slash or to the doubled
    slash an nginx `location`/`proxy_pass` pair routinely emits."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden"}).encode()
    scope = _scope(path, headers=_signed_headers(secret, body))
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 201


def test_asgi_app_still_declines_a_genuinely_unknown_route(tmp_path: Path):
    """Normalization must not turn every near-miss into a match."""
    app = webhook.create_app(tmp_path, b"shared-secret")
    recorder = _Recorder()
    asyncio.run(
        app(
            _scope("/stations/herald/api/v1/webhooks/on-shipp"),
            _boom_receive,
            recorder,
        )
    )
    assert recorder.status == 404


def test_asgi_app_legacy_bare_api_namespace_path_is_not_served(tmp_path: Path):
    """Story 19.1: the pre-seam ``/api/herald/...`` literals must 404."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden"}).encode()
    scope = _scope(
        "/api/herald/webhooks/on-ship",
        headers=_signed_headers(secret, body),
    )
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 404


# --- the documented replace-not-merge contract ---------------------------------


def test_handle_on_ship_second_delivery_replaces_rather_than_merges(tmp_path: Path):
    """Three docstrings and two doc files call this out as a deliberate,
    footgun-shaped contract Story 13.6's workflow author must design
    around, and nothing pinned it: a refactor that read the existing row and
    merged omitted fields would have passed the whole suite. It applies
    across sources too -- the first record here is what an operator's
    `herald progress --update` would have written."""
    webhook.handle_on_ship(
        tmp_path,
        {
            "station": "warden",
            "shipped_capabilities": ["S-1.1"],
            "compute_hours": 6.0,
            "token_spend": 1_200_000,
            "unblock_narrative": "shipped the gate",
        },
    )
    webhook.handle_on_ship(tmp_path, {"station": "warden"})
    (stored,) = progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)
    assert list(stored.shipped_capabilities) == []
    assert (stored.compute_hours, stored.token_spend) == (0.0, 0)
    assert stored.unblock_narrative == ""


# --- Story 13.6: the X-Hub-Timestamp skew window (closing DW-FU-13-4) ---------


def test_verify_signature_rejects_a_timestamp_more_than_5_minutes_old():
    """The literal AC: a captured, previously-valid signed request, replayed
    after 5 minutes, is rejected -- before this story, the HMAC covered only
    `body`, so this exact replay verified forever (DW-FU-13-4)."""
    secret, body = b"shared-secret", b'{"station":"warden"}'
    stale = str(int(time.time()) - webhook.MAX_TIMESTAMP_SKEW_SECONDS - 1)
    header = "sha256=" + hmac.new(secret, stale.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
    assert webhook.verify_signature(secret, body, header, stale) is False


def test_verify_signature_accepts_a_timestamp_just_inside_the_skew_window():
    secret, body = b"shared-secret", b'{"station":"warden"}'
    fresh_enough = str(int(time.time()) - webhook.MAX_TIMESTAMP_SKEW_SECONDS + 5)
    header = "sha256=" + hmac.new(secret, fresh_enough.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
    assert webhook.verify_signature(secret, body, header, fresh_enough) is True


def test_verify_signature_rejects_a_timestamp_more_than_5_minutes_in_the_future():
    """Symmetric, not one-directional: a one-directional "reject only if
    older" check would leave a future-dated timestamp valid forever, until
    the server's own clock caught up to it -- see
    `MAX_TIMESTAMP_SKEW_SECONDS`'s own docstring."""
    secret, body = b"shared-secret", b'{"station":"warden"}'
    future = str(int(time.time()) + webhook.MAX_TIMESTAMP_SKEW_SECONDS + 1)
    header = "sha256=" + hmac.new(secret, future.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
    assert webhook.verify_signature(secret, body, header, future) is False


def test_verify_signature_rejects_a_missing_timestamp_header():
    secret, body = b"shared-secret", b'{"station":"warden"}'
    ts = _timestamp()
    good_signature = _sign(secret, ts, body)
    assert webhook.verify_signature(secret, body, good_signature, None) is False


@pytest.mark.parametrize(
    "bogus_timestamp",
    [
        "",  # empty
        "not-a-number",
        "12345.6",  # not an integer
        "-12345",  # signed -- `int()` alone would accept this
        "+12345",  # signed -- `int()` alone would accept this
        "1" * 17,  # over `_MAX_TIMESTAMP_HEADER_LEN`
        "123 456",  # whitespace -- `int()` alone would accept this
        "\xff" * 5,  # non-ASCII
    ],
)
def test_verify_signature_rejects_a_malformed_timestamp_without_raising(
    bogus_timestamp: str,
):
    """`int()` alone accepts a leading sign, internal whitespace, and
    underscores -- all attacker-controlled since the header is
    attacker-controlled -- so the shape is checked first, the same
    discipline the hex signature half already gets."""
    secret, body = b"shared-secret", b'{"station":"warden"}'
    good_signature = _sign(secret, _timestamp(), body)
    assert webhook.verify_signature(secret, body, good_signature, bogus_timestamp) is False


def test_asgi_app_replayed_request_with_a_stale_timestamp_is_401_before_storage(
    tmp_path: Path,
):
    """The I/O matrix's "Replayed captured request, stale timestamp" row,
    exercised through the full ASGI boundary: a request signed with a
    timestamp more than 5 minutes old is rejected before any storage call
    -- the endpoint never creates a Progress record for it."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden"}).encode("utf-8")
    stale = str(int(time.time()) - webhook.MAX_TIMESTAMP_SKEW_SECONDS - 30)
    headers = _signed_headers(secret, body, timestamp=stale)
    recorder = _Recorder()
    asyncio.run(app(_scope(webhook.ON_SHIP_PATH, headers=headers), _receive_once(body), recorder))
    assert recorder.status == 401
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_asgi_app_missing_timestamp_header_is_401(tmp_path: Path):
    """A correctly-signed body with no `X-Hub-Timestamp` at all -- the
    header simply is not proof, mirroring the existing missing-signature
    case."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden"}).encode("utf-8")
    ts = _timestamp()
    scope = _scope(
        webhook.ON_SHIP_PATH,
        headers=[(b"x-hub-signature-256", _sign(secret, ts, body).encode())],
    )
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 401
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_asgi_app_valid_fresh_timestamp_still_creates_the_record(tmp_path: Path):
    """The ordinary case survives the new gate: a freshly-signed request
    (the shared `_signed_headers` helper every other ASGI test already
    uses) still creates the record."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden"}).encode("utf-8")
    scope = _scope(webhook.ON_SHIP_PATH, headers=_signed_headers(secret, body))
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 201
    assert len(progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH)) == 1


def test_verify_signature_a_timestamp_cannot_be_swapped_onto_a_captured_body():
    """The timestamp is folded INTO the signed content, not merely compared
    alongside an unauthenticated one: recomputing the signature with a
    DIFFERENT timestamp than the one actually signed must fail, even
    though both timestamps are individually fresh -- otherwise a captured
    signature would remain valid under a relabeled timestamp forever,
    defeating the whole point of folding it in."""
    secret, body = b"shared-secret", b'{"station":"warden"}'
    ts_a, ts_b = _timestamp(), str(int(_timestamp()) + 1)
    signature_for_a = _sign(secret, ts_a, body)
    assert webhook.verify_signature(secret, body, signature_for_a, ts_b) is False
