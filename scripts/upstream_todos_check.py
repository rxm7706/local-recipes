#!/usr/bin/env python3
"""Story 67.4: validate docs/foundry/upstream-todos.yaml and its drafts.

Reads ``docs/foundry/sbom-gaps.md`` only through ``sbom_gap_derive.parse_gaps_document``.
Exit codes follow ``docs/reference/judgement-vocabulary.md``: 0 pass, 1 findings, 2 could not run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "docs" / "foundry" / "upstream-todos.yaml"
DRAFTS_DIR = REPO_ROOT / "docs" / "foundry" / "upstream-drafts"
GAPS_DOC = REPO_ROOT / "docs" / "foundry" / "sbom-gaps.md"

DETECTOR = {"scope": "repo"}

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import sbom_gap_derive  # noqa: E402

VALID_STATES = frozenset(
    {"proposed", "drafted", "filed", "tracking", "resolved", "retired"}
)
OPERATOR_STATES = frozenset({"filed", "tracking", "resolved", "retired"})
VALID_DECIDED_BY = frozenset({"agent", "operator"})
VALID_TARGET_KINDS = frozenset({"issue", "pr-close", "comment"})
REQUIRED_FIELDS = frozenset(
    {"id", "source", "evidence", "target", "state", "decided_by", "date"}
)
DRAFT_SECTIONS = (
    "## Title",
    "## Body",
    "## Reproduce or evidence",
    "## Local workaround",
    "## What resolution unblocks here",
)
STATES_NEEDING_DRAFT = frozenset(
    {"drafted", "filed", "tracking", "resolved", "retired"}
)


def _load_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(f"PyYAML not importable: {exc}") from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("registry root must be a mapping")
    return data


def _proposed_stub(row_id: str) -> str:
    return (
        f"  - id: <kebab-case>\n"
        f"    title: <one line>\n"
        f"    source: sbom-gaps:{row_id}\n"
        f"    evidence:\n"
        f"      - docs/foundry/sbom-gaps.md\n"
        f"    target:\n"
        f"      tracker: github\n"
        f"      repo: owner/name\n"
        f"      kind: issue\n"
        f"      verified: null\n"
        f"    state: proposed\n"
        f"    draft: null\n"
        f"    issue_url: null\n"
        f"    observed: null\n"
        f"    decided_by: agent\n"
        f"    date: YYYY-MM-DD\n"
        f"    history: []"
    )


def _check_draft_file(draft_rel: str, repo_root: Path) -> list[str]:
    findings: list[str] = []
    path = repo_root / draft_rel
    if not path.is_file():
        findings.append(f"{draft_rel}: draft file missing")
        return findings
    text = path.read_text(encoding="utf-8")
    for section in DRAFT_SECTIONS:
        if section not in text:
            findings.append(f"{draft_rel}: missing section {section!r}")
    return findings


def check_registry(
    registry: dict[str, Any],
    *,
    gaps_text: str,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    """Return human-readable findings; empty list means pass."""
    findings: list[str] = []
    if registry.get("schema_version") != 1:
        findings.append("upstream-todos.yaml: schema_version must be 1")
    items = registry.get("items")
    if not isinstance(items, list):
        findings.append("upstream-todos.yaml: items must be a list")
        return findings

    gaps = sbom_gap_derive.parse_gaps_document(gaps_text)
    upstream_rows = {
        row_id for row_id, row in gaps.items() if row.disposition == "upstream"
    }
    covered_upstream: set[str] = set()
    seen_ids: set[str] = set()

    for raw in items:
        if not isinstance(raw, dict):
            findings.append("upstream-todos.yaml: each item must be a mapping")
            continue
        item_id = raw.get("id")
        if not isinstance(item_id, str) or not item_id:
            findings.append("upstream-todos.yaml: item missing id")
            continue
        if item_id in seen_ids:
            findings.append(f"{item_id}: duplicate id")
        seen_ids.add(item_id)

        for field in REQUIRED_FIELDS:
            if field not in raw:
                findings.append(f"{item_id}: missing required field {field!r}")

        state = raw.get("state")
        if state not in VALID_STATES:
            findings.append(f"{item_id}: unknown state {state!r}")
            continue

        decided_by = raw.get("decided_by")
        if decided_by not in VALID_DECIDED_BY:
            findings.append(f"{item_id}: unknown decided_by {decided_by!r}")

        date_val = raw.get("date")
        if not isinstance(date_val, str) or not date_val.strip():
            findings.append(f"{item_id}: missing or empty date")

        if state in OPERATOR_STATES:
            if decided_by != "operator":
                findings.append(
                    f"{item_id}: operator-only state {state!r} requires decided_by: operator"
                )
            if state in {"filed", "tracking"}:
                url = raw.get("issue_url")
                if not isinstance(url, str) or not url.startswith("https://"):
                    findings.append(
                        f"{item_id}: {state!r} requires https:// issue_url"
                    )
            if state == "retired":
                reason = raw.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    findings.append(f"{item_id}: retired requires reason")
            if state == "resolved":
                follow = raw.get("local_follow_up")
                if not isinstance(follow, str) or not follow.strip():
                    findings.append(f"{item_id}: resolved requires local_follow_up")

        observed = raw.get("observed")
        if observed is not None and state != "tracking":
            findings.append(f"{item_id}: observed set outside tracking state")

        target = raw.get("target")
        if isinstance(target, dict):
            kind = target.get("kind")
            if kind not in VALID_TARGET_KINDS:
                findings.append(f"{item_id}: unknown target.kind {kind!r}")
        elif "target" in raw:
            findings.append(f"{item_id}: target must be a mapping")

        evidence = raw.get("evidence")
        if evidence is not None and (
            not isinstance(evidence, list) or not evidence
        ):
            findings.append(f"{item_id}: evidence must be a non-empty list")

        source = raw.get("source")
        if isinstance(source, str) and source.startswith("sbom-gaps:"):
            row_key = source.removeprefix("sbom-gaps:")
            covered_upstream.add(row_key)
            if state not in {"resolved", "retired"}:
                row = gaps.get(row_key)
                if row is None:
                    findings.append(
                        f"{item_id}: source row {row_key!r} absent from sbom-gaps.md"
                    )
                elif row.disposition != "upstream":
                    findings.append(
                        f"{item_id}: source row {row_key!r} is no longer upstream"
                    )

        if state in STATES_NEEDING_DRAFT:
            draft = raw.get("draft")
            if not isinstance(draft, str) or not draft.strip():
                findings.append(f"{item_id}: {state!r} requires draft path")
            else:
                findings.extend(_check_draft_file(draft, repo_root))

    for row_id in sorted(upstream_rows - covered_upstream):
        findings.append(
            f"sbom-gaps upstream row {row_id!r} has no registry entry; proposed stub:\n"
            f"{_proposed_stub(row_id)}"
        )

    return findings


def check_upstream_todos(
    *,
    registry_path: Path = REGISTRY_PATH,
    gaps_path: Path = GAPS_DOC,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    if not registry_path.is_file():
        return [f"missing registry: {registry_path.relative_to(repo_root)}"]
    if not gaps_path.is_file():
        return [f"missing sbom-gaps.md: {gaps_path.relative_to(repo_root)}"]
    try:
        registry = _load_yaml(registry_path.read_text(encoding="utf-8"))
    except (RuntimeError, ValueError) as exc:
        return [f"registry unreadable: {exc}"]
    gaps_text = gaps_path.read_text(encoding="utf-8")
    return check_registry(registry, gaps_text=gaps_text, repo_root=repo_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check upstream to-do registry.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=REGISTRY_PATH,
        help="Path to upstream-todos.yaml (default: tracked registry)",
    )
    parser.add_argument(
        "--gaps-doc",
        type=Path,
        default=GAPS_DOC,
        help="Path to sbom-gaps.md (default: tracked file)",
    )
    args = parser.parse_args(argv)

    try:
        findings = check_upstream_todos(
            registry_path=args.registry,
            gaps_path=args.gaps_doc,
        )
    except OSError as exc:
        print(f"could not run: {exc}", file=sys.stderr)
        return 2

    if findings:
        for item in findings:
            print(item, file=sys.stderr)
        print(f"\nFINDINGS ({len(findings)})", file=sys.stderr)
        return 1
    print("OK: upstream-todos.yaml matches sbom-gaps upstream rows and draft rules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
