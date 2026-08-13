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
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pyforge.herald import claims, progress, webhook
from pyforge.herald.errors import HeraldError

# --- ASGI test helpers --------------------------------------------------------


def _sign(secret: bytes, body: bytes) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def _scope(
    path: str, *, method: str = "POST", headers: list[tuple[bytes, bytes]] | None = None
) -> dict[str, Any]:
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
        return next(
            m["status"] for m in self.messages if m["type"] == "http.response.start"
        )

    @property
    def json_body(self) -> Any:
        body = b"".join(
            m["body"] for m in self.messages if m["type"] == "http.response.body"
        )
        return json.loads(body)


# --- verify_signature ---------------------------------------------------------


def test_verify_signature_accepts_a_valid_signature():
    secret = b"shared-secret"
    body = b'{"station": "warden"}'
    assert webhook.verify_signature(secret, body, _sign(secret, body)) is True


def test_verify_signature_rejects_a_mismatched_signature():
    secret = b"shared-secret"
    body = b'{"station": "warden"}'
    assert webhook.verify_signature(secret, body, "sha256=" + "0" * 64) is False


def test_verify_signature_rejects_a_missing_header():
    assert webhook.verify_signature(b"secret", b"body", None) is False


def test_verify_signature_rejects_a_header_with_no_sha256_prefix():
    assert webhook.verify_signature(b"secret", b"body", "deadbeef") is False


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


def test_handle_on_ship_retry_exhausted_emits_one_alert_and_returns_500(
    tmp_path: Path, monkeypatch, caplog
):
    calls = 0

    def always_fails(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise HeraldError("boom")

    monkeypatch.setattr(progress, "upsert", always_fails)
    sleeps: list[float] = []
    with caplog.at_level("ERROR", logger="pyforge.herald.webhook"):
        result = webhook.handle_on_ship(
            tmp_path, {"station": "warden"}, sleep=sleeps.append
        )
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
        "evidence": [
            {"type": "test_results", "url": "https://ci.example/run/1", "label": "tests"}
        ],
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


@pytest.mark.parametrize(
    ("merged", "gates_passed"), [(False, True), (True, False), (False, False)]
)
def test_handle_on_pr_close_not_shipped_is_a_202_no_op(
    tmp_path: Path, merged: bool, gates_passed: bool
):
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
def test_handle_on_pr_close_malformed_shipped_payload_is_400(
    tmp_path: Path, extra: Mapping[str, Any], fragment: str
):
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


def test_handle_on_pr_close_retry_exhausted_emits_one_alert_and_returns_500(
    tmp_path: Path, monkeypatch, caplog
):
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


def test_handle_on_pr_close_retry_is_idempotent_when_the_first_attempt_actually_committed(
    tmp_path: Path, monkeypatch
):
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
        headers=[(b"x-hub-signature-256", _sign(secret, body).encode())],
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
    body = json.dumps(
        {"merged": True, "gates_passed": True, "project_name": "Marshal S-1.10"}
    ).encode("utf-8")
    scope = _scope(
        webhook.ON_PR_CLOSE_PATH,
        headers=[(b"x-hub-signature-256", _sign(secret, body).encode())],
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
        headers=[(b"x-hub-signature-256", _sign(b"a-different-secret", body).encode())],
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
        headers=[(b"x-hub-signature-256", _sign(secret, body).encode())],
    )
    recorder = _Recorder()
    asyncio.run(app(scope, _receive_once(body), recorder))
    assert recorder.status == 400
    assert progress.read_all(tmp_path / progress.DEFAULT_PROGRESS_PATH) == []


def test_asgi_app_oversized_body_is_413_before_signature_check(
    tmp_path: Path, monkeypatch
):
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


def test_asgi_app_unexpected_exception_is_a_500_not_an_uncaught_propagation(
    tmp_path: Path, monkeypatch
):
    """An ASGI app must always send a response. Anything other than the
    deliberately-handled cases (`_BodyTooLarge`, malformed JSON, each
    handler's own `errors.HeraldError` handling) is a bug this module did
    not anticipate -- `json.loads` raising something outside its own
    `except (json.JSONDecodeError, UnicodeDecodeError)` clause stands in
    for one here."""
    secret = b"shared-secret"
    app = webhook.create_app(tmp_path, secret)
    body = json.dumps({"station": "warden"}).encode("utf-8")
    scope = _scope(
        webhook.ON_SHIP_PATH,
        headers=[(b"x-hub-signature-256", _sign(secret, body).encode())],
    )

    def _boom_loads(*args, **kwargs):
        raise RecursionError("not a JSONDecodeError or UnicodeDecodeError")

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
    assert webhook.verify_signature(b"secret", b"body", header) is False


def test_asgi_app_non_ascii_signature_is_401_not_a_500_with_an_alert(
    tmp_path: Path, caplog
):
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
        ({"station": "warden", "event_id": "irrelevant here"}, None),
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


def test_log_retry_exhausted_emits_valid_json_for_a_non_finite_payload_value(
    tmp_path: Path, caplog
):
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
    body = (
        b'{"merged": true, "gates_passed": false, "gates_passed": true,'
        b' "project_name": "M"}'
    )
    scope = _scope(
        webhook.ON_PR_CLOSE_PATH,
        headers=[(b"x-hub-signature-256", _sign(secret, body).encode())],
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
        headers=[(b"x-hub-signature-256", _sign(secret, body).encode())],
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


def test_asgi_app_send_failure_mid_response_does_not_start_a_second_response(
    tmp_path: Path, caplog
):
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
        headers=[(b"x-hub-signature-256", _sign(secret, body).encode())],
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
