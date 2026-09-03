"""CloudEvents-on-Streams names (canopy AD-8 / AD-10)."""

from __future__ import annotations

STREAM = "pyforge.events"
DLQ = "pyforge.events.dlq"
APPLIED_PREFIX = "pyforge.events.applied:"
# Story 42.3: the last handler error per stream entry, so a DLQ write made by
# a later harvest (the failing consumer is gone) still carries the error.
LAST_ERROR_PREFIX = "pyforge.events.lasterror:"
EVENT_FIELD = "event"
SPECVERSION = "1.0"

# CloudEvents JSON extension names — lowercase letters/digits only.
EXT_SPEC_ID = "specid"
EXT_GIT_SHA = "gitsha"
EXT_SBOM_PURL = "sbompurl"
EXT_WORK_ITEM_ID = "workitemid"
EXT_LOOP_DEPTH = "pyforgeloopdepth"
# Story 42.5: tenant id from the publishing assertion's ``pyforge:tenant:*`` claim.
EXT_TENANT = "pyforgetenant"
# CloudEvents Distributed Tracing extension (W3C traceparent). Story 42.3,
# red-team A-5: the envelope is the only thing that crosses the bus, so the
# trace context must ride on it.
EXT_TRACEPARENT = "traceparent"
LOOP_DEPTH_CEILING = 8

# Applied-id TTL (Story 40.2): duplicate-suppression keys must not grow
# without bound. Default seven days — long enough for consumer-group
# harvest cycles and broker restarts; override via
# DJANGO_PYFORGE_EVENT_APPLIED_TTL_SECONDS.
EVENT_APPLIED_TTL_SECONDS_DEFAULT = 7 * 24 * 3600

# Main stream approximate trim (Story 40.2): caps stream head growth under
# broker maxmemory. 100k entries at ~1 KB/event ≈ 100 MB — hours of
# backlog at estate publish rates before a slow group is trimmed; the DLQ
# is never auto-trimmed. Override via DJANGO_PYFORGE_EVENT_STREAM_MAXLEN.
EVENT_STREAM_MAXLEN_DEFAULT = 100_000

# Delivery semantics (Story 42.3, red-team A-2 / A-4, directive R-9).
#
# Attempts are the XPENDING delivery counter: the first XREADGROUP delivery
# is attempt 1 and every XCLAIM that retries the entry adds one. A
# well-formed event whose handler has raised EVENT_MAX_ATTEMPTS times is
# quarantined on ``pyforge.events.dlq`` with the last error and ACKed.
# Override via DJANGO_PYFORGE_EVENT_MAX_ATTEMPTS.
EVENT_MAX_ATTEMPTS_DEFAULT = 5
# Backoff before retry k+1 after k failed attempts: base * 2**(k-1), capped
# at the max. Defaults give 1s, 2s, 4s, 8s between the five attempts.
# Override via DJANGO_PYFORGE_EVENT_BACKOFF_BASE_MS / _BACKOFF_MAX_MS.
EVENT_BACKOFF_BASE_MS_DEFAULT = 1_000
EVENT_BACKOFF_MAX_MS_DEFAULT = 60_000
# Handler budget. ``harvest_poison`` may only claim an entry that has been
# pending at least this long, otherwise it steals a message a healthy
# consumer is still processing (A-4). An independent literal that is EQUAL
# to (not derived from) config.settings.base's CELERY_TASK_TIME_LIMIT of
# 300 s -- the longest work a handler may legitimately wait on; change both
# together. Override via DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS.
EVENT_HANDLER_TIMEOUT_MS_DEFAULT = 5 * 60 * 1000

# DLQ entry fields written next to the original ``event`` field.
DLQ_REASON_FIELD = "reason"
DLQ_ERROR_FIELD = "error"
DLQ_ATTEMPTS_FIELD = "attempts"
DLQ_GROUP_FIELD = "group"
DLQ_STREAM_ID_FIELD = "stream_id"
DLQ_QUARANTINED_AT_FIELD = "quarantined_at"
DLQ_REASON_UNPARSEABLE = "unparseable"
DLQ_REASON_EXHAUSTED = "exhausted"

# Chrome registry: adding a type is a django-pyforge change, not a story-local
# string. Story 42.3 registers the Warden -> Doctor -> Mason vocabulary; every
# type names the dataschema URN its ``data`` object is published under. The
# consuming adapter checks the required keys for its type (BS-6: validation
# in adapters, never at the stream boundary); nothing resolves the URN.
EVENT_SCHEMAS: dict[str, str] = {
    # Warden -> Doctor: an audit verdict that needs a reaction.
    "recipe.audit.failed": "urn:pyforge:schema:events:recipe.audit.failed:v1",
    # Doctor -> Mason: apply a named remedy to a package.
    "remedy.requested": "urn:pyforge:schema:events:remedy.requested:v1",
    # Doctor -> Mason: rebuild a recipe (no source change).
    "recipe.rebuild.requested": "urn:pyforge:schema:events:recipe.rebuild.requested:v1",
    # Mason -> Doctor: the remedy ran; outcome attached.
    "remedy.completed": "urn:pyforge:schema:events:remedy.completed:v1",
    # Supervisor -> bus: a bounded run was published (Story 42.5).
    "run.started": "urn:pyforge:schema:events:run.started:v1",
}
EVENT_TYPES = frozenset(EVENT_SCHEMAS)

STATION_TOKENS = frozenset(
    {
        "atlas",
        "doctor",
        "herald",
        "marshal",
        "mason",
        "scribe",
        "steward",
        "warden",
    },
)

# Which station consumes which types. One stream, one consumer group per
# station (AD-8): a station's consumer reads every entry and ACKs the types
# it does not subscribe to without running a handler.
SUBSCRIPTIONS: dict[str, frozenset[str]] = {
    "doctor": frozenset({"recipe.audit.failed", "remedy.completed"}),
    "mason": frozenset({"remedy.requested", "recipe.rebuild.requested"}),
}
