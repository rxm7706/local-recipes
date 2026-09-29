"""The fold PR's re-key map -- one shape, one parser (doctor Story 25.3).

``spec-one-chain-per-station`` CAP-3(g): a station fold is a *rebase* -- every
epic, story and ledger key renumbers sequentially -- and the fold PR ships
``planning-artifacts/rekey-<date>.md`` so a ``done`` row moves as ``done``,
never as drop-plus-add. This module is the single reader of that file, shared
by ``sources/ledger.py`` (regression verdict), ``sources/marshal.py`` (landing
evidence for a renumbered story) and ``scripts/promote_sprint_status.py``
(``--rekey``). Three readers, one grammar, so the grammar cannot fork.

The grammar is deliberately tiny (CHAIN-STANDARD § 7 item 1):

    # comments and blank lines are ignored
    old-ledger-key -> new-ledger-key

Anything else is a *malformed* line, reported by position and never guessed
at. The map moves KEYS and only keys -- it carries no statuses, so it can
never launder a ``done -> backlog`` flip (Spec Constraint *Re-key, never
regress*).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

__all__ = (
    "REKEY_GLOB",
    "RekeyMap",
    "load_rekey_maps",
    "parse_rekey",
    "reverse_map",
)

#: Where a fold PR puts its map, relative to the repo root. One or more per
#: project; every one is durable provenance and stays tracked forever.
REKEY_GLOB = "_bmad-output/projects/*/planning-artifacts/rekey-*.md"

_LINE_RE = re.compile(r"^\s*(?P<old>[A-Za-z0-9][A-Za-z0-9._-]*)\s*->\s*(?P<new>[A-Za-z0-9][A-Za-z0-9._-]*)\s*$")


@dataclass(frozen=True)
class RekeyMap:
    """A parsed map plus everything the parser refused to guess about."""

    mapping: dict[str, str] = field(default_factory=dict)
    #: ``(line_no, text)`` for every line that is neither blank, comment nor
    #: ``old -> new``.
    malformed: tuple[tuple[int, str], ...] = ()
    #: ``(line_no, old)`` for an old key mapped twice (second mapping wins
    #: nothing -- it is refused, the first stands).
    duplicates: tuple[tuple[int, str], ...] = ()
    #: New keys that two or more old keys collapse onto -- always an error
    #: for a ledger (two rows cannot share a key).
    collisions: tuple[str, ...] = ()

    @property
    def clean(self) -> bool:
        return not (self.malformed or self.duplicates or self.collisions)


def parse_rekey(text: str) -> RekeyMap:
    """Parse one map file's text. Never raises."""
    mapping: dict[str, str] = {}
    malformed: list[tuple[int, str]] = []
    duplicates: list[tuple[int, str]] = []
    for no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if m is None:
            malformed.append((no, raw))
            continue
        old, new = m.group("old"), m.group("new")
        if old in mapping:
            duplicates.append((no, old))
            continue
        mapping[old] = new
    seen: dict[str, int] = {}
    for new in mapping.values():
        seen[new] = seen.get(new, 0) + 1
    collisions = tuple(sorted(k for k, n in seen.items() if n > 1))
    return RekeyMap(
        mapping=mapping,
        malformed=tuple(malformed),
        duplicates=tuple(duplicates),
        collisions=collisions,
    )


def load_rekey_maps(target: Path) -> dict[str, list[tuple[Path, RekeyMap]]]:
    """Every tracked map in the working tree, grouped by project slug
    (``pyforge-<s>``). Unreadable files are skipped silently -- a reader that
    needs to know calls ``parse_rekey`` on the text itself."""
    out: dict[str, list[tuple[Path, RekeyMap]]] = {}
    for path in sorted(target.glob(REKEY_GLOB)):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            continue
        slug = path.parent.parent.name
        out.setdefault(slug, []).append((path, parse_rekey(text)))
    return out


def reverse_map(maps: list[tuple[Path, RekeyMap]]) -> dict[str, tuple[str, ...]]:
    """``new -> (old, ...)`` across a project's maps. Chained renames
    (``a -> b`` in one map, ``b -> c`` in a later one) resolve so ``c`` lists
    both ``a`` and ``b``: evidence recorded under any earlier spelling of a
    story still confirms it."""
    forward: dict[str, str] = {}
    for _path, m in maps:
        forward.update(m.mapping)
    rev: dict[str, set[str]] = {}
    for old in forward:
        cur, hops = old, 0
        while cur in forward and hops < 64:
            cur = forward[cur]
            hops += 1
        rev.setdefault(cur, set()).add(old)
    return {k: tuple(sorted(v)) for k, v in rev.items()}
