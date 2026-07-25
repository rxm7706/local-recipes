"""The port's own invariants: conformance, sanitization, read parsing
(Story 1.2).

These cover the I/O-matrix rows ``base.py`` owns. Everything here is pure
-- no adapter, no caller, no network -- because Story 1.3's
``AgentSdkTransport`` inherits exactly these guarantees by reusing exactly
these functions.
"""

from __future__ import annotations

import socket

import pytest

from pyforge.herald.errors import TransportCallError
from pyforge.herald.transport import (
    DesignTransport,
    McpTransport,
    PreviewRef,
    ToolCaller,
    ToolResult,
    parse_read_response,
    sanitize_payload,
)
from pyforge.herald.transport.base import REDACTED, TOKENIZED_PREVIEW_HOST

_SERVE_URL = f"https://abc123.{TOKENIZED_PREVIEW_HOST}/p/x?token=fake-preview-token"


def test_mcp_transport_conforms_to_the_port():
    assert isinstance(McpTransport(), DesignTransport)


def test_fake_caller_conforms_to_the_caller_seam(fake_caller):
    assert isinstance(fake_caller(), ToolCaller)


def test_port_exposes_exactly_the_eight_bridge_tools():
    expected = {
        "get_design_prompt",
        "create_project",
        "finalize_plan",
        "create_support_js",
        "copy_files",
        "write_files",
        "read_file",
        "render_preview",
    }
    assert set(DesignTransport.__protocol_attrs__) == expected


def test_preview_ref_has_no_serve_url_field():
    preview = PreviewRef(open_url="https://claude.ai/design/p/x?file=Deck.dc.html")
    assert not hasattr(preview, "serve_url")
    assert "serve_url" not in preview.__dataclass_fields__


def test_sanitize_drops_nested_serve_url_keys():
    payload = {
        "open_url": "https://claude.ai/design/p/x",
        "serve_url": _SERVE_URL,
        "nested": [{"serve_url": _SERVE_URL, "keep": "yes"}],
    }
    assert sanitize_payload(payload) == {
        "open_url": "https://claude.ai/design/p/x",
        "nested": [{"keep": "yes"}],
    }


def test_sanitize_redacts_any_string_naming_the_tokenized_host():
    payload = {"note": f"preview at {_SERVE_URL} expires soon", "safe": "hello"}
    sanitized = sanitize_payload(payload)
    assert sanitized == {"note": REDACTED, "safe": "hello"}
    assert TOKENIZED_PREVIEW_HOST not in repr(sanitized)


def test_sanitize_handles_a_bare_string_and_is_idempotent():
    assert sanitize_payload("plain text") == "plain text"
    once = sanitize_payload(_SERVE_URL)
    assert once == REDACTED
    assert sanitize_payload(once) == REDACTED


def test_sanitize_leaves_non_string_scalars_alone():
    assert sanitize_payload({"n": 1, "b": True, "z": None}) == {
        "n": 1,
        "b": True,
        "z": None,
    }


def test_parse_read_response_full_form_decodes_and_strips_the_trailer():
    text = (
        '<untrusted-project-content path="Deck.dc.html" etag="E7">\n'
        "<div>a &amp;&lt;b&gt; c</div>\n"
        "</untrusted-project-content>\n"
        "(The body above is HTML-entity-escaped: &amp; &lt; &gt; -> & < >)"
    )
    read = parse_read_response(text)
    assert read.path == "Deck.dc.html"
    assert read.etag == "E7"
    assert read.body == "<div>a &<b> c</div>"
    assert read.unchanged is False


def test_parse_read_response_decodes_ampersand_last():
    # A file containing the literal text "&lt;" is escaped to "&amp;lt;";
    # decoding &amp; last is what keeps it from collapsing into "<".
    text = (
        '<untrusted-project-content path="p" etag="E">\n'
        "&amp;lt;\n"
        "</untrusted-project-content>"
    )
    assert parse_read_response(text).body == "&lt;"


def test_parse_read_response_keeps_interior_blank_lines():
    text = (
        '<untrusted-project-content path="p" etag="E">\n'
        "one\n\nthree\n"
        "</untrusted-project-content>"
    )
    assert parse_read_response(text).body == "one\n\nthree"


def test_parse_read_response_unchanged_form():
    read = parse_read_response('{"unchanged":true,"etag":"E7","path":"Deck.dc.html"}')
    assert read.path == "Deck.dc.html"
    assert read.etag == "E7"
    assert read.body is None
    assert read.unchanged is True


@pytest.mark.parametrize(
    "text",
    [
        "not a wrapper at all",
        "{not json",
        '{"etag":"E","path":"p"}',
        "</untrusted-project-content>",
    ],
)
def test_parse_read_response_refuses_an_unrecognised_shape(text):
    with pytest.raises(TransportCallError):
        parse_read_response(text)


def test_tool_result_defaults_to_success():
    assert ToolResult(text="ok").is_error is False


def test_the_deny_harness_is_active_for_unmarked_tests(network_denied_error):
    with pytest.raises(network_denied_error):
        socket.getaddrinfo("api.anthropic.com", 443)
    with pytest.raises(network_denied_error):
        socket.create_connection(("api.anthropic.com", 443))
