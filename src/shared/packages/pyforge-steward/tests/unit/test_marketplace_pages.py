"""Story 109.3 — the site: the flag gate on writing, the cards, the index and the generated-site inventory.

The review of 2026-10-28 (the story spec's § Review) added the stale-card removal, the card order and freshness
line, and the positive assertions the two-state test had left as a tautology. Story 109.8 split the listing rules,
the build line and the manifests into their own modules (``DW-steward-109-3-7``).
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

import pytest
import yaml
from marketplace_testkit import _flags_tree, _marketplace, _module, _skill, _tree
from pyforge.core.flags import read_boolean

from pyforge.steward.bootstrap import repo_root
from pyforge.steward.marketplace_pages import (
    FLAG_KEY,
    INDEX_VERSION,
    REPOSITORY_BLOB_URL,
    SCHEMA_ID,
    MarketplaceIndexError,
    MarketplacePagesDisabled,
    _package_entries,
    listing_from_estate_module,
    listings_from_skill_folders,
    load_listings,
    pages_enabled,
    render_site,
    render_skill_card,
    write_site,
    write_site_from_index,
)

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads docs/foundry/marketplace and the estate skill
# copies, so it runs in the station's live-tree half and fires on those paths, not on every edit of the package.
pytestmark = pytest.mark.live_tree

_MARKETPLACE = Path("docs/foundry/marketplace")


@pytest.fixture(autouse=True)
def _dev_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """The flag tree is read for ``dev`` (where the flag is on), whatever the shell exports."""
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")


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


def test_a_skill_with_no_sources_names_the_versioned_release() -> None:
    """Story 109.7: the fallback names the listing's own versioned release too."""
    row = _skill()
    row.pop("sources", None)
    card = render_skill_card(row)
    assert (
        "<p>Versioned sources: a versioned GitHub release of this listing or Artifactory, once the listing is published.</p>"
        in card
    )
    assert "<h2>Sources</h2>" not in card


def test_an_empty_sources_mapping_names_the_versioned_release() -> None:
    """Story 109.7: the second fallback, a ``sources`` mapping with neither entry, says the same."""
    row = _skill()
    row["sources"] = {}
    card = render_skill_card(row)
    assert (
        "<p>Versioned sources: a versioned GitHub release of this listing or Artifactory, once the listing is published.</p>"
        in card
    )
    assert "<h2>Sources</h2>" not in card


def test_the_readme_calls_pages_site_a_pre_release_as_the_cards_do() -> None:
    """Story 109.7: the README, the card's Install section and its Sources block use one word for ``pages-site``."""
    readme = (repo_root() / _MARKETPLACE / "README.md").read_text(encoding="utf-8")
    assert "The rolling `pages-site` pre-release carries one `<scope>-<slug>.zip` per skill," in readme
    assert "The rolling `pages-site` release carries" not in readme
    assert "- A versioned GitHub release of the listing and Artifactory conda and pip are" in readme


def test_a_published_versioned_release_reads_published() -> None:
    """Story 109.7: the pre-release pointer is for an unpublished versioned release only."""
    row = _skill()
    row["sources"] = {"github": {"kind": "release", "published": True}}
    card = render_skill_card(row)
    assert "<p>Versioned sources, published: a versioned GitHub release of this listing.</p>" in card
    assert "is not a versioned release" not in card


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
    # Story 109.7: the sources name a versioned release and say what the rolling pre-release is: one answer; Story
    # 109.8: as one paragraph under Install, not a second unpublished list under its own heading
    assert (
        "<p>Versioned sources, not published: a versioned GitHub release of this listing, Artifactory conda, "
        "Artifactory pip. The rolling <code>pages-site</code> pre-release above moves with every deploy and is not a "
        "versioned release of this listing.</p>" in card
    )
    assert "<li>GitHub release: not published</li>" not in card and "<h2>Sources</h2>" not in card
    assert "rolling <code>pages-site</code> pre-release carries <code>mason-environment.zip</code>" in card
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
    # the lane is named, not defined, on the card (row 55), in the header meta line (Story 109.8)
    assert '<p class="meta">skill · @mason/environment · version 0.1.0 · lane code-backed</p>' in card
    assert (
        "<h2>Contribute</h2><p>A pull request is the publish path; the lanes are defined in the marketplace "
        f'<a href="{REPOSITORY_BLOB_URL}/docs/foundry/marketplace/README.md">README</a>.' in card
    )
    assert "Lane: " not in card
    assert "An instructions-only skill has none" not in card
    assert "· jobs find, install, create</p>" in card and "<p>Jobs:" not in card
    assert "sha256sum -c mason-environment.zip.sha256 &amp;&amp; unzip mason-environment.zip -d .claude/skills/" in card
    assert "-d .agents/skills/" in card
    # the two spec-named items come before the runbook, and the unpublished list names both packages
    assert card.index("<h2>Install</h2>") < card.index("<h2>Unpublished packages</h2>") < card.index("<h2>Steps</h2>")
    # the sources follow the rolling pre-release under Install (Story 109.8); Related precedes Contribute
    assert (
        card.index("pre-release carries")
        < card.index("Versioned sources, not published")
        < card.index("<h2>Unpublished packages</h2>")
    )
    assert card.index("<h2>Steps</h2>") < card.index("<h2>Related</h2>") < card.index("<h2>Contribute</h2>")
    assert "<li>pyforge-mason: PyPI, conda-forge, and SelfExplainML returned 404 on 2026-10-21</li>" in card
    assert "<li>pyforge-core: Required by pyforge mason dispatch; same 404 check</li>" in card
    assert "never verified" in card
    assert "mason-environment.zip" in card and "mason-environment.zip.sha256" in card
    # Story 109.6: the Install section carries Round 0's Claude Code result; Codex's manifest stays a pointer
    assert "found it does not read <code>.agents/skills/</code>" in card
    assert "<code>/plugin marketplace add &lt;checkout&gt;/docs/foundry/marketplace</code>" in card
    assert "<code>/plugin install mason-environment@pyforge-bmad-marketplace</code>" in card
    assert "lists it as <code>mason-environment:mason-environment</code>" in card
    assert "Use the plugin or the folder copy in one project, not both; with both" in card
    # loop 1, row 1: Round 0 ran the plugin install on @warden/scan only, and the card says so
    assert "Round 0</a>, 2026-10-29, run on <code>@warden/scan</code>" in card
    # loop 2, row 1: the commands ran as the claude plugin CLI, not as the slash commands the card prints
    assert "with the <code>claude plugin</code> CLI at local scope, not in an interactive session" in card
    assert "<code>.agents/plugins/marketplace.json</code> stays a discovery pointer until its Round 0 row runs" in card
    assert "as uncertain" not in card and "confirms a plugin install" not in card
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
