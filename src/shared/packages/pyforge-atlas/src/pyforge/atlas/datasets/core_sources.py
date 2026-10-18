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
import zlib
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io import AbstractDataset, DatasetError
from kedro_datasets.api import APIDataset
from pyforge.core.atomic_write import atomic_write
from pyforge.core.errors import PyforgeError

from .json_sources import JSONSourceDataset, _describe_exc
from .refresh import StalenessMarker, _safe_int

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


def _health_from_pr_info(
    pr_info: dict[str, Any] | None,
    version_info: dict[str, Any] | None,
    pr_json: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Feedstock bot health, ported from legacy Phase M (``phase_m_feedstock_health``,
    CFA:6263): ``pr_info.PRed`` is a list of ``{"PR": {"state"}, "data": {"version"}}``;
    ``bad`` on either record flags the feedstock; ``version_pr_info.new_version_errors``
    counts failed version-update attempts. ``open_prs`` is the open bot-PR count (the
    column consumers already read); ``ci_status`` and ``open_issues`` are live GitHub
    signals the bot data does not carry (Phase N, Story 35.3) and stay NA here. Story 34.3:
    the bot keeps closed PRs inline and stores live ones as ``{"__lazy_json__":
    "pr_json/<id>.json"}`` references into ``conda-forge-bot-data-pr_json``; ``pr_json``
    (``id -> record``) resolves them, else a reference counts as unknown, never open."""
    pr_info = pr_info if isinstance(pr_info, dict) else {}
    version_info = version_info if isinstance(version_info, dict) else {}
    raw_pred = pr_info.get("PRed")
    pred: list[Any] = raw_pred if isinstance(raw_pred, list) else []
    refs = pr_json or {}

    def _pr(entry: Any) -> dict[str, Any] | None:
        pr = entry.get("PR") if isinstance(entry, dict) else None
        if isinstance(pr, dict) and isinstance(pr.get("__lazy_json__"), str):
            pr = refs.get(pr["__lazy_json__"].rsplit("/", 1)[-1].removesuffix(".json"))
        return pr if isinstance(pr, dict) else None

    open_count = 0
    for entry in pred:
        pr = _pr(entry)
        if pr is not None and pr.get("state") == "open":
            open_count += 1
    last_state: Any = pd.NA
    last_version: Any = pd.NA
    if pred and isinstance(pred[-1], dict):
        last_pr, last_data = _pr(pred[-1]), pred[-1].get("data")
        if isinstance(last_pr, dict) and last_pr.get("state") is not None:
            last_state = last_pr.get("state")
        if isinstance(last_data, dict) and last_data.get("version") is not None:
            last_version = str(last_data.get("version"))
    errs = version_info.get("new_version_errors")
    errs_count = len(errs) if isinstance(errs, (list, dict)) else 0
    return {
        "ci_status": pd.NA,
        "open_prs": open_count,
        "open_issues": pd.NA,
        "bot_last_pr_state": last_state,
        "bot_last_pr_version": last_version,
        "bot_version_errors_count": errs_count,
        "feedstock_bad": bool(pr_info.get("bad") or version_info.get("bad")),
    }


def _maintainers(payload: dict[str, Any]) -> list[str]:
    """``meta_yaml.extra.recipe-maintainers`` (legacy Phase E, CFA:2335)."""
    meta = payload.get("meta_yaml")
    extra = meta.get("extra") if isinstance(meta, dict) else None
    maints = extra.get("recipe-maintainers") if isinstance(extra, dict) else None
    if isinstance(maints, str):
        maints = [maints]
    return sorted({str(m) for m in maints if m}) if isinstance(maints, list) else []


def _outputs_names(payload: dict[str, Any]) -> list[str]:
    """``outputs_names``: a plain list, or cf-scripts' ``{"elements": [...]}`` set encoding."""
    outputs_raw = payload.get("outputs_names")
    if isinstance(outputs_raw, dict):
        outputs_raw = outputs_raw.get("elements")
    return [str(e) for e in outputs_raw if e] if isinstance(outputs_raw, list) else []


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
        ons = _outputs_names(payload)
        sn = ons[0] if ons else feedstock_basename
        top_reqs = meta_yaml.get("requirements")
        if isinstance(top_reqs, dict):
            pairs.append((sn, top_reqs))
    return pairs


_CF_GRAPH_COLUMNS = [
    "feedstock_name",
    "conda_name",
    "depends_on",
    "dep_type",
    "feedstock_archived",
    "ci_status",
    "open_prs",
    "open_issues",
    "bot_last_pr_state",
    "bot_last_pr_version",
    "bot_version_errors_count",
    "feedstock_bad",
    "maintainers",
]


def _graph_key(path: str) -> str:
    """The graph node a member holds: its path below the tarball's top directory, without
    cf-scripts' five one-character sha1 shard directories and ``.json``. Most nodes are a
    bare feedstock name; a few nest (``conda-forge/label/<name>``, measured 2026-10-18), and
    keying by basename alone would merge them with a different node."""
    parts = path.split("/")[1:]
    dirs, name = parts[:-1], parts[-1].removesuffix(".json")
    if len(dirs) >= 5 and all(len(d) == 1 for d in dirs[-5:]):
        dirs = dirs[:-5]
    return "/".join([*dirs, name])


def _tar_json_members(
    tar_bytes: bytes, select: Callable[[str], bool] | None = None
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Yield ``(member path, graph key, decoded payload)`` for each JSON file, one at a
    time; ``select`` skips a member by path before it is decoded."""
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
        for member in tf:
            if not member.isfile() or not member.name.endswith(".json"):
                continue
            if select is not None and not select(member.name):
                continue
            f = tf.extractfile(member)
            if f is None:
                continue
            try:
                payload = json.load(f)
            except json.JSONDecodeError, UnicodeDecodeError:
                continue
            if isinstance(payload, dict):
                yield member.name, _graph_key(member.name), payload


def _tar_records(tar_bytes: bytes | None) -> dict[str, dict[str, Any]]:
    """``basename -> payload`` for one of the small bot repos (pr_info, version_pr_info, pr_json)."""
    return {name: payload for _, name, payload in _tar_json_members(tar_bytes)} if tar_bytes else {}


def _cf_graph_frame(
    node_attrs: Iterable[tuple[str, dict[str, Any]]],
    pr_info: dict[str, dict[str, Any]],
    version_pr_info: dict[str, dict[str, Any]],
    pr_json: dict[str, dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Build the flat Phases E/J/M frame: one row per dependency edge, plus one anchor row
    (``depends_on`` NA) per output name so every output keeps its maintainers and health
    even with no edges, plus one row per feedstock that has bot data but no node_attrs.

    ``node_attrs`` is consumed as a stream of ``(feedstock, payload)``: each payload becomes
    rows and is dropped, so the 30k decoded node_attrs records are never held at once. The
    first record of a feedstock wins; rows come out sorted by feedstock."""
    rows: list[dict[str, Any]] = []
    seen_feedstocks: set[str] = set()
    for feedstock, payload in node_attrs:
        if feedstock in seen_feedstocks:
            continue
        seen_feedstocks.add(feedstock)
        health = _health_from_pr_info(pr_info.get(feedstock), version_pr_info.get(feedstock), pr_json)
        maints = _maintainers(payload)
        archived = bool(payload.get("archived") or payload.get("feedstock_archived"))
        base = {"feedstock_name": feedstock, "feedstock_archived": archived, "maintainers": maints, **health}
        pairs = _requirements_pairs(feedstock, payload)
        # every output a feedstock names, with or without a requirements block (Phase E)
        anchors = list(dict.fromkeys([*(name for name, _ in pairs), *_outputs_names(payload)])) or [feedstock]
        for source_name in anchors:
            rows.append({**base, "conda_name": source_name, "depends_on": pd.NA, "dep_type": pd.NA})
        for source_name, reqs in pairs:
            for req_type in ("build", "host", "run", "test"):
                spec_list = reqs.get(req_type)
                if not isinstance(spec_list, list):
                    continue
                seen: set[tuple[str, str]] = set()
                for spec in spec_list:
                    if not isinstance(spec, str) or not spec.strip():
                        continue
                    target = spec.strip().split(None, 1)[0]
                    if target == source_name or _JINJA_TARGET.match(target):
                        continue
                    if (target, req_type) in seen:
                        continue
                    seen.add((target, req_type))
                    rows.append({**base, "conda_name": source_name, "depends_on": target, "dep_type": req_type})
    for feedstock in sorted((set(pr_info) | set(version_pr_info)) - seen_feedstocks):
        health = _health_from_pr_info(pr_info.get(feedstock), version_pr_info.get(feedstock), pr_json)
        rows.append(
            {
                "feedstock_name": feedstock,
                "conda_name": pd.NA,
                "depends_on": pd.NA,
                "dep_type": pd.NA,
                "feedstock_archived": False,
                "maintainers": [],
                **health,
            }
        )
    if not rows:
        return pd.DataFrame(columns=_CF_GRAPH_COLUMNS)
    return pd.DataFrame(rows)[_CF_GRAPH_COLUMNS].sort_values("feedstock_name", kind="stable", ignore_index=True)


def _node_attrs_stream(tar_bytes: bytes) -> Iterator[tuple[str, dict[str, Any]]]:
    return ((name, payload) for _, name, payload in _tar_json_members(tar_bytes))


def parse_cf_graph_tarballs(
    node_attrs: bytes,
    pr_info: bytes | None = None,
    version_pr_info: bytes | None = None,
    pr_json: bytes | None = None,
) -> pd.DataFrame:
    """Story 34.3: parse the conda-forge bot's split graph repos
    (``conda-forge-bot-data-node_attrs``, ``-pr_info``, ``-version_pr_info``, ``-pr_json``).
    Each holds one ``<feedstock>.json`` (``<pr id>.json`` for pr_json) under a five-level
    sha1 shard (``<repo>-main/a/b/c/d/e/<name>.json``); the key is the node name with the
    shard removed (:func:`_graph_key`). The small bot records are read first, then node_attrs
    is streamed."""
    return _cf_graph_frame(
        _node_attrs_stream(node_attrs), _tar_records(pr_info), _tar_records(version_pr_info), _tar_records(pr_json)
    )


def parse_cf_graph_tarball(tar_bytes: bytes) -> pd.DataFrame:
    """The pre-split combined layout (``…/node_attrs/…``, ``…/pr_info/…``,
    ``…/version_pr_info/…`` in one tarball), kept for fixtures and mirrors that still
    serve it. Story 34.3: the live source is the split repos (:func:`parse_cf_graph_tarballs`).
    Two passes: the bot records first, then node_attrs streamed, as in the split layout."""
    pi: dict[str, dict[str, Any]] = {}
    vpi: dict[str, dict[str, Any]] = {}
    for path, key, payload in _tar_json_members(tar_bytes, select=lambda p: "/node_attrs/" not in p):
        if "/version_pr_info/" in path:
            vpi[key.removeprefix("version_pr_info/")] = payload
        elif "/pr_info/" in path:
            pi[key.removeprefix("pr_info/")] = payload
    node_attrs = (
        (key.removeprefix("node_attrs/"), payload)
        for _, key, payload in _tar_json_members(tar_bytes, select=lambda p: "/node_attrs/" in p)
    )
    return _cf_graph_frame(node_attrs, pi, vpi)


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
        empty = pd.DataFrame(columns=["conda_name", "subdirs"])
        try:
            payload = self._inner.load()
        except Exception as exc:
            logger.warning("CondaChanneldataDataset transport error, degrading to empty: %s", exc)
            return empty
        repodata = _api_json(payload)
        if repodata is None:
            return empty
        return channeldata_json_to_rows(repodata)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"url": "channeldata.json"}


class _SourceEmpty(PyforgeError, Exception):
    """A configured bot repo answered, but with no records (a redirect, an empty repo)."""


# a fetch failure (kedro's wrapper) or a body that is not a readable gzip tarball; a parser
# bug (KeyError, TypeError, ...) still raises instead of turning into a silent stale serve
_FETCH_OR_PARSE_ERRORS = (DatasetError, tarfile.TarError, EOFError, OSError, zlib.error)


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, str) or not hasattr(value, "__iter__"):
        return []
    return [str(m) for m in value]


def _read_last_good(path: Path) -> pd.DataFrame | None:
    """The kept frame, or ``None`` when absent or unreadable. Parquet hands a list column
    back as numpy arrays; ``maintainers`` is turned back into ``list[str]`` so
    ``enrich_maintainers`` reads the copy exactly as it read the fresh frame."""
    try:
        kept = pd.read_parquet(path)
    except Exception:  # noqa: BLE001 -- an absent or unreadable copy is "no last-good"
        return None
    if "maintainers" in kept.columns:
        kept["maintainers"] = [_as_str_list(v) for v in kept["maintainers"]]
    return kept


class CfGraphTarballDataset(AbstractDataset):
    """Phases E/J/M: the conda-forge bot's graph -> dependency, health and maintainer frame.

    Story 34.3: ``regro/cf-graph-countyfair`` now serves ``conda-forge/conda-forge-bot-data``,
    whose tarball has no ``node_attrs/``, ``pr_info/`` or ``version_pr_info/``; cf-scripts
    publishes them as three repos. ``url`` is the node_attrs tarball, ``pr_info_url`` and
    ``version_pr_info_url`` the next two and ``pr_json_url`` the live-PR records the
    pr_info references resolve against (each composed ``APIDataset``; no client of its
    own). With ``filepath``, a parsed frame is kept as ``last_good.parquet``; a failed fetch,
    a body that is not a gzip tarball, a configured bot repo with no records, or a frame with
    no node_attrs serves it under the AD-13 ``.staleness.json`` marker instead of raising.
    ``staleness()`` and ``last_good_path`` let the read surface report it. Without
    ``filepath`` (fixtures) a failure raises as before.
    """

    LAST_GOOD_FILENAME = "last_good.parquet"
    STALENESS_FILENAME = ".staleness.json"

    def __init__(
        self,
        *,
        url: str,
        pr_info_url: str | None = None,
        version_pr_info_url: str | None = None,
        pr_json_url: str | None = None,
        filepath: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._urls = {
            "node_attrs": url,
            "pr_info": pr_info_url,
            "version_pr_info": version_pr_info_url,
            "pr_json": pr_json_url,
        }
        # one composed APIDataset per repo: the seam fixtures replace (AD-11)
        self._inners: dict[str, Any] = {kind: APIDataset(url=u) for kind, u in self._urls.items() if u}
        self._dir = Path(filepath) if filepath else None
        self.metadata = metadata

    @property
    def last_good_path(self) -> Path | None:
        return self._dir / self.LAST_GOOD_FILENAME if self._dir is not None else None

    def staleness(self) -> StalenessMarker | None:
        """The current AD-13 marker, if the last load served last-good or nothing."""
        if self._dir is None:
            return None
        try:
            raw = json.loads((self._dir / self.STALENESS_FILENAME).read_text(encoding="utf-8"))
        except OSError, ValueError:
            return None
        if not isinstance(raw, dict):
            return None
        return StalenessMarker(
            stale=bool(raw.get("stale", True)),
            reason=str(raw.get("reason", "")),
            marked_at=_safe_int(raw.get("marked_at", 0)),
            last_good_exists=bool(raw.get("last_good_exists", False)),
        )

    def _fetch(self) -> pd.DataFrame:
        blobs = {kind: _as_bytes(inner.load()) for kind, inner in self._inners.items()}
        if set(blobs) == {"node_attrs"}:  # one URL: the pre-split combined tarball (fixtures, mirrors)
            return parse_cf_graph_tarball(blobs["node_attrs"])
        records = {
            kind: _tar_records(blobs[kind]) for kind in ("pr_info", "version_pr_info", "pr_json") if kind in blobs
        }
        # a configured bot repo with no records is the same redirect failure node_attrs had: an
        # all-zero health frame must not replace last-good
        empty = [kind for kind, recs in records.items() if not recs]
        if empty:
            raise _SourceEmpty(f"{', '.join(empty)} yielded no records")
        return _cf_graph_frame(
            _node_attrs_stream(blobs["node_attrs"]),
            records.get("pr_info", {}),
            records.get("version_pr_info", {}),
            records.get("pr_json"),
        )

    def load(self) -> pd.DataFrame:
        if self._dir is None:
            return self._fetch()
        last_good = self._dir / self.LAST_GOOD_FILENAME
        try:
            frame = self._fetch()
        except _SourceEmpty as exc:
            reason = str(exc)
        except _FETCH_OR_PARSE_ERRORS as exc:  # kedro wraps every fetch failure as DatasetError (AD-13)
            reason = f"fetch or parse failed: {_describe_exc(exc)}"
        else:
            # node_attrs is the graph itself; bot records alone (pr_info, version_pr_info) are
            # not a usable graph, so a frame with no node_attrs-derived row degrades too.
            if not frame.empty and frame["conda_name"].notna().any():

                def _write_frame(path: Path) -> None:
                    frame.to_parquet(path, index=False)

                try:
                    atomic_write(last_good, _write_frame)
                    (self._dir / self.STALENESS_FILENAME).unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning("could not keep last-good for %s: %s", self._dir, exc)
                return frame
            reason = "parsed frame is empty (no node_attrs)"
        kept = _read_last_good(last_good)
        suffix = "keeping last-good" if kept is not None else "no last-good"
        marker = StalenessMarker(stale=True, reason=f"{reason} -- {suffix}", last_good_exists=kept is not None)

        def _write_marker(path: Path) -> None:
            path.write_text(json.dumps(marker.to_dict(), indent=2), encoding="utf-8")

        try:
            atomic_write(self._dir / self.STALENESS_FILENAME, _write_marker)
        except OSError as exc:
            logger.warning("could not write staleness marker for %s: %s", self._dir, exc)
        logger.warning("core_cf_graph_raw: %s", marker.reason)
        return kept if kept is not None else pd.DataFrame(columns=_CF_GRAPH_COLUMNS)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"urls": dict(self._urls), "filepath": str(self._dir) if self._dir else None}


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
) -> tuple[dict[str, Any] | None, bool]:
    """Return ``(repodata, connection_failed)`` — connection failures skip a dead mirror."""
    try:
        inner = APIDataset(
            url=url,
            load_args=load_args,
            credentials=credentials,
            metadata=metadata,
        )
        return _api_json(inner.load()), False
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.debug("cross-channel repodata connection failed for %s: %s", url, exc)
        return None, True
    except Exception as exc:
        logger.debug("cross-channel repodata fetch failed for %s: %s", url, exc)
        return None, False


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
            dead_mirrors: set[str] = set()
            for url in _resolve_anaconda_channel_urls(channel_name, subdir, filename):
                mirror_base = url.rsplit("/", 2)[0]
                if mirror_base in dead_mirrors:
                    continue
                repodata, connection_failed = _fetch_repodata_at_url(
                    url,
                    load_args=load_args,
                    credentials=credentials,
                    metadata=metadata,
                )
                if connection_failed:
                    dead_mirrors.add(mirror_base)
                    continue
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
    """Phase C: the conda-forge bot's verified PyPI <-> conda name mapping, for
    ``pypi_parselmouth_mapping_raw`` (legacy ``phase_c_parselmouth_join``, CFA:1744).

    Story 34.2 (CAP-64): reads ``mappings/pypi/name_mapping.yaml`` from
    ``conda-forge/conda-forge-bot-data`` -- the file legacy reads through
    ``conda_forge_metadata``'s ``get_pypi_name_mapping`` -- through a composed
    :class:`~.json_sources.JSONSourceDataset` (YAML decode, AD-13 last-good + marker).
    Until then (Story 21.2) it read the flat ``pypi_conda_map_store``, which only
    ``export_pypi_conda_map`` writes, from the mapping this dataset feeds: on a fresh
    data root it never filled. Rows keep legacy's projection: ``pypi_name`` lowercased,
    ``conda_name`` as given, ``match_source`` ``parselmouth``.
    """

    _COLUMNS = ("pypi_name", "conda_name", "match_source")
    _MATCH_SOURCE = "parselmouth"

    def __init__(self, *, url: str, filepath: str, metadata: dict[str, Any] | None = None) -> None:
        # No **kwargs sink: an unrecognized catalog key must raise loudly (a stale
        # catalog misconfiguration) rather than be silently discarded.
        self._url = url
        self._filepath = filepath
        self.metadata = metadata
        self.source = JSONSourceDataset(url=url, filepath=filepath, expect="list", decode="yaml")

    def load(self) -> pd.DataFrame:
        entries = self.source.load()  # never raises (AD-13): last-good or [] under a marker
        rows: dict[tuple[str, str], dict[str, str]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            pypi_name, conda_name = entry.get("pypi_name"), entry.get("conda_name")
            if not (isinstance(pypi_name, str) and pypi_name and isinstance(conda_name, str) and conda_name):
                continue
            key = (pypi_name.lower(), conda_name)
            rows[key] = {"pypi_name": key[0], "conda_name": conda_name, "match_source": self._MATCH_SOURCE}
        if not rows:
            return pd.DataFrame(columns=self._COLUMNS)
        return pd.DataFrame([rows[k] for k in sorted(rows)], columns=self._COLUMNS).reset_index(drop=True)

    def save(self, data: Any) -> None:
        raise NotImplementedError(f"{type(self).__name__} is read-only")

    def _describe(self) -> dict[str, Any]:
        return {"parameterization": type(self).__name__, "url": self._url, "filepath": self._filepath}
