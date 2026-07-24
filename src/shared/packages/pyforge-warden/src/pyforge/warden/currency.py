"""Per-component + Python-runtime currency verdicts and the currency-axis
warn-cap (Story 6.3, axis ``"currency"``).

This module turns each component (and the running Python interpreter) into
an honest ``supported``/``eol``/``unknown`` :class:`~pyforge.warden.models.
CurrencyVerdict` (FR34) via a tiered resolution ladder and emits
``currency:<reason>:<subject>@<ver>`` ``Finding``s for the ``eol``/
``over-lag``/``unknown`` reason tokens only — never for a fully-current
(``supported``, zero lag) resolution. Mirrors ``license.py``'s shape file-
for-file wherever the shapes coincide (module docstring style, hard-cap rung
function, ``DEFAULT_*_POLICY`` unused-this-story constant, "one function
computes the whole axis's findings"). It NEVER projects an exit code and
NEVER spells the verdict lattice order — ``currency_rung`` produces a
``(Status, StatusDriver)`` rung the sole owner (``verdict.py``) later
projects.

Tier ladder (FR34), edge mode only (no fleet-mode N/N-1 conda-channel-data
tier — out of scope, Boundaries):

1. **``lts-registry``** — the bundled ``data/lts-registry.yaml`` (loaded
   ONCE per process via ``importlib.resources``, name/alias-indexed
   case-insensitively). Only a product entry carrying its own ``lts_lines``
   (the ``source: manual`` shape — per the registry's own header,
   ``lts_lines`` is manual-only) resolves fully offline at this tier; a
   ``source: endoflife`` entry (slug map only, per the registry's own
   header) has no per-version data of its own and routes to tier 2 via its
   ``slug``, and a ``source: heuristic-seed`` entry is a labeled signal
   that carries neither ``lts_lines`` nor (necessarily) a slug — it
   resolves only as far as its (possibly null) slug can route it.
2. **``endoflife-date``** — the cached endoflife.date snapshot
   (``feeds.py``'s ``endoflife_cache_path``/``load_endoflife_snapshot``,
   populated ONLY by ``scripts/refresh_endoflife_feed.py``, never fetched
   here), keyed by the registry's ``slug`` when tier 1 routed here, or by
   the component's own (normalized) name when no registry entry matched at
   all.
3. **``unknown``** — nothing resolves; a WARN-capped ``Finding`` is still
   emitted (never a silent gap).

Ownership decisions recorded:

* ``currency_rung`` is a HARD ``Status.WARN`` cap — it NEVER consults
  ``config.currency_policy`` and NEVER escalates. Real ``eol``/``over-lag``
  -> ``policy-violation`` / ``unknown`` -> ``indeterminate`` escalation is
  Story 6.5's sole ownership (Boundaries); ``tests/conformance/
  test_axis_producer_ceiling.py`` mechanically pins this ceiling.
* Reason-token precedence is the pinned 3-way total order (decision record
  § 2): ``eol`` > ``over-lag`` > ``unknown``. A resolution whose matched
  tier entry is past its EOL date always reports ``eol``, even when it is
  ALSO behind the latest entry (``lag`` still populated on the Finding for
  transparency). ``over-lag`` fires for a NOT-yet-EOL resolution with
  ``lag > 0`` (behind the latest known entry by ANY positive count — this
  story does no threshold comparison against ``--max-lag``; that numeric
  gate is Story 6.5's additive escalation input, per the decision record
  § 3). A resolution with ``lag == 0`` and not EOL is fully current — no
  ``Finding`` at all (mirrors ``license.py``'s ``allowed``-emits-nothing
  rule). ``unknown`` is the floor: nothing on the ladder resolved.
* ``lag`` is an integer count of entries (LTS lines / endoflife.date
  cycles) released strictly after the matched one — ``releases-behind-
  latest``, never calendar time (``max_age_ok`` owns that axis). Both tiers
  compute it identically (a count over the same tier's own entry list); the
  decision record's "approximation, not exact" language describes tier 2's
  cycle-vs-individual-release granularity, not a difference in this
  module's own counting method.
* The Python runtime is ALWAYS put through the SAME resolution ladder as
  any component (``sys.version_info`` as its own ``!python-runtime``-
  subject ``version``, looked up as product name ``"python"``) — "always
  assessed" (FR34) means always RESOLVED, not always Finding-emitting: a
  fully-current runtime resolution emits nothing, exactly like any other
  clean component (Boundaries: ``!python-runtime`` is the id `subject`
  segment, distinct from the report-section field name ``runtime_python``
  the frozen 6.1 schema does not actually carry — see the "schema
  Block-If" note below).
* **Registry freshness gates tier-1's curated JUDGMENT data, not its
  routing metadata** (NFR-S9: "a stale registry never silently reports
  supported"). The registry's own ``updated:`` date (not file mtime — a
  git-checkout artifact, never a meaningful "when was this curated" signal)
  is checked against a 180-day default max-age via ``feeds.is_feed_stale``
  (reused verbatim, per Boundaries). When stale (or unparsable), a matched
  product's own ``lts_lines`` (the curated EOL/LTS judgment data tier 1
  exists to serve) are NOT consulted — resolution falls through to tier
  2/unknown for that data — which is the most literal way to guarantee a
  stale registry can never silently report ``supported`` from data that
  itself might be stale. A matched product's ``slug`` (the alias/name ->
  endoflife.date-slug ROUTING metadata, consulted in ``_resolve``
  unconditionally, regardless of ``registry_fresh``) is deliberately NOT
  gated by this same check: routing metadata is not itself a freshness-
  sensitive concept the way a curated EOL date is — it maps a product name
  to where its per-version data lives, and that mapping does not go stale
  merely because the registry file hasn't been refreshed recently. The
  endoflife.date CACHE's own freshness (via the SAME ``feeds.
  is_feed_stale``/``feed_provenance`` helpers) gates tier-2 use identically
  (stale/absent cache -> tier 2 skipped -> degrades toward ``unknown``),
  mirroring the I/O matrix's "endoflife cache absent/stale" row, which
  groups the two conditions into the same "no tier resolves" outcome.
* **Schema-shape judgment call (documented, not a Block-If gap):** the
  frozen 6.1 ``CurrencyInfo`` sub-object carries no ``snapshot_at``/
  ``max_age_ok`` fields of its own (only the axis-level
  ``ComplianceReport.currency_data: FeedProvenance | None`` slot does, one
  slot, mirroring ``kev_data``'s singular shape) — so "every bundled-
  registry-derived verdict carries snapshot_at + max_age_ok" (Boundaries)
  is satisfied at the REPORT level, not per-``Finding``: ``currency_data``
  reports the BUNDLED REGISTRY's own provenance (the NFR-S9 concern the
  Boundaries text repeatedly names explicitly), not the endoflife.date
  cache's — the cache's own staleness is still computed via the SAME
  ``feeds.py`` helpers (Boundaries: "reuses feeds.py's ... helpers
  verbatim") and gates tier-2 resolution, but has no separate report-level
  slot of its own (there is exactly one ``currency_data`` field to fill).
  This is a considered design decision, not evidence the 6.1 schema is
  incomplete — see the story's Dev Notes for the full rationale.
* ``DEFAULT_CURRENCY_POLICY`` is declared but UNUSED this story (mirrors
  ``license.DEFAULT_LICENSE_POLICY``'s module-default-table precedent) —
  reserved for Story 6.5's real escalation; ``currency_rung`` never reads
  it. Only the two verdicts that can ANCHOR a Finding on their own
  (``eol``/``unknown``) are keyed — ``supported`` is deliberately absent
  (mirrors ``license``'s omission of ``allowed``): a ``supported`` verdict
  can mean either "fully current" (no Finding at all) or "over-lag but not
  EOL" (a Finding DOES exist), a distinction this table cannot itself make
  by verdict alone — Story 6.5's escalation reads the id's reason segment
  (or ``Finding.currency.lag``) for that, per the decision record § 3.
* This module opens no socket and spawns no subprocess: the bundled
  registry is a packaged resource read in-process, and the endoflife.date
  cache is a local file read in-process (populated OFFLINE by ``scripts/
  refresh_endoflife_feed.py`` only) — both fully offline.
* Known residual gotcha (bounded to FOREIGN caches): endoflife.date's real
  API sometimes emits a cycle's ``cycle`` value as a bare JSON NUMBER
  rather than a string (e.g. ``3.1``); ``str(3.10)`` == ``"3.1"`` in
  Python (trailing-zero float truncation), so a numeric cycle value can
  misrepresent a real "3.10" line. ``scripts/refresh_endoflife_feed.py``
  parses API responses with ``parse_float=str``/``parse_int=str`` so a
  snapshot IT provisions preserves the lexical form (``"3.10"`` stays
  ``"3.10"``) — the truncation can therefore only reach this module via a
  hand-built or third-party cache document. This module keeps the ``str()``
  coercion for robustness against exactly those, without special-casing
  the (now writer-side-solved) ambiguity.

This module parses YAML/JSON as DATA: no subprocess, no network, no exec.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from functools import lru_cache
from importlib import resources
from types import MappingProxyType
from typing import NamedTuple

import yaml

from . import feeds
from .interfaces import _sanitize_id_segment
from .inventory import Component
from .models import (
    AXIS_CURRENCY,
    CurrencyInfo,
    CurrencyVerdict,
    FeedProvenance,
    Finding,
    Status,
    StatusDriver,
)

# The reserved sentinel subject for the Python-runtime finding (decision
# record § 2) — "!" is not a legal character in any PyPI or conda package
# name, so this token is structurally uncollidable with a real dependency.
_PYTHON_RUNTIME_SUBJECT = "!python-runtime"

# NFR-S9's default bundled-registry max-age.
_REGISTRY_MAX_AGE_DAYS = 180

# A stable, deterministic identity for the bundled registry's own
# FeedProvenance.source — NOT a filesystem path (which would vary by
# install location/method), matching this module's own determinism
# constraints (NFR-R3b).
_REGISTRY_SOURCE = "pyforge.warden/data/lts-registry.yaml"

# The default currency policy: CurrencyVerdict -> Status. UNUSED this story
# (currency_rung is a hard warn-cap, oblivious to this table) -- reserved
# for Story 6.5's real escalation. MappingProxyType-wrapped, mirroring
# DEFAULT_LICENSE_POLICY/DEFAULT_HYGIENE_POLICY/DEFAULT_VULN_SEVERITY_POLICY.
DEFAULT_CURRENCY_POLICY: MappingProxyType[CurrencyVerdict, Status] = MappingProxyType(
    {
        CurrencyVerdict.EOL: Status.WARN,
        CurrencyVerdict.UNKNOWN: Status.WARN,
    }
)


def currency_rung(finding: Finding) -> tuple[Status, StatusDriver]:
    """Derive the ``(Status, StatusDriver)`` rung for one currency-axis
    finding — UNCONDITIONALLY ``Status.WARN`` (Boundaries: never consult
    ``config.currency_policy``, never escalate — real escalation is Story
    6.5's sole ownership). The driver carries the finding's own axis and
    id."""
    return (
        Status.WARN,
        StatusDriver(axis=finding.axis, finding_id=finding.id),
    )


def _normalize_name(name: str) -> str:
    """Case/separator-insensitive product-name normalization (conda/PyPI
    names commonly vary by casing and ``-``/``_``) — applied identically to
    a component's own name, every registry alias, and every endoflife.date
    cache key so all three compare on the same footing."""
    return name.strip().lower().replace("_", "-")


# --- bundled LTS registry (importlib.resources; tier 1) ----------------------


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, object]:
    """Load + parse the bundled ``data/lts-registry.yaml`` ONCE per process
    — ``{}`` on any read/parse failure (never raises; every lookup then
    degrades to the next tier, exactly like an absent file). ``yaml.
    safe_load`` only (NFR-S1) — this is trusted, packaged data, not
    untrusted input, but the loader stays the same hardened primitive every
    other YAML read in this package uses."""
    try:
        raw = (
            resources.files("pyforge.warden") / "data" / "lts-registry.yaml"
        ).read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        document = yaml.safe_load(raw)
    except yaml.YAMLError:
        return {}
    return document if isinstance(document, dict) else {}


def _registry_products(document: Mapping[str, object]) -> dict[str, object]:
    products = document.get("products")
    return products if isinstance(products, dict) else {}


def _registry_alias_index(products: Mapping[str, object]) -> dict[str, str]:
    """``{normalized-name-or-alias: product-key}`` over every registry
    product's own key AND its ``aliases`` list — the case/separator-
    insensitive lookup table ``_resolve`` consults.

    Raises ``ValueError`` when two DIFFERENT products normalize to the same
    key/alias — a malformed bundled registry (a packaged-data integrity bug,
    never a runtime input problem) that would otherwise silently misroute
    one product's lookups to the other's data. Fails loudly rather than
    degrading — and fails on EVERY call: only the raw YAML load
    (``_load_registry``) is cached, the index itself is rebuilt each
    ``currency_findings`` run, so a collision surfaces as an
    ``engine-execution-failed`` record on every scan until the packaged
    data is fixed (cheap — the registry is small by design)."""
    index: dict[str, str] = {}

    def _add(normalized: str, key: str) -> None:
        existing = index.get(normalized)
        if existing is not None and existing != key:
            raise ValueError(
                f"lts-registry.yaml: {normalized!r} is claimed by both "
                f"{existing!r} and {key!r} — an alias/name collision "
                "would silently misroute currency lookups"
            )
        index[normalized] = key

    for key, entry in products.items():
        if not isinstance(key, str) or not isinstance(entry, dict):
            continue
        _add(_normalize_name(key), key)
        aliases = entry.get("aliases")
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str) and alias:
                    _add(_normalize_name(alias), key)
    return index


def _registry_feed_provenance(
    document: Mapping[str, object], *, now: datetime
) -> FeedProvenance | None:
    """The bundled registry's own ``FeedProvenance`` (see module docstring's
    schema-shape judgment call): ``snapshot_at`` derives from the registry's
    OWN declared ``updated:`` field (a curated date, not a git-checkout file
    mtime), staleness via ``feeds.is_feed_stale`` reused verbatim against a
    180-day default max-age (NFR-S9). ``None`` when ``updated:`` is absent
    or unparsable — the registry is then treated as unusable for provenance
    AND for tier-1 resolution (see ``currency_findings``)."""
    updated = document.get("updated")
    if isinstance(updated, datetime):
        snapshot_dt = updated if updated.tzinfo is not None else updated.replace(tzinfo=UTC)
    elif isinstance(updated, date):
        snapshot_dt = datetime(updated.year, updated.month, updated.day, tzinfo=UTC)
    elif isinstance(updated, str):
        try:
            parsed = datetime.fromisoformat(updated)
        except ValueError:
            return None
        snapshot_dt = parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    else:
        return None
    snapshot_at = snapshot_dt.isoformat()
    stale = feeds.is_feed_stale(snapshot_at, _REGISTRY_MAX_AGE_DAYS, now=now)
    return FeedProvenance(source=_REGISTRY_SOURCE, snapshot_at=snapshot_at, max_age_ok=not stale)


# --- tier resolution -----------------------------------------------------


class _Resolution(NamedTuple):
    """One tier's resolved verdict + provenance for one component/runtime
    lookup — never constructed for an unresolvable lookup (``None`` is used
    instead, see ``_resolve``)."""

    tier: str
    verdict: CurrencyVerdict
    latest: str | None
    lag: int | None
    eol_date: str | None


def _as_date(value: object) -> date | None:
    """Accepts a PyYAML-parsed ``date``/``datetime`` OR an ISO-8601 date
    string (the endoflife.date JSON shape) — ``None`` for anything else or
    unparsable, never raises."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _best_match(entries: Sequence[tuple[str, date, object]], version: str) -> int | None:
    """The index of the entry whose leading identifier (an LTS ``line`` or
    an endoflife.date ``cycle``) is the LONGEST exact-or-prefix match
    against ``version`` (``version == identifier`` or ``version.
    startswith(identifier + ".")``) — the longest match wins so a more
    specific identifier (``"6.1"``) is preferred over a less specific one
    (``"6"``) when both would otherwise match. On an exact length tie
    between two matching identifiers, the first one encountered in
    ``entries`` wins (a strict ``>`` comparison, never ``>=``) — both
    callers pass ``entries`` pre-sorted ascending by release date, so this
    means the OLDER (earlier-released) of the two tied identifiers wins.
    ``None`` when nothing matches."""
    best_index: int | None = None
    best_length = -1
    for index, entry in enumerate(entries):
        identifier = entry[0]
        if version == identifier or version.startswith(identifier + "."):
            if len(identifier) > best_length:
                best_index = index
                best_length = len(identifier)
    return best_index


def _resolve_from_lines(
    lines: Sequence[object], version: str, *, now: datetime
) -> _Resolution | None:
    """Tier 1: resolve against a registry product's own ``lts_lines`` (fully
    self-contained — no endoflife.date consultation needed). ``None`` when
    no line's identifier prefix-matches ``version``, or when the line list
    carries no usable (line/released/eol all present) entry at all."""
    parsed: list[tuple[str, date, date]] = []
    for entry in lines:
        if not isinstance(entry, dict):
            continue
        identifier = entry.get("line")
        released = _as_date(entry.get("released"))
        eol = _as_date(entry.get("eol"))
        if not isinstance(identifier, str) or not identifier or released is None or eol is None:
            continue
        parsed.append((identifier, released, eol))
    if not parsed:
        return None
    parsed.sort(key=lambda item: item[1])  # ascending by released date
    match_index = _best_match(parsed, version)
    if match_index is None:
        return None
    _matched_identifier, matched_released, matched_eol = parsed[match_index]
    newest_identifier = parsed[-1][0]
    lag = sum(1 for _, released, _ in parsed if released > matched_released)
    verdict = (
        CurrencyVerdict.EOL if matched_eol <= now.date() else CurrencyVerdict.SUPPORTED
    )
    return _Resolution(
        tier="lts-registry",
        verdict=verdict,
        latest=newest_identifier,
        lag=lag,
        eol_date=matched_eol.isoformat(),
    )


def _resolve_from_cycles(
    cycles: Sequence[object], version: str, *, now: datetime
) -> _Resolution | None:
    """Tier 2: resolve against a cached endoflife.date cycle array. ``None``
    when no cycle's identifier prefix-matches ``version``, the cycle list
    carries no usable entry, or the matched cycle's own ``eol`` value is
    unusable (never guess a resolution the payload can't honestly support —
    degrades this component to the next tier/unknown rather than
    fabricating an eol_date).

    endoflife.date's documented BOOLEAN ``eol`` shapes (review finding,
    2026-07-23) are honored as far as the frozen 6.1 schema permits:
    ``eol: false`` on a FULLY CURRENT match (lag 0) is an explicit
    still-supported assertion — resolves ``supported`` with
    ``eol_date=None``, which is expressible because a fully-current
    resolution emits no ``Finding`` at all (previously this noised into
    ``unknown``). ``eol: true`` (already-EOL, no date published) and
    ``eol: false`` on a BEHIND match would need a ``currency:eol``/
    ``currency:over-lag`` ``Finding`` with ``eol_date=None`` — the frozen
    6.1 model invariant requires non-null ``latest``/``lag``/``eol_date``
    on both reasons, so those stay degraded to ``None``/unknown rather
    than fabricating a date (schema-blocked; ledger entry 2026-07-23)."""
    parsed: list[tuple[str, date, object, str]] = []
    for entry in cycles:
        if not isinstance(entry, dict):
            continue
        cycle = entry.get("cycle")
        if not isinstance(cycle, (str, int, float)) or isinstance(cycle, bool):
            continue
        cycle_str = str(cycle)
        if not cycle_str:
            continue
        release_date = _as_date(entry.get("releaseDate"))
        if release_date is None:
            continue
        eol = entry.get("eol")
        eol_value: object
        if isinstance(eol, bool):
            eol_value = eol
        elif isinstance(eol, str) and eol:
            eol_value = eol
        else:
            eol_value = None
        latest = entry.get("latest")
        latest_str = latest if isinstance(latest, str) and latest else cycle_str
        parsed.append((cycle_str, release_date, eol_value, latest_str))
    if not parsed:
        return None
    parsed.sort(key=lambda item: item[1])  # ascending by release date
    match_index = _best_match(parsed, version)
    if match_index is None:
        return None
    _matched_cycle, matched_release, matched_eol, _matched_latest = parsed[match_index]
    if matched_eol is None:
        return None
    newest_latest = parsed[-1][3]
    lag = sum(1 for _, release_date, _, _ in parsed if release_date > matched_release)
    eol_date_iso: str | None
    if isinstance(matched_eol, bool):
        if matched_eol or lag:
            # A dateless already-EOL (`eol: true`) or a dateless BEHIND
            # match would need an eol/over-lag Finding with eol_date=None,
            # which the frozen 6.1 model invariant forbids -- degrade to
            # unknown rather than fabricate a date (see docstring).
            return None
        verdict = CurrencyVerdict.SUPPORTED
        eol_date_iso = None
    else:
        matched_eol_date = _as_date(matched_eol)
        if matched_eol_date is None:
            return None
        verdict = (
            CurrencyVerdict.EOL
            if matched_eol_date <= now.date()
            else CurrencyVerdict.SUPPORTED
        )
        eol_date_iso = matched_eol_date.isoformat()
    return _Resolution(
        tier="endoflife-date",
        verdict=verdict,
        latest=newest_latest,
        lag=lag,
        eol_date=eol_date_iso,
    )


def _resolve(
    name: str,
    version: str,
    *,
    products: Mapping[str, object],
    alias_index: Mapping[str, str],
    registry_fresh: bool,
    endoflife_snapshot: Mapping[str, list] | None,
    endoflife_fresh: bool,
    now: datetime,
) -> _Resolution | None:
    """The full tier ladder for one (name, version) lookup — a registry
    match's own ``lts_lines`` (tier 1, gated on ``registry_fresh``) first,
    then the endoflife.date cache (tier 2, gated on ``endoflife_fresh``)
    keyed by the registry's ``slug`` when a registry entry matched, else by
    the lookup name itself (normalized) — ``None`` (tier=unknown) when
    nothing resolves."""
    normalized = _normalize_name(name)
    product_key = alias_index.get(normalized)
    slug: str | None = None
    if product_key is not None:
        entry = products.get(product_key)
        if isinstance(entry, dict):
            if registry_fresh:
                lines = entry.get("lts_lines")
                if isinstance(lines, list) and lines:
                    resolved = _resolve_from_lines(lines, version, now=now)
                    if resolved is not None:
                        return resolved
            candidate_slug = entry.get("slug")
            if isinstance(candidate_slug, str) and candidate_slug:
                slug = _normalize_name(candidate_slug)
    if endoflife_fresh and endoflife_snapshot:
        lookup_key = slug if slug is not None else normalized
        cycles = endoflife_snapshot.get(lookup_key)
        if isinstance(cycles, list) and cycles:
            resolved = _resolve_from_cycles(cycles, version, now=now)
            if resolved is not None:
                return resolved
    return None


def _classify(resolution: _Resolution | None) -> tuple[str, CurrencyVerdict] | None:
    """The 3-way reason-token precedence (decision record § 2): ``eol`` >
    ``over-lag`` > ``unknown``. ``None`` means no ``Finding`` is warranted
    (a resolved, fully-current — not EOL, zero lag — component), mirroring
    ``license.py``'s "allowed emits nothing" rule."""
    if resolution is None:
        return ("unknown", CurrencyVerdict.UNKNOWN)
    if resolution.verdict is CurrencyVerdict.EOL:
        return ("eol", CurrencyVerdict.EOL)
    if resolution.lag:
        return ("over-lag", CurrencyVerdict.SUPPORTED)
    return None


def _currency_finding(
    *,
    name: str,
    subject: str,
    version: str | None,
    reason: str,
    verdict: CurrencyVerdict,
    resolution: _Resolution | None,
) -> Finding:
    """Build the ``currency:`` ``Finding`` for an ``eol``/``over-lag``/
    ``unknown`` reason (never called for a clean resolution — the caller's
    own ``_classify`` filter). Mirrors ``license._license_finding``'s
    version-tail + sanitize-order convention exactly."""
    version_segment = _sanitize_id_segment(version) if version else "unspecified"
    subject_segment = _sanitize_id_segment(subject)
    if resolution is None:
        latest = lag = eol_date = tier = None
        message = f"{name}: currency could not be resolved (no registry/feed match)"
    else:
        latest, lag, eol_date, tier = (
            resolution.latest,
            resolution.lag,
            resolution.eol_date,
            resolution.tier,
        )
        if reason == "eol":
            message = f"{name}: reached end-of-life {eol_date} ({tier})"
        else:
            message = f"{name}: {lag} release(s) behind latest {latest!r} ({tier})"
    return Finding(
        id=f"currency:{reason}:{subject_segment}@{version_segment}",
        axis=AXIS_CURRENCY,
        message=message,
        subject=subject,
        severity=None,
        currency=CurrencyInfo(
            verdict=verdict, latest=latest, lag=lag, eol_date=eol_date, tier=tier
        ),
    )


def currency_findings(
    components: Sequence[Component], *, now: datetime
) -> tuple[tuple[Finding, ...], FeedProvenance | None]:
    """Compute the WHOLE currency axis's findings for one scan — one
    ``eol``/``over-lag``/``unknown``-reason ``Finding`` per component (a
    fully-current resolution emits none) PLUS the Python runtime's own
    finding (same rule), sorted by id — mirrors ``license_findings``'s "one
    function computes the whole axis's findings" shape. Returns
    ``(findings, currency_data)`` — ``currency_data`` is the bundled
    registry's own ``FeedProvenance`` (see module docstring's schema-shape
    judgment call), ``None`` when the registry's own ``updated:`` date is
    unparsable.

    Raises ``ValueError`` (via ``_registry_alias_index``) when the bundled
    registry itself is malformed enough to have two different products
    claiming the same normalized name/alias — a packaged-data integrity bug
    this function deliberately does not swallow; the caller's own seam
    (``engines.CurrencyEngine.run`` / ``cli.py``'s engine try/except) turns
    it into a typed ``engine-execution-failed`` record with the report
    still emitted, same as any other crashing engine."""
    registry = _load_registry()
    currency_data = _registry_feed_provenance(registry, now=now)
    registry_fresh = bool(currency_data is not None and currency_data.max_age_ok)
    products = _registry_products(registry)
    alias_index = _registry_alias_index(products)

    endoflife_snapshot: dict[str, list] | None = None
    endoflife_fresh = False
    cache_dir = feeds.resolve_cache_dir()
    if cache_dir is not None:
        path = feeds.endoflife_cache_path(cache_dir)
        raw_snapshot = feeds.load_endoflife_snapshot(path)
        if raw_snapshot is not None:
            # Two DIFFERENT snapshot keys normalizing to the same product
            # key are ambiguous — drop the colliding key entirely (those
            # lookups degrade to unknown) rather than letting dict order
            # silently pick a winner. The cache is a runtime input, so this
            # degrades honestly instead of raising (contrast the bundled
            # registry's alias index, packaged data, which fails loud).
            normalized_snapshot: dict[str, list] = {}
            colliding: set[str] = set()
            for key, value in raw_snapshot.items():
                normalized_key = _normalize_name(key)
                if normalized_key in normalized_snapshot or normalized_key in colliding:
                    colliding.add(normalized_key)
                    normalized_snapshot.pop(normalized_key, None)
                    continue
                normalized_snapshot[normalized_key] = value
            endoflife_snapshot = normalized_snapshot
            try:
                provenance = feeds.feed_provenance(
                    source=str(path),
                    path=path,
                    max_age_days=feeds.DEFAULT_FEED_MAX_AGE_DAYS,
                    now=now,
                )
                endoflife_fresh = provenance.max_age_ok
            except OSError:
                # The cache vanished between the load above and this
                # provenance stat (TOCTOU) -- treat as absent, mirrors
                # engines._kev_enrichment's own TOCTOU handling.
                endoflife_snapshot = None

    findings: list[Finding] = []
    for component in components:
        resolution = (
            _resolve(
                component.name,
                component.version,
                products=products,
                alias_index=alias_index,
                registry_fresh=registry_fresh,
                endoflife_snapshot=endoflife_snapshot,
                endoflife_fresh=endoflife_fresh,
                now=now,
            )
            if component.version
            else None
        )
        classification = _classify(resolution)
        if classification is not None:
            reason, verdict = classification
            findings.append(
                _currency_finding(
                    name=component.name,
                    subject=component.name,
                    version=component.version,
                    reason=reason,
                    verdict=verdict,
                    resolution=resolution,
                )
            )

    runtime_version = ".".join(str(part) for part in sys.version_info[:3])
    runtime_resolution = _resolve(
        "python",
        runtime_version,
        products=products,
        alias_index=alias_index,
        registry_fresh=registry_fresh,
        endoflife_snapshot=endoflife_snapshot,
        endoflife_fresh=endoflife_fresh,
        now=now,
    )
    runtime_classification = _classify(runtime_resolution)
    if runtime_classification is not None:
        reason, verdict = runtime_classification
        findings.append(
            _currency_finding(
                name="python",
                subject=_PYTHON_RUNTIME_SUBJECT,
                version=runtime_version,
                reason=reason,
                verdict=verdict,
                resolution=runtime_resolution,
            )
        )

    return (tuple(sorted(findings, key=lambda f: f.id)), currency_data)
