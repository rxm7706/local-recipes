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

**Why the failure path does more than wrap.** The SDK runs its transport
in an anyio task group, so a bare connection failure arrives as an
``ExceptionGroup`` whose own message is "unhandled errors in a TaskGroup
(1 sub-exception)" -- the cause is in the leaves. ``_call_via_mcp_sdk``
therefore flattens the group into the message it raises, and reads the
leaves for an HTTP 401/403, which becomes ``AuthError`` naming
``/design-login`` rather than a misleading "endpoint unreachable"
(``bridge-protocol.md`` § Watch parameters: halt on auth error, never
retry a 401). It also refuses up front to run inside a live event loop,
where ``asyncio.run`` cannot work at all.

The ``mcp`` import is lazy, inside the async helper, mirroring
``pyforge.atlas.mcp.server``'s lazy ``from fastmcp import``: importing
``pyforge.herald.transport`` must stay cheap and must not require the SDK
for anything a fake caller can serve.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ..errors import (
    AuthError,
    TransportCallError,
    TransportError,
    TransportUnreachableError,
)
from .base import (
    FileRead,
    PlanHandle,
    PreviewRef,
    ProjectRef,
    ToolCaller,
    ToolResult,
    _as_optional_text,
    _as_text,
    parse_read_response,
    require_conditional,
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

_AUTH_STATUS_CODES = frozenset({401, 403})
_AUTH_TEXT_RE = re.compile(
    r"unauthorized"
    r"|forbidden"
    r"|(?:http|https|status|status_code|code|returned|response)\W{0,3}(?:401|403)\b"
    r"|\b(?:401|403)\s+(?:unauthorized|forbidden)\b",
    re.IGNORECASE,
)
"""Fallback markers for an SDK that stringifies the status instead of
carrying a response object (see ``_indicates_auth_failure``).

A bare ``401``/``403`` is deliberately *not* enough. Those three digits
occur in addresses and identifiers a failing connection routinely names
(``[Errno 101] ... 2607:f8b0:4003::401``, ``Mcp-Session-Id=8f403abc``), and
misreading one as a rejected credential is the expensive direction of the
error: ``bridge-protocol.md`` § Watch parameters says halt on an auth error
and never retry, so a transient outage would stop ``herald deck watch`` for
good and blame a credential that is fine."""

_PLAN_SCOPES = ("paths", "project")

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

    # Anything that is not a finite number is treated as "no declared
    # expiry" rather than a hard failure: the server is the real authority
    # on validity, and a usable token must not be refused over a field
    # shape. `bool` is excluded because it is an `int` subclass, so a stray
    # `"expiresAt": true` would otherwise read as 1 ms and hard-expire a
    # good credential; `json` also accepts NaN/Infinity, neither of which
    # survives `int()`.
    raw_expiry = block.get("expiresAt")
    expires_at: int | None = None
    if isinstance(raw_expiry, (int, float)) and not isinstance(raw_expiry, bool):
        try:
            expires_at = int(raw_expiry)
        except (ValueError, OverflowError):
            expires_at = None
    credential = DesignCredential(access_token=token, expires_at_ms=expires_at)
    if credential.is_expired():
        raise AuthError(
            f"the stored Claude Design credential in {path} expired -- {_REMEDIATION}"
        )
    return credential


def _flatten(exc: BaseException) -> list[BaseException]:
    """Every leaf of a possibly-nested ``ExceptionGroup``.

    The ``mcp`` SDK raises through anyio task groups, so the exception that
    reaches us is routinely a group whose own message says only "unhandled
    errors in a TaskGroup (1 sub-exception)" -- the connection refusal, the
    TLS failure, the HTTP status all live in the leaves."""
    if isinstance(exc, BaseExceptionGroup):
        leaves: list[BaseException] = []
        for member in exc.exceptions:
            leaves.extend(_flatten(member))
        return leaves
    return [exc]


def _describe(exc: BaseException) -> str:
    """``type: message`` for an exception, appending every leaf when it is
    a group -- otherwise the real cause never reaches the operator."""
    head = f"{type(exc).__name__}: {exc}"
    leaves = _flatten(exc)
    if leaves == [exc]:
        return head
    inner = "; ".join(f"{type(leaf).__name__}: {leaf}" for leaf in leaves)
    return f"{head} [{inner}]"


_TOKEN_REDACTED = "<redacted>"
_MIN_TOKEN_FRAGMENT = 12
"""Shortest run of token characters worth scrubbing. Short enough to catch
a truncated echo, long enough not to match ordinary prose."""


def _scrub_token(detail: str, token: str) -> str:
    """Remove the access token -- whole or truncated -- from an error text.

    An exact-substring replace is not enough on its own: a library that
    elides a long header (``Bearer sk-ant-oat01-AbCd...``) leaves a prefix
    behind, and a prefix is still credential material. So the longest
    prefix of at least ``_MIN_TOKEN_FRAGMENT`` characters that actually
    appears is replaced too. The spec's rule is absolute -- no token value
    is ever logged, returned, or written."""
    if not token:
        return detail
    detail = detail.replace(token, _TOKEN_REDACTED)
    for size in range(len(token) - 1, _MIN_TOKEN_FRAGMENT - 1, -1):
        fragment = token[:size]
        if fragment in detail:
            return detail.replace(fragment, _TOKEN_REDACTED)
    return detail


def _indicates_auth_failure(leaves: Sequence[BaseException], detail: str) -> bool:
    """Whether a failed call was rejected rather than unreachable.

    Prefers an ``httpx``-style ``.response.status_code`` on a leaf, which is
    unambiguous, and falls back to a *contextual* scan of the
    already-scrubbed detail for SDKs that only stringify the status.
    Scanning the scrubbed text matters: an access token that happened to
    contain "401" would otherwise misfile a plain connection failure as an
    auth failure."""
    for leaf in leaves:
        status = getattr(getattr(leaf, "response", None), "status_code", None)
        if isinstance(status, int) and status in _AUTH_STATUS_CODES:
            return True
    return _AUTH_TEXT_RE.search(detail) is not None


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
        # The endpoint is the one place the bearer token leaves this
        # process, so it may not be downgraded to cleartext by a caller
        # override -- an http:// endpoint would put the stored
        # /design-login token on the wire in plain text.
        if not url.lower().startswith("https://"):
            raise TransportError(
                f"the claude-design transport refuses the non-https endpoint "
                f"{url!r}: the stored credential must never cross the wire "
                f"in cleartext"
            )
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
            project_id=_as_text(payload.get("project_id")),
            url=_as_text(payload.get("url")),
        )

    def finalize_plan(
        self,
        *,
        project_id: str,
        writes: Sequence[str] = (),
        deletes: Sequence[str] = (),
        scope: str = "paths",
    ) -> PlanHandle:
        if scope not in _PLAN_SCOPES:
            # An unrecognised scope must not degrade to a paths plan: with
            # writes empty that authorizes nothing, and every later write
            # fails at the server with no hint that the typo was the cause.
            raise TransportCallError(
                f"finalize_plan: unknown scope {scope!r}; expected "
                f"{' or '.join(repr(name) for name in _PLAN_SCOPES)}"
            )
        arguments: dict[str, Any] = {"project_id": project_id}
        if scope == "project":
            # A project-scoped plan must declare no paths, and answers with
            # no base_etags -- list_files/read_file supply if_match instead.
            if writes or deletes:
                raise TransportCallError(
                    "finalize_plan: scope='project' already authorizes the "
                    "whole project and must not also declare writes/deletes"
                )
            arguments["scope"] = "project"
        else:
            if not writes and not deletes:
                # Same failure the unknown-scope guard above prevents,
                # reached the other way: a paths plan declaring no paths
                # authorizes nothing, so the caller gets a valid-looking
                # token and every later write is refused server-side with
                # no hint that the empty plan was the cause.
                raise TransportCallError(
                    "finalize_plan: scope='paths' must declare at least one "
                    "write or delete; an empty plan authorizes nothing"
                )
            arguments["writes"] = list(writes)
            arguments["deletes"] = list(deletes)
        payload = self._call_json("finalize_plan", arguments)
        raw_etags = payload.get("base_etags")
        if raw_etags is None:
            raw_etags = {}
        if not isinstance(raw_etags, Mapping):
            raise TransportCallError(
                f"claude-design finalize_plan returned base_etags as "
                f"{type(raw_etags).__name__}, expected an object"
            )
        etags = {str(key): _as_text(value) for key, value in raw_etags.items()}
        plan_token = _as_text(payload.get("plan_token"))
        if not plan_token:
            # An empty token is not "no token": it is marshalled as an
            # explicit `plan_token: ""` on every later write rather than
            # omitted, so the grant fails at the server instead of falling
            # back to the interactive path.
            raise TransportCallError(
                "claude-design finalize_plan returned no plan_token"
            )
        return PlanHandle(
            plan_token=plan_token,
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
        require_conditional("create_support_js", [entry], allow_leaf=False)
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
        # Materialize once, then validate and marshal *that* list: an
        # iterator drained by validation would marshal as [] and write
        # nothing while the call reported success.
        entries = list(files)
        require_conditional("copy_files", entries, allow_leaf=True)
        arguments: dict[str, Any] = {
            "project_id": project_id,
            "files": [dict(entry) for entry in entries],
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
        entries = list(files)  # see copy_files: materialize once, then use it
        require_conditional("write_files", entries, allow_leaf=False)
        arguments: dict[str, Any] = {
            "project_id": project_id,
            "files": [dict(entry) for entry in entries],
        }
        if plan_token is not None:
            arguments["plan_token"] = plan_token
        return self._call_json("write_files", arguments)

    def read_file(
        self,
        *,
        project_id: str,
        path: str,
        if_none_match: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> FileRead:
        arguments: dict[str, Any] = {"project_id": project_id, "path": path}
        if if_none_match is not None:
            arguments["if_none_match"] = if_none_match
        if offset is not None:
            arguments["offset"] = offset
        if limit is not None:
            arguments["limit"] = limit
        # The body is deliberately NOT sanitized -- do not "restore" that.
        # sanitize_payload replaces an entire string that mentions the
        # tokenized host, so a deck legitimately referencing it would come
        # back as a 40-character constant and then be written over the
        # repo's prototype. A file body is user-authored *content*, not a
        # control envelope that could surface a live tokenized URL, and the
        # I/O matrix specifies it entity-decoded and otherwise verbatim.
        # The envelope around it is still covered: no other read_file field
        # crosses the boundary unparsed.
        return parse_read_response(self._raw_text("read_file", arguments))

    def render_preview(self, *, project_id: str, path: str) -> PreviewRef:
        payload = self._call_json(
            "render_preview", {"project_id": project_id, "path": path}
        )
        return PreviewRef(
            open_url=_as_text(payload.get("open_url")),
            expires_at=_as_optional_text(payload.get("expires_at")),
        )

    # --- the call pipeline ---------------------------------------------

    def _raw_text(self, tool: str, arguments: Mapping[str, Any]) -> str:
        """One tool call; raises ``TransportCallError`` on a server-side
        error. Returns the answer verbatim -- callers sanitize.

        The error text is sanitized here rather than by the caller: it is
        the one server string that leaves this class without passing
        through ``_call_text`` / ``_call_json``, and an error message
        quoting a ``serve_url`` back at us would otherwise reach stderr
        intact (NFR-04)."""
        caller = self._caller
        result = (
            caller.call_tool(tool, arguments)
            if caller is not None
            else self._call_via_mcp_sdk(tool, arguments)
        )
        if result.is_error:
            raise TransportCallError(
                f"claude-design {tool} failed: {sanitize_payload(result.text)}"
            )
        return result.text

    def _call_text(self, tool: str, arguments: Mapping[str, Any]) -> str:
        """A prose answer (today: the design-system prompt).

        Deliberately **not** run through ``sanitize_payload``, for the same
        content-versus-envelope reason ``read_file``'s body is exempt. The
        redaction replaces a whole string that merely *mentions* the
        tokenized host, and the real Modernist prompt mentions it once --
        in the rule forbidding it ("Never put a ``serve_url`` (or any
        ``*.claudeusercontent.com`` link) in user-visible text..."). Scrubbing
        here therefore replaced all 33,985 characters of the mandatory
        pre-write gate with a 33-character placeholder. Verified live
        2026-07-25: the prompt carries that one documentary mention and no
        tokenized URL (no ``?t=`` token shape anywhere in it).

        NFR-04 is unaffected. A prose answer has no ``serve_url`` key to
        drop, Herald never surfaces the prompt as a link, and the paths that
        really can carry one -- every JSON envelope via ``_call_json``, and
        ``render_preview``'s structurally serve_url-free ``PreviewRef`` --
        keep their full scrubbing."""
        return self._raw_text(tool, arguments)

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

        A rejected credential becomes ``AuthError`` naming ``/design-login``;
        every other SDK/connection failure becomes
        ``TransportUnreachableError`` naming the endpoint. Both messages
        carry the flattened leaves of an ``ExceptionGroup``, and both are
        scrubbed of the token first, so no exception text can ever carry
        it."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass  # no loop running: `asyncio.run` is free to make one
        else:
            # `asyncio.run` cannot nest, and the failure it raises reads as
            # a connection problem. Say what actually happened instead:
            # `TransportError` rather than `TransportUnreachableError`,
            # because nothing was attempted against the endpoint.
            raise TransportError(
                f"the synchronous claude-design transport cannot run inside "
                f"a live event loop (calling {tool}); drive it from a "
                f"worker thread, or await the SDK directly"
            )

        credential = self._credential
        if credential is None:
            credential = resolve_design_credential()
            self._credential = credential
        try:
            return asyncio.run(
                _call_tool_async(self._url, credential, tool, dict(arguments))
            )
        except ImportError as exc:
            # A broken install, not an outage. `mcp` is a declared runtime
            # dependency, so reporting this as "endpoint unreachable" would
            # send the operator to look at the network.
            raise TransportError(
                f"the mcp SDK is not importable ({exc}); pyforge-herald "
                f"declares mcp>=1.28.1 as a runtime dependency -- reinstall "
                f"the environment"
            ) from None
        except Exception as exc:  # noqa: BLE001 - every SDK failure maps here
            detail = _scrub_token(_describe(exc), credential.access_token)
            if _indicates_auth_failure(_flatten(exc), detail):
                raise AuthError(
                    f"claude-design rejected the stored credential calling "
                    f"{tool}: {detail} -- {_REMEDIATION}"
                ) from None
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
