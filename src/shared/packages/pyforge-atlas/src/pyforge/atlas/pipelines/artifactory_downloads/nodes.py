"""``artifactory_downloads`` pipeline nodes (Story 15.3, CAP-4; Epic 15).

Three PURE nodes wiring Story 15.1's :class:`~pyforge.atlas.artifactory.ArtifactoryAqlAdapter`
(fetch) and Story 15.2's :func:`~pyforge.atlas.artifactory.join_identity` (identity join) into
the Kedro pipeline, then formatting the joined rows into the reversed-direction mapped-PURL
TSV shape ``export_purls.py::mapped_tsv_lines`` already produces for conda->pypi (Code Map).

``fetch_artifactory_downloads`` short-circuits to an empty, correctly-columned DataFrame with
ZERO :class:`~pyforge.atlas.artifactory.ArtifactoryConfig`/
:class:`~pyforge.atlas.artifactory.ArtifactoryAqlAdapter` construction when
``params:artifactory.virtual_repos`` is empty (the committed default) -- no live instance is
named, selected, or contacted anywhere in the default run path. A test-only ``transport`` key
inside ``artifactory_params`` lets a unit test exercise the non-empty-``virtual_repos`` path
against an in-memory mock transport -- never a real HTTP client, and never present in the
committed ``conf/base/parameters.yml`` (whose shipped default carries only ``virtual_repos: []``).

``join_artifactory_identity`` is a thin ``pd.DataFrame`` <-> dataclass adapter around Story
15.2's pure :func:`~pyforge.atlas.artifactory.join_identity` (which operates on
:class:`~pyforge.atlas.artifactory.DownloadRow`/:class:`~pyforge.atlas.artifactory.JoinedDownloadRow`
lists, not DataFrames).

``format_artifactory_purl_export`` includes ONLY rows with a resolved ``conda_name``
(``is_internal=True``/unmatched rows excluded) -- the mirror-image of
``export_purls.py::mapped_tsv_lines``'s own "skip rows missing the join partner" rule, applied
to the reversed pypi->conda direction. ``CHANNEL_QUALIFIER``/``g98_pypi_name`` are reimplemented
locally rather than imported -- no pipeline package imports another module's helpers in this
codebase (see ``artifactory/identity_join.py``'s docstring for the established precedent), and
``export_purls.py`` in particular lives in a completely separate tree
(``.claude/skills/conda-forge-expert/scripts/``), not an importable package from here.

PURE: pandas/stdlib only; no ``dagster``/``kedro_mcp`` import (AD-1); no direct HTTP/DB/
subprocess import.
"""

from __future__ import annotations

import re

import pandas as pd

from ...artifactory import ArtifactoryAqlAdapter, ArtifactoryConfig, DownloadRow, join_identity

# ---------------------------------------------------------------------------
# fetch_artifactory_downloads (CAP-4 fetch half; Story 15.1's adapter)
# ---------------------------------------------------------------------------

_RAW_COLS = ["name", "version", "download_count"]


def _is_missing(v) -> bool:
    """Scalar-safe missing check -- ``True`` for ``None``/NaN/``pd.NA``, ``False`` for a
    real value INCLUDING a list/dict cell (``pd.isna`` on a non-scalar returns an array
    whose truth value is ambiguous, so non-scalars are treated as present rather than
    crashing). Mirrors ``artifactory/identity_join.py::_is_missing`` deliberately rather
    than importing it (no-cross-package-``nodes.py``-import convention). Shared by
    ``join_artifactory_identity`` (value-level row validation) and
    ``format_artifactory_purl_export`` (``conda_name`` resolution check)."""
    if v is None:
        return True
    if isinstance(v, (list, tuple, dict, set)):
        return False
    try:
        return bool(pd.isna(v))
    except ValueError, TypeError:
        return False


def fetch_artifactory_downloads(artifactory_params: dict) -> pd.DataFrame:
    """PURE ``params:artifactory -> pd.DataFrame`` fetch node.

    ``virtual_repos`` empty (the committed default) -> an empty, correctly-columned
    DataFrame, with ZERO :class:`ArtifactoryConfig`/:class:`ArtifactoryAqlAdapter`
    construction -- no live instance is named, selected, or contacted. A non-empty
    ``virtual_repos`` calls Story 15.1's ``fetch_download_rows`` once per virtual repo and
    sums duplicate ``(name, version)`` rows ACROSS repos (the adapter itself only sums
    duplicates WITHIN one virtual repo's raw AQL rows) -- never a real network call unless
    a test also supplies a ``transport`` (never present in the committed
    ``conf/base/parameters.yml``). A ``virtual_repos`` that is present but not a list/tuple
    (e.g. a bare string, which would otherwise iterate per-character) raises ``ValueError``
    immediately rather than issuing bogus per-character AQL calls."""
    params = artifactory_params or {}
    virtual_repos = params.get("virtual_repos") or []
    if not virtual_repos:
        return pd.DataFrame(columns=_RAW_COLS)
    if not isinstance(virtual_repos, (list, tuple)):
        raise ValueError(f"params:artifactory.virtual_repos must be a list, got {type(virtual_repos).__name__}")

    config = ArtifactoryConfig(base_url=params.get("base_url") or "")
    transport = params.get("transport")
    adapter = (
        ArtifactoryAqlAdapter(config, transport=transport) if transport is not None else ArtifactoryAqlAdapter(config)
    )

    totals: dict[tuple[str, str], int] = {}
    for virtual_repo in virtual_repos:
        for row in adapter.fetch_download_rows(virtual_repo):
            key = (row.name, row.version)
            totals[key] = totals.get(key, 0) + row.download_count

    return pd.DataFrame(
        [{"name": n, "version": v, "download_count": c} for (n, v), c in totals.items()],
        columns=_RAW_COLS,
    )


# ---------------------------------------------------------------------------
# join_artifactory_identity (CAP-4 join half; wraps Story 15.2's join_identity)
# ---------------------------------------------------------------------------

_JOINED_COLS = [
    "pypi_name",
    "version",
    "download_count",
    "conda_name",
    "match_source",
    "is_internal",
]


def join_artifactory_identity(
    artifactory_downloads_raw: pd.DataFrame,
    pypi_conda_mapping: pd.DataFrame,
    pypi_universe: pd.DataFrame,
) -> pd.DataFrame:
    """Thin ``pd.DataFrame`` <-> dataclass adapter around Story 15.2's pure
    :func:`~pyforge.atlas.artifactory.join_identity`. Converts each
    ``artifactory_downloads_raw`` row to a :class:`~pyforge.atlas.artifactory.DownloadRow`,
    delegates the actual join to ``join_identity`` UNCHANGED, then flattens the resulting
    :class:`~pyforge.atlas.artifactory.JoinedDownloadRow` list back to a DataFrame. An
    empty/malformed ``artifactory_downloads_raw`` (missing one of ``name``/``version``/
    ``download_count``, or a row carrying a ``None``/NaN cell in one of those columns)
    degrades to an empty frame carrying the full joined schema (that row's degraded
    version, respectively -- the malformed row is skipped, not raised on) -- never raises."""
    if (
        artifactory_downloads_raw is None
        or getattr(artifactory_downloads_raw, "empty", True)
        or not set(_RAW_COLS) <= set(getattr(artifactory_downloads_raw, "columns", []))
    ):
        return pd.DataFrame(columns=_JOINED_COLS)

    rows = []
    for r in artifactory_downloads_raw.itertuples(index=False):
        if _is_missing(r.name) or _is_missing(r.version) or _is_missing(r.download_count):
            continue
        try:
            download_count = int(r.download_count)
        except TypeError, ValueError:
            continue
        rows.append(DownloadRow(name=str(r.name), version=str(r.version), download_count=download_count))
    joined = join_identity(rows, pypi_conda_mapping, pypi_universe)
    return pd.DataFrame(
        [
            {
                "pypi_name": j.pypi_name,
                "version": j.version,
                "download_count": j.download_count,
                "conda_name": j.conda_name,
                "match_source": j.match_source,
                "is_internal": j.is_internal,
            }
            for j in joined
        ],
        columns=_JOINED_COLS,
    )


# ---------------------------------------------------------------------------
# format_artifactory_purl_export (CAP-4 export half)
# ---------------------------------------------------------------------------

# Mirrors export_purls.py's CHANNEL_QUALIFIER / g98_pypi_name / MAPPED_TSV_HEADER exactly
# (module docstring: reimplemented locally, no cross-import -- that file also lives in a
# completely separate tree, `.claude/skills/conda-forge-expert/scripts/`).
CHANNEL_QUALIFIER = "?channel=conda-forge"
_MAPPED_TSV_HEADER = "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence"
_PARTITION_KEY = "artifactory_downloads.tsv"


def g98_pypi_name(name: str) -> str:
    """purl-spec normalization for PyPI purl names: lowercase + ``_``->``-``. Dots are
    PRESERVED (G98 -- PEP 503 folding would over-normalize dotted project names). Mirrors
    ``export_purls.py::g98_pypi_name`` exactly."""
    return name.lower().replace("_", "-")


def format_artifactory_purl_export(artifactory_downloads_joined: pd.DataFrame) -> dict[str, str]:
    """Format the joined rows into the ``derived_purl_exports`` partition this story
    contributes (``artifactory_downloads.tsv``). Includes ONLY rows with a resolved
    ``conda_name`` -- ``is_internal=True``/unmatched rows are excluded, mirroring
    ``export_purls.py::mapped_tsv_lines``'s own "skip rows missing the join partner" rule
    for the reversed pypi->conda direction. ``match_confidence`` is always blank -- this
    data source never carried a confidence column (Design Notes), matching the legacy
    code's own ``p['match_confidence'] or ''`` fallback rather than inventing a value.
    An empty/``None`` ``artifactory_downloads_joined`` yields the header-only content."""
    lines = [_MAPPED_TSV_HEADER]
    if artifactory_downloads_joined is not None and not getattr(artifactory_downloads_joined, "empty", True):
        for row in artifactory_downloads_joined.itertuples(index=False):
            conda_name = getattr(row, "conda_name", None)
            if _is_missing(conda_name) or not isinstance(conda_name, str):
                continue
            pypi_name = getattr(row, "pypi_name", None)
            match_source = getattr(row, "match_source", None)
            lines.append(
                f"pkg:conda/{conda_name}{CHANNEL_QUALIFIER}\t"
                f"pkg:pypi/{g98_pypi_name(str(pypi_name))}\t"
                f"{match_source if isinstance(match_source, str) else ''}\t"
            )
    content = "".join(f"{line}\n" for line in lines)
    return {_PARTITION_KEY: content}


# ---------------------------------------------------------------------------
# project_artifactory_names (Story 21.5, Tier 2: Artifactory/CDO names, not telemetry)
# ---------------------------------------------------------------------------

# Names-only projection -- deliberately EXCLUDES download_count/version/match_source.
# enterprise_jfrog_consumption.parquet (Story 23.2) is where those live; Story 23.2
# depends on THIS story landing first so the names-only identity key exists to extend
# (spec-21-5-tier-2-sources.md Boundaries "Never").
_ENTERPRISE_JFROG_NAMES_COLS = ["pypi_name", "conda_name", "is_internal"]


def project_artifactory_names(artifactory_downloads_joined: pd.DataFrame) -> pd.DataFrame:
    """Project ``artifactory_downloads_joined`` down to ``pypi_name``/``conda_name``/
    ``is_internal`` ONLY -- ``enterprise_jfrog_names``, the Tier 2 Artifactory/CDO
    names-only universe (catalog-sources.md Tier 2). Correct whether the upstream
    fetch is empty (today, ``params:artifactory.virtual_repos: []``) or populated
    later by a live, attended bring-up -- no live call is made here either way.

    An empty/malformed ``artifactory_downloads_joined`` (missing one of the three
    projected columns) degrades to an empty frame carrying the names-only schema --
    never raises. Distinct ``(pypi_name, conda_name)`` pairs only (mirrors
    ``join_artifactory_identity``'s own never-raise/degrade-to-empty-schema style)."""
    if (
        artifactory_downloads_joined is None
        or getattr(artifactory_downloads_joined, "empty", True)
        or not set(_ENTERPRISE_JFROG_NAMES_COLS) <= set(getattr(artifactory_downloads_joined, "columns", []))
    ):
        return pd.DataFrame(columns=_ENTERPRISE_JFROG_NAMES_COLS)
    return (
        artifactory_downloads_joined[_ENTERPRISE_JFROG_NAMES_COLS]
        .drop_duplicates(subset=["pypi_name", "conda_name"])
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# fetch_artifactory_consumption + build_enterprise_jfrog_consumption (Story 23.2)
# ---------------------------------------------------------------------------

_CONSUMPTION_COLS = [
    "name",
    "platform_env_count",
    "internal_app_count",
    "internal_component_count",
    "internal_lob_count",
]

_JFROG_COLS = [
    "core_python_package_name",
    "repository_source",
    "platform_env_count",
    "internal_app_count",
    "artifactory_downloads",
    "artifactory_version_count",
    "internal_component_count",
    "internal_lob_count",
    "packaging_tier",
    "verification_timestamp_utc",
]

_REPOSITORY_SOURCE_CDO_ENT_JFROG = "CDO-ENT-JFROG"


def _pep503(raw) -> str | None:
    """PEP-503 normalization mirroring ``priority.py::pep503`` exactly (reimplemented
    locally -- no cross-tree import). Names shorter than 2 chars normalize to ``None``."""
    from datetime import datetime

    if raw is None or isinstance(raw, datetime):
        return None
    s = str(raw).strip().lower().replace("_", "-").replace(".", "-")
    s = re.sub(r"-+", "-", s).strip("-")
    return s if len(s) >= 2 else None


def fetch_artifactory_consumption(artifactory_params: dict) -> pd.DataFrame:
    """PURE ``params:artifactory -> pd.DataFrame`` consumption fetch node (Story 23.2).

    Mirrors :func:`fetch_artifactory_downloads` exactly: empty ``virtual_repos`` short-
    circuits with ZERO adapter construction; non-list ``virtual_repos`` raises
    ``ValueError``; optional test-only ``transport`` key."""
    params = artifactory_params or {}
    virtual_repos = params.get("virtual_repos") or []
    if not virtual_repos:
        return pd.DataFrame(columns=_CONSUMPTION_COLS)
    if not isinstance(virtual_repos, (list, tuple)):
        raise ValueError(f"params:artifactory.virtual_repos must be a list, got {type(virtual_repos).__name__}")

    config = ArtifactoryConfig(base_url=params.get("base_url") or "")
    transport = params.get("transport")
    adapter = (
        ArtifactoryAqlAdapter(config, transport=transport) if transport is not None else ArtifactoryAqlAdapter(config)
    )

    totals: dict[str, tuple[int, int, int, int]] = {}
    for virtual_repo in virtual_repos:
        for row in adapter.fetch_consumption_rows(virtual_repo):
            prev = totals.get(row.name, (0, 0, 0, 0))
            totals[row.name] = (
                prev[0] + row.platform_env_count,
                prev[1] + row.internal_app_count,
                prev[2] + row.internal_component_count,
                prev[3] + row.internal_lob_count,
            )

    return pd.DataFrame(
        [
            {
                "name": name,
                "platform_env_count": counts[0],
                "internal_app_count": counts[1],
                "internal_component_count": counts[2],
                "internal_lob_count": counts[3],
            }
            for name, counts in totals.items()
        ],
        columns=_CONSUMPTION_COLS,
    )


def build_enterprise_jfrog_consumption(
    artifactory_downloads_joined: pd.DataFrame,
    artifactory_consumption_raw: pd.DataFrame,
) -> pd.DataFrame:
    """PURE join node: aggregate downloads by PEP-503 name, outer-merge consumption
    telemetry, emit ``enterprise_jfrog_consumption`` contract columns. Never raises."""
    verification_ts = pd.Timestamp.now(tz="UTC")

    if (
        artifactory_downloads_joined is None
        or getattr(artifactory_downloads_joined, "empty", True)
        or not {"pypi_name", "version", "download_count"} <= set(getattr(artifactory_downloads_joined, "columns", []))
    ):
        downloads_by_name: dict[str, dict] = {}
    else:
        downloads_by_name = {}
        for row in artifactory_downloads_joined.itertuples(index=False):
            if _is_missing(row.pypi_name) or _is_missing(row.version) or _is_missing(row.download_count):
                continue
            norm = _pep503(row.pypi_name)
            if norm is None:
                continue
            try:
                count = int(row.download_count)
            except TypeError, ValueError:
                continue
            entry = downloads_by_name.setdefault(norm, {"downloads": 0, "versions": set()})
            entry["downloads"] += count
            entry["versions"].add(str(row.version))

    if (
        artifactory_consumption_raw is None
        or getattr(artifactory_consumption_raw, "empty", True)
        or not set(_CONSUMPTION_COLS) <= set(getattr(artifactory_consumption_raw, "columns", []))
    ):
        consumption_by_name: dict[str, dict] = {}
    else:
        consumption_by_name = {}
        for row in artifactory_consumption_raw.itertuples(index=False):
            if _is_missing(row.name):
                continue
            norm = _pep503(row.name)
            if norm is None:
                continue
            try:
                platform_env = int(row.platform_env_count) if not _is_missing(row.platform_env_count) else 0
                internal_app = int(row.internal_app_count) if not _is_missing(row.internal_app_count) else 0
                internal_component = (
                    int(row.internal_component_count) if not _is_missing(row.internal_component_count) else 0
                )
                internal_lob = int(row.internal_lob_count) if not _is_missing(row.internal_lob_count) else 0
            except TypeError, ValueError:
                continue
            prev = consumption_by_name.get(
                norm,
                {
                    "platform_env_count": 0,
                    "internal_app_count": 0,
                    "internal_component_count": 0,
                    "internal_lob_count": 0,
                },
            )
            consumption_by_name[norm] = {
                "platform_env_count": prev["platform_env_count"] + platform_env,
                "internal_app_count": prev["internal_app_count"] + internal_app,
                "internal_component_count": prev["internal_component_count"] + internal_component,
                "internal_lob_count": prev["internal_lob_count"] + internal_lob,
            }

    all_names = set(downloads_by_name) | set(consumption_by_name)
    if not all_names:
        return pd.DataFrame(columns=_JFROG_COLS)

    records = []
    for norm in sorted(all_names):
        dl = downloads_by_name.get(norm, {"downloads": 0, "versions": set()})
        cons = consumption_by_name.get(
            norm,
            {
                "platform_env_count": 0,
                "internal_app_count": 0,
                "internal_component_count": 0,
                "internal_lob_count": 0,
            },
        )
        records.append(
            {
                "core_python_package_name": norm,
                "repository_source": _REPOSITORY_SOURCE_CDO_ENT_JFROG,
                "platform_env_count": cons["platform_env_count"],
                "internal_app_count": cons["internal_app_count"],
                "artifactory_downloads": dl["downloads"],
                "artifactory_version_count": len(dl["versions"]),
                "internal_component_count": cons["internal_component_count"],
                "internal_lob_count": cons["internal_lob_count"],
                "packaging_tier": None,
                "verification_timestamp_utc": verification_ts,
            }
        )

    return pd.DataFrame(records, columns=_JFROG_COLS)
