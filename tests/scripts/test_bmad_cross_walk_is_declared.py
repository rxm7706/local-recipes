"""The BMAD↔Lexicon cross-walk and `pitched`'s optionality are pinned against
``docs/dreams/pyforge-charter.md`` and ``docs/governance/guild-roster.json``
(steward Story 59.3, ``spec-vocabulary-one-name-one-job`` CAP-3).

Hub has a Charter cross-walk (``### Intelligence Hub vocabulary``); BMAD's own
daily nouns -- Epic, Story, Sprint, PRD, Retrospective -- did not, leaving a
dangling forward-reference in ``### The Spec ladder`` ("the full cross-walk
... is CAP-3, not restated here"). This test pins the new
``### BMAD vocabulary`` subsection's shape, its three named divergences, and
the companion ``guild-roster.json`` declaration that ``pitched`` stays
optional and is never backfilled -- so a future edit that drops a term, loses
a divergence, or re-collapses ``optional``/``pitched`` into a false "shared
spelling" claim fails here rather than silently drifting. Pure stdlib
(``json`` + ``pathlib``, no ``pyforge.*`` import), mirroring
``test_spec_ladder_is_declared.py``'s shape exactly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROSTER = REPO / "docs" / "governance" / "guild-roster.json"
CHARTER = REPO / "docs" / "dreams" / "pyforge-charter.md"

# The five-row byte-identical baseline `dream_statuses` must never drift
# while this story only touches its `$comment_dream_statuses` prose.
_PRE_STORY_DREAM_STATUSES = ["dreamt", "pitched", "specified", "realized", "archived"]

_BMAD_HEADING = "### BMAD vocabulary — cross-walk, never a shared noun"
_BMAD_TERMS = ("Epic", "Story", "Sprint", "PRD", "Retrospective")


def _load_roster() -> dict:
    return json.loads(ROSTER.read_text(encoding="utf-8"))


def _charter_text() -> str:
    return CHARTER.read_text(encoding="utf-8")


def _bmad_subsection() -> str:
    """The new subsection's text, from its heading up to the next `### `
    heading (`### Gate has three senses`), so term/divergence checks are
    scoped to the new content rather than matching anywhere in the file.
    Whitespace (including hard line-wraps) is collapsed to single spaces so
    a substring check does not depend on exactly where prose wraps."""
    text = _charter_text()
    start = text.index(_BMAD_HEADING)
    rest = text[start + len(_BMAD_HEADING) :]
    end = rest.index("\n### ")
    raw = _BMAD_HEADING + rest[:end]
    return re.sub(r"\s+", " ", raw)


def test_the_bmad_vocabulary_subsection_exists():
    """Every assertion below reads this heading. If it is renamed or
    removed without updating this test, the cross-walk stops being
    declared anywhere."""
    assert _BMAD_HEADING in _charter_text(), (
        f"{CHARTER.relative_to(REPO)} no longer carries the BMAD cross-walk "
        "subsection this test pins."
    )


def test_the_subsection_sits_between_the_hub_walk_and_gate_senses():
    """Same placement Story 59.3's Code Map requires: immediately after the
    Intelligence Hub cross-walk, before `### Gate has three senses`."""
    text = _charter_text()
    hub_idx = text.index("### Intelligence Hub vocabulary")
    bmad_idx = text.index(_BMAD_HEADING)
    gate_idx = text.index("### Gate has three senses")
    assert hub_idx < bmad_idx < gate_idx


def test_all_five_bmad_terms_are_mapped():
    """Epic / Story / Sprint / PRD / Retrospective are each mapped to a
    Lexicon/estate surface inside the new subsection's table."""
    section = _bmad_subsection()
    for term in _BMAD_TERMS:
        assert f"| {term} |" in section, (
            f"BMAD vocabulary subsection has no table row mapping `{term}`"
        )


def test_spec_is_explained_not_silently_omitted():
    """`Spec` deliberately has no row and no reverse-walk entry -- the
    reason must be stated, not left for a reader to infer."""
    section = _bmad_subsection()
    assert "`Spec` deliberately has no row" in section
    assert "nothing to cross-walk" in section
    assert "`Spec` is the deliberate exception" in section


def test_the_three_divergences_are_named_without_the_false_spelling_claim():
    """Divergence 1: Spec `shipped` != story `done` != Dream `realized`.
    Divergence 2: ledger `blocked` is Guild-only. Divergence 3: BMAD's
    `optional` is a correctly-reused term, unrelated to (never fused with)
    a Dream sitting at `pitched` -- and must NOT claim the two share a
    spelling (review pass 1's bad_spec finding)."""
    section = _bmad_subsection()
    assert "Spec `shipped` ≠ story `done` ≠ Dream `realized`" in section
    assert "Ledger `blocked` is Guild-only" in section
    assert "BMAD's `optional` is a correctly-reused term, not an invented one" in section
    assert "share no spelling and nothing else" in section
    assert "share an English spelling" not in section
    assert "share a spelling" not in section


def test_the_reverse_walk_names_the_untouched_lexicon_nouns():
    section = _bmad_subsection()
    assert "Reverse walk — Lexicon nouns with no BMAD counterpart" in section


def test_the_spec_ladder_forward_reference_now_resolves():
    """`### The Spec ladder`'s CAP-3 forward-reference (2026-09-18) is no
    longer dangling now that the cross-walk exists."""
    text = _charter_text()
    assert "spec-vocabulary-one-name-one-job` CAP-3" in text
    # The forward-reference and the new subsection both exist in the same
    # file -- the dangling pointer now has real content to resolve to.
    assert _BMAD_HEADING in text


def test_the_realization_log_records_this_amendment():
    text = _charter_text()
    assert "2026-09-24 (amendment)" in text
    assert "spec-vocabulary-one-name-one-job` CAP-3 (Story 59.3)" in text


def test_guild_roster_declares_pitched_optional_and_unbackfilled():
    """`guild-roster.json`'s `$comment_dream_statuses` is `pitched`'s
    machine-readable declaration's companion prose (Ruling 6)."""
    data = _load_roster()
    comment = " ".join(data["$comment_dream_statuses"])
    assert "pitched" in comment
    assert "never required" in comment.lower()
    assert "never backfilled" in comment.lower()
    assert "Herald" in comment
    assert "`draft`" in comment


def test_guild_roster_pitched_prose_cites_the_ruling_source_by_full_path():
    """Review pass 1's citation-style finding: cite
    `docs/dreams/vocabulary-one-name-one-job.md` by full path, never the
    bare slug `vocabulary-one-name-one-job` with no path or extension."""
    data = _load_roster()
    comment = " ".join(data["$comment_dream_statuses"])
    assert "docs/dreams/vocabulary-one-name-one-job.md" in comment


def test_guild_roster_pitched_prose_does_not_claim_a_spelling_collision():
    data = _load_roster()
    comment = " ".join(data["$comment_dream_statuses"])
    assert "separate, unrelated fact" in comment
    assert "collision" not in comment.lower()


def test_dream_statuses_array_is_byte_identical_to_its_pre_story_value():
    """Regression guard: this story extends `$comment_dream_statuses`
    prose only. `dream_statuses` itself must not move."""
    data = _load_roster()
    assert data["dream_statuses"] == _PRE_STORY_DREAM_STATUSES
