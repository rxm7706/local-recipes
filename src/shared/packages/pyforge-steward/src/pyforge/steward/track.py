"""Assemble one tracked ``track.json`` per run (Story 53.3 / hub:CAP-3).

Marshal relays the field enumeration (Ops/Gates evidence shapes:
``journal.jsonl``, ``gate-record.json``, ``state.json``). This module
encodes that list — it does not import ``pyforge.marshal``. Steward writes
the Track; raw run payloads stay where they are.

Retention is stated on every record: Track kept indefinitely, raw payload
90 days. Missing optional groups stay ``null`` or ``[]`` — never invented
from policy TOML.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pyforge.core.atomic_write import atomic_write_text

from .interfaces import DutyResult

# Marshal-relayed frozen field list (hub:CAP-3 / B8). Documented in
# docs/foundry/tracks/FIELDS.md. Additive schema growth only.
TRACK_FIELDS: tuple[str, ...] = (
    "run_id",
    "timestamps",
    "tree_revision",
    "guards",
    "gates",
    "model_adapter",
    "human_approvals_overrides",
    "retention",
)

RETENTION: dict[str, object] = {
    "track": "indefinite",
    "raw_payload_days": 90,
}

_JOURNAL = "journal.jsonl"
_GATE_RECORD = "gate-record.json"
_STATE = "state.json"
_TRACK_VERBS: tuple[str, ...] = ("assemble",)


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return None
    return raw if isinstance(raw, dict) else None


def _read_journal(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            entries.append(parsed)
    return entries


def _first_str(*candidates: object) -> str | None:
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _payload(entry: dict[str, Any]) -> dict[str, Any]:
    payload = entry.get("payload")
    return payload if isinstance(payload, dict) else {}


def _collect_run_id(
    journal: list[dict[str, Any]],
    state: dict[str, Any] | None,
    run_dir: Path,
) -> str:
    for entry in journal:
        found = _first_str(entry.get("run_id"))
        if found is not None:
            return found
    if state is not None:
        found = _first_str(state.get("run_id"), state.get("id"))
        if found is not None:
            return found
    return run_dir.name


def _collect_timestamps(
    journal: list[dict[str, Any]],
    gate_record: dict[str, Any] | None,
    state: dict[str, Any] | None,
) -> dict[str, str | None]:
    stamps = [entry.get("ts") for entry in journal if isinstance(entry.get("ts"), str) and entry["ts"].strip()]
    started = stamps[0] if stamps else None
    ended = stamps[-1] if stamps else None
    if started is None and gate_record is not None:
        started = _first_str(gate_record.get("timestamp"))
    if state is not None:
        started = started or _first_str(state.get("started_at"), state.get("started"), state.get("ts_start"))
        ended = ended or _first_str(state.get("ended_at"), state.get("ended"), state.get("ts_end"))
    return {"started_at": started, "ended_at": ended}


def _collect_tree_revision(
    gate_record: dict[str, Any] | None,
    state: dict[str, Any] | None,
) -> str | None:
    if gate_record is not None:
        found = _first_str(gate_record.get("tree_revision"))
        if found is not None:
            return found
    if state is not None:
        return _first_str(
            state.get("tree_revision"),
            state.get("git_sha"),
            state.get("revision"),
        )
    return None


def _guard_from_command(command: object) -> dict[str, object] | None:
    if not isinstance(command, dict):
        return None
    name = _first_str(command.get("command"))
    if name is None:
        return None
    result: dict[str, object] = {}
    if "returncode" in command:
        result["returncode"] = command["returncode"]
    if "resolvable" in command:
        result["resolvable"] = command["resolvable"]
    return {"stage": "verify", "name": name, "result": result}


def _collect_guards(
    journal: list[dict[str, Any]],
    gate_record: dict[str, Any] | None,
) -> list[dict[str, object]]:
    guards: list[dict[str, object]] = []
    if gate_record is not None:
        commands = gate_record.get("commands")
        if isinstance(commands, list):
            for command in commands:
                guard = _guard_from_command(command)
                if guard is not None:
                    guards.append(guard)
    for entry in journal:
        kind = entry.get("kind")
        if not isinstance(kind, str) or not kind.startswith("guard."):
            continue
        payload = _payload(entry)
        name = _first_str(payload.get("name"), kind)
        if name is None:
            continue
        stage = _first_str(payload.get("stage")) or "unspecified"
        result: dict[str, object] = {}
        if "result" in payload and isinstance(payload["result"], dict):
            result = dict(payload["result"])
        elif "verdict" in payload:
            result = {"verdict": payload["verdict"]}
        guards.append({"stage": stage, "name": name, "result": result})
    return guards


def _gate_from_payload(payload: dict[str, Any], *, default_name: str) -> dict[str, object]:
    name = _first_str(payload.get("name")) or default_name
    rule = payload.get("rule")
    if rule is not None and not isinstance(rule, str):
        rule = None
    verdict = payload.get("verdict")
    if verdict is not None and not isinstance(verdict, (str, type(None))):
        verdict = None
    return {"name": name, "rule": rule, "verdict": verdict}


def _collect_gates(
    journal: list[dict[str, Any]],
    gate_record: dict[str, Any] | None,
) -> list[dict[str, object]]:
    gates: list[dict[str, object]] = []
    names: set[str] = set()
    for entry in journal:
        kind = entry.get("kind")
        if not isinstance(kind, str) or not kind.startswith("gate."):
            continue
        gate = _gate_from_payload(_payload(entry), default_name=kind)
        gates.append(gate)
        names.add(str(gate["name"]))
    if gate_record is not None and "scope_check_verdict" in gate_record:
        if "scope_check" not in names:
            gates.append(
                {
                    "name": "scope_check",
                    "rule": None,
                    "verdict": gate_record.get("scope_check_verdict"),
                }
            )
    return gates


def _collect_model_adapter(
    journal: list[dict[str, Any]],
    state: dict[str, Any] | None,
) -> dict[str, object] | None:
    if state is not None:
        raw = state.get("model_adapter")
        if isinstance(raw, dict):
            return {
                "version": raw.get("version") if "version" in raw else None,
                "config": raw.get("config") if "config" in raw else None,
            }
        version = _first_str(state.get("model_version"), state.get("adapter_version"))
        if version is not None or "model_config" in state or "adapter_config" in state:
            config = state.get("model_config", state.get("adapter_config"))
            return {"version": version, "config": config if config is not None else None}
    for entry in journal:
        payload = _payload(entry)
        raw = payload.get("model_adapter")
        if isinstance(raw, dict):
            return {
                "version": raw.get("version") if "version" in raw else None,
                "config": raw.get("config") if "config" in raw else None,
            }
    return None


def _collect_approvals(
    journal: list[dict[str, Any]],
    state: dict[str, Any] | None,
) -> list[object]:
    if state is not None:
        raw = state.get("human_approvals_overrides")
        if isinstance(raw, list):
            return list(raw)
    approvals: list[object] = []
    for entry in journal:
        kind = entry.get("kind")
        if not isinstance(kind, str):
            continue
        if kind.startswith("approval.") or kind.startswith("override."):
            payload = _payload(entry)
            approvals.append(payload if payload else {"kind": kind})
    return approvals


def build_track(run_dir: Path) -> dict[str, object]:
    """Read a run directory and return one Track mapping (no I/O write)."""
    journal = _read_journal(run_dir / _JOURNAL)
    gate_record = _read_json_object(run_dir / _GATE_RECORD)
    state = _read_json_object(run_dir / _STATE)
    return {
        "run_id": _collect_run_id(journal, state, run_dir),
        "timestamps": _collect_timestamps(journal, gate_record, state),
        "tree_revision": _collect_tree_revision(gate_record, state),
        "guards": _collect_guards(journal, gate_record),
        "gates": _collect_gates(journal, gate_record),
        "model_adapter": _collect_model_adapter(journal, state),
        "human_approvals_overrides": _collect_approvals(journal, state),
        "retention": dict(RETENTION),
    }


def assemble(run_dir: Path, out_path: Path) -> dict[str, object]:
    """Assemble ``track.json`` at *out_path* from *run_dir* evidence."""
    if not run_dir.is_dir():
        raise FileNotFoundError(f"track assemble: run dir not found: {run_dir}")
    track = build_track(run_dir)
    text = json.dumps(track, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
    atomic_write_text(out_path, text)
    return track


class TrackDuty:
    """``steward track assemble --run-dir … --out …`` — Story 53.3."""

    name = "track"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "track_verb", None)
        if verb not in _TRACK_VERBS:
            return DutyResult(
                ok=True,
                summary=f"track: available verbs are {', '.join(_TRACK_VERBS)}",
            )
        try:
            track = assemble(Path(ns.run_dir), Path(ns.out))
        except FileNotFoundError as exc:
            return DutyResult(ok=False, summary=str(exc))
        except OSError as exc:
            return DutyResult(ok=False, summary=f"track assemble: {exc}")
        return DutyResult(
            ok=True,
            summary=f"track assemble: wrote {ns.out} (run_id={track['run_id']})",
            details={"track": track, "out": str(ns.out)},
        )
