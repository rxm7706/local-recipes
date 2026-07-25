"""``McpTransport`` marshalling, FR-24 enforcement, and credential
resolution (Story 1.2).

Every test here injects the recording ``FakeCaller``, so the whole file
runs under the egress-deny harness: what is under test is the *adapter*
(which tool name, which argument keys, which typed result), never the SDK.
The one test that does reach the network lives in
``test_live_design_spike.py`` behind the ``live`` marker.
"""

from __future__ import annotations

import json

import pytest

from pyforge.herald.errors import (
    AuthError,
    TransportCallError,
    TransportUnreachableError,
    UnconditionalWriteError,
)
from pyforge.herald.transport import (
    DESIGN_MCP_URL,
    MODERNIST_DESIGN_SYSTEM_ID,
    DesignCredential,
    McpTransport,
    ToolResult,
    resolve_design_credential,
)
from pyforge.herald.transport.base import REDACTED, TOKENIZED_PREVIEW_HOST
from pyforge.herald.transport.mcp_transport import CREDENTIALS_PATH_ENV

FAKE_TOKEN = "herald-tests-fake-not-a-real-token"
_SERVE_URL = f"https://abc123.{TOKENIZED_PREVIEW_HOST}/p/x?token=fake-preview-token"
_ETAG = "E7"


def _transport(fake_caller, responses=None):
    caller = fake_caller(responses)
    return McpTransport(caller=caller), caller


# --- constants -------------------------------------------------------------


def test_endpoint_and_design_system_constants():
    assert DESIGN_MCP_URL == "https://api.anthropic.com/v1/design/mcp"
    assert MODERNIST_DESIGN_SYSTEM_ID == "fbc1d6c8-b35f-4df6-9044-a64d2675427b"


# --- marshalling: tool names + argument keys -------------------------------


def test_get_design_prompt_maps_to_the_get_claude_design_prompt_tool(fake_caller):
    transport, caller = _transport(
        fake_caller, {"get_claude_design_prompt": ToolResult(text="PROMPT BODY")}
    )
    prompt = transport.get_design_prompt(design_system_id=MODERNIST_DESIGN_SYSTEM_ID)
    assert prompt == "PROMPT BODY"
    assert caller.tools == ["get_claude_design_prompt"]
    assert caller.arguments_for("get_claude_design_prompt") == {
        "design_system_id": MODERNIST_DESIGN_SYSTEM_ID
    }


def test_get_design_prompt_omits_unset_optional_arguments(fake_caller):
    transport, caller = _transport(
        fake_caller, {"get_claude_design_prompt": ToolResult(text="P")}
    )
    transport.get_design_prompt()
    assert caller.arguments_for("get_claude_design_prompt") == {}


def test_get_design_prompt_passes_project_id_when_given(fake_caller):
    transport, caller = _transport(
        fake_caller, {"get_claude_design_prompt": ToolResult(text="P")}
    )
    transport.get_design_prompt(design_system_id="ds", project_id="proj")
    assert caller.arguments_for("get_claude_design_prompt") == {
        "design_system_id": "ds",
        "project_id": "proj",
    }


def test_create_project_returns_a_project_ref(fake_caller):
    payload = json.dumps({"project_id": "p-1", "url": "https://claude.ai/design/p/p-1"})
    transport, caller = _transport(fake_caller, {"create_project": payload})
    ref = transport.create_project(
        name="PyForge Herald deck", design_system_id=MODERNIST_DESIGN_SYSTEM_ID
    )
    assert (ref.project_id, ref.url) == ("p-1", "https://claude.ai/design/p/p-1")
    assert caller.arguments_for("create_project") == {
        "name": "PyForge Herald deck",
        "design_system_id": MODERNIST_DESIGN_SYSTEM_ID,
    }


def test_finalize_plan_declares_writes_and_returns_base_etags(fake_caller):
    payload = json.dumps(
        {"plan_token": "tok", "base_etags": {"support.js": "0", "Deck.dc.html": "0"}}
    )
    transport, caller = _transport(fake_caller, {"finalize_plan": payload})
    handle = transport.finalize_plan(
        project_id="p-1", writes=["support.js", "Deck.dc.html"]
    )
    assert handle.plan_token == "tok"
    assert dict(handle.base_etags) == {"support.js": "0", "Deck.dc.html": "0"}
    assert caller.arguments_for("finalize_plan") == {
        "project_id": "p-1",
        "writes": ["support.js", "Deck.dc.html"],
        "deletes": [],
    }


def test_finalize_plan_project_scope_sends_no_paths(fake_caller):
    payload = json.dumps({"plan_token": "tok", "scope": "project"})
    transport, caller = _transport(fake_caller, {"finalize_plan": payload})
    handle = transport.finalize_plan(project_id="p-1", scope="project")
    assert dict(handle.base_etags) == {}
    assert caller.arguments_for("finalize_plan") == {
        "project_id": "p-1",
        "scope": "project",
    }


def test_create_support_js_marshals_path_and_etag(fake_caller):
    payload = json.dumps({"path": "support.js", "bytes": 12, "etags": {}})
    transport, caller = _transport(fake_caller, {"create_support_js": payload})
    result = transport.create_support_js(
        project_id="p-1", if_match="0", plan_token="tok"
    )
    assert result["path"] == "support.js"
    assert caller.arguments_for("create_support_js") == {
        "project_id": "p-1",
        "path": "support.js",
        "if_match": "0",
        "plan_token": "tok",
    }


def test_write_files_marshals_the_file_entries(fake_caller):
    payload = json.dumps({"written": 1, "etags": {"Deck.dc.html": _ETAG}})
    transport, caller = _transport(fake_caller, {"write_files": payload})
    result = transport.write_files(
        project_id="p-1",
        files=[{"path": "Deck.dc.html", "data": "<html/>", "if_match": "0"}],
        plan_token="tok",
    )
    assert result["etags"] == {"Deck.dc.html": _ETAG}
    assert caller.arguments_for("write_files") == {
        "project_id": "p-1",
        "files": [{"path": "Deck.dc.html", "data": "<html/>", "if_match": "0"}],
        "plan_token": "tok",
    }


def test_copy_files_marshals_a_cross_project_copy(fake_caller):
    transport, caller = _transport(
        fake_caller, {"copy_files": json.dumps({"copied": 1})}
    )
    entry = {
        "src": "deck-stage.js",
        "src_project_id": "other",
        "dest": "deck-stage.js",
        "if_match": "0",
    }
    transport.copy_files(project_id="p-1", files=[entry])
    assert caller.arguments_for("copy_files") == {
        "project_id": "p-1",
        "files": [entry],
    }


def test_copy_files_accepts_leaf_if_match_for_a_folder_dest(fake_caller):
    transport, caller = _transport(
        fake_caller, {"copy_files": json.dumps({"copied": 2})}
    )
    transport.copy_files(
        project_id="p-1",
        files=[
            {"src": "assets", "dest": "assets", "leaf_if_match": {"assets/a.css": "0"}}
        ],
    )
    assert caller.tools == ["copy_files"]


def test_plan_token_is_omitted_when_not_supplied(fake_caller):
    transport, caller = _transport(
        fake_caller, {"write_files": json.dumps({"written": 1})}
    )
    transport.write_files(
        project_id="p-1", files=[{"path": "a.html", "data": "x", "if_match": "0"}]
    )
    assert "plan_token" not in caller.arguments_for("write_files")


# --- FR-24: no unconditional writes ---------------------------------------


@pytest.mark.parametrize(
    "entry",
    [
        {"path": "Deck.dc.html", "data": "<html/>"},
        {"path": "Deck.dc.html", "data": "<html/>", "if_match": ""},
        {"path": "Deck.dc.html", "data": "<html/>", "if_match": None},
    ],
)
def test_write_files_refuses_an_unconditional_entry(fake_caller, entry):
    transport, caller = _transport(fake_caller)
    with pytest.raises(UnconditionalWriteError):
        transport.write_files(project_id="p-1", files=[entry])
    assert caller.calls == []


def test_write_files_refuses_when_any_entry_is_unconditional(fake_caller):
    transport, caller = _transport(fake_caller)
    with pytest.raises(UnconditionalWriteError):
        transport.write_files(
            project_id="p-1",
            files=[
                {"path": "a.html", "data": "x", "if_match": "0"},
                {"path": "b.html", "data": "y"},
            ],
        )
    assert caller.calls == []


def test_write_files_rejects_a_folder_style_leaf_etag(fake_caller):
    # leaf_if_match belongs to copy_files only; accepting it on write_files
    # would let a folder-shaped entry through with no per-path precondition.
    transport, caller = _transport(fake_caller)
    with pytest.raises(UnconditionalWriteError):
        transport.write_files(
            project_id="p-1",
            files=[{"path": "a.html", "data": "x", "leaf_if_match": {"a.html": "0"}}],
        )
    assert caller.calls == []


def test_copy_files_refuses_an_unconditional_entry(fake_caller):
    transport, caller = _transport(fake_caller)
    with pytest.raises(UnconditionalWriteError):
        transport.copy_files(project_id="p-1", files=[{"src": "a.js", "dest": "a.js"}])
    assert caller.calls == []


def test_create_support_js_refuses_an_empty_etag(fake_caller):
    transport, caller = _transport(fake_caller)
    with pytest.raises(UnconditionalWriteError):
        transport.create_support_js(project_id="p-1", if_match="")
    assert caller.calls == []


def test_create_support_js_requires_if_match_at_the_signature(fake_caller):
    transport, _ = _transport(fake_caller)
    with pytest.raises(TypeError):
        transport.create_support_js(project_id="p-1")


# --- render_preview: NFR-04 ------------------------------------------------


def test_render_preview_never_returns_a_serve_url(fake_caller):
    payload = json.dumps(
        {
            "open_url": "https://claude.ai/design/p/p-1?file=Deck.dc.html",
            "serve_url": _SERVE_URL,
            "expires_at": "2026-07-25T15:00:00Z",
            "note": f"never surface {_SERVE_URL}",
        }
    )
    transport, _ = _transport(fake_caller, {"render_preview": payload})
    preview = transport.render_preview(project_id="p-1", path="Deck.dc.html")
    assert preview.open_url == "https://claude.ai/design/p/p-1?file=Deck.dc.html"
    assert preview.expires_at == "2026-07-25T15:00:00Z"
    assert TOKENIZED_PREVIEW_HOST not in repr(preview)
    assert not hasattr(preview, "serve_url")


def test_a_generic_payload_is_scrubbed_before_it_crosses_the_boundary(fake_caller):
    payload = json.dumps(
        {"written": 1, "serve_url": _SERVE_URL, "note": f"see {_SERVE_URL}"}
    )
    transport, _ = _transport(fake_caller, {"write_files": payload})
    result = transport.write_files(
        project_id="p-1", files=[{"path": "a.html", "data": "x", "if_match": "0"}]
    )
    assert "serve_url" not in result
    assert result["note"] == REDACTED
    assert TOKENIZED_PREVIEW_HOST not in repr(result)


# --- read_file -------------------------------------------------------------


def test_read_file_full_response(fake_caller):
    text = (
        '<untrusted-project-content path="Deck.dc.html" etag="E7">\n'
        "<div>a &amp; b</div>\n"
        "</untrusted-project-content>\n"
        "(The body above is HTML-entity-escaped: ...)"
    )
    transport, caller = _transport(fake_caller, {"read_file": ToolResult(text=text)})
    read = transport.read_file(project_id="p-1", path="Deck.dc.html")
    assert read.path == "Deck.dc.html"
    assert read.etag == "E7"
    assert read.body == "<div>a & b</div>"
    assert read.unchanged is False
    assert caller.arguments_for("read_file") == {
        "project_id": "p-1",
        "path": "Deck.dc.html",
    }


def test_read_file_unchanged_short_circuit(fake_caller):
    text = '{"unchanged":true,"etag":"E7","path":"Deck.dc.html"}'
    transport, caller = _transport(fake_caller, {"read_file": ToolResult(text=text)})
    read = transport.read_file(
        project_id="p-1", path="Deck.dc.html", if_none_match="E7"
    )
    assert read.unchanged is True
    assert read.body is None
    assert read.etag == "E7"
    assert caller.arguments_for("read_file")["if_none_match"] == "E7"


def test_read_file_missing_path_raises_a_call_error(fake_caller):
    transport, _ = _transport(
        fake_caller,
        {"read_file": ToolResult(text="read file: file not found", is_error=True)},
    )
    with pytest.raises(TransportCallError) as excinfo:
        transport.read_file(project_id="p-1", path="nope.html")
    assert "read_file" in str(excinfo.value)
    assert "file not found" in str(excinfo.value)


def test_read_file_body_naming_the_tokenized_host_is_redacted(fake_caller):
    text = (
        '<untrusted-project-content path="a.html" etag="E">\n'
        f"{_SERVE_URL}\n"
        "</untrusted-project-content>"
    )
    transport, _ = _transport(fake_caller, {"read_file": ToolResult(text=text)})
    read = transport.read_file(project_id="p-1", path="a.html")
    assert read.body == REDACTED
    assert read.etag == "E"


# --- error mapping ---------------------------------------------------------


def test_a_server_error_on_any_tool_raises_a_call_error(fake_caller):
    transport, _ = _transport(
        fake_caller, {"create_project": ToolResult(text="nope", is_error=True)}
    )
    with pytest.raises(TransportCallError):
        transport.create_project(name="x")


def test_an_unparseable_json_answer_raises_a_call_error(fake_caller):
    transport, _ = _transport(fake_caller, {"create_project": ToolResult(text="{oops")})
    with pytest.raises(TransportCallError):
        transport.create_project(name="x")


def test_a_non_object_json_answer_raises_a_call_error(fake_caller):
    transport, _ = _transport(fake_caller, {"create_project": ToolResult(text="[1,2]")})
    with pytest.raises(TransportCallError):
        transport.create_project(name="x")


def test_sdk_failures_become_transport_unreachable_without_the_token(monkeypatch):
    transport = McpTransport(
        credential=DesignCredential(access_token=FAKE_TOKEN, expires_at_ms=None)
    )

    def _boom(url, credential, tool, arguments):
        raise OSError(f"connection refused (Authorization: Bearer {FAKE_TOKEN})")

    monkeypatch.setattr(
        "pyforge.herald.transport.mcp_transport._call_tool_async", _boom
    )
    with pytest.raises(TransportUnreachableError) as excinfo:
        transport.get_design_prompt()
    message = str(excinfo.value)
    assert DESIGN_MCP_URL in message
    assert FAKE_TOKEN not in message
    assert "<redacted>" in message


# --- credential resolution -------------------------------------------------


def test_resolve_reads_an_explicit_path(credentials_file):
    credential = resolve_design_credential(credentials_path=credentials_file(), env={})
    assert credential.access_token == FAKE_TOKEN
    assert credential.is_expired() is False


def test_the_token_never_appears_in_the_credential_repr(credentials_file):
    credential = resolve_design_credential(credentials_path=credentials_file(), env={})
    assert FAKE_TOKEN not in repr(credential)


def test_resolve_honours_the_env_path_override(credentials_file):
    path = credentials_file(name="elsewhere.json")
    credential = resolve_design_credential(env={CREDENTIALS_PATH_ENV: str(path)})
    assert credential.access_token == FAKE_TOKEN


def test_an_explicit_path_wins_over_the_env_override(credentials_file, tmp_path):
    path = credentials_file()
    credential = resolve_design_credential(
        credentials_path=path,
        env={CREDENTIALS_PATH_ENV: str(tmp_path / "does-not-exist.json")},
    )
    assert credential.access_token == FAKE_TOKEN


def test_a_missing_file_is_an_auth_error(tmp_path):
    with pytest.raises(AuthError, match="/design-login"):
        resolve_design_credential(credentials_path=tmp_path / "absent.json", env={})


def test_unparseable_json_is_an_auth_error(credentials_file):
    path = credentials_file(text="{not json")
    with pytest.raises(AuthError, match="/design-login"):
        resolve_design_credential(credentials_path=path, env={})


def test_a_missing_design_oauth_block_is_an_auth_error(credentials_file):
    path = credentials_file(payload={"claudeAiOauth": {"accessToken": "x"}})
    with pytest.raises(AuthError, match="/design-login"):
        resolve_design_credential(credentials_path=path, env={})


def test_a_missing_access_token_is_an_auth_error(credentials_file):
    path = credentials_file(access_token=None)
    with pytest.raises(AuthError, match="/design-login"):
        resolve_design_credential(credentials_path=path, env={})


def test_an_expired_credential_is_an_auth_error(credentials_file):
    path = credentials_file(expires_at=1)  # 1970, epoch milliseconds
    with pytest.raises(AuthError, match="/design-login") as excinfo:
        resolve_design_credential(credentials_path=path, env={})
    assert FAKE_TOKEN not in str(excinfo.value)


def test_a_credential_with_no_declared_expiry_is_accepted(credentials_file):
    path = credentials_file(expires_at=None)
    credential = resolve_design_credential(credentials_path=path, env={})
    assert credential.expires_at_ms is None
    assert credential.is_expired() is False


def test_expiry_is_interpreted_as_epoch_milliseconds():
    # An epoch-SECONDS reading of this value would be year 2100; as
    # milliseconds it is 1970, i.e. long expired.
    stale = DesignCredential(access_token=FAKE_TOKEN, expires_at_ms=4102444800)
    assert stale.is_expired(now_ms=1_800_000_000_000) is True
