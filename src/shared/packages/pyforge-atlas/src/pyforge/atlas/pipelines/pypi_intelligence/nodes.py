"""``pypi_intelligence`` pipeline nodes — PyPI-side intelligence (Story B2, § 5.2 / AD-3).

PURE ``DataFrame -> DataFrame`` transforms (the A2 ``test_no_inline_io.py`` denylist now
scans this module). Every fetch is DATASET-owned: the per-project ``/pypi/<name>/json``
fan-out (Phases H/R) lives in ``datasets/request_datasets.py::PyPIJsonRequestDataset``
(scheduler-gated, DW-B1-2); the Phase P BigQuery job + its two-layer cost gate live in
``datasets/request_datasets.py::BigQueryDownloadsDataset``. A node receives already-
fetched frames and only transforms them (THE CRUX).

Single-write-path (AC-2): ``phase_r_upsert_one`` (CFA:8198) + ``apply_readiness_scores``
(CFA:8484) are the shared helpers Phase R/S AND the S6 ``add-handoff`` CLI re-score
through — factored as module-level pure functions so a one-package re-score flows
through the SAME code the pipeline uses.

``# legacy: Phase <ID>`` provenance per node; ``CFA`` = ``conda_forge_atlas.py`` @ b18cbb5.
"""

from __future__ import annotations

import time

import pandas as pd

# The mapping provenance tiers that must NEVER be clobbered by a later, weaker match
# (Phase C/C.5 no-clobber rule; the g10_spelling tier MUST survive as a valid
# match_source — spec:209-216, MG:79-81). The `mapping-gap` writeback itself is a B6
# node; B2 only preserves the tiers here in the Phase C mapping stage.
_PROTECTED_MATCH_SOURCES = ("parselmouth", "recipe_source_url", "g10_spelling")

# Phase H 30-day safety re-check window (seconds) — eligibility condition 3.
_PHASE_H_SAFETY_RECHECK_SECONDS = 30 * 24 * 3600

# Phase Q channels whose bulk repodata yields the per-channel `in_<channel>` BOOLs.
_CROSS_CHANNELS = ("bioconda", "pytorch", "nvidia", "robostack")


def _is_missing(v) -> bool:
    """Scalar-safe missing check (review-hardening): ``True`` for ``None`` / NaN,
    ``False`` for a real value INCLUDING a list/array/dict cell — ``pd.isna`` on a
    non-scalar returns an array whose truth value is ambiguous (raises ``ValueError``),
    so non-scalars are treated as present rather than crashing the node."""
    if v is None:
        return True
    if isinstance(v, (list, tuple, dict, set)):
        return False
    try:
        return bool(pd.isna(v))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Phase C — parselmouth conda<->PyPI mapping join
# ---------------------------------------------------------------------------

def map_pypi_conda(
    pypi_parselmouth_mapping_raw: pd.DataFrame,
    core_packages_enumerated: pd.DataFrame,
) -> pd.DataFrame:
    # legacy: Phase C  (phase_c_parselmouth_join CFA:1744)
    """Join the parselmouth ``pypi_name -> conda_name`` mapping against the conda
    packages the core pipeline enumerated (cross-pipeline by catalog name, AD-3).

    The ``g10_spelling`` provenance tier MUST survive as a valid ``match_source`` (a
    later, weaker match may not clobber it — no-clobber rule, spec:209-216). Input
    ``pypi_parselmouth_mapping_raw``: ``pypi_name``, ``conda_name``, optional
    ``match_source`` (default ``parselmouth``). ``core_packages_enumerated`` restricts
    the mapping to REAL conda packages (``conda_name``). Output (intermediate, fed to
    Phase C.5): ``pypi_name``, ``conda_name``, ``match_source``.
    """
    cols = ["pypi_name", "conda_name", "match_source"]
    m = pypi_parselmouth_mapping_raw
    if m is None or m.empty or not {"pypi_name", "conda_name"} <= set(m.columns):
        return pd.DataFrame(columns=cols)
    out = m.copy()
    if "match_source" not in out.columns:
        out["match_source"] = "parselmouth"
    else:
        # a missing per-row match_source defaults to parselmouth; a provided tier
        # (incl. g10_spelling) is preserved verbatim.
        out["match_source"] = out["match_source"].fillna("parselmouth")
    # restrict to conda_names the core pipeline actually enumerated (real feedstocks)
    enum = core_packages_enumerated
    if enum is not None and not enum.empty and "conda_name" in enum.columns:
        valid = set(enum["conda_name"].dropna())
        out = out[out["conda_name"].isin(valid)]
    out = out.drop_duplicates(subset=["pypi_name", "conda_name"])
    return out[cols].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase C.5 — source-URL-derived matches (extends the Phase C mapping)
# ---------------------------------------------------------------------------

def match_source_urls(
    pypi_conda_mapping_base: pd.DataFrame,
    pypi_json_raw: pd.DataFrame,
) -> pd.DataFrame:
    # legacy: Phase C.5  (phase_c5_source_url_match CFA:1802)
    """Extend the Phase C mapping with source-URL-derived matches, honouring the
    **no-clobber** discipline: a ``recipe_source_url`` candidate is added ONLY for a
    ``pypi_name`` not already carried by a protected tier (``parselmouth`` /
    ``recipe_source_url`` / ``g10_spelling``). This is the node that WRITES the final
    ``pypi_conda_mapping``.

    ``pypi_json_raw`` supplies the PyPI-side source URLs; rows carrying a resolved
    ``conda_name`` (a source-URL match) become ``match_source='recipe_source_url'``
    candidates. Output: ``pypi_name``, ``conda_name``, ``match_source``.
    """
    cols = ["pypi_name", "conda_name", "match_source"]
    base = pypi_conda_mapping_base
    if base is None or base.empty:
        base = pd.DataFrame(columns=cols)
    base = base[[c for c in cols if c in base.columns]].copy()

    # already-mapped pypi_names under a protected tier — never clobber these.
    protected = set(
        base.loc[base["match_source"].isin(_PROTECTED_MATCH_SOURCES), "pypi_name"]
    ) if "match_source" in base.columns else set(base.get("pypi_name", pd.Series(dtype=object)))

    cand = pypi_json_raw
    new_rows = []
    if cand is not None and not cand.empty and {"pypi_name", "conda_name"} <= set(cand.columns):
        for pypi_name, conda_name in zip(cand["pypi_name"], cand["conda_name"]):
            if pypi_name in protected:
                continue  # no-clobber
            # skip missing OR non-string conda_name (a list/array cell is malformed —
            # scalar-safe: no pd.isna-on-array ValueError, no unhashable-key crash).
            if _is_missing(conda_name) or not isinstance(conda_name, str):
                continue
            new_rows.append((pypi_name, conda_name, "recipe_source_url"))
    extra = pd.DataFrame(new_rows, columns=cols)
    out = pd.concat([base, extra], ignore_index=True)
    out = out.drop_duplicates(subset=["pypi_name", "conda_name"])
    return out[cols].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase D — PyPI universe enumeration
# ---------------------------------------------------------------------------

def enumerate_pypi_universe(pypi_simple_index_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase D  (phase_d_pypi_enumeration CFA:1947)
    """Normalize the PyPI simple index into the ``pypi_universe`` frame (7 d TTL upsert
    at the dataset level). The universe upsert is **skippable** (consumer profile /
    ``PHASE_D_UNIVERSE_DISABLED=1``, AD-6 job config) — when disabled the dataset
    yields nothing and this node degrades cleanly to an empty columned frame (AD-13).
    Input: ``pypi_name`` (+ optional ``last_serial``). Output: ``pypi_name``,
    ``last_serial``."""
    cols = ["pypi_name", "last_serial"]
    idx = pypi_simple_index_raw
    if idx is None or idx.empty or "pypi_name" not in getattr(idx, "columns", []):
        return pd.DataFrame(columns=cols)
    out = idx.copy()
    if "last_serial" not in out.columns:
        out["last_serial"] = pd.NA
    out = out.drop_duplicates(subset=["pypi_name"])
    return out[cols].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase H — current-version fetch (serial-gated)  [AC-5]
# ---------------------------------------------------------------------------

# The 3 serial-gate conditions as SHARED predicates (review-hardening: the node AND the
# stats split now derive from ONE source of truth — no silent drift, CFA:4177-4189).

def _never_fetched(serial_at_fetch) -> bool:
    return _is_missing(serial_at_fetch)


def _serial_moved(serial_at_fetch, last_serial) -> bool:
    # NULL-safe inequality: a NULL serial_at_fetch is caught by never-fetched; a NULL
    # current serial must NOT spuriously flag moved (`!=` on NaN is always True).
    if _is_missing(serial_at_fetch) or _is_missing(last_serial):
        return False
    # Coerce both sides before comparison (matches _safety_recheck): a Parquet/JSON
    # round-trip can stringify a serial ("5"), and a raw `"5" != 5` would spuriously
    # flag "moved" → a needless full re-fetch at atlas scale (B2 follow-up review).
    saf = pd.to_numeric(serial_at_fetch, errors="coerce")
    last = pd.to_numeric(last_serial, errors="coerce")
    if pd.isna(saf) or pd.isna(last):
        # An uncoercible serial can't be proven equal → fail safe (re-fetch), the
        # pre-coercion behavior for non-numeric values.
        return True
    return last != saf


def _safety_recheck(fetched_at, now: int) -> bool:
    # 30-day safety re-check. A missing OR unparseable fetched_at means no proof of
    # freshness -> re-fetch (fail-safe toward re-fetch; never crash on a bad stamp).
    fetched_num = pd.to_numeric(fetched_at, errors="coerce")
    if pd.isna(fetched_num):
        return True
    return (now - int(fetched_num)) >= _PHASE_H_SAFETY_RECHECK_SECONDS


def _phase_h_eligibility(row_serial_at_fetch, row_last_serial, row_fetched_at, now: int) -> bool:
    """The 3-condition Phase H serial gate (CFA:4177-4189): eligible iff never-fetched
    OR serial-moved OR 30-day safety re-check. NULL-safe (CFA:4223-4231)."""
    return bool(
        _never_fetched(row_serial_at_fetch)
        or _serial_moved(row_serial_at_fetch, row_last_serial)
        or _safety_recheck(row_fetched_at, now)
    )


def phase_h_eligibility_stats(pypi_json_raw: pd.DataFrame, now: int | None = None) -> dict:
    """Split the eligible set into its three branches (legacy ``_phase_h_eligibility_stats``
    CFA:4135): ``eligible_never_fetched`` / ``eligible_serial_moved`` /
    ``eligible_safety_recheck`` (+ ``total`` / ``eligible``). Uses the SAME predicates as
    :func:`_phase_h_eligibility` (no drift). A row can satisfy more than one branch;
    branch counts use first-match precedence (never-fetched > serial-moved >
    safety-recheck) so they sum to ``eligible``."""
    if now is None:
        now = int(time.time())
    df = pypi_json_raw
    stats = {
        "total": 0,
        "eligible": 0,
        "eligible_never_fetched": 0,
        "eligible_serial_moved": 0,
        "eligible_safety_recheck": 0,
    }
    if df is None or df.empty or "pypi_name" not in getattr(df, "columns", []):
        return stats
    stats["total"] = len(df)
    for _, r in df.iterrows():
        saf = r.get("pypi_version_serial_at_fetch")
        last = r.get("pypi_last_serial")
        fetched = r.get("fetched_at")
        never = _never_fetched(saf)
        moved = _serial_moved(saf, last)
        recheck = _safety_recheck(fetched, now)
        if not (never or moved or recheck):
            continue
        stats["eligible"] += 1
        if never:
            stats["eligible_never_fetched"] += 1
        elif moved:
            stats["eligible_serial_moved"] += 1
        else:
            stats["eligible_safety_recheck"] += 1
    return stats


def fetch_pypi_current_versions(
    pypi_json_raw: pd.DataFrame,
    pypi_universe: pd.DataFrame,
    now: int | None = None,
) -> pd.DataFrame:
    # legacy: Phase H  (phase_h_pypi_versions CFA:4517; _phase_h_eligible_pypi_names CFA:4174)
    """Stamp the current version for the serial-gated eligible set.

    **AC-5 — the serial gate.** ``pypi_json_raw`` is the already-fetched, ACTIONABLE
    slice (the fan-out is bounded at dataset level to ``v_actionable_packages WHERE
    pypi_name IS NOT NULL``); this node NEVER iterates ``pypi_universe`` (where the
    pypi-only rows live post-v20) — it only LEFT-JOINs it for the authoritative current
    ``pypi_last_serial``. That structural choice is the denominator discipline
    (CFA:4224-4225): pypi-only rows are never re-included (the pre-v7.9.0 6-hour cold-run
    bug the gate must not reintroduce).

    Eligibility = never-fetched OR serial-moved OR 30-day safety re-check
    (CFA:4177-4189, NULL-safe CFA:4223-4231). On fetch, ``pypi_version_serial_at_fetch``
    is stamped to the current ``pypi_last_serial`` (CFA:4293/4321/4476). **RETAIN
    ``upload_time_iso_8601``** per the current release — B9/FR-20 (``release_lag_hours``)
    consumes it downstream with NO new fetch (spec:680).

    Returns the **eligible delta** only. The catalog sink
    (``IncrementalParquetDataset`` with ``merge_on: pypi_name``) upserts that
    delta into the prior store so fresh rows are not deleted (AUD-ATLAS-015).
    Kedro forbids the same dataset as both node input and output, so the merge
    lives at the dataset boundary.

    Input ``pypi_json_raw``: ``pypi_name``, ``version``, optional ``pypi_last_serial``,
    ``pypi_version_serial_at_fetch`` (prior), ``fetched_at`` (prior), ``upload_time_iso_8601``.
    ``pypi_universe``: ``pypi_name``, ``last_serial``. Output ``pypi_current_versions``:
    ``pypi_name``, ``version``, ``pypi_last_serial``, ``pypi_version_serial_at_fetch``,
    ``upload_time_iso_8601``.
    """
    if now is None:
        now = int(time.time())
    cols = [
        "pypi_name",
        "version",
        "pypi_last_serial",
        "pypi_version_serial_at_fetch",
        "upload_time_iso_8601",
    ]
    df = pypi_json_raw
    # scope: iterate ONLY the actionable pypi_json_raw slice (never pypi_universe) —
    # pypi-only rows live in pypi_universe and MUST NOT re-enter the denominator (AC-5,
    # CFA:4224-4225). pypi_universe is joined for the current serial only.
    if df is None or df.empty or "pypi_name" not in getattr(df, "columns", []):
        return pd.DataFrame(columns=cols)
    work = df.copy()
    for c in ("version", "pypi_last_serial", "pypi_version_serial_at_fetch", "upload_time_iso_8601", "fetched_at"):
        if c not in work.columns:
            work[c] = pd.NA

    # authoritative current serial from the universe (left-join; the universe never
    # widens the row set — validate=many_to_one keeps it a pure lookup).
    uni = pypi_universe
    if uni is not None and not uni.empty and {"pypi_name", "last_serial"} <= set(uni.columns):
        serial_map = dict(zip(uni["pypi_name"], uni["last_serial"]))
        work["pypi_last_serial"] = [
            serial_map.get(n, s)
            for n, s in zip(work["pypi_name"], work["pypi_last_serial"])
        ]

    eligible_rows = []
    for _, r in work.iterrows():
        if not _phase_h_eligibility(
            r.get("pypi_version_serial_at_fetch"),
            r.get("pypi_last_serial"),
            r.get("fetched_at"),
            now,
        ):
            continue
        eligible_rows.append(
            {
                "pypi_name": r["pypi_name"],
                "version": r.get("version"),
                "pypi_last_serial": r.get("pypi_last_serial"),
                # stamp serial_at_fetch to the current serial ON fetch (CFA:4293).
                "pypi_version_serial_at_fetch": r.get("pypi_last_serial"),
                # RETAIN upload_time_iso_8601 for B9 (do NOT discard after info.version).
                "upload_time_iso_8601": r.get("upload_time_iso_8601"),
            }
        )
    return pd.DataFrame(eligible_rows, columns=cols).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase O — serial snapshots (90-day rolling; activity band from deltas)
# ---------------------------------------------------------------------------

def snapshot_pypi_serials(pypi_simple_index_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase O  (phase_o_serial_snapshots CFA:7051)
    """Classify per-project activity from serial-snapshot deltas (NO HTTP in the node
    — the snapshot history is dataset-owned, 90-day rolling). Input: ``pypi_name``,
    ``last_serial``, ``prev_serial`` (the prior snapshot's serial, may be NULL for a
    first observation). Output: ``pypi_name``, ``last_serial``, ``serial_delta``,
    ``activity_band`` (``high`` / ``medium`` / ``low`` / ``dormant``)."""
    cols = ["pypi_name", "last_serial", "serial_delta", "activity_band"]
    idx = pypi_simple_index_raw
    if idx is None or idx.empty or "pypi_name" not in getattr(idx, "columns", []):
        return pd.DataFrame(columns=cols)
    out = idx.copy()
    if "last_serial" not in out.columns:
        out["last_serial"] = pd.NA
    if "prev_serial" not in out.columns:
        out["prev_serial"] = pd.NA

    def _delta(last, prev):
        # numeric-coerce so a non-numeric serial degrades to NA (dormant) instead of
        # crashing int() (review-hardening).
        last_n = pd.to_numeric(last, errors="coerce")
        prev_n = pd.to_numeric(prev, errors="coerce")
        if pd.isna(last_n) or pd.isna(prev_n):
            return pd.NA
        return int(last_n) - int(prev_n)

    def _band(delta):
        if delta is pd.NA or pd.isna(delta):
            return "dormant"
        d = int(delta)
        if d >= 100:
            return "high"
        if d >= 10:
            return "medium"
        if d >= 1:
            return "low"
        return "dormant"

    out["serial_delta"] = [_delta(l, p) for l, p in zip(out["last_serial"], out["prev_serial"])]
    out["activity_band"] = [_band(d) for d in out["serial_delta"]]
    out = out.drop_duplicates(subset=["pypi_name"])
    return out[cols].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase P — monthly download counts (BigQuery; the two-layer cost gate is
#           DATASET-owned, this node stays PURE)  [AC-4]
# ---------------------------------------------------------------------------

def fetch_pypi_downloads(pypi_bigquery_downloads_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase P  (phase_p_pypi_downloads CFA:7352)
    """Normalize the already-fetched monthly-download frame. **The node stays PURE**:
    the two-layer BigQuery cost gate (dry-run preflight above cap + ``maximum_bytes_billed``
    + ``PHASE_P_JOB_TIMEOUT_MS`` + literal-TIMESTAMP bounds, D1) lives in the request
    DATASET (``BigQueryDownloadsDataset``, THE CRUX). If ``PHASE_P_ENABLED`` is unset OR
    the dry-run aborts above cap, the dataset yields no rows and this node no-ops
    (mode-machine ``_phase_p_skip`` CFA:7342). AD-6: never a default schedule.

    ``INSERT OR IGNORE`` idempotency → drop duplicate ``(pypi_name, month)`` rows.
    Input: ``pypi_name``, ``month``, ``downloads``. Output ``pypi_downloads_monthly``:
    same columns, deduped."""
    cols = ["pypi_name", "month", "downloads"]
    df = pypi_bigquery_downloads_raw
    if df is None or getattr(df, "empty", True) or "pypi_name" not in getattr(df, "columns", []):
        return pd.DataFrame(columns=cols)
    out = df.copy()
    for c in ("month", "downloads"):
        if c not in out.columns:
            out[c] = pd.NA
    # INSERT OR IGNORE idempotency (CFA): first write per (pypi_name, month) wins.
    out = out.drop_duplicates(subset=["pypi_name", "month"], keep="first")
    return out[cols].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase Q — cross-channel flags
# ---------------------------------------------------------------------------

def flag_cross_channel(pypi_cross_channel_repodata_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase Q  (phase_q_cross_channel CFA:7847)
    """Pivot bulk cross-channel repodata into per-channel ``in_<channel>`` BOOLs.

    **Gap G-2(B2) decision**: the multi-channel fan-out is DATASET-owned (one
    runtime-parameterized entry + a dataset-owned loop over the channels), so the node
    receives ONE already-combined frame carrying a ``channel`` column and stays pure —
    no factory/partitioned dataset needed. Input: ``conda_name``, ``channel`` (one of
    bioconda/pytorch/nvidia/robostack). Output: ``conda_name`` + ``in_bioconda`` /
    ``in_pytorch`` / ``in_nvidia`` / ``in_robostack`` BOOLs (one row per conda_name)."""
    out_cols = ["conda_name"] + [f"in_{c}" for c in _CROSS_CHANNELS]
    df = pypi_cross_channel_repodata_raw
    if df is None or df.empty or not {"conda_name", "channel"} <= set(df.columns):
        return pd.DataFrame(columns=out_cols)
    rows = {}
    for conda_name, channel in zip(df["conda_name"], df["channel"]):
        # skip missing OR non-string conda_name (a list/array cell is malformed — no
        # pd.isna-on-array ValueError, no unhashable-dict-key crash).
        if _is_missing(conda_name) or not isinstance(conda_name, str):
            continue
        flags = rows.setdefault(conda_name, {f"in_{c}": False for c in _CROSS_CHANNELS})
        if channel in _CROSS_CHANNELS:
            flags[f"in_{channel}"] = True
    records = [{"conda_name": name, **flags} for name, flags in rows.items()]
    out = pd.DataFrame(records, columns=out_cols)
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase R — enrichment (single-write-path helpers shared with add-handoff)
# ---------------------------------------------------------------------------

def _classify_packaging_shape(row) -> str:
    """Deterministic packaging-shape classification (pure; CFA:8330 Phase R). Reads
    already-fetched hints on the row (``has_ext_modules`` / ``wheel_tags`` / ``rust``)
    — no IO."""
    tags = row.get("wheel_tags")
    tag_str = " ".join(tags) if isinstance(tags, (list, tuple)) else str(tags or "")
    if row.get("rust") or "pyo3" in tag_str.lower():
        return "rust-pyo3"
    if "none-any" in tag_str or row.get("pure_python") is True:
        return "pure-python"
    if row.get("cython"):
        return "cython"
    if row.get("has_ext_modules"):
        return "c-extension"
    if "none-any" in tag_str:
        return "pure-python"
    return "unknown"


def phase_r_fetch_one(row: dict) -> dict:
    """The per-package enrichment worker (legacy ``_phase_r_fetch_one`` CFA:8146) —
    the shared read/normalize step Phase R AND the S6 ``add-handoff`` CLI both call.
    Pure: transforms one already-fetched PyPI-JSON record into the enriched shape."""
    r = dict(row)
    out = {
        "pypi_name": r.get("pypi_name"),
        "packaging_shape": _classify_packaging_shape(r),
        "license_spdx": r.get("license_spdx"),
        "license_raw": r.get("license_raw"),
        # notes are an operator-override column — carried through verbatim (never
        # synthesised here); Phase S merges them across re-runs (AC-5).
        "notes": r.get("notes"),
    }
    return out


def phase_r_upsert_one(existing: pd.DataFrame, new_row: dict) -> pd.DataFrame:
    """**Single-write-path** (AC-2): upsert ONE enriched package into the frame
    (legacy ``phase_r_upsert_one`` CFA:8198). Phase R maps this over the candidate
    slice; the S6 ``add-handoff`` CLI re-scoring path calls the SAME helper for a
    single package — so a one-package re-score flows through identical code. Replaces
    the existing row for ``pypi_name`` (keeping the new enrichment) and appends a new
    one otherwise."""
    cols = ["pypi_name", "packaging_shape", "license_spdx", "license_raw", "notes"]
    base = existing if existing is not None and not existing.empty else pd.DataFrame(columns=cols)
    base = base[[c for c in cols if c in base.columns]].copy()
    for c in cols:
        if c not in base.columns:
            base[c] = pd.NA
    name = new_row.get("pypi_name")
    # replace-by-key; when the key itself is missing, drop any prior missing-key row so
    # a None/NaN pypi_name replaces (never duplicates) — `!= None` would keep it.
    if _is_missing(name):
        base = base[~base["pypi_name"].apply(_is_missing)]
    else:
        base = base[base["pypi_name"] != name]
    row = {c: new_row.get(c) for c in cols}
    out = pd.concat([base, pd.DataFrame([row], columns=cols)], ignore_index=True)
    return out[cols]


def enrich_pypi_intelligence(pypi_json_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase R  (phase_r_pypi_json_enrich CFA:8330)
    """Enrich the top-N candidate slice (bounded at dataset level) through the shared
    single-write-path helpers (``phase_r_fetch_one`` + ``phase_r_upsert_one``, CFA:8146/8198).
    Input ``pypi_json_raw`` (candidate slice). Output ``pypi_intelligence_enriched``:
    ``pypi_name``, ``packaging_shape``, ``license_spdx``, ``license_raw``, ``notes``."""
    cols = ["pypi_name", "packaging_shape", "license_spdx", "license_raw", "notes"]
    df = pypi_json_raw
    if df is None or df.empty or "pypi_name" not in getattr(df, "columns", []):
        return pd.DataFrame(columns=cols)
    # AUD-ATLAS-028: collect then one concat — avoid O(N²) phase_r_upsert_one
    # concat-in-loop. Last-wins per pypi_name matches upsert semantics.
    rows = [phase_r_fetch_one(r.to_dict()) for _, r in df.iterrows()]
    out = pd.DataFrame(rows, columns=cols)
    out = out.drop_duplicates(subset=["pypi_name"], keep="last")
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase S — readiness scoring (single-write-path; notes survive re-runs)
# ---------------------------------------------------------------------------

_TEMPLATE_BY_SHAPE = {
    "pure-python": "python/noarch-recipe.yaml",
    "c-extension": "python/compiled-recipe.yaml",
    "cython": "python/compiled-recipe.yaml",
    "rust-pyo3": "python/maturin-recipe.yaml",
    "unknown": "python/noarch-recipe.yaml",
}


def _readiness_score(shape: str, license_spdx) -> int:
    """Composite ``conda_forge_readiness`` (0-100). Pure; a licensed pure-python
    package scores highest, an unknown/unlicensed one lowest."""
    score = 40
    if shape == "pure-python":
        score += 40
    elif shape in ("c-extension", "cython", "rust-pyo3"):
        score += 20
    if license_spdx is not None and not (isinstance(license_spdx, float) and pd.isna(license_spdx)) and str(license_spdx).strip():
        score += 20
    return max(0, min(100, score))


def apply_readiness_scores(
    enriched: pd.DataFrame, prior_scored: pd.DataFrame | None = None
) -> pd.DataFrame:
    """**Single-write-path** (AC-2): the shared scorer Phase S AND the S6 ``add-handoff``
    CLI re-score through (legacy ``apply_readiness_scores`` CFA:8484/8489). Computes
    ``conda_forge_readiness`` (0-100) + ``recommended_template`` per row.

    **notes operator overrides survive re-runs** (AC-5): a re-score MERGES the notes
    column from ``prior_scored`` (and from the enriched frame) — it NEVER clobbers an
    operator override. Enriched-frame notes take precedence when present; otherwise the
    prior score's notes are preserved."""
    cols = ["pypi_name", "packaging_shape", "conda_forge_readiness", "recommended_template", "notes"]
    df = enriched
    if df is None or df.empty or "pypi_name" not in getattr(df, "columns", []):
        return pd.DataFrame(columns=cols)
    prior_notes = {}
    if prior_scored is not None and not prior_scored.empty and {"pypi_name", "notes"} <= set(prior_scored.columns):
        prior_notes = dict(zip(prior_scored["pypi_name"], prior_scored["notes"]))

    records = []
    for _, r in df.iterrows():
        shape = r.get("packaging_shape")
        # NaN is truthy, so `shape or "unknown"` would leak NaN into the output +
        # score/template lookup — coerce missing/empty to "unknown" explicitly.
        if _is_missing(shape) or not shape:
            shape = "unknown"
        name = r.get("pypi_name")
        enriched_note = r.get("notes")
        # notes merge: enriched override wins; else preserve prior operator note.
        note = enriched_note
        if note is None or (isinstance(note, float) and pd.isna(note)):
            note = prior_notes.get(name)
        records.append(
            {
                "pypi_name": name,
                "packaging_shape": shape,
                "conda_forge_readiness": _readiness_score(shape, r.get("license_spdx")),
                "recommended_template": _TEMPLATE_BY_SHAPE.get(shape, _TEMPLATE_BY_SHAPE["unknown"]),
                "notes": note,
            }
        )
    return pd.DataFrame(records, columns=cols).reset_index(drop=True)


def score_pypi_readiness(pypi_intelligence_enriched: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase S  (phase_s_computed_scores CFA:8546)
    """Score the enriched frame via the shared ``apply_readiness_scores`` single-write-
    path (CFA:8484). Emits ``conda_forge_readiness`` (0-100) + ``recommended_template``;
    ``notes`` operator overrides survive re-runs. Output ``pypi_intelligence_scored``."""
    return apply_readiness_scores(pypi_intelligence_enriched)


# ---------------------------------------------------------------------------
# View contracts (query-time-correct read surfaces — documented view-equivalents)
# ---------------------------------------------------------------------------

def v_pypi_intelligence_valid(pypi_intelligence_scored: pd.DataFrame) -> pd.DataFrame:
    """``v_pypi_intelligence_valid`` (CFA:615) — the query-time-correct read surface
    for scored PyPI intelligence. Consumers read the VIEW, never the raw scored table
    (AC-2). Validity filter: a package with a known packaging shape and a computed
    readiness score. Kept as a documented view-equivalent transform (not a pipeline
    node) so B2 preserves the discipline without minting an extra output."""
    df = pypi_intelligence_scored
    if df is None or df.empty:
        return pd.DataFrame(columns=getattr(df, "columns", []))
    # a frame missing the scored columns has no valid rows to surface (guard against a
    # KeyError on a mis-shaped non-empty frame — review-hardening).
    if not {"packaging_shape", "conda_forge_readiness"} <= set(df.columns):
        return df.iloc[0:0].reset_index(drop=True)
    valid = df["packaging_shape"].notna() & (df["packaging_shape"] != "unknown") & df["conda_forge_readiness"].notna()
    return df[valid].reset_index(drop=True)


# ---------------------------------------------------------------------------
# update-mapping-cache — the Q6 flat-cache EXPORT shim (§ 3.4, Story B5)
# ---------------------------------------------------------------------------

# Provenance precedence for the flat-cache collapse (no-clobber): a protected tier
# (the g10_spelling writeback + parselmouth/recipe_source_url) always wins over a
# weaker/unknown match; g10_spelling is ranked highest so it provably SURVIVES a
# collision (AC-4). Non-protected/unknown match_source -> rank 1.
_MAP_PROVENANCE_RANK = {"g10_spelling": 3, "parselmouth": 2, "recipe_source_url": 2}


def export_pypi_conda_map(pypi_conda_mapping: pd.DataFrame) -> dict:
    # legacy: update-mapping-cache  (mapping_manager.py; Q6-consolidated onto Phase C)
    """Q6 consolidation shim: export the migrated Phase C mapping (``pypi_conda_mapping``)
    to the flat ``pypi_conda_map.json`` cache (``pypi_conda_map_store``). This REPLACES the
    legacy ``update-mapping-cache`` fetch (regro/cf-graph + conda-forge-metadata API) with a
    read of the already-built LOCAL Phase C dataset — so the mapping refresh is offline-safe
    by construction (Q6 benefit; AD-13 trivially satisfied for the mapping store).

    Single writer of ``pypi_conda_map_store``. **Preserves ``g10_spelling`` provenance +
    no-clobber (AD-10):** collapsing to one ``conda_name`` per ``pypi_name``, the winning row
    is the highest-provenance match — a protected tier (g10_spelling / parselmouth /
    recipe_source_url) is NEVER clobbered by a weaker one, and g10_spelling survives a tie.

    The re-point of ``name_resolver.py`` / ``recipe-generator.py`` at Phase C directly is a
    read-only ``.claude/**`` follow-up (DW-B5-1); until then this flat file is the retained
    compatibility shim, in the legacy ``{pypi_name: conda_name}`` format. The MERGE onto the
    last-good cache (Phase C wins; old-only keys retained) + the keep-last-good-on-empty
    discipline (AD-13) live in ``MappingCacheDataset.save`` — this node returns the export.
    """
    df = pypi_conda_mapping
    if df is None or df.empty or not {"pypi_name", "conda_name"} <= set(df.columns):
        return {}
    has_source = "match_source" in df.columns
    out: dict[str, str] = {}
    ranks: dict[str, int] = {}
    for row in df.itertuples(index=False):
        pypi_name = getattr(row, "pypi_name", None)
        conda_name = getattr(row, "conda_name", None)
        if _is_missing(pypi_name) or _is_missing(conda_name) or not isinstance(conda_name, str):
            continue
        pypi_name = str(pypi_name)
        match_source = getattr(row, "match_source", None) if has_source else None
        # match_source may be a non-string / unhashable cell (malformed) — default rank 1.
        rank = _MAP_PROVENANCE_RANK.get(match_source, 1) if isinstance(match_source, str) else 1
        # no-clobber: replace on STRICTLY higher provenance; on an EQUAL-tier collision with
        # a different conda_name, keep the lexicographically smaller name — a deterministic
        # tie-break so the export is reproducible regardless of Phase C row order.
        if (
            pypi_name not in out
            or rank > ranks[pypi_name]
            or (rank == ranks[pypi_name] and conda_name < out[pypi_name])
        ):
            out[pypi_name] = conda_name
            ranks[pypi_name] = rank
    return out
