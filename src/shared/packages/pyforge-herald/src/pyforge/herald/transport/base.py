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

Three invariants live here rather than in any one adapter, because Story
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
  forms land on one ``FileRead``. The server also caps a read at 256 KiB
  and advertises the window it actually returned (``lines="1-208"
  total_lines="212"``), so ``FileRead`` carries that window and a
  ``truncated`` flag: a partial read must never be mistaken for the file.
* ``require_conditional`` -- FR-24's pre-flight check, run before any
  network call so an unconditional write cannot reach the server at all.

FR-24 is also enforced structurally in the port's own signatures:
``create_support_js`` takes a *required* ``if_match``, and the ``files``
entries of ``write_files`` / ``copy_files`` go through
``require_conditional``. ``read_file``'s ``if_none_match`` stays optional
-- a first read legitimately has no prior etag -- and so do its
``offset`` / ``limit``, which page a file past the size cap.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ..errors import TransportCallError, UnconditionalWriteError

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
_LINES_RE = re.compile(r"\s*(\d+)\s*-\s*(\d+)\s*")


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
    wire, which is exactly what makes ``herald deck watch`` cheap.

    ``first_line`` / ``last_line`` / ``total_lines`` record the window the
    server says it returned, read off the wrapper's ``lines="A-B"`` and
    ``total_lines`` attributes. They are None when the answer declared no
    window (the unchanged form, or a small file the server answered whole),
    which is why they default to None and callers test ``truncated``
    instead of comparing them.

    **When ``truncated`` is True, ``body`` is a window and not the file.**
    The caller must not treat it as whole content, and must not reuse
    ``etag`` as the ``if_match`` of a whole-file write: the etag proves
    nothing about the bytes outside the window, so rebuilding the file from
    a partial view would silently store only the part that fitted. Page the
    rest with ``read_file``'s ``offset``, or move the file server-side with
    ``copy_files``, which is exempt from the size cap."""

    path: str
    etag: str
    body: str | None
    unchanged: bool
    first_line: int | None = None
    last_line: int | None = None
    total_lines: int | None = None

    @property
    def truncated(self) -> bool:
        """True unless the returned window provably covers the whole file.

        A declared ``total_lines`` with no parsable window counts as
        truncated: coverage that cannot be proven is not assumed."""
        if self.total_lines is None:
            return False
        if self.last_line is None:
            return True
        first = 1 if self.first_line is None else self.first_line
        return first > 1 or self.last_line < self.total_lines


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
        self,
        *,
        project_id: str,
        path: str,
        if_none_match: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> FileRead:
        """Read one file, optionally windowed. ``offset`` (1-based first
        line) and ``limit`` page a file past the server's 256 KiB cap; the
        answer's ``truncated`` says whether the window covered it."""
        ...

    def render_preview(self, *, project_id: str, path: str) -> PreviewRef: ...


def sanitize_payload(payload: Any) -> Any:
    """Recursively strip tokenized-preview material from a tool answer.

    Drops every ``serve_url`` key at any depth, and replaces any string
    mentioning ``claudeusercontent.com`` with ``REDACTED`` in full.
    Mappings become plain dicts and sequences become lists; scalars pass
    through unchanged. Idempotent, so it is safe to apply to a raw text
    answer and again to the object parsed out of it.

    The host is matched case-insensitively, because DNS is: an answer
    naming ``ABC123.ClaudeUserContent.com`` resolves to the same tokenized
    origin. Mapping *keys* are scrubbed as well as values -- a server that
    ever keyed a map by URL would otherwise carry one straight through.

    Replacing the whole string is deliberate. A partially-scrubbed URL
    still reads as a URL and invites a paste; a wholly-redacted value
    cannot. The cost is that any control payload legitimately naming the
    host is redacted wholesale rather than corrupted subtly -- fail closed,
    visibly. A *file body* is exempt from that trade and never passed here;
    see ``McpTransport.read_file``."""
    if isinstance(payload, Mapping):
        return {
            sanitize_payload(key): sanitize_payload(value)
            for key, value in payload.items()
            if key != SERVE_URL_KEY
        }
    if isinstance(payload, (list, tuple)):
        return [sanitize_payload(item) for item in payload]
    if isinstance(payload, str) and TOKENIZED_PREVIEW_HOST in payload.lower():
        return REDACTED
    return payload


def _as_text(value: Any) -> str:
    """A wire field as text, or ``""`` when the server sent a non-string.

    ``str(value)`` is the trap this exists to avoid: a JSON ``null`` would
    become the literal ``"None"``, a truthy four-character value that sails
    straight through FR-24's etag check. Anything that is not already a
    string is treated as absent."""
    return value if isinstance(value, str) else ""


def _as_optional_text(value: Any) -> str | None:
    """``_as_text`` for a field the port models as ``str | None``, where
    "the server sent something unusable" and "the server sent nothing" are
    the same answer."""
    return value if isinstance(value, str) else None


def _decode_entities(text: str) -> str:
    """Undo the server's body escaping. ``&amp;`` is decoded LAST so an
    escaped ``&amp;lt;`` in the original file does not become a ``<``."""
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _parse_window(
    attributes: Mapping[str, str],
) -> tuple[int | None, int | None, int | None]:
    """The wrapper's ``lines="A-B"`` / ``total_lines`` window, or Nones.

    An attribute that does not parse is reported as "no declared window"
    rather than raised on: the wrapper is the wire contract, the window is
    an advisory the server attaches to a capped read, and ``truncated``
    already fails closed on a half-declared one."""
    first: int | None = None
    last: int | None = None
    total: int | None = None
    match = _LINES_RE.fullmatch(attributes.get("lines", ""))
    if match is not None:
        first, last = int(match.group(1)), int(match.group(2))
    raw_total = attributes.get("total_lines", "").strip()
    if raw_total.isdigit():
        total = int(raw_total)
    return first, last, total


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
            path=_as_text(payload.get("path")),
            etag=_as_text(payload.get("etag")),
            body=None,
            unchanged=True,
        )

    opening = _READ_OPEN_RE.search(text)
    if opening is None:
        raise TransportCallError(
            f"read_file returned no <{_READ_TAG}> wrapper to parse"
        )
    # The FIRST close tag after the opening is always the right one: the
    # server entity-escapes the body, so the body cannot contain a literal
    # close tag. Searching from the end instead would swallow a trailer
    # that merely mentions the tag into the file content.
    close_at = text.find(_READ_CLOSE, opening.end())
    if close_at < 0:
        raise TransportCallError(
            f"read_file returned no <{_READ_TAG}> wrapper to parse"
        )
    attributes = dict(_ATTR_RE.findall(opening.group(1)))
    first_line, last_line, total_lines = _parse_window(attributes)
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
        first_line=first_line,
        last_line=last_line,
        total_lines=total_lines,
    )


def _is_etag(value: Any) -> bool:
    """An etag precondition is a non-empty ``str`` -- and only that.

    ``"0"`` is legitimate (assert the path does not exist), so the test
    cannot be truthiness; ``5``, ``True`` and ``["x"]`` are shapes the
    server never sends and must not be accepted as preconditions."""
    return isinstance(value, str) and bool(value)


def _is_leaf_etag_map(value: Any) -> bool:
    """``leaf_if_match`` maps every leaf under a folder destination to its
    own etag, so an empty map preconditions nothing and a non-string value
    preconditions the wrong thing."""
    return (
        isinstance(value, Mapping)
        and bool(value)
        and all(_is_etag(item) for item in value.values())
    )


def require_conditional(
    tool: str, files: Sequence[Mapping[str, Any]], *, allow_leaf: bool
) -> None:
    """FR-24: refuse an unconditional write before any network call.

    Lives here, not in one adapter, because Story 1.3's
    ``AgentSdkTransport`` has to refuse exactly the same entries -- this is
    the most load-bearing of the shared invariants.

    ``files`` must be an already-materialized sequence: a caller that
    validates a generator here would hand an exhausted one to marshalling
    and write nothing at all while reporting success. An empty sequence is
    refused for the same reason -- a no-op write dressed up as a result is
    exactly what FR-24 exists to prevent -- and so is a non-mapping entry,
    which would otherwise escape the ``HeraldError`` hierarchy as an
    ``AttributeError``."""
    if not files:
        raise UnconditionalWriteError(
            f"{tool}: no file entries to write (FR-24); an empty write "
            f"would report success without writing anything"
        )
    keys = ("if_match", "leaf_if_match") if allow_leaf else ("if_match",)
    for index, entry in enumerate(files):
        if not isinstance(entry, Mapping):
            raise UnconditionalWriteError(
                f"{tool}: entry {index} is a {type(entry).__name__}, not a "
                f"mapping, so it declares no etag precondition (FR-24)"
            )
        if _is_etag(entry.get("if_match")) or (
            allow_leaf and _is_leaf_etag_map(entry.get("leaf_if_match"))
        ):
            continue
        subject = entry.get("dest") or entry.get("path") or f"entry {index}"
        wanted = " or ".join(repr(key) for key in keys)
        raise UnconditionalWriteError(
            f"{tool}: {subject!r} carries no {wanted} etag precondition "
            f'(FR-24); pass "0" to assert the path does not exist'
        )
