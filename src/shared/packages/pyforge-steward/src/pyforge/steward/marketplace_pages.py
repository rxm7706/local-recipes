"""Static Pages for the reset BMAD marketplace (Story 109.3, CAP-171).

Reads listing metadata in the index schema ``pyforge.bmad-marketplace/v1``
and writes a self-contained index plus one skill card per listing. A v1
``registry/estate.yaml`` document (``modules:``) is accepted as module
listings so the reviewed-listings file stays compatible.

This module does not change ``CatalogEngine.render`` or the committed
``.claude-plugin`` / ``.agents`` manifests. Regeneration is gated by
``pyforge.steward.marketplace_pages`` (dev on, staging and production off).
While the flag is off, ``write_site`` writes nothing.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import yaml
from pyforge.core.flags import read_boolean

from pyforge.steward.catalog import (
    MARKETPLACE_NAME,
    MARKETPLACE_ROOT_RELATIVE,
    PUBLIC_MARKETPLACE_GIT_URL,
)

SCHEMA_ID = "pyforge.bmad-marketplace/v1"
INDEX_VERSION = 1
FLAG_KEY = "pyforge.steward.marketplace_pages"
KINDS = frozenset({"skill", "module", "agent", "bundle"})
TRUST_TIERS = frozenset({"unverified", "community-reviewed", "bmad-certified"})
# bmp tier -> upstream trust_tier (prototypes/p2-index-schema.md).
TIER_TO_TRUST = {
    "bmad-certified": "bmad-certified",
    "estate-reviewed": "community-reviewed",
    "community": "unverified",
}
JOBS = frozenset({"find", "install", "create", "publish"})
LANES = frozenset({"instructions-only", "code-backed"})
INSTALL_TARGETS = (".agents/skills", ".claude/skills")


class MarketplaceIndexError(ValueError):
    """The index document or a listing row is not usable."""


class MarketplacePagesDisabled(RuntimeError):
    """``write_site`` was asked to run while the flag is off."""


def pages_enabled(*, flags_path: Path | str | None = None) -> bool:
    """Whether regeneration is allowed in the current environment."""
    return read_boolean(FLAG_KEY, False, flags_path=flags_path)


def listing_from_estate_module(row: dict[str, Any]) -> dict[str, Any]:
    """Map one ``registry/estate.yaml`` ``modules[]`` row onto an index listing.

    Field names match what ``EstateListingsSource`` already reads (``name``,
    ``description``, ``repository``, ``version``, ``trust_tier``, ``source``,
    ``install_hint``). ``kind`` is ``module``. No row is invented when
    ``modules`` is empty.
    """
    if not isinstance(row, dict):
        raise MarketplaceIndexError("an estate module row must be a mapping")
    name = row.get("name")
    if not isinstance(name, str) or not name.strip():
        raise MarketplaceIndexError("an estate module row needs a name")
    name = name.strip()
    trust = row.get("trust_tier") or "unverified"
    source = row.get("source") or "estate-listings"
    version = row.get("version")
    return {
        "id": f"module/{name}",
        "kind": "module",
        "scope": "module",
        "slug": name,
        "name": name,
        "title": str(row.get("display_name") or name),
        "description": str(row.get("description") or ""),
        "version": None if version is None else str(version),
        "trust_tier": str(trust),
        "source": str(source),
        "jobs": ["find", "install"],
        "path": None,
        "repository": row.get("repository"),
        "install_hint": row.get("install_hint"),
        "lane": "code-backed",
        "contribution_lane": "code-backed",
        "requires": {"packages": []},
    }


def _require_str(row: dict[str, Any], key: str, where: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MarketplaceIndexError(f"{where}: {key} must be a non-empty string")
    return value.strip()


def validate_listing(row: dict[str, Any]) -> None:
    """Raise ``MarketplaceIndexError`` when a listing breaks the index schema."""
    if not isinstance(row, dict):
        raise MarketplaceIndexError("a listing must be a mapping")
    ident = _require_str(row, "id", "listing")
    kind = _require_str(row, "kind", ident)
    if kind not in KINDS:
        raise MarketplaceIndexError(f"{ident}: kind {kind!r} is not one of {sorted(KINDS)}")
    trust = _require_str(row, "trust_tier", ident)
    if trust not in TRUST_TIERS:
        raise MarketplaceIndexError(f"{ident}: trust_tier {trust!r} is not a v1 tier name")
    tier = row.get("tier")
    if tier is not None:
        if tier not in TIER_TO_TRUST:
            raise MarketplaceIndexError(f"{ident}: tier {tier!r} is not a bmp tier")
        expected_trust = TIER_TO_TRUST[str(tier)]
        if trust != expected_trust:
            raise MarketplaceIndexError(f"{ident}: tier {tier} maps to trust_tier {expected_trust}, got {trust}")
    _require_str(row, "name", ident)
    _require_str(row, "source", ident)
    jobs = row.get("jobs") or []
    if not isinstance(jobs, list) or any(not isinstance(item, str) for item in jobs):
        raise MarketplaceIndexError(f"{ident}: jobs must be a list of strings")
    unknown = sorted(set(jobs) - JOBS)
    if unknown:
        raise MarketplaceIndexError(f"{ident}: unknown jobs {unknown}")
    lane = row.get("lane")
    contribution = row.get("contribution_lane")
    if lane is not None and contribution is not None and lane != contribution:
        raise MarketplaceIndexError(f"{ident}: lane and contribution_lane differ")
    chosen = lane if lane is not None else contribution
    if chosen is not None and chosen not in LANES:
        raise MarketplaceIndexError(f"{ident}: lane {chosen!r} is not a known lane")
    _validate_requires(row, ident)
    _validate_install_targets(row, ident)
    if kind == "skill":
        scope = _require_str(row, "scope", ident)
        slug = _require_str(row, "slug", ident)
        path = _require_str(row, "path", ident)
        expected = f"skills/{scope}/{slug}"
        if path != expected:
            raise MarketplaceIndexError(f"{ident}: path {path!r} must be {expected!r}")


def _validate_requires(row: dict[str, Any], ident: str) -> None:
    requires = row.get("requires")
    if requires is None:
        return
    if isinstance(requires, dict):
        packages = requires.get("packages", [])
        if not isinstance(packages, list):
            raise MarketplaceIndexError(f"{ident}: requires.packages must be a list")
        return
    if isinstance(requires, list):
        for item in requires:
            if not isinstance(item, dict) or not isinstance(item.get("kind"), str):
                raise MarketplaceIndexError(f"{ident}: each requires entry needs a kind")
        return
    raise MarketplaceIndexError(f"{ident}: requires must be a list of kinds or a packages mapping")


def _validate_install_targets(row: dict[str, Any], ident: str) -> None:
    install = row.get("install")
    if not isinstance(install, dict) or "targets" not in install:
        return
    targets = install.get("targets")
    if not isinstance(targets, list) or not targets:
        raise MarketplaceIndexError(f"{ident}: install.targets must be a non-empty list")
    for target in targets:
        if not isinstance(target, str) or not _allowed_install_target(target):
            raise MarketplaceIndexError(
                f"{ident}: install target {target!r} must sit under .agents/skills or .claude/skills"
            )


def _allowed_install_target(target: str) -> bool:
    return target in INSTALL_TARGETS or target.startswith(".agents/skills/") or target.startswith(".claude/skills/")


def listings_from_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Listings from an index document or from ``registry/estate.yaml``."""
    if not isinstance(document, dict):
        raise MarketplaceIndexError("the index must be a mapping")
    if "listings" in document:
        schema = document.get("schema")
        if schema != SCHEMA_ID:
            raise MarketplaceIndexError(f"schema must be {SCHEMA_ID}, got {schema!r}")
        version = document.get("index_version", INDEX_VERSION)
        if version != INDEX_VERSION:
            raise MarketplaceIndexError(f"index_version must be {INDEX_VERSION}, got {version!r}")
        rows = document.get("listings")
        if not isinstance(rows, list):
            raise MarketplaceIndexError("listings must be a list")
    elif "modules" in document:
        modules = document.get("modules")
        if modules is None:
            modules = []
        if not isinstance(modules, list):
            raise MarketplaceIndexError("modules must be a list")
        rows = [listing_from_estate_module(row) for row in modules]
    else:
        raise MarketplaceIndexError("document needs listings or modules")
    for row in rows:
        validate_listing(row)
    return sorted(rows, key=lambda row: str(row["id"]))


def load_listings(path: Path) -> list[dict[str, Any]]:
    """Load listings from ``path`` (index schema or estate registry)."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if document is None:
        document = {}
    return listings_from_document(document)


def _card_href(row: dict[str, Any]) -> str:
    scope = str(row.get("scope") or "module")
    slug = str(row.get("slug") or row["name"])
    return f"skills/{scope}/{slug}.html"


def _package_entries(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Package requires, whether the row uses P2's list or ``{packages: [...]}``."""
    requires = row.get("requires")
    if isinstance(requires, dict):
        packages = requires.get("packages") or []
        return [item for item in packages if isinstance(item, dict)]
    if isinstance(requires, list):
        return [item for item in requires if isinstance(item, dict) and item.get("kind", "package") == "package"]
    return []


def _requires_notes(row: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for package in _package_entries(row):
        name = str(package.get("name") or "")
        if package.get("published") is False and name:
            detail = str(package.get("note") or "not on PyPI or conda-forge")
            notes.append(f"{name}: {detail}")
    return notes


def _listing_lane(row: dict[str, Any]) -> str | None:
    lane = row.get("lane", row.get("contribution_lane"))
    return None if lane is None else str(lane)


def _install_targets(row: dict[str, Any]) -> tuple[str, ...]:
    install = row.get("install")
    if isinstance(install, dict) and isinstance(install.get("targets"), list) and install["targets"]:
        return tuple(str(item) for item in install["targets"])
    return INSTALL_TARGETS


def _steps_text(row: dict[str, Any], steps_root: Path | None) -> str | None:
    """Read ``docs.steps``. A bare filename is next to the skill folder (P2)."""
    if steps_root is None:
        return None
    docs = row.get("docs")
    if not isinstance(docs, dict):
        return None
    relative = docs.get("steps")
    if not isinstance(relative, str) or not relative.strip():
        return None
    relative = relative.strip()
    skill_path = row.get("path")
    if "/" not in relative and isinstance(skill_path, str):
        candidate = steps_root / skill_path / relative
    else:
        candidate = steps_root / relative
    if not candidate.is_file():
        return None
    return candidate.read_text(encoding="utf-8")


def _page(title: str, body: str) -> str:
    safe_title = html.escape(title)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{safe_title}</title>\n"
        "<style>\n"
        "body{font-family:Georgia,serif;margin:2rem auto;max-width:46rem;line-height:1.45;"
        "color:#1c1917;background:#fafaf9}\n"
        "a{color:#1d4ed8} code{font-family:ui-monospace,monospace;font-size:.95em}\n"
        "article{border-top:1px solid #d6d3d1;padding-top:1rem;margin-top:1rem}\n"
        ".meta{color:#44403c;font-size:.95rem}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )


def render_skill_card(row: dict[str, Any], *, steps_text: str | None = None) -> str:
    """One self-contained skill card.

    Sections follow the paper card (steps, install, sources, owners, requires,
    related, contribute). The steps are ``steps.md``. The paper prototype's
    sample commands are not rendered.
    """
    validate_listing(row)
    title = str(row.get("title") or row.get("display_name") or row["name"])
    tier = row.get("tier")
    trust = str(row["trust_tier"])
    tier_bit = f"tier {html.escape(str(tier))} · " if tier else ""
    bits = [
        '<p><a href="../../index.html">Marketplace</a></p>',
        f"<h1>{html.escape(title)}</h1>",
        f'<p class="meta">{html.escape(str(row["kind"]))} · '
        f"{html.escape(str(row['name']))} · version {html.escape(str(row.get('version') or 'unversioned'))}</p>",
        f'<p class="meta">{tier_bit}trust {html.escape(trust)} · source {html.escape(str(row["source"]))}</p>',
    ]
    if tier == "community":
        bits.append('<p class="meta">No review record. community maps to unverified until a CODEOWNER promotes it.</p>')
    description = str(row.get("description") or row.get("summary") or "")
    if description:
        bits.append(f"<p>{html.escape(description)}</p>")
    owners = row.get("owners") or []
    if isinstance(owners, list) and owners:
        bits.append("<p>Owners: " + ", ".join(html.escape(str(owner)) for owner in owners) + "</p>")
    if steps_text:
        bits.append("<h2>Steps</h2>")
        bits.append(
            "<p>Rendered from <code>steps.md</code>. "
            "The 2026-10-20 paper card's lock command is sample data and is not this runbook.</p>"
        )
        bits.append(f"<pre>{html.escape(steps_text)}</pre>")
    elif row.get("kind") == "skill":
        bits.append("<h2>Steps</h2><p>This card has no <code>steps.md</code> to render.</p>")
    jobs = row.get("jobs") or []
    if jobs:
        bits.append("<p>Jobs: " + ", ".join(html.escape(str(job)) for job in jobs) + "</p>")
    if row.get("kind") == "skill":
        targets = ", ".join(f"<code>{html.escape(target)}</code>" for target in _install_targets(row))
        bits.append("<h2>Install</h2>")
        bits.append(
            f"<p>Copy the folder <code>{html.escape(str(row['path']))}</code> into {targets}. "
            "Claude Code's documented project skill path is <code>.claude/skills/</code>. "
            "Devin's is <code>.agents/skills/</code>. "
            "The tool matrix marks Claude Code reading <code>.agents/skills/</code> as uncertain "
            "and does not list <code>.claude/skills/</code> for Devin. "
            "<code>bmp install</code> is not built; this page is not an install button.</p>"
        )
        bits.append(_sources_html(row))
    hint = row.get("install_hint")
    if hint:
        bits.append(f"<p>Install hint: {html.escape(str(hint))}</p>")
    notes = _requires_notes(row)
    if notes:
        items = "".join(f"<li>{html.escape(note)}</li>" for note in notes)
        bits.append(f"<h2>Unpublished packages</h2><ul>{items}</ul>")
    related = row.get("related") or []
    if isinstance(related, list) and related:
        items = "".join(f"<li>{html.escape(str(item))}</li>" for item in related)
        bits.append(f"<h2>Related</h2><ul>{items}</ul>")
    lane = _listing_lane(row)
    if lane:
        bits.append(f"<h2>Contribute</h2><p>Lane: {html.escape(lane)}. A pull request is the publish path.</p>")
        if lane == "code-backed":
            bits.append("<p>Code-backed: this listing requires a package. An instructions-only skill has none.</p>")
    return _page(title, "\n".join(bits))


def _sources_html(row: dict[str, Any]) -> str:
    """Name GitHub release and Artifactory conda/pip without inventing URLs."""
    sources = row.get("sources")
    if not isinstance(sources, dict):
        return "<p>Sources: a GitHub release or Artifactory, when this listing is published.</p>"
    lines: list[str] = []
    github = sources.get("github")
    if isinstance(github, dict):
        state = "published" if github.get("published") is True else "not published"
        lines.append(f"<li>GitHub release: {state}</li>")
    artifactory = sources.get("artifactory")
    if isinstance(artifactory, dict):
        for channel in ("conda", "pip"):
            entry = artifactory.get(channel)
            if isinstance(entry, dict):
                state = "published" if entry.get("published") is True else "not published"
                lines.append(f"<li>Artifactory {channel}: {state}</li>")
    if not lines:
        return "<p>Sources: a GitHub release or Artifactory, when this listing is published.</p>"
    return "<h2>Sources</h2><ul>" + "".join(lines) + "</ul>"


def render_index(rows: list[dict[str, Any]]) -> str:
    """The marketplace index page."""
    for row in rows:
        validate_listing(row)
    parts = [
        "<h1>BMAD marketplace</h1>",
        "<p>Skills, modules, and agents. Find, install, create, and publish. "
        "Listings are generated from the index. Nothing here is a live install button.</p>",
    ]
    if not rows:
        parts.append("<p>No listings yet.</p>")
    for row in rows:
        title = html.escape(str(row.get("title") or row["name"]))
        href = html.escape(_card_href(row))
        kind = html.escape(str(row["kind"]))
        trust = html.escape(str(row["trust_tier"]))
        lane = _listing_lane(row)
        lane_bit = f" · {html.escape(lane)}" if lane else ""
        parts.append(
            "<article>"
            f'<h2><a href="{href}">{title}</a></h2>'
            f'<p class="meta">{kind} · {trust}{lane_bit}</p>'
            f"<p>{html.escape(str(row.get('description') or ''))}</p>"
            "</article>"
        )
    return _page("BMAD marketplace", "\n".join(parts))


def render_listings_json(rows: list[dict[str, Any]]) -> str:
    """Machine-readable copy of the same listings the pages show."""
    for row in rows:
        validate_listing(row)
    payload = {"schema": SCHEMA_ID, "listings": rows}
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _skill_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skills = []
    for row in rows:
        validate_listing(row)
        if row.get("kind") == "skill" and row.get("scope") and row.get("slug"):
            skills.append(row)
    return skills


def _marketplace_document(rows: list[dict[str, Any]], source_for: Any) -> str:
    """Claude ``marketplace.json``. ``name`` matches the ``extraKnownMarketplaces`` key."""
    plugins = []
    for row in _skill_rows(rows):
        plugins.append(
            {
                "name": f"{row['scope']}-{row['slug']}",
                "description": str(row.get("description") or ""),
                "version": str(row.get("version") or ""),
                "source": source_for(row),
            }
        )
    document = {
        "name": MARKETPLACE_NAME,
        "owner": {"name": "rxm7706"},
        "metadata": {
            "description": ("BMAD skills, modules, and agents hosted in this monorepo at docs/foundry/marketplace/.")
        },
        "plugins": plugins,
    }
    return json.dumps(document, indent=2) + "\n"


def render_relative_marketplace(rows: list[dict[str, Any]]) -> str:
    """Marketplace file for a ``github`` or ``git`` marketplace source.

    Plugin entries are relative paths, which resolve from the marketplace
    root (the directory that contains ``.claude-plugin/``).
    """

    def source_for(row: dict[str, Any]) -> str:
        return f"./skills/{row['scope']}/{row['slug']}"

    return _marketplace_document(rows, source_for)


def render_url_marketplace(
    rows: list[dict[str, Any]],
    *,
    git_url: str = PUBLIC_MARKETPLACE_GIT_URL,
) -> str:
    """Marketplace file served over HTTP.

    A ``url`` marketplace source downloads only this file, so a relative
    plugin path cannot resolve. Each plugin uses ``git-subdir`` (a plugin
    source: ``url``, ``path``; ``ref`` omitted). ``git-subdir`` is not a
    marketplace source.
    """

    def source_for(row: dict[str, Any]) -> dict[str, str]:
        return {
            "source": "git-subdir",
            "url": git_url,
            "path": f"{MARKETPLACE_ROOT_RELATIVE}/skills/{row['scope']}/{row['slug']}",
        }

    return _marketplace_document(rows, source_for)


def listings_from_skill_folders(marketplace: Path) -> list[dict[str, Any]]:
    """Read each ``skills/<scope>/<slug>/listing.yaml`` and validate it.

    ``index.yaml`` is the committed concatenation of these files until
    ``bmp index build`` exists.
    """
    rows: list[dict[str, Any]] = []
    for path in sorted((marketplace / "skills").glob("*/*/listing.yaml")):
        row = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(row, dict):
            raise MarketplaceIndexError(f"{path}: listing must be a mapping")
        validate_listing(row)
        rows.append(row)
    return sorted(rows, key=lambda row: str(row["id"]))


def write_site(
    rows: list[dict[str, Any]],
    site_dir: Path,
    *,
    flags_path: Path | str | None = None,
    steps_root: Path | None = None,
) -> list[Path]:
    """Write ``index.html``, ``listings.json``, and one card per listing.

    Refuses, and writes nothing, while ``pyforge.steward.marketplace_pages``
    is off. ``flags_path`` is for tests; production reads the estate tree.
    """
    if not pages_enabled(flags_path=flags_path):
        raise MarketplacePagesDisabled(f"{FLAG_KEY} is off; the marketplace pages were not written")
    for row in rows:
        validate_listing(row)
    site_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index_path = site_dir / "index.html"
    index_path.write_text(render_index(rows), encoding="utf-8")
    written.append(index_path)
    data_path = site_dir / "listings.json"
    data_path.write_text(render_listings_json(rows), encoding="utf-8")
    written.append(data_path)
    manifest_path = site_dir / "marketplace.json"
    manifest_path.write_text(render_url_marketplace(rows), encoding="utf-8")
    written.append(manifest_path)
    for row in rows:
        card = site_dir / _card_href(row)
        card.parent.mkdir(parents=True, exist_ok=True)
        card.write_text(
            render_skill_card(row, steps_text=_steps_text(row, steps_root)),
            encoding="utf-8",
        )
        written.append(card)
    return written


def write_site_from_index(
    index_path: Path,
    site_dir: Path,
    *,
    flags_path: Path | str | None = None,
) -> list[Path]:
    """Load ``index_path`` and write the site next to it.

    ``site/marketplace.json`` is the Pages URL form. The git marketplace
    file (``.claude-plugin/marketplace.json``) is written by
    ``write_plugin_manifest`` so a render into a temporary site does not
    touch the index's directory.
    """
    return write_site(
        load_listings(index_path),
        site_dir,
        flags_path=flags_path,
        steps_root=index_path.parent,
    )


def write_plugin_manifest(
    index_path: Path,
    dest: Path,
    *,
    flags_path: Path | str | None = None,
) -> Path:
    """Write the relative-path ``marketplace.json`` a ``github`` or ``git`` source reads."""
    if not pages_enabled(flags_path=flags_path):
        raise MarketplacePagesDisabled(f"{FLAG_KEY} is off; the marketplace manifest was not written")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_relative_marketplace(load_listings(index_path)), encoding="utf-8")
    return dest
