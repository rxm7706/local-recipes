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

SCHEMA_ID = "pyforge.bmad-marketplace/v1"
FLAG_KEY = "pyforge.steward.marketplace_pages"
KINDS = frozenset({"skill", "module", "agent"})
TRUST_TIERS = frozenset({"unverified", "community-reviewed", "bmad-certified"})
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
    _require_str(row, "name", ident)
    _require_str(row, "source", ident)
    jobs = row.get("jobs") or []
    if not isinstance(jobs, list) or any(not isinstance(item, str) for item in jobs):
        raise MarketplaceIndexError(f"{ident}: jobs must be a list of strings")
    unknown = sorted(set(jobs) - JOBS)
    if unknown:
        raise MarketplaceIndexError(f"{ident}: unknown jobs {unknown}")
    lane = row.get("contribution_lane")
    if lane is not None and lane not in LANES:
        raise MarketplaceIndexError(f"{ident}: contribution_lane {lane!r} is not a known lane")
    if kind == "skill":
        scope = _require_str(row, "scope", ident)
        slug = _require_str(row, "slug", ident)
        path = _require_str(row, "path", ident)
        expected = f"skills/{scope}/{slug}"
        if path != expected:
            raise MarketplaceIndexError(f"{ident}: path {path!r} must be {expected!r}")


def listings_from_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Listings from an index document or from ``registry/estate.yaml``."""
    if not isinstance(document, dict):
        raise MarketplaceIndexError("the index must be a mapping")
    if "listings" in document:
        schema = document.get("schema")
        if schema != SCHEMA_ID:
            raise MarketplaceIndexError(f"schema must be {SCHEMA_ID}, got {schema!r}")
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


def _requires_notes(row: dict[str, Any]) -> list[str]:
    requires = row.get("requires") or {}
    packages = requires.get("packages") if isinstance(requires, dict) else None
    notes: list[str] = []
    if not isinstance(packages, list):
        return notes
    for package in packages:
        if not isinstance(package, dict):
            continue
        name = str(package.get("name") or "")
        if package.get("published") is False and name:
            detail = str(package.get("note") or "not on PyPI or conda-forge")
            notes.append(f"{name}: {detail}")
    return notes


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


def render_skill_card(row: dict[str, Any]) -> str:
    """One self-contained skill-card page."""
    validate_listing(row)
    title = str(row.get("title") or row["name"])
    bits = [
        '<p><a href="../../index.html">Marketplace</a></p>',
        f"<h1>{html.escape(title)}</h1>",
        f'<p class="meta">{html.escape(str(row["kind"]))} · '
        f"{html.escape(str(row['id']))} · trust {html.escape(str(row['trust_tier']))} · "
        f"source {html.escape(str(row['source']))}</p>",
    ]
    description = str(row.get("description") or "")
    if description:
        bits.append(f"<p>{html.escape(description)}</p>")
    jobs = row.get("jobs") or []
    if jobs:
        bits.append("<p>Jobs: " + ", ".join(html.escape(str(job)) for job in jobs) + "</p>")
    if row.get("kind") == "skill":
        targets = ", ".join(f"<code>{html.escape(target)}</code>" for target in INSTALL_TARGETS)
        bits.append(f"<p>Install the folder <code>{html.escape(str(row['path']))}</code> into {targets}.</p>")
    hint = row.get("install_hint")
    if hint:
        bits.append(f"<p>Install hint: {html.escape(str(hint))}</p>")
    notes = _requires_notes(row)
    if notes:
        items = "".join(f"<li>{html.escape(note)}</li>" for note in notes)
        bits.append(f"<h2>Unpublished packages</h2><ul>{items}</ul>")
    lane = row.get("contribution_lane")
    if lane:
        bits.append(f"<p>Contribution lane: {html.escape(str(lane))}.</p>")
    return _page(title, "\n".join(bits))


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
        parts.append(
            "<article>"
            f'<h2><a href="{href}">{title}</a></h2>'
            f'<p class="meta">{kind} · {trust}</p>'
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


def write_site(
    rows: list[dict[str, Any]],
    site_dir: Path,
    *,
    flags_path: Path | str | None = None,
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
    for row in rows:
        card = site_dir / _card_href(row)
        card.parent.mkdir(parents=True, exist_ok=True)
        card.write_text(render_skill_card(row), encoding="utf-8")
        written.append(card)
    return written


def write_site_from_index(
    index_path: Path,
    site_dir: Path,
    *,
    flags_path: Path | str | None = None,
) -> list[Path]:
    """Load ``index_path`` and write the site next to it."""
    return write_site(load_listings(index_path), site_dir, flags_path=flags_path)
