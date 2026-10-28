"""Static Pages for the reset BMAD marketplace (Story 109.3, CAP-171).

Reads listing metadata in the index schema ``pyforge.bmad-marketplace/v1``
and writes a self-contained index plus one skill card per listing. A v1
``registry/estate.yaml`` document (``modules:``) is accepted as module
listings so the reviewed-listings file stays compatible.

This module does not change ``CatalogEngine.render`` or the committed
``.claude-plugin`` / ``.agents`` manifests. Regeneration is gated by
``pyforge.steward.marketplace_pages`` (dev on, staging and production off).
While the flag is off, ``write_site`` writes nothing.

The review of 2026-10-28 (the story spec's § Review) hardened the listing
rules: a slug grammar on ``scope``, ``slug`` and a module's ``name``;
install targets and ``docs.steps`` that cannot leave the skill folder;
``published`` a bool and ``name`` non-empty on every package; the lane
against the packages; the folder and its ``SKILL.md`` present; every folder
declared; unique ids, cards and plugin names; a kind-to-directory map; a
quoted ``verified_at``; every document rendered before the site directory
is touched, and the site written into a fresh tree.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml
from pyforge.core import cutover_root
from pyforge.core.flags import read_boolean

from pyforge.steward.catalog import (
    CODEX_MANIFEST_RELATIVE,
    MARKETPLACE_NAME,
    MARKETPLACE_ROOT_RELATIVE,
    PUBLIC_MARKETPLACE_GIT_URL,
)
from pyforge.steward.pages import RELEASE_TAG

SCHEMA_ID = "pyforge.bmad-marketplace/v1"
INDEX_VERSION = 1
FLAG_KEY = "pyforge.steward.marketplace_pages"
#: The build-environment line ``--flag-env`` prints, the one way the flag reaches the Pages build
#: (``docs-site/src/lib/flags.ts`` reads it; the mount and ``pages-check`` follow it).
FLAG_ENV = "PYFORGE_MARKETPLACE_PAGES"
KINDS = frozenset({"skill", "module", "agent", "bundle"})
#: The directory under the site root that holds each kind's cards.
KIND_DIRS: dict[str, str] = {"skill": "skills", "module": "modules", "agent": "agents", "bundle": "bundles"}
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
#: ``scope``, ``slug``, a module's ``name`` and an install target's last part: lower-case, digits and hyphens.
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
#: ``verified_at``: a quoted ``YYYY-MM-DD`` string, or null.
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
#: The files a skill folder ships (the mount, the release zip and ``bmp install`` copy these and nothing else).
SKILL_FILES = ("SKILL.md", "steps.md", "listing.yaml")
#: The one subdirectory a skill folder ships, text files only.
REFERENCES_DIR = "references"
SHIPPED_TEXT_SUFFIXES = frozenset({".md", ".txt", ".yaml", ".yml", ".json"})
#: Caps on what a folder ships: one file, and the folder's total (the Pages artifact has a hard size cap).
MAX_SHIPPED_FILE_BYTES = 1_048_576
MAX_SHIPPED_FOLDER_BYTES = 4 * 1_048_576


class MarketplaceIndexError(ValueError):
    """The index document or a listing row is not usable."""


class MarketplacePagesDisabled(RuntimeError):
    """``write_site`` was asked to run while the flag is off, or with no flag tree to read."""


def pages_enabled(*, flags_path: Path | str | None = None) -> bool:
    """Whether regeneration is allowed in the current environment."""
    return read_boolean(FLAG_KEY, False, flags_path=flags_path)


def _require_enabled(flags_path: Path | str | None, what: str) -> None:
    """Refuse, naming the cause: no flag tree at all (a call from outside the repository) or the flag off."""
    if cutover_root.resolve_flags_path(flags_path) is None:
        raise MarketplacePagesDisabled(
            f"{FLAG_KEY}: no flag tree found (set PYFORGE_FLAGS_PATH, pass flags_path, or run from the "
            f"repository root, whose src/platform/config/flags.json is the tree); the marketplace {what} was not written"
        )
    if not pages_enabled(flags_path=flags_path):
        raise MarketplacePagesDisabled(f"{FLAG_KEY} is off; the marketplace {what} was not written")


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
    if not SLUG.match(name):
        raise MarketplaceIndexError(f"an estate module name must match {SLUG.pattern}, got {name!r}")
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


def _require_slug(row: dict[str, Any], key: str, where: str) -> str:
    """The raw value must match ``SLUG``: a stripped match would let ``" mason"`` flow into hrefs and zip names."""
    value = row.get(key)
    if not isinstance(value, str) or not SLUG.match(value):
        raise MarketplaceIndexError(f"{where}: {key} {value!r} must match {SLUG.pattern}")
    return value


def validate_listing(row: dict[str, Any], *, root: Path | None = None) -> None:
    """Raise ``MarketplaceIndexError`` when a listing breaks the index schema.

    ``root`` is the marketplace directory; given, a skill's folder and its
    ``SKILL.md`` must exist there.
    """
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
    if kind == "skill" and chosen is None:
        raise MarketplaceIndexError(f"{ident}: lane is required for a skill (instructions-only or code-backed)")
    packages = _validate_requires(row, ident)
    if kind == "skill" and chosen is not None:
        # A skill's lane is what its packages say (review 2026-10-28, row 3). A module's package is the module.
        if chosen == "code-backed" and not packages:
            raise MarketplaceIndexError(f"{ident}: lane code-backed requires at least one package under requires")
        if chosen == "instructions-only" and packages:
            raise MarketplaceIndexError(f"{ident}: lane instructions-only names a package under requires")
    _validate_install_targets(row, ident)
    _validate_verified_at(row, ident)
    if kind == "skill":
        scope = _require_slug(row, "scope", ident)
        slug = _require_slug(row, "slug", ident)
        path = _require_str(row, "path", ident)
        expected = f"skills/{scope}/{slug}"
        if path != expected:
            raise MarketplaceIndexError(f"{ident}: path {path!r} must be {expected!r}")
        if ident != f"{scope}/{slug}":
            raise MarketplaceIndexError(f"{ident}: a skill's id must be {scope}/{slug}")
        if root is not None:
            folder = root / path
            if folder.is_symlink() or not folder.is_dir():
                raise MarketplaceIndexError(f"{ident}: folder {path} is not a directory in {root}")
            if not (folder / "SKILL.md").is_file():
                raise MarketplaceIndexError(f"{ident}: {path}/SKILL.md is missing")
            _validate_skill_folder(folder, ident)
    else:
        for key in ("scope", "slug"):
            if row.get(key) is not None:
                _require_slug(row, key, ident)
        if row.get("slug") is None and not SLUG.match(str(row["name"])):
            raise MarketplaceIndexError(f"{ident}: name {row['name']!r} names the card; it must match {SLUG.pattern}")
        # A non-skill row's folder, when it names one, sits under its kind's directory (review loop 2, row 20).
        kind_path = row.get("path")
        if kind_path is not None:
            expected = f"{KIND_DIRS[kind]}/{row.get('slug') or row['name']}"
            if not isinstance(kind_path, str) or not _safe_relative(kind_path) or kind_path != expected:
                raise MarketplaceIndexError(f"{ident}: path {kind_path!r} must be {expected!r}")
            if root is not None and (root / kind_path).is_symlink():
                raise MarketplaceIndexError(f"{ident}: folder {kind_path} is a symlink")
            if root is not None and not (root / kind_path).is_dir():
                raise MarketplaceIndexError(f"{ident}: folder {kind_path} is not a directory in {root}")
    _validate_docs(row, ident)
    try:
        json.dumps(row)
    except TypeError as exc:
        raise MarketplaceIndexError(f"{ident}: a value is not JSON (an unquoted YAML date or time?): {exc}") from exc


def _validate_requires(row: dict[str, Any], ident: str) -> list[dict[str, Any]]:
    """The package entries, each with a non-empty ``name`` and a bool ``published``."""
    requires = row.get("requires")
    if requires is None:
        return []
    if isinstance(requires, dict):
        packages = requires.get("packages", [])
        if not isinstance(packages, list):
            raise MarketplaceIndexError(f"{ident}: requires.packages must be a list")
        entries = packages
    elif isinstance(requires, list):
        for item in requires:
            if not isinstance(item, dict) or not isinstance(item.get("kind"), str):
                raise MarketplaceIndexError(f"{ident}: each requires entry needs a kind")
        entries = [item for item in requires if item.get("kind") == "package"]
    else:
        raise MarketplaceIndexError(f"{ident}: requires must be a list of kinds or a packages mapping")
    for item in entries:
        if not isinstance(item, dict):
            raise MarketplaceIndexError(f"{ident}: each requires package must be a mapping")
        _require_str(item, "name", f"{ident} requires")
        if not isinstance(item.get("published"), bool):
            raise MarketplaceIndexError(f"{ident}: requires package {item['name']} needs published: true or false")
    return [item for item in entries if isinstance(item, dict)]


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
                f"{ident}: install target {target!r} must be .agents/skills or .claude/skills, "
                f"or one folder under either whose name matches {SLUG.pattern}"
            )


def _allowed_install_target(target: str) -> bool:
    """``.agents/skills``, ``.claude/skills``, or one folder under either; never absolute, never ``.`` or ``..``.

    Split on ``/`` rather than through ``PurePosixPath``, which drops ``.`` segments before they can be refused.
    """
    if not target or "\\" in target:
        return False
    parts = target.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    head = "/".join(parts[:2])
    if head not in INSTALL_TARGETS or len(parts) > 3:
        return False
    return len(parts) == 2 or SLUG.match(parts[2]) is not None


def _safe_relative(value: str) -> bool:
    """A relative POSIX path with no empty, ``.`` or ``..`` part, no backslash and no trailing slash."""
    if not value or "\\" in value:
        return False
    parts = value.split("/")
    return not any(part in ("", ".", "..") for part in parts)


def _validate_skill_folder(folder: Path, ident: str) -> None:
    """What a skill folder may hold (review loop 2, rows 23 and 38): ``SKILL.md``, ``steps.md``, ``listing.yaml``
    and text files under ``references/``; no symlink, no dot entry, no other file; one file under
    :data:`MAX_SHIPPED_FILE_BYTES` and the folder under :data:`MAX_SHIPPED_FOLDER_BYTES`. The mount and the release
    zip ship exactly this set, so the folder a teammate copies from git is the same skill."""
    total = 0
    suffixes = ", ".join(sorted(SHIPPED_TEXT_SUFFIXES))
    for entry in sorted(folder.rglob("*")):
        rel = entry.relative_to(folder).as_posix()
        if entry.is_symlink():
            raise MarketplaceIndexError(f"{ident}: {rel} is a symlink; a skill folder ships regular files only")
        parts = rel.split("/")
        if any(part.startswith(".") for part in parts):
            raise MarketplaceIndexError(f"{ident}: {rel} is a dot entry; it does not ship")
        if entry.is_dir():
            if parts[0] != REFERENCES_DIR:
                raise MarketplaceIndexError(
                    f"{ident}: {rel}/ is not {REFERENCES_DIR}/; a skill folder holds "
                    f"{', '.join(SKILL_FILES)} and {REFERENCES_DIR}/"
                )
            continue
        if len(parts) == 1:
            if parts[0] not in SKILL_FILES:
                raise MarketplaceIndexError(f"{ident}: {rel} is not one of {', '.join(SKILL_FILES)}; it does not ship")
        elif parts[0] != REFERENCES_DIR:
            raise MarketplaceIndexError(f"{ident}: {rel} is outside {REFERENCES_DIR}/; it does not ship")
        elif entry.suffix.lower() not in SHIPPED_TEXT_SUFFIXES:
            raise MarketplaceIndexError(f"{ident}: {rel}: {REFERENCES_DIR}/ ships text files only ({suffixes})")
        size = entry.stat().st_size
        if size > MAX_SHIPPED_FILE_BYTES:
            raise MarketplaceIndexError(
                f"{ident}: {rel} is {size} bytes; one shipped file is at most {MAX_SHIPPED_FILE_BYTES}"
            )
        total += size
    if total > MAX_SHIPPED_FOLDER_BYTES:
        raise MarketplaceIndexError(f"{ident}: the folder ships {total} bytes; the cap is {MAX_SHIPPED_FOLDER_BYTES}")


def _validate_docs(row: dict[str, Any], ident: str) -> None:
    docs = row.get("docs")
    if docs is None:
        return
    if not isinstance(docs, dict):
        raise MarketplaceIndexError(f"{ident}: docs must be a mapping")
    steps = docs.get("steps")
    if steps is not None:
        if not isinstance(steps, str) or not _safe_relative(steps.strip()):
            raise MarketplaceIndexError(
                f"{ident}: docs.steps {steps!r} must be a relative path inside the skill folder (no .., no leading /)"
            )
        if not isinstance(row.get("path"), str) or not row.get("path"):
            raise MarketplaceIndexError(f"{ident}: docs.steps is declared but the listing has no path to read it under")
    card = docs.get("card")
    if card is not None:
        expected = _card_href(row)
        if card != expected:
            raise MarketplaceIndexError(f"{ident}: docs.card {card!r} must be {expected!r} (relative to the site root)")


def _validate_verified_at(row: dict[str, Any], ident: str) -> None:
    value = row.get("verified_at")
    if value is None:
        return
    if isinstance(value, (_dt.date, _dt.datetime)):
        raise MarketplaceIndexError(
            f"{ident}: verified_at must be a quoted YYYY-MM-DD string or null; an unquoted {value.isoformat()} is a YAML date"
        )
    if not isinstance(value, str) or not ISO_DATE.match(value):
        raise MarketplaceIndexError(f"{ident}: verified_at {value!r} must be a quoted YYYY-MM-DD string or null")
    try:
        _dt.date.fromisoformat(value)
    except ValueError as exc:
        raise MarketplaceIndexError(f"{ident}: verified_at {value!r} is not a calendar date") from exc


def _plugin_name(row: dict[str, Any]) -> str:
    return f"{row['scope']}-{row['slug']}"


def _check_rows(rows: list[dict[str, Any]]) -> None:
    """Across the listings: unique ids, unique cards and unique ``<scope>-<slug>`` plugin names."""
    seen_ids: dict[str, int] = {}
    seen_cards: dict[str, str] = {}
    seen_plugins: dict[str, str] = {}
    for row in rows:
        ident = str(row["id"])
        if ident in seen_ids:
            raise MarketplaceIndexError(f"{ident}: duplicate id")
        seen_ids[ident] = 1
        href = _card_href(row)
        if href in seen_cards:
            raise MarketplaceIndexError(f"{ident}: card {href} is also {seen_cards[href]}'s")
        seen_cards[href] = ident
        if row.get("kind") == "skill":
            plugin = _plugin_name(row)
            if plugin in seen_plugins:
                raise MarketplaceIndexError(f"{ident}: plugin and zip name {plugin} is also {seen_plugins[plugin]}'s")
            seen_plugins[plugin] = ident


def listings_from_document(document: dict[str, Any], *, root: Path | None = None) -> list[dict[str, Any]]:
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
        validate_listing(row, root=root)
    _check_rows(rows)
    return sorted(rows, key=lambda row: str(row["id"]))


def load_listings(path: Path, *, root: Path | None = None) -> list[dict[str, Any]]:
    """Load listings from ``path`` (index schema or estate registry)."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if document is None:
        document = {}
    return listings_from_document(document, root=root)


def _card_href(row: dict[str, Any]) -> str:
    """The card's path relative to the site root: ``skills/<scope>/<slug>.html`` for a skill, ``<kind dir>/<slug>.html`` otherwise."""
    kind = str(row.get("kind") or "")
    directory = KIND_DIRS.get(kind)
    if directory is None:
        raise MarketplaceIndexError(f"{row.get('id')}: kind {kind!r} has no card directory")
    slug = str(row.get("slug") or row.get("name") or "")
    if kind == "skill":
        return f"{directory}/{row.get('scope')}/{slug}.html"
    return f"{directory}/{slug}.html"


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


def _verified_text(row: dict[str, Any]) -> str:
    value = row.get("verified_at")
    return f"verified {value}" if isinstance(value, str) and value else "never verified"


def _steps_text(row: dict[str, Any], steps_root: Path | None) -> str | None:
    """Read ``docs.steps``, a path inside the skill folder (P2: a bare filename next to ``SKILL.md``).

    The candidate is resolved and must stay under the skill folder; a
    traversing or absolute ``docs.steps`` is refused before anything is
    written (review 2026-10-28, row 1). A declared file that is missing is a
    listing error too.
    """
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
    if not isinstance(skill_path, str) or not skill_path:
        raise MarketplaceIndexError(f"{row['id']}: docs.steps is declared but the listing has no path to read it under")
    if not _safe_relative(relative) or not _safe_relative(skill_path):
        raise MarketplaceIndexError(f"{row['id']}: docs.steps {relative!r} must stay inside {skill_path}")
    folder = (steps_root / skill_path).resolve()
    if not folder.is_relative_to(steps_root.resolve()):
        raise MarketplaceIndexError(f"{row['id']}: path {skill_path!r} resolves outside the marketplace")
    candidate = (folder / relative).resolve()
    if not candidate.is_relative_to(folder):
        raise MarketplaceIndexError(f"{row['id']}: docs.steps {relative!r} resolves outside {skill_path}")
    if not candidate.is_file():
        raise MarketplaceIndexError(f"{row['id']}: docs.steps {relative!r} is not a file under {skill_path}")
    return candidate.read_text(encoding="utf-8")


# ------------------------------------------------------------------------------------------ markdown

#: A fence opens with three or more backticks or tildes after at most three spaces; the info string's first word
#: is the language (``bash title=x`` is still a bash fence); a backtick fence's info string holds no backtick.
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*([A-Za-z0-9_+.-]*)(?:[ \t][^`]*)?$")
_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_BULLET = re.compile(r"^( *)[-*]\s+(.*)$")
_ORDERED = re.compile(r"^( *)\d+[.)]\s+(.*)$")
_CODE_SPAN = re.compile(r"(`[^`]+`)")
_STRONG = re.compile(r"\*\*([^*]+)\*\*")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def _link(match: re.Match[str]) -> str:
    """``[text](url)`` as a link for an ``http(s)`` or relative target; any other scheme stays literal text."""
    text, url = match.group(1), match.group(2)
    scheme = url.split(":", 1)[0].lower() if ":" in url.split("/", 1)[0] else ""
    if scheme and scheme not in ("http", "https"):
        return match.group(0)
    return f'<a href="{url}">{text}</a>'


def _inline(text: str) -> str:
    """Escaped text with ``code`` spans, ``**strong**`` and ``[text](url)`` links; nothing else is markup."""
    rendered: list[str] = []
    for part in _CODE_SPAN.split(html.escape(text)):
        if len(part) >= 2 and part.startswith("`") and part.endswith("`"):
            rendered.append(f"<code>{part[1:-1]}</code>")
        else:
            rendered.append(_LINK.sub(_link, _STRONG.sub(r"<strong>\1</strong>", part)))
    return "".join(rendered)


def _closes(line: str, marker: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(marker[0]) and set(stripped) == {marker[0]} and len(stripped) >= len(marker)


def render_markdown(text: str, *, heading_offset: int = 1) -> str:
    """A deterministic minimal renderer for ``steps.md`` (review 2026-10-28, row 5; loop 2, row 25).

    Recognised: ATX headings (demoted by ``heading_offset`` levels, so the
    card keeps its one ``h1``), fenced code blocks (backtick or tilde, an
    info string, up to three spaces of indent, closed by a fence of the same
    marker), ``-``/``*`` bullet and ``1.`` ordered lists (one level of
    nesting by indent; an indented following line continues the item; a
    fence inside a list closes the list), blank-line-separated paragraphs,
    inline ``code`` spans, ``**strong**`` and ``[text](url)`` links to
    ``http(s)`` or relative targets. Everything is HTML-escaped first; raw
    HTML and images stay literal text. Pure: the same text renders the same
    bytes.
    """
    lines = text.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    # Each list item: (ordered?, text, nested items).
    items: list[tuple[bool, str, list[str]]] = []

    def flush_paragraph() -> None:
        if paragraph:
            out.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if not items:
            return
        ordered = items[0][0]
        tag = "ol" if ordered else "ul"
        parts = []
        for _ordered, item, nested in items:
            inner = "".join(f"<li>{_inline(child)}</li>" for child in nested)
            parts.append(f"<li>{_inline(item)}{f'<ul>{inner}</ul>' if inner else ''}</li>")
        out.append(f"<{tag}>" + "".join(parts) + f"</{tag}>")
        items.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        fence = _FENCE.match(line.lstrip() if items else line)
        if fence:
            flush_paragraph()
            flush_list()
            marker, language = fence.group(1), fence.group(2)
            indent = len(line) - len(line.lstrip())  # a fence under a list item: its lines lose that indent
            code: list[str] = []
            index += 1
            while index < len(lines) and not _closes(lines[index], marker):
                body = lines[index]
                code.append(body[indent:] if body[:indent].strip() == "" else body.lstrip())
                index += 1
            index += 1  # the closing fence, or the end of the text
            attribute = f' class="language-{language}"' if language else ""
            out.append(f"<pre><code{attribute}>{html.escape(chr(10).join(code))}\n</code></pre>")
            continue
        heading = _HEADING.match(line)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(len(heading.group(1)) + heading_offset, 6)
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            index += 1
            continue
        listed = _BULLET.match(line) or _ORDERED.match(line)
        if listed:
            flush_paragraph()
            ordered = _ORDERED.match(line) is not None
            indent, body = len(listed.group(1)), listed.group(2).strip()
            if items and indent >= 2:
                items[-1][2].append(body)
            else:
                if items and items[0][0] != ordered:
                    flush_list()
                items.append((ordered, body, []))
            index += 1
            continue
        if items and line.startswith("  ") and line.strip():
            ordered, body, nested = items[-1]
            if nested:
                nested[-1] = f"{nested[-1]} {line.strip()}"
            else:
                items[-1] = (ordered, f"{body} {line.strip()}", nested)
            index += 1
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            index += 1
            continue
        flush_list()
        paragraph.append(line.strip())
        index += 1
    flush_paragraph()
    flush_list()
    return "\n".join(out)


# --------------------------------------------------------------------------------------------- pages


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
        "pre{background:#f5f5f4;border:1px solid #d6d3d1;padding:.75rem;overflow-x:auto}\n"
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

    Order (the review of 2026-10-28, row 5): what it is, Install, Unpublished
    packages, Sources, the verified date, then Steps (``steps.md`` rendered
    with :func:`render_markdown`), Jobs, Related, Contribute. The paper
    prototype's sample commands are not rendered.
    """
    validate_listing(row)
    title = str(row.get("title") or row.get("display_name") or row["name"])
    tier = row.get("tier")
    trust = str(row["trust_tier"])
    tier_bit = f"tier {html.escape(str(tier))} · " if tier else ""
    href = _card_href(row)
    up = "../" * href.count("/")
    jobs = row.get("jobs") or []
    jobs_bit = (" · jobs " + ", ".join(html.escape(str(job)) for job in jobs)) if jobs else ""
    bits = [
        f'<p><a href="{up}index.html">Marketplace</a></p>',
        f"<h1>{html.escape(title)}</h1>",
        f'<p class="meta">{html.escape(str(row["kind"]))} · '
        f"{html.escape(str(row['name']))} · version {html.escape(str(row.get('version') or 'unversioned'))}</p>",
        f'<p class="meta">{tier_bit}trust {html.escape(trust)} · source {html.escape(str(row["source"]))} · '
        f"{html.escape(_verified_text(row))}{jobs_bit}</p>",
    ]
    if tier == "community":
        bits.append('<p class="meta">No review record. community maps to unverified until a CODEOWNER promotes it.</p>')
    description = str(row.get("description") or row.get("summary") or "")
    if description:
        bits.append(f"<p>{html.escape(description)}</p>")
    owners = row.get("owners") or []
    if isinstance(owners, list) and owners:
        bits.append("<p>Owners: " + ", ".join(html.escape(str(owner)) for owner in owners) + "</p>")
    if row.get("kind") == "skill":
        targets = ", ".join(f"<code>{html.escape(target)}</code>" for target in _install_targets(row))
        plugin = html.escape(_plugin_name(row))
        bits.append("<h2>Install</h2>")
        bits.append(
            f"<p>Copy the folder <code>{html.escape(str(row['path']))}</code> into {targets}. "
            "Claude Code's documented project skill path is <code>.claude/skills/</code>. "
            "Devin's is <code>.agents/skills/</code>. "
            "The tool matrix marks Claude Code reading <code>.agents/skills/</code> as uncertain "
            "and does not list <code>.claude/skills/</code> for Devin. "
            "<code>bmp install</code> is not built; this page is not an install button.</p>"
        )
        bits.append(
            f"<p>The rolling <code>{html.escape(RELEASE_TAG)}</code> release carries <code>{plugin}.zip</code> "
            f"with <code>{plugin}.zip.sha256</code> beside it while the marketplace flag is on for that deploy. "
            f"The zip holds the <code>{plugin}/</code> folder with "
            + ", ".join(f"<code>{name}</code>" for name in SKILL_FILES)
            + f" and <code>{REFERENCES_DIR}/</code> when the skill has one. Check and unpack it where both files "
            f"were downloaded: <code>sha256sum -c {plugin}.zip.sha256 &amp;&amp; unzip {plugin}.zip -d .claude/skills/</code>, "
            f"and the same with <code>-d .agents/skills/</code>.</p>"
        )
        bits.append(
            "<p><code>marketplace.json</code> (the Claude marketplace file) is a discovery pointer for this listing; "
            "the folder copy above is the install until Round 0 confirms a plugin install exposes the skill.</p>"
        )
    hint = row.get("install_hint")
    if hint:
        bits.append(f"<p>Install hint: {html.escape(str(hint))}</p>")
    notes = _requires_notes(row)
    if notes:
        items = "".join(f"<li>{html.escape(note)}</li>" for note in notes)
        bits.append(f"<h2>Unpublished packages</h2><ul>{items}</ul>")
    if row.get("kind") == "skill":
        bits.append(_sources_html(row))
    if steps_text:
        bits.append("<h2>Steps</h2>")
        # The runbook's own ``#`` sits two levels down, so its steps are ``<h4>`` under this one ``<h2>``.
        bits.append(render_markdown(steps_text, heading_offset=2))
    elif row.get("kind") == "skill":
        bits.append("<h2>Steps</h2><p>This card has no <code>steps.md</code> to render.</p>")
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
    _check_rows(rows)
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
            f'<p class="meta">{kind} · {trust}{lane_bit} · {html.escape(_verified_text(row))}</p>'
            f"<p>{html.escape(str(row.get('description') or ''))}</p>"
            "</article>"
        )
    return _page("BMAD marketplace", "\n".join(parts))


def render_listings_json(rows: list[dict[str, Any]]) -> str:
    """Machine-readable copy of the same listings the pages show."""
    for row in rows:
        validate_listing(row)
    _check_rows(rows)
    payload = {"schema": SCHEMA_ID, "listings": rows}
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _skill_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skills = []
    for row in rows:
        validate_listing(row)
        if row.get("kind") == "skill" and row.get("scope") and row.get("slug"):
            skills.append(row)
    _check_rows(rows)
    return skills


def _marketplace_document(rows: list[dict[str, Any]], source_for: Any) -> str:
    """Claude ``marketplace.json``. ``name`` matches the ``extraKnownMarketplaces`` key."""
    plugins = []
    for row in _skill_rows(rows):
        plugins.append(
            {
                "name": _plugin_name(row),
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


def render_codex_marketplace(rows: list[dict[str, Any]]) -> str:
    """Codex's ``.agents/plugins/marketplace.json`` for the marketplace directory (review loop 2, row 21).

    The shape ``CatalogEngine.manifests`` writes for the v1 catalog: ``name``, ``interface.displayName`` and one
    ``local`` plugin per skill, so ``codex plugin marketplace add <marketplace dir>`` reaches the three listings.
    """
    plugins = [
        {
            "name": _plugin_name(row),
            "source": {"source": "local", "path": f"./skills/{row['scope']}/{row['slug']}"},
            "policy": {"installation": "AVAILABLE"},
            "category": "skill",
        }
        for row in _skill_rows(rows)
    ]
    document = {"name": MARKETPLACE_NAME, "interface": {"displayName": "BMAD marketplace"}, "plugins": plugins}
    return json.dumps(document, indent=2) + "\n"


def _skill_folders(marketplace: Path) -> list[Path]:
    """Every ``skills/<scope>/<slug>/`` directory, sorted."""
    skills = marketplace / "skills"
    if not skills.is_dir():
        return []
    return sorted(path for path in skills.glob("*/*") if path.is_dir())


def listings_from_skill_folders(marketplace: Path) -> list[dict[str, Any]]:
    """Read each ``skills/<scope>/<slug>/listing.yaml`` and validate it.

    ``index.yaml`` is the committed concatenation of these files until
    ``bmp index build`` exists. A skill folder with no ``listing.yaml`` is a
    listing error, not a silent omission (review 2026-10-28, row 3).
    """
    rows: list[dict[str, Any]] = []
    for folder in _skill_folders(marketplace):
        relative = folder.relative_to(marketplace).as_posix()
        path = folder / "listing.yaml"
        if not path.is_file():
            raise MarketplaceIndexError(f"{relative}: a skill folder with no listing.yaml")
        row = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(row, dict):
            raise MarketplaceIndexError(f"{path}: listing must be a mapping")
        validate_listing(row, root=marketplace)
        if row.get("path") != relative:
            raise MarketplaceIndexError(f"{path}: path {row.get('path')!r} is not this folder ({relative})")
        rows.append(row)
    _check_rows(rows)
    return sorted(rows, key=lambda row: str(row["id"]))


def _check_folders_declared(rows: list[dict[str, Any]], marketplace: Path) -> None:
    """Every ``skills/<scope>/<slug>/`` folder is a row of the index (the converse is ``validate_listing``'s)."""
    declared = {str(row.get("path")) for row in rows if row.get("kind") == "skill"}
    for folder in _skill_folders(marketplace):
        relative = folder.relative_to(marketplace).as_posix()
        if relative not in declared:
            raise MarketplaceIndexError(f"{relative}: a skill folder the index does not declare")


def render_site(
    rows: list[dict[str, Any]],
    *,
    steps_root: Path | None = None,
) -> dict[str, str]:
    """Every document of the site, ``{relative path: text}``, in write order; nothing is written.

    A listing error raises before any document is produced, so a refused
    render leaves no site directory behind.
    """
    for row in rows:
        validate_listing(row, root=steps_root)
    _check_rows(rows)
    documents: dict[str, str] = {
        "index.html": render_index(rows),
        "listings.json": render_listings_json(rows),
        "marketplace.json": render_url_marketplace(rows),
    }
    for row in rows:
        documents[_card_href(row)] = render_skill_card(row, steps_text=_steps_text(row, steps_root))
    return documents


def _is_generated_site(site_dir: Path) -> bool:
    """A tree this module wrote: ``listings.json`` at its root with this schema (review loop 2, row 22)."""
    listings = site_dir / "listings.json"
    if not listings.is_file():
        return False
    try:
        payload = json.loads(listings.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return False
    return isinstance(payload, dict) and payload.get("schema") == SCHEMA_ID


def write_site(
    rows: list[dict[str, Any]],
    site_dir: Path,
    *,
    flags_path: Path | str | None = None,
    steps_root: Path | None = None,
) -> list[Path]:
    """Write ``index.html``, ``listings.json``, ``marketplace.json`` and one card per listing.

    Refuses, and writes nothing, while ``pyforge.steward.marketplace_pages``
    is off or no flag tree is found. ``flags_path`` is for tests; production
    reads the estate tree. Every document is rendered first; then
    ``site_dir`` is replaced by a fresh tree, so a card whose listing was
    dropped or renamed does not survive (review 2026-10-28, row 4).
    """
    _require_enabled(flags_path, "pages")
    documents = render_site(rows, steps_root=steps_root)
    if steps_root is not None and steps_root.resolve().is_relative_to(site_dir.resolve()):
        raise MarketplaceIndexError(f"site directory {site_dir} would replace the listings under {steps_root}")
    if site_dir.is_symlink():
        raise MarketplaceIndexError(f"site directory {site_dir} is a symlink; refusing to replace it")
    if site_dir.exists():
        if not site_dir.is_dir():
            raise MarketplaceIndexError(f"site directory {site_dir} is not a directory")
        if any(site_dir.iterdir()) and not _is_generated_site(site_dir):
            raise MarketplaceIndexError(
                f"site directory {site_dir} is not a generated site (no listings.json with schema {SCHEMA_ID}); "
                "refusing to replace it"
            )
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True)
    written: list[Path] = []
    for relative, text in documents.items():
        target = site_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        written.append(target)
    return written


def write_site_from_index(
    index_path: Path,
    site_dir: Path,
    *,
    flags_path: Path | str | None = None,
) -> list[Path]:
    """Load ``index_path`` and write the site next to it.

    The index's directory is the marketplace root: each skill row's folder
    and ``SKILL.md`` must exist there, and every ``skills/<scope>/<slug>/``
    folder there must be a row. ``site/marketplace.json`` is the Pages URL
    form. The git marketplace file (``.claude-plugin/marketplace.json``) is
    written by ``write_plugin_manifest`` so a render into a temporary site
    does not touch the index's directory.
    """
    root = index_path.parent
    rows = load_listings(index_path, root=root)
    _check_folders_declared(rows, root)
    return write_site(rows, site_dir, flags_path=flags_path, steps_root=root)


def write_plugin_manifest(
    index_path: Path,
    dest: Path,
    *,
    flags_path: Path | str | None = None,
) -> Path:
    """Write the relative-path ``marketplace.json`` a ``github`` or ``git`` source reads."""
    _require_enabled(flags_path, "manifest")
    rows = load_listings(index_path, root=index_path.parent)
    _check_folders_declared(rows, index_path.parent)
    text = render_relative_marketplace(rows)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


def write_codex_manifest(
    index_path: Path,
    dest: Path,
    *,
    flags_path: Path | str | None = None,
) -> Path:
    """Write Codex's ``.agents/plugins/marketplace.json`` (``CODEX_MANIFEST_RELATIVE``) for the marketplace directory."""
    _require_enabled(flags_path, "Codex manifest")
    rows = load_listings(index_path, root=index_path.parent)
    _check_folders_declared(rows, index_path.parent)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_codex_marketplace(rows), encoding="utf-8")
    return dest


def write_plugin_manifests(index_path: Path, *, flags_path: Path | str | None = None) -> list[Path]:
    """Both manifests beside the index: ``.claude-plugin/marketplace.json`` and ``.agents/plugins/marketplace.json``."""
    root = index_path.parent
    return [
        write_plugin_manifest(index_path, root / ".claude-plugin" / "marketplace.json", flags_path=flags_path),
        write_codex_manifest(index_path, root / CODEX_MANIFEST_RELATIVE, flags_path=flags_path),
    ]


def main(argv: list[str] | None = None) -> int:
    """``python -m pyforge.steward.marketplace_pages --flag-env`` prints ``PYFORGE_MARKETPLACE_PAGES=1|0``.

    The Pages workflow appends the line to ``$GITHUB_ENV`` beside herald's ``pages_env`` lines, in the Guild env
    at the repository root, so the flag is read from the estate tree for the environment the deploy resolves
    (``dev``: ``pages.yml`` sets no ``PYFORGE_ENVIRONMENT``). The one verb; nothing else is a duty.
    """
    parser = argparse.ArgumentParser(
        prog="python -m pyforge.steward.marketplace_pages",
        description=f"print {FLAG_ENV}=1|0 for the Pages build environment",
    )
    parser.add_argument("--flag-env", action="store_true", help=f"print {FLAG_ENV}=1|0 and exit")
    args = parser.parse_args(argv)
    if not args.flag_env:
        parser.error("--flag-env is the one verb")
    if cutover_root.resolve_flags_path(None) is None:
        # Off plus no mount is a valid pages-check state, so a silent 0 would drop /marketplace/ from a deploy
        # with a green workflow (review loop 2, row 37).
        sys.stderr.write(
            f"{FLAG_KEY}: no flag tree found (set PYFORGE_FLAGS_PATH or run from the repository root, whose "
            "src/platform/config/flags.json is the tree); refusing to print a build line\n"
        )
        return 2
    sys.stdout.write(f"{FLAG_ENV}={'1' if pages_enabled() else '0'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
