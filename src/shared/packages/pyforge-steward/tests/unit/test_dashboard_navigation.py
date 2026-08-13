"""Story 9.2 — `Page` construction-time validation + `build_navigation` (CAP-3)."""

from __future__ import annotations

import pytest

from pyforge.steward.dashboard.navigation import Page, build_navigation


def test_page_accepts_a_path_label_and_role_vocabulary():
    page = Page(path="/sales", label="Sales", roles=("east", "west"))
    assert page.path == "/sales"
    assert page.label == "Sales"
    assert page.roles == ("east", "west")


def test_page_rejects_an_empty_path():
    with pytest.raises(ValueError, match="path"):
        Page(path="", label="Sales", roles=("east",))


def test_page_rejects_an_empty_label():
    with pytest.raises(ValueError, match="label"):
        Page(path="/sales", label="", roles=("east",))


def test_page_rejects_whitespace_only_path_and_label():
    with pytest.raises(ValueError, match="path"):
        Page(path="   ", label="Sales", roles=("east",))
    with pytest.raises(ValueError, match="label"):
        Page(path="/sales", label="\t", roles=("east",))


def test_page_rejects_whitespace_padded_path_and_label():
    """Mirrors `AccessDeclaration.access_column`'s padding rejection (not
    trimming) — a padded value is not what a caller actually sees or where
    the route is actually mounted.
    """
    with pytest.raises(ValueError, match="leading/trailing whitespace"):
        Page(path=" /sales", label="Sales", roles=("east",))
    with pytest.raises(ValueError, match="leading/trailing whitespace"):
        Page(path="/sales", label="Sales\n", roles=("east",))


def test_page_rejects_a_non_string_path_or_label():
    with pytest.raises(TypeError, match="path"):
        Page(path=123, label="Sales", roles=("east",))
    with pytest.raises(TypeError, match="label"):
        Page(path="/sales", label=None, roles=("east",))


def test_page_rejects_empty_roles():
    with pytest.raises(ValueError, match="roles"):
        Page(path="/sales", label="Sales", roles=())


def test_page_rejects_a_bare_string_for_roles():
    """A bare string is iterable, so truthiness alone would pass it -- it
    must be rejected by type, since iterating it later would silently
    produce one-character "roles" instead of the intended role names.
    """
    with pytest.raises(TypeError, match="roles"):
        Page(path="/sales", label="Sales", roles="east")


def test_page_rejects_non_string_role_elements():
    with pytest.raises(TypeError, match=r"roles\[0\]"):
        Page(path="/sales", label="Sales", roles=(1, "east"))


def test_page_rejects_an_empty_or_whitespace_only_role_element():
    with pytest.raises(ValueError, match=r"roles\[1\]"):
        Page(path="/sales", label="Sales", roles=("east", ""))
    with pytest.raises(ValueError, match=r"roles\[1\]"):
        Page(path="/sales", label="Sales", roles=("east", "  "))


def test_page_rejects_a_whitespace_padded_role_element():
    with pytest.raises(ValueError, match=r"roles\[0\]"):
        Page(path="/sales", label="Sales", roles=(" east",))


def test_build_navigation_returns_only_pages_the_role_may_see():
    east_page = Page(path="/east", label="East", roles=("east",))
    west_page = Page(path="/west", label="West", roles=("west",))
    shared_page = Page(path="/shared", label="Shared", roles=("east", "west"))
    pages = (east_page, west_page, shared_page)

    assert build_navigation("east", pages) == (east_page, shared_page)


def test_build_navigation_preserves_declared_order():
    first = Page(path="/a", label="A", roles=("viewer",))
    second = Page(path="/b", label="B", roles=("viewer",))
    third = Page(path="/c", label="C", roles=("viewer",))

    assert build_navigation("viewer", (third, first, second)) == (third, first, second)


def test_build_navigation_with_no_identity_returns_an_empty_tuple():
    pages = (
        Page(path="/a", label="A", roles=("viewer",)),
        Page(path="/b", label="B", roles=("admin",)),
    )

    assert build_navigation(None, pages) == ()


def test_build_navigation_with_no_matching_role_returns_an_empty_tuple():
    """An unrecognized role is not a build_navigation error (unlike
    `filter_by_role`'s row-level check) -- it simply matches no page's
    declared roles, same as any other role that owns no pages here.
    """
    pages = (Page(path="/a", label="A", roles=("admin",)),)

    assert build_navigation("superadmin", pages) == ()


def test_build_navigation_with_an_empty_page_list_returns_an_empty_tuple():
    assert build_navigation("viewer", ()) == ()
