"""Stories 83.3, 83.11 and 83.13: the landing heal's unions, run on this checkout's own ledger and memory index.

Story 116.3 (spec-pyforge-marshal:CAP-305): the ``test_dispatch_land_heal.py`` tests that read this checkout's
``deferred-work-ledger.md`` (pyforge-marshal) or ``.claude/memory/MEMORY.md`` as the union base moved here, marked
``live_tree``, with the offset helpers only they use; the root is found when a test runs, never at import, and a
missing file fails the test, never skips it. Every other heal test stays in ``test_dispatch_land_heal.py``, which
keeps the synthetic index text both files use.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_dispatch_land_heal import _memory_index_text

from pyforge.marshal.core import dispatch_landing as _dispatch_landing
from pyforge.marshal.core.dispatch_landing import union_deferred_work_texts, union_team_memory_index_texts

pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    # tests/unit -> tests -> pyforge-marshal -> packages -> shared -> src -> this checkout's root, found when a
    # test runs, never at import
    return Path(__file__).resolve().parents[6]


def _dw_block_count(text: str) -> int:
    return len(_dispatch_landing._opaque_dw_blocks(text)[1])


def test_union_deferred_work_texts_live_marshal_ledger_mixed_formats() -> None:
    """AC 2026-10-03: union on a copy of the real ledger preserves every base block and both appends."""
    ledger_path = _repo_root() / "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    base = ledger_path.read_text(encoding="utf-8")
    base_count = _dw_block_count(base)

    main_append = "\n\n### DW-TEST-MAIN-83-3: Story 83.3 union probe (main)\norigin: test\nstatus: open\n"
    branch_append = (
        "\n\n### DW-TEST-BRANCH-83-3: Story 83.3 union probe (branch)\n"
        "- source_spec: `spec-83-3-the-landing-heal-unions-appended-deferred-work-rows-the-way-it-unions-memlog-entries.md`\n"
        "  status: open\n"
    )
    main = base.rstrip("\n") + main_append
    branch = base.rstrip("\n") + branch_append

    result = union_deferred_work_texts(base, main, branch)

    assert result is not None
    assert result.startswith(base.rstrip("\n"))
    assert _dw_block_count(result) == base_count + 2
    assert "DW-TEST-MAIN-83-3" in result
    assert "DW-TEST-BRANCH-83-3" in result


def test_union_deferred_work_texts_refuses_legacy_entry_edit_on_live_ledger() -> None:
    """AC 2026-10-03: editing a legacy ``## DW-`` entry while appending refuses union."""
    ledger_path = _repo_root() / "_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md"
    base = ledger_path.read_text(encoding="utf-8")
    probe = "\n\n### DW-PROBE-83-3-LEGACY: union legacy-edit probe\norigin: test\nstatus: open\n"
    branch = base.rstrip("\n") + probe
    main = base.replace("status: open\n  severity: low", "status: closed\n  severity: low", 1)
    main = main.rstrip("\n") + probe

    assert union_deferred_work_texts(base, main, branch) is None


def _index_entry_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("- [")]


def _live_memory_index() -> str:
    return (_repo_root() / ".claude" / "memory" / "MEMORY.md").read_text(encoding="utf-8")


def _section_insert_offset(text: str, heading: str) -> int:
    """Offset just past the newline ending the last non-blank line of ``heading``'s section."""
    start = text.index(f"## {heading}\n")
    next_h2 = text.find("\n## ", start)
    stop = len(text) if next_h2 == -1 else next_h2 + 1
    return start + len(text[start:stop].rstrip("\n")) + 1


def _preamble_insert_offset(text: str) -> int:
    """Offset just past the newline ending the last non-blank line before the first ``## ``."""
    first_h2 = text.index("\n## ") + 1
    return len(text[:first_h2].rstrip("\n")) + 1


def _insert_lines(text: str, offset: int, *lines: str) -> str:
    return text[:offset] + "".join(f"{line}\n" for line in lines) + text[offset:]


def _append_to_section(text: str, heading: str, *lines: str) -> str:
    return _insert_lines(text, _section_insert_offset(text, heading), *lines)


@pytest.mark.parametrize("heading", ["Feedback", "Project", "Reference"], ids=["first", "middle", "last-at-eof"])
def test_union_team_memory_index_texts_live_memory_md_parallel_appends(heading: str) -> None:
    """Stories 83.11 + 83.13 (AC1): base + main's line + the branch's line at the end of the section,
    every other byte -- each blank line around every ``## `` heading -- kept as it was."""
    base = _live_memory_index()
    assert base.endswith("\n")
    main_line = "- [union-probe-main-83-13](feedback/union-probe-main-83-13.md) — Story 83.13 live union probe (main)"
    branch_line = (
        "- [union-probe-branch-83-13](feedback/union-probe-branch-83-13.md) — Story 83.13 live union probe (branch)"
    )
    k = _section_insert_offset(base, heading)
    main = base[:k] + main_line + "\n" + base[k:]
    branch = base[:k] + branch_line + "\n" + base[k:]
    if heading != "Reference":
        assert main[k + len(main_line) + 1 :].startswith("\n## ")
    result = union_team_memory_index_texts(base, main, branch)
    assert result == base[:k] + main_line + "\n" + branch_line + "\n" + base[k:]
    assert result.count("\n\n## ") == base.count("\n\n## ")
    assert len(_index_entry_lines(result)) == len(_index_entry_lines(base)) + 2


def test_union_team_memory_index_texts_unchanged_returns_main_bytes() -> None:
    base = _memory_index_text()
    assert union_team_memory_index_texts(base, base, base) == base
    live = _live_memory_index()
    assert union_team_memory_index_texts(live, live, live) == live


def test_branch_preamble_append_is_kept() -> None:
    """Story 83.13 send-back (MEDIUM-3): a branch-only preamble line survives a main section append."""
    base = _live_memory_index()
    preamble_line = "Branch preamble line (Story 83.13)."
    main_line = "- [preamble-probe-main](feedback/preamble-probe-main.md) — main appends to Feedback"
    branch = _insert_lines(base, _preamble_insert_offset(base), preamble_line)
    main = _append_to_section(base, "Feedback", main_line)
    expected = _insert_lines(main, _preamble_insert_offset(main), preamble_line)
    assert union_team_memory_index_texts(base, main, branch) == expected


def test_union_team_memory_index_texts_branch_lines_in_two_sections() -> None:
    """Story 83.13 send-back (LOW-2): two branch lines in Feedback plus one in Project, main appending to
    Project -- each section's later ``## `` offsets must survive the earlier insert."""
    base = _live_memory_index()
    branch_lines = [f"- [multi-probe-{n}](feedback/multi-probe-{n}.md) — branch line {n}" for n in (1, 2, 3)]
    main_line = "- [multi-probe-main](feedback/multi-probe-main.md) — main appends to Project"
    branch = _append_to_section(_append_to_section(base, "Feedback", *branch_lines[:2]), "Project", branch_lines[2])
    assert union_team_memory_index_texts(base, base, branch) == branch
    main = _append_to_section(base, "Project", main_line)
    expected = _append_to_section(_append_to_section(main, "Feedback", *branch_lines[:2]), "Project", branch_lines[2])
    assert union_team_memory_index_texts(base, main, branch) == expected


@pytest.mark.parametrize("separator", ["\u2028", "\x0b", "\x1c", "\x85"], ids=["u2028", "x0b", "x1c", "x85"])
def test_union_team_memory_index_texts_keeps_non_newline_line_separators(separator: str) -> None:
    """Story 83.13 send-back (LOW-3): parsing splits on ``\\n`` only, like the reconstruction, so a line
    carrying a ``str.splitlines`` boundary comes back byte for byte (and never reads as a heading)."""
    base = _live_memory_index()
    odd_line = f"- [odd-probe](feedback/odd-probe.md) — odd{separator}tail{separator}## not a heading"
    main_line = "- [odd-probe-main](feedback/odd-probe-main.md) — main appends to Feedback"
    branch = _append_to_section(base, "Feedback", odd_line)
    assert union_team_memory_index_texts(base, base, branch) == branch
    main = _append_to_section(base, "Feedback", main_line)
    expected = _append_to_section(base, "Feedback", main_line, odd_line)
    assert union_team_memory_index_texts(base, main, branch) == expected
