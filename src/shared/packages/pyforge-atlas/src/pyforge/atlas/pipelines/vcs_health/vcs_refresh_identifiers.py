"""Extract VCS/registry refresh identifier batches from the identity join (Story 27.2), or, with
``pyforge.atlas.live_vcs_universe`` on, from the whole universe (Story 35.2)."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from pyforge.atlas.datasets.core_sources import package_recipe_fields

_GITHUB_RE = re.compile(r"^pkg:github/([^/]+)/([^/#?\s]+)", re.I)
_GITLAB_RE = re.compile(r"^pkg:gitlab/([^/]+)/(.+)$", re.I)
_CODEBERG_RE = re.compile(r"^pkg:codeberg/([^/]+)/([^/#?\s]+)", re.I)
_REGISTRY_PURL: dict[str, re.Pattern[str]] = {
    "npm": re.compile(r"^pkg:npm/(.+)$", re.I),
    "cran": re.compile(r"^pkg:cran/(.+)$", re.I),
    "cpan": re.compile(r"^pkg:cpan/(.+)$", re.I),
    "luarocks": re.compile(r"^pkg:luarocks/(.+)$", re.I),
    "crates": re.compile(r"^pkg:crates/(.+)$", re.I),
    "rubygems": re.compile(r"^pkg:rubygems/(.+)$", re.I),
    "maven": re.compile(r"^pkg:maven/(.+)$", re.I),
    "nuget": re.compile(r"^pkg:nuget/(.+)$", re.I),
}


def _pep503(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _split_purls(*fields: str) -> list[str]:
    out: list[str] = []
    for field in fields:
        if not isinstance(field, str) or not field.strip():
            continue
        for part in field.split(";"):
            p = part.strip()
            if p:
                out.append(p)
    return out


def batches_from_identity(identity_packages_primary: pd.DataFrame | None) -> dict[str, Any]:
    """Return github_repos + per-store vcs_pairs keyed by registry/host store suffix."""
    github: set[tuple[str, str]] = set()
    gitlab: dict[str, str] = {}
    codeberg: dict[str, str] = {}
    registries: dict[str, dict[str, str]] = {k: {} for k in _REGISTRY_PURL}

    if identity_packages_primary is None or getattr(identity_packages_primary, "empty", True):
        return {"github_repos": (), "gitlab": (), "codeberg": (), "registries": {k: () for k in _REGISTRY_PURL}}

    name_col = "Core_Python_Package_Name"
    if name_col not in identity_packages_primary.columns:
        return {"github_repos": (), "gitlab": (), "codeberg": (), "registries": {k: () for k in _REGISTRY_PURL}}

    for row in identity_packages_primary.itertuples(index=False):
        conda_name = getattr(row, name_col, None)
        if not isinstance(conda_name, str) or not conda_name.strip():
            continue
        purls = _split_purls(
            getattr(row, "primary_purl", "") or "",
            getattr(row, "alternative_purls", "") or "",
            getattr(row, "source_repository_url", "") or "",
        )
        for purl in purls:
            if m := _GITHUB_RE.match(purl):
                github.add((m.group(1), m.group(2)))
            if m := _GITLAB_RE.match(purl):
                gitlab[_pep503(conda_name)] = f"{m.group(1)}/{m.group(2)}"
            if m := _CODEBERG_RE.match(purl):
                codeberg[_pep503(conda_name)] = f"{m.group(1)}/{m.group(2)}"
            for reg, pat in _REGISTRY_PURL.items():
                if m := pat.match(purl):
                    registries[reg][_pep503(conda_name)] = m.group(1)

    def _pairs(mapping: dict[str, str]) -> tuple[tuple[str, str], ...]:
        return tuple((k, v) for k, v in sorted(mapping.items()))

    return {
        "github_repos": tuple(sorted(github)),
        "gitlab": _pairs(gitlab),
        "codeberg": _pairs(codeberg),
        "registries": {reg: _pairs(mapping) for reg, mapping in registries.items()},
    }


# -- Story 35.2: the batches from the whole universe (legacy Phases K, L and N) ------------------

# legacy Phase K's repo extraction (``_extract_vcs_repo``, CFA:4575-4606)
_K_GITHUB = re.compile(r"github\.com/([^/\s,]+)/([^/?#.\s,()<>\"']+)")
_K_GITLAB = re.compile(r"gitlab\.com/([^?#\s,]+?)(?:/-/|/?(?:$|[?#\s,]))")
_K_CODEBERG = re.compile(r"codeberg\.org/([^/\s,]+)/([^/?#.\s,()<>\"']+)")
# legacy Phase L's names: npm and Maven from the recipe's source URL (CFA:2049, 2053, 2450-2467), and
# crates, rubygems, nuget and Maven from the about URLs (``_detect_registry_from_urls``, CFA:5746-5785)
_L_NPM_SOURCE = re.compile(r"registry\.npmjs\.org/(@[^/]+/[^/]+|[^/]+)/-/")
_L_MAVEN_SOURCE = re.compile(
    r"(?:repo\.maven\.apache\.org/maven2|repo1\.maven\.org/maven2)/([^?#]+?)/([^/]+)/[^/]+/[^/]+\.(?:jar|pom|aar)"
)
_L_URL_NAMES = (
    ("crates", re.compile(r"crates\.io/crates/([A-Za-z0-9_-]+)")),
    ("rubygems", re.compile(r"rubygems\.org/gems/([A-Za-z0-9_.-]+)")),
    ("nuget", re.compile(r"nuget\.org/packages/([A-Za-z0-9_.-]+)")),
)
_L_MAVEN_URL = re.compile(
    r"(?:search\.maven\.org/artifact|mvnrepository\.com/artifact|central\.sonatype\.com/artifact)"
    r"/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)"
)


def vcs_repo(*urls: Any) -> tuple[str, str, str] | None:
    """``(host, owner_or_path, repo)`` from the first URL that names a GitHub, Codeberg or GitLab
    repo, checked in that order per URL, as legacy Phase K does (CFA:4580). For GitLab the second
    field is the whole project path (subgroups included)."""
    for url in urls:
        if not isinstance(url, str) or not url:
            continue
        if m := _K_GITHUB.search(url):
            return ("github", m.group(1), m.group(2).rstrip("/"))
        if m := _K_CODEBERG.search(url):
            return ("codeberg", m.group(1), m.group(2).rstrip("/"))
        if m := _K_GITLAB.search(url):
            path = m.group(1).rstrip("/")
            path = path[:-4] if path.endswith(".git") else path
            return ("gitlab", path, path.rsplit("/", 1)[-1])
    return None


def registry_names(source_url: Any, *about_urls: Any) -> list[tuple[str, str]]:
    """``(registry, name)`` pairs legacy Phase L queries for one package: npm and Maven from the
    source URL, then crates, rubygems, nuget and Maven from the about URLs. cran, cpan and luarocks
    names are never written by legacy (its Phase E fills only npm and Maven), so none come here."""
    found: list[tuple[str, str]] = []
    if isinstance(source_url, str):
        if m := _L_NPM_SOURCE.search(source_url):
            found.append(("npm", m.group(1)))
        if m := _L_MAVEN_SOURCE.search(source_url):
            found.append(("maven", f"{m.group(1).strip('/').replace('/', '.')}:{m.group(2)}"))
    for url in about_urls:
        if not isinstance(url, str) or not url:
            continue
        for registry, pattern in _L_URL_NAMES:
            if m := pattern.search(url):
                found.append((registry, m.group(1)))
        if m := _L_MAVEN_URL.search(url):
            found.append(("maven", f"{m.group(1)}:{m.group(2)}"))
    return list(dict.fromkeys(found))


def batches_from_universe(
    core_packages_enumerated: pd.DataFrame | None,
    core_cf_graph_raw: pd.DataFrame | None,
    core_feedstock_attribution: pd.DataFrame | None,
) -> dict[str, Any]:
    """Story 35.2: the refresh batches from every enumerated conda package (Phase B), with each
    package's recipe fields from its feedstock (Phase B.5 attribution, then its first anchor):

    - ``upstream_repos``: ``(conda_name, owner, repo)`` per GitHub upstream (Phase K);
    - ``gitlab`` / ``codeberg``: ``(conda_name, project)`` pairs (Phase K);
    - ``registries``: ``(conda_name, name)`` pairs per registry (Phase L);
    - ``feedstocks``: every feedstock an enumerated package is attributed to (Phase N).

    Deviation: legacy selects from ``v_actionable_packages`` (active, not archived); here every
    enumerated package is a candidate, a superset."""
    empty: dict[str, Any] = {
        "upstream_repos": (),
        "gitlab": (),
        "codeberg": (),
        "registries": {k: () for k in _REGISTRY_PURL},
        "feedstocks": (),
    }
    enum = core_packages_enumerated
    if enum is None or enum.empty or "conda_name" not in enum.columns:
        return empty
    names = {c for c in enum["conda_name"].dropna() if isinstance(c, str) and c}
    fields = package_recipe_fields(core_cf_graph_raw, core_feedstock_attribution)
    fields = fields[fields["conda_name"].isin(names)]
    upstream: set[tuple[str, str, str]] = set()
    hosts: dict[str, dict[str, str]] = {"gitlab": {}, "codeberg": {}}
    registries: dict[str, dict[str, str]] = {k: {} for k in _REGISTRY_PURL}
    for row in fields.itertuples(index=False):
        conda = row.conda_name
        repo = vcs_repo(row.repo_url, row.dev_url, row.home_url)
        if repo is not None:
            host, owner_or_path, name = repo
            if host == "github":
                upstream.add((conda, owner_or_path, name))
            else:
                hosts[host].setdefault(conda, owner_or_path if host == "gitlab" else f"{owner_or_path}/{name}")
        for registry, name in registry_names(row.source_url, row.repo_url, row.dev_url, row.home_url):
            registries[registry].setdefault(conda, name)
    feedstocks: set[str] = set()
    att = core_feedstock_attribution
    if att is not None and not att.empty and {"conda_name", "feedstock_name"} <= set(att.columns):
        for conda, feedstock in zip(att["conda_name"], att["feedstock_name"], strict=True):
            if conda in names and isinstance(feedstock, str) and feedstock:
                feedstocks.add(feedstock)

    def _pairs(mapping: dict[str, str]) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(mapping.items()))

    return {
        "upstream_repos": tuple(sorted(upstream)),
        "gitlab": _pairs(hosts["gitlab"]),
        "codeberg": _pairs(hosts["codeberg"]),
        "registries": {reg: _pairs(mapping) for reg, mapping in registries.items()},
        "feedstocks": tuple(sorted(feedstocks)),
    }
