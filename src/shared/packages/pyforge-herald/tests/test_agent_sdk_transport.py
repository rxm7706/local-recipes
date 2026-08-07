"""``AgentSdkTransport`` marshalling, FR-24 enforcement, and the relay
protocol (Story 1.3).

Every ``AgentSdkTransport`` test injects a hand-written ``FakeLauncher``.
``SubprocessAgentLauncher``'s own tests patch out ``subprocess.run`` itself,
so no real process is ever spawned anywhere in this file (see the module
docstring in ``agent_sdk_transport.py`` for why that constraint is hard: two
prior development attempts died silently spawning a real nested agent)."""

from __future__ import annotations

import subprocess

import pytest

from pyforge.herald.errors import (
    AuthError,
    TransportCallError,
    TransportUnreachableError,
    UnconditionalWriteError,
)
from pyforge.herald.transport import AgentSdkTransport, DesignTransport
from pyforge.herald.transport.agent_sdk_transport import (
    ALLOWED_TOOL_PREFIX,
    GET_DESIGN_PROMPT_TOOL,
    AgentLaunchResult,
    SubprocessAgentLauncher,
    _relay_prompt,
)
from pyforge.herald.transport.base import REDACTED, TOKENIZED_PREVIEW_HOST

_SERVE_URL = f"https://abc123.{TOKENIZED_PREVIEW_HOST}/p/x?token=fake-preview-token"


def _ok(text: str) -> AgentLaunchResult:
    return AgentLaunchResult(
        stdout=f"<<<HERALD_TOOL_RESULT>>>{text}<<<END_HERALD_TOOL_RESULT>>>",
        failed=False,
    )


def _tool_error(text: str) -> AgentLaunchResult:
    return AgentLaunchResult(
        stdout=f"<<<HERALD_TOOL_ERROR>>>{text}<<<END_HERALD_TOOL_ERROR>>>",
        failed=False,
    )


class FakeLauncher:
    """Records ``(prompt, allowed_tools)`` per call; answers keyed by the
    single tool name each call's ``allowed_tools`` names (the transport
    always grants exactly one, per FR-22) -- mirrors ``FakeCaller``'s
    per-tool canned-response shape at one layer up the stack."""

    def __init__(self, responses=None):
        self.responses = dict(responses or {})
        self.calls: list[tuple[str, list[str]]] = []

    def run(self, *, prompt: str, allowed_tools):
        tool = allowed_tools[0].removeprefix(ALLOWED_TOOL_PREFIX)
        self.calls.append((prompt, list(allowed_tools)))
        canned = self.responses.get(tool)
        if canned is None:
            return _ok("{}")
        return canned

    def tool_calls(self) -> list[str]:
        return [
            tools[0].removeprefix(ALLOWED_TOOL_PREFIX) for _prompt, tools in self.calls
        ]


@pytest.fixture
def fake_launcher():
    def _make(responses=None) -> FakeLauncher:
        return FakeLauncher(responses)

    return _make


def _transport(fake_launcher_factory, responses=None):
    launcher = fake_launcher_factory(responses)
    return AgentSdkTransport(launcher=launcher), launcher


# --- protocol conformance ---------------------------------------------------


def test_agent_sdk_transport_conforms_to_the_design_transport_protocol():
    assert isinstance(AgentSdkTransport(), DesignTransport)


def test_constructing_the_transport_spawns_no_process(monkeypatch):
    """Building a transport (no calls made) must never touch ``subprocess`` --
    the hard constraint is "never spawned during development or in any
    test", and this is the seam that would prove a regression the loudest."""

    def _forbidden(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called by construction alone")

    monkeypatch.setattr(subprocess, "run", _forbidden)
    AgentSdkTransport()
    AgentSdkTransport(launcher=None)


# --- marshalling: tool names + argument keys, allowlist scoping ------------


def test_get_design_prompt_maps_to_the_get_claude_design_prompt_tool(fake_launcher):
    transport, launcher = _transport(
        fake_launcher, {"get_claude_design_prompt": _ok("PROMPT BODY")}
    )
    prompt = transport.get_design_prompt(design_system_id="ds")
    assert prompt == "PROMPT BODY"
    assert launcher.tool_calls() == ["get_claude_design_prompt"]
    assert GET_DESIGN_PROMPT_TOOL == "get_claude_design_prompt"


def test_each_call_grants_exactly_one_allowlisted_tool(fake_launcher):
    """FR-22: the allowlist is scoped to the single tool being called, never
    the whole claude-design surface."""
    transport, launcher = _transport(
        fake_launcher, {"create_project": _ok('{"project_id":"p","url":"u"}')}
    )
    transport.create_project(name="X")
    _prompt, allowed = launcher.calls[0]
    assert allowed == [f"{ALLOWED_TOOL_PREFIX}create_project"]


def test_create_project_marshals_name_and_design_system_id(fake_launcher):
    transport, launcher = _transport(
        fake_launcher,
        {
            "create_project": _ok(
                '{"project_id": "p-1", "url": "https://claude.ai/design/p/p-1"}'
            )
        },
    )
    ref = transport.create_project(name="PyForge X deck", design_system_id="ds")
    assert ref.project_id == "p-1"
    assert ref.url == "https://claude.ai/design/p/p-1"
    assert '"name": "PyForge X deck"' in launcher.calls[0][0]
    assert '"design_system_id": "ds"' in launcher.calls[0][0]


def test_finalize_plan_paths_scope_returns_plan_and_etags(fake_launcher):
    transport, _launcher = _transport(
        fake_launcher,
        {"finalize_plan": _ok('{"plan_token": "tok", "base_etags": {"a.html": "0"}}')},
    )
    handle = transport.finalize_plan(project_id="p", writes=["a.html"])
    assert handle.plan_token == "tok"
    assert dict(handle.base_etags) == {"a.html": "0"}


def test_finalize_plan_empty_paths_plan_refused_before_any_call(fake_launcher):
    transport, launcher = _transport(fake_launcher)
    with pytest.raises(TransportCallError):
        transport.finalize_plan(project_id="p")
    assert launcher.calls == []


def test_finalize_plan_unknown_scope_refused_before_any_call(fake_launcher):
    transport, launcher = _transport(fake_launcher)
    with pytest.raises(TransportCallError):
        transport.finalize_plan(project_id="p", writes=["x"], scope="bogus")
    assert launcher.calls == []


def test_finalize_plan_returns_no_plan_token_raises(fake_launcher):
    transport, _ = _transport(
        fake_launcher, {"finalize_plan": _ok('{"base_etags": {}}')}
    )
    with pytest.raises(TransportCallError):
        transport.finalize_plan(project_id="p", writes=["x"])


def test_create_support_js_requires_if_match(fake_launcher):
    transport, launcher = _transport(fake_launcher)
    with pytest.raises(UnconditionalWriteError):
        transport.create_support_js(project_id="p", if_match="")
    assert launcher.calls == []


def test_create_support_js_marshals_conditional_write(fake_launcher):
    transport, launcher = _transport(fake_launcher, {"create_support_js": _ok("{}")})
    transport.create_support_js(project_id="p", if_match="0", plan_token="tok")
    assert launcher.tool_calls() == ["create_support_js"]
    assert '"if_match": "0"' in launcher.calls[0][0]


def test_copy_files_requires_if_match_or_leaf_if_match(fake_launcher):
    transport, launcher = _transport(fake_launcher)
    with pytest.raises(UnconditionalWriteError):
        transport.copy_files(project_id="p", files=[{"dest": "x"}])
    assert launcher.calls == []


def test_copy_files_accepts_leaf_if_match(fake_launcher):
    transport, launcher = _transport(fake_launcher, {"copy_files": _ok("{}")})
    transport.copy_files(
        project_id="p", files=[{"dest": "d/", "leaf_if_match": {"d/x": "0"}}]
    )
    assert launcher.tool_calls() == ["copy_files"]


def test_write_files_requires_if_match_for_every_entry(fake_launcher):
    transport, launcher = _transport(fake_launcher)
    with pytest.raises(UnconditionalWriteError):
        transport.write_files(
            project_id="p", files=[{"path": "a", "if_match": "0"}, {"path": "b"}]
        )
    assert launcher.calls == []


def test_write_files_does_not_drain_a_generator_before_validating(fake_launcher):
    transport, launcher = _transport(fake_launcher, {"write_files": _ok("{}")})

    def entries():
        yield {"path": "a", "if_match": "0"}

    transport.write_files(project_id="p", files=entries())
    assert launcher.tool_calls() == ["write_files"]


def test_read_file_full_response_parsed(fake_launcher):
    transport, _launcher = _transport(
        fake_launcher,
        {
            "read_file": _ok(
                '<untrusted-project-content path="p.html" etag="E1">\nhello\n'
                "</untrusted-project-content>\n(trailer note)"
            )
        },
    )
    read = transport.read_file(project_id="p", path="p.html")
    assert read.path == "p.html"
    assert read.etag == "E1"
    assert read.body == "hello"
    assert read.unchanged is False


def test_read_file_unchanged_short_circuit(fake_launcher):
    transport, _ = _transport(
        fake_launcher,
        {"read_file": _ok('{"unchanged": true, "etag": "E1", "path": "p.html"}')},
    )
    read = transport.read_file(project_id="p", path="p.html", if_none_match="E1")
    assert read.unchanged is True
    assert read.body is None
    assert read.etag == "E1"


def test_read_file_body_is_not_sanitized_content_exemption(fake_launcher):
    body = f"a legitimate deck mentioning {TOKENIZED_PREVIEW_HOST} in prose"
    transport, _ = _transport(
        fake_launcher,
        {
            "read_file": _ok(
                f'<untrusted-project-content path="p" etag="E1">\n{body}\n'
                "</untrusted-project-content>"
            )
        },
    )
    read = transport.read_file(project_id="p", path="p")
    assert read.body == body


def test_render_preview_has_no_serve_url_field(fake_launcher):
    transport, _ = _transport(
        fake_launcher,
        {
            "render_preview": _ok(
                '{"open_url": "https://claude.ai/design/p/p-1", '
                f'"serve_url": "{_SERVE_URL}", "expires_at": "2100-01-01"}}'
            )
        },
    )
    preview = transport.render_preview(project_id="p", path="x")
    assert preview.open_url == "https://claude.ai/design/p/p-1"
    assert not hasattr(preview, "serve_url")
    assert _SERVE_URL not in repr(preview)


# --- the relay protocol itself ----------------------------------------------


def test_relay_prompt_names_exactly_one_tool_and_the_json_arguments():
    prompt = _relay_prompt("create_project", {"name": "X"})
    assert "create_project" in prompt
    assert '"name": "X"' in prompt
    assert "<<<HERALD_TOOL_RESULT>>>" in prompt
    assert "<<<HERALD_TOOL_ERROR>>>" in prompt


def test_relay_prompt_sanitizes_a_tokenized_argument():
    prompt = _relay_prompt("write_files", {"note": _SERVE_URL})
    assert _SERVE_URL not in prompt
    assert REDACTED in prompt


def test_missing_marker_raises_transport_unreachable(fake_launcher):
    transport, _ = _transport(
        fake_launcher,
        {
            "get_claude_design_prompt": AgentLaunchResult(
                stdout="no markers here", failed=False
            )
        },
    )
    with pytest.raises(TransportUnreachableError):
        transport.get_design_prompt()


def test_both_markers_present_raises_transport_unreachable(fake_launcher):
    garbled = "<<<HERALD_TOOL_RESULT>>>x<<<END_HERALD_TOOL_RESULT>>><<<HERALD_TOOL_ERROR>>>y<<<END_HERALD_TOOL_ERROR>>>"
    transport, _ = _transport(
        fake_launcher,
        {"get_claude_design_prompt": AgentLaunchResult(stdout=garbled, failed=False)},
    )
    with pytest.raises(TransportUnreachableError):
        transport.get_design_prompt()


def test_error_marker_raises_transport_call_error(fake_launcher):
    transport, _ = _transport(
        fake_launcher, {"read_file": _tool_error("read file: file not found")}
    )
    with pytest.raises(TransportCallError, match="file not found"):
        transport.read_file(project_id="p", path="missing")


def test_launcher_failure_raises_transport_unreachable(fake_launcher):
    transport, _ = _transport(
        fake_launcher,
        {
            "get_claude_design_prompt": AgentLaunchResult(
                stdout="", failed=True, detail="claude: command not found"
            )
        },
    )
    with pytest.raises(TransportUnreachableError, match="command not found"):
        transport.get_design_prompt()


@pytest.mark.parametrize(
    "detail",
    [
        "not currently logged in to Claude",
        "please log in first",
        "no stored credential found; run /design-login",
    ],
)
def test_launcher_failure_naming_auth_denial_raises_auth_error(fake_launcher, detail):
    transport, _ = _transport(
        fake_launcher,
        {
            "get_claude_design_prompt": AgentLaunchResult(
                stdout="", failed=True, detail=detail
            )
        },
    )
    with pytest.raises(AuthError):
        transport.get_design_prompt()


def test_error_marker_naming_auth_denial_raises_auth_error(fake_launcher):
    transport, _ = _transport(
        fake_launcher,
        {"read_file": _tool_error("no active session; please log in")},
    )
    with pytest.raises(AuthError):
        transport.read_file(project_id="p", path="x")


# --- the real launcher's error-mapping, with subprocess.run patched out ----
#
# None of these spawn a real process -- subprocess.run itself is replaced,
# so `.run()`'s own error-mapping logic is exercised without ever getting
# near a nested `claude` invocation (the hard constraint is "never spawn the
# real nested agent", not "never call this method").


def test_subprocess_agent_launcher_class_is_constructible_but_not_invoked():
    launcher = SubprocessAgentLauncher()
    assert launcher._executable == "claude"
    assert launcher._timeout == 120.0


def test_subprocess_agent_launcher_maps_missing_executable_to_a_failure(monkeypatch):
    def _raise(*args, **kwargs):
        raise FileNotFoundError("no such file: claude")

    monkeypatch.setattr(subprocess, "run", _raise)
    result = SubprocessAgentLauncher().run(prompt="p", allowed_tools=["t"])
    assert result.failed is True
    assert "claude" in result.detail


def test_subprocess_agent_launcher_maps_timeout_to_a_failure(monkeypatch):
    def _raise(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

    monkeypatch.setattr(subprocess, "run", _raise)
    result = SubprocessAgentLauncher(timeout=1).run(prompt="p", allowed_tools=["t"])
    assert result.failed is True
    assert "1" in result.detail


def test_subprocess_agent_launcher_maps_permission_denied_to_a_failure(monkeypatch):
    """A launch-time OSError beyond FileNotFoundError (permission denied, a
    fork/exec resource failure, ...) must not escape as a bare OSError."""

    def _raise(*args, **kwargs):
        raise PermissionError("permission denied")

    monkeypatch.setattr(subprocess, "run", _raise)
    result = SubprocessAgentLauncher().run(prompt="p", allowed_tools=["t"])
    assert result.failed is True
    assert "permission denied" in result.detail


def test_subprocess_agent_launcher_maps_nonzero_exit_to_a_failure(monkeypatch):
    class _Completed:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed())
    result = SubprocessAgentLauncher().run(prompt="p", allowed_tools=["t"])
    assert result.failed is True
    assert "boom" in result.detail


def test_subprocess_agent_launcher_returns_stdout_on_success(monkeypatch):
    class _Completed:
        returncode = 0
        stdout = "<<<HERALD_TOOL_RESULT>>>x<<<END_HERALD_TOOL_RESULT>>>"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed())
    result = SubprocessAgentLauncher().run(prompt="p", allowed_tools=["t"])
    assert result.failed is False
    assert result.stdout == _Completed.stdout
