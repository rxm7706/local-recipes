"""pyforge.scribe.extras.move_list -- the foundry-cutover move-list scan
(Story 6.1; docs/dreams/pyforge-target-monorepo.md's cutover phases;
unifying-strategy Grounding 2026-08-30 -- packages fold `src/shared/
packages/` -> `src/packages/`, host drops `sys.path` inserts and
`import pyforge.*`, `five_tier.py` retargets `_packages_root`).

Independent of graphifyy on purpose: the four move-list signals (host
`import pyforge.*` sites, `sys.path` inserts, `five_tier` roots, CFE
callers) are a plain line-oriented scan over `*.py` files, not a graphify
graph analysis -- `scribe index move-list` stays usable even when the
heavy graphify extra is not installed, and never depends on
`SCRIBE_GRAPHIFY_EXTRA`.

Reuses `compile.py`'s own exclusion walk (`_rglob_excluding`) rather than
re-deriving the noise-directory list (`.git`, `.pixi`, `node_modules`, the
worktree homes, `.claude/data`, ...) -- Story 3.3 already paid for that
correctness/performance fix once.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pyforge.scribe.compile import _rglob_excluding

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "import_pyforge",
        re.compile(r"^\s*(import\s+pyforge(\.\w+)*|from\s+pyforge(\.\w+)*\s+import)\b"),
    ),
    ("sys_path_insert", re.compile(r"\bsys\.path\.(insert|append)\s*\(")),
    ("five_tier_root", re.compile(r"\bfive_tier\b")),
    ("cfe_caller", re.compile(r"conda[-_]forge[-_]expert|conda_forge_server")),
)


@dataclass(frozen=True)
class MoveListFinding:
    """One line matching one of the four foundry-cutover move-list signals."""

    category: str  # "import_pyforge" | "sys_path_insert" | "five_tier_root" | "cfe_caller"
    path: str  # repo-relative, posix
    line: int
    snippet: str


def scan_move_list(repo_root: Path) -> list[MoveListFinding]:
    """Scan every `*.py` file (excluding the same noise directories
    `compile.py`'s other surfaces already exclude) for the four cutover-move
    signals. Deterministic order: sorted by (path, line, category), matching
    every other compile surface's own sorted-output discipline.
    """
    findings: list[MoveListFinding] = []
    for path in _rglob_excluding(repo_root, "**/*.py"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relpath = path.relative_to(repo_root).as_posix()
        for line_no, line in enumerate(text.splitlines(), start=1):
            for category, pattern in _PATTERNS:
                if pattern.search(line):
                    findings.append(
                        MoveListFinding(
                            category=category,
                            path=relpath,
                            line=line_no,
                            snippet=line.strip()[:200],
                        )
                    )
    findings.sort(key=lambda f: (f.path, f.line, f.category))
    return findings
