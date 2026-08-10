"""Steward's `sync` duty-adapter module (Epic 8, Story 8.1) — "one module per
duty", mirrors `keys.py`/`deploy.py`/`budget.py`'s own precedent.

Story 8.1 slice: the whole `sync` duty in one pass — `SyncConfig`/
`SyncConfigError`/`load_config` (the non-secret, operator-declared mapping of
GitHub project/field IDs, Jira base URL/project key/field IDs,
`field_overrides`, and `user_mapping` that makes the engine board-agnostic), a
GitHub GraphQL client and a Jira REST v3 client built on an injectable
`transport` seam (a real `urlopen`-backed one by default, wrapping
`.claude/skills/conda-forge-expert/scripts/_http.py`'s `open_url` — never a
live network call from a test), and `reconcile` — the event-triggered
reconciliation core (ARCHITECTURE-SPINE.md's Design Paradigm): a webhook or
schedule tick is only ever a wake-up, never a value source. Every call re-reads
both linked items' current state, compares each side's own `updated_at`
against its own recorded sync-point field (AD-5 — never a cross-vendor
wall-clock comparison), and converges the divergent side; on a real conflict
GitHub wins unless `field_overrides` says otherwise (AD-4). Control-plane
state — the entity link and the per-item sync point — lives only as
configured fields on the items themselves; there is no sidecar store of any
kind (AD-2).

Every outbound request's auth goes through `keys.HostScopedCredential`/
`resolve_headers` → `_http.py`'s `auth_headers_for` (AD-8) — this module
never builds its own credential/header logic. `SyncDuty` is the
`Duty`-conforming adapter `cli.py`'s `resolve_duty("sync")` now returns,
wiring `steward sync reconcile (--github-item ID | --jira-issue KEY)
[--config PATH] [--dry-run]`.

See ARCHITECTURE-SPINE.md's Design Paradigm and this story's own spec Design
Notes ("Reconcile algorithm") for the two load-bearing corrections `reconcile`
implements verbatim: (1) a
value-equality short-circuit before ANY write/no-op decision is reported —
the structural reason an unrelated field edit (AD-5 is item-level, not
field-level, staleness) never drives a live push for a value the destination
already holds; (2) the sync-point timestamp is captured strictly AFTER the
cross-system write completes, never before or once up front — a pre-write
capture can never be guaranteed >= the write's own server-side timestamp,
which would permanently defeat the loop guard for that item.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlparse

import yaml

from .interfaces import DutyResult
from .keys import HostScopedCredential, repo_root, resolve_headers

# `keys.py`'s own import (above) already resolved and inserted `_http.py`'s
# directory onto `sys.path` (its `locate_http_module`/bridge walk-up) --
# reused here rather than repeating that walk-up search a second time.
from _http import open_url  # noqa: E402  — see the comment immediately above

_GITHUB_API_HOST = "api.github.com"
_GITHUB_GRAPHQL_URL = f"https://{_GITHUB_API_HOST}/graphql"


# ── `.steward/sync-config.yaml` read (the non-secret, board-agnostic mapping) ──

_SYNC_CONFIG_RELATIVE_PATH = Path(".steward/sync-config.yaml")

_REQUIRED_GITHUB_FIELDS: tuple[str, ...] = (
    "project_id", "status_field_id", "link_field_id", "sync_point_field_id",
)
_REQUIRED_JIRA_FIELDS: tuple[str, ...] = (
    "base_url", "project_key", "link_field_id", "sync_point_field_id",
)

# The only field_overrides value this story recognizes -- overriding AD-4's
# default GitHub-wins authority for one field. "github" is deliberately not
# accepted: it is already the default, and accepting it as a no-op value
# would let a typo (any string that isn't "jira") silently pass validation
# while still reverting to default authority.
_VALID_OVERRIDE_AUTHORITY = "jira"

# The only field name `reconcile` actually consults an override for. An
# unrecognized key (e.g. a typo'd "statuz") must fail loud too -- otherwise
# it loads successfully and is silently ignored, which is exactly the
# "typo must fail loud" property this module already enforces for the
# authority value but not, before this check, for the key.
_VALID_OVERRIDE_FIELDS: tuple[str, ...] = ("status",)


class SyncConfigError(ValueError):
    """A missing or malformed `.steward/sync-config.yaml` document."""


@dataclass(frozen=True)
class SyncConfig:
    """The operator-declared, non-secret control-plane mapping (AD-2/AD-3).

    Every field here names an ID/URL that already exists on the external
    GitHub Projects V2 board / Jira Cloud project -- this story never
    provisions any of them (Boundaries & Constraints, "Never")."""

    github_project_id: str
    github_status_field_id: str
    github_link_field_id: str
    github_sync_point_field_id: str
    jira_base_url: str
    jira_project_key: str
    jira_link_field_id: str
    jira_sync_point_field_id: str
    field_overrides: dict[str, str] = field(default_factory=dict)
    user_mapping: dict[str, str] = field(default_factory=dict)


def default_config_path() -> Path:
    """`.steward/sync-config.yaml` at the repo root."""
    return repo_root() / _SYNC_CONFIG_RELATIVE_PATH


def _require_section(
    document_path: Path, section: object, section_name: str, keys_: tuple[str, ...]
) -> dict[str, str]:
    if not isinstance(section, dict):
        raise SyncConfigError(
            f"{document_path}: {section_name!r} section missing or not a mapping"
        )
    values: dict[str, str] = {}
    for key in keys_:
        value = section.get(key)
        if not isinstance(value, str) or not value.strip():
            raise SyncConfigError(
                f"{document_path}: '{section_name}.{key}' is required and must be a "
                "non-empty string"
            )
        values[key] = value
    return values


def load_config(path: str | Path) -> SyncConfig:
    """Load `.steward/sync-config.yaml`-shaped YAML from `path`.

    Mirrors `keys.load_inventory`'s missing/malformed handling: a missing
    file and malformed content are two distinct, named `SyncConfigError`
    cases (never a silent "empty config" default -- unlike an inventory or a
    budget ledger, a sync config has no sensible empty state; every field is
    a required precondition an operator must have already provisioned).
    `yaml.safe_load` only.
    """
    document_path = Path(path)
    if not document_path.is_file():
        raise SyncConfigError(f"{document_path}: sync config not found")

    try:
        with document_path.open("r", encoding="utf-8") as f:
            document = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise SyncConfigError(f"{document_path}: malformed YAML: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise SyncConfigError(f"{document_path}: unreadable: {exc}") from exc

    if not isinstance(document, dict):
        raise SyncConfigError(
            f"{document_path}: top-level document must be a mapping, got "
            f"{type(document).__name__}"
        )

    github_values = _require_section(document_path, document.get("github"), "github", _REQUIRED_GITHUB_FIELDS)
    jira_values = _require_section(document_path, document.get("jira"), "jira", _REQUIRED_JIRA_FIELDS)

    field_overrides = document.get("field_overrides") or {}
    if not isinstance(field_overrides, dict):
        raise SyncConfigError(f"{document_path}: 'field_overrides' must be a mapping")
    for field_name, authority in field_overrides.items():
        if field_name not in _VALID_OVERRIDE_FIELDS:
            raise SyncConfigError(
                f"{document_path}: field_overrides key {field_name!r} is not a recognized "
                f"field (only {_VALID_OVERRIDE_FIELDS!r} are recognized)"
            )
        if authority != _VALID_OVERRIDE_AUTHORITY:
            raise SyncConfigError(
                f"{document_path}: field_overrides[{field_name!r}] = {authority!r} is not "
                f"a recognized authority (only {_VALID_OVERRIDE_AUTHORITY!r} is a valid "
                "override -- github is the default and never needs to be named)"
            )

    user_mapping = document.get("user_mapping") or {}
    if not isinstance(user_mapping, dict):
        raise SyncConfigError(f"{document_path}: 'user_mapping' must be a mapping")

    return SyncConfig(
        github_project_id=github_values["project_id"],
        github_status_field_id=github_values["status_field_id"],
        github_link_field_id=github_values["link_field_id"],
        github_sync_point_field_id=github_values["sync_point_field_id"],
        jira_base_url=jira_values["base_url"],
        jira_project_key=jira_values["project_key"],
        jira_link_field_id=jira_values["link_field_id"],
        jira_sync_point_field_id=jira_values["sync_point_field_id"],
        field_overrides=dict(field_overrides),
        user_mapping=dict(user_mapping),
    )


# ── Named failure modes (never swallowed -- every API/link failure surfaces
# as a duty-level failure, per the I/O & Edge-Case Matrix) ─────────────────


class SyncError(Exception):
    """Base class for this module's own named failure modes."""


class SyncAPIError(SyncError):
    """A GitHub/Jira API call failed, or returned a response this module
    cannot use (a non-2xx status, malformed JSON, or a missing expected key)."""


class SyncUnlinkedError(SyncError):
    """An item has no identity-link value recorded pointing at its
    counterpart on the other side."""


# ── The injectable transport seam ───────────────────────────────────────────
#
# Every GitHub/Jira HTTP call goes through this callable -- the default is a
# real `urlopen`-backed one built on `_http.py`'s `open_url`, so tests can
# substitute a fake that returns canned JSON and never make a live network
# call, with no new mocking dependency.


@dataclass(frozen=True)
class TransportResponse:
    """What a `transport` callable returns -- the HTTP status and raw body,
    already fully read (never a context-managed stream a fake would also
    have to imitate)."""

    status: int
    body: bytes


TransportFn = Callable[[urllib.request.Request], TransportResponse]


def _default_transport(request: urllib.request.Request) -> TransportResponse:
    """The real transport: `_http.py`'s `open_url` (truststore injection),
    never a bare `urlopen` call (Boundaries & Constraints: "never call
    urlopen directly").

    An HTTP error status (4xx/5xx) is captured as a `TransportResponse`
    rather than left to raise -- the caller (`github_graphql_request`/the
    Jira client functions) is the one that decides what a given status means
    for that endpoint. A lower-level transport failure (DNS, connection
    refused, timeout -- `URLError`, of which `HTTPError` is itself a
    subclass, so it MUST be caught first) is not a response at all; it is
    raised as `SyncAPIError` here so every caller sees one consistent
    exception type for "the network call itself could not be completed".
    """
    try:
        with open_url(request, timeout=30) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            return TransportResponse(status=status, body=resp.read())
    except urllib.error.HTTPError as exc:
        return TransportResponse(status=exc.code, body=exc.read())
    except urllib.error.URLError as exc:
        raise SyncAPIError(
            f"{request.get_method()} {request.full_url}: {exc.reason}"
        ) from exc


# ── Timestamp handling (AD-5's loop guard compares these) ──────────────────


def _parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp from either vendor's API.

    A timezone-naive value (e.g. a hand-edited sync-point field with no
    offset) is treated as UTC rather than left to raise `TypeError` the
    first time it is compared against a timezone-aware value -- every
    timestamp `reconcile` compares flows through this one function, so
    normalizing here is sufficient; no comparison site needs its own
    naive/aware guard.
    """
    try:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    except (AttributeError, ValueError) as exc:
        raise SyncAPIError(f"sync: cannot parse timestamp {value!r}: {exc}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# ── GitHub Projects V2 (GraphQL) client ─────────────────────────────────────

_GET_PROJECT_ITEM_QUERY = """
query($itemId: ID!) {
  node(id: $itemId) {
    ... on ProjectV2Item {
      id
      updatedAt
      fieldValues(first: 50) {
        nodes {
          ... on ProjectV2ItemFieldTextValue {
            text
            field { ... on ProjectV2FieldCommon { id } }
          }
        }
      }
    }
  }
}
"""

_UPDATE_PROJECT_ITEM_FIELD_MUTATION = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
  updateProjectV2ItemFieldValue(
    input: { projectId: $projectId, itemId: $itemId, fieldId: $fieldId, value: $value }
  ) { projectV2Item { id } }
}
"""


def github_graphql_request(
    query: str, variables: dict[str, object], *, credential: HostScopedCredential, transport: TransportFn
) -> dict[str, object]:
    """POST `query`/`variables` to `https://api.github.com/graphql`.

    Auth via `keys.resolve_headers` (AD-8) -- never a new header/auth path.
    Raises `SyncAPIError` for a non-2xx status, malformed JSON, or a
    populated top-level `"errors"` array (GraphQL's own error-reporting
    shape, distinct from a transport-level HTTP failure) -- propagated, not
    swallowed.
    """
    headers = dict(resolve_headers(credential, _GITHUB_GRAPHQL_URL))
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/vnd.github+json"
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(_GITHUB_GRAPHQL_URL, data=body, headers=headers, method="POST")

    response = transport(request)
    if response.status >= 400:
        raise SyncAPIError(
            f"GitHub GraphQL request failed: HTTP {response.status}: {response.body[:500]!r}"
        )
    try:
        payload = json.loads(response.body)
    except json.JSONDecodeError as exc:
        raise SyncAPIError(f"GitHub GraphQL request: malformed JSON response: {exc}") from exc
    if not isinstance(payload, dict):
        raise SyncAPIError(
            f"GitHub GraphQL request: unexpected response shape ({type(payload).__name__}, not an object)"
        )
    if payload.get("errors"):
        raise SyncAPIError(f"GitHub GraphQL request returned errors: {payload['errors']}")
    return payload


@dataclass(frozen=True)
class GitHubItemState:
    """One GitHub Projects V2 item's current state, as read fresh (the
    reconcile-not-propagate paradigm — a webhook payload is never trusted as
    this state; AD-9)."""

    item_id: str
    link: str | None
    status: str | None
    updated_at: datetime
    sync_point: datetime | None


def get_project_item(
    item_id: str, *, config: SyncConfig, credential: HostScopedCredential, transport: TransportFn
) -> GitHubItemState:
    """Read a GitHub Projects V2 item's `updatedAt`, tracked status, link,
    and sync-point field values.

    Every field is read as `ProjectV2ItemFieldTextValue` -- this story's
    tracked GitHub field is a plain TEXT field, never GitHub's native
    single-select Status field (there is no select-option-ID resolution
    anywhere in this module; the raw string value is propagated 1:1,
    matching the Boundaries & Constraints' "Never build a general
    status-vocabulary translation table").

    Raises `SyncAPIError` for a missing/malformed `data.node` or `updatedAt`
    -- never a raw `KeyError` escaping to `cli.main()`'s crash boundary.
    """
    payload = github_graphql_request(
        _GET_PROJECT_ITEM_QUERY, {"itemId": item_id}, credential=credential, transport=transport
    )
    try:
        node = payload["data"]["node"]
    except (KeyError, TypeError) as exc:
        raise SyncAPIError(
            f"GitHub project item {item_id}: malformed response (missing data.node)"
        ) from exc
    if node is None:
        raise SyncAPIError(f"GitHub project item {item_id}: not found")
    try:
        updated_at = _parse_timestamp(node["updatedAt"])
    except (KeyError, TypeError) as exc:
        raise SyncAPIError(
            f"GitHub project item {item_id}: malformed response (missing updatedAt)"
        ) from exc

    field_values: dict[str, str] = {}
    for entry in ((node.get("fieldValues") or {}).get("nodes") or []):
        field_id = ((entry or {}).get("field") or {}).get("id")
        text = (entry or {}).get("text")
        if field_id is not None and text is not None:
            field_values[field_id] = text

    sync_point_raw = field_values.get(config.github_sync_point_field_id)
    return GitHubItemState(
        item_id=item_id,
        link=field_values.get(config.github_link_field_id),
        status=field_values.get(config.github_status_field_id),
        updated_at=updated_at,
        sync_point=_parse_timestamp(sync_point_raw) if sync_point_raw else None,
    )


def update_project_item_field(
    item_id: str,
    field_id: str,
    value: str,
    *,
    config: SyncConfig,
    credential: HostScopedCredential,
    transport: TransportFn,
) -> None:
    """`updateProjectV2ItemFieldValue` -- write `value` to `field_id` on
    `item_id` (used for both the tracked status field and the sync-point
    field; the caller decides which `field_id`)."""
    variables = {
        "projectId": config.github_project_id,
        "itemId": item_id,
        "fieldId": field_id,
        "value": {"text": value},
    }
    payload = github_graphql_request(
        _UPDATE_PROJECT_ITEM_FIELD_MUTATION, variables, credential=credential, transport=transport
    )
    try:
        payload["data"]["updateProjectV2ItemFieldValue"]["projectV2Item"]["id"]
    except (KeyError, TypeError) as exc:
        raise SyncAPIError(
            f"GitHub update field {field_id} on item {item_id}: malformed response"
        ) from exc


# ── Jira Cloud (REST API v3) client ─────────────────────────────────────────


def _jira_issue_url(config: SyncConfig, issue_key: str) -> str:
    """`issue_key` is escaped -- it can originate from an external webhook
    payload (`--jira-issue` on the CLI), and is never trusted as a safe URL
    path segment."""
    return f"{config.jira_base_url.rstrip('/')}/rest/api/3/issue/{quote(issue_key, safe='')}"


@dataclass(frozen=True)
class JiraIssueState:
    """One Jira issue's current state, as read fresh (same
    reconcile-not-propagate rationale as `GitHubItemState`)."""

    issue_key: str
    link: str | None
    status: str | None
    updated_at: datetime
    sync_point: datetime | None


def get_jira_issue(
    issue_key: str, *, config: SyncConfig, credential: HostScopedCredential, transport: TransportFn
) -> JiraIssueState:
    """`GET /rest/api/3/issue/{key}` -- reads only the fields this module
    needs (`status`, `updated`, the configured link/sync-point custom
    fields), never the full issue payload.

    Raises `SyncAPIError` for a non-2xx status, malformed JSON, or a
    missing/malformed `fields`/`updated` -- never a raw `KeyError`.
    """
    requested_fields = f"status,updated,{config.jira_link_field_id},{config.jira_sync_point_field_id}"
    url = f"{_jira_issue_url(config, issue_key)}?fields={requested_fields}"
    headers = dict(resolve_headers(credential, url))
    headers["Accept"] = "application/json"
    request = urllib.request.Request(url, headers=headers, method="GET")

    response = transport(request)
    if response.status >= 400:
        raise SyncAPIError(f"Jira issue {issue_key}: HTTP {response.status}: {response.body[:500]!r}")
    try:
        payload = json.loads(response.body)
    except json.JSONDecodeError as exc:
        raise SyncAPIError(f"Jira issue {issue_key}: malformed JSON response: {exc}") from exc
    try:
        fields = payload["fields"]
        updated_at = _parse_timestamp(fields["updated"])
    except (KeyError, TypeError) as exc:
        raise SyncAPIError(
            f"Jira issue {issue_key}: malformed response (missing fields/updated)"
        ) from exc

    sync_point_raw = fields.get(config.jira_sync_point_field_id)
    status_field = fields.get("status")
    status = status_field.get("name") if isinstance(status_field, dict) else None
    return JiraIssueState(
        issue_key=issue_key,
        link=fields.get(config.jira_link_field_id),
        status=status,
        updated_at=updated_at,
        sync_point=_parse_timestamp(sync_point_raw) if sync_point_raw else None,
    )


def update_jira_issue_fields(
    issue_key: str,
    fields_: dict[str, object],
    *,
    config: SyncConfig,
    credential: HostScopedCredential,
    transport: TransportFn,
) -> None:
    """`PUT /rest/api/3/issue/{key}` with `{"fields": fields_}` -- used for
    the sync-point field write (status changes go through
    `transition_jira_issue` instead; Jira status is not a plain settable
    field). A 2xx status (Jira's real API returns 204; this module accepts
    any status `< 300` rather than hard-coding 204 exactly) is success."""
    url = _jira_issue_url(config, issue_key)
    headers = dict(resolve_headers(credential, url))
    headers["Content-Type"] = "application/json"
    body = json.dumps({"fields": fields_}).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="PUT")

    response = transport(request)
    if response.status >= 300:
        raise SyncAPIError(
            f"Jira update fields on {issue_key}: HTTP {response.status}: {response.body[:500]!r}"
        )


def transition_jira_issue(
    issue_key: str,
    target_status: str,
    *,
    config: SyncConfig,
    credential: HostScopedCredential,
    transport: TransportFn,
) -> None:
    """Two-step transition (Jira transitions are by ID, not by name): `GET
    .../transitions` to find the transition whose `to.name` matches
    `target_status`, then `POST` the same endpoint with `{"transition":
    {"id": "<found id>"}}`.

    If no transition matches, that IS the I/O & Edge-Case Matrix's "target
    API rejects the pushed value" row -- raises `SyncAPIError` naming the
    unmatched status; never guesses the nearest transition.
    """
    url = f"{_jira_issue_url(config, issue_key)}/transitions"
    get_headers = dict(resolve_headers(credential, url))
    get_headers["Accept"] = "application/json"
    get_request = urllib.request.Request(url, headers=get_headers, method="GET")

    get_response = transport(get_request)
    if get_response.status >= 400:
        raise SyncAPIError(
            f"Jira list transitions for {issue_key}: HTTP {get_response.status}: "
            f"{get_response.body[:500]!r}"
        )
    try:
        transitions = json.loads(get_response.body)["transitions"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise SyncAPIError(f"Jira list transitions for {issue_key}: malformed response") from exc
    if not isinstance(transitions, list):
        raise SyncAPIError(f"Jira list transitions for {issue_key}: 'transitions' is not a list")

    matched_id = None
    for transition in transitions:
        entry = transition if isinstance(transition, dict) else {}
        if (entry.get("to") or {}).get("name") == target_status:
            matched_id = entry.get("id")
            break
    if matched_id is None:
        raise SyncAPIError(
            f"Jira issue {issue_key}: no transition to status {target_status!r} -- the "
            "target API rejects the pushed value"
        )

    post_headers = dict(resolve_headers(credential, url))
    post_headers["Content-Type"] = "application/json"
    post_body = json.dumps({"transition": {"id": matched_id}}).encode("utf-8")
    post_request = urllib.request.Request(url, data=post_body, headers=post_headers, method="POST")

    post_response = transport(post_request)
    if post_response.status >= 300:
        raise SyncAPIError(
            f"Jira transition {issue_key} to {target_status!r}: HTTP {post_response.status}: "
            f"{post_response.body[:500]!r}"
        )


# ── The reconcile core ──────────────────────────────────────────────────────


def _validate_jira_project(issue_key: str, config: SyncConfig) -> None:
    """Reject a Jira issue key that doesn't belong to the configured
    project (`PROJECT-123` -> prefix `PROJECT`).

    `jira_project_key` is a required config field, but before this check
    nothing ever consulted it -- a `--jira-issue`/link value for an
    unrelated project would be read and processed with no rejection.
    Applied to every jira_issue_key this module resolves, whether given
    directly or reached via the GitHub side's link field.
    """
    prefix = issue_key.split("-", 1)[0]
    if prefix != config.jira_project_key:
        raise SyncUnlinkedError(
            f"jira issue {issue_key!r} does not belong to configured project "
            f"{config.jira_project_key!r} (prefix {prefix!r})"
        )


def _read_both_sides(
    *,
    github_item_id: str | None,
    jira_issue_key: str | None,
    config: SyncConfig,
    github_credential: HostScopedCredential,
    jira_credential: HostScopedCredential,
    transport: TransportFn,
) -> tuple[GitHubItemState, JiraIssueState]:
    """Resolve whichever identifier wasn't given via the other side's link
    field, then read both.

    Every identifier check is by truthiness, not `is None` -- an empty
    string given for one identifier must be treated exactly like "not
    given", never leave `gh`/`jira` unset before dereferencing them (the
    class of bug an inconsistent `is None`/truthiness mix produces).

    Raises `SyncUnlinkedError` naming whichever side has no link value --
    covers both the "resolve via the other side's link" path AND the
    both-identifiers-given path (a linked pair might still each carry an
    empty link field independently) -- and also raises it when both sides
    DO carry a link value but they don't reciprocally point at each other
    (a mismatched pair silently treated as linked would otherwise
    cross-propagate status to the wrong item).
    """
    if github_item_id and jira_issue_key:
        _validate_jira_project(jira_issue_key, config)
        gh = get_project_item(github_item_id, config=config, credential=github_credential, transport=transport)
        jira = get_jira_issue(jira_issue_key, config=config, credential=jira_credential, transport=transport)
    elif github_item_id:
        gh = get_project_item(github_item_id, config=config, credential=github_credential, transport=transport)
        if not gh.link:
            raise SyncUnlinkedError(f"unlinked: github item {github_item_id} has no linked jira issue")
        _validate_jira_project(gh.link, config)
        jira = get_jira_issue(gh.link, config=config, credential=jira_credential, transport=transport)
    elif jira_issue_key:
        _validate_jira_project(jira_issue_key, config)
        jira = get_jira_issue(jira_issue_key, config=config, credential=jira_credential, transport=transport)
        if not jira.link:
            raise SyncUnlinkedError(f"unlinked: jira issue {jira_issue_key} has no linked github item")
        gh = get_project_item(jira.link, config=config, credential=github_credential, transport=transport)
    else:
        raise ValueError("_read_both_sides requires github_item_id and/or jira_issue_key")

    if not gh.link:
        raise SyncUnlinkedError(f"unlinked: github item {gh.item_id} has no linked jira issue")
    if not jira.link:
        raise SyncUnlinkedError(f"unlinked: jira issue {jira.issue_key} has no linked github item")
    if gh.link != jira.issue_key or jira.link != gh.item_id:
        raise SyncUnlinkedError(
            f"mismatched link: github item {gh.item_id} points to jira {gh.link!r}, but "
            f"jira issue {jira.issue_key} points to github {jira.link!r} -- not a reciprocal pair"
        )
    return gh, jira


def reconcile(
    *,
    github_item_id: str | None = None,
    jira_issue_key: str | None = None,
    config: SyncConfig,
    dry_run: bool = False,
    transport: TransportFn | None = None,
) -> DutyResult:
    """Re-read both linked items' current state and converge the divergent
    side. See this module's own docstring and the story's Design Notes
    ("Reconcile algorithm") for the full rationale -- re-derived here
    verbatim, not from first principles.
    """
    transport = transport or _default_transport

    if not github_item_id and not jira_issue_key:
        return DutyResult(
            ok=False, summary="sync reconcile: one of --github-item/--jira-issue is required"
        )

    github_credential = HostScopedCredential(hosts=(_GITHUB_API_HOST,))
    jira_host = urlparse(config.jira_base_url).hostname
    if not jira_host:
        return DutyResult(
            ok=False,
            summary=f"sync reconcile: jira_base_url {config.jira_base_url!r} has no hostname",
        )
    jira_credential = HostScopedCredential(hosts=(jira_host,))

    try:
        gh, jira = _read_both_sides(
            github_item_id=github_item_id,
            jira_issue_key=jira_issue_key,
            config=config,
            github_credential=github_credential,
            jira_credential=jira_credential,
            transport=transport,
        )
    except SyncError as exc:
        return DutyResult(ok=False, summary=f"sync reconcile: {exc}")

    # AD-5: an item is a loop candidate when its own updated_at is NOT newer
    # than its own recorded sync point. Absent sync_point => NOT stale --
    # nothing recorded yet can never prove loop candidacy.
    gh_stale = gh.sync_point is not None and gh.updated_at <= gh.sync_point
    jira_stale = jira.sync_point is not None and jira.updated_at <= jira.sync_point

    if gh_stale and jira_stale:
        decision = "no_op"
        target_value: str | None = None
    elif not gh_stale and jira_stale:
        decision = "push_to_jira"
        target_value = gh.status
    elif gh_stale and not jira_stale:
        decision = "push_to_github"
        target_value = jira.status
    else:
        # Real conflict: both changed since their own sync point. AD-4 --
        # GitHub wins unless field_overrides says otherwise; a pure function
        # of (github_value, jira_value, field_mapping), never wall-clock.
        if config.field_overrides.get("status") == "jira":
            decision = "push_to_github"
            target_value = jira.status
        else:
            decision = "push_to_jira"
            target_value = gh.status

    # (1) Value-equality short-circuit -- MUST run before dry_run/no-op
    # reporting, not just before the real write (see this module's
    # docstring / the story's Design Notes for the full rationale: this is
    # what makes AD-5's item-level staleness check safe against an
    # unrelated field edit, and is the structural loop-breaker of last
    # resort).
    if decision != "no_op":
        current_dest_value = jira.status if decision == "push_to_jira" else gh.status
        if target_value == current_dest_value:
            decision = "no_op"

    details: dict[str, object] = {
        "decision": decision,
        "github_item_id": gh.item_id,
        "jira_issue_key": jira.issue_key,
        "target_value": target_value,
    }

    if dry_run or decision == "no_op":
        return DutyResult(
            ok=True,
            summary=f"sync reconcile: {decision} (github={gh.item_id}, jira={jira.issue_key}, dry_run={dry_run})",
            details=details,
        )

    try:
        if decision == "push_to_jira":
            transition_jira_issue(
                jira.issue_key, target_value, config=config, credential=jira_credential, transport=transport
            )
        else:
            update_project_item_field(
                gh.item_id,
                config.github_status_field_id,
                target_value,
                config=config,
                credential=github_credential,
                transport=transport,
            )
    except SyncError as exc:
        return DutyResult(ok=False, summary=f"sync reconcile: {exc}")

    # (2) Capture the sync-point timestamp AFTER the write above completes --
    # NEVER before any write, and never once up front for reuse across all
    # writes (see this module's docstring / the story's Design Notes).
    new_sync_point = datetime.now(timezone.utc).isoformat()

    try:
        update_project_item_field(
            gh.item_id,
            config.github_sync_point_field_id,
            new_sync_point,
            config=config,
            credential=github_credential,
            transport=transport,
        )
        update_jira_issue_fields(
            jira.issue_key,
            {config.jira_sync_point_field_id: new_sync_point},
            config=config,
            credential=jira_credential,
            transport=transport,
        )
    except SyncError as exc:
        # Known, accepted non-atomicity (same risk class as
        # keys.rotate_identity's documented partial-completion state): the
        # tracked-field write above already succeeded; only the sync-point
        # refresh failed. Reported here rather than rolled back.
        return DutyResult(
            ok=False,
            summary=f"sync reconcile: pushed {decision} but failed refreshing sync points: {exc}",
        )

    details["sync_point"] = new_sync_point
    return DutyResult(
        ok=True,
        summary=(
            f"sync reconcile: {decision} -> {target_value!r} "
            f"(github={gh.item_id}, jira={jira.issue_key}); sync points refreshed to {new_sync_point}"
        ),
        details=details,
    )


# ── SyncDuty (Duty-protocol adapter) ────────────────────────────────────────

_SYNC_VERBS: tuple[str, ...] = ("reconcile",)


class SyncDuty:
    """The real `sync` duty -- dispatches `reconcile`, the only verb this
    story defines.

    Bare `steward sync` (no verb) degrades to `DutyResult(ok=True, ...)`
    naming the available verbs (AD-7), matching every other duty's identical
    precedent. A malformed `.steward/sync-config.yaml` is caught here as
    `SyncConfigError`; every GitHub/Jira API or link failure `reconcile`
    doesn't already fold into its own `DutyResult` -- and a transport-level
    failure that somehow slips past `_default_transport`'s own `URLError`
    handling -- is caught here too. Both are reported as duty-level
    failures, never conflated with an internal crash (AD-8 -- that boundary
    is `cli.main()`'s alone).
    """

    name = "sync"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "sync_verb", None)
        if verb not in _SYNC_VERBS:
            return DutyResult(ok=True, summary=f"sync: available verbs are {', '.join(_SYNC_VERBS)}")

        config_path = getattr(ns, "config", None) or default_config_path()
        try:
            config = load_config(config_path)
        except SyncConfigError as exc:
            return DutyResult(ok=False, summary=f"sync {verb}: {exc}")

        try:
            return reconcile(
                github_item_id=getattr(ns, "github_item", None),
                jira_issue_key=getattr(ns, "jira_issue", None),
                config=config,
                dry_run=getattr(ns, "dry_run", False),
            )
        except (OSError, urllib.error.URLError) as exc:
            return DutyResult(ok=False, summary=f"sync {verb}: network error: {exc}")
