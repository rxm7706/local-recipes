"""Story 109.3 — the listing rules, the folder rule and the folder scan of the marketplace index.

Split from ``test_marketplace_pages.py`` by subject (Story 109.8, ``DW-steward-109-3-7``: TEA's H5 on a 1,578-line
file). The review of 2026-10-28 added one negative test per listing rule; later loops added the containment cases.
"""

from __future__ import annotations

import datetime as dt
import os
import threading
from pathlib import Path

import pytest
from marketplace_testkit import _flags_tree, _listing, _marketplace, _module, _skill

from pyforge.steward.bootstrap import repo_root
from pyforge.steward.marketplace_pages import (
    MAX_SHIPPED_FILE_BYTES,
    MAX_SHIPPED_FOLDER_BYTES,
    SCHEMA_ID,
    MarketplaceIndexError,
    _steps_text,
    listing_from_estate_module,
    listings_from_document,
    listings_from_skill_folders,
    load_listings,
    render_skill_card,
    validate_listing,
    write_plugin_manifests,
    write_site,
    write_site_from_index,
)

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads docs/foundry/marketplace and the estate skill
# copies, so it runs in the station's live-tree half and fires on those paths, not on every edit of the package.
pytestmark = pytest.mark.live_tree

_CATALOG = Path("src/shared/packages/pyforge-steward/catalog")
_MARKETPLACE = Path("docs/foundry/marketplace")


@pytest.fixture(autouse=True)
def _dev_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """The flag tree is read for ``dev`` (where the flag is on), whatever the shell exports."""
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")


# --- loading ----------------------------------------------------------------------------------


def test_estate_registry_with_no_modules_loads_as_no_listings() -> None:
    path = repo_root() / _CATALOG / "registry" / "estate.yaml"
    assert load_listings(path) == []


def test_an_estate_module_row_becomes_a_module_listing() -> None:
    row = listing_from_estate_module(
        {
            "name": "bmad-builder",
            "description": "Author modules",
            "repository": "https://github.com/example/bmad-builder",
            "version": "1.2.0",
            "trust_tier": "bmad-certified",
            "source": "estate-listings",
            "install_hint": "bmad-method install",
        }
    )
    assert row["kind"] == "module"
    assert row["id"] == "module/bmad-builder"
    assert row["trust_tier"] == "bmad-certified"
    assert row["source"] == "estate-listings"
    assert row["install_hint"] == "bmad-method install"
    validate_listing(row)


@pytest.mark.parametrize("name", ["../Builder", "Builder", "a b", "x/y", "bmad\n", " bmad"])  # loop 4, row 77: raw
def test_an_estate_module_name_must_be_a_slug(name: str) -> None:
    with pytest.raises(MarketplaceIndexError, match="must match"):
        listing_from_estate_module({"name": name})


# --- the listing rules (review 2026-10-28, rows 2, 3 and 10) -----------------------------------


def test_a_skill_whose_path_does_not_match_scope_and_slug_is_refused(tmp_path: Path) -> None:
    row = _skill()
    row["path"] = "skills/other/environment"
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="path"):
        write_site([row], tmp_path / "site", flags_path=on)
    assert not (tmp_path / "site").exists()


@pytest.mark.parametrize(
    ("edit", "needle"),
    [
        ({"scope": "..", "path": "skills/../environment", "id": "../environment"}, "scope"),
        ({"slug": "Env", "path": "skills/mason/Env", "id": "mason/Env"}, "slug"),
        ({"slug": "a/b", "path": "skills/mason/a/b", "id": "mason/a/b"}, "slug"),
        ({"id": "mason/other"}, "a skill's id must be"),
        ({"requires": {"packages": [{"name": "pyforge-mason", "published": "false"}]}}, "published: true or false"),
        ({"requires": {"packages": [{"published": False}]}}, "name must be a non-empty string"),
        ({"requires": [{"kind": "package", "name": "x", "published": None}]}, "published: true or false"),
        ({"requires": {"packages": []}}, "code-backed requires at least one package"),
        ({"contribution_lane": "instructions-only"}, "instructions-only names a package"),
        ({"docs": {"steps": "../../README.md"}}, "docs.steps"),
        ({"docs": {"steps": "/etc/passwd"}}, "docs.steps"),
        ({"docs": {"card": "site/skills/mason/environment.html"}}, "docs.card"),
        ({"verified_at": dt.date(2026, 10, 21)}, "unquoted"),
        ({"verified_at": "21 Oct 2026"}, "verified_at"),
        ({"install": {"targets": [".claude/skills/../../.ssh"]}}, "install target"),
        ({"install": {"targets": ["/.claude/skills/x"]}}, "install target"),
        ({"install": {"targets": [".agents/skills//x"]}}, "install target"),
        ({"install": {"targets": [".agents/skills/x/y"]}}, "install target"),
        ({"install": {"targets": [".claude/skills/Bad_Name"]}}, "install target"),
        ({"install": {"targets": ["skills/mason-environment"]}}, "install target"),
        # loop 2
        ({"scope": " mason", "path": "skills/ mason/environment"}, "scope"),
        ({"install": {"targets": [".agents/skills/./x"]}}, "install target"),
        ({"verified_at": "2026-99-99"}, "not a calendar date"),
        ({"ci": {"checked": dt.date(2026, 10, 21)}}, "is not JSON"),
        ({"contribution_lane": None}, "lane is required for a skill"),
        # loop 3, row 57: the slug grammar is matched whole, so a double-quoted YAML scalar's newline is refused
        ({"scope": "mason\n", "path": "skills/mason\n/environment"}, "scope"),
        ({"slug": "environment\n"}, "slug"),
        ({"install": {"targets": [".claude/skills/x\n"]}}, "install target"),
        # loop 3, row 53: id and path are compared raw, not stripped
        ({"id": " mason/environment"}, "surrounding whitespace"),
        ({"id": "mason/environment\n"}, "surrounding whitespace"),
        ({"path": "skills/mason/environment "}, "surrounding whitespace"),
        # loop 4, row 66: every enumerated or rendered field is compared raw
        ({"kind": " skill"}, "surrounding whitespace"),
        ({"trust_tier": "unverified "}, "surrounding whitespace"),
        ({"source": " estate-listings"}, "surrounding whitespace"),
        ({"name": "@mason/environment\n"}, "surrounding whitespace"),
        ({"requires": {"packages": [{"name": " pyforge-mason", "published": False}]}}, "surrounding whitespace"),
        # loop 5, row 84: related is a list of strings; an @ entry is a whole @<scope>/<slug>
        ({"related": 5}, "related must be a list of strings"),
        ({"related": "@warden/scan"}, "related must be a list of strings"),
        ({"related": {"a": 1}}, "related must be a list of strings"),
        ({"related": [5]}, "related must be a list of strings"),
        ({"related": ["@Warden/Scan"]}, "must be @<scope>/<slug>"),
        ({"related": ["@warden/scan/extra"]}, "must be @<scope>/<slug>"),
        ({"related": ["@"]}, "must be @<scope>/<slug>"),
        # Story 109.8, DW-steward-109-3-1: an entry is held whole like every other string field
        ({"related": ["@warden/scan\n"]}, "related '@warden/scan\\\\n' carries surrounding whitespace"),
        ({"related": [" @warden/scan"]}, "related ' @warden/scan' carries surrounding whitespace"),
        ({"related": ["\t@warden/scan"]}, "carries surrounding whitespace"),
        ({"related": ["see also "]}, "carries surrounding whitespace"),
        ({"related": [""]}, "related '' is empty"),
        ({"related": [" "]}, "related ' ' is empty"),
        ({"related": ["\t"]}, "is empty"),
        ({"related": ["@warden/scan", "@warden/scan"]}, "related '@warden/scan' appears twice"),
        ({"related": ["notes", "notes"]}, "related 'notes' appears twice"),
    ],
)
def test_each_listing_rule_refuses_its_breach(edit: dict, needle: str) -> None:
    row = _skill()
    row.update(edit)
    with pytest.raises(MarketplaceIndexError, match=needle):
        validate_listing(row)


# moved from test_marketplace_pages.py: a listing rule (Story 109.8, review loop 2, row 13)
def test_a_tier_that_does_not_match_trust_tier_is_refused() -> None:
    row = _skill()
    row["tier"] = "estate-reviewed"
    row["trust_tier"] = "unverified"
    with pytest.raises(MarketplaceIndexError, match="maps to"):
        validate_listing(row)


def test_install_targets_accept_the_two_roots_and_one_folder_under_each() -> None:
    row = _skill()
    row["install"] = {
        "targets": [".agents/skills", ".claude/skills", ".agents/skills/mason-environment", ".claude/skills/x-1"]
    }
    validate_listing(row)


@pytest.mark.parametrize(
    ("second", "needle"),
    [
        ({}, "duplicate id"),
        ({"id": "Mason/environment", "scope": "Mason", "path": "skills/Mason/environment"}, "scope"),
        # loop 4, row 60: the site release's own asset name is never a plugin and zip name
        (
            {"id": "pages/site", "scope": "pages", "slug": "site", "path": "skills/pages/site"},
            "site release's own asset",
        ),
        # loop 4, row 76: a related @scope/slug names a listing
        (
            {"id": "mason/x", "slug": "x", "path": "skills/mason/x", "related": ["@warden/scan"]},
            "names no skill listing",
        ),
    ],
)
def test_duplicate_ids_and_plugin_names_are_refused(second: dict, needle: str) -> None:
    other = _skill()
    other.update(second)
    with pytest.raises(MarketplaceIndexError, match=needle):
        listings_from_document({"schema": SCHEMA_ID, "listings": [_skill(), other]})


def test_a_related_reference_names_a_skill_listing_not_a_module() -> None:
    """Loop 5, row 83: ``@module/bmad`` passed the cross-reference against the module's id and the card linked
    ``skills/module/bmad.html``, which no render produces (the module's card is ``modules/bmad.html``); a whole-value
    match, so a trailing newline is refused by the listing rule before the cross-reference runs."""
    skill = _skill()
    skill["related"] = ["@module/bmad"]
    with pytest.raises(MarketplaceIndexError, match="related @module/bmad names no skill listing"):
        listings_from_document({"schema": SCHEMA_ID, "listings": [skill, _module("bmad")]})
    skill["related"] = ["@warden/scan\n"]
    with pytest.raises(MarketplaceIndexError, match="carries surrounding whitespace"):
        listings_from_document({"schema": SCHEMA_ID, "listings": [skill, _module("bmad")]})
    other = _skill()
    other.update({"id": "warden/scan", "scope": "warden", "slug": "scan", "path": "skills/warden/scan"})
    skill["related"] = ["@warden/scan", "warden/scan"]  # the second is text, not a reference
    rows = listings_from_document({"schema": SCHEMA_ID, "listings": [skill, other]})
    card = render_skill_card(rows[0])
    assert '<li><a href="../warden/scan.html">@warden/scan</a></li><li>warden/scan</li>' in card


def test_distinct_scope_slug_and_plugin_name_are_accepted() -> None:
    other = _skill()
    other.update(
        {"id": "mason-x/environment", "scope": "mason-x", "slug": "environment", "path": "skills/mason-x/environment"}
    )
    rows = listings_from_document({"schema": SCHEMA_ID, "listings": [_skill(), other]})
    assert [row["id"] for row in rows] == ["mason-x/environment", "mason/environment"]


@pytest.mark.parametrize(
    ("row", "needle"),
    [
        (_module("../x"), "names the card"),
        # loop 4, row 70: the non-skill name rule is observed (a trailing newline is now row 66's, caught earlier)
        (dict(_module("x"), name="x y"), "names the card"),
        (dict(_module("x"), name="x\n"), "surrounding whitespace"),
        (dict(_module("x"), kind="agent", id="agent/x", slug="../x"), "slug"),
        (_module("x", path="/etc"), "path"),
        (_module("x", path="../../.."), "path"),
        (_module("x", path="skills/x"), "path"),
        (_module("x", docs={"steps": "hostname"}), "no path"),
    ],
)
def test_a_non_skill_row_keeps_to_its_own_directory(row: dict, needle: str, tmp_path: Path) -> None:
    """Loop 2, row 20: an agent or module row's name, slug and path are held to the kind's directory, and a
    ``docs.steps`` with no path to read it under is refused rather than silently dropped."""
    with pytest.raises(MarketplaceIndexError, match=needle):
        validate_listing(row, root=tmp_path)


def test_a_non_skill_path_cannot_read_outside_the_marketplace(tmp_path: Path) -> None:
    (tmp_path / "secret.md").write_text("# not for a card\n", encoding="utf-8")
    row = _module("x", path="../x", docs={"steps": "secret.md"})  # past validate_listing only by a direct call
    with pytest.raises(MarketplaceIndexError, match="must stay inside"):
        _steps_text(row, tmp_path / "marketplace")
    row = _module("x", path="modules/x", docs={"steps": "../secret.md"})
    (tmp_path / "marketplace" / "modules" / "x").mkdir(parents=True)
    with pytest.raises(MarketplaceIndexError, match="docs.steps"):
        validate_listing(row, root=tmp_path / "marketplace")


def test_two_modules_that_map_to_one_card_are_refused() -> None:
    with pytest.raises(MarketplaceIndexError, match="card modules/a.html is also"):
        listings_from_document({"schema": SCHEMA_ID, "listings": [_module("a"), _module("b", slug="a")]})


def test_two_listings_that_share_a_plugin_name_are_refused() -> None:
    first = _skill()
    first.update({"id": "a-b/c", "scope": "a-b", "slug": "c", "path": "skills/a-b/c"})
    second = _skill()
    second.update({"id": "a/b-c", "scope": "a", "slug": "b-c", "path": "skills/a/b-c"})
    with pytest.raises(MarketplaceIndexError, match="plugin and zip name a-b-c"):
        listings_from_document({"schema": SCHEMA_ID, "listings": [first, second]})


def test_a_declared_folder_must_exist_with_its_skill_md(tmp_path: Path) -> None:
    root = _marketplace(tmp_path)
    (root / "skills/mason/environment/SKILL.md").unlink()
    with pytest.raises(MarketplaceIndexError, match="SKILL.md is missing"):
        load_listings(root / "index.yaml", root=root)
    (root / "skills/mason/environment").rename(root / "skills/mason/gone")
    with pytest.raises(MarketplaceIndexError, match="is not a directory in"):
        load_listings(root / "index.yaml", root=root)


@pytest.mark.parametrize("level", ["skills/mason/environment", "skills/mason", "skills"])
def test_a_symlinked_listing_folder_at_any_level_is_refused_and_nothing_is_written(tmp_path: Path, level: str) -> None:
    """Loop 3, rows 42 and 44: the validator, not only the renderer, refuses a folder reached through a symlink
    (the leaf, its scope directory or ``skills/`` itself pointing outside the tree), so neither the site nor a
    manifest is written for it."""
    outside = tmp_path / "outside"
    real = _marketplace(outside)  # a real tree, elsewhere
    root = tmp_path / "marketplace"
    root.mkdir()
    (root / "index.yaml").write_bytes((real / "index.yaml").read_bytes())
    (root / level).parent.mkdir(parents=True, exist_ok=True)
    (root / level).symlink_to(real / level)
    assert (root / "skills/mason/environment/SKILL.md").is_file()  # the link resolves: the refusal is the rule
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="is a symlink"):
        load_listings(root / "index.yaml", root=root)
    with pytest.raises(MarketplaceIndexError, match="is a symlink"):
        write_site_from_index(root / "index.yaml", tmp_path / "site", flags_path=on)
    assert not (tmp_path / "site").exists()
    with pytest.raises(MarketplaceIndexError, match="is a symlink"):
        write_plugin_manifests(root / "index.yaml", flags_path=on)
    assert not (root / ".claude-plugin").exists() and not (root / ".agents").exists()
    # the renderer's own defence, past the validator: resolve and contain
    with pytest.raises(MarketplaceIndexError, match="resolves outside the marketplace"):
        _steps_text(_listing(), root)


def test_the_folder_scan_refuses_a_symlinked_scope_or_slug_before_reading_it(tmp_path: Path) -> None:
    """Loop 4, row 64: ``_skill_folders`` followed a link and parsed an outside ``listing.yaml`` before the validator
    could refuse the folder; a malformed one surfaced as a raw ``yaml`` error."""
    root = tmp_path / "marketplace"
    (root / "skills" / "mason").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "listing.yaml").write_text(": : not yaml [", encoding="utf-8")
    (root / "skills" / "mason" / "linked").symlink_to(outside)
    with pytest.raises(MarketplaceIndexError, match="skills/mason/linked is a symlink"):
        listings_from_skill_folders(root)
    (root / "skills" / "mason" / "linked").unlink()
    # a scope name that sorts before the now-empty mason/, which the scan refuses as empty (Story 109.8)
    (root / "skills" / "elsewhere").symlink_to(outside)
    with pytest.raises(MarketplaceIndexError, match="skills/elsewhere is a symlink"):
        listings_from_skill_folders(root)
    (root / "skills" / "elsewhere").unlink()
    # a malformed listing.yaml in a real folder, and a malformed index, are listing errors, never a raw yaml error
    real = root / "skills" / "mason" / "environment"
    real.mkdir()
    (real / "listing.yaml").write_text(": : not yaml [", encoding="utf-8")
    with pytest.raises(MarketplaceIndexError, match="not valid YAML"):
        listings_from_skill_folders(root)
    (root / "index.yaml").write_text(": : not yaml [", encoding="utf-8")
    with pytest.raises(MarketplaceIndexError, match="not valid YAML"):
        load_listings(root / "index.yaml", root=root)
    # loop 5, row 86: a listing that is not UTF-8 is a listing error too, never a raw UnicodeDecodeError
    (real / "listing.yaml").write_bytes(b"id: \xff\n")
    with pytest.raises(MarketplaceIndexError, match="not a readable UTF-8 text file"):
        listings_from_skill_folders(root)
    (root / "index.yaml").write_bytes(b"id: \xff\n")
    with pytest.raises(MarketplaceIndexError, match="not a readable UTF-8 text file"):
        load_listings(root / "index.yaml", root=root)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs on this platform")
def test_a_listing_that_is_not_a_regular_file_is_refused_before_it_is_read(tmp_path: Path) -> None:
    """Loop 6, row 98: ``read_text`` on a FIFO ``index.yaml`` blocked the render forever, before row 86's wrap could
    fire; a directory where the index should be is refused the same way, and an absent index is the read's own
    listing error (row 102: the ``OSError`` half of row 86, observed)."""
    root = _marketplace(tmp_path)
    (root / "index.yaml").unlink()
    os.mkfifo(root / "index.yaml")
    outcome: dict[str, BaseException] = {}

    def load() -> None:
        try:
            load_listings(root / "index.yaml", root=root)
        except BaseException as exc:  # noqa: BLE001 -- the thread reports whatever the call raised
            outcome["exc"] = exc

    reader = threading.Thread(target=load, daemon=True)
    reader.start()
    reader.join(5)
    if reader.is_alive():
        os.close(os.open(root / "index.yaml", os.O_WRONLY | os.O_NONBLOCK))  # end the blocked read with EOF
        reader.join(5)
        pytest.fail("load_listings blocked reading a FIFO index")
    assert isinstance(outcome.get("exc"), MarketplaceIndexError)
    assert "not a regular file" in str(outcome["exc"])
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="not a regular file"):
        write_site_from_index(root / "index.yaml", tmp_path / "site", flags_path=on)
    (root / "index.yaml").unlink()
    (root / "index.yaml").mkdir()
    with pytest.raises(MarketplaceIndexError, match="not a regular file"):
        load_listings(root / "index.yaml", root=root)
    (root / "index.yaml").rmdir()
    with pytest.raises(MarketplaceIndexError, match="not a readable UTF-8 text file"):
        load_listings(root / "index.yaml", root=root)
    assert not (tmp_path / "site").exists()


def test_the_folder_scan_refuses_a_symlinked_skills_directory_before_reading_it(tmp_path: Path) -> None:
    """Loop 5, row 91: the ``skills/`` level of the scan's refusal, reached through the scan itself (the validator's
    own ``[skills]`` case reaches its refusal through ``_contained_folder``)."""
    outside = _marketplace(tmp_path / "outside")
    root = tmp_path / "marketplace"
    root.mkdir()
    (root / "skills").symlink_to(outside / "skills")
    with pytest.raises(MarketplaceIndexError, match="^skills is a symlink"):
        listings_from_skill_folders(root)


@pytest.mark.parametrize(
    ("stray", "needle"),
    [
        ("skills/stray.txt", "skills/stray.txt is not a directory; only skill folders sit under skills/"),
        (
            "skills/mason/README.md",
            "skills/mason/README.md is not a directory; only skill folders sit under skills/mason/",
        ),
        ("skills/.DS_Store", "skills/.DS_Store is not a directory"),
    ],
)
def test_a_stray_file_between_the_skill_folders_is_refused(tmp_path: Path, stray: str, needle: str) -> None:
    """Loop 5, row 90: a non-directory under ``skills/`` or ``skills/<scope>/`` was skipped silently by the scan, so a
    stray between the folders was nobody's (the validator sees inside a folder; ``pages-check`` sees the mount)."""
    root = _marketplace(tmp_path)
    (root / stray).write_text("stray\n", encoding="utf-8")
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match=needle):
        listings_from_skill_folders(root)
    with pytest.raises(MarketplaceIndexError, match=needle):
        write_site_from_index(root / "index.yaml", tmp_path / "site", flags_path=on)
    assert not (tmp_path / "site").exists()
    with pytest.raises(MarketplaceIndexError, match=needle):
        write_plugin_manifests(root / "index.yaml", flags_path=on)


def test_a_symlinked_or_absent_non_skill_folder_is_refused(tmp_path: Path) -> None:
    """Loop 3, rows 42 and 44: the same containment on a module's or agent's ``path``."""
    root = tmp_path / "marketplace"
    (root / "modules").mkdir(parents=True)
    with pytest.raises(MarketplaceIndexError, match="is not a directory in"):
        validate_listing(_module("x", path="modules/x"), root=root)
    (tmp_path / "elsewhere").mkdir()
    (root / "modules" / "x").symlink_to(tmp_path / "elsewhere")
    with pytest.raises(MarketplaceIndexError, match="is a symlink"):
        validate_listing(_module("x", path="modules/x"), root=root)
    (root / "modules" / "x").unlink()
    (root / "modules" / "x").mkdir()
    validate_listing(_module("x", path="modules/x"), root=root)  # a real directory passes


def test_every_skill_folder_must_be_declared(tmp_path: Path) -> None:
    root = _marketplace(tmp_path)
    extra = root / "skills/mason/extra"
    extra.mkdir()
    (extra / "SKILL.md").write_text("# x\n", encoding="utf-8")
    with pytest.raises(MarketplaceIndexError, match="no listing.yaml"):
        listings_from_skill_folders(root)
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="the index does not declare"):
        write_site_from_index(root / "index.yaml", tmp_path / "site", flags_path=on)
    assert not (tmp_path / "site").exists()


def test_a_traversing_docs_steps_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    row = _listing()
    row["docs"]["steps"] = "../../index.yaml"
    root = _marketplace(tmp_path, [row])
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="docs.steps"):
        write_site_from_index(root / "index.yaml", tmp_path / "site", flags_path=on)
    assert not (tmp_path / "site").exists()
    # the same breach past the schema check: a symlink that leaves the folder
    row = _listing()
    row["docs"]["steps"] = "link.md"
    root = _marketplace(tmp_path / "two", [row])
    (root / "skills/mason/environment/link.md").symlink_to(root / "index.yaml")
    with pytest.raises(MarketplaceIndexError, match="is a symlink"):
        write_site_from_index(root / "index.yaml", tmp_path / "two" / "site", flags_path=on)
    assert not (tmp_path / "two" / "site").exists()
    # the defence past the folder walk: _steps_text itself resolves and refuses
    with pytest.raises(MarketplaceIndexError, match="resolves outside"):
        _steps_text(row, root)


@pytest.mark.parametrize(
    ("plant", "needle"),
    [
        (lambda folder: (folder / "notes.txt").write_text("x", encoding="utf-8"), "is not one of"),
        (lambda folder: (folder / ".DS_Store").write_text("x", encoding="utf-8"), "dot entry"),
        (
            lambda folder: (
                (folder / "scripts").mkdir(),
                (folder / "scripts" / "run.sh").write_text("x", encoding="utf-8"),
            ),
            "is not references/",
        ),
        (
            lambda folder: ((folder / "references").mkdir(), (folder / "references" / "tool.whl").write_bytes(b"x")),
            "text files only",
        ),
        (
            lambda folder: (
                (folder / "references").mkdir(),
                (folder / "references" / ".hidden").write_text("x", encoding="utf-8"),
            ),
            "dot entry",
        ),
        (
            lambda folder: (folder / "steps.md").write_text("x" * (MAX_SHIPPED_FILE_BYTES + 1), encoding="utf-8"),
            f"at most {MAX_SHIPPED_FILE_BYTES}",
        ),
        (
            lambda folder: (folder / "SKILL.md").unlink() or (folder / "SKILL.md").symlink_to(folder / "steps.md"),
            "is a symlink",
        ),
        # loop 3, row 43: a FIFO named steps.md passed the walk; read_text would block on it
        (lambda folder: (folder / "steps.md").unlink() or os.mkfifo(folder / "steps.md"), "is not a regular file"),
        (
            lambda folder: ((folder / "references").mkdir(), os.mkfifo(folder / "references" / "pipe.md")),
            "is not a regular file",
        ),
        # loop 3, row 44: the folder cap, five files each under the file cap
        (
            lambda folder: (
                (folder / "references").mkdir(),
                [
                    (folder / "references" / f"{n}.md").write_bytes(b"x" * (MAX_SHIPPED_FILE_BYTES - 1))
                    for n in range(5)
                ],
            ),
            f"the cap is {MAX_SHIPPED_FOLDER_BYTES}",
        ),
    ],
)
def test_a_skill_folder_ships_only_the_allowlisted_files(tmp_path: Path, plant, needle: str) -> None:
    """Loop 2, rows 23 and 38; loop 3, rows 43 and 44: the folder a teammate copies from git is the set the mount
    and the zip ship, regular files only, under both caps."""
    root = _marketplace(tmp_path)
    plant(root / "skills/mason/environment")
    with pytest.raises(MarketplaceIndexError, match=needle):
        load_listings(root / "index.yaml", root=root)


def test_a_skill_folder_may_hold_text_references(tmp_path: Path) -> None:
    root = _marketplace(tmp_path)
    references = root / "skills/mason/environment/references"
    (references / "deep").mkdir(parents=True)
    (references / "recreate.md").write_text("# ref\n", encoding="utf-8")
    (references / "deep" / "more.yaml").write_text("a: 1\n", encoding="utf-8")
    assert [row["id"] for row in load_listings(root / "index.yaml", root=root)] == ["mason/environment"]


@pytest.mark.parametrize(
    ("skill_md", "needle"),
    [
        ("# skill\n", "has no YAML frontmatter; its name must be 'mason-environment'"),
        ("---\nname: mason-environment\n", "has no YAML frontmatter; its name must be 'mason-environment'"),
        ("---\nname: [unclosed\n---\n", "(?s)frontmatter is not valid YAML .*must be 'mason-environment'"),
        ("\ufeff---\nname: mason-environment\n---\n", "starts with a byte-order mark.*must be 'mason-environment'"),
        ("---\nname: " + "[" * 5000 + "\n---\n", "frontmatter is not valid YAML"),
        ("---\nname: Mason-Environment\n---\n", "name 'Mason-Environment' must be"),
        ("---\ndescription: x\n---\n", "name None must be 'mason-environment'"),
        ("---\nname: environment\n---\n", "name 'environment' must be 'mason-environment', the plugin name"),
        ("---\nname: 'mason-environment '\n---\n", "name 'mason-environment ' must be"),
        ("---\n- a list\n---\n", "name None must be"),
    ],
)
def test_a_skill_md_name_that_is_not_the_plugin_name_is_refused(tmp_path: Path, skill_md: str, needle: str) -> None:
    """Story 109.7 (DW-steward-109-6-1): Claude Code lists a plugin's skill as ``<plugin>:<name>`` and the card prints
    ``<plugin>:<plugin>``, so the frontmatter ``name`` is the plugin name, compared raw."""
    root = _marketplace(tmp_path)
    (root / "skills/mason/environment/SKILL.md").write_text(skill_md, encoding="utf-8")
    with pytest.raises(MarketplaceIndexError, match=needle):
        load_listings(root / "index.yaml", root=root)


def test_the_committed_skill_md_names_are_the_plugin_names() -> None:
    """Story 109.7: the three pilots pass the name rule over the committed tree."""
    root = repo_root() / _MARKETPLACE
    rows = load_listings(root / "index.yaml", root=root)
    assert sorted(f"{row['scope']}-{row['slug']}" for row in rows) == [
        "mason-environment",
        "mason-package",
        "warden-scan",
    ]


def test_a_skill_md_that_is_not_utf8_is_refused_by_name(tmp_path: Path) -> None:
    """Story 109.7: an unreadable SKILL.md is a named refusal that says what the name must be, never a raw error."""
    root = _marketplace(tmp_path)
    (root / "skills/mason/environment/SKILL.md").write_bytes(b"---\nname: \xff\n---\n")
    with pytest.raises(MarketplaceIndexError, match="(?s)not a readable UTF-8 text file .*must be 'mason-environment'"):
        load_listings(root / "index.yaml", root=root)


def test_a_deeply_nested_index_is_refused_by_name(tmp_path: Path) -> None:
    """Story 109.7: ``_load_yaml`` names a document nested past the recursion limit, never a raw ``RecursionError``."""
    index = tmp_path / "index.yaml"
    index.write_text("listings: " + "[" * 5000 + "\n", encoding="utf-8")
    with pytest.raises(MarketplaceIndexError, match="not valid YAML"):
        load_listings(index)


def test_a_declared_docs_steps_that_is_missing_is_refused(tmp_path: Path) -> None:
    row = _listing()
    root = _marketplace(tmp_path, [row])
    (root / "skills/mason/environment/steps.md").unlink()
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="is not a file"):
        write_site_from_index(root / "index.yaml", tmp_path / "site", flags_path=on)


# --- Story 109.8 ------------------------------------------------------------------------------------------------------


def test_a_related_reference_to_its_own_listing_is_refused() -> None:
    """DW-steward-109-3-1: ``@mason/environment`` on ``mason/environment`` passed and the card linked itself."""
    skill = _skill()
    skill["related"] = ["@mason/environment"]
    with pytest.raises(MarketplaceIndexError, match="related @mason/environment names this listing itself"):
        listings_from_document({"schema": SCHEMA_ID, "listings": [skill]})


def _scan_shape(root: Path, shape: str) -> str:
    """Plant one between-folder shape beside the committed-like skill folder; return the refusal's needle."""
    skills = root / "skills"
    if shape == "empty-scope":
        (skills / "empty").mkdir()
        return "skills/empty is an empty scope directory"
    if shape == "bad-scope-name":
        (skills / "Bad Scope" / "x").mkdir(parents=True)
        return "skills/Bad Scope is not a scope name"
    if shape == "empty-bad-scope-name":
        (skills / "Bad Scope").mkdir()
        return "skills/Bad Scope is not a scope name"
    if shape == "dot-git":
        (skills / ".git").mkdir()
        return "skills/.git is not a scope name"
    assert shape == "bad-slug-name"
    (skills / "mason" / "Env").mkdir()
    return "skills/mason/Env is not a slug name"


@pytest.mark.parametrize("shape", ["empty-scope", "bad-scope-name", "empty-bad-scope-name", "dot-git", "bad-slug-name"])
def test_every_directory_between_the_skill_folders_is_somebodys(tmp_path: Path, shape: str) -> None:
    """DW-steward-109-3-2: an empty, a non-slug or a dot directory between the folders passed the scan, the render
    and the manifests; README's "directories only" was met by a directory that was nobody's."""
    root = _marketplace(tmp_path)
    needle = _scan_shape(root, shape)
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match=needle):
        listings_from_skill_folders(root)
    with pytest.raises(MarketplaceIndexError, match=needle):
        write_site_from_index(root / "index.yaml", tmp_path / "site", flags_path=on)
    assert not (tmp_path / "site").exists()


def test_skills_as_a_regular_file_is_refused(tmp_path: Path) -> None:
    """DW-steward-109-3-2: ``skills`` as a file beside a modules-only index yielded no folders and rendered."""
    root = _marketplace(tmp_path, [_module("bmad")])
    (root / "skills").write_text("x", encoding="utf-8")
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="skills is not a directory"):
        listings_from_skill_folders(root)
    with pytest.raises(MarketplaceIndexError, match="skills is not a directory"):
        write_site_from_index(root / "index.yaml", tmp_path / "site", flags_path=on)
    assert not (tmp_path / "site").exists()


def test_a_symlinked_index_is_refused_even_when_its_target_is_a_regular_file_in_the_tree(tmp_path: Path) -> None:
    """DW-steward-109-3-8, kept by the operator's ruling of 2026-10-30, and DW-steward-109-3-7: the ``is_symlink()``
    half of ``_load_yaml``'s guard survived mutation, because every symlinked index a test used pointed at a
    non-file. A link whose target is the tree's own regular index is refused too."""
    root = _marketplace(tmp_path)
    (root / "real.yaml").write_bytes((root / "index.yaml").read_bytes())
    (root / "index.yaml").unlink()
    (root / "index.yaml").symlink_to(root / "real.yaml")
    with pytest.raises(MarketplaceIndexError, match="not a regular file"):
        load_listings(root / "index.yaml", root=root)


@pytest.mark.parametrize("shape", ["directory", "absent"])
def test_an_index_that_is_a_directory_or_absent_is_refused_by_every_writer(tmp_path: Path, shape: str) -> None:
    """DW-steward-109-3-7: the directory and absent index cases were tested through ``load_listings`` only."""
    root = _marketplace(tmp_path)
    (root / "index.yaml").unlink()
    if shape == "directory":
        (root / "index.yaml").mkdir()
    needle = "not a regular file" if shape == "directory" else "not a readable UTF-8 text file"
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match=needle):
        write_site_from_index(root / "index.yaml", tmp_path / "site", flags_path=on)
    with pytest.raises(MarketplaceIndexError, match=needle):
        write_plugin_manifests(root / "index.yaml", flags_path=on)
    assert not (tmp_path / "site").exists() and not (root / ".claude-plugin").exists()


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root reads a 0o000 directory")
def test_an_unreadable_scope_directory_is_a_listing_error(tmp_path: Path) -> None:
    """Review loop 1, row 8: an unreadable scope directory raised a raw ``PermissionError`` from the scan."""
    root = _marketplace(tmp_path)
    scope = root / "skills" / "mason"
    scope.chmod(0o000)
    try:
        with pytest.raises(MarketplaceIndexError, match="skills/mason cannot be read"):
            listings_from_skill_folders(root)
    finally:
        scope.chmod(0o755)
