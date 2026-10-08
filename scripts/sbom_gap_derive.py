#!/usr/bin/env python3
"""Story 67.3 (fnd:CAP-13): derive SBOM gap keys from ``pixi.toml``.

A **residual solve gap** is every ``[feature.<name>]`` declared in ``pixi.toml``
that is composed into neither ``pyforge-foundry-full`` (the laptop SBOM) nor
``pyforge-foundry-full-stack`` (the SBOM plus its platform layer).

A **fat-only pin** is every package key in ``[feature.local-recipes.dependencies]``
that does not appear in any SBOM feature dependency table.

``docs/foundry/sbom-gaps.md`` holds human dispositions; this module derives the
required row ids and compares them to the tracked file. Exit codes follow
``docs/reference/judgement-vocabulary.md`` script detectors: 0 pass, 1 findings.
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent
PIXII = REPO_ROOT / "pixi.toml"
GAPS_DOC = REPO_ROOT / "docs" / "foundry" / "sbom-gaps.md"

SBOM_ENV = "pyforge-foundry-full"
LAYER_ENV = "pyforge-foundry-full-stack"

Kind = Literal["feature", "pin"]
Disposition = Literal["promote", "won't-do", "upstream"]

ROW_RE = re.compile(
    r"^\|\s*`(?P<id>[^`]+)`\s*\|\s*(?P<kind>feature|pin)\s*\|\s*"
    r"(?P<disposition>promote|won't-do|upstream)\s*\|\s*(?P<reason>[^|]+)\|\s*"
    r"(?P<owner>[^|]+?)\s*\|\s*$"
)


@dataclass(frozen=True)
class GapRow:
    row_id: str
    kind: Kind
    disposition: Disposition
    reason: str
    owner: str


def _load_pixi() -> dict:
    return tomllib.loads(PIXII.read_text(encoding="utf-8"))


def _env_feature_names(data: dict, env_name: str) -> list[str]:
    env = data["environments"][env_name]
    if isinstance(env, dict):
        features = env.get("features")
        if isinstance(features, list):
            return list(features)
        raise ValueError(f"{env_name}: expected features list")
    if isinstance(env, list):
        return list(env)
    raise ValueError(f"{env_name}: unrecognised environment shape")


def _dependency_keys(feature_block: dict) -> set[str]:
    keys: set[str] = set()
    deps = feature_block.get("dependencies")
    if isinstance(deps, dict):
        keys.update(deps.keys())
    for key, value in feature_block.items():
        if key.endswith(".dependencies") and isinstance(value, dict):
            keys.update(value.keys())
    return {_normalize_pkg_name(k) for k in keys}


def _normalize_pkg_name(raw: str) -> str:
    token = raw.strip().split()[0]
    return token.split("@", 1)[0].strip('"')


def derive_gap_features(data: dict | None = None) -> frozenset[str]:
    data = data or _load_pixi()
    layer_features = set(_env_feature_names(data, LAYER_ENV))
    declared = set(data.get("feature", {}).keys())
    return frozenset(declared - layer_features)


def derive_sbom_package_names(data: dict | None = None) -> frozenset[str]:
    data = data or _load_pixi()
    sbom_features = _env_feature_names(data, SBOM_ENV)
    packages: set[str] = set()
    feature_root = data.get("feature", {})
    for name in sbom_features:
        block = feature_root.get(name, {})
        if isinstance(block, dict):
            packages |= _dependency_keys(block)
    return frozenset(packages)


def derive_fat_only_pins(data: dict | None = None) -> frozenset[str]:
    data = data or _load_pixi()
    lr_block = data.get("feature", {}).get("local-recipes", {})
    deps = lr_block.get("dependencies") if isinstance(lr_block, dict) else None
    if not isinstance(deps, dict):
        return frozenset()
    local_names = {_normalize_pkg_name(k) for k in deps.keys()}
    return frozenset(local_names - derive_sbom_package_names(data))


def derive_expected_ids(data: dict | None = None) -> frozenset[str]:
    data = data or _load_pixi()
    ids: set[str] = {f"feature:{name}" for name in derive_gap_features(data)}
    ids |= {f"pin:{name}" for name in derive_fat_only_pins(data)}
    return frozenset(ids)


def parse_gaps_document(text: str) -> dict[str, GapRow]:
    rows: dict[str, GapRow] = {}
    for line in text.splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue
        row_id = match.group("id")
        rows[row_id] = GapRow(
            row_id=row_id,
            kind=match.group("kind"),  # type: ignore[arg-type]
            disposition=match.group("disposition"),  # type: ignore[arg-type]
            reason=match.group("reason").strip(),
            owner=match.group("owner").strip(),
        )
    return rows


def check_gaps_document(
    *,
    data: dict | None = None,
    doc_path: Path = GAPS_DOC,
) -> list[str]:
    """Return human-readable findings; empty list means pass."""
    data = data or _load_pixi()
    expected = derive_expected_ids(data)
    if not doc_path.is_file():
        return [f"missing tracked gap list: {doc_path.relative_to(REPO_ROOT)}"]

    parsed = parse_gaps_document(doc_path.read_text(encoding="utf-8"))
    found = frozenset(parsed.keys())
    findings: list[str] = []

    for missing in sorted(expected - found):
        findings.append(f"derivation expects a row {missing!r} absent from sbom-gaps.md")

    for stale in sorted(found - expected):
        findings.append(f"sbom-gaps.md keeps stale row {stale!r} not found by derivation")

    for row_id in sorted(expected & found):
        row = parsed[row_id]
        if not row.reason.strip():
            findings.append(f"{row_id}: empty reason")
        if not row.owner.strip():
            findings.append(f"{row_id}: empty owner")
        kind_prefix, _, name = row_id.partition(":")
        if kind_prefix == "feature" and row.kind != "feature":
            findings.append(f"{row_id}: kind column must be feature")
        if kind_prefix == "pin" and row.kind != "pin":
            findings.append(f"{row_id}: kind column must be pin")
        if kind_prefix == "feature" and name not in derive_gap_features(data):
            findings.append(f"{row_id}: not a derived feature gap")
        if kind_prefix == "pin" and name not in derive_fat_only_pins(data):
            findings.append(f"{row_id}: not a derived fat-only pin")

    return findings


def _default_feature_row(name: str) -> GapRow:
    known: dict[str, tuple[Disposition, str, str]] = {
        "conda-smithy": (
            "upstream",
            "py-rattler / conda co-solve blocks composing conda-smithy into the laptop SBOM",
            "mason",
        ),
        "python-agent-platform": (
            "upstream",
            "langflow vs pandas / onnxruntime co-solve keeps the agent platform in its own env",
            "steward",
        ),
        "crm": (
            "upstream",
            "conda-recipe-manager 0.8+ caps click while mcp needs click >=8.4.2; feedrattler needs conda-smithy/py-rattler caps",
            "mason",
        ),
        "local-recipes": (
            "won't-do",
            "Recipe-factory closure at scale; never composed into the laptop SBOM",
            "steward",
        ),
    }
    disposition, reason, owner = known.get(
        name,
        (
            "won't-do",
            "Standalone pixi feature/environment; outside pyforge-foundry-full and its stack layer",
            "steward",
        ),
    )
    return GapRow(
        row_id=f"feature:{name}",
        kind="feature",
        disposition=disposition,
        reason=reason,
        owner=owner,
    )


def _default_pin_row(name: str) -> GapRow:
    return GapRow(
        row_id=f"pin:{name}",
        kind="pin",
        disposition="won't-do",
        reason="Declared only in [feature.local-recipes.dependencies]; not in any SBOM feature",
        owner="steward",
    )


def render_gaps_markdown(data: dict | None = None) -> str:
    """Render the full tracked document (bootstrap helper — not used by the check)."""
    data = data or _load_pixi()
    feature_rows = [_default_feature_row(n) for n in sorted(derive_gap_features(data))]
    pin_rows = [_default_pin_row(n) for n in sorted(derive_fat_only_pins(data))]

    lines = [
        "# SBOM gaps and fat-only pins",
        "",
        "Derived keys come from ``pixi.toml`` via ``scripts/sbom_gap_derive.py``.",
        "Do not hand-add rows: ``pixi run -e pyforge-guild sbom-gaps-check`` reds when",
        "derivation and this file diverge.",
        "",
        "| id | kind | disposition | reason | owner |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in feature_rows + pin_rows:
        lines.append(
            f"| `{row.row_id}` | {row.kind} | {row.disposition} | {row.reason} | {row.owner} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive or check SBOM gap rows.")
    parser.add_argument(
        "--write-doc",
        action="store_true",
        help="Rewrite docs/foundry/sbom-gaps.md from defaults (bootstrap only).",
    )
    args = parser.parse_args(argv)

    if args.write_doc:
        GAPS_DOC.parent.mkdir(parents=True, exist_ok=True)
        GAPS_DOC.write_text(render_gaps_markdown(), encoding="utf-8")
        print(f"wrote {GAPS_DOC.relative_to(REPO_ROOT)}")
        return 0

    findings = check_gaps_document()
    if findings:
        for item in findings:
            print(item, file=sys.stderr)
        print(f"\nFINDINGS ({len(findings)})", file=sys.stderr)
        return 1
    print("OK: sbom-gaps.md matches pixi.toml derivation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
