"""Render and compare GitHub rulesets declared from guild-roster protected_refs.

Shared by ``protected_refs_ruleset_check.py`` and its tests. The tracked
``docs/governance/rulesets/protected-refs.json`` is derived from the roster
alone (marshal:AD-12) — never hand-edited.

Every ruleset declares no bypass actor except where its roster entry names one in
``bypass``; the only actor type the roster may name is ``DeployKey``, and only on the
``refs/heads/gitops/`` entry (steward Story 118.9, spec-pyforge-steward CAP-178:
``refs/heads/gitops/**`` is written by ``nic``'s deploy key alone). GitHub's ``DeployKey``
actor admits every deploy key of the repository, so the live check also counts the
repository's write-enabled deploy keys.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ROSTER_PATH = ROOT / "docs" / "governance" / "guild-roster.json"
DOCUMENT_PATH = ROOT / "docs" / "governance" / "rulesets" / "protected-refs.json"

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
    "branch_gitops": "protected-refs-gitops-branches",
}

GITOPS_BRANCH_RULES = ("creation", "update", "deletion", "non_fast_forward")

# The one bypass actor type a roster entry may declare, rendered as GitHub's API spells it
# (``actor_id`` is null for ``DeployKey``).
BYPASS_ACTORS = {
    "DeployKey": {"actor_id": None, "actor_type": "DeployKey", "bypass_mode": "always"},
}
# The one roster entry a bypass actor may sit on: any other ref with a bypass is a finding.
GITOPS_BYPASS_REFNAME = "refs/heads/gitops/"


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


def bypass_actors_for_entry(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """The bypass actors a roster entry declares; ``[]`` unless it names ``bypass``."""
    names = entry.get("bypass") or []
    unknown = [name for name in names if name not in BYPASS_ACTORS]
    if unknown:
        raise ValueError(f"{entry.get('refname')!r}: unsupported bypass actor type(s) {unknown!r}")
    if names and entry.get("refname") != GITOPS_BYPASS_REFNAME:
        raise ValueError(
            f"{entry.get('refname')!r}: only {GITOPS_BYPASS_REFNAME!r} may declare a bypass actor (the DeployKey "
            "bypass admits every deploy key, so it is the gitops branch's alone)"
        )
    return [dict(BYPASS_ACTORS[name]) for name in names]


def _ruleset_name_for_branch_rules(rules: tuple[str, ...]) -> str:
    if rules == GITOPS_BRANCH_RULES:
        return RULESET_NAMES["branch_gitops"]
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
    branch_bypass: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    tag_patterns: list[str] = []
    for entry in entries:
        refname = entry["refname"]
        rules = expected_rules_for_entry(entry)
        bypass = bypass_actors_for_entry(entry)
        if refname.startswith("refs/heads/"):
            if rules in branch_bypass and branch_bypass[rules] != bypass:
                raise ValueError(f"{refname!r}: entries sharing rules {rules!r} declare different bypass actors")
            branch_bypass[rules] = bypass
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
                "bypass_actors": branch_bypass[rules],
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
    bypass = sorted(
        (
            {
                "actor_id": actor.get("actor_id"),
                "actor_type": actor.get("actor_type"),
                "bypass_mode": actor.get("bypass_mode", "always"),
            }
            for actor in raw.get("bypass_actors") or []
            if isinstance(actor, dict)
        ),
        key=lambda actor: (str(actor["actor_type"]), str(actor["actor_id"]), str(actor["bypass_mode"])),
    )
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
        if not want["bypass_actors"] and got["bypass_actors"]:
            diffs.append(f"{name}: bypass_actors must be empty, got {got['bypass_actors']!r}")
        elif want["bypass_actors"] != got["bypass_actors"]:
            diffs.append(f"{name}: bypass_actors {got['bypass_actors']!r} != declared {want['bypass_actors']!r}")
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


def roster_all_refnames(roster: dict[str, Any]) -> set[str]:
    return {entry["refname"] for entry in roster.get("protected_refs", [])}


def declares_deploy_key_bypass(declared: dict[str, dict[str, Any]]) -> bool:
    return any(
        actor.get("actor_type") == "DeployKey" for rs in declared.values() for actor in rs.get("bypass_actors") or []
    )


def deploy_key_findings(keys: list[dict[str, Any]]) -> list[str]:
    """A ``DeployKey`` bypass admits every deploy key, so at most one may write (Story 118.9)."""
    writers = sorted(str(key.get("title", key.get("id"))) for key in keys if key.get("read_only") is False)
    if len(writers) <= 1:
        return []
    return [
        f"{len(writers)} write-enabled deploy keys ({', '.join(writers)}); the DeployKey bypass admits each, "
        "so GITOPS_DEPLOY_KEY must be the only one"
    ]
