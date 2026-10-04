"""Extract VCS/registry refresh identifier batches from the identity join (Story 27.2)."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

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
