"""Story 109.3 — marketplace pages from the index schema, estate.yaml compatible.

The review of 2026-10-28 (the story spec's § Review) added the negative tests: one per listing rule, the traversal
and install-target refusals, the stale-card removal, the card order and freshness line, and the positive assertions
the two-state test had left as a tautology.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import threading
from pathlib import Path

import pytest
import yaml
from pyforge.core.flags import read_boolean

from pyforge.steward.bootstrap import repo_root
from pyforge.steward.marketplace_pages import (
    FLAG_KEY,
    INDEX_VERSION,
    MAX_SHIPPED_FOLDER_BYTES,
    REPOSITORY_BLOB_URL,
    SCHEMA_ID,
    MarketplaceIndexError,
    MarketplacePagesDisabled,
    _package_entries,
    _steps_text,
    listing_from_estate_module,
    listings_from_document,
    listings_from_skill_folders,
    load_listings,
    pages_enabled,
    render_codex_marketplace,
    render_relative_marketplace,
    render_site,
    render_skill_card,
    render_url_marketplace,
    validate_listing,
    write_codex_manifest,
    write_plugin_manifest,
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


def _flags_tree(tmp_path: Path, *, dev: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    flags = {
        "flags": {
            FLAG_KEY: {
                "state": "ENABLED",
                "variants": {"on": True, "off": False},
                "defaultVariant": "off",
                "metadata": {
                    "owner": "steward",
                    "story": "109-3-a-marketplace-tree-renders-a-pages-index-from-listings",
                    "created": "2026-10-21",
                    "on_everywhere": "",
                    "cleanup_by": "",
                },
            }
        }
    }
    overlays = {
        "dev": {FLAG_KEY: dev},
        "staging": {FLAG_KEY: "off"},
        "production": {FLAG_KEY: "off"},
    }
    tree = tmp_path / "flags.json"
    tree.write_text(json.dumps(flags), encoding="utf-8")
    (tmp_path / "flag-overlays.json").write_text(json.dumps(overlays), encoding="utf-8")
    return tree


def _skill() -> dict:
    return {
        "id": "mason/environment",
        "kind": "skill",
        "scope": "mason",
        "slug": "environment",
        "name": "@mason/environment",
        "title": "Lock one environment",
        "description": "Resolve manifests into one lockfile.",
        "version": "0.1.0",
        "trust_tier": "unverified",
        "source": "estate-listings",
        "jobs": ["find", "install"],
        "path": "skills/mason/environment",
        "contribution_lane": "code-backed",
        "requires": {
            "packages": [
                {
                    "name": "pyforge-mason",
                    "published": False,
                    "note": "not on PyPI or conda-forge",
                }
            ]
        },
    }


def _marketplace(tmp_path: Path, rows: list[dict] | None = None, *, steps: str = "# Steps\n\nRun `x`.\n") -> Path:
    """A marketplace directory with ``index.yaml`` and one folder per skill row."""
    root = tmp_path / "marketplace"
    rows = [_skill()] if rows is None else rows
    for row in rows:
        if row.get("kind") == "skill":
            folder = root / row["path"]
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "SKILL.md").write_text("# skill\n", encoding="utf-8")
            (folder / "steps.md").write_text(steps, encoding="utf-8")
            (folder / "listing.yaml").write_text(yaml.safe_dump(row, sort_keys=False), encoding="utf-8")
    root.mkdir(parents=True, exist_ok=True)
    document = {"schema": SCHEMA_ID, "index_version": INDEX_VERSION, "listings": rows}
    (root / "index.yaml").write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return root


def _listing() -> dict:
    """``_skill()`` as the committed listings are shaped: the list form of ``requires`` and ``docs.steps``."""
    row = _skill()
    row["requires"] = [{"kind": "package", "name": "pyforge-mason", "published": False, "note": "404 on 2026-10-21"}]
    row["docs"] = {"steps": "steps.md", "card": "skills/mason/environment.html"}
    return row


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
        ({"related": ["@warden/scan\n"]}, "must be @<scope>/<slug>"),
        ({"related": ["@"]}, "must be @<scope>/<slug>"),
    ],
)
def test_each_listing_rule_refuses_its_breach(edit: dict, needle: str) -> None:
    row = _skill()
    row.update(edit)
    with pytest.raises(MarketplaceIndexError, match=needle):
        validate_listing(row)


def test_install_targets_accept_the_two_roots_and_one_folder_under_each() -> None:
    row = _skill()
    row["install"] = {
        "targets": [".agents/skills", ".claude/skills", ".agents/skills/mason-environment", ".claude/skills/x-1"]
    }
    validate_listing(row)


def test_a_module_or_agent_card_is_written_under_its_own_directory(tmp_path: Path) -> None:
    module = listing_from_estate_module({"name": "bmad-builder", "trust_tier": "bmad-certified"})
    agent = {
        "id": "agent/reviewer",
        "kind": "agent",
        "slug": "reviewer",
        "name": "reviewer",
        "trust_tier": "unverified",
        "source": "estate-listings",
    }
    documents = render_site([module, agent])
    assert set(documents) == {
        "index.html",
        "listings.json",
        "marketplace.json",
        "modules/bmad-builder.html",
        "agents/reviewer.html",
    }
    assert 'href="../index.html"' in documents["agents/reviewer.html"]
    assert json.loads(documents["marketplace.json"])["plugins"] == []  # no skill, no plugin


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
    with pytest.raises(MarketplaceIndexError, match="must be @<scope>/<slug>"):
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


def _module(name: str, **extra: object) -> dict:
    row = {
        "id": f"module/{name}",
        "kind": "module",
        "name": name,
        "trust_tier": "unverified",
        "source": "estate-listings",
    }
    row.update(extra)
    return row


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
    (root / "skills" / "other").symlink_to(outside)
    with pytest.raises(MarketplaceIndexError, match="skills/other is a symlink"):
        listings_from_skill_folders(root)
    (root / "skills" / "other").unlink()
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
        (lambda folder: (folder / "steps.md").write_text("x" * (1_048_576 + 1), encoding="utf-8"), "at most 1048576"),
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
                [(folder / "references" / f"{n}.md").write_bytes(b"x" * (1_048_576 - 1)) for n in range(5)],
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


def test_a_declared_docs_steps_that_is_missing_is_refused(tmp_path: Path) -> None:
    row = _listing()
    root = _marketplace(tmp_path, [row])
    (root / "skills/mason/environment/steps.md").unlink()
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="is not a file"):
        write_site_from_index(root / "index.yaml", tmp_path / "site", flags_path=on)


# --- the two flag states (AC3) ----------------------------------------------------------------


def test_write_site_refuses_when_the_flag_is_off_and_writes_when_it_is_on(tmp_path: Path) -> None:
    off = _flags_tree(tmp_path / "off", dev="off")
    on = _flags_tree(tmp_path / "on", dev="on")
    site = tmp_path / "site"
    with pytest.raises(MarketplacePagesDisabled, match=FLAG_KEY):
        write_site([_skill()], site, flags_path=off)
    assert not site.exists()
    assert pages_enabled(flags_path=off) is False
    assert read_boolean(FLAG_KEY, True, flags_path=off) is False
    written = write_site([_skill()], site, flags_path=on)
    names = {path.relative_to(site).as_posix() for path in written}
    assert names == {
        "index.html",
        "listings.json",
        "marketplace.json",
        "skills/mason/environment.html",
    }
    card = (site / "skills/mason/environment.html").read_text(encoding="utf-8")
    assert "<h1>Lock one environment</h1>" in card
    assert "@mason/environment" in card
    assert "<h2>Unpublished packages</h2><ul><li>pyforge-mason: not on PyPI or conda-forge</li></ul>" in card
    assert ".agents/skills" in card
    assert ".claude/skills" in card
    assert "never verified" in card
    payload = json.loads((site / "listings.json").read_text(encoding="utf-8"))
    assert payload["schema"] == SCHEMA_ID
    assert payload["listings"][0]["id"] == "mason/environment"


def test_write_site_names_a_missing_flag_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The README snippet run from outside the repository (review 2026-10-28, row 18): the refusal names the
    missing tree, not an off flag."""
    monkeypatch.delenv("PYFORGE_FLAGS_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(MarketplacePagesDisabled, match="no flag tree found"):
        write_site([_skill()], tmp_path / "site", flags_path=tmp_path / "absent.json")
    assert not (tmp_path / "site").exists()


def test_the_production_overlay_turns_the_flag_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    on = _flags_tree(tmp_path / "flags", dev="on")
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    with pytest.raises(MarketplacePagesDisabled, match="is off"):
        write_site([_skill()], tmp_path / "site", flags_path=on)


def test_flag_env_prints_the_build_line_for_the_resolved_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``python -m pyforge.steward.marketplace_pages --flag-env`` is how the flag reaches the Pages build (review
    2026-10-28, row 6): dev on, production off, from the same tree."""
    from pyforge.steward.marketplace_pages import FLAG_ENV, main

    on = _flags_tree(tmp_path / "flags", dev="on")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    assert main(["--flag-env"]) == 0
    assert capsys.readouterr().out == f"{FLAG_ENV}=1\n"
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    assert main(["--flag-env"]) == 0
    assert capsys.readouterr().out == f"{FLAG_ENV}=0\n"
    with pytest.raises(SystemExit):
        main([])  # the one verb
    monkeypatch.delenv("PYFORGE_FLAGS_PATH")
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    monkeypatch.chdir(tmp_path)
    assert main(["--flag-env"]) == 2  # loop 2, row 37: no tree is an error, never a silent 0
    captured = capsys.readouterr()
    assert captured.out == "" and "no flag tree found" in captured.err


@pytest.mark.parametrize(
    ("text", "needle"),
    [
        ("{not json", "is not a readable JSON flag tree"),
        ('{"flags": {}}', "declares no such flag"),
        ('{"flags": {"pyforge.other": {}}}', "declares no such flag"),
        ('{"flags": []}', "declares no such flag"),
        ("[]", "declares no such flag"),
        # loop 4, row 63: a declared entry read_boolean would default on is refused too
        ('{"flags": {"%s": "yes"}}' % FLAG_KEY, "a shape the reader would default on"),
        ('{"flags": {"%s": null}}' % FLAG_KEY, "a shape the reader would default on"),
        (
            '{"flags": {"%s": {"defaultVariant": "off", "metadata": {}}}}' % FLAG_KEY,
            "a shape the reader would default on",
        ),
        (
            '{"flags": {"%s": {"variants": {"on": true}, "defaultVariant": "off", "metadata": {}}}}' % FLAG_KEY,
            "a shape the reader would default on",
        ),
        (
            '{"flags": {"%s": {"variants": {"on": "yes", "off": false}, "defaultVariant": "on", "metadata": {}}}}'
            % FLAG_KEY,
            "a shape the reader would default on",
        ),
        (
            '{"flags": {"%s": {"variants": {"on": true, "off": false}, "defaultVariant": "off"}}}' % FLAG_KEY,
            "a shape the reader would default on",
        ),
        # loop 5, row 87: the overlay selects the variant the build reads, so every variant must be a bool
        (
            '{"flags": {"%s": {"variants": {"off": false, "on": "yes"}, "defaultVariant": "off", "metadata": {}}}}'
            % FLAG_KEY,
            "a shape the reader would default on",
        ),
        (
            '{"flags": {"%s": {"variants": {}, "defaultVariant": "off", "metadata": {}}}}' % FLAG_KEY,
            "a shape the reader would default on",
        ),
    ],
)
def test_flag_env_refuses_a_tree_that_does_not_declare_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], text: str, needle: str
) -> None:
    """Loop 3, row 53: a tree that resolves but is malformed or lacks the key went through read_boolean's
    WARN-and-default and printed 0 with exit 0, the row-37 failure under another cause."""
    from pyforge.steward.marketplace_pages import main

    tree = tmp_path / "flags.json"
    tree.write_text(text, encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and needle in captured.err


def test_flag_env_refuses_a_non_bool_variant_the_overlay_selects_and_a_missing_overlay_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Loop 5, row 87: with ``on: "yes"`` under a bool default and the dev overlay naming ``on``, the reader WARNed
    and the step printed ``=0`` with exit 0; so did a tree with no ``flag-overlays.json`` beside it, though dev's
    ``on`` lives only in the overlay. The real tree prints ``=1``."""
    from pyforge.steward.marketplace_pages import FLAG_ENV, main

    on = _flags_tree(tmp_path / "flags", dev="on")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    assert main(["--flag-env"]) == 0 and capsys.readouterr().out == f"{FLAG_ENV}=1\n"
    tree = json.loads(on.read_text(encoding="utf-8"))
    tree["flags"][FLAG_KEY]["variants"] = {"off": False, "on": "yes"}
    on.write_text(json.dumps(tree), encoding="utf-8")
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "a shape the reader would default on" in captured.err
    _flags_tree(tmp_path / "flags", dev="on")
    (tmp_path / "flags" / "flag-overlays.json").unlink()
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "no flag-overlays.json beside" in captured.err
    real = repo_root() / "src" / "platform" / "config" / "flags.json"
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(real))
    assert main(["--flag-env"]) == 0 and capsys.readouterr().out == f"{FLAG_ENV}=1\n"


def test_flag_env_refuses_an_overlay_the_reader_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Loop 4, row 63: an overlay document the reader raises on is exit 2 with its message, never a traceback."""
    from pyforge.steward.marketplace_pages import main

    on = _flags_tree(tmp_path / "flags", dev="on")
    (tmp_path / "flags" / "flag-overlays.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "refusing to print a build line" in captured.err
    # the reader's own metadata check (it runs when an overlay is composed): exit 2 with its message, no traceback
    tree = json.loads(on.read_text(encoding="utf-8"))
    tree["flags"][FLAG_KEY]["metadata"] = {}
    on.write_text(json.dumps(tree), encoding="utf-8")
    (tmp_path / "flags" / "flag-overlays.json").write_text(
        json.dumps({"dev": {FLAG_KEY: "on"}, "staging": {}, "production": {}}), encoding="utf-8"
    )
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "metadata" in captured.err and "refusing to print a build line" in captured.err


@pytest.mark.parametrize("overlays", [{}, {"dev": {}}, {"dev": {"pyforge.other": "on"}, "staging": {}}])
def test_flag_env_refuses_an_overlay_file_with_no_value_for_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], overlays: dict
) -> None:
    """Loop 6, row 101: an overlay file that exists but names no value for the flag under the resolved environment
    read the base default and printed ``=0`` with exit 0, the silent-off row 87 refused for an absent file. A killed
    flag keeps its tree default, so it needs no overlay value."""
    from pyforge.steward.marketplace_pages import FLAG_ENV, main

    on = _flags_tree(tmp_path / "flags", dev="on")
    tree = json.loads(on.read_text(encoding="utf-8"))
    if "pyforge.other" in json.dumps(overlays):
        tree["flags"]["pyforge.other"] = dict(tree["flags"][FLAG_KEY])
        on.write_text(json.dumps(tree), encoding="utf-8")
    (tmp_path / "flags" / "flag-overlays.json").write_text(json.dumps(overlays), encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(on))
    assert main(["--flag-env"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and "names no value for the flag under dev" in captured.err
    tree["flags"][FLAG_KEY]["state"] = "DISABLED"
    on.write_text(json.dumps(tree), encoding="utf-8")
    assert main(["--flag-env"]) == 0 and capsys.readouterr().out == f"{FLAG_ENV}=0\n"


# --- the site tree (AC4) -------------------------------------------------------------------------


def _tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_the_committed_site_is_exactly_the_render_of_the_committed_index(tmp_path: Path) -> None:
    index = repo_root() / _MARKETPLACE / "index.yaml"
    rows = load_listings(index)
    assert [row["id"] for row in rows] == [
        "mason/environment",
        "mason/package",
        "warden/scan",
    ]
    on = _flags_tree(tmp_path / "flags", dev="on")
    site = tmp_path / "site"
    write_site_from_index(index, site, flags_path=on)
    committed = repo_root() / _MARKETPLACE / "site"
    assert _tree(site) == _tree(committed)  # every file, in both directions: a stale card fails here


def test_a_card_whose_listing_was_dropped_or_renamed_does_not_survive_a_render(tmp_path: Path) -> None:
    on = _flags_tree(tmp_path / "flags", dev="on")
    site = tmp_path / "site"
    other = _skill()
    other.update({"id": "mason/old", "slug": "old", "path": "skills/mason/old"})
    write_site([_skill(), other], site, flags_path=on)
    assert (site / "skills/mason/old.html").is_file()
    write_site([_skill()], site, flags_path=on)  # the previous listings.json accounts for old.html: replaced
    assert sorted(_tree(site)) == ["index.html", "listings.json", "marketplace.json", "skills/mason/environment.html"]


def test_write_site_refuses_a_generated_site_that_holds_a_file_its_listings_do_not_account_for(tmp_path: Path) -> None:
    """Loop 3, row 45: the marker is not ownership; a stray file beside a valid ``listings.json`` is refused and
    survives, not deleted."""
    on = _flags_tree(tmp_path / "flags", dev="on")
    site = tmp_path / "site"
    write_site([_skill()], site, flags_path=on)
    (site / "precious.txt").write_text("keep", encoding="utf-8")
    (site / "deep").mkdir()
    (site / "deep" / "more.txt").write_text("keep too", encoding="utf-8")
    with pytest.raises(
        MarketplaceIndexError, match=r"no render of its listings.json produces \(deep/, deep/more.txt, precious.txt\)"
    ):
        write_site([_skill()], site, flags_path=on)
    assert (site / "precious.txt").read_text(encoding="utf-8") == "keep"
    assert (site / "deep" / "more.txt").read_text(encoding="utf-8") == "keep too"
    assert (site / "skills/mason/environment.html").is_file()
    (site / "precious.txt").unlink()
    (site / "deep" / "more.txt").unlink()
    (site / "deep").rmdir()
    (site / "skills/mason/link.html").symlink_to(site / "index.html")  # a symlink is never one of ours
    with pytest.raises(MarketplaceIndexError, match="no render of its listings.json produces"):
        write_site([_skill()], site, flags_path=on)
    (site / "skills/mason/link.html").unlink()
    write_site([_skill()], site, flags_path=on)  # clean again: replaced
    # loop 4, row 62: an empty stray directory is foreign too, and survives
    (site / "precious").mkdir()
    with pytest.raises(MarketplaceIndexError, match=r"produces \(precious/\)"):
        write_site([_skill()], site, flags_path=on)
    assert (site / "precious").is_dir()


def test_a_generated_site_holding_a_module_card_is_replaced_by_the_next_render(tmp_path: Path) -> None:
    """Loop 5, row 91: the inventory reads a module row's card from its ``name`` (no ``slug``), so a site that holds
    a module card is a generated site to the next ``write_site``; every other write-twice case uses skill rows."""
    on = _flags_tree(tmp_path / "flags", dev="on")
    site = tmp_path / "site"
    rows = [_module("x"), _module("y", slug="why")]
    write_site(rows, site, flags_path=on)
    assert (site / "modules" / "x.html").is_file() and (site / "modules" / "why.html").is_file()
    write_site([_module("x")], site, flags_path=on)  # replaced, not refused as a foreign tree
    assert (site / "modules" / "x.html").is_file() and not (site / "modules" / "why.html").exists()


def test_the_inventory_holds_the_markers_rows_to_the_slug_grammar(tmp_path: Path) -> None:
    """Loop 4, row 62: a crafted ``listings.json`` whose row has ``scope: "x/y"`` accounted for any card-shaped file
    under a kind directory; a row with no scope yielded ``skills/None/...``. Both read as not a generated site."""
    on = _flags_tree(tmp_path / "flags", dev="on")
    for rows in (
        [{"kind": "skill", "scope": "x/y", "slug": "precious"}],
        [{"kind": "skill", "slug": "precious"}],
        [{"kind": "module", "name": "../precious"}],
        [{"kind": "agent", "slug": "Precious"}],
    ):
        target = tmp_path / "target"
        shutil.rmtree(target, ignore_errors=True)
        (target / "skills" / "x" / "y").mkdir(parents=True)
        (target / "skills" / "x" / "y" / "precious.html").write_text("keep", encoding="utf-8")
        (target / "listings.json").write_text(json.dumps({"schema": SCHEMA_ID, "listings": rows}), encoding="utf-8")
        with pytest.raises(MarketplaceIndexError, match="is not a generated site"):
            write_site([_skill()], target, flags_path=on)
        assert (target / "skills" / "x" / "y" / "precious.html").read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize(
    "marker",
    ['{"schema": "other", "listings": []}', "{not json", '{"schema": "pyforge.bmad-marketplace/v1"}', "[]"],
)
def test_write_site_refuses_a_marker_that_is_not_this_schema(tmp_path: Path, marker: str) -> None:
    """Loop 3, row 44: the marker's schema and JSON branches, each refused with the directory's files surviving."""
    on = _flags_tree(tmp_path / "flags", dev="on")
    target = tmp_path / "target"
    target.mkdir()
    (target / "precious.txt").write_text("keep", encoding="utf-8")
    (target / "listings.json").write_text(marker, encoding="utf-8")
    with pytest.raises(MarketplaceIndexError, match="is not a generated site"):
        write_site([_skill()], target, flags_path=on)
    assert (target / "precious.txt").read_text(encoding="utf-8") == "keep"
    assert (target / "listings.json").read_text(encoding="utf-8") == marker


def test_a_render_that_fails_leaves_the_existing_site_untouched(tmp_path: Path) -> None:
    on = _flags_tree(tmp_path / "flags", dev="on")
    site = tmp_path / "site"
    write_site([_skill()], site, flags_path=on)
    before = _tree(site)
    bad = _skill()
    bad["verified_at"] = dt.date(2026, 10, 21)
    with pytest.raises(MarketplaceIndexError, match="unquoted"):
        write_site([_skill(), bad], site, flags_path=on)
    assert _tree(site) == before


def test_write_site_refuses_a_directory_that_is_not_a_generated_site(tmp_path: Path) -> None:
    """Loop 2, row 22: the fresh-tree write never deletes a tree this module did not write."""
    on = _flags_tree(tmp_path / "flags", dev="on")
    target = tmp_path / "not-a-site"
    target.mkdir()
    (target / "precious.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(MarketplaceIndexError, match="is not a generated site"):
        write_site([_skill()], target, flags_path=on)
    assert (target / "precious.txt").read_text(encoding="utf-8") == "keep"
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(MarketplaceIndexError, match="is a symlink"):
        write_site([_skill()], link, flags_path=on)
    assert (target / "precious.txt").is_file()
    empty = tmp_path / "empty"
    empty.mkdir()
    write_site([_skill()], empty, flags_path=on)  # an empty directory is fine
    assert (empty / "listings.json").is_file()


def test_write_site_refuses_a_site_directory_that_holds_the_listings(tmp_path: Path) -> None:
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="would replace the listings"):
        write_site(load_listings(root / "index.yaml", root=root), root, flags_path=on, steps_root=root)
    assert (root / "index.yaml").is_file()


def test_index_yaml_round_trips_through_the_schema() -> None:
    index = repo_root() / _MARKETPLACE / "index.yaml"
    document = yaml.safe_load(index.read_text(encoding="utf-8"))
    assert document["schema"] == SCHEMA_ID
    assert document["index_version"] == INDEX_VERSION
    assert document["compatible_with"] == "registry/estate.yaml"


def test_index_rows_match_each_folder_listing_yaml() -> None:
    root = repo_root() / _MARKETPLACE
    assert load_listings(root / "index.yaml", root=root) == listings_from_skill_folders(root)


def test_committed_pilots_are_community_and_code_backed() -> None:
    rows = load_listings(repo_root() / _MARKETPLACE / "index.yaml")
    for row in rows:
        assert row["tier"] == "community"
        assert row["trust_tier"] == "unverified"
        assert row["lane"] == "code-backed"
        assert row["docs"]["steps"] == "steps.md"
        assert row["docs"]["card"] == f"skills/{row['scope']}/{row['slug']}.html"
        packages = _package_entries(row)
        assert packages, row["id"]  # code-backed: the lane rule above holds on the committed rows
        assert any(item["published"] is False for item in packages)
        assert row["verified_at"] is None
        assert "example.com" not in yaml.safe_dump(row)


def test_a_tier_that_does_not_match_trust_tier_is_refused() -> None:
    row = _skill()
    row["tier"] = "estate-reviewed"
    row["trust_tier"] = "unverified"
    with pytest.raises(MarketplaceIndexError, match="maps to"):
        validate_listing(row)


# --- the card (AC3, AC7; review rows 5 and 14) ------------------------------------------------------


def test_committed_environment_card_renders_steps_md_not_the_paper_sample(tmp_path: Path) -> None:
    index = repo_root() / _MARKETPLACE / "index.yaml"
    on = _flags_tree(tmp_path / "flags", dev="on")
    site = tmp_path / "site"
    write_site_from_index(index, site, flags_path=on)
    card = (site / "skills/mason/environment.html").read_text(encoding="utf-8")
    assert "conda-lock lock -f pyproject.toml --lockfile conda-lock.yml" in card
    assert "env.lock" not in card
    assert "paper card" not in card  # loop 2, row 26: reviewer provenance stays in the listing comments
    assert "GitHub release: not published" in card
    assert "Artifactory conda: not published" in card
    assert ".agents/skills/mason-environment" in card
    assert ".claude/skills/mason-environment" in card
    assert "bmp install" in card
    assert "Claude Code" in card
    assert "Devin" in card
    # the runbook is rendered, not dumped: no literal fence or heading marker, the callout is strong text
    assert "```" not in card and "\n## " not in card and "**Before you start.**" not in card
    assert "<strong>Before you start.</strong>" in card
    assert (
        '<pre><code class="language-bash">conda-lock lock -f pyproject.toml --lockfile conda-lock.yml\n</code></pre>'
        in card
    )
    # one <h2>Steps</h2>; the runbook's own title is skipped and its steps sit one level down (loop 3, row 55)
    assert card.count("<h2>Steps</h2>") == 1 and "Steps — @mason/environment" not in card
    assert "<h3>0. Install the published tools</h3>" in card and "<h4>" not in card
    assert card.index("<h2>Steps</h2>") < card.index("<h3>0. Install the published tools</h3>")
    # the lane is named, not defined, on the card (row 55)
    assert (
        "Lane: code-backed. A pull request is the publish path; the lanes are defined in the marketplace "
        f'<a href="{REPOSITORY_BLOB_URL}/docs/foundry/marketplace/README.md">README</a>.' in card
    )
    assert "An instructions-only skill has none" not in card
    assert "· jobs find, install, create</p>" in card and "<p>Jobs:" not in card
    assert "sha256sum -c mason-environment.zip.sha256 &amp;&amp; unzip mason-environment.zip -d .claude/skills/" in card
    assert "-d .agents/skills/" in card
    # the two spec-named items come before the runbook, and the unpublished list names both packages
    assert card.index("<h2>Install</h2>") < card.index("<h2>Unpublished packages</h2>") < card.index("<h2>Steps</h2>")
    # the sources sit after the runbook and its siblings, before Contribute (loop 5, row 94)
    assert card.index("<h2>Steps</h2>") < card.index("<h2>Related</h2>") < card.index("<h2>Sources</h2>")
    assert card.index("<h2>Sources</h2>") < card.index("<h2>Contribute</h2>")
    assert "<li>pyforge-mason: PyPI, conda-forge, and SelfExplainML returned 404 on 2026-10-21</li>" in card
    assert "<li>pyforge-core: Required by pyforge mason dispatch; same 404 check</li>" in card
    assert "never verified" in card
    assert "mason-environment.zip" in card and "mason-environment.zip.sha256" in card
    assert "discovery pointer" in card
    index_html = (site / "index.html").read_text(encoding="utf-8")
    assert index_html.count("never verified") == 3


def test_a_verified_listing_shows_its_date_on_the_card_and_the_index() -> None:
    row = _skill()
    row["verified_at"] = "2026-10-21"
    documents = render_site([row])
    assert "verified 2026-10-21" in documents["skills/mason/environment.html"]
    assert "verified 2026-10-21" in documents["index.html"]
    assert "never verified" not in documents["index.html"]


def test_a_card_escapes_what_a_listing_says() -> None:
    row = _skill()
    row["description"] = "<script>alert(1)</script> & co"
    card = render_skill_card(
        row, steps_text='# title\n\n## <b>x</b>\n\n<img src=x onerror=alert(1)>\n\n```a"onmouseover="alert(1)\nx\n```\n'
    )
    assert "<script>" not in card and "<img" not in card
    assert 'onmouseover="' not in card and "language-a&quot;onmouseover=&quot;alert(1)" in card  # loop 4, row 69
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; co" in card
    assert "<h3>&lt;b&gt;x&lt;/b&gt;</h3>" in card  # the runbook's headings sit one level under the card's Steps
    assert "<h2>title</h2>" not in card and "<h3>title</h3>" not in card


def test_a_module_with_a_runbook_renders_and_keeps_its_relative_links_literal(tmp_path: Path) -> None:
    """Loop 4, row 58: ``render_skill_card`` read ``row['slug']`` for every card, so a module with ``docs.steps``
    raised ``KeyError``; its relative links stay text because the mount ships no module folder."""
    root = tmp_path / "marketplace"
    (root / "modules" / "x").mkdir(parents=True)
    (root / "modules" / "x" / "steps.md").write_text(
        "# t\n\nSee [s](steps.md) and [d](https://e.test/d).\n", encoding="utf-8"
    )
    module = _module("x", path="modules/x", docs={"steps": "steps.md"})
    documents = render_site([module], steps_root=root)
    card = documents["modules/x.html"]
    assert "[s](steps.md)" in card and '<a href="https://e.test/d">d</a>' in card
    assert 'href="steps.md"' not in card and 'href="x/steps.md"' not in card


def test_a_card_links_the_documents_the_mount_does_not_carry_and_the_sibling_cards() -> None:
    """Loop 4, row 76: the README, Round 0 and the tool matrix are repository links; a related skill is its card."""
    row = _skill()
    row["related"] = ["@warden/scan", "a note"]
    card = render_skill_card(row)
    assert f'<a href="{REPOSITORY_BLOB_URL}/docs/foundry/marketplace/README.md">README</a>' in card
    assert f'<a href="{REPOSITORY_BLOB_URL}/docs/foundry/marketplace/MANUAL-CHECKLIST.md">Round 0</a>' in card
    assert f'<a href="{REPOSITORY_BLOB_URL}/_bmad-output/projects/pyforge-steward/planning-artifacts/' in card
    assert 'tool-support-matrix.md">tool matrix</a>' in card
    assert '<h2>Related</h2><ul><li><a href="../warden/scan.html">@warden/scan</a></li><li>a note</li></ul>' in card
    assert REPOSITORY_BLOB_URL == "https://github.com/rxm7706/local-recipes/blob/main"
    module = _module("x", related=["@mason/environment"])
    assert '<li><a href="../skills/mason/environment.html">@mason/environment</a></li>' in render_skill_card(module)


def test_a_cards_relative_runbook_link_points_into_the_mounted_folder() -> None:
    """Loop 3, row 47: the card is ``skills/<scope>/<slug>.html`` beside the folder, so ``[x](steps.md)`` on the
    runbook must resolve to ``skills/<scope>/<slug>/steps.md``."""
    card = render_skill_card(
        _skill(), steps_text="# t\n\nSee [steps](steps.md), [ref](references/x.md) and [docs](https://e.test/d).\n"
    )
    assert '<a href="environment/steps.md">steps</a>' in card
    assert '<a href="environment/references/x.md">ref</a>' in card
    assert '<a href="https://e.test/d">docs</a>' in card


# --- the manifests ------------------------------------------------------------------------------


def test_committed_marketplace_json_uses_documented_source_fields(tmp_path: Path) -> None:
    index = repo_root() / _MARKETPLACE / "index.yaml"
    rows = load_listings(index)
    relative = json.loads(render_relative_marketplace(rows))
    assert relative["name"] == "pyforge-bmad-marketplace"
    assert [plugin["source"] for plugin in relative["plugins"]] == [
        "./skills/mason/environment",
        "./skills/mason/package",
        "./skills/warden/scan",
    ]
    committed = repo_root() / _MARKETPLACE / ".claude-plugin" / "marketplace.json"
    assert committed.read_text(encoding="utf-8") == render_relative_marketplace(rows)
    url_form = json.loads(render_url_marketplace(rows))
    plugin = url_form["plugins"][0]
    assert plugin["source"]["source"] == "git-subdir"
    assert plugin["source"]["url"] == "https://github.com/rxm7706/local-recipes.git"
    assert plugin["source"]["path"] == "docs/foundry/marketplace/skills/mason/environment"
    assert "sparsePaths" not in plugin["source"]
    on = _flags_tree(tmp_path / "flags", dev="on")
    dest = tmp_path / "marketplace.json"
    write_plugin_manifest(index, dest, flags_path=on)
    assert dest.read_text(encoding="utf-8") == render_relative_marketplace(rows)
    off = _flags_tree(tmp_path / "off", dev="off")
    with pytest.raises(MarketplacePagesDisabled):
        write_plugin_manifest(index, tmp_path / "no.json", flags_path=off)
    with pytest.raises(MarketplacePagesDisabled):
        write_codex_manifest(index, tmp_path / "no.json", flags_path=off)


def test_committed_codex_manifest_names_the_three_listings(tmp_path: Path) -> None:
    """Loop 2, row 21: the directory ``codex plugin marketplace add`` names holds a manifest with the skills."""
    index = repo_root() / _MARKETPLACE / "index.yaml"
    rows = load_listings(index)
    committed = repo_root() / _MARKETPLACE / ".agents" / "plugins" / "marketplace.json"
    assert committed.read_text(encoding="utf-8") == render_codex_marketplace(rows)
    document = json.loads(committed.read_text(encoding="utf-8"))
    assert document["name"] == "pyforge-bmad-marketplace"
    assert [plugin["name"] for plugin in document["plugins"]] == ["mason-environment", "mason-package", "warden-scan"]
    assert [plugin["source"] for plugin in document["plugins"]] == [
        {"source": "local", "path": "./skills/mason/environment"},
        {"source": "local", "path": "./skills/mason/package"},
        {"source": "local", "path": "./skills/warden/scan"},
    ]
    on = _flags_tree(tmp_path / "flags", dev="on")
    root = _marketplace(tmp_path)
    written = write_plugin_manifests(root / "index.yaml", flags_path=on)
    assert [path.relative_to(root).as_posix() for path in written] == [
        ".claude-plugin/marketplace.json",
        ".agents/plugins/marketplace.json",
    ]
    # loop 3, row 44: the contents, not only the paths, are each renderer's bytes for the loaded rows
    loaded = load_listings(root / "index.yaml", root=root)
    assert written[0].read_text(encoding="utf-8") == render_relative_marketplace(loaded)
    assert written[1].read_text(encoding="utf-8") == render_codex_marketplace(loaded)
    assert json.loads(written[0].read_text(encoding="utf-8"))["plugins"][0]["source"] == "./skills/mason/environment"
    assert json.loads(written[1].read_text(encoding="utf-8"))["plugins"][0]["source"] == {
        "source": "local",
        "path": "./skills/mason/environment",
    }


@pytest.mark.parametrize("link", [".agents", ".agents/plugins", ".claude-plugin"])
def test_the_manifests_are_not_written_through_a_symlink(tmp_path: Path, link: str) -> None:
    """Loop 4, row 65: ``root/.agents -> /elsewhere`` took the Codex manifest outside the tree while the returned
    path was the in-tree one. The Claude manifest is written first, so it exists exactly when the link is not its
    own directory (loop 5, row 92)."""
    root = _marketplace(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / link).parent.mkdir(parents=True, exist_ok=True)
    (root / link).symlink_to(elsewhere)
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="is a symlink; refusing to write through it"):
        write_plugin_manifests(root / "index.yaml", flags_path=on)
    assert not list(elsewhere.rglob("*"))
    assert (root / ".claude-plugin" / "marketplace.json").is_file() == (link != ".claude-plugin")
    assert not (root / ".agents" / "plugins" / "marketplace.json").exists()
    # a destination outside the tree (a test's temp file) is the caller's and still written
    written = write_plugin_manifest(root / "index.yaml", tmp_path / "out" / "m.json", flags_path=on)
    assert written.is_file()


def test_the_manifests_are_not_written_through_a_symlink_when_the_root_is_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loop 5, row 85: a relative root (the README snippet's ``Path('docs/foundry/marketplace')``) with an absolute
    destination made ``relative_to`` raise and the containment return, so the manifest went through the link."""
    root = _marketplace(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (root / ".agents").symlink_to(elsewhere)
    on = _flags_tree(tmp_path / "flags", dev="on")
    monkeypatch.chdir(tmp_path)
    index = Path("marketplace") / "index.yaml"
    with pytest.raises(MarketplaceIndexError, match=".agents is a symlink; refusing to write through it"):
        write_codex_manifest(index, root / ".agents" / "plugins" / "marketplace.json", flags_path=on)
    with pytest.raises(MarketplaceIndexError, match=".agents is a symlink; refusing to write through it"):
        write_codex_manifest(root / "index.yaml", Path("marketplace") / ".agents" / "plugins" / "m.json", flags_path=on)
    assert not list(elsewhere.rglob("*"))


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
@pytest.mark.parametrize("parent_exists", [False, True])
def test_a_dot_dot_destination_is_read_lexically_for_both_manifests(
    tmp_path: Path, writer, parent_exists: bool
) -> None:
    """Loop 5, row 85: ``root/../out/m.json`` was inside the tree to ``relative_to`` and judged by its resolved parent
    only when that parent existed, so the same destination was written when ``out/`` was absent and refused when it
    was present. Normalised, it is outside the tree either way: the caller's, written where it names."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    if parent_exists:
        (tmp_path / "out").mkdir()
    written = writer(root / "index.yaml", root / ".." / "out" / "m.json", flags_path=on)
    assert written.resolve() == (tmp_path / "out" / "m.json") and written.is_file()
    assert not (root / "out").exists()
    # a .. that stays inside the tree is held to the symlink rule on the normalised path
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir(exist_ok=True)
    (root / ".claude-plugin").symlink_to(elsewhere)
    with pytest.raises(MarketplaceIndexError, match=".claude-plugin is a symlink; refusing to write through it"):
        writer(root / "index.yaml", root / "skills" / ".." / ".claude-plugin" / "marketplace.json", flags_path=on)
    assert not list(elsewhere.rglob("*"))


@pytest.mark.parametrize(
    ("writer", "name"),
    [
        (write_plugin_manifest, ".claude-plugin/marketplace.json"),
        (write_codex_manifest, ".agents/plugins/marketplace.json"),
    ],
)
def test_a_dot_dot_after_a_symlinked_directory_is_refused_for_both_manifests(tmp_path: Path, writer, name: str) -> None:
    """Loop 6, row 96: the loop-5 lexical reading collapsed ``linkdir/..`` before the symlink walk, while the OS
    follows ``linkdir`` first, so ``root/linkdir/../<manifest>`` was written under ``linkdir``'s target's parent;
    ``4e1ac45dbc`` refused it. A tree reached under another spelling (``link -> root``) is the tree: a destination
    spelled through either name is held to the symlink rule."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    (tmp_path / "elsewhere" / "sub").mkdir(parents=True)
    (root / "linkdir").symlink_to(tmp_path / "elsewhere" / "sub")
    with pytest.raises(MarketplaceIndexError, match="steps back out of a symlink with '..'"):
        writer(root / "index.yaml", root / "linkdir" / ".." / name, flags_path=on)
    assert not list((tmp_path / "elsewhere").rglob("*.json")) and not (root / name).exists()
    (root / "linkdir").unlink()
    first = name.split("/", 1)[0]
    (root / first).symlink_to(tmp_path / "elsewhere")
    (tmp_path / "link").symlink_to(root)
    for index, dest in (
        (tmp_path / "link" / "index.yaml", root / name),
        (root / "index.yaml", tmp_path / "link" / name),
    ):
        with pytest.raises(MarketplaceIndexError, match=f"{first} is a symlink; refusing to write through it"):
            writer(index, dest, flags_path=on)
    assert not list((tmp_path / "elsewhere").rglob("*.json"))


@pytest.mark.parametrize("writer", [write_plugin_manifest, write_codex_manifest])
def test_a_manifest_under_a_file_is_a_listing_error(tmp_path: Path, writer) -> None:
    """Loop 6, row 97: a destination whose parent is a regular file in the tree raised a raw ``FileExistsError``
    from ``mkdir``; every containment refusal is a ``MarketplaceIndexError``."""
    root = _marketplace(tmp_path)
    on = _flags_tree(tmp_path / "flags", dev="on")
    for dest in (root / "index.yaml" / "m.json", root / "index.yaml" / "deeper" / "m.json"):
        with pytest.raises(MarketplaceIndexError, match="index.yaml is not a directory; refusing to write under it"):
            writer(root / "index.yaml", dest, flags_path=on)
    assert (root / "index.yaml").is_file()


def test_the_manifests_refuse_a_folder_the_index_does_not_declare(tmp_path: Path) -> None:
    """Loop 2, row 30: ``write_plugin_manifest`` holds the tree to the same rule as ``write_site_from_index``."""
    root = _marketplace(tmp_path)
    extra = root / "skills/mason/extra"
    extra.mkdir()
    (extra / "SKILL.md").write_text("# x\n", encoding="utf-8")
    (extra / "listing.yaml").write_text("id: mason/extra\n", encoding="utf-8")
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="the index does not declare"):
        write_plugin_manifest(root / "index.yaml", tmp_path / "m.json", flags_path=on)
    with pytest.raises(MarketplaceIndexError, match="the index does not declare"):
        write_codex_manifest(root / "index.yaml", tmp_path / "c.json", flags_path=on)
    assert not (tmp_path / "m.json").exists() and not (tmp_path / "c.json").exists()
