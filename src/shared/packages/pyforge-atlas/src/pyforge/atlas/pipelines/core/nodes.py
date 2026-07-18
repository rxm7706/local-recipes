"""``core`` pipeline nodes — the conda-side backbone (Story B1, § 5.2 / AD-3).

PURE functions: ``pandas.DataFrame`` in → ``pandas.DataFrame`` out, NO inline IO
(THE CRUX — ``tests/catalog/test_no_inline_io.py`` bans HTTP/DB clients across the
whole package). Fetch / rate-limiting / TTL are dataset concerns (AD-2 / AD-5); a
node receives already-fetched frames via the catalog and only transforms them.

Each node carries a ``# legacy: Phase <ID>`` provenance comment (spine naming
convention). Legacy source = ``.claude/skills/conda-forge-expert/scripts/
conda_forge_atlas.py`` (``CFA``) @ commit b18cbb5, at the cited lines; the binding
per-phase contracts are cf-atlas-legacy ``references/engineering-contracts.md``.
"""

from __future__ import annotations

import re

import pandas as pd

# Clean Python-version token (Phase F ``pkg_python`` regex-filter — the dirty column
# carries values like "", "unknown", "3" that must be dropped before aggregation).
_CLEAN_PYVER = re.compile(r"^\d+\.\d+$")

# ms-vs-seconds magnitude split (mirrors IncrementalParquetDataset._MS_EPOCH_THRESHOLD).
_MS_THRESHOLD = 1_000_000_000_000


def _as_bool_series(col: pd.Series) -> pd.Series:
    """Coerce a possibly string/NaN boolean column to real booleans. A bare
    ``.astype(bool)`` turns the STRING ``"false"`` into ``True`` (a silent inversion of
    the archived-feedstock filter) — this maps the common truthy string forms explicitly
    and treats nulls as ``False``."""
    if col.dtype == bool:
        return col.fillna(False)

    def _one(v):
        if isinstance(v, bool):
            return v
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return False
        return str(v).strip().lower() in ("true", "1", "t", "yes")

    return col.map(_one).astype(bool)


# ---------------------------------------------------------------------------
# Phase B — conda package enumeration
# ---------------------------------------------------------------------------

def enumerate_conda_packages(
    core_repodata_raw: pd.DataFrame,
    core_channeldata_raw: pd.DataFrame,
) -> pd.DataFrame:
    # legacy: Phase B  (phase_b_conda_enumeration CFA:1408; view v_actionable_packages CFA:376)
    """Enumerate conda-forge packages from current repodata + channeldata.

    # scope: the raw `packages` read carries the v_actionable scope discipline — the
    # enumerated frame is the population the downstream persona filter
    # (conda_name IS NOT NULL AND latest_status='active' AND NOT feedstock_archived)
    # narrows; Phase B itself enumerates the raw channel and is the scope's source
    # of truth (CFA:376-381), so it does not pre-filter.

    Input columns (repodata): ``conda_name``, ``version``, ``timestamp`` (per-build,
    MILLISECONDS in repodata), optional ``subdir``. Channeldata supplies the
    channel-level ``subdirs`` per package. Output: one row per ``conda_name`` with
    ``latest_version`` (newest build, chosen via the repodata ms ``timestamp``
    normalized to seconds — DW-A3-P10 "convert once") + ``subdirs``. This is a plain
    intermediate Parquet output (no TTL stamp — the fetched_at boundary normalization
    is owned by the IncrementalParquetDataset download outputs, Phase F/I).
    """
    repo = core_repodata_raw
    if repo is None or repo.empty or not {"conda_name", "version"} <= set(repo.columns):
        return pd.DataFrame(columns=["conda_name", "latest_version", "subdirs"])

    df = repo.copy()
    # Newest build per package wins latest_version (order by version string is not
    # semver-correct; the legacy path keys on the repodata timestamp — newest build).
    ts = pd.to_numeric(df.get("timestamp"), errors="coerce") if "timestamp" in df else None
    if ts is not None:
        # ms → s boundary normalization (repodata per-build timestamps are ms).
        ts_sec = ts.where(ts < _MS_THRESHOLD, ts // 1000)
        df["_ts"] = ts_sec
        # na_position='first' so a NaN/unparseable timestamp does NOT sort last and
        # win `last` (a missing timestamp must not masquerade as the newest build).
        df = df.sort_values("_ts", na_position="first")
    latest = df.groupby("conda_name", as_index=False).agg(
        latest_version=("version", "last"),
    )

    if core_channeldata_raw is not None and "subdirs" in getattr(core_channeldata_raw, "columns", []):
        cd = core_channeldata_raw[["conda_name", "subdirs"]].drop_duplicates("conda_name")
        latest = latest.merge(cd, on="conda_name", how="left")
    else:
        latest["subdirs"] = None
    return latest.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase B.5 — feedstock attribution
# ---------------------------------------------------------------------------

def _pick_feedstock(pkg_name: str, feedstocks: list[str] | None) -> str | None:
    # legacy: Phase B.5  (_pick_feedstock CFA:1572; logic CFA:1586-1590; call CFA:1632)
    """Umbrella-vs-dedicated attribution (the exact legacy rule, CFA:1586-1590):

    - empty / no feedstocks → ``None``;
    - more than one feedstock AND ``pkg_name`` is one of them → the DEDICATED
      feedstock named exactly ``pkg_name`` (e.g. a split-out ``dbt-bigquery`` output
      → the ``dbt-bigquery`` feedstock, NOT the ``dbt`` umbrella);
    - otherwise → the first feedstock.
    """
    # A missing cell arrives as a scalar (float NaN / None), NOT [] — and NaN is
    # truthy, so `if not feedstocks` does NOT catch it. Normalize any non-sequence
    # (NaN/None) to empty, and a bare string to a single-element list.
    if isinstance(feedstocks, str):
        feedstocks = [feedstocks]
    if not isinstance(feedstocks, (list, tuple)) or len(feedstocks) == 0:
        return None
    if len(feedstocks) > 1 and pkg_name in feedstocks:
        return pkg_name
    return feedstocks[0]


def attribute_feedstocks(core_feedstock_outputs_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase B.5  (phase_b5_feedstock_outputs CFA:1593)
    """Attribute each conda package (output) to its feedstock via
    :func:`_pick_feedstock`. Input: ``conda_name`` + ``feedstocks`` (a list per row,
    the 1:N feedstock-outputs map). Output: ``conda_name``, ``feedstock_name``."""
    src = core_feedstock_outputs_raw
    if src is None or src.empty or not {"conda_name", "feedstocks"} <= set(src.columns):
        return pd.DataFrame(columns=["conda_name", "feedstock_name"])
    out = src.copy()
    out["feedstock_name"] = [
        _pick_feedstock(name, fs)
        for name, fs in zip(out["conda_name"], out["feedstocks"])
    ]
    return out[["conda_name", "feedstock_name"]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase B.6 — latest-status (LITE: presence → active; NO per-version yanked scan)
# ---------------------------------------------------------------------------

def detect_latest_status(
    core_repodata_raw: pd.DataFrame,
    core_channeldata_raw: pd.DataFrame,
) -> pd.DataFrame:
    # legacy: Phase B.6  (phase_b6_yanked_detection CFA:1665)
    """LITE semantics (AC-6): a package present in the current repodata is
    ``latest_status='active'``. Full per-version yanked detection is an explicit
    follow-on, NOT part of this story (spec § 12). Output: ``conda_name``,
    ``latest_status``."""
    repo = core_repodata_raw
    if repo is None or repo.empty:
        return pd.DataFrame(columns=["conda_name", "latest_status"])
    names = pd.Index(repo["conda_name"].dropna().unique(), name="conda_name")
    return pd.DataFrame({"conda_name": names, "latest_status": "active"}).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase F — downloads (provenance discipline)
# ---------------------------------------------------------------------------

def compute_downloads(
    core_anaconda_downloads_raw: pd.DataFrame,
    core_s3_download_stats_raw: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # legacy: Phase F  (phase_f_downloads CFA:3560; contracts 188/538/549/572/3162/3423-3450)
    """Compute download totals + the three breakdown tables, preserving the Phase F
    provenance discipline (engineering-contracts § Phase F):

    - ``downloads_source`` per row ∈ {``anaconda-api``, ``s3-parquet``} — the
      two are correlated-but-distinct MEASUREMENTS, never interchangeable and
      never summed (double-count). The value is the s3 total where s3 has the
      package, else the anaconda fallback; the per-row tag reflects whichever
      dataset populated the value. The run-summary label ``merged`` (auto path
      mixed both sources in a run) is NEVER written per row (CFA:189-193).
    - The three breakdown tables (platform / pyver / channel) are written ONLY on the
      s3-parquet path (CFA:538/549/572); the anaconda-api fallback never touches them
      → empty (but correctly-columned) frames.
    - ``downloads_30d`` = the latest CALENDAR month's downloads, NOT a rolling window
      (CFA:3162) — parquet is monthly, so it is the single most-recent month.
    - The dirty ``pkg_python`` column is regex-filtered before the pyver aggregation.
    - This is one consolidated pyarrow-style sweep (do not split passes); the
      replace-by-scope-key WRITE is dataset-owned (the node returns full frames).

    Returns ``(core_downloads, platform_breakdown, pyver_breakdown, channel_breakdown)``.
    """
    ana = core_anaconda_downloads_raw
    s3 = core_s3_download_stats_raw
    _ana_cols = {"conda_name", "downloads"}
    _s3_cols = {"conda_name", "month", "platform", "pyver", "channel", "downloads"}
    ana_present = ana is not None and not ana.empty and _ana_cols <= set(ana.columns)
    s3_present = s3 is not None and not s3.empty and _s3_cols <= set(s3.columns)

    plat_cols = ["conda_name", "platform", "downloads"]
    pyver_cols = ["conda_name", "pyver", "downloads"]
    chan_cols = ["conda_name", "channel", "downloads"]
    platform_breakdown = pd.DataFrame(columns=plat_cols)
    pyver_breakdown = pd.DataFrame(columns=pyver_cols)
    channel_breakdown = pd.DataFrame(columns=chan_cols)

    parts: dict[str, pd.DataFrame] = {}

    if ana_present:
        ana_tot = ana.groupby("conda_name", as_index=False)["downloads"].sum()
        ana_tot = ana_tot.rename(columns={"downloads": "downloads_total"})
        parts["anaconda-api"] = ana_tot

    if s3_present:
        s3_tot = s3.groupby("conda_name", as_index=False)["downloads"].sum()
        s3_tot = s3_tot.rename(columns={"downloads": "downloads_total"})
        parts["s3-parquet"] = s3_tot

        # downloads_30d = latest CALENDAR month (not rolling). month is YYYY-MM.
        latest_month = s3["month"].max()
        last = s3[s3["month"] == latest_month]
        d30 = last.groupby("conda_name", as_index=False)["downloads"].sum()
        d30 = d30.rename(columns={"downloads": "downloads_30d"})

        # Breakdown tables — s3-parquet path ONLY.
        platform_breakdown = (
            s3.groupby(["conda_name", "platform"], as_index=False)["downloads"].sum()
        )[plat_cols]
        # regex-filter the dirty pkg_python column BEFORE aggregation.
        clean = s3[s3["pyver"].astype(str).str.match(_CLEAN_PYVER)]
        pyver_breakdown = (
            clean.groupby(["conda_name", "pyver"], as_index=False)["downloads"].sum()
        )[pyver_cols]
        channel_breakdown = (
            s3.groupby(["conda_name", "channel"], as_index=False)["downloads"].sum()
        )[chan_cols]
    else:
        d30 = None

    # Assemble core_downloads with per-package downloads_source.
    if s3_present and ana_present:
        merged = parts["s3-parquet"].merge(
            parts["anaconda-api"], on="conda_name", how="outer", suffixes=("_s3", "_ana")
        )
        # prefer s3 total where present, else anaconda
        # A 'merged' row prefers the granular s3 total (falling back to anaconda where
        # s3 is absent). The two are correlated MEASUREMENTS of the same downloads, NOT
        # additive — summing would double-count (CFA:188 "correlated-but-distinct"). The
        # downloads_source label preserves which source the value came from.
        merged["downloads_total"] = merged["downloads_total_s3"].fillna(merged["downloads_total_ana"])
        # Per-row provenance reflects the dataset that ACTUALLY populated
        # downloads_total (s3 preferred, anaconda fallback) — the legacy contract
        # is downloads_source ∈ {'s3-parquet', 'anaconda-api'} PER ROW; 'merged'
        # is a run-summary label the schema explicitly NEVER writes per row
        # (CFA:189-193). A both-present package whose value came from s3 is
        # 's3-parquet'; only a row that fell back to anaconda is 'anaconda-api'.
        merged["downloads_source"] = merged["downloads_total_s3"].notna().map(
            {True: "s3-parquet", False: "anaconda-api"}
        )
        downloads = merged[["conda_name", "downloads_total", "downloads_source"]]
    elif s3_present:
        downloads = parts["s3-parquet"].copy()
        downloads["downloads_source"] = "s3-parquet"
    elif ana_present:
        downloads = parts["anaconda-api"].copy()
        downloads["downloads_source"] = "anaconda-api"
    else:
        empty = pd.DataFrame(columns=["conda_name", "downloads_total", "downloads_30d", "downloads_source"])
        return empty, platform_breakdown, pyver_breakdown, channel_breakdown

    if d30 is not None:
        downloads = downloads.merge(d30, on="conda_name", how="left")
    else:
        downloads["downloads_30d"] = pd.NA

    downloads = downloads[["conda_name", "downloads_total", "downloads_30d", "downloads_source"]]
    return (
        downloads.reset_index(drop=True),
        platform_breakdown.reset_index(drop=True),
        pyver_breakdown.reset_index(drop=True),
        channel_breakdown.reset_index(drop=True),
    )


# ---------------------------------------------------------------------------
# Phase I — per-version download history (PROMOTED to an explicit node, AC-3)
# ---------------------------------------------------------------------------

def compute_version_download_history(core_anaconda_downloads_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase I  (promoted from Phase F side-effect: api CFA:2931 / s3 CFA:3402; table CFA:312-316)
    """Per-version download history as an EXPLICIT declared output (AC-3) — no longer
    an unregistered side-effect of Phase F's anaconda-api path. Consumed downstream by
    Phase G', ``version-downloads``, ``release-cadence`` (which resolve it by catalog
    name, AD-3). Input: ``conda_name``, ``version``, ``downloads``. Output:
    ``conda_name``, ``version``, ``downloads`` aggregated per (package, version)."""
    ana = core_anaconda_downloads_raw
    if ana is None or ana.empty:
        return pd.DataFrame(columns=["conda_name", "version", "downloads"])
    hist = ana.groupby(["conda_name", "version"], as_index=False)["downloads"].sum()
    return hist.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase J — dependency graph (archived-feedstock skip-set filter at the write site)
# ---------------------------------------------------------------------------

def _inactive_feedstocks(cf_graph: pd.DataFrame) -> set[str]:
    """Build the archived/inactive feedstock skip-set (v7.9.0 fix; spec § 3.3
    "Phases J + M archived-feedstock filter") — the set is built at the write site
    BEFORE emitting edges, so archived feedstocks never pollute the graph."""
    if "feedstock_archived" not in cf_graph.columns or "feedstock_name" not in cf_graph.columns:
        return set()
    archived = cf_graph[_as_bool_series(cf_graph["feedstock_archived"])]
    return set(archived["feedstock_name"].dropna())


def build_dependency_graph(core_cf_graph_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase J  (phase_j_dependency_graph CFA:6067)
    """Build the dependency edge list from the cf-graph, filtering the archived-
    feedstock skip-set at the write site (v7.9.0). Input: ``feedstock_name``,
    ``conda_name``, ``depends_on``, ``dep_type`` (+ ``feedstock_archived``). Output:
    ``conda_name``, ``depends_on``, ``dep_type`` for active feedstocks only."""
    g = core_cf_graph_raw
    _req = {"feedstock_name", "conda_name", "depends_on", "dep_type"}
    if g is None or g.empty or not _req <= set(g.columns):
        return pd.DataFrame(columns=["conda_name", "depends_on", "dep_type"])
    skip = _inactive_feedstocks(g)
    active = g[~g["feedstock_name"].isin(skip)]
    edges = active[["conda_name", "depends_on", "dep_type"]].dropna(subset=["depends_on"])
    return edges.drop_duplicates().reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase M — feedstock health (same archived-feedstock scope filter at write SELECT)
# ---------------------------------------------------------------------------

def compute_feedstock_health(core_cf_graph_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase M  (phase_m_feedstock_health CFA:6263)
    """Compute per-feedstock health rows, applying the same archived-feedstock scope
    filter at the write SELECT (v7.9.0). Input: ``feedstock_name`` + health signals
    (``ci_status``, ``open_prs``, ``open_issues`` …) + ``feedstock_archived``. Output:
    one row per ACTIVE feedstock with its health signals."""
    g = core_cf_graph_raw
    if g is None or g.empty or "feedstock_name" not in getattr(g, "columns", []):
        return pd.DataFrame(columns=["feedstock_name", "ci_status", "open_prs", "open_issues"])
    skip = _inactive_feedstocks(g)
    active = g[~g["feedstock_name"].isin(skip)]
    cols = [c for c in ("feedstock_name", "ci_status", "open_prs", "open_issues") if c in active.columns]
    health = active[cols].drop_duplicates("feedstock_name")
    return health.reset_index(drop=True)
