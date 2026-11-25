"""VCS + registry raw-source datasets (Story 21.2 — cf_atlas.db seed removal).

Two catalog families own the Phase K/L live-fetch shape (mechanically repeated, not
10 bespoke designs — GET the wired base URL + a per-package identifier, extract one
version string, wrap in the AD-13 last-good + staleness pattern):

- :class:`VcsHostSeedDataset` — GitLab / Codeberg (``vcs_gitlab_api_raw`` /
  ``vcs_codeberg_api_raw``): latest tag per repository.
- :class:`RegistryUpstreamDataset` — the 8 cross-ecosystem registries
  (``vcs_registry_*_raw``): latest version per package.

Both subclass :class:`_ParquetRefreshStore` (the shared last-good Parquet +
staleness-marker persistence this module hoists out of the two near-identical
implementations, review finding) and compose ``kedro_datasets.api.APIDataset`` for
the physical HTTP fetch (dataset-owned IO, AD-2 — no ``requests``/``sqlite3`` import
here; ``tests/catalog/test_no_inline_io.py`` bans both across the package).

Neither class fetches on a bare Kedro ``load()`` — ``load()`` is a read-only
projection of the persisted store. The live fetch is driven by ``save()``, which
ONLY accepts a :class:`~pyforge.atlas.datasets.refresh.RefreshRequest` trigger
(mirrors ``ExternalRefreshDataset``'s cadence/force honoring) — the pipeline's
refresh-trigger nodes (``pipelines/vcs_health/pipeline.py``) are each entry's SINGLE
writer, mirroring ``refresh_vdb_store``/``refresh_osv_offline_store``. A batch where
every identifier's fetch fails (or the batch is empty — Story 21.2 does not yet wire a
production identifier source; see the module Design Note below) degrades to "no data"
for persistence purposes: last-good is preserved and staleness is marked, never
clobbered with an all-null result.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import pandas as pd
from kedro.io import AbstractDataset
from kedro_datasets.api import APIDataset

from . import credentials as credential_switch
from . import public_sources
from .rate_limit import (
    DEFAULT_FAILURE_BUDGET_SECONDS,
    DEFAULT_MAX_CONSECUTIVE_FAILURES,
    DEFAULT_RPS,
    DEFAULT_RUN_DEADLINE_SECONDS,
    FailureBudget,
    FetchError,
    HostUnavailable,
    RateLimitedScheduler,
)
from .refresh import (
    DEFAULT_REFRESH_MAX_RETRIES,
    DEFAULT_REFRESH_TIMEOUT_SECONDS,
    RefreshRequest,
    _ParquetRefreshStore,
    fetch_one_with_retry,
    retry_backoff_seconds,
)
from .request_datasets import _http_status, _retry_after, normalize_release_tag

logger = logging.getLogger(__name__)

_VERSION_SEGMENT_RE = re.compile(r"\d+|\D+")
USER_AGENT = "pyforge-atlas (+https://github.com/rxm7706/local-recipes)"


def _version_sort_key(version: str) -> tuple:
    """Natural / numeric-aware sort key: splits a version string into alternating
    digit/non-digit runs so a multi-digit numeric segment compares NUMERICALLY
    (e.g. ``"1.10-1"`` > ``"1.2-1"``) rather than lexicographically, where "1.10-1"
    would sort BELOW "1.2-1" as raw strings (review fix #1 — a plain ``sorted()`` on
    the version strings mis-ranks multi-digit components)."""
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in _VERSION_SEGMENT_RE.findall(version))


# Shared row shape for BOTH VcsHostSeedDataset and RegistryUpstreamDataset — the
# review finding added ``last_error`` to the registry side to match the host side.
_VERSION_COLUMNS: tuple[str, ...] = ("conda_name", "upstream_version", "last_error")
#: Story 51.1: when a row was last asked for (epoch seconds), whether or not the host answered: a
#: column of the store file only. ``load`` returns ``_VERSION_COLUMNS``, never this one; a refresh
#: orders its identifiers by it.
_ASKED_AT = "asked_at"
#: Story 51.1: what a host says about its own limit on a 429, in the order logged (GitLab's names).
_LIMIT_HEADERS: tuple[str, ...] = (
    "RateLimit-Name",
    "RateLimit-Limit",
    "RateLimit-Observed",
    "RateLimit-Remaining",
    "RateLimit-Reset",
    "Retry-After",
)
_LIMIT_VALUE_LENGTH = 48
_LIMIT_VALUE_RE = re.compile(r"[^A-Za-z0-9_.:-]")


def _coerce_json(raw: Any) -> Any:
    """Normalize an ``APIDataset.load()`` return value to parsed JSON (dict OR list —
    the GitLab/Codeberg tag endpoints return a JSON list, unlike the dict-shaped
    registry payloads)."""
    if hasattr(raw, "json") and callable(raw.json):
        try:
            return raw.json()
        except ValueError, TypeError:
            return None
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, (bytes, str)):
        try:
            return json.loads(raw)
        except json.JSONDecodeError, TypeError, UnicodeDecodeError:
            return None
    return None


# ---------------------------------------------------------------------------
# Per-host / per-registry request-path builders + response extractors.
# Percent-encode every interpolated identifier (urllib.parse.quote) — a package name
# or repo slug may legitimately contain '/', '@', or other path-special characters.
# ---------------------------------------------------------------------------


def _request_kwargs(timeout: int, credentials: Any) -> dict[str, Any]:
    """Story 35.1: with ``pyforge.atlas.live_vcs_universe`` on, a host or registry request sends no
    credential (legacy Phases K and L read these hosts unauthenticated; Story 35.4 decides which
    may authenticate, and only under the switch), and a no-op auth keeps ``~/.netrc`` out. Off,
    the request is the one this story found, except that (Story 35.5) the catalog credential
    rides only when the operator set ``PYFORGE_ATLAS_CREDENTIALED=1``; without the switch the
    request sends no credential and the same no-op auth (``credential_switch.catalog_request``,
    the one rule the GitHub batch in ``request_datasets`` reads too)."""
    if credential_switch.live_vcs_universe():
        # Story 35.4: an identifying User-Agent, as legacy Phase L sends; crates.io answers
        # requests' default agent with a 403.
        return {"load_args": {**public_sources.request_args(timeout), "headers": {"User-Agent": USER_AGENT}}}
    return credential_switch.catalog_request(timeout, credentials)


@dataclass(frozen=True)
class _EndpointSpec:
    build_path: Callable[[str, str], str]
    extract: Callable[[Any], str | None]


def _require_identifier(kind: str, identifier: str) -> str:
    ident = (identifier or "").strip("/")
    if not ident:
        raise ValueError(f"{kind} request path requires a non-empty identifier")
    return ident


def _first_list_item_field(payload: Any, field: str) -> str | None:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        value = payload[0].get(field)
        return str(value) if value else None
    return None


def _gitlab_path(base: str, identifier: str) -> str:
    ident = _require_identifier("gitlab", identifier)
    return f"{base.rstrip('/')}/projects/{quote(ident, safe='')}/repository/tags?order_by=updated&per_page=1"


def _codeberg_path(base: str, identifier: str) -> str:
    ident = _require_identifier("codeberg", identifier)
    # Exactly one '/' — an identifier like "owner/repo/sub" would otherwise silently
    # percent-encode the extra segment into the `repo` slot, building a malformed
    # request path (review fix #11).
    parts = ident.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"codeberg request path requires a clean 'owner/repo' identifier (exactly one '/'), got {identifier!r}"
        )
    owner, repo = parts
    return f"{base.rstrip('/')}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/tags?sort=updated&limit=1"


def _status_of(exc: BaseException) -> int | None:
    """The HTTP status a failed GET carries (a ``FetchError``'s or the response's), if any."""
    status = getattr(exc, "status", None)
    return status if isinstance(status, int) else _http_status(exc)


def _why(exc: BaseException) -> str:
    """Story 35.4: a row's error as legacy records it (``HTTP 404``), else the type of the failure
    underneath (kedro's ``DatasetError`` wraps a ``ConnectionError`` or a timeout) -- never its text,
    which can quote the request."""
    status = _status_of(exc)
    if status:
        return f"HTTP {status}"
    return type(_root_cause(exc)).__name__


def _limit_said(exc: BaseException) -> str | None:
    """Story 51.1: what a 429 says about the host's limit, as ``name=value`` pairs of
    :data:`_LIMIT_HEADERS` only, each value cut to plain characters and a fixed length (a header is the
    host's text: it reaches the log and the staleness marker, never as sent). ``None`` when the
    failure is not a 429 or carries none of them."""
    if _status_of(exc) != 429:  # noqa: PLR2004
        return None
    for arg in (exc, *getattr(exc, "args", ())):
        headers = getattr(getattr(arg, "response", None), "headers", None)
        if headers is None:
            continue
        said = []
        for name in _LIMIT_HEADERS:
            value = headers.get(name)
            if value is None:
                continue
            clean = _LIMIT_VALUE_RE.sub("", str(value))[:_LIMIT_VALUE_LENGTH]
            if clean:
                said.append(f"{name}={clean}")
        if said:
            return " ".join(said)
    return None


def _transient(exc: BaseException) -> bool:
    """A failure the host may not repeat: a 429, a 5xx, or no status with the network underneath
    (a dropped connection, a timeout: ``OSError``). A 404 is the host's answer, not a failure."""
    status = _status_of(exc)
    if status is None:
        return isinstance(_root_cause(exc), OSError)
    return status == 429 or status >= 500  # noqa: PLR2004


def _fetch_outcome(fetch: Callable[[], Any], spec: _EndpointSpec, budget: FailureBudget) -> _Outcome:
    """Story 50.1, the path that retries inside :func:`fetch_one_with_retry`: one identifier's
    version, or its error as before the story (``str(exc)``), with its failure charged to the run's
    budget when the cause is transient. A refusal resets the count; a stop passes through."""
    started = budget.now()
    try:
        payload = fetch()
    except Exception as exc:
        if not _transient(exc):
            budget.answered()
            return None, str(exc), False
        budget.heard(_limit_said(exc))
        budget.failed_attempt(started)
        budget.exhausted(_why(exc))
        return None, str(exc), True
    budget.answered()
    try:
        version = spec.extract(payload)
    except Exception as exc:  # noqa: BLE001 -- a body the extractor cannot read is that row's error, as before
        return None, str(exc), False
    return version, None if version else "no version found in response", False


def _root_cause(exc: BaseException) -> BaseException:
    """The innermost ``__cause__`` of ``exc``; a chain that loops back on itself stops where it repeats."""
    seen = {id(exc)}
    while exc.__cause__ is not None and id(exc.__cause__) not in seen:
        exc = exc.__cause__
        seen.add(id(exc))
    return exc


def _live_host_paths(host: str, base: str, identifier: str) -> tuple[str, str]:
    """Story 35.4: legacy Phase K's REST pair for a host (``_phase_k_fetch_one``, CFA:4922-5036):
    the latest release, then the tags. GitLab keeps the project path whole (subgroups)."""
    root = base.rstrip("/")
    if host == "gitlab":
        project = quote(_require_identifier("gitlab", identifier), safe="")
        return f"{root}/projects/{project}/releases?per_page=1", f"{root}/projects/{project}/repository/tags?per_page=1"
    _codeberg_path(base, identifier)  # validates the clean owner/repo
    owner, repo = (quote(part, safe="") for part in identifier.strip("/").split("/"))
    return f"{root}/repos/{owner}/{repo}/releases/latest", f"{root}/repos/{owner}/{repo}/tags?limit=10"


def _release_tag(payload: Any) -> str | None:
    """The tag of a release: GitLab lists releases (``tag_name``, else ``name``, as legacy reads them,
    CFA:4997), Codeberg (Gitea) returns the latest one (``tag_name``)."""
    if isinstance(payload, list):
        first = payload[0] if payload and isinstance(payload[0], dict) else {}
        tag = first.get("tag_name") or first.get("name")
    else:
        tag = payload.get("tag_name") if isinstance(payload, dict) else None
    return str(tag) if tag else None


_HOST_SPECS: dict[str, _EndpointSpec] = {
    "gitlab": _EndpointSpec(_gitlab_path, lambda p: _first_list_item_field(p, "name")),
    "codeberg": _EndpointSpec(_codeberg_path, lambda p: _first_list_item_field(p, "name")),
}


def _npm_path(base: str, name: str) -> str:
    ident = _require_identifier("npm", name)
    return f"{base.rstrip('/')}/{quote(ident, safe='@')}"


def _npm_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        tags = payload.get("dist-tags")
        if isinstance(tags, dict):
            v = tags.get("latest")
            return str(v) if v else None
    return None


def _cran_path(base: str, name: str) -> str:
    ident = _require_identifier("cran", name)
    return f"{base.rstrip('/')}/{quote(ident, safe='')}"


def _cran_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        v = payload.get("Version")
        return str(v) if v else None
    return None


def _cpan_path(base: str, name: str) -> str:
    ident = _require_identifier("cpan", name)
    return f"{base.rstrip('/')}/v1/release/{quote(ident, safe='')}"


def _cpan_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        v = payload.get("version")
        return str(v) if v else None
    return None


def _luarocks_path(base: str, name: str) -> str:
    ident = _require_identifier("luarocks", name)
    return f"{base.rstrip('/')}/m/{quote(ident, safe='')}.json"


def _luarocks_extract(payload: Any) -> str | None:
    """LuaRocks' per-module JSON is keyed by version string (``{"versions": {...}}``);
    dict iteration order is not the release order, so pick the genuinely latest version
    via a NUMERIC-AWARE comparator (never ``next(iter(versions))`` on unordered dict
    iteration, and never a raw lexicographic ``sorted()`` — review fix #1: a plain
    string sort mis-ranks multi-digit components, e.g. "1.10-1" sorting below
    "1.2-1").

    Story 52.1: the sort key ranks a non-digit run above a digit run, so ``scm-1`` /
    ``dev-1`` (rolling source rockspecs) beat every numeric release. A version that
    starts with a digit wins when one exists; the others are the fallback only."""
    if isinstance(payload, dict):
        versions = payload.get("versions")
        if isinstance(versions, dict) and versions:
            numeric = [v for v in versions if str(v)[:1].isdigit()]
            return str(max(numeric or versions.keys(), key=_version_sort_key))
    return None


def _crates_path(base: str, name: str) -> str:
    ident = _require_identifier("crates", name)
    return f"{base.rstrip('/')}/api/v1/crates/{quote(ident, safe='')}"


def _crates_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        crate = payload.get("crate")
        if isinstance(crate, dict):
            if credential_switch.live_vcs_universe():
                # Story 35.4: legacy _resolve_crates -- the newest stable version, else the newest
                v = crate.get("max_stable_version") or crate.get("max_version")
            else:
                v = crate.get("newest_version") or crate.get("max_stable_version")
            return str(v) if v else None
    return None


def _rubygems_path(base: str, name: str) -> str:
    ident = _require_identifier("rubygems", name)
    return f"{base.rstrip('/')}/api/v1/gems/{quote(ident, safe='')}.json"


def _rubygems_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        v = payload.get("version")
        return str(v) if v else None
    return None


def _maven_path(base: str, name: str) -> str:
    ident = _require_identifier("maven", name)
    if credential_switch.live_vcs_universe():
        # Story 35.4: legacy _resolve_maven -- a group:artifact coordinate asks for both
        group, _, artifact = ident.partition(":")
        query = f'g:"{group}" AND a:"{artifact}"' if artifact else f'a:"{ident}"'
        return f"{base.rstrip('/')}/solrsearch/select?q={quote(query, safe='')}&rows=1&wt=json"
    return f"{base.rstrip('/')}/solrsearch/select?q=a:{quote(ident, safe='')}&rows=1&wt=json"


def _maven_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        resp = payload.get("response")
        if isinstance(resp, dict):
            docs = resp.get("docs")
            if isinstance(docs, list) and docs and isinstance(docs[0], dict):
                v = docs[0].get("latestVersion")
                if not v and credential_switch.live_vcs_universe():
                    v = docs[0].get("v")  # Story 35.4: legacy's fallback (CFA:5697), with the flag on only
                return str(v) if v else None
    return None


def _nuget_path(base: str, name: str) -> str:
    ident = _require_identifier("nuget", name)
    return f"{base.rstrip('/')}/v3-flatcontainer/{quote(ident.lower(), safe='')}/index.json"


def _nuget_extract(payload: Any) -> str | None:
    if isinstance(payload, dict):
        versions = payload.get("versions")
        if isinstance(versions, list) and versions:
            if credential_switch.live_vcs_universe():
                # Story 35.4: legacy _resolve_nuget -- the last stable version (no "-" pre-release)
                stable = [v for v in versions if "-" not in str(v)]
                return str((stable or versions)[-1])
            return str(versions[-1])
    return None


_REGISTRY_SPECS: dict[str, _EndpointSpec] = {
    "npm": _EndpointSpec(_npm_path, _npm_extract),
    "cran": _EndpointSpec(_cran_path, _cran_extract),
    "cpan": _EndpointSpec(_cpan_path, _cpan_extract),
    "luarocks": _EndpointSpec(_luarocks_path, _luarocks_extract),
    "crates": _EndpointSpec(_crates_path, _crates_extract),
    "rubygems": _EndpointSpec(_rubygems_path, _rubygems_extract),
    "maven": _EndpointSpec(_maven_path, _maven_extract),
    "nuget": _EndpointSpec(_nuget_path, _nuget_extract),
}


#: A progress line at most this often, so a slow run says where it is (atlas Story 50.1).
_PROGRESS_SECONDS = 60.0
#: One identifier's outcome: its version, its error, and whether the error is a transient failure.
_Outcome = tuple[str | None, str | None, bool]


class _BudgetedRefresh:
    """One run's failure budget for a host or registry store (atlas Story 50.1): a fresh
    :class:`FailureBudget` per ``load_many``, the loop that stops when the host uses it up, and the
    lines a reader of the run's log needs -- how many were asked, how far it is, and why it stopped."""

    _failure_budget_seconds: float
    _max_consecutive_failures: int
    _run_deadline_seconds: float
    _clock: Callable[[], float]
    _COLUMNS: tuple[str, ...]
    #: The wall clock a row's asked time is read from (the budget's clock is monotonic); a test sets it.
    _now: Callable[[], float] = staticmethod(time.time)

    if TYPE_CHECKING:  # the store this mixes into (``_ParquetRefreshStore``)
        _store_path: Any

        def _store_exists(self) -> bool: ...
        def _persist(self, frame: pd.DataFrame) -> None: ...
        def _mark_stale(self, reason: str, *, only_if_absent: bool = False) -> Any: ...

    def _new_budget(self) -> FailureBudget:
        return FailureBudget(
            seconds=self._failure_budget_seconds,
            max_consecutive=self._max_consecutive_failures,
            deadline_seconds=self._run_deadline_seconds,
            clock=self._clock,
        )

    def _stored(self) -> pd.DataFrame | None:
        """Story 51.1: the store file as written (its asked time included), or ``None`` when there is
        none or it cannot be read -- the order is a preference, and the refresh goes on without it."""
        if not self._store_exists():
            return None
        try:
            stored = pd.read_parquet(self._store_path)
        except Exception as exc:  # noqa: BLE001 -- see the docstring
            logger.warning("store %s unreadable, asking in the order given: %s", self._store_path, exc)
            return None
        return stored if "conda_name" in stored.columns else None

    @staticmethod
    def _asked_times(stored: pd.DataFrame | None) -> dict[str, float]:
        """Story 51.1: when each ``conda_name`` was last asked; a row with no time (written before
        the story, or never asked) is absent."""
        if stored is None or _ASKED_AT not in stored.columns:
            return {}
        times = pd.to_numeric(stored[_ASKED_AT], errors="coerce")
        return {str(n): float(t) for n, t in zip(stored["conda_name"], times, strict=True) if pd.notna(t)}

    @staticmethod
    def _stalest_first(identifiers: Sequence[tuple[str, str]], stored: pd.DataFrame | None) -> list[tuple[str, str]]:
        """Story 51.1: the identifiers never asked, then the rest longest since asked first -- so the
        runs a host stops cover the whole list between them. Asked in the same second, a row that
        holds a version goes before one that holds none (the ones that fail go last), and the rest
        keep the order given."""
        times = _BudgetedRefresh._asked_times(stored)
        empty: set[str] = set()
        if stored is not None and "upstream_version" in stored.columns:
            empty = {str(n) for n in stored.loc[stored["upstream_version"].isna(), "conda_name"]}

        def key(pair: tuple[str, str]) -> tuple[bool, float, bool]:
            name = str(pair[0])
            return name in times, times.get(name, 0.0), name in empty

        return sorted(identifiers, key=key)

    def _touched(self, stored: pd.DataFrame | None, asked: dict[str, str | None]) -> list[dict[str, Any]]:
        """Story 51.1: rows that record that ``asked`` (name -> its error) were asked now and write
        over no value: a name the store holds keeps its row with the new time; a name it does not
        hold gets a row with no version and its error. Without them an identifier that fails every
        time stays first in every run and stops each one before it reaches the rest."""
        if not asked:
            return []
        now = int(self._now())
        held: dict[str, dict[str, Any]] = {}
        if stored is not None:
            for record in stored.to_dict("records"):
                held[str(record["conda_name"])] = record
        rows = []
        for conda_name, error in asked.items():
            old = held.get(str(conda_name))
            row = (
                {c: old.get(c) for c in self._COLUMNS}
                if old is not None
                else {"conda_name": conda_name, "upstream_version": None, "last_error": error}
            )
            rows.append({**row, _ASKED_AT: now})
        return rows

    def _run(
        self,
        name: str,
        identifiers: Sequence[tuple[str, str]],
        one: Callable[[str, FailureBudget], _Outcome],
    ) -> pd.DataFrame:
        """Ask ``one`` for every ``(conda_name, identifier)``, stalest first, until the list ends or
        the host stops the run, then persist and report. Returns the rows of the identifiers that
        finished."""
        budget = self._new_budget()
        total = len(identifiers)
        finished: list[tuple[dict[str, Any], bool]] = []
        stopped: HostUnavailable | None = None
        stopped_on: str | None = None  # the identifier being asked when the host stopped the run
        logger.info("%s: asking for %d identifier(s)", name, total)
        said = budget.now()
        told = False
        stored = self._stored()
        for conda_name, identifier in self._stalest_first(identifiers, stored):
            asking = False
            try:
                budget.check_deadline()
                asking = True
                version, error, transient = one(identifier, budget)
            except HostUnavailable as exc:
                stopped = exc
                stopped_on = conda_name if asking else None
                break
            finally:
                if budget.host_said and not told:
                    told = True  # Story 51.1: once a run, what the host said about its limit
                    logger.info("%s: the host limits requests: %s", name, budget.host_said)
            row = {"conda_name": conda_name, "upstream_version": version, "last_error": error}
            finished.append(({**row, _ASKED_AT: int(self._now())}, transient))
            if budget.now() - said >= _PROGRESS_SECONDS:
                said = budget.now()
                logger.info("%s: %d of %d finished after %.0f s", name, len(finished), total, budget.elapsed())
        columns = list(self._COLUMNS)
        frame = pd.DataFrame([row for row, _ in finished], columns=columns)
        # A stopped run costs no good data: a row that failed for the cause that stopped it is not
        # written over its last-good value (the store merges by key), and neither is a row never reached.
        kept = [row for row, transient in finished if not (stopped is not None and transient)]
        stored_columns = [*columns, _ASKED_AT]
        has_success = any(row["upstream_version"] is not None and pd.notna(row["upstream_version"]) for row in kept)
        if not has_success:
            kept = []  # AD-13: a batch with no version is not written over last-good
        # Story 51.1: what the stopped run asked and did not write is still marked as asked
        asked: dict[str, str | None] = {}
        if stopped is not None:
            asked = {row["conda_name"]: row["last_error"] for row, transient in finished if transient}
            if stopped_on is not None:
                asked[stopped_on] = stopped.reason.split(";")[0]
        self._persist(pd.DataFrame([*kept, *self._touched(stored, asked)], columns=stored_columns))
        if not has_success and asked:
            # the rows above record only that the host was asked: the store still holds no new data
            self._mark_stale("fetch returned no data — keeping last-good")
        answered = int(frame["upstream_version"].notna().sum()) if not frame.empty else 0
        if stopped is None:
            logger.info(
                "%s: finished %d in %.0f s, %d with a version, %d without",
                name,
                total,
                budget.elapsed(),
                answered,
                len(frame) - answered,
            )
            return frame
        reason = f"{name} unavailable this run: {stopped.reason}; finished {len(frame)} of {total}"
        if budget.host_said and "HTTP 429" in stopped.reason:
            reason += f"; the host said {budget.host_said}"
        logger.warning("%s; the rest keep their last-good rows and are asked again next run", reason)
        self._mark_stale(reason)
        return frame


class VcsHostSeedDataset(_BudgetedRefresh, _ParquetRefreshStore, AbstractDataset):
    """GitLab or Codeberg latest-tag source (``vcs_gitlab_api_raw`` / ``vcs_codeberg_api_raw``).

    ``load()`` is a read-only projection of the persisted store; the live fetch runs
    only via ``save(RefreshRequest(...))`` (the pipeline's refresh-trigger node is the
    single writer, mirroring ``refresh_vdb_store``) — any other payload raises (this
    is still a read-only request source from every OTHER node's perspective).
    """

    _COLUMNS = _VERSION_COLUMNS

    def __init__(
        self,
        *,
        url: str,
        host: str,
        filepath: str,
        credentials: dict[str, Any] | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        rps: float = DEFAULT_RPS,
        scheduler: RateLimitedScheduler | None = None,
        sleep: Callable[[float], None] = time.sleep,
        metadata: dict[str, Any] | None = None,
        failure_budget_seconds: float = DEFAULT_FAILURE_BUDGET_SECONDS,
        max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
        run_deadline_seconds: float = DEFAULT_RUN_DEADLINE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if host not in _HOST_SPECS:
            raise ValueError(f"unknown VCS host {host!r}; expected one of {sorted(_HOST_SPECS)}")
        self._base_url = str(url)
        self._host = host
        self._filepath = str(filepath)
        self._credentials = credentials
        self._timeout_seconds = int(timeout_seconds)
        self._max_retries = int(max_retries)
        self.scheduler = scheduler if scheduler is not None else RateLimitedScheduler(rps=rps)
        self._sleep = sleep
        self.metadata = metadata
        self._failure_budget_seconds = float(failure_budget_seconds)
        self._max_consecutive_failures = int(max_consecutive_failures)
        self._run_deadline_seconds = float(run_deadline_seconds)
        self._clock = clock
        self._new_budget()  # a limit that is not positive is refused here, not at the first refresh
        # review fix #8: the single-source-of-truth store name this instance may
        # legitimately write — validated in save() against the incoming
        # RefreshRequest.store so a future positional drift between
        # _HOST_SPECS/the pipeline's outputs=[...] list can't silently misroute a
        # refresh into the wrong catalog entry.
        self._expected_store = f"vcs_{host}_api_raw"

    def request_path(self, identifier: str) -> str:
        return _HOST_SPECS[self._host].build_path(self._base_url, identifier)

    def fetch_one(self, identifier: str, *, fetcher: Callable[[str], Any] | None = None) -> Any:
        """One bounded fetch via :func:`~pyforge.atlas.datasets.refresh.fetch_one_with_retry`."""
        url = None if fetcher is not None else self.request_path(identifier)

        def _do_fetch() -> Any:
            if fetcher is not None:
                return fetcher(identifier)
            inner = APIDataset(url=url, **_request_kwargs(self._timeout_seconds, self._credentials))
            return _coerce_json(inner.load())

        return fetch_one_with_retry(
            acquire=self.scheduler.acquire,
            fetch=_do_fetch,
            max_retries=self._max_retries,
            sleep=self._sleep,
        )

    def _get(self, url: str, fetcher: Callable[[str], Any] | None, budget: FailureBudget | None = None) -> Any:
        """Story 35.4: one bounded GET with legacy's auth: GitLab's ``PRIVATE-TOKEN`` only under the
        switch, else nothing (a no-op auth keeps ``~/.netrc`` out). ``fetcher`` takes the URL. A 429, a
        5xx or a failure with no status (a dropped connection, a timeout) is retried, a ``Retry-After``
        waited, as legacy retries them (CFA:5009-5014); any other refusal (a 404 release) is not, so the
        tags are asked at once, as legacy does. Story 50.1: every transient failure is held against
        ``budget`` (the run's; a fresh one for a call outside a run) and charged if the request fails in
        the end, which may stop the run with :class:`HostUnavailable`."""

        def _do_fetch() -> Any:
            if fetcher is not None:
                return fetcher(url)
            args = {**public_sources.request_args(self._timeout_seconds), "headers": {"User-Agent": USER_AGENT}}
            auth = credential_switch.gitlab_auth(self._credentials, url) if self._host == "gitlab" else None
            if auth is not None:
                args["auth"] = auth
                # requests strips only ``Authorization`` on a redirect to another host; a custom header
                # would follow it, so a request that carries the token never follows a redirect (AD-2)
                args["allow_redirects"] = False
            response = APIDataset(url=url, load_args=args).load()
            if getattr(response, "is_redirect", False):
                raise FetchError(self._host, int(response.status_code))
            return _coerce_json(response)

        budget = budget if budget is not None else self._new_budget()
        attempt = 0
        while True:
            started = budget.now()
            self.scheduler.acquire()
            try:
                payload = _do_fetch()
            except Exception as exc:
                attempt += 1
                # a failure with no status is retried only when the network caused it (a dropped
                # connection, a timeout: OSError underneath); a programming error is not
                if not _transient(exc):
                    budget.answered()  # a refusal (a 404 release) is the host's answer
                    raise
                budget.heard(_limit_said(exc))
                if attempt > self._max_retries:
                    budget.failed_attempt(started)
                    budget.exhausted(_why(exc))
                    raise
                wait = _retry_after(exc) or retry_backoff_seconds(attempt)
                budget.failed_attempt(started, wait=wait)
                self._sleep(wait)
            else:
                budget.answered()
                return payload

    def _release_or_tag(
        self, identifier: str, *, fetcher: Callable[[str], Any] | None, budget: FailureBudget | None = None
    ) -> tuple[str | None, str | None]:
        """Story 35.4: the latest release, else the first tag, normalized as legacy does
        (``_fetch_release_or_tag``, CFA:4990); ``(None, reason)`` when there is neither."""
        version, error, _transient_failure = self._release_or_tag_outcome(identifier, fetcher, budget)
        return version, error

    def _release_or_tag_outcome(
        self, identifier: str, fetcher: Callable[[str], Any] | None, budget: FailureBudget | None
    ) -> _Outcome:
        """:meth:`_release_or_tag`, and whether its error is a transient failure of the host (Story
        50.1). A stop of the run (:class:`HostUnavailable`) passes through."""
        budget = budget if budget is not None else self._new_budget()
        try:
            release_url, tags_url = _live_host_paths(self._host, self._base_url, identifier)
        except ValueError as exc:
            return None, str(exc), False
        try:
            tag = _release_tag(self._get(release_url, fetcher, budget))
        except HostUnavailable:
            raise
        except Exception:  # noqa: BLE001 -- no release (often a 404): legacy falls back to the tags
            tag = None
        if not tag:
            try:
                tags = self._get(tags_url, fetcher, budget)
            except HostUnavailable:
                raise
            except Exception as exc:  # noqa: BLE001 -- one project's failure is its row's error (AD-13)
                return None, _why(exc), _transient(exc)
            # legacy reads a tag's ``name``, else its ``tag_name``
            names = (
                [t.get("name") or t.get("tag_name") for t in tags if isinstance(t, dict)]
                if isinstance(tags, list)
                else []
            )
            tag = next((str(n) for n in names if n), None)
        version = normalize_release_tag(tag)
        return version, None if version else "no tags", False

    def load_many(
        self,
        identifiers: Sequence[tuple[str, str]],
        *,
        fetcher: Callable[[str], Any] | None = None,
    ) -> pd.DataFrame:
        """Fetch every ``(conda_name, identifier)`` pair, then persist (AD-13
        skip-on-failure: a batch where every fetch failed / yielded no version is
        treated as EMPTY for persistence — never clobbers last-good with an all-null
        result)."""
        live = credential_switch.live_vcs_universe()

        def one(identifier: str, budget: FailureBudget) -> _Outcome:
            if live:
                # Story 35.4: legacy's release-then-tag path (CFA:4990)
                return self._release_or_tag_outcome(identifier, fetcher, budget)
            return _fetch_outcome(lambda: self.fetch_one(identifier, fetcher=fetcher), _HOST_SPECS[self._host], budget)

        # Story 50.1: one budget for failure per run; a host that uses it up is not asked again
        return self._run(self._host, identifiers, one)

    def load(self) -> pd.DataFrame:
        return self._read_store(self._COLUMNS)

    def save(self, data: Any) -> None:
        if not isinstance(data, RefreshRequest):
            raise NotImplementedError(
                f"{type(self).__name__} only accepts a RefreshRequest trigger; it is "
                "otherwise a read-only request source."
            )
        if data.store != self._expected_store:
            # review fix #8: catch a pipeline-wiring drift (e.g. _HOST_SPECS vs. the
            # trigger node's positional outputs=[...] list falling out of sync)
            # loudly rather than silently persisting into the wrong instance's store.
            raise ValueError(
                f"{type(self).__name__} (host={self._host!r}) is configured for store "
                f"{self._expected_store!r} but received a RefreshRequest for "
                f"{data.store!r} — pipeline wiring has drifted out of sync."
            )
        # Story 50.1: a store a stopped run left stale is due, whatever its age, so the rows that run never
        # reached are asked on the next run and its marker is not cleared unasked
        if not data.force and not self.is_stale() and not self._refresh_due(data.cadence_seconds):
            self._clear_stale()
            return
        # Story 35.2: with the flag on, the universe's pairs, not the identity subset
        self.load_many(data.universe_pairs if credential_switch.live_vcs_universe() else data.vcs_pairs)

    def _describe(self) -> dict[str, Any]:
        return {
            "parameterization": type(self).__name__,
            "host": self._host,
            "filepath": self._filepath,
            "rps": self.scheduler.rps,
            "timeout_seconds": self._timeout_seconds,
            "max_retries": self._max_retries,
            "failure_budget_seconds": self._failure_budget_seconds,
            "max_consecutive_failures": self._max_consecutive_failures,
            "run_deadline_seconds": self._run_deadline_seconds,
        }


class RegistryUpstreamDataset(_BudgetedRefresh, _ParquetRefreshStore, AbstractDataset):
    """Cross-ecosystem registry latest-version source (Phase L ``vcs_registry_*_raw``).

    Same shape as :class:`VcsHostSeedDataset` (see its docstring) — one
    ``_REGISTRY_SPECS`` extractor table parameterized per registry.
    """

    _COLUMNS = _VERSION_COLUMNS

    def __init__(
        self,
        *,
        url: str,
        registry: str,
        filepath: str,
        credentials: dict[str, Any] | None = None,
        timeout_seconds: int = DEFAULT_REFRESH_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_REFRESH_MAX_RETRIES,
        rps: float = DEFAULT_RPS,
        scheduler: RateLimitedScheduler | None = None,
        sleep: Callable[[float], None] = time.sleep,
        metadata: dict[str, Any] | None = None,
        failure_budget_seconds: float = DEFAULT_FAILURE_BUDGET_SECONDS,
        max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
        run_deadline_seconds: float = DEFAULT_RUN_DEADLINE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if registry not in _REGISTRY_SPECS:
            raise ValueError(f"unknown registry {registry!r}; expected one of {sorted(_REGISTRY_SPECS)}")
        self._base_url = str(url)
        self._registry = registry
        self._filepath = str(filepath)
        self._credentials = credentials
        self._timeout_seconds = int(timeout_seconds)
        self._max_retries = int(max_retries)
        self.scheduler = scheduler if scheduler is not None else RateLimitedScheduler(rps=rps)
        self._sleep = sleep
        self.metadata = metadata
        self._failure_budget_seconds = float(failure_budget_seconds)
        self._max_consecutive_failures = int(max_consecutive_failures)
        self._run_deadline_seconds = float(run_deadline_seconds)
        self._clock = clock
        self._new_budget()  # a limit that is not positive is refused here, not at the first refresh
        # review fix #8: see VcsHostSeedDataset.__init__ — validated in save().
        self._expected_store = f"vcs_registry_{registry}_raw"

    def request_path(self, identifier: str) -> str:
        return _REGISTRY_SPECS[self._registry].build_path(self._base_url, identifier)

    def fetch_one(self, identifier: str, *, fetcher: Callable[[str], Any] | None = None) -> Any:
        """See :class:`VcsHostSeedDataset.fetch_one` (shared :func:`fetch_one_with_retry`)."""
        url = None if fetcher is not None else self.request_path(identifier)

        def _do_fetch() -> Any:
            if fetcher is not None:
                return fetcher(identifier)
            inner = APIDataset(url=url, **_request_kwargs(self._timeout_seconds, self._credentials))
            return _coerce_json(inner.load())

        return fetch_one_with_retry(
            acquire=self.scheduler.acquire,
            fetch=_do_fetch,
            max_retries=self._max_retries,
            sleep=self._sleep,
        )

    def load_many(
        self,
        identifiers: Sequence[tuple[str, str]],
        *,
        fetcher: Callable[[str], Any] | None = None,
    ) -> pd.DataFrame:
        spec = _REGISTRY_SPECS[self._registry]

        def one(identifier: str, budget: FailureBudget) -> _Outcome:
            return _fetch_outcome(lambda: self.fetch_one(identifier, fetcher=fetcher), spec, budget)

        # Story 50.1: one budget for failure per run, as VcsHostSeedDataset.load_many
        return self._run(self._registry, identifiers, one)

    def load(self) -> pd.DataFrame:
        return self._read_store(self._COLUMNS)

    def save(self, data: Any) -> None:
        if not isinstance(data, RefreshRequest):
            raise NotImplementedError(
                f"{type(self).__name__} only accepts a RefreshRequest trigger; it is "
                "otherwise a read-only request source."
            )
        if data.store != self._expected_store:
            # review fix #8: see VcsHostSeedDataset.save.
            raise ValueError(
                f"{type(self).__name__} (registry={self._registry!r}) is configured for "
                f"store {self._expected_store!r} but received a RefreshRequest for "
                f"{data.store!r} — pipeline wiring has drifted out of sync."
            )
        # Story 50.1: a store a stopped run left stale is due, whatever its age, so the rows that run never
        # reached are asked on the next run and its marker is not cleared unasked
        if not data.force and not self.is_stale() and not self._refresh_due(data.cadence_seconds):
            self._clear_stale()
            return
        # Story 35.2: with the flag on, the universe's pairs, not the identity subset
        self.load_many(data.universe_pairs if credential_switch.live_vcs_universe() else data.vcs_pairs)

    def _describe(self) -> dict[str, Any]:
        return {
            "parameterization": type(self).__name__,
            "registry": self._registry,
            "filepath": self._filepath,
            "rps": self.scheduler.rps,
            "timeout_seconds": self._timeout_seconds,
            "max_retries": self._max_retries,
            "failure_budget_seconds": self._failure_budget_seconds,
            "max_consecutive_failures": self._max_consecutive_failures,
            "run_deadline_seconds": self._run_deadline_seconds,
        }
