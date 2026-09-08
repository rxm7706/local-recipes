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

from pyforge.herald.errors import TransportCallError, UnconditionalWriteError
from pyforge.herald.transport import (
    DesignTransport,
    FileRead,
    McpTransport,
    PreviewRef,
    ToolCaller,
    ToolResult,
    parse_read_response,
    require_conditional,
    sanitize_payload,
)
from pyforge.herald.transport.base import REDACTED, TOKENIZED_PREVIEW_HOST

_SERVE_URL = f"https://abc123.{TOKENIZED_PREVIEW_HOST}/p/x?token=fake-preview-token"


def test_mcp_transport_conforms_to_the_port():
    assert isinstance(McpTransport(), DesignTransport)


def test_fake_caller_conforms_to_the_caller_seam(fake_caller):
    assert isinstance(fake_caller(), ToolCaller)


def test_port_exposes_exactly_the_nine_bridge_tools():
    """Widened from 8 to 9 by Story 3.1/3.2's spine amendment (F10, ``base.py``'s
    own module docstring): ``list_files`` is CAP-3's only way to enumerate a
    Design project's files, needed for the stale-hand-mirror heuristic."""
    expected = {
        "get_design_prompt",
        "create_project",
        "finalize_plan",
        "create_support_js",
        "copy_files",
        "write_files",
        "read_file",
        "render_preview",
        "list_files",
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


def test_sanitize_matches_the_tokenized_host_case_insensitively():
    # DNS is case-insensitive, so ABC.ClaudeUserContent.com is the same
    # tokenized origin and must not slip through on spelling.
    shouted = _SERVE_URL.replace(TOKENIZED_PREVIEW_HOST, "ClaudeUserContent.COM")
    assert sanitize_payload(shouted) == REDACTED
    assert sanitize_payload({"note": shouted}) == {"note": REDACTED}


def test_sanitize_redacts_a_key_naming_the_tokenized_host():
    sanitized = sanitize_payload({_SERVE_URL: "some value"})
    assert sanitized == {REDACTED: "some value"}
    assert TOKENIZED_PREVIEW_HOST not in repr(sanitized)


def test_sanitize_leaves_a_non_string_key_alone():
    # Scrubbing a tuple key would return an unhashable list and raise a
    # bare TypeError out of a function the package exports -- escaping the
    # HeraldError hierarchy that AD-6's CLI boundary catches.
    sanitized = sanitize_payload({("a", "b"): 1, 7: _SERVE_URL})
    assert sanitized == {("a", "b"): 1, 7: REDACTED}


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


def test_parse_read_response_stops_at_the_first_close_tag():
    # The body is entity-escaped, so it cannot contain a literal close tag:
    # the first one after the opening is always the right one. Searching
    # from the end would swallow this trailer into the file content.
    text = (
        '<untrusted-project-content path="p" etag="E">\n'
        "body\n"
        "</untrusted-project-content>\n"
        "(the wrapper above is </untrusted-project-content>)"
    )
    assert parse_read_response(text).body == "body"


def test_parse_read_response_reports_a_truncated_window():
    # The real shape of a capped read, verified live 2026-07-25 against
    # `Warden Infographic standalone.html` (411,764 bytes -> 206,829 chars).
    text = (
        '<untrusted-project-content path="Warden Infographic standalone.html" '
        'etag="1784081111105460" lines="1-208" total_lines="212">\n'
        "<html>...\n"
        "[...file's 256 KiB cap — the body ends at a complete line; "
        "continue with offset=209]\n"
        "</untrusted-project-content>"
    )
    read = parse_read_response(text)
    assert read.etag == "1784081111105460"
    assert (read.first_line, read.last_line, read.total_lines) == (1, 208, 212)
    assert read.truncated is True


def test_parse_read_response_reports_a_window_that_covers_the_file():
    text = (
        '<untrusted-project-content path="p" etag="E" lines="1-212" '
        'total_lines="212">\n'
        "body\n"
        "</untrusted-project-content>"
    )
    read = parse_read_response(text)
    assert (read.first_line, read.last_line, read.total_lines) == (1, 212, 212)
    assert read.truncated is False


def test_parse_read_response_without_a_window_is_not_truncated():
    text = (
        '<untrusted-project-content path="p" etag="E">\n'
        "body\n"
        "</untrusted-project-content>"
    )
    read = parse_read_response(text)
    assert (read.first_line, read.last_line, read.total_lines) == (None, None, None)
    assert read.truncated is False


def test_a_later_page_of_a_file_is_truncated():
    read = FileRead(
        path="p",
        etag="E",
        body="tail",
        unchanged=False,
        first_line=209,
        last_line=212,
        total_lines=212,
    )
    assert read.truncated is True


@pytest.mark.parametrize(
    "attributes",
    [
        'lines="1-208"',  # a window, but no total to measure it against
        'lines="1-208" total_lines=""',
        'lines="1-208" total_lines="212 of 400"',  # not a bare integer
    ],
)
def test_a_declared_window_with_no_parsable_total_fails_closed(attributes):
    # The mirror image of the case below, and the dangerous direction: a
    # window reported as whole would be written over the prototype, and its
    # etag would then license a whole-file overwrite of the lines outside
    # it. Coverage that cannot be proven is not assumed, either way round.
    text = (
        f'<untrusted-project-content path="p" etag="E" {attributes}>\n'
        "body\n"
        "</untrusted-project-content>"
    )
    read = parse_read_response(text)
    assert read.total_lines is None
    assert read.truncated is True


def test_a_declared_total_with_no_parsable_window_fails_closed():
    # Coverage that cannot be proven is not assumed.
    text = (
        '<untrusted-project-content path="p" etag="E" lines="all" '
        'total_lines="212">\n'
        "body\n"
        "</untrusted-project-content>"
    )
    read = parse_read_response(text)
    assert (read.first_line, read.last_line) == (None, None)
    assert read.truncated is True


def test_parse_read_response_unchanged_form():
    read = parse_read_response('{"unchanged":true,"etag":"E7","path":"Deck.dc.html"}')
    assert read.path == "Deck.dc.html"
    assert read.etag == "E7"
    assert read.body is None
    assert read.unchanged is True
    assert read.truncated is False


def test_parse_read_response_never_coerces_a_null_field_to_the_string_none():
    # str(None) is "None" -- a truthy four-character value that would sail
    # straight through FR-24's etag check.
    read = parse_read_response('{"unchanged":true,"etag":"E7","path":null}')
    assert (read.path, read.etag) == ("", "E7")


def test_parse_read_response_refuses_an_unchanged_answer_with_no_etag():
    # The etag is the whole point of the short-circuit: an empty one would
    # be stored as the next poll's if_none_match and silently turn the
    # cheap etag poll into a full download every cycle.
    for text in (
        '{"unchanged":true,"path":"Deck.dc.html"}',
        '{"unchanged":true,"etag":null,"path":"Deck.dc.html"}',
        '{"unchanged":true,"etag":"","path":"Deck.dc.html"}',
    ):
        with pytest.raises(TransportCallError, match="no etag"):
            parse_read_response(text)


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


# --- FR-24: require_conditional, the shared pre-flight check --------------


def test_require_conditional_accepts_a_zero_etag():
    require_conditional(
        "write_files", [{"path": "a", "if_match": "0"}], allow_leaf=False
    )


@pytest.mark.parametrize("etag", [None, "", 5, 0, True, ["x"], {"a": "0"}])
def test_require_conditional_demands_a_non_empty_string_etag(etag):
    # Truthiness is not the test: 5, True and ["x"] are shapes the server
    # never sends, and accepting one would authorize an unconditional write.
    with pytest.raises(UnconditionalWriteError):
        require_conditional(
            "write_files", [{"path": "a", "if_match": etag}], allow_leaf=False
        )


def test_require_conditional_rejects_a_non_mapping_entry():
    # Letting this through raises AttributeError, which escapes AD-6's
    # single HeraldError catch at the CLI boundary.
    with pytest.raises(UnconditionalWriteError):
        require_conditional("write_files", ["a.html"], allow_leaf=False)


def test_require_conditional_rejects_an_empty_sequence():
    with pytest.raises(UnconditionalWriteError):
        require_conditional("write_files", [], allow_leaf=False)


def test_require_conditional_accepts_a_populated_leaf_etag_map():
    require_conditional(
        "copy_files",
        [{"dest": "assets", "leaf_if_match": {"assets/a.css": "0"}}],
        allow_leaf=True,
    )


@pytest.mark.parametrize("leaf", [{}, {"assets/a.css": ""}, {"assets/a.css": 0}, "0"])
def test_require_conditional_demands_a_populated_leaf_etag_map(leaf):
    with pytest.raises(UnconditionalWriteError):
        require_conditional(
            "copy_files", [{"dest": "assets", "leaf_if_match": leaf}], allow_leaf=True
        )


# --- the harness itself ----------------------------------------------------


def test_tool_result_defaults_to_success():
    assert ToolResult(text="ok").is_error is False


def test_the_fake_caller_refuses_to_answer_past_its_canned_list(fake_caller):
    caller = fake_caller({"read_file": [ToolResult(text="{}")]})
    caller.call_tool("read_file", {})
    with pytest.raises(AssertionError):
        caller.call_tool("read_file", {})


def test_the_deny_harness_is_active_for_unmarked_tests(network_denied_error):
    with pytest.raises(network_denied_error):
        socket.getaddrinfo("api.anthropic.com", 443)
    with pytest.raises(network_denied_error):
        socket.create_connection(("api.anthropic.com", 443))
    with pytest.raises(network_denied_error):
        socket.gethostbyname("api.anthropic.com")
    # connect() is the one that matters for an IP-literal destination: it
    # needs no resolver at all, so the two above would never fire.
    with socket.socket() as sock:
        with pytest.raises(network_denied_error):
            sock.connect(("93.184.216.34", 443))
        with pytest.raises(network_denied_error):
            sock.connect_ex(("93.184.216.34", 443))
    # ... and sendto needs no connect at all.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as datagram:
        with pytest.raises(network_denied_error):
            datagram.sendto(b"x", ("93.184.216.34", 53))
