"""Story 109.3 — marketplace pages from the index schema, estate.yaml compatible.

The review of 2026-10-28 (the story spec's § Review) added the negative tests: one per listing rule, the traversal
and install-target refusals, the stale-card removal, the card order and freshness line, and the positive assertions
the two-state test had left as a tautology.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
import yaml
from pyforge.core.flags import read_boolean

from pyforge.steward.bootstrap import repo_root
from pyforge.steward.marketplace_pages import (
    FLAG_KEY,
    INDEX_VERSION,
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


def test_an_estate_module_name_must_be_a_slug() -> None:
    with pytest.raises(MarketplaceIndexError, match="must match"):
        listing_from_estate_module({"name": "../Builder"})


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
        ({"scope": " mason", "id": " mason/environment", "path": "skills/ mason/environment"}, "scope"),
        ({"install": {"targets": [".agents/skills/./x"]}}, "install target"),
        ({"verified_at": "2026-99-99"}, "not a calendar date"),
        ({"ci": {"checked": dt.date(2026, 10, 21)}}, "is not JSON"),
        ({"contribution_lane": None}, "lane is required for a skill"),
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
    ],
)
def test_duplicate_ids_and_plugin_names_are_refused(second: dict, needle: str) -> None:
    other = _skill()
    other.update(second)
    with pytest.raises(MarketplaceIndexError, match=needle):
        listings_from_document({"schema": SCHEMA_ID, "listings": [_skill(), other]})


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
    ],
)
def test_a_skill_folder_ships_only_the_allowlisted_files(tmp_path: Path, plant, needle: str) -> None:
    """Loop 2, rows 23 and 38: the folder a teammate copies from git is the set the mount and the zip ship."""
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


def test_a_card_whose_listing_was_dropped_does_not_survive_a_render(tmp_path: Path) -> None:
    on = _flags_tree(tmp_path / "flags", dev="on")
    site = tmp_path / "site"
    write_site([_skill()], site, flags_path=on)
    stale = site / "skills/mason/old.html"
    stale.write_text("<p>stale</p>", encoding="utf-8")
    (site / "notes.txt").write_text("stale too", encoding="utf-8")
    write_site([_skill()], site, flags_path=on)
    assert sorted(_tree(site)) == ["index.html", "listings.json", "marketplace.json", "skills/mason/environment.html"]


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
    # one <h2>Steps</h2>; the runbook's own headings sit two levels down
    assert card.count("<h2>Steps</h2>") == 1 and "<h3>Steps — @mason/environment</h3>" in card
    assert "<h4>0. Install the published tools</h4>" in card
    assert card.index("<h2>Steps</h2>") < card.index("<h3>Steps — @mason/environment</h3>")
    assert "· jobs find, install, create</p>" in card and "<p>Jobs:" not in card
    assert "sha256sum -c mason-environment.zip.sha256 &amp;&amp; unzip mason-environment.zip -d .claude/skills/" in card
    assert "-d .agents/skills/" in card
    # the two spec-named items come before the runbook, and the unpublished list names both packages
    assert card.index("<h2>Install</h2>") < card.index("<h2>Unpublished packages</h2>") < card.index("<h2>Steps</h2>")
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
    card = render_skill_card(row, steps_text="# <b>x</b>\n\n<img src=x onerror=alert(1)>\n")
    assert "<script>" not in card and "<img" not in card
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; co" in card
    assert "<h3>&lt;b&gt;x&lt;/b&gt;</h3>" in card  # the runbook's headings sit two levels under the card's h1


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
