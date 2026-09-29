"""Steward's ``glass`` duty — the as-of glass over the inbound corridor
(Story 61.3, spec-work-passports-dated-extracts CAP-3 / spec-pyforge-steward
CAP-141).

Standup asks "any news from the vendor?" — this module answers by reading
the most recent ``CorridorLoad`` row for a direction (Story 61.1) and
classifying it: ``unborn`` (nothing has ever loaded), ``fresh`` (today's
drop), ``stale`` (the last drop was not today — "yesterday remains
visible"), or ``failed`` (today's drop is a zero-byte file). ``standup`` and
``shipped`` are two labeled perspectives on the SAME reading — both read
``direction="inbound"`` — never two different directions; "do not invent a
second standup source of truth" protects exactly that (see the story spec's
Design Notes and its 2026-09-19 ``bad_spec`` amendment).

"Empty" is answered from ``CorridorLoad.batch_sha`` alone, by comparing it
to the well-known SHA-256 of zero bytes — ``corridor.py``'s ``load_extract``
deliberately never parses file content, and this module does not either;
no new column, no migration, no loader change.

The durable record lives behind the ``pyforge-steward[dashboard]`` extra.
``compute_glass_reading`` reaches it through the one sanctioned dynamic
base->dashboard idiom (see ``corridor.load_extract`` / ``passport.
mint_vendor_passport`` for the precedent): a lazy ``importlib.import_module``
call, refusing (never raising) when the extra is not installed.

``GlassDuty`` never calls ``sys.exit`` (AD-8) — it returns a ``DutyResult``
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

FLAG_GLASS_EXPORT = "enable_glass_export"
GLASS_EXPORT_FORMATS: tuple[str, ...] = ("csv", "markdown")


class GlassError(ValueError):
    """Unknown direction, or a naive (non-timezone-aware) ``now``."""


@dataclass(frozen=True)
class GlassReading:
    """One as-of reading. ``state`` and ``loaded_at`` are ``None`` only when
    ``status == "refused"`` (the ``[dashboard]`` extra is not installed, or
    Django itself refused)."""

    status: str  # "ok" | "refused"
    direction: str
    state: str | None  # one of GLASS_STATES; None when status == "refused"
    waybill: str | None
    batch_sha: str | None
    loaded_at: str | None  # ISO 8601; None when unborn/refused
    message: str = ""


def compute_glass_reading(*, direction: str, now: datetime | None = None) -> GlassReading:
    """Read the most recent ``CorridorLoad`` for ``direction`` and classify
    its freshness as of ``now`` (default: the real current UTC time)."""
    if direction not in DIRECTIONS:
        raise GlassError(f"unknown direction {direction!r}; must be one of {DIRECTIONS!r}")
    if now is not None and now.tzinfo is None:
        raise GlassError("now must be timezone-aware")
    reference_now = now or datetime.now(timezone.utc)

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

    loaded_at_raw = outcome["loaded_at"]
    loaded_at_dt = datetime.fromisoformat(loaded_at_raw)
    if loaded_at_dt.tzinfo is not None:
        loaded_at_dt = loaded_at_dt.astimezone(timezone.utc)
    is_today = loaded_at_dt.date() == reference_now.astimezone(timezone.utc).date()

    batch_sha = outcome["batch_sha"]
    waybill = outcome["waybill"]

    if is_today and batch_sha == EMPTY_FILE_SHA256:
        state = "failed"
        message = "today's on-time file is empty"
    elif is_today:
        state = "fresh"
        message = ""
    else:
        # Generalizes the I/O Matrix's literal "yesterday" example to ANY
        # most-recent load that is not from today — see the story spec's
        # Design Notes.
        state = "stale"
        message = "no drop yet today -- showing the last known waybill"

    return GlassReading(
        status="ok",
        direction=direction,
        state=state,
        waybill=waybill,
        batch_sha=batch_sha,
        loaded_at=loaded_at_raw,
        message=message,
    )


def _direction_ok(reading: GlassReading) -> bool:
    # "Empty on-time file fails" is the only state this story's own
    # Boundaries call a failure; "stale"/"unborn" are legitimate, non-failing
    # answers ("late drop leaves yesterday stale" is explicitly NOT a fail).
    return reading.status == "ok" and reading.state != "failed"


def _escape_cell(text: str) -> str:
    """Markdown table cells break on an unescaped ``|`` or a raw newline —
    ``waybill``/``message`` are caller-supplied free text (Story 61.1)."""
    return text.replace("|", "\\|").replace("\n", " ")


def render_glass_table(readings: dict[str, GlassReading], fmt: str) -> str:
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

    # fmt == "markdown"
    lines = [
        f"| {' | '.join(header)} |",
        "|---|---|---|---|---|---|",
    ]
    for label, reading in rows:
        lines.append(
            f"| {label} | {reading.direction} | {_escape_cell(reading.state or 'refused')} | "
            f"{_escape_cell(reading.waybill or '')} | {reading.loaded_at or ''} | "
            f"{_escape_cell(reading.message)} |"
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
    Story 61.2's own review lesson from the start (never unify per-branch
    after the fact)."""
    return DutyResult(
        ok=ok,
        summary=(json.dumps(payload, indent=2, sort_keys=True) if as_json else plain_summary),
        details=payload,
    )


class GlassDuty:
    """``steward glass [export]`` — Story 61.3.

    Bare ``steward glass`` reports both the standup and shipped readings
    (the same inbound reading, twice, under two labels). ``export`` renders
    a two-row CSV/markdown table, gated behind ``FLAG_GLASS_EXPORT``
    (off by default).
    """

    name = "glass"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        as_json = bool(getattr(ns, "json", False))
        try:
            verb = getattr(ns, "glass_verb", None)

            if verb is None:
                reading = compute_glass_reading(direction="inbound")
                standup = shipped = reading
                payload = {"standup": asdict(standup), "shipped": asdict(shipped)}
                ok = _direction_ok(standup) and _direction_ok(shipped)
                plain = f"{_line('standup', standup)} | {_line('shipped', shipped)}"
                return _glass_result(ok, payload, plain, as_json)

            if verb == "export":
                overrides = parse_flag_overrides(getattr(ns, "flag", None))
                if not eval_flag(FLAG_GLASS_EXPORT, False, overrides):
                    message = flag_off_message(FLAG_GLASS_EXPORT)
                    return _glass_result(False, {"message": message}, message, as_json)
                reading = compute_glass_reading(direction="inbound")
                standup = shipped = reading
                fmt = getattr(ns, "format", "markdown")
                table = render_glass_table({"standup": standup, "shipped": shipped}, fmt)
                return _glass_result(True, {"format": fmt, "table": table}, table, as_json)

            message = f"glass: unknown verb {verb!r}"
            return _glass_result(False, {"message": message}, message, as_json)
        except Exception as exc:  # noqa: BLE001 — duty boundary
            message = f"glass failed: {exc}"
            return _glass_result(False, {"message": message}, message, as_json)
