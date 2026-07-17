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

import pandas as pd


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
