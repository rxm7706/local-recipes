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
    listing_from_estate_module,
    listings_from_document,
    listings_from_skill_folders,
    load_listings,
    pages_enabled,
    render_relative_marketplace,
    render_site,
    render_skill_card,
    render_url_marketplace,
    validate_listing,
    write_plugin_manifest,
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
        (
            {
                "id": "mason-x/environment",
                "scope": "mason-x",
                "slug": "environment",
                "path": "skills/mason-x/environment",
            },
            None,
        ),
    ],
)
def test_duplicate_ids_and_plugin_names_are_refused(second: dict, needle: str | None) -> None:
    other = _skill()
    other.update(second)
    rows = [_skill(), other]
    if needle is None:
        listings_from_document({"schema": SCHEMA_ID, "listings": rows})  # distinct id, card and plugin name
        return
    with pytest.raises(MarketplaceIndexError, match=needle):
        listings_from_document({"schema": SCHEMA_ID, "listings": rows})


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
    with pytest.raises(MarketplaceIndexError, match="is not in"):
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
    with pytest.raises(MarketplaceIndexError, match="resolves outside"):
        write_site_from_index(root / "index.yaml", tmp_path / "two" / "site", flags_path=on)
    assert not (tmp_path / "two" / "site").exists()


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
    assert "is not this runbook" in card
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
    assert "<h3>0. Install the published tools</h3>" in card
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
    assert "<h2>&lt;b&gt;x&lt;/b&gt;</h2>" in card


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
