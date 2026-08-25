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
