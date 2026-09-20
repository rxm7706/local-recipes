#!/usr/bin/env python3
"""``commit-msg`` hook: a commit message carries no ``Co-Authored-By:`` line
and no AI-attribution trailer (steward Story 66.2, ``spec-pyforge-steward``
CAP-154 -- the AGENTS.md policy line, enforced instead of stated).

Invoked by pre-commit with the message file as the only argument. Comment
lines (``#``) are ignored, the way git does. Names the rule and the offending
line, and exits 1; a clean message exits 0.

    python scripts/commit_msg_hook.py .git/COMMIT_EDITMSG
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RULE = "AGENTS.md § Policy: commit messages carry no `Co-Authored-By` line and no AI attribution"
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Co-Authored-By trailer", re.compile(r"^\s*co-authored-by\s*:", re.I)),
    ("AI-attribution line", re.compile(r"generated (with|by) \[?(claude|copilot|gemini|cursor|codex|chatgpt|openai|anthropic)", re.I)),
    ("AI-attribution emoji line", re.compile(r"^\s*🤖")),
)


def offending_lines(message: str) -> list[tuple[int, str, str]]:
    out: list[tuple[int, str, str]] = []
    for n, line in enumerate(message.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for name, pat in PATTERNS:
            if pat.search(line):
                out.append((n, name, line.strip()))
                break
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: commit_msg_hook.py <commit-message-file>")
        return 2
    message = Path(argv[0]).read_text(encoding="utf-8", errors="replace")
    hits = offending_lines(message)
    if not hits:
        return 0
    print(f"commit refused -- {RULE}")
    for n, name, line in hits:
        print(f"  line {n}: {name}: {line[:100]}")
    print("remove the line(s) and commit again (git commit --amend / re-run the commit)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
