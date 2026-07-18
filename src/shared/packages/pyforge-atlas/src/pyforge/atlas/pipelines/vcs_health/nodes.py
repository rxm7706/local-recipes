"""``vcs_health`` pipeline nodes — VCS + registry health (Story B1, § 5.2 / AD-3).

PURE ``DataFrame -> DataFrame`` transforms. The Phase K single-worker 3-RPS token
bucket, ``Retry-After`` backoff, per-registry concurrency caps, and the 403 →
``last_error`` re-pick are DATASET/RESOURCE concerns (``datasets/rate_limit.py`` +
``datasets/request_datasets.py``, AD-2) — they are NOT in these node bodies. A node
receives already-fetched frames (each carrying a ``last_error`` column the fetcher set
on a non-success status) and only normalizes/merges them. The rate-limit CONTRACT is
fixture-tested against a stub in the node suite (AD-10 / AD-11).

``# legacy: Phase <ID>`` provenance per node; ``CFA`` = ``conda_forge_atlas.py`` @
b18cbb5.
"""

from __future__ import annotations

import time

import pandas as pd

# ms-vs-seconds magnitude split (mirrors core.nodes._MS_THRESHOLD +
# IncrementalParquetDataset._MS_EPOCH_THRESHOLD — "convert once, at the boundary",
# DW-A3-P10). 1e12 cleanly separates epoch-seconds (~1.7e9) from epoch-ms (~1.7e12).
_MS_THRESHOLD = 1_000_000_000_000

# The FR-20 recency gate: the release-velocity signal qualifies ONLY where the
# upstream release is <= 90 days old (the rebuild-cadence-artifact guard). Cross-
# validated live at a 5,000-package sample and the full 19,726-feedstock population
# to within 1 pp (spec § FR-20 / Story B9).
_NINETY_DAYS_SECONDS = 90 * 24 * 3600

# Unix epoch anchor (tz-aware) — subtracting it from a UTC-normalized parse yields
# float seconds and maps an unparseable stamp (NaT) to NaN naturally (AD-13 safety).
_EPOCH_UTC = pd.Timestamp("1970-01-01", tz="UTC")


def _key(v):
    """Normalize a join key to a stripped string, or ``None`` for a missing / non-scalar
    cell. Keeps the (conda_name, version) merge robust when one side round-tripped a
    version like ``1.0`` through a float dtype — both sides string-key identically so a
    value match can't silently miss (B9 review-hardening)."""
    if v is None:
        return None
    if isinstance(v, (list, tuple, dict, set)):
        return None
    try:
        if pd.isna(v):
            return None
    except (ValueError, TypeError):
        return None
    return str(v).strip()


def _as_bool_series(col: pd.Series) -> pd.Series:
    """Coerce a possibly string/NaN boolean column to real booleans (a bare
    ``.astype(bool)`` turns the string ``"false"`` into ``True``). Kept local so the
    two pipelines stay import-independent."""
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
# Phase E — maintainer enrichment  (reads core_cf_graph_raw — cross-pipeline, AD-3)
# ---------------------------------------------------------------------------

def enrich_maintainers(
    core_cf_graph_raw: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # legacy: Phase E  (phase_e_enrichment CFA:2188; delta spec:287-292)
    """Enrich maintainer data from the cf-graph ``node_attrs``.

    Reads ``core_cf_graph_raw`` — a cross-pipeline reference resolved by CATALOG NAME
    (AD-3): the cf-graph tarball is a shared raw SOURCE declared once by the ``core``
    domain and consumed here by ``vcs_health`` Phase E (no producer conflict — it is a
    fetched source, not a node output).

    AC-5 — the maintainer-universe delta is DOCUMENTED here (full reconciliation
    deferred to B4): atlas ``package_maintainers`` = **769** (537 sole + 232 co, build
    2026-06-19) vs cf-graph ``node_attrs`` discovery = **813** (558 + 255,
    conda-forge-tracker.md), Δ≈**44** (spec:287-292). The ~44-feedstock disagreement is
    a data-quality investigation beyond one story; the AC explicitly allows
    "reconciles — or explicitly documents". See the parity notes
    (``tests/parity/PARITY_NOTES.md``).

    Input: ``feedstock_name``, ``conda_name``, ``maintainers`` (list per row). Output:
    ``(vcs_maintainers, vcs_package_maintainers)`` — the unique maintainer universe and
    the per-package (conda_name, maintainer) long form.
    """
    g = core_cf_graph_raw
    maint_cols = ["maintainer"]
    pkg_cols = ["conda_name", "maintainer"]
    if g is None or g.empty or not {"conda_name", "maintainers"} <= set(g.columns):
        return pd.DataFrame(columns=maint_cols), pd.DataFrame(columns=pkg_cols)

    rows: list[tuple[str, str]] = []
    for conda_name, maints in zip(g["conda_name"], g["maintainers"]):
        # a missing cell is a scalar NaN (truthy) — `maints or []` would yield NaN and
        # crash `for m in nan`; iterate only real sequences.
        seq = maints if isinstance(maints, (list, tuple)) else []
        for m in seq:
            rows.append((conda_name, m))
    package_maintainers = pd.DataFrame(rows, columns=pkg_cols).drop_duplicates()
    maintainers = (
        package_maintainers[["maintainer"]].drop_duplicates().sort_values("maintainer")
    )
    return (
        maintainers.reset_index(drop=True),
        package_maintainers.reset_index(drop=True),
    )


# ---------------------------------------------------------------------------
# Phase E.5 — archived-feedstock detection
# ---------------------------------------------------------------------------

def detect_archived_feedstocks(vcs_github_api_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase E.5  (phase_e5_archived_feedstocks CFA:2504)
    """Detect archived feedstocks from the GitHub API response. Input:
    ``feedstock_name``, ``archived`` (bool). Output: the ``feedstock_name`` rows whose
    repo is archived (``archived=True``)."""
    src = vcs_github_api_raw
    if src is None or src.empty or not {"feedstock_name", "archived"} <= set(src.columns):
        return pd.DataFrame(columns=["feedstock_name", "archived"])
    archived = src[_as_bool_series(src["archived"])]
    return archived[["feedstock_name", "archived"]].drop_duplicates().reset_index(drop=True)


# ---------------------------------------------------------------------------
# Phase K — upstream version tracking (3-RPS bucket is DATASET-owned, not here)
# ---------------------------------------------------------------------------

def track_upstream_versions(
    vcs_github_api_raw: pd.DataFrame,
    vcs_gitlab_api_raw: pd.DataFrame,
    vcs_codeberg_api_raw: pd.DataFrame,
) -> pd.DataFrame:
    # legacy: Phase K  (phase_k_vcs_versions CFA:5039; _RateLimitedScheduler CFA:1345)
    """Merge upstream version data across the three VCS hosts into one frame.

    The single-worker 3-RPS token bucket, ``PHASE_K_AGGRESSIVE`` opt-out, 403 →
    ``last_error`` + TTL-bypass re-pick, and ``Retry-After`` backoff are DATASET-owned
    (``datasets/rate_limit.py`` / ``datasets/request_datasets.py``, AD-2) — this node
    body stays pure. Each host frame already carries a ``last_error`` column the
    fetcher set on a non-success status; the node preserves it (the ``last_error``
    column convention) and tags each row with its ``host``. Input columns per host:
    ``conda_name``, ``upstream_version``, optional ``last_error``. Output:
    ``conda_name``, ``host``, ``upstream_version``, ``last_error``."""
    cols = ["conda_name", "host", "upstream_version", "last_error"]
    frames = []
    for host, df in (
        ("github", vcs_github_api_raw),
        ("gitlab", vcs_gitlab_api_raw),
        ("codeberg", vcs_codeberg_api_raw),
    ):
        if df is None or df.empty:
            continue
        part = df.copy()
        part["host"] = host
        # default every non-host column so a mis-shaped host frame never KeyErrors
        # on part[cols] (consistent with track_registry_versions).
        for c in ("conda_name", "upstream_version", "last_error"):
            if c not in part.columns:
                part[c] = pd.NA
        frames.append(part[cols])
    if not frames:
        return pd.DataFrame(columns=cols)
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Phase L — extra-registry version tracking
# ---------------------------------------------------------------------------

_REGISTRY_INPUTS = (
    "npm", "cran", "cpan", "luarocks", "crates", "rubygems", "maven", "nuget",
)


def track_registry_versions(
    vcs_registry_npm_raw: pd.DataFrame,
    vcs_registry_cran_raw: pd.DataFrame,
    vcs_registry_cpan_raw: pd.DataFrame,
    vcs_registry_luarocks_raw: pd.DataFrame,
    vcs_registry_crates_raw: pd.DataFrame,
    vcs_registry_rubygems_raw: pd.DataFrame,
    vcs_registry_maven_raw: pd.DataFrame,
    vcs_registry_nuget_raw: pd.DataFrame,
) -> pd.DataFrame:
    # legacy: Phase L  (phase_l_extra_registries CFA:5841)
    """Merge upstream versions across the 8 cross-ecosystem registries into one frame.
    Per-registry concurrency caps + per-source TTL treatment are DATASET-owned (AD-2);
    this node only tags each frame with its ``registry`` and concatenates. Input per
    registry: ``conda_name``, ``upstream_version``. Output: ``conda_name``,
    ``registry``, ``upstream_version``."""
    cols = ["conda_name", "registry", "upstream_version"]
    frames = []
    per_registry = zip(
        _REGISTRY_INPUTS,
        (
            vcs_registry_npm_raw, vcs_registry_cran_raw, vcs_registry_cpan_raw,
            vcs_registry_luarocks_raw, vcs_registry_crates_raw, vcs_registry_rubygems_raw,
            vcs_registry_maven_raw, vcs_registry_nuget_raw,
        ),
    )
    for registry, df in per_registry:
        if df is None or df.empty:
            continue
        part = df.copy()
        part["registry"] = registry
        for c in ("conda_name", "upstream_version"):
            if c not in part.columns:
                part[c] = pd.NA
        frames.append(part[cols])
    if not frames:
        return pd.DataFrame(columns=cols)
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Phase N — live health signals
# ---------------------------------------------------------------------------

def fetch_live_health(vcs_github_api_raw: pd.DataFrame) -> pd.DataFrame:
    # legacy: Phase N  (phase_n_github_live CFA:6525)
    """Normalize live GitHub health signals (stars / last-commit / open-issues) into
    ``vcs_live_health``. Rate-limit-stderr detection + the 1-day live-signal TTL are
    DATASET-owned (AD-2/AD-5); the node only projects/normalizes the already-fetched
    signals. Input: ``feedstock_name`` + live signals. Output: one row per feedstock
    with the projected signals."""
    src = vcs_github_api_raw
    base_cols = ["feedstock_name", "stars", "last_commit", "open_issues"]
    if src is None or src.empty or "feedstock_name" not in getattr(src, "columns", []):
        return pd.DataFrame(columns=base_cols)
    # Stable output schema: always the full base_cols, missing signals filled NA
    # (a variable schema depending on which inputs happen to be present is unstable
    # for downstream consumers + the parity harness).
    out = src.drop_duplicates("feedstock_name").reset_index(drop=True)
    for c in base_cols:
        if c not in out.columns:
            out[c] = pd.NA
    return out[base_cols]


# ---------------------------------------------------------------------------
# FR-20 — release-to-availability velocity  (Story B9; NEW-SIGNAL, AD-14 —
#         NOT parity-gated. Lives HERE in vcs_health but READS the Phase H
#         dataset produced by pypi_intelligence; Kedro datasets are shared by
#         catalog NAME, ownership = producer, so this node only READS it, AD-3.)
# ---------------------------------------------------------------------------

def derive_release_velocity(
    pypi_current_versions: pd.DataFrame,
    core_repodata_raw: pd.DataFrame,
    pypi_conda_mapping: pd.DataFrame,
    now: int | None = None,
) -> pd.DataFrame:
    # legacy: FR-20 release velocity  (Story B9; spec § 5.2 item 4 / § FR-20 / § 9)
    """Derive ``release_lag_hours`` + ``release_lag_qualifies`` — how long conda-forge
    takes to publish a matching build after an upstream PyPI release. **NO new external
    source**: reuses the Phase H ``pypi_current_versions`` (which RETAINS
    ``upload_time_iso_8601`` per the current release, B2/AC-5) + the already-fetched
    ``core_repodata_raw`` per-build timestamps + the Phase C ``pypi_conda_mapping``.

    **First-availability = MIN timestamp (the load-bearing rule).** The conda side is the
    **minimum per-build ``timestamp`` across the matched version's artifacts**, NEVER
    ``latest_conda_upload``. conda-forge periodically REBUILDS long-stable, version-
    unchanged packages (migrations / ABI / compiler / py-matrix), so a latest-upload
    delta reflects the most recent *rebuild*, not *first availability* — the naive
    ``latest_conda_upload − pypi_upload_time`` produced a false "47% >10 days behind"
    headline. Using MIN(timestamp) means a rebuild landing INSIDE the 90-day window can
    never shift the lag (fixture-enforced). Repodata per-build ``timestamp`` is in
    **MILLISECONDS**; it is normalized ms→s at THIS boundary (the same ``ts.where(ts <
    _MS_THRESHOLD, ts // 1000)`` convention as ``core.nodes`` / IncrementalParquetDataset).

    **The 90-day recency gate (``release_lag_qualifies``).** True ONLY where the upstream
    release is <= 90 days old (``upload_time_iso_8601`` within 90 days of ``now``). A
    version-unchanged package whose upstream release is >90 days old → ``qualifies=False``
    — the belt to first-availability's suspenders; together they make the false "47%
    behind" classification impossible to recur. ``now`` is injectable (default
    ``int(time.time())``) so fixtures are deterministic.

    Lag is computed ONLY for the MATCHED version (same version string on both sides,
    after mapping ``pypi_name → conda_name``); unmatched versions produce no lag (no
    output row). Malformed / unparseable ``upload_time_iso_8601`` → ``release_lag_hours``
    NaN + ``qualifies=False``, never raises (AD-13). Epoch SECONDS everywhere in-frame.

    Calibration reference ONLY (NOT asserted — it is a calibration note, not a gate):
    the live baseline this signal should roughly reproduce is median ≈ 8.9 h, 72.4%
    within 24 h, 83.7% within 72 h (spec § FR-20).

    Inputs — ``pypi_current_versions``: ``pypi_name``, ``version``,
    ``upload_time_iso_8601``. ``core_repodata_raw``: ``conda_name``, ``version``,
    ``timestamp`` (ms), optional ``subdir``. ``pypi_conda_mapping``: ``pypi_name``,
    ``conda_name`` (+ ``match_source``). Output ``vcs_release_velocity``: ``pypi_name``,
    ``conda_name``, ``version``, ``release_lag_hours``, ``release_lag_qualifies``.
    """
    if now is None:
        now = int(time.time())
    cols = ["pypi_name", "conda_name", "version", "release_lag_hours", "release_lag_qualifies"]

    def _empty() -> pd.DataFrame:
        # explicit per-column dtypes so an empty return matches the non-empty path's
        # dtypes (release_lag_hours float64, release_lag_qualifies bool) — a bare
        # ``DataFrame(columns=cols)`` yields object columns, which mismatches a
        # schema-typed parquet sink or a concat with a populated result (B9 review).
        return pd.DataFrame(
            {
                "pypi_name": pd.Series(dtype=object),
                "conda_name": pd.Series(dtype=object),
                "version": pd.Series(dtype=object),
                "release_lag_hours": pd.Series(dtype="float64"),
                "release_lag_qualifies": pd.Series(dtype=bool),
            }
        )

    pcv = pypi_current_versions
    if (
        pcv is None
        or pcv.empty
        or not {"pypi_name", "version", "upload_time_iso_8601"} <= set(pcv.columns)
    ):
        return _empty()

    mp = pypi_conda_mapping
    if mp is None or mp.empty or not {"pypi_name", "conda_name"} <= set(mp.columns):
        return _empty()

    repo = core_repodata_raw
    if repo is None or repo.empty or not {"conda_name", "version", "timestamp"} <= set(repo.columns):
        return _empty()

    # -- conda side: FIRST availability = MIN per-build timestamp, ms→s at the boundary.
    r = repo[["conda_name", "version", "timestamp"]].copy()
    ts = pd.to_numeric(r["timestamp"], errors="coerce")
    # ms → s only for the ms-magnitude values; a NaN stays NaN (min drops it).
    r["_avail_s"] = ts.where(ts < _MS_THRESHOLD, ts // 1000)
    # string-key both join columns so a float-parsed "1.0" version can't miss its match.
    r["conda_name"] = r["conda_name"].map(_key)
    r["version"] = r["version"].map(_key)
    r = r.dropna(subset=["conda_name", "version"])
    first_avail = (
        r.groupby(["conda_name", "version"], as_index=False)["_avail_s"].min()
    )

    # -- pypi side: map pypi_name → conda_name, then match on (conda_name, version).
    p = pcv[["pypi_name", "version", "upload_time_iso_8601"]].copy()
    p["version"] = p["version"].map(_key)
    p = p.dropna(subset=["pypi_name", "version"])

    m = mp[["pypi_name", "conda_name"]].drop_duplicates().copy()
    m["conda_name"] = m["conda_name"].map(_key)
    m = m.dropna(subset=["pypi_name", "conda_name"])

    joined = p.merge(m, on="pypi_name", how="inner")
    # inner-join on (conda_name, version) ⇒ only the MATCHED version survives
    # (unmatched versions produce no lag / no row).
    matched = joined.merge(first_avail, on=["conda_name", "version"], how="inner")
    if matched.empty:
        return _empty()

    # -- upstream upload → epoch seconds (utc-normalized; tz-naive assumed UTC; a bad
    #    stamp parses to NaT → NaN, never raises).
    dt = pd.to_datetime(matched["upload_time_iso_8601"], utc=True, errors="coerce")
    upload_s = (dt - _EPOCH_UTC).dt.total_seconds()

    lag_hours = (matched["_avail_s"] - upload_s) / 3600.0
    # 90-day recency gate: a valid upstream parse AND a real conda availability (so the
    # lag itself exists) AND within 90 days of `now`. A NaN upload_s (unparseable /
    # missing upstream) OR a NaN lag (malformed conda `timestamp`) → qualifies False —
    # a "qualifying" row must carry a real lag, else it pollutes any downstream
    # aggregation over the qualifying population with a NaN (AD-13 "malformed →
    # qualifies False"; B9 review).
    qualifies = (
        upload_s.notna()
        & lag_hours.notna()
        & ((now - upload_s) <= _NINETY_DAYS_SECONDS)
    )

    out = pd.DataFrame(
        {
            "pypi_name": matched["pypi_name"].values,
            "conda_name": matched["conda_name"].values,
            "version": matched["version"].values,
            "release_lag_hours": lag_hours.values,
            "release_lag_qualifies": qualifies.astype(bool).values,
        },
        columns=cols,
    )
    out = out.drop_duplicates(subset=["pypi_name", "conda_name", "version"]).reset_index(drop=True)
    return out
