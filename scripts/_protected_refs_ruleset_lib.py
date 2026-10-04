"""Render and compare GitHub rulesets declared from guild-roster protected_refs.

Shared by ``protected_refs_ruleset_check.py`` and its tests. The tracked
``docs/governance/rulesets/protected-refs.json`` is derived from the roster
alone (marshal:AD-12) — never hand-edited.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ROSTER_PATH = ROOT / "docs" / "governance" / "guild-roster.json"
DOCUMENT_PATH = ROOT / "docs" / "governance" / "rulesets" / "protected-refs.json"
MARSHAL_POLICY_PATH = (
    ROOT
    / "_bmad-output"
    / "projects"
    / "pyforge-marshal"
    / "planning-artifacts"
    / "marshal-policy.toml"
)

TAG_RULES = ("deletion", "update", "non_fast_forward")
BRANCH_RULES_BY_KIND = {
    "operational-branch": ("deletion", "non_fast_forward"),
    "legacy": ("deletion",),
    "preserve-tag": TAG_RULES,
    "archive-tag": TAG_RULES,
}

RULESET_NAMES = {
    "branch_loop": "protected-refs-loop-branches",
    "branch_attempt": "protected-refs-attempt-preserve-branches",
    "tags": "protected-refs-tags",
    "restrict_creation": "protected-refs-restrict-preserve-branch-creation",
}


def _glob_from_prefix(prefix: str) -> str:
    """``refs/heads/loop/`` -> ``refs/heads/loop/**``."""
    if prefix.endswith("/"):
        return prefix + "**"
    return prefix + "/**"


def _rule_objects(types: tuple[str, ...]) -> list[dict[str, str]]:
    return [{"type": t} for t in types]


def load_roster(path: Path = ROSTER_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_rules_for_entry(entry: dict[str, Any]) -> tuple[str, ...]:
    kind = entry["kind"]
    if "rules" in entry:
        rules = tuple(entry["rules"])
    else:
        rules = BRANCH_RULES_BY_KIND.get(kind, TAG_RULES)
    return rules


def _ruleset_name_for_branch_rules(rules: tuple[str, ...]) -> str:
    if rules == ("deletion", "non_fast_forward"):
        return RULESET_NAMES["branch_loop"]
    if rules == ("deletion",):
        return RULESET_NAMES["branch_attempt"]
    slug = "-".join(rules)
    return f"protected-refs-branches-{slug}"


def render_document(roster: dict[str, Any] | None = None) -> dict[str, Any]:
    roster = roster if roster is not None else load_roster()
    entries = roster["protected_refs"]
    branch_groups: dict[tuple[str, ...], list[str]] = {}
    tag_patterns: list[str] = []
    for entry in entries:
        refname = entry["refname"]
        rules = expected_rules_for_entry(entry)
        if refname.startswith("refs/heads/"):
            branch_groups.setdefault(rules, []).append(_glob_from_prefix(refname))
        elif refname.startswith("refs/tags/"):
            tag_patterns.append(_glob_from_prefix(refname))
        else:
            raise ValueError(f"unsupported protected ref prefix: {refname!r}")

    rulesets: list[dict[str, Any]] = []
    for rules, patterns in sorted(branch_groups.items(), key=lambda kv: kv[0]):
        rulesets.append(
            {
                "name": _ruleset_name_for_branch_rules(rules),
                "target": "branch",
                "enforcement": "active",
                "conditions": {
                    "ref_name": {"include": sorted(patterns), "exclude": []}
                },
                "rules": _rule_objects(rules),
                "bypass_actors": [],
            }
        )
    if tag_patterns:
        rulesets.append(
            {
                "name": RULESET_NAMES["tags"],
                "target": "tag",
                "enforcement": "active",
                "conditions": {
                    "ref_name": {"include": sorted(tag_patterns), "exclude": []}
                },
                "rules": _rule_objects(TAG_RULES),
                "bypass_actors": [],
            }
        )
    rulesets.append(
        {
            "name": RULESET_NAMES["restrict_creation"],
            "target": "branch",
            "enforcement": "active",
            "conditions": {
                "ref_name": {
                    "include": [
                        "refs/heads/preserve/**",
                        "refs/heads/archive/**",
                    ],
                    "exclude": [],
                }
            },
            "rules": _rule_objects(("creation",)),
            "bypass_actors": [],
        }
    )
    return {
        "schema_version": 1,
        "source": "docs/governance/guild-roster.json",
        "rulesets": rulesets,
    }


def serialize_document(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def normalize_ruleset(raw: dict[str, Any]) -> dict[str, Any]:
    """Strip live-only fields for comparison."""
    conditions = raw.get("conditions") or {}
    ref_name = conditions.get("ref_name") or {}
    include = sorted(ref_name.get("include") or [])
    exclude = sorted(ref_name.get("exclude") or [])
    rules = raw.get("rules") or []
    rule_types = sorted(r.get("type") for r in rules if isinstance(r, dict))
    bypass = raw.get("bypass_actors")
    if bypass is None:
        bypass = []
    return {
        "name": raw.get("name"),
        "target": raw.get("target"),
        "enforcement": raw.get("enforcement", "active"),
        "conditions": {"ref_name": {"include": include, "exclude": exclude}},
        "rules": rule_types,
        "bypass_actors": bypass,
    }


def rulesets_by_name(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for rs in doc.get("rulesets", []):
        name = rs.get("name")
        if not name:
            continue
        out[name] = normalize_ruleset(rs)
    return out


def compare_ruleset_maps(
    declared: dict[str, dict[str, Any]],
    live: dict[str, dict[str, Any]],
) -> list[str]:
    diffs: list[str] = []
    declared_names = set(declared)
    live_names = set(live)
    for missing in sorted(declared_names - live_names):
        diffs.append(f"missing live ruleset named {missing!r}")
    for extra in sorted(live_names - declared_names):
        if extra.startswith("protected-refs-"):
            diffs.append(f"extra live ruleset named {extra!r}")
    for name in sorted(declared_names & live_names):
        want = declared[name]
        got = live[name]
        if want["target"] != got["target"]:
            diffs.append(
                f"{name}: target {got['target']!r} != declared {want['target']!r}"
            )
        want_inc = want["conditions"]["ref_name"]["include"]
        got_inc = got["conditions"]["ref_name"]["include"]
        if want_inc != got_inc:
            diffs.append(
                f"{name}: ref_name include {got_inc!r} != declared {want_inc!r}"
            )
        want_exc = want["conditions"]["ref_name"]["exclude"]
        got_exc = got["conditions"]["ref_name"]["exclude"]
        if want_exc != got_exc:
            diffs.append(
                f"{name}: ref_name exclude {got_exc!r} != declared {want_exc!r}"
            )
        if want.get("enforcement") != got.get("enforcement"):
            diffs.append(
                f"{name}: enforcement {got.get('enforcement')!r} != declared {want.get('enforcement')!r}"
            )
        if want["rules"] != got["rules"]:
            diffs.append(
                f"{name}: rules {got['rules']!r} != declared {want['rules']!r}"
            )
        if got["bypass_actors"]:
            diffs.append(f"{name}: bypass_actors must be empty, got {got['bypass_actors']!r}")
        for rule in ("deletion", "update", "non_fast_forward", "creation"):
            if rule in want["rules"] and rule not in got["rules"]:
                diffs.append(f"{name}: missing rule {rule!r}")
    return diffs


def roster_branch_refnames(roster: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for entry in roster.get("protected_refs", []):
        ref = entry["refname"]
        if ref.startswith("refs/heads/"):
            out.add(ref)
    return out


def load_marshal_policy_refnames(path: Path = MARSHAL_POLICY_PATH) -> set[str]:
    if not path.is_file():
        return set()
    import tomllib

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for entry in data.get("protected_refs", []):
        ref = entry.get("refname", "")
        if isinstance(ref, str) and ref:
            out.add(ref)
    return out


def roster_all_refnames(roster: dict[str, Any]) -> set[str]:
    return {entry["refname"] for entry in roster.get("protected_refs", [])}


def compare_marshal_policy_to_roster(
    roster: dict[str, Any],
    *,
    policy_path: Path | None = None,
) -> list[str]:
    diffs: list[str] = []
    roster_all = roster_all_refnames(roster)
    roster_branches = roster_branch_refnames(roster)
    policy_all = load_marshal_policy_refnames(policy_path or MARSHAL_POLICY_PATH)
    for extra in sorted(policy_all - roster_all):
        diffs.append(
            f"marshal-policy.toml protected_refs declares {extra!r} absent from roster"
        )
    for missing in sorted(roster_branches - policy_all):
        diffs.append(
            f"roster branch entry {missing!r} missing from marshal-policy.toml protected_refs"
        )
    return diffs
