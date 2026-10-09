"""Story 87.6: protected ref structural exclusion (pure core)."""

from pyforge.marshal.core import protected_refs


def test_loop_main_and_tag_refs_are_structurally_excluded():
    prefixes = protected_refs.effective_protected_prefixes(roster_prefixes=frozenset())
    assert protected_refs.is_branch_name_structurally_excluded("loop/acme", protected_prefixes=prefixes)
    assert protected_refs.is_branch_name_structurally_excluded("main", protected_prefixes=prefixes)
    assert protected_refs.is_branch_name_structurally_excluded(
        "refs/tags/preserve/acme/1.1/x", protected_prefixes=prefixes
    )
    assert protected_refs.is_branch_name_structurally_excluded("preserve/foo", protected_prefixes=prefixes)
    assert not protected_refs.is_branch_name_structurally_excluded("acme-4-10", protected_prefixes=prefixes)


def test_roster_prefixes_union_with_floor():
    roster = frozenset({"refs/heads/attempt-preserve/"})
    prefixes = protected_refs.effective_protected_prefixes(roster_prefixes=roster)
    assert protected_refs.is_branch_name_structurally_excluded(
        "attempt-preserve/foo", protected_prefixes=prefixes
    )
