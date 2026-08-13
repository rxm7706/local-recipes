"""Steward's `sync` duty-adapter module (Epic 8, Story 8.1) — "one module per
duty", mirrors `keys.py`/`deploy.py`/`budget.py`'s own precedent.

Story 8.1 slice: the whole `sync` duty in one pass — `SyncConfig`/
`SyncConfigError`/`load_config` (the non-secret, operator-declared mapping of
GitHub project/field IDs, Jira base URL/project key/field IDs,
`field_overrides`, `user_mapping`, and (Story 8.6) `status_mapping` that makes
the engine board-agnostic), a
GitHub GraphQL client and a Jira REST v3 client built on an injectable
`transport` seam (a real `urlopen`-backed one by default, wrapping
`.claude/skills/conda-forge-expert/scripts/_http.py`'s `open_url` — never a
live network call from a test), and `reconcile` — the event-triggered
reconciliation core (ARCHITECTURE-SPINE.md's Design Paradigm): a webhook or
schedule tick is only ever a wake-up, never a value source. Every call
re-reads both linked items' current state and asks, per side, whether its
current tracked-field value differs from the **baseline** value that side was
last synced to — a per-field map of last-synced values, never a timestamp
(AD-5 amended, AD-10). Neither side differs from its own baseline → no-op.
Exactly one differs → propagate it. Both differ → a genuine conflict, and
GitHub wins unless `field_overrides` says otherwise (AD-4). Control-plane
state — the entity link and the per-field baseline map — lives only as
configured fields on the items themselves; there is no sidecar store of any
kind (AD-2).

Every outbound request's auth goes through `keys.HostScopedCredential`/
`resolve_headers` → `_http.py`'s `auth_headers_for` (AD-8) — this module
never builds its own credential/header logic. `SyncDuty` is the
`Duty`-conforming adapter `cli.py`'s `resolve_duty("sync")` now returns,
wiring `steward sync reconcile (--github-item ID | --jira-issue KEY |
--schedule) [--config PATH] [--dry-run]` -- `--schedule` (Story 8.4)
bulk-enumerates every linked item on the board and dispatches each through
the same single-pair `reconcile` in one run (AD-1's default `trigger=
schedule` operating mode).

See ARCHITECTURE-SPINE.md's AD-5 (amended) and AD-10, and this story's own
spec Design Notes ("Reconcile algorithm"), for the baseline-value mechanism
`reconcile` implements verbatim: an absent baseline key means "never synced"
(a first link, not a loop candidate); a present key holding `None` means "was
synced, and was an explicit clear" — the two must never be collapsed. A
serialized baseline map that would exceed the configured field's size ceiling
is a named failure pointing at Mode B (AD-2/AD-10's documented escape hatch),
never a sidecar store.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
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
    "project_id", "status_field_id", "link_field_id", "baseline_field_id",
)
_REQUIRED_JIRA_FIELDS: tuple[str, ...] = (
    "base_url", "project_key", "link_field_id", "baseline_field_id",
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
    github_baseline_field_id: str
    jira_base_url: str
    jira_project_key: str
    jira_link_field_id: str
    jira_baseline_field_id: str
    field_overrides: dict[str, str] = field(default_factory=dict)
    user_mapping: dict[str, str] = field(default_factory=dict)
    status_mapping: dict[str, str] = field(default_factory=dict)


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

    status_mapping = document.get("status_mapping") or {}
    if not isinstance(status_mapping, dict):
        raise SyncConfigError(f"{document_path}: 'status_mapping' must be a mapping")
    for jira_status, github_status in status_mapping.items():
        # Type safety only -- never vocabulary validation (no closed set of
        # valid status names exists to check against). Without this, a YAML
        # gotcha (`Done: yes` -> `True`, `Done:` -> `None`) loads silently
        # and only surfaces as a malformed GitHub GraphQL write instead of a
        # named config-time `SyncConfigError`.
        if not isinstance(jira_status, str) or not isinstance(github_status, str):
            raise SyncConfigError(
                f"{document_path}: 'status_mapping' keys and values must be strings "
                f"(got {jira_status!r}: {github_status!r})"
            )

    return SyncConfig(
        github_project_id=github_values["project_id"],
        github_status_field_id=github_values["status_field_id"],
        github_link_field_id=github_values["link_field_id"],
        github_baseline_field_id=github_values["baseline_field_id"],
        jira_base_url=jira_values["base_url"],
        jira_project_key=jira_values["project_key"],
        jira_link_field_id=jira_values["link_field_id"],
        jira_baseline_field_id=jira_values["baseline_field_id"],
        field_overrides=dict(field_overrides),
        user_mapping=dict(user_mapping),
        status_mapping=dict(status_mapping),
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


class SyncUnmappedStatusError(SyncError):
    """A non-null status value crossing into GitHub has no `status_mapping`
    entry."""


class SyncBaselineTooLargeError(SyncError):
    """A serialized baseline map would not fit the configured field's
    size ceiling (AD-2/AD-10's documented escape hatch to Mode B) --
    never a licence to fall back to a sidecar store."""


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


# ── Baseline handling (AD-5 amended / AD-10's loop guard compares these) ───

# GitHub Projects V2 text fields have no publicly documented character ceiling (verified by
# web search against GitHub's own GraphQL reference and community discussions, 2026-08-10:
# none exists). Conservative, explicitly unverified placeholder -- re-verify against a live
# board before relying on it.
_GITHUB_BASELINE_FIELD_CEILING = 1024

# Jira Cloud's "Text Field (single line)" custom field type is hard-capped at 255 characters
# at the database level (well-documented, e.g. JRASERVER-42470) -- a write past this limit is
# silently rejected by Jira's own REST API, so this module must catch it first.
_JIRA_BASELINE_FIELD_CEILING = 255


def _parse_baseline(raw: object, *, side: str, identifier: str) -> dict[str, object]:
    """Parse a side's baseline field into its per-field last-synced-value
    map (AD-10). `None` or an empty string (the field has never been
    written) means "never synced" for every field: returns `{}`, never
    raises.

    Deliberately narrower than a bare truthiness check: a baseline field
    genuinely misconfigured to point at a non-text field (e.g. a Jira
    Number/Checkbox field returning `0`/`false`) must not be silently
    swallowed as "never synced" -- it falls through to the JSON parse
    below, which raises a named, loud `SyncAPIError` instead.

    A non-empty value that isn't valid JSON, or that parses to something
    other than a JSON object, is a named `SyncAPIError` -- never a raw
    `json.JSONDecodeError`/`AttributeError` escaping to a caller.
    """
    if raw is None or raw == "":
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SyncAPIError(f"{side} {identifier}: malformed baseline field (not JSON): {exc}") from exc
    if not isinstance(parsed, dict):
        raise SyncAPIError(f"{side} {identifier}: baseline field is not a JSON object")
    return parsed


def _serialize_baseline(baseline: dict[str, object], *, side: str, ceiling: int) -> str:
    """Serialize a baseline map deterministically (`sort_keys` -- stable
    across writes/tests) and enforce the vendor's field-size ceiling before
    either baseline field write is attempted (AD-2/AD-10's documented escape
    hatch to Mode B). Note this only gates the two baseline writes -- by the
    time this runs, the cross-system tracked-value write (the Jira
    transition or GitHub field update) has, in the general case, already
    completed; see `reconcile`'s own accepted-non-atomicity comment.
    """
    text = json.dumps(baseline, sort_keys=True, separators=(",", ":"))
    if len(text) > ceiling:
        raise SyncBaselineTooLargeError(
            f"{side} baseline ({len(text)} chars) exceeds the {ceiling}-char field ceiling -- "
            "see AD-2/AD-10: the documented escape hatch is Mode B, never a sidecar store"
        )
    return text


# ── GitHub Projects V2 (GraphQL) client ─────────────────────────────────────

_GET_PROJECT_ITEM_QUERY = """
query($itemId: ID!) {
  node(id: $itemId) {
    ... on ProjectV2Item {
      id
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

# Story 8.4: `trigger=schedule` (AD-1, the architecture's default operating
# mode) candidate-enumeration query -- ONE paginated GraphQL query over the
# whole board, never one call per item. `ProjectV2.items(first, after)` is
# GitHub's standard Relay-style connection; the caller follows
# `pageInfo.hasNextPage`/`endCursor` until exhausted (see
# `list_linked_github_items`).
_LIST_PROJECT_ITEMS_QUERY = """
query($projectId: ID!, $after: String) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first: 100, after: $after) {
        nodes {
          id
          updatedAt
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
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
    baseline: dict[str, object]


def _parse_field_values(node: dict[str, object]) -> dict[str, str]:
    """Parse a `ProjectV2Item` node's `fieldValues.nodes` connection into a
    flat `{field_id: text}` map.

    Every field is read as `ProjectV2ItemFieldTextValue` -- this story's
    tracked/link/baseline GitHub fields are plain TEXT fields, never
    GitHub's native single-select Status field (there is no
    select-option-ID resolution anywhere in this module; the raw string
    value is propagated 1:1, matching the Boundaries & Constraints' "Never
    build a general status-vocabulary translation table").

    Factored out of `get_project_item`'s own inline loop (Story 8.4). No
    longer called by `list_linked_github_items` (Story 8.5) -- that
    function's bulk listing no longer reads any field value, only `id`/
    `updatedAt` per node.
    """
    field_values: dict[str, str] = {}
    for entry in ((node.get("fieldValues") or {}).get("nodes") or []):
        field_id = ((entry or {}).get("field") or {}).get("id")
        text = (entry or {}).get("text")
        if field_id is not None and text is not None:
            field_values[field_id] = text
    return field_values


def get_project_item(
    item_id: str, *, config: SyncConfig, credential: HostScopedCredential, transport: TransportFn
) -> GitHubItemState:
    """Read a GitHub Projects V2 item's tracked status, link, and baseline
    field values.

    Raises `SyncAPIError` for a missing/malformed `data.node` -- never a raw
    `KeyError` escaping to `cli.main()`'s crash boundary.
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

    field_values = _parse_field_values(node)

    baseline_raw = field_values.get(config.github_baseline_field_id)
    return GitHubItemState(
        item_id=item_id,
        link=field_values.get(config.github_link_field_id),
        status=field_values.get(config.github_status_field_id),
        baseline=_parse_baseline(baseline_raw, side="github item", identifier=item_id),
    )


def list_linked_github_items(
    *, config: SyncConfig, credential: HostScopedCredential, transport: TransportFn
) -> list[dict[str, object]]:
    """Bulk, paginated candidate discovery for `trigger=schedule` (AD-1) --
    enumerates EVERY item on the configured GitHub Projects V2 board, via
    ONE new paginated GraphQL query (`_LIST_PROJECT_ITEMS_QUERY`), never one
    call per item. Follows `pageInfo.hasNextPage`/`endCursor` until
    exhausted.

    A candidate is every deduplicated node the bulk listing returns --
    candidacy is never gated on the link field (or any other field value);
    only `id`/`updatedAt` are read per node. An item with no linked Jira
    issue is still a candidate here, and is dispatched through `reconcile()`
    like any other -- `reconcile()`'s own `_read_both_sides` re-reads the
    item fresh and raises `SyncUnlinkedError` (Story 8.5, CAP-4 "fail loud,
    fail alone") the moment it finds no link, which `reconcile_schedule_batch`
    folds into that candidate's own failed entry without aborting the rest
    of the batch. Candidacy is likewise never gated on the baseline (AD-10
    rule 1: an absent baseline is a first link, not a loop candidate, and is
    still reconciled) -- the baseline is never even read here. `updated_at`
    is fetched and returned per candidate for observability only --
    deliberately never used to filter candidacy: a Jira-only-originated
    change never touches GitHub's `updatedAt`, and AD-5 treats a false
    negative ("silently drops a change") as strictly worse than a false
    positive ("one wasted read, converges to no_op"). See this story's
    Design Notes for the full rationale.

    Raises `SyncAPIError` for a missing/malformed `data.node.items` shape
    (including `nodes`/`pageInfo` present but not list-/dict-shaped), a
    null or malformed entry inside `items.nodes`, or a non-advancing
    pagination cursor -- never a raw `KeyError`/`TypeError`/`AttributeError`
    escaping to the caller, and never an infinite loop against a malformed
    `pageInfo`. Mirrors `transition_jira_issue`'s own
    `isinstance(transitions, list)` + per-entry `isinstance(..., dict)`
    guard for the same class of "valid JSON, wrong shape" response.

    Candidates are deduplicated by `github_item_id` within one call -- GitHub's
    Relay-style pagination offers no guarantee against a repeated node if the
    underlying connection mutates between page fetches, and a duplicate would
    otherwise dispatch the same item twice in one batch.
    """
    candidates: list[dict[str, object]] = []
    seen_item_ids: set[str] = set()
    after: str | None = None
    while True:
        payload = github_graphql_request(
            _LIST_PROJECT_ITEMS_QUERY,
            {"projectId": config.github_project_id, "after": after},
            credential=credential,
            transport=transport,
        )
        try:
            items_conn = payload["data"]["node"]["items"]
            nodes = items_conn["nodes"]
            page_info = items_conn["pageInfo"]
            if not isinstance(nodes, list) or not isinstance(page_info, dict):
                raise TypeError
        except (KeyError, TypeError) as exc:
            raise SyncAPIError(
                f"GitHub project {config.github_project_id}: malformed response "
                "(missing data.node.items)"
            ) from exc

        for node in nodes:
            # A null or non-dict entry (e.g. a partial GraphQL error for one
            # node) is skipped, not fatal -- one bad node must not drop
            # every other candidate on the page, matching this story's own
            # "one item's failure never aborts the batch" spirit.
            if not isinstance(node, dict):
                continue
            item_id = node.get("id")
            if item_id is None or item_id in seen_item_ids:
                continue
            seen_item_ids.add(item_id)
            candidates.append({"github_item_id": item_id, "updated_at": node.get("updatedAt")})

        if not page_info.get("hasNextPage"):
            break
        next_after = page_info.get("endCursor")
        if next_after is None or next_after == after:
            # A vendor response claiming more pages exist but not advancing
            # the cursor -- treat as exhausted rather than loop forever.
            break
        after = next_after

    return candidates


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
    `item_id` (used for both the tracked status field and the baseline
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
    baseline: dict[str, object]


def get_jira_issue(
    issue_key: str, *, config: SyncConfig, credential: HostScopedCredential, transport: TransportFn
) -> JiraIssueState:
    """`GET /rest/api/3/issue/{key}` -- reads only the fields this module
    needs (`status`, the configured link/baseline custom fields), never the
    full issue payload.

    Raises `SyncAPIError` for a non-2xx status, malformed JSON, or a
    missing/malformed `fields` -- never a raw `KeyError`.
    """
    requested_fields = f"status,{config.jira_link_field_id},{config.jira_baseline_field_id}"
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
    fields = payload.get("fields") if isinstance(payload, dict) else None
    if not isinstance(fields, dict):
        raise SyncAPIError(f"Jira issue {issue_key}: malformed response (missing/malformed fields)")

    status_field = fields.get("status")
    status = status_field.get("name") if isinstance(status_field, dict) else None
    return JiraIssueState(
        issue_key=issue_key,
        link=fields.get(config.jira_link_field_id),
        status=status,
        baseline=_parse_baseline(
            fields.get(config.jira_baseline_field_id), side="jira issue", identifier=issue_key
        ),
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
    the baseline field write (status changes go through
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

# This story's one tracked field (matches field_overrides's own
# _VALID_OVERRIDE_FIELDS). _MISSING is a sentinel distinct from `None` -- see
# `reconcile`'s own comment for why the distinction matters (AD-10 rule 2).
_TRACKED_FIELD = "status"
_MISSING = object()


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

    # AD-5 (amended) / AD-10: a side has changed when its current
    # tracked-field value differs from the value its OWN baseline map
    # records for that field. `_MISSING` is a sentinel distinct from `None`
    # -- an absent key means "never synced" (AD-10 rule 1: not a loop
    # candidate, reconcile as a first link); a present key holding `None`
    # means "synced, and was an explicit clear" (AD-10 rule 2). Collapsing
    # those two would make a deliberate clear indistinguishable from a field
    # the engine has never seen -- exactly the trap AD-10 exists to name.
    gh_base = gh.baseline.get(_TRACKED_FIELD, _MISSING)
    jira_base = jira.baseline.get(_TRACKED_FIELD, _MISSING)
    gh_changed = gh_base is _MISSING or gh.status != gh_base
    jira_changed = jira_base is _MISSING or jira.status != jira_base

    if not gh_changed and not jira_changed:
        # True no-op: neither side diverged from its own baseline -- zero
        # writes, baseline left untouched. This is the zero-loop property,
        # and it holds regardless of when reconcile runs. `details` keeps
        # the same shape every other return path uses (including "baseline",
        # here None since it was never touched) so a caller can read
        # `details["baseline"]` unconditionally without a KeyError.
        return DutyResult(
            ok=True,
            summary=f"sync reconcile: no_op (github={gh.item_id}, jira={jira.issue_key}, dry_run={dry_run})",
            details={
                "decision": "no_op",
                "github_item_id": gh.item_id,
                "jira_issue_key": jira.issue_key,
                "target_value": None,
                "baseline": None,
            },
        )

    if gh_changed and not jira_changed:
        decision, target_value = "push_to_jira", gh.status
    elif jira_changed and not gh_changed:
        decision, target_value = "push_to_github", jira.status
    else:
        # Both changed -> AD-4 conflict authority. GitHub wins unless
        # field_overrides says otherwise; a pure function of
        # (github_value, jira_value, field_mapping), never wall-clock.
        if config.field_overrides.get(_TRACKED_FIELD) == "jira":
            decision, target_value = "push_to_github", jira.status
        else:
            decision, target_value = "push_to_jira", gh.status

    # Convergence check -- still required, now for a narrower reason than
    # the mechanism it replaces. Two sides can independently change to the
    # SAME new value (both diverge from their own stale baseline, but agree
    # with each other); this catches "the destination already holds
    # target_value" and downgrades to no_op. It is NOT the early return
    # above -- the baseline still needs refreshing below, since both sides
    # were still stale relative to their own prior baseline.
    current_dest_value = jira.status if decision == "push_to_jira" else gh.status
    if target_value == current_dest_value:
        decision = "no_op"

    # "baseline" defaults to None (overwritten below once actually written)
    # so every return path from here on shares one consistent details shape.
    details: dict[str, object] = {
        "decision": decision,
        "github_item_id": gh.item_id,
        "jira_issue_key": jira.issue_key,
        "target_value": target_value,
        "baseline": None,
    }

    if dry_run:
        return DutyResult(
            ok=True,
            summary=f"sync reconcile: {decision} (github={gh.item_id}, jira={jira.issue_key}, dry_run=True)",
            details=details,
        )

    # `github_write_value` defaults to `target_value` unchanged -- the
    # `push_to_jira` and no_op paths never assign it, so they keep writing
    # exactly what they write today. Only the `push_to_github` branch below
    # translates it (AD-6/CAP-5: every status value crossing into GitHub
    # passes through `status_mapping`; an unmapped value is a hard, named
    # failure, never passed through).
    github_write_value = target_value
    if decision != "no_op":
        try:
            if decision == "push_to_jira":
                transition_jira_issue(
                    jira.issue_key, target_value, config=config, credential=jira_credential, transport=transport
                )
            else:  # push_to_github
                if target_value is None:
                    # An explicit clear is not a status word to translate
                    # (AD-10: an absent baseline key and an explicit null
                    # mean opposite things) -- bypasses the mapping lookup.
                    github_write_value = None
                else:
                    mapped = config.status_mapping.get(target_value)
                    if mapped is None:
                        raise SyncUnmappedStatusError(
                            f"unmapped: jira status {target_value!r} has no status_mapping "
                            "entry for github"
                        )
                    github_write_value = mapped
                update_project_item_field(
                    gh.item_id,
                    config.github_status_field_id,
                    github_write_value,
                    config=config,
                    credential=github_credential,
                    transport=transport,
                )
        except SyncError as exc:
            return DutyResult(ok=False, summary=f"sync reconcile: {exc}")

    # Baseline refresh -- ALWAYS runs from here on (both the "converged
    # already" no_op path and the real-push path reach this), because at
    # least one side diverged from ITS OWN prior baseline and every future
    # reconcile of this pair would otherwise see it as "changed" forever.
    # The GitHub-side baseline records the TRANSLATED (actually-written)
    # value -- `github_write_value`, never the raw `target_value` -- or the
    # next reconcile's `gh.status != gh_base` comparison would permanently
    # mismatch (a zero-loop regression, AD-5). The Jira-side baseline stays
    # keyed on `target_value`: Jira's own value did not change.
    try:
        new_gh_baseline = _serialize_baseline(
            {**gh.baseline, _TRACKED_FIELD: github_write_value},
            side="github",
            ceiling=_GITHUB_BASELINE_FIELD_CEILING,
        )
        new_jira_baseline = _serialize_baseline(
            {**jira.baseline, _TRACKED_FIELD: target_value},
            side="jira",
            ceiling=_JIRA_BASELINE_FIELD_CEILING,
        )
        update_project_item_field(
            gh.item_id,
            config.github_baseline_field_id,
            new_gh_baseline,
            config=config,
            credential=github_credential,
            transport=transport,
        )
        update_jira_issue_fields(
            jira.issue_key,
            {config.jira_baseline_field_id: new_jira_baseline},
            config=config,
            credential=jira_credential,
            transport=transport,
        )
    except SyncError as exc:
        # Known, accepted non-atomicity (same risk class as
        # keys.rotate_identity's documented partial-completion state): the
        # tracked-field write above already succeeded (if decision != no_op);
        # only the baseline refresh failed. Reported here rather than rolled
        # back.
        return DutyResult(
            ok=False,
            summary=f"sync reconcile: {decision} but failed refreshing baseline: {exc}",
        )

    details["baseline"] = {_TRACKED_FIELD: target_value}
    return DutyResult(
        ok=True,
        summary=(
            f"sync reconcile: {decision} -> {target_value!r} "
            f"(github={gh.item_id}, jira={jira.issue_key}); baseline refreshed"
        ),
        details=details,
    )


def reconcile_schedule_batch(
    *, config: SyncConfig, dry_run: bool = False, transport: TransportFn | None = None
) -> DutyResult:
    """`trigger=schedule` (AD-1, the architecture's default operating mode):
    bulk-enumerate every linked item on the GitHub Projects V2 board via
    `list_linked_github_items`, then dispatch each candidate through the
    existing, UNCHANGED single-pair `reconcile()` one at a time, aggregating
    into ONE `DutyResult` (mirrors `reconcile()`'s own `details` convention
    -- `SyncDuty.run()` calls this instead of `reconcile` when `--schedule`
    is given).

    Each candidate's `reconcile(...)` call is wrapped the same way
    `SyncDuty.run()` already wraps its own single-pair call (`except
    (OSError, urllib.error.URLError)`), so one candidate's raw transport
    failure cannot abort the rest of the batch -- it is folded into that
    candidate's own failed entry instead. Overall `ok` is `True` only if
    every candidate's own result was `ok`.

    This story never builds Jira-side (JQL) candidate discovery (GitHub is
    the authoritative board per AD-4, and `reconcile()` already re-reads
    BOTH sides fresh regardless of entry identifier). The "named, greppable
    error for the broken item" refinement (FR-30 / Story 8.5, CAP-4 "fail
    loud, fail alone") is closed by `list_linked_github_items` making every
    board item a candidate -- an unlinked candidate's `reconcile()` call
    raises `SyncUnlinkedError`, which `reconcile()` already catches (as any
    other `SyncError`) and turns into an `ok=False` `DutyResult`, folded here
    into that candidate's own failed entry exactly like any other failure,
    without aborting the rest of the batch.
    """
    transport = transport or _default_transport
    github_credential = HostScopedCredential(hosts=(_GITHUB_API_HOST,))

    try:
        candidates = list_linked_github_items(
            config=config, credential=github_credential, transport=transport
        )
    except (SyncError, OSError, urllib.error.URLError) as exc:
        return DutyResult(
            ok=False,
            summary=f"sync reconcile --schedule: failed enumerating candidates: {exc}",
        )

    entries: list[dict[str, object]] = []
    for candidate in candidates:
        github_item_id = candidate["github_item_id"]
        try:
            result = reconcile(
                github_item_id=github_item_id, config=config, dry_run=dry_run, transport=transport
            )
        except (OSError, urllib.error.URLError) as exc:
            result = DutyResult(ok=False, summary=f"sync reconcile: network error: {exc}")
        entries.append(
            {
                "github_item_id": github_item_id,
                "updated_at": candidate.get("updated_at"),
                "ok": result.ok,
                "summary": result.summary,
            }
        )

    failed = [entry for entry in entries if not entry["ok"]]
    ok_count = len(entries) - len(failed)
    candidate_word = "candidate" if len(entries) == 1 else "candidates"
    return DutyResult(
        ok=not failed,
        summary=(
            f"sync reconcile --schedule: {len(entries)} {candidate_word}, "
            f"{ok_count} ok, {len(failed)} failed"
        ),
        details={"candidates": entries},
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

    `--schedule` (Story 8.4, `trigger=schedule`, AD-1's default operating
    mode) dispatches to `reconcile_schedule_batch` instead of the
    single-pair `reconcile` -- everything else about this method (verb
    dispatch, config load, the network-error catch) is shared verbatim.
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
            if getattr(ns, "schedule", False):
                return reconcile_schedule_batch(config=config, dry_run=getattr(ns, "dry_run", False))
            return reconcile(
                github_item_id=getattr(ns, "github_item", None),
                jira_issue_key=getattr(ns, "jira_issue", None),
                config=config,
                dry_run=getattr(ns, "dry_run", False),
            )
        except (OSError, urllib.error.URLError) as exc:
            return DutyResult(ok=False, summary=f"sync {verb}: network error: {exc}")
