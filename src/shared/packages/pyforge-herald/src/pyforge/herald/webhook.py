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
``merged``/``gates_passed`` booleans. Note that a per-push ``on-ship``
needs the producer to send the day's CUMULATIVE figures on every
delivery, because a same-day second delivery replaces rather than merges
-- see "Same-day ``on-ship`` deliveries REPLACE" below before wiring the
step. Writing the actual ``.github/workflows/*.yml`` step and mounting this
module into a live ASGI host were Story 13.6's job -- done: ``webhook_host.py``
mounts this callable behind ``daphne``, and
``.github/workflows/herald-live-demo.yml`` drives it as a bounded,
CI-contained demonstration (never a persistent, publicly-reachable
deployment -- that stays out of Surface; see this repo's deferred-work
ledger for the tracked gap in Steward's own perimeter tooling). This
module itself is still built and fully tested in isolation, independent of
that host.

**What holding the secret buys.** The CLI's own ``herald progress
--update`` runs behind ``auth.require_operator_role`` (AD-16); this
module deliberately does not, because AD-9's whole point is that a
machine caller authenticates by PROOF rather than by an operator
identity it does not have, and the HMAC signature is that proof. The
consequence is worth stating plainly for whoever mounts this: anything
holding ``HERALD_WEBHOOK_SECRET`` gets progress-write access the CLI
grants only to a verified operator. Scope that secret accordingly --
it is a privilege boundary, not just a spam filter.

**Shape: sync core + one ASGI3 boundary.** Mirrors
``transport/mcp_transport.py``'s "one ``asyncio.run()`` per call"
precedent, inverted for the server side: ``verify_signature``/
``handle_on_ship``/``handle_on_pr_close`` are plain sync functions with
zero framework coupling, directly testable with the same ``tmp_path``
pattern ``test_progress.py``/``test_claims.py`` already use. Only
``create_app``'s returned ``app(scope, receive, send)`` is ``async def`` --
a raw ASGI3 callable, hand-tested with a constructed ``scope``/``receive``/
``send`` triple, no new ``pytest-asyncio``/``anyio``/httpx dependency.
This is also the literal shape AD-8 of Steward's
``spec-secure-live-dashboards`` architecture requires: "the library binds
at the ASGI application boundary ... no adopter may be asked to change
frameworks to adopt" -- Herald never imports Django, Channels, or any web
framework; whatever ASGI host Story 13.6 chooses mounts this callable
directly, alongside Steward's own S-9.1 dashboard middleware, which is a
framework-free raw ASGI3 callable for the same reason. ``app`` calls the
matched sync handler via ``asyncio.to_thread`` rather than directly:
``_retry_with_backoff``'s default ``sleep`` is the real, blocking
``time.sleep``, and calling the handler straight on the event-loop thread
would block the ENTIRE ASGI worker -- every other in-flight request -- not
just the one call that happens to be retrying. Note for whoever mounts
this (Story 13.6): the thread hop bounds the damage, it does not bound the
duration. One call sleeps up to 3s of retry backoff, but each of its 3
attempts can additionally block on SQLite's write lock for up to
``db._BUSY_TIMEOUT_MS`` (30s), so a contended request can occupy its
worker for well over a minute. A request timeout and a bounded executor
belong with the host wiring, not here.

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
DETERMINISTICALLY, by ``_claim_id_for``, from what identifies the event:
the project plus either the payload's own ``event_id`` (the precise
answer, and what Story 13.6's workflow step should send) or, failing
that, the shipped date and the ``evidence`` list. A genuine redelivery of
the same logical event computes the SAME id, and the existing idempotency
guard catches it across the HTTP boundary too -- while two DIFFERENT
ships for one project on one day still compute two ids, which keying on
project+date alone did not, silently swallowing the second ship behind a
``201``.

**Same-day ``on-ship`` deliveries REPLACE, they do not merge.**
``handle_on_ship`` mirrors ``cli._run_progress_update`` exactly, as
Boundaries & Constraints requires -- including its flag defaults -- and
``progress.upsert``'s ``(station, date)`` key makes a second delivery for
one station on one day an in-place replace. So a second delivery that
OMITS a field resets that field to its default rather than preserving
what the first delivery recorded. That is the specified behavior, not an
oversight, but it makes the payload the whole truth for the day: whoever
wires the workflow step (Story 13.6) must send the day's cumulative
figures on every delivery, or fire ``on-ship`` once per day rather than
once per push. The same replace applies across sources, not just across
deliveries -- one ``on-ship`` call also overwrites whatever an operator
entered by hand with ``herald progress <station> --update`` that day.
Relatedly, and for the same "the payload is the whole truth" reason,
BOTH routes reject unknown payload fields outright (400) instead of
ignoring them: a mistyped ``token_spends`` that answered ``201`` would
not merely fail to record a figure, it would wipe the one already there.

**Alerting.** No email/Slack/other operator-alert channel exists anywhere
in this repo to build against, so retries-exhausted is reported the one
way this codebase already has: one structured (JSON) ``ERROR``-level log
record via the stdlib ``logging`` module, plus a non-2xx HTTP response so
CI's own webhook-delivery retry can re-fire the call later. Because that
log IS the alert channel, everything caller-controlled that reaches it is
bounded: the payload it embeds is capped at
``_MAX_ALERT_PAYLOAD_CHARS``, so no one delivery can flood it.

**Body size cap.** ``_read_body`` enforces ``MAX_BODY_BYTES`` and aborts
early once the accumulated body exceeds it -- checked BEFORE
``verify_signature`` runs, because the signature check has nothing to
check until the whole body is read: without this cap, an unauthenticated
caller (anyone who can reach the route, no secret required) could force
unbounded memory buffering just by streaming an oversized body. It
enforces ``MAX_BODY_MESSAGES`` alongside it, because a byte cap alone
does not bound a stream of ZERO-length chunks -- those never advance the
byte counter, so the request would never end. A request that exceeds
either cap gets a 413, before HMAC verification or JSON parsing ever run.

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
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, TypeVar

from pyforge.core.errors import PyforgeError

from . import claims, errors, notices, progress

logger = logging.getLogger(__name__)

ON_SHIP_PATH = "/stations/herald/api/v1/webhooks/on-ship"
ON_PR_CLOSE_PATH = "/stations/herald/api/v1/webhooks/on-pr-close"
"""The two routes ``epics.md``'s Story 13.4 AC names literally. Exported so
Story 13.6's ASGI host wiring (out of this story's Surface) has one place
to import them from rather than re-typing the literals."""

SECRET_ENV_VAR = "HERALD_WEBHOOK_SECRET"
_SIGNATURE_HEADER = "x-hub-signature-256"
_SIGNATURE_PREFIX = "sha256="
_SIGNATURE_HEX_LEN = hashlib.sha256().digest_size * 2
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")

_TIMESTAMP_HEADER = "x-hub-timestamp"
_TIMESTAMP_DIGITS = frozenset("0123456789")
_MAX_TIMESTAMP_HEADER_LEN = 16
"""Generous upper bound on ``X-Hub-Timestamp``'s digit count -- unix seconds
today is 10 digits and will not reach 16 within any realistic operating
lifetime of this module, even counting milliseconds by mistake. Checked
BEFORE ``int(timestamp_header)`` ever runs, the same "bound the caller's own
input before it reaches conversion/arithmetic" discipline
``_SIGNATURE_HEX_LEN``'s shape check already applies to the signature half:
CPython's own string-to-int conversion has a documented complexity blowup
for very long digit strings (``sys.set_int_max_str_digits`` exists for
exactly this), so this module does not rely on that global default alone."""

MAX_TIMESTAMP_SKEW_SECONDS = 300
"""Boundaries & Constraints (closing DW-FU-13-4): the largest age an
``X-Hub-Timestamp`` may carry, in EITHER direction, and still be accepted --
5 minutes. Symmetric, not "reject only if older than 5 minutes": a
one-directional check would leave a request whose timestamp was ever set (by
producer clock skew, or a bug) into the FUTURE valid forever, until the
server's own clock caught up to it -- exactly the forever-valid-replay-token
failure this window exists to close (see ``verify_signature``'s docstring)."""

MAX_BODY_BYTES = 1_000_000
"""Upper bound on a webhook request body (see the module docstring's "Body
size cap" section) -- generous for this payload shape, small JSON with at
most a handful of evidence entries."""

MAX_BODY_MESSAGES = 10_000
"""Upper bound on the number of ASGI ``http.request`` messages one body may
arrive in. ``MAX_BODY_BYTES`` alone does not bound the read: a stream of
ZERO-length chunks (legal -- an HTTP/2 empty ``DATA`` frame without
``END_STREAM`` forwards as one, and ~160 fit in a single packet) adds
nothing to the byte counter, so the cap can never fire, the loop never
terminates, and the chunk list grows one slot per message forever. Measured
before this bound: 3,000,001 empty chunks drained in 0.6s and never tripped
``MAX_BODY_BYTES``, with the request still unfinished. Like the byte cap
this is enforced BEFORE ``verify_signature``, so an UNAUTHENTICATED caller
cannot hold a request open indefinitely."""

_MAX_ALERT_PAYLOAD_CHARS = 2_000
"""Cap on the serialized ``payload`` inside one retries-exhausted alert
record. The record is this module's ONLY operator-alert channel, and the
payload is caller-controlled up to ``MAX_BODY_BYTES`` -- embedding it whole
let one signed 1 MB delivery write a ~1 MB log line per exhausted delivery
(measured: a 200 KB field produced a 200,141-byte record), and the module's
own contract then invites CI to re-fire it. That drowns the real alerts
exactly the way ``verify_signature``'s and ``create_app``'s docstrings each
argue their own guards exist to prevent."""

RETRY_ATTEMPTS = 3
RETRY_BACKOFFS: tuple[float, ...] = (1.0, 2.0, 4.0)
"""Boundaries & Constraints: "max 3 attempts, 1s/2s/4s backoff". Only the
first two entries are ever actually slept on -- there is no sleep after the
LAST attempt of a 3-attempt budget -- the third entry documents where the
schedule would continue if ``RETRY_ATTEMPTS`` ever grew."""

_EVIDENCE_FIELDS = frozenset(("type", "url", "label"))

_ON_SHIP_FIELDS = frozenset(
    (
        "station",
        "shipped_capabilities",
        "compute_hours",
        "token_spend",
        "wall_clock_hours",
        "unblock_narrative",
    )
)
_ON_PR_CLOSE_FIELDS = frozenset(("merged", "gates_passed", "project_name", "shipped_date", "event_id", "evidence"))
"""The complete field set each route accepts. Anything else is a 400 --
see ``_problem_unknown_fields``."""

_MIN_SQLITE_INT = -(2**63)
_MAX_SQLITE_INT = 2**63 - 1
"""SQLite's signed-64-bit ``INTEGER`` range. An ``int`` outside it raises
``OverflowError`` at bind time -- not a ``HeraldError``, so it would escape
the retry helper and surface as an opaque 500 instead of the 400 it is."""

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


def verify_signature(
    secret: bytes,
    body: bytes,
    signature_header: str | None,
    timestamp_header: str | None,
) -> bool:
    """Whether ``signature_header`` (an ``X-Hub-Signature-256: sha256=<hex>``
    value) -- together with ``timestamp_header`` (an ``X-Hub-Timestamp:
    <unix-seconds>`` value) -- proves ``body`` was sent, recently, by a
    holder of ``secret``.

    ``hmac.compare_digest`` -- constant-time, so a mismatch cannot be timed
    to guess the secret byte by byte. A missing header, or one not shaped
    ``sha256=<hex>``, is simply not proof -- returns ``False`` rather than
    raising, so the ASGI boundary has one uniform "was this call proven?"
    answer to act on.

    The ``<hex>`` half is case-folded before comparison: ``hexdigest()``
    is lowercase, so an otherwise-correct signature from a producer that
    renders hex uppercase (Go's ``%X``, Java's ``String.format("%02X")``,
    PowerShell's ``[BitConverter]::ToString``) would fail with a bare 401
    and send whoever writes Story 13.6's producer hunting a secret
    mismatch that never happened. ``_HEX_DIGITS`` already admits uppercase
    through the shape gate, so accepting it here is what that set implies;
    the fold runs on the caller's own input only, so it is not
    secret-dependent and does not affect ``compare_digest``'s
    constant-time property.

    The ``<hex>`` half is shape-checked (exactly ``_SIGNATURE_HEX_LEN``
    hex digits) BEFORE ``compare_digest`` sees it, because
    ``compare_digest`` on two ``str``s RAISES ``TypeError`` for a
    non-ASCII character rather than returning ``False`` -- and the header
    is attacker-controlled (``_header_value`` decodes it ``latin-1``, so
    any byte can reach here). Without this check an unauthenticated caller
    sending ``sha256=<non-ASCII>`` turned its own 401 into a 500 plus one
    ERROR log record per request -- and ERROR logging is this module's
    ONLY operator-alert channel, so that is a way to drown the real
    ``retries_exhausted`` alerts without knowing the secret. The check
    inspects only the caller's own input, never the expected digest, so it
    leaks nothing about ``secret``.

    **The timestamp is folded INTO the signed content, narrowing
    DW-FU-13-4 from a forever-valid forgery token to a <=5-minute replay
    window.** Before Story 13.6, the HMAC covered ``body`` alone, so one
    captured signed request was a forever-valid forgery token: neither
    handler is a pure function of the signed bytes
    (``handle_on_ship``/``handle_on_pr_close`` both compute a server-side
    date whenever the payload omits one), so replaying a stale capture on a
    later day created a fresh record carrying the earlier day's numbers
    under the later day's date. ``timestamp_header`` is signed alongside
    ``body`` (``timestamp_header.encode() + b"." + body`` -- the same
    "signed timestamp prefix" shape Stripe's webhook signatures use)
    rather than merely compared next to an unauthenticated one: a caller
    without ``secret`` cannot swap in a fresh timestamp on a captured old
    body and recompute a matching signature. A request whose
    ``timestamp_header`` is more than ``MAX_TIMESTAMP_SKEW_SECONDS`` from
    the server's own clock, in EITHER direction, is rejected (see that
    constant's own docstring for why the check is symmetric).

    **Residual: a replay INSIDE that window is still a valid request.**
    There is no nonce or single-use token here, only expiry -- a capture
    replayed within the skew window re-sends a request this module itself
    still accepts. Low-impact by construction rather than by this
    function's own doing: ``handle_on_ship``'s ``progress.upsert`` is keyed
    by ``(station, date)`` and ``handle_on_pr_close``'s ``event_id``-derived
    claim id both make an in-window replay idempotent (re-applies the same
    record) rather than exploitable -- see ``deferred-work.md``'s
    ``DW-FU-13-4`` for the full accounting.

    The timestamp's shape is validated the same defensive way the hex
    signature half already is, before either reaches ``int()``/``hmac``:
    non-empty, no longer than ``_MAX_TIMESTAMP_HEADER_LEN``, and composed
    only of ASCII decimal digits (so a leading ``+``/``-`` or stray
    whitespace -- both of which bare ``int()`` accepts -- is rejected
    rather than silently parsed)."""
    if signature_header is None or not signature_header.startswith(_SIGNATURE_PREFIX):
        return False
    provided = signature_header[len(_SIGNATURE_PREFIX) :]
    if len(provided) != _SIGNATURE_HEX_LEN or not _HEX_DIGITS.issuperset(provided):
        return False
    if (
        timestamp_header is None
        or not (1 <= len(timestamp_header) <= _MAX_TIMESTAMP_HEADER_LEN)
        or not _TIMESTAMP_DIGITS.issuperset(timestamp_header)
    ):
        return False
    timestamp_seconds = int(timestamp_header)
    now_seconds = int(datetime.now(UTC).timestamp())
    if abs(now_seconds - timestamp_seconds) > MAX_TIMESTAMP_SKEW_SECONDS:
        return False
    expected = hmac.new(secret, timestamp_header.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided.lower())


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
            f"{SECRET_ENV_VAR} is not set -- the webhook cannot verify HMAC signatures without a shared secret"
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


def _json_safe(value: Any) -> Any:
    """``value`` with every non-finite float replaced by its ``repr``.

    The alert record below is only useful if it is really JSON. Python's
    ``json.dumps`` emits bare ``NaN``/``Infinity`` tokens, which RFC 8259
    does not allow and strict consumers (``jq``, most log pipelines)
    reject -- and such a value can reach the record through any payload
    field ``_problem_on_ship`` does not know about, since ``json.loads``
    accepts those non-standard literals on the way in."""
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, Mapping):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _alert_payload_summary(payload: Mapping[str, Any]) -> Any:
    """``payload``, JSON-safe, and bounded to ``_MAX_ALERT_PAYLOAD_CHARS``.

    "Payload summary", as Boundaries & Constraints puts it -- not the
    payload whole. Small payloads (every real one) are embedded verbatim;
    an oversized one is replaced by a truncated rendering plus its real
    size, so the record stays a bounded, greppable line instead of the
    caller-sized flood ``_MAX_ALERT_PAYLOAD_CHARS`` describes."""
    safe = _json_safe(dict(payload))
    rendered = json.dumps(safe, allow_nan=False, separators=(",", ":"))
    if len(rendered) <= _MAX_ALERT_PAYLOAD_CHARS:
        return safe
    return {
        "truncated": True,
        "serialized_chars": len(rendered),
        "head": rendered[:_MAX_ALERT_PAYLOAD_CHARS],
    }


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
                "payload": _alert_payload_summary(payload),
                "error": f"{type(exc).__name__}: {exc}",
            },
            allow_nan=False,
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


def _problem_unknown_fields(payload: Mapping[str, Any], known: frozenset[str]) -> str | None:
    """Reject any field this route does not know, or ``None``.

    The same AD-6 convention the rest of the package already applies to
    every document it reads: ``progress._fields_problem`` and
    ``claims._claim_from_dict``/``_evidence_from_dict`` each refuse unknown
    fields with this exact message shape. Accepting them here would make
    the one hand-written, un-linted, schema-less producer surface -- a
    workflow YAML nobody is watching -- the single place a typo is silent:
    ``{"token_spends": 250000}`` would answer 201 while storing 0, and
    because a same-day ``on-ship`` delivery REPLACES rather than merges,
    that typo does not merely fail to record the figure, it wipes whatever
    was recorded for the day. Better one loud 400 at the first delivery
    than a day of quietly zeroed records."""
    unknown = sorted(set(payload) - known)
    if unknown:
        return f"unknown field(s) {', '.join(map(repr, unknown))}"
    return None


def _problem_text(field: str, value: object) -> str | None:
    """The shared type/storability check for one string payload field, or
    ``None`` when it is acceptable.

    Storability matters as much as type. ``json.loads`` accepts a lone
    surrogate escape (``"\\ud800"``) and hands back a ``str`` no UTF-8
    encoder will take; ``progress.py`` documents that it surfaces from
    SQLite's TEXT binding as a ``UnicodeEncodeError`` wrapped into a
    ``HeraldError`` -- indistinguishable from a transient storage fault.
    Left to that layer, the caller burns all 3 retry attempts (~3s of real
    blocking), raises one ERROR alert blaming storage for a fault that is
    really the payload's, and returns the 500 this module's own contract
    invites CI to re-fire forever, for a request that can never succeed.
    That is verbatim the anti-pattern ``_problem_number``'s docstring says
    its range/sign checks exist to close -- this is the same close for the
    string fields. ``_claim_id_for`` has its own stake in it too: it feeds
    these values to ``uuid.uuid5``, which encodes UTF-8 and would raise
    outside ``HeraldError`` entirely, escaping even the retry helper's
    translation into an opaque 500."""
    if not isinstance(value, str):
        return f"field {field!r} must be a string"
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return f"field {field!r} must be valid UTF-8"
    return None


# --- on-ship -----------------------------------------------------------------


def _problem_number(field: str, value: object, *, integer: bool) -> str | None:
    """The shared type/range check for one numeric payload field, or
    ``None`` when it is acceptable.

    Range matters as much as type here, and for two reasons that both end
    as a 500 rather than the 400 they are: ``math.isfinite`` RAISES
    ``OverflowError`` for an ``int`` too large to convert to a float (a
    400-digit JSON integer literal is perfectly legal JSON), and an ``int``
    outside SQLite's signed-64-bit range raises ``OverflowError`` at bind
    time inside ``progress.upsert`` -- which is not a ``HeraldError``, so
    it escapes the retry helper's translation entirely.

    Negative values are rejected here too, mirroring what
    ``_problem_on_pr_close_shipped`` already does for the rules
    ``claims.create`` enforces. ``progress.upsert`` rejects them as well,
    but only as a ``HeraldError``, which is indistinguishable from a
    transient storage failure: the caller would burn all 3 retry attempts,
    raise one ERROR alert blaming storage for a fault that is really the
    payload's, and get a 500 -- which this module's own contract invites
    CI to re-fire forever, for a request that can never succeed."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return f"field {field!r} must be {'an integer' if integer else 'a number'}"
    if integer and not isinstance(value, int):
        return f"field {field!r} must be an integer"
    if isinstance(value, int) and not (_MIN_SQLITE_INT <= value <= _MAX_SQLITE_INT):
        return f"field {field!r} is out of range"
    # `json.loads` accepts the non-standard NaN/Infinity/-Infinity
    # literals, and `progress.upsert`'s own `value < 0` guard is `False`
    # for NaN (NaN comparisons are always False) -- neither layer
    # otherwise rejects one, so a non-finite value would be silently
    # stored and could break downstream numeric aggregation. Checked
    # before the sign test below, which NaN would likewise slip past.
    if not math.isfinite(value):
        return f"field {field!r} must be a finite number"
    if value < 0:
        return f"field {field!r} must not be negative"
    return None


def _problem_on_ship(payload: object) -> str | None:
    """Structural validation only -- required fields present, correct JSON
    types, values inside the range the storage layer can actually hold --
    maps to 400 (Boundaries & Constraints)."""
    if not isinstance(payload, Mapping):
        return "payload is not a JSON object"
    problem = _problem_unknown_fields(payload, _ON_SHIP_FIELDS)
    if problem is not None:
        return problem
    if "station" not in payload:
        return "field 'station' is required"
    problem = _problem_text("station", payload["station"])
    if problem is not None:
        return problem
    # NOT re-validated against `progress.STATIONS` (Boundaries &
    # Constraints' explicit "Never"): `progress.upsert` accepts any
    # station name by design. A blank one is a different question -- it is
    # structurally absent, not merely unrecognized, and every blank-station
    # delivery from every repo would otherwise collapse onto the single
    # `("", date)` row.
    if not payload["station"].strip():
        return "field 'station' must not be blank"
    if "shipped_capabilities" in payload:
        caps = payload["shipped_capabilities"]
        if not isinstance(caps, list):
            return "field 'shipped_capabilities' must be an array of strings"
        for cap in caps:
            if not isinstance(cap, str):
                return "field 'shipped_capabilities' must be an array of strings"
            problem = _problem_text("shipped_capabilities entry", cap)
            if problem is not None:
                return problem
    for field, integer in (
        ("compute_hours", False),
        ("token_spend", True),
        ("wall_clock_hours", False),
    ):
        if field in payload:
            problem = _problem_number(field, payload[field], integer=integer)
            if problem is not None:
                return problem
    if "unblock_narrative" in payload:
        problem = _problem_text("unblock_narrative", payload["unblock_narrative"])
        if problem is not None:
            return problem
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
    exactly).

    That parity is over the ``upsert`` CALL, not over the whole CLI path.
    Two deliberate divergences: the CLI calls ``_validate_station`` first
    and rejects anything outside ``progress.STATIONS``, which Boundaries &
    Constraints names an explicit "Never" here (``progress.upsert`` accepts
    any station by design; the "did you mean" hint is CLI-only sugar) -- so
    an unrecognized station is accepted and recorded, and an operator
    reading it back through a station-scoped CLI surface will not find it.
    And a same-day second delivery REPLACES rather than merges (see the
    module docstring's "Same-day ``on-ship`` deliveries" section)."""
    problem = _problem_on_ship(payload)
    if problem is not None:
        return WebhookResponse(400, {"error": problem})
    assert isinstance(payload, Mapping)
    progress_path = repo_root / progress.DEFAULT_PROGRESS_PATH
    on_date = datetime.now(UTC).date().isoformat()
    # Stored stripped, not raw. The validator above already calls `.strip()`
    # to reject a blank station, so storing the unstripped value made
    # `"warden"`, `" warden"` and `"warden\n"` three separate rows -- and
    # `progress.latest_for_station` matches exactly, so two of those three
    # ships become records no station-scoped reader or dashboard can ever
    # find. Whitespace normalization is NOT the "Never re-validate against
    # `progress.STATIONS`" constraint: an unrecognized station is still
    # accepted, and case is deliberately left alone.
    station = payload["station"].strip()

    def attempt() -> progress.Progress:
        return progress.upsert(
            progress_path,
            station=station,
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
    boolean and must not silently pass the gate below).

    The unknown-field check lives here rather than in
    ``_problem_on_pr_close_shipped`` so it also runs for a not-shipped
    (202) delivery: a typo is a producer bug worth one loud 400 whichever
    way the gate happens to fall that day."""
    if not isinstance(payload, Mapping):
        return "payload is not a JSON object"
    problem = _problem_unknown_fields(payload, _ON_PR_CLOSE_FIELDS)
    if problem is not None:
        return problem
    for field in ("merged", "gates_passed"):
        if field not in payload:
            return f"field {field!r} is required"
        if not isinstance(payload[field], bool):
            return f"field {field!r} must be a boolean"
    return None


def _problem_on_pr_close_shipped(repo_root: Path, payload: Mapping[str, Any]) -> str | None:
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
    problem = _problem_text("project_name", payload["project_name"])
    if problem is not None:
        return problem
    if not payload["project_name"].strip():
        return "field 'project_name' must not be blank"
    if payload.get("shipped_date") is not None:
        problem = _problem_text("shipped_date", payload["shipped_date"])
        if problem is not None:
            return problem
        # Format-checked, not merely type-checked. `claims.create` performs
        # NO date validation (it validates only `project_name` and evidence
        # `type`), so whatever arrives here is stored verbatim -- and
        # `claims.list_claims` then calls `date.fromisoformat` on it with no
        # guard, so a single `"13/08/2026"` delivery makes every subsequent
        # `herald success list --date-range ...` raise a bare `ValueError`
        # out of `cli.main` (`cli.dispatch` translates only `HeraldError`).
        # One poisoned row breaks the surface for every operator afterwards,
        # which is exactly the "catch it here rather than let it sail past
        # into storage" rule the blank-`project_name` check below follows.
        #
        # Round-tripped, not merely parsed. `date.fromisoformat` accepts
        # every ISO 8601 date form on Python 3.11+ -- `"20260813"`
        # (compact) and `"2026-W33-4"` (week-date) both parse -- so a
        # parse-only check keeps the promise its own error message makes
        # ("YYYY-MM-DD") for exactly the shapes it rejects and breaks it
        # for the ones it accepts. The value is stored verbatim, and
        # `web/src/panels/SuccessPanel.jsx` filters `shipped_date` by raw
        # STRING comparison, where `"20260813" > "2026-12-31"` is true
        # (`"0"` sorts after `"-"`): a non-canonical date is dropped from
        # every date-filtered dashboard view -- an unrecorded ship being
        # indistinguishable from no ship, arriving through the field this
        # check was added to protect. Two forms of one date also compute
        # two different `_claim_id_for` ids on the evidence branch.
        try:
            parsed = date.fromisoformat(payload["shipped_date"])
        except ValueError:
            return "field 'shipped_date' must be an ISO 8601 date (YYYY-MM-DD)"
        if parsed.isoformat() != payload["shipped_date"]:
            return "field 'shipped_date' must be an ISO 8601 date (YYYY-MM-DD)"
    # Optional, and the caller's own identifier for this event (see
    # `_claim_id_for`) -- it only has to be stable across a redelivery and
    # distinct between events, so any string will do, but it must BE a
    # string: a mutable/unordered JSON value would not render into a
    # stable uuid5 name.
    if payload.get("event_id") is not None:
        problem = _problem_text("event_id", payload["event_id"])
        if problem is not None:
            return problem
        # A BLANK one is worse than none at all. `_claim_id_for` branches on
        # `event_id is not None`, so `""` -- what an unset workflow input or
        # a `${{ github.event.number }}` on a non-PR trigger renders to --
        # becomes the CONSTANT discriminator `"event:"` for every delivery
        # AND suppresses the evidence fallback, collapsing every same-day
        # ship for a project onto one claim, answered 201, with the loser's
        # evidence dropped. That is the "an unrecorded ship is
        # indistinguishable from no ship" failure this story exists to
        # close, so it is a 400 rather than a silent merge.
        if not payload["event_id"].strip():
            return "field 'event_id' must not be blank"
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
            problem = _problem_unknown_fields(entry, _EVIDENCE_FIELDS)
            if problem is not None:
                return f"each 'evidence' entry has {problem}"
            if not all(isinstance(entry[key], str) for key in _EVIDENCE_FIELDS):
                return "each 'evidence' entry's type/url/label must be strings"
            for key in sorted(_EVIDENCE_FIELDS):
                if _problem_text(f"evidence {key}", entry[key]) is not None:
                    return f"each 'evidence' entry's {key} must be valid UTF-8"
            if entry["type"] not in claims.EVIDENCE_TYPES:
                return f"each 'evidence' entry's type must be one of {claims.EVIDENCE_TYPES}; got {entry['type']!r}"
            if entry["type"] == "notice":
                # A `notice` entry's `url` holds a Notice COMPONENT NAME,
                # not an HTTP URL, and both `claims.publish` and
                # `claims._revalidated_entry` short-circuit it as trivially
                # valid -- never HEAD'd, stamped `validated=True` without a
                # single check. The compensating check lives in the CLI:
                # `herald success create --evidence-notice` calls
                # `notices.get_notice` first, "rather than letting a claim
                # silently cite a notice that was never authored (or was
                # mistyped)". Without the same check here, this route is a
                # way to attach evidence that passes Story 9.5's entire
                # evidence gate while referring to nothing -- so it runs
                # here too, as the 400 it is.
                try:
                    notices.get_notice(repo_root, entry["url"])
                except errors.HeraldError as exc:
                    return f"each 'evidence' entry of type 'notice' must name an existing notice: {exc}"
    return None


def _claim_id_for(payload: Mapping[str, Any], shipped_date: str) -> str:
    """A deterministic claim id for one logical CI shipped-PR event --
    ``uuid.uuid5`` over what identifies that event, rather than
    ``uuid.uuid4()`` (see the module docstring's "Retry + idempotency"
    section). A genuine CI webhook redelivery of the SAME event is a
    second, independent HTTP call -- a random id per call would defeat
    ``handle_on_pr_close``'s ``read_one``-before-``create`` idempotency
    guard across that boundary and create a second, duplicate draft claim;
    a deterministic id makes the redelivery compute the SAME id, so the
    very same guard catches it too.

    The identity has to discriminate as well as it deduplicates. Keyed on
    ``project_name`` and ``shipped_date`` ALONE it does not: two different
    PRs for one project merging on one day are two real ships that compute
    one id, so the second is silently swallowed by the idempotency guard
    and answered ``201`` -- exactly the "an unrecorded ship is
    indistinguishable from no ship" failure this story exists to close, and
    its evidence is dropped with it. So a per-event discriminator joins the
    name:

    - ``event_id`` when the payload carries one -- the caller's own
      identifier for the event. This is the precise answer, and what
      Story 13.6's workflow step should send, but it must be GLOBALLY
      unique, not merely unique to its producer: a bare PR number is
      unique only within one repository, so if this endpoint is ever fed
      by two of them, repo A's PR 42 and repo B's PR 42 compute one id
      and the second real ship is swallowed at ``201``. This branch
      deliberately omits the date (see below), which makes such a
      collision permanent rather than same-day. Send something
      repo-qualified (``${{ github.repository }}#${{ github.event.number }}``)
      or globally unique by construction (the delivery GUID). It
      already identifies the event on its own, so the date is deliberately
      left OUT of the name on this branch: ``shipped_date`` falls back to
      the SERVER's clock when the payload omits it, and a redelivery is by
      design a LATER call (the module's own non-2xx contract invites CI to
      re-fire), so folding a server-computed date in made a redelivery that
      merely crossed UTC midnight compute a different id and create the
      duplicate this whole mechanism exists to prevent.
    - otherwise the ``evidence`` list, canonically encoded, keyed with the
      date -- CI's PR-close payload carries the PR's own URL there, so
      distinct PRs differ here even with no ``event_id``, while a
      redelivery of the identical body still computes the identical id.
      This branch keeps the date because evidence alone is a weaker
      identity: without it, two genuinely separate ships that happen to
      cite the same evidence on different days would collapse into one.
      A midnight-crossing redelivery is still a duplicate here, which is
      one more reason Story 13.6's workflow step should send ``event_id``.

    Two same-day ships for one project that supply neither an ``event_id``
    nor any distinguishing evidence remain indistinguishable by
    construction -- nothing in such a payload tells them apart.

    The uuid5 name is built by JSON-encoding the parts as a LIST, never by
    joining them with a separator. Caller-controlled strings around a bare
    ``|`` are ambiguous: ``{"project_name": "A|event:B", "event_id": "C"}``
    and ``{"project_name": "A", "event_id": "B|event:C"}`` rendered the
    identical name, so two distinct events computed one id and the second
    was swallowed by the idempotency guard at ``201`` -- the very
    silent-swallow this function exists to prevent. ``project_name`` is
    stripped for the same reason ``handle_on_ship`` stores ``station``
    stripped: a trailing newline off a ``${{ }}`` expansion is the ordinary
    YAML artifact, and here it would compute a different id and create the
    duplicate claim -- on the one surface with no dedupe key to recover
    with."""
    event_id = payload.get("event_id")
    if event_id is not None:
        key = ["event", event_id]
    else:
        key = [
            "evidence",
            shipped_date,
            [[entry["type"], entry["url"], entry["label"]] for entry in payload.get("evidence", [])],
        ]
    name = json.dumps(
        ["herald-claim", payload["project_name"].strip(), key],
        separators=(",", ":"),
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


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

    shipped_problem = _problem_on_pr_close_shipped(repo_root, payload)
    if shipped_problem is not None:
        return WebhookResponse(400, {"error": shipped_problem})

    claims_path = repo_root / claims.DEFAULT_CLAIMS_PATH
    # Resolved ONCE, here, and passed to BOTH `_claim_id_for` and
    # `claims.create` below. `claims.create`'s own default for an omitted
    # `shipped_date` is `date.today()` -- the LOCAL date -- while this
    # module computes UTC everywhere (`handle_on_ship`'s `date`, per
    # Boundaries & Constraints). Letting each side fall back on its own
    # clock stored a record whose `shipped_date` the id could not be
    # recomputed from, and made a redelivery that straddled the two
    # clocks' midnight compute a different id and create the duplicate
    # this whole mechanism exists to prevent.
    shipped_date = payload.get("shipped_date")
    if shipped_date is None:
        shipped_date = datetime.now(UTC).date().isoformat()
    # Generated ONCE, before the retry loop, and DETERMINISTICALLY (see
    # `_claim_id_for` and the module docstring's "Retry + idempotency"
    # section) -- a genuine redelivery of this same logical event, arriving
    # as a separate top-level call, computes this same id.
    claim_id = _claim_id_for(payload, shipped_date)
    # Stored stripped, matching what `_claim_id_for` hashes and what
    # `handle_on_ship` already does for `station` -- otherwise `"Marshal"`
    # and `"Marshal\n"` are two projects to every reader downstream.
    project_name = payload["project_name"].strip()
    evidence = tuple(
        claims.Evidence(type=e["type"], url=e["url"], label=e["label"]) for e in payload.get("evidence", [])
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
            project_name=project_name,
            shipped_date=shipped_date,
            evidence=evidence,
            id_factory=lambda: claim_id,
        )

    try:
        claim = _retry_with_backoff(attempt, sleep=sleep)
    except errors.HeraldError as exc:
        _log_retry_exhausted("on-pr-close", payload, exc)
        return WebhookResponse(500, {"error": "storage failure"})
    return WebhookResponse(201, {"claim_id": claim.id, "project_name": claim.project_name})


# --- the ASGI3 boundary (AD-8: "protocol, not framework") --------------------


class _BodyTooLarge(PyforgeError, Exception):
    """Raised by ``_read_body`` once the accumulated body exceeds
    ``MAX_BODY_BYTES`` -- caught by ``app()`` and turned into a 413
    response BEFORE the body is ever handed to ``verify_signature`` (see
    the module docstring's "Body size cap" section).

    Multi-inherits ``PyforgeError`` directly (Story 14.3, CAP-5) rather
    than ``errors.HeraldError``: this is an internal ASGI body-read signal
    caught by exact type at its own raise site, not a domain error that
    should join ``HeraldError``'s retry/catch surface."""


class _ClientDisconnected(PyforgeError, Exception):
    """Raised by ``_read_body`` on an ``http.disconnect`` message -- the
    peer went away mid-body, so there is no complete request to act on and
    nobody left to answer.

    Without this, ``http.disconnect`` carries no ``more_body`` key, so the
    drain loop below read it as "body complete" and handed a TRUNCATED body
    on to ``verify_signature`` -- which of course fails, answering a
    network truncation with ``401 invalid or missing HMAC signature`` and
    sending an operator hunting a secret mismatch that never happened."""


async def _read_body(receive: Receive) -> bytes:
    """Drain every ``http.request`` message until ``more_body`` is falsy --
    the ASGI3 contract for a (possibly chunked) request body. Raises
    ``_BodyTooLarge`` once the accumulated size exceeds ``MAX_BODY_BYTES``,
    checked on every chunk so a caller cannot stream past the cap one
    ``more_body: true`` message at a time, or once more than
    ``MAX_BODY_MESSAGES`` messages have arrived, and ``_ClientDisconnected``
    if the peer disconnects before the body is complete.

    The message bound is not redundant with the byte bound: a ZERO-length
    chunk adds nothing to ``size``, so a stream of them never trips the
    byte cap, never satisfies ``more_body``, and never ends -- an
    unauthenticated caller holding one request open forever while the chunk
    list grows a slot per message (see ``MAX_BODY_MESSAGES``).

    Chunks are collected and joined ONCE rather than accumulated with
    ``body += chunk``: ``bytes`` is immutable, so repeated concatenation
    copies the whole accumulated body per chunk, which is quadratic in the
    number of chunks. ``MAX_BODY_BYTES`` bounds the memory but not that
    work, and this coroutine is awaited directly on the event-loop thread
    (it is the one part of the request that cannot go through
    ``asyncio.to_thread``, since it IS the receive side) -- so an
    UNAUTHENTICATED caller, before any signature is checked, could stall
    every other in-flight request just by streaming a capped-size body in
    tiny chunks. Measured before this fix: 1 MB delivered as 1-byte chunks
    burned ~29s of event-loop CPU before the 413. Joining once makes the
    same request linear."""
    chunks: list[bytes] = []
    size = 0
    messages = 0
    more_body = True
    while more_body:
        message = await receive()
        if message.get("type") == "http.disconnect":
            raise _ClientDisconnected("client disconnected before the body was complete")
        messages += 1
        if messages > MAX_BODY_MESSAGES:
            raise _BodyTooLarge(f"request body arrived in more than {MAX_BODY_MESSAGES} chunks")
        chunk = message.get("body", b"")
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise _BodyTooLarge(f"request body exceeds {MAX_BODY_BYTES} bytes")
        if chunk:
            chunks.append(chunk)
        more_body = message.get("more_body", False)
    return b"".join(chunks)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """``object_pairs_hook`` refusing a duplicated key anywhere in the
    request body -- the same AD-6 convention ``progress``/``claims``/
    ``state`` already apply to the documents they read.

    ``json.loads`` otherwise keeps the LAST value for a repeated key, so
    ``{"gates_passed": false, "gates_passed": true}`` passes the ship gate
    on a payload that also says it should not. The body is signed, so this
    is a buggy producer rather than an attacker -- but a mis-gated claim is
    a wrong record either way, and ``app`` already answers a malformed body
    with a 400."""
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate key {key!r}")
        document[key] = value
    return document


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

    Refuses a non-``bytes`` ``secret`` for the same reason, and it is the
    likelier half of that mistake: a caller who bypasses
    ``resolve_webhook_secret`` most plausibly passes
    ``os.environ["HERALD_WEBHOOK_SECRET"]`` directly, which is a ``str``.
    That is truthy, so the emptiness guard alone let it through, returning
    an ``app`` that then died in ``hmac.new`` on EVERY request -- a silent
    100% outage answered 500, with one ``unexpected_exception`` ERROR
    record per delivery flooding this module's only alert channel. Failing
    at construction turns that into one loud error at mount time.

    Route/method/signature/body-shape checks run in the I/O matrix's own
    order: unknown path -> 404, wrong method on a known path -> 405 (both
    before the body is read at all); then the body is read (-> 413 if it
    exceeds ``MAX_BODY_BYTES``) and the HMAC (now including the
    ``X-Hub-Timestamp`` skew check -- ``verify_signature``'s own docstring)
    is checked against it -> 401 (before the body is parsed as JSON); then
    JSON parsing -> 400 on failure; only then does the matched handler run
    (which does its own
    further structural validation -> 400, or the real storage work ->
    201/202/500). Any other exception on that path is a 500 (see the
    module docstring's "Uncaught exceptions" section)."""
    if not isinstance(secret, (bytes, bytearray)):
        raise errors.HeraldError(
            f"create_app was given a {type(secret).__name__} webhook secret -- "
            f"it must be bytes (hmac.new rejects anything else, so every "
            f"request would 500); use resolve_webhook_secret, or encode it "
            f"yourself"
        )
    if not secret:
        raise errors.HeraldError(
            "create_app was given a blank webhook secret -- verify_signature "
            "would accept a forged signature computed from an empty key; "
            "resolve a real secret (e.g. via resolve_webhook_secret) before "
            "calling create_app"
        )

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        scope_type = scope.get("type")
        if scope_type == "websocket":
            # ASGI requires a websocket app to answer the handshake, with
            # an accept or a close; returning without one is an application
            # error the host reports (uvicorn: "ASGI callable returned
            # without sending handshake") once per connection. This is an
            # HTTP-only leaf app, so it declines the connection outright
            # rather than leaving the host to raise -- the same "always
            # answer" reasoning as the HTTP guard further down.
            #
            # Guarded, because this send is exactly the one that can fail:
            # uvicorn's websocket `send` RAISES `ClientDisconnected` up
            # front when the peer is already gone, so a client that
            # vanishes during the handshake would otherwise propagate an
            # exception out of `app` -- the uncaught escape the HTTP guard
            # below exists to prevent, on the one path that was outside it.
            try:
                await send({"type": "websocket.close", "code": 1000})
            except Exception as exc:  # noqa: BLE001 -- nothing left to answer with
                _log_unexpected_exception("websocket", exc)
            return
        if scope_type != "http":
            return  # e.g. an ASGI "lifespan" scope -- nothing for a leaf app to do

        response_started = False
        event_name = "unrouted"

        async def tracking_send(message: Mapping[str, Any]) -> None:
            """``send``, remembering whether the response has begun -- the
            error guards below must not start a SECOND response."""
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        async def fail(status: int, body: Mapping[str, Any]) -> None:
            """Answer with a terminal error, defensively.

            Two ways this can be called when it must NOT send: after the
            response already started (the host rejects a second
            ``http.response.start``, and that rejection propagated out of
            ``app`` -- precisely the uncaught escape the guard exists to
            prevent), and when ``send`` itself is what failed, because the
            peer is gone. In the first case the caller has already logged
            the real cause, so this stays silent; in the second there is
            nothing left to answer with, so it logs and gives up."""
            if response_started:
                return
            try:
                await _send_json(tracking_send, status, body)
            except Exception as exc:  # noqa: BLE001 -- nothing left to answer with
                _log_unexpected_exception(event_name, exc)

        # Everything from routing through the final response send is wrapped
        # in a broad exception guard -- see the module docstring's "Uncaught
        # exceptions" section: an ASGI app must always answer, never let a
        # bug hang whatever host mounts this callable. Routing (and its own
        # 404/405 sends) is INSIDE the guard for the same reason the
        # websocket close above is guarded: a `send` that raises there is
        # still an exception escaping `app`.
        try:
            # `scope["path"]` includes the prefix the host mounted this app
            # under, so an exact match against the route literals 404s every
            # delivery the moment Story 13.6 mounts it anywhere but the root.
            # `root_path` is that prefix; strip it before routing.
            #
            # Stripped on SEGMENT boundaries, and with a trailing slash
            # normalized away first. A host started with `--root-path /`
            # reports `root_path == "/"`, which as a bare string prefix
            # matches every path and left `api/herald/...` with no leading
            # slash -- 404ing every delivery under a perfectly ordinary
            # configuration. A non-boundary prefix (mounted at `/her`,
            # request for `/herald`) was likewise mangled into a bogus route
            # rather than declined.
            #
            # The REQUEST path is normalized the same way, for the same
            # reason the prefix is: a routing 404 is indistinguishable from
            # "the endpoint isn't deployed", so a correctly-signed delivery
            # should not be lost to a producer's trailing slash
            # (`.../on-ship/`) or to the doubled slash an nginx
            # `location`/`proxy_pass` pair routinely emits
            # (`//api/herald/...`). Collapsing repeats and dropping a
            # trailing slash cannot merge two real routes -- these two
            # literals differ in a segment, not in punctuation.
            #
            # Story 19.1: route literals are the full station-API paths
            # (`/stations/herald/api/v1/webhooks/...`). Per the ASGI spec
            # `path` INCLUDES `root_path`, so a host that mounts this app
            # under a further prefix must still strip `root_path` below --
            # the same discipline as Story 13.6's daphne mount note.
            path = scope.get("path") or ""
            while "//" in path:
                path = path.replace("//", "/")
            if len(path) > 1:
                path = path.rstrip("/") or "/"
            root_path = (scope.get("root_path") or "").rstrip("/")
            if root_path and (path == root_path or path.startswith(root_path + "/")):
                path = path[len(root_path) :] or "/"
            if path == ON_SHIP_PATH:
                handler: Callable[..., WebhookResponse] = handle_on_ship
                event_name = "on-ship"
            elif path == ON_PR_CLOSE_PATH:
                handler = handle_on_pr_close
                event_name = "on-pr-close"
            else:
                await _send_json(tracking_send, 404, {"error": f"no such webhook route: {path!r}"})
                return
            if scope.get("method") != "POST":
                await _send_json(tracking_send, 405, {"error": "method not allowed; use POST"})
                return

            body = await _read_body(receive)
            signature = _header_value(scope, _SIGNATURE_HEADER)
            timestamp = _header_value(scope, _TIMESTAMP_HEADER)
            if not verify_signature(secret, body, signature, timestamp):
                await fail(401, {"error": "invalid or missing HMAC signature"})
                return

            try:
                # `ValueError` covers both `json.JSONDecodeError` and the
                # `UnicodeDecodeError` of a non-UTF-8 body, and also the
                # duplicate-key rejection from the hook. `RecursionError`
                # joins it for the same reason `progress.py` and
                # `claims.py` already pair the two when they parse: deeply
                # nested JSON (`[` x 100_000 is only 200 KB, well under
                # `MAX_BODY_BYTES`) blows the stack instead of raising a
                # decode error, and without this it fell through to the
                # last-resort guard as a 500 plus one `unexpected_exception`
                # ERROR record -- for input that is simply malformed, and
                # which this module's own contract then invites CI to
                # re-fire forever, one alert record each time.
                payload = json.loads(body, object_pairs_hook=_reject_duplicate_keys)
            except ValueError, RecursionError:
                await fail(400, {"error": "malformed JSON payload"})
                return

            # Off the event-loop thread: `_retry_with_backoff`'s default
            # `sleep` is the real, blocking `time.sleep`, and calling the
            # handler directly here would block every other in-flight
            # request during any retry (see the module docstring's "Shape"
            # section).
            result = await asyncio.to_thread(handler, repo_root, payload)
            await _send_json(tracking_send, result.status, result.body)
        except _ClientDisconnected:
            return  # nobody left to answer -- see `_ClientDisconnected`
        except _BodyTooLarge as exc:
            # The exception's own message, because there are now two ways
            # to exceed the cap -- too many bytes, or too many chunks --
            # and an operator debugging a 413 needs to know which.
            await fail(413, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 -- last-resort ASGI contract guard
            _log_unexpected_exception(event_name, exc)
            await fail(500, {"error": "internal error"})

    return app
