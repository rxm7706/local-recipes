"""Story 87.6: protected ref structural exclusion (pure core)."""

from pyforge.marshal.core import protected_refs


def test_protected_branch_floor():
    assert "refs/heads/main" in protected_refs.protected_branch_floor()


def test_ref_matches_prefix():
    assert protected_refs.ref_matches_prefix("refs/heads/main", "refs/heads/main")
    assert protected_refs.ref_matches_prefix("refs/heads/loop/x", "refs/heads/loop/")
    assert protected_refs.ref_matches_prefix("refs/heads/foo/bar", "refs/heads/foo")
    assert not protected_refs.ref_matches_prefix("refs/heads/other", "refs/heads/foo")


def test_ref_matches_any_prefix():
    prefixes = frozenset({"refs/heads/main", "refs/tags/"})
    assert protected_refs.ref_matches_any_prefix("refs/tags/v1", prefixes)
    assert not protected_refs.ref_matches_any_prefix("refs/heads/feature/x", prefixes)


def test_branch_to_head_refname():
    assert protected_refs.branch_to_head_refname("main") == "refs/heads/main"
    assert protected_refs.branch_to_head_refname("  main  ") == "refs/heads/main"
    assert protected_refs.branch_to_head_refname("refs/heads/loop/x") == "refs/heads/loop/x"


def test_effective_protected_prefixes_policy_additions():
    prefixes = protected_refs.effective_protected_prefixes(
        roster_prefixes=frozenset(),
        policy_additions=("refs/heads/custom/",),
    )
    assert "refs/heads/custom/" in prefixes
    assert "refs/heads/main" in prefixes


def test_empty_branch_structurally_excluded():
    prefixes = protected_refs.effective_protected_prefixes(roster_prefixes=frozenset())
    assert protected_refs.is_branch_name_structurally_excluded("", protected_prefixes=prefixes)


def test_archive_and_rescue_structurally_excluded():
    prefixes = protected_refs.effective_protected_prefixes(roster_prefixes=frozenset())
    assert protected_refs.is_branch_name_structurally_excluded("archive/old", protected_prefixes=prefixes)
    assert protected_refs.is_branch_name_structurally_excluded("rescue/wip", protected_prefixes=prefixes)


def test_parse_roster_protected_prefixes():
    assert protected_refs.parse_roster_protected_prefixes(None) == frozenset()
    assert protected_refs.parse_roster_protected_prefixes("not-a-list") == frozenset()
    entries = [
        {"refname": "refs/heads/attempt-preserve/", "rules": ["deletion"]},
        {"refname": "refs/heads/skip", "rules": ["other"]},
        {"bad": "entry"},
        {"refname": 1, "rules": ["deletion"]},
    ]
    assert protected_refs.parse_roster_protected_prefixes(entries) == frozenset({"refs/heads/attempt-preserve/"})


def test_validate_policy_protected_additions():
    assert protected_refs.validate_policy_protected_additions(None) == ()
    assert protected_refs.validate_policy_protected_additions(()) == ()
    assert protected_refs.validate_policy_protected_additions(["refs/heads/extra/"]) == ("refs/heads/extra/",)
    # Floor entries are skipped (additions only).
    assert protected_refs.validate_policy_protected_additions(["refs/heads/main"]) == ()
    assert protected_refs.validate_policy_protected_additions("bad") is None
    assert protected_refs.validate_policy_protected_additions([""]) is None
    assert protected_refs.validate_policy_protected_additions(["not-a-ref"]) is None


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
    assert protected_refs.is_branch_name_structurally_excluded("attempt-preserve/foo", protected_prefixes=prefixes)


def test_protected_floor_is_the_branch_floor_plus_every_tag():
    assert protected_refs.protected_floor() == frozenset({"refs/heads/main", "refs/heads/loop/", "refs/tags/"})


def test_floor_entries_weakened_by_names_each_floor_entry_a_removal_overlaps():
    weakened = protected_refs.floor_entries_weakened_by
    assert weakened(["!refs/heads/loop/"]) == ("refs/heads/loop/",)
    assert weakened(["^refs/heads/main"]) == ("refs/heads/main",)
    # A removal that covers the floor entry, or carves a hole in it.
    assert weakened(["!refs/heads/"]) == ("refs/heads/loop/", "refs/heads/main")
    assert weakened(["!refs/heads/loop/acme"]) == ("refs/heads/loop/",)
    assert weakened(["  ! refs/tags/preserve/ "]) == ("refs/tags/",)


def test_floor_entries_weakened_by_ignores_additions_and_off_floor_removals():
    weakened = protected_refs.floor_entries_weakened_by
    assert weakened(["refs/heads/main", "refs/heads/release/"]) == ()
    assert weakened(["!refs/heads/feature/", "!refs/heads/mainline"]) == ()
    assert weakened(["!", "", 3]) == ()
    assert weakened("!refs/heads/loop/") == ()
    assert weakened(None) == ()
