"""La Suite Docs / Wagtail REST sync — Story H3 (FR-22(c), § 7.1, AD-22).

Pushes the Karpathy-wiki's final report pages (``wiki/outputs/`` by default — the Oracle's
human-facing reports, per the H1 layout contract + § 7.4) up to the Layer-1 CMS — the human
"Corporate Brain" (§ 7.1: django-lasuite + Wagtail). Three properties shape this module:

* **Idempotent-first (§ 2.1 — the H3 acceptance contract).** :class:`WikiSyncer` keeps a content
  digest per file, so a re-push of UNCHANGED content makes **no remote call at all** (not a
  redundant PATCH). New file → create; changed content → update; unchanged → skip. An agent can
  safely retry the sync; running it twice on a static wiki is a no-op remotely.
* **Transport is INJECTABLE — offline-testable, live-deferred (the D3/F3/G3 pattern).** The
  client talks to the CMS through an injected ``opener``; the default opens real HTTP via
  ``httpx`` (imported lazily, only when the live path runs), and the gate injects an in-memory
  mock Wagtail so the round-trip (push / update / idempotent re-push) is proven with NO network.
  Standing up a live Wagtail/La Suite server + credential is the attended bring-up (DW-H3).
* **AD-22 write-boundary.** The syncer writes ONLY the CMS (over REST) and its own mapping sidecar
  INSIDE the wiki root (via :class:`~pyforge.atlas.factory.wiki.WikiLayout`) — never an atlas
  dataset. The endpoint + token come from config/env, never a hardcoded host (AD-2).
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from .crews import parse_frontmatter
from .wiki import WikiLayout

# ---------------------------------------------------------------------------
# Config (env-driven, never a hardcoded host — AD-2).
# ---------------------------------------------------------------------------

LASUITE_BASE_URL_ENV = "LASUITE_BASE_URL"
LASUITE_TOKEN_ENV = "LASUITE_API_TOKEN"


@dataclass(frozen=True)
class LaSuiteConfig:
    """A resolved CMS target — base URL + bearer token, both from the environment."""

    base_url: str
    api_token: str


def resolve_lasuite_config(env: Mapping[str, str] | None = None) -> LaSuiteConfig | None:
    """Resolve the CMS endpoint from env, or ``None`` if not configured (both a base URL AND a
    token are required — a partial config resolves to ``None`` so the caller degrades instead of
    pushing at a half-configured or public endpoint). The live bring-up (DW-H3) supplies these."""
    env = os.environ if env is None else env
    base = (env.get(LASUITE_BASE_URL_ENV) or "").strip()
    token = (env.get(LASUITE_TOKEN_ENV) or "").strip()
    if not base or not token:
        return None
    return LaSuiteConfig(base_url=base.rstrip("/"), api_token=token)


# ---------------------------------------------------------------------------
# Transport seam — an injectable request opener.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Request:
    method: str
    url: str
    headers: dict[str, str]
    json: dict[str, Any] | None = None


@dataclass(frozen=True)
class Response:
    status_code: int
    body: Any = None


#: An opener performs ONE HTTP round-trip: it takes a :class:`Request` and returns a
#: :class:`Response`. This is the sole network seam of the module and it is ALWAYS injected —
#: exactly like the B5/B7/B8 dataset ``refresher``/``fetcher`` callables, the concrete HTTP client
#: (httpx/requests) is constructed OUTSIDE package code so no HTTP client is imported here (AC-2:
#: package code performs no direct IO). The gate injects an in-memory mock; the attended live
#: bring-up injects a real httpx-backed opener (DW-H3).
Opener = Callable[[Request], Response]


def _unconfigured_opener(request: Request) -> Response:
    """The default opener — refuses to run because no transport was injected. Package code holds
    no HTTP client (AC-2); the live httpx opener is supplied at the attended H3 bring-up (DW-H3).
    Raising here (rather than importing httpx) keeps the module IO-free and offline by default."""
    raise LaSuiteError(
        f"no CMS transport injected for {request.method} {request.url}: LaSuiteClient needs an "
        "`opener` (package code holds no HTTP client — AC-2). Inject the mock in tests, or the "
        "live httpx-backed opener at the attended La Suite/Wagtail bring-up (DW-H3)."
    )


class LaSuiteError(RuntimeError):
    """A CMS request failed. The message is hyper-clear (§ 2.1: agents auto-diagnose) — it names
    the method, URL, status, and body so a retry/repair can reason about it without a traceback."""


class LaSuiteClient:
    """A thin REST client for La Suite Docs / Wagtail (create / update / get / list documents).

    The client owns the base URL + auth header (from :class:`LaSuiteConfig`) and delegates the
    wire to the injected ``opener``. Every non-2xx response becomes a clear :class:`LaSuiteError`.
    """

    def __init__(self, config: LaSuiteConfig, *, opener: Opener = _unconfigured_opener) -> None:
        self._config = config
        self._opener = opener

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.api_token}",
            "Content-Type": "application/json",
        }

    def _call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        # rstrip so a base_url with OR without a trailing slash composes identically (a raw
        # LaSuiteConfig may carry one; resolve_lasuite_config already strips it).
        url = f"{self._config.base_url.rstrip('/')}{path}"
        resp = self._opener(Request(method=method, url=url, headers=self._headers(), json=payload))
        if not (200 <= resp.status_code < 300):
            raise LaSuiteError(
                f"{method} {url} -> HTTP {resp.status_code}: {resp.body!r} "
                "(La Suite / Wagtail REST call failed)"
            )
        return resp.body

    def create_document(self, title: str, content: str, parent_id: str | None = None) -> dict:
        payload: dict[str, Any] = {"title": title, "content": content}
        if parent_id:
            payload["parent"] = parent_id
        return self._call("POST", "/api/v1/documents/", payload)

    def update_document(self, doc_id: str, title: str, content: str) -> dict:
        return self._call(
            "PATCH", f"/api/v1/documents/{doc_id}/", {"title": title, "content": content}
        )

    def get_document(self, doc_id: str) -> dict:
        return self._call("GET", f"/api/v1/documents/{doc_id}/")

    def list_documents(self) -> list:
        return self._call("GET", "/api/v1/documents/all/")


# ---------------------------------------------------------------------------
# The syncer — idempotent compiled-wiki → CMS push.
# ---------------------------------------------------------------------------

#: Mapping sidecar name, kept at the wiki ROOT (AD-22: inside the wiki tree, never an atlas
#: dataset; not inside compiled/ so it is not itself a lint target).
SYNC_MAP_NAME = ".lasuite_sync.json"


@dataclass
class SyncReport:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # unchanged — NO remote call made

    @property
    def total(self) -> int:
        return len(self.created) + len(self.updated) + len(self.skipped)


class WikiSyncer:
    """Syncs a wiki STAGE to the CMS idempotently, keyed by content digest.

    Default source stage is ``outputs/`` — the Oracle's FINAL human-facing reports (§ 7.4, § 4.12:
    "agents output reports directly into the Wagtail CMS"), which is exactly what the H1
    single-owner layout contract (``wiki.py``) records the H3 syncer reads. ``compiled/`` holds the
    INTERNAL knowledge-graph / BSL-mapped artifacts (§ 7.4) that back those reports but are not
    themselves the CMS surface; ``source_stage`` can override for a different pipeline wiring.

    A local mapping (``<wiki-root>/.lasuite_sync.json``: ``{relpath: {"id", "sha"}}``) records the
    CMS document id + the last-synced content digest for each file — so re-running against an
    unchanged wiki performs ZERO remote calls (idempotent re-push), a changed file UPDATEs (not a
    duplicate create), and a new file CREATEs. The mapping is the idempotency key: it is persisted
    ATOMICALLY (tmp + ``os.replace``, mirroring ``datasets/refresh.py``) so a crash/ENOSPC mid-save
    can't corrupt it, and only after a successful create so a mid-run failure never records a
    phantom id. A corrupt mapping fails LOUDLY (it must not be blind-deleted — that would
    duplicate-create every page).
    """

    def __init__(
        self, client: LaSuiteClient, layout: WikiLayout, *, source_stage: str = "outputs"
    ) -> None:
        self._client = client
        self._layout = layout
        self._source_stage = source_stage
        self._map_path = layout.root / SYNC_MAP_NAME
        self._mapping: dict[str, dict[str, str]] = self._load_mapping()

    def sync_all(self) -> SyncReport:
        report = SyncReport()
        src_dir = self._layout.stage_dir(self._source_stage)
        for md in sorted(src_dir.rglob("*.md")):
            rel = str(md.relative_to(src_dir))
            self._sync_one(md, rel, report)
        return report

    def _sync_one(self, md: Path, rel: str, report: SyncReport) -> None:
        content = md.read_text(encoding="utf-8")
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        title = self._title_of(content, md.stem)
        entry = self._mapping.get(rel)

        if entry is None:
            result = self._client.create_document(title=title, content=content)
            self._mapping[rel] = {"id": self._created_id(result, rel), "sha": sha}
            self._save_mapping()
            report.created.append(rel)
        elif entry.get("sha") != sha:
            doc_id = entry.get("id")
            if not doc_id:
                raise LaSuiteError(
                    f"sync mapping entry for {rel!r} has no 'id' — cannot update it; the mapping "
                    f"file {self._map_path} is corrupt for this page (restore it or reconcile "
                    "against the CMS rather than deleting it, which re-creates every page)."
                )
            self._client.update_document(doc_id=doc_id, title=title, content=content)
            entry["sha"] = sha
            self._save_mapping()
            report.updated.append(rel)
        else:
            # Unchanged since the last sync — idempotent re-push makes NO remote call (§ 2.1).
            report.skipped.append(rel)

    @staticmethod
    def _created_id(result: Any, rel: str) -> str:
        """Extract the new document id from a create response — a clear error, never a bare
        KeyError, if a 2xx body lacks ``id`` (a malformed/enveloped server response), honoring the
        module's § 2.1 error-clarity contract on the LIVE path too."""
        if not isinstance(result, dict) or "id" not in result:
            raise LaSuiteError(
                f"CMS create for {rel!r} returned 2xx but no 'id' (body={result!r}); cannot record "
                "the idempotency mapping. The Wagtail/La Suite create response must include the new "
                "document id."
            )
        return str(result["id"])

    @staticmethod
    def _title_of(content: str, stem: str) -> str:
        try:
            meta, body = parse_frontmatter(content)
        except Exception:
            # A malformed page must not crash the sync (mirrors the H2 crews' per-page
            # resilience); fall back to the file stem as the title.
            return stem
        title = str(meta.get("title") or "").strip()
        if title:
            return title
        for line in body.splitlines():
            if line.startswith("# "):
                heading = line[2:].strip()
                if heading:  # a blank '# ' heading is not a usable title
                    return heading
        return stem  # never an empty title (the live CMS may reject "")

    def _load_mapping(self) -> dict[str, dict[str, str]]:
        if not self._map_path.exists():
            return {}
        try:
            data = json.loads(self._map_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            # The mapping IS the idempotency key — a corrupt one must fail loudly, not be silently
            # treated as empty (which would re-create every page as a CMS duplicate).
            raise LaSuiteError(
                f"the wiki sync mapping {self._map_path} is unreadable/corrupt "
                f"({type(exc).__name__}: {exc}); it is the idempotency key — restore it or reconcile "
                "against the CMS before re-syncing, do NOT delete it blind (that duplicate-creates "
                "every page)."
            ) from exc
        if not isinstance(data, dict):
            raise LaSuiteError(f"the wiki sync mapping {self._map_path} is not a JSON object")
        return data

    def _save_mapping(self) -> None:
        # Atomic write (mirrors datasets/refresh.py): a crash/ENOSPC mid-save can't corrupt the
        # idempotency key — write a sibling tmp then os.replace (atomic on POSIX).
        tmp = self._map_path.with_name(self._map_path.name + ".tmp")
        tmp.write_text(
            json.dumps(self._mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(tmp, self._map_path)
