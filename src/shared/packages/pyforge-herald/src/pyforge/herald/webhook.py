"""HMAC-verified webhook handlers for CI-triggered Progress/Claim creation
(Story 13.4, closing Epic 13's LB-2).

**CI system and events (this story's first, load-bearing AC).** GitHub
Actions -- the repo's only CI system. ``on-ship`` fires from a workflow
step run after a successful push to ``main`` (mirrors this repo's own
``dashboard.yml``/``detectors.yml`` "push to main = ship happened"
convention, not GitHub's native ``pull_request closed+merged`` event,
which no existing workflow here uses). ``on-pr-close`` fires from a
``pull_request: types: [closed]`` step; this module never trusts the HTTP
event alone -- ``handle_on_pr_close`` gates on the payload's own
``merged``/``gates_passed`` booleans. Writing the actual
``.github/workflows/*.yml`` step, mounting this module into a live ASGI
host, and wiring Steward's identity/trust boundary around it are all
Story 13.6's job -- this module is built and fully tested in isolation.

**Shape: sync core + one ASGI3 boundary.** Mirrors
``transport/mcp_transport.py``'s "one ``asyncio.run()`` per call"
precedent, inverted for the server side: ``verify_signature``/
``handle_on_ship``/``handle_on_pr_close`` are plain sync functions with
zero framework coupling, directly testable with the same ``tmp_path``
pattern ``test_progress.py``/``test_claims.py`` already use. Only
``create_app``'s returned ``app(scope, receive, send)`` is ``async def`` --
a raw ASGI3 callable, hand-tested with a constructed ``scope``/``receive``/
``send`` triple, no new ``pytest-asyncio``/``anyio``/httpx dependency.
This is also the literal shape AD-9 of Steward's
``spec-secure-live-dashboards`` architecture requires of a machine caller:
"the library binds at the ASGI application boundary ... no adopter may be
asked to change frameworks to adopt" -- Herald never imports Django,
Channels, or any web framework; whatever ASGI host Story 13.6 chooses
mounts this callable directly. ``app`` calls the matched sync handler via
``asyncio.to_thread`` rather than directly: ``_retry_with_backoff``'s
default ``sleep`` is the real, blocking ``time.sleep``, and calling the
handler straight on the event-loop thread would let up to ~3s of retry
backoff block the ENTIRE ASGI worker -- every other in-flight request --
not just the one call that happens to be retrying.

**HMAC, not ingress.** AD-9 ("machine callers authenticate by proof, not
by ingress"): a caller presents a verifiable HMAC-SHA256 signature over the
raw request body in an ``X-Hub-Signature-256: sha256=<hex>`` header (our
own convention for our own POST, not a GitHub platform requirement) and is
authenticated by that proof, never by source address or a bespoke API key.
``secret`` is resolved once by the caller (``resolve_webhook_secret``, read
from ``HERALD_WEBHOOK_SECRET`` -- never a literal or default fallback) and
handed to ``create_app`` at construction; this module never re-reads the
environment per request, and never imports ``pyforge-steward`` for secret
resolution (its ``keys`` module is provisioning/rotation-shaped, not a
runtime secret-fetch accessor).

**Retry + idempotency.** ``_retry_with_backoff`` retries the storage call
only (never HMAC verification or payload validation) up to
``RETRY_ATTEMPTS`` times on any ``errors.HeraldError``, sleeping
``RETRY_BACKOFFS[i]`` between attempt ``i+1`` and ``i+2`` (the injectable
``sleep``, default ``time.sleep``, is why a test never actually blocks).
``handle_on_pr_close`` pre-generates the claim id ONCE, before the retry
loop, and each attempt first checks whether a claim with that id already
exists (``claims.read_one``) before calling ``claims.create`` again --
so a retry after a would-be-successful first attempt is provably
idempotent (either the first attempt truly failed and this attempt
creates the one real row, or the first attempt actually committed and
this attempt finds it and returns it unchanged) rather than risking a
second, duplicate draft claim for one CI event. ``claims.id`` carries no
schema-level uniqueness (Story 13.3's deliberate choice), so nothing
downstream of ``claims.create`` itself would catch that duplicate.
``handle_on_ship`` needs no matching trick: ``progress.upsert``'s own
``(station, date)`` key already makes a same-day re-invocation an in-place
replace, not a second record.

That guard only covers retries WITHIN one call, though -- a genuine CI
webhook redelivery (a second, independent HTTP POST for the same logical
PR-merge event, which the "Alerting" paragraph below explicitly invites via
a non-2xx response) is a fresh top-level call with its own fresh
``uuid.uuid4()`` id, and would sail straight past the ``read_one`` guard
into a second ``claims.create``. So the claim id is instead derived
DETERMINISTICALLY (``_claim_id_for``: ``uuid.uuid5`` over ``project_name``
and ``shipped_date``, falling back to today's UTC date when the payload
omits it) -- a genuine redelivery of the same logical event computes the
SAME id, and the existing idempotency guard catches it across the HTTP
boundary too, not just across one call's own retry loop.

**Alerting.** No email/Slack/other operator-alert channel exists anywhere
in this repo to build against, so retries-exhausted is reported the one
way this codebase already has: one structured (JSON) ``ERROR``-level log
record via the stdlib ``logging`` module, plus a non-2xx HTTP response so
CI's own webhook-delivery retry can re-fire the call later.

**Body size cap.** ``_read_body`` enforces ``MAX_BODY_BYTES`` and aborts
early once the accumulated body exceeds it -- checked BEFORE
``verify_signature`` runs, because the signature check has nothing to
check until the whole body is read: without this cap, an unauthenticated
caller (anyone who can reach the route, no secret required) could force
unbounded memory buffering just by streaming an oversized body. A
too-large request gets a 413, before HMAC verification or JSON parsing
ever run.

**Uncaught exceptions.** ``app()`` wraps the body-read-through-response-
send flow in a broad exception guard. A well-behaved ASGI application must
always send a response (or handle disconnection) rather than let an
exception propagate uncaught, which would hang whatever host mounts this
callable; everything on that path other than the deliberately-handled
cases (``_BodyTooLarge``, a malformed-JSON ``json.loads``, and each
handler's own internal ``errors.HeraldError`` handling) is by definition a
bug this module did not anticipate, and gets a logged 500 instead of an
uncaught propagation.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import math
import os
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from . import claims, errors, progress

logger = logging.getLogger(__name__)

ON_SHIP_PATH = "/api/herald/webhooks/on-ship"
ON_PR_CLOSE_PATH = "/api/herald/webhooks/on-pr-close"
"""The two routes ``epics.md``'s Story 13.4 AC names literally. Exported so
Story 13.6's ASGI host wiring (out of this story's Surface) has one place
to import them from rather than re-typing the literals."""

SECRET_ENV_VAR = "HERALD_WEBHOOK_SECRET"
_SIGNATURE_HEADER = "x-hub-signature-256"
_SIGNATURE_PREFIX = "sha256="

MAX_BODY_BYTES = 1_000_000
"""Upper bound on a webhook request body (see the module docstring's "Body
size cap" section) -- generous for this payload shape, small JSON with at
most a handful of evidence entries."""

RETRY_ATTEMPTS = 3
RETRY_BACKOFFS: tuple[float, ...] = (1.0, 2.0, 4.0)
"""Boundaries & Constraints: "max 3 attempts, 1s/2s/4s backoff". Only the
first two entries are ever actually slept on -- there is no sleep after the
LAST attempt of a 3-attempt budget -- the third entry documents where the
schedule would continue if ``RETRY_ATTEMPTS`` ever grew."""

_EVIDENCE_FIELDS = frozenset(("type", "url", "label"))

_T = TypeVar("_T")

Scope = Mapping[str, Any]
Receive = Callable[[], Awaitable[Mapping[str, Any]]]
Send = Callable[[Mapping[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


@dataclass(frozen=True)
class WebhookResponse:
    """One handler's answer -- an HTTP status plus a JSON-serializable
    body -- kept separate from the ASGI wire format so ``handle_on_ship``/
    ``handle_on_pr_close`` stay plain, directly-assertable sync functions."""

    status: int
    body: Mapping[str, Any]


# --- HMAC verification (AD-9) ------------------------------------------------


def verify_signature(secret: bytes, body: bytes, signature_header: str | None) -> bool:
    """Whether ``signature_header`` (an ``X-Hub-Signature-256: sha256=<hex>``
    value) proves ``body`` was sent by a holder of ``secret``.

    ``hmac.compare_digest`` -- constant-time, so a mismatch cannot be timed
    to guess the secret byte by byte. A missing header, or one not shaped
    ``sha256=<hex>``, is simply not proof -- returns ``False`` rather than
    raising, so the ASGI boundary has one uniform "was this call proven?"
    answer to act on."""
    if signature_header is None or not signature_header.startswith(_SIGNATURE_PREFIX):
        return False
    provided = signature_header[len(_SIGNATURE_PREFIX) :]
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided)


def resolve_webhook_secret(env: Mapping[str, str] | None = None) -> bytes:
    """The shared HMAC secret, read from ``HERALD_WEBHOOK_SECRET`` -- never
    a literal or a default fallback (Boundaries & Constraints). Read ONCE,
    at ``create_app`` construction time (by whatever caller resolves it --
    Story 13.6's ASGI host wiring), never per request.

    ``env`` defaults to ``os.environ`` and is injectable, mirroring
    ``transport.mcp_transport.resolve_design_credential``'s same
    injectable-env shape so a test never touches the real process
    environment. Raises ``errors.HeraldError`` naming the env var when it
    is unset or empty -- ``create_app`` must never be handed a blank
    secret, which would make ``verify_signature`` accept a forged
    ``X-Hub-Signature-256: sha256=<hmac of empty secret>`` header."""
    source = os.environ if env is None else env
    value = source.get(SECRET_ENV_VAR)
    if not value:
        raise errors.HeraldError(
            f"{SECRET_ENV_VAR} is not set -- the webhook cannot verify HMAC "
            f"signatures without a shared secret"
        )
    return value.encode("utf-8")


# --- retry/backoff (storage call only) ---------------------------------------


def _retry_with_backoff(
    attempt: Callable[[], _T],
    *,
    attempts: int = RETRY_ATTEMPTS,
    backoffs: Sequence[float] = RETRY_BACKOFFS,
    sleep: Callable[[float], None] = time.sleep,
) -> _T:
    """Call ``attempt()`` up to ``attempts`` times, retrying only on
    ``errors.HeraldError`` -- payload validation and HMAC verification
    never reach this helper, only the storage call itself does. Sleeps
    ``backoffs[i]`` between attempt ``i+1`` and ``i+2`` (never after the
    final attempt). Re-raises the last ``HeraldError`` once the budget is
    exhausted, for the caller to translate into the alert log + 500."""
    last_error: errors.HeraldError | None = None
    for index in range(attempts):
        try:
            return attempt()
        except errors.HeraldError as exc:
            last_error = exc
            if index < attempts - 1:
                sleep(backoffs[index])
    assert last_error is not None  # attempts >= 1 in every real call
    raise last_error


def _log_retry_exhausted(event: str, payload: Mapping[str, Any], exc: BaseException) -> None:
    """The sole operator-alert mechanism (Boundaries & Constraints): one
    structured JSON ERROR-level log record -- event type, payload summary,
    exception -- since no email/Slack/other channel exists in this repo to
    build against."""
    logger.error(
        json.dumps(
            {
                "event": "herald.webhook.retries_exhausted",
                "webhook": event,
                "payload": dict(payload),
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    )


def _log_unexpected_exception(event: str, exc: BaseException) -> None:
    """The sibling of ``_log_retry_exhausted`` for ``app()``'s own
    last-resort exception guard (see the module docstring's "Uncaught
    exceptions" section) -- one structured JSON ``ERROR``-level log record
    for a failure this module did not anticipate, since no email/Slack/
    other alert channel exists here to build against."""
    logger.error(
        json.dumps(
            {
                "event": "herald.webhook.unexpected_exception",
                "webhook": event,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    )


# --- on-ship -----------------------------------------------------------------


def _problem_on_ship(payload: object) -> str | None:
    """Structural validation only -- required fields present, correct JSON
    types -- maps to 400 (Boundaries & Constraints). A business-rule
    rejection (e.g. a negative ``compute_hours``) is deliberately NOT
    checked here: that is ``progress.upsert``'s own job, and its
    ``HeraldError`` is eligible for retry/500 like any other storage
    failure, never a fast 400."""
    if not isinstance(payload, Mapping):
        return "payload is not a JSON object"
    if "station" not in payload:
        return "field 'station' is required"
    if not isinstance(payload["station"], str):
        return "field 'station' must be a string"
    if "shipped_capabilities" in payload:
        caps = payload["shipped_capabilities"]
        if not isinstance(caps, list) or not all(isinstance(c, str) for c in caps):
            return "field 'shipped_capabilities' must be an array of strings"
    if "compute_hours" in payload:
        value = payload["compute_hours"]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return "field 'compute_hours' must be a number"
        # `json.loads` accepts the non-standard NaN/Infinity/-Infinity
        # literals, and `progress.upsert`'s own `value < 0` guard is
        # `False` for NaN (NaN comparisons are always False) -- neither
        # layer otherwise rejects one, so a non-finite value would be
        # silently stored and could break downstream numeric aggregation.
        if not math.isfinite(value):
            return "field 'compute_hours' must be a finite number"
    if "token_spend" in payload:
        value = payload["token_spend"]
        if not isinstance(value, int) or isinstance(value, bool):
            return "field 'token_spend' must be an integer"
        # No `math.isfinite` check needed here: `token_spend` is `int`-only
        # (checked above), and a Python `int` can never be NaN/Infinity.
    if "wall_clock_hours" in payload:
        value = payload["wall_clock_hours"]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return "field 'wall_clock_hours' must be a number"
        if not math.isfinite(value):
            return "field 'wall_clock_hours' must be a finite number"
    if "unblock_narrative" in payload and not isinstance(payload["unblock_narrative"], str):
        return "field 'unblock_narrative' must be a string"
    return None


def handle_on_ship(
    repo_root: Path,
    payload: object,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> WebhookResponse:
    """``on-ship``: create/replace today's Progress record for the
    payload's station -- the exact ``progress.upsert`` call
    ``herald progress <station> --update`` makes, with the same flag
    defaults (``[]``/``0.0``/``0``/``0.0``/``""``) and a server-computed
    ``date`` (never caller-supplied, mirroring ``cli._run_progress_update``
    exactly)."""
    problem = _problem_on_ship(payload)
    if problem is not None:
        return WebhookResponse(400, {"error": problem})
    assert isinstance(payload, Mapping)
    progress_path = repo_root / progress.DEFAULT_PROGRESS_PATH
    on_date = datetime.now(UTC).date().isoformat()

    def attempt() -> progress.Progress:
        return progress.upsert(
            progress_path,
            station=payload["station"],
            date=on_date,
            shipped_capabilities=list(payload.get("shipped_capabilities", [])),
            compute_hours=payload.get("compute_hours", 0.0),
            token_spend=payload.get("token_spend", 0),
            wall_clock_hours=payload.get("wall_clock_hours", 0.0),
            unblock_narrative=payload.get("unblock_narrative", ""),
        )

    try:
        record = _retry_with_backoff(attempt, sleep=sleep)
    except errors.HeraldError as exc:
        _log_retry_exhausted("on-ship", payload, exc)
        return WebhookResponse(500, {"error": "storage failure"})
    return WebhookResponse(201, {"station": record.station, "date": record.date})


# --- on-pr-close ---------------------------------------------------------------


def _problem_on_pr_close_gate(payload: object) -> str | None:
    """Structural validation of the two gating fields only -- required,
    and must actually be JSON booleans (a string ``"true"`` is not a
    boolean and must not silently pass the gate below)."""
    if not isinstance(payload, Mapping):
        return "payload is not a JSON object"
    for field in ("merged", "gates_passed"):
        if field not in payload:
            return f"field {field!r} is required"
        if not isinstance(payload[field], bool):
            return f"field {field!r} must be a boolean"
    return None


def _problem_on_pr_close_shipped(payload: Mapping[str, Any]) -> str | None:
    """Structural validation of the fields only needed once the gate
    passes and a Claim is actually about to be created -- never run for a
    not-shipped (202, no-op) payload, which may omit all of these.

    Checks each evidence entry's ``type`` against the real
    ``claims.EVIDENCE_TYPES`` enum (matching ``_problem_on_ship``'s own
    rigor for its fields), and rejects a blank/whitespace-only
    ``project_name`` -- both cheaply and deterministically checkable here,
    rather than sailing past this 400 straight into ``claims.create``'s own
    validation and wasting a full retry-then-500 on something this
    function could catch up front."""
    if "project_name" not in payload:
        return "field 'project_name' is required"
    if not isinstance(payload["project_name"], str):
        return "field 'project_name' must be a string"
    if not payload["project_name"].strip():
        return "field 'project_name' must not be blank"
    if payload.get("shipped_date") is not None and not isinstance(
        payload["shipped_date"], str
    ):
        return "field 'shipped_date' must be a string"
    if "evidence" in payload:
        entries = payload["evidence"]
        if not isinstance(entries, list):
            return "field 'evidence' must be an array"
        for entry in entries:
            if not isinstance(entry, Mapping):
                return "each 'evidence' entry must be a JSON object"
            missing = _EVIDENCE_FIELDS - set(entry)
            if missing:
                return f"each 'evidence' entry is missing field(s) {sorted(missing)}"
            if not all(isinstance(entry[key], str) for key in _EVIDENCE_FIELDS):
                return "each 'evidence' entry's type/url/label must be strings"
            if entry["type"] not in claims.EVIDENCE_TYPES:
                return (
                    f"each 'evidence' entry's type must be one of "
                    f"{claims.EVIDENCE_TYPES}; got {entry['type']!r}"
                )
    return None


def _claim_id_for(project_name: str, shipped_date: str | None) -> str:
    """A deterministic claim id for one logical CI shipped-PR event --
    ``uuid.uuid5`` over ``project_name`` plus ``shipped_date`` (or today's
    UTC date when the payload omits it), rather than ``uuid.uuid4()`` (see
    the module docstring's "Retry + idempotency" section). A genuine CI
    webhook redelivery of the SAME event is a second, independent HTTP
    call -- a random id per call would defeat ``handle_on_pr_close``'s
    ``read_one``-before-``create`` idempotency guard across that boundary
    and create a second, duplicate draft claim; a deterministic id makes
    the redelivery compute the SAME id, so the very same guard catches it
    too."""
    date_component = (
        shipped_date if shipped_date is not None else datetime.now(UTC).date().isoformat()
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"herald-claim:{project_name}|{date_component}"))


def handle_on_pr_close(
    repo_root: Path,
    payload: object,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> WebhookResponse:
    """``on-pr-close``: create a draft Claim -- the exact ``claims.create``
    call ``herald success create <project>`` makes -- only when the
    payload's own ``merged`` AND ``gates_passed`` are both ``true``. Any
    other combination is an explicit no-op, 202, never an error (Boundaries
    & Constraints) -- the handler never trusts the HTTP event (a
    ``pull_request: closed`` step fires on every close, merged or not) over
    the payload's own booleans.

    ``project_name`` is read verbatim from the payload -- this handler
    never parses a PR title or any GitHub-specific shape to infer it
    (Boundaries & Constraints); ``evidence`` entries, if present, are
    passed through as already-shaped ``{type, url, label}`` objects."""
    gate_problem = _problem_on_pr_close_gate(payload)
    if gate_problem is not None:
        return WebhookResponse(400, {"error": gate_problem})
    assert isinstance(payload, Mapping)
    if not (payload["merged"] and payload["gates_passed"]):
        return WebhookResponse(202, {"status": "not-shipped"})

    shipped_problem = _problem_on_pr_close_shipped(payload)
    if shipped_problem is not None:
        return WebhookResponse(400, {"error": shipped_problem})

    claims_path = repo_root / claims.DEFAULT_CLAIMS_PATH
    # Generated ONCE, before the retry loop, and DETERMINISTICALLY (see
    # `_claim_id_for` and the module docstring's "Retry + idempotency"
    # section) -- a genuine redelivery of this same logical event, arriving
    # as a separate top-level call, computes this same id.
    claim_id = _claim_id_for(payload["project_name"], payload.get("shipped_date"))
    evidence = tuple(
        claims.Evidence(type=e["type"], url=e["url"], label=e["label"])
        for e in payload.get("evidence", [])
    )

    def attempt() -> claims.Claim:
        # Idempotency guard: if a prior attempt actually committed before
        # raising, this finds it and returns it unchanged instead of
        # calling `create` a second time with the same id -- `claims.id`
        # carries no schema-level uniqueness (see module docstring).
        try:
            return claims.read_one(claims_path, claim_id)
        except errors.ClaimNotFoundError:
            pass
        return claims.create(
            claims_path,
            project_name=payload["project_name"],
            shipped_date=payload.get("shipped_date"),
            evidence=evidence,
            id_factory=lambda: claim_id,
        )

    try:
        claim = _retry_with_backoff(attempt, sleep=sleep)
    except errors.HeraldError as exc:
        _log_retry_exhausted("on-pr-close", payload, exc)
        return WebhookResponse(500, {"error": "storage failure"})
    return WebhookResponse(
        201, {"claim_id": claim.id, "project_name": claim.project_name}
    )


# --- the ASGI3 boundary (AD-8: "protocol, not framework") --------------------


class _BodyTooLarge(Exception):
    """Raised by ``_read_body`` once the accumulated body exceeds
    ``MAX_BODY_BYTES`` -- caught by ``app()`` and turned into a 413
    response BEFORE the body is ever handed to ``verify_signature`` (see
    the module docstring's "Body size cap" section)."""


async def _read_body(receive: Receive) -> bytes:
    """Drain every ``http.request`` message until ``more_body`` is falsy --
    the ASGI3 contract for a (possibly chunked) request body. Raises
    ``_BodyTooLarge`` once the accumulated size exceeds ``MAX_BODY_BYTES``,
    checked on every chunk so a caller cannot stream past the cap one
    ``more_body: true`` message at a time."""
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        if len(body) > MAX_BODY_BYTES:
            raise _BodyTooLarge(f"request body exceeds {MAX_BODY_BYTES} bytes")
        more_body = message.get("more_body", False)
    return body


def _header_value(scope: Scope, name: str) -> str | None:
    """The first ``scope["headers"]`` entry matching ``name``
    (case-insensitive -- ASGI servers lowercase header names, but a
    hand-constructed test scope should not have to)."""
    for key, value in scope.get("headers", ()):
        if key.decode("latin-1").lower() == name:
            return value.decode("latin-1")
    return None


async def _send_json(send: Send, status: int, body: Mapping[str, Any]) -> None:
    payload = json.dumps(body).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": payload})


def create_app(repo_root: Path, secret: bytes) -> ASGIApp:
    """Build the ASGI3 callable AD-8 requires: a plain
    ``async def app(scope, receive, send)`` with zero framework
    dependency, mountable inside whatever ASGI host Story 13.6 chooses.
    ``secret`` is already-resolved bytes (see ``resolve_webhook_secret``) --
    this factory never itself reads the environment, so constructing it
    twice never re-reads ``HERALD_WEBHOOK_SECRET``.

    Refuses a falsy/empty ``secret`` (``errors.HeraldError``) before ever
    returning ``app``: ``resolve_webhook_secret`` already guards against a
    blank env var, but that guard is opt-in -- a caller who resolves
    ``secret`` some other way would otherwise silently get an ``app`` whose
    ``verify_signature`` accepts ANY signature (an HMAC of an empty key is
    still a valid HMAC), exactly the forgery the module docstring's "HMAC,
    not ingress" section warns about.

    Route/method/signature/body-shape checks run in the I/O matrix's own
    order: unknown path -> 404, wrong method on a known path -> 405 (both
    before the body is read at all); then the body is read (-> 413 if it
    exceeds ``MAX_BODY_BYTES``) and the HMAC is checked against it -> 401
    (before the body is parsed as JSON); then JSON parsing -> 400 on
    failure; only then does the matched handler run (which does its own
    further structural validation -> 400, or the real storage work ->
    201/202/500). Any other exception on that path is a 500 (see the
    module docstring's "Uncaught exceptions" section)."""
    if not secret:
        raise errors.HeraldError(
            "create_app was given a blank webhook secret -- verify_signature "
            "would accept a forged signature computed from an empty key; "
            "resolve a real secret (e.g. via resolve_webhook_secret) before "
            "calling create_app"
        )

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            return  # e.g. an ASGI "lifespan" scope -- nothing for a leaf app to do
        path = scope.get("path")
        if path == ON_SHIP_PATH:
            handler: Callable[..., WebhookResponse] = handle_on_ship
            event_name = "on-ship"
        elif path == ON_PR_CLOSE_PATH:
            handler = handle_on_pr_close
            event_name = "on-pr-close"
        else:
            await _send_json(send, 404, {"error": f"no such webhook route: {path!r}"})
            return
        if scope.get("method") != "POST":
            await _send_json(send, 405, {"error": "method not allowed; use POST"})
            return

        # Everything from here through the final response send is wrapped
        # in a broad exception guard -- see the module docstring's
        # "Uncaught exceptions" section: an ASGI app must always answer,
        # never let a bug hang whatever host mounts this callable.
        try:
            body = await _read_body(receive)
            signature = _header_value(scope, _SIGNATURE_HEADER)
            if not verify_signature(secret, body, signature):
                await _send_json(
                    send, 401, {"error": "invalid or missing HMAC signature"}
                )
                return

            try:
                payload = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                await _send_json(send, 400, {"error": "malformed JSON payload"})
                return

            # Off the event-loop thread: `_retry_with_backoff`'s default
            # `sleep` is the real, blocking `time.sleep`, and calling the
            # handler directly here would block every other in-flight
            # request for up to ~3s during any retry (see the module
            # docstring's "Shape" section).
            result = await asyncio.to_thread(handler, repo_root, payload)
            await _send_json(send, result.status, result.body)
        except _BodyTooLarge:
            await _send_json(
                send, 413, {"error": f"request body exceeds {MAX_BODY_BYTES} bytes"}
            )
        except Exception as exc:  # noqa: BLE001 -- last-resort ASGI contract guard
            _log_unexpected_exception(event_name, exc)
            await _send_json(send, 500, {"error": "internal error"})

    return app
