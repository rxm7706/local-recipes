"""Story 19.1 / spec-pyforge-scribe CAP-27 -- the session contract reaches every harness from one file.

`AGENTS.md` is the only place the estate's cross-tool contract is written. Every harness
loads it natively or through a one-line pointer, and the per-tool files carry tool-specific
addenda only. Copies are the failure mode: the Copilot cloud agent and Devin's Knowledge
ingest `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` and every `.mdc` together, so a mirrored
section loads two or three times and contradicts on the next edit. This test is the gate
CAP-27 names -- a missing pointer, a duplicated section, an oversized per-tool file or a
dangling team-memory path reds the scribe suite. Research (every harness's live docs,
2026-09-19): `planning-artifacts/research/multi-harness-instruction-surface-2026-09-19.md`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


ROOT = _repo_root()
AGENTS = ROOT / "AGENTS.md"

# The per-tool entry files: each is an addendum for one harness and points at AGENTS.md.
POINTER_FILES = (
    "GEMINI.md",
    ".github/copilot-instructions.md",
    ".cursor/rules/specs.mdc",
)
# Every Cursor rule is loaded beside AGENTS.md, so none may repeat one of its sections.
CURSOR_RULES = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / ".cursor" / "rules").glob("*.mdc"))
POINTER_MAX_LINES = 60

_H2 = re.compile(r"^## +(.+?)\s*$", re.M)
_MEMORY_PATH = re.compile(r"`?(\.claude/memory/[A-Za-z0-9_./-]+\.md)`?")


#: Story 19.3 (CAP-29): H2s are compared after normalisation -- casefold, a
#: trailing parenthetical dropped, non-letters removed, and the British/American
#: spellings this repo mixes folded together. The pre-19.3 guard compared raw
#: casefolded text, so CLAUDE.md "## Behavioral Guidelines" and AGENTS.md
#: "## Behavioural guidelines (every harness)" -- the same five principles --
#: never read as a duplicate.
_PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")
_NON_LETTER = re.compile(r"[^a-z]+")
_SPELLING = (("behavioural", "behavioral"), ("optimis", "optimiz"), ("normalis", "normaliz"),
             ("organis", "organiz"), ("colour", "color"), ("catalogue", "catalog"))


def _normalise_heading(heading: str) -> str:
    h = _PARENTHETICAL.sub("", heading.strip().casefold())
    h = _NON_LETTER.sub("", h)
    for british, american in _SPELLING:
        h = h.replace(british, american)
    return h


def _h2_headings(text: str) -> set[str]:
    return {_normalise_heading(h) for h in _H2.findall(text)}


def _strip_jsonc(text: str) -> str:
    """`.vscode/settings.json` carries `//` comments; drop whole-line comments before parsing."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))


def _lines_outside_fences(text: str) -> list[str]:
    out, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    return out


def test_claude_md_imports_agents_md_as_a_bare_line() -> None:
    """The import is the floor on every runtime: below Claude Code 2.1.277, on Bedrock / Vertex /
    Foundry, and in the built-in agents-md mod's default mode (which stays out of any project that
    has a CLAUDE.md), AGENTS.md reaches Claude Code only through this `@AGENTS.md` import (Story 19.3
    / CAP-29 pins `claude-md-and-agents-md` on top, which dedupes the import by path). A backticked
    `@AGENTS.md` is an inert code span, not an import."""
    lines = _lines_outside_fences((ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
    assert "@AGENTS.md" in [line.strip() for line in lines], (
        "CLAUDE.md must carry a bare `@AGENTS.md` line -- without it the verified bmad:context "
        "block never loads in a Claude Code session"
    )


def test_gemini_settings_name_agents_md_first() -> None:
    """Gemini CLI reads AGENTS.md only when `context.fileName` names it (default: GEMINI.md only)."""
    settings = json.loads((ROOT / ".gemini" / "settings.json").read_text(encoding="utf-8"))
    names = settings["context"]["fileName"]
    if isinstance(names, str):
        names = [names]
    assert names[0] == "AGENTS.md", f".gemini/settings.json context.fileName must start with AGENTS.md, got {names}"
    assert "GEMINI.md" in names, "GEMINI.md stays the Gemini-only addendum and must remain listed"


def test_vscode_chat_loads_agents_md() -> None:
    """VS Code Copilot chat reads AGENTS.md only with `chat.useAgentsMdFile` (off by default)."""
    settings = json.loads(_strip_jsonc((ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")))
    assert settings.get("chat.useAgentsMdFile") is True


@pytest.mark.parametrize("rel", POINTER_FILES)
def test_pointer_file_points_at_agents_md_and_stays_thin(rel: str) -> None:
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert "AGENTS.md" in text, f"{rel} must point at AGENTS.md"
    n = len(text.splitlines())
    assert n <= POINTER_MAX_LINES, f"{rel} is {n} lines; a per-tool file is an addendum (<= {POINTER_MAX_LINES})"


@pytest.mark.parametrize("rel", POINTER_FILES + tuple(CURSOR_RULES))
def test_per_tool_file_repeats_no_agents_md_section(rel: str) -> None:
    """The duplication guard: a per-tool file may not carry an H2 that AGENTS.md also carries."""
    agents_h2 = _h2_headings(AGENTS.read_text(encoding="utf-8"))
    tool_h2 = _h2_headings((ROOT / rel).read_text(encoding="utf-8"))
    dup = sorted(agents_h2 & tool_h2)
    assert not dup, f"{rel} repeats AGENTS.md section(s) {dup}; move the content to AGENTS.md and point at it"


def test_agents_md_names_the_team_memory_boot_read_and_the_way_in() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert ".claude/memory/MEMORY.md" in text, "AGENTS.md must name the session-boot read"
    assert "scribe capture" in text, "AGENTS.md must name `scribe capture` as the way into team memory"
    assert "~/.claude/projects" in text, (
        "AGENTS.md must say the per-user auto-memory is outside the repo, so nobody cites it"
    )


def test_every_team_memory_path_agents_md_cites_exists() -> None:
    """PR #1513 cited five memory files that lived only in one operator's home directory."""
    text = AGENTS.read_text(encoding="utf-8")
    cited = sorted(set(_MEMORY_PATH.findall(text)))
    assert cited, "AGENTS.md should cite at least the MEMORY.md index"
    missing = [c for c in cited if not (ROOT / c).is_file()]
    assert not missing, f"AGENTS.md cites team-memory paths that do not exist in the repo: {missing}"


def test_agents_md_documents_every_pointer_mechanism() -> None:
    """The harness table must name the exact mechanism this test enforces for each harness."""
    text = AGENTS.read_text(encoding="utf-8")
    for token in ("@AGENTS.md", "context.fileName", "chat.useAgentsMdFile", "copilot-setup-steps.yml"):
        assert token in text, f"AGENTS.md's harness table must name {token}"


def test_bmad_context_block_is_intact() -> None:
    """CAP-27 edits only the prose outside bmad-project-context's managed block."""
    text = AGENTS.read_text(encoding="utf-8")
    assert text.count("<!-- bmad:context -->") == 1 and text.count("<!-- /bmad:context -->") == 1
    assert text.index("<!-- bmad:context -->") < text.index("<!-- /bmad:context -->")


# --- Story 19.3 (spec-pyforge-scribe CAP-29): Claude Code's built-in agents-md mod ---

def test_heading_normalisation_folds_the_spelling_and_parenthetical_the_old_guard_missed() -> None:
    assert _normalise_heading("Behavioral Guidelines") == _normalise_heading("Behavioural guidelines (every harness)")
    assert _normalise_heading("Team memory — read at session start, every harness") != _normalise_heading("Team Memory Index")


def test_agents_md_claude_code_row_states_the_mod_version_and_the_pinned_mode() -> None:
    """The mod's default mode stays out of a project that has a CLAUDE.md; the
    row must say which version, which pinned mode, and that the import is the
    floor -- so nobody deletes CLAUDE.md to \"default to AGENTS.md\"."""
    text = AGENTS.read_text(encoding="utf-8")
    row = next((line for line in text.splitlines() if line.startswith("| Claude Code |")), "")
    assert row, "AGENTS.md's harness table has no Claude Code row"
    for needle in ("@AGENTS.md", "2.1.277", "agents-md", "claude-md-and-agents-md", "claude_instruction_mode_check.py"):
        assert needle in row, f"the Claude Code row must name {needle!r}"


def test_claude_md_does_not_restate_the_behavioural_guidelines() -> None:
    """CAP-29 collapsed the duplicate: CLAUDE.md points at AGENTS.md's section."""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Think Before Coding** —" not in text, "CLAUDE.md restates the five principles; point at AGENTS.md instead"
    assert "Behavioural guidelines (every harness)" in text


def test_project_settings_custom_instructions_point_at_agents_md() -> None:
    import json as _json
    settings = _json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    joined = " ".join(settings.get("customInstructions", []))
    assert "AGENTS.md" in joined and "CLAUDE.md" not in joined


def test_runtime_mode_check_is_registered_and_silent_without_claude(tmp_path) -> None:
    """The currency signal for the operator's own runtime: a runtime-scope
    detector with a pixi task, silent when no claude binary exists."""
    import importlib.util as _ilu
    import subprocess as _sp
    import sys as _sys

    script = ROOT / "scripts" / "claude_instruction_mode_check.py"
    assert script.is_file()
    assert "[feature.guild-tasks.tasks.claude-instruction-mode-check]" in (ROOT / "pixi.toml").read_text(encoding="utf-8")
    spec = _ilu.spec_from_file_location("claude_instruction_mode_check", script)
    mod = _ilu.module_from_spec(spec); spec.loader.exec_module(mod)  # type: ignore[union-attr]
    assert mod.DETECTOR == {"scope": "runtime"}
    assert mod.PINNED_MODE == "claude-md-and-agents-md" and mod.MIN_VERSION == (2, 1, 277)
    assert mod.configured_mode({"pluginConfigs": {"agents-md@builtin": {"options": {"instructionFiles": "claude-md-and-agents-md"}}}}) == "claude-md-and-agents-md"
    assert mod.configured_mode({"projectInstructions": "both"}) == "claude-md-and-agents-md"
    assert mod.configured_mode({}) is None
    absent = _sp.run([_sys.executable, str(script), "--claude", str(tmp_path / "no-such-claude"), "--settings", str(tmp_path / "none.json")],
                     capture_output=True, text=True)
    assert absent.returncode == 2 and "could-not-run" in absent.stdout
