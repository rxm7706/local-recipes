"""Retirement ledger for preserve tags (Story 87.15, derived state)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

RETIREMENTS_REL = "docs/governance/preserve-retirements.yaml"


@dataclass(frozen=True, slots=True)
class RetirementRow:
    tag: str
    evidence: str
    retired_at: str


def retirements_path(repo_root: Path) -> Path:
    return repo_root / RETIREMENTS_REL


def load_retirements(path: Path) -> list[RetirementRow]:
    if not path.is_file():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows: list[RetirementRow] = []
    for entry in raw.get("retirements") or ():
        if not isinstance(entry, dict):
            continue
        tag = str(entry.get("tag", "")).strip()
        evidence = str(entry.get("evidence", "")).strip()
        retired_at = str(entry.get("retired_at", "")).strip()
        if tag and evidence:
            rows.append(RetirementRow(tag=tag, evidence=evidence, retired_at=retired_at))
    return rows


def append_retirement(path: Path, *, tag: str, evidence: str) -> RetirementRow:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_retirements(path) if path.is_file() else []
    if any(r.tag == tag for r in existing):
        raise ValueError(f"retirement ledger already lists {tag!r}")
    row = RetirementRow(
        tag=tag,
        evidence=evidence,
        retired_at=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    payload = {
        "schema_version": 1,
        "retirements": [{"tag": r.tag, "evidence": r.evidence, "retired_at": r.retired_at} for r in (*existing, row)],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return row


def retired_tag_names(path: Path) -> frozenset[str]:
    return frozenset(r.tag for r in load_retirements(path))
