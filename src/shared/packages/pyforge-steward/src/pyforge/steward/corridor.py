"""Steward's ``load`` duty — corridor transports (Story 61.1,
spec-work-passports-dated-extracts CAP-1 / spec-pyforge-steward CAP-139).

Vendor and estate lists have no idempotent drop path today. This module is
the corridor: every transport writes the SAME loader, keyed on batch sha +
waybill, so a repeat drop of an already-loaded file is a no-op rather than a
duplicate row. ``corridor/corridor.yaml`` (tracked, git is the edit store —
same philosophy as ``catalog/catalog.yaml``) declares which transports are
active; the default transport is ``app-upload``, ``shared-folder`` and
``email`` are ``state: off`` slots until a later story enables them (v1 has
no third-party transport plugin to bind, so a transport row here is only a
provenance label + on/off gate, never a distinct ingestion code path).

The durable idempotency record (``CorridorLoad``) lives behind the
``pyforge-steward[dashboard]`` extra. ``load_extract`` reaches it through the
one sanctioned dynamic base→dashboard idiom (see
``sprint_ledger_query.sync_to_postgres`` for the precedent): a lazy
``importlib.import_module`` call, refusing (never raising) when the extra is
not installed.

``LoadDuty`` never calls ``sys.exit`` (AD-8) — it returns a ``DutyResult``
and ``cli.main`` projects it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .bootstrap import repo_root
from .interfaces import DutyResult

CORRIDOR_RELATIVE = Path("src/shared/packages/pyforge-steward/corridor")
CONFIG_FILENAME = "corridor.yaml"

STATES: tuple[str, ...] = ("on", "off")
STATE_ON, STATE_OFF = STATES

DIRECTIONS: tuple[str, ...] = ("inbound", "outbound")


class CorridorConfigError(ValueError):
    """A missing or malformed ``corridor.yaml`` document."""


@dataclass(frozen=True)
class TransportDecl:
    """One declared transport: ``transports.<name>{state}``."""

    name: str
    state: str


@dataclass(frozen=True)
class CorridorConfig:
    """The operator-declared corridor: which transports are active."""

    transports: tuple[TransportDecl, ...]

    def transport(self, name: str) -> TransportDecl | None:
        for decl in self.transports:
            if decl.name == name:
                return decl
        return None


def default_corridor_dir(root: Path | None = None) -> Path:
    """``src/shared/packages/pyforge-steward/corridor`` at the repo root."""
    return (root if root is not None else repo_root()) / CORRIDOR_RELATIVE


def _load_yaml_mapping(document_path: Path, *, what: str) -> dict[str, Any]:
    """``yaml.safe_load`` a file that must be a mapping — the four named load
    failures (``catalog.py``/``sync.py`` precedent): missing, malformed,
    unreadable, not-a-mapping."""
    if not document_path.is_file():
        raise CorridorConfigError(f"{document_path}: {what} not found")
    try:
        with document_path.open("r", encoding="utf-8") as f:
            document = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise CorridorConfigError(f"{document_path}: malformed YAML: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise CorridorConfigError(f"{document_path}: unreadable: {exc}") from exc
    if document is None:
        document = {}
    if not isinstance(document, dict):
        raise CorridorConfigError(
            f"{document_path}: top-level document must be a mapping, got "
            f"{type(document).__name__}"
        )
    return document


def _normalize_state(document_path: Path, raw: object, where: str) -> str:
    # Bare `on`/`off` are YAML 1.1 booleans; accept them as the words they were.
    if isinstance(raw, bool):
        raw = STATE_ON if raw else STATE_OFF
    if not isinstance(raw, str) or raw.strip() not in STATES:
        raise CorridorConfigError(
            f"{document_path}: '{where}.state' = {raw!r} is not one of {STATES!r}"
        )
    return raw.strip()


def load_config(config_path: str | Path) -> CorridorConfig:
    """Load ``corridor.yaml``-shaped YAML from ``config_path`` (``yaml.safe_load``
    only): a ``transports:`` mapping of ``{name: {state: "on"|"off"}}``."""
    document_path = Path(config_path)
    document = _load_yaml_mapping(document_path, what="corridor config")

    section = document.get("transports")
    if section is None:
        raise CorridorConfigError(f"{document_path}: 'transports' section missing")
    if not isinstance(section, dict):
        raise CorridorConfigError(f"{document_path}: 'transports' section must be a mapping")

    decls: list[TransportDecl] = []
    for name, body in section.items():
        # A bare `on:` / `yes:` key parses to a YAML boolean; it is not a name.
        if not isinstance(name, str) or not name.strip():
            raise CorridorConfigError(
                f"{document_path}: 'transports' key {name!r} must be a non-empty string "
                "(quote it if YAML reads it as a boolean)"
            )
        where = f"transports.{name}"
        if not isinstance(body, dict):
            raise CorridorConfigError(f"{document_path}: '{where}' must be a mapping")
        state = _normalize_state(document_path, body.get("state"), where)
        decls.append(TransportDecl(name=name.strip(), state=state))
    return CorridorConfig(transports=tuple(decls))


def compute_batch_sha(data: bytes) -> str:
    """The corridor's idempotency key half: a plain SHA-256 of the file bytes."""
    return hashlib.sha256(data).hexdigest()


class CorridorLoadError(ValueError):
    """An unknown transport name, or a transport whose declared ``state`` is
    ``"off"``."""


@dataclass(frozen=True)
class LoadOutcome:
    """What ``load_extract`` returns."""

    status: str  # "loaded" | "idempotent" | "refused"
    direction: str
    batch_sha: str
    waybill: str
    transport: str
    message: str = ""


def load_extract(
    *,
    direction: str,
    batch_sha: str,
    waybill: str,
    transport: str,
    config: CorridorConfig,
) -> LoadOutcome:
    """Idempotent on ``(direction, batch_sha, waybill)`` — a repeat drop of the
    same file under the same waybill is a no-op, never a duplicate row.

    Raises :class:`CorridorLoadError` for an unknown or declared-off
    transport (naming the declared transports so a typo is diagnosable);
    otherwise reaches ``dashboard/corridor_load.py`` through the one
    sanctioned dynamic base→dashboard idiom, refusing (never raising) when
    the ``[dashboard]`` extra is not installed.
    """
    if direction not in DIRECTIONS:
        raise CorridorLoadError(
            f"unknown direction {direction!r}; must be one of {DIRECTIONS!r}"
        )
    decl = config.transport(transport)
    declared = ", ".join(t.name for t in config.transports) or "(none declared)"
    if decl is None:
        raise CorridorLoadError(
            f"unknown transport {transport!r}; declared transports: {declared}"
        )
    if decl.state != STATE_ON:
        raise CorridorLoadError(
            f"transport {transport!r} is declared 'off' in corridor.yaml "
            f"(declared transports: {declared})"
        )

    import importlib

    try:
        module = importlib.import_module("pyforge.steward.dashboard.corridor_load")
    except ImportError:
        return LoadOutcome(
            status="refused",
            direction=direction,
            batch_sha=batch_sha,
            waybill=waybill,
            transport=transport,
            message="pyforge-steward[dashboard] extra not installed",
        )
    result = module.record_corridor_load(
        direction=direction, batch_sha=batch_sha, waybill=waybill, transport=transport
    )
    return LoadOutcome(
        status=result["status"],
        direction=result["direction"],
        batch_sha=result["batch_sha"],
        waybill=result["waybill"],
        transport=result["transport"],
        message=result.get("message", ""),
    )


def _outcome_payload(outcome: LoadOutcome) -> dict[str, object]:
    return {
        "status": outcome.status,
        "direction": outcome.direction,
        "batch_sha": outcome.batch_sha,
        "waybill": outcome.waybill,
        "transport": outcome.transport,
        "message": outcome.message,
    }


class LoadDuty:
    """``steward load [inbound|outbound]`` — Story 61.1.

    Bare ``steward load`` (no verb) reports the declared transports and their
    states, read-only — no Django/DB touch at all. ``inbound``/``outbound``
    load a file, idempotent on batch sha + waybill.
    """

    name = "load"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        as_json = bool(getattr(ns, "json", False))
        try:
            root = repo_root()
            corridor_arg = getattr(ns, "corridor", None)
            corridor_dir = (
                Path(corridor_arg).resolve() if corridor_arg else default_corridor_dir(root)
            )
            try:
                config = load_config(corridor_dir / CONFIG_FILENAME)
            except CorridorConfigError as exc:
                payload = {"ok": False, "message": str(exc)}
                return DutyResult(
                    ok=False,
                    summary=json.dumps(payload, indent=2, sort_keys=True) if as_json else f"load: {exc}",
                    details=payload,
                )

            verb = getattr(ns, "load_verb", None)
            if verb is None:
                transports = [{"name": t.name, "state": t.state} for t in config.transports]
                payload = {"transports": transports}
                if as_json:
                    summary = json.dumps(payload, indent=2, sort_keys=True)
                else:
                    summary = ", ".join(f"{t['name']}: {t['state']}" for t in transports)
                return DutyResult(ok=True, summary=summary, details=payload)

            if not Path(ns.file).is_file():
                return DutyResult(ok=False, summary=f"load {verb}: {ns.file}: not found")
            data = Path(ns.file).read_bytes()
            batch_sha = compute_batch_sha(data)
            transport = getattr(ns, "transport", "app-upload")
            try:
                outcome = load_extract(
                    direction=verb,
                    batch_sha=batch_sha,
                    waybill=ns.waybill,
                    transport=transport,
                    config=config,
                )
            except CorridorLoadError as exc:
                return DutyResult(ok=False, summary=f"load {verb}: {exc}")

            payload = _outcome_payload(outcome)
            if outcome.status in ("loaded", "idempotent"):
                text = (
                    f"{outcome.status}: {verb} waybill={outcome.waybill} "
                    f"sha={outcome.batch_sha[:12]} via {outcome.transport}"
                )
                return DutyResult(
                    ok=True,
                    summary=json.dumps(payload, indent=2, sort_keys=True) if as_json else text,
                    details=payload,
                )
            # status == "refused"
            text = f"load {verb}: {outcome.message}"
            return DutyResult(
                ok=False,
                summary=json.dumps(payload, indent=2, sort_keys=True) if as_json else text,
                details=payload,
            )
        except Exception as exc:  # noqa: BLE001 — duty boundary
            return DutyResult(ok=False, summary=f"load failed: {exc}")
