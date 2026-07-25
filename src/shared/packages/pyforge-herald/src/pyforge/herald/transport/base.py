"""The ``DesignTransport`` port and the invariants every adapter upholds
(Story 1.2, AD-3).

``DesignTransport`` is the whole surface Herald is allowed to use against
the ``claude-design`` server: exactly the 8 tools the proven bridge loop
needs (``bridge-protocol.md``), no more. It is a ``@runtime_checkable
typing.Protocol`` -- never an ABC -- mirroring
``pyforge.warden.interfaces``: adapters conform structurally and are
substituted by injection, so a test can pass a hand-written fake with no
inheritance and no network.

Port method names are Herald's, not the server's. They coincide with the
MCP tool names everywhere except one: the port's ``get_design_prompt`` maps
to the tool ``get_claude_design_prompt``. Translating that is the adapter's
job, and ``test_mcp_transport.py`` asserts it.

Two invariants live here rather than in any one adapter, because Story
1.3's ``AgentSdkTransport`` must uphold them identically:

* ``sanitize_payload`` -- NFR-04's defence in depth. ``render_preview`` is
  the only tool that returns a ``serve_url`` (a ``*.claudeusercontent.com``
  link carrying a project-scoped bearer token), and the server's own reply
  says never to surface it, so ``PreviewRef`` has no field to hold one.
  ``sanitize_payload`` covers everything the port does *not* model: it
  drops any ``serve_url`` key at any depth and replaces any string value
  containing the tokenized host with ``REDACTED``. The whole string is
  replaced, not the matching substring -- fail closed, and loudly, rather
  than emit a plausible-looking half-scrubbed URL.
* ``parse_read_response`` -- the ``read_file`` wire format. The server
  wraps the body in an ``untrusted-project-content`` tag carrying ``path``
  and ``etag`` attributes, HTML-entity-escapes the body so it cannot close
  that tag, and appends a human-readable note after the closing tag. An
  ``if_none_match`` hit short-circuits to a tiny JSON object instead. Both
  forms land on one ``FileRead``.

FR-24 (no unconditional writes) is enforced structurally in the port's own
signatures: ``create_support_js`` takes a *required* ``if_match``, and the
``files`` entries of ``write_files`` / ``copy_files`` are validated by the
adapter before any network call. ``read_file``'s ``if_none_match`` stays
optional -- a first read legitimately has no prior etag.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ..errors import TransportCallError

SERVE_URL_KEY = "serve_url"
"""The response key that carries a tokenized preview URL. Always dropped."""

TOKENIZED_PREVIEW_HOST = "claudeusercontent.com"
"""Host of the short-lived, token-bearing preview origin (NFR-04)."""

REDACTED = "<redacted: tokenized preview url>"
"""Replacement for any string value that mentions the tokenized host."""

_READ_TAG = "untrusted-project-content"
_READ_OPEN_RE = re.compile(rf"<{_READ_TAG}\b([^>]*)>")
_READ_CLOSE = f"</{_READ_TAG}>"
_ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


@dataclass(frozen=True)
class ToolResult:
    """One raw tool answer: its concatenated text blocks plus the server's
    own error flag. The low-level seam speaks in these, so a fake caller
    can reproduce an ``isError`` reply without an HTTP layer."""

    text: str
    is_error: bool = False


@dataclass(frozen=True)
class ProjectRef:
    """A created Design project: its id and its durable ``claude.ai`` url."""

    project_id: str
    url: str


@dataclass(frozen=True)
class PlanHandle:
    """A ``finalize_plan`` grant: the signed token plus the current etag of
    every declared write path (``"0"`` where the path does not exist yet).
    ``base_etags`` is empty for a project-scoped plan, which returns none."""

    plan_token: str
    base_etags: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FileRead:
    """One ``read_file`` answer. ``unchanged`` is True only for an
    ``if_none_match`` hit, and then ``body`` is None -- no bytes crossed the
    wire, which is exactly what makes ``herald deck watch`` cheap."""

    path: str
    etag: str
    body: str | None
    unchanged: bool


@dataclass(frozen=True)
class PreviewRef:
    """A preview answer with **no ``serve_url`` field at all** (NFR-04).

    ``open_url`` is the durable ``claude.ai/design`` editor link -- the only
    one that may ever be shown, logged, or persisted."""

    open_url: str
    expires_at: str | None = None


@runtime_checkable
class ToolCaller(Protocol):
    """The injectable low-level seam: one tool call in, one raw answer out.

    ``McpTransport`` owns a real one (an ``mcp`` SDK session per call);
    tests inject a recording fake. Splitting it out is what lets every
    marshalling assertion in the suite run with the socket-deny harness
    active."""

    def call_tool(self, tool: str, arguments: Mapping[str, Any]) -> ToolResult: ...


@runtime_checkable
class DesignTransport(Protocol):
    """The 8-tool ``claude-design`` surface Herald is allowed to use.

    Synchronous by contract: adapters bridging an async SDK do so
    internally. All arguments are keyword-only, so an adapter can add a
    parameter without breaking positional call sites."""

    def get_design_prompt(
        self, *, design_system_id: str | None = None, project_id: str | None = None
    ) -> str:
        """The mandatory pre-write design-system prompt (tool
        ``get_claude_design_prompt``)."""
        ...

    def create_project(
        self, *, name: str, design_system_id: str | None = None
    ) -> ProjectRef: ...

    def finalize_plan(
        self,
        *,
        project_id: str,
        writes: Sequence[str] = (),
        deletes: Sequence[str] = (),
        scope: str = "paths",
    ) -> PlanHandle:
        """Declare the write boundary; returns the token + base etags."""
        ...

    def create_support_js(
        self,
        *,
        project_id: str,
        if_match: str,
        path: str = "support.js",
        plan_token: str | None = None,
    ) -> Mapping[str, Any]:
        """Write the server-provided Design Components runtime. ``if_match``
        is required (FR-24) -- ``"0"`` for a fresh project."""
        ...

    def copy_files(
        self,
        *,
        project_id: str,
        files: Sequence[Mapping[str, Any]],
        plan_token: str | None = None,
    ) -> Mapping[str, Any]:
        """Server-side copy (exempt from ``read_file``'s size cap). Every
        entry needs ``if_match``, or ``leaf_if_match`` for a folder dest."""
        ...

    def write_files(
        self,
        *,
        project_id: str,
        files: Sequence[Mapping[str, Any]],
        plan_token: str | None = None,
    ) -> Mapping[str, Any]:
        """Write inline file contents. Every entry needs ``if_match``."""
        ...

    def read_file(
        self, *, project_id: str, path: str, if_none_match: str | None = None
    ) -> FileRead: ...

    def render_preview(self, *, project_id: str, path: str) -> PreviewRef: ...


def sanitize_payload(payload: Any) -> Any:
    """Recursively strip tokenized-preview material from a tool answer.

    Drops every ``serve_url`` key at any depth, and replaces any string
    mentioning ``claudeusercontent.com`` with ``REDACTED`` in full. Mappings
    become plain dicts and sequences become lists; scalars pass through
    unchanged. Idempotent, so it is safe to apply to a raw text answer and
    again to the object parsed out of it.

    Replacing the whole string is deliberate. A partially-scrubbed URL still
    reads as a URL and invites a paste; a wholly-redacted value cannot. The
    cost is that a *file body* legitimately containing the host is redacted
    wholesale rather than corrupted subtly -- fail closed, visibly."""
    if isinstance(payload, Mapping):
        return {
            key: sanitize_payload(value)
            for key, value in payload.items()
            if key != SERVE_URL_KEY
        }
    if isinstance(payload, (list, tuple)):
        return [sanitize_payload(item) for item in payload]
    if isinstance(payload, str) and TOKENIZED_PREVIEW_HOST in payload:
        return REDACTED
    return payload


def _decode_entities(text: str) -> str:
    """Undo the server's body escaping. ``&amp;`` is decoded LAST so an
    escaped ``&amp;lt;`` in the original file does not become a ``<``."""
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def parse_read_response(text: str) -> FileRead:
    """Parse either ``read_file`` wire form into one ``FileRead``.

    Raises ``TransportCallError`` when the answer matches neither form --
    an unrecognised shape means the wire contract moved, and guessing at it
    would write half-decoded bytes into the repo."""
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise TransportCallError(
                "read_file returned an unparseable JSON answer"
            ) from exc
        if not isinstance(payload, Mapping) or not payload.get("unchanged"):
            raise TransportCallError(
                "read_file returned a JSON answer that is not an "
                "if_none_match short-circuit"
            )
        return FileRead(
            path=str(payload.get("path", "")),
            etag=str(payload.get("etag", "")),
            body=None,
            unchanged=True,
        )

    opening = _READ_OPEN_RE.search(text)
    close_at = text.rfind(_READ_CLOSE)
    if opening is None or close_at < opening.end():
        raise TransportCallError(
            f"read_file returned no <{_READ_TAG}> wrapper to parse"
        )
    attributes = dict(_ATTR_RE.findall(opening.group(1)))
    body = text[opening.end() : close_at]
    # The server puts the body on its own lines inside the wrapper; drop
    # exactly the one framing newline at each end, never real content.
    if body.startswith("\n"):
        body = body[1:]
    if body.endswith("\n"):
        body = body[:-1]
    return FileRead(
        path=_decode_entities(attributes.get("path", "")),
        etag=attributes.get("etag", ""),
        body=_decode_entities(body),
        unchanged=False,
    )
