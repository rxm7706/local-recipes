"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_chain_deferred_work.py``.

These four tests read this repository's own deferred-work ledgers (the
tracked ``deferred-work-ledger.md`` files and marshal's Tier-3
``deferred-work.md``), so they run in the station's live-tree half. Every
other ``gather_deferred_work`` test builds its own tree and stays in
``test_sources_chain_deferred_work.py`` (the package half).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_sources_chain_deferred_work import _uncited

from pyforge.doctor.sources import chain

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    """This repository's root, resolved when a test runs (never at import time)."""
    root = Path(__file__).resolve().parents[6]
    assert (root / ".claude").is_dir(), f"{root} is not the local-recipes checkout root (no .claude/)"
    return root


def test_live_marshal_file_all_nine_identified_plain_headers_do_not_swallow() -> None:
    """Story 8.1's own AC: "the bullet at line 54 (and the analogous bullet
    after each of DW-2/3/4/5/6/7/8/9) classifies as LEGACY_FLAT with
    id=None, never as owned by the preceding IDENTIFIED_PLAIN header."
    Verified here against the REAL, live
    ``_bmad-output/projects/pyforge-marshal/implementation-artifacts/
    deferred-work.md`` (not a copied fixture) -- keyed by id rather than by
    line number so it stays correct as the file grows (append-only
    discipline, this module's own Design Notes). Skips when that gitignored
    Tier-3 file is absent: it is local state, so a fresh clone (CI) or a
    bmad-loop worktree teardown has none to read."""
    marshal_path = (
        _repo_root() / "_bmad-output" / "projects" / "pyforge-marshal" / "implementation-artifacts" / "deferred-work.md"
    )
    if not marshal_path.is_file():
        pytest.skip(
            "pyforge-marshal's Tier-3 deferred-work.md is gitignored local state "
            "(a fresh clone or a worktree teardown has none)"
        )

    entries = sorted(chain.classify_tier3_entries(marshal_path), key=lambda e: e.start_line)
    plain_ids = {f"DW-{n}" for n in range(1, 10)}
    found = {e.id for e in entries if e.shape is chain.Tier3Shape.IDENTIFIED_PLAIN and e.id in plain_ids}
    assert found == plain_ids, f"expected all of DW-1..DW-9 present as identified-plain headers, got {sorted(found)}"

    for idx, entry in enumerate(entries):
        if entry.shape is not chain.Tier3Shape.IDENTIFIED_PLAIN or entry.id not in plain_ids:
            continue
        if idx + 1 >= len(entries):
            pytest.fail(
                f"{entry.id} is the LAST entry in the file -- no following entry to "
                "check it did not swallow (the ledger's own append-only shape changed "
                "under this test; re-derive the expectation rather than IndexError)"
            )
        following = entries[idx + 1]
        assert following.shape in (chain.Tier3Shape.LEGACY_FLAT, chain.Tier3Shape.LEGACY_HEADER), (
            f"{entry.id}'s following entry was not a legacy shape: {following}"
        )
        assert following.id is None, f"{entry.id} swallowed the following entry (id={following.id!r}): {following}"


def test_continuation_join_does_not_split_on_a_bare_indented_word_colon_real_excerpts() -> None:
    """Story 8.1 review pass (2026-08-15), HIGH finding 1: the pre-fix
    ``_CONT_KEY_RE`` treated ANY indented ``word:``-shaped line as a new
    field start, not just a real known field key -- silently truncating
    ``summary``/``evidence`` and misattributing the remainder to a spurious
    key. Reproduced live in 5 real tracked-ledger entries across 3 projects
    -- read directly from the real files (not hand-transcribed, per the
    review's own instruction) so this stays byte-accurate as those ledgers
    grow:

    - atlas ``DW-AD23-2``: ``summary`` wraps through "Not fixed\\n    here:
      the `run_result` signature is E2-owned..." -- the pre-fix code split
      there, leaving ``summary`` truncated and a spurious ``here`` key
      holding the rest through ``resolution:``'s own real key line.
    - herald ``DW-13-6-1``: ``evidence`` wraps through "Not pursued in this
      story: making `deploy perimeter`..." -- same corruption, spurious
      ``story`` key.
    - herald ``DW-14-3-1``: ``evidence`` wraps through "against the real
      extractor: `extract-slides.mjs`'s `slugify..." -- same corruption,
      spurious ``extractor`` key.

    All three must now read back with the false split-text INSIDE the real
    field (not truncated, not a spurious key), and doctor's own
    ``DW-CHAIN-COMPLETENESS-1`` / atlas's ``DW-AD23-3`` (both cited by the
    review as confirmation cases, though neither happens to contain a false
    split) must still read back their real fields intact -- proving the fix
    is not a regression for the common (single-physical-line) case either.
    """
    repo_root = _repo_root()

    def _entry(project: str, id_needle: str) -> chain.LegacyEntry:
        path = repo_root / "_bmad-output" / "projects" / project / "planning-artifacts" / "deferred-work-ledger.md"
        assert path.is_file(), f"{project}'s tracked deferred-work-ledger.md is missing"
        for e in chain.classify_tier3_entries(path):
            if e.id and id_needle in e.id:
                return e
        pytest.fail(f"{id_needle} not found in {path}")
        raise AssertionError("unreachable")  # for the type checker

    ad23_2 = _entry("pyforge-atlas", "AD23-2")
    assert ad23_2.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert "here" not in ad23_2.fields
    assert ("here: the `run_result` signature is E2-owned and touches 10 positional call sites") in ad23_2.fields[
        "summary"
    ]
    assert ad23_2.fields["summary"].endswith("kedro fires `on_pipeline_error` in-process there.")
    assert ad23_2.fields["resolution"].endswith(
        "replacing two undeclared process-lifetime couplings with one explicit lifetime."
    )

    herald_13_6_1 = _entry("pyforge-herald", "13-6-1")
    assert herald_13_6_1.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert "story" not in herald_13_6_1.fields
    assert ("story: making `deploy perimeter` support an arbitrary ASGI target") in herald_13_6_1.fields["evidence"]
    assert herald_13_6_1.fields["evidence"].endswith("before Herald's webhook is ever pointed at it for real.")

    herald_14_3_1 = _entry("pyforge-herald", "14-3-1")
    assert herald_14_3_1.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert "extractor" not in herald_14_3_1.fields
    assert ("extractor: `extract-slides.mjs`'s `slugify(label, i)`") in herald_14_3_1.fields["evidence"]

    chain_completeness = _entry("pyforge-doctor", "CHAIN-COMPLETENESS-1")
    assert chain_completeness.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert chain_completeness.fields["evidence"].endswith("the detector's blind spot easy to keep not noticing.")
    assert "raised" in chain_completeness.fields

    ad23_3 = _entry("pyforge-atlas", "AD23-3")
    assert ad23_3.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert ad23_3.fields["summary"].endswith("this one is the sole CORRECTNESS exposure among them.")


def test_identified_header_field_search_skips_interposed_html_comment_real_marshal_excerpts() -> None:
    """Story 8.1 review pass (2026-08-15), HIGH finding 2: the pre-fix
    ``_consume_identified_entry`` gave up after the first non-blank line
    beneath a ``### DW-<id>:`` header, so a header separated from its own
    ``- source_spec:`` bullet by an interposed ``<!-- id assigned ... -->``
    HTML comment (a real, live convention from the 2026-07-30 verification
    campaign) read as an EMPTY header plus a spurious, unrelated
    ``LEGACY_FLAT`` orphan for its own real content. Reproduced live in
    marshal's tracked ledger at ``## DW-1-2-1`` and ``## DW-1-10-7`` -- read
    directly from the real file (not hand-transcribed)."""
    path = (
        _repo_root()
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "planning-artifacts"
        / "deferred-work-ledger.md"
    )
    assert path.is_file(), "pyforge-marshal's tracked deferred-work-ledger.md is missing"

    entries = sorted(chain.classify_tier3_entries(path), key=lambda e: e.start_line)
    by_id = {e.id: e for e in entries if e.id}

    for entry_id, summary_needle in (
        ("DW-1-2-1", "AD-23 rule text still literally says the canonical story key"),
        ("DW-1-10-7", "No project-policy source anywhere in the repo currently supplies"),
    ):
        assert entry_id in by_id, f"{entry_id} missing entirely from {path}"
        entry = by_id[entry_id]
        assert entry.shape is chain.Tier3Shape.IDENTIFIED_BULLETED, (
            f"{entry_id} misclassified as {entry.shape} -- the interposed HTML "
            "comment defeated the header's own field search"
        )
        assert summary_needle in entry.fields.get("summary", ""), (
            f"{entry_id}'s real content was not captured: {entry.fields}"
        )
        assert "evidence" in entry.fields

        duplicate_orphans = [
            other
            for other in entries
            if other.shape is chain.Tier3Shape.LEGACY_FLAT
            and other.fields.get("source_spec") == entry.fields.get("source_spec")
        ]
        assert not duplicate_orphans, (
            f"{entry_id}'s own real content also leaked out as a spurious orphan entry: {duplicate_orphans}"
        )


def test_the_live_tracked_ledgers_carry_no_uncited_post_cutoff_verified_line() -> None:
    """The AC "given ``main``, ``deferred-work-check`` exits 0", for this
    check: the cutoff is chosen so no committed ledger line is rewritten."""
    repo_root = _repo_root()
    assert (repo_root / "_bmad-output" / "projects").is_dir(), "the _bmad-output/projects tree is missing"

    uncited = _uncited(chain.gather_deferred_work(repo_root))

    assert not uncited, [(f.evidence["project"], f.evidence["id"]) for f in uncited]
