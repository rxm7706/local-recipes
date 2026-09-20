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

**Since Story 61.4** (spec-work-passports-dated-extracts CAP-4 /
spec-pyforge-steward CAP-142 — the signed-outbound-slice gate): a dump of
Jira or factory BMAD can leave unsigned today unless this gate closes it.
Default deny — an ``outbound`` load additionally requires a named
``slice_name`` and a recorded ``signer`` (the named ``outbound-signer`` role
on the existing app) before ``load_extract`` will create a new row; both are
validated only on the CREATE path (an idempotent repeat needs neither,
matching the transport-declared-on check's own idempotency-first shape
immediately below), and both are recorded on the same ``CorridorLoad`` row
``corridor_load.py`` already writes — no second table, no second loader.
"The vendor loads our file — we do not PAT into their org": this gate never
adds a distinct outbound transport that pushes anywhere; it reuses the SAME
declared transports (``corridor.yaml``) as inbound.
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

# Story 61.4: the named role recorded on an outbound `CorridorLoad` row --
# a label this module documents and records, not a live permission check
# (Dream ruling: "a person or GitHub team on the existing app ... default:
# the steward operator running Drop Night"; v1 records who signed, it does
# not authenticate against a roster).
SIGNER_ROLE = "outbound-signer"


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
            f"{document_path}: top-level document must be a mapping, got {type(document).__name__}"
        )
    return document


def _normalize_state(document_path: Path, raw: object, where: str) -> str:
    # Bare `on`/`off` are YAML 1.1 booleans; accept them as the words they were.
    if isinstance(raw, bool):
        raw = STATE_ON if raw else STATE_OFF
    if not isinstance(raw, str) or raw.strip() not in STATES:
        raise CorridorConfigError(f"{document_path}: '{where}.state' = {raw!r} is not one of {STATES!r}")
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
    """What ``load_extract`` returns.

    ``slice_name``/``signer`` (Story 61.4) are blank on every ``inbound``
    outcome; on ``outbound`` they carry the named slice and recorded signer
    that were validated (on create) or ORIGINALLY recorded (on an idempotent
    repeat) -- never the values a repeat call happened to pass.
    """

    status: str  # "loaded" | "idempotent" | "refused"
    direction: str
    batch_sha: str
    waybill: str
    transport: str
    slice_name: str = ""
    signer: str = ""
    message: str = ""


def _outcome_from_result(result: dict[str, Any]) -> LoadOutcome:
    return LoadOutcome(
        status=result["status"],
        direction=result["direction"],
        batch_sha=result["batch_sha"],
        waybill=result["waybill"],
        transport=result["transport"],
        slice_name=result.get("slice_name", ""),
        signer=result.get("signer", ""),
        message=result.get("message", ""),
    )


def load_extract(
    *,
    direction: str,
    batch_sha: str,
    waybill: str,
    transport: str,
    config: CorridorConfig,
    slice_name: str = "",
    signer: str = "",
) -> LoadOutcome:
    """Idempotent on ``(direction, batch_sha, waybill)`` ALONE — no transport
    qualifier. A repeat drop of an already-loaded file is a no-op regardless
    of which transport this call names, even an unknown or declared-off one:
    the existing-record check runs before transport validation, so only the
    path that would actually CREATE a new row needs a transport that is both
    declared and ``state: on``.

    ``slice_name``/``signer`` (Story 61.4) are ignored entirely for
    ``direction="inbound"``. For ``direction="outbound"``, default deny: on
    the CREATE path (no existing record — same "would create" branch the
    transport check gates), both must be non-blank or this raises
    :class:`CorridorLoadError` naming which is missing, before the transport
    is even consulted. An idempotent repeat needs neither (nothing new is
    being signed), matching the transport-declared-on check's own
    idempotency-first shape one branch below.

    Raises :class:`CorridorLoadError` on that create path — for an outbound
    load missing a slice/signer, or for an unknown/declared-off transport
    (naming the declared transports so a typo is diagnosable); otherwise
    reaches ``dashboard/corridor_load.py`` through the one sanctioned dynamic
    base→dashboard idiom, refusing (never raising) when the ``[dashboard]``
    extra is not installed.
    """
    if direction not in DIRECTIONS:
        raise CorridorLoadError(f"unknown direction {direction!r}; must be one of {DIRECTIONS!r}")

    # The gate applies to `outbound` only -- normalize here, before either
    # value is used anywhere below (a record call or the returned outcome),
    # so an inbound caller passing stray slice/signer values never has them
    # persisted or echoed back.
    if direction != "outbound":
        slice_name = ""
        signer = ""

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
            slice_name=slice_name,
            signer=signer,
            message="pyforge-steward[dashboard] extra not installed",
        )

    # Read-only probe: does a record already exist for this (direction,
    # batch_sha, waybill)? If so, it is idempotent no matter what transport
    # this call passed -- report it immediately without ever consulting
    # `config` for this call's (possibly unknown / off) transport, and
    # without re-validating slice/signer (Story 61.4) -- an idempotent
    # repeat reports the ORIGINALLY recorded ones, never re-signs.
    probe = module.record_corridor_load(
        direction=direction,
        batch_sha=batch_sha,
        waybill=waybill,
        transport=transport,
        create_if_missing=False,
    )
    if probe["status"] != "not_found":
        return _outcome_from_result(probe)

    # No existing record -- this call WOULD create one. Story 61.4: default
    # deny an outbound create with no named slice or no recorded signer,
    # BEFORE the transport is even checked.
    if direction == "outbound":
        slice_name = (slice_name or "").strip()
        signer = (signer or "").strip()
        if not slice_name:
            raise CorridorLoadError(
                "an outbound load requires a named slice -- default deny "
                "(Story 61.4, spec-work-passports-dated-extracts CAP-4)"
            )
        if not signer:
            raise CorridorLoadError(
                f"an outbound load requires a recorded {SIGNER_ROLE} -- default deny "
                "(Story 61.4, spec-work-passports-dated-extracts CAP-4)"
            )

    # Only now (past the slice/signer gate, when it applies) does the
    # transport need to be declared and on.
    decl = config.transport(transport)
    declared = ", ".join(t.name for t in config.transports) or "(none declared)"
    if decl is None:
        raise CorridorLoadError(f"unknown transport {transport!r}; declared transports: {declared}")
    if decl.state != STATE_ON:
        raise CorridorLoadError(
            f"transport {transport!r} is declared 'off' in corridor.yaml (declared transports: {declared})"
        )

    result = module.record_corridor_load(
        direction=direction,
        batch_sha=batch_sha,
        waybill=waybill,
        transport=transport,
        slice_name=slice_name,
        signer=signer,
    )
    return _outcome_from_result(result)


def _outcome_payload(outcome: LoadOutcome) -> dict[str, object]:
    return {
        "status": outcome.status,
        "direction": outcome.direction,
        "batch_sha": outcome.batch_sha,
        "waybill": outcome.waybill,
        "transport": outcome.transport,
        "slice_name": outcome.slice_name,
        "signer": outcome.signer,
        "message": outcome.message,
    }


# Mirrors `dashboard/models.py`'s `CorridorLoad.waybill` field
# (`CharField(max_length=128)`). SQLite (every test) does not enforce
# `VARCHAR(n)`; PostgreSQL ("the existing Postgres app" this story targets)
# does -- the same divergence `dashboard/audit.py`'s own module docstring
# documents and guards against for `AuditEntry`. Enforce the cap in Python,
# here, before an over-length waybill ever reaches the ORM.
_MAX_WAYBILL_LENGTH = 128


def _load_result(ok: bool, text: str, payload: dict[str, object], *, as_json: bool) -> DutyResult:
    """Every ``LoadDuty.run`` branch returns through here: one consistent
    payload shape (``"ok"`` always present, merged with the branch's own
    fields) and one consistent ``--json`` rule (``json.dumps(...)`` or the
    human-readable ``text``, never a branch that forgets either)."""
    full_payload: dict[str, object] = {"ok": ok, **payload}
    summary = json.dumps(full_payload, indent=2, sort_keys=True) if as_json else text
    return DutyResult(ok=ok, summary=summary, details=full_payload)


class LoadDuty:
    """``steward load [inbound|outbound]`` — Story 61.1; the ``outbound``
    verb's default-deny slice+signer gate is Story 61.4.

    Bare ``steward load`` (no verb) reports the declared transports and their
    states, read-only — no Django/DB touch at all. ``inbound``/``outbound``
    load a file, idempotent on batch sha + waybill. ``outbound`` additionally
    requires ``--slice``/``--signer`` (default deny — a blank one refuses,
    never a raised traceback).
    """

    name = "load"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        as_json = bool(getattr(ns, "json", False))
        try:
            root = repo_root()
            corridor_arg = getattr(ns, "corridor", None)
            corridor_dir = Path(corridor_arg).resolve() if corridor_arg else default_corridor_dir(root)
            try:
                config = load_config(corridor_dir / CONFIG_FILENAME)
            except CorridorConfigError as exc:
                return _load_result(False, f"load: {exc}", {"message": str(exc)}, as_json=as_json)

            verb = getattr(ns, "load_verb", None)
            if verb is None:
                transports = [{"name": t.name, "state": t.state} for t in config.transports]
                text = ", ".join(f"{t['name']}: {t['state']}" for t in transports)
                return _load_result(True, text, {"transports": transports}, as_json=as_json)

            waybill = ns.waybill
            if len(waybill) > _MAX_WAYBILL_LENGTH:
                text = (
                    f"load {verb}: waybill is {len(waybill)} characters, over the {_MAX_WAYBILL_LENGTH}-character limit"
                )
                return _load_result(False, text, {"message": text}, as_json=as_json)

            if not Path(ns.file).is_file():
                text = f"load {verb}: {ns.file}: not found"
                return _load_result(False, text, {"message": text}, as_json=as_json)
            data = Path(ns.file).read_bytes()
            batch_sha = compute_batch_sha(data)
            transport = getattr(ns, "transport", "app-upload")
            slice_name = getattr(ns, "slice_name", "") or ""
            signer = getattr(ns, "signer", "") or ""
            try:
                outcome = load_extract(
                    direction=verb,
                    batch_sha=batch_sha,
                    waybill=waybill,
                    transport=transport,
                    config=config,
                    slice_name=slice_name,
                    signer=signer,
                )
            except CorridorLoadError as exc:
                text = f"load {verb}: {exc}"
                return _load_result(False, text, {"message": text}, as_json=as_json)

            payload = _outcome_payload(outcome)
            if outcome.status in ("loaded", "idempotent"):
                text = (
                    f"{outcome.status}: {verb} waybill={outcome.waybill} "
                    f"sha={outcome.batch_sha[:12]} via {outcome.transport}"
                )
                if verb == "outbound":
                    text += f' slice="{outcome.slice_name}" signer="{outcome.signer}"'
                return _load_result(True, text, payload, as_json=as_json)
            if outcome.status == "error":
                text = f"load {verb}: data error: {outcome.message}"
            else:
                # status == "refused" (e.g. the [dashboard] extra not installed)
                text = f"load {verb}: {outcome.message}"
            return _load_result(False, text, payload, as_json=as_json)
        except Exception as exc:  # noqa: BLE001 — duty boundary
            return DutyResult(ok=False, summary=f"load failed: {exc}")
