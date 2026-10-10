"""Per-repo dependency history dataset (Story 25.1, CAP-61 / FR-69).

Dataset-owned IO (AD-2): clones, ``git`` / ``git pkgs`` invocations, DuckDB reads
of git-pkgs' transient SQLite DB, and the estate ``pixi.toml`` history walk all
live here — never in ``pipelines/`` nodes. Nodes emit a small
:class:`DependencyHistoryBuildRequest` trigger only.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from kedro.io import AbstractDataset
from kedro_datasets.pandas import ParquetDataset
from pyforge.core.atomic_write import atomic_write
from pyforge.core.process import PosixProcess, ProcessPort

from .refresh import StalenessMarker

logger = logging.getLogger(__name__)

FLAG_KEY = "pyforge.atlas.dependency_history"

SOURCE_GIT_PKGS = "git-pkgs"
SOURCE_ESTATE_PIXI = "estate-pixi-parser"

HISTORY_COLUMNS: tuple[str, ...] = (
    "repo_full_name",
    "commit_sha",
    "commit_time",
    "manifest_path",
    "ecosystem",
    "name",
    "requirement_before",
    "requirement_after",
    "change_kind",
    "source",
    "degradation",
)

_REPO_HEADS_SUFFIX = ".repo_heads.json"
_STALENESS_SUFFIX = ".staleness.json"

_GIT_PKGS_TIMEOUT_S = 900.0
_GIT_TIMEOUT_S = 120.0


@dataclass(frozen=True)
class RepoSource:
    """One repo to scan: a local path or a clone URL (catalog / params declared)."""

    full_name: str
    local_path: str | None = None
    clone_url: str | None = None


@dataclass(frozen=True)
class DependencyHistoryBuildRequest:
    """Pure node output → dataset ``save`` input (trigger, not row payload)."""

    repos: tuple[RepoSource, ...] = ()
    fleet_heads: Mapping[str, str] | None = None
    force: bool = False
    not_applicable: bool = False

    @classmethod
    def skip(cls) -> DependencyHistoryBuildRequest:
        return cls(not_applicable=True)


def _empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=list(HISTORY_COLUMNS))


def _parse_repo_sources(raw: Any) -> tuple[RepoSource, ...]:
    if not raw:
        return ()
    if not isinstance(raw, list):
        return ()
    out: list[RepoSource] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        full_name = str(item.get("full_name") or "").strip()
        if not full_name:
            continue
        local_path = item.get("path") or item.get("local_path")
        clone_url = item.get("clone_url")
        out.append(
            RepoSource(
                full_name=full_name,
                local_path=str(local_path) if local_path else None,
                clone_url=str(clone_url) if clone_url else None,
            )
        )
    return tuple(out)


def _fleet_heads(raw: Mapping[str, Any] | None) -> dict[str, str]:
    if not raw or not isinstance(raw, Mapping):
        return {}
    repos = raw.get("repos")
    if not isinstance(repos, list):
        return {}
    heads: dict[str, str] = {}
    for item in repos:
        if isinstance(item, Mapping):
            name = item.get("full_name")
            sha = item.get("head_sha")
            if name and sha:
                heads[str(name)] = str(sha)
    return heads


def _name_column(ecosystem: str, name: str, purl: str | None) -> str:
    eco = (ecosystem or "").lower()
    if eco == "pypi":
        return name
    if eco == "conda":
        return name
    if purl and purl.startswith("pkg:"):
        # Never persist a purl as the join key — strip to the native name segment.
        tail = purl.split("/")[-1]
        if "@" in tail:
            tail = tail.split("@", 1)[0]
        if tail:
            return tail
    return name


def _epoch_seconds_from_git_timestamp(ts: str) -> int:
    ts = (ts or "").strip()
    if not ts:
        return 0
    if ts.isdigit():
        return int(ts)
    try:
        # git log %ct — epoch seconds
        return int(float(ts.split()[0]))
    except ValueError:
        return 0


def _read_git_pkgs_changes(db_path: Path) -> pd.DataFrame:
    con = duckdb.connect()
    try:
        con.execute("INSTALL sqlite; LOAD sqlite;")
        query = """
        SELECT
            c.sha AS commit_sha,
            epoch(CAST(c.committed_at AS TIMESTAMP))::BIGINT AS commit_time,
            m.path AS manifest_path,
            dc.ecosystem AS ecosystem,
            dc.name AS name,
            dc.previous_requirement AS requirement_before,
            dc.requirement AS requirement_after,
            dc.change_type AS change_kind,
            dc.purl AS purl
        FROM sqlite_scan(?, 'dependency_changes') dc
        JOIN sqlite_scan(?, 'commits') c ON dc.commit_id = c.id
        JOIN sqlite_scan(?, 'manifests') m ON dc.manifest_id = m.id
        """
        return con.execute(query, [str(db_path), str(db_path), str(db_path)]).fetchdf()
    finally:
        con.close()


def _git_pkgs_rows(frame: pd.DataFrame, repo_full_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in frame.to_dict(orient="records"):
        eco = str(rec.get("ecosystem") or "")
        name = str(rec.get("name") or "")
        rows.append(
            {
                "repo_full_name": repo_full_name,
                "commit_sha": str(rec.get("commit_sha") or ""),
                "commit_time": int(rec.get("commit_time") or 0),
                "manifest_path": str(rec.get("manifest_path") or ""),
                "ecosystem": eco,
                "name": _name_column(eco, name, rec.get("purl")),
                "requirement_before": str(rec.get("requirement_before") or ""),
                "requirement_after": str(rec.get("requirement_after") or ""),
                "change_kind": str(rec.get("change_kind") or ""),
                "source": SOURCE_GIT_PKGS,
                "degradation": "",
            }
        )
    return rows


def _parse_pixi_toml_bytes(raw: bytes) -> dict[str, str]:
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        return {}
    deps: dict[str, str] = {}
    project = data.get("project") if isinstance(data.get("project"), Mapping) else {}
    if isinstance(project, Mapping):
        pd_deps = project.get("dependencies")
        if isinstance(pd_deps, list):
            for item in pd_deps:
                if isinstance(item, str):
                    spec = item.strip()
                    if spec:
                        name = re.split(r"[<>=! \[]", spec, maxsplit=1)[0].strip()
                        if name:
                            deps[name] = spec
    table_deps = data.get("dependencies")
    if isinstance(table_deps, Mapping):
        for name, spec in table_deps.items():
            deps[str(name)] = str(spec) if spec is not None else ""
    return deps


def _diff_pixi_deps(
    before: dict[str, str], after: dict[str, str]
) -> list[tuple[str, str, str, str]]:
    """Return (change_kind, name, req_before, req_after) tuples."""
    changes: list[tuple[str, str, str, str]] = []
    names = set(before) | set(after)
    for name in sorted(names):
        b = before.get(name)
        a = after.get(name)
        if b is None and a is not None:
            changes.append(("added", name, "", a))
        elif b is not None and a is None:
            changes.append(("removed", name, b, ""))
        elif b != a:
            changes.append(("modified", name, b or "", a or ""))
    return changes


def _estate_pixi_rows(
    process: ProcessPort,
    repo_path: Path,
    repo_full_name: str,
) -> list[dict[str, Any]]:
    log = process.run(
        ["git", "-C", str(repo_path), "log", "--format=%H %ct", "--", "pixi.toml", "pixi.lock"],
        cwd=repo_path,
        timeout_s=_GIT_TIMEOUT_S,
    )
    if log.returncode != 0:
        return []
    commits: list[tuple[str, int]] = []
    for line in log.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            commits.append((parts[0], _epoch_seconds_from_git_timestamp(parts[1])))
    commits.reverse()
    prev_deps: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    for sha, ts in commits:
        show = process.run(
            ["git", "-C", str(repo_path), "show", f"{sha}:pixi.toml"],
            cwd=repo_path,
            timeout_s=_GIT_TIMEOUT_S,
        )
        if show.returncode != 0 or not show.stdout:
            continue
        deps = _parse_pixi_toml_bytes(show.stdout.encode("utf-8"))
        for kind, name, req_before, req_after in _diff_pixi_deps(prev_deps, deps):
            rows.append(
                {
                    "repo_full_name": repo_full_name,
                    "commit_sha": sha,
                    "commit_time": ts,
                    "manifest_path": "pixi.toml",
                    "ecosystem": "conda",
                    "name": name,
                    "requirement_before": req_before,
                    "requirement_after": req_after,
                    "change_kind": kind,
                    "source": SOURCE_ESTATE_PIXI,
                    "degradation": "",
                }
            )
        prev_deps = deps
    return rows


def _repo_head(process: ProcessPort, repo_path: Path) -> str:
    res = process.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        cwd=repo_path,
        timeout_s=_GIT_TIMEOUT_S,
    )
    if res.returncode != 0:
        return ""
    return res.stdout.strip()


def _run_git_pkgs_init(process: ProcessPort, repo_path: Path, db_path: Path) -> bool:
    env = {**os.environ, "GIT_PKGS_DB": str(db_path)}
    res = process.run(
        ["git", "-C", str(repo_path), "pkgs", "init", "--no-hooks"],
        cwd=repo_path,
        timeout_s=_GIT_PKGS_TIMEOUT_S,
        env=env,
    )
    return res.returncode == 0


def _resolve_repo_path(
    process: ProcessPort,
    source: RepoSource,
    cache_dir: Path,
) -> tuple[Path | None, str]:
    """Return (path, degradation) — degradation non-empty on unreachable."""
    if source.local_path:
        path = Path(source.local_path).resolve()
        if path.is_dir() and (path / ".git").is_dir():
            return path, ""
        return None, "unresolved"
    if source.clone_url:
        safe = source.full_name.replace("/", "__")
        dest = cache_dir / safe
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_dir() and (dest / ".git").is_dir():
            pull = process.run(
                ["git", "-C", str(dest), "pull", "--ff-only"],
                cwd=dest,
                timeout_s=_GIT_TIMEOUT_S,
            )
            if pull.returncode != 0:
                return dest if (dest / ".git").is_dir() else None, "stale"
            return dest, ""
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        clone = process.run(
            ["git", "clone", "--quiet", source.clone_url, str(dest)],
            cwd=cache_dir,
            timeout_s=_GIT_PKGS_TIMEOUT_S,
        )
        if clone.returncode != 0:
            return None, "stale" if dest.is_dir() else "unresolved"
        return dest, ""
    return None, "unresolved"


class RepoDependencyHistoryDataset(AbstractDataset):
    """Primary-layer dependency history store (CAP-61)."""

    def __init__(
        self,
        *,
        filepath: str,
        cache_dir: str,
        process: ProcessPort | None = None,
        load_args: dict[str, Any] | None = None,
        save_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._filepath = str(filepath)
        self._cache_dir = Path(cache_dir)
        self._process = process
        self._inner = ParquetDataset(
            filepath=filepath,
            load_args=load_args,
            save_args=save_args,
            credentials=credentials,
            metadata=metadata,
        )

    @property
    def _heads_path(self) -> Path:
        p = Path(self._filepath)
        return p.with_name(p.name + _REPO_HEADS_SUFFIX)

    @property
    def _staleness_path(self) -> Path:
        p = Path(self._filepath)
        return p.with_name(p.name + _STALENESS_SUFFIX)

    def _process_port(self) -> ProcessPort:
        return self._process if self._process is not None else PosixProcess()

    def _read_heads(self) -> dict[str, str]:
        path = self._heads_path
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items() if v}

    def _write_heads(self, heads: Mapping[str, str]) -> None:
        payload = dict(sorted(heads.items()))

        def _write(target: Path) -> None:
            target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

        atomic_write(self._heads_path, _write)

    def _mark_stale(self, reason: str) -> None:
        marker = StalenessMarker(
            stale=True,
            reason=reason,
            last_good_exists=Path(self._filepath).is_file(),
        )

        def _write(target: Path) -> None:
            target.write_text(json.dumps(marker.to_dict(), indent=2), encoding="utf-8")

        try:
            atomic_write(self._staleness_path, _write)
        except OSError as exc:
            logger.warning("could not write staleness marker: %s", exc)

    def _clear_stale(self) -> None:
        try:
            self._staleness_path.unlink(missing_ok=True)
        except OSError:
            pass

    def load(self) -> pd.DataFrame:
        path = Path(self._filepath)
        if not path.is_file():
            return _empty_history()
        try:
            frame = self._inner.load()
        except Exception as exc:
            logger.warning("repo_dependency_history load failed: %s", exc)
            self._mark_stale(f"parquet unreadable: {type(exc).__name__}")
            return _empty_history()
        missing = [c for c in HISTORY_COLUMNS if c not in frame.columns]
        for col in missing:
            frame[col] = ""
        return frame[list(HISTORY_COLUMNS)]

    def _build_one_repo(
        self,
        process: ProcessPort,
        source: RepoSource,
        prior_heads: dict[str, str],
        force: bool,
    ) -> tuple[list[dict[str, Any]], str, str]:
        repo_path, reach = _resolve_repo_path(process, source, self._cache_dir)
        if repo_path is None:
            return [], prior_heads.get(source.full_name, ""), reach or "unresolved"
        head = _repo_head(process, repo_path)
        if not force and head and prior_heads.get(source.full_name) == head:
            return [], head, ""
        db_path = self._cache_dir / f".git-pkgs-{source.full_name.replace('/', '__')}.sqlite"
        try:
            if db_path.exists():
                db_path.unlink()
            if not _run_git_pkgs_init(process, repo_path, db_path):
                return [], head, "unresolved"
            if not db_path.is_file():
                return [], head, "unresolved"
            pkgs_frame = _read_git_pkgs_changes(db_path)
            rows = _git_pkgs_rows(pkgs_frame, source.full_name)
            rows.extend(_estate_pixi_rows(process, repo_path, source.full_name))
            return rows, head, reach
        finally:
            try:
                db_path.unlink(missing_ok=True)
            except OSError:
                pass

    def save(self, data: Any) -> None:
        if not isinstance(data, DependencyHistoryBuildRequest):
            raise NotImplementedError(
                f"{type(self).__name__} only accepts DependencyHistoryBuildRequest triggers."
            )
        if data.not_applicable:
            return
        process = self._process_port()
        existing = self.load()
        prior_heads = self._read_heads()
        fleet_heads = dict(data.fleet_heads or {})
        new_heads = dict(prior_heads)
        all_rows: list[dict[str, Any]] = []
        stale_reasons: list[str] = []

        for source in data.repos:
            built, head, degradation = self._build_one_repo(
                process, source, prior_heads, data.force
            )
            if degradation == "stale":
                stale_reasons.append(f"{source.full_name}: unreachable")
                if not existing.empty:
                    kept = existing[existing["repo_full_name"] == source.full_name]
                    if not kept.empty:
                        kept = kept.copy()
                        kept["degradation"] = "stale"
                        all_rows.extend(kept.to_dict(orient="records"))
                continue
            if degradation == "unresolved" and not built:
                stale_reasons.append(f"{source.full_name}: git-pkgs unavailable or clone failed")
                if not existing.empty:
                    kept = existing[existing["repo_full_name"] == source.full_name]
                    if not kept.empty:
                        kept = kept.copy()
                        kept["degradation"] = "unresolved"
                        all_rows.extend(kept.to_dict(orient="records"))
                continue
            if head:
                new_heads[source.full_name] = head
            if built:
                all_rows.extend(built)
            elif not existing.empty:
                kept = existing[existing["repo_full_name"] == source.full_name]
                all_rows.extend(kept.to_dict(orient="records"))

        untouched = set(existing["repo_full_name"].unique()) if not existing.empty else set()
        touched = {s.full_name for s in data.repos}
        for name in untouched - touched:
            part = existing[existing["repo_full_name"] == name]
            all_rows.extend(part.to_dict(orient="records"))

        out = pd.DataFrame(all_rows, columns=list(HISTORY_COLUMNS)) if all_rows else _empty_history()
        self._inner.save(out)
        self._write_heads(new_heads)
        if stale_reasons:
            self._mark_stale("; ".join(stale_reasons))
        else:
            self._clear_stale()

    def _describe(self) -> dict[str, Any]:
        return {
            "filepath": self._filepath,
            "cache_dir": str(self._cache_dir),
            "type": "RepoDependencyHistoryDataset",
        }


def build_dependency_history_request(
    *,
    flag_on: bool,
    repo_sources: Any,
    fleet_inventory: Mapping[str, Any] | None,
    force: bool = False,
) -> DependencyHistoryBuildRequest:
    if not flag_on:
        return DependencyHistoryBuildRequest.skip()
    repos = _parse_repo_sources(repo_sources)
    heads = _fleet_heads(fleet_inventory)
    return DependencyHistoryBuildRequest(repos=repos, fleet_heads=heads, force=force)
