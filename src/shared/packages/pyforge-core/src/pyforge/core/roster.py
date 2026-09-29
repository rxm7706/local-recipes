"""pyforge.core.roster -- the one Guild station roster (Story 59.6,
spec-pyforge-steward CAP-137 / spec-vocabulary-one-name-one-job CAP-7).

Four Python-level ``STATIONS``-shaped constants disagreed with each other
(measured 2026-09-14, ``docs/dreams/vocabulary-one-name-one-job.md``):
three distinct member orders, and marshal's ``DREAM_STATIONS`` silently
omitted ``doctor`` and ``scribe`` entirely. This module is the one
declared list every station package imports rather than keeping its own
copy -- the operator ruling (Ruling 18) that resolved the omission was
"collapse the four disagreeing STATIONS lists", not "fix each list's
membership independently".

``docs/governance/guild-roster.json``'s ``stations`` key carries the same
eight names in the same order and remains the canonical SHORT-form
roster for repo-rooted tooling (doctor, ``scripts/*.py``) that already
takes an explicit ``target: Path`` and reads that JSON file directly.
This module exists for in-process station code with no such path, which
must not gain a JSON-parsing / filesystem dependency just to name its
own siblings -- keep the two lists in sync by hand; nothing here reads
the JSON file.
"""

from __future__ import annotations

STATIONS: tuple[str, ...] = (
    "herald",
    "marshal",
    "atlas",
    "warden",
    "mason",
    "doctor",
    "scribe",
    "steward",
)
"""The eight PyForge Guild stations, SHORT form -- matches
``docs/governance/guild-roster.json``'s ``stations`` key exactly."""


def long_form(station: str) -> str:
    """The LONG form of a SHORT station name: ``pyforge-<station>`` --
    the form used for paths, packages, and pixi environments (Ruling 18).
    A mechanical prefix, not a second list."""
    return f"pyforge-{station}"
