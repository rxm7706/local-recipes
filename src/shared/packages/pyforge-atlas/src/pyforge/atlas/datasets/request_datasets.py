"""Request-parameterized API datasets — the B1 catalog FLIPs (AC-1 / AC-2 / G-2).

Two catalog entries were declared in Story A2 as an interim single-URL
``api.APIDataset`` with an explicit ``# FLIP``/``# NOTE`` that "one APIDataset = one
URL, but this feed is per-{package,query}-parameterized … nodes may NOT build request
URLs (AC-2)". Story B1 lands the real request-parameterized datasets so the
parameterization + the rate-limit discipline live HERE (dataset-owned IO, AD-2), and
the node body stays a pure ``DataFrame -> DataFrame`` transform:

- ``AnacondaDownloadsDataset`` — per-package ``/package/<owner>/<name>`` anaconda.org
  download stats (Phases F + I). Catalog: ``core_anaconda_downloads_raw`` (was
  ``# FLIP(B1)``). This story completes that flip.
- ``GitHubRequestDataset`` — per-query GitHub GraphQL/REST request bodies (Phases
  E.5 / K / N) with the Phase K single-worker 3-RPS + ``Retry-After`` discipline
  attached at dataset level. Catalog: ``vcs_github_api_raw``. **Gap G-2**: A2's
  comment mis-attributed this to "the vcs port (B2)"; E.5/K/N are B1 ``vcs_health``
  phases, so the request dataset is authored HERE and the attribution corrected.

Both COMPOSE ``kedro_datasets.api.APIDataset`` for the physical HTTP (fsspec/requests
are owned by the composed dataset, NOT imported here — this module stays clean under
``tests/catalog/test_no_inline_io.py``). Construction is lazy + offline (the composed
APIDataset does no network at ``__init__``), so both materialize under the
``kedro-catalog-check`` offline resolution gate with stub credentials.

The concrete per-{package,query} FAN-OUT (issuing N requests through the scheduler)
is dataset-owned and deferred — B1 seeds the parameterization surface + the
rate-limit ownership; the node consumes already-fetched DataFrames (THE CRUX). The
rate-limit *contract* is fixture-tested against a stub in ``tests/datasets`` /
``tests/pipelines`` (AD-10 / AD-11), never a live endpoint.
"""

from __future__ import annotations

from typing import Any

from kedro.io import AbstractDataset
from kedro_datasets.api import APIDataset

from .rate_limit import DEFAULT_RPS, RateLimitedScheduler


class _RequestParameterizedAPIDataset(AbstractDataset):
    """Shared base: compose an ``APIDataset`` + own a rate-limit scheduler.

    The parameterization (building the per-request path/body) is a DATASET method,
    never a node responsibility — that is the AC-2 boundary the whole migration
    exists to enforce. Subclasses expose the concrete parameterization surface.
    """

    def __init__(
        self,
        *,
        url: str,
        method: str = "GET",
        load_args: dict[str, Any] | None = None,
        save_args: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        rps: float = DEFAULT_RPS,
    ) -> None:
        self._base_url = url
        self._method = method
        self._load_args = dict(load_args or {})
        self._credentials = credentials
        self.metadata = metadata
        # Rate-limit discipline is a DATASET concern (AD-2). The scheduler is
        # single-worker 3-RPS by default (Phase K contract); the concrete fan-out
        # acquires a token per request. Injectable clock/sleep keep it fixture-safe.
        self.scheduler = RateLimitedScheduler(rps=rps)
        # Compose the physical HTTP IO lazily (no network at __init__).
        self._inner = APIDataset(
            url=url,
            method=method,
            load_args=load_args,
            save_args=save_args,
            credentials=credentials,
            metadata=metadata,
        )

    # -- kedro 1.5.0 AbstractDataset public abstract methods ----------------

    def load(self) -> Any:
        """Delegate the physical fetch to the composed ``APIDataset``. The
        per-{package,query} fan-out through :attr:`scheduler` is dataset-owned and
        deferred (B1 seeds it); a node NEVER reaches this — it receives the resolved
        DataFrame via the catalog."""
        return self._inner.load()

    def save(self, data: Any) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} is a read-only request source; it is never saved to."
        )

    def _describe(self) -> dict[str, Any]:
        return {
            "base_url": self._base_url,
            "method": self._method,
            "rps": self.scheduler.rps,
            "parameterization": type(self).__name__,
        }


class AnacondaDownloadsDataset(_RequestParameterizedAPIDataset):
    """Per-package anaconda.org download-stats source (Phases F + I).

    The A2 interim declared a single ``.../package`` URL; the real feed is
    per-package path-parameterized (``/package/<owner>/<name>``). :meth:`request_path`
    builds that path so the NODE never does (AC-2). ``core_anaconda_downloads_raw``.
    """

    def request_path(self, owner: str, name: str) -> str:
        """Build the per-package request path — the parameterization a node may NOT
        perform (AC-2). ``owner`` defaults to ``conda-forge`` in the legacy path."""
        owner = (owner or "conda-forge").strip("/")
        name = name.strip("/")
        return f"{self._base_url.rstrip('/')}/{owner}/{name}"


class GitHubRequestDataset(_RequestParameterizedAPIDataset):
    """Per-query GitHub GraphQL/REST request-body source (Phases E.5 / K / N).

    Gap G-2: authored in B1 (E.5/K/N are ``vcs_health`` B1 phases), not B2. One
    dataset = one request body; :meth:`with_query` produces the parameterized
    ``load_args.json`` a node may NOT build (AC-2). The Phase K single-worker 3-RPS
    token bucket + ``Retry-After`` discipline are attached here (dataset level), not
    in the node body. ``vcs_github_api_raw``.
    """

    def with_query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build the GraphQL POST body for a single query — dataset-owned request
        parameterization (AC-2). Returns the ``load_args.json`` payload; the concrete
        POST fan-out through :attr:`scheduler` is dataset-owned and deferred."""
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = dict(variables)
        return body
