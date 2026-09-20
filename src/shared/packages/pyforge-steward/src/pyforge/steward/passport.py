"""Steward's ``passport`` duty — vendor Work Passport identity (Story 61.2,
spec-work-passports-dated-extracts CAP-2 / spec-pyforge-steward CAP-140).

Jira keys and GitHub numbers can collide across rooms, so identity is a
minted UUID, never a Jira key or GitHub number. Every ``mint`` call creates
a FRESH row -- two mints sharing the same ``vendor_id`` and the same
``jira_key`` never merge; the keys are nicknames on the row, not the
identity.

The durable record (``WorkPassport.vendor_id``) lives behind the
``pyforge-steward[dashboard]`` extra. ``mint_vendor_passport`` reaches it
through the one sanctioned dynamic base->dashboard idiom (see
``corridor.load_extract`` for the precedent): a lazy
``importlib.import_module`` call, refusing (never raising) when the extra is
not installed.

``PassportDuty`` never calls ``sys.exit`` (AD-8) -- it returns a
``DutyResult`` and ``cli.main`` projects it.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from .interfaces import DutyResult


class PassportMintError(ValueError):
    """A blank ``vendor_id``, or neither ``jira_key`` nor ``github_item_id``
    given -- a vendor passport must carry at least one nickname."""


def mint_vendor_passport(
    *,
    vendor_id: str,
    jira_key: str | None = None,
    github_item_id: str | None = None,
    title: str = "",
) -> dict[str, Any]:
    """Validate inputs, then reach the ORM via the sanctioned dynamic
    base->dashboard idiom. Raises :class:`PassportMintError` for a blank
    ``vendor_id`` or when neither nickname is given; otherwise refuses
    (never raises) when the ``[dashboard]`` extra is not installed, and
    returns ``dashboard/passport_mint.py``'s outcome dict verbatim.
    """
    if not vendor_id or not vendor_id.strip():
        raise PassportMintError("vendor_id is required")
    if not (jira_key or "").strip() and not (github_item_id or "").strip():
        raise PassportMintError("a vendor passport must carry at least one nickname (--jira-key or --github-item-id)")

    import importlib

    try:
        module = importlib.import_module("pyforge.steward.dashboard.passport_mint")
    except ImportError:
        return {
            "status": "refused",
            "vendor_id": vendor_id,
            "message": "pyforge-steward[dashboard] extra not installed",
        }

    return module.record_vendor_passport(
        vendor_id=vendor_id.strip(),
        jira_key=jira_key,
        github_item_id=github_item_id,
        title=title,
    )


def _mint_result(outcome: dict[str, Any], *, as_json: bool) -> DutyResult:
    """Every ``mint`` branch returns through here: one consistent ``--json``
    rule (``json.dumps(...)`` or the human-readable text, never a branch
    that forgets either) -- learned from Story 61.1's review finding that
    unifying the payload shape from the start beats doing it per branch."""
    ok = outcome.get("status") == "minted"
    if as_json:
        summary = json.dumps(outcome, indent=2, sort_keys=True)
    elif ok:
        summary = f"minted passport_id={outcome['passport_id']} vendor={outcome['vendor_id']}"
    else:
        summary = f"passport mint: {outcome['message']}"
    return DutyResult(ok=ok, summary=summary, details=outcome)


class PassportDuty:
    """``steward passport mint`` -- Story 61.2.

    Bare ``steward passport`` (no verb) refuses -- there is no config to
    report read-only on a bare invocation, unlike ``load``'s declared
    transports, so this mirrors ``RestoreDuty``'s bare-refuses shape rather
    than ``LoadDuty``'s bare-reports one.
    """

    name = "passport"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        as_json = bool(getattr(ns, "json", False))
        try:
            verb = getattr(ns, "passport_verb", None)
            if verb is None:
                return DutyResult(ok=False, summary="passport: a verb is required (mint)")

            vendor_id = ns.vendor_id
            jira_key = ns.jira_key
            github_item_id = ns.github_item_id
            title = ns.title
            try:
                outcome = mint_vendor_passport(
                    vendor_id=vendor_id,
                    jira_key=jira_key,
                    github_item_id=github_item_id,
                    title=title,
                )
            except PassportMintError as exc:
                outcome = {"status": "error", "vendor_id": vendor_id, "message": str(exc)}
            return _mint_result(outcome, as_json=as_json)
        except Exception as exc:  # noqa: BLE001 — duty boundary
            return DutyResult(ok=False, summary=f"passport failed: {exc}")
