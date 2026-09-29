"""Unit tests for ``pyforge.marshal.seed.regions.apply`` (Stories 8.3/8.4) --
covers the spec's I/O & Edge-Case Matrix: ordinary substitution, byte-for-
byte prefix/suffix preservation, a sha mismatch (raised before any write),
conflict-marker-shaped new body written verbatim, a CRLF file's terminator
preserved verbatim, and a model-version-only change (body text unchanged,
sha therefore unchanged too). Also proves the story's own core invariant --
``fs.replace_span`` is called EXACTLY ONCE per ``substitute_region`` call,
never zero (on the happy path) and never two.

Story 8.4 adds ``insert_region`` coverage: anchor-order-is-preference, the
EOF append fallback (with its leading blank line), both ``<top>`` cases, an
anchor-shadowed-inside-a-fence case, already-present idempotence, and
absent-file creation -- each asserting ``fs.replace_span``/``fs.write`` is
called exactly once on the write paths, and neither on the already-present
no-op.

Imports the ``apply`` module itself (not its individual functions), so the
call-count test can monkeypatch ``apply_module.fs.replace_span``/
``apply_module.fs.write`` -- the exact names ``substitute_region``/
``insert_region`` reference in their own module namespace, mirroring
``test_seed_fs.py``'s own precedent for ``fs.atomic_write_bytes``.

Regions are located by round-tripping through ``render_begin``/
``render_end`` (to construct a well-formed fixture) and ``parse_regions``
(to locate its real ``RegionSpan``), never by hand-computing byte offsets --
hand-computing an exact span is error-prone and the whole point of S-8.2's
own parser is to not need that.
"""

from __future__ import annotations

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.marshal.seed.fs import NeverWrite, NeverWriteViolation
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions import apply as apply_module
from pyforge.marshal.seed.regions.apply import (
    AnchorInsideExistingRegionError,
    InsertionOutcome,
    InsertionResult,
    RegionShaMismatchError,
    insert_region,
    substitute_region,
)
from pyforge.marshal.seed.regions.markers import (
    RegionFormat,
    region_sha,
    render_begin,
    render_end,
)
from pyforge.marshal.seed.regions.parse import RegionSpan, parse_regions

_VERSION = ModelVersion.parse("1.0.0")
_NEW_VERSION = ModelVersion.parse("1.1.0")


def _begin(name: str, sha: str, version: ModelVersion = _VERSION, fmt: RegionFormat = RegionFormat.HTML) -> str:
    return render_begin(fmt, name, version, sha)


def _end(name: str, fmt: RegionFormat = RegionFormat.HTML) -> str:
    return render_end(fmt, name)


def _doc(*lines: str, newline: str = "\n") -> str:
    return "".join(f"{line}{newline}" for line in lines)


def _slice(text: str, span: tuple[int, int]) -> str:
    start, end = span
    return text.encode("utf-8")[start:end].decode("utf-8")


# --- RegionShaMismatchError shape -------------------------------------------


def test_region_sha_mismatch_error_is_a_pyforge_error_and_a_value_error():
    assert issubclass(RegionShaMismatchError, PyforgeError)
    assert issubclass(RegionShaMismatchError, ValueError)


# --- ordinary substitution, I/O Matrix row 1 --------------------------------


def test_ordinary_substitution_updates_marker_and_body(tmp_path):
    old_body = "old body\n"
    old_sha = region_sha(old_body)
    text = _doc("intro", _begin("tiers", old_sha), "old body", _end("tiers"), "outro")
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")

    (region,) = parse_regions(text, RegionFormat.HTML)
    new_body = "new body\n"

    substitute_region(
        text,
        path,
        region,
        new_body,
        model_version=_NEW_VERSION,
        expected_sha=old_sha,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result_text = path.read_text(encoding="utf-8", newline="")
    new_sha = region_sha(new_body)
    expected = _doc(
        "intro",
        _begin("tiers", new_sha, version=_NEW_VERSION),
        "new body",
        _end("tiers"),
        "outro",
    )
    assert result_text == expected

    (result_region,) = parse_regions(result_text, RegionFormat.HTML)
    assert result_region.sha == new_sha
    assert result_region.model_version == _NEW_VERSION
    assert _slice(result_text, result_region.body_span) == new_body


# --- prefix/suffix preservation, I/O Matrix row 2 ---------------------------


def test_prefix_and_suffix_are_byte_for_byte_preserved(tmp_path):
    old_body = "old body\nsecond line\n"
    old_sha = region_sha(old_body)
    text = _doc(
        "prefix line one",
        "prefix line two",
        _begin("tiers", old_sha),
        "old body",
        "second line",
        _end("tiers"),
        "suffix line one",
        "suffix line two",
    )
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    original_bytes = text.encode("utf-8")

    (region,) = parse_regions(text, RegionFormat.HTML)
    new_body = "a very different, much longer replacement body\nwith more lines\nthan before\n"

    substitute_region(
        text,
        path,
        region,
        new_body,
        model_version=_VERSION,
        expected_sha=old_sha,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result_bytes = path.read_bytes()
    prefix = original_bytes[: region.begin_span[0]]
    suffix = original_bytes[region.body_span[1] :]

    # Everything BEFORE the combined span (begin_span[0]) is untouched...
    assert result_bytes[: len(prefix)] == prefix
    # ...and everything AFTER it (from body_span[1] onward in the ORIGINAL
    # file, incl. the `end` marker line and the suffix lines) is untouched
    # too, even though the combined span's own length changed.
    assert result_bytes[len(result_bytes) - len(suffix) :] == suffix


# --- sha mismatch, I/O Matrix row 3 -----------------------------------------


def test_sha_mismatch_raises_before_any_write_and_leaves_the_file_untouched(tmp_path, monkeypatch):
    body = "body\n"
    real_sha = region_sha(body)
    text = _doc(_begin("tiers", real_sha), "body", _end("tiers"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    (region,) = parse_regions(text, RegionFormat.HTML)

    calls: list[object] = []
    monkeypatch.setattr(apply_module.fs, "replace_span", lambda *a, **k: calls.append((a, k)))

    with pytest.raises(RegionShaMismatchError):
        substitute_region(
            text,
            path,
            region,
            "new body\n",
            model_version=_VERSION,
            expected_sha="deadbeef",
            fmt=RegionFormat.HTML,
            repo_root=tmp_path,
            never_write=NeverWrite(()),
        )

    # No write primitive was even reached, let alone the real filesystem.
    assert calls == []
    assert path.read_bytes() == text.encode("utf-8")


def test_sha_mismatch_message_names_the_path_region_and_both_shas(tmp_path):
    """Review finding: the message previously omitted the file path,
    making a batch/multi-file caller's failure unattributable from the
    exception message alone."""
    body = "body\n"
    real_sha = region_sha(body)
    text = _doc(_begin("tiers", real_sha), "body", _end("tiers"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    (region,) = parse_regions(text, RegionFormat.HTML)

    with pytest.raises(RegionShaMismatchError) as exc_info:
        substitute_region(
            text,
            path,
            region,
            "new body\n",
            model_version=_VERSION,
            expected_sha="deadbeef",
            fmt=RegionFormat.HTML,
            repo_root=tmp_path,
            never_write=NeverWrite(()),
        )

    message = str(exc_info.value)
    assert str(path) in message
    assert "tiers" in message
    assert real_sha in message
    assert "deadbeef" in message


def test_malformed_span_where_begin_ends_after_body_starts_raises_before_any_write(
    tmp_path,
):
    """Review finding: a real `parse_regions` output can never produce this
    (the body always starts at or after the begin line's own end), but a
    hand-constructed `RegionSpan` -- exactly the error-prone bypass this
    module's own docstring discourages -- could. Without this check, the
    negative-length slice silently returns `b""` and the new begin line
    gets concatenated directly onto the new body with no terminator and no
    error."""
    body = "body\n"
    old_sha = region_sha(body)
    text = _doc(_begin("tiers", old_sha), "body", _end("tiers"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    (real_region,) = parse_regions(text, RegionFormat.HTML)

    malformed = RegionSpan(
        name=real_region.name,
        model_version=real_region.model_version,
        sha=real_region.sha,
        body_span=(real_region.begin_span[1] - 5, real_region.body_span[1]),
        begin_span=real_region.begin_span,
        end_span=real_region.end_span,
    )

    with pytest.raises(ValueError, match="malformed span"):
        substitute_region(
            text,
            path,
            malformed,
            "new body\n",
            model_version=_VERSION,
            expected_sha=old_sha,
            fmt=RegionFormat.HTML,
            repo_root=tmp_path,
            never_write=NeverWrite(()),
        )
    assert path.read_bytes() == text.encode("utf-8")


def test_new_body_that_is_bytes_not_str_raises_type_error_before_any_write(tmp_path):
    """Review finding: `fs.replace_span` -- this module's own dependency --
    upfront-validates its `new_body: bytes` argument with a named
    `TypeError` for exactly this caller mistake, one layer down. Without a
    mirroring check here, a caller accidentally passing `bytes` (plausible,
    since `fs.replace_span` itself expects `bytes`) previously fell through
    to a bare, contextless `AttributeError` from `new_body.encode(...)`."""
    body = "body\n"
    old_sha = region_sha(body)
    text = _doc(_begin("tiers", old_sha), "body", _end("tiers"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    (region,) = parse_regions(text, RegionFormat.HTML)

    with pytest.raises(TypeError, match="new_body must be str"):
        substitute_region(
            text,
            path,
            region,
            b"new body\n",
            model_version=_VERSION,
            expected_sha=old_sha,
            fmt=RegionFormat.HTML,
            repo_root=tmp_path,
            never_write=NeverWrite(()),
        )
    assert path.read_bytes() == text.encode("utf-8")


# --- conflict-marker-shaped new body, I/O Matrix row 4 ----------------------


def test_conflict_marker_shaped_new_body_is_written_verbatim(tmp_path):
    old_body = "old body\n"
    old_sha = region_sha(old_body)
    text = _doc(_begin("tiers", old_sha), "old body", _end("tiers"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    (region,) = parse_regions(text, RegionFormat.HTML)
    new_body = "<<<<<<< HEAD\n=======\n>>>>>>> branch\n"

    substitute_region(
        text,
        path,
        region,
        new_body,
        model_version=_VERSION,
        expected_sha=old_sha,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result_text = path.read_text(encoding="utf-8", newline="")
    (result_region,) = parse_regions(result_text, RegionFormat.HTML)
    assert _slice(result_text, result_region.body_span) == new_body


# --- CRLF file, I/O Matrix row 5 --------------------------------------------


def test_crlf_terminator_is_preserved_verbatim(tmp_path):
    old_body = "old body\r\n"
    old_sha = region_sha(old_body)
    text = _doc("intro", _begin("tiers", old_sha), "old body", _end("tiers"), "outro", newline="\r\n")
    path = tmp_path / "doc.md"
    path.write_bytes(text.encode("utf-8"))

    # Read with newline="" -- NOT plain read_text() -- so \r\n is preserved
    # verbatim rather than translated to \n, keeping `disk_text`'s byte
    # offsets in sync with the file's real on-disk bytes (the module's own
    # documented requirement).
    disk_text = path.read_text(encoding="utf-8", newline="")
    (region,) = parse_regions(disk_text, RegionFormat.HTML)
    new_body = "new body\r\n"

    substitute_region(
        disk_text,
        path,
        region,
        new_body,
        model_version=_VERSION,
        expected_sha=old_sha,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result_text = path.read_text(encoding="utf-8", newline="")
    (result_region,) = parse_regions(result_text, RegionFormat.HTML)
    terminator = result_text.encode("utf-8")[result_region.begin_span[1] : result_region.body_span[0]]
    assert terminator == b"\r\n"
    assert _slice(result_text, result_region.body_span) == new_body
    # Every other CRLF elsewhere in the file (outside the combined span) is
    # unaffected.
    assert result_text.startswith("intro\r\n")
    assert result_text.endswith("outro\r\n")


# --- never_write guard propagation -------------------------------------------


def test_a_real_non_empty_never_write_guard_blocks_the_write_end_to_end(tmp_path):
    """Review finding: every prior test passed an empty `NeverWrite(())`,
    so nothing proved `substitute_region` actually propagates a REAL
    guard's refusal rather than silently swallowing or bypassing it."""
    body = "body\n"
    old_sha = region_sha(body)
    text = _doc(_begin("tiers", old_sha), "body", _end("tiers"))
    path = tmp_path / "docs" / "dreams" / "doc.md"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8", newline="")
    (region,) = parse_regions(text, RegionFormat.HTML)

    with pytest.raises(NeverWriteViolation):
        substitute_region(
            text,
            path,
            region,
            "new body\n",
            model_version=_VERSION,
            expected_sha=old_sha,
            fmt=RegionFormat.HTML,
            repo_root=tmp_path,
            never_write=NeverWrite(("docs/dreams/*.md",)),
        )

    assert path.read_bytes() == text.encode("utf-8")


# --- body-only change (mirrors the model-version-only test below) ----------


def test_body_only_change_updates_the_sha_but_keeps_the_declared_version(tmp_path):
    """Mirrors `test_model_version_only_change_...` in the other direction:
    the body text changes (so the sha must change) while `model_version`
    is passed unchanged."""
    old_body = "old body\n"
    old_sha = region_sha(old_body)
    text = _doc(_begin("tiers", old_sha), "old body", _end("tiers"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    (region,) = parse_regions(text, RegionFormat.HTML)
    new_body = "a genuinely different body\n"

    substitute_region(
        text,
        path,
        region,
        new_body,
        model_version=_VERSION,  # unchanged
        expected_sha=old_sha,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result_text = path.read_text(encoding="utf-8", newline="")
    (result_region,) = parse_regions(result_text, RegionFormat.HTML)
    assert result_region.sha == region_sha(new_body)
    assert result_region.sha != old_sha
    assert result_region.model_version == _VERSION


# --- multi-region hazard and the safe re-parse-between-calls pattern -------


def test_reusing_stale_offsets_across_two_regions_in_one_file_corrupts_the_second(
    tmp_path,
):
    """Review finding (both reviewers, independently): every `RegionSpan`'s
    byte offsets are only valid against the exact bytes they were parsed
    from. This proves the HAZARD is real -- substituting region "a" (with a
    different-length new body) shifts every byte after it, so region "b"'s
    STALE offsets (from the same, now-outdated `parse_regions` pass) no
    longer point at region "b" at all once naively reused."""
    a_body = "a\n"
    b_body = "b\n"
    a_sha = region_sha(a_body)
    b_sha = region_sha(b_body)
    text = _doc(_begin("a", a_sha), "a", _end("a"), _begin("b", b_sha), "b", _end("b"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")

    region_a, stale_region_b = parse_regions(text, RegionFormat.HTML)
    assert stale_region_b.name == "b"

    # Region "a"'s new body is much longer than the old one -- shifts every
    # byte offset after it, including everything belonging to region "b".
    much_longer_a_body = "a much longer replacement body for region a\n"
    substitute_region(
        text,
        path,
        region_a,
        much_longer_a_body,
        model_version=_VERSION,
        expected_sha=a_sha,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    # Reusing region "b"'s STALE offsets (from the pre-substitution parse)
    # against the file's NEW bytes is exactly the misuse this module's
    # docstring warns against -- it does not point at region "b" anymore.
    new_text = path.read_text(encoding="utf-8", newline="")
    stale_slice = _slice(new_text, stale_region_b.body_span)
    assert stale_slice != b_body, (
        "the stale span coincidentally still pointed at region b's body -- "
        "strengthen this fixture's length difference so the hazard is unambiguous"
    )


def test_reparsing_between_calls_correctly_substitutes_both_regions(tmp_path):
    """The SAFE pattern the module's docstring recommends: re-parse (fresh
    `parse_regions`) between each `substitute_region` call rather than
    reusing offsets from one original pass -- proves this avoids the
    corruption the test above demonstrates."""
    a_body = "a\n"
    b_body = "b\n"
    a_sha = region_sha(a_body)
    b_sha = region_sha(b_body)
    text = _doc(_begin("a", a_sha), "a", _end("a"), _begin("b", b_sha), "b", _end("b"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")

    region_a, _ = parse_regions(text, RegionFormat.HTML)
    much_longer_a_body = "a much longer replacement body for region a\n"
    substitute_region(
        text,
        path,
        region_a,
        much_longer_a_body,
        model_version=_VERSION,
        expected_sha=a_sha,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    # Re-read and re-parse FRESH before substituting region "b" -- the safe
    # pattern.
    text_after_a = path.read_text(encoding="utf-8", newline="")
    _, fresh_region_b = parse_regions(text_after_a, RegionFormat.HTML)
    new_b_body = "a new body for region b\n"
    substitute_region(
        text_after_a,
        path,
        fresh_region_b,
        new_b_body,
        model_version=_VERSION,
        expected_sha=b_sha,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    final_text = path.read_text(encoding="utf-8", newline="")
    region_a_final, region_b_final = parse_regions(final_text, RegionFormat.HTML)
    assert _slice(final_text, region_a_final.body_span) == much_longer_a_body
    assert _slice(final_text, region_b_final.body_span) == new_b_body


# --- model_version-only change, I/O Matrix row 6 ----------------------------


def test_model_version_only_change_keeps_the_sha_but_updates_the_declared_version(tmp_path):
    body = "same body\n"
    old_sha = region_sha(body)
    text = _doc(_begin("tiers", old_sha), "same body", _end("tiers"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    (region,) = parse_regions(text, RegionFormat.HTML)

    substitute_region(
        text,
        path,
        region,
        body,  # new_body == the old body's text, unchanged
        model_version=_NEW_VERSION,
        expected_sha=old_sha,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result_text = path.read_text(encoding="utf-8", newline="")
    (result_region,) = parse_regions(result_text, RegionFormat.HTML)
    assert result_region.sha == old_sha
    assert result_region.model_version == _NEW_VERSION
    assert result_region.model_version != _VERSION


# --- fs.replace_span called exactly once ------------------------------------


def test_fs_replace_span_is_called_exactly_once_per_substitution(tmp_path, monkeypatch):
    """The story's own core invariant: never zero calls (the write must
    happen) and never two (which would open a half-merged-on-crash window)
    -- exactly one, carrying the combined marker+terminator+body payload."""
    body = "body\n"
    old_sha = region_sha(body)
    text = _doc(_begin("tiers", old_sha), "body", _end("tiers"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    (region,) = parse_regions(text, RegionFormat.HTML)
    new_body = "new body\n"

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_replace_span(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(apply_module.fs, "replace_span", fake_replace_span)

    substitute_region(
        text,
        path,
        region,
        new_body,
        model_version=_VERSION,
        expected_sha=old_sha,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] == path
    assert args[1] == region.begin_span[0]
    assert args[2] == region.body_span[1]
    expected_new_sha = region_sha(new_body)
    expected_begin_line = render_begin(RegionFormat.HTML, "tiers", _VERSION, expected_new_sha)
    assert args[3] == expected_begin_line.encode("utf-8") + b"\n" + new_body.encode("utf-8")
    assert kwargs == {"repo_root": tmp_path, "never_write": NeverWrite(())}

    # The fake never actually wrote anything -- proving substitute_region
    # itself has no OTHER write path (no Path.write_text, no second
    # fs.replace_span call) that could have mutated the file instead.
    assert path.read_bytes() == text.encode("utf-8")


# =============================================================================
# Story 8.4: insert_region
# =============================================================================


def _rendered_region(
    name: str, body: str, version: ModelVersion = _VERSION, fmt: RegionFormat = RegionFormat.HTML
) -> str:
    """The exact freestanding-region payload ``insert_region`` renders for a
    brand-new region -- built the same round-trip way the rest of this file
    constructs fixtures, never hand-assembled byte-for-byte."""
    sha = region_sha(body)
    return f"{render_begin(fmt, name, version, sha)}\n{body}{render_end(fmt, name)}\n"


# --- matched anchor, I/O Matrix row 1 ---------------------------------------


def test_insert_region_inserts_immediately_after_the_matching_anchor_line(tmp_path):
    text = "intro\n## The tiers\nrest of section\n"
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    outcome = insert_region(
        text,
        path,
        "tiers",
        ("## The tiers",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert outcome == InsertionResult(outcome=InsertionOutcome.INSERTED, matched="## The tiers")
    result = path.read_text(encoding="utf-8", newline="")
    assert result == ("intro\n## The tiers\n" + _rendered_region("tiers", body) + "rest of section\n")
    (span,) = parse_regions(result, RegionFormat.HTML)
    assert span.name == "tiers"


# --- earlier anchor absent, later matches, I/O Matrix row 2 ----------------


def test_insert_region_ignores_an_earlier_absent_anchor_and_uses_a_later_match(tmp_path):
    """AD-56's own example: order is a PREFERENCE, not a file-position
    search -- the earlier, absent anchor is ignored entirely."""
    text = "intro\n# CLAUDE.md\nmore content\n"
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    outcome = insert_region(
        text,
        path,
        "tiers",
        ("## The tiers", "# CLAUDE.md", "<top>"),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert outcome.matched == "# CLAUDE.md"
    result = path.read_text(encoding="utf-8", newline="")
    assert result == ("intro\n# CLAUDE.md\n" + _rendered_region("tiers", body) + "more content\n")


# --- no anchor matches, no <top>, I/O Matrix row 3 --------------------------


def test_insert_region_appends_at_eof_with_a_leading_blank_line_when_nothing_matches(tmp_path):
    text = "intro\nsome content\n"
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    outcome = insert_region(
        text,
        path,
        "tiers",
        ("## Nope",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert outcome == InsertionResult(outcome=InsertionOutcome.INSERTED, matched=None)
    result = path.read_text(encoding="utf-8", newline="")
    assert result == text + "\n" + _rendered_region("tiers", body)


# --- <top> with frontmatter, I/O Matrix row 4 -------------------------------


def test_insert_region_with_top_inserts_after_the_frontmatter_block(tmp_path):
    text = "---\ntitle: x\n---\n# Heading\nbody\n"
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    outcome = insert_region(
        text,
        path,
        "tiers",
        ("<top>",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert outcome.matched == "<top>"
    result = path.read_text(encoding="utf-8", newline="")
    assert result == ("---\ntitle: x\n---\n" + _rendered_region("tiers", body) + "# Heading\nbody\n")


# --- <top> without frontmatter, I/O Matrix row 5 ----------------------------


def test_insert_region_with_top_and_no_frontmatter_inserts_at_byte_zero(tmp_path):
    text = "# Heading\nbody\n"
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    outcome = insert_region(
        text,
        path,
        "tiers",
        ("<top>",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert outcome.matched == "<top>"
    result = path.read_text(encoding="utf-8", newline="")
    assert result == _rendered_region("tiers", body) + text


# --- anchor shadowed inside a fence, I/O Matrix row 6 -----------------------


def test_insert_region_skips_an_anchor_line_shadowed_inside_a_fence(tmp_path):
    text = "intro\n```markdown\n## The tiers\n```\noutro\n"
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    insert_region(
        text,
        path,
        "tiers",
        ("## The tiers",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    # No real match -- falls through to the EOF append fallback, exactly
    # like row 3, proving the fenced line was never treated as a match.
    result = path.read_text(encoding="utf-8", newline="")
    assert result == text + "\n" + _rendered_region("tiers", body)


# --- region already present, I/O Matrix row 7 -------------------------------


def test_insert_region_is_a_noop_when_the_region_already_exists(tmp_path, monkeypatch):
    body = "old body\n"
    text = _doc(_begin("tiers", region_sha(body)), "old body", _end("tiers"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")

    replace_calls: list[object] = []
    write_calls: list[object] = []
    monkeypatch.setattr(apply_module.fs, "replace_span", lambda *a, **k: replace_calls.append((a, k)))
    monkeypatch.setattr(apply_module.fs, "write", lambda *a, **k: write_calls.append((a, k)))

    outcome = insert_region(
        text,
        path,
        "tiers",
        ("<top>",),
        "a different body\n",
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert outcome == InsertionResult(outcome=InsertionOutcome.ALREADY_PRESENT, matched=None)
    assert replace_calls == []
    assert write_calls == []
    assert path.read_bytes() == text.encode("utf-8")


# --- absent file, I/O Matrix row 8 ------------------------------------------


def test_insert_region_creates_an_absent_file_containing_only_the_rendered_region(tmp_path):
    path = tmp_path / "new.md"
    body = "new body\n"

    outcome = insert_region(
        None,
        path,
        "tiers",
        ("<top>",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert outcome == InsertionResult(outcome=InsertionOutcome.INSERTED, matched=None)
    result = path.read_text(encoding="utf-8", newline="")
    assert result == _rendered_region("tiers", body)
    (span,) = parse_regions(result, RegionFormat.HTML)
    assert span.name == "tiers"


# --- fs.replace_span called exactly once, never fs.write -------------------


def test_insert_region_calls_fs_replace_span_exactly_once_never_fs_write(tmp_path, monkeypatch):
    """The story's own core invariant on the existing-file path: never zero
    (the write must happen) and never two -- exactly one, and never the
    OTHER write primitive either."""
    text = "intro\n## The tiers\nrest\n"
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")

    replace_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    write_calls: list[object] = []
    monkeypatch.setattr(apply_module.fs, "replace_span", lambda *a, **k: replace_calls.append((a, k)))
    monkeypatch.setattr(apply_module.fs, "write", lambda *a, **k: write_calls.append((a, k)))

    insert_region(
        text,
        path,
        "tiers",
        ("## The tiers",),
        "new body\n",
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert len(replace_calls) == 1
    assert write_calls == []
    args, kwargs = replace_calls[0]
    assert args[0] == path
    # Zero-width span -- an insertion, never a substitution.
    assert args[1] == args[2]
    assert kwargs == {"repo_root": tmp_path, "never_write": NeverWrite(())}
    # The fake never actually wrote anything -- the real file is untouched.
    assert path.read_bytes() == text.encode("utf-8")


# --- fs.write called exactly once, never fs.replace_span, absent file ------


def test_insert_region_calls_fs_write_exactly_once_never_fs_replace_span_for_an_absent_file(tmp_path, monkeypatch):
    path = tmp_path / "new.md"
    body = "new body\n"

    replace_calls: list[object] = []
    write_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(apply_module.fs, "replace_span", lambda *a, **k: replace_calls.append((a, k)))
    monkeypatch.setattr(apply_module.fs, "write", lambda *a, **k: write_calls.append((a, k)))

    insert_region(
        None,
        path,
        "tiers",
        ("<top>",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert replace_calls == []
    assert len(write_calls) == 1
    args, kwargs = write_calls[0]
    assert args[0] == path
    assert args[1] == _rendered_region("tiers", body).encode("utf-8")
    assert kwargs == {"repo_root": tmp_path, "never_write": NeverWrite(())}
    # The fake never actually wrote anything -- the file stays absent.
    assert not path.exists()


# --- anchor collides with an existing region's span (review finding) -------


def test_insert_region_raises_when_the_anchor_falls_inside_an_existing_region(tmp_path):
    """The anchor text happens to also appear as ordinary content inside an
    UNRELATED existing region's own body -- naively inserting there would
    splice a brand-new region's markers into the middle of that region,
    producing the exact nested/overlapping structure AR-1 forbids."""
    # The anchor is a literal LINE-PREFIX matcher (`str.startswith`), so the
    # colliding line must itself START WITH the anchor text -- e.g. a
    # documentation example inside the existing region's own body.
    other_body = "## The tiers\nmore explanation\n"
    text = _doc(_begin("other", region_sha(other_body)), "## The tiers", "more explanation", _end("other"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")

    with pytest.raises(AnchorInsideExistingRegionError, match="other"):
        insert_region(
            text,
            path,
            "tiers",
            ("## The tiers",),
            "new body\n",
            model_version=_VERSION,
            fmt=RegionFormat.HTML,
            repo_root=tmp_path,
            never_write=NeverWrite(()),
        )

    # No write attempted -- the file is byte-for-byte untouched.
    assert path.read_bytes() == text.encode("utf-8")


def test_anchor_inside_existing_region_error_is_a_pyforge_error_and_a_value_error():
    assert issubclass(AnchorInsideExistingRegionError, PyforgeError)
    assert issubclass(AnchorInsideExistingRegionError, ValueError)


def test_insert_region_allows_an_anchor_immediately_before_an_existing_regions_begin_marker(
    tmp_path,
):
    """The boundary case: the anchor's line ends EXACTLY where an existing
    region's begin marker starts -- inserting there sits BEFORE the region,
    never inside it, so it must be allowed, not rejected."""
    other_body = "old body\n"
    text = _doc("## The tiers", _begin("other", region_sha(other_body)), "old body", _end("other"))
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")

    insert_region(
        text,
        path,
        "tiers",
        ("## The tiers",),
        "new body\n",
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result = path.read_text(encoding="utf-8", newline="")
    (span,) = [s for s in parse_regions(result, RegionFormat.HTML) if s.name == "tiers"]
    assert span is not None


# --- EOF append blank-line correctness (review finding) ---------------------


def test_eof_append_adds_a_blank_line_when_text_has_no_trailing_newline(tmp_path):
    text = "intro\nsome content"  # deliberately no trailing "\n"
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    insert_region(
        text,
        path,
        "tiers",
        ("## Nope",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result = path.read_text(encoding="utf-8", newline="")
    assert result == text + "\n\n" + _rendered_region("tiers", body)


def test_eof_append_does_not_double_an_already_present_blank_line(tmp_path):
    text = "intro\nsome content\n\n"  # already ends in a blank line
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    insert_region(
        text,
        path,
        "tiers",
        ("## Nope",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result = path.read_text(encoding="utf-8", newline="")
    assert result == text + _rendered_region("tiers", body)


def test_eof_append_adds_no_leading_blank_line_for_a_present_but_empty_file(tmp_path):
    text = ""  # the file exists on disk but is zero bytes, distinct from text=None
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    insert_region(
        text,
        path,
        "tiers",
        ("## Nope",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result = path.read_text(encoding="utf-8", newline="")
    assert result == _rendered_region("tiers", body)


def test_eof_append_adds_a_blank_line_when_a_crlf_file_has_no_trailing_blank_line(tmp_path):
    """Review finding: the original fixed ``"\\n\\n"`` suffix check never
    recognized a CRLF file's own blank line, so this CRLF case previously
    fell through to the "ends in a single terminator" branch and got a
    bare LF-only blank line stacked onto all-CRLF content."""
    text = "intro\r\nsome content\r\n"  # single CRLF terminator, no blank line yet
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    insert_region(
        text,
        path,
        "tiers",
        ("## Nope",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result = path.read_text(encoding="utf-8", newline="")
    assert result == text + "\n" + _rendered_region("tiers", body)


def test_eof_append_does_not_double_an_already_present_crlf_blank_line(tmp_path):
    """Review finding: without terminator-agnostic detection, a CRLF file
    already ending in a blank line (``"...\\r\\n\\r\\n"``) got a SECOND,
    LF-only blank line appended -- violating "never two" and mixing
    line-ending styles in the output."""
    text = "intro\r\nsome content\r\n\r\n"  # already ends in a CRLF blank line
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")
    body = "new body\n"

    insert_region(
        text,
        path,
        "tiers",
        ("## Nope",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result = path.read_text(encoding="utf-8", newline="")
    assert result == text + _rendered_region("tiers", body)


# --- repeated insertions at the same anchor (review finding) ---------------


def test_repeated_insertions_at_the_same_anchor_accumulate_nearest_anchor_first(tmp_path):
    """Documents (module docstring, "Repeated insert_region calls...") that
    this is the literal, spec-mandated consequence of "insertion occurs
    immediately after the first matching anchor line" applied twice -- not
    a stale-offset hazard, since this reproduces even with a correct
    re-detect-between-calls pattern (each call re-reads the file the prior
    call actually wrote)."""
    text = "intro\n## The tiers\nrest\n"
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8", newline="")

    insert_region(
        text,
        path,
        "first",
        ("## The tiers",),
        "first body\n",
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )
    text_after_first = path.read_text(encoding="utf-8", newline="")

    insert_region(
        text_after_first,
        path,
        "second",
        ("## The tiers",),
        "second body\n",
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )
    result = path.read_text(encoding="utf-8", newline="")

    spans = {span.name: span for span in parse_regions(result, RegionFormat.HTML)}
    assert spans["second"].begin_span[0] < spans["first"].begin_span[0]


# --- body without a trailing newline glues the end marker onto its line ----


def test_body_without_a_trailing_newline_glues_the_end_marker_onto_its_own_line(tmp_path):
    """Mirrors ``substitute_region``'s own ``new_body`` contract: this
    primitive does not append a trailing newline on the caller's behalf."""
    path = tmp_path / "doc.md"
    body = "no trailing newline"

    insert_region(
        None,
        path,
        "tiers",
        ("<top>",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    result = path.read_text(encoding="utf-8", newline="")
    expected_end_line = render_end(RegionFormat.HTML, "tiers")
    assert result.endswith(f"{body}{expected_end_line}\n")
    assert f"{body}\n{expected_end_line}" not in result


# --- InsertionResult shape ---------------------------------------------------


def test_insertion_result_is_frozen():
    result = InsertionResult(outcome=InsertionOutcome.INSERTED, matched=None)
    with pytest.raises(AttributeError):
        result.matched = "x"  # pyright: ignore[reportAttributeAccessIssue]
