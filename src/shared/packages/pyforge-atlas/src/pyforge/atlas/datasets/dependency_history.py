"""Per-repo dependency history dataset (Story 25.1, CAP-61 / FR-69).

Dataset-owned IO (AD-2): clones, ``git`` / ``git pkgs`` invocations and the estate
``pixi.toml`` / ``pixi.lock`` history walk all live here -- never in ``pipelines/`` nodes.
Nodes emit a small :class:`DependencyHistoryBuildRequest` trigger only.

Every repo is scanned in a clone kept in Atlas's own cache (a ``local_path`` source is
cloned too), so git-pkgs never runs against an operator's working copy and nothing is
written into a scanned repo. Every git call against a clone is bounded to it
(``GIT_CEILING_DIRECTORIES``), and a clone is used only when its top level is the clone
directory itself and its ``origin`` is the declared source -- the cache defaults to
``data/`` inside the operator's checkout, so a partial clone must never hand a call to it. git-pkgs runs as ``git pkgs init --no-hooks`` with
``GIT_PKGS_DB`` in a throwaway directory outside the repo, and its change rows are read
from its own JSON output (``git pkgs history --format json``) -- no ``sqlite3`` import and
no DuckDB extension, so nothing is ever ``INSTALL``-ed (AD-13). The throwaway directory,
and every SQLite side file with it, is deleted before the next repo.

Store layout (one directory, partitioned by repo)::

    <filepath>/<owner>@<repo>.parquet   one partition per repo (its last-good rows)
    <filepath>/.repo_state.json         per repo: walked head SHA, degradation, reason (AD-5)
    <filepath>/.staleness.json          AD-13 marker, present while any repo is degraded

A repo whose head has not moved since its last complete walk is not re-walked (AD-5). A
repo that cannot be reached keeps its last-good partition and reads ``stale`` (AD-13); a
repo whose git-pkgs half cannot run (git-pkgs absent, outside its tested range, or
failing), or whose build fails in any other way, reads ``unresolved`` and is re-walked on
the next run -- one repo's failure never fails the others. A repo dropped from a non-empty
repo list is pruned: its state, its partition and Atlas's clone of it. No verdict, score
or threshold is computed here ("Atlas measures; Warden judges").
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import tomllib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from kedro.io import AbstractDataset
from pyforge.core.atomic_write import atomic_write, atomic_write_text
from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult

from .refresh import StalenessMarker

logger = logging.getLogger(__name__)

FLAG_KEY = "pyforge.atlas.dependency_history"

SOURCE_GIT_PKGS = "git-pkgs"
SOURCE_ESTATE_PIXI = "estate-pixi-parser"

# Degradation vocabulary (AD-13): never interchanged.
STALE = "stale"
UNRESOLVED = "unresolved"
NOT_APPLICABLE = "not-applicable"

#: git-pkgs's tested version range, ``>=0.21.0,<0.22`` (mason Story 21.1 built 0.21.0).
#: Mirrored by the root ``pixi.toml`` ``[feature.pyforge-atlas.target.linux-64.dependencies]`` pin.
GIT_PKGS_MIN_VERSION: tuple[int, int, int] = (0, 21, 0)
GIT_PKGS_MAX_VERSION: tuple[int, int, int] = (0, 22, 0)  # exclusive

HISTORY_COLUMNS: tuple[str, ...] = (
    "repo_full_name",
    "commit_sha",
    "commit_time",
    "manifest_path",
    "manifest_scope",
    "ecosystem",
    "name",
    "requirement_before",
    "requirement_after",
    "change_kind",
    "source",
    "degradation",
)

_STATE_FILENAME = ".repo_state.json"
_STALENESS_FILENAME = ".staleness.json"
_PARTITION_SUFFIX = ".parquet"
_STATE_FIELDS = ("head", "degradation", "reason")
# Parquet schema-metadata key: the head a partition reflects, written atomically with its rows
# ("" for a partition that reflects no complete walk -- the git-pkgs half kept from an older head).
_PARTITION_HEAD_KEY = b"pyforge.atlas.dependency_history.head"

_GIT_TIMEOUT_S = 120.0
_CLONE_TIMEOUT_S = 900.0
_GIT_PKGS_TIMEOUT_S = 900.0

# <owner>/<repo>, ASCII word characters, dots and dashes only; "." and ".." segments are refused.
_FULL_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
# scp-like ssh form, ``git@host:owner/repo.git``; user, host and path never open with ``-``.
_SCP_URL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*@[A-Za-z0-9][A-Za-z0-9_.-]*:[A-Za-z0-9_.~/][A-Za-z0-9_.~/-]*$")
_ALLOWED_URL_PREFIXES = ("https://", "ssh://", "file://")
# Repository-locating variables an operator shell may export; inherited, they would point
# every git call at another repository than Atlas's clone.
_GIT_REPO_ENV = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)

_PIXI_MANIFEST = "pixi.toml"
_PIXI_LOCK = "pixi.lock"
_CONDA_TABLES = ("dependencies", "host-dependencies", "build-dependencies", "run-dependencies")
_PYPI_TABLE = "pypi-dependencies"
_YAML_LOADER: Any = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
_CONDA_SUFFIXES = (".conda", ".tar.bz2")

# (manifest_scope, ecosystem, name) -> requirement text
_DepKey = tuple[str, str, str]


class GitProcessPort(Protocol):
    """The slice of ``pyforge.core.process`` this dataset uses: ``PosixProcess.run`` with ``env=``.

    ``ProcessPort`` carries no environment parameter; ``GIT_PKGS_DB`` and
    ``GIT_TERMINAL_PROMPT`` must reach the child, so the dataset takes ``PosixProcess``'s
    own signature (the sanctioned way to hand a child a curated environment).
    """

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_s: float | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult: ...


@dataclass(frozen=True)
class RepoSource:
    """One repo to scan: a local path or a clone URL (params-declared)."""

    full_name: str
    local_path: str | None = None
    clone_url: str | None = None


@dataclass(frozen=True)
class DependencyHistoryBuildRequest:
    """Pure node output -> dataset ``save`` input (a trigger, not a row payload)."""

    repos: tuple[RepoSource, ...] = ()
    force: bool = False
    not_applicable: bool = False
    #: entries of the configured list that could not be read as a repo source; while any exist
    #: the configured set is not known, so nothing is pruned.
    malformed_entries: int = 0

    @classmethod
    def skip(cls) -> DependencyHistoryBuildRequest:
        return cls(not_applicable=True)


@dataclass(frozen=True)
class _RepoOutcome:
    degradation: str = ""
    reason: str = ""
    rows: list[dict[str, Any]] | None = None  # None: keep the last-good partition untouched
    head: str | None = None  # None: keep the head of the last complete walk


class _InvalidSource(PyforgeError, Exception):
    """The source cannot be scanned as declared (``unresolved``)."""


class _Unreachable(PyforgeError, Exception):
    """The repo could not be cloned or fetched (``stale``)."""


class _WalkError(PyforgeError, Exception):
    """A history walk of a reachable clone failed (``unresolved``)."""


def _empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=list(HISTORY_COLUMNS))


def _parse_repo_sources(raw: Any) -> tuple[tuple[RepoSource, ...], int]:
    """The repo sources a configured list declares, and how many of its entries were malformed."""
    if not raw:
        return (), 0
    if not isinstance(raw, list):
        logger.warning("dependency_history.repos is a %s, not a list; no repo is read from it", type(raw).__name__)
        return (), 1
    out: list[RepoSource] = []
    seen: set[str] = set()
    malformed = 0
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            logger.warning("dependency_history.repos[%d] is a %s, not a mapping; skipped", index, type(item).__name__)
            malformed += 1
            continue
        full_name = str(item.get("full_name") or "").strip()
        if not full_name:
            logger.warning("dependency_history.repos[%d] has no full_name; skipped", index)
            malformed += 1
            continue
        if full_name in seen:
            logger.warning(
                "dependency_history.repos[%d] repeats full_name %r; the first entry is kept", index, full_name
            )
            malformed += 1
            continue
        seen.add(full_name)
        local_path = item.get("path") or item.get("local_path")
        clone_url = item.get("clone_url")
        out.append(
            RepoSource(
                full_name=full_name,
                local_path=str(local_path) if local_path else None,
                clone_url=str(clone_url) if clone_url else None,
            )
        )
    return tuple(out), malformed


def _fs_name(full_name: str) -> str:
    """``owner/repo`` -> ``owner@repo``; ``@`` is outside the name alphabet, so no two names collide."""
    return full_name.replace("/", "@")


def _clone_url_allowed(url: str) -> bool:
    if any(ch.isspace() or ord(ch) < 32 for ch in url):
        return False
    if url.startswith(_ALLOWED_URL_PREFIXES):
        return True
    return bool(_SCP_URL_RE.match(url))


def _valid_full_name(name: str) -> bool:
    return bool(_FULL_NAME_RE.match(name)) and not any(part in {".", ".."} for part in name.split("/"))


def _source_problem(source: RepoSource) -> str:
    """Why ``source`` cannot be scanned as declared, or ``""`` when it can."""
    name = source.full_name
    if not _valid_full_name(name):
        return f"invalid repo full name {name!r} (expected <owner>/<repo>)"
    if source.clone_url:
        if not _clone_url_allowed(source.clone_url):
            return f"clone URL scheme not allowed (https://, ssh://, file:// or user@host:path): {source.clone_url!r}"
        return ""
    if not source.local_path:
        return "neither a local path nor a clone URL is declared"
    return ""


def _git_env(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in _GIT_REPO_ENV}
    env["GIT_TERMINAL_PROMPT"] = "0"
    if extra:
        env.update(extra)
    return env


def _bounded_env(start: Path, extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """``_git_env`` with repository discovery bounded to ``start`` itself.

    ``GIT_CEILING_DIRECTORIES`` names ``start``'s parent, so a git call run from ``start`` (a
    clone at ``<cache>/<owner>@<repo>``, or the cache) looks for a repository there and never
    climbs into an enclosing one -- the cache defaults to ``data/`` inside the operator's own
    checkout, and a partial ``.git`` would otherwise hand every call to that checkout.
    """
    # git ignores a relative ceiling entry, and the cache path may be relative (``data/...``).
    return _git_env({"GIT_CEILING_DIRECTORIES": str(start.resolve().parent), **(extra or {})})


def _tail(text: str, limit: int = 200) -> str:
    text = (text or "").strip()
    return text[-limit:]


def _epoch_from_iso(value: Any) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    try:
        return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return 0


def _row(
    *,
    repo_full_name: str,
    commit_sha: str,
    commit_time: int,
    manifest_path: str,
    manifest_scope: str,
    ecosystem: str,
    name: str,
    requirement_before: str,
    requirement_after: str,
    change_kind: str,
    source: str,
) -> dict[str, Any]:
    return {
        "repo_full_name": repo_full_name,
        "commit_sha": commit_sha,
        "commit_time": int(commit_time),
        "manifest_path": manifest_path,
        "manifest_scope": manifest_scope,
        "ecosystem": ecosystem,
        "name": name,
        "requirement_before": requirement_before,
        "requirement_after": requirement_after,
        "change_kind": change_kind,
        "source": source,
        "degradation": "",
    }


# --- git-pkgs ------------------------------------------------------------------------------


def _parse_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    if match is None:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def _git_pkgs_problem(process: GitProcessPort, cwd: Path) -> str:
    """``""`` when ``git pkgs`` resolves inside its tested range, else why it cannot be used."""
    try:
        res = process.run(["git", "pkgs", "--version"], cwd=cwd, timeout_s=_GIT_TIMEOUT_S, env=_bounded_env(cwd))
    except ProcessError as exc:
        return f"git-pkgs could not be launched: {exc}"
    if res.returncode != 0:
        return f"git-pkgs is not installed (`git pkgs --version` exited {res.returncode})"
    version = _parse_version(res.stdout)
    if version is None:
        return f"git-pkgs version unreadable: {_tail(res.stdout)!r}"
    if not GIT_PKGS_MIN_VERSION <= version < GIT_PKGS_MAX_VERSION:
        found = ".".join(str(part) for part in version)
        return f"git-pkgs {found} is outside its tested range >=0.21.0,<0.22"
    return ""


def _git_pkgs_change_row(item: Mapping[str, Any], repo_full_name: str) -> dict[str, Any]:
    kind = str(item.get("change_type") or "")
    requirement = str(item.get("requirement") or "")
    previous = str(item.get("previous_requirement") or "")
    if kind == "removed":
        before, after = previous or requirement, ""
    else:
        before, after = previous, requirement
    return _row(
        repo_full_name=repo_full_name,
        commit_sha=str(item.get("sha") or ""),
        commit_time=_epoch_from_iso(item.get("committed_at")),
        manifest_path=str(item.get("manifest_path") or ""),
        manifest_scope="",
        ecosystem=str(item.get("ecosystem") or ""),
        name=str(item.get("name") or ""),
        requirement_before=before,
        requirement_after=after,
        change_kind=kind,
        source=SOURCE_GIT_PKGS,
    )


def _git_pkgs_rows(process: GitProcessPort, repo: Path, repo_full_name: str) -> list[dict[str, Any]]:
    """Index ``repo`` into a throwaway database and read its change rows from git-pkgs' JSON."""
    with tempfile.TemporaryDirectory(prefix="atlas-git-pkgs-") as scratch:
        env = _bounded_env(repo, {"GIT_PKGS_DB": str(Path(scratch) / "pkgs.sqlite3")})
        init = process.run(
            ["git", "-C", str(repo), "pkgs", "init", "--no-hooks", "--quiet"],
            cwd=repo,
            timeout_s=_GIT_PKGS_TIMEOUT_S,
            env=env,
        )
        if init.returncode != 0:
            raise _WalkError(f"git pkgs init exited {init.returncode}: {_tail(init.stderr)}")
        history = process.run(
            ["git", "-C", str(repo), "pkgs", "history", "--format", "json"],
            cwd=repo,
            timeout_s=_GIT_PKGS_TIMEOUT_S,
            env=env,
        )
        if history.returncode != 0:
            raise _WalkError(f"git pkgs history exited {history.returncode}: {_tail(history.stderr)}")
    try:
        payload = json.loads(history.stdout or "[]")
    except (ValueError, RecursionError) as exc:
        raise _WalkError(f"git pkgs history printed no JSON: {exc}") from exc
    if payload is None:
        payload = []
    if not isinstance(payload, list):
        raise _WalkError(f"git pkgs history printed {type(payload).__name__}, not a list")
    return [_git_pkgs_change_row(item, repo_full_name) for item in payload if isinstance(item, Mapping)]


# --- estate pixi parser --------------------------------------------------------------------


def _requirement_text(spec: Any) -> str:
    """One canonical string per spec: a string as written, a ``{version = ...}`` table as its version."""
    if isinstance(spec, str):
        return spec.strip()
    if isinstance(spec, Mapping):
        if set(spec) == {"version"}:
            return str(spec["version"]).strip()
        return json.dumps(dict(spec), sort_keys=True, separators=(", ", ": "), default=str)
    return json.dumps(spec, sort_keys=True, default=str)


def _targets(prefix: str, table: Mapping[str, Any]) -> Iterator[tuple[str, Mapping[str, Any]]]:
    targets = table.get("target")
    if isinstance(targets, Mapping):
        for platform, body in targets.items():
            if isinstance(body, Mapping):
                yield f"{prefix}target.{platform}.", body


def _dependency_scopes(data: Mapping[str, Any]) -> Iterator[tuple[str, Mapping[str, Any]]]:
    """Every table of a pixi manifest that can hold dependency tables, with its dotted prefix."""
    yield "", data
    yield from _targets("", data)
    features = data.get("feature")
    if isinstance(features, Mapping):
        for feature_name, feature in features.items():
            if isinstance(feature, Mapping):
                prefix = f"feature.{feature_name}."
                yield prefix, feature
                yield from _targets(prefix, feature)
    package = data.get("package")
    if isinstance(package, Mapping):
        yield "package.", package
        yield from _targets("package.", package)


def _parse_pixi_manifest(text: str) -> dict[_DepKey, str] | None:
    """Every declared dependency of a ``pixi.toml`` revision; ``None`` when it does not parse."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    deps: dict[_DepKey, str] = {}
    for prefix, table in _dependency_scopes(data):
        for table_name in (*_CONDA_TABLES, _PYPI_TABLE):
            entries = table.get(table_name)
            if not isinstance(entries, Mapping):
                continue
            ecosystem = "pypi" if table_name == _PYPI_TABLE else "conda"
            for name, spec in entries.items():
                deps[(f"{prefix}{table_name}", ecosystem, str(name))] = _requirement_text(spec)
    return deps


def _conda_name_version(locator: str) -> tuple[str, str] | None:
    filename = locator.rstrip("/").rsplit("/", 1)[-1]
    for suffix in _CONDA_SUFFIXES:
        if filename.endswith(suffix):
            parts = filename[: -len(suffix)].rsplit("-", 2)
            if len(parts) == 3 and parts[0] and parts[1]:
                return parts[0], parts[1]
    return None


def _version_sort_key(version: str) -> tuple[tuple[int, int | str], ...]:
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in re.split(r"(\d+)", version) if part)


def _parse_pixi_lock(text: str) -> dict[_DepKey, str] | None:
    """Every locked package of a ``pixi.lock`` revision as ``name -> versions``; ``None`` when unparsable.

    The lock's top-level ``packages`` list holds each locked artifact once across every
    environment and platform; the versions a name resolves to are joined, natural-sorted.
    """
    try:
        data = yaml.load(text, Loader=_YAML_LOADER)
    except yaml.YAMLError:
        return None
    if not isinstance(data, Mapping):
        return None
    packages = data.get("packages")
    if packages is None:
        packages = []
    if not isinstance(packages, list):
        return None
    versions: dict[tuple[str, str], set[str]] = {}
    for item in packages:
        if not isinstance(item, Mapping):
            continue
        kind = item.get("kind")
        if "conda" in item or kind == "conda":
            ecosystem, locator = "conda", item.get("conda") or item.get("url")
        elif "pypi" in item or kind == "pypi":
            ecosystem, locator = "pypi", item.get("pypi") or item.get("url")
        else:
            continue
        name, version = item.get("name"), item.get("version")
        if (not name or not version) and ecosystem == "conda" and isinstance(locator, str):
            parsed = _conda_name_version(locator)
            if parsed is not None:
                name, version = parsed
        if name and version:
            versions.setdefault((ecosystem, str(name)), set()).add(str(version))
    return {
        ("", ecosystem, name): ",".join(sorted(found, key=_version_sort_key))
        for (ecosystem, name), found in versions.items()
    }


def _diff_deps(before: Mapping[_DepKey, str], after: Mapping[_DepKey, str]) -> list[tuple[str, _DepKey, str, str]]:
    """``(change_kind, key, requirement_before, requirement_after)`` for every changed key."""
    changes: list[tuple[str, _DepKey, str, str]] = []
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        if old is None and new is not None:
            changes.append(("added", key, "", new))
        elif old is not None and new is None:
            changes.append(("removed", key, old, ""))
        elif old != new:
            changes.append(("modified", key, old or "", new or ""))
    return changes


def _file_revisions(process: GitProcessPort, repo: Path, path: str) -> list[tuple[str, int]]:
    """Mainline commits touching ``path``, oldest first, as ``(sha, epoch seconds)``."""
    res = process.run(
        ["git", "-C", str(repo), "log", "--first-parent", "--reverse", "--format=%H %ct", "--", path],
        cwd=repo,
        timeout_s=_GIT_TIMEOUT_S,
        env=_bounded_env(repo),
    )
    if res.returncode != 0:
        raise _WalkError(f"git log -- {path} exited {res.returncode}: {_tail(res.stderr)}")
    revisions: list[tuple[str, int]] = []
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            revisions.append((parts[0], int(parts[1])))
    return revisions


def _estate_pixi_rows(process: GitProcessPort, repo: Path, repo_full_name: str) -> list[dict[str, Any]]:
    """The Atlas-native ``pixi.toml`` / ``pixi.lock`` history (git-pkgs has no pixi parser)."""
    parsers: tuple[tuple[str, Callable[[str], dict[_DepKey, str] | None]], ...] = (
        (_PIXI_MANIFEST, _parse_pixi_manifest),
        (_PIXI_LOCK, _parse_pixi_lock),
    )
    rows: list[dict[str, Any]] = []
    for path, parser in parsers:
        previous: dict[_DepKey, str] = {}
        for sha, committed in _file_revisions(process, repo, path):
            shown = process.run(
                ["git", "-C", str(repo), "show", f"{sha}:{path}"],
                cwd=repo,
                timeout_s=_GIT_TIMEOUT_S,
                env=_bounded_env(repo),
            )
            # A non-zero `git show` is the file being absent at that commit (it was deleted).
            current = parser(shown.stdout) if shown.returncode == 0 else {}
            if current is None:
                logger.warning("%s: %s at %s does not parse; revision skipped", repo_full_name, path, sha)
                continue
            for kind, (scope, ecosystem, name), before, after in _diff_deps(previous, current):
                rows.append(
                    _row(
                        repo_full_name=repo_full_name,
                        commit_sha=sha,
                        commit_time=committed,
                        manifest_path=path,
                        manifest_scope=scope,
                        ecosystem=ecosystem,
                        name=name,
                        requirement_before=before,
                        requirement_after=after,
                        change_kind=kind,
                        source=SOURCE_ESTATE_PIXI,
                    )
                )
            previous = current
    return rows


def _git_in(process: GitProcessPort, repo: Path, *args: str, timeout_s: float = _GIT_TIMEOUT_S) -> ProcessResult:
    """``git -C <repo> <args>`` with discovery bounded to ``repo`` (never an enclosing repository)."""
    return process.run(["git", "-C", str(repo), *args], cwd=repo, timeout_s=timeout_s, env=_bounded_env(repo))


def _remote_has_branches(process: GitProcessPort, repo: Path) -> bool:
    res = _git_in(process, repo, "for-each-ref", "--count=1", "refs/remotes/origin/")
    if res.returncode != 0:
        raise _WalkError(f"git for-each-ref exited {res.returncode}: {_tail(res.stderr)}")
    return bool(res.stdout.strip())


def _repo_head(process: GitProcessPort, repo: Path) -> str:
    """The clone's ``HEAD`` commit, or ``""`` for a repository with no commits yet (an unborn ``HEAD``)."""
    res = _git_in(process, repo, "rev-parse", "--verify", "--quiet", "HEAD")
    head = res.stdout.strip() if res.returncode == 0 else ""
    if head:
        return head
    if res.returncode == 1 and not res.stderr.strip():
        return ""  # `--verify --quiet` exits 1, silently, exactly when HEAD names no commit yet
    raise _WalkError(f"git rev-parse HEAD exited {res.returncode}: {_tail(res.stderr)}")


class RepoDependencyHistoryDataset(AbstractDataset):
    """Primary-layer dependency history store, partitioned by repo (CAP-61)."""

    def __init__(
        self,
        *,
        filepath: str,
        cache_dir: str,
        process: GitProcessPort | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._root = Path(filepath)
        self._cache_dir = Path(cache_dir)
        self._process = process
        self.metadata = metadata

    # --- paths and metadata --------------------------------------------------------------

    @property
    def _state_path(self) -> Path:
        return self._root / _STATE_FILENAME

    @property
    def _staleness_path(self) -> Path:
        return self._root / _STALENESS_FILENAME

    def _partition_path(self, full_name: str) -> Path:
        return self._root / f"{_fs_name(full_name)}{_PARTITION_SUFFIX}"

    def _process_port(self) -> GitProcessPort:
        return self._process if self._process is not None else PosixProcess()

    def _read_state(self) -> dict[str, dict[str, str]]:
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            logger.warning("repo_dependency_history state unreadable (%s); every repo is re-walked", exc)
            return {}
        repos = payload.get("repos") if isinstance(payload, dict) else None
        if not isinstance(repos, dict):
            return {}
        return {
            str(name): {field: str(entry.get(field) or "") for field in _STATE_FIELDS}
            for name, entry in repos.items()
            if isinstance(entry, dict)
        }

    def _write_state(self, state: Mapping[str, Mapping[str, str]]) -> None:
        text = json.dumps({"repos": {name: dict(state[name]) for name in sorted(state)}}, indent=2, sort_keys=True)
        atomic_write_text(self._state_path, text + "\n")

    def _write_staleness(self, state: Mapping[str, Mapping[str, str]]) -> None:
        degraded = {name: entry for name, entry in sorted(state.items()) if entry.get("degradation")}
        if not degraded:
            self._staleness_path.unlink(missing_ok=True)
            return
        marker = StalenessMarker(
            stale=True,
            reason="; ".join(f"{name}: {entry['degradation']} ({entry['reason']})" for name, entry in degraded.items()),
            last_good_exists=any(self._root.glob(f"*{_PARTITION_SUFFIX}")),
        )
        payload = {**marker.to_dict(), "repos": {name: entry["degradation"] for name, entry in degraded.items()}}
        text = json.dumps(payload, indent=2, sort_keys=True)
        atomic_write_text(self._staleness_path, text + "\n")

    def _partition_head(self, full_name: str) -> str | None:
        """The head a partition reflects (``""`` when it reflects no complete walk); ``None`` when it does not read."""
        path = self._partition_path(full_name)
        if not path.is_file():
            return None
        try:
            table = pq.read_table(path)
        except Exception as exc:  # noqa: BLE001 -- any read failure means the partition must be rebuilt
            logger.warning("partition %s unreadable (%s); the repo is walked again", path, exc)
            return None
        return (table.schema.metadata or {}).get(_PARTITION_HEAD_KEY, b"").decode("utf-8", "replace")

    def _read_partition_rows(self, full_name: str) -> list[dict[str, Any]]:
        path = self._partition_path(full_name)
        if not path.is_file():
            return []
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001 -- a damaged partition degrades, never crashes the build
            logger.warning("partition %s unreadable: %s", path, exc)
            return []
        return [dict(row) for row in frame.to_dict(orient="records")]

    def _write_partition(self, full_name: str, rows: list[dict[str, Any]], head: str) -> None:
        frame = pd.DataFrame(rows, columns=list(HISTORY_COLUMNS)) if rows else _empty_history()
        if rows:
            frame["commit_time"] = frame["commit_time"].astype("int64")
            frame = frame.sort_values(
                ["commit_time", "manifest_path", "manifest_scope", "ecosystem", "name", "source"], kind="stable"
            ).reset_index(drop=True)
        frame["degradation"] = ""  # the repo-level marker lives in the state file, overlaid on load
        table = pa.Table.from_pandas(frame, preserve_index=False)
        table = table.replace_schema_metadata({**(table.schema.metadata or {}), _PARTITION_HEAD_KEY: head.encode()})
        atomic_write(self._partition_path(full_name), lambda target: pq.write_table(table, target))

    # --- one repo ------------------------------------------------------------------------

    def _clone_dir(self, full_name: str) -> Path:
        cache = self._cache_dir.resolve()
        slot = cache / _fs_name(full_name)
        if slot.is_symlink():
            raise _InvalidSource(f"clone slot for {full_name!r} is a symlink")
        dest = slot.resolve()
        if dest == cache or not dest.is_relative_to(cache):
            raise _InvalidSource(f"clone directory for {full_name!r} escapes the cache")
        return dest

    def _clone_is_usable(self, process: GitProcessPort, dest: Path) -> bool:
        """True only when ``dest`` is a repository of its own.

        Its ``.git`` is a real directory (never a symlink), and its top level, git directory and
        common directory all resolve to the clone itself -- not an enclosing checkout, and not
        another repository's object store reached through a ``commondir`` file or a symlinked
        ``objects`` / ``refs`` directory.
        """
        git_dir = dest / ".git"
        if git_dir.is_symlink() or not git_dir.is_dir():
            return False
        res = _git_in(
            process,
            dest,
            "rev-parse",
            "--path-format=absolute",
            "--show-toplevel",
            "--absolute-git-dir",
            "--git-common-dir",
            "--git-path",
            "objects",
            "--git-path",
            "refs",
        )
        lines = res.stdout.splitlines()
        if res.returncode != 0 or len(lines) != 5:
            return False
        top, own_dir, common_dir, objects, refs = (Path(line.strip()).resolve() for line in lines)
        return (
            top == dest
            and own_dir == git_dir
            and common_dir == git_dir
            and objects == git_dir / "objects"
            and refs == git_dir / "refs"
        )

    def _follow_target(self, process: GitProcessPort, dest: Path) -> str:
        """``@{upstream}``, or the remote's default branch when it has switched to another one.

        ``git remote set-head origin --auto`` re-reads the remote's ``HEAD``; when it now names a
        branch other than the clone's upstream (a default-branch switch that kept the old branch),
        the clone follows the new default.
        """
        if _git_in(process, dest, "remote", "set-head", "origin", "--auto", timeout_s=_CLONE_TIMEOUT_S).returncode:
            return "@{upstream}"
        default = _git_in(process, dest, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
        current = _git_in(process, dest, "rev-parse", "--symbolic-full-name", "@{upstream}")
        if default.returncode == 0 and current.returncode == 0 and default.stdout.strip() != current.stdout.strip():
            return "refs/remotes/origin/HEAD"
        return "@{upstream}"

    def _follow_upstream(self, process: GitProcessPort, dest: Path) -> bool:
        """Hard-reset a fetched clone to its upstream; False when a fresh clone is needed instead."""
        upstream = _git_in(process, dest, "rev-parse", "--verify", "--quiet", "@{upstream}")
        if upstream.returncode == 0:
            return (
                _git_in(process, dest, "reset", "--hard", "--quiet", self._follow_target(process, dest)).returncode == 0
            )
        if _repo_head(process, dest):
            return False  # its upstream branch is gone: clone afresh to follow the remote's default
        if not _remote_has_branches(process, dest):
            return True  # unborn HEAD beside an empty remote: current as it is
        # Unborn HEAD beside remote branches: the remote's HEAD names no branch. A fresh clone
        # would land in the same place, so keep this one until the remote names a branch again.
        named = _git_in(process, dest, "remote", "set-head", "origin", "--auto", timeout_s=_CLONE_TIMEOUT_S)
        return named.returncode != 0

    def _sync_clone(self, process: GitProcessPort, source: RepoSource) -> Path:
        """Bring Atlas's own clone of ``source`` up to its remote; raise ``_Unreachable`` when it cannot.

        Every git call against the clone is bounded to it (``_bounded_env``), and the clone is
        used only when its top level is the clone directory itself and its ``origin`` is the
        declared one. A usable clone is fetched -- a failed fetch is the remote being
        unreachable, so the clone is kept and the repo reads ``stale`` -- then hard-reset to its
        upstream, so a rewritten upstream history is followed, never refused. Anything else (a
        partial ``.git`` a killed run left behind, a changed ``clone_url`` / ``local_path``, an
        upstream that cannot be followed) is removed -- inside the cache only, ``_clone_dir``
        guarantees it -- and cloned afresh; a clone attempt that fails in any way, a timeout
        included, leaves no directory behind.
        """
        dest = self._clone_dir(source.full_name)
        if source.clone_url:
            origin = source.clone_url
        else:
            local = Path(str(source.local_path)).expanduser().resolve()
            if not local.is_dir():
                raise _Unreachable(f"local path {local} does not exist")
            origin = str(local)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if self._clone_is_usable(process, dest):
                current = _git_in(process, dest, "config", "--get", "remote.origin.url").stdout.strip()
                if current != origin:
                    logger.warning(
                        "%s: the declared origin is %r, the clone's is %r; cloning afresh",
                        source.full_name,
                        origin,
                        current,
                    )
                else:
                    fetched = _git_in(
                        process, dest, "fetch", "--quiet", "--prune", "origin", timeout_s=_CLONE_TIMEOUT_S
                    )
                    if fetched.returncode != 0:
                        raise _Unreachable(f"git fetch exited {fetched.returncode}: {_tail(fetched.stderr)}")
                    if self._follow_upstream(process, dest):
                        return dest
                    logger.warning("%s: clone cannot follow its upstream; cloning afresh", source.full_name)
            if dest.is_dir():
                shutil.rmtree(dest)
            elif dest.exists():
                dest.unlink()  # a stray file at the clone slot (rmtree would raise NotADirectoryError)
            try:
                cloned = process.run(
                    ["git", "clone", "--quiet", "--", origin, str(dest)],
                    cwd=dest.parent,
                    timeout_s=_CLONE_TIMEOUT_S,
                    env=_bounded_env(dest.parent),
                )
            except BaseException:
                shutil.rmtree(dest, ignore_errors=True)  # a killed or timed-out clone leaves nothing behind
                raise
            if cloned.returncode != 0:
                shutil.rmtree(dest, ignore_errors=True)
                raise _Unreachable(f"git clone exited {cloned.returncode}: {_tail(cloned.stderr)}")
        except (ProcessError, OSError) as exc:
            raise _Unreachable(f"git could not run: {exc}") from exc
        return dest

    def _forget(self, full_name: str) -> None:
        """Drop a repo no longer configured: its partition and Atlas's clone of it."""
        if not _valid_full_name(full_name):
            return  # an invalid name never had a partition or a clone
        self._partition_path(full_name).unlink(missing_ok=True)
        try:
            clone = self._clone_dir(full_name)
        except _InvalidSource:
            return
        shutil.rmtree(clone, ignore_errors=True)

    def _refresh_repo(
        self,
        process: GitProcessPort,
        source: RepoSource,
        prior_head: str,
        force: bool,
        git_pkgs_problem: Callable[[], str],
    ) -> _RepoOutcome:
        problem = _source_problem(source)
        if problem:
            return _RepoOutcome(UNRESOLVED, problem)
        try:
            clone = self._sync_clone(process, source)
            head = _repo_head(process, clone)
        except _InvalidSource as exc:
            return _RepoOutcome(UNRESOLVED, str(exc))
        except (_Unreachable, _WalkError, ProcessError) as exc:
            return _RepoOutcome(STALE, str(exc))
        if not head:
            if _remote_has_branches(process, clone):
                # The remote has commits but its HEAD names no branch: nothing to check out. Keep the
                # last-good partition and head; the clone is kept too (``_follow_upstream``).
                return _RepoOutcome(UNRESOLVED, "remote HEAD names no branch")
            if prior_head:
                # Built before, its remote now has no branch: keep the last-good history, never wipe it.
                return _RepoOutcome(UNRESOLVED, "the remote has no branches any more")
            # Reachable, with no branch at all yet: an explicit empty history (nothing to re-clone).
            return _RepoOutcome(reason="repository has no commits yet", rows=[], head="")
        if not force and self._partition_head(source.full_name) == head:
            # The partition reflects exactly this head (recorded with its rows): not re-walked (AD-5);
            # reachable again, so no marker. A missing, unreadable, partial or other-head partition
            # is walked again -- whatever the state file says.
            return _RepoOutcome(head=head)
        try:
            pixi_rows = _estate_pixi_rows(process, clone, source.full_name)
        except (_WalkError, ProcessError) as exc:
            return _RepoOutcome(UNRESOLVED, f"pixi history walk failed: {exc}")
        problem = git_pkgs_problem()
        pkgs_rows: list[dict[str, Any]] = []
        if not problem:
            try:
                pkgs_rows = _git_pkgs_rows(process, clone, source.full_name)
            except (_WalkError, ProcessError, OSError) as exc:
                problem = f"git-pkgs walk failed: {exc}"
        if problem:
            # The pixi half is fresh; the git-pkgs half keeps its last-good rows. The partition is
            # written as reflecting no head and the state head is not advanced, so the next run
            # walks this repo again whatever its head is then.
            kept = [row for row in self._read_partition_rows(source.full_name) if row.get("source") == SOURCE_GIT_PKGS]
            return _RepoOutcome(UNRESOLVED, problem, rows=kept + pixi_rows)
        return _RepoOutcome(rows=pkgs_rows + pixi_rows, head=head)

    # --- Kedro dataset API ---------------------------------------------------------------

    def load(self) -> pd.DataFrame:
        if not self._root.is_dir():
            return _empty_history()
        frames: list[pd.DataFrame] = []
        for partition in sorted(self._root.glob(f"*{_PARTITION_SUFFIX}")):
            try:
                frame = pd.read_parquet(partition)
            except Exception as exc:  # noqa: BLE001 -- a damaged partition degrades, never crashes the read
                logger.warning("partition %s unreadable: %s", partition, exc)
                continue
            if not frame.empty:
                frames.append(frame)
        if not frames:
            return _empty_history()
        history = pd.concat(frames, ignore_index=True)
        for column in HISTORY_COLUMNS:
            if column not in history.columns:
                history[column] = ""
        degradation = {name: entry["degradation"] for name, entry in self._read_state().items()}
        history["degradation"] = [degradation.get(str(name), "") for name in history["repo_full_name"]]
        return history[list(HISTORY_COLUMNS)].reset_index(drop=True)

    def save(self, data: Any) -> None:
        if not isinstance(data, DependencyHistoryBuildRequest):
            raise NotImplementedError(f"{type(self).__name__} only accepts DependencyHistoryBuildRequest triggers.")
        if data.not_applicable:
            logger.info("repo_dependency_history: flag %s is off; %s, nothing cloned", FLAG_KEY, NOT_APPLICABLE)
            return
        process = self._process_port()
        state = self._read_state()
        checked: list[str] = []

        def git_pkgs_problem() -> str:
            if not checked:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
                checked.append(_git_pkgs_problem(process, self._cache_dir.resolve()))
            return checked[0]

        for source in data.repos:
            prior = state.get(source.full_name, {})
            try:
                outcome = self._refresh_repo(process, source, prior.get("head", ""), data.force, git_pkgs_problem)
                if outcome.rows is not None:
                    complete = outcome.head if outcome.head and not outcome.degradation else ""
                    self._write_partition(source.full_name, outcome.rows, complete)
            except Exception as exc:  # noqa: BLE001 -- one repo's failure never fails the others (AD-13)
                logger.exception("%s: dependency history build failed", source.full_name)
                outcome = _RepoOutcome(UNRESOLVED, f"build failed: {type(exc).__name__}: {exc}")
            if outcome.degradation:
                logger.warning("%s: %s -- %s", source.full_name, outcome.degradation, outcome.reason)
            state[source.full_name] = {
                "head": outcome.head if outcome.head is not None else prior.get("head", ""),
                "degradation": outcome.degradation,
                "reason": outcome.reason,
            }
        configured = {source.full_name for source in data.repos}
        if data.malformed_entries:
            # The configured set is not known while an entry cannot be read: prune nothing, so a
            # mistyped entry never deletes a repo's state, last-good partition or clone.
            logger.warning(
                "repo_dependency_history: %d malformed repo entr%s; nothing pruned",
                data.malformed_entries,
                "y" if data.malformed_entries == 1 else "ies",
            )
        elif configured:  # an empty list scans nothing and prunes nothing (the shipped offline default)
            for name in sorted(set(state) - configured):
                self._forget(name)
                del state[name]
        self._root.mkdir(parents=True, exist_ok=True)
        self._write_state(state)
        self._write_staleness(state)

    def _describe(self) -> dict[str, Any]:
        return {
            "filepath": str(self._root),
            "cache_dir": str(self._cache_dir),
            "type": "RepoDependencyHistoryDataset",
        }


def build_dependency_history_request(
    *,
    flag_on: bool,
    repo_sources: Any,
    force: bool = False,
) -> DependencyHistoryBuildRequest:
    if not flag_on:
        return DependencyHistoryBuildRequest.skip()
    repos, malformed = _parse_repo_sources(repo_sources)
    return DependencyHistoryBuildRequest(repos=repos, force=force, malformed_entries=malformed)
