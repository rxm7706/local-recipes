"""Story 1.4 — the sole formatter (AD-8): envelope shape, determinism,
text/json parity through `write`, errors rendering."""

from __future__ import annotations

import io
import json

from pyforge.mason import render


def test_render_json_carries_exactly_the_five_envelope_keys():
    doc = json.loads(render.render_json("doctor", "ok", {"message": "hi"}, []))
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["schema_version"] == render.SCHEMA_VERSION
    assert doc["command"] == "doctor"
    assert doc["status"] == "ok"
    assert doc["data"] == {"message": "hi"}
    assert doc["errors"] == []


def test_render_json_is_deterministic_across_calls():
    args = ("doctor", "ok", {"b": 1, "a": 2}, [{"identifier": "x:y", "message": "z"}])
    first = render.render_json(*args)
    second = render.render_json(*args)
    assert first == second


def test_render_json_sorts_keys_regardless_of_insertion_order():
    forward = render.render_json("doctor", "ok", {"a": 1, "b": 2}, [])
    backward = render.render_json("doctor", "ok", {"b": 2, "a": 1}, [])
    assert forward == backward


def test_write_json_format_emits_one_parseable_document(capsys):
    stream = io.StringIO()
    render.write("json", stream, "doctor", "ok", {"message": "hi"}, [])
    output = stream.getvalue()
    # Exactly one JSON document plus the single trailing newline `write`
    # appends -- byte-equality, because json.loads alone tolerates extra
    # surrounding whitespace and would pass a doubled/padded document.
    assert output == render.render_json("doctor", "ok", {"message": "hi"}, []) + "\n"
    doc = json.loads(output)
    assert doc["command"] == "doctor"
    assert doc["status"] == "ok"


def test_write_text_format_renders_a_human_readable_summary():
    stream = io.StringIO()
    render.write("text", stream, "doctor", "ok", {"message": "hi there"}, [])
    output = stream.getvalue()
    assert "doctor" in output
    assert "ok" in output
    assert "hi there" in output


def test_write_falls_back_to_text_for_an_out_of_choices_fmt_value():
    """Only exactly `"json"` selects JSON rendering -- any other value (e.g.
    an unvalidated `MASON_FORMAT` env value) renders as text, matching
    `_resolve_str`'s invalid-value-falls-back-to-default philosophy rather
    than raising."""
    stream = io.StringIO()
    render.write("bogus", stream, "doctor", "ok", {"message": "hi"}, [])
    output = stream.getvalue()
    assert output == render.render_text("doctor", "ok", {"message": "hi"}, []) + "\n"


def test_write_flushes_the_stream():
    class _TrackingStream(io.StringIO):
        def __init__(self):
            super().__init__()
            self.flushed = False

        def flush(self):
            self.flushed = True
            super().flush()

    stream = _TrackingStream()
    render.write("text", stream, "doctor", "ok", {"message": "hi"}, [])
    assert stream.flushed is True


def test_write_never_invokes_render_text_for_json_format(monkeypatch):
    """`write` is the sole call site -- `render_text` must not run when
    `fmt == "json"`."""
    calls = []
    monkeypatch.setattr(render, "render_text", lambda *a, **k: calls.append(a) or "unused")
    stream = io.StringIO()
    render.write("json", stream, "doctor", "ok", {"message": "hi"}, [])
    assert calls == []
    assert json.loads(stream.getvalue())["command"] == "doctor"


def test_write_never_invokes_render_json_for_text_format(monkeypatch):
    calls = []
    monkeypatch.setattr(render, "render_json", lambda *a, **k: calls.append(a) or "unused")
    stream = io.StringIO()
    render.write("text", stream, "doctor", "ok", {"message": "hi"}, [])
    assert calls == []


def test_errors_render_verbatim_as_a_list_in_json():
    errors = [{"identifier": "x:y", "message": "z"}]
    doc = json.loads(render.render_json("doctor", "failed", {}, errors))
    assert doc["errors"] == errors


def test_errors_render_one_line_each_in_text():
    errors = [
        {"identifier": "x:y", "message": "z"},
        {"identifier": "a:b", "message": "c"},
    ]
    text = render.render_text("doctor", "failed", {}, errors)
    lines = text.splitlines()
    assert any("x:y" in line and "z" in line for line in lines)
    assert any("a:b" in line and "c" in line for line in lines)
    # One line per error -- not folded onto a shared line.
    assert sum(1 for line in lines if "x:y" in line) == 1
    assert sum(1 for line in lines if "a:b" in line) == 1
