"""CloudEvents-on-Streams names (canopy AD-8 / AD-10)."""

from __future__ import annotations

STREAM = "pyforge.events"
DLQ = "pyforge.events.dlq"
APPLIED_PREFIX = "pyforge.events.applied:"
EVENT_FIELD = "event"
SPECVERSION = "1.0"

# CloudEvents JSON extension names — lowercase letters/digits only.
EXT_SPEC_ID = "specid"
EXT_GIT_SHA = "gitsha"
EXT_SBOM_PURL = "sbompurl"
EXT_WORK_ITEM_ID = "workitemid"
EXT_LOOP_DEPTH = "pyforgeloopdepth"
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

# Chrome registry: adding a type is a django-pyforge change, not a story-local string.
EVENT_TYPES = frozenset(
    {
        "recipe.audit.failed",
    },
)

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
