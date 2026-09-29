"""Unit tests for ``pyforge.doctor.sources.chain._frontmatter_parse``, its
``_skip_leading_banner`` helper, and the body-side reader of the same
boundary, ``_dream_body_after_frontmatter`` (Story 28.1 / CAP-81).

Covers every case in the story spec's Design Notes § Primitive tests
directly against the parser, independent of any particular caller
(``_collect_dreams``, ``parse_spec_frontmatter_deferrals``, etc. each have
their own fixture coverage in sibling test files; this file pins the shared
primitive itself).

The central regression is exercised in ``test_sources_chain_deferred_work.py``
against a byte-verbatim SNAPSHOT of marshal's Story 50.5 tracked spec (the
file that first surfaced the bug): reverting ``_frontmatter_parse`` to the
old ``text.split("---", 2)`` implementation was verified, during
development, to make that fixture test fail (the mid-scalar ``"---"`` in the
first deferral's ``evidence:`` truncates the YAML block, losing the second
deferral entirely and the first deferral's ``location:``). That verification
is not re-encoded as a second, parallel "old implementation" here -- see the
story spec's own Verification § Manual checks for the requirement -- but the
fixture test's own precision (exact deferral count, exact fingerprints) is
what would catch a regression to the old behavior.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor.sources import chain


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# --- No leading fence: absent metadata, never unparseable -------------------


def test_prose_file_with_a_rule_and_no_leading_fence_is_absent_not_unparseable(
    tmp_path: Path,
) -> None:
    """A markdown thematic break (``---`` on its own line, mid-document) is
    common prose, not a frontmatter declaration -- the file never starts
    with ``---``, so this is absent metadata (``({}, False)``), not a
    malformed-frontmatter WARN. This is the second of the two bugs Story
    28.1 fixes: the old ``if "---" in text: return {}, True`` treated ANY
    ``---`` occurrence anywhere in the document as a frontmatter attempt."""
    path = _write(
        tmp_path,
        "prose.md",
        "# Title\n\nSome text.\n\n---\n\nMore text after a horizontal rule.\n",
    )
    assert chain._frontmatter_parse(path) == ({}, False)


def test_plain_prose_with_no_dashes_at_all_is_absent(tmp_path: Path) -> None:
    path = _write(tmp_path, "plain.md", "just plain prose, no dashes at all\n")
    assert chain._frontmatter_parse(path) == ({}, False)


def test_prose_preceding_a_looks_like_frontmatter_block_is_absent_not_unparseable(
    tmp_path: Path,
) -> None:
    """A ``---``-delimited block that does not start the file (leading prose
    above it) is not a frontmatter declaration either, even though its
    interior parses as a clean YAML mapping -- the fence must be
    line-anchored at the TOP of the document, not merely present somewhere.
    Supersedes the pre-28.1 expectation (Story 17-1 / FR-144) that this
    exact shape was ``unparseable-frontmatter``; see
    ``test_sources_chain_dream_chain.py``'s updated sibling test for the
    ``gather_dream_chain``-level consequence."""
    path = _write(
        tmp_path,
        "nofence.md",
        "Prose that precedes the fence.\n---\nowner: marshal\nstatus: shipped\n---\n",
    )
    assert chain._frontmatter_parse(path) == ({}, False)


def test_leading_blank_line_before_the_fence_is_absent(tmp_path: Path) -> None:
    """The opening fence must be the FIRST line (after an optional banner);
    a blank line above it means line 1 is neither a fence nor an attempted
    opener -- absent metadata, per Design Notes § Opener rule."""
    path = _write(tmp_path, "blank_first.md", "\n---\ntitle: x\n---\n\nBody.\n")
    assert chain._frontmatter_parse(path) == ({}, False)


def test_utf8_bom_before_a_bare_fence_is_absent(tmp_path: Path) -> None:
    """A UTF-8 BOM before a bare ``---`` (no banner): line 1 is ``\\ufeff---``,
    which is neither a fence nor -- since a BOM is not whitespace to
    ``str.strip()`` -- an attempted opener, so absent metadata: the Design
    Notes' chosen verdict (review pass 1, BH6/ECH3: 0 live instances)."""
    path = _write(tmp_path, "bom.md", "\ufeff---\ntitle: x\nstatus: draft\n---\n\nBody.\n")
    assert chain._frontmatter_parse(path) == ({}, False)


# --- Line-anchored closing fence: unbounded stays refused, never silent -----


def test_unclosed_fence_is_unparseable(tmp_path: Path) -> None:
    """The file starts with a real ``---`` opener but no line further down
    is exactly ``---`` -- an unbounded block must stay ``({}, True)``
    (Story 17-1 / FR-144's refusal semantics; Story 28.1's own Never
    clause: do not widen what counts as parseable)."""
    path = _write(
        tmp_path,
        "unclosed.md",
        "---\ntitle: x\nstatus: draft\n\nNo closing fence anywhere in this file.\n",
    )
    assert chain._frontmatter_parse(path) == ({}, True)


def test_a_mid_scalar_dashes_does_not_end_the_block_early(tmp_path: Path) -> None:
    """The exact defect class Story 28.1 fixes, in miniature: a YAML folded
    scalar quoting the literal text ``"---"`` must not be mistaken for the
    closing fence. The old ``text.split("---", 2)`` truncated here; the fix
    must read through to the REAL closing fence on its own line."""
    path = _write(
        tmp_path,
        "quoted-dashes.md",
        (
            "---\n"
            "title: canary\n"
            "note: >-\n"
            '  the gate still checks lines[0] == "---" with no banner-skip\n'
            "status: draft\n"
            "---\n\nbody\n"
        ),
    )
    fields, unparseable = chain._frontmatter_parse(path)
    assert unparseable is False
    assert fields.get("status") == "draft"
    assert fields.get("title") == "canary"
    assert fields.get("note") == 'the gate still checks lines[0] == "---" with no banner-skip'


def test_a_single_line_quoted_dashes_value_parses(tmp_path: Path) -> None:
    """``title: "---"`` on one line: the ``---`` is INSIDE a quoted scalar on
    a line that is not itself a fence (``line.rstrip() != "---"``), so the
    block reads through to the real closing fence."""
    path = _write(
        tmp_path,
        "quoted-title.md",
        '---\ntitle: "---"\nstatus: draft\n---\n\nbody\n',
    )
    assert chain._frontmatter_parse(path) == ({"title": "---", "status": "draft"}, False)


def test_an_indented_dashes_line_inside_a_block_scalar_is_not_the_closing_fence(
    tmp_path: Path,
) -> None:
    """A literal block scalar (``evidence: |``) whose content includes an
    INDENTED ``  ---`` line: the fence test is ``rstrip() == "---"``, never
    ``strip()``, so the indented line stays inside the scalar and the keys
    declared AFTER it are still present. With ``strip()`` this closed the
    block early and returned ``({'title': 'x', 'evidence': ''}, False)`` --
    later keys silently dropped with ``unparseable=False`` (review pass 1,
    BH2/ECH2)."""
    path = _write(
        tmp_path,
        "indented-dashes.md",
        ("---\ntitle: x\nevidence: |\n  first line\n  ---\n  third line\nstatus: draft\nowner: doctor\n---\n\nbody\n"),
    )
    fields, unparseable = chain._frontmatter_parse(path)
    assert unparseable is False
    assert fields == {
        "title": "x",
        "evidence": "first line\n---\nthird line\n",
        "status": "draft",
        "owner": "doctor",
    }


def test_a_block_scalar_as_the_last_key_keeps_its_final_newline(tmp_path: Path) -> None:
    """The YAML handed to ``safe_load`` ends with a newline, as the old
    ``parts[1]`` slice did (it ran up to the newline before the closing
    fence): a ``|`` block scalar that is the LAST frontmatter key keeps its
    final line break, so the value is byte-identical to the old reader's
    (12 live atlas specs' ``frontmatter_note`` have this shape)."""
    path = _write(
        tmp_path,
        "last-key-block.md",
        "---\ntitle: x\nfrontmatter_note: |\n  first\n  second\n---\n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == (
        {"title": "x", "frontmatter_note": "first\nsecond\n"},
        False,
    )


# --- Opener rule: attempted but unbounded is refused, not degraded -----------


def test_glued_opener_is_unparseable_not_absent(tmp_path: Path) -> None:
    """``---title: x`` fused on line 1: the document ATTEMPTED a frontmatter
    block that cannot be bounded -- refused (``({}, True)``), never read as
    absent (that silently dropped owner/status/title on 34 archived Dreams
    at review pass 1) and never parsed leniently (marshal's
    ``is_valid_spec_text`` does; it is a smoke check, not this reader's
    contract)."""
    path = _write(
        tmp_path,
        "glued.md",
        "---title: x\nowner: doctor\nstatus: archived\n---\n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == ({}, True)


def test_opener_with_leading_whitespace_is_unparseable(tmp_path: Path) -> None:
    """`` ---`` (leading whitespace) is not a column-0 fence but starts with
    ``---`` after stripping: attempted, unbounded, refused. The pre-28.1
    reader refused it too (``text.startswith("---")`` was false and the
    body contained ``---``); a ``strip()``-based fence test would have
    widened it to parseable (review pass 1, ECH8)."""
    path = _write(
        tmp_path,
        "leading-space.md",
        " ---\ntitle: x\nstatus: draft\n---\n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == ({}, True)


def test_opener_with_trailing_comment_is_unparseable(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "comment-opener.md",
        "--- # not a fence\ntitle: x\n---\n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == ({}, True)


def test_four_dash_opener_is_unparseable(tmp_path: Path) -> None:
    """``----`` on line 1 starts with ``---`` but is not exactly the fence:
    attempted, unbounded, refused."""
    path = _write(tmp_path, "four-dashes.md", "----\ntitle: x\n---\n\nBody.\n")
    assert chain._frontmatter_parse(path) == ({}, True)


def test_opener_with_trailing_whitespace_is_still_a_fence(tmp_path: Path) -> None:
    """``rstrip`` tolerates trailing whitespace on a fence line -- an editor
    leaving ``---  `` is still a fence, on either side of the block."""
    path = _write(
        tmp_path,
        "trailing-space.md",
        "---  \ntitle: x\nstatus: draft\n--- \n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == ({"title": "x", "status": "draft"}, False)


# --- Banner skip (Story 50.5 convention, ported here) ------------------------


def test_banner_topped_spec_parses(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "banner.md",
        (
            "<!-- Promoted from implementation-artifacts/ to tracked specs "
            "on 2026-08-04 -->\n---\ntitle: x\nstatus: done\n---\n\nBody.\n"
        ),
    )
    assert chain._frontmatter_parse(path) == ({"title": "x", "status": "done"}, False)


def test_multiline_banner_topped_spec_parses(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "banner_multiline.md",
        "<!--\nRECOVERED\nmulti-line note\n-->\n---\ntitle: y\nstatus: done\n---\n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == ({"title": "y", "status": "done"}, False)


def test_banner_below_the_fence_is_unaffected_pr_1460_shape(tmp_path: Path) -> None:
    """The provenance banner placed BELOW the closing fence (the shape every
    tracked spec on ``main`` actually carries, post PR #1460) never starts
    with ``<!--`` at position 0, so ``_skip_leading_banner`` is a no-op and
    parsing proceeds exactly as before Story 28.1."""
    path = _write(
        tmp_path,
        "banner_below.md",
        (
            "---\ntitle: x\nstatus: done\n---\n\n"
            "<!-- Promoted from implementation-artifacts/ to tracked specs "
            "on 2026-08-04 -->\n\nBody.\n"
        ),
    )
    assert chain._frontmatter_parse(path) == ({"title": "x", "status": "done"}, False)


def test_unclosed_banner_is_not_treated_as_a_banner(tmp_path: Path) -> None:
    """An unclosed ``<!--`` is not a banner this parser recognizes -- the
    text is used as-is, which here means line 1 is ``<!-- never closed``:
    neither a fence nor an attempted opener, so absent metadata (matching
    marshal's own ``_skip_leading_banner`` Never clause: "do not treat an
    unclosed ``<!--`` as a banner")."""
    path = _write(
        tmp_path,
        "unclosed_banner.md",
        "<!-- never closed\n---\ntitle: z\nstatus: draft\n---\n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == ({}, False)


def test_bom_and_blank_line_before_the_banner_still_parses(tmp_path: Path) -> None:
    """Marshal Story 51.8 / ``spec-pyforge-marshal:CAP-256`` (closing
    DW-FU-50-6): the banner need not sit at literal text offset 0 -- a UTF-8
    BOM, blank lines or spaces before ``<!--`` are skipped along with it,
    so the frontmatter behind such a banner still parses."""
    path = _write(
        tmp_path,
        "bom_blank_banner.md",
        "\ufeff\n  <!-- Promoted from implementation-artifacts/ -->\n---\ntitle: x\nstatus: done\n---\n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == ({"title": "x", "status": "done"}, False)


def test_indented_fence_behind_a_banner_parses_by_marshal_parity(tmp_path: Path) -> None:
    """The documented consequence of the verbatim port: ``_skip_leading_
    banner``'s trailing ``.lstrip()`` strips indentation from the fence
    line, so the column-0 rule applies to the POST-banner text and a
    banner-topped file tolerates leading whitespace on its opening fence --
    while the same ``   ---`` with no banner stays refused
    (``test_opener_with_leading_whitespace_is_unparseable``). Pinned as a
    deliberate verdict, kept for parity with marshal's helper."""
    path = _write(
        tmp_path,
        "indented_fence_banner.md",
        "<!-- b -->\n   ---\ntitle: x\nstatus: done\n---\n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == ({"title": "x", "status": "done"}, False)


def test_skip_leading_banner_is_the_marshal_port() -> None:
    """The helper's branches, pinned directly against marshal's
    ``promotion.py`` body (Story 50.5 / CAP-248 + Story 51.8 / CAP-256): no
    banner -> ``text`` unchanged (even with leading whitespace); unclosed
    banner -> ``text`` unchanged; closed banner -> the remainder
    ``lstrip``-ed (so the fence lands on line 1 whether the banner's ``-->``
    is followed by one newline or several); BOM/blank/space before the
    banner -> skipped with it."""
    assert chain._skip_leading_banner("---\nx: 1\n---\n") == "---\nx: 1\n---\n"
    assert chain._skip_leading_banner("\n ---\nx: 1\n---\n") == "\n ---\nx: 1\n---\n"
    assert chain._skip_leading_banner("<!-- open\n---\nx: 1\n---\n") == "<!-- open\n---\nx: 1\n---\n"
    assert chain._skip_leading_banner("\ufeff<!-- open\n---\n") == "\ufeff<!-- open\n---\n"
    assert chain._skip_leading_banner("<!-- b -->\n\n\n---\nx: 1\n---\n") == "---\nx: 1\n---\n"
    assert chain._skip_leading_banner("<!--\nmulti\n-->---\nx: 1\n---\n") == "---\nx: 1\n---\n"
    assert chain._skip_leading_banner("\ufeff\n  <!-- b -->\n---\nx: 1\n---\n") == "---\nx: 1\n---\n"


# --- Pre-existing shapes this fix must not disturb ---------------------------


def test_empty_frontmatter_block_is_absent_not_unparseable(tmp_path: Path) -> None:
    path = _write(tmp_path, "empty_fm.md", "---\n---\n\nBody.\n")
    assert chain._frontmatter_parse(path) == ({}, False)


def test_non_mapping_frontmatter_is_unparseable(tmp_path: Path) -> None:
    path = _write(tmp_path, "list_fm.md", "---\n- a\n- b\n---\n\nBody.\n")
    assert chain._frontmatter_parse(path) == ({}, True)


def test_yaml_error_inside_the_block_is_unparseable(tmp_path: Path) -> None:
    path = _write(tmp_path, "bad_yaml.md", "---\ntitle: [unclosed\nstatus: x\n---\n\nBody.\n")
    assert chain._frontmatter_parse(path) == ({}, True)


def test_ordinary_frontmatter_parses_unchanged(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "ordinary.md",
        "---\nowner: doctor\nstatus: draft\ntitle: A Dream\n---\n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == (
        {"owner": "doctor", "status": "draft", "title": "A Dream"},
        False,
    )


def test_unreadable_path_is_unparseable(tmp_path: Path) -> None:
    """A path that cannot be read at all (never created here) degrades to
    the same refusal as malformed content -- pre-existing behavior, pinned
    so the read-failure branch is not accidentally narrowed by this fix."""
    path = tmp_path / "does-not-exist.md"
    assert chain._frontmatter_parse(path) == ({}, True)


# --- Body boundary: the same scan, from the other side -----------------------


def test_body_after_frontmatter_starts_at_the_line_anchored_closing_fence() -> None:
    """A ``---`` quoted inside a frontmatter scalar is not where the body
    starts -- the old ``split("---", 2)`` returned the frontmatter tail as
    body, which the Kinship scan then read (review pass 1, ECH4/VG2)."""
    text = '---\ntitle: x\nnote: "---"\nkin: [[not-a-link]]\n---\n\nBody [[real-link]].\n'
    assert chain._dream_body_after_frontmatter(text) == "\nBody [[real-link]].\n"


def test_body_after_frontmatter_skips_a_leading_banner() -> None:
    text = "<!-- banner -->\n---\ntitle: x\nkin: [[not-a-link]]\n---\nBody.\n"
    assert chain._dream_body_after_frontmatter(text) == "Body.\n"


def test_body_after_frontmatter_with_no_leading_fence_is_the_text_unchanged() -> None:
    text = "Prose first.\n---\ntitle: x\n---\nMore.\n"
    assert chain._dream_body_after_frontmatter(text) is text


def test_body_after_frontmatter_with_no_closing_fence_is_empty() -> None:
    assert chain._dream_body_after_frontmatter("---\ntitle: x\nnever closed\n") == ""


def test_body_after_frontmatter_with_an_unclosed_banner_is_the_text_unchanged() -> None:
    """An unclosed ``<!--`` is not a banner, so line 1 is not a fence and the
    text comes back unchanged -- the same no-frontmatter branch
    ``_frontmatter_parse`` reports as ``({}, False)`` for this shape."""
    text = "<!-- never closed\n---\ntitle: x\n---\nBody.\n"
    assert chain._dream_body_after_frontmatter(text) is text


def test_body_after_frontmatter_normalises_crlf_line_endings() -> None:
    """``splitlines()`` + ``"\\n".join``: CRLF input comes back with ``\\n``
    endings (documented as not load-bearing -- the caller only regexes
    ``[[...]]`` out of the result)."""
    text = "---\r\ntitle: x\r\n---\r\n\r\nBody [[a]].\r\n"
    assert chain._dream_body_after_frontmatter(text) == "\nBody [[a]].\n"


def test_body_after_frontmatter_preserves_the_trailing_newline_state() -> None:
    assert chain._dream_body_after_frontmatter("---\nt: 1\n---\nBody") == "Body"
    assert chain._dream_body_after_frontmatter("---\nt: 1\n---\n") == "\n"
    assert chain._dream_body_after_frontmatter("---\nt: 1\n---") == ""
