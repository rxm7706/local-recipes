"""Story 32.1 / spec-pyforge-scribe CAP-27 (amended 2026-11-10) -- the block states the writer lock and the seed.

Ruling 1 of 2026-11-10 (docs/dreams/pyforge-unifying-strategy.md, Realization log) says A writes every
Dream, Frame, Spec and capability-ledger row until `pyforge.cutover_root` flips, B reads A at a pinned
SHA, the seed is Dream plus memlog (the second addendum, item 7: `archive/**/.memlog.md` included, no
backfill) and a Frame is a pointer. AGENTS.md's bmad:context block stated the reverse until scribe
Story 32.1 refreshed it. This guard reads the block and names each required clause that is missing
and each superseded clause that came back, so the wording cannot drift back unseen.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# This module reads AGENTS.md at the repository root, outside the package, so it runs in the station's
# live-tree half and fires on what it reads.
pytestmark = pytest.mark.live_tree

BLOCK_START = "<!-- bmad:context -->"
BLOCK_END = "<!-- /bmad:context -->"

#: Clause name -> the phrases the block must carry for that clause (every phrase, whitespace collapsed).
REQUIRED_CLAUSES: dict[str, tuple[str, ...]] = {
    "A writes until the flip": (
        "A writes every Dream, Frame, Spec and capability-ledger row until `pyforge.cutover_root` flips",
    ),
    "B reads A at a pinned SHA": ("reads A at a pinned SHA",),
    "the seed is Dream plus memlog, archived memlogs included": ("Dream plus memlog", "`archive/**/.memlog.md`"),
    "a Frame is a pointer": ("a Frame is a pointer",),
    "the mode table is the capability ledger": ("the mode table, `docs/foundry/capability-ledger.yaml`",),
}

#: Clause name -> the pattern of a superseded sentence the block must no longer carry.
SUPERSEDED_CLAUSES: dict[str, re.Pattern[str]] = {
    "the seed as Frame + Spec": re.compile(r"Frame \+ Spec"),
    "the writer lock given to B": re.compile(r"\bare B[’']s\b"),
    "A pins B's SHA": re.compile(r"\bA pins B[’']s SHA"),
    "the mode table given to B": re.compile(r"\b[Tt]he (?:mode )?table is B[’']s"),
}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _agents_md() -> str:
    return (_repo_root() / "AGENTS.md").read_text(encoding="utf-8")


def _managed_block(text: str) -> str:
    """The text between the bmad:context markers, whitespace collapsed so a wrapped line still matches."""
    start = text.index(BLOCK_START)
    end = text.index(BLOCK_END)
    return " ".join(text[start:end].split())


def _cutover_wording_breaks(agents_text: str) -> list[str]:
    block = _managed_block(agents_text)
    breaks = [
        f"the block lacks the required clause: {name}"
        for name, phrases in REQUIRED_CLAUSES.items()
        if not all(phrase in block for phrase in phrases)
    ]
    breaks += [
        f"the block carries the superseded clause: {name}"
        for name, pattern in SUPERSEDED_CLAUSES.items()
        if pattern.search(block)
    ]
    return breaks


def test_the_block_states_the_ruled_writer_seed_and_mode_table() -> None:
    breaks = _cutover_wording_breaks(_agents_md())
    assert not breaks, (
        "AGENTS.md's bmad:context block disagrees with ruling 1 of 2026-11-10; refresh it with "
        "bmad-project-context, never by hand:\n  " + "\n  ".join(breaks)
    )


def _drop(phrase: str):
    return lambda text: text.replace(phrase, "")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


#: One mutation per required phrase: the phrase leaves a copy of the live file.
_REMOVALS = [
    pytest.param(_drop(phrase), name, id=f"drops-{_slug(phrase)}")
    for name, phrases in REQUIRED_CLAUSES.items()
    for phrase in phrases
]

#: One mutation per superseded clause: the sentence the 2026-11-10 refresh replaced comes back into the block.
_PLANTS = [
    pytest.param(
        lambda text, s=sentence: text.replace(BLOCK_END, f"- {s}\n{BLOCK_END}"),
        name,
        id=f"plants-{_slug(name)}",
    )
    for name, sentence in (
        ("the seed as Frame + Spec", "B is the lasting root, its engines rebuilt from Frame + Spec."),
        (
            "the writer lock given to B",
            "Write each artifact on the root that owns it (the writer lock): foundry-product Dreams, "
            "Frames, Spec five-fields and kernel package commits are B's.",
        ),
        ("A pins B's SHA", "A pins B's SHA and invents the factory, CFE and recipes."),
        ("the mode table given to B", "The table is B's docs/foundry/modes.md."),
    )
]


@pytest.mark.parametrize(("mutate", "clause"), _REMOVALS + _PLANTS)
def test_cutover_wording_guard_names_each_broken_clause(mutate, clause: str) -> None:
    """Break one clause on a copy of the live file; exactly that clause is reported."""
    live = _agents_md()
    mutated = mutate(live)
    assert mutated != live, "the mutation did not change its input; the planted or dropped text drifted"
    breaks = _cutover_wording_breaks(mutated)
    assert len(breaks) == 1 and clause in breaks[0], breaks


def test_cutover_wording_guard_reads_only_between_the_markers() -> None:
    """A superseded sentence quoted outside the block (as the notes file does) is not the block's text."""
    live = _agents_md()
    quoted = live + "\nThe 2026-11-01 block said B's engines were rebuilt from Frame + Spec.\n"
    assert _cutover_wording_breaks(quoted) == []
