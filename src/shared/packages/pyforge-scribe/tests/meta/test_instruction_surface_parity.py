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
import os
import re
import stat
import subprocess
import sys
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
_SPELLING = (
    ("behavioural", "behavioral"),
    ("optimis", "optimiz"),
    ("normalis", "normaliz"),
    ("organis", "organiz"),
    ("colour", "color"),
    ("catalogue", "catalog"),
)


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


#: Story 23.2 (CAP-29): the duplicate guard also reads CLAUDE.md, the file whose
#: duplicate motivated CAP-29. CLAUDE.md stays out of POINTER_FILES: the 60-line
#: thin rule is CAP-27's for the per-tool addenda, not for CLAUDE.md.
DUPLICATE_GUARD_FILES = tuple(dict.fromkeys(POINTER_FILES + tuple(CURSOR_RULES) + ("CLAUDE.md",)))


def _duplicate_h2(agents_text: str, tool_text: str) -> list[str]:
    """The normalised H2s a per-tool file shares with AGENTS.md."""
    return sorted(_h2_headings(agents_text) & _h2_headings(tool_text))


@pytest.mark.parametrize("rel", DUPLICATE_GUARD_FILES)
def test_per_tool_file_repeats_no_agents_md_section(rel: str) -> None:
    """The duplication guard: a per-tool file may not carry an H2 that AGENTS.md also carries."""
    dup = _duplicate_h2(AGENTS.read_text(encoding="utf-8"), (ROOT / rel).read_text(encoding="utf-8"))
    assert not dup, f"{rel} repeats AGENTS.md section(s) {dup}; move the content to AGENTS.md and point at it"


def test_duplicate_guard_reports_a_planted_normalised_duplicate_in_claude_md() -> None:
    """Story 23.2: the guard path itself, not only the normaliser, flags the CAP-29 duplicate."""
    agents = AGENTS.read_text(encoding="utf-8")
    assert "## Behavioural guidelines (every harness)" in agents
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert _duplicate_h2(agents, claude) == []
    planted = claude + "\n## Behavioral Guidelines\n\n1. Think before coding.\n"
    assert _duplicate_h2(agents, planted) == [_normalise_heading("Behavioural guidelines (every harness)")]
    assert "CLAUDE.md" in DUPLICATE_GUARD_FILES and "CLAUDE.md" not in POINTER_FILES


def test_agents_md_names_the_team_memory_boot_read_and_the_way_in() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert ".claude/memory/MEMORY.md" in text, "AGENTS.md must name the session-boot read"
    assert "scribe capture" in text, "AGENTS.md must name `scribe capture` as the way into team memory"
    assert "~/.claude/projects" in text, (
        "AGENTS.md must say the per-user auto-memory is outside the repo, so nobody cites it"
    )


def test_agents_md_states_the_session_close_ritual_with_hygiene() -> None:
    """Story 46.3 / spec-pyforge-marshal CAP-192: the close ritual is named once, in
    AGENTS.md, with capture hygiene stated alongside it -- not left implicit in the
    conditional bullets around it."""
    text = AGENTS.read_text(encoding="utf-8")
    assert "session-close ritual" in text.casefold(), "AGENTS.md must name the session-close ritual"
    assert "no secrets, decision-grade facts only" in text, "AGENTS.md must state capture hygiene"


@pytest.mark.parametrize(
    "rel",
    (
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".cursor/rules/trunk-worktree-pr.mdc",
        ".claude/skills/pyforge-marshal/0.1.0/pyforge-marshal/SKILL.md",
        ".claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md",
    ),
)
def test_harness_profile_points_at_the_session_close_ritual(rel: str) -> None:
    """Each harness profile / station skill note carries a one-line pointer to the ritual,
    never a restatement."""
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert "scribe capture" in text and "session-close ritual" in text.casefold(), (
        f"{rel} must point at the AGENTS.md session-close ritual"
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
    assert _normalise_heading("Team memory — read at session start, every harness") != _normalise_heading(
        "Team Memory Index"
    )


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


_PRINCIPLE = re.compile(r"^\d+\. \*\*(.+?)\*\*", re.M)


def _agents_md_principles(agents_text: str) -> list[str]:
    """The bolded principle names in AGENTS.md § Behavioural guidelines (every harness)."""
    section = agents_text.split("## Behavioural guidelines (every harness)", 1)[1].split("\n## ", 1)[0]
    return _PRINCIPLE.findall(section)


def test_project_settings_custom_instructions_point_at_agents_md() -> None:
    """Story 23.2 (operator ruling 2026-11-01): one sentence pointing at the AGENTS.md
    section, never a list of its principles -- a list goes stale (it named five of eight)."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    entries = settings.get("customInstructions", [])
    joined = " ".join(entries)
    assert "AGENTS.md" in joined and "CLAUDE.md" not in joined
    assert len(entries) == 1, f"customInstructions is one pointer sentence, got {len(entries)} entries"
    sentence = entries[0].strip()
    assert "AGENTS.md § Behavioural guidelines (every harness)" in sentence
    assert len(re.findall(r"[.!?](?:\s|$)", sentence)) == 1 and ":" not in sentence, (
        f"customInstructions must be one sentence with no list: {sentence!r}"
    )
    principles = _agents_md_principles(AGENTS.read_text(encoding="utf-8"))
    assert len(principles) >= 8, principles
    listed = [p for p in principles if p.casefold() in sentence.casefold()]
    assert not listed, f"customInstructions restates AGENTS.md principles {listed}; point at the section instead"


SCRIPT = ROOT / "scripts" / "claude_instruction_mode_check.py"
_PINNED_SETTINGS = {
    "pluginConfigs": {"agents-md@builtin": {"options": {"instructionFiles": "claude-md-and-agents-md"}}}
}


def _run_mode_check(path_dir: Path, settings: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    """Run the check with PATH holding only ``path_dir``, so ``shutil.which`` sees a stub or nothing."""
    env = {**os.environ, "PATH": str(path_dir)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--settings", str(settings), *extra],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def _stub_claude(bin_dir: Path, version: str) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    stub = bin_dir / "claude"
    stub.write_text(f"#!{sys.executable}\nprint({version + ' (Claude Code)'!r})\n", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_runtime_mode_check_is_registered() -> None:
    """The currency signal for the operator's own runtime: a runtime-scope
    detector with a pixi task."""
    import importlib.util as _ilu

    script = SCRIPT
    assert script.is_file()
    assert "[feature.guild-tasks.tasks.claude-instruction-mode-check]" in (ROOT / "pixi.toml").read_text(
        encoding="utf-8"
    )
    spec = _ilu.spec_from_file_location("claude_instruction_mode_check", script)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    assert mod.DETECTOR == {"scope": "runtime"}
    assert mod.PINNED_MODE == "claude-md-and-agents-md" and mod.MIN_VERSION == (2, 1, 277)
    assert (
        mod.configured_mode(
            {"pluginConfigs": {"agents-md@builtin": {"options": {"instructionFiles": "claude-md-and-agents-md"}}}}
        )
        == "claude-md-and-agents-md"
    )
    assert mod.configured_mode({"projectInstructions": "both"}) == "claude-md-and-agents-md"
    assert mod.configured_mode({}) is None


@pytest.mark.skipif(sys.platform == "win32", reason="the stub claude is a shebang script")
def test_runtime_mode_check_is_silent_without_claude_on_path(tmp_path: Path) -> None:
    """Story 23.2 (CAP-29): the no-binary branch -- exit 0, empty stdout."""
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    absent = _run_mode_check(empty, tmp_path / "none.json")
    assert absent.returncode == 0, absent.stdout + absent.stderr
    assert absent.stdout == "", f"the no-claude branch must stay silent, printed {absent.stdout!r}"


@pytest.mark.skipif(sys.platform == "win32", reason="the stub claude is a shebang script")
@pytest.mark.parametrize(
    ("version", "pinned", "expected_rc", "needle"),
    (
        ("2.1.276", True, 1, "predates the built-in agents-md mod"),
        ("2.1.300", False, 1, "pins instructionFiles=default"),
        ("2.1.300", True, 0, "ok -- Claude Code 2.1.300 with instructionFiles=claude-md-and-agents-md"),
    ),
    ids=("old-runtime-warns", "unpinned-mode-warns", "pinned-current-ok"),
)
def test_runtime_mode_check_branches_with_a_stub_claude(
    tmp_path: Path, version: str, pinned: bool, expected_rc: int, needle: str
) -> None:
    """Story 23.2 (CAP-29): both warn branches and the ok branch, end to end."""
    bin_dir = tmp_path / "bin"
    _stub_claude(bin_dir, version)
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(_PINNED_SETTINGS if pinned else {}), encoding="utf-8")
    run = _run_mode_check(bin_dir, settings)
    assert run.returncode == expected_rc, run.stdout + run.stderr
    assert needle in run.stdout, run.stdout


def test_runtime_mode_check_could_not_run_on_a_missing_claude_path(tmp_path: Path) -> None:
    """An explicit ``--claude`` that does not exist is the could-not-run branch (exit 2)."""
    run = _run_mode_check(tmp_path, tmp_path / "none.json", "--claude", str(tmp_path / "no-such-claude"))
    assert run.returncode == 2 and "could-not-run" in run.stdout, run.stdout + run.stderr


# --- Story 20.1 (spec-pyforge-scribe CAP-30): the managed block carries no aspiration ---
#
# Two `TODO:` lines stood inside AGENTS.md's bmad:context block from 2026-09-04 to
# 2026-09-20 with no Story behind them, so nothing ever scheduled them -- exactly the
# "aspirational state" bmad-project-context's own best-practices exclude. The block
# states present truth; an intent that has no Story goes to a Dream entry instead.
# Scope is the text BETWEEN the markers only.

_ASPIRATION = re.compile(r"\bTODO\b\s*:|\bFIXME\b\s*:|\bnot (?:yet )?landed\b", re.I)


def _managed_block(text: str) -> str:
    start = text.index("<!-- bmad:context -->")
    end = text.index("<!-- /bmad:context -->")
    return text[start:end]


def _aspiration_lines(text: str) -> list[str]:
    return [line.strip() for line in _managed_block(text).splitlines() if _ASPIRATION.search(line)]


def test_managed_block_carries_no_todo_or_not_yet_landed_line() -> None:
    hits = _aspiration_lines(AGENTS.read_text(encoding="utf-8"))
    assert not hits, (
        "AGENTS.md's bmad:context block states present truth; a decision without a Story is a "
        "Dream entry, never a TODO line every session pays for (spec-pyforge-scribe CAP-30):\n  " + "\n  ".join(hits)
    )


def test_aspiration_guard_reads_only_between_the_markers() -> None:
    planted = (
        "# x\n<!-- bmad:context -->\n## Policy\n- Do the thing. TODO: wire the hook later.\n"
        "- Fine line.\n<!-- /bmad:context -->\n\nTODO: text outside the block is not in scope.\n"
    )
    assert _aspiration_lines(planted) == ["- Do the thing. TODO: wire the hook later."]
    clean = planted.replace(" TODO: wire the hook later.", "")
    assert _aspiration_lines(clean) == []


@pytest.mark.parametrize(
    "line",
    (
        "- The hook. FIXME: wire it later.",
        "- The relay is not yet landed.",
        "- The relay is not landed.",
    ),
    ids=("fixme", "not-yet-landed", "not-landed"),
)
def test_aspiration_guard_reports_every_branch_inside_and_ignores_it_outside(line: str) -> None:
    """Story 23.2 (CAP-30): each regex branch has a planted case, so dropping one reds."""
    inside = f"# x\n<!-- bmad:context -->\n## Policy\n{line}\n- Fine line.\n<!-- /bmad:context -->\n"
    assert _aspiration_lines(inside) == [line]
    outside = f"# x\n<!-- bmad:context -->\n## Policy\n- Fine line.\n<!-- /bmad:context -->\n\n{line}\n"
    assert _aspiration_lines(outside) == []


# --- Story 23.2 (spec-pyforge-scribe CAP-32): the managed block types no derived count ---
#
# The estate catalog (docs/reference/bmad-estate-llms-full.md) derives the suite-member and
# skill-family counts; a count typed into the bmad:context block ("13 members", "16 skf ones")
# goes stale on the next roster move. The block points at the catalog instead.

_TYPED_COUNT = re.compile(
    r"\b\d+\s+(?:(?:active|adopted|installed|bmad-suite|suite|bmad|skf)\s+)*"
    r"(?:members?|ones|skills?|skill[- ]famil(?:y|ies))\b",
    re.I,
)


def _typed_counts(text: str) -> list[str]:
    return [line.strip() for line in _managed_block(text).splitlines() if _TYPED_COUNT.search(line)]


def test_managed_block_types_no_suite_member_or_skill_family_count() -> None:
    hits = _typed_counts(AGENTS.read_text(encoding="utf-8"))
    assert not hits, (
        "AGENTS.md's bmad:context block types a count the estate catalog derives; point at "
        "docs/reference/bmad-estate-llms-full.md instead (spec-pyforge-scribe CAP-32):\n  " + "\n  ".join(hits)
    )


@pytest.mark.parametrize(
    "line",
    (
        "- bmad-suite member wiring (which of the 13 members is adopted, its wielding station).",
        "- It removes every skill dir, not the 16 skf ones.",
    ),
    ids=("13-members", "16-skf-ones"),
)
def test_typed_count_guard_reports_a_planted_count_inside_the_block(line: str) -> None:
    inside = f"# x\n<!-- bmad:context -->\n## Where things are\n{line}\n<!-- /bmad:context -->\n"
    assert _typed_counts(inside) == [line]
    outside = f"# x\n<!-- bmad:context -->\n## Where things are\n<!-- /bmad:context -->\n\n{line}\n"
    assert _typed_counts(outside) == []


# --- Story 23.2 (spec-pyforge-scribe CAP-27): the 2026-09-26 end state holds ---
#
# The SKF managed block lives in AGENTS.md only (scribe Story 23.1): CLAUDE.md carries none,
# skf exports to `other` only, and AGENTS.md says which runners carry governance-currency.
# skf 3.0 still lists `claude-code` in its platform codes, so a hand reinstall would put the
# block back into CLAUDE.md; steward's upgrade restores _bmad/skf/config.yaml, and this test
# reds the regression either way. That AGENTS.md carries the block is mason's assert
# (tests/meta/test_persona_consults_cfe.py), not repeated here.

SKF_CONFIG = ROOT / "_bmad" / "skf" / "config.yaml"


def _governance_currency_bullet(agents_text: str) -> str:
    """The Pre-PR item 10 bullet that says where governance-currency runs, continuation lines joined."""
    lines = agents_text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("- `governance-currency` reds"):
            indent = len(line) - len(line.lstrip())
            out = [line.strip()]
            for nxt in lines[i + 1 :]:
                stripped = nxt.lstrip()
                if not stripped or len(nxt) - len(stripped) <= indent or stripped.startswith("- "):
                    break
                out.append(stripped)
            return " ".join(out)
    return ""


def _skf_end_state_breaks(claude_md: str, skf_ides: object, agents_md: str) -> list[str]:
    breaks = []
    if "<!-- SKF:BEGIN" in claude_md:
        breaks.append("CLAUDE.md carries an SKF managed block (<!-- SKF:BEGIN); it lives in AGENTS.md only")
    if skf_ides != ["other"]:
        breaks.append(
            f"_bmad/skf/config.yaml ides is {skf_ides!r}, not ['other']; claude-code puts the block in CLAUDE.md"
        )
    bullet = _governance_currency_bullet(agents_md)
    for runner in ("`detectors-ci`", "`pr-preflight`"):
        if runner not in bullet:
            breaks.append(f"AGENTS.md's governance-currency line (Pre-PR item 10) does not name {runner} as a runner")
    return breaks


def _top_level_list(text: str, key: str) -> list[str] | None:
    """The block or flow list under a top-level ``key:`` of a flat YAML file, read with the stdlib (Story 23.2
    review follow-up: PyYAML is not a declared scribe dependency). ``None`` when the key is absent."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith(f"{key}:"):
            continue
        rest = line[len(key) + 1 :].split("#", 1)[0].strip()
        if rest.startswith("[") and rest.endswith("]"):
            return [item.strip().strip("'\"") for item in rest[1:-1].split(",") if item.strip()]
        items: list[str] = []
        for follow in lines[i + 1 :]:
            stripped = follow.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not follow.startswith((" ", "\t")):
                break
            if stripped.startswith("- "):
                items.append(stripped[2:].split("#", 1)[0].strip().strip("'\""))
        return items
    return None


def _live_skf_end_state() -> tuple[str, object, str]:
    ides = _top_level_list(SKF_CONFIG.read_text(encoding="utf-8"), "ides")
    return (ROOT / "CLAUDE.md").read_text(encoding="utf-8"), ides, AGENTS.read_text(encoding="utf-8")


def test_the_2026_09_26_skf_end_state_holds() -> None:
    breaks = _skf_end_state_breaks(*_live_skf_end_state())
    assert not breaks, "CAP-27's 2026-09-26 end state regressed:\n  " + "\n  ".join(breaks)


@pytest.mark.parametrize(
    ("mutate", "clause"),
    (
        (lambda c, i, a: (c + "\n<!-- SKF:BEGIN updated:2026-11-01 -->\n<!-- SKF:END -->\n", i, a), "CLAUDE.md"),
        (lambda c, i, a: (c, ["other", "claude-code"], a), "ides"),
        (lambda c, i, a: (c, i, a.replace("so `detectors-ci` and", "so")), "`detectors-ci`"),
        (lambda c, i, a: (c, i, a.replace("and a full-scope `pr-preflight` run", "runs")), "`pr-preflight`"),
    ),
    ids=("claude-md-skf-block", "ides-claude-code", "drops-detectors-ci", "drops-pr-preflight"),
)
def test_skf_end_state_guard_names_each_broken_clause(mutate, clause: str) -> None:
    """AC9 mutation: break one clause on the live inputs; exactly that clause is reported."""
    live = _live_skf_end_state()
    mutated = mutate(*live)
    assert mutated != live, "the mutation did not change its input; the planted text drifted"
    breaks = _skf_end_state_breaks(*mutated)
    assert len(breaks) == 1 and clause in breaks[0], breaks
