"""Story 17.1 — Marshal codegraph owns symbol navigation.

Fails if the AGENTS.md session-path sentences leave the file, or if they
are moved inside the managed ``bmad:context`` block.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[6]
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GRAPHIFY = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe" / "extras" / "graphify.py"

_NAV_OWNER = "Marshal `codegraph`"
_NAV_DB = "`.codegraph/codegraph.db`"
_NAV_OWNS = "owns symbol navigation"
_FORBID_MODE_CODE = "Do not use `scribe recall --mode code` for symbols"


def _session_path_text() -> str:
    text = _AGENTS.read_text(encoding="utf-8")
    close = "<!-- /bmad:context -->"
    idx = text.find(close)
    assert idx != -1, "AGENTS.md missing /bmad:context closer"
    return text[idx + len(close) :]


def test_agents_outside_bmad_context_names_codegraph_nav_owner() -> None:
    outside = _session_path_text()
    assert _NAV_OWNER in outside
    assert _NAV_DB in outside
    assert _NAV_OWNS in outside


def test_agents_outside_bmad_context_forbids_mode_code_for_symbols() -> None:
    outside = _session_path_text()
    assert _FORBID_MODE_CODE in outside


def test_graphify_docstring_says_not_the_nav_api() -> None:
    text = _GRAPHIFY.read_text(encoding="utf-8")
    assert "not the symbol-navigation API" in text
    assert "owns" in text and "symbol" in text
