#!/usr/bin/env python3
"""
The conda-forge bot's graph, as the atlas phases read it.

Until 2026-10 the bot's graph lived in one repo, ``regro/cf-graph-countyfair``,
whose archive held ``node_attrs/``, ``pr_info/``, ``version_pr_info/`` and
``pr_json/``. GitHub now 301-redirects that repo to
``conda-forge/conda-forge-bot-data``, whose archive holds none of them
(``status/``, ``import_to_pkg_maps/``, ``mappings/`` ...). The download still
succeeds, so a reader that only looks for ``/node_attrs/`` finds nothing and
says nothing: Phase J wiped the ``dependencies`` table and wrote 0 edges.

cf-scripts now publishes the graph as four repos, one record per file under a
five-level sha1 shard::

    conda-forge/conda-forge-bot-data-node_attrs        <repo>-main/a/b/c/d/e/<feedstock>.json
    conda-forge/conda-forge-bot-data-pr_info           <repo>-main/a/b/c/d/e/<feedstock>.json
    conda-forge/conda-forge-bot-data-version_pr_info   <repo>-main/a/b/c/d/e/<feedstock>.json
    conda-forge/conda-forge-bot-data-pr_json           <repo>-main/a/b/c/d/e/<pr id>.json

Phase E fetches all four into ``cf-graph-<kind>.tar.gz``; Phases H (cf-graph
mode), J and M read them. A record's key is its path below the archive's top
directory with the shard and ``.json`` removed: most keys are a bare feedstock
name, and a few nest (``conda-forge/label/<name>``), which keying by basename
would merge with a different node.

The pre-split combined layout (``<top>/node_attrs/<shards>/<f>.json`` in one
``cf-graph-countyfair.tar.gz``) is still read when no split cache exists, so a
cache written before the split and the test fixtures keep working.

Private module (underscore-prefixed) — not exposed as a CLI.
"""
from __future__ import annotations

import gzip
import json
import os
import tarfile
import time
import zlib
from pathlib import Path
from typing import Any, Callable, Iterator

KINDS: tuple[str, ...] = ("node_attrs", "pr_info", "version_pr_info", "pr_json")
SPLIT_ORG = "conda-forge"
SPLIT_REPO_PREFIX = "conda-forge-bot-data-"
SPLIT_BRANCH = "main"
LEGACY_CACHE_NAME = "cf-graph-countyfair.tar.gz"
_SHARD_DEPTH = 5


def split_repo_name(kind: str) -> str:
    """``conda-forge-bot-data-<kind>``: the repo name, also the archive's top-dir stem."""
    if kind not in KINDS:
        raise ValueError(f"unknown cf-graph kind {kind!r}; expected one of {KINDS}")
    return f"{SPLIT_REPO_PREFIX}{kind}"


def split_repo(kind: str) -> str:
    """``conda-forge/conda-forge-bot-data-<kind>``, the GitHub repo for one kind."""
    return f"{SPLIT_ORG}/{split_repo_name(kind)}"


def split_archive_path() -> str:
    """The archive path below the repo, for ``resolve_github_urls``."""
    return f"/archive/refs/heads/{SPLIT_BRANCH}.tar.gz"


def split_cache_path(data_dir: Path, kind: str) -> Path:
    split_repo_name(kind)  # validates kind
    return Path(data_dir) / f"cf-graph-{kind}.tar.gz"


def legacy_cache_path(data_dir: Path) -> Path:
    return Path(data_dir) / LEGACY_CACHE_NAME


def _nonempty_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def source_path(data_dir: Path, kind: str) -> Path | None:
    """The cache a reader of ``kind`` uses: the split cache, else the legacy one."""
    split = split_cache_path(data_dir, kind)
    if _nonempty_file(split):
        return split
    legacy = legacy_cache_path(data_dir)
    if _nonempty_file(legacy):
        return legacy
    return None


def _strip_shard(dirs: list[str]) -> list[str]:
    if len(dirs) >= _SHARD_DEPTH and all(len(d) == 1 for d in dirs[-_SHARD_DEPTH:]):
        return dirs[:-_SHARD_DEPTH]
    return dirs


def record_key(member_name: str, kind: str) -> str | None:
    """The graph key of one archive member, or None when it is not a ``kind`` record.

    Split layout: the top directory is ``conda-forge-bot-data-<kind>-<ref>``
    and the five one-character shard directories come right before the file.
    Legacy layout: the second path segment is ``<kind>`` and the shard depth
    varies (3 in old fixtures, 5 in the real graph), so every trailing
    one-character directory is dropped.
    """
    if not member_name.endswith(".json"):
        return None
    parts = member_name.split("/")
    if len(parts) < 2:
        return None
    top = parts[0]
    if len(parts) >= 3 and parts[1] == kind:
        dirs, name = parts[2:-1], parts[-1][:-5]
        while dirs and len(dirs[-1]) == 1:
            dirs.pop()
    elif top.startswith(f"{split_repo_name(kind)}-"):
        dirs, name = _strip_shard(parts[1:-1]), parts[-1][:-5]
    else:
        return None
    if not name:
        return None
    return "/".join([*dirs, name])


def iter_tar_records(
    path: Path,
    kind: str,
    *,
    wanted: set[str] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(key, payload)`` for every ``kind`` record in one tarball, either layout.

    ``wanted`` limits decoding to those keys (``pr_json`` holds a record per
    PR the bot ever opened; Phase M needs only the live ones). A member that
    is not valid JSON, or not a JSON object, is skipped.
    """
    with tarfile.open(path, "r:gz") as tf:
        for member in tf:
            if not member.isfile():
                continue
            key = record_key(member.name, kind)
            if key is None:
                continue
            if wanted is not None and key not in wanted:
                continue
            handle = tf.extractfile(member)
            if handle is None:
                continue
            try:
                payload = json.load(handle)
            except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                continue
            if isinstance(payload, dict):
                yield key, payload


def iter_records(
    data_dir: Path,
    kind: str,
    *,
    wanted: set[str] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(key, payload)`` for ``kind`` from whichever cache :func:`source_path` picks."""
    path = source_path(data_dir, kind)
    if path is None:
        return
    yield from iter_tar_records(path, kind, wanted=wanted)


def has_records(path: Path, kind: str) -> bool:
    """True when the tarball holds at least one ``kind`` record (stops at the first)."""
    try:
        for _ in iter_tar_records(path, kind):
            return True
    except (OSError, tarfile.TarError, EOFError):
        return False
    return False


def validate_split_archive(path: Path, kind: str) -> str | None:
    """None when ``path`` is a whole ``kind`` repo archive; else why it is not.

    Checked before a download replaces the cache:

    - the gzip stream reads to its end and its CRC holds, so a truncated or
      spliced download is rejected (``tarfile`` stops at the end-of-archive
      blocks and can miss a damaged tail);
    - every member sits under ``conda-forge-bot-data-<kind>-<branch>/``, so a
      redirect to another repo (the failure that emptied the ``dependencies``
      table) is rejected even when that repo's archive is full of JSON;
    - at least one member is a sharded ``kind`` record.
    """
    expected_top = f"{split_repo_name(kind)}-{SPLIT_BRANCH}"
    try:
        with gzip.open(path, "rb") as stream:
            while stream.read(1 << 20):
                pass
    except (OSError, EOFError, zlib.error) as exc:
        return f"archive is not a whole gzip stream: {exc}"
    records = 0
    try:
        with tarfile.open(path, "r:gz") as tf:
            for member in tf:
                top = member.name.split("/", 1)[0]
                if top != expected_top:
                    return f"archive top directory is {top!r}, expected {expected_top!r}"
                if member.isfile() and record_key(member.name, kind) is not None:
                    records += 1
    except (OSError, tarfile.TarError, EOFError, zlib.error) as exc:
        return f"archive does not open: {exc}"
    if records == 0:
        return f"archive holds no {kind} record"
    return None


def fetch(
    data_dir: Path,
    kind: str,
    *,
    ttl_days: float,
    urls: list[str],
    download: Callable[[list[str], Path], None],
    now: float | None = None,
) -> dict[str, Any]:
    """Refresh ``cf-graph-<kind>.tar.gz`` unless it is younger than ``ttl_days``.

    ``download(urls, target)`` writes the archive to ``target`` and must start
    every attempt from byte 0: the bot pushes to these repos every few
    minutes, so resuming a partial file can splice two commits. The download
    lands in a staging file, is validated by :func:`validate_split_archive`,
    and only then replaces the cache, so a failed or wrong download keeps the
    previous cache (and says so in the result) instead of replacing it.
    """
    cache = split_cache_path(data_dir, kind)
    now = time.time() if now is None else now
    result: dict[str, Any] = {"kind": kind, "path": str(cache)}
    if _nonempty_file(cache):
        age_days = (now - cache.stat().st_mtime) / 86400
        result["age_days"] = round(age_days, 2)
        if age_days < ttl_days:
            result["cached"] = True
            return result
    staging = cache.with_name(cache.name + ".new")
    # A `.part` is what a resuming downloader leaves; this module never resumes.
    leftovers = (staging, staging.with_name(staging.name + ".part"))
    for leftover in leftovers:
        leftover.unlink(missing_ok=True)
    try:
        download(urls, staging)
    except Exception as exc:  # noqa: BLE001 -- any download failure keeps the old cache
        for leftover in leftovers:
            leftover.unlink(missing_ok=True)
        result["error"] = f"download failed: {exc}"
        result["kept_previous"] = _nonempty_file(cache)
        return result
    problem = validate_split_archive(staging, kind)
    if problem is not None:
        staging.unlink(missing_ok=True)
        result["error"] = f"rejected download: {problem}"
        result["kept_previous"] = _nonempty_file(cache)
        return result
    os.replace(staging, cache)
    result["downloaded"] = True
    result["bytes"] = cache.stat().st_size
    return result


def lazy_pr_json_id(pr: Any) -> str | None:
    """The pr_json key a ``{"__lazy_json__": "pr_json/<id>.json"}`` reference points at."""
    if not isinstance(pr, dict):
        return None
    ref = pr.get("__lazy_json__")
    if not isinstance(ref, str) or not ref:
        return None
    name = ref.rsplit("/", 1)[-1]
    return name[:-5] if name.endswith(".json") else name
