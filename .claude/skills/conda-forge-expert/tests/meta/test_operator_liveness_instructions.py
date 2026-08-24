"""Meta: tracked operator instructions must not prescribe engine.pid hand-parsing
or a bare ``grep 'bmad-loop run'`` as the liveness answer (Marshal Story 24.2,
FR-195 CAP-2 / spec-bmad-loop-liveness-footgun).

Scans team-memory carriers under ``.claude/memory/`` — the checked-in operator
runbook surface agents load every session via ``CLAUDE.md``'s ``@.claude/memory/
MEMORY.md`` import. User-local auto-memory is out of scope (promotion is manual).

Primary answer must be documented in ``reference/fleet-landing-pass-liveness.md``.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
MEMORY_ROOT = REPO_ROOT / ".claude" / "memory"
PRIMARY_DOC = MEMORY_ROOT / "reference" / "fleet-landing-pass-liveness.md"

# Files scanned for forbidden prescriptions (relative to MEMORY_ROOT).
SCAN_GLOBS = ("reference/*.md", "feedback/*.md", "project/*.md")

FORBIDDEN = (
    re.compile(r"cat\s+engine\.pid", re.I),
    re.compile(r"ps\s+-p\s+\$\(cat\s+engine\.pid\)", re.I),
    re.compile(r"ps\s+-p\s+.*engine\.pid", re.I),
    # Bare run-only grep — must include resume|resolve when grep is used for liveness.
    re.compile(
        r"grep(?:\s+-[a-zA-Z]+)*\s+['\"]bmad-loop run['\"]",
        re.I,
    ),
)

# Corroboration greps must match all three argv forms when present.
CORROBORATION_GREP = re.compile(
    r"grep.*bmad-loop.*\(run\|resume\|resolve\)",
    re.I,
)


def _operator_memory_files() -> list[Path]:
    files: list[Path] = []
    for pattern in SCAN_GLOBS:
        files.extend(MEMORY_ROOT.glob(pattern))
    return sorted(p for p in files if p.name != "README.md")


@pytest.mark.parametrize(
    "path",
    [p for p in _operator_memory_files() if p != PRIMARY_DOC],
    ids=lambda p: p.name,
)
def test_operator_memory_never_prescribes_engine_pid_or_bare_run_grep(path: Path):
    text = path.read_text(encoding="utf-8")
    hits: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pat in FORBIDDEN:
            if pat.search(line):
                # Allow lines that explicitly forbid the pattern (Never / do not).
                if re.search(r"\b(never|do not|don't|not prescribe|forbidden)\b", line, re.I):
                    continue
                # Allow bare grep when the line also documents the widened pattern.
                if "run|resume|resolve" in line or "run\\|resume\\|resolve" in line:
                    continue
                hits.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    assert not hits, "Forbidden liveness prescriptions:\n" + "\n".join(hits)


def test_fleet_landing_pass_liveness_doc_is_primary_answer():
    assert PRIMARY_DOC.is_file(), f"missing primary operator doc: {PRIMARY_DOC}"
    text = PRIMARY_DOC.read_text(encoding="utf-8")
    assert "bmad-loop status" in text and "--json" in text
    assert "bmad-loop list --json" in text
    assert "cat engine.pid" in text  # documented as forbidden
    assert "run|resume|resolve" in text or "run\\|resume\\|resolve" in text


def test_memory_index_links_fleet_landing_pass_liveness():
    index = (MEMORY_ROOT / "MEMORY.md").read_text(encoding="utf-8")
    assert "fleet-landing-pass-liveness" in index
