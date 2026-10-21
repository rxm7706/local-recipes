"""Story 109.3 — marketplace pages from the index schema, estate.yaml compatible."""

from __future__ import annotations

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
    listing_from_estate_module,
    listings_from_skill_folders,
    load_listings,
    pages_enabled,
    validate_listing,
    write_site,
    write_site_from_index,
)

_CATALOG = Path("src/shared/packages/pyforge-steward/catalog")


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
        "contribution_lane": "instructions-only",
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


def test_a_skill_whose_path_does_not_match_scope_and_slug_is_refused(tmp_path: Path) -> None:
    row = _skill()
    row["path"] = "skills/other/environment"
    on = _flags_tree(tmp_path / "flags", dev="on")
    with pytest.raises(MarketplaceIndexError, match="path"):
        write_site([row], tmp_path / "site", flags_path=on)
    assert not (tmp_path / "site").exists()


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
        "skills/mason/environment.html",
    }
    card = (site / "skills/mason/environment.html").read_text(encoding="utf-8")
    assert "@mason/environment" not in card or "Lock one environment" in card
    assert "pyforge-mason" in card
    assert ".agents/skills" in card
    assert ".claude/skills" in card
    payload = json.loads((site / "listings.json").read_text(encoding="utf-8"))
    assert payload["schema"] == SCHEMA_ID
    assert payload["listings"][0]["id"] == "mason/environment"


def test_the_committed_index_renders_one_card_per_pilot_skill(tmp_path: Path) -> None:
    index = repo_root() / _CATALOG / "marketplace" / "index.yaml"
    rows = load_listings(index)
    assert [row["id"] for row in rows] == [
        "mason/environment",
        "mason/package",
        "warden/scan",
    ]
    on = _flags_tree(tmp_path / "flags", dev="on")
    site = tmp_path / "site"
    write_site_from_index(index, site, flags_path=on)
    committed = repo_root() / _CATALOG / "marketplace" / "site"
    for relative in (
        "index.html",
        "listings.json",
        "skills/mason/environment.html",
        "skills/mason/package.html",
        "skills/warden/scan.html",
    ):
        assert (site / relative).read_text(encoding="utf-8") == (committed / relative).read_text(encoding="utf-8")


def test_index_yaml_round_trips_through_the_schema() -> None:
    index = repo_root() / _CATALOG / "marketplace" / "index.yaml"
    document = yaml.safe_load(index.read_text(encoding="utf-8"))
    assert document["schema"] == SCHEMA_ID
    assert document["index_version"] == INDEX_VERSION
    assert document["compatible_with"] == "registry/estate.yaml"


def test_index_rows_match_each_folder_listing_yaml() -> None:
    root = repo_root() / _CATALOG / "marketplace"
    assert load_listings(root / "index.yaml") == listings_from_skill_folders(root)


def test_committed_pilots_are_community_and_code_backed() -> None:
    rows = load_listings(repo_root() / _CATALOG / "marketplace" / "index.yaml")
    for row in rows:
        assert row["tier"] == "community"
        assert row["trust_tier"] == "unverified"
        assert row["lane"] == "code-backed"
        assert row["docs"]["steps"] == "steps.md"
        assert any(item.get("published") is False for item in row["requires"])
        assert "example.com" not in yaml.safe_dump(row)


def test_a_tier_that_does_not_match_trust_tier_is_refused() -> None:
    row = _skill()
    row["tier"] = "estate-reviewed"
    row["trust_tier"] = "unverified"
    with pytest.raises(MarketplaceIndexError, match="maps to"):
        validate_listing(row)


def test_committed_environment_card_renders_steps_md_not_the_paper_sample(tmp_path: Path) -> None:
    index = repo_root() / _CATALOG / "marketplace" / "index.yaml"
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
