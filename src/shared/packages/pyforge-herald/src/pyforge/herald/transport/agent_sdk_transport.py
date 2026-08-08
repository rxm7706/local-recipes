"""The fallback ``DesignTransport`` adapter: a headless nested Claude Code
turn used as a mechanical MCP relay (Story 1.3, FR-22).

Story 1.2's live spike proved the primary path (``McpTransport``) reaches
``claude-design`` from a plain, non-interactive Python process, so
``AgentSdkTransport`` is **not** V1's shipped default -- it exists for the
scenario the spike ruled out for *this* environment but cannot rule out for
every environment: a sandbox, CI runner, or air-gapped host where the raw
``mcp`` SDK cannot reach ``api.anthropic.com/v1/design/mcp`` directly, but a
locally-installed, already-authenticated ``claude`` CLI still can, on
Herald's behalf.

**What "reusing the stored login" means here.** Unlike ``McpTransport``,
this adapter never reads ``~/.claude/.credentials.json`` and never touches a
bearer token at all -- NFR-05's "no new credential storage" is satisfied by
construction, not by a scrub. The nested ``claude -p`` process authenticates
itself, the same way any other headless Claude Code invocation on this
machine does. No token value can appear in this module's output because none
ever enters it.

**Why this is still "no LLM in the loop" (bridge-protocol.md's deterministic-
bridge constraint).** The nested turn is not asked to decide anything. The
relay prompt (``_relay_prompt``) names one exact tool and one exact JSON
argument object and instructs the nested agent to call it once, via its
``claude-design`` MCP connection, and echo the raw tool result verbatim
between two fixed sentinel markers -- nothing else. It is a mechanical
protocol bridge standing in for a raw socket, not a decision-maker: the
*port* still marshals every argument and interprets every answer exactly as
``McpTransport`` does, reusing the same ``sanitize_payload`` /
``parse_read_response`` / ``require_conditional`` invariants from
``transport.base``.

**The process-launch seam is always injected, and the real one is never run
in this package's tests or by this module's own import.** Two prior
development attempts at this story died silently, mid-thinking, with a
nested ``claude -p`` still reported ``Running...`` past its own ``timeout
90`` -- asking an agent session to spawn an agent session is the one thing
this story's *subject* requires and the one thing that reliably kills the
session *building* it. ``AgentSdkTransport`` therefore always takes its
launcher via ``launcher: AgentProcessLauncher | None = None`` and only
constructs the real ``SubprocessAgentLauncher`` lazily, inside the call path
that actually needs one -- constructing a transport, or importing this
module, spawns nothing. Every test in this package injects a hand-written
fake; live verification against a real nested agent is an operator-run
integration check, deliberately outside this suite (mirrors Story 1.2's
``test_live_design_spike.py`` boundary, but even that opt-in form is not
shipped here -- the crash history above is why).

**Tool allowlist (FR-22).** Each relay grants the launcher exactly one MCP
tool name, scoped to the single call being made -- never the whole
``claude-design`` surface -- via ``ALLOWED_TOOL_PREFIX + tool``.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from ..errors import AuthError, TransportCallError, TransportUnreachableError
from .base import (
    FileRead,
    ListedFile,
    PlanHandle,
    PreviewRef,
    ProjectRef,
    ToolResult,
    as_optional_text,
    as_text,
    parse_read_response,
    require_conditional,
    sanitize_payload,
)

ALLOWED_TOOL_PREFIX = "mcp__claude-design__"
"""The nested agent's ``--allowedTools`` entry is scoped to exactly one
fully-qualified MCP tool name per call -- FR-22's allowlist, enforced at the
narrowest possible grain."""

# Port method name -> MCP tool name (identical translation to McpTransport's
# single divergence; kept as its own constant here rather than imported,
# since importing across adapter modules is exactly what the determinism
# boundary (AD-3/AD-4) forbids for bridge-core, and adapters are not exempt
# from keeping that boundary meaningful -- each stands alone).
GET_DESIGN_PROMPT_TOOL = "get_claude_design_prompt"

_RESULT_OPEN = "<<<HERALD_TOOL_RESULT>>>"
_RESULT_CLOSE = "<<<END_HERALD_TOOL_RESULT>>>"
_ERROR_OPEN = "<<<HERALD_TOOL_ERROR>>>"
_ERROR_CLOSE = "<<<END_HERALD_TOOL_ERROR>>>"
"""Fixed sentinel markers the relay prompt instructs the nested agent to
wrap its answer in. Deterministic string search, not parsing the agent's own
prose -- the markers are chosen to be vanishingly unlikely to occur in a
legitimate tool answer, and if one ever does, ``_parse_relay`` fails closed
(``TransportUnreachableError``) rather than guess which occurrence is the
real boundary."""

_RESULT_RE = re.compile(
    re.escape(_RESULT_OPEN) + r"(.*?)" + re.escape(_RESULT_CLOSE), re.DOTALL
)
_ERROR_RE = re.compile(
    re.escape(_ERROR_OPEN) + r"(.*?)" + re.escape(_ERROR_CLOSE), re.DOTALL
)

_AUTH_DENIAL_RE = re.compile(
    r"not (?:currently )?(?:logged|authenticated)|please (?:log|sign) in"
    r"|/design-login|no (?:stored|active) (?:credential|session|login)",
    re.IGNORECASE,
)
"""Markers of an auth denial *inside a successfully parsed relay answer* --
distinct from a launch failure. The nested agent has no way to hand back a
structured 401; if its own ``claude-design`` connection is unauthenticated
it can only say so in prose, in whichever wrapper (result or error) it used."""


@dataclass(frozen=True)
class AgentLaunchResult:
    """One nested-agent turn's raw output: what it printed to stdout, and
    whether the process itself reported failure (a non-zero exit, not a
    tool-level error -- those are still inside a well-formed stdout)."""

    stdout: str
    failed: bool
    detail: str = ""


@runtime_checkable
class AgentProcessLauncher(Protocol):
    """The injectable process-launch seam (Story 1.3's hard constraint).

    ``run`` performs exactly one headless turn: send ``prompt``, grant only
    ``allowed_tools``, return the turn's raw output. The real implementation
    (``SubprocessAgentLauncher``) shells out to the ``claude`` CLI; every
    test in this package injects a hand-written fake instead."""

    def run(
        self, *, prompt: str, allowed_tools: Sequence[str]
    ) -> AgentLaunchResult: ...


class SubprocessAgentLauncher:
    """The real ``AgentProcessLauncher``: one headless ``claude -p`` turn.

    **No test in this package ever lets this class reach a real
    ``subprocess.run`` call** -- see the module docstring. Its own tests
    patch ``subprocess.run`` itself to exercise the error-mapping branches
    below with nothing actually spawned; ``AgentSdkTransport``'s tests never
    construct this class at all. Reuses whatever login the local ``claude``
    CLI already holds; this class never reads, passes, or constructs a
    credential of its own.

    ``timeout`` bounds the whole subprocess (default 120s: a single
    mechanical relay turn, not an open-ended agent session) -- a hang here
    must not become a hang in whatever calls Herald."""

    def __init__(self, *, executable: str = "claude", timeout: float = 120.0) -> None:
        self._executable = executable
        self._timeout = timeout

    def run(self, *, prompt: str, allowed_tools: Sequence[str]) -> AgentLaunchResult:
        args = [
            self._executable,
            "-p",
            prompt,
            "--allowedTools",
            ",".join(allowed_tools),
        ]
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return AgentLaunchResult(
                stdout="",
                failed=True,
                detail=f"the nested agent turn exceeded {self._timeout}s ({exc})",
            )
        except OSError as exc:
            # Covers FileNotFoundError (the executable is not on PATH) and
            # every other way launching a subprocess can fail (permission
            # denied, a transient fork/exec resource failure, ...) -- any of
            # these must become a HeraldError, not a bare OSError escaping
            # the AD-6 boundary cli.dispatch catches.
            return AgentLaunchResult(
                stdout="",
                failed=True,
                detail=f"could not launch the {self._executable!r} CLI ({exc})",
            )
        if completed.returncode != 0:
            return AgentLaunchResult(
                stdout=completed.stdout,
                failed=True,
                detail=(completed.stderr or completed.stdout or "").strip()[-2000:],
            )
        return AgentLaunchResult(stdout=completed.stdout, failed=False)


def _relay_prompt(tool: str, arguments: Mapping[str, Any]) -> str:
    """The deterministic, mechanical relay instruction (see module doc:
    this is a protocol bridge, not a decision-maker). ``arguments`` is
    rendered via ``sanitize_payload`` first, so a caller error that put
    tokenized material into an argument (never expected, never observed)
    cannot ride the prompt itself into a process log."""
    safe_arguments = sanitize_payload(dict(arguments))
    payload = json.dumps(safe_arguments, sort_keys=True)
    return (
        f"Call the MCP tool {tool!r} on the claude-design server with "
        f"exactly this JSON arguments object and no others: {payload}\n"
        f"Do not call any other tool. Do not summarize, explain, or add any "
        f"text of your own.\n"
        f"If the call succeeds, print {_RESULT_OPEN} then the tool's raw "
        f"result text verbatim then {_RESULT_CLOSE}, and nothing else.\n"
        f"If the call fails, print {_ERROR_OPEN} then the tool's raw error "
        f"text verbatim then {_ERROR_CLOSE}, and nothing else."
    )


def _parse_relay(tool: str, output: str, *, prompt: str) -> ToolResult:
    """The relay contract's own wire format: exactly one sentinel-wrapped
    block, result or error, in ``output``. Neither match, both matching, or
    an empty capture inside a match are each a protocol failure -- the
    nested agent did not honour the mechanical instruction, and guessing at
    intent here would silently launder a broken relay into a plausible
    answer.

    Review finding: ``_relay_prompt``'s own instructional text necessarily
    contains a COMPLETE, self-matching sentinel pair for both the result
    and the error marker (it has to, to tell the nested agent what to
    print) -- if the nested agent ever echoes any part of that prompt back
    to stdout before its real answer (a plausible headless-CLI behaviour
    this module never previously ruled out), the sentinel regexes would
    happily match the ECHOED INSTRUCTIONS instead of the genuine wrapped
    answer, for ``_call_text`` callers (``get_design_prompt``) silently
    returning garbled prose as if it were the real result. Since the exact
    prompt text sent for THIS call is known here, a leading echo of it is
    stripped before searching -- the nested agent's real answer, if it
    echoes anything at all, always follows what it echoed, never precedes
    it. A partial/reformatted echo (wrapped, reflowed, missing a trailing
    newline) will not match this exact prefix check and falls through to
    searching the whole output, same as this function's behaviour before
    this fix -- a best-effort narrowing of the KNOWN, demonstrated
    collision, not a claim of eliminating every conceivable echo shape."""
    output = output.removeprefix(prompt)
    result_match = _RESULT_RE.search(output)
    error_match = _ERROR_RE.search(output)
    if result_match and error_match:
        raise TransportUnreachableError(
            f"claude-design {tool} (via the nested agent relay): the "
            f"response carried both a result and an error marker; the "
            f"relay contract was not honoured"
        )
    if result_match:
        return ToolResult(text=result_match.group(1).strip(), is_error=False)
    if error_match:
        return ToolResult(text=error_match.group(1).strip(), is_error=True)
    raise TransportUnreachableError(
        f"claude-design {tool} (via the nested agent relay): no "
        f"{_RESULT_OPEN!r} or {_ERROR_OPEN!r} marker found in the nested "
        f"agent's output; the relay contract was not honoured"
    )


class AgentSdkTransport:
    """``DesignTransport`` over a headless nested ``claude`` turn (FR-22,
    the fallback -- see module doc for why and when).

    ``launcher`` is the injectable process-launch seam; omit it for the real
    ``SubprocessAgentLauncher``, constructed lazily on first call so
    building a transport never spawns a process. Marshalling, sanitization,
    and FR-24 validation are identical to ``McpTransport``'s, because both
    adapters uphold the same three shared invariants from ``transport.base``
    -- only the low-level relay differs."""

    def __init__(self, *, launcher: AgentProcessLauncher | None = None) -> None:
        self._launcher = launcher

    # --- the 9 port methods -------------------------------------------

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
            project_id=as_text(payload.get("project_id")),
            url=as_text(payload.get("url")),
        )

    def finalize_plan(
        self,
        *,
        project_id: str,
        writes: Sequence[str] = (),
        deletes: Sequence[str] = (),
        scope: str = "paths",
    ) -> PlanHandle:
        if scope == "project":
            if writes or deletes:
                raise TransportCallError(
                    "finalize_plan: scope='project' already authorizes the "
                    "whole project and must not also declare writes/deletes"
                )
            arguments: dict[str, Any] = {"project_id": project_id, "scope": "project"}
        elif scope == "paths":
            if not writes and not deletes:
                raise TransportCallError(
                    "finalize_plan: scope='paths' must declare at least one "
                    "write or delete; an empty plan authorizes nothing"
                )
            arguments = {
                "project_id": project_id,
                "writes": list(writes),
                "deletes": list(deletes),
            }
        else:
            raise TransportCallError(
                f"finalize_plan: unknown scope {scope!r}; expected 'paths' or 'project'"
            )
        payload = self._call_json("finalize_plan", arguments)
        raw_etags = payload.get("base_etags")
        if raw_etags is None:
            raw_etags = {}
        if not isinstance(raw_etags, Mapping):
            raise TransportCallError(
                f"claude-design finalize_plan returned base_etags as "
                f"{type(raw_etags).__name__}, expected an object"
            )
        etags = {str(key): as_text(value) for key, value in raw_etags.items()}
        plan_token = as_text(payload.get("plan_token"))
        if not plan_token:
            raise TransportCallError(
                "claude-design finalize_plan returned no plan_token"
            )
        return PlanHandle(plan_token=plan_token, base_etags=MappingProxyType(etags))

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
        entries = list(files)
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
        # Not sanitized -- content, not envelope. Same exemption and same
        # rationale as McpTransport.read_file: sanitize_payload replaces a
        # whole string that merely mentions the tokenized host, and a
        # legitimate deck body would come back corrupted.
        return parse_read_response(self._raw_text("read_file", arguments))

    def render_preview(self, *, project_id: str, path: str) -> PreviewRef:
        payload = self._call_json(
            "render_preview", {"project_id": project_id, "path": path}
        )
        return PreviewRef(
            open_url=as_text(payload.get("open_url")),
            expires_at=as_optional_text(payload.get("expires_at")),
        )

    def list_files(self, *, project_id: str) -> Sequence[ListedFile]:
        payload = self._call_json("list_files", {"project_id": project_id})
        raw_files = payload.get("files")
        if raw_files is None:
            raw_files = []
        if not isinstance(raw_files, Sequence) or isinstance(raw_files, (str, bytes)):
            raise TransportCallError(
                f"claude-design list_files returned files as "
                f"{type(raw_files).__name__}, expected a list"
            )
        files: list[ListedFile] = []
        for entry in raw_files:
            if not isinstance(entry, Mapping):
                raise TransportCallError(
                    f"claude-design list_files returned a non-object file "
                    f"entry ({type(entry).__name__})"
                )
            raw_size = entry.get("size")
            size = (
                raw_size
                if isinstance(raw_size, int) and not isinstance(raw_size, bool)
                else None
            )
            files.append(
                ListedFile(
                    path=as_text(entry.get("path")),
                    etag=as_text(entry.get("etag")),
                    size=size,
                )
            )
        return files

    # --- the relay pipeline ---------------------------------------------

    def _raw_text(self, tool: str, arguments: Mapping[str, Any]) -> str:
        """One relay turn; raises the appropriate ``HeraldError`` subclass.

        ``launcher.run`` failing outright (process not found, non-zero
        exit, timeout) is ``TransportUnreachableError`` -- the nested agent
        itself could not be reached or run, distinct from a well-formed
        relay answer reporting a tool-level failure
        (``TransportCallError``, mirroring ``McpTransport``'s identical
        distinction) or an auth denial found inside either
        (``AuthError``, checked first since it is the one error that must
        halt rather than retry -- ``bridge-protocol.md`` § Watch
        parameters)."""
        launcher = self._launcher
        if launcher is None:
            launcher = SubprocessAgentLauncher()
            self._launcher = launcher
        prompt = _relay_prompt(tool, arguments)
        result = launcher.run(
            prompt=prompt,
            allowed_tools=[ALLOWED_TOOL_PREFIX + tool],
        )
        if result.failed:
            detail = sanitize_payload(result.detail)
            if _AUTH_DENIAL_RE.search(detail):
                raise AuthError(
                    f"claude-design {tool} (via the nested agent relay): "
                    f"the local claude CLI reported no usable login: "
                    f"{detail} -- run /design-login in Claude Code"
                )
            raise TransportUnreachableError(
                f"could not run the nested agent relay for claude-design "
                f"{tool}: {detail}"
            )
        tool_result = _parse_relay(tool, result.stdout, prompt=prompt)
        text = (
            sanitize_payload(tool_result.text)
            if tool_result.is_error
            else tool_result.text
        )
        if tool_result.is_error:
            if _AUTH_DENIAL_RE.search(text):
                raise AuthError(
                    f"claude-design {tool} (via the nested agent relay) "
                    f"reported no usable login: {text} -- run "
                    f"/design-login in Claude Code"
                )
            raise TransportCallError(f"claude-design {tool} failed: {text}")
        return tool_result.text

    def _call_text(self, tool: str, arguments: Mapping[str, Any]) -> str:
        """A prose answer -- not sanitized, for the identical reason
        ``McpTransport._call_text`` is not: the real Modernist prompt
        mentions the tokenized host exactly once, in the rule forbidding
        it, and whole-string redaction there would destroy the mandatory
        pre-write gate rather than protect anything."""
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
