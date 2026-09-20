"""Steward's ``glass`` duty — the as-of glass over standup/shipped (Story
61.3, spec-work-passports-dated-extracts CAP-3 / spec-pyforge-steward CAP-141).

Standup asks "any news from the vendor?" This module answers it from the
SAME `CorridorLoad` idempotency record 61.1 already ships: `standup`
(inbound) and `shipped` (outbound) are the two directions of one glass,
read through one shared `compute_glass_reading(direction=...)` -- never two
independently hand-rolled freshness computations ("do not invent a second
standup source of truth").

"Empty" is a zero-byte-file check, not content parsing: `corridor.py`'s
`load_extract` is deliberately content-blind (61.1/61.2), so "was the file
empty?" is answered by comparing `batch_sha` to the well-known SHA-256 of
zero bytes, with no new schema and no loader change. "On time" means
"today" (UTC calendar date); anything else is `stale`, a deliberate
generalization of the literal I/O Matrix example "yesterday" to "not
today" -- no cutoff-hour or business-day config exists to special-case.

The durable record lives behind the `pyforge-steward[dashboard]` extra.
`compute_glass_reading` reaches it through the same sanctioned dynamic
base->dashboard idiom as `corridor.load_extract`/`passport.
mint_vendor_passport`: a lazy `importlib.import_module` call, refusing
(never raising) when the extra is not installed.

`GlassDuty` never calls ``sys.exit`` (AD-8) -- it returns a ``DutyResult``
and ``cli.main`` projects it.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .corridor import DIRECTIONS
from .interfaces import DutyResult
from .sprint_ledger_query import eval_flag, flag_off_message, parse_flag_overrides

EMPTY_FILE_SHA256 = hashlib.sha256(b"").hexdigest()
GLASS_STATES: tuple[str, ...] = ("unborn", "fresh", "stale", "failed")


class GlassError(ValueError):
    """Unknown direction, or a naive (non-timezone-aware) ``now``."""


@dataclass(frozen=True)
class GlassReading:
    """One glass reading -- either an answer (``status="ok"``) or a refusal
    (``status="refused"``, no ORM reachable). ``state`` is one of
    :data:`GLASS_STATES`, or ``None`` when ``status == "refused"``."""

    status: str  # "ok" | "refused"
    direction: str
    state: str | None
    waybill: str | None
    batch_sha: str | None
    loaded_at: str | None  # ISO 8601; None when unborn/refused
    message: str = ""


def compute_glass_reading(*, direction: str, now: datetime | None = None) -> GlassReading:
    """Read the most recent corridor load for ``direction`` and classify it.

    Raises :class:`GlassError` for an unknown direction or a naive ``now``;
    otherwise refuses (never raises) when the ``[dashboard]`` extra is not
    installed or the ORM is otherwise unreachable.
    """
    if direction not in DIRECTIONS:
        raise GlassError(f"unknown direction {direction!r}; must be one of {DIRECTIONS!r}")

    reference_now = now if now is not None else datetime.now(timezone.utc)
    if now is not None and now.tzinfo is None:
        raise GlassError("now must be timezone-aware (naive datetime not accepted)")

    import importlib

    try:
        module = importlib.import_module("pyforge.steward.dashboard.glass_query")
    except ImportError:
        return GlassReading(
            status="refused",
            direction=direction,
            state=None,
            waybill=None,
            batch_sha=None,
            loaded_at=None,
            message="pyforge-steward[dashboard] extra not installed",
        )

    outcome = module.read_latest_corridor_load(direction=direction)
    if outcome["status"] == "refused":
        return GlassReading(
            status="refused",
            direction=direction,
            state=None,
            waybill=None,
            batch_sha=None,
            loaded_at=None,
            message=outcome["message"],
        )

    if not outcome["found"]:
        return GlassReading(
            status="ok",
            direction=direction,
            state="unborn",
            waybill=None,
            batch_sha=None,
            loaded_at=None,
            message="no waybill has ever loaded for this direction",
        )

    waybill = outcome["waybill"]
    batch_sha = outcome["batch_sha"]
    loaded_at = outcome["loaded_at"]
    loaded_date = datetime.fromisoformat(loaded_at).astimezone(timezone.utc).date()
    is_today = loaded_date == reference_now.astimezone(timezone.utc).date()

    if is_today and batch_sha == EMPTY_FILE_SHA256:
        state, message = "failed", "today's on-time file is empty"
    elif is_today:
        state, message = "fresh", ""
    else:
        state, message = "stale", "no drop yet today -- showing the last known waybill"

    return GlassReading(
        status="ok",
        direction=direction,
        state=state,
        waybill=waybill,
        batch_sha=batch_sha,
        loaded_at=loaded_at,
        message=message,
    )


def _direction_ok(reading: GlassReading) -> bool:
    """"Empty on-time file fails" is the only state this story's own
    Boundaries call a failure; "stale"/"unborn" are legitimate, non-failing
    answers ("late drop leaves yesterday stale" is explicitly NOT a fail)."""
    return reading.status == "ok" and reading.state != "failed"


FLAG_GLASS_EXPORT = "enable_glass_export"
GLASS_EXPORT_FORMATS: tuple[str, ...] = ("csv", "markdown")


def render_glass_table(readings: dict[str, GlassReading], fmt: str) -> str:
    """Render a two-row (standup, shipped) table -- the companion doc's
    "mailed/export of last waybill" made real as a switchable plugin."""
    if fmt not in GLASS_EXPORT_FORMATS:
        raise GlassError(f"unknown format {fmt!r}; must be one of {GLASS_EXPORT_FORMATS!r}")

    rows = [("Standup", readings["standup"]), ("Shipped", readings["shipped"])]
    header = ["View", "Direction", "State", "Waybill", "Loaded At (UTC)", "Message"]

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        for label, reading in rows:
            writer.writerow(
                [
                    label,
                    reading.direction,
                    reading.state or "refused",
                    reading.waybill or "",
                    reading.loaded_at or "",
                    reading.message,
                ]
            )
        return output.getvalue()

    lines = ["| " + " | ".join(header) + " |", "|---|---|---|---|---|---|"]
    for label, reading in rows:
        lines.append(
            f"| {label} | {reading.direction} | {reading.state or 'refused'} | "
            f"{reading.waybill or ''} | {reading.loaded_at or ''} | {reading.message} |"
        )
    return "\n".join(lines)


def _line(label: str, reading: GlassReading) -> str:
    if reading.status == "refused":
        return f"{label}: refused ({reading.message})"
    text = f"{label}: {reading.state} waybill={reading.waybill or '-'}"
    if reading.message:
        text += f" ({reading.message})"
    return text


def _glass_result(ok: bool, payload: dict, plain_summary: str, as_json: bool) -> DutyResult:
    """One unified --json/payload-shape helper across every branch, applying
    61.2's own review lesson from the start (never unify per-branch after
    the fact)."""
    return DutyResult(
        ok=ok,
        summary=json.dumps(payload, indent=2, sort_keys=True) if as_json else plain_summary,
        details=payload,
    )


class GlassDuty:
    """``steward glass [export]`` -- Story 61.3.

    Bare ``steward glass`` reports standup (inbound) and shipped (outbound)
    freshness. ``export`` renders a two-row CSV/markdown table, gated behind
    :data:`FLAG_GLASS_EXPORT` (off by default).
    """

    name = "glass"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        as_json = bool(getattr(ns, "json", False))
        verb = getattr(ns, "glass_verb", None)
        try:
            if verb is None:
                standup = compute_glass_reading(direction="inbound")
                shipped = compute_glass_reading(direction="outbound")
                payload = {"standup": asdict(standup), "shipped": asdict(shipped)}
                ok = _direction_ok(standup) and _direction_ok(shipped)
                plain = f"{_line('standup', standup)} | {_line('shipped', shipped)}"
                return _glass_result(ok, payload, plain, as_json)

            if verb == "export":
                # Check the flag FIRST (cheaper, gate-before-fetch).
                overrides = parse_flag_overrides(getattr(ns, "flag", None))
                if not eval_flag(FLAG_GLASS_EXPORT, False, overrides):
                    message = flag_off_message(FLAG_GLASS_EXPORT)
                    return _glass_result(False, {"message": message}, message, as_json)
                standup = compute_glass_reading(direction="inbound")
                shipped = compute_glass_reading(direction="outbound")
                fmt = getattr(ns, "format", "markdown")
                table = render_glass_table({"standup": standup, "shipped": shipped}, fmt)
                return _glass_result(True, {"format": fmt, "table": table}, table, as_json)

            message = f"glass: unknown verb {verb!r}"
            return _glass_result(False, {"message": message}, message, as_json)
        except Exception as exc:  # noqa: BLE001 — duty boundary
            message = f"glass failed: {exc}"
            return _glass_result(False, {"message": message}, message, as_json)
