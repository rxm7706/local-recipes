"""Build League measure catalog config (Story 62.2, spec-build-league-scorecard CAP-2).

``measures/measures.yaml`` names every published measure with ``on`` / ``off`` /
``archived`` state. A new source is a new row starting ``off``; archive keeps
the id on the row (or in ``archived_ids`` when removed) and forbids reuse.
Consumers read this file — not the companion markdown table — for state.

``MeasureDuty`` never calls ``sys.exit`` (AD-8).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .bootstrap import repo_root
from .interfaces import DutyResult

MEASURES_RELATIVE = Path("src/shared/packages/pyforge-steward/measures")
CONFIG_FILENAME = "measures.yaml"

STATES: tuple[str, ...] = ("on", "off", "archived")
STATE_ON, STATE_OFF, STATE_ARCHIVED = STATES
DIMENSIONS: tuple[str, ...] = ("human", "agent", "team")

FIRST_CUT_IDS: frozenset[str] = frozenset(
    {
        "warden-verdict",
        "owner-work-class",
        "gate-record-outcomes",
        "journal-timing",
        "run-cost-usd",
        "ledger-throughput",
        "detector-pass-fail",
        "five-tier-completeness",
    }
)

_TOP_LEVEL_KEYS: frozenset[str] = frozenset({"catalog", "archived_ids", "measures"})
VERBS: tuple[str, ...] = ("check", "list")


class MeasureConfigError(ValueError):
    """Invalid ``measures.yaml`` or measure declaration."""


@dataclass(frozen=True)
class MeasureDecl:
    measure_id: str
    dimension: str
    source: str
    state: str
    notes: str = ""


@dataclass(frozen=True)
class MeasureConfig:
    name: str
    companion: str
    archived_ids: tuple[str, ...]
    measures: tuple[MeasureDecl, ...]

    def by_id(self) -> dict[str, MeasureDecl]:
        return {m.measure_id: m for m in self.measures}


def default_measures_dir(root: Path | None = None) -> Path:
    return (root if root is not None else repo_root()) / MEASURES_RELATIVE


def _load_yaml_mapping(document_path: Path, *, what: str) -> dict[str, Any]:
    if not document_path.is_file():
        raise MeasureConfigError(f"{document_path}: {what} not found")
    try:
        raw = yaml.safe_load(document_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise MeasureConfigError(f"{document_path}: malformed YAML: {exc}") from exc
    except OSError as exc:
        raise MeasureConfigError(f"{document_path}: unreadable: {exc}") from exc
    if not isinstance(raw, dict):
        raise MeasureConfigError(f"{document_path}: top-level document must be a mapping")
    return raw


def _normalize_state(document_path: Path, raw: object, where: str) -> str:
    if isinstance(raw, bool):
        raw = STATE_ON if raw else STATE_OFF
    if not isinstance(raw, str) or raw.strip() not in STATES:
        raise MeasureConfigError(f"{document_path}: '{where}.state' = {raw!r} is not one of {STATES!r}")
    return raw.strip()


def _require_str(document_path: Path, body: dict[str, Any], key: str, where: str) -> str:
    raw = body.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise MeasureConfigError(f"{document_path}: '{where}.{key}' is required and must be a non-empty string")
    return raw.strip()


def load_config(path: str | Path) -> MeasureConfig:
    document_path = Path(path)
    document = _load_yaml_mapping(document_path, what="measure config")

    unknown = sorted(str(k) for k in document if k not in _TOP_LEVEL_KEYS)
    if unknown:
        raise MeasureConfigError(
            f"{document_path}: unknown top-level key(s) {unknown!r}; only {sorted(_TOP_LEVEL_KEYS)!r} are recognized"
        )

    catalog = document.get("catalog")
    if not isinstance(catalog, dict):
        raise MeasureConfigError(f"{document_path}: 'catalog' section missing or not a mapping")
    name = _require_str(document_path, catalog, "name", "catalog")
    companion = catalog.get("companion")
    companion_str = companion.strip() if isinstance(companion, str) else ""

    archived_raw = document.get("archived_ids")
    if archived_raw is None:
        archived_raw = []
    if not isinstance(archived_raw, list):
        raise MeasureConfigError(f"{document_path}: 'archived_ids' must be a list")
    archived_ids: list[str] = []
    for index, item in enumerate(archived_raw):
        if not isinstance(item, str) or not item.strip():
            raise MeasureConfigError(f"{document_path}: 'archived_ids[{index}]' must be a non-empty string")
        archived_ids.append(item.strip())

    section = document.get("measures")
    if section is None:
        section = {}
    if not isinstance(section, dict):
        raise MeasureConfigError(f"{document_path}: 'measures' section must be a mapping")

    decls: list[MeasureDecl] = []
    for measure_id, body in section.items():
        if not isinstance(measure_id, str) or not measure_id.strip():
            raise MeasureConfigError(f"{document_path}: 'measures' key {measure_id!r} must be a non-empty string")
        mid = measure_id.strip()
        where = f"measures.{mid}"
        if not isinstance(body, dict):
            raise MeasureConfigError(f"{document_path}: '{where}' must be a mapping")
        dimension = _require_str(document_path, body, "dimension", where)
        if dimension not in DIMENSIONS:
            raise MeasureConfigError(
                f"{document_path}: '{where}.dimension' = {dimension!r} is not one of {DIMENSIONS!r}"
            )
        source = _require_str(document_path, body, "source", where)
        state = _normalize_state(document_path, body.get("state"), where)
        notes_raw = body.get("notes", "")
        notes = notes_raw.strip() if isinstance(notes_raw, str) else ""
        decls.append(
            MeasureDecl(
                measure_id=mid,
                dimension=dimension,
                source=source,
                state=state,
                notes=notes,
            )
        )

    overlap = sorted(set(archived_ids) & {d.measure_id for d in decls})
    if overlap:
        raise MeasureConfigError(f"{document_path}: id(s) {overlap!r} appear in both 'measures' and 'archived_ids'")

    return MeasureConfig(
        name=name,
        companion=companion_str,
        archived_ids=tuple(archived_ids),
        measures=tuple(decls),
    )


def validate_add_rules(config: MeasureConfig) -> list[str]:
    """Return human-readable findings for add/archive invariants."""
    findings: list[str] = []
    ids = {m.measure_id for m in config.measures}
    for mid in config.archived_ids:
        if mid in ids:
            findings.append(f"id {mid!r} is listed in archived_ids and measures")
    for decl in config.measures:
        if decl.measure_id not in FIRST_CUT_IDS and decl.state != STATE_OFF:
            findings.append(f"measures.{decl.measure_id}: new measures must start with state 'off', got {decl.state!r}")
    return findings


def refuse_reuse(measure_id: str, config: MeasureConfig) -> str | None:
    """If ``measure_id`` cannot be added, return a refusal reason."""
    if measure_id in config.by_id():
        return f"measure id {measure_id!r} already exists"
    if measure_id in config.archived_ids:
        return f"measure id {measure_id!r} is archived and cannot be reused"
    for decl in config.measures:
        if decl.measure_id == measure_id and decl.state == STATE_ARCHIVED:
            return f"measure id {measure_id!r} is archived and cannot be reused"
    return None


def format_list(config: MeasureConfig) -> str:
    lines = [f"catalog {config.name!r} — {len(config.measures)} measure(s)"]
    for decl in sorted(config.measures, key=lambda d: d.measure_id):
        note = f" — {decl.notes}" if decl.notes else ""
        lines.append(f"  {decl.measure_id}: {decl.state} ({decl.dimension}) {decl.source}{note}")
    if config.archived_ids:
        lines.append(f"  archived_ids (reserved): {', '.join(config.archived_ids)}")
    return "\n".join(lines)


class MeasureDuty:
    """``steward measure check|list [--json]`` — Story 62.2."""

    name = "measure"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "measure_verb", None) or "check"
        as_json = bool(getattr(ns, "json", False))
        root = repo_root()
        measures_arg = getattr(ns, "measures_dir", None)
        measures_dir = Path(measures_arg).resolve() if measures_arg else default_measures_dir(root)
        config_path = measures_dir / CONFIG_FILENAME
        try:
            config = load_config(config_path)
        except MeasureConfigError as exc:
            payload = {"ok": False, "findings": [{"code": "config-load", "message": str(exc)}]}
            return DutyResult(
                ok=False,
                summary=json.dumps(payload, indent=2) if as_json else f"measure {verb}: {exc}",
                details=payload,
            )

        if verb == "list":
            rows = [decl.__dict__ for decl in config.measures]
            payload = {
                "name": config.name,
                "companion": config.companion,
                "archived_ids": list(config.archived_ids),
                "count": len(rows),
                "measures": rows,
            }
            return DutyResult(
                ok=True,
                summary=json.dumps(payload, indent=2) if as_json else format_list(config),
                details=payload,
            )

        findings = validate_add_rules(config)
        ok = not findings
        payload = {
            "ok": ok,
            "findings": [{"code": "measure-policy", "message": msg} for msg in findings],
        }
        text = "measure check: ok" if ok else "measure check: " + "; ".join(findings)
        return DutyResult(
            ok=ok,
            summary=json.dumps(payload, indent=2) if as_json else text,
            details=payload,
        )
