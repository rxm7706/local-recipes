#!/usr/bin/env python3
"""``commit-msg`` hook: a commit message carries no ``Co-Authored-By:`` line
and no AI-attribution trailer (steward Story 66.2, ``spec-pyforge-steward``
CAP-154 -- the AGENTS.md policy line, enforced instead of stated).

Also WARNS (never refuses) on Story 59.6 / CAP-137's commit-subject shape
(Ruling 17, ``docs/dreams/vocabulary-one-name-one-job.md``): a Capitalized
sentence, no trailing period, conventional ``type(scope):`` allowed only
under ``recipes/`` and the CFE changelog. Ruling 17 calls this "the one
shape a commit hook can enforce", but several already-live machine commit
generators (``pyforge-marshal``'s dispatch/land/deploy flows, e.g.
``"marshal: reconcile spec-surface drift for ..."``) predate the rule and
are out of this story's scope to migrate -- making the shape check BLOCKING
would refuse those commits today. It stays advisory until those call sites
are brought into line (tracked as follow-up, not this story). The
auto-checkpoint marker is excluded even from the warning: it is a
deliberately internal, never-pushed commit shape (``worktree_checkpoint.py``)
that would otherwise warn on every idle checkpoint, drowning the signal.

Invoked by pre-commit with the message file as the only argument. Comment
lines (``#``) are ignored, the way git does. Names the rule and the offending
line for the blocking check, and exits 1; a clean message exits 0.

    python scripts/commit_msg_hook.py .git/COMMIT_EDITMSG
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RULE = "AGENTS.md § Policy: commit messages carry no `Co-Authored-By` line and no AI attribution"
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Co-Authored-By trailer", re.compile(r"^\s*co-authored-by\s*:", re.I)),
    ("AI-attribution line", re.compile(r"generated (with|by) \[?(claude|copilot|gemini|cursor|codex|chatgpt|openai|anthropic)", re.I)),
    ("AI-attribution emoji line", re.compile(r"^\s*🤖")),
)

_CONVENTIONAL_RE = re.compile(r"^[a-z][a-z0-9_-]*(\([\w./-]+\))?!?:\s")
_AUTO_CHECKPOINT_MARKER = "(auto-checkpoint)"
_CFE_CHANGELOG_PATH = ".claude/skills/conda-forge-expert/CHANGELOG.md"


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


def subject_line(message: str) -> str:
    """The first non-comment, non-blank line -- the commit subject."""
    for line in message.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            return line.strip()
    return ""


def _staged_paths() -> list[str] | None:
    """Staged paths relative to the repo root, or ``None`` when they could
    not be determined (git unavailable / not a repo) -- callers then skip
    the recipes/CFE-changelog exemption rather than guessing."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def _is_recipe_or_changelog_commit(staged: list[str] | None) -> bool:
    if not staged:
        return False
    return all(path.startswith("recipes/") or path == _CFE_CHANGELOG_PATH for path in staged)


def subject_shape_warning(subject: str, *, staged: list[str] | None) -> str | None:
    """``None`` when ``subject`` matches Ruling 17's shape (or is exempt),
    otherwise a human-readable reason."""
    if not subject:
        return None
    if _AUTO_CHECKPOINT_MARKER in subject:
        return None
    if _CONVENTIONAL_RE.match(subject):
        if _is_recipe_or_changelog_commit(staged):
            return None
        return (
            "conventional `type(scope):` subject is only for commits under `recipes/` "
            "or the CFE changelog (Ruling 17)"
        )
    if not subject[0:1].isupper():
        return "subject should be a Capitalized sentence (Ruling 17)"
    if subject.endswith("."):
        return "subject should carry no trailing period (Ruling 17)"
    return None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: commit_msg_hook.py <commit-message-file>")
        return 2
    message = Path(argv[0]).read_text(encoding="utf-8", errors="replace")

    warning = subject_shape_warning(subject_line(message), staged=_staged_paths())
    if warning is not None:
        print(f"commit-msg warning (not refused) -- {warning}")

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
