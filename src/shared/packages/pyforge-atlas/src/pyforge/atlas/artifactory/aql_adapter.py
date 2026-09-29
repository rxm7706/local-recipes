"""Injectable Artifactory AQL adapter -- Story 15.1 (CAP-1, Epic 15).

Resolves a virtual repository's backing repositories, then aggregates download counts by
package name + version -- the org-specific download telemetry a public PyPI/conda-forge
crawl structurally cannot see. Mock-only: no live Artifactory instance is named, selected,
or contacted anywhere in this module; live wiring is a separate, later, attended step.

Follows the same injectable-transport pattern proven by :mod:`pyforge.atlas.factory.lasuite`
(``LaSuiteClient``): network access happens through EXACTLY ONE injectable transport seam
(``AqlTransport = Callable[[AqlRequest], AqlResponse]``); the default transport (used when
none is injected) raises a clear, named :class:`ArtifactoryAqlError` rather than reaching for
a real HTTP client -- this module imports no ``requests``/``httpx``/``urllib3``/etc. (enforced
structurally, repo-wide, by ``tests/catalog/test_no_inline_io.py``'s ``IO_DENYLIST`` scan).
Unlike ``LaSuiteClient``, this module has no env-driven config resolver -- see the
``ArtifactoryConfig`` docstring below for why.

:class:`ArtifactoryConfig` intentionally carries ONLY ``base_url`` -- no credential/token
field and no env-var credential resolver. Artifactory's real auth shape is undecided and out
of scope for this story; any auth header a live call eventually needs is attached by the real
transport, constructed OUTSIDE package code at the later attended live bring-up. Introducing a
credential resolver here would be exactly the kind of second bespoke credential path this
story must not add.

Resolving backing repos and fetching download rows are two SEPARATE transport round trips
(topology resolution, then the AQL aggregation query) -- never conflated into one request.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pyforge.core.errors import PyforgeError

# ---------------------------------------------------------------------------
# Config -- base URL only. No credential field, no env resolver (see module docstring).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArtifactoryConfig:
    """A resolved Artifactory target -- base URL only."""

    base_url: str


# ---------------------------------------------------------------------------
# Transport seam -- an injectable request/response pair, mirroring lasuite.py's
# Request/Response/Opener triad.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AqlRequest:
    method: str
    url: str
    body: dict[str, Any] | None = None


@dataclass(frozen=True)
class AqlResponse:
    status_code: int
    body: Any = None


#: A transport performs ONE HTTP round-trip: it takes an :class:`AqlRequest` and returns an
#: :class:`AqlResponse`. This is the sole network seam of the module and it is ALWAYS
#: injected -- the concrete HTTP client is constructed OUTSIDE package code so no HTTP client
#: is imported here. Tests inject an in-memory mock; a live opener is a later attended
#: bring-up, out of scope for this story.
AqlTransport = Callable[[AqlRequest], AqlResponse]


def _unconfigured_transport(request: AqlRequest) -> AqlResponse:
    """The default transport -- refuses to run because no transport was injected. Package
    code holds no HTTP client; raising here (rather than importing an HTTP client) keeps the
    module IO-free and offline by default."""
    raise ArtifactoryAqlError(
        f"no Artifactory transport injected for {request.method} {request.url}: "
        "ArtifactoryAqlAdapter needs a `transport` (package code holds no HTTP client). "
        "Inject the mock in tests -- a live transport is a separate, later, attended "
        "Artifactory bring-up; this story (15.1, CAP-1) is mock-only."
    )


class ArtifactoryAqlError(PyforgeError, RuntimeError):
    """An Artifactory AQL request failed. The message names the method, URL, status, and body
    so a retry/repair can reason about it without a traceback, mirroring ``LaSuiteError``."""


# ---------------------------------------------------------------------------
# Output row.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DownloadRow:
    """One aggregated download row -- summed across backing repos and duplicate raw rows for
    the same ``(name, version)`` pair. CAP-1 does not classify or flag rows (no internal/
    private field) -- that is Story 15.2's job."""

    name: str
    version: str
    download_count: int


@dataclass(frozen=True)
class ConsumptionRow:
    """One aggregated org telemetry row -- summed across backing repos and duplicate raw rows
    for the same ``name``. Story 23.2 (CAP-8): platform/app/component/LOB counts from a
    separate consumption rollup round trip (never conflated with download aggregation)."""

    name: str
    platform_env_count: int
    internal_app_count: int
    internal_component_count: int
    internal_lob_count: int


# ---------------------------------------------------------------------------
# The adapter.
# ---------------------------------------------------------------------------


class ArtifactoryAqlAdapter:
    """Resolves a virtual repo's backing repos, then fetches + aggregates its download rows.

    Owns the base URL (from :class:`ArtifactoryConfig`) and delegates the wire to the injected
    ``transport``. Every non-2xx response becomes a clear :class:`ArtifactoryAqlError`.
    """

    def __init__(self, config: ArtifactoryConfig, *, transport: AqlTransport = _unconfigured_transport) -> None:
        self._config = config
        self._transport = transport

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        resp = self._transport(AqlRequest(method=method, url=url, body=body))
        if not (200 <= resp.status_code < 300):
            raise ArtifactoryAqlError(
                f"{method} {url} -> HTTP {resp.status_code}: {resp.body!r} (Artifactory AQL call failed)"
            )
        return resp.body

    def resolve_backing_repos(self, virtual_repo: str) -> list[str]:
        """Resolve a virtual repository to its list of backing repositories (topology round
        trip #1 of 2 -- see :meth:`fetch_download_rows`)."""
        result = self._call("GET", f"/api/repositories/{virtual_repo}")
        repos = result.get("repositories") if isinstance(result, dict) else None
        if not isinstance(repos, list) or not all(isinstance(r, str) for r in repos):
            raise ArtifactoryAqlError(
                f"GET .../api/repositories/{virtual_repo} returned no valid 'repositories' "
                f"list of strings (body={result!r})"
            )
        return list(repos)

    def _fetch_raw_download_rows(self, virtual_repo: str, backing_repos: list[str]) -> list[dict[str, Any]]:
        result = self._call(
            "POST",
            "/api/search/aql",
            {"virtual_repo": virtual_repo, "repos": backing_repos},
        )
        rows = result.get("results") if isinstance(result, dict) else None
        if not isinstance(rows, list):
            raise ArtifactoryAqlError(f"POST .../api/search/aql returned no 'results' list (body={result!r})")
        return rows

    def fetch_download_rows(self, virtual_repo: str) -> list[DownloadRow]:
        """Resolve ``virtual_repo``'s backing repos, fetch its raw download rows, then group
        + sum by ``(name, version)`` -- multiple raw rows for the same pair (one per backing
        repo, or one per file path) sum into one output row, in first-seen order (NOT a
        semantic/version-aware sort -- plain insertion order, so it never implies an ordering
        guarantee it doesn't provide). Two separate transport round trips (topology, then
        aggregation) -- never conflated into one request."""
        backing_repos = self.resolve_backing_repos(virtual_repo)
        raw_rows = self._fetch_raw_download_rows(virtual_repo, backing_repos)

        totals: dict[tuple[str, str], int] = {}
        for row in raw_rows:
            try:
                key = (str(row["name"]), str(row["version"]))
                count = int(row["count"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ArtifactoryAqlError(
                    f"malformed download row for {virtual_repo!r} -- expected "
                    f"'name'/'version'/'count' fields (row={row!r}): {exc}"
                ) from exc
            totals[key] = totals.get(key, 0) + count

        return [
            DownloadRow(name=name, version=version, download_count=count) for (name, version), count in totals.items()
        ]

    def _fetch_raw_consumption_rows(self, virtual_repo: str, backing_repos: list[str]) -> list[dict[str, Any]]:
        result = self._call(
            "POST",
            "/api/consumption/rollup",
            {"virtual_repo": virtual_repo, "repos": backing_repos},
        )
        rows = result.get("results") if isinstance(result, dict) else None
        if not isinstance(rows, list):
            raise ArtifactoryAqlError(f"POST .../api/consumption/rollup returned no 'results' list (body={result!r})")
        return rows

    def fetch_consumption_rows(self, virtual_repo: str) -> list[ConsumptionRow]:
        """Resolve ``virtual_repo``'s backing repos, fetch its raw consumption rollup rows,
        then group + sum by ``name`` -- multiple raw rows for the same name (one per backing
        repo) sum into one output row. Two separate transport round trips (topology, then
        consumption rollup) -- never conflated with :meth:`fetch_download_rows`."""
        backing_repos = self.resolve_backing_repos(virtual_repo)
        raw_rows = self._fetch_raw_consumption_rows(virtual_repo, backing_repos)

        totals: dict[str, tuple[int, int, int, int]] = {}
        for row in raw_rows:
            try:
                name = str(row["name"])
            except (KeyError, TypeError) as exc:
                raise ArtifactoryAqlError(
                    f"malformed consumption row for {virtual_repo!r} -- expected a 'name' field (row={row!r}): {exc}"
                ) from exc
            try:
                platform_env = int(row.get("platform_env_count", 0))
                internal_app = int(row.get("internal_app_count", 0))
                internal_component = int(row.get("internal_component_count", 0))
                internal_lob = int(row.get("internal_lob_count", 0))
            except (TypeError, ValueError) as exc:
                raise ArtifactoryAqlError(
                    f"malformed consumption row for {virtual_repo!r} -- expected numeric "
                    f"telemetry fields (row={row!r}): {exc}"
                ) from exc
            prev = totals.get(name, (0, 0, 0, 0))
            totals[name] = (
                prev[0] + platform_env,
                prev[1] + internal_app,
                prev[2] + internal_component,
                prev[3] + internal_lob,
            )

        return [
            ConsumptionRow(
                name=name,
                platform_env_count=counts[0],
                internal_app_count=counts[1],
                internal_component_count=counts[2],
                internal_lob_count=counts[3],
            )
            for name, counts in totals.items()
        ]
