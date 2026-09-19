"""Unit tests for ``pyforge.doctor.sources.chain._frontmatter_parse`` and its
``_skip_leading_banner`` helper (Story 28.1 / CAP-81).

Covers every row of the spec's I/O & Edge-Case Matrix directly against the
parser, independent of any particular caller (``_collect_dreams``,
``parse_spec_frontmatter_deferrals``, etc. each have their own fixture
coverage in sibling test files; this file pins the shared primitive itself).

The central regression is exercised in ``test_sources_chain_deferred_work.py``
against the REAL marshal Story 50.5 tracked spec (the file that first
surfaced the bug): reverting ``_frontmatter_parse`` to the old
``text.split("---", 2)`` implementation was verified, during development, to
make that fixture test fail (the mid-scalar ``"---"`` in the first
deferral's ``evidence:`` truncates the YAML block, losing the second
deferral entirely and the first deferral's ``location:``). That verification
is not re-encoded as a second, parallel "old implementation" here -- see the
story spec's own Tasks & Acceptance for the requirement -- but the fixture
test's own precision (exact deferral count, exact fingerprints) is what
would catch a regression to the old behavior.
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
    """The exact defect class Story 28.1 fixes, in miniature: a YAML scalar
    quoting the literal text ``"---"`` must not be mistaken for the closing
    fence. The old ``text.split("---", 2)`` truncated here; the fix must
    read through to the REAL closing fence on its own line."""
    path = _write(
        tmp_path,
        "quoted-dashes.md",
        (
            "---\n"
            "title: canary\n"
            'note: >-\n'
            '  the gate still checks lines[0] == "---" with no banner-skip\n'
            "status: draft\n"
            "---\n\nbody\n"
        ),
    )
    fields, unparseable = chain._frontmatter_parse(path)
    assert unparseable is False
    assert fields.get("status") == "draft"
    assert fields.get("title") == "canary"


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
    text is used as-is, which here means it never starts with ``---``
    (matching marshal's own ``_skip_leading_banner`` Never clause: "do not
    treat an unclosed ``<!--`` as a banner")."""
    path = _write(
        tmp_path,
        "unclosed_banner.md",
        "<!-- never closed\n---\ntitle: z\nstatus: draft\n---\n\nBody.\n",
    )
    assert chain._frontmatter_parse(path) == ({}, False)


# --- Pre-existing shapes this fix must not disturb ---------------------------


def test_empty_frontmatter_block_is_absent_not_unparseable(tmp_path: Path) -> None:
    path = _write(tmp_path, "empty_fm.md", "---\n---\n\nBody.\n")
    assert chain._frontmatter_parse(path) == ({}, False)


def test_non_mapping_frontmatter_is_unparseable(tmp_path: Path) -> None:
    path = _write(tmp_path, "list_fm.md", "---\n- a\n- b\n---\n\nBody.\n")
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
