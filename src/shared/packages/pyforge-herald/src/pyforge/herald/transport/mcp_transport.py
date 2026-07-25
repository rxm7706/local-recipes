"""The primary ``DesignTransport`` adapter: a plain MCP client (Story 1.2).

This module is the FR-21 prove-or-kill spike made permanent. It talks to
``https://api.anthropic.com/v1/design/mcp`` with the ``mcp`` SDK's
``streamablehttp_client``, authenticating with the OAuth access token the
Claude Code CLI already stored for ``/design-login``. Proven live on
2026-07-25 from a plain, non-interactive Python process: ``initialize``
answered, ``list_tools`` listed all 8 port tools, and
``get_claude_design_prompt`` returned a full design-system prompt. FR-22's
Agent-SDK fallback (Story 1.3) is therefore the fallback, not V1's default.

**Credentials.** ``resolve_design_credential`` copies warden's
``resolve_forge(env=...)`` seam: resolution is injectable, so tests never
touch a real ``~/.claude/.credentials.json``. Herald only ever *reads* that
file -- NFR-05 forbids introducing new credential storage, and minting or
refreshing a token is the CLI's job, so an expired token is a clean
``AuthError`` naming ``/design-login``, never a self-heal attempt. The token
value is never logged, returned, or written: ``DesignCredential`` keeps it
out of its own ``repr``, and the one place an SDK exception message could
plausibly echo it, ``_call_via_mcp_sdk`` scrubs it first.

**Why one ``asyncio.run()`` per call.** The port is synchronous and the SDK
is async, so each call opens a session, runs one tool, and closes. The
obvious worry -- losing session continuity -- does not apply: the server
keeps no session-scoped state Herald depends on. ``plan_token`` and the
``if_match`` / ``if_none_match`` etags are explicit parameters on every
later call. A persistent session would need a background event loop plus a
single owning task (anyio cancel scopes forbid entering and exiting
``streamablehttp_client`` from different tasks) -- real concurrency
machinery and a new dependency -- to save one initialize round-trip on
commands that make a handful of calls. Recorded in ``deferred-work.md`` as
an available optimization if ``herald deck watch`` ever needs it.

The ``mcp`` import is lazy, inside the async helper, mirroring
``pyforge.atlas.mcp.server``'s lazy ``from fastmcp import``: importing
``pyforge.herald.transport`` must stay cheap and must not require the SDK
for anything a fake caller can serve.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ..errors import (
    AuthError,
    TransportCallError,
    TransportUnreachableError,
    UnconditionalWriteError,
)
from .base import (
    FileRead,
    PlanHandle,
    PreviewRef,
    ProjectRef,
    ToolCaller,
    ToolResult,
    parse_read_response,
    sanitize_payload,
)

DESIGN_MCP_URL = "https://api.anthropic.com/v1/design/mcp"
"""The remote ``claude-design`` MCP endpoint (verified 2026-07-25)."""

ANTHROPIC_VERSION = "2023-06-01"
DESIGN_CLIENT_HEADER = "claude-cli-design-tool"

MODERNIST_DESIGN_SYSTEM_ID = "fbc1d6c8-b35f-4df6-9044-a64d2675427b"
"""The Modernist design system every PyForge deck is bound to
(``bridge-protocol.md`` § Conventions)."""

CREDENTIALS_PATH_ENV = "HERALD_DESIGN_CREDENTIALS"
"""Overrides the ``~/.claude/.credentials.json`` lookup (tests, sandboxes)."""

DESIGN_OAUTH_KEY = "designOauth"
_REMEDIATION = "run /design-login in Claude Code to refresh it"

# The port method whose name differs from its MCP tool name. Kept as a
# named constant so the divergence is greppable rather than a literal
# buried in one method body.
GET_DESIGN_PROMPT_TOOL = "get_claude_design_prompt"


@dataclass(frozen=True)
class DesignCredential:
    """A stored ``/design-login`` OAuth credential.

    ``access_token`` is excluded from ``repr`` so no accidental log line,
    assertion message, or pytest failure dump can leak it.
    ``expires_at_ms`` is epoch **milliseconds** (the file's own unit), and
    ``None`` means the file declared no expiry."""

    access_token: str = field(repr=False)
    expires_at_ms: int | None = None

    def is_expired(self, *, now_ms: float | None = None) -> bool:
        if self.expires_at_ms is None:
            return False
        current = time.time() * 1000 if now_ms is None else now_ms
        return self.expires_at_ms <= current


def _default_credentials_path() -> Path:
    return Path.home() / ".claude" / ".credentials.json"


def resolve_design_credential(
    *,
    credentials_path: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> DesignCredential:
    """Read the stored ``/design-login`` credential (warden's
    ``resolve_forge(env=...)`` shape: injectable, no CLI flag).

    Precedence: an explicit ``credentials_path``, else
    ``HERALD_DESIGN_CREDENTIALS`` from ``env`` (defaulting to
    ``os.environ``), else ``~/.claude/.credentials.json``. A missing file,
    unreadable JSON, absent ``designOauth`` block, absent token, or an
    ``expiresAt`` already in the past all raise ``AuthError`` naming
    ``/design-login``. No refresh is attempted and nothing is written
    back (NFR-05)."""
    source = os.environ if env is None else env
    if credentials_path is not None:
        path = Path(credentials_path)
    else:
        override = source.get(CREDENTIALS_PATH_ENV)
        path = Path(override) if override else _default_credentials_path()

    if not path.is_file():
        raise AuthError(
            f"no stored Claude Design credential at {path} -- {_REMEDIATION}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthError(
            f"could not read the stored Claude Design credential at {path} "
            f"({type(exc).__name__}) -- {_REMEDIATION}"
        ) from exc

    block = payload.get(DESIGN_OAUTH_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(block, Mapping):
        raise AuthError(f"{path} has no {DESIGN_OAUTH_KEY!r} block -- {_REMEDIATION}")
    token = block.get("accessToken")
    if not isinstance(token, str) or not token:
        raise AuthError(
            f"{path} has no {DESIGN_OAUTH_KEY}.accessToken -- {_REMEDIATION}"
        )

    raw_expiry = block.get("expiresAt")
    # Anything non-numeric is treated as "no declared expiry" rather than a
    # hard failure: the server is the real authority on validity, and a
    # usable token must not be refused over a field shape.
    expires_at = int(raw_expiry) if isinstance(raw_expiry, (int, float)) else None
    credential = DesignCredential(access_token=token, expires_at_ms=expires_at)
    if credential.is_expired():
        raise AuthError(
            f"the stored Claude Design credential in {path} expired -- {_REMEDIATION}"
        )
    return credential


def _require_conditional(
    tool: str, files: Sequence[Mapping[str, Any]], *, allow_leaf: bool
) -> None:
    """FR-24: refuse an unconditional write before any network call.

    ``"0"`` is a legitimate precondition (assert the path does not exist),
    so the check is presence-of-a-non-empty-string, not truthiness of the
    etag itself."""
    for index, entry in enumerate(files):
        keys = ("if_match", "leaf_if_match") if allow_leaf else ("if_match",)
        if any(entry.get(key) for key in keys):
            continue
        subject = entry.get("dest") or entry.get("path") or f"entry {index}"
        wanted = " or ".join(repr(key) for key in keys)
        raise UnconditionalWriteError(
            f"{tool}: {subject!r} carries no {wanted} etag precondition "
            f'(FR-24); pass "0" to assert the path does not exist'
        )


class McpTransport:
    """``DesignTransport`` over the remote ``claude-design`` MCP server.

    ``caller`` is the injectable low-level seam -- omit it for the real SDK
    session, pass a fake to exercise marshalling with no network.
    ``credential`` is resolved lazily on first real call, so constructing a
    transport never touches the filesystem."""

    def __init__(
        self,
        *,
        caller: ToolCaller | None = None,
        credential: DesignCredential | None = None,
        url: str = DESIGN_MCP_URL,
    ) -> None:
        self._caller = caller
        self._credential = credential
        self._url = url

    # --- the 8 port methods -------------------------------------------

    def get_design_prompt(
        self, *, design_system_id: str | None = None, project_id: str | None = None
    ) -> str:
        arguments: dict[str, Any] = {}
        if design_system_id is not None:
            arguments["design_system_id"] = design_system_id
        if project_id is not None:
            arguments["project_id"] = project_id
        return self._call_text(GET_DESIGN_PROMPT_TOOL, arguments)

    def create_project(
        self, *, name: str, design_system_id: str | None = None
    ) -> ProjectRef:
        arguments: dict[str, Any] = {"name": name}
        if design_system_id is not None:
            arguments["design_system_id"] = design_system_id
        payload = self._call_json("create_project", arguments)
        return ProjectRef(
            project_id=str(payload.get("project_id", "")),
            url=str(payload.get("url", "")),
        )

    def finalize_plan(
        self,
        *,
        project_id: str,
        writes: Sequence[str] = (),
        deletes: Sequence[str] = (),
        scope: str = "paths",
    ) -> PlanHandle:
        arguments: dict[str, Any] = {"project_id": project_id}
        if scope == "project":
            # A project-scoped plan must declare no paths, and answers with
            # no base_etags -- list_files/read_file supply if_match instead.
            arguments["scope"] = "project"
        else:
            arguments["writes"] = list(writes)
            arguments["deletes"] = list(deletes)
        payload = self._call_json("finalize_plan", arguments)
        raw_etags = payload.get("base_etags") or {}
        etags = {str(key): str(value) for key, value in raw_etags.items()}
        return PlanHandle(
            plan_token=str(payload.get("plan_token", "")),
            base_etags=MappingProxyType(etags),
        )

    def create_support_js(
        self,
        *,
        project_id: str,
        if_match: str,
        path: str = "support.js",
        plan_token: str | None = None,
    ) -> Mapping[str, Any]:
        entry = {"path": path, "if_match": if_match}
        _require_conditional("create_support_js", [entry], allow_leaf=False)
        arguments: dict[str, Any] = {
            "project_id": project_id,
            "path": path,
            "if_match": if_match,
        }
        if plan_token is not None:
            arguments["plan_token"] = plan_token
        return self._call_json("create_support_js", arguments)

    def copy_files(
        self,
        *,
        project_id: str,
        files: Sequence[Mapping[str, Any]],
        plan_token: str | None = None,
    ) -> Mapping[str, Any]:
        _require_conditional("copy_files", files, allow_leaf=True)
        arguments: dict[str, Any] = {
            "project_id": project_id,
            "files": [dict(entry) for entry in files],
        }
        if plan_token is not None:
            arguments["plan_token"] = plan_token
        return self._call_json("copy_files", arguments)

    def write_files(
        self,
        *,
        project_id: str,
        files: Sequence[Mapping[str, Any]],
        plan_token: str | None = None,
    ) -> Mapping[str, Any]:
        _require_conditional("write_files", files, allow_leaf=False)
        arguments: dict[str, Any] = {
            "project_id": project_id,
            "files": [dict(entry) for entry in files],
        }
        if plan_token is not None:
            arguments["plan_token"] = plan_token
        return self._call_json("write_files", arguments)

    def read_file(
        self, *, project_id: str, path: str, if_none_match: str | None = None
    ) -> FileRead:
        arguments: dict[str, Any] = {"project_id": project_id, "path": path}
        if if_none_match is not None:
            arguments["if_none_match"] = if_none_match
        # Parse first, sanitize the parsed body: scrubbing the raw answer
        # would redact the whole wrapper (a serve_url anywhere in a body
        # would take the wrapper's own attributes with it).
        read = parse_read_response(self._raw_text("read_file", arguments))
        if read.body is None:
            return read
        return replace(read, body=sanitize_payload(read.body))

    def render_preview(self, *, project_id: str, path: str) -> PreviewRef:
        payload = self._call_json(
            "render_preview", {"project_id": project_id, "path": path}
        )
        expires_at = payload.get("expires_at")
        return PreviewRef(
            open_url=str(payload.get("open_url", "")),
            expires_at=None if expires_at is None else str(expires_at),
        )

    # --- the call pipeline ---------------------------------------------

    def _raw_text(self, tool: str, arguments: Mapping[str, Any]) -> str:
        """One tool call; raises ``TransportCallError`` on a server-side
        error. Returns the answer verbatim -- callers sanitize."""
        caller = self._caller
        result = (
            caller.call_tool(tool, arguments)
            if caller is not None
            else self._call_via_mcp_sdk(tool, arguments)
        )
        if result.is_error:
            raise TransportCallError(f"claude-design {tool} failed: {result.text}")
        return result.text

    def _call_text(self, tool: str, arguments: Mapping[str, Any]) -> str:
        return sanitize_payload(self._raw_text(tool, arguments))

    def _call_json(self, tool: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        text = self._raw_text(tool, arguments)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise TransportCallError(
                f"claude-design {tool} returned an unparseable answer"
            ) from exc
        if not isinstance(payload, Mapping):
            raise TransportCallError(
                f"claude-design {tool} returned {type(payload).__name__}, "
                f"expected an object"
            )
        return sanitize_payload(payload)

    def _call_via_mcp_sdk(self, tool: str, arguments: Mapping[str, Any]) -> ToolResult:
        """One ``asyncio.run()``-scoped session per call (see module doc).

        Every SDK/connection failure becomes ``TransportUnreachableError``
        naming the endpoint. The token is scrubbed from the message before
        it is raised, so no exception text can ever carry it."""
        credential = self._credential
        if credential is None:
            credential = resolve_design_credential()
            self._credential = credential
        try:
            return asyncio.run(
                _call_tool_async(self._url, credential, tool, dict(arguments))
            )
        except Exception as exc:  # noqa: BLE001 - every SDK failure maps here
            detail = f"{type(exc).__name__}: {exc}"
            if credential.access_token in detail:
                detail = detail.replace(credential.access_token, "<redacted>")
            raise TransportUnreachableError(
                f"could not reach the claude-design MCP endpoint at "
                f"{self._url} calling {tool}: {detail}"
            ) from None


async def _call_tool_async(
    url: str, credential: DesignCredential, tool: str, arguments: dict[str, Any]
) -> ToolResult:
    """Open a streamable-HTTP session, run one tool, close.

    The ``mcp`` import is lazy so importing this module costs nothing and a
    fake-caller test never needs the SDK installed. The SDK supplies
    ``Accept`` and ``Mcp-Session-Id``; these three headers are ours."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {
        "Authorization": f"Bearer {credential.access_token}",
        "anthropic-version": ANTHROPIC_VERSION,
        "X-Anthropic-Client": DESIGN_CLIENT_HEADER,
    }
    async with streamablehttp_client(url, headers=headers) as (read_end, write_end, _):
        async with ClientSession(read_end, write_end) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
    text = "".join(
        block.text for block in result.content if getattr(block, "type", "") == "text"
    )
    return ToolResult(text=text, is_error=bool(result.isError))
