"""``upstream_discovery`` pipeline nodes — GitHub-trending discovery trigger (Story 13.1,
FR-64 / CAP-1) + tier classification (Story 13.2, FR-65 / CAP-2) + fixed-source audit
track (Story 13.4, FR-67 / CAP-4).

CAP-1's ``refresh_trending_candidates`` is a PURE ``params -> RefreshRequest`` trigger —
mirrors ``pipelines/vulnerability/nodes.py::refresh_vdb_store`` exactly. ALL fetch +
HTML/JSON parsing IO lives in ``datasets/upstream_discovery.py`` (dataset-owned IO, AD-2);
no HTTP/parse imports here.

CAP-2's ``classify_trending_candidates`` joins the already-materialized
``trending_candidates`` against ``pypi_universe`` / ``pypi_conda_mapping`` /
``pypi_intelligence_enriched`` catalog datasets and assigns a tier + reason to every row —
pure pandas/stdlib, no new fetch (mirrors ``pipelines/seed_gaps/nodes.py``'s
join-then-classify-then-DataFrame style).

CAP-4's ``load_org_audit_candidates`` is a PURE ``params -> pd.DataFrame`` loader over the
git-tracked, hand-curated ``params:org_audit_candidates`` list — no HTTP/parse import; the
source is config, not a live fetch. ``classify_trending_candidates`` (above, unchanged) is
reused as CAP-4's classify half via a second ``pipeline.py`` node binding: Kedro's
positional ``inputs=[...]`` lets the same function serve ``org_audit_candidates`` in place
of ``trending_candidates``."""

from __future__ import annotations

import logging
import re

import pandas as pd

from ...datasets.refresh import DAILY_SECONDS, WEEKLY_SECONDS, RefreshRequest

logger = logging.getLogger(__name__)


def _coerce_cadence(ttls: dict, key: str, default: int = DAILY_SECONDS) -> int:
    """Read a cadence (seconds) from ``params:ttls``; a missing / null / non-numeric
    value, OR a non-dict ``ttls`` (review finding, Story 13.1 — the precedent
    ``vulnerability/nodes.py::_coerce_cadence`` this mirrors only guards a falsy value,
    not a truthy non-dict), falls back to ``default`` (daily unless the caller says
    otherwise — Story 21.4's weekly package-catalog triggers pass ``WEEKLY_SECONDS``)
    rather than crashing."""
    raw = ttls.get(key) if isinstance(ttls, dict) else None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def refresh_trending_candidates(ttls: dict) -> RefreshRequest:
    # CAP-1 — GitHub-trending discovery ingest (Story 13.1, FR-64; spec-upstream-discovery)
    """External-refresh asset for the GitHub-trending candidate snapshot. PURE: emits the
    ``RefreshRequest`` trigger ``TrendingSnapshotDataset`` consumes (which HONORS its
    cadence/force and invokes the dataset-owned injected fetch of the 3
    daily/weekly/monthly HTML pages + the Search API fallback — NO HTTP/parse import
    here). Cadence daily (``ttls.trending_candidates``; no legacy equivalent). Single
    writer of ``trending_candidates``."""
    return RefreshRequest(
        store="trending_candidates",
        cadence_seconds=_coerce_cadence(ttls, "trending_candidates"),
    )


# ---------------------------------------------------------------------------
# Story 21.4 — Tier 1 external-refresh triggers (spec-atlas-kedro-catalog-expansion CAP-2)
# ---------------------------------------------------------------------------
#
# Three PURE ``params:ttls -> RefreshRequest`` triggers mirroring
# ``refresh_trending_candidates`` exactly — each is the SINGLE writer of its named
# catalog entry (AD-3/AD-10). Their datasets (``AnacondaDist2026Dataset`` /
# ``BasiliskPackagesDataset`` / ``AossPremiumPythonDataset``, all
# ``ExternalRefreshDataset`` subclasses) have a ``load()`` that is a read-only
# projection of a persisted store — EMPTY forever unless some node's ``outputs=``
# binding calls ``save()``. These nodes are that binding (the Story 21.2 pass-1
# pipeline-dormancy lesson). ``discovery_aoss_free_python_raw`` (``TrackedSeedDataset``)
# deliberately has NO trigger: its ``load()`` reads the git-tracked seed directly.
# Cadence: weekly (``ttls.discovery_*_raw`` — keyed by the catalog entry name, as
# kedro-catalog-check requires — matching the sibling ``vcs_registry_versions`` weekly
# default for slow-moving package catalogs).


def refresh_anaconda_dist_2026x(ttls: dict) -> RefreshRequest:
    # Story 21.4 — Anaconda Distribution 2026.x package list (HTML scrape + seed fallback)
    """External-refresh trigger for ``discovery_anaconda_dist_2026x_raw``. PURE: emits
    the ``RefreshRequest`` ``AnacondaDist2026Dataset.save()`` honors (cadence/force) and
    which invokes the dataset-owned injected scrape — NO HTTP/parse import here."""
    return RefreshRequest(
        store="discovery_anaconda_dist_2026x_raw",
        cadence_seconds=_coerce_cadence(ttls, "discovery_anaconda_dist_2026x_raw", WEEKLY_SECONDS),
    )


def refresh_basilisk_packages(ttls: dict) -> RefreshRequest:
    # Story 21.4 — Basilisk GET /v1/packages catalog (distinct from vulnerability_basilisk_*)
    """External-refresh trigger for ``discovery_basilisk_packages_raw``. PURE: emits the
    ``RefreshRequest`` ``BasiliskPackagesDataset.save()`` honors; the paginated GET walk
    is dataset-owned."""
    return RefreshRequest(
        store="discovery_basilisk_packages_raw",
        cadence_seconds=_coerce_cadence(ttls, "discovery_basilisk_packages_raw", WEEKLY_SECONDS),
    )


def refresh_aoss_premium_python(ttls: dict) -> RefreshRequest:
    # Story 21.4 — Google Assured OSS premium-tier Python catalog (live doc)
    """External-refresh trigger for ``discovery_aoss_premium_python_raw``. PURE: emits
    the ``RefreshRequest`` ``AossPremiumPythonDataset.save()`` honors; on failure the
    dataset's inherited keep-last-good + mark-stale applies."""
    return RefreshRequest(
        store="discovery_aoss_premium_python_raw",
        cadence_seconds=_coerce_cadence(ttls, "discovery_aoss_premium_python_raw", WEEKLY_SECONDS),
    )


# ---------------------------------------------------------------------------
# Story 21.5 — Tier 2 catalog sources (spec-21-5-tier-2-sources.md): rxm7706/about
# maintainer universe (CDO-ENT-CONDA)
# ---------------------------------------------------------------------------


def refresh_about_maintainers(ttls: dict) -> RefreshRequest:
    # Story 21.5 — rxm7706/about maintainer + co-maintainer feedstock lists
    """External-refresh trigger for ``discovery_about_maintainers_raw``. PURE: emits
    the ``RefreshRequest`` ``AboutMaintainersDataset.save()`` honors; the single-URL
    fetch + parse is dataset-owned (AD-2). Cadence WEEKLY (not daily): the about README
    maintainer lists change on a manual maintainer-list refresh cadence, not
    continuously — mirrors the sibling Tier-1 ``discovery_*_raw`` cadence, not
    ``trending_candidates``'s daily one."""
    return RefreshRequest(
        store="discovery_about_maintainers_raw",
        cadence_seconds=_coerce_cadence(ttls, "discovery_about_maintainers_raw", WEEKLY_SECONDS),
    )


# The `conda-forge/` prefix and `-feedstock` suffix parse_about_readme's
# `feedstock_slug` column carries (the FULL matched slug, e.g.
# "conda-forge/dbt-bigquery-feedstock") — stripped here, at JOIN time, before
# comparing against `core_feedstock_attribution.feedstock_name` (a bare name, e.g.
# "dbt-bigquery"). Never done at parse time: the raw dataset preserves exactly what
# the README said (spec Boundaries).
_FEEDSTOCK_SLUG_PREFIX = "conda-forge/"
_FEEDSTOCK_SLUG_SUFFIX = "-feedstock"

# The complete-export-contract.md §1 "CDO-ENT-CONDA maintainer universe" column
# contract (also this story's I/O Matrix), in order.
_ENTERPRISE_CONDA_MAINTAINERS_COLS = [
    "core_python_package_name",
    "role",
    "feedstock_slug",
    "repository_source",
]

REPOSITORY_SOURCE_CDO_ENT_CONDA = "CDO-ENT-CONDA"


def _strip_feedstock_slug(slug) -> str | None:
    """Strip the ``conda-forge/`` prefix and ``-feedstock`` suffix from an
    about-parsed ``feedstock_slug`` for comparison against
    ``core_feedstock_attribution.feedstock_name``. A non-string/blank slug (or one
    that strips down to nothing) returns ``None`` — never matches, never raises."""
    if not isinstance(slug, str):
        return None
    value = slug.strip()
    if value.startswith(_FEEDSTOCK_SLUG_PREFIX):
        value = value[len(_FEEDSTOCK_SLUG_PREFIX) :]
    if value.endswith(_FEEDSTOCK_SLUG_SUFFIX):
        value = value[: -len(_FEEDSTOCK_SLUG_SUFFIX)]
    return value or None


def join_enterprise_conda_maintainers(
    discovery_about_maintainers_raw: pd.DataFrame,
    core_feedstock_attribution: pd.DataFrame,
) -> pd.DataFrame:
    # CDO-ENT-CONDA enterprise-consumption universe (Story 21.5, Tier 2)
    """Join ``discovery_about_maintainers_raw`` against ``core_feedstock_attribution``
    (``conda_name``/``feedstock_name``) on the STRIPPED feedstock slug
    (:func:`_strip_feedstock_slug`), producing the ``enterprise_conda_maintainers``
    CDO-ENT-CONDA universe (complete-export-contract.md §1's exact column contract).

    An about row whose stripped slug has no ``core_feedstock_attribution`` match (a
    renamed/retired feedstock) is DROPPED — never fabricated with a null
    ``core_python_package_name`` — and logged at WARN, not raised. An
    empty/malformed ``discovery_about_maintainers_raw`` or an
    empty/unusable ``core_feedstock_attribution`` degrades to an empty frame carrying
    the full output schema; never raises."""
    if (
        discovery_about_maintainers_raw is None
        or getattr(discovery_about_maintainers_raw, "empty", True)
        or not {"feedstock_slug", "role"} <= set(getattr(discovery_about_maintainers_raw, "columns", []))
    ):
        return pd.DataFrame(columns=_ENTERPRISE_CONDA_MAINTAINERS_COLS)

    attribution_index: dict[str, str] = {}
    if (
        core_feedstock_attribution is not None
        and not getattr(core_feedstock_attribution, "empty", True)
        and {"conda_name", "feedstock_name"} <= set(getattr(core_feedstock_attribution, "columns", []))
    ):
        for row in core_feedstock_attribution.itertuples(index=False):
            feedstock_name = getattr(row, "feedstock_name", None)
            conda_name = getattr(row, "conda_name", None)
            if not isinstance(feedstock_name, str) or not isinstance(conda_name, str):
                continue
            # first-seen wins on a duplicate feedstock_name (should not happen
            # upstream, but never silently overwrite a resolved mapping).
            attribution_index.setdefault(feedstock_name, conda_name)

    rows: list[dict] = []
    for row in discovery_about_maintainers_raw.itertuples(index=False):
        raw_slug = getattr(row, "feedstock_slug", None)
        stripped = _strip_feedstock_slug(raw_slug)
        conda_name = attribution_index.get(stripped) if stripped is not None else None
        if conda_name is None:
            logger.warning(
                "enterprise_conda_maintainers: no core_feedstock_attribution match "
                "for feedstock_slug=%r (stripped=%r) — dropped, not fabricated",
                raw_slug,
                stripped,
            )
            continue
        rows.append(
            {
                "core_python_package_name": conda_name,
                "role": getattr(row, "role", None),
                "feedstock_slug": raw_slug,
                "repository_source": REPOSITORY_SOURCE_CDO_ENT_CONDA,
            }
        )
    return pd.DataFrame(rows, columns=_ENTERPRISE_CONDA_MAINTAINERS_COLS)


# ---------------------------------------------------------------------------
# classify_trending_candidates (Story 13.2, CAP-2 / FR-65)
# ---------------------------------------------------------------------------

_PEP503_RUN_RE = re.compile(r"[-_.]+")

# A small, curated OSI-approved SPDX allowlist — NOT the full SPDX list (Design
# Notes: the same accepted scope decision as any other curated-map addition in
# this codebase; git review decides, not exhaustive automation).
_OSI_APPROVED_SPDX_IDS = frozenset(
    {
        "MIT",
        "MIT-0",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "BSD-3-Clause-Clear",
        "0BSD",
        "ISC",
        "GPL-2.0-only",
        "GPL-2.0-or-later",
        "GPL-3.0-only",
        "GPL-3.0-or-later",
        "AGPL-3.0-only",
        "AGPL-3.0-or-later",
        "LGPL-2.1-only",
        "LGPL-2.1-or-later",
        "LGPL-3.0-only",
        "LGPL-3.0-or-later",
        "MPL-2.0",
        "EPL-2.0",
        "BSL-1.0",
        "Unlicense",
        "Zlib",
        "PSF-2.0",
    }
)

# The only packaging shapes `_classify_packaging_shape` (pypi_intelligence/nodes.py)
# ever emits for a compiled/native package; anything else (a malformed/unexpected
# value) degrades to `unclassified-needs-human` rather than a confident tier "2".
_COMPILED_SHAPES = frozenset({"c-extension", "cython", "rust-pyo3"})

_CLASSIFIER_NEW_COLS = ["pypi_name", "tier", "reason"]

# The exact `reason` value for a resolved+already-on-conda-forge skip (Story 13.2).
# Named (not inline) because CAP-3's `trending_candidates/query.py` imports it as the
# single source of truth for its `--not-on-cf` filter (review finding, Story 13.3:
# an independent copy of this literal would silently drift if this wording ever changed).
REASON_ALREADY_ON_CF = "already-on-conda-forge"


def _normalize_pypi_name(name: str) -> str:
    """PEP 503 name normalization: lowercase, collapse runs of ``-``/``_``/``.``
    into a single ``-``."""
    return _PEP503_RUN_RE.sub("-", name).lower()


def _is_missing(v) -> bool:
    """Scalar-safe missing check — ``True`` for ``None`` / NaN / ``pd.NA``, ``False``
    for a real value INCLUDING a list/dict cell (``pd.isna`` on a non-scalar returns
    an array whose truth value is ambiguous, so non-scalars are treated as present
    rather than crashing the node).

    Mirrors ``pipelines/pypi_intelligence/nodes.py::_is_missing`` deliberately rather
    than importing it — no pipeline package imports another's ``nodes`` module in this
    codebase. A plain ``v is None or isinstance(v, float) and pd.isna(v)`` check misses
    ``pd.NA``, which the string dtypes this project targets under pandas 3.0 produce for
    a null cell; that would insert ``str(pd.NA)`` -> ``"<na>"`` as a live join key
    (review finding, Story 13.2)."""
    if v is None:
        return True
    if isinstance(v, (list, tuple, dict, set)):
        return False
    try:
        return bool(pd.isna(v))
    except (ValueError, TypeError):
        return False


def _repo_segment(repo_full_name) -> str | None:
    """The ``repo`` half of a GitHub ``owner/repo`` full name (after the final
    ``/``); ``None`` on a non-string (e.g. a NaN cell), empty, or malformed value
    (no ``/``, or an empty segment) — never raises."""
    if not isinstance(repo_full_name, str) or "/" not in repo_full_name:
        return None
    segment = repo_full_name.rsplit("/", 1)[-1]
    return segment or None


def _normalized_pypi_index(pypi_universe: pd.DataFrame) -> dict[str, str]:
    """``{normalized_name: canonical pypi_name}`` from ``pypi_universe.pypi_name`` —
    the index :func:`_resolve_pypi_name` matches against, built ONCE (per call) and
    reused by :func:`classify_trending_candidates` across every row. An
    empty/malformed table (missing ``pypi_name``) degrades to ``{}`` — never raises."""
    if (
        pypi_universe is None
        or getattr(pypi_universe, "empty", True)
        or "pypi_name" not in getattr(pypi_universe, "columns", [])
    ):
        return {}
    index: dict[str, str] = {}
    for name in pypi_universe["pypi_name"]:
        if _is_missing(name):
            continue
        index.setdefault(_normalize_pypi_name(str(name)), str(name))
    return index


def _resolve_pypi_name(
    repo_full_name: str,
    pypi_universe: pd.DataFrame,
    *,
    index: dict[str, str] | None = None,
) -> str | None:
    """Resolve a trending repo's ``owner/repo`` full name to a canonical PyPI package
    name: normalize the repo segment after ``/`` (PEP 503) and exact-match it against
    a normalized index built from ``pypi_universe.pypi_name``. ``None`` on no
    match, a malformed/empty ``repo_full_name``, or an empty/malformed
    ``pypi_universe`` — never raises.

    Pass ``index`` (from :func:`_normalized_pypi_index`) to reuse an index built ONCE
    across many rows — :func:`classify_trending_candidates` does exactly that, so this
    IS the production resolution path rather than a second copy of it that only the
    tests exercise (review finding, Story 13.2: an inline duplicate here would let the
    tested copy and the shipped copy drift apart silently). Without ``index`` the table
    is indexed per call — correct, but O(universe) per row if called in a loop.

    A documented, lossy v1 heuristic (Design Notes): no atlas dataset maps a GitHub
    ``owner/repo`` to a PyPI name today, so a package published under a name
    different from its own repo (e.g. the ``python-requests`` repo / ``requests``
    package) false-negatives to no match — an accepted v1 limitation, not a defect."""
    segment = _repo_segment(repo_full_name)
    if segment is None:
        return None
    lookup = _normalized_pypi_index(pypi_universe) if index is None else index
    return lookup.get(_normalize_pypi_name(segment))


def _is_awesome_list(repo_full_name: str, description) -> bool:
    """Awesome-list shape heuristic: the repo segment starts with ``awesome``
    (case-insensitive), OR ``description`` contains ``curated list`` / ``awesome
    list`` (case-insensitive). A missing/non-string/NaN ``description`` never
    raises — it just fails the description half of the check."""
    segment = _repo_segment(repo_full_name) or ""
    if segment.lower().startswith("awesome"):
        return True
    if _is_missing(description):
        return False
    desc = str(description).lower()
    return "curated list" in desc or "awesome list" in desc


def _classify_row(
    row,
    pypi_name: str | None,
    on_cf: bool,
    intel: dict | None,
    *,
    universe_usable: bool,
    mapping_usable: bool,
) -> tuple[str, str]:
    """The CAP-2 decision tree (``tier-taxonomy.md``; I/O & Edge-Case Matrix),
    evaluated in this fixed order — never raises, always returns a non-null tier and
    a non-empty reason. ``universe_usable``/``mapping_usable`` let a genuinely
    unusable (empty/malformed) join-signal table degrade to
    ``unclassified-needs-human`` PER SIGNAL, distinct from a usable table that was
    searched and confirmed empty for this specific row (review finding, Story 13.2 —
    the awesome-list heuristic below never depends on any join table, so it must
    still fire even when every table is unusable):

    1. unresolved (``pypi_name is None``): awesome-list heuristic match ->
       ``"skip", "awesome-list"`` (checked first — independent of any join table);
       else, if ``pypi_universe`` itself was unusable -> ``"skip",
       "unclassified-needs-human"`` (we couldn't actually search); else ``"skip",
       "no-pypi-artifact"`` (searched, no match).
    2. resolved but ``pypi_conda_mapping`` was unusable -> ``"skip",
       "unclassified-needs-human"`` (can't confirm not-on-cf).
    3. resolved + already on conda-forge (``on_cf``) -> ``"skip",
       "already-on-conda-forge"``.
    4. resolved + no ``pypi_intelligence_enriched`` row (``intel is None`` — covers
       both an unusable table and a usable table missing this specific name) ->
       ``"skip", "unclassified-needs-human"``.
    5. ``license_spdx`` not a string in :data:`_OSI_APPROVED_SPDX_IDS` -> ``"skip",
       "not-osi-license"``.
    6. ``packaging_shape == "pure-python"`` -> tier ``"1"``.
    7. ``packaging_shape`` in :data:`_COMPILED_SHAPES` -> tier ``"2"``.
    8. any other (missing/``"unknown"``/malformed) shape -> ``"skip",
       "unclassified-needs-human"``.

    ``row`` is the raw ``trending_candidates`` record (dict-like via ``.get``) — used
    only by the unresolved branch's ``repo_full_name``/``description``."""
    if pypi_name is None:
        repo_full_name = row.get("repo_full_name") or ""
        description = row.get("description")
        if _is_awesome_list(repo_full_name, description):
            return "skip", "awesome-list"
        if not universe_usable:
            return "skip", "unclassified-needs-human"
        return "skip", "no-pypi-artifact"
    if not mapping_usable:
        return "skip", "unclassified-needs-human"
    if on_cf:
        return "skip", REASON_ALREADY_ON_CF
    if intel is None:
        return "skip", "unclassified-needs-human"
    license_spdx = intel.get("license_spdx")
    if not isinstance(license_spdx, str) or license_spdx not in _OSI_APPROVED_SPDX_IDS:
        return "skip", "not-osi-license"
    shape = intel.get("packaging_shape")
    if shape == "pure-python":
        return "1", f"pure-python packaging shape, OSI-approved license {license_spdx}"
    if shape in _COMPILED_SHAPES:
        return "2", f"{shape} packaging shape, OSI-approved license {license_spdx}"
    return "skip", "unclassified-needs-human"


def classify_trending_candidates(
    trending_candidates: pd.DataFrame,
    pypi_universe: pd.DataFrame,
    pypi_conda_mapping: pd.DataFrame,
    pypi_intelligence_enriched: pd.DataFrame,
) -> pd.DataFrame:
    # CAP-2 — tier classification (Story 13.2, FR-65; spec-upstream-discovery)
    """Join each ``trending_candidates`` row against already-materialized atlas signals
    and assign a ``tier`` (``"1"``/``"2"``/``"skip"``) + a non-empty ``reason`` to
    EVERY row — never a silent drop (I/O & Edge-Case Matrix). Output =
    ``trending_candidates``'s own columns + ``pypi_name``/``tier``/``reason``.

    Builds the normalized ``pypi_universe`` name index, the normalized on-conda-forge
    ``pypi_name`` set, and the normalized ``pypi_intelligence_enriched``-by-``pypi_name``
    dict each ONCE (ALL THREE keyed the same PEP-503-normalized way — review finding,
    Story 13.2: comparing a normalized-resolved name against un-normalized join keys
    silently missed real matches), then resolves each row through
    :func:`_resolve_pypi_name` (the SAME helper the unit tests exercise — passed the
    prebuilt index so the shipped path and the tested path cannot drift) and classifies
    it via :func:`_classify_row` (mirrors
    ``seed_gaps/nodes.py::report_lts_registry_gap``'s join-then-classify-then-DataFrame
    style). An empty/malformed ``trending_candidates`` (missing ``repo_full_name``)
    returns an empty frame with the full output schema. A genuinely unusable
    ``pypi_universe``/``pypi_conda_mapping`` table — empty, missing the column, OR
    non-empty but carrying zero searchable keys — degrades its OWN affected rows to
    ``unclassified-needs-human`` (:func:`_classify_row`'s
    ``universe_usable``/``mapping_usable``) rather than a blanket all-three-tables
    check — never raises (Boundaries & Constraints)."""
    if (
        trending_candidates is None
        or getattr(trending_candidates, "empty", True)
        or "repo_full_name" not in getattr(trending_candidates, "columns", [])
    ):
        base_cols = (
            list(trending_candidates.columns)
            if trending_candidates is not None and hasattr(trending_candidates, "columns")
            else []
        )
        out_cols = base_cols + [c for c in _CLASSIFIER_NEW_COLS if c not in base_cols]
        return pd.DataFrame(columns=out_cols)

    # A signal table is "usable" only when it yielded at least one searchable key —
    # a table that is non-empty and carries the column but whose every `pypi_name`
    # cell is missing was never actually searchable, so treating it as authoritative
    # would emit a confident `no-pypi-artifact` / not-on-cf call off zero data
    # (review finding, Story 13.2).
    pypi_index = _normalized_pypi_index(pypi_universe)
    universe_usable = bool(pypi_index)

    on_cf_names: set[str] = set()
    if (
        pypi_conda_mapping is not None
        and not getattr(pypi_conda_mapping, "empty", True)
        and "pypi_name" in getattr(pypi_conda_mapping, "columns", [])
    ):
        for name in pypi_conda_mapping["pypi_name"]:
            if _is_missing(name):
                continue
            on_cf_names.add(_normalize_pypi_name(str(name)))
    mapping_usable = bool(on_cf_names)

    intel_by_name: dict[str, dict] = {}
    if (
        pypi_intelligence_enriched is not None
        and not getattr(pypi_intelligence_enriched, "empty", True)
        and "pypi_name" in getattr(pypi_intelligence_enriched, "columns", [])
    ):
        for _, r in pypi_intelligence_enriched.iterrows():
            name = r.get("pypi_name")
            if _is_missing(name):
                continue
            intel_by_name[_normalize_pypi_name(str(name))] = r.to_dict()

    base_cols = list(trending_candidates.columns)
    out_cols = base_cols + [c for c in _CLASSIFIER_NEW_COLS if c not in base_cols]

    rows: list[dict] = []
    for _, row in trending_candidates.iterrows():
        record = row.to_dict()
        pypi_name = _resolve_pypi_name(
            record.get("repo_full_name"), pypi_universe, index=pypi_index
        )
        normalized_name = _normalize_pypi_name(pypi_name) if pypi_name is not None else None
        on_cf = normalized_name is not None and normalized_name in on_cf_names
        intel_row = intel_by_name.get(normalized_name) if normalized_name is not None else None
        tier, reason = _classify_row(
            record,
            pypi_name,
            on_cf,
            intel_row,
            universe_usable=universe_usable,
            mapping_usable=mapping_usable,
        )
        record["pypi_name"] = pypi_name
        record["tier"] = tier
        record["reason"] = reason
        rows.append(record)

    return pd.DataFrame(rows, columns=out_cols)


# ---------------------------------------------------------------------------
# load_org_audit_candidates (Story 13.4, CAP-4 / FR-67)
# ---------------------------------------------------------------------------

_ORG_AUDIT_COLS = ["repo_full_name"]


def _add_org_audit_row(rows: list[dict], seen: set[str], repo_full_name) -> None:
    """Shared row-building rule for BOTH ``org_audit_candidates`` entries and
    ``discovery_curated_groups_seed`` repos (Story 21.5): a non-string value degrades
    to ``None`` (visible skip, never excluded); a resolved value that repeats an
    earlier one case-insensitively is deduped, keeping the first occurrence's casing."""
    if not isinstance(repo_full_name, str):
        repo_full_name = None
    if repo_full_name is not None:
        key = repo_full_name.casefold()
        if key in seen:
            return
        seen.add(key)
    rows.append({"repo_full_name": repo_full_name})


def _flatten_curated_groups(discovery_curated_groups_seed) -> list:
    # Story 21.5 — curated org sweeps (Tier 2 catalog-sources.md; a git-tracked,
    # hand-curated air-gap seed, NEVER a live GitHub-org-enumeration crawl)
    """Flatten ``{"groups": [{"org": ..., "repos": [...]}]}`` into a flat list of repo
    entries (possibly malformed — validated by :func:`_add_org_audit_row`). NEVER
    raises: a missing/non-dict seed, a missing/non-list ``groups``, a non-dict group,
    or a non-list ``repos`` degrades that portion to contributing ZERO entries —
    exactly like a malformed ``params:org_audit_candidates`` entry degrades today."""
    if not isinstance(discovery_curated_groups_seed, dict):
        return []
    groups = discovery_curated_groups_seed.get("groups")
    if not isinstance(groups, list):
        return []
    entries: list = []
    for group in groups:
        repos = group.get("repos") if isinstance(group, dict) else None
        if not isinstance(repos, list):
            continue
        entries.extend(repos)
    return entries


def load_org_audit_candidates(
    org_audit_candidates: list | None,
    discovery_curated_groups_seed: dict | None = None,
) -> pd.DataFrame:
    # CAP-4 — fixed-source audit track ingest (Story 13.4, FR-67; spec-upstream-discovery)
    # Story 21.5 (Tier 2) extends this with a SECOND source: discovery_curated_groups_seed.
    """PURE ``(params:org_audit_candidates, discovery_curated_groups_seed) ->
    pd.DataFrame`` loader: builds a ``repo_full_name``-column frame from the UNION of
    the git-tracked, hand-curated declared list (``conf/base/parameters.yml``) and the
    NEW git-tracked curated-org-sweep seed (``conf/base/curated_groups.json``,
    flattened by :func:`_flatten_curated_groups`). No HTTP/parse import — both sources
    are config, not a live fetch, so there is no dataset-owned IO seam to inject
    (Boundaries & Constraints).

    Every entry from EITHER source produces exactly one row — never a silent drop
    (review finding, Story 13.4, preserved unchanged by Story 21.5: matches
    :func:`classify_trending_candidates`'s own stated "never a silent drop" invariant).
    A non-dict entry, a missing ``repo_full_name`` key, or a non-string value degrades
    that row's ``repo_full_name`` to ``None`` rather than being excluded — the
    downstream classifier already resolves a ``None``/non-string ``repo_full_name`` to
    a visible ``skip``/``no-pypi-artifact`` (or ``unclassified-needs-human``) row via
    its existing ``_repo_segment`` guard, so a hand-edit typo surfaces as a reasoned
    skip instead of vanishing. A resolved ``repo_full_name`` that repeats an earlier
    one (case-insensitively, ACROSS both sources — ``org_audit_candidates`` processed
    first) is deduped, keeping the first occurrence's original casing — a literal or
    case-variant duplicate must not double-count in ``org_audit_candidates_classified``.
    ``None``/non-list ``org_audit_candidates`` and a missing/malformed
    ``discovery_curated_groups_seed`` each independently degrade to contributing ZERO
    rows (never raises); if BOTH are empty/malformed the result is an empty frame
    carrying the ``repo_full_name`` column, matching
    :func:`classify_trending_candidates`'s own empty-input schema."""
    rows: list[dict] = []
    seen: set[str] = set()
    if isinstance(org_audit_candidates, list):
        for entry in org_audit_candidates:
            repo_full_name = entry.get("repo_full_name") if isinstance(entry, dict) else None
            _add_org_audit_row(rows, seen, repo_full_name)
    for repo_full_name in _flatten_curated_groups(discovery_curated_groups_seed):
        _add_org_audit_row(rows, seen, repo_full_name)
    return pd.DataFrame(rows, columns=_ORG_AUDIT_COLS)
