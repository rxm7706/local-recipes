"""``upstream_discovery`` pipeline nodes — GitHub-trending discovery trigger (Story 13.1,
FR-64 / CAP-1) + tier classification (Story 13.2, FR-65 / CAP-2).

CAP-1's ``refresh_trending_candidates`` is a PURE ``params -> RefreshRequest`` trigger —
mirrors ``pipelines/vulnerability/nodes.py::refresh_vdb_store`` exactly. ALL fetch +
HTML/JSON parsing IO lives in ``datasets/upstream_discovery.py`` (dataset-owned IO, AD-2);
no HTTP/parse imports here.

CAP-2's ``classify_trending_candidates`` joins the already-materialized
``trending_candidates`` against ``pypi_universe`` / ``pypi_conda_mapping`` /
``pypi_intelligence_enriched`` catalog datasets and assigns a tier + reason to every row —
pure pandas/stdlib, no new fetch (mirrors ``pipelines/seed_gaps/nodes.py``'s
join-then-classify-then-DataFrame style)."""

from __future__ import annotations

import re

import pandas as pd

from ...datasets.refresh import DAILY_SECONDS, RefreshRequest


def _coerce_cadence(ttls: dict, key: str) -> int:
    """Read a cadence (seconds) from ``params:ttls``; a missing / null / non-numeric
    value, OR a non-dict ``ttls`` (review finding, Story 13.1 — the precedent
    ``vulnerability/nodes.py::_coerce_cadence`` this mirrors only guards a falsy value,
    not a truthy non-dict), falls back to the daily default rather than crashing."""
    raw = ttls.get(key) if isinstance(ttls, dict) else None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return DAILY_SECONDS


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
        return "skip", "already-on-conda-forge"
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
