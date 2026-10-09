"""Protected refname prefixes for land/retire (Story 87.6, CAP-287 / AD-47).

Pure data and matching only (AD-4): roster JSON is read at the CLI boundary;
this module never touches the filesystem.
"""

from __future__ import annotations

# Code floor (review M3): always unioned with roster and policy additions.
_PROTECTED_BRANCH_FLOOR: frozenset[str] = frozenset({"refs/heads/main", "refs/heads/loop/"})
_PROTECTED_TAG_FLOOR: frozenset[str] = frozenset({"refs/tags/"})
_BRANCH_NAME_FLOOR: frozenset[str] = frozenset({"main", "loop/"})
_STRUCTURAL_BRANCH_PREFIXES: frozenset[str] = frozenset(
    {"preserve/", "archive/", "rescue/"},
)
# A policy entry that starts with one of these asks to REMOVE a ref from the
# protected list -- refused, since a policy layer may only add (AD-47, AD-27).
_REMOVAL_MARKERS: tuple[str, ...] = ("!", "^")


def protected_branch_floor() -> frozenset[str]:
    return _PROTECTED_BRANCH_FLOOR


def ref_matches_prefix(refname: str, prefix: str) -> bool:
    if refname == prefix:
        return True
    if prefix.endswith("/") and refname.startswith(prefix):
        return True
    if not prefix.endswith("/") and refname.startswith(prefix + "/"):
        return True
    return False


def ref_matches_any_prefix(refname: str, prefixes: frozenset[str] | set[str]) -> bool:
    return any(ref_matches_prefix(refname, p) for p in prefixes)


def branch_to_head_refname(branch: str) -> str:
    branch = branch.strip()
    if branch.startswith("refs/"):
        return branch
    return f"refs/heads/{branch}"


def effective_protected_prefixes(
    *,
    roster_prefixes: frozenset[str] | set[str],
    policy_additions: tuple[str, ...] = (),
) -> frozenset[str]:
    merged: set[str] = set(_PROTECTED_BRANCH_FLOOR)
    merged.update(_PROTECTED_TAG_FLOOR)
    merged.update(roster_prefixes)
    merged.update(policy_additions)
    return frozenset(merged)


def is_branch_name_structurally_excluded(
    branch: str,
    *,
    protected_prefixes: frozenset[str] | set[str],
) -> bool:
    """Structural exclusion before evidence-gathering (Story 87.6)."""
    if not branch:
        return True
    if branch.startswith("refs/tags/"):
        return True
    head_ref = branch_to_head_refname(branch)
    if ref_matches_any_prefix(head_ref, protected_prefixes):
        return True
    if branch in _BRANCH_NAME_FLOOR or branch == "main":
        return True
    if branch.startswith("loop/"):
        return True
    if any(branch.startswith(p) for p in _STRUCTURAL_BRANCH_PREFIXES):
        return True
    return False


def parse_roster_protected_prefixes(entries: object) -> frozenset[str]:
    if not isinstance(entries, list):
        return frozenset()
    out: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        refname = entry.get("refname")
        rules = entry.get("rules")
        if not isinstance(refname, str) or not isinstance(rules, list):
            continue
        if "deletion" not in rules:
            continue
        out.add(refname)
    return frozenset(out)


def protected_floor() -> frozenset[str]:
    """The code floor every protected list starts from: the branch floor plus
    all of ``refs/tags/``. No policy layer can remove an entry from it."""
    return _PROTECTED_BRANCH_FLOOR | _PROTECTED_TAG_FLOOR


def floor_entries_weakened_by(value: object) -> tuple[str, ...]:
    """The floor entries a policy value tries to remove, sorted; ``()`` when it
    tries none.

    A policy layer may only add prefixes. An entry spelled as a removal -- a
    leading ``!`` or ``^`` (git's own negative-refspec marker) -- weakens the
    floor when the ref it names overlaps a floor entry: it covers the entry
    (``!refs/heads/`` drops ``refs/heads/main`` and ``refs/heads/loop/``) or
    carves a hole in it (``!refs/heads/loop/acme``). A removal that overlaps no
    floor entry is malformed rather than weakening, and is left to
    ``validate_policy_protected_additions``."""
    if not isinstance(value, (list, tuple)):
        return ()
    weakened: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        entry = item.strip()
        if not entry or entry[0] not in _REMOVAL_MARKERS:
            continue
        target = entry[1:].strip()
        if not target:
            continue
        for floor_entry in protected_floor():
            if ref_matches_prefix(floor_entry, target) or ref_matches_prefix(target, floor_entry):
                weakened.add(floor_entry)
    return tuple(sorted(weakened))


def validate_policy_protected_additions(value: object) -> tuple[str, ...] | None:
    """Policy may only extend the floor; entries must be non-empty refname prefixes."""
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        return None
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        prefix = item.strip()
        if not prefix.startswith("refs/"):
            return None
        # Cannot "remove" floor by re-declaring a strict subset intent — additions only.
        if prefix in _PROTECTED_BRANCH_FLOOR or prefix in _PROTECTED_TAG_FLOOR:
            continue
        out.append(prefix)
    return tuple(out)
