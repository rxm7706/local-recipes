"""Generic feed cache-dir resolution, staleness math, and ``FeedProvenance``
construction (Story 6.4) — the shared substrate every Epic 6 feed-backed
axis builds on: CISA KEV now, currency (6.3) and EPSS (6.7) reuse it
unchanged. Deliberately KEV-agnostic in every name except the one function
that resolves the KEV file's own on-disk path (``kev_cache_path``) — a
later feed adds its own ``<feed>_cache_path`` sibling, never a rename of
this module's generic surface.

Ownership decisions recorded:

* ``PYFORGE_WARDEN_FEED_CACHE_DIR`` is THIS project's OWN env var — unlike
  ``vuln.py``'s ``OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`` (osv-scanner's
  own), no upstream tool defines or reads it. Mirrors ``vuln.
  resolve_cache_dir``'s shape exactly: an unset/empty env var resolves to
  ``None`` — v1 has NO implicit default (no per-user cache guess).
* ``is_feed_stale`` generalizes ``vuln.is_db_stale``'s exact staleness
  rule (decision record § 2, Story 2.5) to any feed, not just the OSV DB:
  stale = ``snapshot_at`` STRICTLY older than ``now - max_age_days``
  (exactly-at-the-boundary is NOT stale — a non-strict inequality would
  false-positive the boundary case); a future-dated ``snapshot_at`` (clock
  skew) is ALSO stale, never "fresh"; a missing, unparsable, or naive (no
  UTC offset) timestamp degrades to stale (never fresh, never raises).
  ``feeds.py`` owns this math so no axis (this story's KEV, or a later
  currency/EPSS producer) computes its own staleness rule.
* ``DEFAULT_FEED_MAX_AGE_DAYS = 7`` mirrors ``vuln.DB_MAX_AGE_DAYS`` — a
  hardcoded ceiling shared by every feed this module resolves, until a
  config surface is asked for one (no Epic 6 story adds one yet).
* ``load_kev_catalog`` distinguishes "no usable feed" (``None`` — missing
  file, unreadable, not valid JSON, wrong top-level shape) from "feed
  present but genuinely empty" (``{}`` — a freshly-provisioned catalog
  with zero entries, e.g. the ambient test fixture) — collapsing the two
  would make an empty-but-fresh feed indistinguishable from an absent one,
  which is exactly the distinction Story 6.4's ambient conftest fixture
  needs (present + fresh + zero entries, never "absent"). Per-entry
  tolerant: a malformed vulnerability entry (missing/non-string
  ``cveID``/``dateAdded``) is skipped, never aborts the load of the rest
  (mirrors ``vuln.py``'s per-entry tolerance throughout).
* ``write_kev_cache`` is the ONE writer both ``scripts/refresh_kev_feed.py``
  (the real, opt-in-online provisioning path) and the test suite's ambient
  fixture (``conftest.py``) share — a second, hand-rolled writer in either
  caller could silently drift from the on-disk shape ``load_kev_catalog``
  reads. Atomic (temp file in the SAME directory, then ``os.replace``) so a
  reader never observes a partially-written cache file.

This module reads/writes JSON as DATA: no subprocess, no network, no exec.
The online fetch that POPULATES this cache lives entirely outside the
installed package (``scripts/refresh_kev_feed.py``) — see that script's own
docstring for why (NFR-S2: the ``scan`` runtime path opens no socket at any
point).
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import FeedProvenance

# This project's OWN cache-root env var (no implicit default — mirrors
# vuln.OSV_DB_CACHE_ENV_VAR's "no per-user guess" posture).
FEED_CACHE_DIR_ENV_VAR = "PYFORGE_WARDEN_FEED_CACHE_DIR"

# Mirrors vuln.DB_MAX_AGE_DAYS: a config surface (a future `--feed-max-age`
# or TOML key) is a later story's, never this one's.
DEFAULT_FEED_MAX_AGE_DAYS = 7

# The CISA KEV feed's own subdirectory + filename under the shared cache
# root: <cache_dir>/kev/known_exploited_vulnerabilities.json.
_KEV_FEED_DIR_NAME = "kev"
_KEV_FEED_FILENAME = "known_exploited_vulnerabilities.json"


def resolve_cache_dir(*, env: Mapping[str, str] | None = None) -> str | None:
    """Resolve ``$PYFORGE_WARDEN_FEED_CACHE_DIR`` — ``None`` when unset or
    empty (no implicit default). ``env`` is an optional injected mapping
    for tests; production callers omit it and read the real process
    environment."""
    source = env if env is not None else os.environ
    cache_dir = source.get(FEED_CACHE_DIR_ENV_VAR)
    return cache_dir if cache_dir else None


def kev_cache_path(cache_dir: str | Path) -> Path:
    """The on-disk KEV cache path under ``cache_dir``:
    ``<cache_dir>/kev/known_exploited_vulnerabilities.json`` — both
    ``scripts/refresh_kev_feed.py`` (writer) and ``vuln.py``'s KEV
    consultation (reader) resolve through this one helper, so the two
    never drift apart on layout."""
    return Path(cache_dir) / _KEV_FEED_DIR_NAME / _KEV_FEED_FILENAME


def feed_snapshot_at(path: Path) -> str:
    """A feed file's own filesystem mtime, ISO-8601 UTC — mirrors
    ``vuln.db_snapshot_at``'s honest snapshot signal: no separate
    provisioning-time metadata file, the file's own mtime IS the
    snapshot."""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def is_feed_stale(snapshot_at: str | None, max_age_days: int, *, now: datetime) -> bool:
    """Generalizes ``vuln.is_db_stale``'s exact staleness rule to any feed
    (see module docstring). Degrades conservatively on anything unparsable
    or unexpected: never fresh, never raises."""
    if snapshot_at is None:
        return True
    try:
        parsed = datetime.fromisoformat(snapshot_at)
    except ValueError:
        return True
    if parsed.tzinfo is None:
        return True
    age = now - parsed
    if age < timedelta(0):
        return True  # future-dated: clock skew, never "fresh"
    return age > timedelta(days=max_age_days)


def feed_provenance(
    *, source: str, path: Path, max_age_days: int, now: datetime
) -> FeedProvenance:
    """Build one ``FeedProvenance`` for a feed that WAS actually consulted
    (the file exists and was read) — ``snapshot_at``/``max_age_ok`` derived
    from ``path``'s own mtime via ``is_feed_stale``. A caller that never
    even opened the feed (an absent cache) constructs
    ``FeedProvenance(None, None, None)`` directly instead of calling this
    helper — it exists for the "we read it" path only."""
    snapshot_at = feed_snapshot_at(path)
    stale = is_feed_stale(snapshot_at, max_age_days, now=now)
    return FeedProvenance(source=source, snapshot_at=snapshot_at, max_age_ok=not stale)


def load_kev_catalog(path: Path) -> dict[str, str] | None:
    """Load the CISA KEV catalog JSON into a ``{cve_id: dateAdded}`` dict.

    ``None`` on anything that prevents a trustworthy read (missing file,
    unreadable, not valid JSON, a top level that is not a JSON object, or a
    ``vulnerabilities`` key that is not a list) — distinct from a present-
    but-empty catalog (``{}``, see module docstring). An entry lacking a
    non-empty string ``cveID`` OR a non-empty string ``dateAdded`` is
    skipped (never partially trusted) — this codebase's established
    tolerant-per-entry convention (mirrors ``vuln._is_valid_osv_advisory``:
    one malformed entry never aborts the load of the rest)."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(document, dict):
        return None
    vulnerabilities = document.get("vulnerabilities")
    if not isinstance(vulnerabilities, list):
        return None
    catalog: dict[str, str] = {}
    for entry in vulnerabilities:
        if not isinstance(entry, dict):
            continue
        cve_id = entry.get("cveID")
        date_added = entry.get("dateAdded")
        if (
            isinstance(cve_id, str)
            and cve_id
            and isinstance(date_added, str)
            and date_added
        ):
            catalog[cve_id] = date_added
    return catalog


def write_kev_cache(cache_dir: str | Path, document: Mapping[str, object]) -> Path:
    """Atomically write ``document`` (the full CISA KEV JSON payload — the
    SAME on-disk shape ``load_kev_catalog`` reads back, not just the
    extracted catalog) to ``kev_cache_path(cache_dir)``. Creates the parent
    directory if needed. Write-to-temp-in-the-same-directory then
    ``os.replace`` — the replace is atomic on every POSIX/NTFS filesystem,
    so a concurrent reader never observes a partially-written file. The
    sole writer both ``scripts/refresh_kev_feed.py`` and the test suite's
    ambient fixture share (see module docstring)."""
    target = kev_cache_path(cache_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp_name = tempfile.mkstemp(
        dir=target.parent, prefix=f".{_KEV_FEED_FILENAME}-", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            json.dump(document, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return target
