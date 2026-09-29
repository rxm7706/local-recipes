"""Capability-ledger extract detector (Story 55.2 / ``fcl:CAP-2``).

Inventory is a CAP heading + intent/success extract
(``spec-foundry-capability-ledger/extract.md``). Do not inventory
through Scribe's text-file node helper or a truncated SPEC prefix.

HARD: unclassified live ``CAP-N``, ``A-only`` without expiry.
``--append`` (WARN): a path/Spec added after the ledger ``source_sha``
that has no ledger row.

Independence: never imports ``pyforge.steward`` / ``pyforge.scribe``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = (
    "UNIQUE_WHY_FIXTURE_SENTENCE",
    "extract_caps",
    "gather",
    "iter_live_specs",
    "load_case_list_ids",
    "parse_case_list_ids",
)

_CHECK = "capability-ledger"
_LIVE_STATUSES = frozenset({"ready", "in-progress"})
_LEDGER = Path("docs") / "foundry" / "capability-ledger.yaml"
_SPEC_GLOB = "_bmad-output/projects/*/planning-artifacts/specs/*/SPEC.md"
_CASE_LIST = (
    Path("_bmad-output")
    / "projects"
    / "pyforge-steward"
    / "planning-artifacts"
    / "specs"
    / "spec-foundry-regenerate-not-fold"
    / "case-list.md"
)
_CASE_ID_RE = re.compile(r"^\|\s*(k-[a-z0-9-]+)\s*\|", re.MULTILINE)
_FRAME_CLAIM_RE = re.compile(r"(?:docs/foundry/frames/|\.frame\.md)", re.IGNORECASE)

# Story 55.2 AC-1: fixture Why text the extract must drop.
UNIQUE_WHY_FIXTURE_SENTENCE = "UNIQUE_WHY_55_2_the-capability-section-must-survive-this-sentence"

_HEADING_BOLD = re.compile(
    r"^\s*[-*]?\s*\*\*CAP-(\d+)\s+[—–-]\s*(.+?)\*\*",
    re.MULTILINE,
)
_HEADING_PLAIN = re.compile(
    r"^\s*[-*]?\s*\*\*CAP-(\d+)\*\*(?:\s*[—–-]\s*(.+?))?",
    re.MULTILINE,
)
_INTENT_RE = re.compile(
    r"^\s*[-*]?\s*\*\*intent:\*\*\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)
_SUCCESS_RE = re.compile(
    r"^\s*[-*]?\s*\*\*success:\*\*\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)
_CITE_MAP = {
    "foundry-regenerate-not-fold": "fnr",
    "foundry-capability-ledger": "fcl",
    "python-foundry-cutover": "fnd",
    "intelligence-hub": "hub",
    "pyforge-unifying-strategy": "pap",
    "pyforge-pages": "pgs",
}


@dataclass(frozen=True)
class CapExtract:
    spec: str
    cap_n: int
    heading: str
    intent: str
    success: str
    path: str
    cite_id: str


def extract_caps(text: str) -> list[tuple[int, str, str, str]]:
    """Return ``(n, heading, intent, success)`` from ``text``.

    Stores heading + the following intent/success lines only. Why,
    Non-goals, and Assumptions are not kept.
    """
    hits: dict[int, tuple[int, str]] = {}
    for rx in (_HEADING_BOLD, _HEADING_PLAIN):
        for match in rx.finditer(text):
            n = int(match.group(1))
            heading = (match.group(2) or "").strip().rstrip(".").rstrip("*").strip()
            if n not in hits or (heading and not hits[n][1]):
                hits[n] = (match.start(), heading)
    rows: list[tuple[int, str, str, str]] = []
    ordered = sorted(hits.items(), key=lambda item: item[1][0])
    for idx, (n, (start, heading)) in enumerate(ordered):
        end = ordered[idx + 1][1][0] if idx + 1 < len(ordered) else len(text)
        block = text[start:end]
        intent_m = _INTENT_RE.search(block)
        success_m = _SUCCESS_RE.search(block)
        rows.append(
            (
                n,
                heading,
                (intent_m.group(1).strip() if intent_m else ""),
                (success_m.group(1).strip() if success_m else ""),
            )
        )
    return rows


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line or line[:1] in {" ", "-", "#"}:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip("'\"")
        if value and not value.startswith(("[", "|", "{")):
            fields[key.strip()] = value
    return fields


def _cite_id(spec: str, cap_n: int) -> str:
    prefix = _CITE_MAP.get(spec, spec)
    return f"{prefix}:CAP-{cap_n}"


def iter_live_specs(target: Path) -> list[CapExtract]:
    """Walk ready/in-progress ``SPEC.md`` files and extract live CAPs."""
    rows: list[CapExtract] = []
    for path in sorted(target.glob(_SPEC_GLOB)):
        text = path.read_text(encoding="utf-8", errors="replace")
        meta = _frontmatter(text)
        if meta.get("status") not in _LIVE_STATUSES:
            continue
        spec = meta.get("spec") or path.parent.name.removeprefix("spec-")
        rel = str(path.relative_to(target)).replace("\\", "/")
        for cap_n, heading, intent, success in extract_caps(text):
            rows.append(
                CapExtract(
                    spec=spec,
                    cap_n=cap_n,
                    heading=heading,
                    intent=intent,
                    success=success,
                    path=rel,
                    cite_id=_cite_id(spec, cap_n),
                )
            )
    return rows


def _load_ledger(target: Path) -> dict:
    path = target / _LEDGER
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("capability-ledger.yaml is not a mapping")
    return data


def _row_matches(row: dict, extracted: CapExtract) -> bool:
    rid = str(row.get("id") or "")
    if rid == extracted.cite_id:
        return True
    rspec = str(row.get("spec") or "")
    return rspec == extracted.spec and rid.endswith(f":CAP-{extracted.cap_n}")


def parse_case_list_ids(text: str) -> frozenset[str]:
    """54.1 case-list ids — first column of the thin-oracle table."""
    return frozenset(_CASE_ID_RE.findall(text))


def load_case_list_ids(target: Path) -> frozenset[str]:
    path = target / _CASE_LIST
    if not path.is_file():
        return frozenset()
    return parse_case_list_ids(path.read_text(encoding="utf-8", errors="replace"))


def _claim_verified(row: dict) -> bool:
    state = str(row.get("state") or "").strip()
    if state == "verified-in-foundry":
        return True
    flag = row.get("verified_in_foundry")
    if flag is True:
        return True
    if isinstance(flag, str) and flag.strip():
        return True
    return False


def _claim_case_id(row: dict) -> str:
    for key in ("case_id", "case-list", "case_list_id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    flag = row.get("verified_in_foundry")
    if isinstance(flag, str) and flag.strip():
        return flag.strip()
    return ""


def _added_after_pin(target: Path, pin_sha: str) -> set[str]:
    if not pin_sha:
        return set()
    try:
        out = run_git(
            target,
            ["diff", "--name-only", "--diff-filter=A", f"{pin_sha}..HEAD"],
        )
    except CliBridgeError, UnicodeDecodeError:
        return set()
    return {line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()}


def _finding(
    status: DoctorStatus,
    message: str,
    evidence: dict,
) -> Finding:
    return Finding(
        source=Source.CAPABILITY_LEDGER,
        check=_CHECK,
        status=status,
        message=message,
        evidence=evidence,
    )


def _gather(target: Path) -> tuple[Finding, ...]:
    ledger = _load_ledger(target)
    if not ledger:
        return (
            _finding(
                DoctorStatus.OK,
                "no capability-ledger.yaml -- nothing to classify yet",
                {"ledger": None},
            ),
        )

    rows = ledger.get("capabilities")
    if not isinstance(rows, list):
        raise ValueError("capability-ledger.yaml missing capabilities list")

    pin = str(ledger.get("source_sha") or "")
    added = _added_after_pin(target, pin)
    extracted = iter_live_specs(target)
    findings: list[Finding] = []
    case_ids = load_case_list_ids(target)

    for row in rows:
        if not isinstance(row, dict):
            continue
        mode = str(row.get("mode") or "")
        if mode == "A-only" and not str(row.get("expiry") or "").strip():
            findings.append(
                _finding(
                    DoctorStatus.FAIL,
                    f"{row.get('id')}: A-only without expiry",
                    {"kind": "undated-a-only", "id": row.get("id")},
                )
            )
        if _claim_verified(row):
            case_id = _claim_case_id(row)
            if not case_id:
                findings.append(
                    _finding(
                        DoctorStatus.FAIL,
                        f"{row.get('id')}: verified-in-foundry without a case-list id",
                        {"kind": "verified-missing-case", "id": row.get("id")},
                    )
                )
            elif _FRAME_CLAIM_RE.search(case_id) or case_id not in case_ids:
                findings.append(
                    _finding(
                        DoctorStatus.FAIL,
                        f"{row.get('id')}: verified-in-foundry {case_id!r} is not a 54.1 case-list id",
                        {
                            "kind": "verified-unknown-case",
                            "id": row.get("id"),
                            "case_id": case_id,
                        },
                    )
                )

    classified_paths: set[str] = set()
    for row in rows:
        if isinstance(row, dict) and row.get("path"):
            classified_paths.add(str(row["path"]).replace("\\", "/"))

    for cap in extracted:
        if any(_row_matches(row, cap) for row in rows if isinstance(row, dict)):
            continue
        evidence = {
            "kind": "unclassified",
            "id": cap.cite_id,
            "spec": cap.spec,
            "path": cap.path,
            "heading": cap.heading,
            "intent": cap.intent,
            "success": cap.success,
        }
        if cap.path in added:
            findings.append(
                _finding(
                    DoctorStatus.WARN,
                    f"{cap.cite_id}: post-PIN unclassified --append",
                    {**evidence, "kind": "append"},
                )
            )
        else:
            findings.append(
                _finding(
                    DoctorStatus.FAIL,
                    f"{cap.cite_id}: unclassified CAP-N",
                    evidence,
                )
            )

    for path in sorted(added):
        if not path.endswith("/SPEC.md"):
            continue
        if "/planning-artifacts/specs/" not in path:
            continue
        if path in classified_paths:
            continue
        if any(cap.path == path for cap in extracted):
            continue
        findings.append(
            _finding(
                DoctorStatus.WARN,
                f"{path}: post-PIN Spec without a ledger row --append",
                {"kind": "append", "path": path},
            )
        )

    if findings:
        return tuple(findings)

    stored = [f"{cap.cite_id}:{cap.intent}:{cap.success}" for cap in extracted]
    return (
        _finding(
            DoctorStatus.OK,
            f"{len(extracted)} live CAP extract(s) match the ledger",
            {"checked": len(extracted), "stored": stored},
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Classify live CAP extracts against ``docs/foundry/capability-ledger.yaml``."""
    return degrade_on_exception(Source.CAPABILITY_LEDGER, _CHECK, lambda: _gather(target))
