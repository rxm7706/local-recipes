"""Core pipeline raw-source datasets (Story B1 gap closure).

The A2 catalog declared several ``api.APIDataset`` entries whose payloads are
NOT node-ready frames (zip/tar archives, multi-subdir repodata, channeldata
JSON). IO + parsing live here (AD-2); nodes stay pure ``DataFrame -> DataFrame``.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import tarfile
import zipfile
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset
from kedro_datasets.api import APIDataset

from .refresh import MappingCacheDataset

logger = logging.getLogger(__name__)

CONDA_FORGE_SUBDIRS = (
    "noarch",
    "linux-64",
    "linux-aarch64",
    "linux-ppc64le",
    "osx-64",
    "osx-arm64",
    "win-64",
)

_JINJA_TARGET = re.compile(r"^[\{\$]")


def _as_bytes(payload: Any) -> bytes:
    if isinstance(payload, bytes):
        return payload
    content = getattr(payload, "content", None)
    if isinstance(content, bytes):
        return content
    if hasattr(payload, "read"):
        data = payload.read()
        if isinstance(data, bytes):
            return data
    raise TypeError(f"expected bytes-like API payload, got {type(payload)!r}")


def _api_json(payload: Any) -> dict[str, Any] | None:
    """Normalize ``APIDataset.load()`` return value to a JSON dict."""
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "json"):
        try:
            data = payload.json()
            return data if isinstance(data, dict) else None
        except ValueError, TypeError:
            return None
    if isinstance(payload, (bytes, str)):
        try:
            data = json.loads(payload)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError, TypeError, UnicodeDecodeError:
            return None
    return None


def parse_feedstock_outputs_zip(zip_bytes: bytes) -> pd.DataFrame:
    """Parse conda-forge/feedstock-outputs ``main.zip`` → ``conda_name``, ``feedstocks``."""
    mapping: dict[str, list[str]] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not name.endswith(".json") or "/outputs/" not in name:
                continue
            package_name = name.rsplit("/", 1)[-1][:-5]
            if not package_name:
                continue
            try:
                payload = json.loads(zf.read(name))
            except json.JSONDecodeError, UnicodeDecodeError:
                continue
            feedstocks = payload.get("feedstocks") or []
            if feedstocks:
                mapping[package_name] = list(feedstocks)
    if not mapping:
        return pd.DataFrame(columns=["conda_name", "feedstocks"])
    rows = [{"conda_name": k, "feedstocks": v} for k, v in sorted(mapping.items())]
    return pd.DataFrame(rows)


def repodata_json_to_rows(repodata: dict[str, Any], subdir: str) -> list[dict[str, Any]]:
    """Flatten one subdir's ``current_repodata.json`` to node-ready rows."""
    rows: list[dict[str, Any]] = []
    for source_dict in (repodata.get("packages.conda", {}), repodata.get("packages", {})):
        if not isinstance(source_dict, dict):
            continue
        for rec in source_dict.values():
            if not isinstance(rec, dict):
                continue
            name = rec.get("name")
            version = rec.get("version")
            if not name or version is None:
                continue
            rows.append(
                {
                    "conda_name": name,
                    "version": version,
                    "timestamp": rec.get("timestamp"),
                    "subdir": subdir,
                }
            )
    return rows


def channeldata_json_to_rows(payload: dict[str, Any]) -> pd.DataFrame:
    """Parse ``channeldata.json`` → ``conda_name``, ``subdirs`` (list per row)."""
    packages = payload.get("packages") or {}
    if not isinstance(packages, dict):
        return pd.DataFrame(columns=["conda_name", "subdirs"])
    rows: list[dict[str, Any]] = []
    for name, meta in sorted(packages.items()):
        if not isinstance(meta, dict):
            continue
        subdirs = meta.get("subdirs") or []
        if not isinstance(subdirs, list):
            subdirs = [subdirs]
        rows.append({"conda_name": name, "subdirs": subdirs})
    return pd.DataFrame(rows)


def _health_from_pr_info(pr_info: dict[str, Any] | None, version_info: dict[str, Any] | None) -> dict[str, Any]:
    pr_info = pr_info or {}
    version_info = version_info or {}
    open_prs = 0
    for pr in pr_info.get("prs") or []:
        if isinstance(pr, dict) and pr.get("state") == "open":
            open_prs += 1
    open_issues = len([i for i in (pr_info.get("issues") or []) if isinstance(i, dict)])
    ci_status = None
    checks = version_info.get("checks") or pr_info.get("checks")
    if isinstance(checks, dict):
        ci_status = checks.get("state") or checks.get("status")
    return {
        "ci_status": ci_status,
        "open_prs": open_prs,
        "open_issues": open_issues,
    }


def _requirements_pairs(feedstock_basename: str, payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    meta_yaml = payload.get("meta_yaml")
    if not isinstance(meta_yaml, dict):
        return []
    pairs: list[tuple[str, dict[str, Any]]] = []
    outputs_block = meta_yaml.get("outputs")
    if isinstance(outputs_block, list) and outputs_block:
        seen: set[str] = set()
        for out in outputs_block:
            if not isinstance(out, dict):
                continue
            out_name = (out.get("name") or "").strip()
            if not out_name or out_name in seen:
                continue
            seen.add(out_name)
            out_reqs = out.get("requirements")
            if isinstance(out_reqs, dict):
                pairs.append((out_name, out_reqs))
        if not pairs:
            outputs_block = None
    if not pairs:
        outputs_raw = payload.get("outputs_names")
        ons: list[str] = []
        if isinstance(outputs_raw, dict) and "elements" in outputs_raw:
            elems = outputs_raw.get("elements") or []
            if isinstance(elems, list):
                ons = [str(e) for e in elems if e]
        elif isinstance(outputs_raw, list):
            ons = [str(e) for e in outputs_raw if e]
        sn = ons[0] if ons else feedstock_basename
        top_reqs = meta_yaml.get("requirements")
        if isinstance(top_reqs, dict):
            pairs.append((sn, top_reqs))
    return pairs


def parse_cf_graph_tarball(tar_bytes: bytes) -> pd.DataFrame:
    """Parse cf-graph-countyfair tarball → flat frame for Phases J + M nodes."""
    pr_info_data: dict[str, dict[str, Any]] = {}
    version_pr_info_data: dict[str, dict[str, Any]] = {}
    edge_rows: list[dict[str, Any]] = []
    health_feedstocks: set[str] = set()

    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
        for member in tf:
            if not member.isfile() or not member.name.endswith(".json"):
                continue
            f = tf.extractfile(member)
            if f is None:
                continue
            if "/pr_info/" in member.name and "/version_pr_info/" not in member.name:
                feedstock = member.name.rsplit("/", 1)[-1][:-5]
                try:
                    pr_info_data[feedstock] = json.load(f)
                except json.JSONDecodeError, UnicodeDecodeError:
                    pass
                continue
            if "/version_pr_info/" in member.name:
                feedstock = member.name.rsplit("/", 1)[-1][:-5]
                try:
                    version_pr_info_data[feedstock] = json.load(f)
                except json.JSONDecodeError, UnicodeDecodeError:
                    pass
                continue
            if "/node_attrs/" not in member.name:
                continue
            feedstock_basename = member.name.rsplit("/", 1)[-1][:-5]
            try:
                payload = json.load(f)
            except json.JSONDecodeError, UnicodeDecodeError:
                continue
            health = _health_from_pr_info(
                pr_info_data.get(feedstock_basename),
                version_pr_info_data.get(feedstock_basename),
            )
            health_feedstocks.add(feedstock_basename)
            archived = bool(payload.get("archived") or payload.get("feedstock_archived"))
            for source_name, reqs in _requirements_pairs(feedstock_basename, payload):
                for req_type in ("build", "host", "run", "test"):
                    spec_list = reqs.get(req_type)
                    if not isinstance(spec_list, list):
                        continue
                    seen: set[tuple[str, str]] = set()
                    for spec in spec_list:
                        if not isinstance(spec, str):
                            continue
                        spec = spec.strip()
                        if not spec:
                            continue
                        parts = spec.split(None, 1)
                        target = parts[0]
                        if target == source_name or _JINJA_TARGET.match(target):
                            continue
                        key = (target, req_type)
                        if key in seen:
                            continue
                        seen.add(key)
                        edge_rows.append(
                            {
                                "feedstock_name": feedstock_basename,
                                "conda_name": source_name,
                                "depends_on": target,
                                "dep_type": req_type,
                                "feedstock_archived": archived,
                                **health,
                            }
                        )

    # Feedstock-level health rows for feedstocks with pr_info but no emitted edges.
    for feedstock in sorted(set(pr_info_data) | set(version_pr_info_data)):
        if feedstock in health_feedstocks:
            continue
        health = _health_from_pr_info(pr_info_data.get(feedstock), version_pr_info_data.get(feedstock))
        edge_rows.append(
            {
                "feedstock_name": feedstock,
                "conda_name": pd.NA,
                "depends_on": pd.NA,
                "dep_type": pd.NA,
                "feedstock_archived": False,
                **health,
            }
        )

    cols = [
        "feedstock_name",
        "conda_name",
        "depends_on",
        "dep_type",
        "feedstock_archived",
        "ci_status",
        "open_prs",
        "open_issues",
    ]
    if not edge_rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(edge_rows)[cols]


class _HttpBytesDataset(AbstractDataset):
    """Fetch a single URL via composed ``APIDataset`` and return raw bytes."""

    def __init__(
        self,
        *,
        url: str,
        method: str = "GET",
        load_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._inner = APIDataset(
            url=url,
            method=method,
            load_args=load_args,
            credentials=credentials,
            metadata=metadata,
        )

    def load(self) -> bytes:
        return _as_bytes(self._inner.load())

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"url": self._inner._url if hasattr(self._inner, "_url") else "api"}


class FeedstockOutputsArchiveDataset(_HttpBytesDataset):
    """Phase B.5: feedstock-outputs zip → ``conda_name``, ``feedstocks`` frame."""

    def load(self) -> pd.DataFrame:
        return parse_feedstock_outputs_zip(super().load())


class CondaRepodataDataset(AbstractDataset):
    """Phase B: all platform ``current_repodata.json`` files → flat repodata frame."""

    def __init__(
        self,
        *,
        url: str,
        subdirs: tuple[str, ...] = CONDA_FORGE_SUBDIRS,
        load_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._base_url = url.rstrip("/")
        self._subdirs = subdirs
        self._load_args = load_args
        self._credentials = credentials
        self.metadata = metadata

    def load(self) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for subdir in self._subdirs:
            fetch_url = f"{self._base_url}/{subdir}/current_repodata.json"
            inner = APIDataset(
                url=fetch_url,
                load_args=self._load_args,
                credentials=self._credentials,
                metadata=self.metadata,
            )
            payload = inner.load()
            repodata = _api_json(payload)
            if repodata is not None:
                rows.extend(repodata_json_to_rows(repodata, subdir))
            else:
                logger.warning("subdir %s repodata was not JSON dict — skipped", subdir)
        if not rows:
            return pd.DataFrame(columns=["conda_name", "version", "timestamp", "subdir"])
        return pd.DataFrame(rows)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"base_url": self._base_url, "subdirs": list(self._subdirs)}


class CondaChanneldataDataset(AbstractDataset):
    """Phase B: ``channeldata.json`` → ``conda_name``, ``subdirs`` frame."""

    def __init__(
        self,
        *,
        url: str,
        load_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._inner = APIDataset(
            url=url,
            load_args=load_args,
            credentials=credentials,
            metadata=metadata,
        )

    def load(self) -> pd.DataFrame:
        payload = self._inner.load()
        repodata = _api_json(payload)
        if repodata is None:
            return pd.DataFrame(columns=["conda_name", "subdirs"])
        return channeldata_json_to_rows(repodata)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"url": "channeldata.json"}


class CfGraphTarballDataset(_HttpBytesDataset):
    """Phases J/M: cf-graph tarball → dependency + health frame."""

    def load(self) -> pd.DataFrame:
        return parse_cf_graph_tarball(super().load())


class S3DownloadStatsDataset(AbstractDataset):
    """Phase F s3-parquet source placeholder.

    Full monthly-parquet fan-out is attended/credentialed; until wired the node
    receives an empty but correctly-columned frame (graceful no-op in
    ``compute_downloads``).
    """

    def __init__(self, *, url: str, metadata: dict[str, Any] | None = None) -> None:
        self._url = url
        self.metadata = metadata

    def load(self) -> pd.DataFrame:
        return pd.DataFrame(columns=["conda_name", "month", "platform", "pyver", "channel", "downloads"])

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"url": self._url, "note": "stub-empty until s3-parquet fan-out lands"}


def parse_pypi_simple_index(payload: Any) -> pd.DataFrame:
    """PyPI Simple API v1 JSON → ``pypi_name``, ``last_serial`` frame."""
    doc = _api_json(payload)
    if not doc:
        return pd.DataFrame(columns=["pypi_name", "last_serial"])
    projects = doc.get("projects") or []
    rows: list[dict[str, Any]] = []
    for proj in projects:
        if not isinstance(proj, dict):
            continue
        name = proj.get("name")
        if not name:
            continue
        rows.append({"pypi_name": name, "last_serial": proj.get("_last-serial")})
    if not rows:
        return pd.DataFrame(columns=["pypi_name", "last_serial"])
    return pd.DataFrame(rows)[["pypi_name", "last_serial"]].reset_index(drop=True)


class PyPISimpleIndexDataset(AbstractDataset):
    """Phase D/O: PyPI Simple v1 JSON catalog → node-ready frame."""

    def __init__(
        self,
        *,
        url: str,
        load_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        args = dict(load_args or {})
        headers = dict(args.get("headers") or {})
        headers.setdefault("Accept", "application/vnd.pypi.simple.v1+json")
        args["headers"] = headers
        base = url.rstrip("/") + "/"
        self._inner = APIDataset(
            url=base,
            method="GET",
            load_args=args,
            credentials=credentials,
            metadata=metadata,
        )
        self.metadata = metadata

    def load(self) -> pd.DataFrame:
        return parse_pypi_simple_index(self._inner.load())

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"parameterization": type(self).__name__}


# Phase Q cross-channel specs: ``(short_name, channel, subdirs)``. Story 21.4 hardened
# every channel to a 2-subdir FALLBACK list (the first subdir that yields repodata
# wins — see ``_fetch_channel_repodata``): a channel that publishes under only one of
# ``noarch``/``linux-64`` no longer reads as "unavailable" just because the first
# guess 404s. The ``_REPDATA_FILENAMES`` current_repodata.json -> repodata.json
# fallback below is the second axis (selfexplainml + robostack-staging publish NO
# current_repodata.json at all — live-verified 2026-08-30). Order per channel is the
# subdir most likely to carry the bulk of the package names first.
_CROSS_CHANNEL_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("bioconda", "bioconda", ("noarch", "linux-64")),
    ("pytorch", "pytorch", ("noarch", "linux-64")),
    ("nvidia", "nvidia", ("noarch", "linux-64")),
    # robostack-staging: packages live under linux-64; channel omits current_repodata.json.
    ("robostack", "robostack-staging", ("linux-64", "noarch")),
    # Story 21.4 (Tier 1, catalog-sources.md): SelfExplainML publishes noarch + linux-64,
    # repodata.json only (no current_repodata.json), on conda.anaconda.org only (the
    # prefix.dev mirror 404s, so the mirror chain falls through to anaconda.org).
    ("selfexplainml", "selfexplainml", ("noarch", "linux-64")),
)
_REPDATA_FILENAMES = ("current_repodata.json", "repodata.json")


def _resolve_anaconda_channel_urls(
    channel: str,
    subdir: str,
    filename: str,
) -> list[str]:
    """Mirror legacy ``_http.resolve_anaconda_channel_urls`` for Phase Q fetches."""
    env_key = f"{channel.upper().replace('-', '_')}_BASE_URL"
    bases: list[str] = []
    env_base = os.environ.get(env_key)
    if env_base:
        bases.append(env_base.rstrip("/"))
    bases.extend((f"https://repo.prefix.dev/{channel}", f"https://conda.anaconda.org/{channel}"))
    seen: set[str] = set()
    urls: list[str] = []
    for base in bases:
        if base in seen:
            continue
        seen.add(base)
        urls.append(f"{base}/{subdir}/{filename}")
    return urls


def _fetch_repodata_at_url(
    url: str,
    *,
    load_args: dict[str, Any] | None,
    credentials: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    try:
        inner = APIDataset(
            url=url,
            load_args=load_args,
            credentials=credentials,
            metadata=metadata,
        )
        return _api_json(inner.load())
    except Exception as exc:
        logger.debug("cross-channel repodata fetch failed for %s: %s", url, exc)
        return None


def _repodata_has_packages(repodata: dict[str, Any]) -> bool:
    """True when the index carries at least one record under ``packages`` or
    ``packages.conda``. A VALID but EMPTY index (``{"packages": {}, "packages.conda":
    {}}`` — common for an unpopulated ``noarch``) must NOT count as a successful fetch,
    or the per-channel subdir fallback would never be tried (review-pass 1, Story 21.4)."""
    for key in ("packages.conda", "packages"):
        source = repodata.get(key)
        if isinstance(source, dict) and source:
            return True
    return False


def _fetch_channel_repodata(
    channel_name: str,
    subdirs: tuple[str, ...],
    *,
    load_args: dict[str, Any] | None,
    credentials: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch one channel's repodata; mirrors legacy ``_phase_q_fetch_channel_pypi_names`` IO.
    The first ``(subdir, filename, mirror)`` combo whose index actually carries packages
    wins; a missing OR empty index falls through to the next combo. ``(None, None)``
    only after every combo is exhausted."""
    for subdir in subdirs:
        for filename in _REPDATA_FILENAMES:
            for url in _resolve_anaconda_channel_urls(channel_name, subdir, filename):
                repodata = _fetch_repodata_at_url(
                    url,
                    load_args=load_args,
                    credentials=credentials,
                    metadata=metadata,
                )
                if repodata is None:
                    continue
                if not _repodata_has_packages(repodata):
                    logger.debug("cross-channel repodata at %s is empty — trying the next combo", url)
                    continue
                return repodata, subdir
    return None, None


class CrossChannelRepodataDataset(AbstractDataset):
    """Phase Q: bulk repodata from bioconda/pytorch/nvidia/robostack/selfexplainml →
    ``conda_name``, ``channel`` (Story 21.4 added selfexplainml as the 5th
    ``_CROSS_CHANNEL_SPECS`` tuple — same entry, same parser, no new catalog entry)."""

    def __init__(
        self,
        *,
        url: str,
        load_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        _ = url  # catalog placeholder; URLs resolve per-channel via env + mirrors
        self._load_args = load_args
        self._credentials = credentials
        self.metadata = metadata

    def load(self) -> pd.DataFrame:
        rows: list[dict[str, str]] = []
        for channel_short, channel_name, subdirs in _CROSS_CHANNEL_SPECS:
            repodata, subdir = _fetch_channel_repodata(
                channel_name,
                subdirs,
                load_args=self._load_args,
                credentials=self._credentials,
                metadata=self.metadata,
            )
            if repodata is None or subdir is None:
                logger.warning(
                    "cross-channel repodata for %s unavailable — skipped",
                    channel_short,
                )
                continue
            for row in repodata_json_to_rows(repodata, subdir):
                rows.append({"conda_name": row["conda_name"], "channel": channel_short})
        if not rows:
            return pd.DataFrame(columns=["conda_name", "channel"])
        return pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"parameterization": type(self).__name__, "channels": list(_CROSS_CHANNEL_SPECS)}


class ParselmouthMappingDataset(AbstractDataset):
    """Phase C: parselmouth / verified mapping slice for ``pypi_parselmouth_mapping_raw``.

    Story 21.2: reads the already-populated ``pypi_conda_map_store`` flat cache
    (produced by the ``export_pypi_conda_map`` node, Story 21.1's bootstrap chain) via
    a composed :class:`~.refresh.MappingCacheDataset` pointed at the SAME ``filepath``
    — never a second fetch (the intent's "Parselmouth reads from the existing
    pypi_conda_map_store rather than a new fetch"). The composed dataset ALREADY owns
    the AD-13 last-good/staleness discipline; this class only reprojects its flat
    ``{pypi_name: conda_name}`` map to the 3-column shape Phase C nodes expect.
    """

    _COLUMNS = ("pypi_name", "conda_name", "match_source")
    _MATCH_SOURCE = "pypi_conda_map_store"

    def __init__(self, *, filepath: str, metadata: dict[str, Any] | None = None) -> None:
        # No **kwargs sink: an unrecognized catalog key must raise loudly (a stale
        # catalog misconfiguration) rather than be silently discarded.
        self._filepath = filepath
        self.metadata = metadata
        self._cache = MappingCacheDataset(filepath=filepath)

    def load(self) -> pd.DataFrame:
        try:
            mapping = self._cache.load()
        except Exception as exc:  # never raise (AD-13): degrade to empty.
            logger.warning("pypi_conda_map_store unreadable, degrading to empty: %s", exc)
            mapping = {}
        if not isinstance(mapping, dict):
            mapping = {}
        if not mapping:
            return pd.DataFrame(columns=self._COLUMNS)
        rows = [
            {"pypi_name": k, "conda_name": v, "match_source": self._MATCH_SOURCE}
            for k, v in sorted(mapping.items())
            if isinstance(k, str) and isinstance(v, str)
        ]
        return pd.DataFrame(rows, columns=self._COLUMNS).reset_index(drop=True)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"parameterization": type(self).__name__, "filepath": self._filepath}
