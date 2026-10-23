"""The six export-purls artifacts and their manifest (Story 37.8, CAP-69).

A port of legacy ``export_purls.py`` (cyclonedx-universe-inventory Wave A / S1) onto the datasets the pipelines
write. PURE: every input arrives as a frame, the artifacts leave as text partitions.

Ordering contract (legacy's regression surface): artifacts 1, 2 and 4 sort by ``conda_name`` in C-locale, never by
full line (``?`` sorts after ``-`` and would flip ``foo`` / ``foo-bar``); artifact 3 is a full-line C-sort; 5 sorts
by recipe directory; 6 by (``conda_name``, source). purl conventions (G98): a conda purl carries
``?channel=conda-forge``; a PyPI purl name is lowercased with ``_`` as ``-``, dots kept. Folding (``[-_.]+`` to
``-``) is for membership lookup only.
"""

from __future__ import annotations

import re
import time
import urllib.parse
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from ...datasets.core_sources import package_recipe_fields

CHANNEL_QUALIFIER = "?channel=conda-forge"
MAPPED_TSV_HEADER = "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence"
UPSTREAM_TSV_HEADER = "conda_purl\tupstream_purl\tupstream_source"
ARTIFACTS = (
    "purls_conda-forge.txt",
    "purls_conda-forge_versioned.txt",
    "purls_pypi.txt",
    "purls_conda-pypi_mapped.tsv",
    "recipe-purl-exceptions.txt",
    "purls_conda-upstream_mapped.tsv",
)
#: the two TSVs open with a header line, which is not a row
TSV_ARTIFACTS = frozenset({"purls_conda-pypi_mapped.tsv", "purls_conda-upstream_mapped.tsv"})
MANIFEST_COLUMNS = ["artifact_name", "regenerated_at", "row_count"]

_GITHUB_RE = re.compile(r"github\.com/([^/]+)/([^/#?]+)", re.IGNORECASE)
_NPM_RE = re.compile(r"registry\.npmjs\.(?:org|com)/((?:@[^/]+/)?[^/#?]+)", re.IGNORECASE)
_CRATES_RE = re.compile(r"crates\.io/(?:api/v1/crates/|crates/)([^/#?]+)", re.IGNORECASE)
_GEM_RE = re.compile(r"rubygems\.org/(?:api/v1/gems/|gems/)([^/#?]+?)(?:\.json)?$", re.IGNORECASE)
_MAVEN_RE = re.compile(r"maven2/(.+)/([^/]+)/maven-metadata", re.IGNORECASE)
#: a recipe URL's host, as the upstream source legacy's ``upstream_versions`` would name it
_HOST_SOURCES = (
    ("github.com", "github"),
    ("gitlab.com", "gitlab"),
    ("codeberg.org", "codeberg"),
    ("registry.npmjs.org", "npm"),
    ("registry.npmjs.com", "npm"),
    ("crates.io", "crates"),
    ("rubygems.org", "rubygems"),
    ("maven2/", "maven"),
)


def g98_pypi_name(name: str) -> str:
    """legacy ``g98_pypi_name``: lowercase, ``_`` as ``-``, dots kept."""
    return name.lower().replace("_", "-")


def fold_name(name: str) -> str:
    """legacy ``fold_name``: PEP 503's fold, for membership lookup only."""
    return re.sub(r"[-_.]+", "-", name.lower())


def upstream_purl(source: str, url: str | None) -> str | None:
    """legacy ``upstream_purl``, unchanged: a (source, url) pair as a spec-conformant purl, or ``None`` when the URL
    does not parse."""
    url = url or ""
    if source == "github":
        m = _GITHUB_RE.search(url)
        if m:
            owner = m.group(1).lower()
            repo = re.sub(r"\.git$", "", m.group(2)).lower()
            return f"pkg:github/{owner}/{repo}"
        return None
    if source == "npm":
        m = _NPM_RE.search(url)
        if m:
            return f"pkg:npm/{m.group(1).replace('@', '%40', 1)}"
        return None
    if source == "crates":
        m = _CRATES_RE.search(url)
        return f"pkg:cargo/{m.group(1)}" if m else None
    if source == "rubygems":
        m = _GEM_RE.search(url)
        return f"pkg:gem/{m.group(1)}" if m else None
    if source == "maven":
        m = _MAVEN_RE.search(url)
        if m:
            return f"pkg:maven/{m.group(1).replace('/', '.')}/{m.group(2)}"
        return None
    if source in ("gitlab", "codeberg"):
        parsed = urllib.parse.urlsplit(url)
        segments = [s for s in parsed.path.split("/") if s]
        if not (parsed.netloc and segments):
            return None
        repo = re.sub(r"\.git$", "", segments[-1])
        vcs_url = urllib.parse.quote(f"git+{url}", safe="")
        return f"pkg:generic/{repo}?vcs_url={vcs_url}"
    return None


def _url_source(url: str) -> str | None:
    lowered = url.lower()
    return next((source for marker, source in _HOST_SOURCES if marker in lowered), None)


def _active_packages(enumerated: pd.DataFrame | None, latest_status: pd.DataFrame | None) -> pd.DataFrame:
    """Every enumerated package whose latest status is ``active`` (legacy includes archived-but-active ones),
    sorted by name in C-locale."""
    if enumerated is None or enumerated.empty or "conda_name" not in enumerated.columns:
        return pd.DataFrame(columns=["conda_name", "latest_version"])
    pkgs = enumerated.dropna(subset=["conda_name"]).drop_duplicates("conda_name").copy()
    pkgs["conda_name"] = pkgs["conda_name"].astype(str)
    if "latest_version" not in pkgs.columns:
        pkgs["latest_version"] = None
    if latest_status is not None and {"conda_name", "latest_status"} <= set(latest_status.columns):
        active = set(latest_status.loc[latest_status["latest_status"] == "active", "conda_name"].astype(str))
        pkgs = pkgs[pkgs["conda_name"].isin(active)]
    return pkgs.sort_values("conda_name", key=lambda s: s.map(lambda v: v.encode())).reset_index(drop=True)


def _mapping_rows(mapping: pd.DataFrame | None) -> pd.DataFrame:
    if mapping is None or mapping.empty or not {"conda_name", "pypi_name"} <= set(mapping.columns):
        return pd.DataFrame(columns=["conda_name", "pypi_name", "match_source", "match_confidence"])
    rows = mapping.dropna(subset=["conda_name", "pypi_name"]).copy()
    rows = rows[rows["pypi_name"].astype(str) != ""]
    for column in ("match_source", "match_confidence"):
        if column not in rows.columns:
            rows[column] = None
    rows["conda_name"] = rows["conda_name"].astype(str)
    rows["pypi_name"] = rows["pypi_name"].astype(str)
    return rows.drop_duplicates(["conda_name", "pypi_name"])


def _cell(value: Any) -> str:
    return "" if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NA else str(value)


def _exception_lines(recipe_extras: pd.DataFrame | None, conda_names: set[str], pypi_fold_index: set[str]) -> list[str]:
    """legacy ``recipe_exception_lines``: a ``pending-``/``blocked-`` recipe whose conda name is not active on
    conda-forge, or (a PyPI-registry recipe) whose upstream name is not in the PyPI export. Conda-side membership is
    exact spelling; PyPI-side folds both sides."""
    if recipe_extras is None or recipe_extras.empty or "dir_name" not in recipe_extras.columns:
        return []
    lines = []
    for row in recipe_extras.sort_values("dir_name").to_dict("records"):
        status = _cell(row.get("status"))
        if not (status.startswith("pending-") or status.startswith("blocked-")):
            continue
        rdir = _cell(row.get("dir_name"))
        conda_name = _cell(row.get("conda_name")) or rdir
        if conda_name not in conda_names:
            lines.append(f"{rdir}: conda:{conda_name} not-on-cf (status={status})")
            continue
        if _cell(row.get("upstream_registry")) == "pypi":
            upstream = _cell(row.get("upstream_name")) or conda_name
            if fold_name(upstream) not in pypi_fold_index:
                lines.append(f"{rdir}: pypi:{upstream} not-in-pypi-export")
    return lines


def _upstream_lines(pkgs: pd.DataFrame, mapped: set[str], recipe_fields: pd.DataFrame) -> list[str]:
    """legacy ``upstream_tsv_lines`` over the recipes' own URLs: each active, PyPI-unmapped package's
    ``repo_url``, ``source_url``, ``dev_url`` and ``home_url``, classified by host as legacy's upstream sources
    are; one row per (package, source), from the first of those URLs that parses."""
    lines = [UPSTREAM_TSV_HEADER]
    if recipe_fields is None or recipe_fields.empty or "conda_name" not in recipe_fields.columns:
        return lines
    by_name = recipe_fields.drop_duplicates("conda_name").set_index("conda_name")
    url_columns = [c for c in ("repo_url", "source_url", "dev_url", "home_url") if c in by_name.columns]
    for name in pkgs["conda_name"]:
        if name in mapped or name not in by_name.index:
            continue
        found: dict[str, str] = {}
        for column in url_columns:
            url = _cell(by_name.at[name, column])
            source = _url_source(url) if url else None
            if source is None or source in found:
                continue
            purl = upstream_purl(source, url)
            if purl is not None:
                found[source] = purl
        for source in sorted(found):
            lines.append(f"pkg:conda/{name}{CHANNEL_QUALIFIER}\t{found[source]}\t{source}")
    return lines


def export_purl_artifacts(
    core_packages_enumerated: pd.DataFrame | None,
    core_latest_status: pd.DataFrame | None,
    pypi_conda_mapping: pd.DataFrame | None,
    pypi_universe: pd.DataFrame | None,
    discovery_recipe_extras_raw: pd.DataFrame | None,
    core_cf_graph_raw: pd.DataFrame | None,
    core_feedstock_attribution: pd.DataFrame | None,
    now: float | None = None,
) -> tuple[dict[str, str], pd.DataFrame]:
    # legacy: export_purls.py export_all  (cyclonedx-universe-inventory Wave A / S1)
    """The six export-purls artifacts (text partitions of ``derived_purl_artifacts``) and their manifest: one row
    per artifact with ``regenerated_at`` (this run, ``now`` pins it in tests) and ``row_count`` (its lines, a
    TSV's header not counted)."""
    pkgs = _active_packages(core_packages_enumerated, core_latest_status)
    conda_names = set(pkgs["conda_name"])
    mapping = _mapping_rows(pypi_conda_mapping)
    mapping = mapping[mapping["conda_name"].isin(conda_names)]
    names = (
        pypi_universe["pypi_name"].dropna().astype(str)
        if pypi_universe is not None and "pypi_name" in pypi_universe.columns
        else pd.Series(dtype=str)
    )
    pypi_lines = sorted({f"pkg:pypi/{g98_pypi_name(n)}" for n in names}, key=lambda line: line.encode())
    pypi_fold_index = {fold_name(line[len("pkg:pypi/") :]) for line in pypi_lines}

    conda_lines = [f"pkg:conda/{name}{CHANNEL_QUALIFIER}" for name in pkgs["conda_name"]]
    versioned = [
        f"pkg:conda/{name}@{_cell(ver)}{CHANNEL_QUALIFIER}" if _cell(ver) else f"pkg:conda/{name}{CHANNEL_QUALIFIER}"
        for name, ver in zip(pkgs["conda_name"], pkgs["latest_version"], strict=True)
    ]
    mapped_lines = [MAPPED_TSV_HEADER]
    order = {name: i for i, name in enumerate(pkgs["conda_name"])}
    for row in sorted(mapping.to_dict("records"), key=lambda r: (order[r["conda_name"]], r["pypi_name"])):
        mapped_lines.append(
            f"pkg:conda/{row['conda_name']}{CHANNEL_QUALIFIER}\tpkg:pypi/{g98_pypi_name(row['pypi_name'])}\t"
            f"{_cell(row['match_source'])}\t{_cell(row['match_confidence'])}"
        )
    exceptions = _exception_lines(discovery_recipe_extras_raw, conda_names, pypi_fold_index)
    recipe_fields = package_recipe_fields(core_cf_graph_raw, core_feedstock_attribution)
    upstream_lines = _upstream_lines(pkgs, set(mapping["conda_name"]), recipe_fields)

    contents = {
        "purls_conda-forge.txt": conda_lines,
        "purls_conda-forge_versioned.txt": versioned,
        "purls_pypi.txt": pypi_lines,
        "purls_conda-pypi_mapped.tsv": mapped_lines,
        "recipe-purl-exceptions.txt": exceptions,
        "purls_conda-upstream_mapped.tsv": upstream_lines,
    }
    stamp = datetime.fromtimestamp(time.time() if now is None else now, tz=UTC).replace(microsecond=0)
    partitions = {name: "".join(f"{line}\n" for line in lines) for name, lines in contents.items()}
    manifest = pd.DataFrame(
        {
            "artifact_name": pd.Series(list(ARTIFACTS), dtype="string"),
            "regenerated_at": pd.Series([stamp] * len(ARTIFACTS), dtype="datetime64[us, UTC]"),
            "row_count": pd.Series(
                [len(contents[name]) - (1 if name in TSV_ARTIFACTS else 0) for name in ARTIFACTS], dtype="int64"
            ),
        },
        columns=MANIFEST_COLUMNS,
    )
    return partitions, manifest
