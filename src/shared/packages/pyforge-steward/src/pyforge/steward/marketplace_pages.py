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
is touched, and the site written into a fresh tree. Loop 3 of that review
(rows 42-57) made containment the validator's (a symlinked parent, a FIFO),
the previous ``listings.json`` the inventory ``write_site`` may replace,
the fence and link grammar CommonMark-shaped, and the build line refused on
a tree that does not declare the flag.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import os
import posixpath
import re
import shutil
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import yaml
from pyforge.core import cutover_root
from pyforge.core.flags import FlagConfigError, overlays_path_for, read_boolean

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
#: Where a card links the documents the mount does not carry (loop 4, row 76): the repository's blob view of
#: ``main``; the mount rewrites the host to the deploying one (``docs-site/src/lib/marketplace.ts``).
REPOSITORY_BLOB_URL = PUBLIC_MARKETPLACE_GIT_URL.removesuffix(".git") + "/blob/main"
TOOL_MATRIX_RELATIVE = (
    "_bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/"
    "tool-support-matrix.md"
)
#: A ``related`` entry that names a skill listing, ``@<scope>/<slug>`` (matched whole, loop 5, row 83); the card
#: links it to the sibling skill card. Any other string under ``related`` is text on the card.
_RELATED_SKILL = re.compile(r"^@([a-z0-9][a-z0-9-]*)/([a-z0-9][a-z0-9-]*)$")


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
    if not isinstance(name, str) or not name:
        raise MarketplaceIndexError("an estate module row needs a name")
    if not SLUG.fullmatch(name):
        # matched whole and raw, as the index rows are (loop 4, row 77): "bmad\n" is not bmad
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


def _require_exact(row: dict[str, Any], key: str, where: str) -> str:
    """A non-empty string with no surrounding whitespace: ``id``, ``path``, ``kind``, ``trust_tier``, ``source``,
    ``name`` and a package's ``name`` flow raw into ``listings.json``, the folder lookup and the card, so a stripped
    comparison would admit ``" mason/environment"`` or ``" skill"`` (loop 3, row 53; loop 4, row 66)."""
    value = _require_str(row, key, where)
    if row.get(key) != value:
        raise MarketplaceIndexError(f"{where}: {key} {row.get(key)!r} carries surrounding whitespace")
    return value


def _require_slug(row: dict[str, Any], key: str, where: str) -> str:
    """The raw value must match ``SLUG`` whole: a stripped match would let ``" mason"`` flow into hrefs and zip names,
    and ``re.match`` against ``$`` would let ``"mason\\n"`` (a double-quoted YAML scalar) through (loop 3, row 57)."""
    value = row.get(key)
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise MarketplaceIndexError(f"{where}: {key} {value!r} must match {SLUG.pattern}")
    return value


def validate_listing(row: dict[str, Any], *, root: Path | None = None) -> None:
    """Raise ``MarketplaceIndexError`` when a listing breaks the index schema.

    ``root`` is the marketplace directory; given, a skill's folder and its
    ``SKILL.md`` must exist there.
    """
    if not isinstance(row, dict):
        raise MarketplaceIndexError("a listing must be a mapping")
    ident = _require_exact(row, "id", "listing")
    kind = _require_exact(row, "kind", ident)
    if kind not in KINDS:
        raise MarketplaceIndexError(f"{ident}: kind {kind!r} is not one of {sorted(KINDS)}")
    trust = _require_exact(row, "trust_tier", ident)
    if trust not in TRUST_TIERS:
        raise MarketplaceIndexError(f"{ident}: trust_tier {trust!r} is not a v1 tier name")
    tier = row.get("tier")
    if tier is not None:
        if tier not in TIER_TO_TRUST:
            raise MarketplaceIndexError(f"{ident}: tier {tier!r} is not a bmp tier")
        expected_trust = TIER_TO_TRUST[str(tier)]
        if trust != expected_trust:
            raise MarketplaceIndexError(f"{ident}: tier {tier} maps to trust_tier {expected_trust}, got {trust}")
    _require_exact(row, "name", ident)
    _require_exact(row, "source", ident)
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
        path = _require_exact(row, "path", ident)
        expected = f"skills/{scope}/{slug}"
        if path != expected:
            raise MarketplaceIndexError(f"{ident}: path {path!r} must be {expected!r}")
        if ident != f"{scope}/{slug}":
            raise MarketplaceIndexError(f"{ident}: a skill's id must be {scope}/{slug}")
        if root is not None:
            folder = _contained_folder(root, path, ident)
            if not (folder / "SKILL.md").is_file():
                raise MarketplaceIndexError(f"{ident}: {path}/SKILL.md is missing")
            _validate_skill_folder(folder, ident)
    else:
        for key in ("scope", "slug"):
            if row.get(key) is not None:
                _require_slug(row, key, ident)
        if row.get("slug") is None and not SLUG.fullmatch(str(row["name"])):
            raise MarketplaceIndexError(f"{ident}: name {row['name']!r} names the card; it must match {SLUG.pattern}")
        # A non-skill row's folder, when it names one, sits under its kind's directory (review loop 2, row 20).
        kind_path = row.get("path")
        if kind_path is not None:
            expected = f"{KIND_DIRS[kind]}/{row.get('slug') or row['name']}"
            if not isinstance(kind_path, str) or not _safe_relative(kind_path) or kind_path != expected:
                raise MarketplaceIndexError(f"{ident}: path {kind_path!r} must be {expected!r}")
            if root is not None:
                _contained_folder(root, kind_path, ident)
    _validate_docs(row, ident)
    _validate_related(row, ident)
    try:
        json.dumps(row)
    except TypeError as exc:
        raise MarketplaceIndexError(f"{ident}: a value is not JSON (an unquoted YAML date or time?): {exc}") from exc


def _validate_related(row: dict[str, Any], ident: str) -> None:
    """``related`` is a list of strings; an entry that starts with ``@`` is a whole ``@<scope>/<slug>`` reference
    (loop 5, row 84: an int raised a raw ``TypeError`` from the cross-reference, a bare string was iterated character
    by character, and ``@Warden/Scan`` or ``@warden/scan/extra`` passed as free text, so the rule held only for a
    reference spelled right). Whether the reference names a skill listing is ``_check_rows``'s."""
    related = row.get("related")
    if related is None:
        return
    if not isinstance(related, list) or any(not isinstance(item, str) for item in related):
        raise MarketplaceIndexError(f"{ident}: related must be a list of strings")
    for item in related:
        if item.startswith("@") and not _RELATED_SKILL.fullmatch(item):
            raise MarketplaceIndexError(f"{ident}: related {item!r} must be @<scope>/<slug> ({SLUG.pattern} each)")


def _contained_folder(root: Path, relative: str, ident: str) -> Path:
    """The listing's folder under ``root``: a directory, not a symlink at any level, whose resolved path stays inside
    the resolved marketplace (loop 3, row 42: ``skills/linked -> /outside`` passed the leaf-only check, so both
    manifests were written for a folder outside the tree)."""
    folder = root / relative
    probe = root
    for part in relative.split("/"):
        probe = probe / part
        if probe.is_symlink():
            raise MarketplaceIndexError(
                f"{ident}: {probe.relative_to(root).as_posix()} is a symlink; folder {relative} is refused"
            )
    if not folder.is_dir():
        raise MarketplaceIndexError(f"{ident}: folder {relative} is not a directory in {root}")
    if not folder.resolve().is_relative_to(root.resolve()):
        raise MarketplaceIndexError(f"{ident}: folder {relative} resolves outside the marketplace")
    return folder


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
        _require_exact(item, "name", f"{ident} requires")
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
    return len(parts) == 2 or SLUG.fullmatch(parts[2]) is not None


def _safe_relative(value: str) -> bool:
    """A relative POSIX path with no empty, ``.`` or ``..`` part, no backslash and no trailing slash."""
    if not value or "\\" in value:
        return False
    parts = value.split("/")
    return not any(part in ("", ".", "..") for part in parts)


def _validate_skill_folder(folder: Path, ident: str) -> None:
    """What a skill folder may hold (review loop 2, rows 23 and 38): ``SKILL.md``, ``steps.md``, ``listing.yaml``
    and text files under ``references/``; regular files only (no symlink, no FIFO), no dot entry, no other file; one file under
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
        if not entry.is_file():
            # a FIFO, a socket or a device node (loop 3, row 43): read_text would block or throw on it
            raise MarketplaceIndexError(f"{ident}: {rel} is not a regular file")
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
    """Across the listings: unique ids, unique cards and unique ``<scope>-<slug>`` plugin names; no plugin named like
    the site release's own asset (loop 4, row 60); every ``related`` ``@scope/slug`` names a listing (row 76)."""
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
            if plugin == RELEASE_TAG:
                raise MarketplaceIndexError(
                    f"{ident}: plugin and zip name {plugin} is the site release's own asset ({RELEASE_TAG}.zip)"
                )
            if plugin in seen_plugins:
                raise MarketplaceIndexError(f"{ident}: plugin and zip name {plugin} is also {seen_plugins[plugin]}'s")
            seen_plugins[plugin] = ident
    # a reference names a skill row, whose card is skills/<scope>/<slug>.html, the href the card builds (loop 5, row
    # 83: @module/bmad passed against the module's id and linked a card no render produces)
    skills = {str(row["id"]) for row in rows if row.get("kind") == "skill"}
    for row in rows:
        for item in row.get("related") or []:
            match = _RELATED_SKILL.fullmatch(str(item))
            if match and f"{match.group(1)}/{match.group(2)}" not in skills:
                raise MarketplaceIndexError(f"{row['id']}: related {item} names no skill listing")


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


def _load_yaml(path: Path) -> Any:
    """``yaml.safe_load`` of ``path``, a listing error (not a raw ``yaml.YAMLError``) when it does not parse, and
    (loop 5, row 86) when it is not UTF-8 text or cannot be read."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        raise MarketplaceIndexError(f"{path}: not a readable UTF-8 text file ({exc})") from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise MarketplaceIndexError(f"{path}: not valid YAML ({exc})") from exc


def load_listings(path: Path, *, root: Path | None = None) -> list[dict[str, Any]]:
    """Load listings from ``path`` (index schema or estate registry)."""
    document = _load_yaml(path)
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

#: A fence opens with three or more backticks or tildes (matched after the line's indent is taken off, so a fence
#: under a list item or indented four spaces still opens); the info string's first word, cut at the first ``,`` or
#: ``{``, is the language (``bash title=x``, ``python,linenos`` and ``bash{.cls}`` are still bash and python fences;
#: ``{r}`` has none); a backtick fence's info string holds no backtick (loop 3, row 46).
_FENCE = re.compile(r"^(`{3,}|~{3,})[ \t]*(\S*)(.*)$")
_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_BULLET = re.compile(r"^( *)[-*]\s+(.*)$")
#: An ordered marker is one or two digits (loop 3, row 47: ``2026. The year`` is a paragraph, not a list).
_ORDERED = re.compile(r"^( *)(\d{1,2})[.)]\s+(.*)$")
_CODE_SPAN = re.compile(r"(`[^`]+`)")
_STRONG = re.compile(r"\*\*([^*]+)\*\*")
#: ``[text](url)``; a preceding ``!`` (an image) leaves the whole thing literal.
_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)\)")


def _link_href(url: str, link_base: str | None) -> str | None:
    """The ``href`` for a markdown target, or ``None`` when it stays literal text (loop 3, row 47).

    ``http(s)`` targets pass through. A relative target (no scheme, not ``/``-rooted, not protocol-relative, no
    ``..`` or empty segment, decoded or not; a leading ``./`` dropped) is prefixed with ``link_base`` so a card
    beside the mounted skill folder points into it; with ``link_base`` ``None`` (a card whose folder the mount does
    not carry, loop 4, row 58) a relative target stays literal. A fragment-only target passes through. Any other
    scheme, ``//host``, ``/rooted`` and a traversing path stay literal.
    """
    if url.startswith("#"):
        return url
    head = url.split("/", 1)[0]
    scheme = url.split(":", 1)[0].lower() if ":" in head else ""
    if scheme:
        return url if scheme in ("http", "https") and url.lower().startswith(f"{scheme}://") else None
    if url.startswith("/") or link_base is None:
        return None
    while url.startswith("./"):  # a leading ./ names the same folder (loop 4, row 61)
        url = url[2:]
    if ":" in url.split("/", 1)[0]:
        # loop 5, row 81: the strip ran after the scheme test, so ./javascript:x lost its ./ and became a
        # javascript: href; a stripped target whose first segment holds a colon is a scheme, never a file
        return None
    path = url.split("#", 1)[0].split("?", 1)[0]
    # the rule holds for the decoded path too: %2e%2e is .. to the browser (row 61)
    if not path or not _safe_relative(path) or not _safe_relative(urllib.parse.unquote(path)):
        return None
    return f"{link_base}{url}"


def _inline(text: str, link_base: str | None = None) -> str:
    """Escaped text with ``code`` spans, ``**strong**`` and ``[text](url)`` links; nothing else is markup."""

    def link(match: re.Match[str]) -> str:
        target = match.group(2)
        if target.startswith("&lt;") and target.endswith("&gt;"):
            # a CommonMark <destination>, escaped already (loop 5, row 93): the brackets are not part of the target
            target = target[4:-4]
        href = _link_href(target, link_base)
        return match.group(0) if href is None else f'<a href="{href}">{match.group(1)}</a>'

    rendered: list[str] = []
    # re.split with one group alternates text and code span; the odd parts are the spans (a bare "``" in text is
    # text, loop 3's non-fence case)
    for index, part in enumerate(_CODE_SPAN.split(html.escape(text))):
        if index % 2:
            rendered.append(f"<code>{part[1:-1]}</code>")
        else:
            rendered.append(_LINK.sub(link, _STRONG.sub(r"<strong>\1</strong>", part)))
    return "".join(rendered)


def _expand_leading(line: str) -> str:
    """``line`` with the tabs of its leading whitespace expanded to four-column stops; the rest is untouched."""
    rest = line.lstrip(" \t")
    return line[: len(line) - len(rest)].expandtabs(4) + rest


def _dedent_columns(line: str, columns: int) -> str:
    """``line`` with ``columns`` columns of leading whitespace removed, a tab reaching the next four-column stop; a
    tab that crosses the boundary leaves its remaining columns as spaces (CommonMark's rule)."""
    column = index = 0
    while index < len(line) and column < columns and line[index] in " \t":
        column += 1 if line[index] == " " else 4 - column % 4
        index += 1
    return " " * max(column - columns, 0) + line[index:]


def _opens(line: str) -> tuple[str, str, int] | None:
    """``(marker, language, indent)`` when ``line`` opens a fence, else ``None``."""
    stripped = line.lstrip()
    fence = _FENCE.match(stripped)
    if not fence:
        return None
    marker, info, tail = fence.group(1), fence.group(2), fence.group(3)
    if marker[0] == "`" and "`" in info + tail:
        return None
    language = re.split(r"[,{]", info, maxsplit=1)[0]
    return marker, language, len(line) - len(stripped)


def _closes(line: str, marker: str, indent: int) -> bool:
    """A closing fence: the opening marker's character, at least as long, nothing else, indented at most three
    spaces past the opening fence (loop 3, row 46: a deeper-indented backtick line is code, not the close)."""
    stripped = line.strip()
    leading = len(line) - len(line.lstrip(" "))
    return (
        leading <= indent + 3
        and stripped.startswith(marker[0])
        and set(stripped) == {marker[0]}
        and len(stripped) >= len(marker)
    )


#: One list item: ordered?, the marker's number (1 for a bullet), text, nested items ``(ordered?, number, text)``.
_Item = tuple[bool, int, str, list[tuple[bool, int, str]]]


def _list_html(ordered: bool, start: int, rows: list[str]) -> str:
    tag = "ol" if ordered else "ul"
    attribute = f' start="{start}"' if ordered and start != 1 else ""
    return f"<{tag}{attribute}>" + "".join(rows) + f"</{tag}>"


def render_markdown(
    text: str, *, heading_offset: int = 1, link_base: str | None = None, skip_leading_h1: bool = False
) -> str:
    """A deterministic minimal renderer for ``steps.md`` (review 2026-10-28, row 5; loop 2, row 25; loop 3, rows
    46, 47 and 55).

    Recognised: ATX headings (demoted by ``heading_offset`` levels, so the
    card keeps its one ``h1``; with ``skip_leading_h1`` the text's first line,
    when it is a ``#`` heading, is dropped), fenced code blocks (backtick or
    tilde, an info string, any indent, closed by a fence of the same marker
    indented at most three spaces past the opening), ``-``/``*`` bullet and
    ``1.`` ordered lists (one level of nesting by indent, each level with its
    own tag and an ``<ol>`` carrying ``start`` when its first marker is not
    1; an indented following line continues the item; a fence inside a list
    closes the list), blank-line-separated paragraphs, inline ``code``
    spans, ``**strong**`` and ``[text](url)`` links to ``http(s)`` or
    relative targets, the relative ones prefixed with ``link_base`` (the
    default ``None`` leaves a relative target literal, loop 5, row 81).
    Everything is HTML-escaped first; raw HTML, images, ``//host`` and
    ``/rooted`` links stay literal text. Pure: the same text renders the
    same bytes.
    """
    # a leading tab counts as four columns, so a tab-indented close, nested item or fence behaves like a
    # space-indented one (loop 4, row 68); a tab inside a line, in a fence body or a code span, is emitted as it is
    # (loop 5, row 82: expanding every tab rewrote a Makefile fence)
    raws = text.splitlines()
    lines = [_expand_leading(line) for line in raws]
    if skip_leading_h1:
        first = next((i for i, line in enumerate(lines) if line.strip()), None)
        # the leading title is any level-1 ATX heading, indented or tab-separated, even an empty one (row 67)
        if first is not None and re.fullmatch(r"#(\s+.*)?", lines[first].strip()):
            lines, raws = lines[first + 1 :], raws[first + 1 :]
    out: list[str] = []
    paragraph: list[str] = []
    items: list[_Item] = []

    def inline(part: str) -> str:
        return _inline(part, link_base)

    def flush_paragraph() -> None:
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if not items:
            return
        rows = []
        for _ordered, _number, item, nested in items:
            inner = ""
            # consecutive nested items of one kind form one list; a change of marker starts another (row 68)
            run: list[tuple[bool, int, str]] = []
            for child in nested:
                if run and run[0][0] != child[0]:
                    inner += _list_html(run[0][0], run[0][1], [f"<li>{inline(text)}</li>" for _, _, text in run])
                    run = []
                run.append(child)
            if run:
                inner += _list_html(run[0][0], run[0][1], [f"<li>{inline(text)}</li>" for _, _, text in run])
            rows.append(f"<li>{inline(item)}{inner}</li>")
        out.append(_list_html(items[0][0], items[0][1], rows))
        items.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        opened = _opens(line)
        if opened:
            flush_paragraph()
            flush_list()
            marker, language, indent = opened  # a fence under a list item: its lines lose that indent
            code: list[str] = []
            index += 1
            while index < len(lines) and not _closes(lines[index], marker, indent):
                body, raw = lines[index], raws[index]
                code.append(_dedent_columns(raw, indent) if body[:indent].strip() == "" else raw.lstrip())
                index += 1
            index += 1  # the closing fence, or the end of the text
            attribute = f' class="language-{html.escape(language, quote=True)}"' if language else ""
            out.append(f"<pre><code{attribute}>{html.escape(chr(10).join(code))}\n</code></pre>")
            continue
        heading = _HEADING.match(line)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(len(heading.group(1)) + heading_offset, 6)
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            index += 1
            continue
        bullet, numbered = _BULLET.match(line), _ORDERED.match(line)
        if bullet or numbered:
            flush_paragraph()
            ordered = numbered is not None
            if numbered:
                indent, number, body = len(numbered.group(1)), int(numbered.group(2)), numbered.group(3).strip()
            else:
                assert bullet is not None
                indent, number, body = len(bullet.group(1)), 1, bullet.group(2).strip()
            inner = body
            while nested_marker := (_BULLET.match(inner) or _ORDERED.match(inner)):
                inner = nested_marker.group(nested_marker.re.groups).strip()  # loop 5, row 93: `- - ```bash`
            if _opens(inner):
                # an item whose text is a fence opener is a fence at the text's column (row 68): re-read the line
                # as one, so its closer closes it instead of opening a block that swallows the rest
                lines[index] = " " * (len(line.rstrip()) - len(inner)) + inner
                continue
            if items and indent >= 2:
                items[-1][3].append((ordered, number, body))
            else:
                if items and items[0][0] != ordered:
                    flush_list()
                items.append((ordered, number, body, []))
            index += 1
            continue
        if items and line.startswith("  ") and line.strip():
            ordered, number, body, nested = items[-1]
            if nested:
                child_ordered, child_number, child = nested[-1]
                nested[-1] = (child_ordered, child_number, f"{child} {line.strip()}")
            else:
                items[-1] = (ordered, number, f"{body} {line.strip()}", nested)
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

    Order (the review of 2026-10-28, row 5; loop 2, row 26; loop 5, row 94):
    the header meta lines carry the verified date and the jobs, then what it
    is, Install, Unpublished packages, Steps (``steps.md`` rendered with
    :func:`render_markdown`), Related, Sources, Contribute. The paper
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
            f'The <a href="{REPOSITORY_BLOB_URL}/{TOOL_MATRIX_RELATIVE}">tool matrix</a> marks Claude Code reading '
            "<code>.agents/skills/</code> as uncertain and does not list <code>.claude/skills/</code> for Devin. "
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
            f'the folder copy above is the install until <a href="{REPOSITORY_BLOB_URL}/{MARKETPLACE_ROOT_RELATIVE}/'
            'MANUAL-CHECKLIST.md">Round 0</a> confirms a plugin install exposes the skill.</p>'
        )
    hint = row.get("install_hint")
    if hint:
        bits.append(f"<p>Install hint: {html.escape(str(hint))}</p>")
    notes = _requires_notes(row)
    if notes:
        items = "".join(f"<li>{html.escape(note)}</li>" for note in notes)
        bits.append(f"<h2>Unpublished packages</h2><ul>{items}</ul>")
    if steps_text:
        bits.append("<h2>Steps</h2>")
        # The runbook's own ``#`` (its title, the card's h1 already names the skill) is skipped and the rest demoted
        # one level, so its steps are ``<h3>`` under this one ``<h2>`` (loop 3, row 55); a relative link on a skill's
        # runbook points into the mounted folder beside this card (row 47); the mount ships no other kind's folder,
        # so a module's or agent's relative links stay literal (loop 4, row 58).
        base = f"{row['slug']}/" if row.get("kind") == "skill" else None
        bits.append(render_markdown(steps_text, heading_offset=1, link_base=base, skip_leading_h1=True))
    elif row.get("kind") == "skill":
        bits.append("<h2>Steps</h2><p>This card has no <code>steps.md</code> to render.</p>")
    related = row.get("related") or []
    if isinstance(related, list) and related:
        # a related skill is the sibling card at a known path (loop 4, row 76); anything else stays text
        rendered: list[str] = []
        for item in related:
            match = _RELATED_SKILL.fullmatch(str(item))
            if match:
                target = posixpath.relpath(
                    f"{KIND_DIRS['skill']}/{match.group(1)}/{match.group(2)}.html", posixpath.dirname(href)
                )
                rendered.append(f'<li><a href="{target}">{html.escape(str(item))}</a></li>')
            else:
                rendered.append(f"<li>{html.escape(str(item))}</li>")
        bits.append("<h2>Related</h2><ul>" + "".join(rendered) + "</ul>")
    if row.get("kind") == "skill":
        bits.append(_sources_html(row))  # after the runbook and its siblings (loop 5, row 94)
    lane = _listing_lane(row)
    if lane:
        # The lanes are defined once, in the marketplace README (loop 3, row 55); the card names this listing's and
        # links the definition (loop 4, row 76).
        bits.append(
            f"<h2>Contribute</h2><p>Lane: {html.escape(lane)}. A pull request is the publish path; the lanes are "
            f'defined in the marketplace <a href="{REPOSITORY_BLOB_URL}/{MARKETPLACE_ROOT_RELATIVE}/README.md">README</a>.</p>'
        )
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
    """Every ``skills/<scope>/<slug>/`` directory, sorted; a symlink at any of the three levels is refused before
    anything under it is read (loop 4, row 64: ``is_dir()`` follows links, so ``listing.yaml`` was parsed from
    outside the tree before the validator could refuse the folder)."""
    skills = marketplace / "skills"
    if skills.is_symlink():
        raise MarketplaceIndexError("skills is a symlink; a skill folder is never reached through a link")
    if not skills.is_dir():
        return []
    folders: list[Path] = []
    for scope in sorted(skills.iterdir()):
        if scope.is_symlink():
            raise MarketplaceIndexError(
                f"skills/{scope.name} is a symlink; a skill folder is never reached through a link"
            )
        if not scope.is_dir():
            # loop 5, row 90: a stray between the folders was nobody's (the validator sees inside a folder, the
            # mount skips what is not a folder); only scope directories sit under skills/
            raise MarketplaceIndexError(f"skills/{scope.name} is not a directory; only skill folders sit under skills/")
        for slug in sorted(scope.iterdir()):
            if slug.is_symlink():
                raise MarketplaceIndexError(
                    f"skills/{scope.name}/{slug.name} is a symlink; a skill folder is never reached through a link"
                )
            if not slug.is_dir():
                raise MarketplaceIndexError(
                    f"skills/{scope.name}/{slug.name} is not a directory; only skill folders sit under skills/{scope.name}/"
                )
            folders.append(slug)
    return folders


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
        row = _load_yaml(path)
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


def _generated_site_inventory(site_dir: Path) -> set[str] | None:
    """The files a tree this module wrote may hold, read from its ``listings.json`` (review loop 2, row 22; loop 3,
    row 45): the three documents plus one card per listing of that file. ``None`` when there is no such file, it is
    not JSON, or its schema is not this module's."""
    listings = site_dir / "listings.json"
    if listings.is_symlink() or not listings.is_file():
        return None
    try:
        payload = json.loads(listings.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != SCHEMA_ID
        or not isinstance(payload.get("listings"), list)
    ):
        return None
    inventory = {"index.html", "listings.json", "marketplace.json"}
    for row in payload["listings"]:
        if not isinstance(row, dict) or not isinstance(row.get("kind"), str) or row["kind"] not in KIND_DIRS:
            return None
        # the marker's rows are held to the slug grammar (loop 4, row 62): a crafted scope of "x/y" would otherwise
        # account for any card-shaped file under a kind directory
        leaf = row.get("slug") if row.get("slug") is not None else row.get("name")
        if not isinstance(leaf, str) or not SLUG.fullmatch(leaf):
            return None
        if row["kind"] == "skill" and (not isinstance(row.get("scope"), str) or not SLUG.fullmatch(row["scope"])):
            return None
        inventory.add(_card_href(row))
    return inventory


def _check_generated_site(site_dir: Path) -> None:
    """Refuse to replace ``site_dir`` unless every entry in it is one a render of its own ``listings.json`` produces:
    the marker alone is not ownership (loop 3, row 45: ``precious.txt`` beside a marker was deleted)."""
    inventory = _generated_site_inventory(site_dir)
    if inventory is None:
        raise MarketplaceIndexError(
            f"site directory {site_dir} is not a generated site (no listings.json with schema {SCHEMA_ID}); "
            "refusing to replace it"
        )
    # a directory is one of ours only when an inventory path sits under it (row 62: an empty stray directory was
    # removed silently)
    ancestors = {
        "/".join(posixpath.dirname(item).split("/")[: n + 1]) for item in inventory for n in range(item.count("/"))
    }
    foreign = sorted(
        path.relative_to(site_dir).as_posix() + ("/" if path.is_dir() and not path.is_symlink() else "")
        for path in site_dir.rglob("*")
        if path.is_symlink()
        or (path.is_dir() and path.relative_to(site_dir).as_posix() not in ancestors)
        or (not path.is_dir() and path.relative_to(site_dir).as_posix() not in inventory)
    )
    if foreign:
        raise MarketplaceIndexError(
            f"site directory {site_dir} holds files no render of its listings.json produces "
            f"({', '.join(foreign)}); refusing to replace it"
        )


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
    dropped or renamed does not survive (review 2026-10-28, row 4). A
    non-empty ``site_dir`` is replaced only when every file in it is one its
    own ``listings.json`` accounts for (loop 2, row 22; loop 3, row 45).
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
        if any(site_dir.iterdir()):
            _check_generated_site(site_dir)
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


def _contained_dest(root: Path, dest: Path, what: str) -> None:
    """A manifest under ``root`` is written only where no symlink stands between ``root`` and it and its parent
    resolves inside the tree (loop 4, row 65: ``root/.agents -> /elsewhere`` took the Codex manifest outside the
    marketplace while the returned path was the in-tree one). A ``dest`` outside ``root`` is the caller's. Both
    sides are normalised lexically first (loop 5, row 85: a relative ``root`` with an absolute ``dest`` made
    ``relative_to`` raise and the check return, and ``root/../x`` was read as inside the tree), and the parent's
    resolution is judged whether or not it exists yet."""
    root_abs = Path(os.path.abspath(root))
    dest_abs = Path(os.path.abspath(dest))
    try:
        relative = dest_abs.relative_to(root_abs)
    except ValueError:
        return
    probe = root_abs
    for part in relative.parts:
        probe = probe / part
        if probe.is_symlink():
            raise MarketplaceIndexError(
                f"{what}: {probe.relative_to(root_abs).as_posix()} is a symlink; refusing to write through it"
            )
    if not dest_abs.parent.resolve().is_relative_to(root_abs.resolve()):
        raise MarketplaceIndexError(f"{what}: {relative.as_posix()} resolves outside the marketplace")


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
    _contained_dest(index_path.parent, dest, "manifest")
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
    text = render_codex_marketplace(rows)
    _contained_dest(index_path.parent, dest, "Codex manifest")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
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
    tree = cutover_root.resolve_flags_path(None)
    if tree is None:
        # Off plus no mount is a valid pages-check state, so a silent 0 would drop /marketplace/ from a deploy
        # with a green workflow (review loop 2, row 37).
        sys.stderr.write(
            f"{FLAG_KEY}: no flag tree found (set PYFORGE_FLAGS_PATH or run from the repository root, whose "
            "src/platform/config/flags.json is the tree); refusing to print a build line\n"
        )
        return 2
    # The same silent 0 through read_boolean's WARN-and-default on a tree that resolves but is unreadable, not
    # JSON or missing the key (loop 3, row 53): the key must be declared before a line is printed.
    try:
        document = json.loads(Path(tree).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.stderr.write(
            f"{FLAG_KEY}: {tree} is not a readable JSON flag tree ({exc}); refusing to print a build line\n"
        )
        return 2
    flags = document.get("flags") if isinstance(document, dict) else None
    if not isinstance(flags, dict) or FLAG_KEY not in flags:
        sys.stderr.write(f"{FLAG_KEY}: {tree} declares no such flag; refusing to print a build line\n")
        return 2
    # A declared entry read_boolean would still default on (loop 4, row 63): not a mapping, no variants mapping,
    # a defaultVariant naming no bool, no metadata object (check_metadata raises on that one). Every variant must
    # be a bool, not only the default one (loop 5, row 87: the overlay selects the variant the build reads).
    entry = flags[FLAG_KEY]
    variants = entry.get("variants") if isinstance(entry, dict) else None
    chosen = entry.get("defaultVariant") if isinstance(entry, dict) else None
    if (
        not isinstance(entry, dict)
        or not isinstance(variants, dict)
        or not variants
        or not all(isinstance(value, bool) for value in variants.values())
        or not isinstance(chosen, str)
        or chosen not in variants
        or not isinstance(entry.get("metadata"), dict)
    ):
        sys.stderr.write(
            f"{FLAG_KEY}: {tree} declares the flag with a shape the reader would default on (it needs a variants "
            "mapping of bools, a defaultVariant naming one of them and a metadata object); refusing to print a "
            "build line\n"
        )
        return 2
    if overlays_path_for(tree) is None:
        # The environment's value lives in the overlay (dev is on there and nowhere else); a tree with no overlay
        # file beside it reads the base default and prints 0 with exit 0 (row 87).
        sys.stderr.write(
            f"{FLAG_KEY}: no flag-overlays.json beside {tree} (the build line's value is the overlay's); refusing "
            "to print a build line\n"
        )
        return 2
    try:
        enabled = pages_enabled()
    except FlagConfigError as exc:  # an overlay or metadata the reader refuses: never a defaulted line
        sys.stderr.write(f"{FLAG_KEY}: {exc}; refusing to print a build line\n")
        return 2
    sys.stdout.write(f"{FLAG_ENV}={'1' if enabled else '0'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
