"""Story 18.3: `slides-generator` is herald-wielded (AD-2 routing note).

`bmad-labs-skills`' `slides-generator` skill was provisioned onto disk by
steward Story 46.5 (`.claude/skills/slides-generator/`), and
adoption-register.md § 2 row 44 already names herald as its sole wielding
station -- but `bmad-agent-herald/SKILL.md` carried no routing note for it
until this story. This module proves the routing note exists, states the
CAP-6 boundary concretely (draft only; never a deck head; the Claude-Design
-> Vite pipeline stays the deck source of record -- not a bare "wields"
mention), that CLAUDE.md still never mentions the skill (AD-2), and that
steward's own `_ROUTING_STORY_NOT_YET_LANDED` carve-out no longer lists this
row now that the mention exists (the carve-out dict's own comment requires
its removal the same day).

Self-contained (Design Notes): Story 18.2 lives on a sibling branch
(`herald-r2a`) not present in this worktree's history, so this module does
not assume `test_release_comms_routing.py` exists -- it only mirrors that
precedent's general shape: producer-on-disk check + synthetic
missing-producer proof, routing-section token check, boundary-language
check, CLAUDE.md silence check.

Deliberately NOT checked here: AD-2 exclusivity (that no OTHER station's
persona also mentions `slides-generator`). Steward's own
`test_skill_routing_matches_ad2_for_every_currently_provisioned_row`
already exercises that half unconditionally for every § 2 row, this one
included, so re-checking it here would be redundant, not defense in depth.
"""

from __future__ import annotations

import re
from pathlib import Path

SKILL_NAME = "slides-generator"
PERSONA_SKILL = "bmad-agent-herald"
DECK_PIPELINE_SPEC = "docs/specs/presentation-deck.md"
STEWARD_ROUTING_TEST = "src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _producer_skill_md(root: Path) -> Path:
    return root / ".claude" / "skills" / SKILL_NAME / "SKILL.md"


def _assert_producer_on_disk(root: Path) -> None:
    """AD-10-style producer check: the labs skill this story routes must
    actually be provisioned on disk (Story 46.5). Names the missing path
    explicitly -- never a bare boolean."""
    path = _producer_skill_md(root)
    if not path.is_file():
        raise AssertionError(f"producer skill missing: {path}")


def _persona_skill_md(root: Path) -> Path:
    return root / ".claude" / "skills" / PERSONA_SKILL / "SKILL.md"


def _routing_section(text: str) -> str:
    """Body of the '## Utility skill routing (AD-2)' section. The heading is
    kept stable per this story's own Code Map (a sibling branch's test also
    anchors on it)."""
    pattern = r"(?ms)^## Utility skill routing \(AD-2\)\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    if not match:
        raise AssertionError("'## Utility skill routing (AD-2)' section not found")
    return match.group(1)


# ── producer-on-disk (+ synthetic missing-producer proof) ───────────────────


def test_slides_generator_producer_is_on_disk():
    root = _repo_root()
    _assert_producer_on_disk(root)


def test_missing_producer_is_reported_explicitly(tmp_path):
    fake_root = tmp_path
    try:
        _assert_producer_on_disk(fake_root)
    except AssertionError as exc:
        message = str(exc)
        assert "producer skill missing" in message
        assert SKILL_NAME in message
        return
    raise AssertionError("a missing producer skill was not reported")


# ── routing-note presence + boundary language (this story's headline AC) ────


def test_herald_persona_names_slides_generator_in_the_routing_section():
    root = _repo_root()
    text = _persona_skill_md(root).read_text(encoding="utf-8")
    section = _routing_section(text)
    assert SKILL_NAME in section, f"{PERSONA_SKILL}/SKILL.md's AD-2 routing section does not name {SKILL_NAME!r}"


def test_boundary_language_is_concrete_not_a_bare_wields_mention():
    """Acceptance: 'draft only; never a deck head; the Claude-Design pipeline
    stays the deck source of record' -- a concrete, checkable boundary
    statement, not a bare 'wields' mention."""
    root = _repo_root()
    text = _persona_skill_md(root).read_text(encoding="utf-8")
    section = _routing_section(text)

    assert SKILL_NAME in section
    assert re.search(r"(?i)quick draft", section), "missing 'quick draft' framing"
    assert re.search(r"(?i)never\b[^.]*\bdeck head", section), "missing the 'never a deck head' boundary"
    assert DECK_PIPELINE_SPEC in section, f"missing a pointer to {DECK_PIPELINE_SPEC}"
    assert re.search(r"(?i)deck source of record", section), "missing the 'deck source of record' framing"


def test_claude_md_never_mentions_slides_generator():
    root = _repo_root()
    claude_md = (root / "CLAUDE.md").read_text(encoding="utf-8")
    assert SKILL_NAME not in claude_md, "CLAUDE.md must never route slides-generator (AD-2)"


# ── steward carve-out removal (I/O & Edge-Case Matrix) ───────────────────────


def test_steward_carve_out_no_longer_lists_slides_generator():
    """If steward's `_ROUTING_STORY_NOT_YET_LANDED` dict still carved
    `slides-generator` out once this story lands the persona mention,
    steward's own AD-2 meta-test would silently skip the positive assertion
    for this row -- this story's own test must fail instead of relying on
    that silent skip."""
    root = _repo_root()
    path = root / STEWARD_ROUTING_TEST
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?s)_ROUTING_STORY_NOT_YET_LANDED\s*=\s*\{(.*?)\n\}", text)
    assert match, f"could not locate _ROUTING_STORY_NOT_YET_LANDED dict in {path}"
    body = match.group(1)
    assert SKILL_NAME not in body, (
        "steward's _ROUTING_STORY_NOT_YET_LANDED still carves out "
        f"{SKILL_NAME!r} after herald 18.3 landed the persona mention -- "
        f"remove the entry now that {PERSONA_SKILL}/SKILL.md names it"
    )
