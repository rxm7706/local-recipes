"""osv-scanner offline DB resolution, content pre-flight, input synthesis,
and JSON-output parsing (Story 1.5). ``engines.OsvEngine`` owns the actual
subprocess call; this module is the vulnerability engine's non-subprocess
logic: filesystem reads (an env var + a zip archive) and JSON-as-data
parsing — no subprocess, no network, no exec.

Ownership decisions recorded:

* The DB cache-dir env var + on-disk layout are osv-scanner's OWN, not ours:
  ``$OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`` -> ``<dir>/osv-scanner/<eco-dir>/
  all.zip``, where the ecosystem SEGMENT is osv's own case-sensitive spelling
  (``PyPI``, NOT the lowercase ``pypi`` ``Ecosystem`` enum value — decision
  record § 4 / M1). ``_OSV_ECOSYSTEM_DIR`` is the canonical enum -> osv-dir
  -name map, v1 populated for PyPI only (conda is Epic 2 scope); an
  unrecognized ecosystem resolves to no DB path, never a lowercase guess.
  **No implicit default**: an unset/empty env var resolves to ``None`` —
  v1 never falls back to osv-scanner's own per-user cache guess (decision
  record § 5/§10).
* ``_db_has_valid_advisory`` is a fresh, tolerant PRODUCTION implementation
  of the decision record's minimal-OSV-advisory-shape check — NOT an import
  of ``tests/fixtures/osv_db_builder.py``'s ``_entry_for_record`` (that stays
  test-only; production code must not depend on the tests/fixtures tree,
  which the built package does not ship). It tolerates a malformed entry
  (bad JSON, wrong shape) without aborting the check of the REST of the zip
  — one bad entry must never mask a good one elsewhere in the archive.
* ``_synthesize_requirements`` is the NFR-S6 purity guard: a component whose
  resolved pypi name/version isn't a safe ``[A-Za-z0-9._-]+`` token, or that
  starts with ``-`` (a pip-option-injection shape even though ``-`` is in
  the allowed charset), is EXCLUDED — never written raw to the temp input
  file — and reported back to the caller (``SynthesizedInput.excluded``) so
  it can emit one ``indeterminate:unsafe-identity:<pkg>`` finding per
  exclusion via ``unsafe_identity_finding``.
* ``parse_osv_output`` mirrors ``hygiene.parse_deptry_output``'s shape: a
  frozen dataclass result (``OsvParse``) holding sorted findings, built
  defensively so a malformed/unexpected document never crashes the scan — a
  wholly unparseable top-level document surfaces one ``ENGINE_OUTPUT_
  UNPARSEABLE`` error (mirroring ``hygiene.py``'s own convention) with empty
  findings; a per-package/per-group shape mismatch is skipped, never raised.
* CVSS-score -> ``SeverityTier`` (``_cvss_score_to_tier``) follows the CVSS
  v3.1 §5 qualitative severity-rating bands, applied to the GROUP's
  ``max_severity`` (a numeric-string base score osv itself computes;
  empirically re-confirmed against osv-scanner 2.4.0 this story: `{"ids":
  [...], "aliases": [...], "max_severity": "9.8"}`). ``severity.raw`` on the
  emitted ``Finding`` is instead the id-MATCHING vulnerability's OWN
  ``severity[0].score`` (a CVSS VECTOR string, read from the sibling
  ``vulnerabilities[]`` array) — the two fields are read from different
  parts of the document by design, never conflated.
* ``DEFAULT_VULN_SEVERITY_POLICY`` is a MODULE DEFAULT (Story 1.6): mirrors
  ``hygiene.DEFAULT_HYGIENE_POLICY``'s shape exactly, one tier lower down the
  lattice. ``CRITICAL`` -> ``policy-violation`` (FR18's default gate: block
  on critical CVEs); ``HIGH``/``MEDIUM``/``LOW``/``NONE`` -> ``warn`` (the
  same ceiling 1.3 already gave DEP001-005). ``UNKNOWN`` is DELIBERATELY
  ABSENT from the table: an out-of-range/unparseable CVSS score is malformed
  data, not evidence of a low-severity vulnerability (see
  ``_cvss_score_to_tier``'s own docstring), so it degrades to
  ``indeterminate`` via ``status_for_severity_tier``'s
  ``.get(tier, Status.INDETERMINATE)`` fallback — never a silent downgrade
  (the same shape as ``hygiene.status_for_code``'s unknown-DEP-code
  fallback). Story 3.1: ``config.py``'s ``EffectiveConfig.
  vuln_severity_policy`` (derived from ``--fail-on``) now supplies the
  effective table ``DefaultPolicy`` threads through ``vuln_rung``'s
  optional ``policy`` parameter; this dict remains the fallback default for
  direct callers (unit tests, and the ``fail-on=critical`` default case,
  which reproduces this table exactly) and is now ``MappingProxyType``-
  wrapped (closes deferred-work.md's unprotected-mutable-dict finding).
* Story 2.5 adds two independent honesty tiers, both consumed by
  ``engines.OsvEngine.run`` (this module owns no clock/subprocess of its
  own): ``is_db_stale``/``stale_vuln_data_finding`` (FR12 — the offline DB's
  own ``snapshot_at`` degrades the WHOLE vulnerability axis to
  ``indeterminate`` when stale or future-dated, per the decision record's
  strict-inequality boundary rule) and ``cvss_v31_base_score`` +
  ``name_level_critical_advisory_ids``/``name_level_critical_cve_finding``
  (FR13 — "does this mapped-but-unversioned package carry any known
  CRITICAL advisory at ANY version?", a direct offline zip read, never a
  second ``osv-scanner`` subprocess: osv has no "any version" query mode).
  The raw OSV DB stores a CVSS VECTOR string (``severity[].score``), never
  osv-scanner's own numeric ``max_severity`` OUTPUT aggregate (which only
  exists after a real version-matched scan) — ``cvss_v31_base_score``
  computes the CVSS v3.1 §7.2 BASE score from the vector directly, BASE
  metrics only (``AV/AC/PR/UI/S/C/I/A``); CVSS v2/v4 and any temporal/
  environmental metric make the vector unparsable (``None``), which feeds
  ``_cvss_score_to_tier`` as ``SeverityTier.UNKNOWN`` — never counted
  critical, the same conservative-degrade convention every other function
  in this module already follows.
* Story 6.7 (FR: ``--min-epss``) reuses ``OsvParse.kev_candidates`` verbatim
  for a SECOND, independent feed consultation: ``epss_match``/``epss_stale_
  finding`` mirror ``kev_match``/``kev_stale_finding`` structurally (same
  candidate-set shape, same feed-provenance-owned-by-``feeds.py`` posture),
  but the enrichment itself is asymmetric with KEV's own: ``kev``/``kev_date``
  are ALWAYS stamped (``True``/``False``) once a catalog loads (there is a
  definite answer to "is this CVE KEV-listed?"), while ``epss`` has no
  boolean equivalent for "no match" — a finding with no EPSS score simply
  stays at ``Finding.epss``'s own ``None`` default. ``vuln_rung``'s
  ``min_epss`` param mirrors ``fail_on_kev``'s escalate-only shape: forces
  ``Status.POLICY_VIOLATION`` when ``finding.epss.score >= min_epss``, never
  fires when ``finding.epss is None``, never downgrades an
  already-``POLICY_VIOLATION`` status.
* Story 5.1 (AC1, remediation content): ``_extract_fixed_version`` surfaces
  osv-scanner's own discarded ``fixed`` version — read from the id-matching
  vulnerability record's OWN ``affected[].ranges[].events[]`` (the SAME raw
  record ``_own_severity_raw`` already reads its ``severity`` from), never
  a second lookup. Per the decision record (Design Notes): the FIRST
  well-formed ``fixed`` event found for that advisory wins, defensively —
  this is deliberately NOT a semver-range resolver correlating the fixed
  event against the scanned package's OWN version (out of scope); any
  missing/malformed ``affected``/``ranges``/``events`` shape yields
  ``None``, mirroring this module's "any shape mismatch yields fewer
  findings, never a crash" ethos throughout. Returned alongside ``Finding``
  the same way ``kev_candidates`` is (``OsvParse.fixed_versions``,
  ``finding.id -> fixed version string`` — no entry when unknown, never
  stored ON ``Finding``: Story 6.1 froze the schema, and fixed-version was
  never a reserved slot).
* Story 6.4 (FR36) finally stores what this docstring already documented
  but no code path ever captured: ``group.get("aliases")``.
  ``_findings_for_package`` now returns each ``Finding`` PAIRED with its
  raw (unsanitized) KEV-match candidate set — the group's own
  ``advisory_id`` plus every alias osv-scanner reported for that group
  (empirically confirmed, osv-scanner 2.4.0: ``aliases`` includes the
  primary id itself alongside any CVE cross-reference) — because CISA KEV
  is CVE-keyed while a PyPI advisory's own primary id is frequently
  GHSA-/PYSEC-shaped, with the CVE living only in ``aliases``. ``OsvParse``
  carries this as ``kev_candidates`` (finding id -> candidate tuple),
  consulted by ``engines.OsvEngine.run`` ONLY (never rendered into the
  report itself — ``Finding`` has no aliases slot, by design: Story 6.1
  froze the schema). ``kev_match``/``kev_stale_finding`` are this story's
  KEV-specific vocabulary; ``feeds.py`` owns the feed's cache layout,
  staleness math, and provenance shape (this module never reimplements
  any of those).

This module parses JSON and zip archives as DATA: no subprocess, no
network, no exec.
"""

from __future__ import annotations

import json
import math
import os
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType

from .feeds import DEFAULT_FEED_MAX_AGE_DAYS
from .interfaces import _sanitize_id_segment
from .inventory import Component, canonical_name
from .models import (
    AXIS_VULNERABILITY,
    Ecosystem,
    ErrorKind,
    ErrorRecord,
    Finding,
    Severity,
    SeverityTier,
    Status,
    StatusDriver,
)

# osv-scanner's own env var selecting the offline DB cache root (no CLI flag
# exists in 2.4.0 — decision record § 1).
OSV_DB_CACHE_ENV_VAR = "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY"

# osv-scanner's on-disk ecosystem SEGMENT name (case-sensitive), distinct
# from the lowercase Ecosystem enum value. v1 only feeds PyPI-ecosystem
# components (Epic 2 adds conda).
_OSV_ECOSYSTEM_DIR: dict[Ecosystem, str] = {
    Ecosystem.PYPI: "PyPI",
}

# NFR-S6 purity guard: a manifest-derived name/version must be exactly this
# token shape to be written into the synthesized osv input file.
_SAFE_TOKEN_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
)

_OWNER = "osv-scanner"


def resolve_cache_dir(*, env: Mapping[str, str] | None = None) -> str | None:
    """Resolve ``$OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`` — ``None`` when
    unset or empty (v1 has NO implicit default DB path). ``env`` is an
    optional injected mapping for tests; production callers omit it and read
    the real process environment."""
    source = env if env is not None else os.environ
    cache_dir = source.get(OSV_DB_CACHE_ENV_VAR)
    return cache_dir if cache_dir else None


def db_zip_path(
    cache_dir: str | Path, ecosystem: Ecosystem = Ecosystem.PYPI
) -> Path | None:
    """The on-disk ``all.zip`` path osv-scanner itself would load for
    ``ecosystem`` under ``cache_dir`` — ``None`` for an ecosystem this v1
    module has no osv-dir mapping for (never a lowercase-enum-derived
    guess)."""
    dir_name = _OSV_ECOSYSTEM_DIR.get(ecosystem)
    if dir_name is None:
        return None
    return Path(cache_dir) / "osv-scanner" / dir_name / "all.zip"


def db_snapshot_at(zip_path: Path) -> str:
    """``all.zip``'s own filesystem mtime, ISO-8601 UTC — the only honest
    ``VulnData.snapshot_at`` signal available without real provisioning
    infrastructure (Story 5.1)."""
    return datetime.fromtimestamp(zip_path.stat().st_mtime, tz=UTC).isoformat()


def _is_valid_osv_advisory(record: object, osv_ecosystem: str) -> bool:
    """The minimal OSV advisory shape check (decision record § 4): a dict
    carrying a non-empty string ``id`` and an ``affected[]`` entry naming
    ``osv_ecosystem`` (osv's own string, e.g. ``"PyPI"``) with a non-empty
    package name AND a concrete ``versions``/``ranges`` spec. Tolerant by
    construction — every branch returns ``False`` on a shape mismatch,
    never raises (one malformed entry must not abort the check of the rest
    of the zip)."""
    if not isinstance(record, dict):
        return False
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id:
        return False
    affected = record.get("affected")
    if not isinstance(affected, list):
        return False
    for entry in affected:
        if not isinstance(entry, dict):
            continue
        package = entry.get("package")
        if not isinstance(package, dict):
            continue
        if package.get("ecosystem") != osv_ecosystem:
            continue
        name = package.get("name")
        if not isinstance(name, str) or not name:
            continue
        versions = entry.get("versions")
        has_versions = isinstance(versions, list) and any(
            isinstance(v, str) and v for v in versions
        )
        ranges = entry.get("ranges")
        has_ranges = isinstance(ranges, list) and any(
            isinstance(r, dict) and r.get("events") for r in ranges
        )
        if has_versions or has_ranges:
            return True
    return False


def _db_has_valid_advisory(
    zip_path: Path, ecosystem: Ecosystem = Ecosystem.PYPI
) -> bool:
    """The decision record § 4 CONTENT pre-flight: ``True`` only when
    ``zip_path`` exists, opens as a zip, and holds >=1 entry that parses as
    JSON and satisfies ``_is_valid_osv_advisory`` for ``ecosystem``. A
    per-entry decode/shape failure is tolerated (one malformed entry must
    not abort the check of the rest); any failure to even OPEN the zip
    (missing file/dir, ``BadZipFile``, ...) fails the whole pre-flight."""
    osv_ecosystem = _OSV_ECOSYSTEM_DIR.get(ecosystem)
    if osv_ecosystem is None:
        return False
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for name in archive.namelist():
                if not name.endswith(".json"):
                    continue
                try:
                    record = json.loads(archive.read(name))
                except (
                    KeyError,
                    OSError,
                    zipfile.BadZipFile,
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                    # zipfile.ZipFile.read() raises RuntimeError for an
                    # encrypted entry (wrong/no password) and
                    # NotImplementedError for an unsupported compression
                    # method — either way, one bad entry must not abort the
                    # check of the rest of the archive.
                    RuntimeError,
                    NotImplementedError,
                ):
                    continue
                if _is_valid_osv_advisory(record, osv_ecosystem):
                    return True
    except (OSError, zipfile.BadZipFile):
        return False
    return False


@dataclass(frozen=True)
class SynthesizedInput:
    """The result of turning vuln-matchable PyPI components into a
    ``name==version`` requirements-style input: ``lines`` are the SORTED,
    NFR-S6-safe subset actually destined for the temp file; ``excluded`` are
    the components withheld by the purity guard (never written raw) — the
    caller emits one ``indeterminate:unsafe-identity:<pkg>`` finding per
    excluded component via ``unsafe_identity_finding``."""

    lines: tuple[str, ...]
    excluded: tuple[Component, ...]


def _is_safe_token(value: str) -> bool:
    """NFR-S6: exactly the ``[A-Za-z0-9._-]+`` token shape AND not leading
    with ``-`` (a pip-option-injection shape even though ``-`` is itself in
    the allowed charset)."""
    return (
        bool(value)
        and not value.startswith("-")
        and all(char in _SAFE_TOKEN_CHARS for char in value)
    )


def _synthesize_requirements(components: Sequence[Component]) -> SynthesizedInput:
    """Turn vuln-matchable components into sorted, de-duplicated
    ``name==version`` lines from their resolved ``pypi_identity`` (any
    ecosystem — Story 2.1 widened the caller's filter from
    ``ecosystem is Ecosystem.PYPI`` to ``pypi_identity is not None``, so
    a verified-mapped conda component flows through here too, under its
    MAPPED PyPI name). Callers are expected to have already filtered to
    ``component.vuln_matchable`` (this function trusts that pre-filter and
    only re-validates TOKEN safety, not vuln-matchability, so it stays a
    pure data-projection step). Lines are de-duplicated: two components may
    legitimately resolve to the same identity (a conda package and its pip
    twin in one lockfile)."""
    lines: list[str] = []
    excluded: list[Component] = []
    for component in components:
        identity = component.pypi_identity
        if identity is None or identity.version is None:
            # Defensive: Component.__post_init__ guarantees vuln_matchable
            # components carry a resolved identity + concrete version, so
            # this branch is unreachable given a correct pre-filter — but an
            # absent identity is exactly as unsafe as a bad token, so route
            # it the same way rather than crash.
            excluded.append(component)
            continue
        if _is_safe_token(identity.name) and _is_safe_token(identity.version):
            lines.append(f"{identity.name}=={identity.version}")
        else:
            excluded.append(component)
    return SynthesizedInput(
        lines=tuple(sorted(set(lines))), excluded=tuple(excluded)
    )


def _indeterminate_finding(reason: str, component: Component, message: str) -> Finding:
    # The subject segment carries BOTH name and version (mirroring the
    # `vuln:<id>:<pkg>@<version>` family): two components sharing a name but
    # differing by version are a legitimate, distinct inventory state
    # (inventory.py: "distinct versions of the same name stay distinct"). A
    # name-only id would collide across them and DefaultPolicy's
    # engine-finding dedup would then silently drop the second one's
    # finding (the aggregate verdict stays honest via the redundant
    # per-component match-level rung, but per-component traceability in
    # `findings[]` would be lost — never acceptable for a waivable finding).
    version_segment = (
        _sanitize_id_segment(component.version)
        if component.version
        else "unspecified"
    )
    return Finding(
        id=(
            f"indeterminate:{reason}:"
            f"{_sanitize_id_segment(component.name)}@{version_segment}"
        ),
        axis=AXIS_VULNERABILITY,
        message=message,
        subject=component.name,
        severity=None,
    )


def unsafe_identity_finding(component: Component) -> Finding:
    """One finding per NFR-S6-excluded component: its resolved pypi identity
    failed the safe-token purity guard and was never written into the
    synthesized osv input."""
    return _indeterminate_finding(
        "unsafe-identity",
        component,
        f"{component.name}: excluded from the osv-scanner input — its "
        "resolved pypi identity does not satisfy the safe-token purity "
        "guard (NFR-S6)",
    )


def offline_db_unavailable_finding(component: Component) -> Finding:
    """One finding per candidate withheld because the offline OSV database
    failed the content pre-flight (decision record § 4), or because osv
    itself reported no packages to scan (exit 128) — both are
    coverage-skipped, never a confident clean."""
    return _indeterminate_finding(
        "offline-db-unavailable",
        component,
        f"{component.name}: not checked against the offline OSV database — "
        "no usable local database found (absent, empty, or content-corrupt)",
    )


# --- Story 2.5 (FR12): stale-DB honesty --------------------------------------

# The offline DB's own `snapshot_at` must be fresher than this many days, or
# the WHOLE vulnerability axis routes to `indeterminate` via
# `stale_vuln_data_finding()` (decision record § 2). Hardcoded like
# `OSV_TIMEOUT_SECONDS`/`DEPTRY_TIMEOUT_SECONDS` -- a config surface
# (`--db-max-age`) is Story 3.1's, never this story's.
DB_MAX_AGE_DAYS = 7


def is_db_stale(snapshot_at: str | None, max_age_days: int, *, now: datetime) -> bool:
    """Decision record § 2's staleness rule: stale = ``snapshot_at``
    STRICTLY older than ``now - max_age_days`` (exactly-at-the-boundary is
    NOT stale — a non-strict inequality would false-positive the boundary
    case); a future-dated ``snapshot_at`` (clock skew) is ALSO treated as
    stale, never "fresh". Degrades conservatively on anything unparsable or
    unexpected: a missing, unparsable, or naive (no UTC offset — unsafe to
    compare against an aware ``now`` without guessing a timezone) timestamp
    is treated as stale (never fresh, never raises)."""
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


def stale_vuln_data_finding() -> Finding:
    """The single whole-axis ``indeterminate:vuln-data-stale:vuln-database``
    finding: forces the ENTIRE vulnerability axis to ``indeterminate`` when
    the offline DB is stale or future-dated (decision record § 2) — never a
    trusted ``clean``/unqualified ``policy-violation`` off untrustworthy
    data, even when the underlying match would otherwise be clean."""
    return Finding(
        id="indeterminate:vuln-data-stale:vuln-database",
        axis=AXIS_VULNERABILITY,
        message=(
            "the offline OSV vulnerability database is stale (its snapshot "
            f"is older than {DB_MAX_AGE_DAYS} days) or future-dated — the "
            "vulnerability axis cannot be trusted for this scan"
        ),
        subject="vuln-database",
        severity=None,
    )


# --- CVSS v3.1 §5 qualitative severity-rating bands --------------------------

_CVSS_BANDS: tuple[tuple[float, SeverityTier], ...] = (
    (0.1, SeverityTier.NONE),
    (4.0, SeverityTier.LOW),
    (7.0, SeverityTier.MEDIUM),
    (9.0, SeverityTier.HIGH),
)


def _cvss_score_to_tier(raw_score: object) -> SeverityTier:
    """CVSS v3.1 §5 qualitative bands, applied to a numeric-string BASE
    score (``group.max_severity`` — NOT a CVSS vector string): ``<0.1`` ->
    none, ``0.1-3.9`` -> low, ``4.0-6.9`` -> medium, ``7.0-8.9`` -> high,
    ``>=9.0`` -> critical. An absent, non-string, unparsable-as-float,
    non-finite (NaN/inf), or out-of-the-valid-CVSS-range (``[0.0, 10.0]``)
    score degrades to ``UNKNOWN`` (never a silent downgrade to a lower
    tier — an out-of-range score is malformed data, not evidence of a
    low-severity vulnerability)."""
    if not isinstance(raw_score, str) or not raw_score:
        return SeverityTier.UNKNOWN
    try:
        score = float(raw_score)
    except ValueError:
        return SeverityTier.UNKNOWN
    if not math.isfinite(score) or not (0.0 <= score <= 10.0):
        return SeverityTier.UNKNOWN
    for threshold, tier in _CVSS_BANDS:
        if score < threshold:
            return tier
    return SeverityTier.CRITICAL


# --- Story 2.5 (FR13): CVSS v3.1 BASE-metrics-only score calculator ----------
#
# The raw OSV DB stores a CVSS VECTOR string (severity[].score), never a
# numeric base score — group.max_severity (which _cvss_score_to_tier consumes
# above) is osv-scanner's own OUTPUT aggregate, computed only after a real
# version-matched scan and absent from a stored advisory. The name-level tier
# has no version-matched scan to read that aggregate from, so it computes the
# score itself, directly from the vector, per the official CVSS v3.1 §7.2
# formulas, using ONLY the 8 BASE metrics (AV/AC/PR/UI/S/C/I/A) — CVSS v2, v4,
# and any temporal/environmental metric (E, RL, RC, MAV, ...) are OUT OF
# SCOPE and make the vector unparsable (-> None -> SeverityTier.UNKNOWN via
# _cvss_score_to_tier, never counted critical).

_CVSS_V31_PREFIX = "CVSS:3.1"

_CVSS_AV_WEIGHTS = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
_CVSS_AC_WEIGHTS = {"L": 0.77, "H": 0.44}
_CVSS_UI_WEIGHTS = {"N": 0.85, "R": 0.62}
_CVSS_PR_WEIGHTS_UNCHANGED = {"N": 0.85, "L": 0.62, "H": 0.27}
_CVSS_PR_WEIGHTS_CHANGED = {"N": 0.85, "L": 0.68, "H": 0.5}
_CVSS_CIA_WEIGHTS = {"H": 0.56, "L": 0.22, "N": 0.0}

# The 8 BASE metrics + their legal single-letter values — a vector carrying
# any other key (a temporal/environmental metric, or CVSS v2's distinct
# metric set) is unparsable; so is one missing or duplicating any of these 8.
_CVSS_BASE_METRIC_VALUES: dict[str, frozenset[str]] = {
    "AV": frozenset(_CVSS_AV_WEIGHTS),
    "AC": frozenset(_CVSS_AC_WEIGHTS),
    "PR": frozenset(_CVSS_PR_WEIGHTS_UNCHANGED),
    "UI": frozenset(_CVSS_UI_WEIGHTS),
    "S": frozenset("UC"),
    "C": frozenset(_CVSS_CIA_WEIGHTS),
    "I": frozenset(_CVSS_CIA_WEIGHTS),
    "A": frozenset(_CVSS_CIA_WEIGHTS),
}


def _parse_cvss_v31_base_metrics(vector: object) -> dict[str, str] | None:
    """Parse a CVSS v3.1 vector string into its 8 BASE metrics — ``None`` on
    anything unparsable: a non-``CVSS:3.1``-prefixed vector, a missing or
    duplicated BASE metric, an unrecognized metric key (a temporal/
    environmental metric, or a CVSS v2/v4 shape), or an unrecognized value
    for a known metric. Tolerant by construction: never raises."""
    if not isinstance(vector, str) or not vector:
        return None
    parts = vector.split("/")
    if parts[0] != _CVSS_V31_PREFIX:
        return None
    metrics: dict[str, str] = {}
    for part in parts[1:]:
        segment = part.split(":", 1)
        if len(segment) != 2:
            return None
        key, value = segment
        legal_values = _CVSS_BASE_METRIC_VALUES.get(key)
        if legal_values is None or key in metrics or value not in legal_values:
            return None
        metrics[key] = value
    if metrics.keys() != _CVSS_BASE_METRIC_VALUES.keys():
        return None
    return metrics


def _round_up(value: float) -> float:
    """CVSS v3.1's own float-epsilon-safe roundup: round to the nearest
    1e-5 FIRST (killing binary-float noise like ``4.999999999999999``), then
    ceil to one decimal place — the official reference calculator's own
    algorithm, not a naive ``ceil(x * 10) / 10``."""
    scaled = round(value * 100_000)
    if scaled % 10_000 == 0:
        return scaled / 100_000
    return (scaled // 10_000 + 1) / 10


def cvss_v31_base_score(vector: object) -> float | None:
    """Compute the CVSS v3.1 BASE score (§7.2's official formula) from a raw
    vector string — ``None`` on anything unparsable (see
    ``_parse_cvss_v31_base_metrics``), never a guessed/partial score.
    Regression-pinned against the two fixture vectors this story documents:
    ``PDOS-FIXTURE-0001``'s vector -> 9.8 (critical), ``PDOS-FIXTURE-0002``'s
    -> 8.8 (high). Feed the result (as a string) straight into the existing
    ``_cvss_score_to_tier`` — no parallel banding table."""
    metrics = _parse_cvss_v31_base_metrics(vector)
    if metrics is None:
        return None
    scope = metrics["S"]
    c = _CVSS_CIA_WEIGHTS[metrics["C"]]
    i = _CVSS_CIA_WEIGHTS[metrics["I"]]
    a = _CVSS_CIA_WEIGHTS[metrics["A"]]
    iss = 1 - (1 - c) * (1 - i) * (1 - a)
    changed = scope == "C"
    impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if changed else 6.42 * iss
    if impact <= 0:
        return 0.0
    pr_weights = _CVSS_PR_WEIGHTS_CHANGED if changed else _CVSS_PR_WEIGHTS_UNCHANGED
    exploitability = (
        8.22
        * _CVSS_AV_WEIGHTS[metrics["AV"]]
        * _CVSS_AC_WEIGHTS[metrics["AC"]]
        * pr_weights[metrics["PR"]]
        * _CVSS_UI_WEIGHTS[metrics["UI"]]
    )
    combined = impact + exploitability
    if changed:
        return _round_up(min(1.08 * combined, 10.0))
    return _round_up(min(combined, 10.0))


# --- Story 2.5 (FR13): the name-level "any version" offline DB scan ---------


def _advisory_top_level_cvss_v3_vector(record: dict) -> str | None:
    """The advisory's OWN top-level ``severity[0].score`` (first
    ``type == "CVSS_V3"`` entry) — the raw DB has no ``group.max_severity``
    (osv-scanner's own OUTPUT aggregate); ``None`` on anything absent or
    malformed, never raises."""
    severity_list = record.get("severity")
    if not isinstance(severity_list, list):
        return None
    for entry in severity_list:
        if isinstance(entry, dict) and entry.get("type") == "CVSS_V3":
            score = entry.get("score")
            if isinstance(score, str) and score:
                return score
    return None


def _advisory_targets_pypi_name(
    record: dict,
    osv_ecosystem: str,
    canonical_target: str,
    ecosystem: Ecosystem = Ecosystem.PYPI,
) -> bool:
    """Mirrors ``_is_valid_osv_advisory``'s tolerant per-entry ``affected[]``
    loop, but matches on a PEP-503-canonicalized package NAME instead of
    merely checking a matchable spec is present. ``ecosystem`` canonicalizes
    the entry's OWN name the SAME way ``canonical_target`` was derived (never
    hardcoded to PyPI) — inert today (``_OSV_ECOSYSTEM_DIR`` only maps PyPI,
    so no other ecosystem reaches this function yet), but load-bearing once
    Epic 2 registers conda: ``canonical_name`` leaves conda names verbatim,
    so hardcoding PyPI here would PEP-503-fold a conda name it must not."""
    affected = record.get("affected")
    if not isinstance(affected, list):
        return False
    for entry in affected:
        if not isinstance(entry, dict):
            continue
        package = entry.get("package")
        if not isinstance(package, dict):
            continue
        if package.get("ecosystem") != osv_ecosystem:
            continue
        name = package.get("name")
        if not isinstance(name, str) or not name:
            continue
        if canonical_name(ecosystem, name) == canonical_target:
            return True
    return False


def name_level_critical_advisory_ids(
    zip_path: Path, pypi_name: str, ecosystem: Ecosystem = Ecosystem.PYPI
) -> tuple[str, ...]:
    """FR13's name-level CVE tier: does ``pypi_name`` carry >=1 CRITICAL
    advisory in the offline OSV DB at ANY affected version? A direct,
    offline, in-process zip read — osv-scanner has no "any version" query
    mode, so this is never a second subprocess. Tolerant per-entry parse
    (mirrors ``_db_has_valid_advisory``'s own zip-walking loop): one
    malformed zip entry never aborts the scan of the rest of the archive.
    Severity comes from the advisory's OWN top-level ``severity[]`` (osv's
    ``max_severity`` GROUP aggregate does not exist on a raw stored
    advisory); an unparsable CVSS vector degrades to ``SeverityTier.
    UNKNOWN`` via ``cvss_v31_base_score`` + ``_cvss_score_to_tier``, never
    counted critical. Returns a SORTED, deduplicated tuple of matching
    advisory ids (empty when the zip cannot even be opened, or on no
    critical match)."""
    osv_ecosystem = _OSV_ECOSYSTEM_DIR.get(ecosystem)
    if osv_ecosystem is None:
        return ()
    target = canonical_name(ecosystem, pypi_name)
    matches: set[str] = set()
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for name in archive.namelist():
                if not name.endswith(".json"):
                    continue
                try:
                    record = json.loads(archive.read(name))
                except (
                    KeyError,
                    OSError,
                    zipfile.BadZipFile,
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                    # See _db_has_valid_advisory's own comment: an encrypted
                    # or unsupported-compression entry must not abort the
                    # scan of the rest of the archive either.
                    RuntimeError,
                    NotImplementedError,
                ):
                    continue
                if not isinstance(record, dict):
                    continue
                if not _advisory_targets_pypi_name(
                    record, osv_ecosystem, target, ecosystem
                ):
                    continue
                vector = _advisory_top_level_cvss_v3_vector(record)
                if vector is None:
                    continue
                score = cvss_v31_base_score(vector)
                if score is None:
                    continue
                if _cvss_score_to_tier(str(score)) is not SeverityTier.CRITICAL:
                    continue
                record_id = record.get("id")
                if isinstance(record_id, str) and record_id:
                    matches.add(record_id)
    except (OSError, zipfile.BadZipFile):
        return ()
    return tuple(sorted(matches))


def name_level_critical_cve_finding(
    component: Component, advisory_ids: Sequence[str]
) -> Finding:
    """FR13's name-level enrichment: a mapped-but-unversioned component
    (resolved ``pypi_identity``, ``version=None``) whose name carries >=1
    CRITICAL advisory in the offline DB at SOME version. ADDS this finding
    ON TOP OF the baseline ``indeterminate:no-version|range-only:<pkg>``
    finding ``DefaultPolicy`` already derives for a withheld component —
    never replaces or suppresses it (the distinct reason token,
    ``name-level-critical-cve``, keeps the two ids from colliding)."""
    ids = ", ".join(sorted(advisory_ids))
    return _indeterminate_finding(
        "name-level-critical-cve",
        component,
        f"{component.name}: carries a CRITICAL advisory ({ids}) at some "
        "version but is unpinned — resolve a version or waive explicitly",
    )


def _own_severity_raw(vuln_record: object) -> str | None:
    """The id-matching vulnerability's OWN ``severity[0].score`` (a CVSS
    vector string) — ``None`` when absent/malformed, never raises."""
    if not isinstance(vuln_record, dict):
        return None
    severity_list = vuln_record.get("severity")
    if not isinstance(severity_list, list) or not severity_list:
        return None
    first = severity_list[0]
    if not isinstance(first, dict):
        return None
    score = first.get("score")
    return score if isinstance(score, str) and score else None


def _extract_fixed_version(
    vuln_record: object, *, pkg_name: str, pkg_ecosystem: str | None
) -> str | None:
    """Story 5.1 (AC1): the FIRST well-formed ``fixed`` version event found
    in ``vuln_record``'s own ``affected[].ranges[].events[]`` — walked in
    document order (``affected`` entries, then each entry's ``ranges``,
    then each range's ``events``), defensively (mirrors ``_own_severity_
    raw``'s tolerant read of the SAME raw record one field over): ``None``
    on any missing/wrong-typed ``affected``/``ranges``/``events``, or when
    no event carries a non-empty string ``fixed``. Deliberately NOT a
    semver-range resolver correlating the fixed event against the scanned
    package's OWN version — see the module docstring / decision record.

    Review finding (2026-07-24): an OSV/GHSA advisory can legitimately list
    MULTIPLE affected packages (a monorepo-style advisory) under one id --
    reading ``fixed`` from an ``affected[]`` entry that isn't actually the
    package this Finding is about would attribute an unrelated package's
    fixed version. Every ``affected[]`` entry is now matched against
    ``pkg_name``/``pkg_ecosystem`` (this record's OWN embedded ``package``
    sub-object, exact string match -- mirrors ``_advisory_targets_pypi_
    name``'s tolerant per-entry shape, but without its cross-ecosystem
    canonicalization: both sides originate from the SAME osv-scanner/DB
    source here, never our own resolved identity) before its ranges/events
    are read; an entry with no/malformed ``package`` sub-object, or one
    that doesn't match, is skipped. ``pkg_ecosystem=None`` (an unparsable
    top-level ecosystem) skips the ecosystem half of the match rather than
    rejecting every entry outright -- name alone is still a meaningful
    filter and never worse than the pre-fix unfiltered behavior.

    Review finding (2026-07-24): only ``ECOSYSTEM``/``SEMVER``-typed ranges
    are read -- a ``GIT``-typed range's ``fixed`` event is a COMMIT HASH,
    not a version (PYSEC records routinely list the GIT range first), and
    rendering "upgrade to >= <40-hex sha>" is nonsense advice. A range with
    a missing/unrecognized ``type`` is skipped as malformed (OSV requires
    ``type``; the module's "fewer findings, never a crash" ethos)."""
    if not isinstance(vuln_record, dict):
        return None
    affected = vuln_record.get("affected")
    if not isinstance(affected, list):
        return None
    for entry in affected:
        if not isinstance(entry, dict):
            continue
        package = entry.get("package")
        if not isinstance(package, dict):
            continue
        if package.get("name") != pkg_name:
            continue
        if pkg_ecosystem is not None and package.get("ecosystem") != pkg_ecosystem:
            continue
        ranges = entry.get("ranges")
        if not isinstance(ranges, list):
            continue
        for one_range in ranges:
            if not isinstance(one_range, dict):
                continue
            if one_range.get("type") not in ("ECOSYSTEM", "SEMVER"):
                continue
            events = one_range.get("events")
            if not isinstance(events, list):
                continue
            for event in events:
                if not isinstance(event, dict):
                    continue
                fixed = event.get("fixed")
                if isinstance(fixed, str) and fixed:
                    return fixed
    return None


def _findings_for_package(
    package_entry: object,
) -> list[tuple[Finding, tuple[str, ...], str | None]]:
    """One ``(vuln:<advisory-id>:<pkg>@<ver> Finding, kev-match candidates,
    fixed version)`` triple per ``(group.ids[i], package)`` for one
    ``results[].packages[]`` entry. Defensive throughout: any shape
    mismatch at any level yields fewer findings, never a crash.

    The candidate tuple (Story 6.4/FR36) is ``advisory_id`` followed by the
    group's own ``aliases`` (RAW, unsanitized strings — deduplicated,
    order-preserving) — the set ``vuln.kev_match`` checks against a CISA
    KEV catalog. The fixed version (Story 5.1, AC1) is the id-matching raw
    vulnerability record's own ``_extract_fixed_version`` result, ``None``
    when unknown. Both are returned alongside the ``Finding``, never stored
    ON it (``Finding`` has no aliases or fixed-version slot)."""
    if not isinstance(package_entry, dict):
        return []
    package = package_entry.get("package")
    if not isinstance(package, dict):
        return []
    pkg_name = package.get("name")
    if not isinstance(pkg_name, str) or not pkg_name:
        return []
    pkg_version = package.get("version")
    raw_pkg_ecosystem = package.get("ecosystem")
    pkg_ecosystem = (
        raw_pkg_ecosystem if isinstance(raw_pkg_ecosystem, str) else None
    )
    groups = package_entry.get("groups")
    if not isinstance(groups, list):
        return []
    vuln_by_id: dict[str, dict] = {}
    vulnerabilities = package_entry.get("vulnerabilities")
    if isinstance(vulnerabilities, list):
        for vuln_record in vulnerabilities:
            if isinstance(vuln_record, dict):
                vid = vuln_record.get("id")
                if isinstance(vid, str) and vid and vid not in vuln_by_id:
                    vuln_by_id[vid] = vuln_record

    name_segment = _sanitize_id_segment(pkg_name)
    version_segment = (
        _sanitize_id_segment(pkg_version)
        if isinstance(pkg_version, str) and pkg_version
        else "unspecified"
    )

    findings: list[tuple[Finding, tuple[str, ...], str | None]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        ids = group.get("ids")
        if not isinstance(ids, list):
            continue
        tier = _cvss_score_to_tier(group.get("max_severity"))
        raw_aliases = group.get("aliases")
        aliases = (
            tuple(a for a in raw_aliases if isinstance(a, str) and a)
            if isinstance(raw_aliases, list)
            else ()
        )
        for advisory_id in ids:
            if not isinstance(advisory_id, str) or not advisory_id:
                continue
            vuln_record = vuln_by_id.get(advisory_id)
            severity_raw = _own_severity_raw(vuln_record)
            finding_id = (
                f"vuln:{_sanitize_id_segment(advisory_id)}:"
                f"{name_segment}@{version_segment}"
            )
            try:
                finding = Finding(
                    id=finding_id,
                    axis=AXIS_VULNERABILITY,
                    message=f"{pkg_name}: {advisory_id} (severity {tier.value})",
                    subject=pkg_name,
                    severity=Severity(tier=tier, raw=severity_raw),
                )
            except ValueError:
                # Belt-and-suspenders: sanitized segments always yield a
                # grammar-valid id, but never let a Finding-invariant raise
                # crash the parse — drop the single malformed entry.
                continue
            candidates = tuple(dict.fromkeys((advisory_id, *aliases)))
            fixed_version = _extract_fixed_version(
                vuln_record, pkg_name=pkg_name, pkg_ecosystem=pkg_ecosystem
            )
            findings.append((finding, candidates, fixed_version))
    return findings


@dataclass(frozen=True)
class OsvParse:
    """The outcome of parsing one osv-scanner ``--format json`` document
    (mirrors ``hygiene.DeptryParse``'s shape): ``findings`` are the mapped
    ``vuln:`` findings (sorted by id, deduplicated by id), built
    defensively so a malformed/unexpected document never crashes the scan.
    A wholly unparseable top-level document surfaces one ``errors`` record
    instead (``ENGINE_OUTPUT_UNPARSEABLE``, mirroring ``hygiene.py``'s own
    convention) with empty findings.

    ``kev_candidates`` (Story 6.4/FR36, additive): ``finding.id ->
    (advisory_id, *aliases)`` for every ``findings`` entry — the raw
    (unsanitized) KEV-match candidate set ``engines.OsvEngine.run`` checks
    against a CISA KEV catalog via ``kev_match``. Never rendered into the
    report itself (``Finding`` carries no aliases slot).

    ``fixed_versions`` (Story 5.1, AC1, additive): ``finding.id -> fixed
    version string`` for every ``findings`` entry whose id-matching raw
    vulnerability record yielded a well-formed ``fixed`` event
    (``_extract_fixed_version`` — see its docstring); an entry with an
    unknown fixed version is simply ABSENT from this mapping (never a
    ``None`` value, never a guess). Consulted by ``engines.OsvEngine.run``
    (threaded into ``EngineResult.fixed_versions``) and, from there,
    ``cli.py``'s ``render_text`` remediation lines — never stored ON
    ``Finding`` (Story 6.1 froze the schema; fixed-version was never a
    reserved slot)."""

    findings: tuple[Finding, ...]
    errors: tuple[ErrorRecord, ...]
    kev_candidates: Mapping[str, tuple[str, ...]] = MappingProxyType({})
    fixed_versions: Mapping[str, str] = MappingProxyType({})


def parse_osv_output(raw: str) -> OsvParse:
    """Parse osv-scanner's ``--format json`` document into ``vuln:``
    findings.

    Empirically-verified 2.4.0 shape (decision record, re-confirmed this
    story): ``results[].packages[].groups[]`` = ``{ids, aliases,
    max_severity}`` (osv's own aggregation; ``max_severity`` is a
    numeric-string CVSS BASE score shared by every id in the group —
    attributing the group's max to each id is conservative, never
    under-claims severity); ``results[].packages[].vulnerabilities[]``
    carries the raw per-id OSV record, including ``severity: [{type,
    score}]`` where ``score`` is a CVSS VECTOR string. For every
    ``(group.ids[i], package)`` pair this emits one ``Finding`` whose
    ``severity.tier`` comes from ``max_severity`` and whose ``severity.raw``
    is the id-MATCHING vulnerability's own ``severity[0].score`` (``None``
    if no matching record or no severity is present)."""
    if not raw.strip():
        return OsvParse(
            findings=(),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=_OWNER,
                    message="osv-scanner produced no machine output (empty --output-file)",
                ),
            ),
        )
    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return OsvParse(
            findings=(),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=_OWNER,
                    message="osv-scanner output is not valid JSON",
                ),
            ),
        )
    if not isinstance(document, dict):
        return OsvParse(
            findings=(),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=_OWNER,
                    message=(
                        "osv-scanner output is not a JSON object "
                        f"(got {type(document).__name__})"
                    ),
                ),
            ),
        )
    results = document.get("results")
    if not isinstance(results, list):
        # A schema-drifted-but-still-JSON-object document (e.g. no "results"
        # key at all): nothing to report, no findings — not a parse failure
        # (osv's own "no vulnerabilities" body already omits nothing).
        return OsvParse(findings=(), errors=())

    by_id: dict[str, Finding] = {}
    candidates_by_id: dict[str, tuple[str, ...]] = {}
    fixed_version_by_id: dict[str, str] = {}
    for result in results:
        if not isinstance(result, dict):
            continue
        packages = result.get("packages")
        if not isinstance(packages, list):
            continue
        for package_entry in packages:
            for finding, candidates, fixed_version in _findings_for_package(
                package_entry
            ):
                if finding.id not in by_id:
                    by_id[finding.id] = finding
                    candidates_by_id[finding.id] = candidates
                    if fixed_version is not None:
                        fixed_version_by_id[finding.id] = fixed_version
    ordered = tuple(sorted(by_id.values(), key=lambda f: f.id))
    return OsvParse(
        findings=ordered,
        errors=(),
        kev_candidates=MappingProxyType(
            {finding.id: candidates_by_id[finding.id] for finding in ordered}
        ),
        fixed_versions=MappingProxyType(
            {
                finding.id: fixed_version_by_id[finding.id]
                for finding in ordered
                if finding.id in fixed_version_by_id
            }
        ),
    )


# --- Story 6.4 (FR36): CISA KEV enrichment -----------------------------------


def kev_match(candidates: Sequence[str], catalog: Mapping[str, str]) -> str | None:
    """Return CISA's ``dateAdded`` for the first of ``candidates`` (a
    finding's own ``advisory_id`` followed by its group's raw ``aliases`` —
    ``OsvParse.kev_candidates``' shape) present in ``catalog`` (a
    ``{cve_id: dateAdded}`` mapping, ``feeds.load_kev_catalog``'s shape) —
    ``None`` when none match. Checked in ``candidates``' own order
    (deterministic; membership is what matters — a KEV catalog is keyed by
    literal CVE id, so at most one candidate can ever match in practice)."""
    for candidate in candidates:
        date_added = catalog.get(candidate)
        if date_added is not None:
            return date_added
    return None


def kev_stale_finding(*, unavailable: bool) -> Finding:
    """The single whole-axis KEV-provenance ``indeterminate:`` finding —
    mirrors ``stale_vuln_data_finding``'s role for the OSV DB one level up
    (feed PROVENANCE, not advisory content): forces the ENTIRE
    vulnerability axis to ``indeterminate`` when ``fail-on-kev`` is active
    but the CISA KEV feed cannot be trusted this scan.

    ``unavailable=True`` -> ``indeterminate:kev-data-unavailable:kev-feed``
    (no usable feed at all — absent, unreadable, or content-corrupt);
    ``unavailable=False`` -> ``indeterminate:kev-data-stale:kev-feed`` (a
    real, loadable feed whose snapshot is too old). Either way: never a
    trusted ``clean``/unqualified ``policy-violation`` off untrustworthy
    KEV data, even when every underlying CVSS match would otherwise be
    clean."""
    if unavailable:
        return Finding(
            id="indeterminate:kev-data-unavailable:kev-feed",
            axis=AXIS_VULNERABILITY,
            message=(
                "the CISA KEV feed is unavailable (absent, unreadable, or "
                "content-corrupt) while fail-on-kev is active — the "
                "vulnerability axis cannot be trusted for this scan"
            ),
            subject="kev-feed",
            severity=None,
        )
    return Finding(
        id="indeterminate:kev-data-stale:kev-feed",
        axis=AXIS_VULNERABILITY,
        message=(
            "the CISA KEV feed is stale (its snapshot is older than "
            f"{DEFAULT_FEED_MAX_AGE_DAYS} days) or future-dated while "
            "fail-on-kev is active — the vulnerability axis cannot be "
            "trusted for this scan"
        ),
        subject="kev-feed",
        severity=None,
    )


# --- Story 6.7 (FR: --min-epss): FIRST.org EPSS enrichment -------------------


def epss_match(
    candidates: Sequence[str], scores: Mapping[str, tuple[float, float]]
) -> tuple[float, float] | None:
    """Return the ``(score, percentile)`` pair for the first of
    ``candidates`` (``OsvParse.kev_candidates``' SAME shape — a finding's own
    ``advisory_id`` followed by its group's raw ``aliases``) present in
    ``scores`` (a ``{cve_id: (score, percentile)}`` mapping,
    ``feeds.load_epss_scores``'s shape) — ``None`` when none match. Mirrors
    ``kev_match``'s first-hit-wins semantics exactly (checked in
    ``candidates``' own order; membership is what matters — an EPSS catalog
    is keyed by literal CVE id, so at most one candidate can ever match in
    practice)."""
    for candidate in candidates:
        pair = scores.get(candidate)
        if pair is not None:
            return pair
    return None


def epss_stale_finding(*, unavailable: bool) -> Finding:
    """The single whole-axis EPSS-provenance ``indeterminate:`` finding —
    mirrors ``kev_stale_finding`` verbatim, one feed over: forces the ENTIRE
    vulnerability axis to ``indeterminate`` when ``--min-epss`` is active but
    the FIRST.org EPSS feed cannot be trusted this scan.

    ``unavailable=True`` -> ``indeterminate:epss-data-unavailable:epss-feed``
    (no usable feed at all — absent, unreadable, or content-corrupt);
    ``unavailable=False`` -> ``indeterminate:epss-data-stale:epss-feed`` (a
    real, loadable feed whose snapshot is too old). Either way: never a
    trusted ``clean``/unqualified ``policy-violation`` off untrustworthy
    EPSS data, even when every underlying CVSS/KEV match would otherwise be
    clean."""
    reason = "unavailable" if unavailable else "stale"
    detail = (
        "unavailable (absent, unreadable, or content-corrupt)"
        if unavailable
        else (
            "stale (its snapshot is older than "
            f"{DEFAULT_FEED_MAX_AGE_DAYS} days) or future-dated"
        )
    )
    return Finding(
        id=f"indeterminate:epss-data-{reason}:epss-feed",
        axis=AXIS_VULNERABILITY,
        message=(
            f"the FIRST.org EPSS feed is {detail} while --min-epss is active — "
            "the vulnerability axis cannot be trusted for this scan"
        ),
        subject="epss-feed",
        severity=None,
    )


# --- Story 1.6: severity -> rung composition ---------------------------------

# The default vuln policy: SeverityTier -> Status. Mirrors
# hygiene.DEFAULT_HYGIENE_POLICY's shape exactly: CRITICAL blocks (FR18's
# default gate), HIGH/MEDIUM/LOW/NONE all warn (1.3's DEP001-005 ceiling).
# UNKNOWN is deliberately absent (see module docstring). Keys are
# SeverityTier members (NOT Status tokens), so the sole-ownership
# rung-ordering guard does not fire on this literal. MappingProxyType-
# wrapped (Story 3.1, deferred-work.md): an unprotected mutable module
# dict was a latent in-process-mutation risk with no exploit path
# identified — now closed directly rather than merely noted.
DEFAULT_VULN_SEVERITY_POLICY: Mapping[SeverityTier, Status] = MappingProxyType(
    {
        SeverityTier.CRITICAL: Status.POLICY_VIOLATION,
        SeverityTier.HIGH: Status.WARN,
        SeverityTier.MEDIUM: Status.WARN,
        SeverityTier.LOW: Status.WARN,
        SeverityTier.NONE: Status.WARN,
    }
)


def status_for_severity_tier(
    tier: SeverityTier, *, policy: Mapping[SeverityTier, Status] | None = None
) -> Status:
    """The status for a CVSS severity tier under ``policy`` (Story 3.1:
    ``config.py``'s ``EffectiveConfig.vuln_severity_policy``, threaded by
    ``DefaultPolicy``) — ``DEFAULT_VULN_SEVERITY_POLICY`` when ``policy`` is
    ``None`` (every pre-3.1 direct caller, unchanged). ``UNKNOWN`` (absent
    from every legal policy table — see the module docstring) degrades to
    ``indeterminate`` (never a false-green): an unassessable severity is
    never treated as safely non-blocking."""
    # `is not None` (not truthiness): an explicitly empty policy={} is a
    # real, distinct table (every tier indeterminate) -- `or` would wrongly
    # coerce it to DEFAULT_VULN_SEVERITY_POLICY instead of honoring it
    # (review finding).
    table = policy if policy is not None else DEFAULT_VULN_SEVERITY_POLICY
    return table.get(tier, Status.INDETERMINATE)


def vuln_rung(
    finding: Finding,
    *,
    policy: Mapping[SeverityTier, Status] | None = None,
    fail_on_kev: bool = False,
    min_epss: float | None = None,
) -> tuple[Status, StatusDriver]:
    """Derive the ``(Status, StatusDriver)`` rung for one vulnerability-axis
    finding.

    A real ``vuln:`` finding carries a populated ``Finding.severity``, whose
    ``.tier`` is looked up via ``status_for_severity_tier(..., policy=
    policy)`` — ``policy=None`` (every pre-3.1 caller) falls back to
    ``DEFAULT_VULN_SEVERITY_POLICY`` there. A finding with no severity at
    all — the axis's own ``indeterminate:`` withhold findings (no-version,
    unsafe-identity, offline-db-unavailable, ...) — yields
    ``Status.INDETERMINATE`` directly, exactly as it did under the pre-1.6
    backstop, regardless of ``policy``; this mirrors how ``hygiene_rung``
    already handles a stray ``indeterminate:`` id on the hygiene axis the
    same way. The driver carries the finding's own axis and id.

    ``fail_on_kev=True`` (Story 6.4, default ``False`` here — every
    pre-6.4 direct caller is unaffected; ``interfaces.DefaultPolicy``
    threads the configured value): when ``finding.kev is True``, the
    status is forced to ``Status.POLICY_VIOLATION`` regardless of the
    CVSS-derived status above — an actively-exploited (CISA KEV-listed)
    advisory blocks independent of its own severity tier (FR36). This can
    only ESCALATE (never downgrade an already-``POLICY_VIOLATION`` CVSS
    status — forcing the same value is a no-op) and never fires for a
    finding with ``kev`` ``None``/``False`` (every non-``vuln:`` finding,
    and any ``vuln:`` finding the KEV feed was never consulted for or did
    not match).

    ``min_epss`` (Story 6.7, default ``None`` here — every pre-6.7 direct
    caller is unaffected): when ``finding.epss is not None`` and
    ``finding.epss.score >= min_epss``, the status is forced to
    ``Status.POLICY_VIOLATION`` — mirrors ``fail_on_kev``'s escalate-only
    shape exactly (never downgrades an already-``POLICY_VIOLATION`` status,
    never fires when ``finding.epss is None`` — no EPSS match, or the feed
    was never consulted)."""
    status = (
        status_for_severity_tier(finding.severity.tier, policy=policy)
        if finding.severity is not None
        else Status.INDETERMINATE
    )
    if fail_on_kev and finding.kev is True:
        status = Status.POLICY_VIOLATION
    if (
        min_epss is not None
        and finding.epss is not None
        and finding.epss.score >= min_epss
    ):
        status = Status.POLICY_VIOLATION
    return (
        status,
        StatusDriver(axis=finding.axis, finding_id=finding.id),
    )
