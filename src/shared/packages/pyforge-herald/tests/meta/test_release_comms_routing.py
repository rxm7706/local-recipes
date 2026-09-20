"""Story 18.2: herald's own AD-2 routing-note gate for release comms.

`bmad-agent-herald/SKILL.md`'s "Utility skill routing (AD-2)" section used to
be a bare one-line "wields" mention (added incidentally by steward 46.2 to
satisfy its own generic AD-2 meta-test). This module machine-checks the
concrete, numbered release-comms procedure that replaced it -- CAP-3's own
routing-note contract -- including the AD-10 "check against the producer's
live artifact" this story's acceptance criteria require.

Kept herald-local (`pyforge-herald-test` alone proves this story's AC)
rather than folded into `pyforge-steward`'s
`test_adoption_register.py::test_skill_routing_matches_ad2_for_every_currently_provisioned_row`,
which already proves AD-2 generically for these two skills off the (now
expanded) routing note -- this module adds herald-specific procedure + AD-10
assertions without duplicating that generic check.

Deliberately documentation-only: this story lands as a routing-note change
per `spec-bmad-suite-lifecycle`'s CAP-3 Success criteria (routing table +
persona citation + meta-test -- no live-fire requirement) and AD-2 ("routing
lives with the wielder, in one durable home"). No test here drafts a real
changelog/social post or files a real `herald notice`/`success` record --
that would require an actual bmad-suite refresh to draft comms for, which is
out of this story's scope.
"""

from __future__ import annotations

import re
from pathlib import Path

PERSONA_SKILL_MD = ".claude/skills/bmad-agent-herald/SKILL.md"
PRODUCER_SKILL_DIRS = (
    ".claude/skills/bmad-os-changelog",
    ".claude/skills/bmad-os-changelog-social",
)
REGISTER_RELATIVE = (
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md"
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _persona_text(root: Path) -> str:
    return (root / PERSONA_SKILL_MD).read_text(encoding="utf-8")


def _routing_section(text: str) -> str:
    pattern = r"(?ms)^## Utility skill routing \(AD-2\)\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    if not match:
        raise AssertionError("persona SKILL.md has no 'Utility skill routing (AD-2)' section")
    return match.group(1)


# ── (a) AD-10 producer check: both routed-to skills are live on disk ────────


def test_producer_skills_are_live_on_disk():
    """A future regression here (one producer skill removed) must fail the
    suite loudly, naming the exact missing path -- the I/O & Edge-Case
    Matrix's second row."""
    root = _repo_root()
    missing = [d for d in PRODUCER_SKILL_DIRS if not (root / d / "SKILL.md").is_file()]
    assert not missing, f"producer skill(s) missing from disk (AD-10): {missing}"


def test_producer_check_would_fail_and_name_a_missing_producer_dir(tmp_path):
    """Synthetic proof of the I/O & Edge-Case Matrix's second row: today's
    live tree has both producer skills present, so the missing-dir branch is
    exercised here against a fixture root instead.

    Builds every dir but the last one, so this stays correct (rather than
    raising an unpack error) if `PRODUCER_SKILL_DIRS` ever grows past two
    entries.
    """
    assert len(PRODUCER_SKILL_DIRS) >= 2, "need at least one present + one absent dir"
    fake_root = tmp_path
    *present_dirs, absent_dir = PRODUCER_SKILL_DIRS
    for present_dir in present_dirs:
        (fake_root / present_dir).mkdir(parents=True)
        (fake_root / present_dir / "SKILL.md").write_text("stub", encoding="utf-8")
    # absent_dir is deliberately never created.

    missing = [d for d in PRODUCER_SKILL_DIRS if not (fake_root / d / "SKILL.md").is_file()]
    assert missing == [absent_dir]


# ── (b) + (c): the routing section is a concrete, followable procedure ──────


def test_routing_section_names_both_producer_skills_and_the_filing_grammar():
    root = _repo_root()
    section = _routing_section(_persona_text(root))
    required_tokens = (
        "bmad-os-changelog",
        "bmad-os-changelog-social",
        "herald notice",
        "herald success",
        "AD-10",
    )
    missing = [token for token in required_tokens if token not in section]
    assert not missing, f"routing section missing required mention(s): {missing}"


def test_routing_section_names_both_producer_skill_directories_literally():
    root = _repo_root()
    section = _routing_section(_persona_text(root))
    missing = [d for d in PRODUCER_SKILL_DIRS if f"{d}/" not in section]
    assert not missing, f"routing section does not literally name: {missing}"


def test_routing_section_is_a_numbered_procedure_not_a_bare_mention():
    """Guards against a regression back to the old bare "wields" one-liner."""
    root = _repo_root()
    section = _routing_section(_persona_text(root))
    numbered_steps = re.findall(r"^\s*\d+\.\s", section, flags=re.MULTILINE)
    assert len(numbered_steps) >= 4, (
        f"routing section is not a numbered procedure (found {len(numbered_steps)} numbered lines)"
    )


# ── (d) adoption-register.md's combined row is untouched (read-only ref) ────


def test_adoption_register_combined_row_still_names_herald():
    root = _repo_root()
    text = (root / REGISTER_RELATIVE).read_text(encoding="utf-8")
    match = re.search(
        r"^\|\s*`bmad-os-changelog`,\s*`bmad-os-changelog-social`\s*\|.*$",
        text,
        flags=re.MULTILINE,
    )
    assert match, "adoption-register.md's combined changelog/social row not found"
    assert "herald" in match.group(0), "combined changelog/social row no longer names herald as wielder"


# ── (e) CLAUDE.md stays silent on both producer skills (AD-2) ───────────────


def test_claude_md_never_mentions_bmad_os_changelog():
    root = _repo_root()
    text = (root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "bmad-os-changelog" not in text, "CLAUDE.md must never route bmad-os-changelog (AD-2)"
