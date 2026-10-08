"""Steward's ``quarantine`` duty — missing-passport mint-then-reject (Story 61.5,
spec-work-passports-dated-extracts CAP-5 / spec-pyforge-steward CAP-143).

Unlinked inbound rows wait on a quarantine shelf until a human links
nicknames. During the configured missing-passport window (default 14 days,
``corridor/corridor.yaml``) a row without a passport is minted into
quarantine; after that window mint is refused but the row still lands on
the shelf with no ``passport_id``. There is no title-match endpoint.

``QuarantineDuty`` never calls ``sys.exit`` (AD-8) — it returns a
``DutyResult`` and ``cli.main`` projects it.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .corridor import CONFIG_FILENAME, CorridorConfigError, default_corridor_dir, load_config
from .interfaces import DutyResult


class QuarantineAdmitError(ValueError):
    """Blank ``vendor_id`` or neither nickname given."""


def admit_inbound_without_passport(
    *,
    vendor_id: str,
    jira_key: str | None = None,
    github_item_id: str | None = None,
    title: str = "",
    arrived_at: datetime | None = None,
    config: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate inputs, load corridor config, reach the ORM via the sanctioned
    dynamic base→dashboard idiom."""
    if not vendor_id or not vendor_id.strip():
        raise QuarantineAdmitError("vendor_id is required")
    if not (jira_key or "").strip() and not (github_item_id or "").strip():
        raise QuarantineAdmitError("an inbound row must carry at least one nickname (--jira-key or --github-item-id)")

    if config is not None:
        config_path = config / CONFIG_FILENAME if config.is_dir() else config
    else:
        config_path = default_corridor_dir() / CONFIG_FILENAME
    try:
        corridor_config = load_config(config_path)
    except CorridorConfigError as exc:
        return {"status": "refused", "vendor_id": vendor_id, "message": str(exc)}

    reference_arrived = arrived_at if arrived_at is not None else datetime.now(timezone.utc)
    if reference_arrived.tzinfo is None:
        reference_arrived = reference_arrived.replace(tzinfo=timezone.utc)

    import importlib

    try:
        module = importlib.import_module("pyforge.steward.dashboard.quarantine_admit")
    except ImportError:
        return {
            "status": "refused",
            "vendor_id": vendor_id,
            "message": "pyforge-steward[dashboard] extra not installed",
        }

    return module.record_quarantine_admit(
        vendor_id=vendor_id.strip(),
        jira_key=jira_key,
        github_item_id=github_item_id,
        title=title,
        arrived_at=reference_arrived,
        missing_passport_window_days=corridor_config.quarantine.missing_passport_window_days,
        now=now,
    )


def list_quarantine_shelf(*, include_linked: bool = False) -> dict[str, Any]:
    import importlib

    try:
        module = importlib.import_module("pyforge.steward.dashboard.quarantine_admit")
    except ImportError:
        return {"status": "refused", "message": "pyforge-steward[dashboard] extra not installed"}
    return module.list_quarantine_shelf_rows(include_linked=include_linked)


def _quarantine_result(outcome: dict[str, Any], *, as_json: bool, ok: bool) -> DutyResult:
    if as_json:
        summary = json.dumps(outcome, indent=2, sort_keys=True)
    elif outcome.get("status") == "quarantined":
        mint = outcome.get("mint_status", "")
        pid = outcome.get("passport_id") or "none"
        summary = f"quarantined row_id={outcome['row_id']} mint={mint} passport_id={pid}"
    elif outcome.get("status") == "ok":
        summary = f"quarantine shelf: {outcome.get('count', 0)} row(s)"
    else:
        summary = f"quarantine: {outcome.get('message', outcome.get('status', 'failed'))}"
    return DutyResult(ok=ok, summary=summary, details=outcome)


class QuarantineDuty:
    """``steward quarantine admit|shelf`` — Story 61.5."""

    name = "quarantine"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        as_json = bool(getattr(ns, "json", False))
        try:
            verb = getattr(ns, "quarantine_verb", None)
            if verb is None:
                return DutyResult(ok=False, summary="quarantine: a verb is required (admit, shelf)")

            corridor_raw = getattr(ns, "corridor", None)
            config_path = Path(corridor_raw) if corridor_raw else None

            if verb == "shelf":
                outcome = list_quarantine_shelf(include_linked=bool(getattr(ns, "include_linked", False)))
                ok = outcome.get("status") == "ok"
                return _quarantine_result(outcome, as_json=as_json, ok=ok)

            if verb == "admit":
                arrived_raw = getattr(ns, "arrived_at", None)
                arrived_at = None
                if arrived_raw:
                    arrived_at = datetime.fromisoformat(arrived_raw.replace("Z", "+00:00"))
                try:
                    outcome = admit_inbound_without_passport(
                        vendor_id=ns.vendor_id,
                        jira_key=ns.jira_key,
                        github_item_id=ns.github_item_id,
                        title=getattr(ns, "title", "") or "",
                        arrived_at=arrived_at,
                        config=config_path,
                    )
                except QuarantineAdmitError as exc:
                    outcome = {"status": "error", "vendor_id": ns.vendor_id, "message": str(exc)}
                    return _quarantine_result(outcome, as_json=as_json, ok=False)

                ok = outcome.get("status") == "quarantined"
                return _quarantine_result(outcome, as_json=as_json, ok=ok)

            return DutyResult(ok=False, summary=f"quarantine: unknown verb {verb!r}")
        except Exception as exc:  # noqa: BLE001 — duty boundary
            return DutyResult(ok=False, summary=f"quarantine failed: {exc}")
