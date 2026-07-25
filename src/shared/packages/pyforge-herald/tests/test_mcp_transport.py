"""``McpTransport`` marshalling, FR-24 enforcement, and credential
resolution (Story 1.2).

Every test here injects the recording ``FakeCaller``, so the whole file
runs under the egress-deny harness: what is under test is the *adapter*
(which tool name, which argument keys, which typed result), never the SDK.
The one test that does reach the network lives in
``test_live_design_spike.py`` behind the ``live`` marker.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from pyforge.herald.errors import (
    AuthError,
    TransportCallError,
    TransportError,
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


def test_get_design_prompt_survives_documenting_the_tokenized_host(fake_caller):
    """A prose answer is content, not an envelope, so it is never redacted.

    Regression for a live failure: the real Modernist prompt mentions
    ``claudeusercontent.com`` exactly once -- in the rule forbidding it --
    and whole-string redaction therefore replaced all 33,985 characters of
    the mandatory pre-write seed gate with the placeholder. Verified live
    2026-07-25 that the prompt carries no tokenized URL, only that one
    documentary mention."""
    prompt = (
        "Never put a serve_url (or any *.claudeusercontent.com link) in "
        "user-visible text -- it carries a project-scoped token."
    )
    transport, _ = _transport(
        fake_caller, {"get_claude_design_prompt": ToolResult(text=prompt)}
    )
    returned = transport.get_design_prompt(design_system_id=MODERNIST_DESIGN_SYSTEM_ID)
    assert returned == prompt
    assert returned != REDACTED
    assert TOKENIZED_PREVIEW_HOST in returned


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


@pytest.mark.parametrize("scope", ["Project", "PATHS", "all", ""])
def test_finalize_plan_refuses_an_unrecognised_scope(fake_caller, scope):
    # "Project" silently degrading to a paths plan with no writes would
    # authorize nothing, and every later write would fail server-side with
    # no hint that the capital P was the cause.
    transport, caller = _transport(fake_caller)
    with pytest.raises(TransportCallError, match="scope"):
        transport.finalize_plan(project_id="p-1", scope=scope, writes=["a.html"])
    assert caller.calls == []


@pytest.mark.parametrize("paths", [{"writes": ["a.html"]}, {"deletes": ["b.html"]}])
def test_finalize_plan_refuses_project_scope_combined_with_paths(fake_caller, paths):
    transport, caller = _transport(fake_caller)
    with pytest.raises(TransportCallError):
        transport.finalize_plan(project_id="p-1", scope="project", **paths)
    assert caller.calls == []


def test_finalize_plan_refuses_a_paths_plan_declaring_nothing(fake_caller):
    # The same hazard the unknown-scope guard prevents, reached the other
    # way: an empty paths plan authorizes nothing, so the caller would get
    # a valid-looking token and every later write would be refused
    # server-side with no hint that the empty plan was the cause.
    transport, caller = _transport(fake_caller)
    with pytest.raises(TransportCallError, match="authorizes nothing"):
        transport.finalize_plan(project_id="p-1")
    assert caller.calls == []


def test_finalize_plan_refuses_an_answer_carrying_no_plan_token(fake_caller):
    # "" is not "absent": it is marshalled as an explicit plan_token on
    # every later write rather than omitted.
    payload = json.dumps({"base_etags": {"a.html": "0"}})
    transport, _ = _transport(fake_caller, {"finalize_plan": payload})
    with pytest.raises(TransportCallError, match="no plan_token"):
        transport.finalize_plan(project_id="p-1", writes=["a.html"])


def test_finalize_plan_refuses_a_non_mapping_base_etags(fake_caller):
    # Iterating a list of pairs would raise AttributeError straight past
    # AD-6's single HeraldError catch at the CLI boundary.
    payload = json.dumps({"plan_token": "tok", "base_etags": ["support.js"]})
    transport, _ = _transport(fake_caller, {"finalize_plan": payload})
    with pytest.raises(TransportCallError, match="base_etags"):
        transport.finalize_plan(project_id="p-1", writes=["support.js"])


def test_a_null_base_etag_is_not_coerced_to_the_string_none(fake_caller):
    # str(None) == "None" is a truthy four-character etag that would pass
    # FR-24 and then be rejected by the server as a bogus precondition.
    payload = json.dumps({"plan_token": "tok", "base_etags": {"a.html": None}})
    transport, _ = _transport(fake_caller, {"finalize_plan": payload})
    handle = transport.finalize_plan(project_id="p-1", writes=["a.html"])
    assert handle.base_etags["a.html"] == ""
    with pytest.raises(UnconditionalWriteError):
        transport.write_files(
            project_id="p-1",
            files=[
                {"path": "a.html", "data": "x", "if_match": handle.base_etags["a.html"]}
            ],
        )


def test_create_project_null_fields_become_empty_strings(fake_caller):
    payload = json.dumps({"project_id": None, "url": None})
    transport, _ = _transport(fake_caller, {"create_project": payload})
    ref = transport.create_project(name="x")
    assert (ref.project_id, ref.url) == ("", "")


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


@pytest.mark.parametrize("method", ["write_files", "copy_files"])
def test_a_write_of_no_entries_is_refused(fake_caller, method):
    transport, caller = _transport(fake_caller)
    with pytest.raises(UnconditionalWriteError):
        getattr(transport, method)(project_id="p-1", files=[])
    assert caller.calls == []


@pytest.mark.parametrize("method", ["write_files", "copy_files"])
def test_a_non_mapping_entry_is_refused_as_a_herald_error(fake_caller, method):
    transport, caller = _transport(fake_caller)
    with pytest.raises(UnconditionalWriteError):
        getattr(transport, method)(project_id="p-1", files=["a.html"])
    assert caller.calls == []


def test_write_files_validates_and_marshals_the_same_entries(fake_caller):
    # A generator drained by validation used to marshal as [] -- an
    # unconditional-write check that passed, followed by a write of
    # nothing reported as success.
    entry = {"path": "a.html", "data": "x", "if_match": "0"}
    transport, caller = _transport(
        fake_caller, {"write_files": json.dumps({"written": 1})}
    )
    transport.write_files(project_id="p-1", files=(entry for _ in range(1)))
    assert caller.arguments_for("write_files")["files"] == [entry]


def test_copy_files_validates_and_marshals_the_same_entries(fake_caller):
    entry = {"src": "a.js", "dest": "a.js", "if_match": "0"}
    transport, caller = _transport(
        fake_caller, {"copy_files": json.dumps({"copied": 1})}
    )
    transport.copy_files(project_id="p-1", files=(entry for _ in range(1)))
    assert caller.arguments_for("copy_files")["files"] == [entry]


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


def test_render_preview_ignores_a_non_string_expiry(fake_caller):
    # PreviewRef models expires_at as `str | None`; str(123) would invent a
    # timestamp format nothing downstream can parse.
    payload = json.dumps(
        {"open_url": "https://claude.ai/design/p/p-1", "expires_at": 123}
    )
    transport, _ = _transport(fake_caller, {"render_preview": payload})
    preview = transport.render_preview(project_id="p-1", path="Deck.dc.html")
    assert preview.expires_at is None
    assert preview.open_url == "https://claude.ai/design/p/p-1"


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


def test_read_file_body_is_content_and_is_never_redacted(fake_caller):
    # Deliberate, and load-bearing: sanitize_payload replaces an ENTIRE
    # string that mentions the host, so redacting the body would turn a
    # deck legitimately referencing it into a 40-character constant that
    # `herald deck pull` then writes over the repo's prototype. A file body
    # is user-authored content, not an envelope that could surface a live
    # tokenized URL.
    text = (
        '<untrusted-project-content path="a.html" etag="E">\n'
        f"{_SERVE_URL}\n"
        "</untrusted-project-content>"
    )
    transport, _ = _transport(fake_caller, {"read_file": ToolResult(text=text)})
    read = transport.read_file(project_id="p-1", path="a.html")
    assert read.body == _SERVE_URL
    assert read.body != REDACTED
    assert read.etag == "E"


def test_read_file_marshals_offset_and_limit(fake_caller):
    text = (
        '<untrusted-project-content path="a.html" etag="E" lines="209-212" '
        'total_lines="212">\n'
        "tail\n"
        "</untrusted-project-content>"
    )
    transport, caller = _transport(fake_caller, {"read_file": ToolResult(text=text)})
    read = transport.read_file(project_id="p-1", path="a.html", offset=209, limit=200)
    assert caller.arguments_for("read_file") == {
        "project_id": "p-1",
        "path": "a.html",
        "offset": 209,
        "limit": 200,
    }
    assert read.body == "tail"


def test_read_file_omits_offset_and_limit_when_unset(fake_caller):
    text = (
        '<untrusted-project-content path="a.html" etag="E">\n'
        "body\n"
        "</untrusted-project-content>"
    )
    transport, caller = _transport(fake_caller, {"read_file": ToolResult(text=text)})
    transport.read_file(project_id="p-1", path="a.html")
    arguments = caller.arguments_for("read_file")
    assert "offset" not in arguments
    assert "limit" not in arguments


def test_a_capped_read_is_reported_as_truncated(fake_caller):
    # The server caps read_file at 256 KiB and says so in the wrapper --
    # verified live 2026-07-25. Without this, a partial read is
    # indistinguishable from a complete one and `deck pull` would write a
    # window over the whole prototype.
    text = (
        '<untrusted-project-content path="Warden Infographic standalone.html" '
        'etag="1784081111105460" lines="1-208" total_lines="212">\n'
        "<html>...\n"
        "</untrusted-project-content>"
    )
    transport, _ = _transport(fake_caller, {"read_file": ToolResult(text=text)})
    read = transport.read_file(
        project_id="p-1", path="Warden Infographic standalone.html"
    )
    assert read.truncated is True
    assert (read.first_line, read.last_line, read.total_lines) == (1, 208, 212)


def test_a_whole_file_read_is_not_truncated(fake_caller):
    text = (
        '<untrusted-project-content path="a.html" etag="E" lines="1-3" '
        'total_lines="3">\n'
        "a\nb\nc\n"
        "</untrusted-project-content>"
    )
    transport, _ = _transport(fake_caller, {"read_file": ToolResult(text=text)})
    assert transport.read_file(project_id="p-1", path="a.html").truncated is False


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


def test_a_server_error_message_is_sanitized_before_it_is_raised(fake_caller):
    # The error text is the one server string that never passes through
    # _call_text/_call_json, so it is the one path a serve_url could ride
    # out to stderr intact (NFR-04).
    transport, _ = _transport(
        fake_caller,
        {
            "render_preview": ToolResult(
                text=f"render failed; preview was at {_SERVE_URL}", is_error=True
            )
        },
    )
    with pytest.raises(TransportCallError) as excinfo:
        transport.render_preview(project_id="p-1", path="a.html")
    message = str(excinfo.value)
    assert TOKENIZED_PREVIEW_HOST not in message
    assert REDACTED in message
    assert "render_preview" in message


def _raises(exc: BaseException):
    """A stand-in ``_call_tool_async`` that fails before any loop is made."""

    def _boom(url, credential, tool, arguments):
        raise exc

    return _boom


def _transport_failing_with(monkeypatch, exc: BaseException) -> McpTransport:
    monkeypatch.setattr(
        "pyforge.herald.transport.mcp_transport._call_tool_async", _raises(exc)
    )
    return McpTransport(
        credential=DesignCredential(access_token=FAKE_TOKEN, expires_at_ms=None)
    )


def test_sdk_failures_become_transport_unreachable_without_the_token(monkeypatch):
    transport = _transport_failing_with(
        monkeypatch,
        OSError(f"connection refused (Authorization: Bearer {FAKE_TOKEN})"),
    )
    with pytest.raises(TransportUnreachableError) as excinfo:
        transport.get_design_prompt()
    message = str(excinfo.value)
    assert DESIGN_MCP_URL in message
    assert FAKE_TOKEN not in message
    assert "<redacted>" in message


def test_an_exception_group_is_flattened_into_the_detail(monkeypatch):
    # The mcp SDK raises through anyio task groups, so the group's own
    # message is only "unhandled errors in a TaskGroup (1 sub-exception)".
    transport = _transport_failing_with(
        monkeypatch,
        ExceptionGroup(
            "unhandled errors in a TaskGroup",
            [ConnectionRefusedError("no route to api.anthropic.com")],
        ),
    )
    with pytest.raises(TransportUnreachableError) as excinfo:
        transport.get_design_prompt()
    message = str(excinfo.value)
    assert "ConnectionRefusedError: no route to api.anthropic.com" in message


def test_a_nested_exception_group_is_flattened_to_its_leaves(monkeypatch):
    transport = _transport_failing_with(
        monkeypatch,
        ExceptionGroup(
            "outer",
            [ExceptionGroup("inner", [OSError("tls handshake failed")])],
        ),
    )
    with pytest.raises(TransportUnreachableError) as excinfo:
        transport.get_design_prompt()
    assert "OSError: tls handshake failed" in str(excinfo.value)


class _FakeHttpResponse:
    """The one attribute the auth check reads off an ``httpx``-style error."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeHttpStatusError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.response = _FakeHttpResponse(status_code)


@pytest.mark.parametrize("status", [401, 403])
def test_an_http_rejection_becomes_an_auth_error_not_unreachable(monkeypatch, status):
    # bridge-protocol.md § Watch parameters: halt on auth error, never
    # retry a 401. That is only possible if a 401 is distinguishable.
    transport = _transport_failing_with(
        monkeypatch,
        ExceptionGroup(
            "unhandled errors in a TaskGroup",
            [_FakeHttpStatusError("server rejected the request", status)],
        ),
    )
    with pytest.raises(AuthError, match="/design-login") as excinfo:
        transport.get_design_prompt()
    assert FAKE_TOKEN not in str(excinfo.value)


def test_a_stringified_status_is_enough_to_raise_an_auth_error(monkeypatch):
    transport = _transport_failing_with(
        monkeypatch, RuntimeError("session terminated: HTTP 401 Unauthorized")
    )
    with pytest.raises(AuthError, match="/design-login"):
        transport.get_design_prompt()


@pytest.mark.parametrize(
    "message",
    [
        # An IPv6 literal, and a session id: both routinely carry the
        # digits, neither says anything about a credential.
        "[Errno 101] Network is unreachable: connect to 2607:f8b0:4003::401",
        "stream closed unexpectedly; Mcp-Session-Id=8f403abc401d",
        "read timed out after 401 seconds",
    ],
)
def test_a_bare_401_in_an_address_is_not_read_as_a_rejected_credential(
    monkeypatch, message
):
    # bridge-protocol.md § Watch parameters halts on an auth error and
    # never retries, so a misfiled transient outage would stop `herald deck
    # watch` for good and blame a credential that is perfectly valid.
    transport = _transport_failing_with(monkeypatch, OSError(message))
    with pytest.raises(TransportUnreachableError):
        transport.get_design_prompt()


@pytest.mark.parametrize(
    "message",
    [
        "session terminated: HTTP 401 Unauthorized",
        "server responded 403 Forbidden",
        "status_code=401 while opening the stream",
        "the request was unauthorized",
    ],
)
def test_a_stringified_http_status_is_still_read_as_an_auth_error(monkeypatch, message):
    transport = _transport_failing_with(monkeypatch, RuntimeError(message))
    with pytest.raises(AuthError, match="/design-login"):
        transport.get_design_prompt()


def test_a_truncated_token_echo_is_still_scrubbed(monkeypatch):
    # A library that elides a long Authorization header leaves a prefix
    # behind, and a prefix is still credential material.
    token = "herald-tests-fake-token-with-a-long-and-distinctive-body"
    monkeypatch.setattr(
        "pyforge.herald.transport.mcp_transport._call_tool_async",
        _raises(OSError(f"connection refused (Authorization: Bearer {token[:34]}...)")),
    )
    transport = McpTransport(
        credential=DesignCredential(access_token=token, expires_at_ms=None)
    )
    with pytest.raises(TransportUnreachableError) as excinfo:
        transport.get_design_prompt()
    message = str(excinfo.value)
    assert token[:34] not in message
    assert "<redacted>" in message


def test_the_transport_refuses_a_non_https_endpoint():
    # The endpoint is the one place the bearer token leaves the process.
    with pytest.raises(TransportError, match="cleartext"):
        McpTransport(url="http://localhost:8080/v1/design/mcp")


def test_a_missing_mcp_sdk_is_not_reported_as_an_outage(monkeypatch):
    # `mcp` is a declared runtime dependency, so an ImportError is a broken
    # install; calling it "endpoint unreachable" sends the operator to look
    # at the network instead.
    transport = _transport_failing_with(
        monkeypatch, ImportError("No module named 'mcp'")
    )
    with pytest.raises(TransportError) as excinfo:
        transport.get_design_prompt()
    assert not isinstance(excinfo.value, TransportUnreachableError)
    assert "mcp SDK is not importable" in str(excinfo.value)


def test_a_token_containing_an_auth_marker_does_not_fake_an_auth_error(monkeypatch):
    # The auth token scan runs on the SCRUBBED detail, so a token that
    # happens to contain "401" cannot misfile a connection failure.
    token = "herald-tests-fake-401-not-a-real-token"
    monkeypatch.setattr(
        "pyforge.herald.transport.mcp_transport._call_tool_async",
        _raises(OSError(f"connection refused for Bearer {token}")),
    )
    transport = McpTransport(
        credential=DesignCredential(access_token=token, expires_at_ms=None)
    )
    with pytest.raises(TransportUnreachableError) as excinfo:
        transport.get_design_prompt()
    assert token not in str(excinfo.value)


def test_the_sync_transport_refuses_to_run_inside_a_live_event_loop():
    # asyncio.run cannot nest; the RuntimeError it raises would otherwise
    # be reported as "could not reach the endpoint", which is a lie.
    transport = McpTransport(
        credential=DesignCredential(access_token=FAKE_TOKEN, expires_at_ms=None)
    )

    async def _drive() -> None:
        transport.get_design_prompt()

    with pytest.raises(TransportError) as excinfo:
        asyncio.run(_drive())
    message = str(excinfo.value)
    assert "event loop" in message
    assert "get_claude_design_prompt" in message


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


def test_a_boolean_expiry_is_not_read_as_a_timestamp(credentials_file):
    # bool is an int subclass, so `"expiresAt": true` used to resolve to
    # 1 ms -- 1970 -- and hard-expire a perfectly good credential.
    path = credentials_file(expires_at=True)
    credential = resolve_design_credential(credentials_path=path, env={})
    assert credential.expires_at_ms is None
    assert credential.is_expired() is False


@pytest.mark.parametrize("raw", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_expiry_is_treated_as_no_declared_expiry(credentials_file, raw):
    # `json` accepts NaN and Infinity; int() raises ValueError/OverflowError
    # on them, which would escape the AuthError contract.
    path = credentials_file(expires_at=raw)
    credential = resolve_design_credential(credentials_path=path, env={})
    assert credential.expires_at_ms is None


def test_the_test_harness_points_credential_resolution_at_a_missing_file():
    # conftest's deny_network fixture redirects the override env var so no
    # offline test can quietly succeed on the developer's real
    # ~/.claude/.credentials.json.
    assert not Path(os.environ[CREDENTIALS_PATH_ENV]).exists()
    with pytest.raises(AuthError, match="/design-login"):
        resolve_design_credential()


def test_expiry_is_interpreted_as_epoch_milliseconds():
    # An epoch-SECONDS reading of this value would be year 2100; as
    # milliseconds it is 1970, i.e. long expired.
    stale = DesignCredential(access_token=FAKE_TOKEN, expires_at_ms=4102444800)
    assert stale.is_expired(now_ms=1_800_000_000_000) is True
