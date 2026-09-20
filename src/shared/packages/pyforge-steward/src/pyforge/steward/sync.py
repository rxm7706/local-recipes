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

# `keys.py`'s own import (above) already resolved and inserted `_http.py`'s
# directory onto `sys.path` (its `locate_http_module`/bridge walk-up) --
# reused here rather than repeating that walk-up search a second time.
from _http import open_url  # noqa: E402  — see the comment immediately above

from .interfaces import DutyResult
from .keys import HostScopedCredential, repo_root, resolve_headers

_GITHUB_API_HOST = "api.github.com"
_GITHUB_GRAPHQL_URL = f"https://{_GITHUB_API_HOST}/graphql"


# ── `.steward/sync-config.yaml` read (the non-secret, board-agnostic mapping) ──

_SYNC_CONFIG_RELATIVE_PATH = Path(".steward/sync-config.yaml")

_REQUIRED_GITHUB_FIELDS: tuple[str, ...] = (
    "project_id",
    "status_field_id",
    "link_field_id",
    "baseline_field_id",
)
_REQUIRED_JIRA_FIELDS: tuple[str, ...] = (
    "base_url",
    "project_key",
    "link_field_id",
    "baseline_field_id",
)

# The only field_overrides value this story recognizes -- overriding AD-4's
# default GitHub-wins authority for one field. "github" is deliberately not
# accepted: it is already the default, and accepting it as a no-op value
# would let a typo (any string that isn't "jira") silently pass validation
# while still reverting to default authority.
_VALID_OVERRIDE_AUTHORITY = "jira"

# The only field names `reconcile` actually consults an override for. An
# unrecognized key (e.g. a typo'd "statuz") must fail loud too -- otherwise
# it loads successfully and is silently ignored, which is exactly the
# "typo must fail loud" property this module already enforces for the
# authority value but not, before this check, for the key. Story 8.7 adds
# "assignee" -- it follows status's exact decision shape (AD-4 conflict
# authority), so it is a valid override target too.
_VALID_OVERRIDE_FIELDS: tuple[str, ...] = ("status", "assignee")


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


def _require_section(document_path: Path, section: object, section_name: str, keys_: tuple[str, ...]) -> dict[str, str]:
    if not isinstance(section, dict):
        raise SyncConfigError(f"{document_path}: {section_name!r} section missing or not a mapping")
    values: dict[str, str] = {}
    for key in keys_:
        value = section.get(key)
        if not isinstance(value, str) or not value.strip():
            raise SyncConfigError(f"{document_path}: '{section_name}.{key}' is required and must be a non-empty string")
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
        raise SyncConfigError(f"{document_path}: top-level document must be a mapping, got {type(document).__name__}")

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
    for github_login, jira_account_id in user_mapping.items():
        # Type safety only -- mirrors status_mapping's own check above (Story
        # 8.6 precedent). Story 8.7: user_mapping is consulted now (assignee
        # translation), so an unquoted-YAML-gotcha value (e.g. an accountId
        # that YAML parses as a number/bool) must fail loud at config-load
        # time, not surface later as a malformed GitHub/Jira write.
        if not isinstance(github_login, str) or not isinstance(jira_account_id, str):
            raise SyncConfigError(
                f"{document_path}: 'user_mapping' keys and values must be strings "
                f"(got {github_login!r}: {jira_account_id!r})"
            )
        # Non-empty, too (fix, review-confirmed): an empty translated value
        # is FALSY, and `update_github_assignees` skips the half of its
        # add/remove pair whose value is falsy. An empty mapping value
        # therefore silently skips the POST while the DELETE of the current
        # assignee still runs, leaving the item unassigned and recording
        # `""` as the converged baseline -- a silent loss, where a loud
        # config error at load time costs nothing.
        if not github_login.strip() or not jira_account_id.strip():
            raise SyncConfigError(
                f"{document_path}: 'user_mapping' keys and values must be non-empty "
                f"(got {github_login!r}: {jira_account_id!r})"
            )

    # Review-confirmed fix: Story 8.7 is what FIRST makes the computed
    # inverse (`{v: k for k, v in user_mapping.items()}`) load-bearing (push
    # to github translation) -- two different github logins accidentally
    # mapped to the same jira accountId (a plausible copy-paste mistake)
    # would otherwise silently collapse to whichever entry iterates last in
    # that inverse, with no load-time warning. Mirrors this module's own
    # "a typo/misconfiguration must fail loud" convention.
    value_counts: dict[str, int] = {}
    for jira_account_id in user_mapping.values():
        value_counts[jira_account_id] = value_counts.get(jira_account_id, 0) + 1
    duplicate_values = sorted(value for value, count in value_counts.items() if count > 1)
    if duplicate_values:
        raise SyncConfigError(
            f"{document_path}: 'user_mapping' has duplicate values (two github logins "
            f"mapped to the same jira accountId) -- {duplicate_values!r}"
        )

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


class SyncUnmappedUserError(SyncError):
    """A non-null assignee value crossing into GitHub or Jira has no
    `user_mapping` entry in the needed direction (mirrors
    `SyncUnmappedStatusError` exactly)."""


class SyncMultipleAssigneesError(SyncError):
    """A GitHub item's `content.assignees` carries more than one node --
    an untracked co-assignee exists (escalation, finding 4). Refused named
    rather than silently tracking only `assignees[0]`, which can leave the
    item with two assignees or silently revert a human's later Jira
    reassignment."""


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
        raise SyncAPIError(f"{request.get_method()} {request.full_url}: {exc.reason}") from exc


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

# Story 8.7: the `content` fragment reads the item's underlying Issue/PR --
# GitHub's assignee is native to the CONTENT, never a custom Projects V2
# field (Boundaries & Constraints). `content` is a `DraftIssue` (or absent)
# for a draft item -- neither branch below matches, so it parses as "no
# assignee, no content_ref" (a valid state, never an error; see
# `_parse_content`).
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
      content {
        ... on Issue {
          number
          assignees(first: 10) { nodes { login } }
          repository { owner { login } name }
        }
        ... on PullRequest {
          number
          assignees(first: 10) { nodes { login } }
          repository { owner { login } name }
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
        raise SyncAPIError(f"GitHub GraphQL request failed: HTTP {response.status}: {response.body[:500]!r}")
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
    this state; AD-9).

    `assignee` (Story 8.7) is the FIRST `content.assignees` login, or `None`
    if the content has no assignee, is a `DraftIssue`, or is absent --
    tracks only one assignee, never more; more than one raises
    `SyncMultipleAssigneesError` named rather than silently picking the
    first (Boundaries & Constraints, escalation finding 4). `content_ref`
    is `(owner, repo, number)` for a real Issue/PR, or `None` for a
    `DraftIssue`/absent content -- a write targeted at a `None` ref has
    nothing to address and must raise `SyncAPIError` naming the item, never
    guess a target. `assignee_unknown` (escalation, finding 3) is `True`
    when `content`/`content.assignees` could not be confidently parsed --
    distinct from a genuinely empty/`DraftIssue` `assignee=None` -- so the
    caller can downgrade to `no_op` instead of treating an unreadable read
    as an authoritative unassignment."""

    item_id: str
    link: str | None
    status: str | None
    baseline: dict[str, object]
    assignee: str | None = None
    content_ref: tuple[str, str, int] | None = None
    assignee_unknown: bool = False


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
    for entry in (node.get("fieldValues") or {}).get("nodes") or []:
        field_id = ((entry or {}).get("field") or {}).get("id")
        text = (entry or {}).get("text")
        if field_id is not None and text is not None:
            field_values[field_id] = text
    return field_values


def _parse_content(
    node: dict[str, object],
) -> tuple[str | None, tuple[str, str, int] | None, bool]:
    """Parse a `ProjectV2Item` node's `content` into `(assignee_login,
    content_ref, assignee_unknown)` (Story 8.7).

    `content` ABSENT from `node` entirely (no key at all -- every pre-8.7
    test fixture, and GitHub's actual shape for a `DraftIssue`, which has
    none of `number`/`repository`/`assignees`) reads as a CONFIDENT "no
    assignee": `(None, None, False)`.

    `content` present but explicit `None` (escalation, finding 3, resolved
    2026-08-15) is DISTINCT from "absent" -- a partial-response signature
    (a permission gap, e.g. a Projects-only token that cannot read a
    private repo's issue `content`, this story's own documented risk) --
    and reads as UNKNOWN, never a confident unassignment:
    `(None, None, True)`.

    Every nested shape is type-checked rather than assumed (fix,
    review-confirmed): this parses an externally-sourced response, and a
    partial/proxied/hostile one whose `repository` or `assignees` came back
    as a list or a string would otherwise raise a raw `AttributeError` out
    of `reconcile` -- escaping this module's named-error contract and, under
    `--schedule`, aborting the whole batch instead of failing one item.
    `number` is required to be a real `int` for the same reason plus one
    more: it is interpolated into the REST assignees URL as a path segment
    (`_github_issue_assignees_url` escapes `owner`/`repo` but cannot
    meaningfully escape an integer), so a string `number` would build a
    malformed or injected URL -- `content_ref` alone stays `None` for a
    malformed `number` without affecting `assignee`/`assignee_unknown`
    (the two are read independently).

    The `assignees` sub-shape specifically determines `assignee_unknown`
    (escalation, finding 3): a well-formed, confidently-empty
    `{"nodes": []}` (a real `DraftIssue` or a real Issue/PR with genuinely
    no assignee) is `(None, False)` -- but `assignees` missing/malformed,
    or its `nodes` not a list, or a node whose `login` isn't a string, is
    UNREADABLE, never a guessed `None` -- `(None, True)`. Exactly ONE
    well-formed node is the normal case. MORE than one raises
    `SyncMultipleAssigneesError` named (escalation, finding 4) rather than
    silently tracking only the first -- an untracked co-assignee is a
    named failure, never a guess.
    """
    content = node.get("content")
    if content is None:
        if "content" in node:
            return None, None, True
        return None, None, False
    if not isinstance(content, dict):
        return None, None, True
    number = content.get("number")
    repository = content.get("repository")
    if not isinstance(repository, dict):
        repository = {}
    owner_node = repository.get("owner")
    owner = owner_node.get("login") if isinstance(owner_node, dict) else None
    repo = repository.get("name")
    content_ref: tuple[str, str, int] | None = None
    if isinstance(owner, str) and isinstance(repo, str) and isinstance(number, int) and not isinstance(number, bool):
        content_ref = (owner, repo, number)
    assignees = content.get("assignees")
    if assignees is None:
        return None, content_ref, False
    if not isinstance(assignees, dict):
        return None, content_ref, True
    assignee_nodes = assignees.get("nodes")
    if not isinstance(assignee_nodes, list):
        return None, content_ref, True
    if not assignee_nodes:
        return None, content_ref, False
    if len(assignee_nodes) > 1:
        raise SyncMultipleAssigneesError(
            f"GitHub item has {len(assignee_nodes)} assignees, this module tracks exactly one: {assignee_nodes!r}"
        )
    first = assignee_nodes[0]
    login = first.get("login") if isinstance(first, dict) else None
    if isinstance(login, str):
        return login, content_ref, False
    return None, content_ref, True


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
        raise SyncAPIError(f"GitHub project item {item_id}: malformed response (missing data.node)") from exc
    if node is None:
        raise SyncAPIError(f"GitHub project item {item_id}: not found")

    field_values = _parse_field_values(node)
    assignee, content_ref, assignee_unknown = _parse_content(node)

    baseline_raw = field_values.get(config.github_baseline_field_id)
    return GitHubItemState(
        item_id=item_id,
        link=field_values.get(config.github_link_field_id),
        status=field_values.get(config.github_status_field_id),
        baseline=_parse_baseline(baseline_raw, side="github item", identifier=item_id),
        assignee=assignee,
        content_ref=content_ref,
        assignee_unknown=assignee_unknown,
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
                f"GitHub project {config.github_project_id}: malformed response (missing data.node.items)"
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
        raise SyncAPIError(f"GitHub update field {field_id} on item {item_id}: malformed response") from exc


def _github_issue_assignees_url(owner: str, repo: str, number: int) -> str:
    """`https://api.github.com/repos/{owner}/{repo}/issues/{number}/assignees`
    -- `owner`/`repo` are escaped, matching `_jira_issue_url`'s own
    "never trust an externally-sourced path segment" precedent."""
    return f"https://{_GITHUB_API_HOST}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/issues/{number}/assignees"


def update_github_assignees(
    owner: str,
    repo: str,
    number: int,
    *,
    add: str | None,
    remove: str | None,
    credential: HostScopedCredential,
    transport: TransportFn,
) -> None:
    """`POST`/`DELETE .../issues/{number}/assignees` -- write GitHub's
    assignee via REST, never GraphQL (Boundaries & Constraints: avoids a
    second login-to-node-ID resolution call).

    Removes ONLY `remove` (the previously-tracked login, from baseline) and
    adds ONLY `add` (the new one) -- never touches an assignee this module
    didn't itself add. Either may be `None`/falsy, in which case that half
    of the operation is simply skipped -- never an empty-body request. A 2xx
    status is success (this module accepts any status `< 300`, mirroring
    `update_jira_issue_fields`'s own status-check shape).

    ADD happens before REMOVE (never the reverse) -- a review-confirmed fix:
    DELETE-then-POST left a window where a POST failure after a successful
    DELETE would leave the GitHub item with ZERO assignees, strictly worse
    than either the old or new state. Worst case on a partial failure this
    way is briefly TWO assignees (old + new), which self-heals on the next
    reconcile -- safer than zero.

    `remove == add` is never issued (fix, review-confirmed): the caller
    passes GitHub's LIVE current assignee as `remove`, so a write whose
    target happens to already be assigned would otherwise POST that login
    and immediately DELETE it again, leaving the item unassigned -- the
    exact zero-assignee outcome the ADD-before-REMOVE ordering above exists
    to prevent. `reconcile`'s convergence check is what normally keeps such
    a write from being issued at all; this is the belt-and-braces guard at
    the only place that can actually cause the loss.
    """
    url = _github_issue_assignees_url(owner, repo, number)
    if add:
        headers = dict(resolve_headers(credential, url))
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/vnd.github+json"
        body = json.dumps({"assignees": [add]}).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        response = transport(request)
        if response.status >= 300:
            raise SyncAPIError(
                f"GitHub add assignee {add!r} on {owner}/{repo}#{number}: "
                f"HTTP {response.status}: {response.body[:500]!r}"
            )
    if remove and remove != add:
        headers = dict(resolve_headers(credential, url))
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/vnd.github+json"
        body = json.dumps({"assignees": [remove]}).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="DELETE")
        response = transport(request)
        if response.status >= 300:
            raise SyncAPIError(
                f"GitHub remove assignee {remove!r} on {owner}/{repo}#{number}: "
                f"HTTP {response.status}: {response.body[:500]!r}"
            )


# ── Jira Cloud (REST API v3) client ─────────────────────────────────────────


def _jira_issue_url(config: SyncConfig, issue_key: str) -> str:
    """`issue_key` is escaped -- it can originate from an external webhook
    payload (`--jira-issue` on the CLI), and is never trusted as a safe URL
    path segment."""
    return f"{config.jira_base_url.rstrip('/')}/rest/api/3/issue/{quote(issue_key, safe='')}"


@dataclass(frozen=True)
class JiraIssueState:
    """One Jira issue's current state, as read fresh (same
    reconcile-not-propagate rationale as `GitHubItemState`).

    `assignee` (Story 8.7) is `fields.assignee.accountId`, or `None` if
    unassigned."""

    issue_key: str
    link: str | None
    status: str | None
    baseline: dict[str, object]
    assignee: str | None = None


def get_jira_issue(
    issue_key: str, *, config: SyncConfig, credential: HostScopedCredential, transport: TransportFn
) -> JiraIssueState:
    """`GET /rest/api/3/issue/{key}` -- reads only the fields this module
    needs (`status`, the configured link/baseline custom fields), never the
    full issue payload.

    Raises `SyncAPIError` for a non-2xx status, malformed JSON, or a
    missing/malformed `fields` -- never a raw `KeyError`.
    """
    requested_fields = f"status,assignee,{config.jira_link_field_id},{config.jira_baseline_field_id}"
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
    assignee_field = fields.get("assignee")
    assignee = assignee_field.get("accountId") if isinstance(assignee_field, dict) else None
    return JiraIssueState(
        issue_key=issue_key,
        link=fields.get(config.jira_link_field_id),
        status=status,
        baseline=_parse_baseline(fields.get(config.jira_baseline_field_id), side="jira issue", identifier=issue_key),
        assignee=assignee,
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
        raise SyncAPIError(f"Jira update fields on {issue_key}: HTTP {response.status}: {response.body[:500]!r}")


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
            f"Jira list transitions for {issue_key}: HTTP {get_response.status}: {get_response.body[:500]!r}"
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

# This story's tracked fields (matches field_overrides's own
# _VALID_OVERRIDE_FIELDS). _MISSING is a sentinel distinct from `None` -- see
# `reconcile`'s own comment for why the distinction matters (AD-10 rule 2).
_TRACKED_FIELD = "status"
_ASSIGNEE_FIELD = "assignee"
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

    Raises `SyncUnlinkedError` naming whichever DRIVING side has no link
    value of its own -- there is nothing to resolve the pair from (the
    single-identifier paths below). Also raises it when both sides DO
    carry a non-empty link value but they don't reciprocally point at each
    other (a mismatched pair silently treated as linked would otherwise
    cross-propagate status to the wrong item) -- "not a reciprocal pair".

    Story 8.7: the ONE case this no longer hard-fails is "one side is
    already resolved (has a link value, or was given directly), the OTHER
    side's OWN link field reads empty" -- the literal AF-5 gap. That case
    (and the "both sides empty, both identifiers given directly" case) now
    returns the resolved `(gh, jira)` pair unchanged in shape; `reconcile`'s
    link-repair step writes whichever side doesn't already match, since
    both sides' correct values are always independently, statelessly
    derivable from the resolved pair itself (Design Notes).
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

    # Story 8.7: the "one/both side(s) empty" case is no longer a hard
    # failure here (see docstring) -- only a genuine, non-empty MISMATCH
    # still is. Each side is judged INDEPENDENTLY (fix, review-confirmed):
    # an empty link is never a mismatch (that is the now-relaxed AF-5
    # repair case, since an empty string trivially "differs" from a real
    # issue key/item id), but a NON-empty link that names something other
    # than its counterpart is still "not a reciprocal pair" even when the
    # OTHER side's link happens to be empty. Requiring BOTH sides to be
    # non-empty before checking either would let the both-identifiers-given
    # call silently overwrite an existing link: a GitHub item already
    # linked to a THIRD Jira issue, paired against a Jira issue whose own
    # link field is empty, would have its real link destroyed and status/
    # assignee cross-propagated between two items that were never a pair.
    if (gh.link and gh.link != jira.issue_key) or (jira.link and jira.link != gh.item_id):
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
        return DutyResult(ok=False, summary="sync reconcile: one of --github-item/--jira-issue is required")

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

    # Story 8.7 (Design Notes, "Why a missing baseline key IS a first-sync
    # decision, per field" -- revised 2026-08-15, escalation findings 1+2).
    # A missing `"assignee"` baseline key on EITHER side -- whether that
    # side's whole baseline map is empty (a genuinely new pair) or merely
    # missing this one key (an established pair predating this story) -- is
    # read as a real first-sync AD-4 decision for the assignee field alone,
    # exactly parallel to `status` above (`_MISSING` stays `_MISSING`, never
    # silently adopted). The prior design instead adopted a missing-key
    # side's OWN current value as its baseline without ever comparing it to
    # the other side: on a genuinely mismatched pre-8.7 pair this made
    # assignee sync permanently inert (nothing ever recorded the pair as
    # observed, so every tick re-derived the same "not yet observed" state
    # forever), and it let a LATER field's successful baseline persist
    # (e.g. status) silently make an EARLIER field's failed write look
    # "established" on the very next tick, masking the failure as
    # convergence. Deriving each field's own `_changed` flag strictly from
    # that field's own persisted baseline key (never from the pair's overall
    # baseline truthiness) closes both: a missing key always re-enters the
    # AD-4 decision below, so an already-converged pair produces zero writes
    # (the convergence check downgrades it) while a genuinely diverged pair
    # gets a real, one-time write -- and a failed write, having never
    # persisted its own key, is re-attempted on the next tick instead of
    # disappearing.
    gh_assignee_base = gh.baseline.get(_ASSIGNEE_FIELD, _MISSING)
    jira_assignee_base = jira.baseline.get(_ASSIGNEE_FIELD, _MISSING)
    gh_assignee_changed = gh_assignee_base is _MISSING or gh.assignee != gh_assignee_base
    jira_assignee_changed = jira_assignee_base is _MISSING or jira.assignee != jira_assignee_base
    # A missing key alone must not, by itself, trigger a baseline WRITE when
    # both sides genuinely agree (the AD-4 comparison above still runs and
    # correctly finds nothing to change) -- only a REAL push, or riding
    # along for free when status ALSO writes this round, should. Tracked
    # separately from `*_assignee_changed` (which must stay True to drive
    # the comparison) so `should_persist_assignee` below can distinguish
    # "key missing" from "value actually diverged."
    assignee_key_missing = gh_assignee_base is _MISSING or jira_assignee_base is _MISSING

    # Identity-link repair need (Boundaries & Constraints): stateless and
    # independently derivable from the resolved pair alone, no extra read
    # required. Never baselined, never routed through field_overrides/AD-4 --
    # see the module Design Notes for why this can't share status/assignee's
    # "which side wins" decision shape.
    link_repair_github = gh.link != jira.issue_key
    link_repair_jira = jira.link != gh.item_id

    if (
        not gh_changed
        and not jira_changed
        and not gh_assignee_changed
        and not jira_assignee_changed
        and not link_repair_github
        and not link_repair_jira
    ):
        # True no-op: neither tracked field diverged from its own baseline
        # on either side, AND both identity links already reciprocally
        # match -- zero writes, baseline left untouched. This is the
        # zero-loop property, and it holds regardless of when reconcile
        # runs. `details` keeps the same shape every other return path uses
        # so a caller can read any key unconditionally without a KeyError.
        return DutyResult(
            ok=True,
            summary=f"sync reconcile: no_op (github={gh.item_id}, jira={jira.issue_key}, dry_run={dry_run})",
            details={
                "decision": "no_op",
                "github_item_id": gh.item_id,
                "jira_issue_key": jira.issue_key,
                "target_value": None,
                "baseline": None,
                "assignee": {"decision": "no_op", "target_value": None, "written_value": None},
                "link_repairs": [],
            },
        )

    # -- Status decision -- explicitly guarded for "status itself didn't
    # change" (unreachable pre-8.7, since the fast path above always
    # short-circuited first whenever both status flags were False; now
    # reachable when only assignee or a link repair carries execution past
    # it) so a still-converged status can never be misread as a conflict.
    if not gh_changed and not jira_changed:
        decision, target_value = "no_op", None
    elif gh_changed and not jira_changed:
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

    if decision != "no_op":
        # Convergence check -- still required, now for a narrower reason
        # than the mechanism it replaces. Two sides can independently change
        # to the SAME new value (both diverge from their own stale
        # baseline, but agree with each other); this catches "the
        # destination already holds target_value" and downgrades to no_op.
        # It is NOT the early return above -- the baseline still needs
        # refreshing below, since both sides were still stale relative to
        # their own prior baseline.
        current_dest_value = jira.status if decision == "push_to_jira" else gh.status
        if target_value == current_dest_value:
            decision = "no_op"

    # -- Assignee decision -- structurally parallel to status's (duplicated,
    # not shared, per the Code Map), translated through `user_mapping`
    # (push_to_jira) or its computed inverse (push_to_github) rather than
    # status's `status_mapping`.
    #
    # RESOLVED 2026-08-15 (escalation, finding 3): an UNREADABLE GitHub
    # `content` (`gh.assignee_unknown`) must never reach the normal decision
    # below -- `gh.assignee` reads `None` in that case, and treating it as a
    # confident value would compare against a real baseline (e.g.
    # "octocat") as a genuine change and push an unassignment to Jira,
    # silently destroying a real assignee on a permission hiccup. Downgrade
    # unconditionally to `no_op`, no baseline touch, re-attempted next tick.
    if gh.assignee_unknown:
        assignee_decision, assignee_target_value = "no_op", None
    elif not gh_assignee_changed and not jira_assignee_changed:
        assignee_decision, assignee_target_value = "no_op", None
    elif gh_assignee_changed and not jira_assignee_changed:
        assignee_decision, assignee_target_value = "push_to_jira", gh.assignee
    elif jira_assignee_changed and not gh_assignee_changed:
        assignee_decision, assignee_target_value = "push_to_github", jira.assignee
    else:
        if config.field_overrides.get(_ASSIGNEE_FIELD) == "jira":
            assignee_decision, assignee_target_value = "push_to_github", jira.assignee
        else:
            assignee_decision, assignee_target_value = "push_to_jira", gh.assignee

    if assignee_decision != "no_op":
        # Convergence check -- assignee's analog of status's above, with one
        # difference status does not have: the comparison MUST be made in
        # the DESTINATION's own vocabulary (fix, review-confirmed).
        # `assignee_target_value` is the SOURCE side's spelling (a GitHub
        # login for push_to_jira, a Jira accountId for push_to_github) while
        # the destination holds the OTHER system's spelling, so comparing
        # the two raw can never match under any non-identity `user_mapping`
        # -- the check silently never fired.
        #
        # That is not merely a redundant write. For push_to_github the
        # redundant write is `add=<mapped login>, remove=gh.assignee` with
        # BOTH naming the same login whenever the destination already
        # agrees, which POSTs and then DELETEs that login and leaves the
        # item with NO assignee at all -- a silent loss the next reconcile
        # then reads as a genuine unassignment and propagates to Jira,
        # converging both systems on "unassigned" permanently.
        #
        # Translating here is deliberately NON-raising: an unmapped value
        # must still reach the write phase below and fail there as a named
        # `SyncUnmappedUserError` exactly as before (an unknown translation
        # is never evidence of convergence), hence `translation_known`.
        if assignee_decision == "push_to_jira":
            assignee_translated_value = (
                None if assignee_target_value is None else config.user_mapping.get(assignee_target_value)
            )
            assignee_current_dest_value = jira.assignee
        else:
            assignee_translated_value = (
                None
                if assignee_target_value is None
                else {v: k for k, v in config.user_mapping.items()}.get(assignee_target_value)
            )
            assignee_current_dest_value = gh.assignee
        translation_known = assignee_target_value is None or assignee_translated_value is not None
        if translation_known and assignee_translated_value == assignee_current_dest_value:
            assignee_decision = "no_op"

    link_repairs: list[str] = []
    if link_repair_github:
        link_repairs.append("github")
    if link_repair_jira:
        link_repairs.append("jira")

    # "baseline" defaults to None (overwritten below once actually written)
    # so every return path from here on shares one consistent details shape.
    # The top-level "decision"/"target_value"/"baseline" keys keep meaning
    # STATUS's own, unchanged, for backward compatibility with pre-8.7
    # assertions; assignee's own decision lives under "assignee".
    details: dict[str, object] = {
        "decision": decision,
        "github_item_id": gh.item_id,
        "jira_issue_key": jira.issue_key,
        "target_value": target_value,
        "baseline": None,
        "assignee": {
            "decision": assignee_decision,
            "target_value": assignee_target_value,
            # Fix (review-confirmed): populated below, after the write phase,
            # with the actually-persisted/translated value -- mirrors how
            # "baseline" above reflects status's actually-written value
            # rather than its raw pre-translation `target_value`. Stays
            # `None` for --dry-run (nothing was written) and whenever
            # assignee_decision is "no_op".
            "written_value": None,
        },
        "link_repairs": link_repairs,
    }

    if dry_run:
        return DutyResult(
            ok=True,
            summary=(
                f"sync reconcile: status={decision}, assignee={assignee_decision}, "
                f"link_repairs={link_repairs} (github={gh.item_id}, jira={jira.issue_key}, dry_run=True)"
            ),
            details=details,
        )

    # Per-side "resulting" values -- default to each side's own CURRENT
    # value (nothing written there this round) and are only overridden below
    # when this round actually writes to that specific side. This is what
    # lets the merge below safely carry forward an unchanged field (status
    # OR assignee) even when the OTHER field is what triggered this write --
    # using the frozen pre-downgrade decision/target_value here instead
    # would, under a non-identity status_mapping, misrecord a status that
    # never actually changed (see this story's own dev-notes: the old
    # single-field code never had to handle "this field didn't move, but we
    # got this far anyway", because before Story 8.7 that combination could
    # never reach past the true no-op fast path above).
    github_status_result = gh.status
    jira_status_result = jira.status
    github_assignee_result = gh.assignee
    jira_assignee_result = jira.assignee

    # Fix (review-confirmed): tracks, independently per tracked field,
    # whether that field's OWN write this round is safe to persist to the
    # baseline -- True once that field's block below completes without
    # raising (including trivially, when its own decision was "no_op" and
    # nothing needed writing). A LATER field's failure (or a link-repair
    # failure, which is not itself baselined) must not strand an EARLIER
    # field's already-successful write's baseline forever -- see the
    # baseline-refresh section below for how these flags are used.
    status_persist_ok = False
    assignee_persist_ok = False

    # Field writes proceed in this fixed order -- status, then assignee,
    # then link repairs; a `SyncError` from any step stops immediately
    # (never attempts a later step after an earlier one failed) -- captured
    # as `write_error` rather than returned immediately, so the field(s)
    # that already succeeded can still get a chance to persist their
    # baseline below.
    write_error: SyncError | None = None
    # Which link repairs this round ACTUALLY performed, as opposed to which
    # ones it computed as needed. On the success path the two are identical;
    # on a failure path they are not, because the link repairs are sequenced
    # last and an earlier field's `SyncError` skips them entirely. Reporting
    # the computed list on that path told callers a repair had happened when
    # nothing was written (fix, review-confirmed) -- `details` reports what
    # was persisted, the same property `written_value`/`baseline` carry.
    link_repairs_done: list[str] = []
    try:
        if decision == "push_to_jira":
            transition_jira_issue(
                jira.issue_key, target_value, config=config, credential=jira_credential, transport=transport
            )
            jira_status_result = target_value
        elif decision == "push_to_github":
            if target_value is None:
                # An explicit clear is not a status word to translate
                # (AD-10: an absent baseline key and an explicit null mean
                # opposite things) -- bypasses the mapping lookup.
                github_write_value = None
            else:
                mapped = config.status_mapping.get(target_value)
                if mapped is None:
                    raise SyncUnmappedStatusError(
                        f"unmapped: jira status {target_value!r} has no status_mapping entry for github"
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
            github_status_result = github_write_value
        status_persist_ok = True

        if assignee_decision == "push_to_jira":
            # gh.assignee (a GitHub login) -> Jira accountId, via
            # user_mapping directly. An explicit None (unassigned) bypasses
            # translation (mirrors status_mapping's None-bypass precedent).
            if assignee_target_value is None:
                jira_assignee_write_value = None
            else:
                mapped_account_id = config.user_mapping.get(assignee_target_value)
                if mapped_account_id is None:
                    raise SyncUnmappedUserError(
                        f"unmapped: github login {assignee_target_value!r} has no user_mapping entry for jira"
                    )
                jira_assignee_write_value = mapped_account_id
            update_jira_issue_fields(
                jira.issue_key,
                {
                    "assignee": (
                        {"accountId": jira_assignee_write_value} if jira_assignee_write_value is not None else None
                    )
                },
                config=config,
                credential=jira_credential,
                transport=transport,
            )
            jira_assignee_result = jira_assignee_write_value
        elif assignee_decision == "push_to_github":
            # jira.assignee (a Jira accountId) -> GitHub login, via
            # user_mapping's computed inverse. An explicit None bypasses
            # translation the same way.
            if assignee_target_value is None:
                github_assignee_write_value = None
            else:
                inverse_user_mapping = {v: k for k, v in config.user_mapping.items()}
                mapped_login = inverse_user_mapping.get(assignee_target_value)
                if mapped_login is None:
                    raise SyncUnmappedUserError(
                        f"unmapped: jira accountId {assignee_target_value!r} has no user_mapping entry for github"
                    )
                github_assignee_write_value = mapped_login
            if gh.content_ref is None:
                # Never guess a target -- a DraftIssue (or absent content)
                # has no owner/repo/number to address.
                raise SyncAPIError(
                    f"github item {gh.item_id}: cannot write assignee -- content is a "
                    "draft issue (or absent), no owner/repo/number to target"
                )
            owner, repo, number = gh.content_ref
            update_github_assignees(
                owner,
                repo,
                number,
                add=github_assignee_write_value,
                # Remove GH's own LIVE current assignee (`gh.assignee`, just
                # freshly read this call) -- review-confirmed fix: the
                # baseline value can be stale relative to what's actually
                # assigned on GitHub right now (reachable in the
                # both-changed/jira-wins conflict branch), and targeting a
                # login that isn't actually assigned is a no-op DELETE
                # against the real API while the additive POST above still
                # adds the new person -- leaving BOTH the drifted-away live
                # assignee and the new one assigned simultaneously, which
                # this module must never do (Boundaries & Constraints:
                # "never manage more than one GitHub assignee"). `None`
                # (nobody currently assigned) means nothing to remove.
                remove=gh.assignee,
                credential=github_credential,
                transport=transport,
            )
            github_assignee_result = github_assignee_write_value
        assignee_persist_ok = True

        if link_repair_github:
            update_project_item_field(
                gh.item_id,
                config.github_link_field_id,
                jira.issue_key,
                config=config,
                credential=github_credential,
                transport=transport,
            )
            link_repairs_done.append("github")
        if link_repair_jira:
            update_jira_issue_fields(
                jira.issue_key,
                {config.jira_link_field_id: gh.item_id},
                config=config,
                credential=jira_credential,
                transport=transport,
            )
            link_repairs_done.append("jira")
    except SyncError as exc:
        write_error = exc
        details["link_repairs"] = link_repairs_done

    # Fix (review-confirmed): surface the actually-persisted/translated
    # assignee value (mirrors "baseline" above for status) -- only when
    # assignee's own write this round actually happened (never during
    # --dry-run, never when its own decision was "no_op", never when its
    # own write is what failed).
    if assignee_persist_ok and assignee_decision != "no_op":
        details["assignee"]["written_value"] = (
            jira_assignee_result if assignee_decision == "push_to_jira" else github_assignee_result
        )

    # Baseline refresh -- runs whenever at least one TRACKED field (status
    # or assignee) diverged from ITS OWN prior baseline on EITHER side AND
    # that field's own write this round is safe to persist (`status_persist_
    # ok`/`assignee_persist_ok`), because every future reconcile of this
    # pair would otherwise see an unpersisted field as "changed" forever
    # (AD-5's zero-loop property). Deliberately NOT gated on the
    # link-repair flags -- the identity link is never baselined (Boundaries
    # & Constraints), so a link-repair-only round makes exactly the link
    # write(s) above and nothing else.
    should_persist_status = status_persist_ok and (gh_changed or jira_changed)
    # A side whose baseline KEY WAS PRESENT but stale against its own
    # current value (unchanged pre-8.7 behavior, status's own analogous
    # case) still needs its baseline refreshed even when the two sides'
    # values happen to converge -- distinct from a MISSING key with no
    # prior recorded value to be stale against.
    assignee_baseline_stale = (
        not gh.assignee_unknown and gh_assignee_base is not _MISSING and gh.assignee != gh_assignee_base
    ) or (jira_assignee_base is not _MISSING and jira.assignee != jira_assignee_base)
    # RESOLVED 2026-08-15 (escalation, finding 1): a MISSING key whose
    # comparison converges to `no_op` (both sides already agree, or
    # `gh.assignee_unknown`) must NOT by itself trigger a baseline write --
    # that would reintroduce a write on every single pre-8.7 pair's first
    # post-upgrade reconcile regardless of whether assignee actually
    # diverges, exactly the write-storm this story's own Approach rejects.
    # Persist when assignee's own decision resulted in a real push, OR a
    # PRESENT key was genuinely stale (even if now converged), OR
    # (unchanged free-backfill behavior) a missing key rides along for
    # free because status ALSO writes this round.
    should_persist_assignee = assignee_persist_ok and (
        assignee_decision != "no_op" or assignee_baseline_stale or (assignee_key_missing and should_persist_status)
    )

    def _persist_merged_baseline() -> None:
        """Serialize and write both sides' merged baseline maps. Each
        side's baseline records that side's own ACTUALLY-RESULTING value
        for a tracked field ONLY WHEN that field's own write this round is
        `*_persist_ok` -- this is both how a pre-8.7 item's first
        post-upgrade reconcile backfills its missing "assignee" baseline
        key for free the moment any OTHER field's divergence already
        triggered a write (Design Notes), AND (fix, review-confirmed) how a
        LATER field's write failure no longer strands an EARLIER field's
        already-successful write's baseline forever: a field whose OWN
        write just failed is excluded from the override (its prior baseline
        value, if any, is carried forward untouched by `**gh.baseline`/
        `**jira.baseline` instead) so it is never falsely marked
        "converged" -- it is correctly re-attempted on the next reconcile.
        Raises `SyncError` on failure; the caller decides how to report it.
        """
        gh_overrides: dict[str, object] = {}
        jira_overrides: dict[str, object] = {}
        if status_persist_ok:
            gh_overrides[_TRACKED_FIELD] = github_status_result
            jira_overrides[_TRACKED_FIELD] = jira_status_result
        if assignee_persist_ok:
            gh_overrides[_ASSIGNEE_FIELD] = github_assignee_result
            jira_overrides[_ASSIGNEE_FIELD] = jira_assignee_result
        new_gh_baseline = _serialize_baseline(
            {**gh.baseline, **gh_overrides}, side="github", ceiling=_GITHUB_BASELINE_FIELD_CEILING
        )
        new_jira_baseline = _serialize_baseline(
            {**jira.baseline, **jira_overrides}, side="jira", ceiling=_JIRA_BASELINE_FIELD_CEILING
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
        if status_persist_ok:
            # `github_status_result` mirrors what the GH-side baseline write
            # above actually persisted for status, not the raw pre-translation
            # value -- matches the pre-8.7 detail shape callers already assert.
            details["baseline"] = {_TRACKED_FIELD: github_status_result}

    if write_error is not None:
        # Fix (review-confirmed): a LATER field's write failure must not
        # strand an EARLIER field's already-successful write's baseline
        # forever -- the same "Known, accepted non-atomicity" risk class as
        # the baseline-refresh-itself-failing case below, just for a new
        # cause. Whichever field(s) already completed (or needed nothing
        # this round) still get a chance to persist here.
        if should_persist_status or should_persist_assignee:
            try:
                _persist_merged_baseline()
            except SyncError as baseline_exc:
                return DutyResult(
                    ok=False,
                    summary=(
                        f"sync reconcile: {write_error} (baseline refresh for the "
                        f"field(s) that already succeeded also failed: {baseline_exc})"
                    ),
                    details=details,
                )
        return DutyResult(ok=False, summary=f"sync reconcile: {write_error}", details=details)

    if should_persist_status or should_persist_assignee:
        try:
            _persist_merged_baseline()
        except SyncError as exc:
            # Known, accepted non-atomicity (same risk class as
            # keys.rotate_identity's documented partial-completion state):
            # the tracked-field write(s) above already succeeded; only the
            # baseline refresh failed. Reported here rather than rolled
            # back.
            #
            # `details` is passed (fix, review-confirmed) -- this was the
            # one return path that omitted it, defaulting to `{}` and
            # breaking this function's own stated shape guarantee ("a
            # caller can read any key unconditionally without a KeyError",
            # the no-op path's comment above) on exactly the path where a
            # caller most needs to know what did get written. The summary
            # names assignee's decision too, for the same reason: status's
            # alone was misleading once assignee could be the field that
            # actually moved.
            return DutyResult(
                ok=False,
                summary=(
                    f"sync reconcile: status={decision}, assignee={assignee_decision} "
                    f"but failed refreshing baseline: {exc}"
                ),
                details=details,
            )

    return DutyResult(
        ok=True,
        summary=(
            f"sync reconcile: status={decision}, assignee={assignee_decision}, "
            f"link_repairs={link_repairs} (github={gh.item_id}, jira={jira.issue_key})"
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
        candidates = list_linked_github_items(config=config, credential=github_credential, transport=transport)
    except (SyncError, OSError, urllib.error.URLError) as exc:
        return DutyResult(
            ok=False,
            summary=f"sync reconcile --schedule: failed enumerating candidates: {exc}",
        )

    entries: list[dict[str, object]] = []
    for candidate in candidates:
        github_item_id = candidate["github_item_id"]
        try:
            result = reconcile(github_item_id=github_item_id, config=config, dry_run=dry_run, transport=transport)
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
        summary=(f"sync reconcile --schedule: {len(entries)} {candidate_word}, {ok_count} ok, {len(failed)} failed"),
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
